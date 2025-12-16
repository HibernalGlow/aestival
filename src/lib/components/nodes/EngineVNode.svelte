<script lang="ts">
  /**
   * EngineVNode - Wallpaper Engine 工坊管理节点
   * 使用区块系统，支持普通模式（Bento Grid）和全屏模式（GridStack）
   * 功能：扫描、过滤、预览、批量重命名
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import * as Select from '$lib/components/ui/select';
  import { DashboardGrid, DashboardItem } from '$lib/components/ui/dashboard-grid';
  import type { GridItem } from '$lib/components/ui/dashboard-grid';
  import { BlockCard } from '$lib/components/blocks';
  import { ENGINEV_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import { getDefaultPreset } from '$lib/stores/layoutPresets';
  import NodeWrapper from './NodeWrapper.svelte';
  import { 
    LoaderCircle, FolderOpen, Clipboard, Search, Play, Download,
    Filter, BarChart3, Pencil, Grid3X3, List, Copy, Check,
    Video, Globe, Layers, Image, RefreshCw, Trash2
  } from '@lucide/svelte';
  import {
    type WallpaperItem, type FilterOptions, type EngineVStats, type RenameConfig, type Phase, type EngineVState,
    getPhaseBorderClass, getRatingInfo, getTypeInfo, formatSize, formatDate,
    generateNewName, calculateStats, filterWallpapers, getAllTags,
    DEFAULT_STATS, DEFAULT_FILTERS, DEFAULT_RENAME_CONFIG, DEFAULT_GRID_LAYOUT
  } from './enginev-utils';
  
  export let id: string;
  export let data: { config?: { path?: string }; logs?: string[] } = {};
  export let isFullscreenRender = false;
  
  // 从 nodeStateStore 恢复状态
  const savedState = getNodeState<EngineVState>(id);
  
  // 状态初始化
  let phase: Phase = savedState?.phase ?? 'idle';
  let logs: string[] = savedState?.logs ?? (data?.logs ? [...data.logs] : []);
  let copied = false;

  // 配置
  let workshopPath = savedState?.workshopPath ?? data?.config?.path ?? '';
  
  // 数据
  let wallpapers: WallpaperItem[] = savedState?.wallpapers ?? [];
  let filteredWallpapers: WallpaperItem[] = savedState?.filteredWallpapers ?? [];
  let stats: EngineVStats = savedState?.stats ?? { ...DEFAULT_STATS };
  let filters: FilterOptions = savedState?.filters ?? { ...DEFAULT_FILTERS };
  let renameConfig: RenameConfig = savedState?.renameConfig ?? { ...DEFAULT_RENAME_CONFIG };
  let selectedIds: Set<string> = new Set(savedState?.selectedIds ?? []);
  let viewMode: 'grid' | 'list' = savedState?.viewMode ?? 'grid';
  let allTags: string[] = [];
  
  // GridStack 布局
  function getInitialLayout(): GridItem[] {
    if (savedState?.gridLayout) return savedState.gridLayout;
    const defaultPreset = getDefaultPreset('enginev');
    if (defaultPreset) return [...defaultPreset.layout];
    return [...ENGINEV_DEFAULT_GRID_LAYOUT];
  }
  let gridLayout: GridItem[] = getInitialLayout();
  
  let dashboardGrid: { compact: () => void; applyLayout: (layout: GridItem[]) => void } | undefined;

  function handleLayoutChange(newLayout: GridItem[]) { gridLayout = newLayout; saveState(); }
  function getLayoutItem(itemId: string): GridItem {
    return gridLayout.find(item => item.id === itemId) ?? { id: itemId, x: 0, y: 0, w: 1, h: 1 };
  }
  
  function saveState() {
    setNodeState<EngineVState>(id, {
      phase, logs, workshopPath, wallpapers, filteredWallpapers, stats, filters, renameConfig,
      gridLayout, selectedIds, viewMode
    });
  }
  
  $: if (phase || wallpapers || filteredWallpapers || stats || gridLayout) saveState();
  $: isRunning = phase === 'scanning' || phase === 'renaming';
  $: borderClass = getPhaseBorderClass(phase);

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  async function selectFolder() {
    try {
      const { platform } = await import('$lib/api/platform');
      const s = await platform.openFolderDialog('选择 Wallpaper Engine 工坊目录');
      if (s) workshopPath = s;
    } catch (e) { log(`选择失败: ${e}`); }
  }

  async function pastePath() {
    try { workshopPath = (await navigator.clipboard.readText()).trim(); } catch (e) { log(`粘贴失败: ${e}`); }
  }

  async function handleScan() {
    if (!workshopPath.trim()) { log('❌ 请输入工坊路径'); return; }
    phase = 'scanning'; log(`🔍 扫描: ${workshopPath}`);
    try {
      const r = await api.executeNode('enginev', {
        action: 'scan', workshop_path: workshopPath
      }) as any;
      if (r.success && r.data) {
        wallpapers = r.data.wallpapers || [];
        filteredWallpapers = [...wallpapers];
        stats = calculateStats(wallpapers, filteredWallpapers);
        allTags = getAllTags(wallpapers);
        phase = 'ready';
        log(`✅ 扫描完成: ${wallpapers.length} 个壁纸`);
      } else { phase = 'error'; log(`❌ ${r.message}`); }
    } catch (e) { phase = 'error'; log(`❌ ${e}`); }
  }

  function applyFilters() {
    filteredWallpapers = filterWallpapers(wallpapers, filters);
    stats = calculateStats(wallpapers, filteredWallpapers);
    log(`🔍 过滤: ${filteredWallpapers.length}/${wallpapers.length}`);
  }

  function clearFilters() {
    filters = { ...DEFAULT_FILTERS };
    filteredWallpapers = [...wallpapers];
    stats = calculateStats(wallpapers, filteredWallpapers);
    log('🗑️ 已清空过滤条件');
  }

  async function handleRename() {
    const targets = selectedIds.size > 0 
      ? filteredWallpapers.filter(w => selectedIds.has(w.workshop_id))
      : filteredWallpapers;
    if (targets.length === 0) { log('❌ 无可重命名项'); return; }
    
    phase = 'renaming'; 
    log(`${renameConfig.dryRun ? '🔍 模拟' : '▶️ 执行'}重命名 ${targets.length} 项...`);
    try {
      const r = await api.executeNode('enginev', {
        action: 'rename',
        workshop_ids: targets.map(w => w.workshop_id),
        template: renameConfig.template,
        desc_max_length: renameConfig.descMaxLength,
        name_max_length: renameConfig.nameMaxLength,
        dry_run: renameConfig.dryRun,
        copy_mode: renameConfig.copyMode,
        target_path: renameConfig.targetPath
      }) as any;
      if (r.success) {
        phase = 'completed';
        log(`✅ 成功 ${r.data?.success_count || 0} 失败 ${r.data?.failed_count || 0}`);
      } else { phase = 'error'; log(`❌ ${r.message}`); }
    } catch (e) { phase = 'error'; log(`❌ ${e}`); }
  }

  async function exportData(format: 'json' | 'paths') {
    const targets = selectedIds.size > 0 
      ? filteredWallpapers.filter(w => selectedIds.has(w.workshop_id))
      : filteredWallpapers;
    if (targets.length === 0) { log('❌ 无可导出项'); return; }
    
    try {
      const content = format === 'json' 
        ? JSON.stringify(targets, null, 2)
        : targets.map(w => w.path).join('\n');
      const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `enginev_export_${Date.now()}.${format === 'json' ? 'json' : 'txt'}`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
      log(`💾 已导出 ${targets.length} 项 (${format})`);
    } catch (e) { log(`导出失败: ${e}`); }
  }

  function toggleSelect(workshopId: string) {
    if (selectedIds.has(workshopId)) {
      selectedIds.delete(workshopId);
    } else {
      selectedIds.add(workshopId);
    }
    selectedIds = new Set(selectedIds);
  }

  function selectAll() {
    selectedIds = new Set(filteredWallpapers.map(w => w.workshop_id));
  }

  function clearSelection() {
    selectedIds = new Set();
  }
  
  function clear() {
    wallpapers = []; filteredWallpapers = []; selectedIds = new Set();
    stats = { ...DEFAULT_STATS }; phase = 'idle';
    log('🗑️ 已清空');
  }
  
  async function copyLogs() { 
    try { await navigator.clipboard.writeText(logs.join('\n')); copied = true; setTimeout(() => copied = false, 2000); } catch {} 
  }

  // 获取类型图标组件
  function getTypeIcon(type: string) {
    switch (type) {
      case 'Video': return Video;
      case 'Web': return Globe;
      case 'Scene': return Layers;
      default: return Image;
    }
  }
</script>


<!-- ========== 区块内容 Snippets ========== -->

<!-- 路径输入区块 -->
{#snippet pathBlockContent()}
  <div class="flex gap-2 {isFullscreenRender ? 'mb-4' : 'mb-2'}">
    <Input bind:value={workshopPath} placeholder="Wallpaper Engine 工坊路径..." disabled={isRunning} class="flex-1 {isFullscreenRender ? 'h-10' : 'h-7 text-xs'}" />
    <Button variant="outline" size="icon" class="{isFullscreenRender ? 'h-10 w-10' : 'h-7 w-7'} shrink-0" onclick={selectFolder} disabled={isRunning}>
      <FolderOpen class="{isFullscreenRender ? 'h-4 w-4' : 'h-3 w-3'}" />
    </Button>
    <Button variant="outline" size="icon" class="{isFullscreenRender ? 'h-10 w-10' : 'h-7 w-7'} shrink-0" onclick={pastePath} disabled={isRunning}>
      <Clipboard class="{isFullscreenRender ? 'h-4 w-4' : 'h-3 w-3'}" />
    </Button>
  </div>
  {#if isFullscreenRender}
    <Button variant="outline" class="w-full h-12" onclick={handleScan} disabled={isRunning}>
      {#if isRunning && phase === 'scanning'}<LoaderCircle class="h-4 w-4 mr-2 animate-spin" />{:else}<RefreshCw class="h-4 w-4 mr-2" />{/if}扫描工坊
    </Button>
  {:else}
    <Button variant="outline" size="sm" class="w-full h-7 text-xs" onclick={handleScan} disabled={isRunning}>
      {#if isRunning && phase === 'scanning'}<LoaderCircle class="h-3 w-3 mr-1 animate-spin" />{/if}扫描
    </Button>
  {/if}
{/snippet}

<!-- 过滤条件区块 -->
{#snippet filterBlockContent()}
  <div class="space-y-{isFullscreenRender ? '3' : '2'}">
    <Input bind:value={filters.title} placeholder="搜索标题..." class="{isFullscreenRender ? 'h-9' : 'h-6 text-xs'}" onchange={applyFilters} />
    <div class="grid grid-cols-2 gap-{isFullscreenRender ? '2' : '1'}">
      <select bind:value={filters.contentrating} onchange={applyFilters} class="h-{isFullscreenRender ? '9' : '6'} text-{isFullscreenRender ? 'sm' : 'xs'} rounded-md border bg-background px-2">
        <option value="">全部评级</option>
        <option value="Everyone">全年龄</option>
        <option value="Mature">成熟</option>
        <option value="Adult">成人</option>
      </select>
      <select bind:value={filters.type} onchange={applyFilters} class="h-{isFullscreenRender ? '9' : '6'} text-{isFullscreenRender ? 'sm' : 'xs'} rounded-md border bg-background px-2">
        <option value="">全部类型</option>
        <option value="Video">视频</option>
        <option value="Scene">场景</option>
        <option value="Web">网页</option>
      </select>
    </div>
    <div class="flex gap-1">
      <Button variant="outline" size="sm" class="flex-1 {isFullscreenRender ? 'h-8' : 'h-6 text-xs'}" onclick={applyFilters}>
        <Filter class="{isFullscreenRender ? 'h-3 w-3' : 'h-2.5 w-2.5'} mr-1" />应用
      </Button>
      <Button variant="ghost" size="sm" class="{isFullscreenRender ? 'h-8' : 'h-6 text-xs'}" onclick={clearFilters}>
        <Trash2 class="{isFullscreenRender ? 'h-3 w-3' : 'h-2.5 w-2.5'}" />
      </Button>
    </div>
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlockContent()}
  {#if isFullscreenRender}
    <div class="space-y-2 flex-1">
      <div class="flex items-center justify-between p-2 bg-muted/50 rounded-lg">
        <span class="text-sm">总计</span><span class="text-xl font-bold">{stats.total}</span>
      </div>
      <div class="flex items-center justify-between p-2 bg-blue-500/10 rounded-lg">
        <span class="text-sm">已过滤</span><span class="text-xl font-bold text-blue-600">{stats.filtered}</span>
      </div>
      <div class="flex items-center justify-between p-2 bg-purple-500/10 rounded-lg">
        <span class="text-sm">已选择</span><span class="text-xl font-bold text-purple-600">{selectedIds.size}</span>
      </div>
    </div>
  {:else}
    <div class="grid grid-cols-3 gap-1 text-xs">
      <div class="text-center p-1.5 bg-muted/50 rounded-lg"><div class="font-bold">{stats.total}</div><div class="text-muted-foreground text-[10px]">总计</div></div>
      <div class="text-center p-1.5 bg-blue-500/10 rounded-lg"><div class="font-bold text-blue-600">{stats.filtered}</div><div class="text-muted-foreground text-[10px]">过滤</div></div>
      <div class="text-center p-1.5 bg-purple-500/10 rounded-lg"><div class="font-bold text-purple-600">{selectedIds.size}</div><div class="text-muted-foreground text-[10px]">选择</div></div>
    </div>
  {/if}
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlockContent()}
  <div class="flex flex-col gap-{isFullscreenRender ? '2' : '1.5'} {isFullscreenRender ? 'flex-1 justify-center' : ''}">
    {#if isFullscreenRender}
      <Button variant={phase === 'ready' ? 'default' : 'outline'} class="h-12" onclick={handleRename} disabled={isRunning || stats.filtered === 0}>
        {#if phase === 'renaming'}<LoaderCircle class="h-4 w-4 mr-2 animate-spin" />{:else}<Pencil class="h-4 w-4 mr-2" />{/if}执行重命名
      </Button>
      <div class="flex gap-2">
        <Button variant="outline" class="flex-1 h-10" onclick={() => exportData('json')} disabled={stats.filtered === 0}>
          <Download class="h-4 w-4 mr-1" />JSON
        </Button>
        <Button variant="outline" class="flex-1 h-10" onclick={() => exportData('paths')} disabled={stats.filtered === 0}>
          <Download class="h-4 w-4 mr-1" />路径
        </Button>
      </div>
      <Button variant="ghost" class="h-10" onclick={clear}><Trash2 class="h-4 w-4 mr-2" />清空</Button>
    {:else}
      <Button class="flex-1 h-7 text-xs" onclick={handleRename} disabled={isRunning || stats.filtered === 0}>
        {#if phase === 'renaming'}<LoaderCircle class="h-3 w-3 mr-1 animate-spin" />{:else}<Pencil class="h-3 w-3 mr-1" />{/if}重命名
      </Button>
      <div class="flex gap-1">
        <Button variant="outline" size="sm" class="flex-1 h-6 text-xs" onclick={() => exportData('json')} disabled={stats.filtered === 0}>JSON</Button>
        <Button variant="outline" size="sm" class="flex-1 h-6 text-xs" onclick={() => exportData('paths')} disabled={stats.filtered === 0}>路径</Button>
      </div>
    {/if}
  </div>
{/snippet}

<!-- 重命名配置区块 -->
{#snippet renameBlockContent()}
  {@const placeholderText = '[#{id}]{original_name}+{title}'}
  {@const helpText = '占位符: {id} {title} {original_name} {type} {rating} {desc}'}
  <div class="space-y-{isFullscreenRender ? '3' : '2'}">
    <div>
      <span class="text-{isFullscreenRender ? 'sm' : 'xs'} text-muted-foreground mb-1 block">命名模板</span>
      <Input bind:value={renameConfig.template} placeholder={placeholderText} class="{isFullscreenRender ? 'h-9' : 'h-6 text-xs'}" />
    </div>
    <div class="flex flex-wrap gap-{isFullscreenRender ? '3' : '2'} text-{isFullscreenRender ? 'sm' : 'xs'}">
      <label class="flex items-center gap-1.5">
        <Checkbox bind:checked={renameConfig.dryRun} class="{isFullscreenRender ? '' : 'h-3 w-3'}" />
        <span>模拟执行</span>
      </label>
      <label class="flex items-center gap-1.5">
        <Checkbox bind:checked={renameConfig.copyMode} class="{isFullscreenRender ? '' : 'h-3 w-3'}" />
        <span>复制模式</span>
      </label>
    </div>
    {#if renameConfig.copyMode}
      <Input bind:value={renameConfig.targetPath} placeholder="目标路径..." class="{isFullscreenRender ? 'h-9' : 'h-6 text-xs'}" />
    {/if}
    <div class="text-{isFullscreenRender ? 'xs' : '[10px]'} text-muted-foreground">
      {helpText}
    </div>
  </div>
{/snippet}


<!-- 壁纸列表区块 -->
{#snippet galleryBlockContent()}
  {#if isFullscreenRender}
    <div class="h-full flex flex-col overflow-hidden">
      <div class="flex items-center justify-between p-2 border-b bg-muted/30 shrink-0">
        <span class="font-semibold flex items-center gap-2"><Grid3X3 class="w-4 h-4 text-purple-500" />壁纸列表</span>
        <div class="flex items-center gap-2">
          <Button variant="ghost" size="sm" class="h-7 px-2 text-xs" onclick={selectAll}>全选</Button>
          <Button variant="ghost" size="sm" class="h-7 px-2 text-xs" onclick={clearSelection}>清除</Button>
          <Button variant="ghost" size="icon" class="h-7 w-7" onclick={() => viewMode = viewMode === 'grid' ? 'list' : 'grid'}>
            {#if viewMode === 'grid'}<List class="h-4 w-4" />{:else}<Grid3X3 class="h-4 w-4" />{/if}
          </Button>
        </div>
      </div>
      <div class="flex-1 overflow-y-auto p-2">
        {#if filteredWallpapers.length > 0}
          {#if viewMode === 'grid'}
            <div class="grid grid-cols-3 gap-2">
              {#each filteredWallpapers.slice(0, 50) as wallpaper}
                {@const isSelected = selectedIds.has(wallpaper.workshop_id)}
                {@const ratingInfo = getRatingInfo(wallpaper.content_rating)}
                <button 
                  class="p-2 rounded-lg border text-left transition-all hover:bg-muted/50 {isSelected ? 'border-primary bg-primary/10' : 'border-border'}"
                  onclick={() => toggleSelect(wallpaper.workshop_id)}
                >
                  <div class="text-sm font-medium truncate" title={wallpaper.title}>{wallpaper.title || wallpaper.folder_name}</div>
                  <div class="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                    <span class={ratingInfo.color}>{ratingInfo.name}</span>
                    <span>{wallpaper.wallpaper_type}</span>
                  </div>
                  <div class="text-xs text-muted-foreground mt-1 truncate">{wallpaper.workshop_id}</div>
                </button>
              {/each}
            </div>
          {:else}
            <div class="space-y-1">
              {#each filteredWallpapers.slice(0, 100) as wallpaper}
                {@const isSelected = selectedIds.has(wallpaper.workshop_id)}
                {@const ratingInfo = getRatingInfo(wallpaper.content_rating)}
                <button 
                  class="w-full p-2 rounded-lg border text-left flex items-center gap-3 transition-all hover:bg-muted/50 {isSelected ? 'border-primary bg-primary/10' : 'border-border'}"
                  onclick={() => toggleSelect(wallpaper.workshop_id)}
                >
                  <Checkbox checked={isSelected} class="shrink-0" />
                  <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium truncate">{wallpaper.title || wallpaper.folder_name}</div>
                    <div class="text-xs text-muted-foreground truncate">{wallpaper.path}</div>
                  </div>
                  <div class="flex items-center gap-2 text-xs shrink-0">
                    <span class={ratingInfo.color}>{ratingInfo.name}</span>
                    <span class="text-muted-foreground">{wallpaper.wallpaper_type}</span>
                    <span class="text-muted-foreground">{formatSize(wallpaper.size)}</span>
                  </div>
                </button>
              {/each}
            </div>
          {/if}
          {#if filteredWallpapers.length > (viewMode === 'grid' ? 50 : 100)}
            <div class="text-center text-sm text-muted-foreground py-4">
              显示前 {viewMode === 'grid' ? 50 : 100} 项，共 {filteredWallpapers.length} 项
            </div>
          {/if}
        {:else}
          <div class="text-center text-muted-foreground py-8">扫描后显示壁纸列表</div>
        {/if}
      </div>
    </div>
  {:else}
    <div class="flex items-center justify-between mb-2">
      <span class="text-xs font-semibold flex items-center gap-1"><Grid3X3 class="w-3 h-3 text-purple-500" />壁纸</span>
      <div class="flex items-center gap-1">
        <Button variant="ghost" size="sm" class="h-5 px-1 text-[10px]" onclick={selectAll}>全选</Button>
        <Button variant="ghost" size="sm" class="h-5 px-1 text-[10px]" onclick={clearSelection}>清除</Button>
      </div>
    </div>
    <div class="max-h-32 overflow-y-auto space-y-1">
      {#if filteredWallpapers.length > 0}
        {#each filteredWallpapers.slice(0, 10) as wallpaper}
          {@const isSelected = selectedIds.has(wallpaper.workshop_id)}
          <button 
            class="w-full p-1.5 rounded border text-left text-xs transition-all hover:bg-muted/50 {isSelected ? 'border-primary bg-primary/10' : 'border-border'}"
            onclick={() => toggleSelect(wallpaper.workshop_id)}
          >
            <div class="truncate font-medium">{wallpaper.title || wallpaper.folder_name}</div>
            <div class="text-muted-foreground text-[10px]">{wallpaper.wallpaper_type} · {wallpaper.workshop_id}</div>
          </button>
        {/each}
        {#if filteredWallpapers.length > 10}
          <div class="text-center text-[10px] text-muted-foreground py-1">+{filteredWallpapers.length - 10} 更多</div>
        {/if}
      {:else}
        <div class="text-xs text-muted-foreground text-center py-3">扫描后显示</div>
      {/if}
    </div>
  {/if}
{/snippet}

<!-- 日志区块 -->
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
          {#each logs.slice(-15) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
        {:else}
          <div class="text-muted-foreground text-center py-4">暂无日志</div>
        {/if}
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
      {#each logs.slice(-4) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
    </div>
  {/if}
{/snippet}


<!-- ========== 主渲染 ========== -->
<div class="h-full w-full flex flex-col overflow-hidden">
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={200} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}
  
  <NodeWrapper 
    nodeId={id} title="enginev" icon={Image} status={phase} {borderClass} {isFullscreenRender}
    onCompact={() => dashboardGrid?.compact()}
    onResetLayout={() => { gridLayout = [...ENGINEV_DEFAULT_GRID_LAYOUT]; dashboardGrid?.applyLayout(gridLayout); saveState(); }}
    nodeType="enginev" currentLayout={gridLayout}
    onApplyLayout={(layout) => { gridLayout = layout; dashboardGrid?.applyLayout(layout); saveState(); }}
  >
    {#snippet children()}
      {#if isFullscreenRender}
        <!-- 全屏模式：GridStack -->
        <div class="h-full overflow-hidden">
          <DashboardGrid bind:this={dashboardGrid} columns={4} cellHeight={80} margin={12} showToolbar={false} onLayoutChange={handleLayoutChange}>
            {@const pathItem = getLayoutItem('path')}
            <DashboardItem id="path" x={pathItem.x} y={pathItem.y} w={pathItem.w} h={pathItem.h} minW={1} minH={1}>
              <BlockCard id="path" title="工坊路径" icon={FolderOpen} iconClass="text-primary" isFullscreen={true}>
                {#snippet children()}{@render pathBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            {@const filterItem = getLayoutItem('filter')}
            <DashboardItem id="filter" x={filterItem.x} y={filterItem.y} w={filterItem.w} h={filterItem.h} minW={1} minH={1}>
              <BlockCard id="filter" title="过滤条件" icon={Filter} iconClass="text-blue-500" isFullscreen={true}>
                {#snippet children()}{@render filterBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            {@const statsItem = getLayoutItem('stats')}
            <DashboardItem id="stats" x={statsItem.x} y={statsItem.y} w={statsItem.w} h={statsItem.h} minW={1} minH={1}>
              <BlockCard id="stats" title="统计" icon={BarChart3} iconClass="text-yellow-500" isFullscreen={true}>
                {#snippet children()}{@render statsBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            {@const opItem = getLayoutItem('operation')}
            <DashboardItem id="operation" x={opItem.x} y={opItem.y} w={opItem.w} h={opItem.h} minW={1} minH={1}>
              <BlockCard id="operation" title="操作" icon={Play} iconClass="text-green-500" isFullscreen={true}>
                {#snippet children()}{@render operationBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            {@const renameItem = getLayoutItem('rename')}
            <DashboardItem id="rename" x={renameItem.x} y={renameItem.y} w={renameItem.w} h={renameItem.h} minW={1} minH={1}>
              <BlockCard id="rename" title="重命名配置" icon={Pencil} iconClass="text-orange-500" isFullscreen={true}>
                {#snippet children()}{@render renameBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            {@const galleryItem = getLayoutItem('gallery')}
            <DashboardItem id="gallery" x={galleryItem.x} y={galleryItem.y} w={galleryItem.w} h={galleryItem.h} minW={2} minH={2}>
              <BlockCard id="gallery" title="壁纸列表" icon={Grid3X3} iconClass="text-purple-500" isFullscreen={true} fullHeight={true} hideHeader={true}>
                {#snippet children()}{@render galleryBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
            
            {@const logItem = getLayoutItem('log')}
            <DashboardItem id="log" x={logItem.x} y={logItem.y} w={logItem.w} h={logItem.h} minW={1} minH={1}>
              <BlockCard id="log" title="日志" icon={Copy} iconClass="text-muted-foreground" isFullscreen={true} fullHeight={true} hideHeader={true}>
                {#snippet children()}{@render logBlockContent()}{/snippet}
              </BlockCard>
            </DashboardItem>
          </DashboardGrid>
        </div>

      {:else}
        <!-- 普通模式：Bento Grid -->
        <div class="flex-1 overflow-y-auto p-2">
          <div class="grid grid-cols-2 gap-2" style="grid-auto-rows: minmax(auto, max-content);">
            <BlockCard id="path" title="工坊路径" icon={FolderOpen} iconClass="text-primary" class="col-span-2">
              {#snippet children()}{@render pathBlockContent()}{/snippet}
            </BlockCard>
            
            <BlockCard id="filter" title="过滤" icon={Filter} iconClass="text-blue-500" class="col-span-2">
              {#snippet children()}{@render filterBlockContent()}{/snippet}
            </BlockCard>
            
            <BlockCard id="stats" title="统计" icon={BarChart3} iconClass="text-yellow-500" class="col-span-1">
              {#snippet children()}{@render statsBlockContent()}{/snippet}
            </BlockCard>
            
            <BlockCard id="operation" title="操作" icon={Play} iconClass="text-green-500" class="col-span-1">
              {#snippet children()}{@render operationBlockContent()}{/snippet}
            </BlockCard>
            
            <BlockCard id="rename" title="重命名" icon={Pencil} iconClass="text-orange-500" class="col-span-2">
              {#snippet children()}{@render renameBlockContent()}{/snippet}
            </BlockCard>
            
            <BlockCard id="gallery" title="壁纸" icon={Grid3X3} iconClass="text-purple-500" class="col-span-2">
              {#snippet children()}{@render galleryBlockContent()}{/snippet}
            </BlockCard>
            
            <BlockCard id="log" title="日志" icon={Copy} iconClass="text-muted-foreground" class="col-span-2" collapsible={true}>
              {#snippet children()}{@render logBlockContent()}{/snippet}
            </BlockCard>
          </div>
        </div>
      {/if}
    {/snippet}
  </NodeWrapper>
  
  {#if !isFullscreenRender}
    <Handle type="source" position={Position.Right} class="bg-primary!" />
  {/if}
</div>
