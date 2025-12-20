<script lang="ts">
  /**
   * MigrateFNode - 文件迁移节点组件
   * 扫描并迁移文件到目标目录
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';
  import { Badge } from '$lib/components/ui/badge';

  import { InteractiveHover } from '$lib/components/ui/interactive-hover';
  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { getSizeClasses, type SizeMode } from '$lib/utils/sizeUtils';
  import { formatFileSize, getStatusColorClass, getStatusName } from './utils';
  import { 
    Play, LoaderCircle, FolderOpen, Clipboard, FolderInput,
    CircleCheck, CircleX, Search, FileText, ArrowRight,
    Copy, Check, RotateCcw, FolderOutput
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: { path?: string; target_path?: string; pattern?: string; recursive?: boolean; dry_run?: boolean };
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
      label?: string;
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'scanning' | 'scanned' | 'migrating' | 'completed' | 'error';

  interface ScanResult {
    configPath: string;
    totalFiles: number;
    totalSize: number;
    fileList?: any[];
  }

  interface MigrateResultData {
    success: boolean;
    moved: number;
    skipped: number;
    failed: number;
    total: number;
    dryRun: boolean;
  }

  interface MigrateFNodeState {
    phase: Phase;
    progress: number;
    progressText: string;
    scanResult: ScanResult | null;
    migrateResult: MigrateResultData | null;
  }

  // 从 nodeStateStore 恢复状态
  const savedState = getNodeState<MigrateFNodeState>(id);

  // 状态初始化
  let sourcePath = $state(data?.config?.path ?? '');
  let targetPath = $state(data?.config?.target_path ?? '');
  let pattern = $state(data?.config?.pattern ?? '*');
  let recursive = $state(data?.config?.recursive ?? true);
  let dryRun = $state(data?.config?.dry_run ?? true);
  let overwrite = $state(false);
  let preserveStructure = $state(true);
  
  let phase = $state<Phase>(savedState?.phase ?? 'idle');
  let logs = $state<string[]>(data?.logs ? [...data.logs] : []);
  let hasInputConnection = $state(data?.hasInputConnection ?? false);
  let copied = $state(false);

  let progress = $state(savedState?.progress ?? 0);
  let progressText = $state(savedState?.progressText ?? '');

  let scanResult = $state<ScanResult | null>(savedState?.scanResult ?? null);
  let migrateResult = $state<MigrateResultData | null>(savedState?.migrateResult ?? null);

  // NodeLayoutRenderer 引用
  let layoutRenderer = $state<any>(undefined);

  function saveState() {
    setNodeState<MigrateFNodeState>(id, {
      phase, progress, progressText, scanResult, migrateResult
    });
  }

  // 响应式派生值
  let canScan = $derived(phase === 'idle' && (sourcePath.trim() !== '' || hasInputConnection));
  let canMigrate = $derived(phase === 'scanned' && scanResult !== null && targetPath.trim() !== '');
  let isRunning = $derived(phase === 'scanning' || phase === 'migrating');
  let borderClass = $derived({
    idle: 'border-border', scanning: 'border-primary shadow-sm', scanned: 'border-primary/50',
    migrating: 'border-primary shadow-sm', completed: 'border-primary/50', error: 'border-destructive/50'
  }[phase]);

  // 状态变化时自动保存
  $effect(() => {
    if (phase || scanResult || migrateResult) saveState();
  });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  async function selectFolder(type: 'source' | 'target') {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFolderDialog(type === 'source' ? '选择源文件夹' : '选择目标文件夹');
      if (selected) {
        if (type === 'source') sourcePath = selected;
        else targetPath = selected;
      }
    } catch (e) { log(`选择文件夹失败: ${e}`); }
  }

  async function pasteFromClipboard(type: 'source' | 'target') {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) {
        if (type === 'source') sourcePath = text.trim();
        else targetPath = text.trim();
      }
    } catch (e) { log(`读取剪贴板失败: ${e}`); }
  }

  async function handleScan() {
    if (!canScan) return;
    phase = 'scanning'; progress = 0; progressText = '正在扫描文件...';
    scanResult = null; migrateResult = null;
    log(`🔍 开始扫描目录: ${sourcePath}`);
    log(`📋 匹配模式: ${pattern}, 递归: ${recursive ? '是' : '否'}`);

    try {
      progress = 30; progressText = '正在分析文件...';
      const response = await api.executeNode('migratefnode', {
        action: 'scan', path: sourcePath, pattern, recursive
      }) as any;

      if (response.success && response.data) {
        phase = 'scanned'; progress = 100; progressText = '扫描完成';
        scanResult = {
          configPath: response.data.config_path ?? '',
          totalFiles: response.data.total_files ?? 0,
          totalSize: response.data.total_size ?? 0,
          fileList: response.data.file_list
        };
        log(`✅ 扫描完成，共 ${scanResult.totalFiles} 个文件`);
        log(`📊 总大小: ${formatFileSize(scanResult.totalSize)}`);
      } else { phase = 'error'; progress = 0; log(`❌ 扫描失败: ${response.message}`); }
    } catch (error) { phase = 'error'; progress = 0; log(`❌ 扫描失败: ${error}`); }
  }

  async function handleMigrate() {
    if (!canMigrate || !scanResult) return;
    phase = 'migrating'; progress = 0; progressText = '正在迁移文件...';
    log(`📁 开始迁移到: ${targetPath}`);
    log(`⚙️ 模式: ${dryRun ? '模拟执行' : '实际执行'}`);

    try {
      progress = 20;
      const response = await api.executeNode('migratefnode', {
        action: 'migrate',
        config_path: scanResult.configPath,
        target_path: targetPath,
        dry_run: dryRun,
        overwrite,
        preserve_structure: preserveStructure
      }) as any;

      if (response.success) {
        phase = 'completed'; progress = 100; progressText = '迁移完成';
        migrateResult = {
          success: true,
          moved: response.data?.moved_count ?? 0,
          skipped: response.data?.skipped_count ?? 0,
          failed: response.data?.failed_count ?? 0,
          total: response.data?.total_files ?? 0,
          dryRun: response.data?.dry_run ?? dryRun
        };
        log(`✅ ${response.message}`);
      } else { phase = 'error'; progress = 0; log(`❌ 迁移失败: ${response.message}`); }
    } catch (error) { phase = 'error'; progress = 0; log(`❌ 迁移失败: ${error}`); }
  }

  function handleReset() {
    phase = 'idle'; progress = 0; progressText = '';
    scanResult = null; migrateResult = null; logs = [];
  }

  async function copyLogs() {
    try { await navigator.clipboard.writeText(logs.join('\n')); copied = true; setTimeout(() => { copied = false; }, 2000); }
    catch (e) { console.error('复制失败:', e); }
  }
</script>

<!-- ========== 区块内容 Snippets ========== -->

<!-- 源路径输入区块 -->
{#snippet sourcePathBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="{c.mb}">
    <div class="flex items-center gap-1 mb-1 {c.text}">
      <FolderInput class={c.icon} />
      <span class="font-medium">源目录</span>
    </div>
    {#if !hasInputConnection}
      <div class="flex {c.gap}">
        <Input bind:value={sourcePath} placeholder="输入或选择源文件夹..." disabled={isRunning} class="flex-1 {c.input}" />
        <Button variant="outline" size="icon" class="{c.buttonIcon} shrink-0" onclick={() => selectFolder('source')} disabled={isRunning}>
          <FolderOpen class={c.icon} />
        </Button>
        <Button variant="outline" size="icon" class="{c.buttonIcon} shrink-0" onclick={() => pasteFromClipboard('source')} disabled={isRunning}>
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

<!-- 目标路径输入区块 -->
{#snippet targetPathBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="{c.mb}">
    <div class="flex items-center gap-1 mb-1 {c.text}">
      <FolderOutput class={c.icon} />
      <span class="font-medium">目标目录</span>
    </div>
    <div class="flex {c.gap}">
      <Input bind:value={targetPath} placeholder="输入或选择目标文件夹..." disabled={isRunning} class="flex-1 {c.input}" />
      <Button variant="outline" size="icon" class="{c.buttonIcon} shrink-0" onclick={() => selectFolder('target')} disabled={isRunning}>
        <FolderOpen class={c.icon} />
      </Button>
      <Button variant="outline" size="icon" class="{c.buttonIcon} shrink-0" onclick={() => pasteFromClipboard('target')} disabled={isRunning}>
        <Clipboard class={c.icon} />
      </Button>
    </div>
  </div>
{/snippet}

<!-- 选项区块 -->
{#snippet optionsBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="space-y-2">
    <div class="flex {c.gap}">
      <Input bind:value={pattern} placeholder="匹配模式 (如 *.jpg)" disabled={isRunning} class="flex-1 {c.input}" />
    </div>
    <div class="flex flex-wrap {c.gap}">
      <label class="flex items-center {c.gap} cursor-pointer {c.text}">
        <Checkbox bind:checked={recursive} disabled={isRunning} />
        <span>递归</span>
      </label>
      <label class="flex items-center {c.gap} cursor-pointer {c.text}">
        <Checkbox bind:checked={preserveStructure} disabled={isRunning} />
        <span>保持结构</span>
      </label>
      <label class="flex items-center {c.gap} cursor-pointer {c.text}">
        <Checkbox bind:checked={overwrite} disabled={isRunning} />
        <span>覆盖</span>
      </label>
      <label class="flex items-center {c.gap} cursor-pointer {c.text}">
        <Checkbox bind:checked={dryRun} disabled={isRunning} />
        <span>模拟</span>
      </label>
    </div>
  </div>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="flex flex-col {c.gap} {size === 'normal' ? 'flex-1 justify-center' : ''}">
    {#if size === 'normal'}
      {#if phase === 'idle' || phase === 'error'}
        <InteractiveHover text="扫描文件" class="w-full h-12 text-sm" onclick={handleScan} disabled={!canScan}>
          {#snippet icon()}<Search class="h-4 w-4" />{/snippet}
        </InteractiveHover>
      {:else if phase === 'scanning'}
        <InteractiveHover text="扫描中" class="w-full h-12 text-sm" disabled>
          {#snippet icon()}<LoaderCircle class="h-4 w-4 animate-spin" />{/snippet}
        </InteractiveHover>
      {:else if phase === 'scanned'}
        <InteractiveHover text="开始迁移" class="w-full h-12 text-sm" onclick={handleMigrate} disabled={!canMigrate}>
          {#snippet icon()}<ArrowRight class="h-4 w-4" />{/snippet}
        </InteractiveHover>
      {:else if phase === 'migrating'}
        <InteractiveHover text="迁移中" class="w-full h-12 text-sm" disabled>
          {#snippet icon()}<LoaderCircle class="h-4 w-4 animate-spin" />{/snippet}
        </InteractiveHover>
      {:else if phase === 'completed'}
        <InteractiveHover text="重新开始" class="w-full h-12 text-sm" onclick={handleReset}>
          {#snippet icon()}<Play class="h-4 w-4" />{/snippet}
        </InteractiveHover>
      {/if}
      <Button variant="ghost" class="h-9" onclick={handleReset} disabled={isRunning}>
        <RotateCcw class="h-4 w-4 mr-2" />重置
      </Button>
    {:else}
      <div class="flex {c.gapSm}">
        {#if phase === 'idle' || phase === 'error'}
          <Button class="flex-1 {c.button}" onclick={handleScan} disabled={!canScan}>
            <Search class="{c.icon} mr-1" />扫描
          </Button>
        {:else if phase === 'scanning'}
          <Button class="flex-1 {c.button}" disabled>
            <LoaderCircle class="{c.icon} mr-1 animate-spin" />扫描中
          </Button>
        {:else if phase === 'scanned'}
          <Button class="flex-1 {c.button}" onclick={handleMigrate} disabled={!canMigrate}>
            <ArrowRight class="{c.icon} mr-1" />迁移
          </Button>
        {:else if phase === 'migrating'}
          <Button class="flex-1 {c.button}" disabled>
            <LoaderCircle class="{c.icon} mr-1 animate-spin" />迁移中
          </Button>
        {:else if phase === 'completed'}
          <Button class="flex-1 {c.button}" variant="outline" onclick={handleReset}>
            <Play class="{c.icon} mr-1" />重新
          </Button>
        {/if}
        <Button variant="ghost" size="icon" class="{c.buttonIcon}" onclick={handleReset} disabled={isRunning} title="重置">
          <RotateCcw class={c.icon} />
        </Button>
      </div>
    {/if}
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlock(size: SizeMode)}
  {#if size === 'normal'}
    <div class="space-y-2 flex-1">
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-blue-500/15 to-blue-500/5 rounded-xl border border-blue-500/20">
        <span class="text-sm text-muted-foreground">文件数</span>
        <span class="text-2xl font-bold text-blue-600 tabular-nums">{scanResult?.totalFiles ?? '-'}</span>
      </div>
      <div class="flex items-center justify-between p-3 bg-gradient-to-r from-purple-500/15 to-purple-500/5 rounded-xl border border-purple-500/20">
        <span class="text-sm text-muted-foreground">总大小</span>
        <span class="text-lg font-bold text-purple-600">{scanResult ? formatFileSize(scanResult.totalSize) : '-'}</span>
      </div>
      {#if migrateResult}
        <div class="flex items-center justify-between p-3 bg-gradient-to-r from-green-500/15 to-green-500/5 rounded-xl border border-green-500/20">
          <span class="text-sm text-muted-foreground">已迁移</span>
          <span class="text-2xl font-bold text-green-600 tabular-nums">{migrateResult.moved}</span>
        </div>
      {/if}
    </div>
  {:else}
    <div class="grid grid-cols-2 gap-1.5">
      <div class="text-center p-1.5 bg-blue-500/10 rounded-lg">
        <div class="text-sm font-bold text-blue-600 tabular-nums">{scanResult?.totalFiles ?? '-'}</div>
        <div class="text-[10px] text-muted-foreground">文件</div>
      </div>
      <div class="text-center p-1.5 bg-purple-500/10 rounded-lg">
        <div class="text-xs font-bold text-purple-600">{scanResult ? formatFileSize(scanResult.totalSize) : '-'}</div>
        <div class="text-[10px] text-muted-foreground">大小</div>
      </div>
    </div>
  {/if}
{/snippet}

<!-- 进度/状态区块 -->
{#snippet progressBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  {#if size === 'normal'}
    <div class="h-full flex items-center gap-3">
      {#if migrateResult}
        {#if migrateResult.success}
          <CircleCheck class="w-8 h-8 text-green-500 shrink-0" />
          <div class="flex-1">
            <span class="font-semibold text-green-600">{migrateResult.dryRun ? '模拟' : ''}迁移完成</span>
            <div class="flex gap-4 text-sm mt-1">
              <span class="text-green-600">成功: {migrateResult.moved}</span>
              <span class="text-yellow-600">跳过: {migrateResult.skipped}</span>
              <span class="text-red-600">失败: {migrateResult.failed}</span>
            </div>
          </div>
        {:else}
          <CircleX class="w-8 h-8 text-red-500 shrink-0" />
          <span class="font-semibold text-red-600">迁移失败</span>
        {/if}
      {:else if isRunning}
        <LoaderCircle class="w-8 h-8 text-primary animate-spin shrink-0" />
        <div class="flex-1">
          <div class="flex justify-between text-sm mb-1"><span>{progressText}</span><span>{progress}%</span></div>
          <Progress value={progress} class="h-2" />
        </div>
      {:else}
        <FolderInput class="w-8 h-8 text-muted-foreground/50 shrink-0" />
        <div class="flex-1">
          <span class="text-muted-foreground">等待扫描</span>
          <div class="text-xs text-muted-foreground/70 mt-1">扫描完成后可开始迁移</div>
        </div>
      {/if}
    </div>
  {:else}
    {#if migrateResult}
      <div class="flex items-center gap-2 {c.text}">
        {#if migrateResult.success}
          <CircleCheck class="{c.icon} text-green-500" />
          <span class="text-green-600">成功 {migrateResult.moved}</span>
        {:else}
          <CircleX class="{c.icon} text-red-500" />
          <span class="text-red-600">失败</span>
        {/if}
      </div>
    {:else if isRunning}
      <div class={c.spaceSm}>
        <Progress value={progress} class="h-1.5" />
        <div class="{c.text} text-muted-foreground">{progress}%</div>
      </div>
    {:else}
      <div class="{c.text} text-muted-foreground">等待扫描</div>
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
        {#if logs.length > 0}{#each logs.slice(-15) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}{:else}<div class="text-muted-foreground text-center py-4">暂无日志</div>{/if}
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
      {#each logs.slice(-4) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
    </div>
  {/if}
{/snippet}

<!-- 通用区块渲染器 -->
{#snippet renderBlockContent(blockId: string, size: SizeMode)}
  {#if blockId === 'path'}{@render sourcePathBlock(size)}{@render targetPathBlock(size)}{@render optionsBlock(size)}
  {:else if blockId === 'source'}{@render sourcePathBlock(size)}
  {:else if blockId === 'target'}{@render targetPathBlock(size)}
  {:else if blockId === 'options'}{@render optionsBlock(size)}
  {:else if blockId === 'operation'}{@render operationBlock(size)}
  {:else if blockId === 'stats'}{@render statsBlock(size)}
  {:else if blockId === 'progress'}{@render progressBlock(size)}
  {:else if blockId === 'log'}{@render logBlock(size)}
  {/if}
{/snippet}


<!-- ========== 主渲染 ========== -->
<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 400px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={200} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={id} 
    title="migratefnode" 
    icon={FolderInput} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="migratefnode" 
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
        nodeType="migratefnode"
        isFullscreen={isFullscreenRender}
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
