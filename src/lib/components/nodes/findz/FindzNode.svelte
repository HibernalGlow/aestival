<script lang="ts">
  /**
   * FindzNode - 文件搜索节点组件
   * 
   * 使用 Container Query 自动响应尺寸
   * - 一套 HTML 结构，CSS 控制尺寸变化
   * - 紧凑模式保留核心功能，详细操作在全屏
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import type { GridItem } from '$lib/components/ui/dashboard-grid';
  import type { NodeConfig, LayoutMode } from '$lib/stores/nodeLayoutStore';
  import { FINDZ_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import FilterBuilder from './FilterBuilder.svelte';
  import AnalysisPanel from './AnalysisPanel.svelte';
  import type { FileData, SearchResult, FindzNodeState } from './types';
  import { 
    Search, LoaderCircle, FolderOpen, Clipboard, CircleCheck, CircleX, 
    File, Folder, Archive, Copy, Check, RotateCcw, Package, Layers
  } from '@lucide/svelte';

  /** NodeLayoutRenderer 组件实例类型 */
  interface LayoutRendererInstance {
    compact: () => void;
    resetLayout: () => Promise<void>;
    getCurrentLayout: () => GridItem[];
    getCurrentTabGroups: () => { id: string; blockIds: string[]; activeIndex: number }[];
    applyLayout: (layout: GridItem[], tabGroups?: { id: string; blockIds: string[]; activeIndex: number }[] | null) => Promise<void>;
    createTab: (blockIds: string[]) => Promise<string | null>;
    getCurrentMode: () => LayoutMode;
    getConfig: () => NodeConfig;
  }

  interface Props {
    id: string;
    data?: {
      config?: { path?: string; where?: string };
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'searching' | 'completed' | 'error';
  type Action = 'search' | 'nested' | 'archives_only';

  // 使用 $derived 确保响应式
  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<FindzNodeState>(nodeId));
  const configPath = $derived(data?.config?.path ?? '.');
  const configWhere = $derived(data?.config?.where ?? '1');
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  // 状态
  let targetPath = $state('.');
  let whereClause = $state('1');
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let hasInputConnection = $state(false);
  let progress = $state(0);
  let searchResult = $state<SearchResult | null>(null);
  let files = $state<FileData[]>([]);
  let byExtension = $state<Record<string, number>>({});
  let layoutRenderer = $state<LayoutRendererInstance | undefined>(undefined);
  let advancedMode = $state(false);
  
  // 复制状态
  let copiedLogs = $state(false);
  let copiedPath = $state(false);

  // 初始化标记
  let initialized = $state(false);

  // 初始化 effect - 只执行一次
  $effect(() => {
    if (initialized) return;
    
    if (savedState) {
      phase = savedState.phase ?? 'idle';
      progress = savedState.progress ?? 0;
      searchResult = savedState.searchResult ?? null;
      files = savedState.files ?? [];
      byExtension = savedState.byExtension ?? {};
      targetPath = savedState.targetPath || configPath || '';
      whereClause = savedState.whereClause || configWhere || '';
    } else {
      targetPath = configPath || '';
      whereClause = configWhere || '';
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
    setNodeState<FindzNodeState>(nodeId, { phase, progress, searchResult, files, byExtension, targetPath, whereClause });
  }

  let canExecute = $derived(phase === 'idle' && (targetPath.trim() !== '' || hasInputConnection));
  let isRunning = $derived(phase === 'searching');
  let borderClass = $derived({
    idle: 'border-border',
    searching: 'border-blue-500 shadow-sm',
    completed: 'border-primary/50',
    error: 'border-destructive/50'
  }[phase]);

  $effect(() => { if (phase || searchResult || files) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  async function selectFolder() {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFolderDialog('选择搜索目录');
      if (selected) targetPath = selected;
    } catch (e) { log(`选择文件夹失败: ${e}`); }
  }

  async function pasteFromClipboard() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) targetPath = text.trim();
    } catch (e) { log(`读取剪贴板失败: ${e}`); }
  }

  async function executeAction(action: Action) {
    if (!canExecute) return;
    phase = 'searching'; progress = 0;
    log(`🔍 开始搜索: ${targetPath}`);

    try {
      progress = 10;
      const response = await api.executeNode('findz', {
        path: targetPath, where: whereClause, action, long_format: true, max_results: 1000
      }) as any;

      if (response.logs) for (const m of response.logs) log(m);

      if (response.success) {
        phase = 'completed'; progress = 100;
        searchResult = {
          total_count: response.data?.total_count ?? 0,
          file_count: response.data?.file_count ?? 0,
          dir_count: response.data?.dir_count ?? 0,
          archive_count: response.data?.archive_count ?? 0,
          nested_count: response.data?.nested_count ?? 0,
        };
        files = response.data?.files ?? [];
        byExtension = response.data?.by_extension ?? {};
        log(`✅ ${response.message}`);
      } else {
        phase = 'error'; progress = 0;
        log(`❌ 失败: ${response.message}`);
      }
    } catch (error) {
      phase = 'error'; progress = 0;
      log(`❌ 失败: ${error}`);
    }
  }

  function handleReset() {
    phase = 'idle'; progress = 0;
    searchResult = null; files = []; byExtension = {}; logs = [];
  }

  async function copyToClipboard(text: string, setter: (v: boolean) => void) {
    try {
      await navigator.clipboard.writeText(text);
      setter(true);
      setTimeout(() => setter(false), 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  function getOutsideArchiveCount(): number {
    return files.filter(f => !f.archive && !f.container).length;
  }
</script>

<!-- ========== 统一 UI 结构的区块 ========== -->

<!-- 路径输入 -->
{#snippet pathBlock()}
  <div class="cq-mb">
    <div class="flex items-center gap-1 mb-1 cq-text">
      <Search class="cq-icon" />
      <span class="font-medium">搜索路径</span>
    </div>
    {#if !hasInputConnection}
      <div class="flex cq-gap">
        <Input bind:value={targetPath} placeholder="输入或选择目录..." disabled={isRunning} class="flex-1 cq-input" />
        <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={selectFolder} disabled={isRunning}>
          <FolderOpen class="cq-icon" />
        </Button>
        <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={pasteFromClipboard} disabled={isRunning}>
          <Clipboard class="cq-icon" />
        </Button>
      </div>
    {:else}
      <div class="text-muted-foreground cq-padding bg-muted cq-rounded flex items-center cq-gap cq-text">
        <span>←</span><span>输入来自上游节点</span>
      </div>
    {/if}
  </div>
{/snippet}

<!-- 过滤器 -->
{#snippet filterBlock()}
  <div class="h-full flex flex-col overflow-auto">
    <FilterBuilder 
      advancedMode={advancedMode}
      sqlValue={whereClause}
      onchange={(_, sql) => { whereClause = sql; }}
      onAdvancedChange={(adv) => advancedMode = adv}
      disabled={isRunning}
    />
  </div>
{/snippet}

<!-- 操作按钮（含状态显示） -->
{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <!-- 状态指示 -->
    <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded">
      {#if phase === 'completed'}
        <CircleCheck class="cq-icon text-green-500 shrink-0" />
        <span class="cq-text text-green-600 font-medium">完成</span>
        <span class="cq-text-sm text-muted-foreground ml-auto">{searchResult?.total_count ?? 0} 项</span>
      {:else if phase === 'error'}
        <CircleX class="cq-icon text-red-500 shrink-0" />
        <span class="cq-text text-red-600 font-medium">失败</span>
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <div class="flex-1">
          <Progress value={progress} class="h-1.5" />
        </div>
        <span class="cq-text-sm text-muted-foreground">{progress}%</span>
      {:else}
        <Search class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text text-muted-foreground">等待执行</span>
      {/if}
    </div>
    <!-- 主按钮 -->
    <Button class="w-full cq-button flex-1" onclick={() => executeAction('search')} disabled={!canExecute || isRunning}>
      {#if isRunning}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<Search class="cq-icon mr-1" />{/if}
      <span>搜索</span>
    </Button>
    <!-- 辅助按钮 -->
    <div class="flex cq-gap">
      <Button variant="outline" class="flex-1 cq-button-sm" onclick={() => executeAction('archives_only')} disabled={!canExecute || isRunning}>
        <Archive class="cq-icon" /><span class="cq-wide-only ml-1">压缩包</span>
      </Button>
      <Button variant="outline" class="flex-1 cq-button-sm" onclick={() => executeAction('nested')} disabled={!canExecute || isRunning}>
        <Layers class="cq-icon" /><span class="cq-wide-only ml-1">嵌套</span>
      </Button>
      {#if phase === 'completed' || phase === 'error'}
        <Button variant="ghost" size="icon" class="cq-button-icon" onclick={handleReset}>
          <RotateCcw class="cq-icon" />
        </Button>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 统计 -->
{#snippet statsBlock()}
  {@const outsideCount = getOutsideArchiveCount()}
  {#if searchResult}
    <div class="grid grid-cols-2 cq-gap">
      <div class="cq-stat-card bg-blue-500/10 col-span-2">
        <div class="flex items-center justify-between">
          <span class="cq-stat-label text-muted-foreground">总计</span>
          <span class="cq-stat-value text-blue-600 tabular-nums">{searchResult.total_count}</span>
        </div>
      </div>
      <div class="cq-stat-card bg-green-500/10">
        <div class="flex items-center justify-between">
          <File class="cq-icon text-green-600" />
          <span class="cq-stat-value text-green-600 tabular-nums">{outsideCount}</span>
        </div>
        <div class="cq-stat-label text-muted-foreground">文件系统</div>
      </div>
      <div class="cq-stat-card bg-purple-500/10">
        <div class="flex items-center justify-between">
          <Package class="cq-icon text-purple-600" />
          <span class="cq-stat-value text-purple-600 tabular-nums">{searchResult.archive_count}</span>
        </div>
        <div class="cq-stat-label text-muted-foreground">压缩包内</div>
      </div>
    </div>
    <!-- 扩展名统计（仅宽屏） -->
    {#if Object.keys(byExtension).length > 0}
      <div class="cq-wide-only mt-2">
        <div class="text-xs text-muted-foreground mb-1">按扩展名</div>
        <div class="flex flex-wrap gap-1">
          {#each Object.entries(byExtension).sort((a, b) => b[1] - a[1]).slice(0, 8) as [ext, count]}
            <span class="text-xs px-1.5 py-0.5 bg-muted rounded">.{ext || '无'}: {count}</span>
          {/each}
        </div>
      </div>
    {/if}
  {:else}
    <div class="cq-text text-muted-foreground text-center py-2">搜索后显示统计</div>
  {/if}
{/snippet}

<!-- 文件列表 -->
{#snippet treeBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between cq-padding border-b bg-muted/30 shrink-0">
      <span class="cq-text font-semibold flex items-center gap-1">
        <Folder class="cq-icon text-yellow-500" />文件列表
      </span>
      <div class="flex items-center gap-1">
        <span class="cq-text-sm text-muted-foreground">{files.length}</span>
        {#if files.length > 0}
          <Button variant="ghost" size="icon" class="h-5 w-5" onclick={() => copyToClipboard(files.map(f => f.container ? `${f.container}//${f.path}` : f.path).join('\n'), v => copiedPath = v)}>
            {#if copiedPath}<Check class="w-3 h-3 text-green-500" />{:else}<Copy class="w-3 h-3" />{/if}
          </Button>
        {/if}
      </div>
    </div>
    <div class="flex-1 overflow-y-auto cq-padding">
      {#if files.length > 0}
        <div class="space-y-0.5">
          {#each files.slice(0, 50) as file}
            <div class="flex items-center gap-1 cq-text truncate py-0.5 hover:bg-muted/50 rounded px-1">
              {#if file.container}
                <Package class="w-3 h-3 text-purple-500 shrink-0" />
              {:else}
                <File class="w-3 h-3 text-blue-500 shrink-0" />
              {/if}
              <span class="truncate flex-1">{file.name}</span>
              <span class="cq-text-sm text-muted-foreground shrink-0">{file.size_formatted}</span>
            </div>
          {/each}
          {#if files.length > 50}
            <div class="cq-text-sm text-muted-foreground text-center py-1">+{files.length - 50} 更多</div>
          {/if}
        </div>
      {:else}
        <div class="cq-text text-muted-foreground text-center py-4">搜索后显示</div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 日志 -->
{#snippet logBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold">日志</span>
      <Button variant="ghost" size="icon" class="h-5 w-5" onclick={() => copyToClipboard(logs.join('\n'), v => copiedLogs = v)}>
        {#if copiedLogs}<Check class="w-3 h-3 text-green-500" />{:else}<Copy class="w-3 h-3" />{/if}
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

<!-- 分析面板 -->
{#snippet analysisBlock()}
  <AnalysisPanel {files} />
{/snippet}

<!-- 区块渲染器 -->
{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'path'}{@render pathBlock()}
  {:else if blockId === 'filter'}{@render filterBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'stats'}{@render statsBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {:else if blockId === 'tree'}{@render treeBlock()}
  {:else if blockId === 'analysis'}{@render analysisBlock()}
  {/if}
{/snippet}

<!-- 主渲染 -->
<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 420px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={300} minHeight={380} maxWidth={420} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="findz" 
    icon={Search} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="findz" 
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
        nodeType="findz"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={FINDZ_DEFAULT_GRID_LAYOUT}
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
