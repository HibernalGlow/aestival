<script lang="ts">
  /**
   * CrashuNode - 重复文件检测节点组件
   * 使用 NodeLayoutRenderer 统一布局，支持节点模式和全屏模式
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';
  import { Badge } from '$lib/components/ui/badge';
  import { Slider } from '$lib/components/ui/slider';

  import { InteractiveHover } from '$lib/components/ui/interactive-hover';
  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { CRASHU_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { getSizeClasses, type SizeMode } from '$lib/utils/sizeUtils';
  import { 
    Play, LoaderCircle, FolderOpen, Clipboard, Zap,
    CircleCheck, Copy, Check, Trash2, Image, ChevronRight, ChevronDown
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: { path?: string; similarity_threshold?: number; auto_move?: boolean };
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
      label?: string;
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'scanning' | 'completed' | 'error';

  interface DuplicateGroup { hash: string; files: string[]; size: number; }
  interface CrashuResult { totalScanned: number; duplicateGroups: number; duplicateFiles: number; savedSpace: number; groups: DuplicateGroup[]; }
  interface CrashuState { phase: Phase; progress: number; progressText: string; crashuResult: CrashuResult | null; similarityThreshold: number; autoMove: boolean; expandedGroups: string[]; }

  const savedState = getNodeState<CrashuState>(id);

  let path = $state(data?.config?.path ?? '');
  let similarityThreshold = $state(savedState?.similarityThreshold ?? data?.config?.similarity_threshold ?? 0.8);
  let autoMove = $state(savedState?.autoMove ?? data?.config?.auto_move ?? false);
  let phase = $state<Phase>(savedState?.phase ?? 'idle');
  let logs = $state<string[]>(data?.logs ? [...data.logs] : []);
  let hasInputConnection = $state(data?.hasInputConnection ?? false);
  let copied = $state(false);
  let progress = $state(savedState?.progress ?? 0);
  let progressText = $state(savedState?.progressText ?? '');
  let crashuResult = $state<CrashuResult | null>(savedState?.crashuResult ?? null);
  let expandedGroups = $state<Set<string>>(new Set(savedState?.expandedGroups ?? []));

  let layoutRenderer = $state<{ createTab: (blockIds: string[]) => void; getUsedBlockIdsForTab: () => string[]; compact: () => void; resetLayout: () => void; applyLayout: (layout: any[]) => void; getCurrentLayout: () => any[]; getCurrentTabGroups: () => any[]; } | undefined>(undefined);

  function saveState() { setNodeState<CrashuState>(id, { phase, progress, progressText, crashuResult, similarityThreshold, autoMove, expandedGroups: Array.from(expandedGroups) }); }

  let canExecute = $derived(phase === 'idle' && (path.trim() !== '' || hasInputConnection));
  let isRunning = $derived(phase === 'scanning');
  let borderClass = $derived({ idle: 'border-border', scanning: 'border-primary shadow-sm', completed: 'border-primary/50', error: 'border-destructive/50' }[phase]);

  $effect(() => { if (phase || crashuResult) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }
  function toggleGroup(hash: string) { if (expandedGroups.has(hash)) expandedGroups.delete(hash); else expandedGroups.add(hash); expandedGroups = new Set(expandedGroups); }

  async function selectFolder() { try { const { platform } = await import('$lib/api/platform'); const selected = await platform.openFolderDialog('选择文件夹'); if (selected) path = selected; } catch (e) { log(`选择文件夹失败: ${e}`); } }
  async function pasteFromClipboard() { try { const { platform } = await import('$lib/api/platform'); const text = await platform.readClipboard(); if (text) path = text.trim(); } catch (e) { log(`读取剪贴板失败: ${e}`); } }

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
  }

  async function handleExecute() {
    if (!canExecute) return;
    phase = 'scanning'; progress = 0; progressText = '正在扫描文件...';
    crashuResult = null; expandedGroups.clear();
    log(`💥 开始执行 crashu: ${path}`);
    log(`📋 相似度阈值: ${similarityThreshold}`);
    if (autoMove) log(`🗑️ 自动移动重复文件`);
    try {
      progress = 30; progressText = '正在计算文件哈希...';
      const response = await api.executeNode('crashu', { path, similarity_threshold: similarityThreshold, auto_move: autoMove }) as any;
      if (response.success) {
        phase = 'completed'; progress = 100; progressText = '检测完成';
        crashuResult = { totalScanned: response.data?.total_scanned ?? 0, duplicateGroups: response.data?.duplicate_groups ?? 0, duplicateFiles: response.data?.duplicate_files ?? 0, savedSpace: response.data?.saved_space ?? 0, groups: response.data?.groups ?? [] };
        log(`✅ ${response.message}`);
        log(`📊 扫描: ${crashuResult.totalScanned}, 重复组: ${crashuResult.duplicateGroups}, 重复文件: ${crashuResult.duplicateFiles}`);
      } else { phase = 'error'; progress = 0; log(`❌ 执行失败: ${response.message}`); }
    } catch (error) { phase = 'error'; progress = 0; log(`❌ 执行失败: ${error}`); }
  }

  function handleReset() { phase = 'idle'; progress = 0; progressText = ''; crashuResult = null; logs = []; expandedGroups.clear(); }
  async function copyLogs() { try { await navigator.clipboard.writeText(logs.join('\n')); copied = true; setTimeout(() => { copied = false; }, 2000); } catch (e) { console.error('复制失败:', e); } }
</script>

{#snippet pathBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if !hasInputConnection}
    <div class="flex {c.gap} {c.mb}">
      <Input bind:value={path} placeholder="输入或选择文件夹路径..." disabled={isRunning} class="flex-1 {c.input}" />
      <Button variant="outline" size="icon" class="{c.buttonIcon} shrink-0" onclick={selectFolder} disabled={isRunning}><FolderOpen class={c.icon} /></Button>
      <Button variant="outline" size="icon" class="{c.buttonIcon} shrink-0" onclick={pasteFromClipboard} disabled={isRunning}><Clipboard class={c.icon} /></Button>
    </div>
  {:else}
    <div class="text-muted-foreground {c.padding} bg-muted {c.rounded} flex items-center {c.gap} {c.mb} {c.text}"><span>←</span><span>输入来自上游节点</span></div>
  {/if}
{/snippet}

{#snippet optionsBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="{c.space}">
    <div class="{c.spaceSm}">
      <div class="flex items-center justify-between {c.text}"><span>相似度阈值</span><span class="font-mono">{(similarityThreshold * 100).toFixed(0)}%</span></div>
      <Slider value={[similarityThreshold]} onValueChange={(v) => similarityThreshold = v[0]} min={0.5} max={1} step={0.05} disabled={isRunning} class="w-full" />
    </div>
    <label class="flex items-center {c.gap} cursor-pointer">
      <Checkbox id="auto-move-{id}" bind:checked={autoMove} disabled={isRunning} />
      <span class="{c.text} flex items-center gap-1"><Trash2 class={c.icon} />自动移动重复文件</span>
    </label>
  </div>
{/snippet}

{#snippet operationBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="flex flex-col {c.gap} {size === 'normal' ? 'flex-1 justify-center' : ''}">
    {#if size === 'normal'}
      {#if phase === 'idle' || phase === 'error'}
        <InteractiveHover text="开始检测" class="w-full h-12 text-sm" onclick={handleExecute} disabled={!canExecute}>{#snippet icon()}<Zap class="h-4 w-4" />{/snippet}</InteractiveHover>
      {:else if phase === 'scanning'}
        <InteractiveHover text="检测中" class="w-full h-12 text-sm" disabled>{#snippet icon()}<LoaderCircle class="h-4 w-4 animate-spin" />{/snippet}</InteractiveHover>
      {:else if phase === 'completed'}
        <InteractiveHover text="重新开始" class="w-full h-12 text-sm" onclick={handleReset}>{#snippet icon()}<Play class="h-4 w-4" />{/snippet}</InteractiveHover>
      {/if}
    {:else}
      {#if phase === 'idle' || phase === 'error'}
        <Button class="flex-1 {c.button}" onclick={handleExecute} disabled={!canExecute}><Zap class="{c.icon} mr-1" />检测</Button>
      {:else if phase === 'scanning'}
        <Button class="flex-1 {c.button}" disabled><LoaderCircle class="{c.icon} mr-1 animate-spin" />检测中</Button>
      {:else if phase === 'completed'}
        <Button class="flex-1 {c.button}" variant="outline" onclick={handleReset}><Play class="{c.icon} mr-1" />重新开始</Button>
      {/if}
    {/if}
  </div>
{/snippet}

{#snippet statsBlock(size: SizeMode)}
  {#if size === 'normal'}
    <div class="space-y-2 flex-1">
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-blue-500/15 to-blue-500/5 rounded-xl border border-blue-500/20"><span class="text-sm text-muted-foreground">扫描</span><span class="text-2xl font-bold text-blue-600 tabular-nums">{crashuResult?.totalScanned ?? '-'}</span></div>
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-orange-500/15 to-orange-500/5 rounded-xl border border-orange-500/20"><span class="text-sm text-muted-foreground">重复组</span><span class="text-2xl font-bold text-orange-600 tabular-nums">{crashuResult?.duplicateGroups ?? '-'}</span></div>
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-red-500/15 to-red-500/5 rounded-xl border border-red-500/20"><span class="text-sm text-muted-foreground">重复文件</span><span class="text-2xl font-bold text-red-600 tabular-nums">{crashuResult?.duplicateFiles ?? '-'}</span></div>
    </div>
  {:else}
    <div class="grid grid-cols-3 gap-1.5">
      <div class="text-center p-1.5 bg-blue-500/10 rounded-lg"><div class="text-sm font-bold text-blue-600 tabular-nums">{crashuResult?.totalScanned ?? '-'}</div><div class="text-[10px] text-muted-foreground">扫描</div></div>
      <div class="text-center p-1.5 bg-orange-500/10 rounded-lg"><div class="text-sm font-bold text-orange-600 tabular-nums">{crashuResult?.duplicateGroups ?? '-'}</div><div class="text-[10px] text-muted-foreground">重复组</div></div>
      <div class="text-center p-1.5 bg-red-500/10 rounded-lg"><div class="text-sm font-bold text-red-600 tabular-nums">{crashuResult?.duplicateFiles ?? '-'}</div><div class="text-[10px] text-muted-foreground">重复</div></div>
    </div>
  {/if}
{/snippet}

{#snippet progressBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if size === 'normal'}
    <div class="h-full flex items-center gap-3">
      {#if crashuResult}
        <CircleCheck class="w-8 h-8 text-green-500 shrink-0" />
        <div class="flex-1"><span class="font-semibold text-green-600">检测完成</span><div class="flex gap-4 text-sm mt-1"><span class="text-orange-600">重复组: {crashuResult.duplicateGroups}</span><span class="text-muted-foreground">可节省: {formatSize(crashuResult.savedSpace)}</span></div></div>
      {:else if isRunning}
        <LoaderCircle class="w-8 h-8 text-primary animate-spin shrink-0" />
        <div class="flex-1"><div class="flex justify-between text-sm mb-1"><span>{progressText}</span><span>{progress}%</span></div><Progress value={progress} class="h-2" /></div>
      {:else}
        <Zap class="w-8 h-8 text-muted-foreground/50 shrink-0" />
        <div class="flex-1"><span class="text-muted-foreground">等待执行</span><div class="text-xs text-muted-foreground/70 mt-1">设置路径后开始检测</div></div>
      {/if}
    </div>
  {:else}
    {#if crashuResult}
      <div class="flex items-center gap-2 {c.text}"><CircleCheck class="{c.icon} text-green-500" /><span class="text-green-600">完成 {crashuResult.duplicateGroups}组</span></div>
    {:else if isRunning}
      <div class={c.spaceSm}><Progress value={progress} class="h-1.5" /><div class="{c.text} text-muted-foreground">{progress}%</div></div>
    {:else}
      <div class="flex items-center gap-2 {c.text} text-muted-foreground"><Zap class={c.icon} /><span>等待执行</span></div>
    {/if}
  {/if}
{/snippet}

{#snippet duplicatesBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if size === 'normal'}
    <div class="h-full flex flex-col overflow-hidden">
      <div class="flex items-center justify-between p-2 border-b bg-muted/30 shrink-0">
        <div class="flex items-center gap-2"><Copy class="w-5 h-5 text-orange-500" /><span class="font-semibold">重复文件</span>{#if crashuResult}<Badge variant="secondary">{crashuResult.duplicateGroups} 组</Badge>{/if}</div>
        {#if crashuResult}<span class="text-xs text-muted-foreground">可节省 {formatSize(crashuResult.savedSpace)}</span>{/if}
      </div>
      <div class="flex-1 overflow-y-auto p-2">
        {#if crashuResult && crashuResult.groups.length > 0}
          {#each crashuResult.groups as group}
            {@const isExpanded = expandedGroups.has(group.hash)}
            <div class="mb-2">
              <button class="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-muted/50 text-left" onclick={() => toggleGroup(group.hash)}>
                {#if isExpanded}<ChevronDown class="w-4 h-4 text-muted-foreground" />{:else}<ChevronRight class="w-4 h-4 text-muted-foreground" />{/if}
                <Image class="w-4 h-4 text-orange-500" /><span class="flex-1 text-sm truncate">{group.files.length} 个文件</span><span class="text-xs text-muted-foreground">{formatSize(group.size)}</span>
              </button>
              {#if isExpanded}<div class="ml-6 mt-1 space-y-1">{#each group.files as file}<div class="text-xs text-muted-foreground truncate p-1 bg-muted/30 rounded">{file}</div>{/each}</div>{/if}
            </div>
          {/each}
        {:else}<div class="text-center text-muted-foreground py-8">检测后显示重复文件</div>{/if}
      </div>
    </div>
  {:else}
    <div class="flex items-center justify-between mb-2"><span class="{c.text} font-semibold flex items-center gap-1"><Copy class="w-3 h-3 text-orange-500" />重复文件</span>{#if crashuResult}<Badge variant="secondary" class="text-[10px]">{crashuResult.duplicateGroups}</Badge>{/if}</div>
    <div class="{c.maxHeight} overflow-y-auto">
      {#if crashuResult && crashuResult.groups.length > 0}
        {#each crashuResult.groups.slice(0, 3) as group}<div class="text-xs text-muted-foreground p-1 bg-muted/30 rounded mb-1 truncate">{group.files.length} 文件 · {formatSize(group.size)}</div>{/each}
        {#if crashuResult.groups.length > 3}<div class="text-xs text-muted-foreground text-center">+{crashuResult.groups.length - 3} 更多</div>{/if}
      {:else}<div class="{c.text} text-muted-foreground text-center py-3">检测后显示</div>{/if}
    </div>
  {/if}
{/snippet}

{#snippet logBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if size === 'normal'}
    <div class="h-full flex flex-col">
      <div class="flex items-center justify-between mb-2 shrink-0"><span class="font-semibold text-sm">日志</span><Button variant="ghost" size="icon" class="h-6 w-6" onclick={copyLogs}>{#if copied}<Check class="h-3 w-3 text-green-500" />{:else}<Copy class="h-3 w-3" />{/if}</Button></div>
      <div class="flex-1 overflow-y-auto bg-muted/30 rounded-xl p-2 font-mono text-xs space-y-1">{#if logs.length > 0}{#each logs.slice(-15) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}{:else}<div class="text-muted-foreground text-center py-4">暂无日志</div>{/if}</div>
    </div>
  {:else}
    <div class="flex items-center justify-between mb-1"><span class="{c.text} font-semibold">日志</span><Button variant="ghost" size="icon" class="h-5 w-5" onclick={copyLogs}>{#if copied}<Check class="{c.iconSm} text-green-500" />{:else}<Copy class={c.iconSm} />{/if}</Button></div>
    <div class="bg-muted/30 {c.rounded} {c.paddingSm} font-mono {c.textSm} {c.maxHeightSm} overflow-y-auto {c.spaceSm}">{#each logs.slice(-4) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}</div>
  {/if}
{/snippet}

{#snippet renderBlockContent(blockId: string, size: SizeMode)}
  {#if blockId === 'path'}{@render pathBlock(size)}
  {:else if blockId === 'options'}{@render optionsBlock(size)}
  {:else if blockId === 'operation'}{@render operationBlock(size)}
  {:else if blockId === 'stats'}{@render statsBlock(size)}
  {:else if blockId === 'progress'}{@render progressBlock(size)}
  {:else if blockId === 'duplicates'}{@render duplicatesBlock(size)}
  {:else if blockId === 'log'}{@render logBlock(size)}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 400px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={200} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={id} 
    title="crashu" 
    icon={Zap} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="crashu" 
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
        nodeType="crashu"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={CRASHU_DEFAULT_GRID_LAYOUT}
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
