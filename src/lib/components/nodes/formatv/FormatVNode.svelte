<script lang="ts">
  /**
   * FormatVNode - 视频格式过滤节点组件
   * 添加/移除 .nov 后缀，检查重复项
   * 
   * 使用 Container Query 自动响应尺寸
   * - 一套 HTML 结构，CSS 控制尺寸变化
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
  import { 
    LoaderCircle, FolderOpen, Clipboard, Video,
    CircleCheck, CircleX, Plus, Minus, Search,
    Copy, Check, RotateCcw, RefreshCw, Folder
  } from '@lucide/svelte';

  /** NodeLayoutRenderer 组件实例类型 */
  interface LayoutRendererInstance {
    compact: () => void;
    resetLayout: () => Promise<void>;
    getCurrentLayout: () => import('$lib/components/ui/dashboard-grid').GridItem[];
    getCurrentTabGroups: () => { id: string; blockIds: string[]; activeIndex: number }[];
    applyLayout: (layout: import('$lib/components/ui/dashboard-grid').GridItem[], tabGroups?: { id: string; blockIds: string[]; activeIndex: number }[] | null) => Promise<void>;
    createTab: (blockIds: string[]) => Promise<string | null>;
  }

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
    targetPath?: string;
    logs?: string[];
  }

  // 使用 $derived 确保响应式
  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<FormatVNodeState>(nodeId));
  const configPath = $derived(data?.config?.path ?? 'E:\\1Hub\\EH\\1EHV');
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  // 状态
  let targetPath = $state('E:\\1Hub\\EH\\1EHV');
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let hasInputConnection = $state(false);
  let copiedLogs = $state(false);
  let progress = $state(0);
  let progressText = $state('');
  let scanResult = $state<ScanResult | null>(null);
  let duplicateCount = $state(0);
  let fileListData = $state<FileListData | null>(null);
  let layoutRenderer = $state<LayoutRendererInstance | undefined>(undefined);
  
  // 选中的文件（用于预览）
  let selectedFile = $state<string | null>(null);

  // 初始化标记，防止 $effect 覆盖用户输入
  let initialized = $state(false);

  // 初始化状态（只执行一次）
  $effect(() => {
    if (initialized) return;
    
    targetPath = savedState?.targetPath ?? configPath;
    logs = savedState?.logs ?? [...dataLogs];
    hasInputConnection = dataHasInputConnection;
    
    if (savedState) {
      phase = savedState.phase ?? 'idle';
      progress = savedState.progress ?? 0;
      progressText = savedState.progressText ?? '';
      scanResult = savedState.scanResult ?? null;
      duplicateCount = savedState.duplicateCount ?? 0;
      fileListData = savedState.fileListData ?? null;
    }
    
    initialized = true;
  });

  // 同步外部连接状态
  $effect(() => {
    if (!initialized) return;
    hasInputConnection = dataHasInputConnection;
  });

  // 获取视频缩略图 URL（使用系统缩略图）
  function getThumbnailUrl(filePath: string): string {
    return `${getApiV1Url()}/file?path=${encodeURIComponent(filePath)}&thumbnail=true`;
  }

  function saveState() {
    setNodeState<FormatVNodeState>(nodeId, {
      phase, progress, progressText, scanResult, duplicateCount, fileListData, targetPath, logs
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

  /**
   * 构建完整的文件树结构
   */
  function buildFullFileTree(fileListData: FileListData): FileTreeNode[] {
    const nodeMap = new Map<string, FileTreeNode>();
    
    function addFile(filePath: string, category: FileCategory) {
      const parts = filePath.split(/[/\\]/);
      let currentPath = '';
      
      for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i];
        const parentPath = currentPath;
        currentPath = currentPath ? `${currentPath}\\${part}` : part;
        
        if (!nodeMap.has(currentPath)) {
          const dirNode: FileTreeNode = { name: part, path: currentPath, isDir: true, children: [] };
          nodeMap.set(currentPath, dirNode);
          if (parentPath && nodeMap.has(parentPath)) {
            const parent = nodeMap.get(parentPath)!;
            if (!parent.children!.find(c => c.path === currentPath)) parent.children!.push(dirNode);
          }
        }
      }
      
      const fileName = parts[parts.length - 1];
      const fileNode: FileTreeNode = { name: fileName, path: filePath, isDir: false, category };
      nodeMap.set(filePath, fileNode);
      if (currentPath && nodeMap.has(currentPath)) {
        const parent = nodeMap.get(currentPath)!;
        if (!parent.children!.find(c => c.path === filePath)) parent.children!.push(fileNode);
      }
    }
    
    for (const file of fileListData.normal_files ?? []) addFile(file, 'normal');
    for (const file of fileListData.nov_files ?? []) addFile(file, 'nov');
    for (const [prefix, files] of Object.entries(fileListData.prefixed_files ?? {})) {
      for (const file of files ?? []) addFile(file, prefix);
    }
    
    const rootNodes: FileTreeNode[] = [];
    for (const [path, node] of nodeMap) {
      if (node.isDir) {
        const parentPath = path.split(/[/\\]/).slice(0, -1).join('\\');
        if (!parentPath || !nodeMap.has(parentPath)) rootNodes.push(node);
      }
    }
    
    function sortChildren(node: FileTreeNode) {
      if (node.children && node.children.length > 0) {
        node.children.sort((a, b) => {
          if (a.isDir !== b.isDir) return a.isDir ? -1 : 1;
          return a.name.localeCompare(b.name);
        });
        for (const child of node.children) sortChildren(child);
      }
    }
    
    for (const root of rootNodes) sortChildren(root);
    rootNodes.sort((a, b) => a.name.localeCompare(b.name));
    return rootNodes;
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
    
    const actionText = { scan: '扫描', add_nov: '添加 .nov', remove_nov: '移除 .nov', check_duplicates: '检查重复' }[action];
    log(`🎬 开始${actionText}: ${targetPath}`);

    try {
      progress = 10;
      const response = await api.executeNode('formatv', { path: targetPath, action }) as any;

      if (response.success) {
        phase = 'completed'; progress = 100; progressText = '完成';
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
        phase = 'error'; progress = 0;
        log(`❌ 失败: ${response.message}`);
      }
    } catch (error) {
      phase = 'error'; progress = 0;
      log(`❌ 失败: ${error}`);
    }
  }

  function handleReset() {
    phase = 'idle'; progress = 0; progressText = '';
    scanResult = null; duplicateCount = 0; fileListData = null; selectedFile = null; logs = [];
  }

  async function copyToClipboard(text: string, setter: (v: boolean) => void) {
    try {
      await navigator.clipboard.writeText(text);
      setter(true);
      setTimeout(() => setter(false), 2000);
    } catch (e) { console.error('复制失败:', e); }
  }
</script>

<!-- ========== 统一 UI 结构的区块 ========== -->

<!-- 路径输入区块 -->
{#snippet pathBlock()}
  <div class="cq-mb">
    <div class="flex items-center gap-1 mb-1 cq-text">
      <Video class="cq-icon" />
      <span class="font-medium">目标目录</span>
    </div>
    {#if !hasInputConnection}
      <div class="flex cq-gap">
        <Input bind:value={targetPath} placeholder="输入或选择目录..." disabled={isRunning} class="flex-1 cq-input" />
        <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={selectFolder} disabled={isRunning}>
          <FolderOpen class="cq-icon" />
        </Button>
        <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={pasteFromClipboard} disabled={isRunning}>
          <Clipboard class="cq-icon" />
        </Button>
      </div>
    {:else}
      <div class="text-muted-foreground cq-padding bg-muted cq-rounded flex items-center cq-gap cq-text">
        <span>←</span><span>输入来自上游节点</span>
      </div>
    {/if}
  </div>
{/snippet}

<!-- 操作区块（含状态显示） -->
{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <!-- 状态指示 -->
    <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded">
      {#if phase === 'completed'}
        <CircleCheck class="cq-icon text-green-500 shrink-0" />
        <span class="cq-text text-green-600 font-medium">完成</span>
        <span class="cq-text-sm text-muted-foreground ml-auto">{scanResult?.normal_count ?? 0} 项</span>
      {:else if phase === 'error'}
        <CircleX class="cq-icon text-red-500 shrink-0" />
        <span class="cq-text text-red-600 font-medium">失败</span>
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <div class="flex-1">
          <Progress value={progress} class="h-1.5" />
        </div>
        <span class="cq-text-sm text-muted-foreground">{progress}%</span>
      {:else}
        <Video class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text text-muted-foreground">等待执行</span>
      {/if}
    </div>
    <!-- 主按钮 -->
    <Button class="w-full cq-button flex-1" onclick={() => executeAction('scan')} disabled={!canExecute || isRunning}>
      {#if phase === 'scanning'}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<RefreshCw class="cq-icon mr-1" />{/if}
      <span>扫描</span>
    </Button>
    <!-- 辅助按钮 -->
    <div class="flex cq-gap">
      <Button variant="outline" class="flex-1 cq-button-sm" onclick={() => executeAction('add_nov')} disabled={!canExecute || isRunning}>
        <Plus class="cq-icon" /><span class="cq-wide-only ml-1">.nov</span>
      </Button>
      <Button variant="outline" class="flex-1 cq-button-sm" onclick={() => executeAction('remove_nov')} disabled={!canExecute || isRunning}>
        <Minus class="cq-icon" /><span class="cq-wide-only ml-1">.nov</span>
      </Button>
      <Button variant="secondary" class="flex-1 cq-button-sm" onclick={() => executeAction('check_duplicates')} disabled={!canExecute || isRunning}>
        <Search class="cq-icon" /><span class="cq-wide-only ml-1">重复</span>
      </Button>
      {#if phase === 'completed' || phase === 'error'}
        <Button variant="ghost" size="icon" class="cq-button-icon" onclick={handleReset}>
          <RotateCcw class="cq-icon" />
        </Button>
      {/if}
    </div>
  </div>
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

<!-- 文件树区块（含统计信息） -->
{#snippet treeBlock()}
  {@const fileTree = fileListData ? buildFullFileTree(fileListData) : []}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between cq-padding border-b bg-muted/30 shrink-0">
      <span class="cq-text font-semibold flex items-center gap-1">
        <Folder class="cq-icon text-yellow-500" />文件树
      </span>
      {#if scanResult}
        <div class="flex items-center gap-2 cq-text-sm">
          <span class="flex items-center gap-1 text-green-600" title="普通视频">
            <span class="w-2 h-2 rounded-full bg-green-500"></span>
            {scanResult.normal_count}
          </span>
          <span class="flex items-center gap-1 text-yellow-600" title=".nov 文件">
            <span class="w-2 h-2 rounded-full bg-yellow-500"></span>
            {scanResult.nov_count}
          </span>
          {#each Object.entries(scanResult.prefixed_counts) as [name, count]}
            {#if count > 0}
              <span class="flex items-center gap-1 text-blue-600" title="[{name}] 前缀">
                <span class="w-2 h-2 rounded-full bg-blue-500"></span>
                {count}
              </span>
            {/if}
          {/each}
        </div>
      {:else}
        <span class="cq-text-sm text-muted-foreground">扫描后显示</span>
      {/if}
    </div>
    <div class="flex-1 overflow-y-auto cq-padding">
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
{/snippet}

<!-- 日志区块 -->
{#snippet logBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold">日志</span>
      <Button variant="ghost" size="icon" class="h-5 w-5" onclick={() => copyToClipboard(logs.join('\n'), v => copiedLogs = v)}>
        {#if copiedLogs}<Check class="w-3 h-3 text-green-500" />{:else}<Copy class="w-3 h-3" />{/if}
      </Button>
    </div>
    <div class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding font-mono cq-text-sm space-y-0.5">
      {#if logs.length > 0}
        {#each logs.slice(-10) as logItem}
          <div class="text-muted-foreground break-all">{logItem}</div>
        {/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 区块渲染器 -->
{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'path'}{@render pathBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'tree'}{@render treeBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<!-- 主渲染 -->
<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 400px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={350} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
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
        nodeId={nodeId}
        nodeType="formatv"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={FORMATV_DEFAULT_GRID_LAYOUT}
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
