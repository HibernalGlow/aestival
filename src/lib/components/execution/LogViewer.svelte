<script lang="ts">
  import { taskStore, recentLogs } from '$lib/stores';
  import { Terminal, XCircle, CheckCircle2, Loader2 } from '@lucide/svelte';

  let logContainer: HTMLElement | undefined = $state();

  $effect(() => {
    if ($recentLogs.length && logContainer) {
      logContainer.scrollTop = logContainer.scrollHeight;
    }
  });

  const statusInfo = $derived({
    idle: { icon: Terminal, color: 'text-gray-500', label: '空闲' },
    running: { icon: Loader2, color: 'text-blue-500', label: '执行中' },
    completed: { icon: CheckCircle2, color: 'text-green-500', label: '完成' },
    failed: { icon: XCircle, color: 'text-red-500', label: '失败' },
    cancelled: { icon: XCircle, color: 'text-amber-500', label: '已取消' }
  }[$taskStore.status]);

  function clearLogs() {
    taskStore.reset();
  }
</script>

<div class="h-full flex flex-col bg-gray-900">
  <div class="flex items-center justify-between px-4 py-2 border-b border-gray-700">
    <div class="flex items-center gap-2">
      {#if $taskStore.status === 'running'}
        <Loader2 class="w-4 h-4 {statusInfo.color} animate-spin" />
      {:else if $taskStore.status === 'completed'}
        <CheckCircle2 class="w-4 h-4 {statusInfo.color}" />
      {:else if $taskStore.status === 'failed' || $taskStore.status === 'cancelled'}
        <XCircle class="w-4 h-4 {statusInfo.color}" />
      {:else}
        <Terminal class="w-4 h-4 {statusInfo.color}" />
      {/if}
      <span class="text-white font-medium text-sm">执行日志</span>
      <span class="text-xs {statusInfo.color}">{statusInfo.label}</span>
    </div>
    <button
      class="text-xs text-gray-400 hover:text-white transition-colors"
      onclick={clearLogs}
    >
      清空
    </button>
  </div>

  <div
    bind:this={logContainer}
    class="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-0.5"
  >
    {#each $recentLogs as log}
      <div class="flex">
        <span class="text-gray-500 w-24 flex-shrink-0">
          {new Date(log.timestamp).toLocaleTimeString()}
        </span>
        <span class="text-blue-400 w-24 flex-shrink-0 truncate" title={log.nodeId}>
          [{log.nodeId}]
        </span>
        <span
          class={log.type === 'stderr' || log.type === 'error'
            ? 'text-red-400'
            : log.type === 'info'
              ? 'text-cyan-400'
              : 'text-green-400'}
        >
          {log.content}
        </span>
      </div>
    {/each}

    {#if $recentLogs.length === 0}
      <div class="text-gray-500 text-center py-8">
        暂无日志，执行流程后将在此显示
      </div>
    {/if}
  </div>
</div>
