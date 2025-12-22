<script lang="ts">
  /**
   * NodeTreePalette - 节点树面板
   * 保持原有样式，支持分类展示、搜索过滤、拖拽添加、JSON 导入导出
   */
  import { NODE_DEFINITIONS, getNodesByCategory } from '$lib/stores/nodeRegistry';
  import { flowStore } from '$lib/stores';
  import * as Collapsible from '$lib/components/ui/collapsible';
  import {
    Clipboard, Folder, FileInput, Package, Search, AlertTriangle,
    FolderSync, FileText, Video, Terminal, GripVertical, Download, Upload,
    ChevronRight, ChevronDown, Star, FolderOpen, Archive, Monitor, Type,
    Clock, Link, Trash2, Filter, BookOpen, Image, MousePointer, FolderInput
  } from '@lucide/svelte';

  // 图标映射
  const icons: Record<string, any> = {
    Clipboard, Folder, FileInput, Package, Search, AlertTriangle,
    FolderSync, FileText, Video, Terminal, Image, Clock, Link,
    Trash2, Filter, BookOpen, MousePointer, FolderInput, Download
  };

  // 从 localStorage 加载保存的树结构
  const STORAGE_KEY = 'node-tree-layout';

  let searchQuery = $state('');
  let nodeIdCounter = 1;
  let fileInput: HTMLInputElement;

  // 树结构类型
  interface TreeFolder {
    id: string;
    name: string;
    icon: string;
    expanded: boolean;
    children: TreeFolder[];
    nodeTypes: string[];  // 该文件夹包含的节点类型
  }

  // 默认分类结构
  const defaultTreeData: TreeFolder[] = [
    {
      id: 'favorites',
      name: '收藏',
      icon: 'Star',
      expanded: true,
      children: [],
      nodeTypes: [],
    },
    {
      id: 'input',
      name: '输入',
      icon: 'FileInput',
      expanded: true,
      children: [],
      nodeTypes: NODE_DEFINITIONS.filter(n => n.category === 'input').map(n => n.type),
    },
    {
      id: 'tool',
      name: '工具',
      icon: 'Package',
      expanded: true,
      children: [
        {
          id: 'tool-file',
          name: '文件操作',
          icon: 'Folder',
          expanded: false,
          children: [],
          nodeTypes: ['repacku', 'movea', 'dissolvef', 'trename', 'migratef', 'linku'],
        },
        {
          id: 'tool-archive',
          name: '压缩包',
          icon: 'Archive',
          expanded: false,
          children: [],
          nodeTypes: ['bandia', 'rawfilter', 'findz', 'encodeb'],
        },
        {
          id: 'tool-media',
          name: '媒体',
          icon: 'Video',
          expanded: false,
          children: [],
          nodeTypes: ['enginev', 'formatv', 'kavvka'],
        },
        {
          id: 'tool-system',
          name: '系统',
          icon: 'Monitor',
          expanded: false,
          children: [],
          nodeTypes: ['sleept', 'scoolp', 'reinstallp', 'recycleu', 'owithu'],
        },
        {
          id: 'tool-text',
          name: '文本',
          icon: 'Type',
          expanded: false,
          children: [],
          nodeTypes: ['linedup', 'crashu', 'seriex'],
        },
      ],
      nodeTypes: [],
    },
    {
      id: 'output',
      name: '输出',
      icon: 'Terminal',
      expanded: true,
      children: [],
      nodeTypes: NODE_DEFINITIONS.filter(n => n.category === 'output').map(n => n.type),
    },
  ];

  // 加载树数据
  function loadTreeData(): TreeFolder[] {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.warn('加载节点树布局失败:', e);
      }
    }
    return defaultTreeData;
  }

  let treeData = $state<TreeFolder[]>(loadTreeData());

  // 保存树数据
  function saveTreeData() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(treeData));
  }

  // 添加节点到画布
  function addNode(type: string, label: string) {
    const node = {
      id: `node-${nodeIdCounter++}-${Date.now()}`,
      type,
      position: { x: 250 + Math.random() * 100, y: 150 + Math.random() * 100 },
      data: { label, status: 'idle' as const },
    };
    flowStore.addNode(node);
  }

  // 拖拽开始
  function onDragStart(event: DragEvent, type: string, label: string) {
    if (event.dataTransfer) {
      event.dataTransfer.setData('application/json', JSON.stringify({ type, label }));
      event.dataTransfer.effectAllowed = 'move';
    }
  }

  // 导出 JSON
  function exportJson() {
    const json = JSON.stringify(treeData, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'node-tree-layout.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  // 导入 JSON
  function importJson(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        treeData = data;
        saveTreeData();
      } catch (err) {
        console.error('导入 JSON 失败:', err);
        alert('导入失败：JSON 格式错误');
      }
    };
    reader.readAsText(file);
    input.value = '';
  }

  // 获取节点定义
  function getNodeDef(type: string) {
    return NODE_DEFINITIONS.find(n => n.type === type);
  }

  // 搜索过滤 - 检查节点是否匹配
  function nodeMatches(type: string, query: string): boolean {
    if (!query) return true;
    const def = getNodeDef(type);
    if (!def) return false;
    const q = query.toLowerCase();
    return def.label.toLowerCase().includes(q) || def.type.toLowerCase().includes(q);
  }

  // 搜索过滤 - 检查文件夹是否有匹配的节点
  function folderHasMatches(folder: TreeFolder, query: string): boolean {
    if (!query) return true;
    if (folder.nodeTypes.some(t => nodeMatches(t, query))) return true;
    return folder.children.some(c => folderHasMatches(c, query));
  }

  // 切换文件夹展开状态
  function toggleFolder(folder: TreeFolder) {
    folder.expanded = !folder.expanded;
    saveTreeData();
  }

  // 获取分类颜色
  function getCategoryColor(folderId: string): string {
    if (folderId === 'input' || folderId.startsWith('input')) return 'green';
    if (folderId === 'output' || folderId.startsWith('output')) return 'amber';
    if (folderId === 'favorites') return 'yellow';
    return 'blue';
  }
