<script lang="ts">
  /**
   * DashboardItem - gridstack 网格项包装组件
   * 用于包装每个可拖拽的卡片内容
   */
  import type { Snippet } from 'svelte';

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
    class: className = '',
    children
  }: Props = $props();
</script>

<!-- gridstack 使用 gs-* 属性，需要用 {...} 展开来绕过类型检查 -->
<div
  class="grid-stack-item {className}"
  {...{
    'gs-id': id,
    'gs-x': x,
    'gs-y': y,
    'gs-w': w,
    'gs-h': h,
    'gs-min-w': minW,
    'gs-min-h': minH,
    'gs-max-w': maxW,
    'gs-max-h': maxH,
    'gs-no-resize': noResize || undefined,
    'gs-no-move': noMove || undefined
  }}
>
  <div class="grid-stack-item-content p-4">
    {#if children}
      {@render children()}
    {/if}
  </div>
</div>
