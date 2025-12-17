<script lang="ts">
  /**
   * EngineVNode - Wallpaper Engine 工坊管理节点
   * 使用 NodeLayoutRenderer 统一布局，支持节点模式和全屏模式
   * 功能：扫描、过滤、预览、批量重命名
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { ENGINEV_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from './NodeWrapper.svelte';
  import { getSizeClasses, type SizeMode } from '$lib/utils/sizeUtils';
  import { 
    LoaderCircle, FolderOpen, Clipboard, Download,
    Filter, BarChart3, Pencil, Grid3X3, List, Copy, Check,
    Image, RefreshCw, Trash2
  } from '@lucide/svelte';
  import {
    type WallpaperItem, type FilterOptions, type EngineVStats, type RenameConfig, type Phase, type EngineVState,
    getPhaseBorderClass, getRatingInfo, formatSize, calculateStats, filterWallpapers, getPreviewUrl,
    DEFAULT_STATS, DEFAULT_FILTERS, DEFAULT_RENAME_CONFIG
  } from './enginev-utils';
  import { getApiV1Url } from '$lib/stores/backend';
  
  interface Props {
    id: string;
    data?: { config?: { path?: string }; logs?: string[] };
    isFullscreenRender?: boolean;
  }
  
  let { id, data = {}, isFullscreenRender = false }: Props = $props();
  
  // 从 nodeStateStore 恢复状态
  const savedState = getNodeState<EngineVState>(id);
  
  // 默认 Wallpaper Engine 工坊目录
  const DEFAULT_WORKSHOP_PATH = 'E:\\SteamLibrary\\steamapps\\workshop\\content\\431960';
  // API 基础 URL（用于图片预览）
  const apiBase = getApiV1Url();
  
  // 状态初始化
  let phase = $state<Phase>(savedState?.phase ?? 'idle');
  let logs = $state<string[]>(savedState?.logs ?? (data?.logs ? [...data.logs] : []));
  let copied = $state(false);
  let workshopPath = $state(savedState?.workshopPath ?? data?.config?.path ?? DEFAULT_WORKSHOP_PATH);

  // 数据状态
  let wallpapers = $state<WallpaperItem[]>(savedState?.wallpapers ?? []);
  let filteredWallpapers = $state<WallpaperItem[]>(savedState?.filteredWallpapers ?? []);
  let stats = $state<EngineVStats>(savedState?.stats ?? { ...DEFAULT_STATS });
  let filters = $state<FilterOptions>(savedState?.filters ?? { ...DEFAULT_FILTERS });
  let renameConfig = $state<RenameConfig>(savedState?.renameConfig ?? { ...DEFAULT_RENAME_CONFIG });
  let selectedIds = $state<Set<string>>(new Set(savedState?.selectedIds ?? []));
  let viewMode = $state<'grid' | 'list'>(savedState?.viewMode ?? 'grid');

  // NodeLayoutRenderer 引用
  let layoutRenderer = $state<{ 
    createTab: (blockIds: string[]) => void;
    getUsedBlockIds: () => string[];
    compact: () => void;
    resetLayout: () => void;
    applyLayout: (layout: any[]) => void;
    getCurrentLayout: () => any[];
  } | undefined>(undefined);
  
  function saveState() {
    setNodeState<EngineVState>(id, {
      phase, logs, workshopPath, wallpapers, filteredWallpapers, stats, filters, renameConfig,
      selectedIds, viewMode
    });
  }
  
  // 响应式派生值
  let isRunning = $derived(phase === 'scanning' || phase === 'renaming');
  let borderClass = $derived(getPhaseBorderClass(phase));
  
  // 状态变化时自动保存
  $effect(() => {
    if (phase || wallpapers || filteredWallpapers || stats) saveState();
  });

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
    if (selectedIds.has(workshopId)) selectedIds.delete(workshopId);
    else selectedIds.add(workshopId);
    selectedIds = new Set(selectedIds);
  }

  function selectAll() { selectedIds = new Set(filteredWallpapers.map(w => w.workshop_id)); }
  function clearSelection() { selectedIds = new Set(); }
  
  function clear() {
    wallpapers = []; filteredWallpapers = []; selectedIds = new Set();
    stats = { ...DEFAULT_STATS }; phase = 'idle';
    log('🗑️ 已清空');
  }
  
  async function copyLogs() { 
    try { await navigator.clipboard.writeText(logs.join('\n')); copied = true; setTimeout(() => copied = false, 2000); } catch {} 
  }
</script>


<!-- ========== 区块内容 Snippets（参数化尺寸） ========== -->

<!-- 路径输入区块 -->
{#snippet pathBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="flex {c.gap} {c.mb}">
    <Input bind:value={workshopPath} placeholder="Wallpaper Engine 工坊路径..." disabled={isRunning} class="flex-1 {c.input}" />
    <Button variant="outline" size="icon" class="{c.buttonIcon} shrink-0" onclick={selectFolder} disabled={isRunning}>
      <FolderOpen class={c.icon} />
    </Button>
    <Button variant="outline" size="icon" class="{c.buttonIcon} shrink-0" onclick={pastePath} disabled={isRunning}>
      <Clipboard class={c.icon} />
    </Button>
  </div>
  <Button variant="outline" class="w-full {c.button}" onclick={handleScan} disabled={isRunning}>
    {#if isRunning && phase === 'scanning'}<LoaderCircle class="{c.icon} mr-2 animate-spin" />{:else}<RefreshCw class="{c.icon} mr-2" />{/if}
    {size === 'normal' ? '扫描工坊' : '扫描'}
  </Button>
{/snippet}

<!-- 过滤条件区块 -->
{#snippet filterBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class={c.space}>
    <Input bind:value={filters.title} placeholder="搜索标题..." class={c.input} onchange={applyFilters} />
    <div class="grid grid-cols-2 {c.gap}">
      <select bind:value={filters.contentrating} onchange={applyFilters} class="{c.select} rounded-md border bg-background px-2">
        <option value="">全部评级</option>
        <option value="Everyone">全年龄</option>
        <option value="Mature">成熟</option>
        <option value="Adult">成人</option>
      </select>
      <select bind:value={filters.type} onchange={applyFilters} class="{c.select} rounded-md border bg-background px-2">
        <option value="">全部类型</option>
        <option value="Video">视频</option>
        <option value="Scene">场景</option>
        <option value="Web">网页</option>
      </select>
    </div>
    <div class="flex {c.gapSm}">
      <Button variant="outline" size="sm" class="flex-1 {c.buttonSm}" onclick={applyFilters}>
        <Filter class="{c.iconSm} mr-1" />应用
      </Button>
      <Button variant="ghost" size="sm" class={c.buttonSm} onclick={clearFilters}>
        <Trash2 class={c.iconSm} />
      </Button>
    </div>
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if size === 'normal'}
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
    <div class="grid grid-cols-3 {c.gapSm} {c.text}">
      <div class="text-center {c.paddingSm} bg-muted/50 {c.rounded}"><div class="font-bold">{stats.total}</div><div class="text-muted-foreground {c.textSm}">总计</div></div>
      <div class="text-center {c.paddingSm} bg-blue-500/10 {c.rounded}"><div class="font-bold text-blue-600">{stats.filtered}</div><div class="text-muted-foreground {c.textSm}">过滤</div></div>
      <div class="text-center {c.paddingSm} bg-purple-500/10 {c.rounded}"><div class="font-bold text-purple-600">{selectedIds.size}</div><div class="text-muted-foreground {c.textSm}">选择</div></div>
    </div>
  {/if}
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="flex flex-col {c.gap} {size === 'normal' ? 'flex-1 justify-center' : ''}">
    {#if size === 'normal'}
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
      <Button class="flex-1 {c.button}" onclick={handleRename} disabled={isRunning || stats.filtered === 0}>
        {#if phase === 'renaming'}<LoaderCircle class="{c.icon} mr-1 animate-spin" />{:else}<Pencil class="{c.icon} mr-1" />{/if}重命名
      </Button>
      <div class="flex {c.gapSm}">
        <Button variant="outline" size="sm" class="flex-1 {c.buttonSm}" onclick={() => exportData('json')} disabled={stats.filtered === 0}>JSON</Button>
        <Button variant="outline" size="sm" class="flex-1 {c.buttonSm}" onclick={() => exportData('paths')} disabled={stats.filtered === 0}>路径</Button>
      </div>
    {/if}
  </div>
{/snippet}

<!-- 重命名配置区块 -->
{#snippet renameBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {@const placeholderText = '[#{id}]{original_name}+{title}'}
  {@const helpText = '占位符: {id} {title} {original_name} {type} {rating} {desc}'}
  <div class={c.space}>
    <div>
      <span class="{c.text} text-muted-foreground mb-1 block">命名模板</span>
      <Input bind:value={renameConfig.template} placeholder={placeholderText} class={c.input} />
    </div>
    <div class="flex flex-wrap {c.gap} {c.text}">
      <label class="flex items-center gap-1.5">
        <Checkbox bind:checked={renameConfig.dryRun} class={size === 'compact' ? 'h-3 w-3' : ''} />
        <span>模拟执行</span>
      </label>
      <label class="flex items-center gap-1.5">
        <Checkbox bind:checked={renameConfig.copyMode} class={size === 'compact' ? 'h-3 w-3' : ''} />
        <span>复制模式</span>
      </label>
    </div>
    {#if renameConfig.copyMode}
      <Input bind:value={renameConfig.targetPath} placeholder="目标路径..." class={c.input} />
    {/if}
    <div class="{c.textSm} text-muted-foreground">{helpText}</div>
  </div>
{/snippet}

<!-- 壁纸列表区块 -->
{#snippet galleryBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if size === 'normal'}
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
            <div class="grid grid-cols-3 gap-3">
              {#each filteredWallpapers.slice(0, 50) as wallpaper}
                {@const isSelected = selectedIds.has(wallpaper.workshop_id)}
                {@const ratingInfo = getRatingInfo(wallpaper.content_rating)}
                {@const previewUrl = getPreviewUrl(wallpaper, apiBase)}
                <button class="rounded-lg border text-left transition-all hover:bg-muted/50 overflow-hidden {isSelected ? 'border-primary bg-primary/10 ring-2 ring-primary/30' : 'border-border'}" onclick={() => toggleSelect(wallpaper.workshop_id)}>
                  <div class="aspect-video bg-muted/50 relative overflow-hidden">
                    {#if previewUrl}<img src={previewUrl} alt={wallpaper.title || wallpaper.folder_name} class="w-full h-full object-cover" loading="lazy" onerror={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />{:else}<div class="w-full h-full flex items-center justify-center"><Image class="w-8 h-8 text-muted-foreground/30" /></div>{/if}
                    <div class="absolute top-1 right-1 px-1.5 py-0.5 rounded text-[10px] bg-black/60 text-white">{wallpaper.wallpaper_type}</div>
                    {#if isSelected}<div class="absolute top-1 left-1 w-5 h-5 rounded-full bg-primary flex items-center justify-center"><Check class="w-3 h-3 text-primary-foreground" /></div>{/if}
                  </div>
                  <div class="p-2">
                    <div class="text-sm font-medium truncate" title={wallpaper.title}>{wallpaper.title || wallpaper.folder_name}</div>
                    <div class="flex items-center gap-2 mt-1 text-xs text-muted-foreground"><span class={ratingInfo.color}>{ratingInfo.name}</span><span class="truncate">{wallpaper.workshop_id}</span></div>
                  </div>
                </button>
              {/each}
            </div>
          {:else}
            <div class="space-y-1">
              {#each filteredWallpapers.slice(0, 100) as wallpaper}
                {@const isSelected = selectedIds.has(wallpaper.workshop_id)}
                {@const ratingInfo = getRatingInfo(wallpaper.content_rating)}
                {@const previewUrl = getPreviewUrl(wallpaper, apiBase)}
                <button class="w-full p-2 rounded-lg border text-left flex items-center gap-3 transition-all hover:bg-muted/50 {isSelected ? 'border-primary bg-primary/10' : 'border-border'}" onclick={() => toggleSelect(wallpaper.workshop_id)}>
                  <Checkbox checked={isSelected} class="shrink-0" />
                  <div class="w-16 h-10 rounded bg-muted/50 overflow-hidden shrink-0">
                    {#if previewUrl}<img src={previewUrl} alt={wallpaper.title || wallpaper.folder_name} class="w-full h-full object-cover" loading="lazy" onerror={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />{:else}<div class="w-full h-full flex items-center justify-center"><Image class="w-4 h-4 text-muted-foreground/30" /></div>{/if}
                  </div>
                  <div class="flex-1 min-w-0"><div class="text-sm font-medium truncate">{wallpaper.title || wallpaper.folder_name}</div><div class="text-xs text-muted-foreground truncate">{wallpaper.path}</div></div>
                  <div class="flex items-center gap-2 text-xs shrink-0"><span class={ratingInfo.color}>{ratingInfo.name}</span><span class="text-muted-foreground">{wallpaper.wallpaper_type}</span><span class="text-muted-foreground">{formatSize(wallpaper.size)}</span></div>
                </button>
              {/each}
            </div>
          {/if}
          {#if filteredWallpapers.length > (viewMode === 'grid' ? 50 : 100)}<div class="text-center text-sm text-muted-foreground py-4">显示前 {viewMode === 'grid' ? 50 : 100} 项，共 {filteredWallpapers.length} 项</div>{/if}
        {:else}<div class="text-center text-muted-foreground py-8">扫描后显示壁纸列表</div>{/if}
      </div>
    </div>
  {:else}
    <div class="flex items-center justify-between mb-2">
      <span class="{c.text} font-semibold flex items-center gap-1"><Grid3X3 class="w-3 h-3 text-purple-500" />壁纸</span>
      <div class="flex items-center gap-1">
        <Button variant="ghost" size="sm" class="h-5 px-1 {c.textSm}" onclick={selectAll}>全选</Button>
        <Button variant="ghost" size="sm" class="h-5 px-1 {c.textSm}" onclick={clearSelection}>清除</Button>
      </div>
    </div>
    <div class="{c.maxHeight} overflow-y-auto {c.spaceSm}">
      {#if filteredWallpapers.length > 0}
        {#each filteredWallpapers.slice(0, 10) as wallpaper}
          {@const isSelected = selectedIds.has(wallpaper.workshop_id)}
          {@const previewUrl = getPreviewUrl(wallpaper, apiBase)}
          <button class="w-full {c.paddingSm} {c.rounded} border text-left {c.text} transition-all hover:bg-muted/50 flex items-center gap-2 {isSelected ? 'border-primary bg-primary/10' : 'border-border'}" onclick={() => toggleSelect(wallpaper.workshop_id)}>
            <div class="w-10 h-7 rounded bg-muted/50 overflow-hidden shrink-0">{#if previewUrl}<img src={previewUrl} alt="" class="w-full h-full object-cover" loading="lazy" onerror={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />{/if}</div>
            <div class="flex-1 min-w-0"><div class="truncate font-medium">{wallpaper.title || wallpaper.folder_name}</div><div class="text-muted-foreground {c.textSm}">{wallpaper.wallpaper_type} · {wallpaper.workshop_id}</div></div>
          </button>
        {/each}
        {#if filteredWallpapers.length > 10}<div class="text-center {c.textSm} text-muted-foreground py-1">+{filteredWallpapers.length - 10} 更多</div>{/if}
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
  {#if blockId === 'path'}{@render pathBlock(size)}
  {:else if blockId === 'filter'}{@render filterBlock(size)}
  {:else if blockId === 'stats'}{@render statsBlock(size)}
  {:else if blockId === 'operation'}{@render operationBlock(size)}
  {:else if blockId === 'rename'}{@render renameBlock(size)}
  {:else if blockId === 'gallery'}{@render galleryBlock(size)}
  {:else if blockId === 'log'}{@render logBlock(size)}
  {/if}
{/snippet}


<!-- ========== 主渲染 ========== -->
<div class="h-full w-full flex flex-col overflow-hidden">
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={200} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}
  
  <NodeWrapper 
    nodeId={id} 
    title="enginev" 
    icon={Image} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="enginev" 
    currentLayout={layoutRenderer?.getCurrentLayout()}
    onApplyLayout={(layout) => layoutRenderer?.applyLayout(layout)}
    canCreateTab={true}
    onCreateTab={(blockIds) => layoutRenderer?.createTab(blockIds)}
    usedTabBlockIds={layoutRenderer?.getUsedBlockIds() ?? []}
  >
    {#snippet children()}
      <NodeLayoutRenderer
        bind:this={layoutRenderer}
        nodeId={id}
        nodeType="enginev"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={ENGINEV_DEFAULT_GRID_LAYOUT}
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
