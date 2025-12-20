<script lang="ts">
  import { page } from '$app/state';
  import { onMount } from 'svelte';
  import { flowStore, taskStore } from '$lib/stores';
  import { api } from '$lib/services/api';
  import FlowCanvas from '$lib/components/flow/FlowCanvas.svelte';
  import TitleBar from '$lib/components/flow/TitleBar.svelte';
  import AutoHideTitleBar from '$lib/components/layout/AutoHideTitleBar.svelte';
  import FloatingPalette from '$lib/components/flow/FloatingPalette.svelte';
  import LogViewer from '$lib/components/execution/LogViewer.svelte';
  import { themeStore } from '$lib/stores/theme.svelte';
  import { fullscreenNodeStore } from '$lib/stores/fullscreenNode.svelte';
  import { getNodeTypes } from '$lib/stores/nodeRegistry';

  const flowId = $derived(page.params.id);
  
  // 自动隐藏标题栏引用
  let autoHideTitleBar: AutoHideTitleBar;
  
  // 获取全屏节点的信息
  let fullscreenNode = $derived(
    $fullscreenNodeStore.isOpen && $fullscreenNodeStore.nodeId
      ? $flowStore.nodes.find(n => n.id === $fullscreenNodeStore.nodeId)
      : null
  );
  
  // 获取节点类型组件
  const nodeTypes = getNodeTypes();

  onMount(() => {
    if (flowId && flowId !== 'new') {
      // 从 URL 加载指定流程
      api.getFlow(flowId)
        .then(flow => {
          flowStore.load(flow);
          localStorage.setItem('aestivus_last_flow', flowId);
        })
        .catch(e => console.error('加载流程失败:', e));
    } else {
      // 尝试加载上次使用的流程
      const lastFlowId = localStorage.getItem('aestivus_last_flow');
      if (lastFlowId) {
        api.getFlow(lastFlowId)
          .then(flow => flowStore.load(flow))
          .catch(() => {
            // 上次的流程不存在了，清除记忆
            localStorage.removeItem('aestivus_last_flow');
            flowStore.reset();
          });
      } else {
        flowStore.reset();
      }
    }

    return () => {
      flowStore.reset();
      taskStore.reset();
    };
  });
  
  // ESC 键退出全屏
  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape' && $fullscreenNodeStore.isOpen) {
      fullscreenNodeStore.close();
    }
  }
</script>

<svelte:window onkeydown={handleKeyDown} />

<div class="h-full flex flex-col relative">
  <!-- 背景图层 - 覆盖整个页面 -->
  {#if $themeStore.backgroundImage}
    <div 
      class="absolute inset-0 bg-cover bg-center bg-no-repeat pointer-events-none z-0"
      style="background-image: url({$themeStore.backgroundImage}); opacity: {$themeStore.backgroundOpacity / 100};"
    ></div>
  {:else}
    <div class="absolute inset-0 bg-background pointer-events-none z-0"></div>
  {/if}

  <!-- 顶部标题栏 - 自动隐藏，悬停唤出，支持 pin -->
  <AutoHideTitleBar bind:this={autoHideTitleBar}>
    <TitleBar onTogglePin={() => autoHideTitleBar?.togglePin()} />
  </AutoHideTitleBar>

  <!-- 画布区域 -->
  <div class="flex-1 relative z-[1]">
    <FlowCanvas />
  </div>

  <!-- 浮动面板 -->
  <FloatingPalette />

  <!-- 日志面板 -->
  {#if $taskStore.status !== 'idle' || $taskStore.logs.length > 0}
    <div class="absolute bottom-0 left-0 right-0 h-64 bg-card/95 backdrop-blur border-t">
      <LogViewer />
    </div>
  {/if}

</div>

<!-- 全屏节点容器（在 xyflow 外部渲染） -->
{#if fullscreenNode && fullscreenNode.type && nodeTypes[fullscreenNode.type]}
  {@const FullscreenComponent = nodeTypes[fullscreenNode.type]}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div 
    class="fixed inset-0 z-[100]"
    onclick={() => fullscreenNodeStore.close()}
  >
    <!-- 全屏背景图 -->
    {#if $themeStore.backgroundImage}
      <div 
        class="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style="background-image: url({$themeStore.backgroundImage}); opacity: {$themeStore.backgroundOpacity / 100};"
      ></div>
    {/if}
    <!-- 半透明遮罩 -->
    <div class="absolute inset-0 bg-background/40 backdrop-blur-sm"></div>
  </div>
  <div class="fixed inset-4 z-[101] flex flex-col">
    <FullscreenComponent 
      id={fullscreenNode.id} 
      data={fullscreenNode.data}
      isFullscreenRender={true}
    />
  </div>
{/if}
