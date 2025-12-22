<script lang="ts">
  /**
   * NodeTreePalette - 节点树面板
   * 支持分类展示、搜索过滤、拖拽添加到画布、拖拽移动分类、JSON 导入导出
   */
  import { NODE_DEFINITIONS } from '$lib/stores/nodeRegistry';
  import { flowStore } from '$lib/stores';
  import { dndzone, SOURCES, TRIGGERS } from 'svelte-dnd-action';
  import {
    Clipboard, Folder, FileInput, Package, Search, AlertTriangle,
    FolderSync, FileText, Video, Terminal, GripVertical, Download, Upload,
    ChevronRight, ChevronDown, Star, Archive, Monitor, Type,
    Clock, Link, Trash2, Filter, BookOpen, Image, MousePointer, FolderInput
  } from '@lucide/svelte';

  // 图标映射
  const icons: Record<string, any> = {
    Clipboard, Folder, FileInput, Package, Search, AlertTriangle,
    FolderSync, FileText, Video, Terminal, Image, Clock, Link,
    Trash2, Filter, BookOpen, MousePointer, FolderInput, Download
  };

  const STORAGE_KEY = 'node-tree-layout';
  const flipDurationMs = 200;

  let searchQuery = $state('');
  let nodeIdCounter = 1;
  let fileInput: HTMLInputElement;
  let dragDisabled = $state(true);  // 默认禁用拖拽，按住手柄才启用

  // 节点项类型
  interface NodeItem {
    id: string;
    type: string;
    label: string;
    icon: string;
  }

  // 文件夹类型
  interface TreeFolder {
    id: string;
    name: string;
    icon: string;
    expanded: boolean;
    items: NodeItem[];
    children: TreeFolder[];
  }

  // 从 NODE_DEFINITIONS 构建节点项
  function buildNodeItem(type: string): NodeItem | null {
    const def = NODE_DEFINITIONS.find(n => n.type === type);
    if (!def) return null;
    return { id: type, type: def.type, label: def.label, icon: def.icon };
  }

  // 默认分类结构
  function getDefaultTreeData(): TreeFolder[] {
    return [
      {
        id: 'favorites',
        name: '收藏',
        icon: 'Star',
        expanded: true,
        items: [],
        children: [],
      },
      {
        id: 'input',
        name: '输入',
        icon: 'FileInput',
        expanded: true,
        items: NODE_DEFINITIONS.filter(n => n.category === 'input')
          .map(n => buildNodeItem(n.type)!).filter(Boolean),
        children: [],
      },
      {
        id: 'tool',
        name: '工具',
        icon: 'Package',
        expanded: true,
        items: [],
        children: [
          {
            id: 'tool-file',
            name: '文件操作',
            icon: 'Folder',
            expanded: false,
            items: ['repacku', 'movea', 'dissolvef', 'trename', 'migratef', 'linku']
              .map(t => buildNodeItem(t)!).filter(Boolean),
            children: [],
          },
          {
            id: 'tool-archive',
            name: '压缩包',
            icon: 'Archive',
            expanded: false,
            items: ['bandia', 'rawfilter', 'findz', 'encodeb']
              .map(t => buildNodeItem(t)!).filter(Boolean),
            children: [],
          },
          {
            id: 'tool-media',
            name: '媒体',
            icon: 'Video',
            expanded: false,
            items: ['enginev', 'formatv', 'kavvka']
              .map(t => buildNodeItem(t)!).filter(Boolean),
            children: [],
          },
          {
            id: 'tool-system',
            name: '系统',
            icon: 'Monitor',
            expanded: false,
            items: ['sleept', 'scoolp', 'reinstallp', 'recycleu', 'owithu']
              .map(t => buildNodeItem(t)!).filter(Boolean),
            children: [],
          },
          {
            id: 'tool-text',
            name: '文本',
            icon: 'Type',
            expanded: false,
            items: ['linedup', 'crashu', 'seriex']
              .map(t => buildNodeItem(t)!).filter(Boolean),
            children: [],
          },
        ],
      },
      {
        id: 'output',
        name: '输出',
        icon: 'Terminal',
        expanded: true,
        items: NODE_DEFINITIONS.filter(n => n.category === 'output')
          .map(n => buildNodeItem(n.type)!).filter(Boolean),
        children: [],
      },
    ];
  }

  // 加载树数据
  function loadTreeData(): TreeFolder[] {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const data = JSON.parse(saved);
        // 检查是否是旧格式（有 nodeTypes 而没有 items）
        const isOldFormat = data.some((f: any) => f.nodeTypes !== undefined && f.items === undefined);
        if (isOldFormat) {
          console.warn('检测到旧格式数据，使用默认布局');
          localStorage.removeItem(STORAGE_KEY);
          return getDefaultTreeData();
        }
        // 确保每个文件夹都有 items 数组
        function ensureItems(folders: TreeFolder[]) {
          for (const folder of folders) {
            if (!folder.items) folder.items = [];
            if (!folder.children) folder.children = [];
            ensureItems(folder.children);
          }
        }
        ensureItems(data);
        return data;
      } catch (e) {
        console.warn('加载节点树布局失败，使用默认布局:', e);
        localStorage.removeItem(STORAGE_KEY);
      }
    }
    return getDefaultTreeData();
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

  // 拖拽到画布
  function onDragStartToCanvas(event: DragEvent, type: string, label: string) {
    if (event.dataTransfer) {
      event.dataTransfer.setData('application/json', JSON.stringify({ type, label }));
      event.dataTransfer.effectAllowed = 'copy';
    }
  }

  // 处理 dnd 拖拽（分类内排序）
  function handleDndConsider(folderId: string, e: CustomEvent<{ items: NodeItem[] }>) {
    updateFolderItems(folderId, e.detail.items);
  }

  function handleDndFinalize(folderId: string, e: CustomEvent<{ items: NodeItem[] }>) {
    updateFolderItems(folderId, e.detail.items);
    saveTreeData();
  }

  // 更新文件夹的 items
  function updateFolderItems(folderId: string, items: NodeItem[]) {
    function update(folders: TreeFolder[]): boolean {
      for (const folder of folders) {
        if (folder.id === folderId) {
          folder.items = items;
          return true;
        }
        if (update(folder.children)) return true;
      }
      return false;
    }
    update(treeData);
    treeData = [...treeData];  // 触发响应式更新
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

  // 重置布局
  function resetLayout() {
    treeData = getDefaultTreeData();
    saveTreeData();
  }

  // 搜索过滤
  function nodeMatches(item: NodeItem, query: string): boolean {
    if (!query) return true;
    const q = query.toLowerCase();
    return item.label.toLowerCase().includes(q) || item.type.toLowerCase().includes(q);
  }

  function folderHasMatches(folder: TreeFolder, query: string): boolean {
    if (!query) return true;
    if (folder.items.some(item => nodeMatches(item, query))) return true;
    return folder.children.some(c => folderHasMatches(c, query));
  }

  // 切换文件夹展开状态
  function toggleFolder(folder: TreeFolder) {
    folder.expanded = !folder.expanded;
    treeData = [...treeData];
    saveTreeData();
  }

  // 获取分类颜色
  function getCategoryColor(folderId: string): string {
    if (folderId === 'input' || folderId.startsWith('input')) return 'green';
    if (folderId === 'output' || folderId.startsWith('output')) return 'amber';
    if (folderId === 'favorites') return 'yellow';
    return 'blue';
  }

  // 启用拖拽（按住手柄时）
  function startDrag(e: Event) {
    e.preventDefault();
    dragDisabled = false;
  }

  // 拖拽结束后禁用
  function handleDragEnd() {
    dragDisabled = true;
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
      onclick={resetLayout}
      title="重置布局"
    >
      <Trash2 class="w-4 h-4" />
    </button>
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
            <span class="text-[10px] opacity-50">({folder.items.length})</span>
          </button>

          {#if folder.expanded}
            <!-- 节点列表 - 支持拖拽排序（仅当有节点时显示） -->
            {#if folder.items.length > 0}
              <div
                class="space-y-1 ml-1"
                use:dndzone={{
                  items: folder.items,
                  flipDurationMs,
                  dragDisabled: dragDisabled || !!searchQuery,
                  dropTargetStyle: { outline: '2px dashed hsl(var(--primary))', outlineOffset: '-2px' }
                }}
                onconsider={(e) => handleDndConsider(folder.id, e)}
                onfinalize={(e) => { handleDndFinalize(folder.id, e); handleDragEnd(); }}
              >
              {#each folder.items.filter(item => nodeMatches(item, searchQuery)) as item (item.id)}
                {@const Icon = icons[item.icon] || Terminal}
                <div
                  class="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:border-{color}-400 hover:bg-{color}-50 dark:hover:bg-{color}-950/30 transition-colors bg-card"
                  draggable="true"
                  ondragstart={(e) => onDragStartToCanvas(e, item.type, item.label)}
                >
                  <!-- svelte-ignore a11y_no_static_element_interactions -->
                  <div
                    class="cursor-grab active:cursor-grabbing touch-none"
                    onmousedown={startDrag}
                    ontouchstart={startDrag}
                  >
                    <GripVertical class="w-3 h-3 text-muted-foreground" />
                  </div>
                  <button
                    class="flex-1 flex items-center gap-2 text-left"
                    onclick={() => addNode(item.type, item.label)}
                  >
                    <Icon class="w-4 h-4 text-{color}-600 dark:text-{color}-400" />
                    <span class="text-sm">{item.label}</span>
                  </button>
                </div>
              {/each}
              </div>
            {/if}

            <!-- 子文件夹 -->
            {#each folder.children as subFolder (subFolder.id)}
              {#if folderHasMatches(subFolder, searchQuery)}
                {@const SubIcon = icons[subFolder.icon] || Folder}
                <div class="mt-2 ml-2">
                  <button
                    class="w-full flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-1.5 hover:text-foreground transition-colors"
                    onclick={() => toggleFolder(subFolder)}
                  >
                    {#if subFolder.expanded}
                      <ChevronDown class="w-3 h-3" />
                    {:else}
                      <ChevronRight class="w-3 h-3" />
                    {/if}
                    <SubIcon class="w-3.5 h-3.5" />
                    <span>{subFolder.name}</span>
                    <span class="text-[10px] opacity-50">({subFolder.items.length})</span>
                  </button>

                  {#if subFolder.expanded}
                    <div
                      class="space-y-1 ml-3 min-h-[20px]"
                      use:dndzone={{
                        items: subFolder.items,
                        flipDurationMs,
                        dragDisabled: dragDisabled || !!searchQuery,
                        dropTargetStyle: { outline: '2px dashed hsl(var(--primary))', outlineOffset: '-2px' }
                      }}
                      onconsider={(e) => handleDndConsider(subFolder.id, e)}
                      onfinalize={(e) => { handleDndFinalize(subFolder.id, e); handleDragEnd(); }}
                    >
                      {#each subFolder.items.filter(item => nodeMatches(item, searchQuery)) as item (item.id)}
                        {@const Icon = icons[item.icon] || Terminal}
                        <div
                          class="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:border-{color}-400 hover:bg-{color}-50 dark:hover:bg-{color}-950/30 transition-colors bg-card"
                          draggable="true"
                          ondragstart={(e) => onDragStartToCanvas(e, item.type, item.label)}
                        >
                          <!-- svelte-ignore a11y_no_static_element_interactions -->
                          <div
                            class="cursor-grab active:cursor-grabbing touch-none"
                            onmousedown={startDrag}
                            ontouchstart={startDrag}
                          >
                            <GripVertical class="w-3 h-3 text-muted-foreground" />
                          </div>
                          <button
                            class="flex-1 flex items-center gap-2 text-left"
                            onclick={() => addNode(item.type, item.label)}
                          >
                            <Icon class="w-4 h-4 text-{color}-600 dark:text-{color}-400" />
                            <span class="text-sm">{item.label}</span>
                          </button>
                        </div>
                      {/each}
                    </div>
                  {/if}
                </div>
              {/if}
            {/each}
          {/if}
        </div>
      {/if}
    {/each}
  </div>

  <!-- 提示 -->
  <div class="p-2 border-t text-xs text-muted-foreground text-center">
    拖拽到画布添加 · 拖拽手柄排序
  </div>
</div>
