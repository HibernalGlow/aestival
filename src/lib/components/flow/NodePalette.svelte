<script lang="ts">
  import { NODE_DEFINITIONS, getNodesByCategory } from '$lib/stores/nodeRegistry';
  import { flowStore } from '$lib/stores';
  import {
    Clipboard,
    Folder,
    FileInput,
    Package,
    Search,
    AlertTriangle,
    FolderSync,
    FileText,
    Video,
    Terminal,
    GripVertical,
    RefreshCw
  } from '@lucide/svelte';

  const icons: Record<string, typeof Clipboard> = {
    Clipboard,
    Folder,
    FileInput,
    Package,
    Search,
    AlertTriangle,
    FolderSync,
    FileText,
    Video,
    Terminal
  };

  const categories = [
    { id: 'input', label: '输入', color: 'green' },
    { id: 'tool', label: '工具', color: 'blue' },
    { id: 'output', label: '输出', color: 'amber' }
  ];

  let nodeIdCounter = 1;

  function addNode(type: string, label: string) {
    const node = {
      id: `node-${nodeIdCounter++}-${Date.now()}`,
      type,
      position: { x: 250 + Math.random() * 100, y: 150 + Math.random() * 100 },
      data: { label, status: 'idle' as const }
    };
    flowStore.addNode(node);
  }

  function onDragStart(event: DragEvent, type: string, label: string) {
    if (event.dataTransfer) {
      event.dataTransfer.setData('application/json', JSON.stringify({ type, label }));
      event.dataTransfer.effectAllowed = 'move';
    }
  }
</script>

<div class="w-64 bg-white border-r border-gray-200 flex flex-col h-full">
  <div class="p-4 border-b border-gray-200">
    <div class="flex items-center justify-between">
      <h2 class="font-semibold text-gray-800">节点面板</h2>
      <button
        class="p-1 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors"
        onclick={() => window.location.reload()}
        title="刷新页面"
      >
        <RefreshCw class="w-4 h-4" />
      </button>
    </div>
    <p class="text-xs text-gray-500 mt-1">拖拽或点击添加节点</p>
  </div>

  <div class="flex-1 overflow-y-auto p-3 space-y-4">
    {#each categories as category}
      {@const nodes = getNodesByCategory(category.id)}
      {#if nodes.length > 0}
        <div>
          <h3 class="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
            {category.label}
          </h3>
          <div class="space-y-1">
            {#each nodes as nodeDef}
              {@const Icon = icons[nodeDef.icon] || Terminal}
              <button
                class="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 hover:border-{category.color}-300 hover:bg-{category.color}-50 transition-colors cursor-grab active:cursor-grabbing"
                draggable="true"
                onclick={() => addNode(nodeDef.type, nodeDef.label)}
                ondragstart={(e) => onDragStart(e, nodeDef.type, nodeDef.label)}
              >
                <GripVertical class="w-3 h-3 text-gray-400" />
                <Icon class="w-4 h-4 text-{category.color}-600" />
                <span class="text-sm text-gray-700">{nodeDef.label}</span>
              </button>
            {/each}
          </div>
        </div>
      {/if}
    {/each}
  </div>
</div>
