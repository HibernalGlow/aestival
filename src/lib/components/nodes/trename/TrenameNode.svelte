<script lang="ts">
  /**
   * TrenameNode - 批量重命名节点
   * 
   * 使用 Container Query 自动响应尺寸
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import * as TreeView from '$lib/components/ui/tree-view';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { TRENAME_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    LoaderCircle, FolderOpen, Clipboard, FilePenLine, Search, Undo2,
    Download, Upload, Play, RefreshCw,
    File, Folder, Check, Copy, RotateCcw
  } from '@lucide/svelte';
  import {
    type TreeNode, type TrenameState, type Phase, type OperationRecord,
    isDir, getNodeStatus, parseTree, getPhaseBorderClass,
    DEFAULT_STATS, DEFAULT_EXCLUDE_EXTS, generateDownloadFilename
  } from './utils';

  interface Props {
    id: string;
    data?: { config?: { path?: string }; logs?: string[]; showTree?: boolean };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  // 使用 $derived 确保响应式
  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<TrenameState>(nodeId));
  const configPath = $derived(data?.config?.path ?? '');
  const dataLogs = $derived(data?.logs ?? []);

  // 状态初始化
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let copied = $state(false);

  // 配置
  let scanPath = $state('');
  let includeHidden = $state(false);
  let excludeExts = $state(DEFAULT_EXCLUDE_EXTS);
  let maxLines = $state(1000);
  let useCompact = $state(true);
  let basePath = $state('');
  let dryRun = $state(false);

  // 数据
  let treeData = $state<TreeNode[]>([]);
  let segments = $state<string[]>([]);
  let currentSegment = $state(0);
  let stats = $state({ ...DEFAULT_STATS });
  let conflicts = $state<string[]>([]);
  let lastOperationId = $state('');
  let operationHistory = $state<OperationRecord[]>([]);

  // 初始化状态
  $effect(() => {
    scanPath = savedState?.scanPath ?? configPath;
    logs = savedState?.logs ?? [...dataLogs];
    
    if (savedState) {
      phase = savedState.phase ?? 'idle';
      includeHidden = savedState.includeHidden ?? false;
      excludeExts = savedState.excludeExts ?? DEFAULT_EXCLUDE_EXTS;
      maxLines = savedState.maxLines ?? 1000;
      useCompact = savedState.useCompact ?? true;
      basePath = savedState.basePath ?? '';
      dryRun = savedState.dryRun ?? false;
      treeData = savedState.treeData ?? [];
      segments = savedState.segments ?? [];
      currentSegment = savedState.currentSegment ?? 0;
      stats = savedState.stats ?? { ...DEFAULT_STATS };
      conflicts = savedState.conflicts ?? [];
      lastOperationId = savedState.lastOperationId ?? '';
      operationHistory = savedState.operationHistory ?? [];
    }
  });

  // NodeLayoutRenderer 引用
  let layoutRenderer = $state<any>(undefined);

  function saveState() {
    setNodeState<TrenameState>(nodeId, {
      phase, logs, showTree: true, showOptions: true, showJsonInput: false, jsonInputText: '',
      scanPath, includeHidden, excludeExts, maxLines, useCompact, basePath, dryRun,
      treeData, segments, currentSegment, stats, conflicts, lastOperationId, operationHistory
    });
  }

  // 响应式派生值
  let isRunning = $derived(phase === 'scanning' || phase === 'renaming');
  let canRename = $derived(phase === 'ready' && stats.ready > 0);
  let borderClass = $derived(getPhaseBorderClass(phase));

  // 状态变化时自动保存
  $effect(() => {
    if (phase || treeData || segments || stats) saveState();
  });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  async function selectFolder() {
    try {
      const { platform } = await import('$lib/api/platform');
      const s = await platform.openFolderDialog('选择文件夹');
      if (s) scanPath = s;
    } catch (e) { log(`选择失败: ${e}`); }
  }

  async function pastePath() {
    try { scanPath = (await navigator.clipboard.readText()).trim(); } catch (e) { log(`粘贴失败: ${e}`); }
  }

  async function handleScan(merge = false) {
    if (!scanPath.trim()) { log('❌ 请输入路径'); return; }
    phase = 'scanning'; log(`🔍 ${merge ? '合并' : '替换'}扫描: ${scanPath}`);
    try {
      const r = await api.executeNode('trename', {
        action: 'scan', paths: [scanPath], include_hidden: includeHidden,
        exclude_exts: excludeExts, max_lines: maxLines, compact: useCompact
      }) as any;
      if (r.success && r.data) {
        const segs = r.data.segments || [];
        if (merge && segments.length > 0) {
          segments = [...segments, ...segs];
          stats.total += r.data.total_items || 0;
          stats.pending += r.data.pending_count || 0;
          stats.ready += r.data.ready_count || 0;
        } else {
          segments = segs;
          stats = { total: r.data.total_items || 0, pending: r.data.pending_count || 0, ready: r.data.ready_count || 0, conflicts: 0 };
          basePath = r.data.base_path || '';
        }
        if (segs.length > 0) treeData = parseTree(segs[0]);
        currentSegment = 0; conflicts = []; phase = 'ready';
        log(`✅ ${r.data.total_items} 项, ${segs.length} 段`);
      } else { phase = 'error'; log(`❌ ${r.message}`); }
    } catch (e) { phase = 'error'; log(`❌ ${e}`); }
  }

  async function importJson() {
    try {
      const text = await navigator.clipboard.readText();
      if (!text.trim()) { log('❌ 剪贴板为空'); return; }
      log('📋 导入中...');
      const r = await api.executeNode('trename', { action: 'import', json_content: text }) as any;
      if (r.success && r.data) {
        segments = [text];
        stats = { total: r.data.total_items || 0, pending: r.data.pending_count || 0, ready: r.data.ready_count || 0, conflicts: 0 };
        treeData = parseTree(text);
        currentSegment = 0; phase = 'ready';
        log(`✅ 导入 ${r.data.total_items} 项`);
      } else log(`❌ ${r.message}`);
    } catch (e) { log(`❌ ${e}`); }
  }

  async function copySegment(i: number) {
    if (i >= segments.length) return;
    try { await navigator.clipboard.writeText(segments[i]); copied = true; log(`📋 段${i+1}已复制`); setTimeout(() => copied = false, 2000); }
    catch (e) { log(`复制失败: ${e}`); }
  }

  function downloadSegment(i: number) {
    if (i >= segments.length) return;
    try {
      const blob = new Blob([segments[i]], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = generateDownloadFilename(i);
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url); log(`💾 段${i + 1}已下载`);
    } catch (e) { log(`下载失败: ${e}`); }
  }

  async function validate() {
    if (!segments.length) return;
    log('🔍 检测冲突...');
    try {
      const r = await api.executeNode('trename', { action: 'validate', json_content: segments[currentSegment], base_path: basePath }) as any;
      if (r.success) { conflicts = r.data?.conflicts || []; stats.conflicts = conflicts.length; log(conflicts.length ? `⚠️ ${conflicts.length} 冲突` : '✅ 无冲突'); }
      else log(`❌ ${r.message}`);
    } catch (e) { log(`❌ ${e}`); }
  }

  async function handleRename() {
    if (!segments.length || !stats.ready) { log('❌ 无可重命名项'); return; }
    phase = 'renaming'; log(`${dryRun ? '🔍 模拟' : '▶️ 执行'}重命名...`);
    try {
      const r = await api.executeNode('trename', { action: 'rename', json_content: segments[currentSegment], base_path: basePath, dry_run: dryRun }) as any;
      if (r.success) {
        lastOperationId = r.data?.operation_id || ''; phase = 'completed';
        const successCount = r.data?.success_count || 0;
        log(`✅ 成功${successCount} 失败${r.data?.failed_count || 0}`);
        if (lastOperationId && !dryRun) {
          operationHistory = [{ id: lastOperationId, time: new Date().toLocaleTimeString(), count: successCount, canUndo: true }, ...operationHistory].slice(0, 10);
        }
      } else { phase = 'error'; log(`❌ ${r.message}`); }
    } catch (e) { phase = 'error'; log(`❌ ${e}`); }
  }

  async function handleUndo(opId?: string) {
    const targetId = opId || lastOperationId;
    if (!targetId) { log('❌ 无可撤销操作'); return; }
    log('🔄 撤销...');
    try {
      const r = await api.executeNode('trename', { action: 'undo', batch_id: targetId }) as any;
      if (r.success) { 
        log(`✅ ${r.message}`); 
        operationHistory = operationHistory.map(op => op.id === targetId ? { ...op, canUndo: false } : op);
        if (targetId === lastOperationId) lastOperationId = '';
        phase = 'ready'; 
      } else log(`❌ ${r.message}`);
    } catch (e) { log(`❌ ${e}`); }
  }

  function clear() {
    treeData = []; segments = []; currentSegment = 0;
    stats = { ...DEFAULT_STATS }; conflicts = []; lastOperationId = ''; phase = 'idle';
    log('🗑️ 已清空');
  }

  async function copyLogs() { 
    try { await navigator.clipboard.writeText(logs.join('\n')); copied = true; setTimeout(() => copied = false, 2000); } catch {} 
  }
</script>


<!-- 递归渲染文件树 -->
{#snippet renderTreeNode(node: TreeNode)}
  {@const dir = isDir(node)}
  {@const status = getNodeStatus(node)}
  {@const srcName = dir ? node.src_dir : node.src}
  {@const tgt = dir ? node.tgt_dir : node.tgt}
  {@const statusClass = status === 'ready' ? 'bg-green-500' : status === 'pending' ? 'bg-yellow-500' : 'bg-gray-300'}
  {@const hasChange = tgt && tgt !== srcName}

  {#if dir}
    <TreeView.Folder name={srcName} open={true} class="text-xs">
      {#snippet icon()}
        <div class="flex items-center gap-1">
          <Folder class="w-3 h-3 text-yellow-500 shrink-0" />
          <span class="w-2 h-2 rounded-full shrink-0 {statusClass}"></span>
        </div>
      {/snippet}
      {#snippet children()}
        {#if hasChange}<div class="text-xs text-green-600 pl-4 py-0.5 truncate" title={tgt}>→ {tgt}</div>{/if}
        {#if node.children}{#each node.children as child}{@render renderTreeNode(child)}{/each}{/if}
      {/snippet}
    </TreeView.Folder>
  {:else}
    <div class="flex flex-col py-0.5 text-xs pl-1">
      <div class="flex items-center gap-1">
        <File class="w-3 h-3 text-blue-500 shrink-0" />
        <span class="truncate flex-1" title={srcName}>{srcName}</span>
        <span class="w-2 h-2 rounded-full shrink-0 {statusClass}"></span>
      </div>
      {#if hasChange}<div class="text-green-600 pl-4 truncate" title={tgt}>→ {tgt}</div>{/if}
    </div>
  {/if}
{/snippet}


<!-- ========== 区块内容 Snippets（使用 Container Query CSS） ========== -->

<!-- 路径输入区块 -->
{#snippet pathBlock()}
  <div class="flex cq-gap cq-mb">
    <Input bind:value={scanPath} placeholder="输入目录路径..." disabled={isRunning} class="flex-1 cq-input" />
    <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={selectFolder} disabled={isRunning}>
      <FolderOpen class="cq-icon" />
    </Button>
    <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={pastePath} disabled={isRunning}>
      <Clipboard class="cq-icon" />
    </Button>
  </div>
  <div class="cq-wide-only-flex cq-gap">
    <Button variant="outline" class="flex-1 cq-button" onclick={() => handleScan(false)} disabled={isRunning}>
      {#if isRunning && phase === 'scanning'}<LoaderCircle class="cq-icon mr-2 animate-spin" />{:else}<RefreshCw class="cq-icon mr-2" />{/if}替换扫描
    </Button>
    <Button variant="outline" class="flex-1 cq-button" onclick={() => handleScan(true)} disabled={isRunning}>
      <Download class="cq-icon mr-2" />合并扫描
    </Button>
  </div>
{/snippet}

<!-- 扫描区块（紧凑模式） -->
{#snippet scanBlock()}
  <div class="flex cq-gap">
    <Button variant="outline" size="sm" class="flex-1 cq-button" onclick={() => handleScan(false)} disabled={isRunning}>
      {#if isRunning && phase === 'scanning'}<LoaderCircle class="cq-icon-sm mr-1 animate-spin" />{/if}替换
    </Button>
    <Button variant="outline" size="sm" class="flex-1 cq-button" onclick={() => handleScan(true)} disabled={isRunning}>合并</Button>
  </div>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <!-- 状态指示 -->
    <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded">
      {#if phase === 'completed'}
        <Check class="cq-icon text-green-500 shrink-0" />
        <span class="cq-text text-green-600 font-medium">完成</span>
      {:else if phase === 'error'}
        <span class="cq-text text-red-600 font-medium">错误</span>
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <span class="cq-text text-muted-foreground">{phase === 'scanning' ? '扫描中' : '执行中'}</span>
      {:else}
        <FilePenLine class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text text-muted-foreground">等待扫描</span>
      {/if}
    </div>
    <!-- 主按钮 -->
    {#if phase === 'idle' || phase === 'error'}
      <Button class="w-full cq-button flex-1" onclick={() => handleScan(false)} disabled={!scanPath.trim()}>
        <Search class="cq-icon mr-1" /><span>扫描</span>
      </Button>
    {:else if phase === 'scanning'}
      <Button class="w-full cq-button flex-1" disabled>
        <LoaderCircle class="cq-icon mr-1 animate-spin" /><span>扫描中</span>
      </Button>
    {:else if phase === 'ready' || phase === 'completed'}
      <Button class="w-full cq-button flex-1" onclick={handleRename} disabled={!canRename}>
        <Play class="cq-icon mr-1" /><span>执行重命名</span>
      </Button>
    {:else if phase === 'renaming'}
      <Button class="w-full cq-button flex-1" disabled>
        <LoaderCircle class="cq-icon mr-1 animate-spin" /><span>执行中</span>
      </Button>
    {/if}
    <!-- 辅助按钮 -->
    <div class="flex cq-gap">
      <Button variant="outline" class="flex-1 cq-button-sm" onclick={validate} disabled={isRunning || !segments.length}>
        <Search class="cq-icon mr-1" />检测冲突
      </Button>
      <Button variant="ghost" class="flex-1 cq-button-sm" onclick={clear} disabled={isRunning}>
        <RotateCcw class="cq-icon mr-1" />清空
      </Button>
    </div>
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlock()}
  <div class="grid grid-cols-3 cq-gap">
    <div class="cq-stat-card bg-muted/40">
      <div class="flex flex-col items-center">
        <span class="cq-stat-value tabular-nums">{stats.total}</span>
        <span class="cq-stat-label text-muted-foreground">总计</span>
      </div>
    </div>
    <div class="cq-stat-card bg-yellow-500/10">
      <div class="flex flex-col items-center">
        <span class="cq-stat-value text-yellow-600 tabular-nums">{stats.pending}</span>
        <span class="cq-stat-label text-muted-foreground">待翻译</span>
      </div>
    </div>
    <div class="cq-stat-card bg-green-500/10">
      <div class="flex flex-col items-center">
        <span class="cq-stat-value text-green-600 tabular-nums">{stats.ready}</span>
        <span class="cq-stat-label text-muted-foreground">就绪</span>
      </div>
    </div>
  </div>
{/snippet}

<!-- 导入导出区块 -->
{#snippet importExportBlock()}
  <div class="flex cq-gap flex-wrap">
    <Button variant="ghost" size="sm" class="cq-button-sm" onclick={importJson} disabled={isRunning}>
      <Upload class="cq-icon mr-1" />导入
    </Button>
    <Button variant="ghost" size="sm" class="cq-button-sm" onclick={() => copySegment(currentSegment)} disabled={!segments.length}>
      {#if copied}<Check class="cq-icon mr-1 text-green-500" />{:else}<Clipboard class="cq-icon mr-1" />{/if}复制
    </Button>
    <Button variant="ghost" size="sm" class="cq-button-sm" onclick={() => downloadSegment(currentSegment)} disabled={!segments.length}>
      <Download class="cq-icon" />
    </Button>
  </div>
  {#if segments.length > 1}
    <div class="flex items-center gap-1 cq-text mt-2">
      <span class="text-muted-foreground">段:</span>
      {#each segments as _, i}
        <Button variant={currentSegment === i ? 'default' : 'ghost'} size="sm" class="h-5 w-5 p-0 cq-text"
          onclick={() => { currentSegment = i; treeData = parseTree(segments[i]); }}>{i + 1}</Button>
      {/each}
    </div>
  {/if}
{/snippet}

<!-- 高级选项区块 -->
{#snippet optionsBlock()}
  <div class="flex flex-wrap cq-gap cq-text mb-2">
    <label class="flex items-center gap-1"><Checkbox bind:checked={includeHidden} class="h-3 w-3" /><span>隐藏文件</span></label>
    <label class="flex items-center gap-1"><Checkbox bind:checked={dryRun} class="h-3 w-3" /><span>模拟执行</span></label>
    <label class="flex items-center gap-1"><Checkbox bind:checked={useCompact} class="h-3 w-3" /><span>紧凑格式</span></label>
  </div>
  <div class="flex cq-gap cq-text">
    <label class="flex items-center gap-1 flex-1 min-w-0">
      <span class="text-muted-foreground whitespace-nowrap">排除:</span>
      <Input bind:value={excludeExts} class="cq-input flex-1 min-w-0" placeholder=".json,.txt" />
    </label>
    <label class="flex items-center gap-1">
      <span class="text-muted-foreground whitespace-nowrap">分段:</span>
      <Input type="number" bind:value={maxLines} class="cq-input w-16" min={50} max={5000} step={100} />
    </label>
  </div>
{/snippet}

<!-- 文件树区块 -->
{#snippet treeBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold flex items-center gap-1">
        <Folder class="cq-icon text-yellow-500" />文件树
      </span>
      <div class="flex items-center cq-gap cq-text-sm">
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-yellow-500"></span>{stats.pending}</span>
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>{stats.ready}</span>
      </div>
    </div>
    <div class="flex-1 overflow-y-auto cq-padding">
      {#if treeData.length > 0}
        <TreeView.Root class="text-xs">{#each treeData as node}{@render renderTreeNode(node)}{/each}</TreeView.Root>
      {:else}<div class="cq-text text-muted-foreground text-center py-3">扫描后显示</div>{/if}
    </div>
  </div>
{/snippet}

<!-- 日志区块 -->
{#snippet logBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold">日志</span>
      <Button variant="ghost" size="icon" class="h-5 w-5" onclick={copyLogs}>
        {#if copied}<Check class="w-3 h-3 text-green-500" />{:else}<Copy class="w-3 h-3" />{/if}
      </Button>
    </div>
    <div class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding font-mono cq-text-sm space-y-0.5 mb-2" style="max-height: 80px;">
      {#if logs.length > 0}
        {#each logs.slice(-8) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
    <div class="flex items-center gap-2 mb-1 shrink-0"><Undo2 class="cq-icon" /><span class="cq-text font-semibold">操作历史</span></div>
    <div class="flex-1 overflow-y-auto">
      {#if operationHistory.length > 0}
        {#each operationHistory as op}
          <div class="flex items-center justify-between cq-padding bg-muted/30 cq-rounded mb-1 cq-text-sm">
            <span>{op.time} - {op.count}项</span>
            {#if op.canUndo}<Button variant="ghost" size="sm" class="h-5 px-2 cq-text-sm" onclick={() => handleUndo(op.id)}>撤销</Button>
            {:else}<span class="text-muted-foreground">已撤销</span>{/if}
          </div>
        {/each}
      {:else}<div class="cq-text-sm text-muted-foreground text-center py-2">暂无记录</div>{/if}
    </div>
  </div>
{/snippet}

<!-- 通用区块渲染器 -->
{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'path'}{@render pathBlock()}
  {:else if blockId === 'scan'}{@render scanBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'stats'}{@render statsBlock()}
  {:else if blockId === 'importExport'}{@render importExportBlock()}
  {:else if blockId === 'options'}{@render optionsBlock()}
  {:else if blockId === 'tree'}{@render treeBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}


<!-- ========== 主渲染 ========== -->
<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 400px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={200} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="trename" 
    icon={FilePenLine} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="trename" 
    currentLayout={layoutRenderer?.getCurrentLayout()}
    currentTabGroups={layoutRenderer?.getCurrentTabGroups()}
    onApplyLayout={(layout, tabGroups) => layoutRenderer?.applyLayout(layout, tabGroups)}
    canCreateTab={true}
    onCreateTab={(blockIds) => layoutRenderer?.createTab(blockIds)}
    layoutMode={isFullscreenRender ? 'fullscreen' : 'normal'}
  >
    {#snippet children()}
      <NodeLayoutRenderer
        bind:this={layoutRenderer}
        nodeId={nodeId}
        nodeType="trename"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={TRENAME_DEFAULT_GRID_LAYOUT}
      >
        {#snippet renderBlock(blockId: string)}
          {@render renderBlockContent(blockId)}
        {/snippet}
      </NodeLayoutRenderer>
    {/snippet}
  </NodeWrapper>

  {#if !isFullscreenRender}
    <Handle type="source" position={Position.Right} class="bg-primary!" />
  {/if}
</div>
