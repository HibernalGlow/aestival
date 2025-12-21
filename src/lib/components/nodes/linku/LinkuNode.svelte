<script lang="ts">
  /**
   * LinkuNode - 软链接管理节点组件
   * 支持创建、移动、恢复软链接
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { LINKU_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, FolderOpen, Link, Clipboard,
    CircleCheck, CircleX, Copy, Check, RotateCcw, RefreshCw
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: Record<string, any>;
      status?: 'idle' | 'running' | 'completed' | 'error';
      logs?: string[];
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'running' | 'completed' | 'error';

  interface LinkRecord {
    link: string;
    target: string;
    type: string;
    created_at: string;
  }

  interface LinkuState {
    sourcePath: string;
    targetPath: string;
    links: LinkRecord[];
  }

  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<LinkuState>(nodeId));
  const dataLogs = $derived(data?.logs ?? []);

  let sourcePath = $state('');
  let targetPath = $state('');
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let copied = $state(false);
  let links = $state<LinkRecord[]>([]);
  let layoutRenderer = $state<any>(undefined);

  let initialized = $state(false);
  
  $effect(() => {
    if (initialized) return;
    if (savedState) {
      sourcePath = savedState.sourcePath ?? '';
      targetPath = savedState.targetPath ?? '';
      links = savedState.links ?? [];
    }
    initialized = true;
  });
  
  $effect(() => { logs = [...dataLogs]; });

  function saveState() {
    if (!initialized) return;
    setNodeState<LinkuState>(nodeId, { sourcePath, targetPath, links });
  }

  let canExecute = $derived(phase === 'idle' && sourcePath.trim() !== '');
  let isRunning = $derived(phase === 'running');
  let borderClass = $derived({
    idle: 'border-border', running: 'border-primary shadow-sm',
    completed: 'border-primary/50', error: 'border-destructive/50'
  }[phase]);

  $effect(() => { if (sourcePath || targetPath) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  async function pasteSource() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) {
        sourcePath = text.trim().replace(/^["']|["']$/g, '');
        log(`📋 源路径: ${sourcePath.split(/[/\\]/).pop()}`);
      }
    } catch (e) { log(`❌ 读取剪贴板失败: ${e}`); }
  }

  async function selectSource() {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFolderDialog('选择源路径');
      if (selected) {
        sourcePath = selected;
        log(`📁 选择源路径: ${selected.split(/[/\\]/).pop()}`);
      }
    } catch (e) { log(`❌ 选择失败: ${e}`); }
  }

  async function pasteTarget() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) {
        targetPath = text.trim().replace(/^["']|["']$/g, '');
        log(`📋 目标路径: ${targetPath.split(/[/\\]/).pop()}`);
      }
    } catch (e) { log(`❌ 读取剪贴板失败: ${e}`); }
  }

  async function selectTarget() {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFolderDialog('选择目标路径');
      if (selected) {
        targetPath = selected;
        log(`📁 选择目标路径: ${selected.split(/[/\\]/).pop()}`);
      }
    } catch (e) { log(`❌ 选择失败: ${e}`); }
  }

  async function handleCreateLink() {
    if (!sourcePath.trim() || !targetPath.trim()) { 
      log('❌ 请输入源路径和目标路径'); 
      return; 
    }
    
    phase = 'running';
    log('🔗 创建软链接...');
    
    try {
      const response = await api.executeNode('linku', {
        action: 'create',
        path: sourcePath.trim(),
        target: targetPath.trim()
      }) as any;
      
      if (response.success) {
        phase = 'completed';
        log(`✅ ${response.message}`);
        await loadLinks();
      } else {
        phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (e) {
      phase = 'error';
      log(`❌ 创建失败: ${e}`);
    }
  }

  async function handleMoveAndLink() {
    if (!sourcePath.trim() || !targetPath.trim()) { 
      log('❌ 请输入源路径和目标路径'); 
      return; 
    }
    
    phase = 'running';
    log('📦 移动并创建链接...');
    
    try {
      const response = await api.executeNode('linku', {
        action: 'move_link',
        path: sourcePath.trim(),
        target: targetPath.trim()
      }) as any;
      
      if (response.success) {
        phase = 'completed';
        log(`✅ ${response.message}`);
        await loadLinks();
      } else {
        phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (e) {
      phase = 'error';
      log(`❌ 操作失败: ${e}`);
    }
  }

  async function loadLinks() {
    try {
      const response = await api.executeNode('linku', { action: 'list' }) as any;
      if (response.success) {
        links = response.data?.links ?? [];
        saveState();
      }
    } catch (e) {
      log(`❌ 加载链接列表失败: ${e}`);
    }
  }

  async function handleRecover() {
    phase = 'running';
    log('🔄 恢复链接...');
    
    try {
      const response = await api.executeNode('linku', { action: 'recover' }) as any;
      
      if (response.success) {
        phase = 'completed';
        log(`✅ ${response.message}`);
        await loadLinks();
      } else {
        phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (e) {
      phase = 'error';
      log(`❌ 恢复失败: ${e}`);
    }
  }

  function handleReset() {
    phase = 'idle';
    logs = [];
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
  <div class="flex flex-col cq-gap h-full">
    <span class="cq-text-sm text-muted-foreground">源路径（实际文件/目录）</span>
    <div class="flex cq-gap">
      <Button variant="outline" size="sm" class="cq-button-sm" onclick={pasteSource} disabled={isRunning}>
        <Clipboard class="cq-icon" />
      </Button>
      <Button variant="outline" size="sm" class="cq-button-sm" onclick={selectSource} disabled={isRunning}>
        <FolderOpen class="cq-icon" />
      </Button>
    </div>
    <Input bind:value={sourcePath} placeholder="源路径" disabled={isRunning} class="cq-text font-mono" />
  </div>
{/snippet}

{#snippet targetBlock()}
  <div class="flex flex-col cq-gap h-full">
    <span class="cq-text-sm text-muted-foreground">目标路径（链接位置）</span>
    <div class="flex cq-gap">
      <Button variant="outline" size="sm" class="cq-button-sm" onclick={pasteTarget} disabled={isRunning}>
        <Clipboard class="cq-icon" />
      </Button>
      <Button variant="outline" size="sm" class="cq-button-sm" onclick={selectTarget} disabled={isRunning}>
        <FolderOpen class="cq-icon" />
      </Button>
    </div>
    <Input bind:value={targetPath} placeholder="目标路径" disabled={isRunning} class="cq-text font-mono" />
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded">
      {#if phase === 'completed'}
        <CircleCheck class="cq-icon text-green-500 shrink-0" />
        <span class="cq-text-sm text-green-600">完成</span>
      {:else if phase === 'error'}
        <CircleX class="cq-icon text-red-500 shrink-0" />
        <span class="cq-text-sm text-red-600">失败</span>
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <span class="cq-text-sm">处理中</span>
      {:else}
        <Link class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text-sm text-muted-foreground">等待</span>
      {/if}
    </div>
    <Button class="w-full cq-button-sm" onclick={handleCreateLink} disabled={!canExecute || !targetPath || isRunning}>
      <Link class="cq-icon mr-1" />创建链接
    </Button>
    <Button variant="secondary" class="w-full cq-button-sm" onclick={handleMoveAndLink} disabled={!canExecute || !targetPath || isRunning}>
      <Play class="cq-icon mr-1" />移动并链接
    </Button>
    <Button variant="outline" class="w-full cq-button-sm" onclick={handleRecover} disabled={isRunning}>
      <RefreshCw class="cq-icon mr-1" />恢复链接
    </Button>
    <Button variant="ghost" class="w-full cq-button-sm" onclick={handleReset} disabled={isRunning}>
      <RotateCcw class="cq-icon mr-1" />重置
    </Button>
  </div>
{/snippet}

{#snippet linksBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold">已记录链接 ({links.length})</span>
      <Button variant="ghost" size="sm" class="h-5 px-2" onclick={loadLinks}>
        刷新
      </Button>
    </div>
    <div class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding space-y-1">
      {#if links.length > 0}
        {#each links as link}
          <div class="cq-padding bg-background/50 cq-rounded cq-text-sm">
            <div class="flex items-center gap-1">
              <Link class="w-3 h-3 text-primary shrink-0" />
              <span class="truncate">{link.link.split(/[/\\]/).pop()}</span>
            </div>
            <div class="text-muted-foreground truncate pl-4">→ {link.target.split(/[/\\]/).pop()}</div>
          </div>
        {/each}
      {:else}
        <div class="cq-text text-muted-foreground text-center py-3">暂无记录</div>
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
        {#each logs as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'source'}{@render sourceBlock()}
  {:else if blockId === 'target'}{@render targetBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'links'}{@render linksBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 380px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={200} maxWidth={380} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="linku" 
    icon={Link} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="linku" 
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
        nodeType="linku"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={LINKU_DEFAULT_GRID_LAYOUT}
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
