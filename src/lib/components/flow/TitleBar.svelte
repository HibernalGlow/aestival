<script lang="ts">
  /**
   * 自定义标题栏 - 集成窗口控制和工具栏功能
   */
  import { flowStore, taskStore, isRunning, openSettingsOverlay } from '$lib/stores';
  import { api } from '$lib/services/api';
  import { 
    Save, Play, Square, RotateCcw, FileDown, FileUp, 
    Sun, Moon, Monitor, Image, X,
    Minus, Square as MaxIcon, X as CloseIcon,
    FolderOpen, Settings
  } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { themeStore, toggleThemeMode } from '$lib/stores/theme.svelte';
  import { settingsManager } from '$lib/settings/settingsManager';

  // 获取面板设置
  let panelSettings = $state(settingsManager.getSettings().panels);
  
  // 计算标题栏样式
  let toolbarStyle = $derived(
    `background-color: hsl(var(--card) / ${panelSettings.topToolbarOpacity / 100}); backdrop-filter: blur(${panelSettings.topToolbarBlur}px);`
  );

  // Tauri 窗口 API
  let windowApi: any = null;
  
  // 动态导入 Tauri API
  import { onMount } from 'svelte';
  onMount(async () => {
    try {
      const { getCurrentWindow } = await import('@tauri-apps/api/window');
      windowApi = getCurrentWindow();
    } catch (e) {
      console.log('Not running in Tauri');
    }
    
    // 监听设置变化
    settingsManager.addListener((s) => {
      panelSettings = s.panels;
    });
  });

  // 拖拽窗口
  async function startDrag(e: MouseEvent) {
    // 只响应左键
    if (e.button !== 0) return;
    await windowApi?.startDragging();
  }

  // 窗口控制
  async function minimizeWindow() {
    await windowApi?.minimize();
  }

  async function toggleMaximize() {
    await windowApi?.toggleMaximize();
  }

  async function closeWindow() {
    await windowApi?.close();
  }

  // 流程管理弹窗
  let showFlowManager = $state(false);
  let flows = $state<Array<{id: string, name: string, updatedAt: string}>>([]);

  function loadFlowList() {
    try {
      const saved = localStorage.getItem('aestival_flows');
      if (saved) flows = JSON.parse(saved);
    } catch (e) {
      console.error('加载流程列表失败:', e);
    }
  }

  function openFlowManager() {
    loadFlowList();
    showFlowManager = true;
  }

  function closeFlowManager() {
    showFlowManager = false;
  }

  function selectFlow(id: string) {
    api.getFlow(id)
      .then(flow => {
        flowStore.load(flow);
        // 记忆上次使用的流程
        localStorage.setItem('aestivus_last_flow', id);
      })
      .catch(e => console.error('加载流程失败:', e));
    showFlowManager = false;
  }

  function createNewFlow() {
    flowStore.reset();
    // 清除上次记忆
    localStorage.removeItem('aestivus_last_flow');
    showFlowManager = false;
  }

  function deleteFlow(id: string, event: MouseEvent) {
    event.stopPropagation();
    if (confirm('确定删除此流程？')) {
      flows = flows.filter(f => f.id !== id);
      localStorage.setItem('aestival_flows', JSON.stringify(flows));
    }
  }

  // 背景图展开栏
  let showBgBar = $state(false);

  function toggleBgBar() {
    showBgBar = !showBgBar;
  }

  // 背景图上传
  function uploadBackground() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = () => {
          themeStore.setBackgroundImage(reader.result as string);
        };
        reader.readAsDataURL(file);
      }
    };
    input.click();
  }

  function clearBackground() {
    themeStore.clearBackground();
  }

  // 流程操作
  async function saveFlow() {
    const flow = flowStore.toFlow();
    try {
      if (flow.id && flowStore.getState().id) {
        await api.updateFlow(flow.id, flow);
      } else {
        const saved = await api.createFlow(flow);
        flowStore.load(saved);
      }
      flowStore.markSaved();
    } catch (e) { console.error('保存失败:', e); }
  }

  async function executeFlow() {
    const state = flowStore.getState();
    if (!state.id) await saveFlow();
    try {
      const { taskId } = await api.executeFlow(flowStore.getState().id!);
      taskStore.startTask(taskId);
    } catch (e) { console.error('执行失败:', e); }
  }

  function stopExecution() {
    const taskId = $taskStore.taskId;
    if (taskId) { api.cancelTask(taskId); taskStore.cancel(); }
  }

  function resetFlow() {
    if (confirm('确定要重置流程吗？')) { flowStore.reset(); taskStore.reset(); }
  }

  function exportFlow() {
    const flow = flowStore.toFlow();
    const blob = new Blob([JSON.stringify(flow, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${flow.name || 'flow'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function importFlow() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const text = await file.text();
        flowStore.load(JSON.parse(text));
      }
    };
    input.click();
  }
</script>

<!-- 标题栏容器 -->
<div class="flex flex-col">
  <!-- 顶部标题栏 -->
  <div class="h-10 border-b flex items-center select-none" style={toolbarStyle}>
    <!-- 左侧：Logo 和流程名 -->
  <div class="flex items-center gap-2 px-3">
    <span class="text-sm font-bold text-primary">Aestivus</span>
    <div class="w-px h-4 bg-border"></div>
    <Button variant="ghost" size="sm" class="h-7 px-2" onclick={openFlowManager} title="打开流程">
      <FolderOpen class="w-3.5 h-3.5 mr-1" />
      <span class="text-xs">流程</span>
    </Button>
    <input
      type="text"
      class="text-sm bg-transparent border-none focus:outline-none focus:ring-1 focus:ring-primary rounded px-2 py-1 w-32"
      value={$flowStore.name}
      onchange={(e) => flowStore.setName(e.currentTarget.value)}
      placeholder="未命名流程"
    />
    {#if $flowStore.isDirty}
      <span class="text-xs text-amber-600 bg-amber-100 dark:bg-amber-900/30 px-1.5 py-0.5 rounded">未保存</span>
    {/if}
  </div>

  <!-- 中间：左侧拖拽区域 -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="flex-1 h-full cursor-default" onmousedown={startDrag}></div>

  <!-- 居中按钮组 -->
  <div class="flex items-center gap-0.5">
    <!-- 主题模式切换 -->
    <Button variant="ghost" size="icon" class="h-7 w-7" onclick={toggleThemeMode} title="主题">
      {#if $themeStore.mode === 'dark'}<Moon class="w-3.5 h-3.5" />
      {:else if $themeStore.mode === 'light'}<Sun class="w-3.5 h-3.5" />
      {:else}<Monitor class="w-3.5 h-3.5" />{/if}
    </Button>
    <!-- 背景图展开按钮 -->
    <Button variant={showBgBar ? "secondary" : "ghost"} size="icon" class="h-7 w-7" onclick={toggleBgBar} title="背景图设置">
      <Image class="w-3.5 h-3.5" />
    </Button>
    <!-- 设置 -->
    <Button variant="ghost" size="icon" class="h-7 w-7" onclick={openSettingsOverlay} title="设置">
      <Settings class="w-3.5 h-3.5" />
    </Button>
  </div>

  <!-- 中间：右侧拖拽区域 -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="flex-1 h-full cursor-default" onmousedown={startDrag}></div>

  <!-- 右侧：工具按钮 -->
  <div class="flex items-center gap-0.5 px-2">
    <!-- 流程操作 -->
    <Button variant="ghost" size="icon" class="h-7 w-7" onclick={importFlow} title="导入">
      <FileUp class="w-3.5 h-3.5" />
    </Button>
    <Button variant="ghost" size="icon" class="h-7 w-7" onclick={exportFlow} title="导出">
      <FileDown class="w-3.5 h-3.5" />
    </Button>
    <Button variant="ghost" size="icon" class="h-7 w-7" onclick={resetFlow} title="重置">
      <RotateCcw class="w-3.5 h-3.5" />
    </Button>
    <Button variant="ghost" size="icon" class="h-7 w-7" onclick={saveFlow} disabled={!$flowStore.isDirty} title="保存">
      <Save class="w-3.5 h-3.5" />
    </Button>
    {#if $isRunning}
      <Button variant="destructive" size="icon" class="h-7 w-7" onclick={stopExecution} title="停止">
        <Square class="w-3.5 h-3.5" />
      </Button>
    {:else}
      <Button variant="default" size="icon" class="h-7 w-7" onclick={executeFlow} disabled={$flowStore.nodes.length === 0} title="执行">
        <Play class="w-3.5 h-3.5" />
      </Button>
    {/if}
    
    <div class="w-px h-5 bg-border mx-1"></div>
    
    <!-- 窗口控制按钮 -->
    <button 
      class="h-7 w-10 flex items-center justify-center hover:bg-muted transition-colors"
      onclick={minimizeWindow}
      title="最小化"
    >
      <Minus class="w-4 h-4" />
    </button>
    <button 
      class="h-7 w-10 flex items-center justify-center hover:bg-muted transition-colors"
      onclick={toggleMaximize}
      title="最大化"
    >
      <MaxIcon class="w-3.5 h-3.5" />
    </button>
    <button 
      class="h-7 w-10 flex items-center justify-center hover:bg-destructive hover:text-destructive-foreground transition-colors"
      onclick={closeWindow}
      title="关闭"
    >
      <CloseIcon class="w-4 h-4" />
    </button>
  </div>
</div>

<!-- 背景图设置展开栏 -->
{#if showBgBar}
  <div class="h-9 border-b flex items-center gap-3 px-4" style={toolbarStyle}>
    <span class="text-xs text-muted-foreground">背景</span>
    <Button variant="outline" size="sm" class="h-6 text-xs" onclick={uploadBackground}>
      <FileUp class="w-3 h-3 mr-1" />
      上传
    </Button>
    {#if $themeStore.backgroundImage}
      <Button variant="ghost" size="sm" class="h-6 text-xs text-destructive" onclick={clearBackground}>
        <X class="w-3 h-3 mr-1" />
        清除
      </Button>
      <div class="flex items-center gap-2">
        <span class="text-xs text-muted-foreground">透明度</span>
        <input
          type="range"
          min="0"
          max="100"
          value={$themeStore.backgroundOpacity}
          oninput={(e) => themeStore.setBackgroundOpacity(parseInt(e.currentTarget.value))}
          class="w-24 h-1.5 accent-primary cursor-pointer"
        />
        <span class="text-xs w-8">{$themeStore.backgroundOpacity}%</span>
      </div>
    {/if}
  </div>
{/if}
</div>

<!-- 流程管理弹窗 -->
{#if showFlowManager}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="fixed inset-0 z-[200] bg-black/50" onclick={closeFlowManager}></div>
  <div class="fixed top-12 left-4 z-[201] w-80 bg-card border rounded-lg shadow-xl">
    <div class="p-3 border-b flex items-center justify-between">
      <span class="font-medium">流程列表</span>
      <Button variant="outline" size="sm" onclick={createNewFlow}>新建</Button>
    </div>
    <div class="max-h-80 overflow-y-auto">
      {#if flows.length === 0}
        <div class="p-4 text-center text-muted-foreground text-sm">暂无保存的流程</div>
      {:else}
        {#each flows as flow}
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div 
            class="p-3 hover:bg-muted cursor-pointer flex items-center justify-between group"
            onclick={() => selectFlow(flow.id)}
          >
            <div>
              <div class="font-medium text-sm">{flow.name || '未命名'}</div>
              <div class="text-xs text-muted-foreground">
                {new Date(flow.updatedAt).toLocaleString('zh-CN')}
              </div>
            </div>
            <button
              class="opacity-0 group-hover:opacity-100 p-1 hover:text-destructive transition-all"
              onclick={(e) => deleteFlow(flow.id, e)}
            >
              <X class="w-4 h-4" />
            </button>
          </div>
        {/each}
      {/if}
    </div>
  </div>
{/if}
