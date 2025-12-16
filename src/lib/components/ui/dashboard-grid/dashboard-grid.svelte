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
   * 支持拖拽移动、调整大小、布局持久化、自动整理
   * 兼容 Svelte 5 runes
   */
  import { onMount, onDestroy, tick } from 'svelte';
  import { GridStack } from 'gridstack';
  import 'gridstack/dist/gridstack.min.css';
  import type { Snippet } from 'svelte';

  interface Props {
    items?: GridItem[];
    columns?: number;
    cellHeight?: number;
    margin?: number;
    float?: boolean;
    disableDrag?: boolean;
    disableResize?: boolean;
    showToolbar?: boolean;
    onLayoutChange?: (items: GridItem[]) => void;
    onReset?: () => void;
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
    showToolbar = true,
    onLayoutChange,
    onReset,
    children
  }: Props = $props();

  let gridElement: HTMLDivElement | undefined = $state();
  let grid: GridStack | null = null;
  
  /** 整理布局 - 消除空隙 */
  export function compact() {
    if (!grid) return;
    grid.compact();
    handleLayoutChange();
  }
  
  /** 锁定/解锁布局 */
  export function setLocked(locked: boolean) {
    if (!grid) return;
    if (locked) {
      grid.disable();
    } else {
      grid.enable();
    }
  }

  /** 更新单个 item 的布局 */
  export function updateItem(id: string, x: number, y: number, w: number, h: number) {
    if (!grid) return;
    const el = gridElement?.querySelector(`[gs-id="${id}"]`) as HTMLElement;
    if (el) {
      grid.update(el, { x, y, w, h });
      handleLayoutChange();
    }
  }

  /** 批量应用布局 - 用于切换预设 */
  export function applyLayout(newLayout: GridItem[]) {
    if (!grid || !gridElement) return;
    
    // 批量更新模式，避免触发多次事件
    grid.batchUpdate();
    
    for (const item of newLayout) {
      const el = gridElement.querySelector(`[gs-id="${item.id}"]`) as HTMLElement;
      if (el) {
        grid.update(el, { x: item.x, y: item.y, w: item.w, h: item.h });
      }
    }
    
    grid.batchUpdate(false);
    handleLayoutChange();
  }

  // 从 DOM 元素获取当前布局（优先从 DOM 属性读取，确保 resize 后数据正确）
  function getCurrentLayout(): GridItem[] {
    if (!grid) return [];
    return grid.getGridItems().map((el) => {
      const node = el.gridstackNode;
      // 优先从 DOM 属性获取，因为 resize 后 node 对象可能未及时更新
      const id = el.getAttribute('gs-id') || node?.id || '';
      const x = parseInt(el.getAttribute('gs-x') || '') || (node?.x ?? 0);
      const y = parseInt(el.getAttribute('gs-y') || '') || (node?.y ?? 0);
      const w = parseInt(el.getAttribute('gs-w') || '') || (node?.w ?? 1);
      const h = parseInt(el.getAttribute('gs-h') || '') || (node?.h ?? 1);
      return {
        id,
        x,
        y,
        w,
        h,
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
      // margin 格式: 'top right bottom left' 或单个值
      margin: `${margin}px`,
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

  // 提供 context 给子组件
  import { setContext } from 'svelte';
  setContext('dashboard-grid', {
    updateItem: (id: string, x: number, y: number, w: number, h: number) => {
      if (!grid) return;
      const el = gridElement?.querySelector(`[gs-id="${id}"]`) as HTMLElement;
      if (el) {
        grid.update(el, { x, y, w, h });
        handleLayoutChange();
      }
    }
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



<div class="dashboard-container">
  <div bind:this={gridElement} class="grid-stack dashboard-grid">
    {#if children}
      {@render children()}
    {/if}
  </div>
</div>

<style>
  .dashboard-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
  }
  
  .dashboard-grid {
    width: 100%;
    flex: 1;
    overflow: auto;
  }

  :global(.grid-stack > .grid-stack-item > .grid-stack-item-content) {
    background: transparent;
    overflow: auto;
    /* 使用绝对定位 + inset 实现居中 */
    position: absolute;
    top: 4px;
    right: 4px;
    bottom: 4px;
    left: 4px;
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
    border-radius: 0.375rem;
  }

  :global(.ui-resizable-handle) {
    opacity: 0;
    transition: opacity 0.2s;
  }

  :global(.grid-stack-item:hover .ui-resizable-handle) {
    opacity: 0.6;
  }

  /* 四角 resize 手柄 - 小圆点 */
  :global(.ui-resizable-se) {
    width: 10px;
    height: 10px;
    right: 8px;
    bottom: 8px;
    background: hsl(var(--muted-foreground) / 0.5) !important;
    border-radius: 50%;
    cursor: se-resize !important;
  }

  :global(.ui-resizable-sw) {
    width: 10px;
    height: 10px;
    left: 8px;
    bottom: 8px;
    background: hsl(var(--muted-foreground) / 0.5) !important;
    border-radius: 50%;
    cursor: sw-resize !important;
  }

  :global(.ui-resizable-ne) {
    width: 10px;
    height: 10px;
    right: 8px;
    top: 8px;
    background: hsl(var(--muted-foreground) / 0.5) !important;
    border-radius: 50%;
    cursor: ne-resize !important;
  }

  :global(.ui-resizable-nw) {
    width: 10px;
    height: 10px;
    left: 8px;
    top: 8px;
    background: hsl(var(--muted-foreground) / 0.5) !important;
    border-radius: 50%;
    cursor: nw-resize !important;
  }

  /* 边缘 resize 手柄 - 小横条/竖条 */
  :global(.ui-resizable-n) {
    height: 6px;
    width: 30px;
    top: 6px;
    left: 50%;
    transform: translateX(-50%);
    background: hsl(var(--muted-foreground) / 0.4) !important;
    border-radius: 3px;
    cursor: n-resize !important;
  }

  :global(.ui-resizable-s) {
    height: 6px;
    width: 30px;
    bottom: 6px;
    left: 50%;
    transform: translateX(-50%);
    background: hsl(var(--muted-foreground) / 0.4) !important;
    border-radius: 3px;
    cursor: s-resize !important;
  }

  :global(.ui-resizable-e) {
    width: 6px;
    height: 30px;
    right: 6px;
    top: 50%;
    transform: translateY(-50%);
    background: hsl(var(--muted-foreground) / 0.4) !important;
    border-radius: 3px;
    cursor: e-resize !important;
  }

  :global(.ui-resizable-w) {
    width: 6px;
    height: 30px;
    left: 6px;
    top: 50%;
    transform: translateY(-50%);
    background: hsl(var(--muted-foreground) / 0.4) !important;
    border-radius: 3px;
    cursor: w-resize !important;
  }
</style>
