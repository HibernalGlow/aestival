<script lang="ts">
  /**
   * NodeLayoutRenderer - 统一节点布局渲染器
   * 处理节点模式和全屏模式的布局切换、Tab 管理、状态持久化
   * 节点组件只需提供内容 snippets，无需关心布局逻辑
   */
  import type { Snippet } from 'svelte';
  import type { GridItem } from '$lib/components/ui/dashboard-grid';
  import { DashboardGrid, DashboardItem } from '$lib/components/ui/dashboard-grid';
  import { BlockCard, TabBlockCard } from '$lib/components/blocks';
  import { 
    getBlockDefinition, 
    getNodeBlockLayout,
    type BlockDefinition
  } from './blockRegistry';
  import {
    getOrCreateNodeConfig,
    updateFullscreenGridLayout,
    updateNormalBlocks,
    updateTabState,
    createTabBlock,
    removeTabBlock,
    subscribeNodeConfig,
    type NodeConfig,
    type NormalBlockConfig,
    type BlockSizeOverride
  } from '$lib/stores/nodeLayoutStore';
  import { getSizeMode, type SizeMode } from '$lib/utils/sizeUtils';
  import { onMount } from 'svelte';

  interface Props {
    /** 节点 ID */
    nodeId: string;
    /** 节点类型（用于获取区块定义） */
    nodeType: string;
    /** 是否全屏模式 */
    isFullscreen: boolean;
    /** 默认 GridStack 布局（首次渲染时使用） */
    defaultGridLayout?: GridItem[];
    /** 区块内容渲染器 */
    renderBlock: Snippet<[blockId: string, size: SizeMode]>;
    /** 配置变化回调（可选） */
    onConfigChange?: (config: NodeConfig) => void;
  }

  let {
    nodeId,
    nodeType,
    isFullscreen,
    defaultGridLayout = [],
    renderBlock,
    onConfigChange
  }: Props = $props();

  // 当前模式
  let mode = $derived(isFullscreen ? 'fullscreen' : 'normal') as 'fullscreen' | 'normal';
  
  // 尺寸模式
  let sizeMode = $derived(getSizeMode(isFullscreen));

  // 节点配置 - 使用响应式订阅
  let nodeConfig = $state<NodeConfig>(
    getOrCreateNodeConfig(nodeId, nodeType, defaultGridLayout)
  );
  
  // 初始化时确保配置存在，并初始化节点模式区块配置
  $effect(() => {
    const config = getOrCreateNodeConfig(nodeId, nodeType, defaultGridLayout);
    
    // 如果节点模式区块配置为空，从 blockRegistry 初始化
    if (config.normal.blocks.length === 0) {
      const blockLayout = getNodeBlockLayout(nodeType);
      if (blockLayout) {
        const initialBlocks: NormalBlockConfig[] = blockLayout.blocks
          .filter(b => b.visibleInNormal !== false && !b.isTabContainer)
          .map((b, idx) => ({
            id: b.id,
            order: idx,
            visible: true
          }));
        updateNormalBlocks(nodeId, initialBlocks);
      }
    }
    
    nodeConfig = config;
  });
  
  // 订阅配置变化
  onMount(() => {
    const currentNodeId = nodeId;
    const unsubscribe = subscribeNodeConfig(currentNodeId, (config) => {
      if (config) {
        nodeConfig = config;
        onConfigChange?.(config);
      }
    });
    
    return unsubscribe;
  });

  // GridStack 布局（全屏模式）
  let gridLayout = $derived(nodeConfig.fullscreen.gridLayout);

  // DashboardGrid 引用
  let dashboardGrid = $state<{ compact: () => void; applyLayout: (layout: GridItem[]) => void } | undefined>(undefined);

  // 获取区块布局配置（代码默认）
  let blockLayout = $derived(getNodeBlockLayout(nodeType));
  
  // 获取已使用的 Tab 区块 ID
  let usedTabIds = $derived(() => {
    const ids: string[] = [];
    for (const tabState of Object.values(nodeConfig[mode].tabStates)) {
      ids.push(...tabState.children.slice(1));
    }
    return ids;
  });

  // 获取节点模式可见区块列表（从配置读取，支持持久化）
  let normalVisibleBlocks = $derived(() => {
    if (!blockLayout) return [];
    const usedIds = usedTabIds();
    
    // 如果有保存的配置，使用配置
    if (nodeConfig.normal.blocks.length > 0) {
      return nodeConfig.normal.blocks
        .filter(b => b.visible && !usedIds.includes(b.id))
        .sort((a, b) => a.order - b.order)
        .map(b => {
          const def = blockLayout!.blocks.find(d => d.id === b.id);
          if (!def) return null;
          // 合并尺寸覆盖
          return {
            ...def,
            colSpan: b.sizeOverride?.colSpan ?? def.colSpan
          } as BlockDefinition;
        })
        .filter((b): b is BlockDefinition => b !== null);
    }
    
    // 否则使用默认配置
    return blockLayout.blocks.filter(b => {
      if (usedIds.includes(b.id)) return false;
      if (b.isTabContainer) return false;
      return b.visibleInNormal !== false;
    });
  });

  // 获取全屏模式可见区块（从 gridLayout 读取）
  let fullscreenVisibleBlocks = $derived(() => {
    const usedIds = usedTabIds();
    return gridLayout.filter(item => !usedIds.includes(item.id));
  });

  // 处理 GridStack 布局变化
  function handleGridLayoutChange(newLayout: GridItem[]) {
    updateFullscreenGridLayout(nodeId, newLayout);
  }

  // 处理 Tab 状态变化
  function handleTabStateChange(tabId: string, state: { activeTab: number; children: string[] }) {
    updateTabState(nodeId, mode, tabId, state);
  }

  // 创建 Tab 区块
  export function createTab(blockIds: string[]) {
    createTabBlock(nodeId, mode, blockIds);
    
    // 全屏模式下，从 gridLayout 中移除被合并的区块（保留第一个）
    if (isFullscreen && blockIds.length > 1) {
      const otherBlockIds = blockIds.slice(1);
      const newLayout = gridLayout.filter(item => !otherBlockIds.includes(item.id));
      updateFullscreenGridLayout(nodeId, newLayout);
    }
  }

  // 删除 Tab 区块
  function handleRemoveTab(tabId: string) {
    const childIds = removeTabBlock(nodeId, mode, tabId);
    
    // 全屏模式下，恢复被隐藏的区块到布局中
    if (isFullscreen && childIds.length > 0) {
      const tabItem = gridLayout.find(item => item.id === tabId);
      const baseY = tabItem?.y ?? 0;
      const baseX = (tabItem?.x ?? 0) + (tabItem?.w ?? 2);
      
      const restoredItems: GridItem[] = childIds.map((childId, index) => ({
        id: childId,
        x: baseX,
        y: baseY + index * 2,
        w: 1,
        h: 2,
        minW: 1,
        minH: 1
      }));
      
      updateFullscreenGridLayout(nodeId, [...gridLayout, ...restoredItems]);
    }
  }

  // 检查区块是否是 Tab 容器
  function checkIsTabContainer(blockId: string): boolean {
    return nodeConfig[mode].tabBlocks.includes(blockId);
  }

  // 获取 Tab 状态
  function getBlockTabState(blockId: string) {
    return nodeConfig[mode].tabStates[blockId];
  }

  // 获取已使用的 Tab 区块 ID
  export function getUsedBlockIds(): string[] {
    const ids: string[] = [];
    for (const tabState of Object.values(nodeConfig[mode].tabStates)) {
      ids.push(...tabState.children.slice(1));
    }
    return ids;
  }

  // 应用尺寸覆盖到 GridItem
  function applyGridItemOverride(item: GridItem): GridItem {
    const override = nodeConfig.fullscreen.sizeOverrides[item.id];
    if (!override) return item;
    return {
      ...item,
      minW: override.minW ?? item.minW,
      minH: override.minH ?? item.minH
    };
  }

  // 整理布局（全屏模式）
  export function compact() {
    dashboardGrid?.compact();
  }

  // 重置布局（全屏模式）
  export function resetLayout() {
    updateFullscreenGridLayout(nodeId, defaultGridLayout);
    dashboardGrid?.applyLayout(defaultGridLayout);
  }

  // 应用布局预设
  export function applyLayout(layout: GridItem[]) {
    updateFullscreenGridLayout(nodeId, layout);
    dashboardGrid?.applyLayout(layout);
  }

  // 获取当前布局
  export function getCurrentLayout(): GridItem[] {
    return gridLayout;
  }

  // 获取当前配置
  export function getConfig(): NodeConfig {
    return nodeConfig;
  }
