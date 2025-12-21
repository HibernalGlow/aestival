<script lang="ts">
  /**
   * ScoolpNode - Scoop 包管理节点组件
   * 支持检查状态、安装包、清理缓存、同步 buckets
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Checkbox } from '$lib/components/ui/checkbox';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { SCOOLP_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, Package, Download, Trash2, RefreshCw,
    CircleCheck, CircleX, Copy, Check, Plus
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

  interface ScoolpState {
    packageInput: string;
    bucketInput: string;
    cleanCache: boolean;
    cleanOldVersions: boolean;
    installedPackages: string[];
    buckets: string[];
    scoopInstalled: boolean;
  }

  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<ScoolpState>(nodeId));
  const dataLogs = $derived(data?.logs ?? []);

  let packageInput = $state('');
  let bucketInput = $state('');
  let cleanCache = $state(true);
  let cleanOldVersions = $state(true);
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let copied = $state(false);
  let installedPackages = $state<string[]>([]);
  let buckets = $state<string[]>([]);
  let scoopInstalled = $state(false);
  let layoutRenderer = $state<any>(undefined);

  let initialized = $state(false);
  
  $effect(() => {
    if (initialized) return;
    if (savedState) {
      packageInput = savedState.packageInput ?? '';
      bucketInput = savedState.bucketInput ?? '';
      cleanCache = savedState.cleanCache ?? true;
      cleanOldVersions = savedState.cleanOldVersions ?? true;
      installedPackages = savedState.installedPackages ?? [];
      buckets = savedState.buckets ?? [];
      scoopInstalled = savedState.scoopInstalled ?? false;
    }
    initialized = true;
  });
  
  $effect(() => { logs = [...dataLogs]; });

  function saveState() {
    if (!initialized) return;
    setNodeState<ScoolpState>(nodeId, { 
      packageInput, bucketInput, cleanCache, cleanOldVersions,
      installedPackages, buckets, scoopInstalled 
    });
  }

  let isRunning = $derived(phase === 'running');
  let borderClass = $derived({
    idle: 'border-border', running: 'border-primary shadow-sm',
    completed: 'border-primary/50', error: 'border-destructive/50'
  }[phase]);

  $effect(() => { if (packageInput || bucketInput || cleanCache || cleanOldVersions) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  async function checkStatus() {
    phase = 'running';
    log('🔍 检查 Scoop 状态...');
    
    try {
      const response = await api.executeNode('scoolp', { action: 'status' }) as any;
      
      if (response.success) {
        scoopInstalled = response.scoop_installed ?? false;
        installedPackages = response.installed_packages ?? [];
        buckets = response.added_buckets ?? [];
        phase = 'completed';
        log(`✅ ${response.message}`);
        saveState();
      } else {
        phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (e) {
      phase = 'error';
      log(`❌ 检查失败: ${e}`);
    }
  }

  async function handleInstall() {
    if (!packageInput.trim()) { log('❌ 请输入要安装的包'); return; }
    
    const packages = packageInput.split(/[,\s]+/).filter(p => p.trim());
    if (packages.length === 0) { log('❌ 请输入有效的包名'); return; }
    
    phase = 'running';
    log(`📦 安装 ${packages.length} 个包...`);
    
    try {
      const response = await api.executeNode('scoolp', {
        action: 'install',
        packages
      }) as any;
      
      if (response.success) {
        phase = 'completed';
        log(`✅ ${response.message}`);
        await checkStatus();
      } else {
        phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (e) {
      phase = 'error';
      log(`❌ 安装失败: ${e}`);
    }
  }

  async function handleClean() {
    phase = 'running';
    log('🧹 清理中...');
    
    try {
      const response = await api.executeNode('scoolp', {
        action: 'clean',
        clean_cache: cleanCache,
        clean_old_versions: cleanOldVersions
      }) as any;
      
      if (response.success) {
        phase = 'completed';
        log(`✅ ${response.message}`);
      } else {
        phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (e) {
      phase = 'error';
      log(`❌ 清理失败: ${e}`);
    }
  }

  async function handleSync() {
    const bucketsToAdd = bucketInput.split(/[,\s]+/).filter(b => b.trim());
    
    phase = 'running';
    log('🔄 同步 buckets...');
    
    try {
      const response = await api.executeNode('scoolp', {
        action: 'sync',
        buckets: bucketsToAdd
      }) as any;
      
      if (response.success) {
        phase = 'completed';
        log(`✅ ${response.message}`);
        await checkStatus();
      } else {
        phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (e) {
      phase = 'error';
      log(`❌ 同步失败: ${e}`);
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

{#snippet packagesBlock()}
  <div class="flex flex-col cq-gap h-full">
    <span class="cq-text-sm text-muted-foreground">安装包（逗号或空格分隔）</span>
    <Input bind:value={packageInput} placeholder="git, nodejs, python..." disabled={isRunning} class="cq-text" />
    <Button class="w-full cq-button-sm" onclick={handleInstall} disabled={isRunning || !packageInput.trim()}>
      <Download class="cq-icon mr-1" />安装
    </Button>
    <div class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding">
      <span class="cq-text-sm text-muted-foreground">已安装 ({installedPackages.length})</span>
      <div class="flex flex-wrap gap-1 mt-1">
        {#each installedPackages.slice(0, 20) as pkg}
          <span class="cq-text-sm bg-primary/10 text-primary px-1.5 py-0.5 rounded">{pkg}</span>
        {/each}
        {#if installedPackages.length > 20}
          <span class="cq-text-sm text-muted-foreground">+{installedPackages.length - 20} 更多</span>
        {/if}
      </div>
    </div>
  </div>
{/snippet}

{#snippet bucketsBlock()}
  <div class="flex flex-col cq-gap h-full">
    <span class="cq-text-sm text-muted-foreground">添加 Bucket</span>
    <Input bind:value={bucketInput} placeholder="extras, versions..." disabled={isRunning} class="cq-text-sm" />
    <Button variant="outline" class="w-full cq-button-sm" onclick={handleSync} disabled={isRunning}>
      <Plus class="cq-icon mr-1" />同步
    </Button>
    <div class="flex-1 overflow-y-auto">
      <span class="cq-text-sm text-muted-foreground">已添加</span>
      <div class="space-y-0.5 mt-1">
        {#each buckets as bucket}
          <div class="cq-text-sm bg-green-500/10 text-green-600 px-1.5 py-0.5 rounded">{bucket}</div>
        {/each}
      </div>
    </div>
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <Button variant="outline" class="w-full cq-button-sm" onclick={checkStatus} disabled={isRunning}>
      <RefreshCw class="cq-icon mr-1" />检查状态
    </Button>
    <div class="flex flex-col cq-gap">
      <label class="flex items-center cq-gap cursor-pointer" onclick={() => { if (!isRunning) cleanCache = !cleanCache; }}>
        <Checkbox checked={cleanCache} disabled={isRunning} />
        <span class="cq-text-sm">清理缓存</span>
      </label>
      <label class="flex items-center cq-gap cursor-pointer" onclick={() => { if (!isRunning) cleanOldVersions = !cleanOldVersions; }}>
        <Checkbox checked={cleanOldVersions} disabled={isRunning} />
        <span class="cq-text-sm">清理旧版本</span>
      </label>
    </div>
    <Button variant="secondary" class="w-full cq-button-sm" onclick={handleClean} disabled={isRunning}>
      <Trash2 class="cq-icon mr-1" />清理
    </Button>
    <Button variant="ghost" class="w-full cq-button-sm" onclick={handleReset} disabled={isRunning}>
      重置
    </Button>
  </div>
{/snippet}

{#snippet statusBlock()}
  <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded h-full">
    {#if phase === 'completed'}
      <CircleCheck class="cq-icon text-green-500 shrink-0" />
      <div class="flex flex-col">
        <span class="cq-text text-green-600 font-medium">
          {scoopInstalled ? 'Scoop 已安装' : 'Scoop 未安装'}
        </span>
        {#if scoopInstalled}
          <span class="cq-text-sm text-muted-foreground">
            {installedPackages.length} 个包, {buckets.length} 个 bucket
          </span>
        {/if}
      </div>
    {:else if phase === 'error'}
      <CircleX class="cq-icon text-red-500 shrink-0" />
      <span class="cq-text text-red-600 font-medium">操作失败</span>
    {:else if isRunning}
      <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
      <span class="cq-text">处理中...</span>
    {:else}
      <Package class="cq-icon text-muted-foreground/50 shrink-0" />
      <span class="cq-text text-muted-foreground">点击"检查状态"开始</span>
    {/if}
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
  {#if blockId === 'packages'}{@render packagesBlock()}
  {:else if blockId === 'buckets'}{@render bucketsBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'status'}{@render statusBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 400px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={300} minHeight={220} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="scoolp" 
    icon={Package} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="scoolp" 
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
        nodeType="scoolp"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={SCOOLP_DEFAULT_GRID_LAYOUT}
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
