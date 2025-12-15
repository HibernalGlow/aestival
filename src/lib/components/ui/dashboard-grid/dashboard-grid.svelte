<script lang="ts" module>
  /**
   * GridItem 类型定义 - 网格项配置
   */
  export interface GridItem {
    id: string;
    x: number;
    y: number;
    w: number;
    h: number;
    minW?: number;
    minH?: number;
    maxW?: number;
    maxH?: number;
    noResize?: boolean;
    noMove?: boolean;
  }
</script>

<script lang="ts">
  /**
   * DashboardGrid - 基于 gridstack.js 的可拖拽网格布局
   * 支持拖拽移动、调整大小、布局持久化
   * 兼容 Svelte 5 runes
   */
  import { onMount, onDestroy, tick } from 'svelte';
  import { GridStack } from 'gridstack';
  import type { Snippet } from 'svelte';

  interface Props {
    items?: GridItem[];
    columns?: number;
    cellHeight?: number;
    margin?: number;
    float?: boolean;
    disableDrag?: boolean;
    disableResize?: boolean;
    onLayoutChange?: (items: GridItem[]) => void;
    children?: Snippet;
  }

  let {
    items = $bindable([]),
    columns = 4,
    cellHeight = 80,
    margin = 12,
    float = true,
    disableDrag = false,
    disableResize = false,
    onLayoutChange,
    children
  }: Props = $props();

  let gridElement: HTMLDivElement | undefined = $state();
  let grid: GridStack | null = null;

  // 从 DOM 元素获取当前布局
  function getCurrentLayout(): GridItem[] {
    if (!grid) return [];
    return grid.getGridItems().map((el) => {
      const node = el.gridstackNode;
      return {
        id: node?.id || el.getAttribute('gs-id') || '',
        x: node?.x ?? 0,
        y: node?.y ?? 0,
        w: node?.w ?? 1,
        h: node?.h ?? 1,
        minW: node?.minW,
        minH: node?.minH,
        maxW: node?.maxW,
        maxH: node?.maxH
      };
    });
  }

  // 处理布局变化
  function handleLayoutChange() {
    if (!grid || !onLayoutChange) return;
    const newLayout = getCurrentLayout();
    onLayoutChange(newLayout);
  }

  onMount(async () => {
    if (!gridElement) return;
    
    // 等待 DOM 渲染完成
    await tick();

    // 初始化 GridStack
    grid = GridStack.init({
      column: columns,
      cellHeight: cellHeight,
      margin: margin,
      float: float,
      disableDrag: disableDrag,
      disableResize: disableResize,
      animate: true,
      resizable: { handles: 'se,sw,ne,nw,e,w,n,s' }
    }, gridElement);

    // 监听布局变化事件
    grid.on('change', handleLayoutChange);
    grid.on('resizestop', handleLayoutChange);
    grid.on('dragstop', handleLayoutChange);
  });

  onDestroy(() => {
    if (grid) {
      grid.off('change');
      grid.off('resizestop');
      grid.off('dragstop');
      grid.destroy(false);
      grid = null;
    }
  });
</script>

<svelte:head>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gridstack@12/dist/gridstack.min.css" />
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gridstack@12/dist/gridstack-extra.min.css" />
</svelte:head>

<div bind:this={gridElement} class="grid-stack dashboard-grid">
  {#if children}
    {@render children()}
  {/if}
</div>

<style>
  .dashboard-grid {
    width: 100%;
    min-height: 100%;
  }

  :global(.grid-stack > .grid-stack-item > .grid-stack-item-content) {
    background: hsl(var(--card));
    border: 1px solid hsl(var(--border));
    border-radius: 1.5rem;
    overflow: auto;
    inset: 6px;
  }

  :global(.grid-stack-item) {
    cursor: grab;
  }

  :global(.grid-stack-item:active) {
    cursor: grabbing;
  }

  :global(.grid-stack-placeholder > .placeholder-content) {
    background: hsl(var(--primary) / 0.1);
    border: 2px dashed hsl(var(--primary) / 0.5);
    border-radius: 1.5rem;
  }

  :global(.ui-resizable-handle) {
    opacity: 0;
    transition: opacity 0.2s;
  }

  :global(.grid-stack-item:hover .ui-resizable-handle) {
    opacity: 0.6;
  }

  :global(.ui-resizable-se) {
    width: 16px;
    height: 16px;
    right: 8px;
    bottom: 8px;
    background: hsl(var(--muted-foreground) / 0.4);
    border-radius: 4px;
  }
</style>
