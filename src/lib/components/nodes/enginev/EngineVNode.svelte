<script lang="ts">
  /**
   * EngineVNode - Wallpaper Engine 工坊管理节点
   * 功能：扫描、过滤、预览、批量重命名
   * 
   * 使用 Container Query 自动响应尺寸
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';

  import { InteractiveHover } from '$lib/components/ui/interactive-hover';
  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { ENGINEV_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    LoaderCircle, FolderOpen, Clipboard, Download,
    Filter, Pencil, Grid3X3, List, Copy, Check,
    Image, RefreshCw, Trash2, RotateCcw
  } from '@lucide/svelte';
  import {
    type WallpaperItem, type FilterOptions, type EngineVStats, type RenameConfig, type Phase, type EngineVState,
    getPhaseBorderClass, getRatingInfo, formatSize, calculateStats, filterWallpapers, getPreviewUrl,
    DEFAULT_STATS, DEFAULT_FILTERS, DEFAULT_RENAME_CONFIG
  } from './utils';
  import { getApiV1Url } from '$lib/stores/backend';
  
  interface Props {
    id: string;
    data?: { config?: { path?: string }; logs?: string[] };
    isFullscreenRender?: boolean;
  }
  
  let { id, data = {}, isFullscreenRender = false }: Props = $props();
  
  // 使用 $derived 确保响应式
  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<EngineVState>(nodeId));
  const DEFAULT_WORKSHOP_PATH = 'E:\\SteamLibrary\\steamapps\\workshop\\content\\431960';
  const apiBase = getApiV1Url();
  const configPath = $derived(data?.config?.path ?? DEFAULT_WORKSHOP_PATH);
  const dataLogs = $derived(data?.logs ?? []);
  
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let copied = $state(false);
  let workshopPath = $state(DEFAULT_WORKSHOP_PATH);

  let wallpapers = $state<WallpaperItem[]>([]);
  let filteredWallpapers = $state<WallpaperItem[]>([]);
  let stats = $state<EngineVStats>({ ...DEFAULT_STATS });
  let filters = $state<FilterOptions>({ ...DEFAULT_FILTERS });
  let renameConfig = $state<RenameConfig>({ ...DEFAULT_RENAME_CONFIG });
  let selectedIds = $state<Set<string>>(new Set());
  let viewMode = $state<'grid' | 'list'>('grid');

  let layoutRenderer = $state<any>(undefined);

  // 初始化标记，防止 $effect 覆盖用户输入
  let initialized = $state(false);

  // 初始化状态（只执行一次）
  $effect(() => {
    if (initialized) return;
    
    workshopPath = savedState?.workshopPath ?? configPath;
    logs = savedState?.logs ?? [...dataLogs];
    
    if (savedState) {
      phase = savedState.phase ?? 'idle';
      wallpapers = savedState.wallpapers ?? [];
      filteredWallpapers = savedState.filteredWallpapers ?? [];
      stats = savedState.stats ?? { ...DEFAULT_STATS };
      filters = savedState.filters ?? { ...DEFAULT_FILTERS };
      renameConfig = savedState.renameConfig ?? { ...DEFAULT_RENAME_CONFIG };
      selectedIds = new Set(savedState.selectedIds ?? []);
      viewMode = savedState.viewMode ?? 'grid';
    }
    
    initialized = true;
  });
  
  function saveState() { setNodeState<EngineVState>(nodeId, { phase, logs, workshopPath, wallpapers, filteredWallpapers, stats, filters, renameConfig, selectedIds, viewMode }); }
  
  let isRunning = $derived(phase === 'scanning' || phase === 'renaming');
  let borderClass = $derived(getPhaseBorderClass(phase));
  
  $effect(() => { if (phase || wallpapers || filteredWallpapers || stats) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  async function selectFolder() {
    try { const { platform } = await import('$lib/api/platform'); const s = await platform.openFolderDialog('选择 Wallpaper Engine 工坊目录'); if (s) workshopPath = s; }
    catch (e) { log(`选择失败: ${e}`); }
  }

  async function pastePath() { try { workshopPath = (await navigator.clipboard.readText()).trim(); } catch (e) { log(`粘贴失败: ${e}`); } }

  async function handleScan() {
    if (!workshopPath.trim()) { log('❌ 请输入工坊路径'); return; }
    phase = 'scanning'; log(`🔍 扫描: ${workshopPath}`);
    try {
      const r = await api.executeNode('enginev', { action: 'scan', workshop_path: workshopPath }) as any;
      if (r.success && r.data) {
        wallpapers = r.data.wallpapers || [];
        filteredWallpapers = [...wallpapers];
        stats = calculateStats(wallpapers, filteredWallpapers);
        phase = 'ready';
        log(`✅ 扫描完成: ${wallpapers.length} 个壁纸`);
      } else { phase = 'error'; log(`❌ ${r.message}`); }
    } catch (e) { phase = 'error'; log(`❌ ${e}`); }
  }

  function applyFilters() { filteredWallpapers = filterWallpapers(wallpapers, filters); stats = calculateStats(wallpapers, filteredWallpapers); log(`🔍 过滤: ${filteredWallpapers.length}/${wallpapers.length}`); }
  function clearFilters() { filters = { ...DEFAULT_FILTERS }; filteredWallpapers = [...wallpapers]; stats = calculateStats(wallpapers, filteredWallpapers); log('🗑️ 已清空过滤条件'); }

  async function handleRename() {
    const targets = selectedIds.size > 0 ? filteredWallpapers.filter(w => selectedIds.has(w.workshop_id)) : filteredWallpapers;
    if (targets.length === 0) { log('❌ 无可重命名项'); return; }
    
    phase = 'renaming'; 
    log(`${renameConfig.dryRun ? '🔍 模拟' : '▶️ 执行'}重命名 ${targets.length} 项...`);
    try {
      const r = await api.executeNode('enginev', { action: 'rename', workshop_ids: targets.map(w => w.workshop_id), template: renameConfig.template, desc_max_length: renameConfig.descMaxLength, name_max_length: renameConfig.nameMaxLength, dry_run: renameConfig.dryRun, copy_mode: renameConfig.copyMode, target_path: renameConfig.targetPath }) as any;
      if (r.success) { phase = 'completed'; log(`✅ 成功 ${r.data?.success_count || 0} 失败 ${r.data?.failed_count || 0}`); }
      else { phase = 'error'; log(`❌ ${r.message}`); }
    } catch (e) { phase = 'error'; log(`❌ ${e}`); }
  }

  async function exportData(format: 'json' | 'paths') {
    const targets = selectedIds.size > 0 ? filteredWallpapers.filter(w => selectedIds.has(w.workshop_id)) : filteredWallpapers;
    if (targets.length === 0) { log('❌ 无可导出项'); return; }
    try {
      const content = format === 'json' ? JSON.stringify(targets, null, 2) : targets.map(w => w.path).join('\n');
      const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `enginev_export_${Date.now()}.${format === 'json' ? 'json' : 'txt'}`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
      log(`💾 已导出 ${targets.length} 项 (${format})`);
    } catch (e) { log(`导出失败: ${e}`); }
  }

  function toggleSelect(workshopId: string) { if (selectedIds.has(workshopId)) selectedIds.delete(workshopId); else selectedIds.add(workshopId); selectedIds = new Set(selectedIds); }
  function selectAll() { selectedIds = new Set(filteredWallpapers.map(w => w.workshop_id)); }
  function clearSelection() { selectedIds = new Set(); }
  function clear() { wallpapers = []; filteredWallpapers = []; selectedIds = new Set(); stats = { ...DEFAULT_STATS }; phase = 'idle'; log('🗑️ 已清空'); }
  async function copyLogs() { try { await navigator.clipboard.writeText(logs.join('\n')); copied = true; setTimeout(() => copied = false, 2000); } catch {} }
</script>

<!-- 路径输入区块 -->
{#snippet pathBlock()}
  <div class="flex cq-gap cq-mb">
    <Input bind:value={workshopPath} placeholder="Wallpaper Engine 工坊路径..." disabled={isRunning} class="flex-1 cq-input" />
    <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={selectFolder} disabled={isRunning}>
      <FolderOpen class="cq-icon" />
    </Button>
    <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={pastePath} disabled={isRunning}>
      <Clipboard class="cq-icon" />
    </Button>
  </div>
  <Button variant="outline" class="w-full cq-button" onclick={handleScan} disabled={isRunning}>
    {#if isRunning && phase === 'scanning'}<LoaderCircle class="cq-icon mr-2 animate-spin" />{:else}<RefreshCw class="cq-icon mr-2" />{/if}
    扫描工坊
  </Button>
{/snippet}

<!-- 过滤条件区块 -->
{#snippet filterBlock()}
  <div class="cq-space">
    <Input bind:value={filters.title} placeholder="搜索标题..." class="cq-input" onchange={applyFilters} />
    <div class="grid grid-cols-2 cq-gap">
      <select bind:value={filters.contentrating} onchange={applyFilters} class="cq-select rounded-md border bg-background px-2">
        <option value="">全部评级</option>
        <option value="Everyone">全年龄</option>
        <option value="Mature">成熟</option>
        <option value="Adult">成人</option>
      </select>
      <select bind:value={filters.type} onchange={applyFilters} class="cq-select rounded-md border bg-background px-2">
        <option value="">全部类型</option>
        <option value="Video">视频</option>
        <option value="Scene">场景</option>
        <option value="Web">网页</option>
      </select>
    </div>
    <div class="flex cq-gap-sm">
      <Button variant="outline" size="sm" class="flex-1 cq-button-sm" onclick={applyFilters}>
        <Filter class="cq-icon-sm mr-1" />应用
      </Button>
      <Button variant="ghost" size="sm" class="cq-button-sm" onclick={clearFilters}>
        <Trash2 class="cq-icon-sm" />
      </Button>
    </div>
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlock()}
  {@const filterPercent = stats.total > 0 ? ((stats.filtered / stats.total) * 100).toFixed(0) : '0'}
  {@const selectPercent = stats.filtered > 0 ? ((selectedIds.size / stats.filtered) * 100).toFixed(0) : '0'}
  <div class="grid grid-cols-3 cq-gap">
    <div class="cq-stat-card bg-muted/40">
      <div class="flex flex-col items-center">
        <span class="cq-stat-value tabular-nums">{stats.total}</span>
        <span class="cq-stat-label text-muted-foreground">总计</span>
      </div>
    </div>
    <div class="cq-stat-card bg-blue-500/10">
      <div class="flex flex-col items-center">
        <span class="cq-stat-value text-blue-500 tabular-nums">{stats.filtered}</span>
        <span class="cq-stat-label text-muted-foreground">{filterPercent}%</span>
      </div>
    </div>
    <div class="cq-stat-card bg-purple-500/10">
      <div class="flex flex-col items-center">
        <span class="cq-stat-value text-purple-500 tabular-nums">{selectedIds.size}</span>
        <span class="cq-stat-label text-muted-foreground">{selectPercent}%</span>
      </div>
    </div>
  </div>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <!-- 主按钮 -->
    <Button class="w-full cq-button flex-1" onclick={handleRename} disabled={isRunning || stats.filtered === 0}>
      {#if phase === 'renaming'}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<Pencil class="cq-icon mr-1" />{/if}
      <span>重命名</span>
    </Button>
    <!-- 导出按钮 -->
    <div class="flex cq-gap">
      <Button variant="outline" class="flex-1 cq-button-sm" onclick={() => exportData('json')} disabled={stats.filtered === 0}>
        <Download class="cq-icon mr-1" />JSON
      </Button>
      <Button variant="outline" class="flex-1 cq-button-sm" onclick={() => exportData('paths')} disabled={stats.filtered === 0}>
        <Download class="cq-icon mr-1" />路径
      </Button>
    </div>
    <!-- 重置按钮 -->
    <Button variant="ghost" class="w-full cq-button-sm" onclick={clear} disabled={isRunning}>
      <RotateCcw class="cq-icon mr-1" />清空
    </Button>
  </div>
{/snippet}

<!-- 重命名配置区块 -->
{#snippet renameBlock()}
  {@const placeholderText = '[#{id}]{original_name}+{title}'}
  {@const helpText = '占位符: {id} {title} {original_name} {type} {rating} {desc}'}
  <div class="cq-space">
    <div>
      <span class="cq-text text-muted-foreground mb-1 block">命名模板</span>
      <Input bind:value={renameConfig.template} placeholder={placeholderText} class="cq-input" />
    </div>
    <div class="flex flex-wrap cq-gap cq-text">
      <label class="flex items-center gap-1.5">
        <Checkbox bind:checked={renameConfig.dryRun} />
        <span>模拟执行</span>
      </label>
      <label class="flex items-center gap-1.5">
        <Checkbox bind:checked={renameConfig.copyMode} />
        <span>复制模式</span>
      </label>
    </div>
    {#if renameConfig.copyMode}
      <Input bind:value={renameConfig.targetPath} placeholder="目标路径..." class="cq-input" />
    {/if}
    <div class="cq-text-sm text-muted-foreground">{helpText}</div>
  </div>
{/snippet}

<!-- 壁纸列表区块 -->
{#snippet galleryBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between cq-padding border-b bg-muted/30 shrink-0">
      <span class="font-semibold cq-text flex items-center gap-2"><Grid3X3 class="cq-icon text-purple-500" />壁纸列表</span>
      <div class="flex items-center gap-2">
        <Button variant="ghost" size="sm" class="h-7 px-2 cq-text-sm" onclick={selectAll}>全选</Button>
        <Button variant="ghost" size="sm" class="h-7 px-2 cq-text-sm" onclick={clearSelection}>清除</Button>
        <Button variant="ghost" size="icon" class="h-7 w-7" onclick={() => viewMode = viewMode === 'grid' ? 'list' : 'grid'}>
          {#if viewMode === 'grid'}<List class="cq-icon" />{:else}<Grid3X3 class="cq-icon" />{/if}
        </Button>
      </div>
    </div>
    <div class="flex-1 overflow-y-auto cq-padding">
      {#if filteredWallpapers.length > 0}
        {#if viewMode === 'grid'}
          <div class="grid grid-cols-3 cq-gap">
            {#each filteredWallpapers.slice(0, 50) as wallpaper}
              {@const isSelected = selectedIds.has(wallpaper.workshop_id)}
              {@const ratingInfo = getRatingInfo(wallpaper.content_rating)}
              {@const previewUrl = getPreviewUrl(wallpaper, apiBase)}
              <button class="cq-rounded border text-left transition-all hover:bg-muted/50 overflow-hidden {isSelected ? 'border-primary bg-primary/10 ring-2 ring-primary/30' : 'border-border'}" onclick={() => toggleSelect(wallpaper.workshop_id)}>
                <div class="aspect-video bg-muted/50 relative overflow-hidden">
                  {#if previewUrl}<img src={previewUrl} alt={wallpaper.title || wallpaper.folder_name} class="w-full h-full object-cover" loading="lazy" onerror={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />{:else}<div class="w-full h-full flex items-center justify-center"><Image class="w-8 h-8 text-muted-foreground/30" /></div>{/if}
                  <div class="absolute top-1 right-1 px-1.5 py-0.5 rounded cq-text-sm bg-black/60 text-white">{wallpaper.wallpaper_type}</div>
                  {#if isSelected}<div class="absolute top-1 left-1 w-5 h-5 rounded-full bg-primary flex items-center justify-center"><Check class="w-3 h-3 text-primary-foreground" /></div>{/if}
                </div>
                <div class="cq-padding">
                  <div class="cq-text font-medium truncate" title={wallpaper.title}>{wallpaper.title || wallpaper.folder_name}</div>
                  <div class="flex items-center gap-2 mt-1 cq-text-sm text-muted-foreground"><span class={ratingInfo.color}>{ratingInfo.name}</span><span class="truncate">{wallpaper.workshop_id}</span></div>
                </div>
              </button>
            {/each}
          </div>
        {:else}
          <div class="cq-space-sm">
            {#each filteredWallpapers.slice(0, 100) as wallpaper}
              {@const isSelected = selectedIds.has(wallpaper.workshop_id)}
              {@const ratingInfo = getRatingInfo(wallpaper.content_rating)}
              {@const previewUrl = getPreviewUrl(wallpaper, apiBase)}
              <button class="w-full cq-padding cq-rounded border text-left flex items-center cq-gap transition-all hover:bg-muted/50 {isSelected ? 'border-primary bg-primary/10' : 'border-border'}" onclick={() => toggleSelect(wallpaper.workshop_id)}>
                <Checkbox checked={isSelected} class="shrink-0" />
                <div class="w-16 h-10 rounded bg-muted/50 overflow-hidden shrink-0">
                  {#if previewUrl}<img src={previewUrl} alt={wallpaper.title || wallpaper.folder_name} class="w-full h-full object-cover" loading="lazy" onerror={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />{:else}<div class="w-full h-full flex items-center justify-center"><Image class="w-4 h-4 text-muted-foreground/30" /></div>{/if}
                </div>
                <div class="flex-1 min-w-0"><div class="cq-text font-medium truncate">{wallpaper.title || wallpaper.folder_name}</div><div class="cq-text-sm text-muted-foreground truncate">{wallpaper.path}</div></div>
                <div class="flex items-center gap-2 cq-text-sm shrink-0"><span class={ratingInfo.color}>{ratingInfo.name}</span><span class="text-muted-foreground">{wallpaper.wallpaper_type}</span><span class="text-muted-foreground">{formatSize(wallpaper.size)}</span></div>
              </button>
            {/each}
          </div>
        {/if}
        {#if filteredWallpapers.length > (viewMode === 'grid' ? 50 : 100)}<div class="text-center cq-text text-muted-foreground py-4">显示前 {viewMode === 'grid' ? 50 : 100} 项，共 {filteredWallpapers.length} 项</div>{/if}
      {:else}<div class="text-center text-muted-foreground py-8 cq-text">扫描后显示壁纸列表</div>{/if}
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

<!-- 区块渲染器 -->
{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'path'}{@render pathBlock()}
  {:else if blockId === 'filter'}{@render filterBlock()}
  {:else if blockId === 'stats'}{@render statsBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'rename'}{@render renameBlock()}
  {:else if blockId === 'gallery'}{@render galleryBlock()}
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
    title="enginev" 
    icon={Image} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="enginev" 
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
        nodeType="enginev"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={ENGINEV_DEFAULT_GRID_LAYOUT}
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
