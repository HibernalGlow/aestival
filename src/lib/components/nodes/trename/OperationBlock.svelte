<script lang="ts">
  /**
   * OperationBlock - 操作按钮区块
   */
  import { Button } from '$lib/components/ui/button';
  import { Play, Search, Trash2, LoaderCircle } from '@lucide/svelte';
  import type { Phase } from '../trename-utils';

  interface Props {
    isFullscreen?: boolean;
    phase: Phase;
    isRunning: boolean;
    canRename: boolean;
    hasSegments: boolean;
    hasScanPath: boolean;
    onValidate: () => void;
    onRename: () => void;
    onClear: () => void;
    onScan: () => void;
  }

  let {
    isFullscreen = false,
    phase,
    isRunning,
    canRename,
    hasSegments,
    hasScanPath,
    onValidate,
    onRename,
    onClear,
    onScan
  }: Props = $props();
</script>

{#if isFullscreen}
  <!-- 全屏模式 -->
  <div class="h-full flex flex-col p-2">
    <div class="flex items-center gap-2 mb-3">
      <Play class="w-5 h-5 text-green-500" />
      <span class="font-semibold">操作</span>
    </div>
    <div class="flex flex-col gap-2 flex-1 justify-center">
      <Button variant="outline" class="h-12" onclick={onValidate} disabled={isRunning || !hasSegments}>
        <Search class="h-4 w-4 mr-2" />检测冲突
      </Button>
      <Button variant={canRename ? 'default' : 'outline'} class="h-12" onclick={onRename} disabled={isRunning || !canRename}>
        {#if phase === 'renaming'}<LoaderCircle class="h-4 w-4 mr-2 animate-spin" />{:else}<Play class="h-4 w-4 mr-2" />{/if}执行重命名
      </Button>
      <Button variant="ghost" class="h-10" onclick={onClear}>
        <Trash2 class="h-4 w-4 mr-2" />清空
      </Button>
    </div>
  </div>
{:else}
  <!-- 普通模式 -->
  <div class="flex items-center gap-1.5 mb-2">
    <Play class="w-4 h-4 text-green-500" />
    <span class="text-xs font-semibold">操作</span>
  </div>
  <div class="flex-1 flex flex-col gap-1.5">
    {#if phase === 'idle' || phase === 'error'}
      <Button class="flex-1 h-8 text-xs" onclick={onScan} disabled={!hasScanPath}>
        <Search class="h-3 w-3 mr-1" />扫描
      </Button>
    {:else if phase === 'scanning'}
      <Button class="flex-1 h-8 text-xs" disabled>
        <LoaderCircle class="h-3 w-3 mr-1 animate-spin" />扫描中
      </Button>
    {:else if phase === 'ready' || phase === 'completed'}
      <Button class="flex-1 h-8 text-xs" onclick={onRename} disabled={!canRename}>
        <Play class="h-3 w-3 mr-1" />执行
      </Button>
      <Button variant="outline" class="h-6 text-xs" onclick={onClear}>重置</Button>
    {:else if phase === 'renaming'}
      <Button class="flex-1 h-8 text-xs" disabled>
        <LoaderCircle class="h-3 w-3 mr-1 animate-spin" />执行中
      </Button>
    {/if}
  </div>
{/if}
