<script lang="ts">
  /**
   * TrenameNode - 批量重命名节点
   * 使用 TanStack Store 在全屏/普通模式间共享状态
   * 全屏模式使用 GridStack 可拖拽布局
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import * as TreeView from '$lib/components/ui/tree-view';
  import { DashboardGrid, DashboardItem } from '$lib/components/ui/dashboard-grid';
  import type { GridItem } from '$lib/components/ui/dashboard-grid';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from './NodeWrapper.svelte';
  import * as Table from '$lib/components/ui/table';
  import { 
    LoaderCircle, FolderOpen, Clipboard, FilePenLine, Search, Undo2,
    Download, Upload, TriangleAlert, Play, RefreshCw, FileJson,
    File, Folder, Trash2, PanelRightOpen, PanelRightClose, Settings2, Check
  } from '@lucide/svelte';
  import {
    type TreeNode, type TrenameState, type Phase, type OperationRecord,
    isDir, getNodeStatus, parseTree, getPhaseBorderClass,
    DEFAULT_GRID_LAYOUT, DEFAULT_STATS, DEFAULT_EXCLUDE_EXTS, generateDownloadFilename
  } from './trename-utils';
  
  export let id: string;
  export let data: { config?: { path?: string }; logs?: string[]; showTree?: boolean } = {};
  export let isFullscreenRender = false;
  
  // 从 TanStack Store 恢复状态
  const savedState = getNodeState<TrenameState>(id);
  
  // 状态初始化
  let phase: Phase = savedState?.phase ?? 'idle';
  let logs: string[] = savedState?.logs ?? (data?.logs ? [...data.logs] : []);
  let copied = false;
  let showTree = savedState?.showTree ?? data?.showTree ?? true;
  let showOptions = savedState?.showOptions ?? false;
  let showJsonInput = savedState?.showJsonInput ?? false;
  let jsonInputText = savedState?.jsonInputText ?? '';
  
  // 配置
  let scanPath = savedState?.scanPath ?? data?.config?.path ?? '';
  let includeHidden = savedState?.includeHidden ?? false;
  let excludeExts = savedState?.excludeExts ?? DEFAULT_EXCLUDE_EXTS;
  let maxLines = savedState?.maxLines ?? 1000;
  let useCompact = savedState?.useCompact ?? true;
  let basePath = savedState?.basePath ?? '';
  let dryRun = savedState?.dryRun ?? false;
  
  // 数据
  let treeData: TreeNode[] = savedState?.treeData ?? [];
  let segments: string[] = savedState?.segments ?? [];
  let currentSegment = savedState?.currentSegment ?? 0;
  let stats = savedState?.stats ?? { ...DEFAULT_STATS };
  let conflicts: string[] = savedState?.conflicts ?? [];
  let lastOperationId = savedState?.lastOperationId ?? '';
  let operationHistory: OperationRecord[] = savedState?.operationHistory ?? [];
  
  // GridStack 布局（默认值）
  let gridLayout: GridItem[] = savedState?.gridLayout ?? [...DEFAULT_GRID_LAYOUT];
  
  // DashboardGrid 组件引用
  let dashboardGrid: { compact: () => void } | undefined;

  // 处理布局变化
  function handleLayoutChange(newLayout: GridItem[]) {
    gridLayout = newLayout;
    saveState();
  }
  
  // 根据 id 获取布局项
  function getLayoutItem(itemId: string): GridItem {
    return gridLayout.find(item => item.id === itemId) ?? { id: itemId, x: 0, y: 0, w: 1, h: 1 };
  }
  
  // 保存状态到 TanStack Store
  function saveState() {
    setNodeState<TrenameState>(id, {
      phase, logs, showTree, showOptions, showJsonInput, jsonInputText,
      scanPath, includeHidden, excludeExts, maxLines, useCompact, basePath, dryRun,
      treeData, segments, currentSegment, stats, conflicts, lastOperationId, operationHistory,
      gridLayout
    });
  }
  
  // 状态变化时自动保存
  $: if (phase || treeData || segments || stats || gridLayout) {
    saveState();
  }

  // 计算属性
  $: isRunning = phase === 'scanning' || phase === 'renaming';
  $: canRename = phase === 'ready' && stats.ready > 0;
  $: borderClass = getPhaseBorderClass(phase);

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }
  
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
      await processJsonImport(text, replace);
    } catch (e) { log(`❌ ${e}`); }
  }
  
  async function importFromInput() {
    if (!jsonInputText.trim()) { log('❌ 输入为空'); return; }
    await processJsonImport(jsonInputText, true);
    jsonInputText = '';
    showJsonInput = false;
  }
  
  async function processJsonImport(text: string, replace: boolean) {
    log('📋 导入中...');
    try {
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
  
  function downloadSegment(i: number) {
    if (i >= segments.length) return;
    try {
      const content = segments[i];
      const blob = new Blob([content], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = generateDownloadFilename(i);
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      log(`💾 段${i + 1}已下载`);
    } catch (e) { log(`下载失败: ${e}`); }
  }
  
  function downloadAllSegments() {
    if (segments.length === 0) return;
    if (segments.length === 1) { downloadSegment(0); return; }
    segments.forEach((_, i) => downloadSegment(i));
    log(`💾 已下载全部 ${segments.length} 段`);
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
        const successCount = r.data?.success_count || 0;
        log(`✅ 成功${successCount} 失败${r.data?.failed_count || 0}`);
        if (lastOperationId && !dryRun) {
          operationHistory = [{
            id: lastOperationId, time: new Date().toLocaleTimeString(), count: successCount, canUndo: true
          }, ...operationHistory].slice(0, 10);
        }
      } else { phase = 'error'; log(`❌ ${r.message}`); }
    } catch (e) { phase = 'error'; log(`❌ ${e}`); }
  }

  async function handleUndo(opId?: string) {
    const targetId = opId || lastOperationId;
    if (!targetId) { log('❌ 无可撤销操作'); return; }
    log('🔄 撤销...');
    try {
      const r = await api.executeNode('trename', { action: 'undo', batch_id: targetId }) as any;
      if (r.success) { 
        log(`✅ ${r.message}`); 
        operationHistory = operationHistory.map(op => op.id === targetId ? { ...op, canUndo: false } : op);
        if (targetId === lastOperationId) lastOperationId = '';
        phase = 'ready'; 
      }
      else log(`❌ ${r.message}`);
    } catch (e) { log(`❌ ${e}`); }
  }
  
  function clear() {
    treeData = []; segments = []; currentSegment = 0;
    stats = { ...DEFAULT_STATS };
    conflicts = []; lastOperationId = ''; phase = 'idle';
    log('🗑️ 已清空');
  }
  
  async function copyLogs() { try { await navigator.clipboard.writeText(logs.join('\n')); } catch {} }
</script>

<!-- 递归渲染文件树 -->
{#snippet renderTreeNode(node: TreeNode)}
  {@const dir = isDir(node)}
  {@const status = getNodeStatus(node)}
  {@const srcName = dir ? node.src_dir : node.src}
  {@const tgt = dir ? node.tgt_dir : node.tgt}
  {@const statusClass = status === 'ready' ? 'bg-green-500' : status === 'pending' ? 'bg-yellow-500' : 'bg-gray-300'}
  {@const hasChange = tgt && tgt !== srcName}
  
  {#if dir}
    <TreeView.Folder name={srcName} open={true} class="text-xs">
      {#snippet icon()}
        <div class="flex items-center gap-1">
          <Folder class="w-3 h-3 text-yellow-500 shrink-0" />
          <span class="w-2 h-2 rounded-full shrink-0 {statusClass}"></span>
        </div>
      {/snippet}
      {#snippet children()}
        {#if hasChange}
          <div class="text-xs text-green-600 pl-4 py-0.5 truncate" title={tgt}>→ {tgt}</div>
        {/if}
        {#if node.children}
          {#each node.children as child}
            {@render renderTreeNode(child)}
          {/each}
        {/if}
      {/snippet}
    </TreeView.Folder>
  {:else}
    <div class="flex flex-col py-0.5 text-xs pl-1">
      <div class="flex items-center gap-1">
        <File class="w-3 h-3 text-blue-500 shrink-0" />
        <span class="truncate flex-1" title={srcName}>{srcName}</span>
        <span class="w-2 h-2 rounded-full shrink-0 {statusClass}"></span>
      </div>
      {#if hasChange}
        <div class="text-green-600 pl-4 truncate" title={tgt}>→ {tgt}</div>
      {/if}
    </div>
  {/if}
{/snippet}


<div class="h-full w-full flex flex-col overflow-hidden">
  {#if !isFullscreenRender}
    <NodeResizer minWidth={240} minHeight={180} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}
  
  <NodeWrapper 
    nodeId={id} 
    title="trename" 
    icon={FilePenLine} 
    status={phase} 
    {borderClass} 
    {isFullscreenRender}
    onCompact={() => dashboardGrid?.compact()}
    onResetLayout={() => { gridLayout = [...DEFAULT_GRID_LAYOUT]; saveState(); }}
  >
    {#snippet headerExtra()}
      <Button variant="ghost" size="icon" class="h-6 w-6" onclick={() => showOptions = !showOptions} title="选项">
        <Settings2 class="h-3 w-3" />
      </Button>
      <Button variant="ghost" size="icon" class="h-6 w-6" onclick={() => showTree = !showTree} title="文件树">
        {#if showTree}<PanelRightClose class="h-3 w-3" />{:else}<PanelRightOpen class="h-3 w-3" />{/if}
      </Button>
    {/snippet}
    
    {#snippet children()}
      {#if isFullscreenRender}
        <!-- 全屏模式：GridStack 可拖拽布局 -->
        <div class="h-full overflow-hidden">
          <DashboardGrid 
            bind:this={dashboardGrid}
            columns={4} 
            cellHeight={80} 
            margin={12}
            showToolbar={false}
            onLayoutChange={handleLayoutChange}
          >
            <!-- 路径输入 + 扫描 -->
            {@const pathItem = getLayoutItem('path')}
            <DashboardItem id="path" x={pathItem.x} y={pathItem.y} w={pathItem.w} h={pathItem.h} minW={2} minH={2}>
              <div class="h-full flex flex-col p-2">
                <div class="flex items-center gap-2 mb-3">
                  <FolderOpen class="w-5 h-5 text-primary" />
                  <span class="font-semibold">扫描路径</span>
                </div>
                <div class="flex gap-2 mb-4">
                  <Input bind:value={scanPath} placeholder="输入目录路径..." disabled={isRunning} class="flex-1 h-10" />
                  <Button variant="outline" size="icon" class="h-10 w-10 shrink-0" onclick={selectFolder} disabled={isRunning}>
                    <FolderOpen class="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="icon" class="h-10 w-10 shrink-0" onclick={pastePath} disabled={isRunning}>
                    <Clipboard class="h-4 w-4" />
                  </Button>
                </div>
                <div class="flex gap-2">
                  <Button variant="outline" class="flex-1 h-12" onclick={() => handleScan(false)} disabled={isRunning}>
                    {#if isRunning && phase === 'scanning'}<LoaderCircle class="h-4 w-4 mr-2 animate-spin" />{:else}<RefreshCw class="h-4 w-4 mr-2" />{/if}替换扫描
                  </Button>
                  <Button variant="outline" class="flex-1 h-12" onclick={() => handleScan(true)} disabled={isRunning}>
                    <Download class="h-4 w-4 mr-2" />合并扫描
                  </Button>
                </div>
              </div>
            </DashboardItem>

            
            <!-- 操作按钮 -->
            {@const opItem = getLayoutItem('operation')}
            <DashboardItem id="operation" x={opItem.x} y={opItem.y} w={opItem.w} h={opItem.h} minW={1} minH={2}>
              <div class="h-full flex flex-col p-2">
                <div class="flex items-center gap-2 mb-3">
                  <Play class="w-5 h-5 text-green-500" />
                  <span class="font-semibold">操作</span>
                </div>
                <div class="flex flex-col gap-2 flex-1 justify-center">
                  <Button variant="outline" class="h-12" onclick={validate} disabled={isRunning || !segments.length}>
                    <Search class="h-4 w-4 mr-2" />检测冲突
                  </Button>
                  <Button variant={canRename ? 'default' : 'outline'} class="h-12" onclick={handleRename} disabled={isRunning || !canRename}>
                    {#if phase === 'renaming'}<LoaderCircle class="h-4 w-4 mr-2 animate-spin" />{:else}<Play class="h-4 w-4 mr-2" />{/if}执行重命名
                  </Button>
                  <Button variant="ghost" class="h-10" onclick={clear}>
                    <Trash2 class="h-4 w-4 mr-2" />清空
                  </Button>
                </div>
              </div>
            </DashboardItem>
            
            <!-- 统计信息 -->
            {@const statsItem = getLayoutItem('stats')}
            <DashboardItem id="stats" x={statsItem.x} y={statsItem.y} w={statsItem.w} h={statsItem.h} minW={1} minH={2}>
              <div class="h-full flex flex-col p-2">
                <div class="flex items-center gap-2 mb-3">
                  <FilePenLine class="w-5 h-5 text-blue-500" />
                  <span class="font-semibold">统计</span>
                </div>
                <div class="space-y-2 flex-1">
                  <div class="flex items-center justify-between p-2 bg-muted/50 rounded-lg">
                    <span class="text-sm">总计</span>
                    <span class="text-xl font-bold">{stats.total}</span>
                  </div>
                  <div class="flex items-center justify-between p-2 bg-yellow-500/10 rounded-lg">
                    <span class="text-sm">待翻译</span>
                    <span class="text-xl font-bold text-yellow-600">{stats.pending}</span>
                  </div>
                  <div class="flex items-center justify-between p-2 bg-green-500/10 rounded-lg">
                    <span class="text-sm">就绪</span>
                    <span class="text-xl font-bold text-green-600">{stats.ready}</span>
                  </div>
                  {#if stats.conflicts > 0}
                    <div class="flex items-center justify-between p-2 bg-red-500/10 rounded-lg">
                      <span class="text-sm">冲突</span>
                      <span class="text-xl font-bold text-red-600">{stats.conflicts}</span>
                    </div>
                  {/if}
                </div>
              </div>
            </DashboardItem>

            
            <!-- 导入/导出 -->
            {@const importItem = getLayoutItem('importExport')}
            <DashboardItem id="importExport" x={importItem.x} y={importItem.y} w={importItem.w} h={importItem.h} minW={2} minH={1}>
              <div class="h-full flex items-center gap-3 p-2">
                <Button variant="outline" class="flex-1 h-10" onclick={() => importJson(false)} disabled={isRunning}>
                  <Upload class="h-4 w-4 mr-2" />从剪贴板导入
                </Button>
                <Button variant="outline" class="flex-1 h-10" onclick={() => copySegment(currentSegment)} disabled={!segments.length}>
                  {#if copied}<Check class="h-4 w-4 mr-2 text-green-500" />{:else}<Clipboard class="h-4 w-4 mr-2" />{/if}复制当前段
                </Button>
                <Button variant="outline" class="h-10 w-10 shrink-0" onclick={() => downloadSegment(currentSegment)} disabled={!segments.length}>
                  <Download class="h-4 w-4" />
                </Button>
                {#if segments.length > 1}
                  <div class="flex items-center gap-1 text-sm">
                    <span class="text-muted-foreground">段:</span>
                    {#each segments as _, i}
                      <Button variant={currentSegment === i ? 'default' : 'ghost'} size="sm" class="h-7 w-7 p-0"
                        onclick={() => { currentSegment = i; treeData = parseTree(segments[i]); }}>{i + 1}</Button>
                    {/each}
                  </div>
                {/if}
              </div>
            </DashboardItem>
            
            <!-- 文件树 -->
            {@const treeItem = getLayoutItem('tree')}
            <DashboardItem id="tree" x={treeItem.x} y={treeItem.y} w={treeItem.w} h={treeItem.h} minW={2} minH={2}>
              <div class="h-full flex flex-col overflow-hidden">
                <div class="flex items-center justify-between p-3 border-b bg-muted/30 shrink-0">
                  <span class="font-semibold flex items-center gap-2">
                    <Folder class="w-5 h-5 text-yellow-500" />文件树
                  </span>
                  <span class="text-sm text-muted-foreground">{stats.total} 项</span>
                </div>
                <div class="flex-1 overflow-y-auto p-2">
                  {#if treeData.length > 0}
                    <TreeView.Root class="text-sm">
                      {#each treeData as node}{@render renderTreeNode(node)}{/each}
                    </TreeView.Root>
                  {:else}
                    <div class="text-center text-muted-foreground py-8">扫描后显示文件树</div>
                  {/if}
                </div>
              </div>
            </DashboardItem>

            
            <!-- 日志 + 历史 -->
            {@const logItem = getLayoutItem('log')}
            <DashboardItem id="log" x={logItem.x} y={logItem.y} w={logItem.w} h={logItem.h} minW={1} minH={2}>
              <div class="h-full flex flex-col p-2">
                <div class="flex items-center justify-between mb-2 shrink-0">
                  <span class="font-semibold text-sm">日志</span>
                  <Button variant="ghost" size="icon" class="h-6 w-6" onclick={copyLogs}>
                    <Clipboard class="h-3 w-3" />
                  </Button>
                </div>
                <div class="flex-1 overflow-y-auto bg-muted/30 rounded-xl p-2 font-mono text-xs space-y-1 mb-3" style="max-height: 120px;">
                  {#if logs.length > 0}
                    {#each logs.slice(-12) as logItem}
                      <div class="text-muted-foreground break-all">{logItem}</div>
                    {/each}
                  {:else}
                    <div class="text-muted-foreground text-center py-4">暂无日志</div>
                  {/if}
                </div>
                
                <div class="flex items-center gap-2 mb-2 shrink-0">
                  <Undo2 class="w-4 h-4" />
                  <span class="font-semibold text-sm">操作历史</span>
                </div>
                <div class="flex-1 overflow-y-auto">
                  {#if operationHistory.length > 0}
                    {#each operationHistory as op}
                      <div class="flex items-center justify-between p-2 bg-muted/30 rounded-lg mb-1 text-xs">
                        <span>{op.time} - {op.count}项</span>
                        {#if op.canUndo}
                          <Button variant="ghost" size="sm" class="h-6 px-2 text-xs" onclick={() => handleUndo(op.id)}>撤销</Button>
                        {:else}
                          <span class="text-muted-foreground">已撤销</span>
                        {/if}
                      </div>
                    {/each}
                  {:else}
                    <div class="text-xs text-muted-foreground text-center py-2">暂无记录</div>
                  {/if}
                </div>
              </div>
            </DashboardItem>
          </DashboardGrid>
        </div>
      {:else}
        <!-- 普通模式：Bento 块布局 -->
        <div class="flex-1 overflow-y-auto p-2">
          <div class="grid grid-cols-2 gap-2" style="grid-auto-rows: minmax(auto, max-content);">
            
            <!-- 路径输入块 -->
            <div class="col-span-2 bg-card rounded-2xl border p-3 shadow-sm">
              <div class="flex items-center gap-1.5 mb-2">
                <FolderOpen class="w-4 h-4 text-primary" />
                <span class="text-xs font-semibold">路径</span>
              </div>
              <div class="flex gap-1">
                <Input bind:value={scanPath} placeholder="输入路径..." disabled={isRunning} class="flex-1 h-7 text-xs" />
                <Button variant="outline" size="icon" class="h-7 w-7 shrink-0" onclick={selectFolder} disabled={isRunning}>
                  <FolderOpen class="h-3 w-3" />
                </Button>
                <Button variant="outline" size="icon" class="h-7 w-7 shrink-0" onclick={pastePath} disabled={isRunning}>
                  <Clipboard class="h-3 w-3" />
                </Button>
              </div>
            </div>
            
            <!-- 扫描块 -->
            <div class="col-span-1 bg-card rounded-2xl border p-3 shadow-sm">
              <div class="flex items-center gap-1.5 mb-2">
                <RefreshCw class="w-4 h-4 text-blue-500" />
                <span class="text-xs font-semibold">扫描</span>
              </div>
              <div class="flex gap-1">
                <Button variant="outline" size="sm" class="flex-1 h-7 text-xs" onclick={() => handleScan(false)} disabled={isRunning}>
                  {#if isRunning && phase === 'scanning'}<LoaderCircle class="h-3 w-3 mr-1 animate-spin" />{/if}替换
                </Button>
                <Button variant="outline" size="sm" class="flex-1 h-7 text-xs" onclick={() => handleScan(true)} disabled={isRunning}>
                  合并
                </Button>
              </div>
            </div>
            
            <!-- 操作块 -->
            <div class="col-span-1 bg-card rounded-2xl border p-3 shadow-sm flex flex-col">
              <div class="flex items-center gap-1.5 mb-2">
                <Play class="w-4 h-4 text-green-500" />
                <span class="text-xs font-semibold">操作</span>
              </div>
              <div class="flex-1 flex flex-col gap-1.5">
                {#if phase === 'idle' || phase === 'error'}
                  <Button class="flex-1 h-8 text-xs" onclick={() => handleScan(false)} disabled={!scanPath.trim()}>
                    <Search class="h-3 w-3 mr-1" />扫描
                  </Button>
                {:else if phase === 'scanning'}
                  <Button class="flex-1 h-8 text-xs" disabled>
                    <LoaderCircle class="h-3 w-3 mr-1 animate-spin" />扫描中
                  </Button>
                {:else if phase === 'ready' || phase === 'completed'}
                  <Button class="flex-1 h-8 text-xs" onclick={handleRename} disabled={!canRename}>
                    <Play class="h-3 w-3 mr-1" />执行
                  </Button>
                  <Button variant="outline" class="h-6 text-xs" onclick={clear}>重置</Button>
                {:else if phase === 'renaming'}
                  <Button class="flex-1 h-8 text-xs" disabled>
                    <LoaderCircle class="h-3 w-3 mr-1 animate-spin" />执行中
                  </Button>
                {/if}
              </div>
            </div>
            
            <!-- 统计块 -->
            <div class="col-span-1 bg-card rounded-2xl border p-3 shadow-sm">
              <div class="flex items-center gap-1.5 mb-2">
                <FilePenLine class="w-4 h-4 text-yellow-500" />
                <span class="text-xs font-semibold">统计</span>
              </div>
              <div class="grid grid-cols-3 gap-1 text-xs">
                <div class="text-center p-1.5 bg-muted/50 rounded-lg">
                  <div class="font-bold">{stats.total}</div>
                  <div class="text-muted-foreground text-[10px]">总计</div>
                </div>
                <div class="text-center p-1.5 bg-yellow-500/10 rounded-lg">
                  <div class="font-bold text-yellow-600">{stats.pending}</div>
                  <div class="text-muted-foreground text-[10px]">待翻译</div>
                </div>
                <div class="text-center p-1.5 bg-green-500/10 rounded-lg">
                  <div class="font-bold text-green-600">{stats.ready}</div>
                  <div class="text-muted-foreground text-[10px]">就绪</div>
                </div>
              </div>
            </div>
            
            <!-- 导入导出/状态块 -->
            <div class="col-span-1 bg-card rounded-2xl border p-3 shadow-sm">
              <div class="flex items-center gap-1.5 mb-2">
                <Upload class="w-4 h-4 text-muted-foreground" />
                <span class="text-xs font-semibold">导入/导出</span>
              </div>
              <div class="flex gap-1 flex-wrap">
                <Button variant="ghost" size="sm" class="h-6 text-xs px-2" onclick={() => importJson(false)} disabled={isRunning}>
                  <Upload class="h-3 w-3 mr-1" />导入
                </Button>
                <Button variant="ghost" size="sm" class="h-6 text-xs px-2" onclick={() => copySegment(currentSegment)} disabled={!segments.length}>
                  {#if copied}<Check class="h-3 w-3 mr-1 text-green-500" />{:else}<Clipboard class="h-3 w-3 mr-1" />{/if}复制
                </Button>
                <Button variant="ghost" size="sm" class="h-6 w-6 p-0" onclick={() => downloadSegment(currentSegment)} disabled={!segments.length}>
                  <Download class="h-3 w-3" />
                </Button>
              </div>
              {#if segments.length > 1}
                <div class="flex items-center gap-1 text-xs mt-2">
                  <span class="text-muted-foreground">段:</span>
                  {#each segments as _, i}
                    <Button variant={currentSegment === i ? 'default' : 'ghost'} size="sm" class="h-5 w-5 p-0 text-xs"
                      onclick={() => { currentSegment = i; treeData = parseTree(segments[i]); }}>{i + 1}</Button>
                  {/each}
                </div>
              {/if}
            </div>
            
            <!-- 文件树块 (可展开) -->
            {#if showTree}
              <div class="col-span-2 bg-card rounded-2xl border shadow-sm overflow-hidden">
                <div class="flex items-center justify-between p-2 border-b bg-muted/30">
                  <span class="text-xs font-semibold flex items-center gap-1">
                    <Folder class="w-3 h-3 text-yellow-500" />文件树
                  </span>
                  <div class="flex items-center gap-2 text-[10px]">
                    <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-yellow-500"></span>{stats.pending}</span>
                    <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>{stats.ready}</span>
                    {#if stats.conflicts > 0}
                      <span class="flex items-center gap-0.5"><span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>{stats.conflicts}</span>
                    {/if}
                  </div>
                </div>
                <div class="p-2 max-h-40 overflow-y-auto">
                  {#if treeData.length > 0}
                    <TreeView.Root class="text-xs">
                      {#each treeData as node}{@render renderTreeNode(node)}{/each}
                    </TreeView.Root>
                  {:else}
                    <div class="text-xs text-muted-foreground text-center py-3">扫描后显示</div>
                  {/if}
                </div>
              </div>
            {/if}
            
            <!-- 高级选项块 -->
            {#if showOptions}
              <div class="col-span-2 bg-card rounded-2xl border p-3 shadow-sm">
                <div class="flex items-center gap-1.5 mb-2">
                  <Settings2 class="w-4 h-4 text-muted-foreground" />
                  <span class="text-xs font-semibold">高级选项</span>
                </div>
                <div class="flex flex-wrap gap-2 text-xs mb-2">
                  <label class="flex items-center gap-1"><Checkbox bind:checked={includeHidden} class="h-3 w-3" /><span>隐藏文件</span></label>
                  <label class="flex items-center gap-1"><Checkbox bind:checked={dryRun} class="h-3 w-3" /><span>模拟执行</span></label>
                  <label class="flex items-center gap-1"><Checkbox bind:checked={useCompact} class="h-3 w-3" /><span>紧凑格式</span></label>
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
            
            <!-- 冲突块 -->
            {#if conflicts.length > 0}
              <div class="col-span-2 bg-card rounded-2xl border border-red-500/30 p-3 shadow-sm">
                <div class="text-xs text-red-500 font-medium mb-1 flex items-center gap-1">
                  <TriangleAlert class="h-3 w-3" />冲突 ({conflicts.length})
                </div>
                <div class="max-h-16 overflow-y-auto">
                  {#each conflicts as c}<div class="text-xs text-red-400 truncate" title={c}>{c}</div>{/each}
                </div>
              </div>
            {/if}
            
            <!-- 日志块 -->
            {#if logs.length > 0}
              <div class="col-span-2 bg-card rounded-2xl border p-2 shadow-sm">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-semibold">日志</span>
                  <Button variant="ghost" size="icon" class="h-5 w-5" onclick={copyLogs}>
                    {#if copied}<Check class="h-2.5 w-2.5 text-green-500" />{:else}<Clipboard class="h-2.5 w-2.5" />{/if}
                  </Button>
                </div>
                <div class="bg-muted/30 rounded-lg p-1.5 font-mono text-[10px] max-h-16 overflow-y-auto space-y-0.5">
                  {#each logs.slice(-4) as log}
                    <div class="text-muted-foreground break-all">{log}</div>
                  {/each}
                </div>
              </div>
            {/if}
            
            <!-- 操作历史块 -->
            {#if operationHistory.length > 0}
              <div class="col-span-2 bg-card rounded-2xl border p-2 shadow-sm">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-semibold flex items-center gap-1">
                    <Undo2 class="h-3 w-3" />操作历史
                  </span>
                  <span class="text-xs text-muted-foreground">{operationHistory.filter(o => o.canUndo).length} 可撤销</span>
                </div>
                <div class="max-h-20 overflow-y-auto">
                  {#each operationHistory.slice(0, 3) as op}
                    <div class="flex items-center justify-between p-1.5 bg-muted/30 rounded-lg mb-1 text-xs">
                      <span class="text-muted-foreground">{op.time} - {op.count}项</span>
                      {#if op.canUndo}
                        <Button variant="ghost" size="sm" class="h-5 px-2 text-xs" onclick={() => handleUndo(op.id)}>撤销</Button>
                      {:else}
                        <span class="text-muted-foreground text-[10px]">已撤销</span>
                      {/if}
                    </div>
                  {/each}
                </div>
              </div>
            {/if}
            
          </div>
        </div>
      {/if}
    {/snippet}
  </NodeWrapper>
  
  {#if !isFullscreenRender}
    <Handle type="source" position={Position.Right} class="bg-primary!" />
  {/if}
</div>