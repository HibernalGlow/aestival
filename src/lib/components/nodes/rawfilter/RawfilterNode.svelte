<script lang="ts">
  /**
   * RawfilterNode - 文件过滤节点组件
   * 使用 NodeLayoutRenderer 统一布局，支持节点模式和全屏模式
   * 
   * 使用 Container Query 自动响应尺寸
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';

  import { InteractiveHover } from '$lib/components/ui/interactive-hover';
  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { RAWFILTER_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, FolderOpen, Clipboard, Search,
    CircleCheck, Copy, Check, FileSearch, Trash2, Link, FileText
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: { path?: string; name_only_mode?: boolean; create_shortcuts?: boolean; trash_only?: boolean };
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
      label?: string;
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'scanning' | 'completed' | 'error';

  interface FilterResult { totalScanned: number; filtered: number; moved: number; shortcuts: number; }
  interface RawfilterState { phase: Phase; progress: number; progressText: string; filterResult: FilterResult | null; nameOnlyMode: boolean; createShortcuts: boolean; trashOnly: boolean; path: string; }

  // 使用 $derived 确保响应式
  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<RawfilterState>(nodeId));
  const configPath = $derived(data?.config?.path ?? '');
  const configNameOnlyMode = $derived(data?.config?.name_only_mode ?? false);
  const configCreateShortcuts = $derived(data?.config?.create_shortcuts ?? false);
  const configTrashOnly = $derived(data?.config?.trash_only ?? false);
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  let path = $state('');
  let nameOnlyMode = $state(false);
  let createShortcuts = $state(false);
  let trashOnly = $state(false);
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let hasInputConnection = $state(false);
  let copied = $state(false);
  let progress = $state(0);
  let progressText = $state('');
  let filterResult = $state<FilterResult | null>(null);

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
      filterResult = savedState.filterResult ?? null;
      nameOnlyMode = savedState.nameOnlyMode ?? configNameOnlyMode;
      createShortcuts = savedState.createShortcuts ?? configCreateShortcuts;
      trashOnly = savedState.trashOnly ?? configTrashOnly;
      path = savedState.path || configPath || '';
    } else {
      path = configPath || '';
      nameOnlyMode = configNameOnlyMode;
      createShortcuts = configCreateShortcuts;
      trashOnly = configTrashOnly;
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
    setNodeState<RawfilterState>(nodeId, { phase, progress, progressText, filterResult, nameOnlyMode, createShortcuts, trashOnly, path }); 
  }

  let canExecute = $derived(phase === 'idle' && (path.trim() !== '' || hasInputConnection));
  let isRunning = $derived(phase === 'scanning');
  let borderClass = $derived({ idle: 'border-border', scanning: 'border-primary shadow-sm', completed: 'border-primary/50', error: 'border-destructive/50' }[phase]);

  $effect(() => { if (phase || filterResult) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  async function selectFolder() { try { const { platform } = await import('$lib/api/platform'); const selected = await platform.openFolderDialog('选择文件夹'); if (selected) path = selected; } catch (e) { log(`选择文件夹失败: ${e}`); } }
  async function pasteFromClipboard() { try { const { platform } = await import('$lib/api/platform'); const text = await platform.readClipboard(); if (text) path = text.trim(); } catch (e) { log(`读取剪贴板失败: ${e}`); } }

  async function handleExecute() {
    if (!canExecute) return;
    phase = 'scanning'; progress = 0; progressText = '正在扫描文件...';
    filterResult = null;
    log(`🔍 开始执行 rawfilter: ${path}`);
    if (nameOnlyMode) log(`📋 仅名称模式`);
    if (createShortcuts) log(`🔗 创建快捷方式`);
    if (trashOnly) log(`🗑️ 仅移动到 trash`);

    try {
      progress = 30; progressText = '正在分析文件...';
      const response = await api.executeNode('rawfilter', { path, name_only_mode: nameOnlyMode, create_shortcuts: createShortcuts, trash_only: trashOnly }) as any;
      if (response.success) {
        phase = 'completed'; progress = 100; progressText = '执行完成';
        filterResult = { totalScanned: response.data?.total_scanned ?? 0, filtered: response.data?.filtered ?? 0, moved: response.data?.moved ?? 0, shortcuts: response.data?.shortcuts ?? 0 };
        log(`✅ ${response.message}`);
        log(`📊 扫描: ${filterResult.totalScanned}, 过滤: ${filterResult.filtered}, 移动: ${filterResult.moved}`);
      } else { phase = 'error'; progress = 0; log(`❌ 执行失败: ${response.message}`); }
    } catch (error) { phase = 'error'; progress = 0; log(`❌ 执行失败: ${error}`); }
  }

  function handleReset() { phase = 'idle'; progress = 0; progressText = ''; filterResult = null; logs = []; }
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
    <label class="flex items-center cq-gap cursor-pointer">
      <Checkbox id="name-only-{id}" bind:checked={nameOnlyMode} disabled={isRunning} />
      <span class="cq-text flex items-center gap-1"><FileText class="cq-icon" />仅名称模式</span>
    </label>
    <label class="flex items-center cq-gap cursor-pointer">
      <Checkbox id="shortcuts-{id}" bind:checked={createShortcuts} disabled={isRunning} />
      <span class="cq-text flex items-center gap-1"><Link class="cq-icon" />创建快捷方式</span>
    </label>
    <label class="flex items-center cq-gap cursor-pointer">
      <Checkbox id="trash-only-{id}" bind:checked={trashOnly} disabled={isRunning} />
      <span class="cq-text flex items-center gap-1"><Trash2 class="cq-icon" />仅移动到 trash</span>
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
        <span class="cq-text-sm text-muted-foreground ml-auto">{filterResult?.moved ?? 0} 移动</span>
      {:else if phase === 'error'}
        <Search class="cq-icon text-red-500 shrink-0" />
        <span class="cq-text text-red-600 font-medium">失败</span>
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <div class="flex-1"><Progress value={progress} class="h-1.5" /></div>
        <span class="cq-text-sm text-muted-foreground">{progress}%</span>
      {:else}
        <FileSearch class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text text-muted-foreground">等待执行</span>
      {/if}
    </div>
    <!-- 主按钮 -->
    <Button class="w-full cq-button flex-1" onclick={handleExecute} disabled={!canExecute || isRunning}>
      {#if isRunning}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<Search class="cq-icon mr-1" />{/if}
      <span>过滤</span>
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
  {#if filterResult}
    <div class="grid grid-cols-3 cq-gap">
      <div class="cq-stat-card bg-blue-500/10">
        <div class="flex flex-col items-center">
          <span class="cq-stat-value text-blue-600 tabular-nums">{filterResult.totalScanned}</span>
          <span class="cq-stat-label text-muted-foreground">扫描</span>
        </div>
      </div>
      <div class="cq-stat-card bg-yellow-500/10">
        <div class="flex flex-col items-center">
          <span class="cq-stat-value text-yellow-600 tabular-nums">{filterResult.filtered}</span>
          <span class="cq-stat-label text-muted-foreground">过滤</span>
        </div>
      </div>
      <div class="cq-stat-card bg-green-500/10">
        <div class="flex flex-col items-center">
          <span class="cq-stat-value text-green-600 tabular-nums">{filterResult.moved}</span>
          <span class="cq-stat-label text-muted-foreground">移动</span>
        </div>
      </div>
    </div>
  {:else}
    <div class="cq-text text-muted-foreground text-center py-2">执行后显示统计</div>
  {/if}
{/snippet}

<!-- 进度/状态区块 -->
{#snippet progressBlock()}
  <div class="h-full flex items-center cq-gap">
    {#if filterResult}
      <CircleCheck class="cq-icon-lg text-green-500 shrink-0" />
      <div class="flex-1">
        <span class="font-semibold text-green-600 cq-text">执行完成</span>
        <div class="flex cq-gap cq-text-sm mt-1">
          <span class="text-blue-600">扫描: {filterResult.totalScanned}</span>
          <span class="text-green-600">移动: {filterResult.moved}</span>
        </div>
      </div>
    {:else if isRunning}
      <LoaderCircle class="cq-icon-lg text-primary animate-spin shrink-0" />
      <div class="flex-1">
        <div class="flex justify-between cq-text-sm mb-1"><span>{progressText}</span><span>{progress}%</span></div>
        <Progress value={progress} class="h-2" />
      </div>
    {:else}
      <FileSearch class="cq-icon-lg text-muted-foreground/50 shrink-0" />
      <div class="flex-1">
        <span class="text-muted-foreground cq-text">等待执行</span>
        <div class="cq-text-sm text-muted-foreground/70 mt-1">设置路径后开始过滤</div>
      </div>
    {/if}
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
        {#each logs.slice(-10) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
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
    title="rawfilter" 
    icon={Search} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="rawfilter" 
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
        nodeType="rawfilter"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={RAWFILTER_DEFAULT_GRID_LAYOUT}
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
