<script lang="ts">
  /**
   * BlockContainer - 区块容器
   * 根据 isFullscreen 自动选择渲染方式：
   * - 普通模式：简单的 grid 布局
   * - 全屏模式：GridStack 可拖拽布局
   */
  import { DashboardGrid, DashboardItem } from '$lib/components/ui/dashboard-grid';
  import type { GridItem } from '$lib/components/ui/dashboard-grid';
  import type { BlockDefinition } from './types';
  import { getNormalModeBlocks } from './types';
  import type { Snippet } from 'svelte';

  interface Props {
    /** 区块定义列表 */
    blocks: BlockDefinition[];
    /** 是否全屏模式 */
    isFullscreen?: boolean;
    /** 当前 GridStack 布局（全屏模式） */
    gridLayout?: GridItem[];
    /** 布局变化回调 */
    onLayoutChange?: (layout: GridItem[]) => void;
    /** 区块内容渲染器 */
    renderBlock: Snippet<[{ block: BlockDefinition; isFullscreen: boolean }]>;
  }

  let {
    blocks,
    isFullscreen = false,
    gridLayout = [],
    onLayoutChange,
    renderBlock
  }: Props = $props();

  // DashboardGrid 组件引用
  let dashboardGrid: { compact: () => void; applyLayout: (layout: GridItem[]) => void } | undefined;

  // 获取普通模式下的区块
  let normalBlocks = $derived(getNormalModeBlocks(blocks));

  // 根据 id 获取布局项
  function getLayoutItem(blockId: string): GridItem {
    const item = gridLayout.find(item => item.id === blockId);
    if (item) return item;
    // 从区块定义获取默认值
    const block = blocks.find(b => b.id === blockId);
    if (block) {
      return {
        id: blockId,
        x: block.fullscreenLayout.x,
        y: block.fullscreenLayout.y,
        w: block.fullscreenLayout.w,
        h: block.fullscreenLayout.h,
        minW: block.fullscreenLayout.minW,
        minH: block.fullscreenLayout.minH,
      };
    }
    return { id: blockId, x: 0, y: 0, w: 1, h: 1 };
  }

  /** 整理布局 */
  export function compact() {
    dashboardGrid?.compact();
  }

  /** 应用布局 */
  export function applyLayout(layout: GridItem[]) {
    dashboardGrid?.applyLayout(layout);
  }
</script>

{#if isFullscreen}
  <!-- 全屏模式：GridStack 可拖拽布局 -->
  <div class="h-full overflow-hidden">
    <DashboardGrid 
      bind:this={dashboardGrid}
      columns={4} 
      cellHeight={80} 
      margin={12}
      showToolbar={false}
      onLayoutChange={onLayoutChange}
    >
      {#each blocks as block}
        {@const layoutItem = getLayoutItem(block.id)}
        <DashboardItem 
          id={block.id} 
          x={layoutItem.x} 
          y={layoutItem.y} 
          w={layoutItem.w} 
          h={layoutItem.h} 
          minW={layoutItem.minW} 
          minH={layoutItem.minH}
        >
          {@render renderBlock({ block, isFullscreen: true })}
        </DashboardItem>
      {/each}
    </DashboardGrid>
  </div>
{:else}
  <!-- 普通模式：简单 grid 布局 -->
  <div class="flex-1 overflow-y-auto p-2">
    <div class="grid grid-cols-2 gap-2" style="grid-auto-rows: minmax(auto, max-content);">
      {#each normalBlocks as block}
        {@const colSpan = block.normalLayout.colSpan ?? 1}
        <div class="{colSpan === 2 ? 'col-span-2' : 'col-span-1'} bg-card rounded-2xl border p-3 shadow-sm">
          {@render renderBlock({ block, isFullscreen: false })}
        </div>
      {/each}
    </div>
  </div>
{/if}
