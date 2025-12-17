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

  // 生成节点模式默认布局
  function generateNormalLayout(): GridItem[] {
    const layout = getNodeBlockLayout(nodeType);
    if (!layout) return [];
    return layout.blocks
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
  }

  // 检查模式是否有任何已保存的状态（布局或 Tab）
  function hasSavedState(modeState: typeof nodeConfig.normal): boolean {
    return modeState.gridLayout.length > 0 || 
           modeState.tabBlocks.length > 0 || 
           Object.keys(modeState.tabStates).length > 0;
  }

  // 初始化节点配置（使用 nodeType 作为 key）
  function initNodeConfig(): NodeConfig {
    const config = getOrCreateNodeConfig(nodeId, nodeType, defaultFullscreenLayout, defaultNormalLayout);
    
    console.log('[NodeLayoutRenderer] 初始化配置:', {
      nodeType,
      mode,
      gridLayout: config[mode].gridLayout.map(i => i.id),
      tabBlocks: config[mode].tabBlocks,
      tabStates: Object.keys(config[mode].tabStates)
    });
    
    // 只有当模式完全没有保存状态时才初始化布局
    let needsUpdate = false;
    
    // 节点模式：没有任何保存状态时才初始化
    if (!hasSavedState(config.normal)) {
      const normalLayout = defaultNormalLayout.length > 0 ? defaultNormalLayout : generateNormalLayout();
      if (normalLayout.length > 0) {
        updateGridLayout(nodeType, 'normal', normalLayout);
        needsUpdate = true;
      }
    }
    
    // 全屏模式：没有任何保存状态时才初始化
    if (!hasSavedState(config.fullscreen) && defaultFullscreenLayout.length > 0) {
      updateGridLayout(nodeType, 'fullscreen', defaultFullscreenLayout);
      needsUpdate = true;
    }
    
    // 如果有更新，重新获取配置
    const finalConfig = needsUpdate 
      ? getOrCreateNodeConfig(nodeId, nodeType, defaultFullscreenLayout, defaultNormalLayout)
      : config;
    
    console.log('[NodeLayoutRenderer] 最终配置:', {
      gridLayoutIds: finalConfig[mode].gridLayout.map(i => i.id),
      tabBlocks: finalConfig[mode].tabBlocks,
      tabStatesKeys: Object.keys(finalConfig[mode].tabStates)
    });
    
    return finalConfig;
  }

  // 节点配置
  let nodeConfig = $state<NodeConfig>(initNodeConfig());
  
  // 当 isFullscreen 变化时重新初始化（因为 mode 变了）
  $effect(() => {
    // 触发依赖
    const currentMode = isFullscreen ? 'fullscreen' : 'normal';
    console.log('[NodeLayoutRenderer] mode 变化:', currentMode);
    // 重新获取配置，确保当前模式有正确的布局
    const config = getOrCreateNodeConfig(nodeId, nodeType, defaultFullscreenLayout, defaultNormalLayout);
    if (!hasSavedState(config[currentMode])) {
      const defaultLayout = currentMode === 'fullscreen' 
        ? defaultFullscreenLayout 
        : (defaultNormalLayout.length > 0 ? defaultNormalLayout : generateNormalLayout());
      if (defaultLayout.length > 0) {
        updateGridLayout(nodeType, currentMode, defaultLayout);
      }
    }
  });
  
  // 订阅配置变化（使用 nodeType 作为 key）
  onMount(() => {
    const unsubscribe = subscribeNodeConfig(nodeType, (config) => {
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
    const visible = currentLayout.filter(item => !usedIds.includes(item.id));
    console.log('[NodeLayoutRenderer] visibleBlocks:', {
      mode,
      currentLayoutIds: currentLayout.map(i => i.id),
      usedIds,
      visibleIds: visible.map(i => i.id),
      tabBlocks: nodeConfig[mode].tabBlocks
    });
    return visible;
  });

  // 处理布局变化（使用 nodeType 作为 key）
  function handleLayoutChange(newLayout: GridItem[]) {
    updateGridLayout(nodeType, mode, newLayout);
  }

  // 处理 Tab 状态变化（使用 nodeType 作为 key）
  function handleTabStateChange(tabId: string, state: { activeTab: number; children: string[] }) {
    updateTabState(nodeType, mode, tabId, state);
  }

  // 创建 Tab 区块（原子操作，使用 nodeType 作为 key）
  export function createTab(blockIds: string[]) {
    createTabBlock(nodeType, mode, blockIds, true);
  }

  // 删除 Tab 区块（原子操作，使用 nodeType 作为 key）
  function handleRemoveTab(tabId: string) {
    removeTabBlock(nodeType, mode, tabId, true, isFullscreen);
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

  // 重置布局（使用 nodeType 作为 key）
  export function resetLayout() {
    const defaultLayout = isFullscreen ? defaultFullscreenLayout : defaultNormalLayout;
    updateGridLayout(nodeType, mode, defaultLayout);
    if (isFullscreen) dashboardGrid?.applyLayout(defaultLayout);
  }

  // 应用布局预设（使用 nodeType 作为 key）
  export function applyLayout(layout: GridItem[]) {
    updateGridLayout(nodeType, mode, layout);
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
