<script lang="ts">
  /**
   * FormatVNode - 视频格式过滤节点组件
   * 添加/移除 .nov 后缀，检查重复项
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';
  import * as TreeView from '$lib/components/ui/tree-view';

  import { InteractiveHover } from '$lib/components/ui/interactive-hover';
  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { FORMATV_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getApiV1Url } from '$lib/stores/backend';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { getSizeClasses, type SizeMode } from '$lib/utils/sizeUtils';
  import { 
    Play, LoaderCircle, FolderOpen, Clipboard, Video,
    CircleCheck, CircleX, Plus, Minus, Search,
    Copy, Check, RotateCcw, RefreshCw, File, Folder,
    ChevronRight, ChevronDown, Image
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: { path?: string };
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'scanning' | 'processing' | 'completed' | 'error';
  type Action = 'scan' | 'add_nov' | 'remove_nov' | 'check_duplicates';
  type FileCategory = 'normal' | 'nov' | string;

  /** 文件树节点 */
  interface FileTreeNode {
    name: string;
    path: string;
    isDir: boolean;
    children?: FileTreeNode[];
    category?: FileCategory;
  }

  interface ScanResult {
    normal_count: number;
    nov_count: number;
    prefixed_counts: Record<string, number>;
  }

  interface FileListData {
    normal_files: string[];
    nov_files: string[];
    prefixed_files: Record<string, string[]>;
  }

  interface FormatVNodeState {
    phase: Phase;
    progress: number;
    progressText: string;
    scanResult: ScanResult | null;
    duplicateCount: number;
    fileListData: FileListData | null;
  }

  const savedState = getNodeState<FormatVNodeState>(id);

  // 状态
  let targetPath = $state(data?.config?.path ?? 'E:\\1Hub\\EH\\1EHV');
  let phase = $state<Phase>(savedState?.phase ?? 'idle');
  let logs = $state<string[]>(data?.logs ? [...data.logs] : []);
  let hasInputConnection = $state(data?.hasInputConnection ?? false);
  let copied = $state(false);
  let progress = $state(savedState?.progress ?? 0);
  let progressText = $state(savedState?.progressText ?? '');
  let scanResult = $state<ScanResult | null>(savedState?.scanResult ?? null);
  let duplicateCount = $state(savedState?.duplicateCount ?? 0);
  let fileListData = $state<FileListData | null>(savedState?.fileListData ?? null);
  let prefixName = $state('hb');
  let layoutRenderer = $state<any>(undefined);
  
  // 选中的文件（用于预览）
  let selectedFile = $state<string | null>(null);
  // 视图模式
  let viewMode = $state<'tree' | 'list'>('tree');

  // 获取视频缩略图 URL（使用系统缩略图）
  function getThumbnailUrl(filePath: string): string {
    return `${getApiV1Url()}/file?path=${encodeURIComponent(filePath)}&thumbnail=true`;
  }

  function saveState() {
    setNodeState<FormatVNodeState>(id, {
      phase, progress, progressText, scanResult, duplicateCount, fileListData
    });
  }

  let canExecute = $derived(phase === 'idle' && (targetPath.trim() !== '' || hasInputConnection));
  let isRunning = $derived(phase === 'scanning' || phase === 'processing');
  let borderClass = $derived({
    idle: 'border-border',
    scanning: 'border-blue-500 shadow-sm',
    processing: 'border-primary shadow-sm',
    completed: 'border-primary/50',
    error: 'border-destructive/50'
  }[phase]);

  $effect(() => { if (phase || scanResult || fileListData) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  // 获取文件名
  function getFileName(path: string): string {
    return path.split(/[/\\]/).pop() || path;
  }

  /**
   * 构建完整的文件树结构
   * 将所有文件路径合并成一棵树，保留完整的目录层级
   */
  function buildFullFileTree(fileListData: FileListData): FileTreeNode[] {
    // 使用 Map 存储树节点，key 为完整路径
    const nodeMap = new Map<string, FileTreeNode>();
    
    // 处理单个文件，确保所有父目录都存在
    function addFile(filePath: string, category: FileCategory) {
      const parts = filePath.split(/[/\\]/);
      let currentPath = '';
      
      // 创建所有父目录节点
      for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i];
        const parentPath = currentPath;
        currentPath = currentPath ? `${currentPath}\\${part}` : part;
        
        if (!nodeMap.has(currentPath)) {
          const dirNode: FileTreeNode = {
            name: part,
            path: currentPath,
            isDir: true,
            children: []
          };
          nodeMap.set(currentPath, dirNode);
          
          // 添加到父节点的 children
          if (parentPath && nodeMap.has(parentPath)) {
            const parent = nodeMap.get(parentPath)!;
            if (!parent.children!.find(c => c.path === currentPath)) {
              parent.children!.push(dirNode);
            }
          }
        }
      }
      
      // 创建文件节点
      const fileName = parts[parts.length - 1];
      const fileNode: FileTreeNode = {
        name: fileName,
        path: filePath,
        isDir: false,
        category
      };
      nodeMap.set(filePath, fileNode);
      
      // 添加到父目录
      if (currentPath && nodeMap.has(currentPath)) {
        const parent = nodeMap.get(currentPath)!;
        if (!parent.children!.find(c => c.path === filePath)) {
          parent.children!.push(fileNode);
        }
      }
    }
    
    // 添加所有文件
    for (const file of fileListData.normal_files ?? []) {
      addFile(file, 'normal');
    }
    for (const file of fileListData.nov_files ?? []) {
      addFile(file, 'nov');
    }
    for (const [prefix, files] of Object.entries(fileListData.prefixed_files ?? {})) {
      for (const file of files ?? []) {
        addFile(file, prefix);
      }
    }
    
    // 找出根节点（没有父节点的目录）
    const rootNodes: FileTreeNode[] = [];
    for (const [path, node] of nodeMap) {
      if (node.isDir) {
        const parentPath = path.split(/[/\\]/).slice(0, -1).join('\\');
        if (!parentPath || !nodeMap.has(parentPath)) {
          rootNodes.push(node);
        }
      }
    }
    
    // 递归排序所有节点的 children
    function sortChildren(node: FileTreeNode) {
      if (node.children && node.children.length > 0) {
        node.children.sort((a, b) => {
          // 目录在前，文件在后
          if (a.isDir !== b.isDir) return a.isDir ? -1 : 1;
          return a.name.localeCompare(b.name);
        });
        for (const child of node.children) {
          sortChildren(child);
        }
      }
    }
    
    for (const root of rootNodes) {
      sortChildren(root);
    }
    
    // 排序根节点
    rootNodes.sort((a, b) => a.name.localeCompare(b.name));
    
    return rootNodes;
  }
  
  // 计算树中的文件总数
  function countFilesInTree(nodes: FileTreeNode[]): number {
    let count = 0;
    for (const node of nodes) {
      if (node.isDir && node.children) {
        count += countFilesInTree(node.children);
      } else if (!node.isDir) {
        count++;
      }
    }
    return count;
  }

  async function selectFolder() {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFolderDialog('选择目录');
      if (selected) targetPath = selected;
    } catch (e) { log(`选择文件夹失败: ${e}`); }
  }

  async function pasteFromClipboard() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) targetPath = text.trim();
    } catch (e) { log(`读取剪贴板失败: ${e}`); }
  }

  async function executeAction(action: Action) {
    if (!canExecute && action !== 'scan') return;
    
    phase = action === 'scan' ? 'scanning' : 'processing';
    progress = 0;
    progressText = action === 'scan' ? '扫描中...' : '处理中...';
    
    const actionText = {
      scan: '扫描',
      add_nov: '添加 .nov',
      remove_nov: '移除 .nov',
      check_duplicates: '检查重复'
    }[action];
    
    log(`🎬 开始${actionText}: ${targetPath}`);

    try {
      progress = 10;
      const response = await api.executeNode('formatv', {
        path: targetPath,
        action,
        prefix_name: prefixName
      }) as any;

      if (response.success) {
        phase = 'completed';
        progress = 100;
        progressText = '完成';
        
        if (action === 'scan') {
          scanResult = {
            normal_count: response.data?.normal_count ?? 0,
            nov_count: response.data?.nov_count ?? 0,
            prefixed_counts: response.data?.prefixed_counts ?? {}
          };
          fileListData = {
            normal_files: response.data?.normal_files ?? [],
            nov_files: response.data?.nov_files ?? [],
            prefixed_files: response.data?.prefixed_files ?? {}
          };
        } else if (action === 'check_duplicates') {
          duplicateCount = response.data?.duplicate_count ?? 0;
        }
        
        log(`✅ ${response.message}`);
      } else {
        phase = 'error';
        progress = 0;
        log(`❌ 失败: ${response.message}`);
      }
    } catch (error) {
      phase = 'error';
      progress = 0;
      log(`❌ 失败: ${error}`);
    }
  }

  function handleReset() {
    phase = 'idle';
    progress = 0;
    progressText = '';
    scanResult = null;
    duplicateCount = 0;
    fileListData = null;
    selectedFile = null;
    logs = [];
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(logs.join('\n'));
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  // 获取文件类型的颜色
  function getCategoryColor(category: FileCategory): string {
    switch (category) {
      case 'normal': return 'text-green-500';
      case 'nov': return 'text-yellow-500';
      default: return 'text-blue-500';
    }
  }

  // 获取文件类型的标签
  function getCategoryLabel(category: FileCategory): string {
    switch (category) {
      case 'normal': return '普通';
      case 'nov': return '.nov';
      default: return `[${category}]`;
    }
  }
</script>

<!-- 路径输入区块 -->
{#snippet pathBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="{c.mb}">
    <div class="flex items-center gap-1 mb-1 {c.text}">
      <Video class={c.icon} />
      <span class="font-medium">目标目录</span>
    </div>
    {#if !hasInputConnection}
      <div class="flex {c.gap}">
        <Input bind:value={targetPath} placeholder="输入或选择目录..." disabled={isRunning} class="flex-1 {c.input}" />
        <Button variant="outline" size="icon" class="{c.buttonIcon} shrink-0" onclick={selectFolder} disabled={isRunning}>
          <FolderOpen class={c.icon} />
        </Button>
        <Button variant="outline" size="icon" class="{c.buttonIcon} shrink-0" onclick={pasteFromClipboard} disabled={isRunning}>
          <Clipboard class={c.icon} />
        </Button>
      </div>
    {:else}
      <div class="text-muted-foreground {c.padding} bg-muted {c.rounded} flex items-center {c.gap} {c.text}">
        <span>←</span><span>输入来自上游节点</span>
      </div>
    {/if}
  </div>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="flex flex-col {c.gap}">
    {#if size === 'normal'}
      <InteractiveHover text="扫描" class="w-full h-10 text-sm" onclick={() => executeAction('scan')} disabled={!canExecute || isRunning}>
        {#snippet icon()}{#if phase === 'scanning'}<LoaderCircle class="h-4 w-4 animate-spin" />{:else}<RefreshCw class="h-4 w-4" />{/if}{/snippet}
      </InteractiveHover>
      <div class="grid grid-cols-2 gap-2">
        <Button variant="outline" class="h-9" onclick={() => executeAction('add_nov')} disabled={!canExecute || isRunning}>
          <Plus class="h-4 w-4 mr-1" />.nov
        </Button>
        <Button variant="outline" class="h-9" onclick={() => executeAction('remove_nov')} disabled={!canExecute || isRunning}>
          <Minus class="h-4 w-4 mr-1" />.nov
        </Button>
      </div>
      <Button variant="secondary" class="h-9" onclick={() => executeAction('check_duplicates')} disabled={!canExecute || isRunning}>
        <Search class="h-4 w-4 mr-2" />检查重复
      </Button>
      <Button variant="ghost" class="h-8" onclick={handleReset} disabled={isRunning}>
        <RotateCcw class="h-4 w-4 mr-2" />重置
      </Button>
    {:else}
      <div class="flex flex-wrap {c.gap}">
        <Button size="sm" class={c.button} onclick={() => executeAction('scan')} disabled={!canExecute || isRunning}>
          {#if phase === 'scanning'}<LoaderCircle class="{c.icon} mr-1 animate-spin" />{:else}<RefreshCw class="{c.icon} mr-1" />{/if}扫描
        </Button>
        <Button size="sm" variant="outline" class={c.button} onclick={() => executeAction('add_nov')} disabled={!canExecute || isRunning}>
          <Plus class={c.icon} />.nov
        </Button>
        <Button size="sm" variant="outline" class={c.button} onclick={() => executeAction('remove_nov')} disabled={!canExecute || isRunning}>
          <Minus class={c.icon} />.nov
        </Button>
        <Button size="sm" variant="secondary" class={c.button} onclick={() => executeAction('check_duplicates')} disabled={!canExecute || isRunning}>
          <Search class={c.icon} />重复
        </Button>
      </div>
    {/if}
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlock(size: SizeMode)}
  {#if size === 'normal'}
    <div class="space-y-2 flex-1">
      {#if scanResult}
        <div class="flex items-center justify-between p-3 bg-gradient-to-r from-green-500/15 to-green-500/5 rounded-xl border border-green-500/20">
          <span class="text-sm text-muted-foreground">普通视频</span>
          <span class="text-2xl font-bold text-green-600 tabular-nums">{scanResult.normal_count}</span>
        </div>
        <div class="flex items-center justify-between p-3 bg-gradient-to-r from-yellow-500/15 to-yellow-500/5 rounded-xl border border-yellow-500/20">
          <span class="text-sm text-muted-foreground">.nov 文件</span>
          <span class="text-2xl font-bold text-yellow-600 tabular-nums">{scanResult.nov_count}</span>
        </div>
        {#each Object.entries(scanResult.prefixed_counts) as [name, count]}
          {#if count > 0}
            <div class="flex items-center justify-between p-3 bg-gradient-to-r from-blue-500/15 to-blue-500/5 rounded-xl border border-blue-500/20">
              <span class="text-sm text-muted-foreground">[{name}]</span>
              <span class="text-2xl font-bold text-blue-600 tabular-nums">{count}</span>
            </div>
          {/if}
        {/each}
      {:else}
        <div class="text-center text-muted-foreground py-4">扫描后显示统计</div>
      {/if}
    </div>
  {:else}
    {#if scanResult}
      <div class="grid grid-cols-2 gap-1.5">
        <div class="text-center p-1.5 bg-green-500/10 rounded-lg">
          <div class="text-sm font-bold text-green-600 tabular-nums">{scanResult.normal_count}</div>
          <div class="text-[10px] text-muted-foreground">普通</div>
        </div>
        <div class="text-center p-1.5 bg-yellow-500/10 rounded-lg">
          <div class="text-sm font-bold text-yellow-600 tabular-nums">{scanResult.nov_count}</div>
          <div class="text-[10px] text-muted-foreground">.nov</div>
        </div>
      </div>
    {:else}
      <div class="text-xs text-muted-foreground text-center">-</div>
    {/if}
  {/if}
{/snippet}

<!-- 进度区块 -->
{#snippet progressBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if size === 'normal'}
    <div class="h-full flex items-center gap-3">
      {#if phase === 'completed'}
        <CircleCheck class="w-8 h-8 text-green-500 shrink-0" />
        <span class="font-semibold text-green-600">完成</span>
      {:else if phase === 'error'}
        <CircleX class="w-8 h-8 text-red-500 shrink-0" />
        <span class="font-semibold text-red-600">失败</span>
      {:else if isRunning}
        <LoaderCircle class="w-8 h-8 text-primary animate-spin shrink-0" />
        <div class="flex-1">
          <div class="flex justify-between text-sm mb-1"><span>{progressText}</span><span>{progress}%</span></div>
          <Progress value={progress} class="h-2" />
        </div>
      {:else}
        <Video class="w-8 h-8 text-muted-foreground/50 shrink-0" />
        <span class="text-muted-foreground">等待执行</span>
      {/if}
    </div>
  {:else}
    {#if phase === 'completed'}
      <div class="flex items-center gap-2 {c.text}">
        <CircleCheck class="{c.icon} text-green-500" />
        <span class="text-green-600">完成</span>
      </div>
    {:else if isRunning}
      <div class={c.spaceSm}>
        <Progress value={progress} class="h-1.5" />
        <div class="{c.text} text-muted-foreground">{progress}%</div>
      </div>
    {:else}
      <div class="{c.text} text-muted-foreground">等待执行</div>
    {/if}
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
        {#if logs.length > 0}
          {#each logs.slice(-15) as logItem}
            <div class="text-muted-foreground break-all">{logItem}</div>
          {/each}
        {:else}
          <div class="text-muted-foreground text-center py-4">暂无日志</div>
        {/if}
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
      {#each logs.slice(-4) as logItem}
        <div class="text-muted-foreground break-all">{logItem}</div>
      {/each}
    </div>
  {/if}
{/snippet}

<!-- 递归渲染文件树节点 -->
{#snippet renderTreeNode(node: FileTreeNode)}
  {#if node.isDir}
    <TreeView.Folder name={node.name} open={true} class="text-xs">
      {#snippet icon()}
        <Folder class="w-3 h-3 text-yellow-500" />
      {/snippet}
      {#snippet children()}
        {#if node.children}
          {#each node.children as child}
            {@render renderTreeNode(child)}
          {/each}
        {/if}
      {/snippet}
    </TreeView.Folder>
  {:else}
    {@const categoryColor = node.category === 'normal' ? 'text-green-500' : node.category === 'nov' ? 'text-yellow-500' : 'text-blue-500'}
    <button 
      class="flex items-center gap-2 py-1 px-1 w-full text-left hover:bg-muted/50 rounded transition-colors {selectedFile === node.path ? 'bg-primary/10' : ''}"
      onclick={() => selectedFile = node.path}
    >
      <div class="w-10 h-7 rounded bg-muted/50 overflow-hidden shrink-0 flex items-center justify-center relative">
        <img 
          src={getThumbnailUrl(node.path)} 
          alt="" 
          class="w-full h-full object-cover" 
          loading="lazy"
          onerror={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
        />
        <Video class="w-3 h-3 {categoryColor} absolute" />
      </div>
      <span class="truncate flex-1 text-xs" title={node.path}>{node.name}</span>
      {#if node.category && node.category !== 'normal'}
        <span class="text-[10px] px-1 rounded {node.category === 'nov' ? 'bg-yellow-500/20 text-yellow-600' : 'bg-blue-500/20 text-blue-600'}">
          {node.category === 'nov' ? '.nov' : `[${node.category}]`}
        </span>
      {/if}
    </button>
  {/if}
{/snippet}

<!-- 文件树区块 -->
{#snippet treeBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {@const fileTree = fileListData ? buildFullFileTree(fileListData) : []}
  {@const totalFiles = fileListData ? (fileListData.normal_files?.length ?? 0) + (fileListData.nov_files?.length ?? 0) + Object.values(fileListData.prefixed_files ?? {}).reduce((sum, arr) => sum + (arr?.length ?? 0), 0) : 0}
  
  {#if size === 'normal'}
    <div class="h-full flex flex-col overflow-hidden">
      <!-- 标题栏 -->
      <div class="flex items-center justify-between p-2 border-b bg-muted/30 shrink-0">
        <span class="font-semibold flex items-center gap-2">
          <Folder class="w-5 h-5 text-yellow-500" />文件树
        </span>
        <div class="flex items-center gap-3 text-xs">
          <span class="flex items-center gap-1 text-green-600">
            <span class="w-2 h-2 rounded-full bg-green-500"></span>
            {fileListData?.normal_files?.length ?? 0}
          </span>
          <span class="flex items-center gap-1 text-yellow-600">
            <span class="w-2 h-2 rounded-full bg-yellow-500"></span>
            {fileListData?.nov_files?.length ?? 0}
          </span>
          {#each Object.entries(fileListData?.prefixed_files ?? {}) as [prefix, files]}
            {#if files?.length > 0}
              <span class="flex items-center gap-1 text-blue-600">
                <span class="w-2 h-2 rounded-full bg-blue-500"></span>
                [{prefix}] {files.length}
              </span>
            {/if}
          {/each}
        </div>
      </div>
      
      <!-- 文件树内容 -->
      <div class="flex-1 overflow-y-auto p-2">
        {#if fileTree.length > 0}
          <TreeView.Root class="text-sm">
            {#each fileTree as node}
              {@render renderTreeNode(node)}
            {/each}
          </TreeView.Root>
        {:else if fileListData}
          <div class="text-center text-muted-foreground py-8">没有找到视频文件</div>
        {:else}
          <div class="text-center text-muted-foreground py-8">扫描后显示文件树</div>
        {/if}
      </div>
    </div>
  {:else}
    <!-- 紧凑模式 -->
    <div class="flex items-center justify-between mb-2">
      <span class="{c.text} font-semibold flex items-center gap-1">
        <Folder class="w-3 h-3 text-yellow-500" />文件树
      </span>
      <div class="flex items-center gap-2 {c.textSm}">
        <span class="flex items-center gap-0.5 text-green-600">
          <span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>
          {fileListData?.normal_files?.length ?? 0}
        </span>
        <span class="flex items-center gap-0.5 text-yellow-600">
          <span class="w-1.5 h-1.5 rounded-full bg-yellow-500"></span>
          {fileListData?.nov_files?.length ?? 0}
        </span>
      </div>
    </div>
    <div class="{c.maxHeight} overflow-y-auto">
      {#if fileTree.length > 0}
        <TreeView.Root class="text-xs">
          {#each fileTree as node}
            {@render renderTreeNode(node)}
          {/each}
        </TreeView.Root>
      {:else}
        <div class="{c.text} text-muted-foreground text-center py-3">扫描后显示</div>
      {/if}
    </div>
  {/if}
{/snippet}

<!-- 通用区块渲染器 -->
{#snippet renderBlockContent(blockId: string, size: SizeMode)}
  {#if blockId === 'path'}{@render pathBlock(size)}
  {:else if blockId === 'operation'}{@render operationBlock(size)}
  {:else if blockId === 'stats'}{@render statsBlock(size)}
  {:else if blockId === 'progress'}{@render progressBlock(size)}
  {:else if blockId === 'log'}{@render logBlock(size)}
  {:else if blockId === 'tree'}{@render treeBlock(size)}
  {/if}
{/snippet}

<!-- 主渲染 -->
<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 400px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={350} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={id} 
    title="formatv" 
    icon={Video} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="formatv" 
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
        nodeId={id}
        nodeType="formatv"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={FORMATV_DEFAULT_GRID_LAYOUT}
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
