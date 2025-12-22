<script lang="ts">
  /**
   * LinedupNode - 行去重工具节点
   * 
   * 功能：过滤包含特定内容的行
   * 如果源行包含过滤行中的任何内容，则移除该行
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Textarea } from '$lib/components/ui/textarea';
  import { Label } from '$lib/components/ui/label';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { LINEDUP_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    LoaderCircle, Filter, FolderOpen, Clipboard,
    Copy, Check, RotateCcw, Zap, FileText
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: Record<string, any>;
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'running' | 'completed' | 'error';

  interface LinedupState {
    sourceText: string;
    filterText: string;
  }

  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<LinedupState>(nodeId));
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  // 状态变量
  let sourceText = $state('');
  let filterText = $state('');
  let resultText = $state('');
  
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let copied = $state(false);
  let removedCount = $state(0);
  let keptCount = $state(0);
  let hasInputConnection = $state(false);
  let layoutRenderer = $state<any>(undefined);

  let initialized = $state(false);
  
  $effect(() => {
    if (initialized) return;
    
    if (savedState) {
      sourceText = savedState.sourceText ?? '';
      filterText = savedState.filterText ?? '';
    }
    initialized = true;
  });
  
  $effect(() => {
    logs = [...dataLogs];
    hasInputConnection = dataHasInputConnection;
  });

  function saveState() {
    if (!initialized) return;
    setNodeState<LinedupState>(nodeId, { sourceText, filterText });
  }

  let isRunning = $derived(phase === 'running');
  let sourceLines = $derived(sourceText.split('\n').filter(s => s.trim()));
  let filterLines = $derived(filterText.split('\n').filter(s => s.trim()));
  let canExecute = $derived(sourceLines.length > 0 && !isRunning);
  
  let borderClass = $derived({
    idle: 'border-border',
    running: 'border-primary shadow-sm',
    completed: 'border-green-500/50',
    error: 'border-destructive/50'
  }[phase]);

  $effect(() => { if (sourceText || filterText) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-50), msg]; }

  async function pasteSource() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) sourceText = text;
    } catch (e) { log(`读取剪贴板失败: ${e}`); }
  }

  async function pasteFilter() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) filterText = text;
    } catch (e) { log(`读取剪贴板失败: ${e}`); }
  }

  // 执行过滤
  async function handleExecute() {
    if (!canExecute) return;
    
    phase = 'running';
    resultText = '';
    removedCount = 0;
    keptCount = 0;
    log(`🔍 开始过滤，源: ${sourceLines.length} 行，过滤条件: ${filterLines.length} 行`);
    
    try {
      const response = await api.executeNode('linedup', {
        action: 'filter',
        source_lines: sourceLines,
        filter_lines: filterLines
      }) as any;
      
      if (response.logs) for (const m of response.logs) log(m);
      
      if (response.success) {
        phase = 'completed';
        const filtered = response.data?.filtered_lines ?? [];
        resultText = filtered.join('\n');
        removedCount = response.data?.removed_count ?? 0;
        keptCount = response.data?.kept_count ?? 0;
        log(`✅ ${response.message}`);
      } else {
        phase = 'error';
        log(`❌ 过滤失败: ${response.message}`);
      }
    } catch (error) {
      phase = 'error';
      log(`❌ 过滤失败: ${error}`);
    }
  }

  function handleReset() {
    phase = 'idle';
    resultText = '';
    removedCount = 0;
    keptCount = 0;
    logs = [];
  }

  async function copyResult() {
    if (!resultText) return;
    try {
      await navigator.clipboard.writeText(resultText);
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
      log('✅ 结果已复制到剪贴板');
    } catch (e) { 
      console.error('复制失败:', e); 
      log(`❌ 复制失败: ${e}`);
    }
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(logs.join('\n'));
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }
</script>

{#snippet sourceBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between cq-mb shrink-0">
      <Label class="cq-text font-medium">源内容</Label>
      <Button variant="outline" size="icon" class="cq-button-icon" onclick={pasteSource} disabled={isRunning}>
        <Clipboard class="cq-icon" />
      </Button>
    </div>
    <Textarea 
      bind:value={sourceText}
      placeholder="每行一个内容..."
      disabled={isRunning}
      class="flex-1 cq-input font-mono text-xs resize-none min-h-[80px]"
    />
    <span class="cq-text-sm text-muted-foreground mt-1">{sourceLines.length} 行</span>
  </div>
{/snippet}

{#snippet filterBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between cq-mb shrink-0">
      <Label class="cq-text font-medium">过滤条件</Label>
      <Button variant="outline" size="icon" class="cq-button-icon" onclick={pasteFilter} disabled={isRunning}>
        <Clipboard class="cq-icon" />
      </Button>
    </div>
    <Textarea 
      bind:value={filterText}
      placeholder="每行一个过滤关键词...&#10;源行包含这些内容将被移除"
      disabled={isRunning}
      class="flex-1 cq-input font-mono text-xs resize-none min-h-[80px]"
    />
    <span class="cq-text-sm text-muted-foreground mt-1">{filterLines.length} 个条件</span>
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="p-2 rounded cq-text-sm bg-muted/50">
      <div class="text-muted-foreground">源: {sourceLines.length} 行</div>
      <div class="text-muted-foreground">过滤: {filterLines.length} 条件</div>
      {#if keptCount > 0 || removedCount > 0}
        <div class="text-green-600 mt-1">保留: {keptCount}</div>
        <div class="text-red-500">移除: {removedCount}</div>
      {/if}
    </div>
    
    <Button 
      class="w-full cq-button flex-1" 
      onclick={handleExecute}
      disabled={!canExecute}
    >
      {#if isRunning}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<Zap class="cq-icon mr-1" />{/if}
      <span>过滤</span>
    </Button>
    
    <Button 
      variant="outline" 
      class="w-full cq-button flex-1" 
      onclick={copyResult}
      disabled={!resultText}
    >
      {#if copied}<Check class="cq-icon mr-1 text-green-500" />{:else}<Copy class="cq-icon mr-1" />{/if}
      <span>复制结果</span>
    </Button>
    
    <Button variant="ghost" class="w-full cq-button-sm" onclick={handleReset}>
      <RotateCcw class="cq-icon mr-1" />重置
    </Button>
  </div>
{/snippet}

{#snippet resultBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between cq-padding border-b bg-muted/30 shrink-0">
      <span class="font-semibold cq-text">过滤结果</span>
      {#if keptCount > 0}
        <span class="cq-text-sm text-muted-foreground">{keptCount} 行</span>
      {/if}
    </div>
    <Textarea 
      bind:value={resultText}
      readonly
      placeholder="过滤后的结果将显示在这里..."
      class="flex-1 cq-input font-mono text-xs resize-none border-0"
    />
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
        {#each logs.slice(-15) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'source'}{@render sourceBlock()}
  {:else if blockId === 'filter'}{@render filterBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'result'}{@render resultBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 480px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={360} minHeight={300} maxWidth={480} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="linedup" 
    icon={Filter} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="linedup" 
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
        nodeType="linedup"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={LINEDUP_DEFAULT_GRID_LAYOUT}
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
