<script lang="ts">
  /**
   * NodeTreePalette - 节点树面板
   * 使用原生拖拽 API 实现：分类内排序 + 拖到画布
   */
  import { NODE_DEFINITIONS } from '$lib/stores/nodeRegistry';
  import { flowStore } from '$lib/stores';
  import { fullscreenNodeStore } from '$lib/stores/fullscreenNode.svelte';
  import {
    Clipboard, Folder, FileInput, Package, Search,
    FolderSync, FileText, Video, Terminal, GripVertical, Download, Upload,
    ChevronRight, ChevronDown, Trash2, Image, MousePointer, FolderInput,
    Clock, Link, BookOpen, TriangleAlert, Maximize2
  } from '@lucide/svelte';

  const icons: Record<string, any> = {
    Clipboard, Folder, FileInput, Package, Search, TriangleAlert,
    FolderSync, FileText, Video, Terminal, Image, Clock, Link,
    Trash2, BookOpen, MousePointer, FolderInput, Download,
    AlertTriangle: TriangleAlert, Filter: Search
  };

  const STORAGE_KEY = 'node-tree-layout';

  let searchQuery = $state('');
  let nodeIdCounter = 1;
  let fileInput: HTMLInputElement;

  // 拖拽排序状态
  let dragState = $state<{
    folderId: string | null;
    itemId: string | null;
    overItemId: string | null;
    overFolderId: string | null;
  }>({ folderId: null, itemId: null, overItemId: null, overFolderId: null });

  interface NodeItem {
    id: string;
    type: string;
    label: string;
    icon: string;
  }

  interface TreeFolder {
    id: string;
    name: string;
    icon: string;
    expanded: boolean;
    items: NodeItem[];
    children: TreeFolder[];
  }

  function buildNodeItem(type: string): NodeItem | null {
    const def = NODE_DEFINITIONS.find(n => n.type === type);
    if (!def) return null;
    return { id: type, type: def.type, label: def.label, icon: def.icon };
  }

  function getDefaultTreeData(): TreeFolder[] {
    return [
      {
        id: 'favorites', name: '收藏', icon: 'Folder', expanded: true, items: [], children: [],
      },
      {
        id: 'input', name: '输入', icon: 'FileInput', expanded: true,
        items: NODE_DEFINITIONS.filter(n => n.category === 'input').map(n => buildNodeItem(n.type)!).filter(Boolean),
        children: [],
      },
      {
        id: 'tool', name: '工具', icon: 'Package', expanded: true, items: [],
        children: [
          { id: 'tool-file', name: '文件操作', icon: 'Folder', expanded: false,
            items: ['repacku', 'movea', 'dissolvef', 'trename', 'migratef', 'linku'].map(t => buildNodeItem(t)!).filter(Boolean), children: [] },
          { id: 'tool-archive', name: '压缩包', icon: 'Package', expanded: false,
            items: ['bandia', 'rawfilter', 'findz', 'encodeb'].map(t => buildNodeItem(t)!).filter(Boolean), children: [] },
          { id: 'tool-media', name: '媒体', icon: 'Video', expanded: false,
            items: ['enginev', 'formatv', 'kavvka'].map(t => buildNodeItem(t)!).filter(Boolean), children: [] },
          { id: 'tool-system', name: '系统', icon: 'Terminal', expanded: false,
            items: ['sleept', 'scoolp', 'reinstallp', 'recycleu', 'owithu'].map(t => buildNodeItem(t)!).filter(Boolean), children: [] },
          { id: 'tool-text', name: '文本', icon: 'FileText', expanded: false,
            items: ['linedup', 'crashu', 'seriex'].map(t => buildNodeItem(t)!).filter(Boolean), children: [] },
        ],
      },
      {
        id: 'output', name: '输出', icon: 'Terminal', expanded: true,
        items: NODE_DEFINITIONS.filter(n => n.category === 'output').map(n => buildNodeItem(n.type)!).filter(Boolean),
        children: [],
      },
    ];
  }

  function loadTreeData(): TreeFolder[] {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const data = JSON.parse(saved);
        if (data.some((f: any) => f.nodeTypes !== undefined)) {
          localStorage.removeItem(STORAGE_KEY);
          return getDefaultTreeData();
        }
        function ensureItems(folders: TreeFolder[]) {
          const seenIds = new Set<string>();
          for (const folder of folders) {
            if (!folder.items) folder.items = [];
            if (!folder.children) folder.children = [];
            folder.items = folder.items.filter(item => {
              if (seenIds.has(item.id)) return false;
              seenIds.add(item.id);
              return true;
            });
            ensureItems(folder.children);
          }
        }
        ensureItems(data);
        return data;
      } catch { localStorage.removeItem(STORAGE_KEY); }
    }
    return getDefaultTreeData();
  }

  let treeData = $state<TreeFolder[]>(loadTreeData());

  function saveTreeData() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(treeData));
  }

  function addNode(type: string, label: string): string {
    const nodeId = `node-${nodeIdCounter++}-${Date.now()}`;
    flowStore.addNode({
      id: nodeId, type,
      position: { x: 250 + Math.random() * 100, y: 150 + Math.random() * 100 },
      data: { label, status: 'idle' as const },
    });
    return nodeId;
  }

  function openFullscreen(type: string, label: string) {
    fullscreenNodeStore.open(addNode(type, label));
  }

  // 查找文件夹
  function findFolder(folderId: string, folders: TreeFolder[] = treeData): TreeFolder | null {
    for (const f of folders) {
      if (f.id === folderId) return f;
      const found = findFolder(folderId, f.children);
      if (found) return found;
    }
    return null;
  }

  // 原生拖拽：开始
  function handleDragStart(e: DragEvent, folderId: string, item: NodeItem) {
    if (!e.dataTransfer) return;
    // 设置数据供画布使用
    e.dataTransfer.setData('application/json', JSON.stringify({ type: item.type, label: item.label }));
    e.dataTransfer.setData('text/plain', `sort:${folderId}:${item.id}`);
    e.dataTransfer.effectAllowed = 'copyMove';
    dragState = { folderId, itemId: item.id, overItemId: null };
  }

  // 原生拖拽：经过（支持跨文件夹）
  function handleDragOver(e: DragEvent, folderId: string, itemId: string) {
    e.preventDefault();
    if (dragState.itemId && dragState.itemId !== itemId) {
      dragState.overItemId = itemId;
      dragState.overFolderId = folderId;
    }
  }

  // 原生拖拽：离开
  function handleDragLeave(e: DragEvent, itemId: string) {
    if (dragState.overItemId === itemId) {
      dragState.overItemId = null;
      dragState.overFolderId = null;
    }
  }

  // 原生拖拽：放置（支持跨文件夹排序）
  function handleDrop(e: DragEvent, targetFolderId: string, targetItemId: string) {
    e.preventDefault();
    const sortData = e.dataTransfer?.getData('text/plain');
    if (!sortData?.startsWith('sort:')) return;

    const [, srcFolderId, srcItemId] = sortData.split(':');
    if (srcItemId === targetItemId) {
      resetDragState();
      return;
    }

    const srcFolder = findFolder(srcFolderId);
    const tgtFolder = findFolder(targetFolderId);
    if (!srcFolder || !tgtFolder) return;

    const srcIdx = srcFolder.items.findIndex(i => i.id === srcItemId);
    if (srcIdx === -1) return;

    // 从源文件夹移除
    const [item] = srcFolder.items.splice(srcIdx, 1);

    // 插入到目标文件夹
    const tgtIdx = tgtFolder.items.findIndex(i => i.id === targetItemId);
    if (tgtIdx === -1) {
      tgtFolder.items.push(item);
    } else {
      tgtFolder.items.splice(tgtIdx, 0, item);
    }

    treeData = [...treeData];
    saveTreeData();
    resetDragState();
  }

  // 拖拽到空文件夹区域
  function handleDropOnFolder(e: DragEvent, folderId: string) {
    e.preventDefault();
    const sortData = e.dataTransfer?.getData('text/plain');
    if (!sortData?.startsWith('sort:')) return;

    const [, srcFolderId, srcItemId] = sortData.split(':');
    if (srcFolderId === folderId) {
      resetDragState();
      return;
    }

    const srcFolder = findFolder(srcFolderId);
    const tgtFolder = findFolder(folderId);
    if (!srcFolder || !tgtFolder) return;

    const srcIdx = srcFolder.items.findIndex(i => i.id === srcItemId);
    if (srcIdx === -1) return;

    const [item] = srcFolder.items.splice(srcIdx, 1);
    tgtFolder.items.push(item);

    treeData = [...treeData];
    saveTreeData();
    resetDragState();
  }

  function resetDragState() {
    dragState = { folderId: null, itemId: null, overItemId: null, overFolderId: null };
  }

  // 拖拽结束
  function handleDragEnd() {
    resetDragState();
  }

  function exportJson() {
    const blob = new Blob([JSON.stringify(treeData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'node-tree-layout.json'; a.click();
    URL.revokeObjectURL(url);
  }

  function importJson(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        treeData = JSON.parse(e.target?.result as string);
        saveTreeData();
      } catch { alert('导入失败：JSON 格式错误'); }
    };
    reader.readAsText(file);
    (event.target as HTMLInputElement).value = '';
  }

  function resetLayout() {
    treeData = getDefaultTreeData();
    saveTreeData();
  }

  function nodeMatches(item: NodeItem, query: string): boolean {
    if (!query) return true;
    const q = query.toLowerCase();
    return item.label.toLowerCase().includes(q) || item.type.toLowerCase().includes(q);
  }

  function folderHasMatches(folder: TreeFolder, query: string): boolean {
    if (!query) return true;
    return folder.items.some(item => nodeMatches(item, query)) || folder.children.some(c => folderHasMatches(c, query));
  }

  function toggleFolder(folder: TreeFolder) {
    folder.expanded = !folder.expanded;
    treeData = [...treeData];
    saveTreeData();
  }

  function getCategoryColor(folderId: string): string {
    if (folderId === 'input' || folderId.startsWith('input')) return 'green';
    if (folderId === 'output' || folderId.startsWith('output')) return 'amber';
    if (folderId === 'favorites') return 'yellow';
    if (folderId === 'tool-file') return 'blue';
    if (folderId === 'tool-archive') return 'purple';
    if (folderId === 'tool-media') return 'pink';
    if (folderId === 'tool-system') return 'orange';
    if (folderId === 'tool-text') return 'cyan';
    if (folderId === 'tool') return 'indigo';
    return 'blue';
  }
</script>

<div class="h-full flex flex-col">
  <div class="p-3 border-b flex items-center gap-2">
    <div class="relative flex-1">
      <Search class="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
      <input type="text" placeholder="搜索节点..." class="w-full pl-8 pr-2 py-1.5 text-sm rounded border bg-background" bind:value={searchQuery} />
    </div>
    <button class="p-1.5 rounded hover:bg-muted transition-colors" onclick={resetLayout} title="重置布局"><Trash2 class="w-4 h-4" /></button>
    <button class="p-1.5 rounded hover:bg-muted transition-colors" onclick={exportJson} title="导出 JSON"><Download class="w-4 h-4" /></button>
    <button class="p-1.5 rounded hover:bg-muted transition-colors" onclick={() => fileInput.click()} title="导入 JSON"><Upload class="w-4 h-4" /></button>
    <input bind:this={fileInput} type="file" accept=".json" class="hidden" onchange={importJson} />
  </div>

  <div class="flex-1 overflow-y-auto p-3 space-y-3">
    {#each treeData as folder (folder.id)}
      {#if folderHasMatches(folder, searchQuery)}
        {@const color = getCategoryColor(folder.id)}
        {@const FolderIcon = icons[folder.icon] || Folder}
        <div>
          <button class="w-full flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 hover:text-foreground transition-colors" onclick={() => toggleFolder(folder)}>
            {#if folder.expanded}<ChevronDown class="w-3 h-3" />{:else}<ChevronRight class="w-3 h-3" />{/if}
            <FolderIcon class="w-3.5 h-3.5 text-{color}-500" />
            <span>{folder.name}</span>
            {#if folder.items.length > 0}<span class="text-[10px] opacity-50">({folder.items.length})</span>{/if}
          </button>

          {#if folder.expanded}
            {#if folder.items.length > 0}
              <div 
                class="space-y-1 ml-1"
                ondragover={(e) => e.preventDefault()}
                ondrop={(e) => handleDropOnFolder(e, folder.id)}
              >
                {#each folder.items.filter(item => nodeMatches(item, searchQuery)) as item (item.id)}
                  {@const Icon = icons[item.icon] || Terminal}
                  {@const isOver = dragState.overItemId === item.id && dragState.overFolderId === folder.id}
                  <div class="flex items-center gap-1 group">
                    <div
                      class="flex-1 flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors cursor-grab active:cursor-grabbing bg-card
                        {isOver ? 'border-primary bg-primary/10' : 'border-border hover:border-' + color + '-400 hover:bg-' + color + '-50 dark:hover:bg-' + color + '-950/30'}"
                      draggable="true"
                      ondragstart={(e) => handleDragStart(e, folder.id, item)}
                      ondragover={(e) => handleDragOver(e, folder.id, item.id)}
                      ondragleave={(e) => handleDragLeave(e, item.id)}
                      ondrop={(e) => handleDrop(e, folder.id, item.id)}
                      ondragend={handleDragEnd}
                      onclick={() => addNode(item.type, item.label)}
                      onkeydown={(e) => e.key === 'Enter' && addNode(item.type, item.label)}
                      role="button"
                      tabindex="0"
                    >
                      <GripVertical class="w-3 h-3 text-muted-foreground" />
                      <Icon class="w-4 h-4 text-{color}-600 dark:text-{color}-400" />
                      <span class="text-sm text-left flex-1">{item.label}</span>
                    </div>
                    <button class="p-1.5 rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all" onclick={() => openFullscreen(item.type, item.label)} title="全屏打开">
                      <Maximize2 class="w-3.5 h-3.5 text-muted-foreground" />
                    </button>
                  </div>
                {/each}
              </div>
            {/if}

            {#each folder.children as subFolder (subFolder.id)}
              {#if folderHasMatches(subFolder, searchQuery)}
                {@const SubIcon = icons[subFolder.icon] || Folder}
                {@const subColor = getCategoryColor(subFolder.id)}
                <div class="mt-2 ml-2">
                  <button class="w-full flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-1.5 hover:text-foreground transition-colors" onclick={() => toggleFolder(subFolder)}>
                    {#if subFolder.expanded}<ChevronDown class="w-3 h-3" />{:else}<ChevronRight class="w-3 h-3" />{/if}
                    <SubIcon class="w-3.5 h-3.5 text-{subColor}-500" />
                    <span>{subFolder.name}</span>
                    <span class="text-[10px] opacity-50">({subFolder.items.length})</span>
                  </button>

                  {#if subFolder.expanded}
                    <div 
                      class="space-y-1 ml-3"
                      ondragover={(e) => e.preventDefault()}
                      ondrop={(e) => handleDropOnFolder(e, subFolder.id)}
                    >
                      {#each subFolder.items.filter(item => nodeMatches(item, searchQuery)) as item (item.id)}
                        {@const Icon = icons[item.icon] || Terminal}
                        {@const isOver = dragState.overItemId === item.id && dragState.overFolderId === subFolder.id}
                        <div class="flex items-center gap-1 group">
                          <div
                            class="flex-1 flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors cursor-grab active:cursor-grabbing bg-card
                              {isOver ? 'border-primary bg-primary/10' : 'border-border hover:border-' + subColor + '-400 hover:bg-' + subColor + '-50 dark:hover:bg-' + subColor + '-950/30'}"
                            draggable="true"
                            ondragstart={(e) => handleDragStart(e, subFolder.id, item)}
                            ondragover={(e) => handleDragOver(e, subFolder.id, item.id)}
                            ondragleave={(e) => handleDragLeave(e, item.id)}
                            ondrop={(e) => handleDrop(e, subFolder.id, item.id)}
                            ondragend={handleDragEnd}
                            onclick={() => addNode(item.type, item.label)}
                            onkeydown={(e) => e.key === 'Enter' && addNode(item.type, item.label)}
                            role="button"
                            tabindex="0"
                          >
                            <GripVertical class="w-3 h-3 text-muted-foreground" />
                            <Icon class="w-4 h-4 text-{subColor}-600 dark:text-{subColor}-400" />
                            <span class="text-sm text-left flex-1">{item.label}</span>
                          </div>
                          <button class="p-1.5 rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all" onclick={() => openFullscreen(item.type, item.label)} title="全屏打开">
                            <Maximize2 class="w-3.5 h-3.5 text-muted-foreground" />
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

  <div class="p-2 border-t text-xs text-muted-foreground text-center">
    拖拽排序或到画布 · 点击添加
  </div>
</div>
