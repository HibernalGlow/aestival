<script lang="ts">
  /**
   * TrenameNode - 批量重命名节点
   * 使用 NodeLayoutRenderer 统一布局，支持节点模式和全屏模式
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import * as TreeView from '$lib/components/ui/tree-view';

  import { InteractiveHover } from '$lib/components/ui/interactive-hover';
  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { TRENAME_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { getSizeClasses, type SizeMode } from '$lib/utils/sizeUtils';
  import { 
    LoaderCircle, FolderOpen, Clipboard, FilePenLine, Search, Undo2,
    Download, Upload, TriangleAlert, Play, RefreshCw,
    File, Folder, Trash2, Settings2, Check, Copy, RotateCcw
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

  // 从 nodeStateStore 恢复状态
  const savedState = getNodeState<TrenameState>(id);

  // 状态初始化
  let phase = $state<Phase>(savedState?.phase ?? 'idle');
  let logs = $state<string[]>(savedState?.logs ?? (data?.logs ? [...data.logs] : []));
  let copied = $state(false);

  // 配置
  let scanPath = $state(savedState?.scanPath ?? data?.config?.path ?? '');
  let includeHidden = $state(savedState?.includeHidden ?? false);
  let excludeExts = $state(savedState?.excludeExts ?? DEFAULT_EXCLUDE_EXTS);
  let maxLines = $state(savedState?.maxLines ?? 1000);
  let useCompact = $state(savedState?.useCompact ?? true);
  let basePath = $state(savedState?.basePath ?? '');
  let dryRun = $state(savedState?.dryRun ?? false);

  // 数据
  let treeData = $state<TreeNode[]>(savedState?.treeData ?? []);
  let segments = $state<string[]>(savedState?.segments ?? []);
  let currentSegment = $state(savedState?.currentSegment ?? 0);
  let stats = $state(savedState?.stats ?? { ...DEFAULT_STATS });
  let conflicts = $state<string[]>(savedState?.conflicts ?? []);
  let lastOperationId = $state(savedState?.lastOperationId ?? '');
  let operationHistory = $state<OperationRecord[]>(savedState?.operationHistory ?? []);

  // NodeLayoutRenderer 引用
  let layoutRenderer = $state<{ 
    createTab: (blockIds: string[]) => void;
    getUsedBlockIdsForTab: () => string[];
    compact: () => void;
    resetLayout: () => void;
    applyLayout: (layout: any[]) => void;
    getCurrentLayout: () => any[];
    getCurrentTabGroups: () => any[];
  } | undefined>(undefined);

  function saveState() {
    setNodeState<TrenameState>(id, {
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


<!-- ========== 区块内容 Snippets（参数化尺寸） ========== -->

<!-- 路径输入区块 -->
{#snippet pathBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="flex {c.gap} {c.mb}">
    <Input bind:value={scanPath} placeholder="输入目录路径..." disabled={isRunning} class="flex-1 {c.input}" />
    <Button variant="outline" size="icon" class="{c.buttonIcon} shrink-0" onclick={selectFolder} disabled={isRunning}>
      <FolderOpen class={c.icon} />
    </Button>
    <Button variant="outline" size="icon" class="{c.buttonIcon} shrink-0" onclick={pastePath} disabled={isRunning}>
      <Clipboard class={c.icon} />
    </Button>
  </div>
  {#if size === 'normal'}
    <div class="flex {c.gap}">
      <Button variant="outline" class="flex-1 {c.button}" onclick={() => handleScan(false)} disabled={isRunning}>
        {#if isRunning && phase === 'scanning'}<LoaderCircle class="{c.icon} mr-2 animate-spin" />{:else}<RefreshCw class="{c.icon} mr-2" />{/if}替换扫描
      </Button>
      <Button variant="outline" class="flex-1 {c.button}" onclick={() => handleScan(true)} disabled={isRunning}>
        <Download class="{c.icon} mr-2" />合并扫描
      </Button>
    </div>
  {/if}
{/snippet}

<!-- 扫描区块（紧凑模式） -->
{#snippet scanBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="flex {c.gapSm}">
    <Button variant="outline" size="sm" class="flex-1 {c.button}" onclick={() => handleScan(false)} disabled={isRunning}>
      {#if isRunning && phase === 'scanning'}<LoaderCircle class="{c.iconSm} mr-1 animate-spin" />{/if}替换
    </Button>
    <Button variant="outline" size="sm" class="flex-1 {c.button}" onclick={() => handleScan(true)} disabled={isRunning}>合并</Button>
  </div>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="flex flex-col {c.gap} {size === 'normal' ? 'flex-1 justify-center' : ''}">
    {#if size === 'normal'}
      <InteractiveHover text="检测冲突" class="w-full h-10 text-sm" onclick={validate} disabled={isRunning || !segments.length}>
        {#snippet icon()}<Search class="h-4 w-4" />{/snippet}
      </InteractiveHover>
      <InteractiveHover text="执行重命名" class="w-full h-12 text-sm" onclick={handleRename} disabled={isRunning || !canRename}>
        {#snippet icon()}
          {#if phase === 'renaming'}<LoaderCircle class="h-4 w-4 animate-spin" />{:else}<Play class="h-4 w-4" />{/if}
        {/snippet}
      </InteractiveHover>
      <!-- 重置按钮常驻 -->
      <Button variant="ghost" class="h-9" onclick={clear} disabled={isRunning}><RotateCcw class="h-4 w-4 mr-2" />清空</Button>
    {:else}
      <!-- 紧凑模式 -->
      <div class="flex {c.gapSm}">
        {#if phase === 'idle' || phase === 'error'}
          <Button class="flex-1 {c.button}" onclick={() => handleScan(false)} disabled={!scanPath.trim()}>
            <Search class="{c.icon} mr-1" />扫描
          </Button>
        {:else if phase === 'scanning'}
          <Button class="flex-1 {c.button}" disabled><LoaderCircle class="{c.icon} mr-1 animate-spin" />扫描中</Button>
        {:else if phase === 'ready' || phase === 'completed'}
          <Button class="flex-1 {c.button}" onclick={handleRename} disabled={!canRename}><Play class="{c.icon} mr-1" />执行</Button>
        {:else if phase === 'renaming'}
          <Button class="flex-1 {c.button}" disabled><LoaderCircle class="{c.icon} mr-1 animate-spin" />执行中</Button>
        {/if}
        <!-- 重置按钮常驻 -->
        <Button variant="ghost" size="icon" class="{c.buttonIcon}" onclick={clear} disabled={isRunning} title="清空">
          <RotateCcw class={c.icon} />
        </Button>
      </div>
    {/if}
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlock(size: SizeMode)}
  {#if size === 'normal'}
    <div class="space-y-2 flex-1">
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-muted/60 to-muted/30 rounded-xl border border-border/50">
        <span class="text-sm text-muted-foreground">总计</span>
        <span class="text-2xl font-bold tabular-nums">{stats.total}</span>
      </div>
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-yellow-500/15 to-yellow-500/5 rounded-xl border border-yellow-500/20">
        <span class="text-sm text-muted-foreground">待翻译</span>
        <span class="text-2xl font-bold text-yellow-600 tabular-nums">{stats.pending}</span>
      </div>
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-green-500/15 to-green-500/5 rounded-xl border border-green-500/20">
        <span class="text-sm text-muted-foreground">就绪</span>
        <span class="text-2xl font-bold text-green-600 tabular-nums">{stats.ready}</span>
      </div>
      {#if stats.conflicts > 0}
        <div class="flex items-center justify-between p-3 bg-gradient-to-r from-red-500/15 to-red-500/5 rounded-xl border border-red-500/20">
          <span class="text-sm text-muted-foreground">冲突</span>
          <span class="text-2xl font-bold text-red-600 tabular-nums">{stats.conflicts}</span>
        </div>
      {/if}
    </div>
  {:else}
    <div class="grid grid-cols-3 gap-1.5">
      <div class="text-center p-1.5 bg-muted/40 rounded-lg">
        <div class="text-sm font-bold tabular-nums">{stats.total}</div>
        <div class="text-[10px] text-muted-foreground">总计</div>
      </div>
      <div class="text-center p-1.5 bg-yellow-500/10 rounded-lg">
        <div class="text-sm font-bold text-yellow-600 tabular-nums">{stats.pending}</div>
        <div class="text-[10px] text-muted-foreground">待翻译</div>
      </div>
      <div class="text-center p-1.5 bg-green-500/10 rounded-lg">
        <div class="text-sm font-bold text-green-600 tabular-nums">{stats.ready}</div>
        <div class="text-[10px] text-muted-foreground">就绪</div>
      </div>
    </div>
  {/if}
{/snippet}

<!-- 导入导出区块 -->
{#snippet importExportBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if size === 'normal'}
    <div class="h-full flex items-center {c.gap}">
      <InteractiveHover text="从剪贴板导入" class="flex-1 h-10 text-xs" onclick={importJson} disabled={isRunning}>
        {#snippet icon()}<Upload class="h-4 w-4" />{/snippet}
      </InteractiveHover>
      <InteractiveHover text="复制当前段" class="flex-1 h-10 text-xs" onclick={() => copySegment(currentSegment)} disabled={!segments.length}>
        {#snippet icon()}
          {#if copied}<Check class="h-4 w-4 text-green-500" />{:else}<Clipboard class="h-4 w-4" />{/if}
        {/snippet}
      </InteractiveHover>
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
    <div class="flex {c.gapSm} flex-wrap">
      <Button variant="ghost" size="sm" class="h-6 {c.text} px-2" onclick={importJson} disabled={isRunning}>
        <Upload class="{c.iconSm} mr-1" />导入
      </Button>
      <Button variant="ghost" size="sm" class="h-6 {c.text} px-2" onclick={() => copySegment(currentSegment)} disabled={!segments.length}>
        {#if copied}<Check class="{c.iconSm} mr-1 text-green-500" />{:else}<Clipboard class="{c.iconSm} mr-1" />{/if}复制
      </Button>
      <Button variant="ghost" size="sm" class="h-6 w-6 p-0" onclick={() => downloadSegment(currentSegment)} disabled={!segments.length}>
        <Download class={c.iconSm} />
      </Button>
    </div>
    {#if segments.length > 1}
      <div class="flex items-center gap-1 {c.text} mt-2">
        <span class="text-muted-foreground">段:</span>
        {#each segments as _, i}
          <Button variant={currentSegment === i ? 'default' : 'ghost'} size="sm" class="h-5 w-5 p-0 {c.text}"
            onclick={() => { currentSegment = i; treeData = parseTree(segments[i]); }}>{i + 1}</Button>
        {/each}
      </div>
    {/if}
  {/if}
{/snippet}

<!-- 高级选项区块 -->
{#snippet optionsBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if size === 'normal'}
    <div class={c.space}>
      <div class="flex flex-wrap {c.gap}">
        <label class="flex items-center gap-2"><Checkbox bind:checked={includeHidden} /><span class={c.text}>包含隐藏文件</span></label>
        <label class="flex items-center gap-2"><Checkbox bind:checked={dryRun} /><span class={c.text}>模拟执行</span></label>
        <label class="flex items-center gap-2"><Checkbox bind:checked={useCompact} /><span class={c.text}>紧凑格式</span></label>
      </div>
      <div class="flex {c.gap}">
        <label class="flex items-center gap-2 flex-1">
          <span class="{c.text} text-muted-foreground whitespace-nowrap">排除扩展名:</span>
          <Input bind:value={excludeExts} class="h-9 flex-1" placeholder=".json,.txt" />
        </label>
        <label class="flex items-center gap-2">
          <span class="{c.text} text-muted-foreground whitespace-nowrap">分段行数:</span>
          <Input type="number" bind:value={maxLines} class="h-9 w-24" min={50} max={5000} step={100} />
        </label>
      </div>
    </div>
  {:else}
    <div class="flex flex-wrap {c.gap} {c.text} mb-2">
      <label class="flex items-center gap-1"><Checkbox bind:checked={includeHidden} class="h-3 w-3" /><span>隐藏文件</span></label>
      <label class="flex items-center gap-1"><Checkbox bind:checked={dryRun} class="h-3 w-3" /><span>模拟执行</span></label>
      <label class="flex items-center gap-1"><Checkbox bind:checked={useCompact} class="h-3 w-3" /><span>紧凑格式</span></label>
    </div>
    <div class="flex {c.gap} {c.text}">
      <label class="flex items-center gap-1 flex-1 min-w-0">
        <span class="text-muted-foreground whitespace-nowrap">排除:</span>
        <Input bind:value={excludeExts} class="h-6 {c.text} flex-1 min-w-0" placeholder=".json,.txt" />
      </label>
      <label class="flex items-center gap-1">
        <span class="text-muted-foreground whitespace-nowrap">分段:</span>
        <Input type="number" bind:value={maxLines} class="h-6 {c.text} w-16" min={50} max={5000} step={100} />
      </label>
    </div>
  {/if}
{/snippet}

<!-- 文件树区块 -->
{#snippet treeBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if size === 'normal'}
    <div class="h-full flex flex-col overflow-hidden">
      <div class="flex items-center justify-between p-2 border-b bg-muted/30 shrink-0">
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
      <span class="{c.text} font-semibold flex items-center gap-1"><Folder class="w-3 h-3 text-yellow-500" />文件树</span>
      <div class="flex items-center gap-2 {c.textSm}">
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-yellow-500"></span>{stats.pending}</span>
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>{stats.ready}</span>
      </div>
    </div>
    <div class="{c.maxHeight} overflow-y-auto">
      {#if treeData.length > 0}
        <TreeView.Root class="text-xs">{#each treeData as node}{@render renderTreeNode(node)}{/each}</TreeView.Root>
      {:else}<div class="{c.text} text-muted-foreground text-center py-3">扫描后显示</div>{/if}
    </div>
  {/if}
{/snippet}

<!-- 日志区块 -->
{#snippet logBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if size === 'normal'}
    <div class="h-full flex flex-col">
      <div class="flex items-center justify-between mb-2 shrink-0">
        <span class="font-semibold text-sm">日志</span>
        <Button variant="ghost" size="icon" class="h-6 w-6" onclick={copyLogs}>
          {#if copied}<Check class="h-3 w-3 text-green-500" />{:else}<Copy class="h-3 w-3" />{/if}
        </Button>
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
      <span class="{c.text} font-semibold">日志</span>
      <Button variant="ghost" size="icon" class="h-5 w-5" onclick={copyLogs}>
        {#if copied}<Check class="{c.iconSm} text-green-500" />{:else}<Copy class={c.iconSm} />{/if}
      </Button>
    </div>
    <div class="bg-muted/30 {c.rounded} {c.paddingSm} font-mono {c.textSm} {c.maxHeightSm} overflow-y-auto {c.spaceSm}">
      {#each logs.slice(-4) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
    </div>
  {/if}
{/snippet}

<!-- 通用区块渲染器 -->
{#snippet renderBlockContent(blockId: string, size: SizeMode)}
  {#if blockId === 'path'}{@render pathBlock(size)}
  {:else if blockId === 'scan'}{@render scanBlock(size)}
  {:else if blockId === 'operation'}{@render operationBlock(size)}
  {:else if blockId === 'stats'}{@render statsBlock(size)}
  {:else if blockId === 'importExport'}{@render importExportBlock(size)}
  {:else if blockId === 'options'}{@render optionsBlock(size)}
  {:else if blockId === 'tree'}{@render treeBlock(size)}
  {:else if blockId === 'log'}{@render logBlock(size)}
  {/if}
{/snippet}


<!-- ========== 主渲染 ========== -->
<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 400px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={200} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={id} 
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
        nodeId={id}
        nodeType="trename"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={TRENAME_DEFAULT_GRID_LAYOUT}
      >
        {#snippet renderBlock(blockId: string, size: SizeMode)}
          {@render renderBlockContent(blockId, size)}
        {/snippet}
      </NodeLayoutRenderer>
    {/snippet}
  </NodeWrapper>

  {#if !isFullscreenRender}
    <Handle type="source" position={Position.Right} class="bg-primary!" />
  {/if}
</div>
