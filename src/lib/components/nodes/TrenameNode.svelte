<script lang="ts">
  /**
   * TrenameNode - 批量重命名节点
   * 
   * 完整功能：
   * 1. 扫描目录（合并/替换模式）
   * 2. 导入 JSON（从剪贴板）
   * 3. 导出 JSON（分段复制）
   * 4. 文件树预览（可展开收起）
   * 5. 冲突检测
   * 6. 执行重命名
   * 7. 撤销操作
   * 8. 分段数值设置
   */
  import { Handle, Position } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Badge } from '$lib/components/ui/badge';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';
  import { api } from '$lib/services/api';
  import { 
    LoaderCircle, 
    FolderOpen, 
    Clipboard, 
    FileEdit,
    Search,
    Undo2,
    Copy,
    Check,
    Download,
    Upload,
    AlertTriangle,
    Play,
    RefreshCw,
    ChevronDown,
    ChevronRight,
    File,
    Folder,
    Trash2,
    TreePine,
    Settings
  } from '@lucide/svelte';
  
  // Props
  export let id: string;
  export let data: {
    config?: { path?: string };
    logs?: string[];
  } = {};

  // 类型定义
  interface FileNode {
    src: string;
    tgt: string;
  }
  interface DirNode {
    src_dir: string;
    tgt_dir: string;
    children: (FileNode | DirNode)[];
  }
  type TreeNode = FileNode | DirNode;

  // 状态
  type Phase = 'idle' | 'scanning' | 'ready' | 'renaming' | 'completed' | 'error';
  let phase: Phase = 'idle';
  let logs: string[] = data?.logs ? [...data.logs] : [];
  let copied = false;
  
  // 扫描配置
  let scanPath = data?.config?.path ?? '';
  let includeHidden = false;
  let excludeExts = '.json,.txt,.html,.htm,.md,.log';
  let maxLines = 1000;
  let useCompact = true;
  
  // 重命名配置
  let basePath = '';
  let dryRun = false;
  
  // 数据状态
  let treeData: TreeNode[] = [];  // 文件树数据
  let segments: string[] = [];
  let currentSegment = 0;
  
  // 统计
  let stats = { total: 0, pending: 0, ready: 0, conflicts: 0 };
  
  // 冲突和撤销
  let conflicts: string[] = [];
  let lastOperationId = '';
  
  // 进度
  let progress = 0;
  let progressText = '';
  
  // UI 状态
  let showTree = false;
  let showSettings = false;
  let expandedPaths: Set<string> = new Set();

  // 计算状态
  $: isRunning = phase === 'scanning' || phase === 'renaming';
  $: canRename = phase === 'ready' && stats.ready > 0;
  $: borderClass = {
    idle: 'border-border',
    scanning: 'border-blue-500 shadow-blue-500/20 shadow-lg',
    ready: 'border-yellow-500',
    renaming: 'border-blue-500 shadow-blue-500/20 shadow-lg',
    completed: 'border-green-500',
    error: 'border-red-500'
  }[phase];

  function log(msg: string) {
    logs = [...logs.slice(-20), msg];
  }

  // 判断节点类型
  function isDir(node: TreeNode): node is DirNode {
    return 'src_dir' in node;
  }

  // 获取节点状态
  function getNodeStatus(node: TreeNode): 'pending' | 'ready' | 'same' {
    if (isDir(node)) {
      if (!node.tgt_dir || node.tgt_dir === '') return 'pending';
      if (node.tgt_dir === node.src_dir) return 'same';
      return 'ready';
    } else {
      if (!node.tgt || node.tgt === '') return 'pending';
      if (node.tgt === node.src) return 'same';
      return 'ready';
    }
  }

  // 切换展开状态
  function toggleExpand(path: string) {
    if (expandedPaths.has(path)) {
      expandedPaths.delete(path);
    } else {
      expandedPaths.add(path);
    }
    expandedPaths = expandedPaths;
  }

  // 解析 JSON 为树结构
  function parseJsonToTree(jsonStr: string): TreeNode[] {
    try {
      const data = JSON.parse(jsonStr);
      return data.root || [];
    } catch {
      return [];
    }
  }

  async function selectFolder() {
    try {
      if (window.pywebview?.api?.open_folder_dialog) {
        const selected = await window.pywebview.api.open_folder_dialog();
        if (selected) scanPath = selected;
      } else {
        log('⚠️ 文件夹选择需要桌面应用');
      }
    } catch (e) {
      log(`选择文件夹失败: ${e}`);
    }
  }

  async function pastePathFromClipboard() {
    try {
      const text = await navigator.clipboard.readText();
      scanPath = text.trim();
    } catch (e) {
      log(`读取剪贴板失败: ${e}`);
    }
  }

  async function handleScan(merge = false) {
    if (!scanPath.trim()) {
      log('❌ 请输入目录路径');
      return;
    }
    
    phase = 'scanning';
    progress = 0;
    progressText = '正在扫描...';
    log(`🔍 ${merge ? '合并' : '替换'}扫描: ${scanPath}`);
    
    try {
      const response = await api.executeNode('trename', {
        action: 'scan',
        paths: [scanPath],
        include_hidden: includeHidden,
        exclude_exts: excludeExts,
        max_lines: maxLines,
        compact: useCompact
      }) as any;
      
      if (response.success && response.data) {
        const newSegments = response.data.segments || [];
        
        if (merge && segments.length > 0) {
          segments = [...segments, ...newSegments];
          stats.total += response.data.total_items || 0;
          stats.pending += response.data.pending_count || 0;
          stats.ready += response.data.ready_count || 0;
        } else {
          segments = newSegments;
          stats = {
            total: response.data.total_items || 0,
            pending: response.data.pending_count || 0,
            ready: response.data.ready_count || 0,
            conflicts: 0
          };
          basePath = response.data.base_path || '';
        }
        
        // 解析文件树
        if (newSegments.length > 0) {
          treeData = parseJsonToTree(newSegments[0]);
        }
        
        currentSegment = 0;
        conflicts = [];
        phase = 'ready';
        log(`✅ 扫描完成: ${response.data.total_items} 项, ${newSegments.length} 段`);
      } else {
        phase = 'error';
        log(`❌ 扫描失败: ${response.message}`);
      }
    } catch (error) {
      phase = 'error';
      log(`❌ 扫描失败: ${error}`);
    }
    
    progress = 0;
    progressText = '';
  }

  async function importFromClipboard(replace = false) {
    try {
      const text = await navigator.clipboard.readText();
      if (!text.trim()) {
        log('❌ 剪贴板为空');
        return;
      }
      
      log('📋 从剪贴板导入...');
      
      const response = await api.executeNode('trename', {
        action: 'import',
        json_content: text
      }) as any;
      
      if (response.success && response.data) {
        if (replace || segments.length === 0) {
          segments = [text];
          stats = {
            total: response.data.total_items || 0,
            pending: response.data.pending_count || 0,
            ready: response.data.ready_count || 0,
            conflicts: 0
          };
        } else {
          segments = [...segments, text];
          stats.total += response.data.total_items || 0;
          stats.pending += response.data.pending_count || 0;
          stats.ready += response.data.ready_count || 0;
        }
        
        // 解析文件树
        treeData = parseJsonToTree(text);
        
        currentSegment = segments.length - 1;
        phase = 'ready';
        log(`✅ 导入成功: ${response.data.total_items} 项`);
      } else {
        log(`❌ 导入失败: ${response.message}`);
      }
    } catch (e) {
      log(`❌ 导入失败: ${e}`);
    }
  }

  async function copySegment(index: number) {
    if (index >= segments.length) return;
    try {
      await navigator.clipboard.writeText(segments[index]);
      copied = true;
      log(`📋 第 ${index + 1} 段已复制`);
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) {
      log(`复制失败: ${e}`);
    }
  }

  async function validateConflicts() {
    if (segments.length === 0) return;
    log('🔍 检测冲突...');
    try {
      const response = await api.executeNode('trename', {
        action: 'validate',
        json_content: segments[currentSegment],
        base_path: basePath
      }) as any;
      
      if (response.success) {
        conflicts = response.data?.conflicts || [];
        stats.conflicts = conflicts.length;
        log(conflicts.length > 0 ? `⚠️ ${conflicts.length} 个冲突` : '✅ 没有冲突');
      } else {
        log(`❌ 验证失败: ${response.message}`);
      }
    } catch (e) {
      log(`❌ 验证失败: ${e}`);
    }
  }

  async function handleRename() {
    if (segments.length === 0 || stats.ready === 0) {
      log('❌ 没有可重命名的项目');
      return;
    }
    
    phase = 'renaming';
    progressText = dryRun ? '模拟执行中...' : '重命名中...';
    log(`${dryRun ? '🔍 模拟' : '▶️ 执行'}重命名...`);
    
    try {
      const response = await api.executeNode('trename', {
        action: 'rename',
        json_content: segments[currentSegment],
        base_path: basePath,
        dry_run: dryRun
      }) as any;
      
      if (response.success) {
        const data = response.data || {};
        lastOperationId = data.operation_id || '';
        phase = 'completed';
        log(`✅ 成功: ${data.success_count}, 失败: ${data.failed_count}`);
        if (lastOperationId) log(`🔄 撤销 ID: ${lastOperationId}`);
      } else {
        phase = 'error';
        log(`❌ 重命名失败: ${response.message}`);
      }
    } catch (error) {
      phase = 'error';
      log(`❌ 重命名失败: ${error}`);
    }
    progressText = '';
  }

  async function handleUndo() {
    log('🔄 撤销...');
    try {
      const response = await api.executeNode('trename', {
        action: 'undo',
        batch_id: lastOperationId
      }) as any;
      
      if (response.success) {
        log(`✅ ${response.message}`);
        lastOperationId = '';
        phase = 'ready';
      } else {
        log(`❌ 撤销失败: ${response.message}`);
      }
    } catch (e) {
      log(`❌ 撤销失败: ${e}`);
    }
  }

  function handleClear() {
    treeData = [];
    segments = [];
    currentSegment = 0;
    stats = { total: 0, pending: 0, ready: 0, conflicts: 0 };
    conflicts = [];
    lastOperationId = '';
    phase = 'idle';
    expandedPaths.clear();
    log('🗑️ 已清空');
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(logs.join('\n'));
    } catch (e) {
      console.error('复制失败:', e);
    }
  }

  void id;
