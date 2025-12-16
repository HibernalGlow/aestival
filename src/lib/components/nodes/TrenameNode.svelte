<script lang="ts">
  /**
   * TrenameNode - 批量重命名节点
   * 使用区块系统，支持普通模式（Bento Grid）和全屏模式（GridStack）
   * 使用 nodeStateStore 在全屏和普通模式间共享状态
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import * as TreeView from '$lib/components/ui/tree-view';
  import { DashboardGrid, DashboardItem } from '$lib/components/ui/dashboard-grid';
  import type { GridItem } from '$lib/components/ui/dashboard-grid';
  import { BlockCard } from '$lib/components/blocks';
  import { TRENAME_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import { getDefaultPreset } from '$lib/stores/layoutPresets';
  import NodeWrapper from './NodeWrapper.svelte';
  import { 
    LoaderCircle, FolderOpen, Clipboard, FilePenLine, Search, Undo2,
    Download, Upload, TriangleAlert, Play, RefreshCw,
    File, Folder, Trash2, PanelRightOpen, PanelRightClose, Settings2, Check, Copy
  } from '@lucide/svelte';
  import {
    type TreeNode, type TrenameState, type Phase, type OperationRecord,
    isDir, getNodeStatus, parseTree, getPhaseBorderClass,
    DEFAULT_GRID_LAYOUT, DEFAULT_STATS, DEFAULT_EXCLUDE_EXTS, generateDownloadFilename
  } from './trename-utils';
  
  export let id: string;
  export let data: { config?: { path?: string }; logs?: string[]; showTree?: boolean } = {};
  export let isFullscreenRender = false;
  
  // 从 nodeStateStore 恢复状态
  const savedState = getNodeState<TrenameState>(id);
  
  // 状态初始化
  let phase: Phase = savedState?.phase ?? 'idle';
  let logs: string[] = savedState?.logs ?? (data?.logs ? [...data.logs] : []);
  let copied = false;

  // 配置
  let scanPath = savedState?.scanPath ?? data?.config?.path ?? '';
  let includeHidden = savedState?.includeHidden ?? false;
  let excludeExts = savedState?.excludeExts ?? DEFAULT_EXCLUDE_EXTS;
  let maxLines = savedState?.maxLines ?? 1000;
  let useCompact = savedState?.useCompact ?? true;
  let basePath = savedState?.basePath ?? '';
  let dryRun = savedState?.dryRun ?? false;
  
  // 数据
  let treeData: TreeNode[] = savedState?.treeData ?? [];
  let segments: string[] = savedState?.segments ?? [];
  let currentSegment = savedState?.currentSegment ?? 0;
  let stats = savedState?.stats ?? { ...DEFAULT_STATS };
  let conflicts: string[] = savedState?.conflicts ?? [];
  let lastOperationId = savedState?.lastOperationId ?? '';
  let operationHistory: OperationRecord[] = savedState?.operationHistory ?? [];
  
  // GridStack 布局
  function getInitialLayout(): GridItem[] {
    if (savedState?.gridLayout) return savedState.gridLayout;
    const defaultPreset = getDefaultPreset('trename');
    if (defaultPreset) return [...defaultPreset.layout];
    return [...TRENAME_DEFAULT_GRID_LAYOUT];
  }
  let gridLayout: GridItem[] = getInitialLayout();
  
  let dashboardGrid: { compact: () => void; applyLayout: (layout: GridItem[]) => void } | undefined;

  function handleLayoutChange(newLayout: GridItem[]) { gridLayout = newLayout; saveState(); }
  function getLayoutItem(itemId: string): GridItem {
    return gridLayout.find(item => item.id === itemId) ?? { id: itemId, x: 0, y: 0, w: 1, h: 1 };
  }
  
  function saveState() {
    setNodeState<TrenameState>(id, {
      phase, logs, showTree: true, showOptions: true, showJsonInput: false, jsonInputText: '',
      scanPath, includeHidden, excludeExts, maxLines, useCompact, basePath, dryRun,
      treeData, segments, currentSegment, stats, conflicts, lastOperationId, operationHistory, gridLayout
    });
  }
  
  $: if (phase || treeData || segments || stats || gridLayout) saveState();
  $: isRunning = phase === 'scanning' || phase === 'renaming';
  $: canRename = phase === 'ready' && stats.ready > 0;
  $: borderClass = getPhaseBorderClass(phase);

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
  
  async function copyLogs() { try { await navigator.clipboard.writeText(logs.join('\n')); } catch {} }
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

<!-- ========== 区块内容 Snippets ========== -->

<!-- 路径输入区块 -->
{#snippet pathBlockContent()}
  <div class="flex gap-2 {isFullscreenRender ? 'mb-4' : 'mb-2'}">
    <Input bind:value={scanPath} placeholder="输入目录路径..." disabled={isRunning} class="flex-1 {isFullscreenRender ? 'h-10' : 'h-7 text-xs'}" />
    <Button variant="outline" size="icon" class="{isFullscreenRender ? 'h-10 w-10' : 'h-7 w-7'} shrink-0" onclick={selectFolder} disabled={isRunning}>
      <FolderOpen class="{isFullscreenRender ? 'h-4 w-4' : 'h-3 w-3'}" />
    </Button>
    <Button variant="outline" size="icon" class="{isFullscreenRender ? 'h-10 w-10' : 'h-7 w-7'} shrink-0" onclick={pastePath} disabled={isRunning}>
      <Clipboard class="{isFullscreenRender ? 'h-4 w-4' : 'h-3 w-3'}" />
    </Button>
  </div>
  {#if isFullscreenRender}
    <div class="flex gap-2">
      <Button variant="outline" class="flex-1 h-12" onclick={() => handleScan(false)} disabled={isRunning}>
        {#if isRunning && phase === 'scanning'}<LoaderCircle class="h-4 w-4 mr-2 animate-spin" />{:else}<RefreshCw class="h-4 w-4 mr-2" />{/if}替换扫描
      </Button>
      <Button variant="outline" class="flex-1 h-12" onclick={() => handleScan(true)} disabled={isRunning}>
        <Download class="h-4 w-4 mr-2" />合并扫描
      </Button>
    </div>
  {/if}
{/snippet}


<!-- 扫描区块（普通模式） -->
{#snippet scanBlockContent()}
  <div class="flex gap-1">
    <Button variant="outline" size="sm" class="flex-1 h-7 text-xs" onclick={() => handleScan(false)} disabled={isRunning}>
      {#if isRunning && phase === 'scanning'}<LoaderCircle class="h-3 w-3 mr-1 animate-spin" />{/if}替换
    </Button>
    <Button variant="outline" size="sm" class="flex-1 h-7 text-xs" onclick={() => handleScan(true)} disabled={isRunning}>合并</Button>
  </div>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlockContent()}
  <div class="flex flex-col gap-{isFullscreenRender ? '2' : '1.5'} {isFullscreenRender ? 'flex-1 justify-center' : ''}">
    {#if isFullscreenRender}
      <Button variant="outline" class="h-12" onclick={validate} disabled={isRunning || !segments.length}>
        <Search class="h-4 w-4 mr-2" />检测冲突
      </Button>
      <Button variant={canRename ? 'default' : 'outline'} class="h-12" onclick={handleRename} disabled={isRunning || !canRename}>
        {#if phase === 'renaming'}<LoaderCircle class="h-4 w-4 mr-2 animate-spin" />{:else}<Play class="h-4 w-4 mr-2" />{/if}执行重命名
      </Button>
      <Button variant="ghost" class="h-10" onclick={clear}><Trash2 class="h-4 w-4 mr-2" />清空</Button>
    {:else}
      {#if phase === 'idle' || phase === 'error'}
        <Button class="flex-1 h-8 text-xs" onclick={() => handleScan(false)} disabled={!scanPath.trim()}>
          <Search class="h-3 w-3 mr-1" />扫描
        </Button>
      {:else if phase === 'scanning'}
        <Button class="flex-1 h-8 text-xs" disabled><LoaderCircle class="h-3 w-3 mr-1 animate-spin" />扫描中</Button>
      {:else if phase === 'ready' || phase === 'completed'}
        <Button class="flex-1 h-8 text-xs" onclick={handleRename} disabled={!canRename}><Play class="h-3 w-3 mr-1" />执行</Button>
        <Button variant="outline" class="h-6 text-xs" onclick={clear}>重置</Button>
      {:else if phase === 'renaming'}
        <Button class="flex-1 h-8 text-xs" disabled><LoaderCircle class="h-3 w-3 mr-1 animate-spin" />执行中</Button>
      {/if}
    {/if}
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlockContent()}
  {#if isFullscreenRender}
    <div class="space-y-2 flex-1">
      <div class="flex items-center justify-between p-2 bg-muted/50 rounded-lg">
        <span class="text-sm">总计</span><span class="text-xl font-bold">{stats.total}</span>
      </div>
      <div class="flex items-center justify-between p-2 bg-yellow-500/10 rounded-lg">
        <span class="text-sm">待翻译</span><span class="text-xl font-bold text-yellow-600">{stats.pending}</span>
      </div>
      <div class="flex items-center justify-between p-2 bg-green-500/10 rounded-lg">
        <span class="text-sm">就绪</span><span class="text-xl font-bold text-green-600">{stats.ready}</span>
      </div>
      {#if stats.conflicts > 0}
        <div class="flex items-center justify-between p-2 bg-red-500/10 rounded-lg">
          <span class="text-sm">冲突</span><span class="text-xl font-bold text-red-600">{stats.conflicts}</span>
        </div>
      {/if}
    </div>
  {:else}
    <div class="grid grid-cols-3 gap-1 text-xs">
      <div class="text-center p-1.5 bg-muted/50 rounded-lg"><div class="font-bold">{stats.total}</div><div class="text-muted-foreground text-[10px]">总计</div></div>
      <div class="text-center p-1.5 bg-yellow-500/10 rounded-lg"><div class="font-bold text-yellow-600">{stats.pending}</div><div class="text-muted-foreground text-[10px]">待翻译</div></div>
      <div class="text-center p-1.5 bg-green-500/10 rounded-lg"><div class="font-bold text-green-600">{stats.ready}</div><div class="text-muted-foreground text-[10px]">就绪</div></div>
    </div>
  {/if}
{/snippet}


<!-- 导入导出区块 -->
{#snippet importExportBlockContent()}
  {#if isFullscreenRender}
    <div class="h-full flex items-center gap-3">
      <Button variant="outline" class="flex-1 h-10" onclick={importJson} disabled={isRunning}>
        <Upload class="h-4 w-4 mr-2" />从剪贴板导入
      </Button>
      <Button variant="outline" class="flex-1 h-10" onclick={() => copySegment(currentSegment)} disabled={!segments.length}>
        {#if copied}<Check class="h-4 w-4 mr-2 text-green-500" />{:else}<Clipboard class="h-4 w-4 mr-2" />{/if}复制当前段
      </Button>
      <Button variant="outline" class="h-10 w-10 shrink-0" onclick={() => downloadSegment(currentSegment)} disabled={!segments.length}>
        <Download class="h-4 w-4" />
      </Button>
      {#if segments.length > 1}
        <div class="flex items-center gap-1 text-sm">
          <span class="text-muted-foreground">段:</span>
          {#each segments as _, i}
            <Button variant={currentSegment === i ? 'default' : 'ghost'} size="sm" class="h-7 w-7 p-0"
              onclick={() => { currentSegment = i; treeData = parseTree(segments[i]); }}>{i + 1}</Button>
          {/each}
        </div>
      {/if}
    </div>
  {:else}
    <div class="flex gap-1 flex-wrap">
      <Button variant="ghost" size="sm" class="h-6 text-xs px-2" onclick={importJson} disabled={isRunning}>
        <Upload class="h-3 w-3 mr-1" />导入
      </Button>
      <Button variant="ghost" size="sm" class="h-6 text-xs px-2" onclick={() => copySegment(currentSegment)} disabled={!segments.length}>
        {#if copied}<Check class="h-3 w-3 mr-1 text-green-500" />{:else}<Clipboard class="h-3 w-3 mr-1" />{/if}复制
      </Button>
      <Button variant="ghost" size="sm" class="h-6 w-6 p-0" onclick={() => downloadSegment(currentSegment)} disabled={!segments.length}>
        <Download class="h-3 w-3" />
      </Button>
    </div>
    {#if segments.length > 1}
      <div class="flex items-center gap-1 text-xs mt-2">
        <span class="text-muted-foreground">段:</span>
        {#each segments as _, i}
          <Button variant={currentSegment === i ? 'default' : 'ghost'} size="sm" class="h-5 w-5 p-0 text-xs"
            onclick={() => { currentSegment = i; treeData = parseTree(segments[i]); }}>{i + 1}</Button>
        {/each}
      </div>
    {/if}
  {/if}
{/snippet}

<!-- 文件树区块 -->
{#snippet treeBlockContent()}
  {#if isFullscreenRender}
    <div class="h-full flex flex-col overflow-hidden">
      <div class="flex items-center justify-between p-3 border-b bg-muted/30 shrink-0">
        <span class="font-semibold flex items-center gap-2"><Folder class="w-5 h-5 text-yellow-500" />文件树</span>
        <span class="text-sm text-muted-foreground">{stats.total} 项</span>
      </div>
      <div class="flex-1 overflow-y-auto p-2">
        {#if treeData.length > 0}
          <TreeView.Root class="text-sm">{#each treeData as node}{@render renderTreeNode(node)}{/each}</TreeView.Root>
        {:else}<div class="text-center text-muted-foreground py-8">扫描后显示文件树</div>{/if}
      </div>
    </div>
  {:else}
    <div class="flex items-center justify-between mb-2">
      <span class="text-xs font-semibold flex items-center gap-1"><Folder class="w-3 h-3 text-yellow-500" />文件树</span>
      <div class="flex items-center gap-2 text-[10px]">
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-yellow-500"></span>{stats.pending}</span>
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>{stats.ready}</span>
      </div>
    </div>
    <div class="max-h-40 overflow-y-auto">
      {#if treeData.length > 0}
        <TreeView.Root class="text-xs">{#each treeData as node}{@render renderTreeNode(node)}{/each}</TreeView.Root>
      {:else}<div class="text-xs text-muted-foreground text-center py-3">扫描后显示</div>{/if}
    </div>
  {/if}
{/snippet}


<!-- 日志区块 -->
{#snippet logBlockContent()}
  {#if isFullscreenRender}
    <div class="h-full flex flex-col">
      <div class="flex items-center justify-between mb-2 shrink-0">
        <span class="font-semibold text-sm">日志</span>
        <Button variant="ghost" size="icon" class="h-6 w-6" onclick={copyLogs}><Copy class="h-3 w-3" /></Button>
      </div>
      <div class="flex-1 overflow-y-auto bg-muted/30 rounded-xl p-2 font-mono text-xs space-y-1 mb-3" style="max-height: 120px;">
        {#if logs.length > 0}{#each logs.slice(-12) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
        {:else}<div class="text-muted-foreground text-center py-4">暂无日志</div>{/if}
      </div>
      <div class="flex items-center gap-2 mb-2 shrink-0"><Undo2 class="w-4 h-4" /><span class="font-semibold text-sm">操作历史</span></div>
      <div class="flex-1 overflow-y-auto">
        {#if operationHistory.length > 0}
          {#each operationHistory as op}
            <div class="flex items-center justify-between p-2 bg-muted/30 rounded-lg mb-1 text-xs">
              <span>{op.time} - {op.count}项</span>
              {#if op.canUndo}<Button variant="ghost" size="sm" class="h-6 px-2 text-xs" onclick={() => handleUndo(op.id)}>撤销</Button>
              {:else}<span class="text-muted-foreground">已撤销</span>{/if}
            </div>
          {/each}
        {:else}<div class="text-xs text-muted-foreground text-center py-2">暂无记录</div>{/if}
      </div>
    </div>
  {:else}
    <div class="flex items-center justify-between mb-1">
      <span class="text-xs font-semibold">日志</span>
      <Button variant="ghost" size="icon" class="h-5 w-5" onclick={copyLogs}>
        {#if copied}<Check class="h-2.5 w-2.5 text-green-500" />{:else}<Copy class="h-2.5 w-2.5" />{/if}
      </Button>
    </div>
    <div class="bg-muted/30 rounded-lg p-1.5 font-mono text-[10px] max-h-16 overflow-y-auto space-y-0.5">
      {#each logs.slice(-4) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
    </div>
  {/if}
{/snippet}

<!-- 高级选项区块 -->
{#snippet optionsBlockContent()}
  {#if isFullscreenRender}
    <div class="space-y-3">
      <div class="flex flex-wrap gap-4">
        <label class="flex items-center gap-2"><Checkbox bind:checked={includeHidden} /><span class="text-sm">包含隐藏文件</span></label>
        <label class="flex items-center gap-2"><Checkbox bind:checked={dryRun} /><span class="text-sm">模拟执行</span></label>
        <label class="flex items-center gap-2"><Checkbox bind:checked={useCompact} /><span class="text-sm">紧凑格式</span></label>
      </div>
      <div class="flex gap-4">
        <label class="flex items-center gap-2 flex-1">
          <span class="text-sm text-muted-foreground whitespace-nowrap">排除扩展名:</span>
          <Input bind:value={excludeExts} class="h-9 flex-1" placeholder=".json,.txt" />
        </label>
        <label class="flex items-center gap-2">
          <span class="text-sm text-muted-foreground whitespace-nowrap">分段行数:</span>
          <Input type="number" bind:value={maxLines} class="h-9 w-24" min={50} max={5000} step={100} />
        </label>
      </div>
    </div>
  {:else}
    <div class="flex flex-wrap gap-2 text-xs mb-2">
      <label class="flex items-center gap-1"><Checkbox bind:checked={includeHidden} class="h-3 w-3" /><span>隐藏文件</span></label>
      <label class="flex items-center gap-1"><Checkbox bind:checked={dryRun} class="h-3 w-3" /><span>模拟执行</span></label>
      <label class="flex items-center gap-1"><Checkbox bind:checked={useCompact} class="h-3 w-3" /><span>紧凑格式</span></label>
    </div>
    <div class="flex gap-2 text-xs">
      <label class="flex items-center gap-1 flex-1 min-w-0">
        <span class="text-muted-foreground whitespace-nowrap">排除:</span>
        <Input bind:value={excludeExts} class="h-6 text-xs flex-1 min-w-0" placeholder=".json,.txt" />
      </label>
      <label class="flex items-center gap-1">
        <span class="text-muted-foreground whitespace-nowrap">分段:</span>
        <Input type="number" bind:value={maxLines} class="h-6 text-xs w-16" min={50} max={5000} step={100} />
      </label>
    </div>
  {/if}
{/snippet}


<!-- ========== 主渲染 ========== -->
<div class="h-full w-full flex flex-col overflow-hidden">
  {#if !isFullscreenRender}
    <NodeResizer minWidth={240} minHeight={180} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}
  
  <NodeWrapper 
    nodeId={id} title="trename" icon={FilePenLine} status={phase} {borderClass} {isFullscreenRender}
    onCompact={() => dashboardGrid?.compact()}
    onResetLayout={() => { gridLayout = [...TRENAME_DEFAULT_GRID_LAYOUT]; dashboardGrid?.applyLayout(gridLayout); saveState(); }}
    nodeType="trename" currentLayout={gridLayout}
    onApplyLayout={(layout) => { gridLayout = layout; dashboardGrid?.applyLayout(layout); saveState(); }}
  >

    
    {#snippet children()}
      {#if isFullscreenRender}
        <!-- 全屏模式：GridStack -->
        <div class="h-full overflow-hidden">
          <DashboardGrid bind:this={dashboardGrid} columns={4} cellHeight={80} margin={12} showToolbar={false} onLayoutChange={handleLayoutChange}>
            {@const pathItem = getLayoutItem('path')}
            <DashboardItem id="path" x={pathItem.x} y={pathItem.y} w={pathItem.w} h={pathItem.h} minW={1} minH={2}>
              <BlockCard id="path" title="扫描路径" icon={FolderOpen} iconClass="text-primary" isFullscreen={true}>
                {#snippet children()}{@render pathBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            {@const opItem = getLayoutItem('operation')}
            <DashboardItem id="operation" x={opItem.x} y={opItem.y} w={opItem.w} h={opItem.h} minW={1} minH={1}>
              <BlockCard id="operation" title="操作" icon={Play} iconClass="text-green-500" isFullscreen={true}>
                {#snippet children()}{@render operationBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            {@const statsItem = getLayoutItem('stats')}
            <DashboardItem id="stats" x={statsItem.x} y={statsItem.y} w={statsItem.w} h={statsItem.h} minW={1} minH={1}>
              <BlockCard id="stats" title="统计" icon={FilePenLine} iconClass="text-blue-500" isFullscreen={true}>
                {#snippet children()}{@render statsBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            {@const importItem = getLayoutItem('importExport')}
            <DashboardItem id="importExport" x={importItem.x} y={importItem.y} w={importItem.w} h={importItem.h} minW={1} minH={1}>
              <BlockCard id="importExport" title="导入/导出" icon={Upload} iconClass="text-muted-foreground" isFullscreen={true} hideHeader={true}>
                {#snippet children()}{@render importExportBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            {@const treeItem = getLayoutItem('tree')}
            <DashboardItem id="tree" x={treeItem.x} y={treeItem.y} w={treeItem.w} h={treeItem.h} minW={1} minH={1}>
              <BlockCard id="tree" title="文件树" icon={Folder} iconClass="text-yellow-500" isFullscreen={true} fullHeight={true} hideHeader={true}>
                {#snippet children()}{@render treeBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            {@const logItem = getLayoutItem('log')}
            <DashboardItem id="log" x={logItem.x} y={logItem.y} w={logItem.w} h={logItem.h} minW={1} minH={1}>
              <BlockCard id="log" title="日志" icon={Copy} iconClass="text-muted-foreground" isFullscreen={true} fullHeight={true} hideHeader={true}>
                {#snippet children()}{@render logBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            {@const optionsItem = getLayoutItem('options')}
            <DashboardItem id="options" x={optionsItem.x} y={optionsItem.y} w={optionsItem.w} h={optionsItem.h} minW={1} minH={1}>
              <BlockCard id="options" title="高级选项" icon={Settings2} iconClass="text-muted-foreground" isFullscreen={true}>
                {#snippet children()}{@render optionsBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
          </DashboardGrid>
        </div>

      {:else}
        <!-- 普通模式：Bento Grid -->
        <div class="flex-1 overflow-y-auto p-2">
          <div class="grid grid-cols-2 gap-2" style="grid-auto-rows: minmax(auto, max-content);">
            <BlockCard id="path" title="路径" icon={FolderOpen} iconClass="text-primary" class="col-span-2">
              {#snippet children()}{@render pathBlockContent()}{/snippet}
            </BlockCard>
            
            <BlockCard id="scan" title="扫描" icon={RefreshCw} iconClass="text-blue-500" class="col-span-1">
              {#snippet children()}{@render scanBlockContent()}{/snippet}
            </BlockCard>
            
            <BlockCard id="operation" title="操作" icon={Play} iconClass="text-green-500" class="col-span-1">
              {#snippet children()}{@render operationBlockContent()}{/snippet}
            </BlockCard>
            
            <BlockCard id="stats" title="统计" icon={FilePenLine} iconClass="text-yellow-500" class="col-span-1">
              {#snippet children()}{@render statsBlockContent()}{/snippet}
            </BlockCard>
            
            <BlockCard id="importExport" title="导入/导出" icon={Upload} iconClass="text-muted-foreground" class="col-span-1">
              {#snippet children()}{@render importExportBlockContent()}{/snippet}
            </BlockCard>
            
            <BlockCard id="tree" title="文件树" icon={Folder} iconClass="text-yellow-500" class="col-span-2" collapsible={true}>
              {#snippet children()}{@render treeBlockContent()}{/snippet}
            </BlockCard>
            
            <BlockCard id="options" title="高级选项" icon={Settings2} iconClass="text-muted-foreground" class="col-span-2">
              {#snippet children()}{@render optionsBlockContent()}{/snippet}
            </BlockCard>
            
            {#if conflicts.length > 0}
              <BlockCard id="conflicts" title="冲突" icon={TriangleAlert} iconClass="text-red-500" class="col-span-2">
                {#snippet children()}
                  <div class="max-h-16 overflow-y-auto">
                    {#each conflicts as c}<div class="text-xs text-red-400 truncate" title={c}>{c}</div>{/each}
                  </div>
                {/snippet}
              </BlockCard>
            {/if}
            
            {#if logs.length > 0}
              <BlockCard id="log" title="日志" icon={Copy} iconClass="text-muted-foreground" class="col-span-2">
                {#snippet children()}{@render logBlockContent()}{/snippet}
              </BlockCard>
            {/if}
            
            {#if operationHistory.length > 0}
              <BlockCard id="history" title="操作历史" icon={Undo2} iconClass="text-muted-foreground" class="col-span-2">
                {#snippet children()}
                  <div class="max-h-20 overflow-y-auto">
                    {#each operationHistory.slice(0, 3) as op}
                      <div class="flex items-center justify-between p-1.5 bg-muted/30 rounded-lg mb-1 text-xs">
                        <span class="text-muted-foreground">{op.time} - {op.count}项</span>
                        {#if op.canUndo}<Button variant="ghost" size="sm" class="h-5 px-2 text-xs" onclick={() => handleUndo(op.id)}>撤销</Button>
                        {:else}<span class="text-muted-foreground text-[10px]">已撤销</span>{/if}
                      </div>
                    {/each}
                  </div>
                {/snippet}
              </BlockCard>
            {/if}
          </div>
        </div>
      {/if}
    {/snippet}
  </NodeWrapper>
  
  {#if !isFullscreenRender}
    <Handle type="source" position={Position.Right} class="bg-primary!" />
  {/if}
</div>