</script>

<div class="h-full flex flex-col">
  <!-- 工具栏 -->
  <div class="p-3 border-b flex items-center gap-2">
    <div class="relative flex-1">
      <Search class="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
      <input
        type="text"
        placeholder="搜索节点..."
        class="w-full pl-8 pr-2 py-1.5 text-sm rounded border bg-background"
        bind:value={searchQuery}
      />
    </div>
    <button
      class="p-1.5 rounded hover:bg-muted transition-colors"
      onclick={exportJson}
      title="导出 JSON"
    >
      <Download class="w-4 h-4" />
    </button>
    <button
      class="p-1.5 rounded hover:bg-muted transition-colors"
      onclick={() => fileInput.click()}
      title="导入 JSON"
    >
      <Upload class="w-4 h-4" />
    </button>
    <input
      bind:this={fileInput}
      type="file"
      accept=".json"
      class="hidden"
      onchange={importJson}
    />
  </div>

  <!-- 树容器 -->
  <div class="flex-1 overflow-y-auto p-3 space-y-3">
    {#each treeData as folder (folder.id)}
      {#if folderHasMatches(folder, searchQuery)}
        {@const color = getCategoryColor(folder.id)}
        {@const FolderIcon = icons[folder.icon] || Folder}
        <div>
          <!-- 文件夹标题 -->
          <button
            class="w-full flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 hover:text-foreground transition-colors"
            onclick={() => toggleFolder(folder)}
          >
            {#if folder.expanded}
              <ChevronDown class="w-3 h-3" />
            {:else}
              <ChevronRight class="w-3 h-3" />
            {/if}
            <FolderIcon class="w-3.5 h-3.5" />
            <span>{folder.name}</span>
          </button>

          {#if folder.expanded}
            <!-- 节点列表 -->
            <div class="space-y-1 ml-1">
              {#each folder.nodeTypes as nodeType}
                {@const nodeDef = getNodeDef(nodeType)}
                {#if nodeDef && nodeMatches(nodeType, searchQuery)}
                  {@const Icon = icons[nodeDef.icon] || Terminal}
                  <button
                    class="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:border-{color}-400 hover:bg-{color}-50 dark:hover:bg-{color}-950/30 transition-colors cursor-grab active:cursor-grabbing"
                    draggable="true"
                    onclick={() => addNode(nodeDef.type, nodeDef.label)}
                    ondragstart={(e) => onDragStart(e, nodeDef.type, nodeDef.label)}
                  >
                    <GripVertical class="w-3 h-3 text-muted-foreground" />
                    <Icon class="w-4 h-4 text-{color}-600 dark:text-{color}-400" />
                    <span class="text-sm">{nodeDef.label}</span>
                  </button>
                {/if}
              {/each}

              <!-- 子文件夹 -->
              {#each folder.children as subFolder (subFolder.id)}
                {#if folderHasMatches(subFolder, searchQuery)}
                  {@const SubIcon = icons[subFolder.icon] || Folder}
                  <div class="mt-2">
                    <button
                      class="w-full flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-1.5 hover:text-foreground transition-colors pl-2"
                      onclick={() => toggleFolder(subFolder)}
                    >
                      {#if subFolder.expanded}
                        <ChevronDown class="w-3 h-3" />
                      {:else}
                        <ChevronRight class="w-3 h-3" />
                      {/if}
                      <SubIcon class="w-3.5 h-3.5" />
                      <span>{subFolder.name}</span>
                    </button>

                    {#if subFolder.expanded}
                      <div class="space-y-1 ml-3">
                        {#each subFolder.nodeTypes as nodeType}
                          {@const nodeDef = getNodeDef(nodeType)}
                          {#if nodeDef && nodeMatches(nodeType, searchQuery)}
                            {@const Icon = icons[nodeDef.icon] || Terminal}
                            <button
                              class="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:border-{color}-400 hover:bg-{color}-50 dark:hover:bg-{color}-950/30 transition-colors cursor-grab active:cursor-grabbing"
                              draggable="true"
                              onclick={() => addNode(nodeDef.type, nodeDef.label)}
                              ondragstart={(e) => onDragStart(e, nodeDef.type, nodeDef.label)}
                            >
                              <GripVertical class="w-3 h-3 text-muted-foreground" />
                              <Icon class="w-4 h-4 text-{color}-600 dark:text-{color}-400" />
                              <span class="text-sm">{nodeDef.label}</span>
                            </button>
                          {/if}
                        {/each}
                      </div>
                    {/if}
                  </div>
                {/if}
              {/each}
            </div>
          {/if}
        </div>
      {/if}
    {/each}
  </div>

  <!-- 提示 -->
  <div class="p-2 border-t text-xs text-muted-foreground text-center">
    拖拽或点击添加节点
  </div>
</div>
