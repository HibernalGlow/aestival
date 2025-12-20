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
  import { Badge } from '$lib/components/ui/badge';

  import { InteractiveHover } from '$lib/components/ui/interactive-hover';
  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { REPACKU_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { getSizeClasses, type SizeMode } from '$lib/utils/sizeUtils';
  import type { FolderNode, CompressionStats } from '$lib/types/repacku';
  import { getModeColorClass, getModeName, countCompressionModes } from './utils';
  import { 
    Play, LoaderCircle, FolderOpen, Clipboard, Package,
    CircleCheck, CircleX, FileArchive, Search, FolderTree,
    Trash2, Copy, Check, Folder, Image, FileText, Video, Music, 
    ChevronRight, ChevronDown, RefreshCw, RotateCcw
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
  }

  // 从 nodeStateStore 恢复状态
  const savedState = getNodeState<RepackuState>(id);

  // 状态初始化
  let path = $state(data?.config?.path ?? '');
  let deleteAfter = $state(data?.config?.delete_after ?? false);
  let phase = $state<Phase>(savedState?.phase ?? 'idle');
  let logs = $state<string[]>(data?.logs ? [...data.logs] : []);
  let hasInputConnection = $state(data?.hasInputConnection ?? false);
  let copied = $state(false);

  let progress = $state(savedState?.progress ?? 0);
  let progressText = $state(savedState?.progressText ?? '');

  // 文件树数据
  let folderTree = $state<FolderNode | null>(savedState?.folderTree ?? null);
  let stats = $state<CompressionStats>({ total: 0, entire: 0, selective: 0, skip: 0 });
  let expandedFolders = $state<Set<string>>(new Set(savedState?.expandedFolders ?? []));

  let analysisResult = $state<AnalysisResult | null>(savedState?.analysisResult ?? null);
  let compressionResult = $state<CompressionResultData | null>(savedState?.compressionResult ?? null);
  let selectedTypes = $state<string[]>(savedState?.selectedTypes ?? []);

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

  const typeOptions = [
    { value: 'image', label: '图片' },
    { value: 'document', label: '文档' },
    { value: 'video', label: '视频' },
    { value: 'audio', label: '音频' }
  ];

  function saveState() {
    setNodeState<RepackuState>(id, {
      phase, progress, progressText, folderTree, analysisResult, compressionResult,
      selectedTypes, expandedFolders: Array.from(expandedFolders)
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

<!-- 类型过滤区块 -->
{#snippet typesBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="flex flex-wrap {c.gap}">
    {#each typeOptions as option}
      <button
        class="{c.px} {c.py} {c.text} {c.rounded} border transition-colors {selectedTypes.includes(option.value) ? 'bg-primary text-primary-foreground border-primary' : 'bg-background border-border hover:border-primary'}"
        onclick={() => toggleType(option.value)} disabled={isRunning}
      >{option.label}</button>
    {/each}
  </div>
  {#if size === 'normal'}
    <label class="flex items-center {c.gap} mt-auto pt-3 border-t cursor-pointer">
      <Checkbox id="delete-after-fs-{id}" bind:checked={deleteAfter} disabled={isRunning} />
      <span class="{c.text} flex items-center gap-1"><Trash2 class={c.icon} />压缩后删除源文件</span>
    </label>
  {/if}
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="flex flex-col {c.gap} {size === 'normal' ? 'flex-1 justify-center' : ''}">
    {#if size === 'normal'}
      <!-- 全屏模式：使用 InteractiveHover 按钮 -->
      {#if phase === 'idle' || phase === 'error'}
        <InteractiveHover text="扫描分析" class="w-full h-12 text-sm" onclick={handleAnalyze} disabled={!canAnalyze}>
          {#snippet icon()}<Search class="h-4 w-4" />{/snippet}
        </InteractiveHover>
      {:else if phase === 'analyzing'}
        <InteractiveHover text="分析中" class="w-full h-12 text-sm" disabled>
          {#snippet icon()}<LoaderCircle class="h-4 w-4 animate-spin" />{/snippet}
        </InteractiveHover>
      {:else if phase === 'analyzed'}
        <InteractiveHover text="开始压缩" class="w-full h-12 text-sm" onclick={handleCompress} disabled={!canCompress}>
          {#snippet icon()}<FileArchive class="h-4 w-4" />{/snippet}
        </InteractiveHover>
      {:else if phase === 'compressing'}
        <InteractiveHover text="压缩中" class="w-full h-12 text-sm" disabled>
          {#snippet icon()}<LoaderCircle class="h-4 w-4 animate-spin" />{/snippet}
        </InteractiveHover>
      {:else if phase === 'completed'}
        <InteractiveHover text="重新开始" class="w-full h-12 text-sm" onclick={handleReset}>
          {#snippet icon()}<Play class="h-4 w-4" />{/snippet}
        </InteractiveHover>
      {/if}
      <!-- 重置按钮常驻 -->
      <Button variant="ghost" class="h-9" onclick={handleReset} disabled={isRunning}>
        <RotateCcw class="h-4 w-4 mr-2" />重置
      </Button>
    {:else}
      <!-- 紧凑模式 -->
      <div class="flex {c.gapSm}">
        {#if phase === 'idle' || phase === 'error'}
          <Button class="flex-1 {c.button}" onclick={handleAnalyze} disabled={!canAnalyze}>
            <Search class="{c.icon} mr-1" />扫描
          </Button>
        {:else if phase === 'analyzing'}
          <Button class="flex-1 {c.button}" disabled>
            <LoaderCircle class="{c.icon} mr-1 animate-spin" />分析中
          </Button>
        {:else if phase === 'analyzed'}
          <Button class="flex-1 {c.button}" onclick={handleCompress} disabled={!canCompress}>
            <FileArchive class="{c.icon} mr-1" />压缩
          </Button>
        {:else if phase === 'compressing'}
          <Button class="flex-1 {c.button}" disabled>
            <LoaderCircle class="{c.icon} mr-1 animate-spin" />压缩中
          </Button>
        {:else if phase === 'completed'}
          <Button class="flex-1 {c.button}" variant="outline" onclick={handleReset}>
            <Play class="{c.icon} mr-1" />重新
          </Button>
        {/if}
        <!-- 重置按钮常驻 -->
        <Button variant="ghost" size="icon" class="{c.buttonIcon}" onclick={handleReset} disabled={isRunning} title="重置">
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
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-green-500/15 to-green-500/5 rounded-xl border border-green-500/20">
        <span class="text-sm text-muted-foreground">整体</span>
        <span class="text-2xl font-bold text-green-600 tabular-nums">{analysisResult?.entireCount ?? '-'}</span>
      </div>
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-yellow-500/15 to-yellow-500/5 rounded-xl border border-yellow-500/20">
        <span class="text-sm text-muted-foreground">选择性</span>
        <span class="text-2xl font-bold text-yellow-600 tabular-nums">{analysisResult?.selectiveCount ?? '-'}</span>
      </div>
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-muted/60 to-muted/30 rounded-xl border border-border/50">
        <span class="text-sm text-muted-foreground">跳过</span>
        <span class="text-2xl font-bold text-gray-500 tabular-nums">{analysisResult?.skipCount ?? '-'}</span>
      </div>
    </div>
  {:else}
    <div class="grid grid-cols-3 gap-1.5">
      <div class="text-center p-1.5 bg-green-500/10 rounded-lg">
        <div class="text-sm font-bold text-green-600 tabular-nums">{analysisResult?.entireCount ?? '-'}</div>
        <div class="text-[10px] text-muted-foreground">整体</div>
      </div>
      <div class="text-center p-1.5 bg-yellow-500/10 rounded-lg">
        <div class="text-sm font-bold text-yellow-600 tabular-nums">{analysisResult?.selectiveCount ?? '-'}</div>
        <div class="text-[10px] text-muted-foreground">选择</div>
      </div>
      <div class="text-center p-1.5 bg-muted/40 rounded-lg">
        <div class="text-sm font-bold text-gray-500 tabular-nums">{analysisResult?.skipCount ?? '-'}</div>
        <div class="text-[10px] text-muted-foreground">跳过</div>
      </div>
    </div>
  {/if}
{/snippet}

<!-- 进度/状态区块 -->
{#snippet progressBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if size === 'normal'}
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
      <div class="flex items-center gap-2 {c.text}">
        {#if compressionResult.success}
          <CircleCheck class="{c.icon} text-green-500" />
          <span class="text-green-600">成功 {compressionResult.compressed}</span>
        {:else}
          <CircleX class="{c.icon} text-red-500" />
          <span class="text-red-600">失败</span>
        {/if}
      </div>
    {:else if isRunning}
      <div class={c.spaceSm}>
        <Progress value={progress} class="h-1.5" />
        <div class="{c.text} text-muted-foreground">{progress}%</div>
      </div>
    {:else}
      <label class="flex items-center gap-2 cursor-pointer {c.text}">
        <Checkbox id="delete-after-{id}" bind:checked={deleteAfter} disabled={isRunning} class="h-3 w-3" />
        <span class="flex items-center gap-1"><Trash2 class="{c.iconSm} text-orange-500" />删除源</span>
      </label>
    {/if}
  {/if}
{/snippet}

<!-- 文件树区块 -->
{#snippet treeBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if size === 'normal'}
    <div class="h-full flex flex-col overflow-hidden">
      <div class="flex items-center justify-between p-2 border-b bg-muted/30 shrink-0">
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
      <span class="{c.text} font-semibold flex items-center gap-1">
        <FolderTree class="w-3 h-3 text-yellow-500" />文件树
      </span>
      <div class="flex items-center gap-2 {c.textSm}">
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>{stats.entire}</span>
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-yellow-500"></span>{stats.selective}</span>
        <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-gray-400"></span>{stats.skip}</span>
      </div>
    </div>
    <div class="{c.maxHeight} overflow-y-auto">
      {#if folderTree}{@render renderFolderNode(folderTree)}
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
  {#if blockId === 'path'}{@render pathBlock(size)}{@render typesBlock(size)}
  {:else if blockId === 'types'}{@render typesBlock(size)}
  {:else if blockId === 'operation'}{@render operationBlock(size)}
  {:else if blockId === 'stats'}{@render statsBlock(size)}
  {:else if blockId === 'progress'}{@render progressBlock(size)}
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
        nodeId={id}
        nodeType="repacku"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={REPACKU_DEFAULT_GRID_LAYOUT}
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
