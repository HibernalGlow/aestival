<script lang="ts">
  /**
   * NodeLayoutRenderer - 统一节点布局渲染器
   * 两种模式共用 GridItem[] 结构，全屏用 GridStack，节点用静态 CSS Grid
   */
  import type { Snippet } from 'svelte';
  import type { GridItem } from '$lib/components/ui/dashboard-grid';
  import { DashboardGrid, DashboardItem } from '$lib/components/ui/dashboard-grid';
  import { BlockCard, TabBlockCard } from '$lib/components/blocks';
  import { getBlockDefinition, getNodeBlockLayout } from './blockRegistry';
  import {
    getOrCreateNodeConfig,
    updateGridLayout,
    updateTabState,
    createTabBlock,
    removeTabBlock,
    subscribeNodeConfig,
    type NodeConfig
  } from '$lib/stores/nodeLayoutStore';
  import { getSizeMode, type SizeMode } from '$lib/utils/sizeUtils';
  import { onMount } from 'svelte';

  interface Props {
    nodeId: string;
    nodeType: string;
    isFullscreen: boolean;
    /** 全屏模式默认布局 */
    defaultFullscreenLayout?: GridItem[];
    /** 节点模式默认布局 */
    defaultNormalLayout?: GridItem[];
    renderBlock: Snippet<[blockId: string, size: SizeMode]>;
    onConfigChange?: (config: NodeConfig) => void;
  }

  let {
    nodeId,
    nodeType,
    isFullscreen,
    defaultFullscreenLayout = [],
    defaultNormalLayout = [],
    renderBlock,
    onConfigChange
  }: Props = $props();

  // 当前模式
  let mode = $derived(isFullscreen ? 'fullscreen' : 'normal') as 'fullscreen' | 'normal';
  
  // 尺寸模式
  let sizeMode = $derived(getSizeMode(isFullscreen));

  // 节点配置
  let nodeConfig = $state<NodeConfig>(
    getOrCreateNodeConfig(nodeId, nodeType, defaultFullscreenLayout, defaultNormalLayout)
  );
  
  // 初始化配置
  $effect(() => {
    let config = getOrCreateNodeConfig(nodeId, nodeType, defaultFullscreenLayout, defaultNormalLayout);
    
    // 如果节点模式布局为空，从 blockRegistry 初始化
    if (config.normal.gridLayout.length === 0) {
      const blockLayout = getNodeBlockLayout(nodeType);
      if (blockLayout) {
        const initialLayout: GridItem[] = blockLayout.blocks
          .filter(b => b.visibleInNormal !== false && !b.isTabContainer)
          .map((b, idx) => ({
            id: b.id,
            x: idx % 2,
            y: Math.floor(idx / 2),
            w: b.colSpan ?? 1,
            h: 1,
            minW: 1,
            minH: 1
          }));
        updateGridLayout(nodeId, 'normal', initialLayout);
        // 重新获取更新后的配置
        config = getOrCreateNodeConfig(nodeId, nodeType, defaultFullscreenLayout, defaultNormalLayout);
      }
    }
    
    // 如果全屏模式布局为空，也初始化
    if (config.fullscreen.gridLayout.length === 0 && defaultFullscreenLayout.length > 0) {
      updateGridLayout(nodeId, 'fullscreen', defaultFullscreenLayout);
      config = getOrCreateNodeConfig(nodeId, nodeType, defaultFullscreenLayout, defaultNormalLayout);
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

  // 当前模式的布局
  let currentLayout = $derived(nodeConfig[mode].gridLayout);

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

  // 获取可见区块（过滤掉被合并到 Tab 的）
  let visibleBlocks = $derived(() => {
    const usedIds = usedTabIds();
    return currentLayout.filter(item => !usedIds.includes(item.id));
  });

  // 处理布局变化
  function handleLayoutChange(newLayout: GridItem[]) {
    updateGridLayout(nodeId, mode, newLayout);
  }

  // 处理 Tab 状态变化
  function handleTabStateChange(tabId: string, state: { activeTab: number; children: string[] }) {
    updateTabState(nodeId, mode, tabId, state);
  }

  // 创建 Tab 区块
  export function createTab(blockIds: string[]) {
    createTabBlock(nodeId, mode, blockIds);
    
    // 从布局中移除被合并的区块（保留第一个）
    if (blockIds.length > 1) {
      const otherBlockIds = blockIds.slice(1);
      const newLayout = currentLayout.filter(item => !otherBlockIds.includes(item.id));
      updateGridLayout(nodeId, mode, newLayout);
    }
  }

  // 删除 Tab 区块
  function handleRemoveTab(tabId: string) {
    const childIds = removeTabBlock(nodeId, mode, tabId);
    
    // 恢复被隐藏的区块到布局中
    if (childIds.length > 0) {
      const tabItem = currentLayout.find(item => item.id === tabId);
      const baseY = tabItem?.y ?? 0;
      const baseX = (tabItem?.x ?? 0) + (tabItem?.w ?? 2);
      
      const restoredItems: GridItem[] = childIds.map((childId, index) => ({
        id: childId,
        x: isFullscreen ? baseX : index % 2,
        y: isFullscreen ? baseY + index * 2 : Math.floor(index / 2) + baseY + 1,
        w: 1,
        h: isFullscreen ? 2 : 1,
        minW: 1,
        minH: 1
      }));
      
      updateGridLayout(nodeId, mode, [...currentLayout, ...restoredItems]);
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
    return usedTabIds();
  }

  // 应用尺寸覆盖
  function applyGridItemOverride(item: GridItem): GridItem {
    const override = nodeConfig[mode].sizeOverrides[item.id];
    if (!override) return item;
    return {
      ...item,
      minW: override.minW ?? item.minW,
      minH: override.minH ?? item.minH
    };
  }

  // 整理布局
  export function compact() {
    dashboardGrid?.compact();
  }

  // 重置布局
  export function resetLayout() {
    const defaultLayout = isFullscreen ? defaultFullscreenLayout : defaultNormalLayout;
    updateGridLayout(nodeId, mode, defaultLayout);
    if (isFullscreen) dashboardGrid?.applyLayout(defaultLayout);
  }

  // 应用布局预设
  export function applyLayout(layout: GridItem[]) {
    updateGridLayout(nodeId, mode, layout);
    if (isFullscreen) dashboardGrid?.applyLayout(layout);
  }

  // 获取当前布局
  export function getCurrentLayout(): GridItem[] {
    return currentLayout;
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
      onLayoutChange={handleLayoutChange}
    >
      {#each visibleBlocks() as item (item.id)}
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
  <!-- 节点模式：静态 CSS Grid 布局 -->
  <div class="flex-1 overflow-y-auto p-2">
    <div class="grid grid-cols-2 gap-2" style="grid-auto-rows: minmax(auto, max-content);">
      {#each visibleBlocks() as item (item.id)}
        {@const blockDef = getBlockDefinition(nodeType, item.id)}
        {@const colSpan = item.w >= 2 ? 2 : 1}
        {#if checkIsTabContainer(item.id)}
          <div class={colSpan === 2 ? 'col-span-2' : ''}>
            <TabBlockCard
              id={item.id}
              children={getBlockTabState(item.id)?.children ?? []}
              {nodeType}
              isFullscreen={false}
              initialState={getBlockTabState(item.id)}
              onStateChange={(state) => handleTabStateChange(item.id, state)}
              onRemove={() => handleRemoveTab(item.id)}
            >
              {#snippet renderContent(blockId: string)}
                {@render renderBlock(blockId, sizeMode)}
              {/snippet}
            </TabBlockCard>
          </div>
        {:else if blockDef}
          <BlockCard 
            id={item.id} 
            title={blockDef.title} 
            icon={blockDef.icon as any} 
            iconClass={blockDef.iconClass}
            collapsible={blockDef.collapsible}
            defaultExpanded={blockDef.defaultExpanded ?? true}
            class={colSpan === 2 ? 'col-span-2' : ''}
          >
            {#snippet children()}
              {@render renderBlock(item.id, sizeMode)}
            {/snippet}
          </BlockCard>
        {/if}
      {/each}
    </div>
  </div>
{/if}
