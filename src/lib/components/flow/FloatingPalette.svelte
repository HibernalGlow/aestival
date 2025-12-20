<script lang="ts">
  /**
   * 浮动节点面板 - 可拖拽的节点选择器
   * 功能：虚拟树分类、搜索过滤、收藏/常用、折叠记忆、节点预览
   */
  import { NODE_DEFINITIONS, type NodeDefinition } from '$lib/stores/nodeRegistry';
  import { flowStore } from '$lib/stores';
  import { fullscreenNodeStore } from '$lib/stores/fullscreenNode.svelte';
  import {
    Clipboard, Folder, FileInput, Package, Search, AlertTriangle,
    FolderSync, FileText, Video, Terminal, ChevronDown, ChevronRight,
    Maximize2, Star, X, Image
  } from '@lucide/svelte';
  import { settingsManager } from '$lib/settings/settingsManager';
  import { onMount } from 'svelte';

  // ========== 图标映射 ==========
  const icons: Record<string, typeof Clipboard> = {
    Clipboard, Folder, FileInput, Package, Search, AlertTriangle,
    FolderSync, FileText, Video, Terminal, Image
  };

  // ========== 分类定义 ==========
  const categories = [
    { id: 'favorites', label: '收藏', color: 'text-yellow-500', icon: Star },
    { id: 'frequent', label: '常用', color: 'text-purple-500', icon: Star },
    { id: 'input', label: '输入', color: 'text-green-600', icon: Folder },
    { id: 'tool', label: '工具', color: 'text-blue-600', icon: Package },
    { id: 'output', label: '输出', color: 'text-amber-600', icon: Terminal }
  ];

  // ========== 面板设置 ==========
  let panelSettings = $state(settingsManager.getSettings().panels);
  let sidebarStyle = $derived(
    `background: color-mix(in srgb, var(--card) ${panelSettings.sidebarOpacity}%, transparent); backdrop-filter: blur(${panelSettings.sidebarBlur}px);`
  );

  // ========== 持久化状态 ==========
  const STORAGE_KEY = 'aestivus_palette_state';
  
  interface PaletteState {
    position: { x: number; y: number };
    size: { width: number; height: number };
    collapsed: boolean;
    expandedCategories: Record<string, boolean>;
    favorites: string[];
    usageCount: Record<string, number>;
  }

  function loadState(): PaletteState {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch (e) { console.warn('加载面板状态失败:', e); }
    return {
      position: { x: 20, y: 100 },
      size: { width: 200, height: 400 },
      collapsed: false,
      expandedCategories: { favorites: true, frequent: false, input: true, tool: true, output: true },
      favorites: [],
      usageCount: {}
    };
  }

  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        position, size, collapsed, expandedCategories, favorites, usageCount
      }));
    } catch (e) { console.warn('保存面板状态失败:', e); }
  }

  // ========== 状态 ==========
  let savedState = loadState();
  let position = $state(savedState.position);
  let size = $state(savedState.size);
  let collapsed = $state(savedState.collapsed);
  let expandedCategories = $state<Record<string, boolean>>(savedState.expandedCategories);
  let favorites = $state<string[]>(savedState.favorites);
  let usageCount = $state<Record<string, number>>(savedState.usageCount);
  
  // 搜索
  let searchQuery = $state('');
  let searchInputRef: HTMLInputElement;
  
  // 拖拽和调整大小
  let isDragging = $state(false);
  let isResizing = $state(false);
  let dragOffset = { x: 0, y: 0 };
  let resizeStart = { x: 0, y: 0, width: 0, height: 0 };
  
  // 悬停预览
  let hoveredNode = $state<NodeDefinition | null>(null);
  let hoverPosition = $state({ x: 0, y: 0 });
  let hoverTimeout: number | null = null;

  let nodeIdCounter = 1;

  // ========== 计算属性 ==========
  
  // 常用节点（按使用频率排序，取前5个）
  let frequentNodes = $derived(() => {
    return Object.entries(usageCount)
      .filter(([_, count]) => count > 0)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([type]) => NODE_DEFINITIONS.find(n => n.type === type))
      .filter((n): n is NodeDefinition => n !== undefined);
  });

  // 收藏节点
  let favoriteNodes = $derived(() => {
    return favorites
      .map(type => NODE_DEFINITIONS.find(n => n.type === type))
      .filter((n): n is NodeDefinition => n !== undefined);
  });

  // 过滤后的节点
  function getFilteredNodes(category: string): NodeDefinition[] {
    let nodes: NodeDefinition[];
    
    if (category === 'favorites') {
      nodes = favoriteNodes();
    } else if (category === 'frequent') {
      nodes = frequentNodes();
    } else {
      nodes = NODE_DEFINITIONS.filter(n => n.category === category);
    }
    
    if (!searchQuery.trim()) return nodes;
    
    const query = searchQuery.toLowerCase();
    return nodes.filter(n => 
      n.label.toLowerCase().includes(query) ||
      n.description?.toLowerCase().includes(query) ||
      n.type.toLowerCase().includes(query)
    );
  }

  // 是否有搜索结果
  let hasSearchResults = $derived(() => {
    if (!searchQuery.trim()) return true;
    return categories.some(cat => getFilteredNodes(cat.id).length > 0);
  });

  // ========== 生命周期 ==========
  onMount(() => {
    settingsManager.addListener((s) => {
      panelSettings = s.panels;
    });
  });

  // 状态变化时保存
  $effect(() => {
    saveState();
  });

  // ========== 事件处理 ==========
  
  function onMouseDown(e: MouseEvent) {
    if ((e.target as HTMLElement).closest('button')) return;
    if ((e.target as HTMLElement).closest('input')) return;
    if ((e.target as HTMLElement).closest('.resize-handle')) return;
    isDragging = true;
    dragOffset = { x: e.clientX - position.x, y: e.clientY - position.y };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }

  function onMouseMove(e: MouseEvent) {
    if (isDragging) {
      position = { x: e.clientX - dragOffset.x, y: e.clientY - dragOffset.y };
    } else if (isResizing) {
      const newWidth = Math.max(160, Math.min(400, resizeStart.width + (e.clientX - resizeStart.x)));
      const newHeight = Math.max(200, Math.min(700, resizeStart.height + (e.clientY - resizeStart.y)));
      size = { width: newWidth, height: newHeight };
    }
  }

  function onMouseUp() {
    isDragging = false;
    isResizing = false;
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('mouseup', onMouseUp);
  }

  function onResizeStart(e: MouseEvent) {
    e.stopPropagation();
    isResizing = true;
    resizeStart = { x: e.clientX, y: e.clientY, width: size.width, height: size.height };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }

  function addNode(type: string, label: string) {
    const node = {
      id: `node-${nodeIdCounter++}-${Date.now()}`,
      type,
      position: { x: 300 + Math.random() * 100, y: 200 + Math.random() * 100 },
      data: { label, status: 'idle' as const }
    };
    flowStore.addNode(node);
    usageCount[type] = (usageCount[type] || 0) + 1;
  }

  function openFullscreen(type: string, label: string) {
    // 先创建节点
    const nodeId = `node-${nodeIdCounter++}-${Date.now()}`;
    const node = {
      id: nodeId,
      type,
      position: { x: 300 + Math.random() * 100, y: 200 + Math.random() * 100 },
      data: { label, status: 'idle' as const }
    };
    flowStore.addNode(node);
    usageCount[type] = (usageCount[type] || 0) + 1;
    
    // 再打开全屏
    fullscreenNodeStore.open(nodeId);
  }

  function onDragStart(event: DragEvent, type: string, label: string) {
    if (event.dataTransfer) {
      event.dataTransfer.setData('application/json', JSON.stringify({ type, label }));
      event.dataTransfer.effectAllowed = 'move';
    }
  }

  function toggleCategory(id: string) {
    expandedCategories[id] = !expandedCategories[id];
  }

  function toggleFavorite(type: string, e: MouseEvent) {
    e.stopPropagation();
    if (favorites.includes(type)) {
      favorites = favorites.filter(t => t !== type);
    } else {
      favorites = [...favorites, type];
    }
  }

  // 悬停预览
  function onNodeHover(node: NodeDefinition, e: MouseEvent) {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    hoverTimeout = setTimeout(() => {
      hoveredNode = node;
      hoverPosition = { x: rect.right + 8, y: rect.top };
    }, 400) as unknown as number;
  }

  function onNodeLeave() {
    if (hoverTimeout) {
      clearTimeout(hoverTimeout);
      hoverTimeout = null;
    }
    hoveredNode = null;
  }

  function clearSearch() {
    searchQuery = '';
    searchInputRef?.focus();
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="fixed z-50 select-none"
  style="left: {position.x}px; top: {position.y}px; width: {size.width}px;"
  onmousedown={onMouseDown}
>
  <div class="rounded-2xl shadow-xl overflow-hidden" style={sidebarStyle}>
    <!-- 标题栏 -->
    <div class="flex items-center justify-between px-3 py-2 cursor-move border-b border-border/50">
      <div class="flex items-center gap-2">
        <div class="grid grid-cols-2 gap-0.5">
          <div class="w-1 h-1 rounded-full bg-muted-foreground/40"></div>
          <div class="w-1 h-1 rounded-full bg-muted-foreground/40"></div>
          <div class="w-1 h-1 rounded-full bg-muted-foreground/40"></div>
          <div class="w-1 h-1 rounded-full bg-muted-foreground/40"></div>
          <div class="w-1 h-1 rounded-full bg-muted-foreground/40"></div>
          <div class="w-1 h-1 rounded-full bg-muted-foreground/40"></div>
        </div>
        <span class="text-sm font-medium">节点</span>
      </div>
      <button
        class="p-1 rounded-lg hover:bg-muted/50 transition-colors"
        onclick={() => collapsed = !collapsed}
      >
        {#if collapsed}
          <ChevronRight class="w-4 h-4" />
        {:else}
          <ChevronDown class="w-4 h-4" />
        {/if}
      </button>
    </div>

    {#if !collapsed}
      <!-- 搜索框 -->
      <div class="px-2 py-1.5 border-b border-border/50">
        <div class="relative">
          <Search class="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <input
            bind:this={searchInputRef}
            bind:value={searchQuery}
            type="text"
            placeholder="搜索节点..."
            class="w-full h-7 pl-7 pr-7 text-xs bg-muted/50 rounded-md border-none focus:outline-none focus:ring-1 focus:ring-primary/50"
          />
          {#if searchQuery}
            <button
              class="absolute right-1.5 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-muted"
              onclick={clearSearch}
            >
              <X class="w-3 h-3 text-muted-foreground" />
            </button>
          {/if}
        </div>
      </div>

      <!-- 节点列表 -->
      <div class="overflow-y-auto p-1.5 space-y-1 scrollbar-hide" style="max-height: {size.height - 90}px;">
        {#if !hasSearchResults()}
          <div class="text-center text-xs text-muted-foreground py-4">
            未找到匹配的节点
          </div>
        {:else}
          {#each categories as category}
            {@const nodes = getFilteredNodes(category.id)}
            {#if nodes.length > 0 || (category.id !== 'favorites' && category.id !== 'frequent')}
              <div>
                <button
                  class="w-full flex items-center gap-1.5 px-1.5 py-1 text-xs font-medium text-muted-foreground hover:text-foreground rounded transition-colors"
                  onclick={() => toggleCategory(category.id)}
                >
                  {#if expandedCategories[category.id]}
                    <ChevronDown class="w-3 h-3" />
                  {:else}
                    <ChevronRight class="w-3 h-3" />
                  {/if}
                  <svelte:component this={category.icon} class="w-3 h-3 {category.color}" />
                  <span class="uppercase tracking-wider">{category.label}</span>
                  <span class="text-[10px] text-muted-foreground/60 ml-auto">{nodes.length}</span>
                </button>

                {#if expandedCategories[category.id]}
                  <div class="space-y-0.5 ml-2">
                    {#if nodes.length === 0}
                      <div class="text-[10px] text-muted-foreground/60 px-2 py-1">
                        {category.id === 'favorites' ? '点击 ★ 收藏节点' : '暂无'}
                      </div>
                    {:else}
                      {#each nodes as nodeDef}
                        {@const Icon = icons[nodeDef.icon] || Terminal}
                        {@const isFavorite = favorites.includes(nodeDef.type)}
                        <div 
                          class="flex items-center gap-1 group"
                          onmouseenter={(e) => onNodeHover(nodeDef, e)}
                          onmouseleave={onNodeLeave}
                        >
                          <button
                            class="flex-1 flex items-center gap-2 px-2 py-1.5 rounded text-left hover:bg-muted/70 transition-colors cursor-grab active:cursor-grabbing text-xs"
                            draggable="true"
                            onclick={() => addNode(nodeDef.type, nodeDef.label)}
                            ondragstart={(e) => onDragStart(e, nodeDef.type, nodeDef.label)}
                          >
                            <Icon class="w-3.5 h-3.5 {categories.find(c => c.id === nodeDef.category)?.color || 'text-muted-foreground'}" />
                            <span class="truncate flex-1">{nodeDef.label}</span>
                            {#if usageCount[nodeDef.type]}
                              <span class="text-[9px] text-muted-foreground/50">{usageCount[nodeDef.type]}</span>
                            {/if}
                          </button>
                          <button
                            class="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all {isFavorite ? '!opacity-100' : ''}"
                            onclick={(e) => toggleFavorite(nodeDef.type, e)}
                            title={isFavorite ? '取消收藏' : '收藏'}
                          >
                            <Star class="w-3 h-3 {isFavorite ? 'text-yellow-500 fill-yellow-500' : 'text-muted-foreground'}" />
                          </button>
                          <button
                            class="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
                            onclick={() => openFullscreen(nodeDef.type, nodeDef.label)}
                            title="全屏打开"
                          >
                            <Maximize2 class="w-3 h-3 text-muted-foreground" />
                          </button>
                        </div>
                      {/each}
                    {/if}
                  </div>
                {/if}
              </div>
            {/if}
          {/each}
        {/if}
      </div>
    {/if}
  </div>
  
  {#if !collapsed}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div 
      class="resize-handle absolute bottom-0 right-0 w-5 h-5 cursor-se-resize flex items-center justify-center opacity-50 hover:opacity-100 transition-all"
      onmousedown={onResizeStart}
    >
      <svg width="16" height="16" viewBox="0 0 16 16" class="text-muted-foreground">
        <path d="M14 2C14 8.627 8.627 14 2 14" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" fill="none"/>
      </svg>
    </div>
  {/if}
</div>

<!-- 悬停预览卡片 -->
{#if hoveredNode}
  <div 
    class="fixed z-[60] p-3 rounded-lg shadow-lg border bg-popover text-popover-foreground max-w-[220px] animate-in fade-in-0 zoom-in-95 duration-150"
    style="left: {hoverPosition.x}px; top: {hoverPosition.y}px;"
    onmouseenter={() => {}}
    onmouseleave={onNodeLeave}
  >
    <div class="font-medium text-sm mb-1">{hoveredNode.label}</div>
    {#if hoveredNode.description}
      <div class="text-xs text-muted-foreground mb-2">{hoveredNode.description}</div>
    {/if}
    <div class="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-muted-foreground/70">
      {#if hoveredNode.inputs?.length}
        <span>输入: {hoveredNode.inputs.join(', ')}</span>
      {/if}
      {#if hoveredNode.outputs?.length}
        <span>输出: {hoveredNode.outputs.join(', ')}</span>
      {/if}
    </div>
  </div>
{/if}
