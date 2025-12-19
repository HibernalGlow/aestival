<script lang="ts">
  /**
   * NodeLayoutRenderer - 统一节点布局渲染器
   *
   * Tab 分组采用"虚拟分组"模式：
   * - 区块始终保留在 gridLayout 中
   * - Tab 分组使用主区块（第一个区块）的位置渲染
   * - tabGroups 只存储在 fullscreen 模式，两种模式都读取 fullscreen 的配置
   */
  import type { Snippet } from "svelte";
  import type { GridItem } from "$lib/components/ui/dashboard-grid";
  import {
    DashboardGrid,
    DashboardItem,
  } from "$lib/components/ui/dashboard-grid";
  import { BlockCard, TabGroupCard } from "$lib/components/blocks";
  import { getBlockDefinition, getNodeBlockLayout } from "./blockRegistry";
  import {
    getOrCreateNodeConfig,
    updateGridLayout,
    subscribeNodeConfig,
    createTabGroup,
    dissolveTabGroup,
    switchTabGroupActive,
    removeBlockFromTabGroup,
    reorderTabGroupBlocks,
    clearTabGroups,
    getUsedBlockIds,
    type NodeConfig,
    type LayoutMode,
  } from "$lib/stores/nodeLayoutStore";
  import { getSizeMode, type SizeMode } from "$lib/utils/sizeUtils";
  import { onMount, tick } from "svelte";

  interface Props {
    nodeId: string;
    nodeType: string;
    isFullscreen: boolean;
    defaultFullscreenLayout?: GridItem[];
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
    onConfigChange,
  }: Props = $props();

  let mode = $derived(isFullscreen ? "fullscreen" : "normal") as "fullscreen" | "normal";
  let sizeMode = $derived(getSizeMode(isFullscreen));

  function generateNormalLayout(): GridItem[] {
    const layout = getNodeBlockLayout(nodeType);
    if (!layout) return [];
    return layout.blocks
      .filter((b) => b.visibleInNormal !== false && !b.isTabContainer)
      .map((b, idx) => ({
        id: b.id,
        x: idx % 2,
        y: Math.floor(idx / 2),
        w: b.colSpan ?? 1,
        h: 1,
        minW: 1,
        minH: 1,
      }));
  }

  function hasSavedLayout(modeState: { gridLayout: GridItem[] }): boolean {
    return modeState.gridLayout.length > 0;
  }

  function initNodeConfig(): NodeConfig {
    const config = getOrCreateNodeConfig(
      nodeId,
      nodeType,
      defaultFullscreenLayout,
      defaultNormalLayout
    );
    let needsUpdate = false;
    if (!hasSavedLayout(config.normal)) {
      const normalLayout =
        defaultNormalLayout.length > 0
          ? defaultNormalLayout
          : generateNormalLayout();
      if (normalLayout.length > 0) {
        updateGridLayout(nodeType, "normal", normalLayout);
        needsUpdate = true;
      }
    }
    if (
      !hasSavedLayout(config.fullscreen) &&
      defaultFullscreenLayout.length > 0
    ) {
      updateGridLayout(nodeType, "fullscreen", defaultFullscreenLayout);
      needsUpdate = true;
    }
    return needsUpdate
      ? getOrCreateNodeConfig(
          nodeId,
          nodeType,
          defaultFullscreenLayout,
          defaultNormalLayout
        )
      : config;
  }

  let nodeConfig = $state<NodeConfig>(initNodeConfig());

  $effect(() => {
    const currentMode = isFullscreen ? "fullscreen" : "normal";
    const config = getOrCreateNodeConfig(
      nodeId,
      nodeType,
      defaultFullscreenLayout,
      defaultNormalLayout
    );
    if (!hasSavedLayout(config[currentMode])) {
      const defaultLayout =
        currentMode === "fullscreen"
          ? defaultFullscreenLayout
          : defaultNormalLayout.length > 0
            ? defaultNormalLayout
            : generateNormalLayout();
      if (defaultLayout.length > 0)
        updateGridLayout(nodeType, currentMode, defaultLayout);
    }
  });

  onMount(() => {
    const unsubscribe = subscribeNodeConfig(nodeType, (config) => {
      if (config) {
        nodeConfig = config;
        onConfigChange?.(config);
      }
    });
    return unsubscribe;
  });

  let currentLayout = $derived(nodeConfig[mode].gridLayout);
  
  // 每种模式使用自己的 tabGroups
  let tabGroups = $derived(nodeConfig[mode].tabGroups);
  
  // 计算被 Tab 分组隐藏的区块 ID（用于全屏模式的 CSS 隐藏）
  let hiddenBlockIds = $derived(new Set(tabGroups.flatMap(g => g.blockIds.slice(1))));

  let dashboardGrid = $state<{
    compact: () => void;
    applyLayout: (layout: GridItem[]) => void;
    refresh?: () => Promise<void>;
  } | undefined>(undefined);

  function handleLayoutChange(newLayout: GridItem[]) {
    updateGridLayout(nodeType, mode, newLayout);
  }

  /** 解散 Tab 分组 - 使用 CSS 显示，无需刷新 GridStack */
  function handleDissolveTabGroup(groupId: string) {
    console.log("[NodeLayoutRenderer] handleDissolveTabGroup:", { groupId, mode });
    dissolveTabGroup(nodeType, groupId, mode);
  }

  /** 切换 Tab 分组活动区块 */
  function handleSwitchTab(groupId: string, index: number) {
    switchTabGroupActive(nodeType, groupId, index, mode);
  }

  /** 从 Tab 分组移除区块 */
  function handleRemoveBlockFromGroup(groupId: string, blockId: string) {
    removeBlockFromTabGroup(nodeType, groupId, blockId, mode);
  }

  /** 重排序 Tab 分组区块 */
  function handleReorderTabGroup(groupId: string, newOrder: string[]) {
    reorderTabGroupBlocks(nodeType, groupId, newOrder, mode);
  }

  function applyGridItemOverride(item: GridItem): GridItem {
    const override = nodeConfig[mode].sizeOverrides[item.id];
    return override
      ? {
          ...item,
          minW: override.minW ?? item.minW,
          minH: override.minH ?? item.minH,
        }
      : item;
  }

  /** 创建 Tab 分组 - 使用 CSS 隐藏，无需刷新 GridStack */
  export async function createTab(blockIds: string[]): Promise<string | null> {
    console.log("[NodeLayoutRenderer] createTab:", { blockIds, mode });
    const groupId = createTabGroup(nodeType, blockIds, mode);
    return groupId;
  }

  export function getUsedBlockIdsForTab(): string[] {
    return getUsedBlockIds(nodeType, mode);
  }
  
  /** 获取当前模式 */
  export function getCurrentMode(): LayoutMode {
    return mode;
  }

  export function compact() {
    dashboardGrid?.compact();
  }

  /** 重置布局 */
  export async function resetLayout() {
    console.log("[NodeLayoutRenderer] resetLayout:", { mode, isFullscreen });

    // 清除当前模式的所有 Tab 分组
    clearTabGroups(nodeType, mode);

    // 重置当前模式的布局
    const defaultLayout = isFullscreen
      ? defaultFullscreenLayout
      : defaultNormalLayout;
    updateGridLayout(nodeType, mode, defaultLayout);

    // 如果在节点模式下重置，也需要重置 fullscreen 的 gridLayout
    if (!isFullscreen) {
      updateGridLayout(nodeType, "fullscreen", defaultFullscreenLayout);
    }

    if (isFullscreen && dashboardGrid) {
      // 先等待 nodeConfig 更新触发 effectiveItems 重新计算
      await tick();
      // 再等待 DOM 根据新的 effectiveItems 更新
      await tick();
      // 现在 DOM 中应该有所有区块了，调用 refresh 同步 GridStack
      await dashboardGrid.refresh?.();
      // 最后应用布局位置
      dashboardGrid.applyLayout(defaultLayout);
    }
  }

  /** 应用布局（包含 Tab 分组） */
  export async function applyLayout(
    layout: GridItem[], 
    newTabGroups?: { id: string; blockIds: string[]; activeIndex: number }[] | null
  ) {
    // 节点模式下限制宽度为最大 2（因为 grid 只有 2 列）
    const adjustedLayout = isFullscreen 
      ? layout 
      : layout.map(item => ({
          ...item,
          w: Math.min(item.w, 2),
          x: Math.min(item.x, 1) // x 也限制在 0-1 范围内
        }));
    
    updateGridLayout(nodeType, mode, adjustedLayout);
    
    // 应用 Tab 分组：
    // - 如果 newTabGroups 是数组（包括空数组），则清除现有分组并应用新分组
    // - 如果 newTabGroups 是 undefined/null，则保留现有 Tab 分组（旧预设兼容）
    if (Array.isArray(newTabGroups)) {
      clearTabGroups(nodeType, mode);
      for (const group of newTabGroups) {
        if (group.blockIds.length >= 2) {
          createTabGroup(nodeType, group.blockIds, mode);
          // 设置活动索引
          if (group.activeIndex > 0) {
            switchTabGroupActive(nodeType, group.blockIds[0], group.activeIndex, mode);
          }
        }
      }
    }
    
    if (isFullscreen && dashboardGrid) {
      dashboardGrid.applyLayout(layout);
      await tick();
      await dashboardGrid.refresh?.();
    }
  }

  export function getCurrentLayout(): GridItem[] {
    return currentLayout;
  }
  
  /** 获取当前 Tab 分组配置 */
  export function getCurrentTabGroups(): { id: string; blockIds: string[]; activeIndex: number }[] {
    return tabGroups;
  }

  export function getConfig(): NodeConfig {
    return nodeConfig;
  }
