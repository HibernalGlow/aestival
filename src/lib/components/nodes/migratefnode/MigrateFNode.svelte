<script lang="ts">
  /**
   * MigrateFNode - 文件迁移节点组件
   * 保持目录结构迁移文件和文件夹
   * 
   * 使用 Container Query 自动响应尺寸
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { MIGRATEF_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    LoaderCircle, FolderOpen, Clipboard, FolderInput,
    CircleCheck, CircleX, ArrowRight, FolderOutput,
    Copy, Check, RotateCcw, Undo2
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: { path?: string; target_path?: string; mode?: string; action?: string };
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
      label?: string;
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'migrating' | 'completed' | 'error';

  interface MigrateResultData { success: boolean; migrated: number; skipped: number; error: number; total: number; operation_id?: string; }
  interface MigrateFNodeState { phase: Phase; progress: number; progressText: string; migrateResult: MigrateResultData | null; lastOperationId: string; sourcePath: string; targetPath: string; mode: string; action: string; }

  // 使用 $derived 确保响应式
  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<MigrateFNodeState>(nodeId));
  const configPath = $derived(data?.config?.path ?? '');
  const configTargetPath = $derived(data?.config?.target_path ?? 'E:\\1Hub\\EH\\2EHV');
  const configMode = $derived(data?.config?.mode as 'preserve' | 'flat' | 'direct' ?? 'preserve');
  const configAction = $derived(data?.config?.action as 'copy' | 'move' ?? 'move');
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  let sourcePath = $state('');
  let targetPath = $state('E:\\1Hub\\EH\\2EHV');
  let mode = $state<'preserve' | 'flat' | 'direct'>('preserve');
  let action = $state<'copy' | 'move'>('move');
  
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let hasInputConnection = $state(false);
  let copied = $state(false);
  let progress = $state(0);
  let progressText = $state('');
  let migrateResult = $state<MigrateResultData | null>(null);
  let lastOperationId = $state('');
  let isUndoing = $state(false);

  let layoutRenderer = $state<any>(undefined);

  // 初始化标记
  let initialized = $state(false);

  // 初始化 effect - 只执行一次
  $effect(() => {
    if (initialized) return;
    
    if (savedState) {
      phase = savedState.phase ?? 'idle';
      progress = savedState.progress ?? 0;
      progressText = savedState.progressText ?? '';
      migrateResult = savedState.migrateResult ?? null;
      lastOperationId = savedState.lastOperationId ?? '';
      sourcePath = savedState.sourcePath || configPath || '';
      targetPath = savedState.targetPath || configTargetPath || '';
      mode = savedState.mode || configMode || 'preserve';
      action = savedState.action || configAction || 'copy';
    } else {
      sourcePath = configPath || '';
      targetPath = configTargetPath || '';
      mode = configMode || 'preserve';
      action = configAction || 'copy';
    }
    
    initialized = true;
  });
  
  // 持续同步外部数据
  $effect(() => {
    logs = [...dataLogs];
    hasInputConnection = dataHasInputConnection;
  });

  const modeOptions = [
    { value: 'preserve', label: '保持结构' },
    { value: 'flat', label: '扁平' },
    { value: 'direct', label: '直接' }
  ];

  function saveState() { 
    if (!initialized) return;
    setNodeState<MigrateFNodeState>(nodeId, { phase, progress, progressText, migrateResult, lastOperationId, sourcePath, targetPath, mode, action }); 
  }

  let canMigrate = $derived(phase === 'idle' && (sourcePath.trim() !== '' || hasInputConnection) && targetPath.trim() !== '');
  let isRunning = $derived(phase === 'migrating');
  let borderClass = $derived({ idle: 'border-border', migrating: 'border-primary shadow-sm', completed: 'border-primary/50', error: 'border-destructive/50' }[phase]);

  $effect(() => { if (phase || migrateResult) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  async function selectFolder(type: 'source' | 'target') {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFolderDialog(type === 'source' ? '选择源文件夹' : '选择目标文件夹');
      if (selected) { if (type === 'source') sourcePath = selected; else targetPath = selected; }
    } catch (e) { log(`选择文件夹失败: ${e}`); }
  }

  async function pasteFromClipboard(type: 'source' | 'target') {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) { if (type === 'source') sourcePath = text.trim(); else targetPath = text.trim(); }
    } catch (e) { log(`读取剪贴板失败: ${e}`); }
  }

  async function handleMigrate() {
    if (!canMigrate) return;
    phase = 'migrating'; progress = 0; progressText = '正在迁移...';
    migrateResult = null;
    
    const actionText = action === 'move' ? '移动' : '复制';
    const modeText = mode === 'preserve' ? '保持结构' : mode === 'flat' ? '扁平' : '直接';
    log(`📁 开始${actionText}到: ${targetPath}`);
    log(`⚙️ 模式: ${modeText}`);

    try {
      progress = 10;
      const response = await api.executeNode('migratef', { path: sourcePath, target_path: targetPath, mode, action }) as any;
      if (response.success) {
        phase = 'completed'; progress = 100; progressText = '迁移完成';
        const opId = response.data?.operation_id ?? '';
        migrateResult = { success: true, migrated: response.data?.migrated_count ?? 0, skipped: response.data?.skipped_count ?? 0, error: response.data?.error_count ?? 0, total: response.data?.total_count ?? 0, operation_id: opId };
        if (opId) lastOperationId = opId;
        log(`✅ ${response.message}`);
        if (opId) log(`🔄 撤销 ID: ${opId}`);
      } else { phase = 'error'; progress = 0; log(`❌ 迁移失败: ${response.message}`); }
    } catch (error) { phase = 'error'; progress = 0; log(`❌ 迁移失败: ${error}`); }
  }

  function handleReset() { phase = 'idle'; progress = 0; progressText = ''; migrateResult = null; logs = []; lastOperationId = ''; }

  async function handleUndo() {
    if (!lastOperationId || isUndoing) return;
    isUndoing = true;
    log(`🔄 开始撤销操作: ${lastOperationId}`);
    try {
      const response = await api.executeNode('migratef', { action: 'undo', batch_id: lastOperationId }) as any;
      if (response.success) { log(`✅ ${response.message}`); lastOperationId = ''; migrateResult = null; phase = 'idle'; }
      else { log(`❌ 撤销失败: ${response.message}`); }
    } catch (error) { log(`❌ 撤销失败: ${error}`); }
    finally { isUndoing = false; }
  }

  async function copyLogs() { try { await navigator.clipboard.writeText(logs.join('\n')); copied = true; setTimeout(() => { copied = false; }, 2000); } catch (e) { console.error('复制失败:', e); } }
</script>

<!-- 源路径输入区块 -->
{#snippet sourcePathBlock()}
  <div class="cq-mb">
    <div class="flex items-center gap-1 mb-1 cq-text">
      <FolderInput class="cq-icon" />
      <span class="font-medium">源目录</span>
    </div>
    {#if !hasInputConnection}
      <div class="flex cq-gap">
        <Input bind:value={sourcePath} placeholder="输入或选择源文件夹..." disabled={isRunning} class="flex-1 cq-input" />
        <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={() => selectFolder('source')} disabled={isRunning}>
          <FolderOpen class="cq-icon" />
        </Button>
        <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={() => pasteFromClipboard('source')} disabled={isRunning}>
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

<!-- 目标路径输入区块 -->
{#snippet targetPathBlock()}
  <div class="cq-mb">
    <div class="flex items-center gap-1 mb-1 cq-text">
      <FolderOutput class="cq-icon" />
      <span class="font-medium">目标目录</span>
    </div>
    <div class="flex cq-gap">
      <Input bind:value={targetPath} placeholder="输入或选择目标文件夹..." disabled={isRunning} class="flex-1 cq-input" />
      <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={() => selectFolder('target')} disabled={isRunning}>
        <FolderOpen class="cq-icon" />
      </Button>
      <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={() => pasteFromClipboard('target')} disabled={isRunning}>
        <Clipboard class="cq-icon" />
      </Button>
    </div>
  </div>
{/snippet}

<!-- 选项区块 -->
{#snippet optionsBlock()}
  <div class="cq-space">
    <div class="flex items-center gap-1 cq-text">
      <span class="font-medium">迁移模式</span>
    </div>
    <div class="flex flex-wrap cq-gap">
      {#each modeOptions as opt}
        <button
          class="cq-px cq-py cq-text cq-rounded border transition-colors {mode === opt.value ? 'bg-primary text-primary-foreground border-primary' : 'bg-background border-border hover:border-primary'}"
          onclick={() => mode = opt.value as any} disabled={isRunning}
        >{opt.label}</button>
      {/each}
    </div>
    <div class="flex items-center cq-gap pt-2">
      <span class="cq-text font-medium">操作:</span>
      <button
        class="cq-px cq-py cq-text cq-rounded border transition-colors {action === 'move' ? 'bg-blue-500 text-white border-blue-500' : 'bg-background border-border hover:border-blue-500'}"
        onclick={() => action = 'move'} disabled={isRunning}
      >移动</button>
      <button
        class="cq-px cq-py cq-text cq-rounded border transition-colors {action === 'copy' ? 'bg-green-500 text-white border-green-500' : 'bg-background border-border hover:border-green-500'}"
        onclick={() => action = 'copy'} disabled={isRunning}
      >复制</button>
    </div>
  </div>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <!-- 状态指示 -->
    <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded">
      {#if phase === 'completed'}
        <CircleCheck class="cq-icon text-green-500 shrink-0" />
        <span class="cq-text text-green-600 font-medium">完成</span>
        <span class="cq-text-sm text-muted-foreground ml-auto">{migrateResult?.migrated ?? 0} 成功</span>
      {:else if phase === 'error'}
        <CircleX class="cq-icon text-red-500 shrink-0" />
        <span class="cq-text text-red-600 font-medium">失败</span>
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <div class="flex-1"><Progress value={progress} class="h-1.5" /></div>
        <span class="cq-text-sm text-muted-foreground">{progress}%</span>
      {:else}
        <FolderInput class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text text-muted-foreground">等待执行</span>
      {/if}
    </div>
    <!-- 主按钮 -->
    <Button class="w-full cq-button flex-1" onclick={handleMigrate} disabled={!canMigrate || isRunning}>
      {#if isRunning}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<ArrowRight class="cq-icon mr-1" />{/if}
      <span>{action === 'move' ? '移动' : '复制'}</span>
    </Button>
    <!-- 辅助按钮 -->
    <div class="flex cq-gap">
      <Button variant="ghost" class="flex-1 cq-button-sm" onclick={handleReset} disabled={isRunning}>
        <RotateCcw class="cq-icon mr-1" />重置
      </Button>
      {#if lastOperationId}
        <Button variant="outline" class="flex-1 cq-button-sm" onclick={handleUndo} disabled={isUndoing || isRunning}>
          {#if isUndoing}<LoaderCircle class="cq-icon mr-1 animate-spin" />撤销中{:else}<Undo2 class="cq-icon mr-1" />撤销{/if}
        </Button>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlock()}
  {#if migrateResult}
    <div class="grid grid-cols-3 cq-gap">
      <div class="cq-stat-card bg-green-500/10">
        <div class="flex flex-col items-center">
          <span class="cq-stat-value text-green-600 tabular-nums">{migrateResult.migrated}</span>
          <span class="cq-stat-label text-muted-foreground">成功</span>
        </div>
      </div>
      <div class="cq-stat-card bg-yellow-500/10">
        <div class="flex flex-col items-center">
          <span class="cq-stat-value text-yellow-600 tabular-nums">{migrateResult.skipped}</span>
          <span class="cq-stat-label text-muted-foreground">跳过</span>
        </div>
      </div>
      <div class="cq-stat-card bg-red-500/10">
        <div class="flex flex-col items-center">
          <span class="cq-stat-value text-red-600 tabular-nums">{migrateResult.error}</span>
          <span class="cq-stat-label text-muted-foreground">失败</span>
        </div>
      </div>
    </div>
  {:else}
    <div class="cq-text text-muted-foreground text-center py-2">执行后显示统计</div>
  {/if}
{/snippet}

<!-- 进度/状态区块 -->
{#snippet progressBlock()}
  <div class="h-full flex items-center cq-gap">
    {#if migrateResult}
      {#if migrateResult.success}
        <CircleCheck class="cq-icon-lg text-green-500 shrink-0" />
        <div class="flex-1">
          <span class="font-semibold text-green-600 cq-text">迁移完成</span>
          <div class="flex cq-gap cq-text-sm mt-1">
            <span class="text-green-600">成功: {migrateResult.migrated}</span>
            <span class="text-yellow-600">跳过: {migrateResult.skipped}</span>
            <span class="text-red-600">失败: {migrateResult.error}</span>
          </div>
        </div>
      {:else}
        <CircleX class="cq-icon-lg text-red-500 shrink-0" />
        <span class="font-semibold text-red-600 cq-text">迁移失败</span>
      {/if}
    {:else if isRunning}
      <LoaderCircle class="cq-icon-lg text-primary animate-spin shrink-0" />
      <div class="flex-1">
        <div class="flex justify-between cq-text-sm mb-1"><span>{progressText}</span><span>{progress}%</span></div>
        <Progress value={progress} class="h-2" />
      </div>
    {:else}
      <FolderInput class="cq-icon-lg text-muted-foreground/50 shrink-0" />
      <div class="flex-1">
        <span class="text-muted-foreground cq-text">等待执行</span>
        <div class="cq-text-sm text-muted-foreground/70 mt-1">设置源和目标后点击执行</div>
      </div>
    {/if}
  </div>
{/snippet}

<!-- 日志区块 -->
{#snippet logBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold">日志</span>
      <Button variant="ghost" size="icon" class="h-5 w-5" onclick={copyLogs}>
        {#if copied}<Check class="w-3 h-3 text-green-500" />{:else}<Copy class="w-3 h-3" />{/if}
      </Button>
    </div>
    <div class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding font-mono cq-text-sm space-y-0.5">
      {#if logs.length > 0}
        {#each logs.slice(-10) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 区块渲染器 -->
{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'path'}{@render sourcePathBlock()}{@render targetPathBlock()}
  {:else if blockId === 'source'}{@render sourcePathBlock()}
  {:else if blockId === 'target'}{@render targetPathBlock()}
  {:else if blockId === 'options'}{@render optionsBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'stats'}{@render statsBlock()}
  {:else if blockId === 'progress'}{@render progressBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<!-- 主渲染 -->
<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 400px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={200} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="migratef" 
    icon={FolderInput} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="migratef" 
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
        nodeType="migratef"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={MIGRATEF_DEFAULT_GRID_LAYOUT}
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
