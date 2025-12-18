<script lang="ts">
  /**
   * NodeLayoutRenderer - 统一节点布局渲染器
   *
   * 模式说明：
   * - mode: 当前渲染模式，决定使用哪个 gridLayout（fullscreen 或 normal）
   * - tabMode: Tab 状态存储的模式，始终为 'fullscreen'
   *   - 这意味着 Tab 配置只在全屏模式下创建和编辑
   *   - 节点模式会读取全屏模式的 Tab 配置来渲染
   *
   * Tab 容器使用独立 ID（tab-xxx），不再复用子区块 ID
   */
  import type { Snippet } from "svelte";
  import type { GridItem } from "$lib/components/ui/dashboard-grid";
  import {
    DashboardGrid,
    DashboardItem,
  } from "$lib/components/ui/dashboard-grid";
  import { BlockCard, TabBlockCard } from "$lib/components/blocks";
  import { getBlockDefinition, getNodeBlockLayout } from "./blockRegistry";
  import {
    getOrCreateNodeConfig,
    updateGridLayout,
    subscribeNodeConfig,
    createTab as createLayoutTab,
    removeTab as removeLayoutTab,
    clearTabStates,
    getUsedBlockIds as getLayoutUsedBlockIds,
    isTabContainer as checkLayoutTabContainer,
    type NodeConfig,
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

  let mode = $derived(isFullscreen ? "fullscreen" : "normal") as
    | "fullscreen"
    | "normal";
  // tabMode: Tab 状态存储模式，跟随 mode 变化，确保模式隔离
  let tabMode = $derived(mode);
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
  let dashboardGrid = $state<
    | {
        compact: () => void;
        applyLayout: (layout: GridItem[]) => void;
        refresh?: () => Promise<void>;
      }
    | undefined
  >(undefined);
  let usedTabIds = $derived(() => getLayoutUsedBlockIds(nodeType, tabMode));
  // visibleBlocks: gridLayout 中不在 Tab 内的区块（Tab 容器本身会在 gridLayout 中，子区块不会）
  let visibleBlocks = $derived(() =>
    currentLayout.filter((item) => !usedTabIds().includes(item.id))
  );

  function handleLayoutChange(newLayout: GridItem[]) {
    updateGridLayout(nodeType, mode, newLayout);
  }

  /** 删除 Tab 并刷新 GridStack */
  async function handleRemoveTab(tabId: string) {
    console.log("[NodeLayoutRenderer] handleRemoveTab:", {
      tabId,
      mode,
      tabMode,
    });
    removeLayoutTab(nodeType, tabMode, tabId);
    // 等待 Svelte 更新 DOM 后刷新 GridStack
    await tick();
    if (isFullscreen && dashboardGrid?.refresh) {
      await dashboardGrid.refresh();
    }
  }

  function checkIsTabContainer(blockId: string): boolean {
    return checkLayoutTabContainer(nodeType, tabMode, blockId);
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

  /** 创建 Tab 并刷新 GridStack */
  export async function createTab(blockIds: string[]): Promise<string | null> {
    console.log("[NodeLayoutRenderer] createTab:", { blockIds, mode, tabMode });
    const tabId = createLayoutTab(nodeType, tabMode, blockIds);
    if (tabId && isFullscreen && dashboardGrid?.refresh) {
      await tick();
      await dashboardGrid.refresh();
    }
    return tabId;
  }

  export function getUsedBlockIds(): string[] {
    return usedTabIds();
  }
  export function isTabContainer(blockId: string): boolean {
    return checkIsTabContainer(blockId);
  }
  export function compact() {
    dashboardGrid?.compact();
  }

  /** 重置布局 */
  export async function resetLayout() {
    console.log("[NodeLayoutRenderer] resetLayout:", {
      mode,
      tabMode,
      isFullscreen,
    });

    // 清除当前模式下的所有 Tab 状态
    clearTabStates(nodeType, mode);

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
              {nodeType}
              mode={tabMode}
              isFullscreen={true}
              onRemove={() => handleRemoveTab(gridItem.id)}
            >
              {#snippet renderContent(blockId: string)}{@render renderBlock(
                  blockId,
                  sizeMode
                )}{/snippet}
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
                {#snippet children()}{@render renderBlock(
                    gridItem.id,
                    sizeMode
                  )}{/snippet}
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
      {#each visibleBlocks() as item (item.id)}
        {@const blockDef = getBlockDefinition(nodeType, item.id)}
        {@const colSpan = item.w >= 2 ? 2 : 1}
        {#if checkIsTabContainer(item.id)}
          <div class={colSpan === 2 ? "col-span-2" : ""}>
            <TabBlockCard
              id={item.id}
              {nodeType}
              mode={tabMode}
              isFullscreen={false}
              onRemove={() => handleRemoveTab(item.id)}
            >
              {#snippet renderContent(blockId: string)}{@render renderBlock(
                  blockId,
                  sizeMode
                )}{/snippet}
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
            class={colSpan === 2 ? "col-span-2" : ""}
          >
            {#snippet children()}{@render renderBlock(
                item.id,
                sizeMode
              )}{/snippet}
          </BlockCard>
        {/if}
      {/each}
    </div>
  </div>
{/if}
