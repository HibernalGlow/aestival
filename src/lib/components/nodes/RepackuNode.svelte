<script lang="ts">
  /**
   * RepackuNode - 文件重打包节点组件
   * 使用区块系统，支持普通模式（Bento Grid）和全屏模式（GridStack）
   * 使用 nodeStateStore 在全屏和普通模式间共享状态
   */
  import { Handle, Position } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';
  import { Badge } from '$lib/components/ui/badge';
  import { DashboardGrid, DashboardItem } from '$lib/components/ui/dashboard-grid';
  import type { GridItem } from '$lib/components/ui/dashboard-grid';
  import { BlockCard } from '$lib/components/blocks';
  import { REPACKU_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import { getDefaultPreset } from '$lib/stores/layoutPresets';
  import NodeWrapper from './NodeWrapper.svelte';
  import type { FolderNode, CompressionStats } from '$lib/types/repacku';
  import { getModeColorClass, getModeName, countCompressionModes } from './repacku-utils';
  import { 
    Play, LoaderCircle, FolderOpen, Clipboard, Package,
    CircleCheck, CircleX, FileArchive, Search, FolderTree,
    Trash2, Copy, Check, PanelRightOpen, PanelRightClose,
    Folder, Image, FileText, Video, Music, ChevronRight, ChevronDown
  } from '@lucide/svelte';
  
  let copied = false;
  
  export let id: string;
  export let data: {
    config?: { path?: string; types?: string[]; delete_after?: boolean };
    status?: 'idle' | 'running' | 'completed' | 'error';
    hasInputConnection?: boolean;
    logs?: string[];
    label?: string;
    showTree?: boolean;
  } = {};
  export let isFullscreenRender = false;

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
  
  // 节点内部状态类型
  interface RepackuState {
    phase: Phase;
    progress: number;
    progressText: string;
    folderTree: FolderNode | null;
    analysisResult: AnalysisResult | null;
    compressionResult: CompressionResultData | null;
    selectedTypes: string[];
    expandedFolders: string[];
    gridLayout?: GridItem[];
  }
  
  // 从 nodeStateStore 获取或初始化状态
  const savedState = getNodeState<RepackuState>(id);
  
  // 初始化状态
  let path = data?.config?.path ?? '';
  let deleteAfter = data?.config?.delete_after ?? false;
  let phase: Phase = savedState?.phase ?? 'idle';
  let logs: string[] = data?.logs ? [...data.logs] : [];
  let hasInputConnection = data?.hasInputConnection ?? false;
  let showTree = data?.showTree ?? true;
  
  let progress = savedState?.progress ?? 0;
  let progressText = savedState?.progressText ?? '';
  
  // 文件树数据
  let folderTree: FolderNode | null = savedState?.folderTree ?? null;
  let stats: CompressionStats = { total: 0, entire: 0, selective: 0, skip: 0 };
  let expandedFolders: Set<string> = new Set(savedState?.expandedFolders ?? []);
  
  let analysisResult: AnalysisResult | null = savedState?.analysisResult ?? null;
  let compressionResult: CompressionResultData | null = savedState?.compressionResult ?? null;

  // GridStack 布局（优先使用保存的状态，其次用户设置的默认预设，最后硬编码默认值）
  function getInitialLayout(): GridItem[] {
    if (savedState?.gridLayout) return savedState.gridLayout;
    const defaultPreset = getDefaultPreset('repacku');
    if (defaultPreset) return [...defaultPreset.layout];
    return [...REPACKU_DEFAULT_GRID_LAYOUT];
  }
  let gridLayout: GridItem[] = getInitialLayout();
  
  // DashboardGrid 组件引用
  let dashboardGrid: { compact: () => void; applyLayout: (layout: GridItem[]) => void } | undefined;
  
  // 处理布局变化
  function handleLayoutChange(newLayout: GridItem[]) {
    gridLayout = newLayout;
    saveState();
  }
  
  // 根据 id 获取布局项
  function getLayoutItem(itemId: string): GridItem {
    return gridLayout.find(item => item.id === itemId) ?? { id: itemId, x: 0, y: 0, w: 1, h: 1 };
  }

  const typeOptions = [
    { value: 'image', label: '图片' },
    { value: 'document', label: '文档' },
    { value: 'video', label: '视频' },
    { value: 'audio', label: '音频' }
  ];
  
  let selectedTypes: string[] = savedState?.selectedTypes ?? [];
  
  // 保存状态到 nodeStateStore
  function saveState() {
    setNodeState<RepackuState>(id, {
      phase, progress, progressText, folderTree, analysisResult, compressionResult,
      selectedTypes, expandedFolders: Array.from(expandedFolders), gridLayout
    });
  }
  
  // 状态变化时自动保存
  $: if (phase || folderTree || analysisResult || compressionResult) saveState();

  $: canAnalyze = phase === 'idle' && (path.trim() !== '' || hasInputConnection);
  $: canCompress = phase === 'analyzed' && analysisResult !== null;
  $: isRunning = phase === 'analyzing' || phase === 'compressing';
  
  $: borderClass = {
    idle: 'border-border', analyzing: 'border-primary shadow-sm', analyzed: 'border-primary/50',
    compressing: 'border-primary shadow-sm', completed: 'border-primary/50', error: 'border-destructive/50'
  }[phase];

  // 当 folderTree 更新时，重新计算统计
  $: if (folderTree) stats = countCompressionModes(folderTree);

  function toggleFolder(path: string) {
    if (expandedFolders.has(path)) expandedFolders.delete(path);
    else expandedFolders.add(path);
    expandedFolders = new Set(expandedFolders);
  }

  async function selectFolder() {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFolderDialog('选择文件夹');
      if (selected) path = selected;
    } catch (e) { logs = [...logs, `选择文件夹失败: ${e}`]; }
  }

  async function pasteFromClipboard() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) path = text.trim();
    } catch (e) { logs = [...logs, `读取剪贴板失败: ${e}`]; }
  }

  function toggleType(type: string) {
    if (selectedTypes.includes(type)) selectedTypes = selectedTypes.filter(t => t !== type);
    else selectedTypes = [...selectedTypes, type];
  }

  async function handleAnalyze() {
    if (!canAnalyze) return;
    phase = 'analyzing'; progress = 0; progressText = '正在扫描目录结构...';
    analysisResult = null; compressionResult = null; folderTree = null;
    logs = [...logs, `🔍 开始分析目录: ${path}`];
    if (selectedTypes.length > 0) logs = [...logs, `📋 类型过滤: ${selectedTypes.join(', ')}`];
    
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
        logs = [...logs, `✅ 分析完成`, `📊 整体压缩: ${analysisResult.entireCount}, 选择性: ${analysisResult.selectiveCount}, 跳过: ${analysisResult.skipCount}`];
      } else { phase = 'error'; progress = 0; logs = [...logs, `❌ 分析失败: ${response.message}`]; }
    } catch (error) { phase = 'error'; progress = 0; logs = [...logs, `❌ 分析失败: ${error}`]; }
  }

  async function handleCompress() {
    if (!canCompress || !analysisResult) return;
    phase = 'compressing'; progress = 0; progressText = '正在压缩文件...';
    logs = [...logs, `📦 开始压缩...`];
    
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
        logs = [...logs, `✅ ${response.message}`, `📊 成功: ${compressionResult.compressed}, 失败: ${compressionResult.failed}`];
      } else { phase = 'error'; progress = 0; logs = [...logs, `❌ 压缩失败: ${response.message}`]; }
    } catch (error) { phase = 'error'; progress = 0; logs = [...logs, `❌ 压缩失败: ${error}`]; }
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


