<script lang="ts">
  import { page } from '$app/state';
  import { onMount } from 'svelte';
  import { flowStore, taskStore } from '$lib/stores';
  import { api } from '$lib/services/api';
  import FlowCanvas from '$lib/components/flow/FlowCanvas.svelte';
  import FloatingToolbar from '$lib/components/flow/FloatingToolbar.svelte';
  import FloatingPalette from '$lib/components/flow/FloatingPalette.svelte';
  import LogViewer from '$lib/components/execution/LogViewer.svelte';

  const flowId = $derived(page.params.id);

  onMount(() => {
    if (flowId && flowId !== 'new') {
      api.getFlow(flowId)
        .then(flow => flowStore.load(flow))
        .catch(e => console.error('加载流程失败:', e));
    } else {
      flowStore.reset();
    }

    return () => {
      flowStore.reset();
      taskStore.reset();
    };
  });
</script>

<div class="h-full flex flex-col bg-background relative">
  <!-- 全屏画布 -->
  <div class="flex-1">
    <FlowCanvas />
  </div>

  <!-- 浮动面板 -->
  <FloatingToolbar />
  <FloatingPalette />

  <!-- 日志面板 -->
  {#if $taskStore.status !== 'idle' || $taskStore.logs.length > 0}
    <div class="absolute bottom-0 left-0 right-0 h-64 bg-card/95 backdrop-blur border-t">
      <LogViewer />
    </div>
  {/if}
</div>
