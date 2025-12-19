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
    getEffectiveTabGroups,
    getUsedBlockIds,
    computeEffectiveItems,
    type NodeConfig,
    type EffectiveItem,
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
  let tabGroups = $derived(getEffectiveTabGroups(nodeType));
  
  // 计算有效渲染项
  let effectiveItems = $derived(computeEffectiveItems(currentLayout, tabGroups));

  let dashboardGrid = $state<{
    compact: () => void;
    applyLayout: (layout: GridItem[]) => void;
    refresh?: () => Promise<void>;
  } | undefined>(undefined);

  function handleLayoutChange(newLayout: GridItem[]) {
    updateGridLayout(nodeType, mode, newLayout);
  }

  /** 解散 Tab 分组并刷新 */
  async function handleDissolveTabGroup(groupId: string) {
    console.log("[NodeLayoutRenderer] handleDissolveTabGroup:", { groupId });
    dissolveTabGroup(nodeType, groupId);
    await tick();
    if (isFullscreen && dashboardGrid?.refresh) {
      await dashboardGrid.refresh();
    }
  }

  /** 切换 Tab 分组活动区块 */
  function handleSwitchTab(groupId: string, index: number) {
    switchTabGroupActive(nodeType, groupId, index);
  }

  /** 从 Tab 分组移除区块 */
  async function handleRemoveBlockFromGroup(groupId: string, blockId: string) {
    removeBlockFromTabGroup(nodeType, groupId, blockId);
    await tick();
    if (isFullscreen && dashboardGrid?.refresh) {
      await dashboardGrid.refresh();
    }
  }

  /** 重排序 Tab 分组区块 */
  function handleReorderTabGroup(groupId: string, newOrder: string[]) {
    reorderTabGroupBlocks(nodeType, groupId, newOrder);
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

  /** 创建 Tab 分组并刷新 */
  export async function createTab(blockIds: string[]): Promise<string | null> {
    console.log("[NodeLayoutRenderer] createTab:", { blockIds });
    const groupId = createTabGroup(nodeType, blockIds);
    if (groupId && isFullscreen && dashboardGrid?.refresh) {
      await tick();
      await dashboardGrid.refresh();
    }
    return groupId;
  }

  export function getUsedBlockIdsForTab(): string[] {
    return getUsedBlockIds(nodeType);
  }

  export function compact() {
    dashboardGrid?.compact();
  }

  /** 重置布局 */
  export async function resetLayout() {
    console.log("[NodeLayoutRenderer] resetLayout:", { mode, isFullscreen });

    // 清除所有 Tab 分组
    clearTabGroups(nodeType);

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
      dashboardGrid.applyLayout(defaultLayout);
      await tick();
      await dashboardGrid.refresh?.();
    }
  }

  /** 应用布局 */
  export async function applyLayout(layout: GridItem[]) {
    updateGridLayout(nodeType, mode, layout);
    if (isFullscreen && dashboardGrid) {
      dashboardGrid.applyLayout(layout);
      await tick();
      await dashboardGrid.refresh?.();
    }
  }

  export function getCurrentLayout(): GridItem[] {
    return currentLayout;
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
      {#each effectiveItems as item (item.gridItem.id)}
        {@const gridItem = applyGridItemOverride(item.gridItem)}
        <DashboardItem
          id={gridItem.id}
          x={gridItem.x}
          y={gridItem.y}
          w={gridItem.w}
          h={gridItem.h}
          minW={gridItem.minW ?? 1}
          minH={gridItem.minH ?? 1}
        >
          {#if item.type === 'tab-group'}
            <TabGroupCard
              group={item.group}
              {nodeType}
              isFullscreen={true}
              onSwitch={(index) => handleSwitchTab(item.group.id, index)}
              onDissolve={() => handleDissolveTabGroup(item.group.id)}
              onRemoveBlock={(blockId) => handleRemoveBlockFromGroup(item.group.id, blockId)}
              onReorder={(newOrder) => handleReorderTabGroup(item.group.id, newOrder)}
            >
              {#snippet renderContent(blockId: string)}
                {@render renderBlock(blockId, sizeMode)}
              {/snippet}
            </TabGroupCard>
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
  <div class="flex-1 overflow-y-auto p-2">
    <div
      class="grid grid-cols-2 gap-2"
      style="grid-auto-rows: minmax(auto, max-content);"
    >
      {#each effectiveItems as item (item.gridItem.id)}
        {@const colSpan = item.gridItem.w >= 2 ? 2 : 1}
        {#if item.type === 'tab-group'}
          <div class={colSpan === 2 ? "col-span-2" : ""}>
            <TabGroupCard
              group={item.group}
              {nodeType}
              isFullscreen={false}
              onSwitch={(index) => handleSwitchTab(item.group.id, index)}
              onDissolve={() => handleDissolveTabGroup(item.group.id)}
              onRemoveBlock={(blockId) => handleRemoveBlockFromGroup(item.group.id, blockId)}
              onReorder={(newOrder) => handleReorderTabGroup(item.group.id, newOrder)}
            >
              {#snippet renderContent(blockId: string)}
                {@render renderBlock(blockId, sizeMode)}
              {/snippet}
            </TabGroupCard>
          </div>
        {:else}
          {@const blockDef = getBlockDefinition(nodeType, item.gridItem.id)}
          {#if blockDef}
            <BlockCard
              id={item.gridItem.id}
              title={blockDef.title}
              icon={blockDef.icon as any}
              iconClass={blockDef.iconClass}
              collapsible={blockDef.collapsible}
              defaultExpanded={blockDef.defaultExpanded ?? true}
              class={colSpan === 2 ? "col-span-2" : ""}
            >
              {#snippet children()}
                {@render renderBlock(item.gridItem.id, sizeMode)}
              {/snippet}
            </BlockCard>
          {/if}
        {/if}
      {/each}
    </div>
  </div>
{/if}
