<script lang="ts">
  /**
   * BandiaNode - 批量解压节点组件
   * 使用 Bandizip 批量解压压缩包
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Progress } from '$lib/components/ui/progress';
  import { Textarea } from '$lib/components/ui/textarea';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { BANDIA_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, Clipboard, FileArchive,
    CircleCheck, CircleX, Trash2, Copy, Check, RotateCcw, FolderOpen
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: { paths?: string[]; delete_after?: boolean; use_trash?: boolean };
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
      label?: string;
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'extracting' | 'completed' | 'error';

  interface BandiaState {
    phase: Phase;
    progress: number;
    progressText: string;
    archivePaths: string[];
    deleteAfter: boolean;
    useTrash: boolean;
    extractResult: ExtractResult | null;
  }

  interface ExtractResult {
    success: boolean;
    extracted: number;
    failed: number;
    total: number;
  }

  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<BandiaState>(nodeId));
  const configPaths = $derived(data?.config?.paths ?? []);
  const configDeleteAfter = $derived(data?.config?.delete_after ?? true);
  const configUseTrash = $derived(data?.config?.use_trash ?? true);
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  let pathsText = $state('');
  let deleteAfter = $state(true);
  let useTrash = $state(true);
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let hasInputConnection = $state(false);
  let copied = $state(false);
  let progress = $state(0);
  let progressText = $state('');
  let archivePaths = $state<string[]>([]);
  let extractResult = $state<ExtractResult | null>(null);
  let layoutRenderer = $state<any>(undefined);

  $effect(() => {
    pathsText = configPaths.join('\n');
    deleteAfter = configDeleteAfter;
    useTrash = configUseTrash;
    logs = [...dataLogs];
    hasInputConnection = dataHasInputConnection;
    if (savedState) {
      phase = savedState.phase ?? 'idle';
      progress = savedState.progress ?? 0;
      progressText = savedState.progressText ?? '';
      archivePaths = savedState.archivePaths ?? [];
      deleteAfter = savedState.deleteAfter ?? true;
      useTrash = savedState.useTrash ?? true;
      extractResult = savedState.extractResult ?? null;
    }
  });

  function saveState() {
    setNodeState<BandiaState>(nodeId, {
      phase, progress, progressText, archivePaths, deleteAfter, useTrash, extractResult
    });
  }

  let canExtract = $derived(phase === 'idle' && (pathsText.trim() !== '' || hasInputConnection));
  let isRunning = $derived(phase === 'extracting');
  let borderClass = $derived({
    idle: 'border-border', extracting: 'border-primary shadow-sm',
    completed: 'border-primary/50', error: 'border-destructive/50'
  }[phase]);

  $effect(() => { if (phase || archivePaths || extractResult) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  function parsePaths(text: string): string[] {
    return text.split('\n')
      .map(line => line.trim().replace(/^["']|["']$/g, ''))
      .filter(line => line && /\.(zip|7z|rar|tar|gz|bz2|xz)$/i.test(line));
  }

  async function pasteFromClipboard() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) {
        pathsText = text.trim();
        log(`📋 从剪贴板读取 ${parsePaths(pathsText).length} 个压缩包路径`);
      }
    } catch (e) { log(`❌ 读取剪贴板失败: ${e}`); }
  }

  async function selectFiles() {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFileDialog('选择压缩包', [
        { name: '压缩文件', extensions: ['zip', '7z', 'rar', 'tar', 'gz', 'bz2', 'xz'] }
      ]);
      if (selected) {
        pathsText = pathsText ? pathsText + '\n' + selected : selected;
        log(`📁 选择了文件: ${selected.split(/[/\\]/).pop()}`);
      }
    } catch (e) { log(`❌ 选择文件失败: ${e}`); }
  }

  async function handleExtract() {
    if (!canExtract) return;
    const paths = parsePaths(pathsText);
    if (paths.length === 0) { log('❌ 没有有效的压缩包路径'); return; }
    archivePaths = paths;
    phase = 'extracting'; progress = 0; progressText = '正在解压...'; extractResult = null;
    log(`📦 开始解压 ${paths.length} 个压缩包...`);
    try {
      progress = 20;
      const response = await api.executeNode('bandia', {
        action: 'extract', paths, delete_after: deleteAfter, use_trash: useTrash
      }) as any;
      if (response.success) {
        phase = 'completed'; progress = 100; progressText = '解压完成';
        extractResult = {
          success: true,
          extracted: response.data?.extracted_count ?? 0,
          failed: response.data?.failed_count ?? 0,
          total: response.data?.total_count ?? paths.length
        };
        log(`✅ ${response.message}`);
        log(`📊 成功: ${extractResult.extracted}, 失败: ${extractResult.failed}`);
      } else { phase = 'error'; progress = 0; log(`❌ 解压失败: ${response.message}`); }
    } catch (error) { phase = 'error'; progress = 0; log(`❌ 解压失败: ${error}`); }
  }

  function handleReset() {
    phase = 'idle'; progress = 0; progressText = '';
    extractResult = null; archivePaths = []; logs = [];
  }

  async function copyLogs() {
    try { await navigator.clipboard.writeText(logs.join('\n')); copied = true; setTimeout(() => { copied = false; }, 2000); }
    catch (e) { console.error('复制失败:', e); }
  }
</script>


{#snippet sourceBlock()}
  {#if !hasInputConnection}
    <div class="flex flex-col cq-gap h-full">
      <div class="flex cq-gap">
        <Button variant="outline" size="sm" class="cq-button-sm flex-1" onclick={pasteFromClipboard} disabled={isRunning}>
          <Clipboard class="cq-icon mr-1" />剪贴板
        </Button>
        <Button variant="outline" size="sm" class="cq-button-sm flex-1" onclick={selectFiles} disabled={isRunning}>
          <FolderOpen class="cq-icon mr-1" />选择文件
        </Button>
      </div>
      <Textarea bind:value={pathsText} placeholder="粘贴压缩包路径（每行一个）&#10;支持: .zip .7z .rar .tar .gz .bz2 .xz" disabled={isRunning} class="flex-1 cq-text font-mono resize-none min-h-[60px]" />
      <div class="cq-text-sm text-muted-foreground">已识别 {parsePaths(pathsText).length} 个压缩包</div>
    </div>
  {:else}
    <div class="text-muted-foreground cq-padding bg-muted cq-rounded flex items-center cq-gap cq-text">
      <span>←</span><span>输入来自上游节点</span>
    </div>
  {/if}
{/snippet}

{#snippet optionsBlock()}
  <div class="flex flex-col cq-gap">
    <label class="flex items-center cq-gap cursor-pointer">
      <Checkbox bind:checked={deleteAfter} disabled={isRunning} />
      <span class="cq-text">解压后删除源文件</span>
    </label>
    {#if deleteAfter}
      <label class="flex items-center cq-gap cursor-pointer ml-4">
        <Checkbox bind:checked={useTrash} disabled={isRunning} />
        <span class="cq-text flex items-center gap-1"><Trash2 class="cq-icon text-orange-500" />移入回收站</span>
      </label>
    {/if}
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded">
      {#if extractResult}
        {#if extractResult.success && extractResult.failed === 0}
          <CircleCheck class="cq-icon text-green-500 shrink-0" />
          <span class="cq-text text-green-600 font-medium">完成</span>
          <span class="cq-text-sm text-muted-foreground ml-auto">{extractResult.extracted} 成功</span>
        {:else if extractResult.success}
          <CircleCheck class="cq-icon text-yellow-500 shrink-0" />
          <span class="cq-text text-yellow-600 font-medium">部分完成</span>
        {:else}
          <CircleX class="cq-icon text-red-500 shrink-0" />
          <span class="cq-text text-red-600 font-medium">失败</span>
        {/if}
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <div class="flex-1"><Progress value={progress} class="h-1.5" /></div>
        <span class="cq-text-sm text-muted-foreground">{progress}%</span>
      {:else}
        <FileArchive class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text text-muted-foreground">等待解压</span>
      {/if}
    </div>
    {#if phase === 'idle' || phase === 'error'}
      <Button class="w-full cq-button flex-1" onclick={handleExtract} disabled={!canExtract}>
        <Play class="cq-icon mr-1" /><span>开始解压</span>
      </Button>
    {:else if phase === 'extracting'}
      <Button class="w-full cq-button flex-1" disabled>
        <LoaderCircle class="cq-icon mr-1 animate-spin" /><span>解压中</span>
      </Button>
    {:else if phase === 'completed'}
      <Button class="w-full cq-button flex-1" onclick={handleReset}>
        <Play class="cq-icon mr-1" /><span>重新开始</span>
      </Button>
    {/if}
    <Button variant="ghost" class="w-full cq-button-sm" onclick={handleReset} disabled={isRunning}>
      <RotateCcw class="cq-icon mr-1" />重置
    </Button>
  </div>
{/snippet}

{#snippet filesBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold flex items-center gap-1"><FileArchive class="cq-icon text-blue-500" />待解压文件</span>
      <span class="cq-text-sm text-muted-foreground">{archivePaths.length || parsePaths(pathsText).length} 个</span>
    </div>
    <div class="flex-1 overflow-y-auto cq-padding bg-muted/30 cq-rounded">
      {#if archivePaths.length > 0 || parsePaths(pathsText).length > 0}
        {#each (archivePaths.length > 0 ? archivePaths : parsePaths(pathsText)) as filePath, idx}
          <div class="cq-text-sm text-muted-foreground truncate py-0.5" title={filePath}>{idx + 1}. {filePath.split(/[/\\]/).pop()}</div>
        {/each}
      {:else}
        <div class="cq-text text-muted-foreground text-center py-3">暂无文件</div>
      {/if}
    </div>
  </div>
{/snippet}

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

{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'source'}{@render sourceBlock()}
  {:else if blockId === 'options'}{@render optionsBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'files'}{@render filesBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 400px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={200} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="bandia" 
    icon={FileArchive} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="bandia" 
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
        nodeType="bandia"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={BANDIA_DEFAULT_GRID_LAYOUT}
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
