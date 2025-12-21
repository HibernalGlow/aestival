<script lang="ts">
  /**
   * ReinstallpNode - Python 可编辑包重新安装节点组件
   * 扫描目录查找 pyproject.toml 项目并重新安装
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Checkbox } from '$lib/components/ui/checkbox';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { REINSTALLP_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, FolderOpen, Clipboard, Search,
    CircleCheck, CircleX, Copy, Check, Download
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

  interface Project {
    path: string;
    name: string;
    selected: boolean;
    status?: 'pending' | 'success' | 'failed';
  }

  interface ReinstallpState {
    pathText: string;
    useSystem: boolean;
    projects: Project[];
  }

  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<ReinstallpState>(nodeId));
  const dataLogs = $derived(data?.logs ?? []);

  let pathText = $state('');
  let useSystem = $state(true);
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let copied = $state(false);
  let projects = $state<Project[]>([]);
  let layoutRenderer = $state<any>(undefined);

  let initialized = $state(false);
  
  $effect(() => {
    if (initialized) return;
    if (savedState) {
      pathText = savedState.pathText ?? '';
      useSystem = savedState.useSystem ?? true;
      projects = savedState.projects ?? [];
    }
    initialized = true;
  });
  
  $effect(() => { logs = [...dataLogs]; });

  function saveState() {
    if (!initialized) return;
    setNodeState<ReinstallpState>(nodeId, { pathText, useSystem, projects });
  }

  let canScan = $derived(phase === 'idle' && pathText.trim() !== '');
  let canInstall = $derived(phase === 'idle' && projects.some(p => p.selected));
  let isRunning = $derived(phase === 'running');
  let borderClass = $derived({
    idle: 'border-border', running: 'border-primary shadow-sm',
    completed: 'border-primary/50', error: 'border-destructive/50'
  }[phase]);

  $effect(() => { if (pathText || useSystem) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  async function pasteFromClipboard() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) {
        pathText = text.trim().replace(/^["']|["']$/g, '');
        log(`📋 从剪贴板读取路径`);
      }
    } catch (e) { log(`❌ 读取剪贴板失败: ${e}`); }
  }

  async function selectFolder() {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFolderDialog('选择要扫描的目录');
      if (selected) {
        pathText = selected;
        log(`📁 选择了目录: ${selected.split(/[/\\]/).pop()}`);
      }
    } catch (e) { log(`❌ 选择目录失败: ${e}`); }
  }

  async function handleScan() {
    if (!pathText.trim()) { log('❌ 请输入扫描路径'); return; }
    
    phase = 'running';
    log('🔍 扫描项目...');
    
    try {
      const response = await api.executeNode('reinstallp', {
        action: 'scan',
        path: pathText.trim()
      }) as any;
      
      if (response.success) {
        projects = (response.data?.projects ?? []).map((p: any) => ({
          path: p.path,
          name: p.name,
          selected: true,
          status: 'pending'
        }));
        phase = 'completed';
        log(`✅ 找到 ${projects.length} 个项目`);
        saveState();
      } else {
        phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (e) {
      phase = 'error';
      log(`❌ 扫描失败: ${e}`);
    }
  }

  async function handleInstall() {
    const selectedProjects = projects.filter(p => p.selected);
    if (selectedProjects.length === 0) { log('❌ 请选择要安装的项目'); return; }
    
    phase = 'running';
    log(`📦 安装 ${selectedProjects.length} 个项目...`);
    
    try {
      const response = await api.executeNode('reinstallp', {
        action: 'install',
        projects: selectedProjects.map(p => p.path),
        use_system: useSystem
      }) as any;
      
      // 更新项目状态
      const results = response.data?.results ?? [];
      projects = projects.map(p => {
        const result = results.find((r: any) => r.path === p.path);
        if (result) {
          return { ...p, status: result.status === 'success' ? 'success' : 'failed' };
        }
        return p;
      });
      
      if (response.success) {
        phase = 'completed';
        log(`✅ ${response.message}`);
      } else {
        phase = 'error';
        log(`❌ ${response.message}`);
      }
      saveState();
    } catch (e) {
      phase = 'error';
      log(`❌ 安装失败: ${e}`);
    }
  }

  function toggleProject(index: number) {
    if (isRunning) return;
    projects[index].selected = !projects[index].selected;
    projects = [...projects];
    saveState();
  }

  function selectAll() {
    projects = projects.map(p => ({ ...p, selected: true }));
    saveState();
  }

  function selectNone() {
    projects = projects.map(p => ({ ...p, selected: false }));
    saveState();
  }

  function handleReset() {
    phase = 'idle';
    projects = projects.map(p => ({ ...p, status: 'pending' }));
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
    <div class="flex cq-gap">
      <Button variant="outline" size="sm" class="cq-button-sm flex-1" onclick={pasteFromClipboard} disabled={isRunning}>
        <Clipboard class="cq-icon mr-1" />剪贴板
      </Button>
      <Button variant="outline" size="sm" class="cq-button-sm flex-1" onclick={selectFolder} disabled={isRunning}>
        <FolderOpen class="cq-icon mr-1" />选择
      </Button>
    </div>
    <Input bind:value={pathText} placeholder="扫描目录路径" disabled={isRunning} class="cq-text font-mono" />
  </div>
{/snippet}

{#snippet optionsBlock()}
  <div class="flex flex-col cq-gap">
    <span class="cq-text-sm text-muted-foreground">安装模式</span>
    <label class="flex items-center cq-gap cursor-pointer" onclick={() => { if (!isRunning) useSystem = true; }}>
      <Checkbox checked={useSystem} disabled={isRunning} />
      <span class="cq-text-sm">系统安装</span>
    </label>
    <label class="flex items-center cq-gap cursor-pointer" onclick={() => { if (!isRunning) useSystem = false; }}>
      <Checkbox checked={!useSystem} disabled={isRunning} />
      <span class="cq-text-sm">虚拟环境</span>
    </label>
    <span class="cq-text-sm text-muted-foreground mt-2">
      {useSystem ? '使用 --system 安装到系统 Python' : '安装到项目虚拟环境'}
    </span>
  </div>
{/snippet}

{#snippet projectsBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold">项目 ({projects.filter(p => p.selected).length}/{projects.length})</span>
      <div class="flex cq-gap">
        <Button variant="ghost" size="sm" class="h-5 px-2 cq-text-sm" onclick={selectAll}>全选</Button>
        <Button variant="ghost" size="sm" class="h-5 px-2 cq-text-sm" onclick={selectNone}>全不选</Button>
      </div>
    </div>
    <div class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding space-y-1">
      {#if projects.length > 0}
        {#each projects as project, i}
          <div 
            class="flex items-center cq-gap cq-padding bg-background/50 cq-rounded cursor-pointer hover:bg-background/80"
            onclick={() => toggleProject(i)}
          >
            <Checkbox checked={project.selected} disabled={isRunning} />
            <div class="flex-1 min-w-0">
              <span class="cq-text truncate block">{project.name}</span>
              <span class="cq-text-sm text-muted-foreground truncate block">{project.path.split(/[/\\]/).slice(-2).join('/')}</span>
            </div>
            {#if project.status === 'success'}
              <CircleCheck class="w-4 h-4 text-green-500 shrink-0" />
            {:else if project.status === 'failed'}
              <CircleX class="w-4 h-4 text-red-500 shrink-0" />
            {/if}
          </div>
        {/each}
      {:else}
        <div class="cq-text text-muted-foreground text-center py-3">点击扫描查找项目</div>
      {/if}
    </div>
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
        <Search class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text-sm text-muted-foreground">等待</span>
      {/if}
    </div>
    <Button class="w-full cq-button-sm" onclick={handleScan} disabled={!canScan || isRunning}>
      <Search class="cq-icon mr-1" />扫描
    </Button>
    <Button variant="secondary" class="w-full cq-button-sm" onclick={handleInstall} disabled={!canInstall || isRunning}>
      <Download class="cq-icon mr-1" />安装选中
    </Button>
    <Button variant="ghost" class="w-full cq-button-sm" onclick={handleReset} disabled={isRunning}>
      重置
    </Button>
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
  {:else if blockId === 'options'}{@render optionsBlock()}
  {:else if blockId === 'projects'}{@render projectsBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 400px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={300} minHeight={240} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="reinstallp" 
    icon={Download} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="reinstallp" 
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
        nodeType="reinstallp"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={REINSTALLP_DEFAULT_GRID_LAYOUT}
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
