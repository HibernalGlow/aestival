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
  import { onMount, onDestroy, tick } from "svelte";
  import { GridStack } from "gridstack";
  import "gridstack/dist/gridstack.min.css";
  import type { Snippet } from "svelte";

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
    children,
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
  export function updateItem(
    id: string,
    x: number,
    y: number,
    w: number,
    h: number
  ) {
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
      const el = gridElement.querySelector(
        `[gs-id="${item.id}"]`
      ) as HTMLElement;
      if (el) {
        grid.update(el, { x: item.x, y: item.y, w: item.w, h: item.h });
      }
    }

    grid.batchUpdate(false);
    handleLayoutChange();
  }

  /** 刷新网格 - 重新扫描并同步所有元素位置（用于动态添加/删除元素后） */
  export async function refresh() {
    if (!grid || !gridElement) return;

    // 等待 DOM 更新
    await tick();

    const currentGridItems = grid.getGridItems();
    const allDomItems = Array.from(
      gridElement.querySelectorAll(".grid-stack-item")
    ) as HTMLElement[];

    // 构建 ID -> 元素 映射
    const managedMap = new Map<string, HTMLElement>();
    for (const el of currentGridItems) {
      const node = (el as any).gridstackNode;
      const id = node?.id || el.getAttribute("gs-id");
      if (id) managedMap.set(id, el);
    }

    const domMap = new Map<string, HTMLElement>();
    for (const el of allDomItems) {
      const id = el.getAttribute("gs-id");
      if (id) domMap.set(id, el);
    }

    // 1. 清理失效节点（在 GridStack 中但不在 DOM 中）
    const toRemove: HTMLElement[] = [];
    for (const [id, el] of managedMap) {
      if (!domMap.has(id)) {
        toRemove.push(el);
      }
    }

    // 2. 找出需要注册的新元素（在 DOM 中但不在 GridStack 中）
    const toAdd: HTMLElement[] = [];
    for (const [id, el] of domMap) {
      if (!managedMap.has(id)) {
        toAdd.push(el);
      }
    }

    // 3. 找出位置不同步的元素（在两边都存在，但位置不一致或 DOM 元素不同）
    // 注意：需要同时保存 managedEl（用于移除）和 domEl（用于重新添加）
    const toSync: { managedEl: HTMLElement; domEl: HTMLElement; x: number; y: number; w: number; h: number }[] = [];
    for (const [id, domEl] of domMap) {
      const managedEl = managedMap.get(id);
      if (managedEl) {
        const node = (managedEl as any).gridstackNode;
        const domX = parseInt(domEl.getAttribute("gs-x") || "0");
        const domY = parseInt(domEl.getAttribute("gs-y") || "0");
        const domW = parseInt(domEl.getAttribute("gs-w") || "1");
        const domH = parseInt(domEl.getAttribute("gs-h") || "1");
        // 从 GridStack node 获取正确的位置（这是 ground truth）
        const nodeX = node?.x ?? domX;
        const nodeY = node?.y ?? domY;
        const nodeW = node?.w ?? domW;
        const nodeH = node?.h ?? domH;

        // 检查位置是否不一致，或者 DOM 元素是否不同（Svelte 可能创建了新元素）
        if (domX !== nodeX || domY !== nodeY || domW !== nodeW || domH !== nodeH || managedEl !== domEl) {
          // 使用 GridStack node 的位置（正确的位置），而不是 DOM 属性
          toSync.push({ managedEl, domEl, x: nodeX, y: nodeY, w: nodeW, h: nodeH });
        }
      }
    }

    console.log("[DashboardGrid] refresh - 详细状态:", {
      managedIds: Array.from(managedMap.keys()).sort(),
      domIds: Array.from(domMap.keys()).sort(),
      managedCount: managedMap.size,
      domCount: domMap.size,
    });
    
    console.log("[DashboardGrid] refresh - 操作:", {
      toRemove: toRemove.map(el => el.getAttribute("gs-id")),
      toAdd: toAdd.map(el => el.getAttribute("gs-id")),
      toSync: toSync.map(item => ({ id: item.domEl.getAttribute("gs-id"), x: item.x, y: item.y, sameEl: item.managedEl === item.domEl })),
    });

    if (toRemove.length === 0 && toAdd.length === 0 && toSync.length === 0) {
      console.log("[DashboardGrid] refresh - 无需更新");
      return;
    }

    try {
      grid.batchUpdate();

      // 移除失效节点
      for (const el of toRemove) {
        const id = el.getAttribute("gs-id");
        console.log("[DashboardGrid] refresh - 移除失效节点:", { id });
        grid.removeWidget(el, true); // 使用 true 完全移除，包括 DOM
      }

      // 注册新节点 - GridStack V11 使用 makeWidget 而非 addWidget
      for (const el of toAdd) {
        const id = el.getAttribute("gs-id");
        const x = parseInt(el.getAttribute("gs-x") || "0");
        const y = parseInt(el.getAttribute("gs-y") || "0");
        const w = parseInt(el.getAttribute("gs-w") || "1");
        const h = parseInt(el.getAttribute("gs-h") || "1");
        const minW = el.getAttribute("gs-min-w") ? parseInt(el.getAttribute("gs-min-w")!) : undefined;
        const minH = el.getAttribute("gs-min-h") ? parseInt(el.getAttribute("gs-min-h")!) : undefined;

        console.log("[DashboardGrid] refresh - 注册新元素:", { id, x, y, w, h });
        
        // GridStack V11: 先设置 DOM 属性，再用 makeWidget 注册
        el.setAttribute("gs-x", String(x));
        el.setAttribute("gs-y", String(y));
        el.setAttribute("gs-w", String(w));
        el.setAttribute("gs-h", String(h));
        if (minW !== undefined) el.setAttribute("gs-min-w", String(minW));
        if (minH !== undefined) el.setAttribute("gs-min-h", String(minH));
        
        grid.makeWidget(el);
        grid.update(el, { x, y, w, h, minW, minH });
        grid.movable(el, true);
        grid.resizable(el, true);
      }

      // 同步位置不一致的元素 - 需要先移除旧元素
      for (const { managedEl, domEl, x, y, w, h } of toSync) {
        const id = managedEl.getAttribute("gs-id");
        const sameElement = managedEl === domEl;
        console.log("[DashboardGrid] refresh - 移除旧元素:", { id, x, y, w, h, sameElement });
        
        // 从 GridStack 移除旧元素
        // 如果 managedEl 和 domEl 是不同的元素，需要完全移除旧元素（包括 DOM）
        grid.removeWidget(managedEl, !sameElement);
      }
    } finally {
      grid.batchUpdate(false);
    }

    // 在 batchUpdate 之外重新添加需要同步的元素（使用新的 DOM 元素）
    if (toSync.length > 0) {
      await tick();
      
      for (const { domEl, x, y, w, h } of toSync) {
        const id = domEl.getAttribute("gs-id");
        const minW = domEl.getAttribute("gs-min-w") ? parseInt(domEl.getAttribute("gs-min-w")!) : undefined;
        const minH = domEl.getAttribute("gs-min-h") ? parseInt(domEl.getAttribute("gs-min-h")!) : undefined;
        
        console.log("[DashboardGrid] refresh - 重新添加元素:", { id, x, y, w, h });
        
        // GridStack V11: 先设置 DOM 属性，再用 makeWidget 注册
        domEl.setAttribute("gs-x", String(x));
        domEl.setAttribute("gs-y", String(y));
        domEl.setAttribute("gs-w", String(w));
        domEl.setAttribute("gs-h", String(h));
        if (minW !== undefined) domEl.setAttribute("gs-min-w", String(minW));
        if (minH !== undefined) domEl.setAttribute("gs-min-h", String(minH));
        
        grid.makeWidget(domEl);
        grid.update(domEl, { x, y, w, h, minW, minH });
        grid.movable(domEl, true);
        grid.resizable(domEl, true);
      }
    }

    grid.enable();
    console.log("[DashboardGrid] refresh - 完成");
  }

  // 从 DOM 元素获取当前布局（优先从 GridStack node 获取，同步更准确）
  function getCurrentLayout(): GridItem[] {
    if (!grid) return [];
    return grid.getGridItems().map((el) => {
      const node = (el as any).gridstackNode;
      // 优先从 node 对象获取，因为它是 Ground Truth
      const id = el.getAttribute("gs-id") || node?.id || "";
      const x = node?.x ?? parseInt(el.getAttribute("gs-x") || "0");
      const y = node?.y ?? parseInt(el.getAttribute("gs-y") || "0");
      const w = node?.w ?? parseInt(el.getAttribute("gs-w") || "1");
      const h = node?.h ?? parseInt(el.getAttribute("gs-h") || "1");

      return {
        id,
        x,
        y,
        w,
        h,
        minW: node?.minW,
        minH: node?.minH,
        maxW: node?.maxW,
        maxH: node?.maxH,
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
    grid = GridStack.init(
      {
        column: columns,
        cellHeight: cellHeight,
        // margin 格式: 'top right bottom left' 或单个值
        margin: `${margin}px`,
        float: float,
        disableDrag: disableDrag,
        disableResize: disableResize,
        animate: true,
        resizable: { handles: "se,sw,ne,nw,e,w,n,s" },
      },
      gridElement
    );

    // 监听布局变化事件
    grid.on("change", handleLayoutChange);
    grid.on("resizestop", handleLayoutChange);
    grid.on("dragstop", handleLayoutChange);
  });

  // 提供 context 给子组件
  import { setContext } from "svelte";
  setContext("dashboard-grid", {
    updateItem: (id: string, x: number, y: number, w: number, h: number) => {
      if (!grid) return;
      const el = gridElement?.querySelector(`[gs-id="${id}"]`) as HTMLElement;
      if (el) {
        grid.update(el, { x, y, w, h });
        handleLayoutChange();
      }
    },
  });

  onDestroy(() => {
    if (grid) {
      grid.off("change");
      grid.off("resizestop");
      grid.off("dragstop");
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