</script>

{#if isFullscreen}
  <div class="h-full overflow-hidden">
    <DashboardGrid
      bind:this={dashboardGrid}
      columns={4}
      cellHeight={80}
      margin={12}
      showToolbar={false}
      onLayoutChange={handleLayoutChange}
    >
      {#each currentLayout as gridItem (gridItem.id)}
        {@const item = applyGridItemOverride(gridItem)}
        {@const tabGroup = tabGroups.find(g => g.blockIds[0] === gridItem.id)}
        {@const isHiddenByTab = hiddenBlockIds.has(gridItem.id)}
        <DashboardItem
          id={item.id}
          x={item.x}
          y={item.y}
          w={item.w}
          h={item.h}
          minW={item.minW ?? 1}
          minH={item.minH ?? 1}
          class={isHiddenByTab ? 'hidden-by-tab' : ''}
        >
          {#if tabGroup}
            <!-- Tab 分组主区块 -->
            <TabGroupCard
              group={tabGroup}
              {nodeType}
              isFullscreen={true}
              onSwitch={(index) => handleSwitchTab(tabGroup.id, index)}
              onDissolve={() => handleDissolveTabGroup(tabGroup.id)}
              onRemoveBlock={(blockId) => handleRemoveBlockFromGroup(tabGroup.id, blockId)}
              onReorder={(newOrder) => handleReorderTabGroup(tabGroup.id, newOrder)}
            >
              {#snippet renderContent(blockId: string)}
                {@render renderBlock(blockId, sizeMode)}
              {/snippet}
            </TabGroupCard>
          {:else if !isHiddenByTab}
            <!-- 普通区块 -->
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
  <div class="flex-1 flex flex-col overflow-hidden p-2 min-w-0">
    <!-- 上部区块：使用 grid 布局，不拉伸 -->
    <div
      class="grid grid-cols-2 gap-2 min-w-0 shrink-0"
      style="grid-auto-rows: minmax(auto, max-content);"
    >
      {#each currentLayout.slice(0, -1) as gridItem (gridItem.id)}
        {@const colSpan = gridItem.w >= 2 ? 2 : 1}
        {@const tabGroup = tabGroups.find(g => g.blockIds[0] === gridItem.id)}
        {@const isHiddenByTab = hiddenBlockIds.has(gridItem.id)}
        {#if tabGroup}
          <div class={colSpan === 2 ? "col-span-2" : ""}>
            <TabGroupCard
              group={tabGroup}
              {nodeType}
              isFullscreen={false}
              onSwitch={(index) => handleSwitchTab(tabGroup.id, index)}
              onDissolve={() => handleDissolveTabGroup(tabGroup.id)}
              onRemoveBlock={(blockId) => handleRemoveBlockFromGroup(tabGroup.id, blockId)}
              onReorder={(newOrder) => handleReorderTabGroup(tabGroup.id, newOrder)}
            >
              {#snippet renderContent(blockId: string)}
                {@render renderBlock(blockId, sizeMode)}
              {/snippet}
            </TabGroupCard>
          </div>
        {:else if !isHiddenByTab}
          {@const blockDef = getBlockDefinition(nodeType, gridItem.id)}
          {#if blockDef}
            <BlockCard
              id={gridItem.id}
              title={blockDef.title}
              icon={blockDef.icon as any}
              iconClass={blockDef.iconClass}
              collapsible={blockDef.collapsible}
              defaultExpanded={blockDef.defaultExpanded ?? true}
              class={colSpan === 2 ? "col-span-2" : ""}
            >
              {#snippet children()}
                {@render renderBlock(gridItem.id, sizeMode)}
              {/snippet}
            </BlockCard>
          {/if}
        {/if}
      {/each}
    </div>
    <!-- 最后一个区块：可拉伸填充剩余空间 -->
    {#if currentLayout.length > 0}
      {@const lastItem = currentLayout[currentLayout.length - 1]}
      {@const tabGroup = tabGroups.find(g => g.blockIds[0] === lastItem.id)}
      {@const isHiddenByTab = hiddenBlockIds.has(lastItem.id)}
      {#if tabGroup}
        <div class="flex-1 min-h-0 mt-2 flex flex-col">
          <TabGroupCard
            group={tabGroup}
            {nodeType}
            isFullscreen={false}
            onSwitch={(index) => handleSwitchTab(tabGroup.id, index)}
            onDissolve={() => handleDissolveTabGroup(tabGroup.id)}
            onRemoveBlock={(blockId) => handleRemoveBlockFromGroup(tabGroup.id, blockId)}
            onReorder={(newOrder) => handleReorderTabGroup(tabGroup.id, newOrder)}
          >
            {#snippet renderContent(blockId: string)}
              {@render renderBlock(blockId, sizeMode)}
            {/snippet}
          </TabGroupCard>
        </div>
      {:else if !isHiddenByTab}
        {@const blockDef = getBlockDefinition(nodeType, lastItem.id)}
        {#if blockDef}
          <div class="flex-1 min-h-0 mt-2 flex flex-col">
            <BlockCard
              id={lastItem.id}
              title={blockDef.title}
              icon={blockDef.icon as any}
              iconClass={blockDef.iconClass}
              collapsible={blockDef.collapsible}
              defaultExpanded={blockDef.defaultExpanded ?? true}
              fullHeight={true}
            >
              {#snippet children()}
                {@render renderBlock(lastItem.id, sizeMode)}
              {/snippet}
            </BlockCard>
          </div>
        {/if}
      {/if}
    {/if}
  </div>
{/if}