</script>

{#if isFullscreen}
  <!-- 全屏模式：GridStack 布局 -->
  <div class="h-full overflow-hidden">
    <DashboardGrid 
      bind:this={dashboardGrid} 
      columns={4} 
      cellHeight={80} 
      margin={12} 
      showToolbar={false} 
      onLayoutChange={handleGridLayoutChange}
    >
      {#each fullscreenVisibleBlocks() as item (item.id)}
        {@const gridItem = applyGridItemOverride(item)}
        <DashboardItem 
          id={gridItem.id} 
          x={gridItem.x} 
          y={gridItem.y} 
          w={gridItem.w} 
          h={gridItem.h} 
          minW={gridItem.minW ?? 1} 
          minH={gridItem.minH ?? 1}
        >
          {#if checkIsTabContainer(gridItem.id)}
            <!-- Tab 容器模式 -->
            <TabBlockCard
              id={gridItem.id}
              children={getBlockTabState(gridItem.id)?.children ?? []}
              {nodeType}
              isFullscreen={true}
              initialState={getBlockTabState(gridItem.id)}
              onStateChange={(state) => handleTabStateChange(gridItem.id, state)}
              onRemove={() => handleRemoveTab(gridItem.id)}
            >
              {#snippet renderContent(blockId: string)}
                {@render renderBlock(blockId, sizeMode)}
              {/snippet}
            </TabBlockCard>
          {:else}
            <!-- 普通区块模式 -->
            {@const blockDef = getBlockDefinition(nodeType, gridItem.id)}
            {#if blockDef}
              <BlockCard 
                id={gridItem.id} 
                title={blockDef.title} 
                icon={blockDef.icon as any} 
                iconClass={blockDef.iconClass} 
                isFullscreen={true} 
                fullHeight={blockDef.fullHeight} 
                hideHeader={blockDef.hideHeader}
              >
                {#snippet children()}
                  {@render renderBlock(gridItem.id, sizeMode)}
                {/snippet}
              </BlockCard>
            {/if}
          {/if}
        </DashboardItem>
      {/each}
    </DashboardGrid>
  </div>
{:else}
  <!-- 节点模式：BentoGrid 布局 -->
  <div class="flex-1 overflow-y-auto p-2">
    <div class="grid grid-cols-2 gap-2" style="grid-auto-rows: minmax(auto, max-content);">
      {#each normalVisibleBlocks() as block (block.id)}
        {#if checkIsTabContainer(block.id)}
          <!-- Tab 容器模式 -->
          <div class="col-span-{block.colSpan ?? 1}">
            <TabBlockCard
              id={block.id}
              children={getBlockTabState(block.id)?.children ?? []}
              {nodeType}
              isFullscreen={false}
              initialState={getBlockTabState(block.id)}
              onStateChange={(state) => handleTabStateChange(block.id, state)}
              onRemove={() => handleRemoveTab(block.id)}
            >
              {#snippet renderContent(blockId: string)}
                {@render renderBlock(blockId, sizeMode)}
              {/snippet}
            </TabBlockCard>
          </div>
        {:else}
          <!-- 普通区块模式 -->
          <BlockCard 
            id={block.id} 
            title={block.title} 
            icon={block.icon as any} 
            iconClass={block.iconClass}
            collapsible={block.collapsible}
            defaultExpanded={block.defaultExpanded ?? true}
            class="col-span-{block.colSpan ?? 1}"
          >
            {#snippet children()}
              {@render renderBlock(block.id, sizeMode)}
            {/snippet}
          </BlockCard>
        {/if}
      {/each}
    </div>
  </div>
{/if}
