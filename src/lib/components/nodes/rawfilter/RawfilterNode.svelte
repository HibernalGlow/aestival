<script lang="ts">
  /**
   * RawfilterNode - 文件过滤节点组件
   * 使用 NodeLayoutRenderer 统一布局，支持节点模式和全屏模式
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';
  import { Badge } from '$lib/components/ui/badge';

  import { InteractiveHover } from '$lib/components/ui/interactive-hover';
  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { RAWFILTER_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { getSizeClasses, type SizeMode } from '$lib/utils/sizeUtils';
  import { 
    Play, LoaderCircle, FolderOpen, Clipboard, Search,
    CircleCheck, CircleX, Copy, Check, FileSearch, Trash2,
    Link, FileText
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: { 
        path?: string; 
        name_only_mode?: boolean;
        create_shortcuts?: boolean;
        trash_only?: boolean;
      };
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
      label?: string;
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'scanning' | 'completed' | 'error';

  interface FilterResult {
    totalScanned: number;
    filtered: number;
    moved: number;
    shortcuts: number;
  }

  interface RawfilterState {
    phase: Phase;
    progress: number;
    progressText: string;
    filterResult: FilterResult | null;
    nameOnlyMode: boolean;
    createShortcuts: boolean;
    trashOnly: boolean;
  }

  // 从 nodeStateStore 恢复状态
  const savedState = getNodeState<RawfilterState>(id);

  // 状态初始化
  let path = $state(data?.config?.path ?? '');
  let nameOnlyMode = $state(savedState?.nameOnlyMode ?? data?.config?.name_only_mode ?? false);
  let createShortcuts = $state(savedState?.createShortcuts ?? data?.config?.create_shortcuts ?? false);
  let trashOnly = $state(savedState?.trashOnly ?? data?.config?.trash_only ?? false);
  let phase = $state<Phase>(savedState?.phase ?? 'idle');
  let logs = $state<string[]>(data?.logs ? [...data.logs] : []);
  let hasInputConnection = $state(data?.hasInputConnection ?? false);
  let copied = $state(false);

  let progress = $state(savedState?.progress ?? 0);
  let progressText = $state(savedState?.progressText ?? '');
  let filterResult = $state<FilterResult | null>(savedState?.filterResult ?? null);

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
    setNodeState<RawfilterState>(id, {
      phase, progress, progressText, filterResult,
      nameOnlyMode, createShortcuts, trashOnly
    });
  }

  // 响应式派生值
  let canExecute = $derived(phase === 'idle' && (path.trim() !== '' || hasInputConnection));
  let isRunning = $derived(phase === 'scanning');
  let borderClass = $derived({
    idle: 'border-border', scanning: 'border-primary shadow-sm',
    completed: 'border-primary/50', error: 'border-destructive/50'
  }[phase]);

  // 状态变化时自动保存
  $effect(() => {
    if (phase || filterResult) saveState();
  });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  async function selectFolder() {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFolderDialog('选择文件夹');
      if (selected) path = selected;
    } catch (e) { log(`选择文件夹失败: ${e}`); }
  }

  async function pasteFromClipboard() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) path = text.trim();
    } catch (e) { log(`读取剪贴板失败: ${e}`); }
  }

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
      const response = await api.executeNode('rawfilter', {
        path, name_only_mode: nameOnlyMode, 
        create_shortcuts: createShortcuts, trash_only: trashOnly
      }) as any;

      if (response.success) {
        phase = 'completed'; progress = 100; progressText = '执行完成';
        filterResult = {
          totalScanned: response.data?.total_scanned ?? 0,
          filtered: response.data?.filtered ?? 0,
          moved: response.data?.moved ?? 0,
          shortcuts: response.data?.shortcuts ?? 0
        };
        log(`✅ ${response.message}`);
        log(`📊 扫描: ${filterResult.totalScanned}, 过滤: ${filterResult.filtered}, 移动: ${filterResult.moved}`);
      } else { phase = 'error'; progress = 0; log(`❌ 执行失败: ${response.message}`); }
    } catch (error) { phase = 'error'; progress = 0; log(`❌ 执行失败: ${error}`); }
  }

  function handleReset() {
    phase = 'idle'; progress = 0; progressText = '';
    filterResult = null; logs = [];
  }

  async function copyLogs() {
    try { await navigator.clipboard.writeText(logs.join('\n')); copied = true; setTimeout(() => { copied = false; }, 2000); }
    catch (e) { console.error('复制失败:', e); }
  }
</script>


<!-- ========== 区块内容 Snippets（参数化尺寸） ========== -->

<!-- 路径输入区块 -->
{#snippet pathBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if !hasInputConnection}
    <div class="flex {c.gap} {c.mb}">
      <Input bind:value={path} placeholder="输入或选择文件夹路径..." disabled={isRunning} class="flex-1 {c.input}" />
      <Button variant="outline" size="icon" class="{c.buttonIcon} shrink-0" onclick={selectFolder} disabled={isRunning}>
        <FolderOpen class={c.icon} />
      </Button>
      <Button variant="outline" size="icon" class="{c.buttonIcon} shrink-0" onclick={pasteFromClipboard} disabled={isRunning}>
        <Clipboard class={c.icon} />
      </Button>
    </div>
  {:else}
    <div class="text-muted-foreground {c.padding} bg-muted {c.rounded} flex items-center {c.gap} {c.mb} {c.text}">
      <span>←</span><span>输入来自上游节点</span>
    </div>
  {/if}
{/snippet}

<!-- 选项区块 -->
{#snippet optionsBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="{c.space}">
    <label class="flex items-center {c.gap} cursor-pointer">
      <Checkbox id="name-only-{id}" bind:checked={nameOnlyMode} disabled={isRunning} />
      <span class="{c.text} flex items-center gap-1"><FileText class={c.icon} />仅名称模式</span>
    </label>
    <label class="flex items-center {c.gap} cursor-pointer">
      <Checkbox id="shortcuts-{id}" bind:checked={createShortcuts} disabled={isRunning} />
      <span class="{c.text} flex items-center gap-1"><Link class={c.icon} />创建快捷方式</span>
    </label>
    <label class="flex items-center {c.gap} cursor-pointer">
      <Checkbox id="trash-only-{id}" bind:checked={trashOnly} disabled={isRunning} />
      <span class="{c.text} flex items-center gap-1"><Trash2 class={c.icon} />仅移动到 trash</span>
    </label>
  </div>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="flex flex-col {c.gap} {size === 'normal' ? 'flex-1 justify-center' : ''}">
    {#if size === 'normal'}
      {#if phase === 'idle' || phase === 'error'}
        <InteractiveHover text="开始过滤" class="w-full h-12 text-sm" onclick={handleExecute} disabled={!canExecute}>
          {#snippet icon()}<Search class="h-4 w-4" />{/snippet}
        </InteractiveHover>
      {:else if phase === 'scanning'}
        <InteractiveHover text="执行中" class="w-full h-12 text-sm" disabled>
          {#snippet icon()}<LoaderCircle class="h-4 w-4 animate-spin" />{/snippet}
        </InteractiveHover>
      {:else if phase === 'completed'}
        <InteractiveHover text="重新开始" class="w-full h-12 text-sm" onclick={handleReset}>
          {#snippet icon()}<Play class="h-4 w-4" />{/snippet}
        </InteractiveHover>
      {/if}
    {:else}
      {#if phase === 'idle' || phase === 'error'}
        <Button class="flex-1 {c.button}" onclick={handleExecute} disabled={!canExecute}>
          <Search class="{c.icon} mr-1" />过滤
        </Button>
      {:else if phase === 'scanning'}
        <Button class="flex-1 {c.button}" disabled>
          <LoaderCircle class="{c.icon} mr-1 animate-spin" />执行中
        </Button>
      {:else if phase === 'completed'}
        <Button class="flex-1 {c.button}" variant="outline" onclick={handleReset}>
          <Play class="{c.icon} mr-1" />重新开始
        </Button>
      {/if}
    {/if}
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlock(size: SizeMode)}
  {#if size === 'normal'}
    <div class="space-y-2 flex-1">
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-blue-500/15 to-blue-500/5 rounded-xl border border-blue-500/20">
        <span class="text-sm text-muted-foreground">扫描</span>
        <span class="text-2xl font-bold text-blue-600 tabular-nums">{filterResult?.totalScanned ?? '-'}</span>
      </div>
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-yellow-500/15 to-yellow-500/5 rounded-xl border border-yellow-500/20">
        <span class="text-sm text-muted-foreground">过滤</span>
        <span class="text-2xl font-bold text-yellow-600 tabular-nums">{filterResult?.filtered ?? '-'}</span>
      </div>
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-green-500/15 to-green-500/5 rounded-xl border border-green-500/20">
        <span class="text-sm text-muted-foreground">移动</span>
        <span class="text-2xl font-bold text-green-600 tabular-nums">{filterResult?.moved ?? '-'}</span>
      </div>
    </div>
  {:else}
    <div class="grid grid-cols-3 gap-1.5">
      <div class="text-center p-1.5 bg-blue-500/10 rounded-lg">
        <div class="text-sm font-bold text-blue-600 tabular-nums">{filterResult?.totalScanned ?? '-'}</div>
        <div class="text-[10px] text-muted-foreground">扫描</div>
      </div>
      <div class="text-center p-1.5 bg-yellow-500/10 rounded-lg">
        <div class="text-sm font-bold text-yellow-600 tabular-nums">{filterResult?.filtered ?? '-'}</div>
        <div class="text-[10px] text-muted-foreground">过滤</div>
      </div>
      <div class="text-center p-1.5 bg-green-500/10 rounded-lg">
        <div class="text-sm font-bold text-green-600 tabular-nums">{filterResult?.moved ?? '-'}</div>
        <div class="text-[10px] text-muted-foreground">移动</div>
      </div>
    </div>
  {/if}
{/snippet}

<!-- 进度/状态区块 -->
{#snippet progressBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if size === 'normal'}
    <div class="h-full flex items-center gap-3">
      {#if filterResult}
        <CircleCheck class="w-8 h-8 text-green-500 shrink-0" />
        <div class="flex-1">
          <span class="font-semibold text-green-600">执行完成</span>
          <div class="flex gap-4 text-sm mt-1">
            <span class="text-blue-600">扫描: {filterResult.totalScanned}</span>
            <span class="text-green-600">移动: {filterResult.moved}</span>
          </div>
        </div>
      {:else if isRunning}
        <LoaderCircle class="w-8 h-8 text-primary animate-spin shrink-0" />
        <div class="flex-1">
          <div class="flex justify-between text-sm mb-1"><span>{progressText}</span><span>{progress}%</span></div>
          <Progress value={progress} class="h-2" />
        </div>
      {:else}
        <FileSearch class="w-8 h-8 text-muted-foreground/50 shrink-0" />
        <div class="flex-1">
          <span class="text-muted-foreground">等待执行</span>
          <div class="text-xs text-muted-foreground/70 mt-1">设置路径后开始过滤</div>
        </div>
      {/if}
    </div>
  {:else}
    {#if filterResult}
      <div class="flex items-center gap-2 {c.text}">
        <CircleCheck class="{c.icon} text-green-500" />
        <span class="text-green-600">完成 {filterResult.moved}</span>
      </div>
    {:else if isRunning}
      <div class={c.spaceSm}>
        <Progress value={progress} class="h-1.5" />
        <div class="{c.text} text-muted-foreground">{progress}%</div>
      </div>
    {:else}
      <div class="flex items-center gap-2 {c.text} text-muted-foreground">
        <FileSearch class={c.icon} />
        <span>等待执行</span>
      </div>
    {/if}
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
      <div class="flex-1 overflow-y-auto bg-muted/30 rounded-xl p-2 font-mono text-xs space-y-1">
        {#if logs.length > 0}{#each logs.slice(-15) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}{:else}<div class="text-muted-foreground text-center py-4">暂无日志</div>{/if}
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
  {:else if blockId === 'options'}{@render optionsBlock(size)}
  {:else if blockId === 'operation'}{@render operationBlock(size)}
  {:else if blockId === 'stats'}{@render statsBlock(size)}
  {:else if blockId === 'progress'}{@render progressBlock(size)}
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
        nodeId={id}
        nodeType="rawfilter"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={RAWFILTER_DEFAULT_GRID_LAYOUT}
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
