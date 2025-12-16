<script lang="ts">
  /**
   * StatsBlock - 统计信息区块
   */
  import { FilePenLine } from '@lucide/svelte';

  interface Props {
    isFullscreen?: boolean;
    total: number;
    pending: number;
    ready: number;
    conflicts: number;
  }

  let {
    isFullscreen = false,
    total,
    pending,
    ready,
    conflicts
  }: Props = $props();
</script>

{#if isFullscreen}
  <!-- 全屏模式 -->
  <div class="h-full flex flex-col p-2">
    <div class="flex items-center gap-2 mb-3">
      <FilePenLine class="w-5 h-5 text-blue-500" />
      <span class="font-semibold">统计</span>
    </div>
    <div class="space-y-2 flex-1">
      <div class="flex items-center justify-between p-2 bg-muted/50 rounded-lg">
        <span class="text-sm">总计</span>
        <span class="text-xl font-bold">{total}</span>
      </div>
      <div class="flex items-center justify-between p-2 bg-yellow-500/10 rounded-lg">
        <span class="text-sm">待翻译</span>
        <span class="text-xl font-bold text-yellow-600">{pending}</span>
      </div>
      <div class="flex items-center justify-between p-2 bg-green-500/10 rounded-lg">
        <span class="text-sm">就绪</span>
        <span class="text-xl font-bold text-green-600">{ready}</span>
      </div>
      {#if conflicts > 0}
        <div class="flex items-center justify-between p-2 bg-red-500/10 rounded-lg">
          <span class="text-sm">冲突</span>
          <span class="text-xl font-bold text-red-600">{conflicts}</span>
        </div>
      {/if}
    </div>
  </div>
{:else}
  <!-- 普通模式 -->
  <div class="flex items-center gap-1.5 mb-2">
    <FilePenLine class="w-4 h-4 text-yellow-500" />
    <span class="text-xs font-semibold">统计</span>
  </div>
  <div class="grid grid-cols-3 gap-1 text-xs">
    <div class="text-center p-1.5 bg-muted/50 rounded-lg">
      <div class="font-bold">{total}</div>
      <div class="text-muted-foreground text-[10px]">总计</div>
    </div>
    <div class="text-center p-1.5 bg-yellow-500/10 rounded-lg">
      <div class="font-bold text-yellow-600">{pending}</div>
      <div class="text-muted-foreground text-[10px]">待翻译</div>
    </div>
    <div class="text-center p-1.5 bg-green-500/10 rounded-lg">
      <div class="font-bold text-green-600">{ready}</div>
      <div class="text-muted-foreground text-[10px]">就绪</div>
    </div>
  </div>
{/if}
