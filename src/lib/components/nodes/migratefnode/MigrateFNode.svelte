<script lang="ts">
  /**
   * MigrateFNode - 文件迁移节点组件
   * 保持目录结构迁移文件和文件夹
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';

  import { InteractiveHover } from '$lib/components/ui/interactive-hover';
  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { MIGRATEF_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { getSizeClasses, type SizeMode } from '$lib/utils/sizeUtils';
  import { 
    Play, LoaderCircle, FolderOpen, Clipboard, FolderInput,
    CircleCheck, CircleX, ArrowRight, FolderOutput,
    Copy, Check, RotateCcw
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

  interface MigrateResultData {
    success: boolean;
    migrated: number;
    skipped: number;
    error: number;
    total: number;
  }

  interface MigrateFNodeState {
    phase: Phase;
    progress: number;
    progressText: string;
    migrateResult: MigrateResultData | null;
  }

  // 从 nodeStateStore 恢复状态
  const savedState = getNodeState<MigrateFNodeState>(id);

  // 状态初始化
  let sourcePath = $state(data?.config?.path ?? '');
  let targetPath = $state(data?.config?.target_path ?? 'E:\\1Hub\\EH\\2EHV');
  let mode = $state<'preserve' | 'flat' | 'direct'>(data?.config?.mode as any ?? 'preserve');
  let action = $state<'copy' | 'move'>(data?.config?.action as any ?? 'move');
  
  let phase = $state<Phase>(savedState?.phase ?? 'idle');
  let logs = $state<string[]>(data?.logs ? [...data.logs] : []);
  let hasInputConnection = $state(data?.hasInputConnection ?? false);
  let copied = $state(false);

  let progress = $state(savedState?.progress ?? 0);
  let progressText = $state(savedState?.progressText ?? '');

  let migrateResult = $state<MigrateResultData | null>(savedState?.migrateResult ?? null);

  // NodeLayoutRenderer 引用
  let layoutRenderer = $state<any>(undefined);

  const modeOptions = [
    { value: 'preserve', label: '保持结构' },
    { value: 'flat', label: '扁平' },
    { value: 'direct', label: '直接' }
  ];

  function saveState() {
    setNodeState<MigrateFNodeState>(id, {
      phase, progress, progressText, migrateResult
    });
  }

  // 响应式派生值
  let canMigrate = $derived(phase === 'idle' && (sourcePath.trim() !== '' || hasInputConnection) && targetPath.trim() !== '');
  let isRunning = $derived(phase === 'migrating');
  let borderClass = $derived({
    idle: 'border-border', migrating: 'border-primary shadow-sm',
    completed: 'border-primary/50', error: 'border-destructive/50'
  }[phase]);

  // 状态变化时自动保存
  $effect(() => {
    if (phase || migrateResult) saveState();
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
      const response = await api.executeNode('migratef', {
        path: sourcePath,
        target_path: targetPath,
        mode,
        action
      }) as any;

      if (response.success) {
        phase = 'completed'; progress = 100; progressText = '迁移完成';
        migrateResult = {
          success: true,
          migrated: response.data?.migrated_count ?? 0,
          skipped: response.data?.skipped_count ?? 0,
          error: response.data?.error_count ?? 0,
          total: response.data?.total_count ?? 0
        };
        log(`✅ ${response.message}`);
      } else { phase = 'error'; progress = 0; log(`❌ 迁移失败: ${response.message}`); }
    } catch (error) { phase = 'error'; progress = 0; log(`❌ 迁移失败: ${error}`); }
  }

  function handleReset() {
    phase = 'idle'; progress = 0; progressText = '';
    migrateResult = null; logs = [];
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
    <div class="flex items-center gap-1 {c.text}">
      <span class="font-medium">迁移模式</span>
    </div>
    <div class="flex flex-wrap {c.gap}">
      {#each modeOptions as opt}
        <button
          class="{c.px} {c.py} {c.text} {c.rounded} border transition-colors {mode === opt.value ? 'bg-primary text-primary-foreground border-primary' : 'bg-background border-border hover:border-primary'}"
          onclick={() => mode = opt.value as any} disabled={isRunning}
        >{opt.label}</button>
      {/each}
    </div>
    <div class="flex items-center {c.gap} pt-2">
      <span class="{c.text} font-medium">操作:</span>
      <button
        class="{c.px} {c.py} {c.text} {c.rounded} border transition-colors {action === 'move' ? 'bg-blue-500 text-white border-blue-500' : 'bg-background border-border hover:border-blue-500'}"
        onclick={() => action = 'move'} disabled={isRunning}
      >移动</button>
      <button
        class="{c.px} {c.py} {c.text} {c.rounded} border transition-colors {action === 'copy' ? 'bg-green-500 text-white border-green-500' : 'bg-background border-border hover:border-green-500'}"
        onclick={() => action = 'copy'} disabled={isRunning}
      >复制</button>
    </div>
  </div>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock(size: SizeMode)}
  {@const c = getSizeClasses(size)}
  <div class="flex flex-col {c.gap} {size === 'normal' ? 'flex-1 justify-center' : ''}">
    {#if size === 'normal'}
      {#if phase === 'idle' || phase === 'error'}
        <InteractiveHover text={action === 'move' ? '开始移动' : '开始复制'} class="w-full h-12 text-sm" onclick={handleMigrate} disabled={!canMigrate}>
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
          <Button class="flex-1 {c.button}" onclick={handleMigrate} disabled={!canMigrate}>
            <ArrowRight class="{c.icon} mr-1" />{action === 'move' ? '移动' : '复制'}
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
      {#if migrateResult}
        <div class="flex items-center justify-between p-3 bg-gradient-to-r from-green-500/15 to-green-500/5 rounded-xl border border-green-500/20">
          <span class="text-sm text-muted-foreground">成功</span>
          <span class="text-2xl font-bold text-green-600 tabular-nums">{migrateResult.migrated}</span>
        </div>
        <div class="flex items-center justify-between p-3 bg-gradient-to-r from-yellow-500/15 to-yellow-500/5 rounded-xl border border-yellow-500/20">
          <span class="text-sm text-muted-foreground">跳过</span>
          <span class="text-2xl font-bold text-yellow-600 tabular-nums">{migrateResult.skipped}</span>
        </div>
        <div class="flex items-center justify-between p-3 bg-gradient-to-r from-red-500/15 to-red-500/5 rounded-xl border border-red-500/20">
          <span class="text-sm text-muted-foreground">失败</span>
          <span class="text-2xl font-bold text-red-600 tabular-nums">{migrateResult.error}</span>
        </div>
      {:else}
        <div class="text-center text-muted-foreground py-4">执行后显示统计</div>
      {/if}
    </div>
  {:else}
    {#if migrateResult}
      <div class="grid grid-cols-3 gap-1.5">
        <div class="text-center p-1.5 bg-green-500/10 rounded-lg">
          <div class="text-sm font-bold text-green-600 tabular-nums">{migrateResult.migrated}</div>
          <div class="text-[10px] text-muted-foreground">成功</div>
        </div>
        <div class="text-center p-1.5 bg-yellow-500/10 rounded-lg">
          <div class="text-sm font-bold text-yellow-600 tabular-nums">{migrateResult.skipped}</div>
          <div class="text-[10px] text-muted-foreground">跳过</div>
        </div>
        <div class="text-center p-1.5 bg-red-500/10 rounded-lg">
          <div class="text-sm font-bold text-red-600 tabular-nums">{migrateResult.error}</div>
          <div class="text-[10px] text-muted-foreground">失败</div>
        </div>
      </div>
    {:else}
      <div class="text-xs text-muted-foreground text-center">-</div>
    {/if}
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
            <span class="font-semibold text-green-600">迁移完成</span>
            <div class="flex gap-4 text-sm mt-1">
              <span class="text-green-600">成功: {migrateResult.migrated}</span>
              <span class="text-yellow-600">跳过: {migrateResult.skipped}</span>
              <span class="text-red-600">失败: {migrateResult.error}</span>
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
          <span class="text-muted-foreground">等待执行</span>
          <div class="text-xs text-muted-foreground/70 mt-1">设置源和目标后点击执行</div>
        </div>
      {/if}
    </div>
  {:else}
    {#if migrateResult}
      <div class="flex items-center gap-2 {c.text}">
        {#if migrateResult.success}
          <CircleCheck class="{c.icon} text-green-500" />
          <span class="text-green-600">成功 {migrateResult.migrated}</span>
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
  {#if blockId === 'path'}{@render sourcePathBlock(size)}{@render targetPathBlock(size)}
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
        nodeId={id}
        nodeType="migratef"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={MIGRATEF_DEFAULT_GRID_LAYOUT}
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
