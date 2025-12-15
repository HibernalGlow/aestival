<script lang="ts">
  import { page } from '$app/state';
  import { onMount } from 'svelte';
  import { flowStore, taskStore } from '$lib/stores';
  import { api } from '$lib/services/api';
  import FlowCanvas from '$lib/components/flow/FlowCanvas.svelte';
  import FlowToolbar from '$lib/components/flow/FlowToolbar.svelte';
  import NodePalette from '$lib/components/flow/NodePalette.svelte';
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

<div class="h-full flex flex-col bg-background">
  <FlowToolbar />

  <div class="flex-1 flex overflow-hidden">
    <NodePalette />

    <div class="flex-1 flex flex-col">
      <div class="flex-1">
        <FlowCanvas />
      </div>

      {#if $taskStore.status !== 'idle' || $taskStore.logs.length > 0}
        <div class="h-64 border-t">
          <LogViewer />
        </div>
      {/if}
    </div>
  </div>
</div>
