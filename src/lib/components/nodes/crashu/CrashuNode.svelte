<script lang="ts">
  /**
   * CrashuNode - 重复文件检测节点组件
   * 使用 NodeLayoutRenderer 统一布局，支持节点模式和全屏模式
   * 
   * 使用 Container Query 自动响应尺寸
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
  interface CrashuState { phase: Phase; progress: number; progressText: string; crashuResult: CrashuResult | null; similarityThreshold: number; autoMove: boolean; expandedGroups: string[]; path: string; }

  // 使用 $derived 确保响应式
  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<CrashuState>(nodeId));
  const configPath = $derived(data?.config?.path ?? '');
  const configSimilarityThreshold = $derived(data?.config?.similarity_threshold ?? 0.8);
  const configAutoMove = $derived(data?.config?.auto_move ?? false);
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  let path = $state('');
  let similarityThreshold = $state(0.8);
  let autoMove = $state(false);
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let hasInputConnection = $state(false);
  let copied = $state(false);
  let progress = $state(0);
  let progressText = $state('');
  let crashuResult = $state<CrashuResult | null>(null);
  let expandedGroups = $state<Set<string>>(new Set());

  let layoutRenderer = $state<any>(undefined);

  // 初始化标记
  let initialized = $state(false);
  
  // 初始化 effect - 只执行一次
  $effect(() => {
    if (initialized) return;
    
    if (savedState) {
      phase = savedState.phase ?? 'idle';
      progress = savedState.progress ?? 0;
      progressText = savedState.progressText ?? '';
      crashuResult = savedState.crashuResult ?? null;
      expandedGroups = new Set(savedState.expandedGroups ?? []);
      similarityThreshold = savedState.similarityThreshold ?? configSimilarityThreshold;
      autoMove = savedState.autoMove ?? configAutoMove;
      path = savedState.path || configPath || '';
    } else {
      path = configPath || '';
      similarityThreshold = configSimilarityThreshold;
      autoMove = configAutoMove;
    }
    
    initialized = true;
  });
  
  // 持续同步外部数据
  $effect(() => {
    logs = [...dataLogs];
    hasInputConnection = dataHasInputConnection;
  });

  function saveState() { 
    if (!initialized) return;
    setNodeState<CrashuState>(nodeId, { phase, progress, progressText, crashuResult, similarityThreshold, autoMove, expandedGroups: Array.from(expandedGroups), path }); 
  }

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

<!-- 路径输入区块 -->
{#snippet pathBlock()}
  {#if !hasInputConnection}
    <div class="flex cq-gap cq-mb">
      <Input bind:value={path} placeholder="输入或选择文件夹路径..." disabled={isRunning} class="flex-1 cq-input" />
      <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={selectFolder} disabled={isRunning}><FolderOpen class="cq-icon" /></Button>
      <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={pasteFromClipboard} disabled={isRunning}><Clipboard class="cq-icon" /></Button>
    </div>
  {:else}
    <div class="text-muted-foreground cq-padding bg-muted cq-rounded flex items-center cq-gap cq-mb cq-text"><span>←</span><span>输入来自上游节点</span></div>
  {/if}
{/snippet}

<!-- 选项区块 -->
{#snippet optionsBlock()}
  <div class="cq-space">
    <div class="cq-space-sm">
      <div class="flex items-center justify-between cq-text"><span>相似度阈值</span><span class="font-mono">{(similarityThreshold * 100).toFixed(0)}%</span></div>
      <Slider type="single" value={similarityThreshold} onValueChange={(v: number) => similarityThreshold = v} min={0.5} max={1} step={0.05} disabled={isRunning} class="w-full" />
    </div>
    <label class="flex items-center cq-gap cursor-pointer">
      <Checkbox id="auto-move-{nodeId}" bind:checked={autoMove} disabled={isRunning} />
      <span class="cq-text flex items-center gap-1"><Trash2 class="cq-icon" />自动移动重复文件</span>
    </label>
  </div>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <!-- 状态指示 -->
    <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded">
      {#if phase === 'completed'}
        <CircleCheck class="cq-icon text-green-500 shrink-0" />
        <span class="cq-text text-green-600 font-medium">完成</span>
        <span class="cq-text-sm text-muted-foreground ml-auto">{crashuResult?.duplicateGroups ?? 0} 组</span>
      {:else if phase === 'error'}
        <Zap class="cq-icon text-red-500 shrink-0" />
        <span class="cq-text text-red-600 font-medium">失败</span>
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <div class="flex-1">
          <Progress value={progress} class="h-1.5" />
        </div>
        <span class="cq-text-sm text-muted-foreground">{progress}%</span>
      {:else}
        <Zap class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text text-muted-foreground">等待执行</span>
      {/if}
    </div>
    <!-- 主按钮 -->
    <Button class="w-full cq-button flex-1" onclick={handleExecute} disabled={!canExecute || isRunning}>
      {#if isRunning}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<Zap class="cq-icon mr-1" />{/if}
      <span>检测</span>
    </Button>
    <!-- 重置按钮 -->
    {#if phase === 'completed' || phase === 'error'}
      <Button variant="outline" class="w-full cq-button-sm" onclick={handleReset}>
        <Play class="cq-icon mr-1" />重新开始
      </Button>
    {/if}
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlock()}
  {#if crashuResult}
    <div class="grid grid-cols-3 cq-gap">
      <div class="cq-stat-card bg-blue-500/10">
        <div class="flex flex-col items-center">
          <span class="cq-stat-value text-blue-600 tabular-nums">{crashuResult.totalScanned}</span>
          <span class="cq-stat-label text-muted-foreground">扫描</span>
        </div>
      </div>
      <div class="cq-stat-card bg-orange-500/10">
        <div class="flex flex-col items-center">
          <span class="cq-stat-value text-orange-600 tabular-nums">{crashuResult.duplicateGroups}</span>
          <span class="cq-stat-label text-muted-foreground">重复组</span>
        </div>
      </div>
      <div class="cq-stat-card bg-red-500/10">
        <div class="flex flex-col items-center">
          <span class="cq-stat-value text-red-600 tabular-nums">{crashuResult.duplicateFiles}</span>
          <span class="cq-stat-label text-muted-foreground">重复</span>
        </div>
      </div>
    </div>
  {:else}
    <div class="cq-text text-muted-foreground text-center py-2">检测后显示统计</div>
  {/if}
{/snippet}

<!-- 进度/状态区块 -->
{#snippet progressBlock()}
  <div class="h-full flex items-center cq-gap">
    {#if crashuResult}
      <CircleCheck class="cq-icon-lg text-green-500 shrink-0" />
      <div class="flex-1">
        <span class="font-semibold text-green-600 cq-text">检测完成</span>
        <div class="flex cq-gap cq-text-sm mt-1">
          <span class="text-orange-600">重复组: {crashuResult.duplicateGroups}</span>
          <span class="text-muted-foreground">可节省: {formatSize(crashuResult.savedSpace)}</span>
        </div>
      </div>
    {:else if isRunning}
      <LoaderCircle class="cq-icon-lg text-primary animate-spin shrink-0" />
      <div class="flex-1">
        <div class="flex justify-between cq-text-sm mb-1"><span>{progressText}</span><span>{progress}%</span></div>
        <Progress value={progress} class="h-2" />
      </div>
    {:else}
      <Zap class="cq-icon-lg text-muted-foreground/50 shrink-0" />
      <div class="flex-1">
        <span class="text-muted-foreground cq-text">等待执行</span>
        <div class="cq-text-sm text-muted-foreground/70 mt-1">设置路径后开始检测</div>
      </div>
    {/if}
  </div>
{/snippet}

<!-- 重复文件区块 -->
{#snippet duplicatesBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between cq-padding border-b bg-muted/30 shrink-0">
      <div class="flex items-center cq-gap">
        <Copy class="cq-icon text-orange-500" />
        <span class="font-semibold cq-text">重复文件</span>
        {#if crashuResult}<Badge variant="secondary" class="cq-text-sm">{crashuResult.duplicateGroups} 组</Badge>{/if}
      </div>
      {#if crashuResult}<span class="cq-text-sm text-muted-foreground">可节省 {formatSize(crashuResult.savedSpace)}</span>{/if}
    </div>
    <div class="flex-1 overflow-y-auto cq-padding">
      {#if crashuResult && crashuResult.groups.length > 0}
        {#each crashuResult.groups as group}
          {@const isExpanded = expandedGroups.has(group.hash)}
          <div class="mb-2">
            <button class="w-full flex items-center cq-gap cq-padding cq-rounded hover:bg-muted/50 text-left" onclick={() => toggleGroup(group.hash)}>
              {#if isExpanded}<ChevronDown class="cq-icon text-muted-foreground" />{:else}<ChevronRight class="cq-icon text-muted-foreground" />{/if}
              <Image class="cq-icon text-orange-500" />
              <span class="flex-1 cq-text truncate">{group.files.length} 个文件</span>
              <span class="cq-text-sm text-muted-foreground">{formatSize(group.size)}</span>
            </button>
            {#if isExpanded}
              <div class="ml-6 mt-1 cq-space-sm">
                {#each group.files as file}
                  <div class="cq-text-sm text-muted-foreground truncate cq-padding bg-muted/30 cq-rounded">{file}</div>
                {/each}
              </div>
            {/if}
          </div>
        {/each}
      {:else}
        <div class="text-center text-muted-foreground py-8 cq-text">检测后显示重复文件</div>
      {/if}
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
    <div class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding font-mono cq-text-sm space-y-0.5">
      {#if logs.length > 0}
        {#each logs.slice(-10) as logItem}
          <div class="text-muted-foreground break-all">{logItem}</div>
        {/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 区块渲染器 -->
{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'path'}{@render pathBlock()}
  {:else if blockId === 'options'}{@render optionsBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'stats'}{@render statsBlock()}
  {:else if blockId === 'progress'}{@render progressBlock()}
  {:else if blockId === 'duplicates'}{@render duplicatesBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<!-- 主渲染 -->
<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 400px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={200} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
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
        nodeId={nodeId}
        nodeType="crashu"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={CRASHU_DEFAULT_GRID_LAYOUT}
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
