<script lang="ts">
  /**
   * FindzNode - 文件搜索节点组件
   * 使用 SQL-like WHERE 语法或可视化构建器搜索文件（支持压缩包内部）
   * 
   * 已迁移到 Container Query 响应式布局
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';
  import * as TreeView from '$lib/components/ui/tree-view';

  import { InteractiveHover } from '$lib/components/ui/interactive-hover';
  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { FINDZ_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import FilterBuilder from './FilterBuilder.svelte';
  import AnalysisPanel from './AnalysisPanel.svelte';
  import { 
    Search, LoaderCircle, FolderOpen, Clipboard,
    CircleCheck, CircleX, File, Folder, Archive,
    Copy, Check, RotateCcw, Package, Layers, Funnel
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: { path?: string; where?: string };
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'searching' | 'completed' | 'error';
  type Action = 'search' | 'nested' | 'archives_only' | 'interactive';

  /** 文件树节点 */
  interface FileTreeNode {
    name: string;
    path: string;
    isDir: boolean;
    children?: FileTreeNode[];
    size?: number;
    sizeFormatted?: string;
    date?: string;
    ext?: string;
    archive?: string;
    container?: string;
  }

  interface SearchResult {
    total_count: number;
    file_count: number;
    dir_count: number;
    archive_count: number;
    nested_count: number;
  }

  interface FileData {
    name: string;
    path: string;
    size: number;
    size_formatted: string;
    date: string;
    time: string;
    type: string;
    ext: string;
    archive: string;
    container: string;
  }

  interface FindzNodeState {
    phase: Phase;
    progress: number;
    progressText: string;
    searchResult: SearchResult | null;
    files: FileData[];
    byExtension: Record<string, number>;
  }

  const savedState = getNodeState<FindzNodeState>(id);

  // 状态
  let targetPath = $state(data?.config?.path ?? '.');
  let whereClause = $state(data?.config?.where ?? '1');
  let phase = $state<Phase>(savedState?.phase ?? 'idle');
  let logs = $state<string[]>(data?.logs ? [...data.logs] : []);
  let hasInputConnection = $state(data?.hasInputConnection ?? false);
  let copied = $state(false);
  let progress = $state(savedState?.progress ?? 0);
  let progressText = $state(savedState?.progressText ?? '');
  let searchResult = $state<SearchResult | null>(savedState?.searchResult ?? null);
  let files = $state<FileData[]>(savedState?.files ?? []);
  let byExtension = $state<Record<string, number>>(savedState?.byExtension ?? {});
  let copiedPath = $state(false);

  let layoutRenderer = $state<any>(undefined);
  let selectedFile = $state<string | null>(null);
  let advancedMode = $state(false);

  function saveState() {
    setNodeState<FindzNodeState>(id, {
      phase, progress, progressText, searchResult, files, byExtension
    });
  }

  let canExecute = $derived(phase === 'idle' && (targetPath.trim() !== '' || hasInputConnection));
  let isRunning = $derived(phase === 'searching');
  let borderClass = $derived({
    idle: 'border-border',
    searching: 'border-blue-500 shadow-sm',
    completed: 'border-primary/50',
    error: 'border-destructive/50'
  }[phase]);

  $effect(() => { if (phase || searchResult || files) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  /** 构建文件树结构 */
  function buildFileTree(fileList: FileData[]): FileTreeNode[] {
    const nodeMap = new Map<string, FileTreeNode>();
    
    function addFile(file: FileData) {
      const fullPath = file.container ? `${file.container}//${file.path}` : file.path;
      const parts = fullPath.split(/[/\\]|\/\//);
      let currentPath = '';
      
      for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i];
        const parentPath = currentPath;
        currentPath = currentPath ? `${currentPath}/${part}` : part;
        
        if (!nodeMap.has(currentPath)) {
          const dirNode: FileTreeNode = { name: part, path: currentPath, isDir: true, children: [] };
          nodeMap.set(currentPath, dirNode);
          if (parentPath && nodeMap.has(parentPath)) {
            const parent = nodeMap.get(parentPath)!;
            if (!parent.children!.find(c => c.path === currentPath)) parent.children!.push(dirNode);
          }
        }
      }
      
      const fileNode: FileTreeNode = {
        name: file.name, path: fullPath, isDir: file.type === 'dir',
        size: file.size, sizeFormatted: file.size_formatted, date: file.date,
        ext: file.ext, archive: file.archive, container: file.container,
        children: file.type === 'dir' ? [] : undefined
      };
      nodeMap.set(fullPath, fileNode);
      if (currentPath && nodeMap.has(currentPath)) {
        const parent = nodeMap.get(currentPath)!;
        if (!parent.children!.find(c => c.path === fullPath)) parent.children!.push(fileNode);
      }
    }
    
    for (const file of fileList) addFile(file);
    
    const rootNodes: FileTreeNode[] = [];
    for (const [path, node] of nodeMap) {
      const parentPath = path.split(/[/\\]|\/\//).slice(0, -1).join('/');
      if (!parentPath || !nodeMap.has(parentPath)) rootNodes.push(node);
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
      const selected = await platform.openFolderDialog('选择搜索目录');
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
    if (!canExecute && action !== 'interactive') return;
    phase = 'searching'; progress = 0; progressText = '搜索中...';
    
    const actionText = { search: '搜索文件', nested: '查找嵌套压缩包', archives_only: '搜索压缩包', interactive: '帮助' }[action];
    log(`🔍 开始${actionText}: ${targetPath}`);
    log(`📝 过滤条件: ${whereClause}`);

    try {
      progress = 10;
      const response = await api.executeNode('findz', {
        path: targetPath, where: whereClause, action, long_format: true, max_results: 1000
      }) as any;

      if (response.logs && Array.isArray(response.logs)) {
        for (const logMsg of response.logs) log(logMsg);
      }

      if (response.success) {
        phase = 'completed'; progress = 100; progressText = '完成';
        searchResult = {
          total_count: response.data?.total_count ?? 0, file_count: response.data?.file_count ?? 0,
          dir_count: response.data?.dir_count ?? 0, archive_count: response.data?.archive_count ?? 0,
          nested_count: response.data?.nested_count ?? 0,
        };
        files = response.data?.files ?? [];
        byExtension = response.data?.by_extension ?? {};
        log(`✅ ${response.message}`);
      } else {
        phase = 'error'; progress = 0; log(`❌ 失败: ${response.message}`);
      }
    } catch (error) {
      phase = 'error'; progress = 0; log(`❌ 失败: ${error}`);
    }
  }

  function handleReset() {
    phase = 'idle'; progress = 0; progressText = '';
    searchResult = null; files = []; byExtension = {};
    selectedFile = null; logs = [];
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(logs.join('\n'));
      copied = true; setTimeout(() => { copied = false; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  async function copyAllPaths() {
    try {
      const paths = files.map(f => f.container ? `${f.container}//${f.path}` : f.path).join('\n');
      await navigator.clipboard.writeText(paths);
      copiedPath = true; setTimeout(() => { copiedPath = false; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  async function copyFilePath(file: FileData) {
    try {
      const path = file.container ? `${file.container}//${file.path}` : file.path;
      await navigator.clipboard.writeText(path);
      copiedPath = true; setTimeout(() => { copiedPath = false; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  function getOutsideArchiveCount(): number {
    return files.filter(f => !f.archive && !f.container).length;
  }
</script>


<!-- ========== 区块内容 Snippets（使用 Container Query 响应式） ========== -->

<!-- 路径输入区块 -->
{#snippet pathBlock()}
  <div class="cq-mb">
    <div class="flex items-center gap-1 mb-1 cq-text">
      <Search class="cq-icon" />
      <span class="font-medium">搜索路径</span>
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

<!-- 过滤器区块 -->
{#snippet filterBlock()}
  <div class="h-full flex flex-col overflow-auto">
    <!-- 宽屏模式：可视化过滤器构建器 -->
    <div class="cq-wide-only h-full">
      <FilterBuilder 
        advancedMode={advancedMode}
        sqlValue={whereClause}
        onchange={(_, sql) => { whereClause = sql; }}
        onAdvancedChange={(adv) => advancedMode = adv}
        disabled={isRunning}
      />
    </div>
    <!-- 紧凑模式：只显示 SQL 输入 -->
    <div class="cq-compact-only">
      <div class="flex items-center gap-1 mb-1 cq-text">
        <Funnel class="cq-icon" />
        <span class="font-medium">过滤</span>
      </div>
      <Input bind:value={whereClause} placeholder="过滤条件" disabled={isRunning} class="cq-input font-mono text-xs" />
    </div>
  </div>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock()}
  <div class="flex flex-col cq-gap">
    <!-- 宽屏模式 -->
    <div class="cq-wide-only-flex flex-col gap-2">
      <InteractiveHover text="搜索文件" class="w-full h-10 text-sm" onclick={() => executeAction('search')} disabled={!canExecute || isRunning}>
        {#snippet icon()}{#if phase === 'searching'}<LoaderCircle class="h-4 w-4 animate-spin" />{:else}<Search class="h-4 w-4" />{/if}{/snippet}
      </InteractiveHover>
      <div class="grid grid-cols-2 gap-2">
        <Button variant="outline" class="h-9" onclick={() => executeAction('archives_only')} disabled={!canExecute || isRunning}>
          <Archive class="h-4 w-4 mr-1" />压缩包
        </Button>
        <Button variant="outline" class="h-9" onclick={() => executeAction('nested')} disabled={!canExecute || isRunning}>
          <Layers class="h-4 w-4 mr-1" />嵌套
        </Button>
      </div>
      {#if phase === 'completed' || phase === 'error'}
        <Button variant="ghost" class="h-8" onclick={handleReset}>
          <RotateCcw class="h-4 w-4 mr-2" />重置结果
        </Button>
      {/if}
    </div>
    <!-- 紧凑模式 -->
    <div class="cq-compact-only-flex flex-wrap cq-gap">
      <Button size="sm" class="cq-button" onclick={() => executeAction('search')} disabled={!canExecute || isRunning}>
        {#if phase === 'searching'}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<Search class="cq-icon mr-1" />{/if}搜索
      </Button>
      <Button size="sm" variant="outline" class="cq-button" onclick={() => executeAction('archives_only')} disabled={!canExecute || isRunning}>
        <Archive class="cq-icon" />
      </Button>
      <Button size="sm" variant="outline" class="cq-button" onclick={() => executeAction('nested')} disabled={!canExecute || isRunning}>
        <Layers class="cq-icon" />
      </Button>
      {#if phase === 'completed' || phase === 'error'}
        <Button size="sm" variant="ghost" class="cq-button" onclick={handleReset}>
          <RotateCcw class="cq-icon" />
        </Button>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlock()}
  {@const outsideCount = getOutsideArchiveCount()}
  <!-- 宽屏模式 -->
  <div class="cq-wide-only space-y-2 flex-1">
    {#if searchResult}
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-blue-500/15 to-blue-500/5 rounded-xl border border-blue-500/20">
        <span class="text-sm text-muted-foreground">总计</span>
        <span class="text-2xl font-bold text-blue-600 tabular-nums">{searchResult.total_count}</span>
      </div>
      <div class="grid grid-cols-2 gap-2">
        <div class="flex items-center justify-between p-2 bg-green-500/10 rounded-lg">
          <div class="flex items-center gap-1">
            <File class="w-3 h-3 text-green-600" />
            <span class="text-xs text-muted-foreground">文件系统</span>
          </div>
          <span class="text-lg font-bold text-green-600 tabular-nums">{outsideCount}</span>
        </div>
        <div class="flex items-center justify-between p-2 bg-purple-500/10 rounded-lg">
          <div class="flex items-center gap-1">
            <Package class="w-3 h-3 text-purple-600" />
            <span class="text-xs text-muted-foreground">压缩包内</span>
          </div>
          <span class="text-lg font-bold text-purple-600 tabular-nums">{searchResult.archive_count}</span>
        </div>
        {#if searchResult.dir_count > 0}
          <div class="flex items-center justify-between p-2 bg-yellow-500/10 rounded-lg">
            <div class="flex items-center gap-1">
              <Folder class="w-3 h-3 text-yellow-600" />
              <span class="text-xs text-muted-foreground">目录</span>
            </div>
            <span class="text-lg font-bold text-yellow-600 tabular-nums">{searchResult.dir_count}</span>
          </div>
        {/if}
        {#if searchResult.nested_count > 0}
          <div class="flex items-center justify-between p-2 bg-red-500/10 rounded-lg">
            <div class="flex items-center gap-1">
              <Layers class="w-3 h-3 text-red-600" />
              <span class="text-xs text-muted-foreground">嵌套</span>
            </div>
            <span class="text-lg font-bold text-red-600 tabular-nums">{searchResult.nested_count}</span>
          </div>
        {/if}
      </div>
      {#if Object.keys(byExtension).length > 0}
        <div class="mt-2">
          <div class="text-xs text-muted-foreground mb-1">按扩展名</div>
          <div class="flex flex-wrap gap-1">
            {#each Object.entries(byExtension).sort((a, b) => b[1] - a[1]).slice(0, 8) as [ext, count]}
              <span class="text-xs px-1.5 py-0.5 bg-muted rounded">.{ext || '无'}: {count}</span>
            {/each}
          </div>
        </div>
      {/if}
    {:else}
      <div class="text-center text-muted-foreground py-4">搜索后显示统计</div>
    {/if}
  </div>
  <!-- 紧凑模式 -->
  <div class="cq-compact-only">
    {#if searchResult}
      <div class="grid grid-cols-2 gap-1.5">
        <div class="text-center p-1.5 bg-blue-500/10 rounded-lg">
          <div class="text-sm font-bold text-blue-600 tabular-nums">{searchResult.total_count}</div>
          <div class="text-[10px] text-muted-foreground">总计</div>
        </div>
        <div class="text-center p-1.5 bg-green-500/10 rounded-lg">
          <div class="text-sm font-bold text-green-600 tabular-nums">{searchResult.file_count}</div>
          <div class="text-[10px] text-muted-foreground">文件</div>
        </div>
      </div>
    {:else}
      <div class="text-xs text-muted-foreground text-center">-</div>
    {/if}
  </div>
{/snippet}

<!-- 进度区块 -->
{#snippet progressBlock()}
  <!-- 宽屏模式 -->
  <div class="cq-wide-only-flex h-full items-center gap-3">
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
      <Search class="w-8 h-8 text-muted-foreground/50 shrink-0" />
      <span class="text-muted-foreground">等待执行</span>
    {/if}
  </div>
  <!-- 紧凑模式 -->
  <div class="cq-compact-only">
    {#if phase === 'completed'}
      <div class="flex items-center gap-2 cq-text">
        <CircleCheck class="cq-icon text-green-500" />
        <span class="text-green-600">完成</span>
      </div>
    {:else if isRunning}
      <div class="space-y-1">
        <Progress value={progress} class="h-1.5" />
        <div class="cq-text text-muted-foreground">{progress}%</div>
      </div>
    {:else}
      <div class="cq-text text-muted-foreground">等待执行</div>
    {/if}
  </div>
{/snippet}

<!-- 日志区块 -->
{#snippet logBlock()}
  <!-- 宽屏模式 -->
  <div class="cq-wide-only h-full flex flex-col">
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
  <!-- 紧凑模式 -->
  <div class="cq-compact-only">
    <div class="flex items-center justify-between mb-1">
      <span class="cq-text font-semibold">日志</span>
      <Button variant="ghost" size="icon" class="h-5 w-5" onclick={copyLogs}>
        {#if copied}<Check class="cq-icon-sm text-green-500" />{:else}<Copy class="cq-icon-sm" />{/if}
      </Button>
    </div>
    <div class="bg-muted/30 cq-rounded cq-padding-sm font-mono cq-text-sm cq-max-h-sm overflow-y-auto space-y-1">
      {#each logs.slice(-4) as logItem}
        <div class="text-muted-foreground break-all">{logItem}</div>
      {/each}
    </div>
  </div>
{/snippet}

<!-- 递归渲染文件树节点 -->
{#snippet renderTreeNode(node: FileTreeNode)}
  {#if node.isDir}
    <TreeView.Folder name={node.name} open={false} class="text-xs">
      {#snippet icon()}
        {#if node.name.includes('//')}
          <Archive class="w-3 h-3 text-purple-500" />
        {:else}
          <Folder class="w-3 h-3 text-yellow-500" />
        {/if}
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
    {@const isInArchive = !!node.container}
    <button 
      class="flex items-center gap-2 py-1 px-1 w-full text-left hover:bg-muted/50 rounded transition-colors {selectedFile === node.path ? 'bg-primary/10' : ''}"
      onclick={() => selectedFile = node.path}
    >
      {#if isInArchive}
        <Package class="w-3 h-3 text-purple-500 shrink-0" />
      {:else}
        <File class="w-3 h-3 text-blue-500 shrink-0" />
      {/if}
      <span class="truncate flex-1 text-xs" title={node.path}>{node.name}</span>
      {#if node.sizeFormatted}
        <span class="text-[10px] text-muted-foreground shrink-0">{node.sizeFormatted}</span>
      {/if}
    </button>
  {/if}
{/snippet}

<!-- 文件树区块 -->
{#snippet treeBlock()}
  {@const fileTree = files.length > 0 ? buildFileTree(files) : []}
  <!-- 宽屏模式 -->
  <div class="cq-wide-only h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between p-2 border-b bg-muted/30 shrink-0">
      <span class="font-semibold flex items-center gap-2">
        <Folder class="w-5 h-5 text-yellow-500" />文件列表
      </span>
      <div class="flex items-center gap-1">
        <span class="text-xs text-muted-foreground">{files.length} 项</span>
        {#if files.length > 0}
          <Button variant="ghost" size="icon" class="h-6 w-6" onclick={copyAllPaths} title="复制所有路径">
            {#if copiedPath}<Check class="w-3 h-3 text-green-500" />{:else}<Copy class="w-3 h-3" />{/if}
          </Button>
        {/if}
      </div>
    </div>
    <div class="flex-1 overflow-y-auto p-2">
      {#if fileTree.length > 0}
        <TreeView.Root class="text-sm">
          {#each fileTree as node}
            {@render renderTreeNode(node)}
          {/each}
        </TreeView.Root>
      {:else if files.length > 0}
        <div class="space-y-1">
          {#each files.slice(0, 100) as file}
            <div class="group flex items-center gap-2 py-1 px-1 hover:bg-muted/50 rounded text-xs">
              {#if file.container}
                <Package class="w-3 h-3 text-purple-500 shrink-0" />
              {:else}
                <File class="w-3 h-3 text-blue-500 shrink-0" />
              {/if}
              <span class="truncate flex-1" title={file.container ? `${file.container}//${file.path}` : file.path}>{file.name}</span>
              <span class="text-muted-foreground shrink-0">{file.size_formatted}</span>
              <button class="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-muted rounded" onclick={() => copyFilePath(file)} title="复制路径">
                <Copy class="w-3 h-3" />
              </button>
            </div>
          {/each}
          {#if files.length > 100}
            <div class="text-center text-muted-foreground py-2">还有 {files.length - 100} 项未显示</div>
          {/if}
        </div>
      {:else}
        <div class="text-center text-muted-foreground py-8">搜索后显示文件列表</div>
      {/if}
    </div>
  </div>
  <!-- 紧凑模式 -->
  <div class="cq-compact-only">
    <div class="flex items-center justify-between mb-2">
      <span class="cq-text font-semibold flex items-center gap-1">
        <Folder class="w-3 h-3 text-yellow-500" />文件
      </span>
      <span class="cq-text-sm text-muted-foreground">{files.length}</span>
    </div>
    <div class="cq-max-h overflow-y-auto">
      {#if files.length > 0}
        <div class="space-y-0.5">
          {#each files.slice(0, 10) as file}
            <div class="flex items-center gap-1 text-xs truncate">
              <File class="w-2.5 h-2.5 text-blue-500 shrink-0" />
              <span class="truncate">{file.name}</span>
            </div>
          {/each}
          {#if files.length > 10}
            <div class="text-[10px] text-muted-foreground">+{files.length - 10} 更多</div>
          {/if}
        </div>
      {:else}
        <div class="cq-text text-muted-foreground text-center py-3">搜索后显示</div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 分析区块 -->
{#snippet analysisBlock()}
  <AnalysisPanel {files} />
{/snippet}

<!-- 通用区块渲染器（保留 size 参数以兼容 NodeLayoutRenderer，但内部使用 Container Query） -->
{#snippet renderBlockContent(blockId: string, _size: import('$lib/utils/sizeUtils').SizeMode)}
  {#if blockId === 'path'}{@render pathBlock()}
  {:else if blockId === 'filter'}{@render filterBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'stats'}{@render statsBlock()}
  {:else if blockId === 'progress'}{@render progressBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {:else if blockId === 'tree'}{@render treeBlock()}
  {:else if blockId === 'analysis'}{@render analysisBlock()}
  {/if}
{/snippet}

<!-- ========== 主渲染 ========== -->
<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 420px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={300} minHeight={380} maxWidth={420} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={id} 
    title="findz" 
    icon={Search} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="findz" 
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
        nodeType="findz"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={FINDZ_DEFAULT_GRID_LAYOUT}
      >
        {#snippet renderBlock(blockId: string, size: import('$lib/utils/sizeUtils').SizeMode)}
          {@render renderBlockContent(blockId, size)}
        {/snippet}
      </NodeLayoutRenderer>
    {/snippet}
  </NodeWrapper>

  {#if !isFullscreenRender}
    <Handle type="source" position={Position.Right} class="bg-primary!" />
  {/if}
</div>
