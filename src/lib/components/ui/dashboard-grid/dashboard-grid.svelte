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



<div class="dashboard-container">
  {#if showToolbar}
    <div class="dashboard-toolbar">
      <button class="toolbar-btn" onclick={compact} title="整理布局">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
        </svg>
        <span>整理</span>
      </button>
      {#if onReset}
        <button class="toolbar-btn" onclick={onReset} title="重置布局">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>
          </svg>
          <span>重置</span>
        </button>
      {/if}
    </div>
  {/if}
  
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
  
  .dashboard-toolbar {
    display: flex;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    border-bottom: 1px solid hsl(var(--border));
    background: hsl(var(--muted) / 0.3);
    flex-shrink: 0;
  }
  
  .toolbar-btn {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.375rem 0.75rem;
    font-size: 0.75rem;
    color: hsl(var(--muted-foreground));
    background: hsl(var(--background));
    border: 1px solid hsl(var(--border));
    border-radius: 0.5rem;
    cursor: pointer;
    transition: all 0.15s;
  }
  
  .toolbar-btn:hover {
    color: hsl(var(--foreground));
    border-color: hsl(var(--primary) / 0.5);
    background: hsl(var(--muted) / 0.5);
  }

  .dashboard-grid {
    width: 100%;
    flex: 1;
    overflow: auto;
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