</script>

<!-- 递归渲染文件树节点 -->
{#snippet treeNode(node: TreeNode, path: string, depth: number)}
  {@const isDirectory = isDir(node)}
  {@const status = getNodeStatus(node)}
  {@const expanded = expandedPaths.has(path)}
  {@const name = isDirectory ? node.src_dir : node.src}
  {@const target = isDirectory ? node.tgt_dir : node.tgt}
  
  <div class="flex items-center gap-1 py-0.5 hover:bg-muted/50 rounded" style="padding-left: {depth * 12}px">
    {#if isDirectory}
      <button class="p-0.5 hover:bg-muted rounded" onclick={() => toggleExpand(path)}>
        {#if expanded}
          <ChevronDown class="w-3 h-3 text-muted-foreground" />
        {:else}
          <ChevronRight class="w-3 h-3 text-muted-foreground" />
        {/if}
      </button>
      <Folder class="w-3 h-3 text-yellow-500 shrink-0" />
    {:else}
      <span class="w-4"></span>
      <File class="w-3 h-3 text-blue-500 shrink-0" />
    {/if}
    
    <span class="truncate flex-1 text-xs" title={name}>{name}</span>
    
    {#if target && target !== name}
      <span class="text-xs text-muted-foreground">→</span>
      <span class="truncate text-xs text-green-600 max-w-[80px]" title={target}>{target}</span>
    {/if}
    
    <span class="w-2 h-2 rounded-full shrink-0 {status === 'ready' ? 'bg-green-500' : status === 'pending' ? 'bg-yellow-500' : 'bg-gray-300'}"></span>
  </div>
  
  {#if isDirectory && expanded && node.children}
    {#each node.children as child, i}
      {@render treeNode(child, `${path}/${i}`, depth + 1)}
    {/each}
  {/if}
{/snippet}

<div class="rounded-lg border-2 bg-card p-3 min-w-[380px] max-w-[500px] {borderClass}">
  <Handle type="target" position={Position.Left} class="bg-primary!" />
  
  <!-- 标题栏 -->
  <div class="flex items-center justify-between mb-2">
    <div class="flex items-center gap-2">
      <FileEdit class="w-5 h-5 text-purple-500" />
      <span class="font-semibold">批量重命名</span>
    </div>
    <div class="flex items-center gap-1">
      <Button variant="ghost" size="icon" class="h-6 w-6" onclick={() => showSettings = !showSettings} title="设置">
        <Settings class="h-3 w-3" />
      </Button>
      <Badge variant={phase === 'error' ? 'destructive' : phase === 'completed' ? 'default' : 'secondary'} class="text-xs">
        {phase === 'idle' ? '就绪' : phase === 'scanning' ? '扫描中' : phase === 'ready' ? '待操作' : phase === 'renaming' ? '执行中' : phase === 'completed' ? '完成' : '错误'}
      </Badge>
    </div>
  </div>

  <!-- 设置面板（可收起） -->
  {#if showSettings}
    <div class="mb-2 p-2 rounded bg-muted/50 space-y-2 text-xs">
      <div class="flex items-center gap-2">
        <span class="text-muted-foreground w-16">分段行数:</span>
        <Input type="number" bind:value={maxLines} min={100} max={5000} step={100} class="h-6 w-20 text-xs" />
        <span class="text-muted-foreground">排除扩展名:</span>
        <Input bind:value={excludeExts} class="flex-1 h-6 text-xs" placeholder=".json,.txt" />
      </div>
      <div class="flex items-center gap-4">
        <label class="flex items-center gap-1 cursor-pointer">
          <Checkbox bind:checked={includeHidden} class="h-3 w-3" />
          <span>包含隐藏文件</span>
        </label>
        <label class="flex items-center gap-1 cursor-pointer">
          <Checkbox bind:checked={useCompact} class="h-3 w-3" />
          <span>紧凑格式</span>
        </label>
        <label class="flex items-center gap-1 cursor-pointer">
          <Checkbox bind:checked={dryRun} class="h-3 w-3" />
          <span>模拟执行</span>
        </label>
      </div>
    </div>
  {/if}

  <!-- 扫描区域 -->
  <div class="mb-2 space-y-1">
    <div class="flex gap-1">
      <Input bind:value={scanPath} placeholder="目录路径..." disabled={isRunning} class="flex-1 h-7 text-xs" />
      <Button variant="ghost" size="icon" class="h-7 w-7" onclick={selectFolder} disabled={isRunning}>
        <FolderOpen class="h-3 w-3" />
      </Button>
      <Button variant="ghost" size="icon" class="h-7 w-7" onclick={pastePathFromClipboard} disabled={isRunning}>
        <Clipboard class="h-3 w-3" />
      </Button>
    </div>
    <div class="flex gap-1">
      <Button variant="outline" size="sm" class="flex-1 h-7 text-xs" onclick={() => handleScan(false)} disabled={isRunning}>
        <RefreshCw class="h-3 w-3 mr-1" />替换扫描
      </Button>
      <Button variant="outline" size="sm" class="flex-1 h-7 text-xs" onclick={() => handleScan(true)} disabled={isRunning}>
        <Download class="h-3 w-3 mr-1" />合并扫描
      </Button>
    </div>
  </div>

  <!-- 导入/导出 -->
  <div class="mb-2 flex gap-1">
    <Button variant="outline" size="sm" class="flex-1 h-7 text-xs" onclick={() => importFromClipboard(false)} disabled={isRunning}>
      <Upload class="h-3 w-3 mr-1" />导入
    </Button>
    <Button variant="outline" size="sm" class="flex-1 h-7 text-xs" onclick={() => importFromClipboard(true)} disabled={isRunning}>
      <RefreshCw class="h-3 w-3 mr-1" />替换导入
    </Button>
    {#if segments.length > 0}
      {#if segments.length > 1}
        <select bind:value={currentSegment} class="h-7 text-xs rounded border bg-background px-1 w-16">
          {#each segments as _, i}
            <option value={i}>段{i + 1}</option>
          {/each}
        </select>
      {/if}
      <Button variant="outline" size="sm" class="h-7 text-xs" onclick={() => copySegment(currentSegment)}>
        {#if copied}<Check class="h-3 w-3 text-green-500" />{:else}<Copy class="h-3 w-3" />{/if}
      </Button>
    {/if}
  </div>

  <!-- 统计信息 -->
  {#if stats.total > 0}
    <div class="mb-2 grid grid-cols-4 gap-1 text-center text-xs">
      <div class="p-1 rounded bg-muted"><div class="font-semibold">{stats.total}</div><div class="text-muted-foreground text-[10px]">总计</div></div>
      <div class="p-1 rounded bg-muted"><div class="font-semibold text-yellow-600">{stats.pending}</div><div class="text-muted-foreground text-[10px]">待翻译</div></div>
      <div class="p-1 rounded bg-muted"><div class="font-semibold text-green-600">{stats.ready}</div><div class="text-muted-foreground text-[10px]">可重命名</div></div>
      <div class="p-1 rounded bg-muted"><div class="font-semibold {stats.conflicts > 0 ? 'text-red-600' : ''}">{stats.conflicts}</div><div class="text-muted-foreground text-[10px]">冲突</div></div>
    </div>
  {/if}

  <!-- 文件树预览（可展开收起） -->
  {#if treeData.length > 0}
    <div class="mb-2">
      <button 
        class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground w-full"
        onclick={() => showTree = !showTree}
      >
        {#if showTree}
          <ChevronDown class="w-3 h-3" />
        {:else}
          <ChevronRight class="w-3 h-3" />
        {/if}
        <TreePine class="w-3 h-3" />
        <span>文件树预览 ({treeData.length} 项)</span>
      </button>
      
      {#if showTree}
        <div class="mt-1 p-2 rounded bg-muted/30 max-h-40 overflow-y-auto text-xs">
          {#each treeData as node, i}
            {@render treeNode(node, String(i), 0)}
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <!-- 冲突警告 -->
  {#if conflicts.length > 0}
    <div class="mb-2 p-2 rounded bg-red-50 border border-red-200 text-xs">
      <div class="flex items-center gap-1 text-red-600 font-medium">
        <AlertTriangle class="w-3 h-3" />
        <span>{conflicts.length} 个冲突</span>
      </div>
      <div class="max-h-12 overflow-y-auto text-red-500 mt-1">
        {#each conflicts.slice(0, 2) as c}<div class="truncate">• {c}</div>{/each}
        {#if conflicts.length > 2}<div class="text-muted-foreground">... 还有 {conflicts.length - 2} 个</div>{/if}
      </div>
    </div>
  {/if}

  <!-- 进度条 -->
  {#if isRunning}
    <div class="mb-2"><Progress value={progress} class="h-1" /><div class="text-xs text-muted-foreground mt-0.5">{progressText}</div></div>
  {/if}

  <!-- 操作按钮 -->
  <div class="mb-2 space-y-1">
    <div class="flex gap-1 items-center text-xs">
      <span class="text-muted-foreground shrink-0">基础路径:</span>
      <Input bind:value={basePath} placeholder="自动检测..." disabled={isRunning} class="flex-1 h-6 text-xs" />
    </div>
    <div class="flex gap-1">
      <Button variant="outline" size="sm" class="h-7 text-xs" onclick={validateConflicts} disabled={isRunning || segments.length === 0}>
        <AlertTriangle class="h-3 w-3 mr-1" />冲突
      </Button>
      <Button size="sm" class="flex-1 h-7 text-xs" onclick={handleRename} disabled={isRunning || !canRename}>
        {#if phase === 'renaming'}<LoaderCircle class="h-3 w-3 mr-1 animate-spin" />{:else}<Play class="h-3 w-3 mr-1" />{/if}
        执行重命名
      </Button>
      <Button variant="outline" size="sm" class="h-7 text-xs" onclick={handleUndo} disabled={isRunning || !lastOperationId}>
        <Undo2 class="h-3 w-3" />
      </Button>
      <Button variant="ghost" size="sm" class="h-7 text-xs" onclick={handleClear} disabled={isRunning}>
        <Trash2 class="h-3 w-3" />
      </Button>
    </div>
  </div>

  <!-- 日志 -->
  {#if logs.length > 0}
    <div class="relative">
      <Button variant="ghost" size="icon" class="absolute top-0.5 right-0.5 h-5 w-5 opacity-60 hover:opacity-100 z-10" onclick={copyLogs}>
        <Copy class="h-3 w-3" />
      </Button>
      <div class="p-2 pr-7 bg-muted rounded text-xs font-mono max-h-16 overflow-y-auto select-text">
        {#each logs.slice(-4) as l}<div class="text-muted-foreground break-all">{l}</div>{/each}
      </div>
    </div>
  {/if}
  
  <Handle type="source" position={Position.Right} class="bg-primary!" />
</div>
