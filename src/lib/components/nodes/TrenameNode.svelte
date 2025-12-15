<script lang="ts">
  /**
   * TrenameNode - 可拖拽调整大小的批量重命名节点
   * 
   * 布局：左右分栏
   * - 左侧：操作区（扫描、导入、执行等）
   * - 右侧：文件树预览（可展开/收起）
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Badge } from '$lib/components/ui/badge';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import { api } from '$lib/services/api';
  import { flowStore } from '$lib/stores';
  import { 
    LoaderCircle, FolderOpen, Clipboard, FileEdit, Search, Undo2, Copy, Check,
    Download, Upload, AlertTriangle, Play, RefreshCw, ChevronDown, ChevronRight,
    File, Folder, Trash2, PanelRightOpen, PanelRightClose, Settings2,
    X, Pin, PinOff
  } from '@lucide/svelte';
  
  export let id: string;
  export let data: { config?: { path?: string }; logs?: string[]; showTree?: boolean } = {};

  // 文件树类型
  interface FileNode { src: string; tgt: string; }
  interface DirNode { src_dir: string; tgt_dir: string; children: (FileNode | DirNode)[]; }
  type TreeNode = FileNode | DirNode;

  // 状态
  type Phase = 'idle' | 'scanning' | 'ready' | 'renaming' | 'completed' | 'error';
  let phase: Phase = 'idle';
  let logs: string[] = data?.logs ? [...data.logs] : [];
  let copied = false;
  let showTree = data?.showTree ?? false;  // 右侧文件树面板
  let showOptions = false;  // 高级选项
  
  // 配置
  let scanPath = data?.config?.path ?? '';
  let includeHidden = false;
  let excludeExts = '.json,.txt,.html,.htm,.md,.log';
  let maxLines = 1000;
  let useCompact = true;
  let basePath = '';
  let dryRun = false;
  
  // 数据
  let treeData: TreeNode[] = [];
  let segments: string[] = [];
  let currentSegment = 0;
  let stats = { total: 0, pending: 0, ready: 0, conflicts: 0 };
  let conflicts: string[] = [];
  let lastOperationId = '';
  let expandedPaths: Set<string> = new Set();
  
  // 节点控制
  let collapsed = false;
  let pinned = false;
  
  function handleClose() { flowStore.removeNode(id); }
  function toggleCollapse() { collapsed = !collapsed; }
  function togglePin() { pinned = !pinned; }

  // 计算
  $: isRunning = phase === 'scanning' || phase === 'renaming';
  $: canRename = phase === 'ready' && stats.ready > 0;

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }
  function isDir(node: TreeNode): node is DirNode { return 'src_dir' in node; }
  function getStatus(node: TreeNode): 'pending' | 'ready' | 'same' {
    const tgt = isDir(node) ? node.tgt_dir : node.tgt;
    const src = isDir(node) ? node.src_dir : node.src;
    if (!tgt || tgt === '') return 'pending';
    if (tgt === src) return 'same';
    return 'ready';
  }
  function toggleExpand(path: string) {
    expandedPaths.has(path) ? expandedPaths.delete(path) : expandedPaths.add(path);
    expandedPaths = expandedPaths;
  }
  function parseTree(json: string): TreeNode[] {
    try { return JSON.parse(json).root || []; } catch { return []; }
  }

  async function selectFolder() {
    try {
      if (window.pywebview?.api?.open_folder_dialog) {
        const s = await window.pywebview.api.open_folder_dialog();
        if (s) scanPath = s;
      } else log('⚠️ 需要桌面应用');
    } catch (e) { log(`选择失败: ${e}`); }
  }
  async function pastePath() {
    try { scanPath = (await navigator.clipboard.readText()).trim(); } catch (e) { log(`粘贴失败: ${e}`); }
  }
  async function handleScan(merge = false) {
    if (!scanPath.trim()) { log('❌ 请输入路径'); return; }
    phase = 'scanning';
    log(`🔍 ${merge ? '合并' : '替换'}扫描: ${scanPath}`);
    try {
      const r = await api.executeNode('trename', {
        action: 'scan', paths: [scanPath], include_hidden: includeHidden,
        exclude_exts: excludeExts, max_lines: maxLines, compact: useCompact
      }) as any;
      if (r.success && r.data) {
        const segs = r.data.segments || [];
        if (merge && segments.length > 0) {
          segments = [...segments, ...segs];
          stats.total += r.data.total_items || 0;
          stats.pending += r.data.pending_count || 0;
          stats.ready += r.data.ready_count || 0;
        } else {
          segments = segs;
          stats = { total: r.data.total_items || 0, pending: r.data.pending_count || 0, ready: r.data.ready_count || 0, conflicts: 0 };
          basePath = r.data.base_path || '';
        }
        if (segs.length > 0) treeData = parseTree(segs[0]);
        currentSegment = 0; conflicts = []; phase = 'ready';
        log(`✅ ${r.data.total_items} 项, ${segs.length} 段`);
      } else { phase = 'error'; log(`❌ ${r.message}`); }
    } catch (e) { phase = 'error'; log(`❌ ${e}`); }
  }

  async function importJson(replace = false) {
    try {
      const text = await navigator.clipboard.readText();
      if (!text.trim()) { log('❌ 剪贴板为空'); return; }
      log('📋 导入中...');
      const r = await api.executeNode('trename', { action: 'import', json_content: text }) as any;
      if (r.success && r.data) {
        if (replace || segments.length === 0) {
          segments = [text];
          stats = { total: r.data.total_items || 0, pending: r.data.pending_count || 0, ready: r.data.ready_count || 0, conflicts: 0 };
        } else {
          segments = [...segments, text];
          stats.total += r.data.total_items || 0;
          stats.pending += r.data.pending_count || 0;
          stats.ready += r.data.ready_count || 0;
        }
        treeData = parseTree(text);
        currentSegment = segments.length - 1; phase = 'ready';
        log(`✅ 导入 ${r.data.total_items} 项`);
      } else log(`❌ ${r.message}`);
    } catch (e) { log(`❌ ${e}`); }
  }
  async function copySegment(i: number) {
    if (i >= segments.length) return;
    try { await navigator.clipboard.writeText(segments[i]); copied = true; log(`📋 段${i+1}已复制`); setTimeout(() => copied = false, 2000); }
    catch (e) { log(`复制失败: ${e}`); }
  }
  async function validate() {
    if (!segments.length) return;
    log('🔍 检测冲突...');
    try {
      const r = await api.executeNode('trename', { action: 'validate', json_content: segments[currentSegment], base_path: basePath }) as any;
      if (r.success) { conflicts = r.data?.conflicts || []; stats.conflicts = conflicts.length; log(conflicts.length ? `⚠️ ${conflicts.length} 冲突` : '✅ 无冲突'); }
      else log(`❌ ${r.message}`);
    } catch (e) { log(`❌ ${e}`); }
  }
  async function handleRename() {
    if (!segments.length || !stats.ready) { log('❌ 无可重命名项'); return; }
    phase = 'renaming'; log(`${dryRun ? '🔍 模拟' : '▶️ 执行'}重命名...`);
    try {
      const r = await api.executeNode('trename', { action: 'rename', json_content: segments[currentSegment], base_path: basePath, dry_run: dryRun }) as any;
      if (r.success) {
        lastOperationId = r.data?.operation_id || ''; phase = 'completed';
        log(`✅ 成功${r.data?.success_count || 0} 失败${r.data?.failed_count || 0}`);
        if (lastOperationId) log(`🔄 撤销ID: ${lastOperationId}`);
      } else { phase = 'error'; log(`❌ ${r.message}`); }
    } catch (e) { phase = 'error'; log(`❌ ${e}`); }
  }
  async function handleUndo() {
    log('🔄 撤销...');
    try {
      const r = await api.executeNode('trename', { action: 'undo', batch_id: lastOperationId }) as any;
      if (r.success) { log(`✅ ${r.message}`); lastOperationId = ''; phase = 'ready'; }
      else log(`❌ ${r.message}`);
    } catch (e) { log(`❌ ${e}`); }
  }
  function clear() {
    treeData = []; segments = []; currentSegment = 0;
    stats = { total: 0, pending: 0, ready: 0, conflicts: 0 };
    conflicts = []; lastOperationId = ''; phase = 'idle'; expandedPaths.clear();
    log('🗑️ 已清空');
  }
  async function copyLogs() { try { await navigator.clipboard.writeText(logs.join('\n')); } catch {} }
  void id;
</script>

<!-- 递归渲染文件树 -->
{#snippet treeNode(node: TreeNode, path: string, depth: number)}
  {@const dir = isDir(node)}
  {@const status = getStatus(node)}
  {@const exp = expandedPaths.has(path)}
  {@const name = dir ? node.src_dir : node.src}
  {@const tgt = dir ? node.tgt_dir : node.tgt}
  
  <div class="flex items-center gap-1 py-0.5 hover:bg-muted/50 rounded text-xs" style="padding-left: {depth * 12}px">
    {#if dir}
      <button class="p-0.5 hover:bg-muted rounded" onclick={() => toggleExpand(path)}>
        {#if exp}<ChevronDown class="w-3 h-3" />{:else}<ChevronRight class="w-3 h-3" />{/if}
      </button>
      <Folder class="w-3 h-3 text-yellow-500 shrink-0" />
    {:else}
      <span class="w-4"></span>
      <File class="w-3 h-3 text-blue-500 shrink-0" />
    {/if}
    <span class="truncate flex-1 min-w-0" title={name}>{name}</span>
    {#if tgt && tgt !== name}
      <span class="text-muted-foreground shrink-0">→</span>
      <span class="truncate text-green-600 max-w-24" title={tgt}>{tgt}</span>
    {/if}
    <span class="w-2 h-2 rounded-full shrink-0 {status === 'ready' ? 'bg-green-500' : status === 'pending' ? 'bg-yellow-500' : 'bg-gray-300'}"></span>
  </div>
  {#if dir && exp && node.children}
    {#each node.children as child, i}{@render treeNode(child, `${path}/${i}`, depth + 1)}{/each}
  {/if}
{/snippet}

<div class="rounded-lg border-2 bg-card transition-all h-full w-full flex flex-col overflow-hidden
  {phase === 'error' ? 'border-red-500' : phase === 'completed' ? 'border-green-500' : phase === 'scanning' || phase === 'renaming' ? 'border-blue-500 shadow-lg' : 'border-border'}">
  
  <!-- NodeResizer 支持任意拖拽调整大小 -->
  <NodeResizer minWidth={280} minHeight={200} />
  
  <Handle type="target" position={Position.Left} class="bg-primary!" />
  
  <!-- 标题栏 -->
  <div class="flex items-center justify-between px-2 py-1.5 border-b shrink-0 bg-muted/30">
    <!-- 左侧：折叠 + 图标 + 标题 -->
    <div class="flex items-center gap-1.5">
      <button class="p-0.5 rounded hover:bg-muted" onclick={toggleCollapse} title={collapsed ? '展开' : '折叠'}>
        {#if collapsed}<ChevronRight class="w-4 h-4" />{:else}<ChevronDown class="w-4 h-4" />{/if}
      </button>
      <FileEdit class="w-4 h-4 text-purple-500" />
      <span class="font-semibold text-sm">批量重命名</span>
      <Badge variant={phase === 'error' ? 'destructive' : phase === 'completed' ? 'default' : 'secondary'} class="text-xs ml-1">
        {phase === 'idle' ? '就绪' : phase === 'scanning' ? '扫描' : phase === 'ready' ? '待操作' : phase === 'renaming' ? '执行' : phase === 'completed' ? '完成' : '错误'}
      </Badge>
    </div>
    <!-- 右侧：操作按钮 -->
    <div class="flex items-center gap-0.5">
      <Button variant="ghost" size="icon" class="h-6 w-6" onclick={() => showOptions = !showOptions} title="选项">
        <Settings2 class="h-3 w-3" />
      </Button>
      <Button variant="ghost" size="icon" class="h-6 w-6" onclick={() => showTree = !showTree} title="文件树">
        {#if showTree}<PanelRightClose class="h-3 w-3" />{:else}<PanelRightOpen class="h-3 w-3" />{/if}
      </Button>
      <button class="p-1 rounded hover:bg-muted {pinned ? 'text-primary' : 'text-muted-foreground'}" onclick={togglePin} title={pinned ? '取消固定' : '固定'}>
        {#if pinned}<Pin class="w-3.5 h-3.5" />{:else}<PinOff class="w-3.5 h-3.5" />{/if}
      </button>
      <button class="p-1 rounded hover:bg-destructive hover:text-destructive-foreground text-muted-foreground" onclick={handleClose} title="关闭">
        <X class="w-3.5 h-3.5" />
      </button>
    </div>
  </div>

  <!-- 主体：左右分栏（折叠时隐藏） -->
  {#if !collapsed}
  <div class="flex flex-1 min-h-0 overflow-hidden nodrag">
    <!-- 左侧：操作区 -->
    <div class="flex flex-col p-2 space-y-2 {showTree ? 'w-1/2 border-r' : 'flex-1'} overflow-y-auto">
      <!-- 路径输入 -->
      <div class="flex gap-1">
        <Input bind:value={scanPath} placeholder="目录路径..." disabled={isRunning} class="flex-1 h-7 text-xs" />
        <Button variant="ghost" size="icon" class="h-7 w-7 shrink-0" onclick={selectFolder} disabled={isRunning}><FolderOpen class="h-3 w-3" /></Button>
        <Button variant="ghost" size="icon" class="h-7 w-7 shrink-0" onclick={pastePath} disabled={isRunning}><Clipboard class="h-3 w-3" /></Button>
      </div>
      
      <!-- 扫描按钮 -->
      <div class="flex gap-1">
        <Button variant="outline" size="sm" class="flex-1 h-7 text-xs" onclick={() => handleScan(false)} disabled={isRunning}>
          {#if isRunning && phase === 'scanning'}<LoaderCircle class="h-3 w-3 mr-1 animate-spin" />{:else}<RefreshCw class="h-3 w-3 mr-1" />{/if}替换
        </Button>
        <Button variant="outline" size="sm" class="flex-1 h-7 text-xs" onclick={() => handleScan(true)} disabled={isRunning}>
          <Download class="h-3 w-3 mr-1" />合并
        </Button>
      </div>
      
      <!-- 导入/导出 -->
      <div class="flex gap-1">
        <Button variant="ghost" size="sm" class="flex-1 h-7 text-xs" onclick={() => importJson(false)} disabled={isRunning} title="从剪贴板导入JSON">
          <Upload class="h-3 w-3 mr-1" />导入
        </Button>
        <Button variant="ghost" size="sm" class="flex-1 h-7 text-xs" onclick={() => importJson(true)} disabled={isRunning} title="替换当前数据">
          <Copy class="h-3 w-3 mr-1" />替换
        </Button>
        <Button variant="ghost" size="sm" class="flex-1 h-7 text-xs" onclick={() => copySegment(currentSegment)} disabled={!segments.length} title="复制当前段">
          {#if copied}<Check class="h-3 w-3 mr-1 text-green-500" />{:else}<Clipboard class="h-3 w-3 mr-1" />{/if}复制
        </Button>
      </div>
      
      <!-- 分段选择器 -->
      {#if segments.length > 1}
        <div class="flex items-center gap-1 text-xs flex-wrap">
          <span class="text-muted-foreground">段:</span>
          {#each segments as _, i}
            <Button 
              variant={currentSegment === i ? 'default' : 'ghost'} 
              size="sm" 
              class="h-5 w-5 p-0 text-xs"
              onclick={() => { currentSegment = i; treeData = parseTree(segments[i]); }}
            >{i + 1}</Button>
          {/each}
        </div>
      {/if}
      
      <!-- 统计信息 -->
      {#if stats.total > 0}
        <div class="flex gap-2 text-xs flex-wrap">
          <span class="text-muted-foreground">总计: <span class="text-foreground">{stats.total}</span></span>
          <span class="text-yellow-500">待翻译: {stats.pending}</span>
          <span class="text-green-500">就绪: {stats.ready}</span>
          {#if stats.conflicts > 0}<span class="text-red-500">冲突: {stats.conflicts}</span>{/if}
        </div>
      {/if}
      
      <!-- 操作按钮 -->
      <div class="flex gap-1">
        <Button variant="outline" size="sm" class="flex-1 h-7 text-xs" onclick={validate} disabled={isRunning || !segments.length}>
          <Search class="h-3 w-3 mr-1" />冲突
        </Button>
        <Button variant={canRename ? 'default' : 'outline'} size="sm" class="flex-1 h-7 text-xs" onclick={handleRename} disabled={isRunning || !canRename}>
          {#if phase === 'renaming'}<LoaderCircle class="h-3 w-3 mr-1 animate-spin" />{:else}<Play class="h-3 w-3 mr-1" />{/if}执行
        </Button>
        <Button variant="ghost" size="sm" class="h-7 w-7 p-0 shrink-0" onclick={handleUndo} disabled={!lastOperationId} title="撤销">
          <Undo2 class="h-3 w-3" />
        </Button>
        <Button variant="ghost" size="sm" class="h-7 w-7 p-0 shrink-0" onclick={clear} title="清空">
          <Trash2 class="h-3 w-3" />
        </Button>
      </div>
      
      <!-- 高级选项 -->
      {#if showOptions}
        <div class="border rounded p-2 space-y-2 bg-muted/20">
          <div class="flex flex-wrap gap-2 text-xs">
            <label class="flex items-center gap-1">
              <Checkbox bind:checked={includeHidden} class="h-3 w-3" />
              <span>隐藏文件</span>
            </label>
            <label class="flex items-center gap-1">
              <Checkbox bind:checked={dryRun} class="h-3 w-3" />
              <span>模拟执行</span>
            </label>
            <label class="flex items-center gap-1">
              <Checkbox bind:checked={useCompact} class="h-3 w-3" />
              <span>紧凑格式</span>
            </label>
          </div>
          <div class="flex gap-2 text-xs">
            <label class="flex items-center gap-1 flex-1 min-w-0">
              <span class="text-muted-foreground whitespace-nowrap">排除:</span>
              <Input bind:value={excludeExts} class="h-6 text-xs flex-1 min-w-0" placeholder=".json,.txt" />
            </label>
            <label class="flex items-center gap-1">
              <span class="text-muted-foreground whitespace-nowrap">分段:</span>
              <Input type="number" bind:value={maxLines} class="h-6 text-xs w-16" min={50} max={5000} step={100} />
            </label>
          </div>
        </div>
      {/if}
      
      <!-- 冲突列表 -->
      {#if conflicts.length > 0}
        <div class="border border-red-500/30 rounded p-2 bg-red-500/5 max-h-20 overflow-y-auto">
          <div class="text-xs text-red-500 font-medium mb-1 flex items-center gap-1">
            <AlertTriangle class="h-3 w-3" />冲突 ({conflicts.length})
          </div>
          {#each conflicts as c}
            <div class="text-xs text-red-400 truncate" title={c}>{c}</div>
          {/each}
        </div>
      {/if}
      
      <!-- 日志区域 -->
      {#if logs.length > 0}
        <div class="border rounded bg-muted/20 flex-1 min-h-16 max-h-32 overflow-hidden flex flex-col">
          <div class="flex items-center justify-between px-1 py-0.5 border-b bg-muted/30 shrink-0">
            <span class="text-xs text-muted-foreground">日志</span>
            <Button variant="ghost" size="sm" class="h-4 w-4 p-0" onclick={copyLogs} title="复制日志">
              <Clipboard class="h-2 w-2" />
            </Button>
          </div>
          <div class="p-1 space-y-0.5 overflow-y-auto flex-1">
            {#each logs as logItem}
              <div class="text-xs font-mono text-muted-foreground truncate" title={logItem}>{logItem}</div>
            {/each}
          </div>
        </div>
      {/if}
    </div>
    
    <!-- 右侧：文件树面板 -->
    {#if showTree}
      <div class="w-1/2 flex flex-col overflow-hidden">
        <div class="text-xs font-medium p-1 border-b bg-muted/30 flex items-center justify-between shrink-0">
          <span>文件树</span>
          <span class="text-muted-foreground">{stats.total} 项</span>
        </div>
        <div class="flex-1 overflow-y-auto p-1">
          {#if treeData.length > 0}
            {#each treeData as node, i}
              {@render treeNode(node, `root_${i}`, 0)}
            {/each}
          {:else}
            <div class="text-xs text-muted-foreground text-center py-4">暂无数据</div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
  {/if}
  
  <Handle type="source" position={Position.Right} class="bg-primary!" />
</div>
