<script lang="ts">
  /**
   * DashboardItem - gridstack 网格项包装组件
   */
  import type { Snippet } from "svelte";

  interface Props {
    id: string;
    x?: number;
    y?: number;
    w?: number;
    h?: number;
    minW?: number;
    minH?: number;
    maxW?: number;
    maxH?: number;
    noResize?: boolean;
    noMove?: boolean;
    class?: string;
    children?: Snippet;
  }

  let {
    id,
    x = 0,
    y = 0,
    w = 1,
    h = 1,
    minW,
    minH,
    maxW,
    maxH,
    noResize = false,
    noMove = false,
    class: className = "",
    children,
  }: Props = $props();
</script>

<div
  class="grid-stack-item {className}"
  gs-id={id}
  gs-x={x}
  gs-y={y}
  gs-w={w}
  gs-h={h}
  gs-min-w={minW}
  gs-min-h={minH}
  gs-max-w={maxW}
  gs-max-h={maxH}
  gs-no-resize={noResize || undefined}
  gs-no-move={noMove || undefined}
>
  <div class="grid-stack-item-content">
    {#if children}
      {@render children()}
    {/if}
  </div>
</div>

<style>
  /* 被 Tab 分组隐藏的区块 - 完全不可见但保留在 GridStack 中 */
  :global(.grid-stack-item.hidden-by-tab) {
    visibility: hidden !important;
    pointer-events: none !important;
  }
</style>
