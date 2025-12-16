<script lang="ts">
  /**
   * 浮动节点面板 - 可拖拽的节点选择器
   */
  import { getNodesByCategory } from '$lib/stores/nodeRegistry';
  import { flowStore } from '$lib/stores';
  import { fullscreenNodeStore } from '$lib/stores/fullscreenNode.svelte';
  import {
    Clipboard, Folder, FileInput, Package, Search, AlertTriangle,
    FolderSync, FileText, Video, Terminal, GripHorizontal, ChevronDown, ChevronRight,
    Maximize2
  } from '@lucide/svelte';
  import { settingsManager } from '$lib/settings/settingsManager';
  import { onMount } from 'svelte';

  // 获取面板设置
  let panelSettings = $state(settingsManager.getSettings().panels);
  
  // 计算侧边栏样式
  let sidebarStyle = $derived(
    `background-color: hsl(var(--card) / ${panelSettings.sidebarOpacity / 100}); backdrop-filter: blur(${panelSettings.sidebarBlur}px);`
  );

  onMount(() => {
    // 监听设置变化
    settingsManager.addListener((s) => {
      panelSettings = s.panels;
    });
  });

  const icons: Record<string, typeof Clipboard> = {
    Clipboard, Folder, FileInput, Package, Search, AlertTriangle,
    FolderSync, FileText, Video, Terminal
  };

  const categories = [
    { id: 'input', label: '输入', color: 'text-green-600' },
    { id: 'tool', label: '工具', color: 'text-blue-600' },
    { id: 'output', label: '输出', color: 'text-amber-600' }
  ];

  // 拖拽状态
  let isDragging = $state(false);
  let position = $state({ x: 20, y: 100 });
  let dragOffset = { x: 0, y: 0 };
  let collapsed = $state(false);
  let expandedCategories = $state<Record<string, boolean>>({ input: true, tool: true, output: true });

  let nodeIdCounter = 1;

  function onMouseDown(e: MouseEvent) {
    if ((e.target as HTMLElement).closest('button')) return;
    isDragging = true;
    dragOffset = { x: e.clientX - position.x, y: e.clientY - position.y };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }

  function onMouseMove(e: MouseEvent) {
    if (!isDragging) return;
    position = { x: e.clientX - dragOffset.x, y: e.clientY - dragOffset.y };
  }

  function onMouseUp() {
    isDragging = false;
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('mouseup', onMouseUp);
  }

  function addNode(type: string, label: string) {
    const node = {
      id: `node-${nodeIdCounter++}-${Date.now()}`,
      type,
      position: { x: 300 + Math.random() * 100, y: 200 + Math.random() * 100 },
      data: { label, status: 'idle' as const }
    };
    flowStore.addNode(node);
  }

  function openFullscreen(type: string) {
    fullscreenNodeStore.open(type);
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
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="fixed z-50 border rounded-lg shadow-lg select-none w-48"
  style="left: {position.x}px; top: {position.y}px; {sidebarStyle}"
  onmousedown={onMouseDown}
>
  <!-- 标题栏 -->
  <div class="flex items-center justify-between px-3 py-2 border-b cursor-move">
    <div class="flex items-center gap-2">
      <GripHorizontal class="w-4 h-4 text-muted-foreground" />
      <span class="text-sm font-semibold">节点</span>
    </div>
    <button
      class="p-0.5 rounded hover:bg-muted"
      onclick={() => collapsed = !collapsed}
    >
      {#if collapsed}
        <ChevronRight class="w-4 h-4" />
      {:else}
        <ChevronDown class="w-4 h-4" />
      {/if}
    </button>
  </div>

  <!-- 节点列表 -->
  {#if !collapsed}
    <div class="max-h-80 overflow-y-auto p-2 space-y-2">
      {#each categories as category}
        {@const nodes = getNodesByCategory(category.id)}
        {#if nodes.length > 0}
          <div>
            <button
              class="w-full flex items-center gap-1 text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1 hover:text-foreground"
              onclick={() => toggleCategory(category.id)}
            >
              {#if expandedCategories[category.id]}
                <ChevronDown class="w-3 h-3" />
              {:else}
                <ChevronRight class="w-3 h-3" />
              {/if}
              {category.label}
            </button>
            {#if expandedCategories[category.id]}
              <div class="space-y-0.5 ml-1">
                {#each nodes as nodeDef}
                  {@const Icon = icons[nodeDef.icon] || Terminal}
                  <div class="flex items-center gap-1 group">
                    <button
                      class="flex-1 flex items-center gap-2 px-2 py-1.5 rounded text-left hover:bg-muted transition-colors cursor-grab active:cursor-grabbing text-sm"
                      draggable="true"
                      onclick={() => addNode(nodeDef.type, nodeDef.label)}
                      ondragstart={(e) => onDragStart(e, nodeDef.type, nodeDef.label)}
                    >
                      <Icon class="w-3.5 h-3.5 {category.color}" />
                      <span class="truncate">{nodeDef.label}</span>
                    </button>
                    <!-- 全屏打开按钮 -->
                    <button
                      class="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
                      onclick={() => openFullscreen(nodeDef.type)}
                      title="全屏打开"
                    >
                      <Maximize2 class="w-3 h-3 text-muted-foreground" />
                    </button>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
      {/each}
    </div>
  {/if}
</div>
