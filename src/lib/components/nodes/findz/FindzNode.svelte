<script lang="ts">
  /**
   * FindzNode - 文件搜索节点组件
   * 使用 SQL-like WHERE 语法或可视化构建器搜索文件（支持压缩包内部）
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
  import { getSizeClasses, type SizeMode } from '$lib/utils/sizeUtils';
  import FilterBuilder from './FilterBuilder.svelte';
  import { 
    Search, LoaderCircle, FolderOpen, Clipboard,
    CircleCheck, CircleX, File, Folder, Archive,
    Copy, Check, RotateCcw, RefreshCw, HelpCircle,
    Filter, Package, Layers, BarChart3, ArrowUpDown,
    ArrowUp, ArrowDown
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
  let copiedPath = $state(false);  // 复制路径状态
  
  // 分析区块状态
  type GroupByField = 'archive' | 'ext' | 'dir';  // 分组字段
  type SortField = 'name' | 'count' | 'totalSize' | 'avgSize';
  type SortOrder = 'asc' | 'desc';
  let analysisGroupBy = $state<GroupByField>('archive');  // 分组方式
  let analysisSortField = $state<SortField>('avgSize');
  let analysisSortOrder = $state<SortOrder>('desc');
  let analysisMinFiles = $state(1);  // 最小文件数过滤

  /** 分组分析数据 */
  interface GroupAnalysis {
    key: string;       // 分组键
    name: string;      // 显示名称
    fileCount: number;
    totalSize: number;
    avgSize: number;
    avgSizeFormatted: string;
    totalSizeFormatted: string;
    subStats: Record<string, number>;  // 子统计（如扩展名分布）
  }

  /** 分组配置 */
  const groupByOptions: { field: GroupByField; label: string; icon: typeof Package }[] = [
    { field: 'archive', label: '压缩包', icon: Package },
    { field: 'ext', label: '扩展名', icon: File },
    { field: 'dir', label: '目录', icon: Folder },
  ];

  /** 格式化文件大小 */
  function formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  /** 获取文件的分组键 */
  function getGroupKey(file: FileData, groupBy: GroupByField): string | null {
    switch (groupBy) {
      case 'archive':
        return file.archive || file.container || null;
      case 'ext':
        return file.ext || '(无扩展名)';
      case 'dir': {
        // 获取父目录
        const fullPath = file.container ? `${file.container}//${file.path}` : file.path;
        const parts = fullPath.split(/[/\\]|\/\//);
        return parts.length > 1 ? parts.slice(0, -1).join('/') : '(根目录)';
      }
    }
  }

  /** 获取分组显示名称 */
  function getGroupName(key: string, groupBy: GroupByField): string {
    switch (groupBy) {
      case 'archive':
        return key.split(/[/\\]/).pop() || key;
      case 'ext':
        return key.startsWith('(') ? key : `.${key}`;
      case 'dir':
        return key.split(/[/\\]|\/\//).pop() || key;
    }
  }

  /** 通用分组分析 */
  function analyzeByGroup(): GroupAnalysis[] {
    const groupMap = new Map<string, { files: FileData[], totalSize: number }>();
    
    for (const file of files) {
      const key = getGroupKey(file, analysisGroupBy);
      if (key === null) continue;  // 跳过无法分组的文件
      
      if (!groupMap.has(key)) {
        groupMap.set(key, { files: [], totalSize: 0 });
      }
      const data = groupMap.get(key)!;
      data.files.push(file);
      data.totalSize += file.size;
    }
    
    const results: GroupAnalysis[] = [];
    for (const [key, data] of groupMap) {
      const avgSize = data.files.length > 0 ? data.totalSize / data.files.length : 0;
      
      // 子统计：根据分组类型显示不同信息
      const subStats: Record<string, number> = {};
      if (analysisGroupBy === 'archive' || analysisGroupBy === 'dir') {
        // 按扩展名统计
        for (const f of data.files) {
          const ext = f.ext || '无';
          subStats[ext] = (subStats[ext] || 0) + 1;
        }
      } else if (analysisGroupBy === 'ext') {
        // 按压缩包/目录统计
        for (const f of data.files) {
          const container = f.archive || f.container || '文件系统';
          const name = container === '文件系统' ? container : container.split(/[/\\]/).pop() || container;
          subStats[name] = (subStats[name] || 0) + 1;
        }
      }
      
      results.push({
        key,
        name: getGroupName(key, analysisGroupBy),
        fileCount: data.files.length,
        totalSize: data.totalSize,
        avgSize,
        avgSizeFormatted: formatSize(avgSize),
        totalSizeFormatted: formatSize(data.totalSize),
        subStats,
      });
    }
    
    // 过滤和排序
    return results
      .filter(a => a.fileCount >= analysisMinFiles)
      .sort((a, b) => {
        let cmp = 0;
        switch (analysisSortField) {
          case 'name': cmp = a.name.localeCompare(b.name); break;
          case 'count': cmp = a.fileCount - b.fileCount; break;
          case 'totalSize': cmp = a.totalSize - b.totalSize; break;
          case 'avgSize': cmp = a.avgSize - b.avgSize; break;
        }
        return analysisSortOrder === 'desc' ? -cmp : cmp;
      });
  }

  /** 切换排序 */
  function toggleSort(field: SortField) {
    if (analysisSortField === field) {
      analysisSortOrder = analysisSortOrder === 'asc' ? 'desc' : 'asc';
    } else {
      analysisSortField = field;
      analysisSortOrder = 'desc';
    }
  }

  /** 获取分组内的所有文件 */
  function getFilesInGroup(groupKey: string): FileData[] {
    return files.filter(f => getGroupKey(f, analysisGroupBy) === groupKey);
  }

  /** 复制分组内文件路径 */
  let copiedGroupKey = $state<string | null>(null);
  async function copyGroupPaths(groupKey: string) {
    try {
      const groupFiles = getFilesInGroup(groupKey);
      const paths = groupFiles.map(f => f.container ? `${f.container}//${f.path}` : f.path).join('\n');
      await navigator.clipboard.writeText(paths);
      copiedGroupKey = groupKey;
      setTimeout(() => { copiedGroupKey = null; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  let layoutRenderer = $state<any>(undefined);
  let selectedFile = $state<string | null>(null);
  let advancedMode = $state(false);
  let filterConfig = $state<any>(null);

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

  /**
   * 构建文件树结构
   */
  function buildFileTree(fileList: FileData[]): FileTreeNode[] {
    const nodeMap = new Map<string, FileTreeNode>();
    
    function addFile(file: FileData) {
      // 如果在压缩包内，使用 container 作为前缀
      const fullPath = file.container ? `${file.container}//${file.path}` : file.path;
      const parts = fullPath.split(/[/\\]|\/\//);
      let currentPath = '';
      
      for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i];
        const parentPath = currentPath;
        currentPath = currentPath ? `${currentPath}/${part}` : part;
        
        if (!nodeMap.has(currentPath)) {
          const dirNode: FileTreeNode = {
            name: part,
            path: currentPath,
            isDir: true,
            children: []
          };
          nodeMap.set(currentPath, dirNode);
          
          if (parentPath && nodeMap.has(parentPath)) {
            const parent = nodeMap.get(parentPath)!;
            if (!parent.children!.find(c => c.path === currentPath)) {
              parent.children!.push(dirNode);
            }
          }
        }
      }
      
      const fileNode: FileTreeNode = {
        name: file.name,
        path: fullPath,
        isDir: file.type === 'dir',
        size: file.size,
        sizeFormatted: file.size_formatted,
        date: file.date,
        ext: file.ext,
        archive: file.archive,
        container: file.container,
        children: file.type === 'dir' ? [] : undefined
      };
      nodeMap.set(fullPath, fileNode);
      
      if (currentPath && nodeMap.has(currentPath)) {
        const parent = nodeMap.get(currentPath)!;
        if (!parent.children!.find(c => c.path === fullPath)) {
          parent.children!.push(fileNode);
        }
      }
    }
    
    for (const file of fileList) {
      addFile(file);
    }
    
    // 找出根节点
    const rootNodes: FileTreeNode[] = [];
    for (const [path, node] of nodeMap) {
      const parentPath = path.split(/[/\\]|\/\//).slice(0, -1).join('/');
      if (!parentPath || !nodeMap.has(parentPath)) {
        rootNodes.push(node);
      }
    }
    
    // 排序
    function sortChildren(node: FileTreeNode) {
      if (node.children && node.children.length > 0) {
        node.children.sort((a, b) => {
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
    
    phase = 'searching';
    progress = 0;
    progressText = '搜索中...';
    
    const actionText = {
      search: '搜索文件',
      nested: '查找嵌套压缩包',
      archives_only: '搜索压缩包',
      interactive: '帮助'
    }[action];
    
    log(`🔍 开始${actionText}: ${targetPath}`);
    log(`📝 过滤条件: ${whereClause}`);

    try {
      progress = 10;
      const response = await api.executeNode('findz', {
        path: targetPath,
        where: whereClause,
        action,
        long_format: true,
        max_results: 1000
      }) as any;

      // 显示后端返回的日志
      if (response.logs && Array.isArray(response.logs)) {
        for (const logMsg of response.logs) {
          log(logMsg);
        }
      }

      if (response.success) {
        phase = 'completed';
        progress = 100;
        progressText = '完成';
        
        searchResult = {
          total_count: response.data?.total_count ?? 0,
          file_count: response.data?.file_count ?? 0,
          dir_count: response.data?.dir_count ?? 0,
          archive_count: response.data?.archive_count ?? 0,
          nested_count: response.data?.nested_count ?? 0,
        };
        files = response.data?.files ?? [];
        byExtension = response.data?.by_extension ?? {};
        
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
    searchResult = null;
    files = [];
    byExtension = {};
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

  /** 复制所有文件路径 */
  async function copyAllPaths() {
    try {
      const paths = files.map(f => f.container ? `${f.container}//${f.path}` : f.path).join('\n');
      await navigator.clipboard.writeText(paths);
      copiedPath = true;
      setTimeout(() => { copiedPath = false; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  /** 复制单个文件路径 */
  async function copyFilePath(file: FileData) {
    try {
      const path = file.container ? `${file.container}//${file.path}` : file.path;
      await navigator.clipboard.writeText(path);
      copiedPath = true;
      setTimeout(() => { copiedPath = false; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  /** 计算压缩包外文件数 */
  function getOutsideArchiveCount(): number {
    return files.filter(f => !f.archive && !f.container).length;
  }

  function applyPreset(value: string) {
    whereClause = value;
  }
</script>

<!-- 路径输入区块 -->
{#snippet pathBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="{c.mb}">
    <div class="flex items-center gap-1 mb-1 {c.text}">
      <Search class={c.icon} />
      <span class="font-medium">搜索路径</span>
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

<!-- 过滤器区块 -->
{#snippet filterBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="h-full flex flex-col overflow-auto">
    {#if size === 'normal'}
      <!-- 使用新的可视化过滤器构建器 -->
      <FilterBuilder 
        advancedMode={advancedMode}
        sqlValue={whereClause}
        onchange={(config, sql) => {
          filterConfig = config;
          whereClause = sql;
        }}
        onAdvancedChange={(adv) => advancedMode = adv}
        disabled={isRunning}
      />
    {:else}
      <!-- 紧凑模式：只显示 SQL 输入 -->
      <div class="flex items-center gap-1 mb-1 {c.text}">
        <Filter class={c.icon} />
        <span class="font-medium">过滤</span>
      </div>
      <Input bind:value={whereClause} placeholder="过滤条件" disabled={isRunning} class="{c.input} font-mono text-xs" />
    {/if}
  </div>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="flex flex-col {c.gap}">
    {#if size === 'normal'}
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
    {:else}
      <div class="flex flex-wrap {c.gap}">
        <Button size="sm" class={c.button} onclick={() => executeAction('search')} disabled={!canExecute || isRunning}>
          {#if phase === 'searching'}<LoaderCircle class="{c.icon} mr-1 animate-spin" />{:else}<Search class="{c.icon} mr-1" />{/if}搜索
        </Button>
        <Button size="sm" variant="outline" class={c.button} onclick={() => executeAction('archives_only')} disabled={!canExecute || isRunning}>
          <Archive class={c.icon} />
        </Button>
        <Button size="sm" variant="outline" class={c.button} onclick={() => executeAction('nested')} disabled={!canExecute || isRunning}>
          <Layers class={c.icon} />
        </Button>
        {#if phase === 'completed' || phase === 'error'}
          <Button size="sm" variant="ghost" class={c.button} onclick={handleReset}>
            <RotateCcw class={c.icon} />
          </Button>
        {/if}
      </div>
    {/if}
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlock(size: SizeMode)}
  {@const outsideCount = getOutsideArchiveCount()}
  {#if size === 'normal'}
    <div class="space-y-2 flex-1">
      {#if searchResult}
        <div class="flex items-center justify-between p-3 bg-gradient-to-r from-blue-500/15 to-blue-500/5 rounded-xl border border-blue-500/20">
          <span class="text-sm text-muted-foreground">总计</span>
          <span class="text-2xl font-bold text-blue-600 tabular-nums">{searchResult.total_count}</span>
        </div>
        <div class="grid grid-cols-2 gap-2">
          <!-- 压缩包外文件 -->
          <div class="flex items-center justify-between p-2 bg-green-500/10 rounded-lg">
            <div class="flex items-center gap-1">
              <File class="w-3 h-3 text-green-600" />
              <span class="text-xs text-muted-foreground">文件系统</span>
            </div>
            <span class="text-lg font-bold text-green-600 tabular-nums">{outsideCount}</span>
          </div>
          <!-- 压缩包内文件 -->
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
        
        <!-- 扩展名统计 -->
        {#if Object.keys(byExtension).length > 0}
          <div class="mt-2">
            <div class="text-xs text-muted-foreground mb-1">按扩展名</div>
            <div class="flex flex-wrap gap-1">
              {#each Object.entries(byExtension).sort((a, b) => b[1] - a[1]).slice(0, 8) as [ext, count]}
                <span class="text-xs px-1.5 py-0.5 bg-muted rounded">
                  .{ext || '无'}: {count}
                </span>
              {/each}
            </div>
          </div>
        {/if}
      {:else}
        <div class="text-center text-muted-foreground py-4">搜索后显示统计</div>
      {/if}
    </div>
  {:else}
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
        <Search class="w-8 h-8 text-muted-foreground/50 shrink-0" />
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
{#snippet treeBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {@const fileTree = files.length > 0 ? buildFileTree(files) : []}
  
  {#if size === 'normal'}
    <div class="h-full flex flex-col overflow-hidden">
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
          <!-- 平铺列表模式 -->
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
                <button 
                  class="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-muted rounded"
                  onclick={() => copyFilePath(file)}
                  title="复制路径"
                >
                  <Copy class="w-3 h-3" />
                </button>
              </div>
            {/each}
            {#if files.length > 100}
              <div class="text-center text-muted-foreground py-2">
                还有 {files.length - 100} 项未显示
              </div>
            {/if}
          </div>
        {:else}
          <div class="text-center text-muted-foreground py-8">搜索后显示文件列表</div>
        {/if}
      </div>
    </div>
  {:else}
    <div class="flex items-center justify-between mb-2">
      <span class="{c.text} font-semibold flex items-center gap-1">
        <Folder class="w-3 h-3 text-yellow-500" />文件
      </span>
      <span class="{c.textSm} text-muted-foreground">{files.length}</span>
    </div>
    <div class="{c.maxHeight} overflow-y-auto">
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
        <div class="{c.text} text-muted-foreground text-center py-3">搜索后显示</div>
      {/if}
    </div>
  {/if}
{/snippet}

<!-- 通用分析区块 -->
{#snippet analysisBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {@const analysisData = analyzeByGroup()}
  {@const currentGroupOption = groupByOptions.find(o => o.field === analysisGroupBy)!}
  
  {#if size === 'normal'}
    <div class="h-full flex flex-col overflow-hidden">
      <!-- 标题栏：分组选择 -->
      <div class="flex items-center justify-between p-2 border-b bg-muted/30 shrink-0">
        <div class="flex items-center gap-1">
          {#each groupByOptions as opt}
            <button
              class="px-2 py-1 rounded text-xs flex items-center gap-1 transition-colors {analysisGroupBy === opt.field ? 'bg-primary/20 text-primary' : 'hover:bg-muted text-muted-foreground'}"
              onclick={() => analysisGroupBy = opt.field}
            >
              <svelte:component this={opt.icon} class="w-3 h-3" />
              {opt.label}
            </button>
          {/each}
        </div>
        <label class="flex items-center gap-1 text-xs text-muted-foreground">
          <span>≥</span>
          <Input 
            type="number" 
            bind:value={analysisMinFiles} 
            min={1} 
            class="w-10 h-6 text-xs px-1"
          />
        </label>
      </div>
      
      <!-- 排序按钮 -->
      <div class="flex items-center gap-1 p-2 border-b text-xs">
        <span class="text-muted-foreground mr-1">排序:</span>
        {#each [
          { field: 'name' as SortField, label: '名称' },
          { field: 'count' as SortField, label: '数量' },
          { field: 'totalSize' as SortField, label: '总大小' },
          { field: 'avgSize' as SortField, label: '平均' }
        ] as item}
          <button
            class="px-2 py-0.5 rounded flex items-center gap-0.5 transition-colors {analysisSortField === item.field ? 'bg-primary/20 text-primary' : 'hover:bg-muted'}"
            onclick={() => toggleSort(item.field)}
          >
            {item.label}
            {#if analysisSortField === item.field}
              {#if analysisSortOrder === 'desc'}
                <ArrowDown class="w-3 h-3" />
              {:else}
                <ArrowUp class="w-3 h-3" />
              {/if}
            {/if}
          </button>
        {/each}
      </div>
      
      <!-- 分析列表 -->
      <div class="flex-1 overflow-y-auto p-2">
        {#if analysisData.length > 0}
          <div class="space-y-2">
            {#each analysisData as group}
              <div class="group/item p-2 bg-muted/30 rounded-lg border border-border/50 hover:border-primary/30 transition-colors">
                <div class="flex items-start justify-between gap-2 mb-1">
                  <span class="text-sm font-medium truncate flex-1" title={group.key}>
                    {group.name}
                  </span>
                  <div class="flex items-center gap-1 shrink-0">
                    <!-- 复制路径按钮 -->
                    <button
                      class="p-1 rounded opacity-0 group-hover/item:opacity-100 hover:bg-muted transition-all"
                      onclick={() => copyGroupPaths(group.key)}
                      title="复制该分组所有文件路径"
                    >
                      {#if copiedGroupKey === group.key}
                        <Check class="w-3 h-3 text-green-500" />
                      {:else}
                        <Copy class="w-3 h-3" />
                      {/if}
                    </button>
                    <span class="text-xs px-1.5 py-0.5 bg-orange-500/20 text-orange-600 rounded">
                      平均 {group.avgSizeFormatted}
                    </span>
                  </div>
                </div>
                <div class="flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{group.fileCount} 文件</span>
                  <span>总计 {group.totalSizeFormatted}</span>
                </div>
                <!-- 子统计 -->
                {#if Object.keys(group.subStats).length > 0}
                  <div class="flex flex-wrap gap-1 mt-1">
                    {#each Object.entries(group.subStats).sort((a, b) => b[1] - a[1]).slice(0, 4) as [label, count]}
                      <span class="text-[10px] px-1 py-0.5 bg-muted rounded">
                        {analysisGroupBy === 'ext' ? label : `.${label}`}: {count}
                      </span>
                    {/each}
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {:else if files.length > 0}
          <div class="text-center text-muted-foreground py-4">
            <svelte:component this={currentGroupOption.icon} class="w-8 h-8 mx-auto mb-2 opacity-50" />
            <div>无匹配的分组数据</div>
          </div>
        {:else}
          <div class="text-center text-muted-foreground py-4">
            <BarChart3 class="w-8 h-8 mx-auto mb-2 opacity-50" />
            <div>搜索后显示分析</div>
          </div>
        {/if}
      </div>
      
      <!-- 底部统计 -->
      {#if analysisData.length > 0}
        <div class="p-2 border-t bg-muted/20 text-xs text-muted-foreground shrink-0">
          共 {analysisData.length} 个{currentGroupOption.label}
        </div>
      {/if}
    </div>
  {:else}
    <!-- 紧凑模式 -->
    <div class="flex items-center justify-between mb-1">
      <span class="{c.text} font-semibold flex items-center gap-1">
        <BarChart3 class="w-3 h-3 text-orange-500" />分析
      </span>
      <span class="{c.textSm} text-muted-foreground">{analysisData.length}</span>
    </div>
    <div class="{c.maxHeight} overflow-y-auto">
      {#if analysisData.length > 0}
        <div class="space-y-0.5">
          {#each analysisData.slice(0, 5) as group}
            <div class="flex items-center justify-between text-xs">
              <span class="truncate flex-1">{group.name}</span>
              <span class="text-orange-600 shrink-0">{group.avgSizeFormatted}</span>
            </div>
          {/each}
          {#if analysisData.length > 5}
            <div class="text-[10px] text-muted-foreground">+{analysisData.length - 5} 更多</div>
          {/if}
        </div>
      {:else}
        <div class="{c.text} text-muted-foreground text-center py-2">-</div>
      {/if}
    </div>
  {/if}
{/snippet}

<!-- 通用区块渲染器 -->
{#snippet renderBlockContent(blockId: string, size: SizeMode)}
  {#if blockId === 'path'}{@render pathBlock(size)}
  {:else if blockId === 'filter'}{@render filterBlock(size)}
  {:else if blockId === 'operation'}{@render operationBlock(size)}
  {:else if blockId === 'stats'}{@render statsBlock(size)}
  {:else if blockId === 'progress'}{@render progressBlock(size)}
  {:else if blockId === 'log'}{@render logBlock(size)}
  {:else if blockId === 'tree'}{@render treeBlock(size)}
  {:else if blockId === 'analysis'}{@render analysisBlock(size)}
  {/if}
{/snippet}

<!-- 主渲染 -->
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
