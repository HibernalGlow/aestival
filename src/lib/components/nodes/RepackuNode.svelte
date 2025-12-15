<script lang="ts">
  /**
   * RepackuNode - 文件重打包节点组件
   * 支持文件树预览和 Bento Grid 全屏布局
   */
  import { Handle, Position } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Label } from '$lib/components/ui/label';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';
  import { Badge } from '$lib/components/ui/badge';
  import * as TreeView from '$lib/components/ui/tree-view';
  import * as BentoGrid from '$lib/components/ui/bento-grid';
  import { api } from '$lib/services/api';
  import NodeWrapper from './NodeWrapper.svelte';
  import type { FolderNode, CompressionStats, FolderCard } from '$lib/types/repacku';
  import { 
    getModeColorClass, getModeTextColorClass, getModeName, 
    countCompressionModes, flattenTreeToCards, calculateCardSpan,
    getFileTypeIconName
  } from './repacku-utils';
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
  
  let path = data?.config?.path ?? '';
  let deleteAfter = data?.config?.delete_after ?? false;
  let phase: Phase = 'idle';
  let logs: string[] = data?.logs ? [...data.logs] : [];
  let hasInputConnection = data?.hasInputConnection ?? false;
  let showTree = data?.showTree ?? true;
  
  let progress = 0;
  let progressText = '';
  
  // 文件树数据
  let folderTree: FolderNode | null = null;
  let stats: CompressionStats = { total: 0, entire: 0, selective: 0, skip: 0 };
  let expandedFolders: Set<string> = new Set();
  
  // Bento Grid 卡片数据
  let bentoCards: FolderCard[] = [];
  let expandedCards: Set<string> = new Set();
  
  let analysisResult: {
    configPath: string;
    totalFolders: number;
    entireCount: number;
    selectiveCount: number;
    skipCount: number;
    folderTree?: FolderNode;
  } | null = null;
  
  let compressionResult: {
    success: boolean;
    compressed: number;
    failed: number;
    total: number;
  } | null = null;

  const typeOptions = [
    { value: 'image', label: '图片' },
    { value: 'document', label: '文档' },
    { value: 'video', label: '视频' },
    { value: 'audio', label: '音频' }
  ];
  
  let selectedTypes: string[] = [];

  $: canAnalyze = phase === 'idle' && (path.trim() !== '' || hasInputConnection);
  $: canCompress = phase === 'analyzed' && analysisResult !== null;
  $: isRunning = phase === 'analyzing' || phase === 'compressing';
  
  $: borderClass = {
    idle: 'border-border',
    analyzing: 'border-primary shadow-sm',
    analyzed: 'border-primary/50',
    compressing: 'border-primary shadow-sm',
    completed: 'border-primary/50',
    error: 'border-destructive/50'
  }[phase];

  // 当 folderTree 更新时，重新计算统计和卡片
  $: if (folderTree) {
    stats = countCompressionModes(folderTree);
    bentoCards = flattenTreeToCards(folderTree, 2);
  }

  function toggleFolder(path: string) {
    if (expandedFolders.has(path)) {
      expandedFolders.delete(path);
    } else {
      expandedFolders.add(path);
    }
    expandedFolders = new Set(expandedFolders);
  }

  function toggleCard(path: string) {
    if (expandedCards.has(path)) {
      expandedCards.delete(path);
    } else {
      expandedCards.add(path);
    }
    expandedCards = new Set(expandedCards);
  }

  async function selectFolder() {
    try {
      if (window.pywebview?.api?.open_folder_dialog) {
        const selected = await window.pywebview.api.open_folder_dialog();
        if (selected) path = selected;
      } else {
        logs = [...logs, '⚠️ 文件夹选择功能需要在桌面应用中使用'];
      }
    } catch (e) {
      logs = [...logs, `选择文件夹失败: ${e}`];
    }
  }

  async function pasteFromClipboard() {
    try {
      if (window.pywebview?.api?.read_clipboard) {
        const text = await window.pywebview.api.read_clipboard();
        if (text) path = text.trim();
      } else {
        const text = await navigator.clipboard.readText();
        path = text.trim();
      }
    } catch (e) {
      logs = [...logs, `读取剪贴板失败: ${e}`];
    }
  }

  function toggleType(type: string) {
    if (selectedTypes.includes(type)) {
      selectedTypes = selectedTypes.filter(t => t !== type);
    } else {
      selectedTypes = [...selectedTypes, type];
    }
  }

  async function handleAnalyze() {
    if (!canAnalyze) return;
    phase = 'analyzing';
    progress = 0;
    progressText = '正在扫描目录结构...';
    analysisResult = null;
    compressionResult = null;
    folderTree = null;
    logs = [...logs, `🔍 开始分析目录: ${path}`];
    if (selectedTypes.length > 0) logs = [...logs, `📋 类型过滤: ${selectedTypes.join(', ')}`];
    
    try {
      progress = 30;
      progressText = '正在分析文件类型分布...';
      const response = await api.executeNode('repacku', {
        action: 'analyze', path, types: selectedTypes.length > 0 ? selectedTypes : [], display_tree: true
      }) as any;
      
      if (response.success && response.data) {
        phase = 'analyzed';
        progress = 100;
        progressText = '分析完成';
        folderTree = response.data.folder_tree || null;
        analysisResult = {
          configPath: response.data.config_path ?? '',
          totalFolders: response.data.total_folders ?? 0,
          entireCount: response.data.entire_count ?? 0,
          selectiveCount: response.data.selective_count ?? 0,
          skipCount: response.data.skip_count ?? 0,
          folderTree: response.data.folder_tree
        };
        logs = [...logs, `✅ 分析完成`, `📊 整体压缩: ${analysisResult.entireCount}, 选择性: ${analysisResult.selectiveCount}, 跳过: ${analysisResult.skipCount}`];
      } else {
        phase = 'error';
        progress = 0;
        logs = [...logs, `❌ 分析失败: ${response.message}`];
      }
    } catch (error) {
      phase = 'error';
      progress = 0;
      logs = [...logs, `❌ 分析失败: ${error}`];
    }
  }

  async function handleCompress() {
    if (!canCompress || !analysisResult) return;
    phase = 'compressing';
    progress = 0;
    progressText = '正在压缩文件...';
    logs = [...logs, `📦 开始压缩...`];
    
    try {
      progress = 20;
      const response = await api.executeNode('repacku', {
        action: 'compress', config_path: analysisResult.configPath, delete_after: deleteAfter
      }) as any;
      
      if (response.success) {
        phase = 'completed';
        progress = 100;
        progressText = '压缩完成';
        compressionResult = {
          success: true,
          compressed: response.data?.compressed_count ?? 0,
          failed: response.data?.failed_count ?? 0,
          total: response.data?.total_folders ?? 0
        };
        logs = [...logs, `✅ ${response.message}`, `📊 成功: ${compressionResult.compressed}, 失败: ${compressionResult.failed}`];
      } else {
        phase = 'error';
        progress = 0;
        logs = [...logs, `❌ 压缩失败: ${response.message}`];
      }
    } catch (error) {
      phase = 'error';
      progress = 0;
      logs = [...logs, `❌ 压缩失败: ${error}`];
    }
  }

  function handleReset() {
    phase = 'idle';
    progress = 0;
    progressText = '';
    analysisResult = null;
    compressionResult = null;
    folderTree = null;
    logs = [];
    expandedFolders.clear();
    expandedCards.clear();
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(logs.join('\n'));
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) {
      console.error('复制失败:', e);
    }
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
      role="button"
      tabindex="0"
    >
      <!-- 展开/折叠图标 -->
      {#if hasChildren}
        {#if isExpanded}
          <ChevronDown class="w-3 h-3 text-muted-foreground shrink-0" />
        {:else}
          <ChevronRight class="w-3 h-3 text-muted-foreground shrink-0" />
        {/if}
      {:else}
        <span class="w-3 h-3 shrink-0"></span>
      {/if}
      
      <!-- 文件夹图标 -->
      <Folder class="w-3 h-3 text-yellow-500 shrink-0" />
      
      <!-- 压缩模式指示器 -->
      <span class="w-2 h-2 rounded-full shrink-0 {modeColor}" title={modeText}></span>
      
      <!-- 文件夹名称 -->
      <span class="truncate flex-1" title={node.name}>{node.name}</span>
      
      <!-- 文件数量 -->
      <span class="text-muted-foreground shrink-0">{node.total_files}</span>
      
      <!-- 文件类型徽章 -->
      {#if node.dominant_types && node.dominant_types.length > 0}
        <div class="flex gap-0.5 shrink-0">
          {#each node.dominant_types.slice(0, 2) as type}
            {@const IconComponent = getFileTypeIcon(type)}
            <IconComponent class="w-3 h-3 text-muted-foreground" />
          {/each}
        </div>
      {/if}
    </div>
    
    <!-- 子节点 -->
    {#if hasChildren && isExpanded}
      {#each node.children as child}
        {@render renderFolderNode(child, depth + 1)}
      {/each}
    {/if}
  </div>
{/snippet}

<!-- Bento Grid 卡片渲染 -->
{#snippet renderBentoCard(card: FolderCard)}
  {@const node = card.node}
  {@const isExpanded = expandedCards.has(node.path)}
  {@const modeColor = getModeColorClass(node.compress_mode)}
  {@const modeTextColor = getModeTextColorClass(node.compress_mode)}
  {@const modeText = getModeName(node.compress_mode)}
  
  <BentoGrid.Card 
    colSpan={card.colSpan} 
    rowSpan={card.rowSpan}
    clickable={card.hasChildren}
    onclick={() => card.hasChildren && toggleCard(node.path)}
    class="relative overflow-hidden"
  >
    <!-- 压缩模式指示条 -->
    <div class="absolute top-0 left-0 right-0 h-1 {modeColor}"></div>
    
    <!-- 卡片内容 -->
    <div class="pt-2">
      <!-- 头部：文件夹名和展开图标 -->
      <div class="flex items-center gap-2 mb-2">
        <Folder class="w-5 h-5 text-yellow-500 shrink-0" />
        <span class="font-medium truncate flex-1" title={node.name}>{node.name}</span>
        {#if card.hasChildren}
          {#if isExpanded}
            <ChevronDown class="w-4 h-4 text-muted-foreground" />
          {:else}
            <ChevronRight class="w-4 h-4 text-muted-foreground" />
          {/if}
        {/if}
      </div>
      
      <!-- 统计信息 -->
      <div class="flex items-center gap-3 text-sm text-muted-foreground mb-2">
        <span>{node.total_files} 文件</span>
        <span class={modeTextColor}>{modeText}</span>
      </div>
      
      <!-- 文件类型分布 -->
      {#if node.dominant_types && node.dominant_types.length > 0}
        <div class="flex flex-wrap gap-1">
          {#each node.dominant_types as type}
            {@const IconComponent = getFileTypeIcon(type)}
            <Badge variant="secondary" class="text-xs gap-1">
              <IconComponent class="w-3 h-3" />
              {type}
            </Badge>
          {/each}
        </div>
      {/if}
      
      <!-- 展开的子文件夹 -->
      {#if isExpanded && node.children && node.children.length > 0}
        <div class="mt-3 pt-3 border-t space-y-2">
          {#each node.children as child}
            <div class="flex items-center gap-2 text-sm p-2 rounded bg-muted/30">
              <span class="w-2 h-2 rounded-full shrink-0 {getModeColorClass(child.compress_mode)}"></span>
              <Folder class="w-4 h-4 text-yellow-500 shrink-0" />
              <span class="truncate flex-1">{child.name}</span>
              <span class="text-muted-foreground">{child.total_files}</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </BentoGrid.Card>
{/snippet}

<div class="{isFullscreenRender ? 'h-full w-full flex flex-col' : 'min-w-[260px] max-w-[400px]'}">
  {#if !isFullscreenRender}
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}
  
  <NodeWrapper nodeId={id} title="repacku" icon={Package} status={phase} {borderClass} {isFullscreenRender}>
    {#snippet headerExtra()}
      <Button variant="ghost" size="icon" class="h-6 w-6" onclick={() => showTree = !showTree} title="文件树">
        {#if showTree}<PanelRightClose class="h-3 w-3" />{:else}<PanelRightOpen class="h-3 w-3" />{/if}
      </Button>
    {/snippet}
    
    {#snippet children()}
      {#if isFullscreenRender}
        <!-- 全屏模式：Bento Grid 便当盒布局 - 错位组合 -->
        <div class="h-full overflow-y-auto p-4">
          <div class="grid grid-cols-4 gap-4" style="grid-auto-rows: minmax(80px, auto);">
            
            <!-- 左侧大卡片: 路径输入 + 类型过滤 (占2列3行，竖向) -->
            <div class="col-span-2 row-span-3 bg-card rounded-3xl border p-6 shadow-sm flex flex-col">
              <!-- 路径输入 -->
              <div class="mb-6">
                <div class="flex items-center gap-2 mb-3">
                  <FolderOpen class="w-5 h-5 text-primary" />
                  <span class="font-semibold">目标路径</span>
                </div>
                {#if !hasInputConnection}
                  <div class="flex gap-2">
                    <Input bind:value={path} placeholder="输入或选择文件夹路径..." disabled={isRunning} class="flex-1 h-10" />
                    <Button variant="outline" size="icon" class="h-10 w-10 shrink-0" onclick={selectFolder} disabled={isRunning}>
                      <FolderOpen class="h-4 w-4" />
                    </Button>
                    <Button variant="outline" size="icon" class="h-10 w-10 shrink-0" onclick={pasteFromClipboard} disabled={isRunning}>
                      <Clipboard class="h-4 w-4" />
                    </Button>
                  </div>
                {:else}
                  <div class="text-muted-foreground p-3 bg-muted rounded-xl flex items-center gap-2">
                    <span>←</span><span>输入来自上游节点</span>
                  </div>
                {/if}
              </div>
              
              <!-- 文件类型过滤 -->
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-3">
                  <FileText class="w-5 h-5 text-blue-500" />
                  <span class="font-semibold">文件类型</span>
                  <span class="text-xs text-muted-foreground">(留空全部)</span>
                </div>
                <div class="flex flex-wrap gap-2">
                  {#each typeOptions as option}
                    <button
                      class="px-4 py-2.5 text-sm rounded-xl border transition-all {selectedTypes.includes(option.value) ? 'bg-primary text-primary-foreground border-primary shadow-sm' : 'bg-background border-border hover:border-primary'}"
                      onclick={() => toggleType(option.value)}
                      disabled={isRunning}
                    >{option.label}</button>
                  {/each}
                </div>
              </div>
              
              <!-- 选项 -->
              <div class="pt-4 border-t mt-4">
                <label class="flex items-center gap-3 cursor-pointer">
                  <Checkbox id="delete-after-fs-{id}" bind:checked={deleteAfter} disabled={isRunning} />
                  <span class="text-sm flex items-center gap-1"><Trash2 class="w-4 h-4 text-orange-500" />压缩后删除源文件</span>
                </label>
              </div>
            </div>
            
            <!-- 右上: 操作按钮 (占1列2行，高卡片) -->
            <div class="col-span-1 row-span-2 bg-card rounded-3xl border p-5 shadow-sm flex flex-col">
              <div class="flex items-center gap-2 mb-4">
                <Play class="w-5 h-5 text-green-500" />
                <span class="font-semibold">操作</span>
              </div>
              <div class="flex flex-col gap-3 flex-1 justify-center">
                {#if phase === 'idle' || phase === 'error'}
                  <Button class="h-14 text-base" onclick={handleAnalyze} disabled={!canAnalyze}>
                    <Search class="h-5 w-5 mr-2" />扫描分析
                  </Button>
                {:else if phase === 'analyzing'}
                  <Button class="h-14 text-base" disabled>
                    <LoaderCircle class="h-5 w-5 mr-2 animate-spin" />分析中...
                  </Button>
                {:else if phase === 'analyzed'}
                  <Button class="h-14 text-base" onclick={handleCompress} disabled={!canCompress}>
                    <FileArchive class="h-5 w-5 mr-2" />开始压缩
                  </Button>
                  <Button variant="outline" class="h-10" onclick={handleReset}>重置</Button>
                {:else if phase === 'compressing'}
                  <Button class="h-14 text-base" disabled>
                    <LoaderCircle class="h-5 w-5 mr-2 animate-spin" />压缩中...
                  </Button>
                {:else if phase === 'completed'}
                  <Button class="h-14 text-base" variant="outline" onclick={handleReset}>
                    <Play class="h-5 w-5 mr-2" />重新开始
                  </Button>
                {/if}
              </div>
            </div>
            
            <!-- 右上角: 统计数字 (占1列2行) -->
            <div class="col-span-1 row-span-2 bg-card rounded-3xl border p-5 shadow-sm">
              <div class="flex items-center gap-2 mb-3">
                <FolderTree class="w-5 h-5 text-yellow-500" />
                <span class="font-semibold">统计</span>
              </div>
              <div class="space-y-3">
                <div class="flex items-center justify-between p-3 bg-green-500/10 rounded-xl">
                  <span class="text-sm">整体压缩</span>
                  <span class="text-2xl font-bold text-green-600">{analysisResult?.entireCount ?? '-'}</span>
                </div>
                <div class="flex items-center justify-between p-3 bg-yellow-500/10 rounded-xl">
                  <span class="text-sm">选择性</span>
                  <span class="text-2xl font-bold text-yellow-600">{analysisResult?.selectiveCount ?? '-'}</span>
                </div>
                <div class="flex items-center justify-between p-3 bg-gray-500/10 rounded-xl">
                  <span class="text-sm">跳过</span>
                  <span class="text-2xl font-bold text-gray-500">{analysisResult?.skipCount ?? '-'}</span>
                </div>
              </div>
            </div>
            
            <!-- 进度/结果卡片 (占2列1行，始终显示) -->
            <div class="col-span-2 row-span-1 bg-card rounded-3xl border p-4 shadow-sm">
              <div class="flex items-center gap-3">
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
                    <div class="flex justify-between text-sm mb-1">
                      <span>{progressText}</span>
                      <span>{progress}%</span>
                    </div>
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
            </div>
            
            <!-- 文件树预览 (占3列，高度自适应) -->
            <div class="col-span-3 row-span-4 bg-card rounded-3xl border shadow-sm overflow-hidden">
              <div class="flex items-center justify-between p-4 border-b bg-muted/30">
                <div class="flex items-center gap-2">
                  <FolderTree class="w-5 h-5 text-yellow-500" />
                  <span class="font-semibold">文件夹结构</span>
                  {#if stats.total > 0}
                    <Badge variant="secondary">{stats.total} 个</Badge>
                  {/if}
                </div>
                <div class="flex gap-3 text-xs">
                  <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-green-500"></span>{stats.entire}</span>
                  <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-yellow-500"></span>{stats.selective}</span>
                  <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-gray-400"></span>{stats.skip}</span>
                </div>
              </div>
              <div class="p-3 overflow-y-auto" style="max-height: 350px;">
                {#if folderTree}
                  {@render renderFolderNode(folderTree)}
                {:else}
                  <div class="text-center text-muted-foreground py-8">扫描后显示文件夹结构</div>
                {/if}
              </div>
            </div>
            
            <!-- 日志卡片 (占1列，竖向) -->
            <div class="col-span-1 row-span-4 bg-card rounded-3xl border p-4 shadow-sm flex flex-col">
              <div class="flex items-center justify-between mb-2 shrink-0">
                <span class="font-semibold text-sm">日志</span>
                <Button variant="ghost" size="icon" class="h-6 w-6" onclick={copyLogs}>
                  {#if copied}<Check class="h-3 w-3 text-green-500" />{:else}<Copy class="h-3 w-3" />{/if}
                </Button>
              </div>
              <div class="flex-1 overflow-y-auto bg-muted/30 rounded-xl p-2 font-mono text-xs space-y-1">
                {#if logs.length > 0}
                  {#each logs.slice(-12) as log}
                    <div class="text-muted-foreground break-all">{log}</div>
                  {/each}
                {:else}
                  <div class="text-muted-foreground text-center py-4">暂无日志</div>
                {/if}
              </div>
            </div>
            
          </div>
        </div>
      {:else}
        <!-- 普通模式：左右分栏 -->
        <div class="flex flex-1 min-h-0 overflow-hidden">
          <!-- 左侧：控制面板 -->
          <div class="flex flex-col p-3 space-y-2 {showTree ? 'w-1/2 border-r' : 'flex-1'} overflow-y-auto">
            <!-- 路径输入区域 -->
            {#if !hasInputConnection}
              <div class="space-y-1">
                <Label class="text-xs text-muted-foreground">目标路径</Label>
                <div class="flex gap-1">
                  <Input bind:value={path} placeholder="输入或选择文件夹路径..." disabled={isRunning} class="flex-1 h-7 text-xs" />
                  <Button variant="outline" size="icon" class="h-7 w-7 shrink-0" onclick={selectFolder} disabled={isRunning} title="选择文件夹">
                    <FolderOpen class="h-3 w-3" />
                  </Button>
                  <Button variant="outline" size="icon" class="h-7 w-7 shrink-0" onclick={pasteFromClipboard} disabled={isRunning} title="从剪贴板粘贴">
                    <Clipboard class="h-3 w-3" />
                  </Button>
                </div>
              </div>
            {:else}
              <div class="text-xs text-muted-foreground p-2 bg-muted rounded flex items-center gap-2">
                <span>←</span><span>输入来自上游节点</span>
              </div>
            {/if}
            
            <!-- 文件类型过滤 -->
            <div class="space-y-1">
              <Label class="text-xs text-muted-foreground">文件类型过滤</Label>
              <div class="flex flex-wrap gap-1">
                {#each typeOptions as option}
                  <button
                    class="px-2 py-0.5 text-xs rounded border transition-colors {selectedTypes.includes(option.value) ? 'bg-primary text-primary-foreground border-primary' : 'bg-background border-border hover:border-primary'}"
                    onclick={() => toggleType(option.value)}
                    disabled={isRunning}
                  >{option.label}</button>
                {/each}
              </div>
            </div>
            
            <!-- 选项 -->
            <div class="flex items-center gap-2">
              <Checkbox id="delete-after-{id}" bind:checked={deleteAfter} disabled={isRunning} />
              <Label for="delete-after-{id}" class="text-xs cursor-pointer flex items-center gap-1">
                <Trash2 class="w-3 h-3" />压缩后删除源文件
              </Label>
            </div>
            
            <!-- 进度条 -->
            {#if isRunning}
              <div class="space-y-1">
                <div class="flex justify-between text-xs text-muted-foreground"><span>{progressText}</span><span>{progress}%</span></div>
                <Progress value={progress} class="h-1.5" />
              </div>
            {/if}
            
            <!-- 分析结果统计 -->
            {#if analysisResult && phase !== 'idle'}
              <div class="p-2 rounded bg-muted space-y-1">
                <div class="flex items-center gap-2 text-xs font-medium"><FolderTree class="w-3 h-3 text-yellow-500" /><span>分析结果</span></div>
                <div class="grid grid-cols-3 gap-1 text-xs">
                  <div class="text-center p-1 bg-background rounded"><div class="font-semibold text-green-600">{analysisResult.entireCount}</div><div class="text-muted-foreground">整体</div></div>
                  <div class="text-center p-1 bg-background rounded"><div class="font-semibold text-yellow-600">{analysisResult.selectiveCount}</div><div class="text-muted-foreground">选择性</div></div>
                  <div class="text-center p-1 bg-background rounded"><div class="font-semibold text-gray-500">{analysisResult.skipCount}</div><div class="text-muted-foreground">跳过</div></div>
                </div>
              </div>
            {/if}
            
            <!-- 压缩结果 -->
            {#if compressionResult}
              <div class="p-2 rounded bg-muted space-y-1">
                <div class="flex items-center gap-2 text-xs">
                  {#if compressionResult.success}<CircleCheck class="w-3 h-3 text-green-500" /><span class="text-green-600">压缩完成</span>
                  {:else}<CircleX class="w-3 h-3 text-red-500" /><span class="text-red-600">压缩失败</span>{/if}
                </div>
                <div class="grid grid-cols-2 gap-1 text-xs">
                  <div class="text-center p-1 bg-background rounded"><div class="font-semibold text-green-600">{compressionResult.compressed}</div><div class="text-muted-foreground">成功</div></div>
                  <div class="text-center p-1 bg-background rounded"><div class="font-semibold text-red-600">{compressionResult.failed}</div><div class="text-muted-foreground">失败</div></div>
                </div>
              </div>
            {/if}
            
            <!-- 操作按钮 -->
            <div class="flex gap-1">
              {#if phase === 'idle' || phase === 'error'}
                <Button class="flex-1 h-7 text-xs" onclick={handleAnalyze} disabled={!canAnalyze}><Search class="h-3 w-3 mr-1" />扫描</Button>
              {:else if phase === 'analyzing'}
                <Button class="flex-1 h-7 text-xs" disabled><LoaderCircle class="h-3 w-3 mr-1 animate-spin" />分析中</Button>
              {:else if phase === 'analyzed'}
                <Button class="flex-1 h-7 text-xs" onclick={handleCompress} disabled={!canCompress}><FileArchive class="h-3 w-3 mr-1" />压缩</Button>
                <Button variant="outline" class="h-7 text-xs" onclick={handleReset}>重置</Button>
              {:else if phase === 'compressing'}
                <Button class="flex-1 h-7 text-xs" disabled><LoaderCircle class="h-3 w-3 mr-1 animate-spin" />压缩中</Button>
              {:else if phase === 'completed'}
                <Button class="flex-1 h-7 text-xs" variant="outline" onclick={handleReset}><Play class="h-3 w-3 mr-1" />重新开始</Button>
              {/if}
            </div>
            
            <!-- 日志输出 -->
            {#if logs.length > 0}
              <div class="relative">
                <div class="absolute top-1 right-1 z-10">
                  <Button variant="ghost" size="icon" class="h-5 w-5 opacity-60 hover:opacity-100" onclick={copyLogs} title="复制日志">
                    {#if copied}<Check class="h-2 w-2 text-green-500" />{:else}<Copy class="h-2 w-2" />{/if}
                  </Button>
                </div>
                <div class="p-1.5 pr-6 bg-muted rounded text-xs font-mono max-h-16 overflow-y-auto space-y-0.5 select-text cursor-text">
                  {#each logs.slice(-4) as log}<div class="text-muted-foreground break-all whitespace-pre-wrap">{log}</div>{/each}
                </div>
              </div>
            {/if}
          </div>
          
          <!-- 右侧：文件树面板 -->
          {#if showTree}
            <div class="w-1/2 flex flex-col overflow-hidden">
              <div class="text-xs font-medium p-1.5 border-b bg-muted/30 flex items-center justify-between shrink-0">
                <span class="flex items-center gap-1">
                  <FolderTree class="w-3 h-3 text-yellow-500" />
                  文件树
                </span>
                <span class="text-muted-foreground">{stats.total} 项</span>
              </div>
              <div class="flex-1 overflow-y-auto p-1">
                {#if folderTree}
                  {@render renderFolderNode(folderTree)}
                {:else}
                  <div class="text-xs text-muted-foreground text-center py-4">扫描后显示文件树</div>
                {/if}
              </div>
            </div>
          {/if}
        </div>
      {/if}
    {/snippet}
  </NodeWrapper>
  
  {#if !isFullscreenRender}
    <Handle type="source" position={Position.Right} class="bg-primary!" />
  {/if}
</div>