<!-- ========== 区块内容 Snippets ========== -->

<!-- 路径输入区块内容 -->
{#snippet pathBlockContent()}
  {#if !hasInputConnection}
    <div class="flex gap-2 {isFullscreenRender ? 'mb-4' : 'mb-2'}">
      <Input bind:value={path} placeholder="输入或选择文件夹路径..." disabled={isRunning} 
        class="flex-1 {isFullscreenRender ? 'h-10' : 'h-7 text-xs'}" />
      <Button variant="outline" size="icon" class="{isFullscreenRender ? 'h-10 w-10' : 'h-7 w-7'} shrink-0" onclick={selectFolder} disabled={isRunning}>
        <FolderOpen class="{isFullscreenRender ? 'h-4 w-4' : 'h-3 w-3'}" />
      </Button>
      <Button variant="outline" size="icon" class="{isFullscreenRender ? 'h-10 w-10' : 'h-7 w-7'} shrink-0" onclick={pasteFromClipboard} disabled={isRunning}>
        <Clipboard class="{isFullscreenRender ? 'h-4 w-4' : 'h-3 w-3'}" />
      </Button>
    </div>
  {:else}
    <div class="text-muted-foreground {isFullscreenRender ? 'p-3' : 'p-2 text-xs'} bg-muted rounded-xl flex items-center gap-2 {isFullscreenRender ? 'mb-4' : 'mb-2'}">
      <span>←</span><span>输入来自上游节点</span>
    </div>
  {/if}
{/snippet}

<!-- 类型过滤区块内容 -->
{#snippet typesBlockContent()}
  <div class="flex flex-wrap gap-{isFullscreenRender ? '2' : '1'}">
    {#each typeOptions as option}
      <button
        class="px-{isFullscreenRender ? '3' : '2'} py-{isFullscreenRender ? '1.5' : '1'} text-{isFullscreenRender ? 'sm' : 'xs'} rounded-lg border transition-colors {selectedTypes.includes(option.value) ? 'bg-primary text-primary-foreground border-primary' : 'bg-background border-border hover:border-primary'}"
        onclick={() => toggleType(option.value)} disabled={isRunning}
      >{option.label}</button>
    {/each}
  </div>
{/snippet}

<!-- 操作区块内容 -->
{#snippet operationBlockContent()}
  <div class="flex flex-col gap-{isFullscreenRender ? '2' : '1.5'} {isFullscreenRender ? 'flex-1 justify-center' : ''}">
    {#if phase === 'idle' || phase === 'error'}
      <Button class="{isFullscreenRender ? 'h-12' : 'flex-1 h-8 text-xs'}" onclick={handleAnalyze} disabled={!canAnalyze}>
        <Search class="{isFullscreenRender ? 'h-4 w-4 mr-2' : 'h-3 w-3 mr-1'}" />扫描{isFullscreenRender ? '分析' : ''}
      </Button>
    {:else if phase === 'analyzing'}
      <Button class="{isFullscreenRender ? 'h-12' : 'flex-1 h-8 text-xs'}" disabled>
        <LoaderCircle class="{isFullscreenRender ? 'h-4 w-4 mr-2' : 'h-3 w-3 mr-1'} animate-spin" />分析中
      </Button>
    {:else if phase === 'analyzed'}
      <Button class="{isFullscreenRender ? 'h-12' : 'flex-1 h-8 text-xs'}" onclick={handleCompress} disabled={!canCompress}>
        <FileArchive class="{isFullscreenRender ? 'h-4 w-4 mr-2' : 'h-3 w-3 mr-1'}" />{isFullscreenRender ? '开始' : ''}压缩
      </Button>
      <Button variant="outline" class="{isFullscreenRender ? 'h-9' : 'h-6 text-xs'}" onclick={handleReset}>重置</Button>
    {:else if phase === 'compressing'}
      <Button class="{isFullscreenRender ? 'h-12' : 'flex-1 h-8 text-xs'}" disabled>
        <LoaderCircle class="{isFullscreenRender ? 'h-4 w-4 mr-2' : 'h-3 w-3 mr-1'} animate-spin" />压缩中
      </Button>
    {:else if phase === 'completed'}
      <Button class="{isFullscreenRender ? 'h-12' : 'flex-1 h-8 text-xs'}" variant="outline" onclick={handleReset}>
        <Play class="{isFullscreenRender ? 'h-4 w-4 mr-2' : 'h-3 w-3 mr-1'}" />重新开始
      </Button>
    {/if}
  </div>
{/snippet}


<!-- 统计区块内容 -->
{#snippet statsBlockContent()}
  {#if isFullscreenRender}
    <div class="space-y-2 flex-1">
      <div class="flex items-center justify-between p-2 bg-green-500/10 rounded-lg">
        <span class="text-sm">整体</span>
        <span class="text-xl font-bold text-green-600">{analysisResult?.entireCount ?? '-'}</span>
      </div>
      <div class="flex items-center justify-between p-2 bg-yellow-500/10 rounded-lg">
        <span class="text-sm">选择性</span>
        <span class="text-xl font-bold text-yellow-600">{analysisResult?.selectiveCount ?? '-'}</span>
      </div>
      <div class="flex items-center justify-between p-2 bg-gray-500/10 rounded-lg">
        <span class="text-sm">跳过</span>
        <span class="text-xl font-bold text-gray-500">{analysisResult?.skipCount ?? '-'}</span>
      </div>
    </div>
  {:else}
    <div class="grid grid-cols-3 gap-1 text-xs">
      <div class="text-center p-1.5 bg-green-500/10 rounded-lg">
        <div class="font-bold text-green-600">{analysisResult?.entireCount ?? '-'}</div>
        <div class="text-muted-foreground text-[10px]">整体</div>
      </div>
      <div class="text-center p-1.5 bg-yellow-500/10 rounded-lg">
        <div class="font-bold text-yellow-600">{analysisResult?.selectiveCount ?? '-'}</div>
        <div class="text-muted-foreground text-[10px]">选择</div>
      </div>
      <div class="text-center p-1.5 bg-gray-500/10 rounded-lg">
        <div class="font-bold text-gray-500">{analysisResult?.skipCount ?? '-'}</div>
        <div class="text-muted-foreground text-[10px]">跳过</div>
      </div>
    </div>
  {/if}
{/snippet}

<!-- 进度/状态区块内容 -->
{#snippet progressBlockContent()}
  {#if isFullscreenRender}
    <div class="h-full flex items-center gap-3">
      {#if compressionResult}
        {#if compressionResult.success}
          <CircleCheck class="w-8 h-8 text-green-500 shrink-0" />
          <div class="flex-1">
            <span class="font-semibold text-green-600">压缩完成</span>
            <div class="flex gap-4 text-sm mt-1">
              <span class="text-green-600">成功: {compressionResult.compressed}</span>
              <span class="text-red-600">失败: {compressionResult.failed}</span>
            </div>
          </div>
        {:else}
          <CircleX class="w-8 h-8 text-red-500 shrink-0" />
          <span class="font-semibold text-red-600">压缩失败</span>
        {/if}
      {:else if isRunning}
        <LoaderCircle class="w-8 h-8 text-primary animate-spin shrink-0" />
        <div class="flex-1">
          <div class="flex justify-between text-sm mb-1"><span>{progressText}</span><span>{progress}%</span></div>
          <Progress value={progress} class="h-2" />
        </div>
      {:else}
        <Package class="w-8 h-8 text-muted-foreground/50 shrink-0" />
        <div class="flex-1">
          <span class="text-muted-foreground">等待扫描</span>
          <div class="text-xs text-muted-foreground/70 mt-1">扫描完成后可开始压缩</div>
        </div>
      {/if}
    </div>
  {:else}
    {#if compressionResult}
      <div class="flex items-center gap-2 text-xs">
        {#if compressionResult.success}
          <CircleCheck class="w-4 h-4 text-green-500" />
          <span class="text-green-600">成功 {compressionResult.compressed}</span>
        {:else}
          <CircleX class="w-4 h-4 text-red-500" />
          <span class="text-red-600">失败</span>
        {/if}
      </div>
    {:else if isRunning}
      <div class="space-y-1">
        <Progress value={progress} class="h-1.5" />
        <div class="text-xs text-muted-foreground">{progress}%</div>
      </div>
    {:else}
      <label class="flex items-center gap-2 cursor-pointer text-xs">
        <Checkbox id="delete-after-{id}" bind:checked={deleteAfter} disabled={isRunning} class="h-3 w-3" />
        <span class="flex items-center gap-1"><Trash2 class="w-3 h-3 text-orange-500" />删除源</span>
      </label>
    {/if}
  {/if}
{/snippet}


<!-- 文件树区块内容 -->
{#snippet treeBlockContent()}
  {#if isFullscreenRender}
    <div class="h-full flex flex-col overflow-hidden">
      <div class="flex items-center justify-between p-3 border-b bg-muted/30 shrink-0">
        <div class="flex items-center gap-2">
          <FolderTree class="w-5 h-5 text-yellow-500" />
          <span class="font-semibold">文件夹结构</span>
          {#if stats.total > 0}<Badge variant="secondary">{stats.total} 个</Badge>{/if}
        </div>
        <div class="flex gap-2 text-xs">
          <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-green-500"></span>{stats.entire}</span>
          <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-yellow-500"></span>{stats.selective}</span>
          <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-gray-400"></span>{stats.skip}</span>
        </div>
      </div>
      <div class="flex-1 overflow-y-auto p-2">
        {#if folderTree}{@render renderFolderNode(folderTree)}
        {:else}<div class="text-center text-muted-foreground py-8">扫描后显示文件夹结构</div>{/if}
      </div>
    </div>
  {:else}
    <div class="flex items-center justify-between mb-2">
      <span class="text-xs font-semibold flex items-center gap-1">
        <FolderTree class="w-3 h-3 text-yellow-500" />文件树
      </span>
      <div class="flex items-center gap-2 text-[10px]">
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>{stats.entire}</span>
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-yellow-500"></span>{stats.selective}</span>
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-gray-400"></span>{stats.skip}</span>
      </div>
    </div>
    <div class="max-h-40 overflow-y-auto">
      {#if folderTree}{@render renderFolderNode(folderTree)}
      {:else}<div class="text-xs text-muted-foreground text-center py-3">扫描后显示</div>{/if}
    </div>
  {/if}
{/snippet}

<!-- 日志区块内容 -->
{#snippet logBlockContent()}
  {#if isFullscreenRender}
    <div class="h-full flex flex-col">
      <div class="flex items-center justify-between mb-2 shrink-0">
        <span class="font-semibold text-sm">日志</span>
        <Button variant="ghost" size="icon" class="h-6 w-6" onclick={copyLogs}>
          {#if copied}<Check class="h-3 w-3 text-green-500" />{:else}<Copy class="h-3 w-3" />{/if}
        </Button>
      </div>
      <div class="flex-1 overflow-y-auto bg-muted/30 rounded-xl p-2 font-mono text-xs space-y-1">
        {#if logs.length > 0}
          {#each logs.slice(-12) as log}<div class="text-muted-foreground break-all">{log}</div>{/each}
        {:else}<div class="text-muted-foreground text-center py-4">暂无日志</div>{/if}
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
      {#each logs.slice(-4) as log}<div class="text-muted-foreground break-all">{log}</div>{/each}
    </div>
  {/if}
{/snippet}


<!-- ========== 主渲染 ========== -->
<div class="{isFullscreenRender ? 'h-full w-full flex flex-col' : 'min-w-[260px] max-w-[400px]'}">
  {#if !isFullscreenRender}
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}
  
  <NodeWrapper 
    nodeId={id} title="repacku" icon={Package} status={phase} {borderClass} {isFullscreenRender}
    onCompact={() => dashboardGrid?.compact()}
    onResetLayout={() => { gridLayout = [...REPACKU_DEFAULT_GRID_LAYOUT]; dashboardGrid?.applyLayout(gridLayout); saveState(); }}
    nodeType="repacku" currentLayout={gridLayout}
    onApplyLayout={(layout) => { gridLayout = layout; dashboardGrid?.applyLayout(layout); saveState(); }}
  >
    {#snippet children()}
      {#if isFullscreenRender}
        <!-- 全屏模式：GridStack 可拖拽布局 -->
        <div class="h-full overflow-hidden">
          <DashboardGrid bind:this={dashboardGrid} columns={4} cellHeight={80} margin={12} showToolbar={false} onLayoutChange={handleLayoutChange}>
            <!-- 路径输入 + 类型过滤 -->
            {@const pathItem = getLayoutItem('path')}
            <DashboardItem id="path" x={pathItem.x} y={pathItem.y} w={pathItem.w} h={pathItem.h} minW={1} minH={2}>
              <BlockCard id="path" title="目标路径" icon={FolderOpen} iconClass="text-primary" isFullscreen={true}>
                {#snippet children()}
                  {@render pathBlockContent()}
                  <div class="flex items-center gap-2 mb-2"><FileText class="w-4 h-4 text-blue-500" /><span class="text-sm font-medium">文件类型</span></div>
                  {@render typesBlockContent()}
                  <label class="flex items-center gap-2 mt-auto pt-3 border-t cursor-pointer">
                    <Checkbox id="delete-after-fs-{id}" bind:checked={deleteAfter} disabled={isRunning} />
                    <span class="text-sm flex items-center gap-1"><Trash2 class="w-4 h-4 text-orange-500" />压缩后删除源文件</span>
                  </label>
                {/snippet}
              </BlockCard>
            </DashboardItem>
            
            <!-- 操作按钮 -->
            {@const opItem = getLayoutItem('operation')}
            <DashboardItem id="operation" x={opItem.x} y={opItem.y} w={opItem.w} h={opItem.h} minW={1} minH={1}>
              <BlockCard id="operation" title="操作" icon={Play} iconClass="text-green-500" isFullscreen={true}>
                {#snippet children()}{@render operationBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            <!-- 统计数字 -->
            {@const statsItem = getLayoutItem('stats')}
            <DashboardItem id="stats" x={statsItem.x} y={statsItem.y} w={statsItem.w} h={statsItem.h} minW={1} minH={1}>
              <BlockCard id="stats" title="统计" icon={FolderTree} iconClass="text-yellow-500" isFullscreen={true}>
                {#snippet children()}{@render statsBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            <!-- 进度/结果 -->
            {@const progressItem = getLayoutItem('progress')}
            <DashboardItem id="progress" x={progressItem.x} y={progressItem.y} w={progressItem.w} h={progressItem.h} minW={1} minH={1}>
              <BlockCard id="progress" title="状态" icon={Package} iconClass="text-muted-foreground" isFullscreen={true} hideHeader={true}>
                {#snippet children()}{@render progressBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>

            <!-- 文件树预览 -->
            {@const treeItem = getLayoutItem('tree')}
            <DashboardItem id="tree" x={treeItem.x} y={treeItem.y} w={treeItem.w} h={treeItem.h} minW={1} minH={1}>
              <BlockCard id="tree" title="文件夹结构" icon={FolderTree} iconClass="text-yellow-500" isFullscreen={true} fullHeight={true} hideHeader={true}>
                {#snippet children()}{@render treeBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            <!-- 日志 -->
            {@const logItem = getLayoutItem('log')}
            <DashboardItem id="log" x={logItem.x} y={logItem.y} w={logItem.w} h={logItem.h} minW={1} minH={1}>
              <BlockCard id="log" title="日志" icon={Copy} iconClass="text-muted-foreground" isFullscreen={true} fullHeight={true} hideHeader={true}>
                {#snippet children()}{@render logBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
          </DashboardGrid>
        </div>
      {:else}
        <!-- 普通模式：Bento Grid 布局 -->
        <div class="flex-1 overflow-y-auto p-2">
          <div class="grid grid-cols-2 gap-2" style="grid-auto-rows: minmax(auto, max-content);">
            <!-- 路径输入块 -->
            <BlockCard id="path" title="路径" icon={FolderOpen} iconClass="text-primary" class="col-span-2">
              {#snippet children()}{@render pathBlockContent()}{/snippet}
            </BlockCard>
            
            <!-- 类型过滤块 -->
            <BlockCard id="types" title="类型" icon={FileText} iconClass="text-blue-500" class="col-span-1">
              {#snippet children()}{@render typesBlockContent()}{/snippet}
            </BlockCard>
            
            <!-- 操作块 -->
            <BlockCard id="operation" title="操作" icon={Play} iconClass="text-green-500" class="col-span-1">
              {#snippet children()}{@render operationBlockContent()}{/snippet}
            </BlockCard>
            
            <!-- 统计块 -->
            <BlockCard id="stats" title="统计" icon={FolderTree} iconClass="text-yellow-500" class="col-span-1">
              {#snippet children()}{@render statsBlockContent()}{/snippet}
            </BlockCard>
            
            <!-- 进度/状态块 -->
            <BlockCard id="progress" title="状态" icon={Package} iconClass="text-muted-foreground" class="col-span-1">
              {#snippet children()}{@render progressBlockContent()}{/snippet}
            </BlockCard>
            
            <!-- 文件树块 -->
            <BlockCard id="tree" title="文件树" icon={FolderTree} iconClass="text-yellow-500" class="col-span-2" collapsible={true}>
              {#snippet children()}{@render treeBlockContent()}{/snippet}
            </BlockCard>
            
            <!-- 日志块 -->
            {#if logs.length > 0}
              <BlockCard id="log" title="日志" icon={Copy} iconClass="text-muted-foreground" class="col-span-2">
                {#snippet children()}{@render logBlockContent()}{/snippet}
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
