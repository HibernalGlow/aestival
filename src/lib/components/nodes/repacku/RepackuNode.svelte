<script lang="ts">
  /**
   * RepackuNode - 文件重打包节点组件
   * 使用 NodeLayoutRenderer 统一布局，支持节点模式和全屏模式
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { REPACKU_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import type { FolderNode, CompressionStats } from '$lib/types/repacku';
  import { getModeColorClass, getModeName, countCompressionModes } from './utils';
  import { 
    Play, LoaderCircle, FolderOpen, Clipboard, Package,
    CircleCheck, CircleX, FileArchive, Search, FolderTree,
    Trash2, Copy, Check, Folder, Image, FileText, Video, Music, 
    ChevronRight, ChevronDown, RotateCcw
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: { path?: string; types?: string[]; delete_after?: boolean };
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
      label?: string;
      showTree?: boolean;
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'analyzing' | 'analyzed' | 'compressing' | 'completed' | 'error';

  interface AnalysisResult {
    configPath: string;
    totalFolders: number;
    entireCount: number;
    selectiveCount: number;
    skipCount: number;
    folderTree?: FolderNode;
  }

  interface CompressionResultData {
    success: boolean;
    compressed: number;
    failed: number;
    total: number;
  }

  interface RepackuState {
    phase: Phase;
    progress: number;
    progressText: string;
    folderTree: FolderNode | null;
    analysisResult: AnalysisResult | null;
    compressionResult: CompressionResultData | null;
    selectedTypes: string[];
    expandedFolders: string[];
    path: string;
    deleteAfter: boolean;
  }

  // 使用 $derived 确保响应式
  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<RepackuState>(nodeId));
  const configPath = $derived(data?.config?.path ?? '');
  const configDeleteAfter = $derived(data?.config?.delete_after ?? false);
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  // 状态初始化
  let path = $state('');
  let deleteAfter = $state(false);
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let hasInputConnection = $state(false);
  let copied = $state(false);

  let progress = $state(0);
  let progressText = $state('');

  // 文件树数据
  let folderTree = $state<FolderNode | null>(null);
  let stats = $state<CompressionStats>({ total: 0, entire: 0, selective: 0, skip: 0 });
  let expandedFolders = $state<Set<string>>(new Set());

  let analysisResult = $state<AnalysisResult | null>(null);
  let compressionResult = $state<CompressionResultData | null>(null);
  let selectedTypes = $state<string[]>([]);

  // 初始化标记
  let initialized = $state(false);

  // 初始化 effect - 只执行一次
  $effect(() => {
    if (initialized) return;
    
    if (savedState) {
      phase = savedState.phase ?? 'idle';
      progress = savedState.progress ?? 0;
      progressText = savedState.progressText ?? '';
      folderTree = savedState.folderTree ?? null;
      analysisResult = savedState.analysisResult ?? null;
      compressionResult = savedState.compressionResult ?? null;
      selectedTypes = savedState.selectedTypes ?? [];
      expandedFolders = new Set(savedState.expandedFolders ?? []);
      path = savedState.path || configPath || '';
      deleteAfter = savedState.deleteAfter ?? configDeleteAfter;
    } else {
      path = configPath || '';
      deleteAfter = configDeleteAfter;
    }
    
    initialized = true;
  });
  
  // 持续同步外部数据
  $effect(() => {
    logs = [...dataLogs];
    hasInputConnection = dataHasInputConnection;
  });

  // NodeLayoutRenderer 引用
  let layoutRenderer = $state<any>(undefined);

  const typeOptions = [
    { value: 'image', label: '图片' },
    { value: 'document', label: '文档' },
    { value: 'video', label: '视频' },
    { value: 'audio', label: '音频' }
  ];

  function saveState() {
    if (!initialized) return;
    setNodeState<RepackuState>(nodeId, {
      phase, progress, progressText, folderTree, analysisResult, compressionResult,
      selectedTypes, expandedFolders: Array.from(expandedFolders), path, deleteAfter
    });
  }

  // 响应式派生值
  let canAnalyze = $derived(phase === 'idle' && (path.trim() !== '' || hasInputConnection));
  let canCompress = $derived(phase === 'analyzed' && analysisResult !== null);
  let isRunning = $derived(phase === 'analyzing' || phase === 'compressing');
  let borderClass = $derived({
    idle: 'border-border', analyzing: 'border-primary shadow-sm', analyzed: 'border-primary/50',
    compressing: 'border-primary shadow-sm', completed: 'border-primary/50', error: 'border-destructive/50'
  }[phase]);

  // 状态变化时自动保存
  $effect(() => {
    if (phase || folderTree || analysisResult || compressionResult) saveState();
  });

  // 当 folderTree 更新时，重新计算统计
  $effect(() => {
    if (folderTree) stats = countCompressionModes(folderTree);
  });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  function toggleFolder(folderPath: string) {
    if (expandedFolders.has(folderPath)) expandedFolders.delete(folderPath);
    else expandedFolders.add(folderPath);
    expandedFolders = new Set(expandedFolders);
  }

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

  function toggleType(type: string) {
    if (selectedTypes.includes(type)) selectedTypes = selectedTypes.filter(t => t !== type);
    else selectedTypes = [...selectedTypes, type];
  }

  async function handleAnalyze() {
    if (!canAnalyze) return;
    phase = 'analyzing'; progress = 0; progressText = '正在扫描目录结构...';
    analysisResult = null; compressionResult = null; folderTree = null;
    log(`🔍 开始分析目录: ${path}`);
    if (selectedTypes.length > 0) log(`📋 类型过滤: ${selectedTypes.join(', ')}`);

    try {
      progress = 30; progressText = '正在分析文件类型分布...';
      const response = await api.executeNode('repacku', {
        action: 'analyze', path, types: selectedTypes.length > 0 ? selectedTypes : [], display_tree: true
      }) as any;

      if (response.success && response.data) {
        phase = 'analyzed'; progress = 100; progressText = '分析完成';
        folderTree = response.data.folder_tree || null;
        analysisResult = {
          configPath: response.data.config_path ?? '', totalFolders: response.data.total_folders ?? 0,
          entireCount: response.data.entire_count ?? 0, selectiveCount: response.data.selective_count ?? 0,
          skipCount: response.data.skip_count ?? 0, folderTree: response.data.folder_tree
        };
        log(`✅ 分析完成`);
        log(`📊 整体压缩: ${analysisResult.entireCount}, 选择性: ${analysisResult.selectiveCount}, 跳过: ${analysisResult.skipCount}`);
      } else { phase = 'error'; progress = 0; log(`❌ 分析失败: ${response.message}`); }
    } catch (error) { phase = 'error'; progress = 0; log(`❌ 分析失败: ${error}`); }
  }

  async function handleCompress() {
    if (!canCompress || !analysisResult) return;
    phase = 'compressing'; progress = 0; progressText = '正在压缩文件...';
    log(`📦 开始压缩...`);

    try {
      progress = 20;
      const response = await api.executeNode('repacku', {
        action: 'compress', config_path: analysisResult.configPath, delete_after: deleteAfter
      }) as any;

      if (response.success) {
        phase = 'completed'; progress = 100; progressText = '压缩完成';
        compressionResult = {
          success: true, compressed: response.data?.compressed_count ?? 0,
          failed: response.data?.failed_count ?? 0, total: response.data?.total_folders ?? 0
        };
        log(`✅ ${response.message}`);
        log(`📊 成功: ${compressionResult.compressed}, 失败: ${compressionResult.failed}`);
      } else { phase = 'error'; progress = 0; log(`❌ 压缩失败: ${response.message}`); }
    } catch (error) { phase = 'error'; progress = 0; log(`❌ 压缩失败: ${error}`); }
  }

  function handleReset() {
    phase = 'idle'; progress = 0; progressText = '';
    analysisResult = null; compressionResult = null; folderTree = null;
    logs = []; expandedFolders.clear();
  }

  async function copyLogs() {
    try { await navigator.clipboard.writeText(logs.join('\n')); copied = true; setTimeout(() => { copied = false; }, 2000); }
    catch (e) { console.error('复制失败:', e); }
  }

  function getFileTypeIcon(type: string) {
    switch (type.toLowerCase()) {
      case 'image': return Image;
      case 'document': return FileText;
      case 'video': return Video;
      case 'audio': return Music;
      default: return FileText;
    }
  }
</script>


<!-- 递归渲染文件夹树节点 -->
{#snippet renderFolderNode(node: FolderNode, depth: number = 0)}
  {@const isExpanded = expandedFolders.has(node.path)}
  {@const hasChildren = node.children && node.children.length > 0}
  {@const modeColor = getModeColorClass(node.compress_mode)}
  {@const modeText = getModeName(node.compress_mode)}

  <div class="select-none">
    <div 
      class="flex items-center gap-1 py-0.5 px-1 rounded hover:bg-muted/50 cursor-pointer text-xs"
      style="padding-left: {depth * 12}px"
      onclick={() => hasChildren && toggleFolder(node.path)}
      onkeydown={(e) => e.key === 'Enter' && hasChildren && toggleFolder(node.path)}
      role="button" tabindex="0"
    >
      {#if hasChildren}
        {#if isExpanded}<ChevronDown class="w-3 h-3 text-muted-foreground shrink-0" />
        {:else}<ChevronRight class="w-3 h-3 text-muted-foreground shrink-0" />{/if}
      {:else}<span class="w-3 h-3 shrink-0"></span>{/if}

      <Folder class="w-3 h-3 text-yellow-500 shrink-0" />
      <span class="w-2 h-2 rounded-full shrink-0 {modeColor}" title={modeText}></span>
      <span class="truncate flex-1" title={node.name}>{node.name}</span>
      <span class="text-muted-foreground shrink-0">{node.total_files}</span>

      {#if node.dominant_types && node.dominant_types.length > 0}
        <div class="flex gap-0.5 shrink-0">
          {#each node.dominant_types.slice(0, 2) as type}
            {@const IconComponent = getFileTypeIcon(type)}
            <IconComponent class="w-3 h-3 text-muted-foreground" />
          {/each}
        </div>
      {/if}
    </div>

    {#if hasChildren && isExpanded}
      {#each node.children as child}
        {@render renderFolderNode(child, depth + 1)}
      {/each}
    {/if}
  </div>
{/snippet}


<!-- ========== 区块内容 Snippets（使用 Container Query CSS） ========== -->

<!-- 路径输入区块 -->
{#snippet pathBlock()}
  {#if !hasInputConnection}
    <div class="flex cq-gap cq-mb">
      <Input bind:value={path} placeholder="输入或选择文件夹路径..." disabled={isRunning} class="flex-1 cq-input" />
      <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={selectFolder} disabled={isRunning}>
        <FolderOpen class="cq-icon" />
      </Button>
      <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={pasteFromClipboard} disabled={isRunning}>
        <Clipboard class="cq-icon" />
      </Button>
    </div>
  {:else}
    <div class="text-muted-foreground cq-padding bg-muted cq-rounded flex items-center cq-gap cq-mb cq-text">
      <span>←</span><span>输入来自上游节点</span>
    </div>
  {/if}
{/snippet}

<!-- 类型过滤区块 -->
{#snippet typesBlock()}
  <div class="flex flex-wrap cq-gap">
    {#each typeOptions as option}
      <button
        class="cq-px cq-py cq-text cq-rounded border transition-colors {selectedTypes.includes(option.value) ? 'bg-primary text-primary-foreground border-primary' : 'bg-background border-border hover:border-primary'}"
        onclick={() => toggleType(option.value)} disabled={isRunning}
      >{option.label}</button>
    {/each}
  </div>
  <label class="cq-wide-only-flex items-center cq-gap mt-auto pt-3 border-t cursor-pointer">
    <Checkbox id="delete-after-fs-{nodeId}" bind:checked={deleteAfter} disabled={isRunning} />
    <span class="cq-text flex items-center gap-1"><Trash2 class="cq-icon" />压缩后删除源文件</span>
  </label>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <!-- 状态指示 -->
    <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded">
      {#if compressionResult}
        {#if compressionResult.success}
          <CircleCheck class="cq-icon text-green-500 shrink-0" />
          <span class="cq-text text-green-600 font-medium">完成</span>
          <span class="cq-text-sm text-muted-foreground ml-auto">{compressionResult.compressed} 成功</span>
        {:else}
          <CircleX class="cq-icon text-red-500 shrink-0" />
          <span class="cq-text text-red-600 font-medium">失败</span>
        {/if}
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <div class="flex-1"><Progress value={progress} class="h-1.5" /></div>
        <span class="cq-text-sm text-muted-foreground">{progress}%</span>
      {:else}
        <Package class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text text-muted-foreground">等待扫描</span>
      {/if}
    </div>
    <!-- 主按钮 -->
    {#if phase === 'idle' || phase === 'error'}
      <Button class="w-full cq-button flex-1" onclick={handleAnalyze} disabled={!canAnalyze}>
        <Search class="cq-icon mr-1" /><span>扫描分析</span>
      </Button>
    {:else if phase === 'analyzing'}
      <Button class="w-full cq-button flex-1" disabled>
        <LoaderCircle class="cq-icon mr-1 animate-spin" /><span>分析中</span>
      </Button>
    {:else if phase === 'analyzed'}
      <Button class="w-full cq-button flex-1" onclick={handleCompress} disabled={!canCompress}>
        <FileArchive class="cq-icon mr-1" /><span>开始压缩</span>
      </Button>
    {:else if phase === 'compressing'}
      <Button class="w-full cq-button flex-1" disabled>
        <LoaderCircle class="cq-icon mr-1 animate-spin" /><span>压缩中</span>
      </Button>
    {:else if phase === 'completed'}
      <Button class="w-full cq-button flex-1" onclick={handleReset}>
        <Play class="cq-icon mr-1" /><span>重新开始</span>
      </Button>
    {/if}
    <!-- 辅助按钮 -->
    <div class="flex cq-gap">
      <Button variant="ghost" class="flex-1 cq-button-sm" onclick={handleReset} disabled={isRunning}>
        <RotateCcw class="cq-icon mr-1" />重置
      </Button>
      <!-- 紧凑模式下的删除选项 -->
      <label class="cq-compact-only-flex items-center gap-2 cursor-pointer">
        <Checkbox id="delete-after-compact-{nodeId}" bind:checked={deleteAfter} disabled={isRunning} class="h-3 w-3" />
        <span class="cq-text-sm flex items-center gap-1"><Trash2 class="cq-icon-sm text-orange-500" />删除源</span>
      </label>
    </div>
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlock()}
  <div class="grid grid-cols-3 cq-gap">
    <div class="cq-stat-card bg-green-500/10">
      <div class="flex flex-col items-center">
        <span class="cq-stat-value text-green-600 tabular-nums">{analysisResult?.entireCount ?? '-'}</span>
        <span class="cq-stat-label text-muted-foreground">整体</span>
      </div>
    </div>
    <div class="cq-stat-card bg-yellow-500/10">
      <div class="flex flex-col items-center">
        <span class="cq-stat-value text-yellow-600 tabular-nums">{analysisResult?.selectiveCount ?? '-'}</span>
        <span class="cq-stat-label text-muted-foreground">选择</span>
      </div>
    </div>
    <div class="cq-stat-card bg-muted/40">
      <div class="flex flex-col items-center">
        <span class="cq-stat-value text-gray-500 tabular-nums">{analysisResult?.skipCount ?? '-'}</span>
        <span class="cq-stat-label text-muted-foreground">跳过</span>
      </div>
    </div>
  </div>
{/snippet}

<!-- 进度/状态区块 -->
{#snippet progressBlock()}
  <div class="h-full flex items-center cq-gap">
    {#if compressionResult}
      {#if compressionResult.success}
        <CircleCheck class="cq-icon-lg text-green-500 shrink-0" />
        <div class="flex-1">
          <span class="font-semibold text-green-600 cq-text">压缩完成</span>
          <div class="flex cq-gap cq-text-sm mt-1">
            <span class="text-green-600">成功: {compressionResult.compressed}</span>
            <span class="text-red-600">失败: {compressionResult.failed}</span>
          </div>
        </div>
      {:else}
        <CircleX class="cq-icon-lg text-red-500 shrink-0" />
        <span class="font-semibold text-red-600 cq-text">压缩失败</span>
      {/if}
    {:else if isRunning}
      <LoaderCircle class="cq-icon-lg text-primary animate-spin shrink-0" />
      <div class="flex-1">
        <div class="flex justify-between cq-text-sm mb-1"><span>{progressText}</span><span>{progress}%</span></div>
        <Progress value={progress} class="h-2" />
      </div>
    {:else}
      <Package class="cq-icon-lg text-muted-foreground/50 shrink-0" />
      <div class="flex-1">
        <span class="text-muted-foreground cq-text">等待扫描</span>
        <div class="cq-text-sm text-muted-foreground/70 mt-1">扫描完成后可开始压缩</div>
      </div>
    {/if}
  </div>
{/snippet}

<!-- 文件树区块 -->
{#snippet treeBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold flex items-center gap-1">
        <FolderTree class="cq-icon text-yellow-500" />文件树
      </span>
      <div class="flex items-center cq-gap cq-text-sm">
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>{stats.entire}</span>
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-yellow-500"></span>{stats.selective}</span>
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-gray-400"></span>{stats.skip}</span>
      </div>
    </div>
    <div class="flex-1 overflow-y-auto cq-padding">
      {#if folderTree}{@render renderFolderNode(folderTree)}
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
    <div class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding font-mono cq-text-sm space-y-0.5">
      {#if logs.length > 0}
        {#each logs.slice(-10) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 通用区块渲染器 -->
{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'path'}{@render pathBlock()}{@render typesBlock()}
  {:else if blockId === 'types'}{@render typesBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'stats'}{@render statsBlock()}
  {:else if blockId === 'progress'}{@render progressBlock()}
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
    title="repacku" 
    icon={Package} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="repacku" 
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
        nodeType="repacku"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={REPACKU_DEFAULT_GRID_LAYOUT}
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
