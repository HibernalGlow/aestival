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
  // 已迁移到 Container Query CSS，不再需要 SizeMode
  import { onMount, tick, getContext } from "svelte";
  
  // 从 NodeWrapper 获取编辑模式 context
  import { BLOCK_EDIT_MODE_KEY, type BlockEditModeContext } from "$lib/components/nodes/blockEditContext";
  
  const blockEditContext = getContext<BlockEditModeContext | undefined>(BLOCK_EDIT_MODE_KEY);

  interface Props {
    nodeId: string;
    nodeType: string;
    isFullscreen: boolean;
    defaultFullscreenLayout?: GridItem[];
    defaultNormalLayout?: GridItem[];
    renderBlock: Snippet<[blockId: string]>;
    onConfigChange?: (config: NodeConfig) => void;
    /** 是否启用区块尺寸编辑模式（节点模式下） */
    editMode?: boolean;
  }

  let {
    nodeId,
    nodeType,
    isFullscreen,
    defaultFullscreenLayout = [],
    defaultNormalLayout = [],
    renderBlock,
    onConfigChange,
    editMode: editModeProp = false,
  }: Props = $props();

  // 从 context store 获取编辑模式，否则使用 prop
  let editModeFromContext = $state(false);
  
  // 订阅 context store
  $effect(() => {
    if (blockEditContext?.editMode) {
      const unsubscribe = blockEditContext.editMode.subscribe(v => {
        editModeFromContext = v;
      });
      return unsubscribe;
    }
  });
  
  // 最终编辑模式：优先使用 context，否则使用 prop
  let editMode = $derived(editModeFromContext || editModeProp);

  let mode = $derived(isFullscreen ? "fullscreen" : "normal") as "fullscreen" | "normal";

  function generateNormalLayout(): GridItem[] {
    const layout = getNodeBlockLayout(nodeType);
    if (!layout) return [];
    
    const blocks = layout.blocks.filter((b) => b.visibleInNormal !== false && !b.isTabContainer);
    const result: GridItem[] = [];
    
    let currentY = 0;
    let currentX = 0;
    
    for (const b of blocks) {
      const w = b.colSpan ?? 1;
      
      // 如果当前行放不下，换行
      if (currentX + w > 2) {
        currentY++;
        currentX = 0;
      }
      
      result.push({
        id: b.id,
        x: currentX,
        y: currentY,
        w: Math.min(w, 2), // 节点模式最大宽度为 2
        h: 1,
        minW: 1,
        minH: 1,
      });
      
      currentX += w;
      
      // 如果当前行已满，换行
      if (currentX >= 2) {
        currentY++;
        currentX = 0;
      }
    }
    
    return result;
  }

  function hasSavedLayout(modeState: { gridLayout: GridItem[] }): boolean {
    return modeState.gridLayout.length > 0;
  }

  /** 修复布局数据：过滤掉没有有效 id 的项 */
  function fixLayoutIds(layout: GridItem[]): GridItem[] {
    return layout.filter(item => item.id && typeof item.id === 'string');
  }

  /** 检查并添加缺失的区块到布局中 */
  function ensureAllBlocksInLayout(layout: GridItem[], modeType: 'normal' | 'fullscreen'): GridItem[] {
    // 先过滤掉无效的布局项
    const validLayout = fixLayoutIds(layout);
    
    const blockLayout = getNodeBlockLayout(nodeType);
    if (!blockLayout) return validLayout;
    
    const existingIds = new Set(validLayout.map(item => item.id));
    const visibleBlocks = blockLayout.blocks.filter(b => 
      modeType === 'normal' 
        ? b.visibleInNormal !== false && !b.isTabContainer
        : b.visibleInFullscreen !== false && !b.isTabContainer
    );
    
    // 找出缺失的区块
    const missingBlocks = visibleBlocks.filter(b => !existingIds.has(b.id));
    
    if (missingBlocks.length === 0) return validLayout;
    
    // 计算新区块的位置（放在最下面）
    const maxY = validLayout.length > 0 
      ? validLayout.reduce((max, item) => Math.max(max, item.y + item.h), 0)
      : 0;
    
    const newItems: GridItem[] = missingBlocks.map((b, idx) => ({
      id: b.id,
      x: idx % 4,
      y: maxY + Math.floor(idx / 4),
      w: b.colSpan ?? 1,
      h: 2,
      minW: 1,
      minH: 1,
    }));
    
    console.log(`[NodeLayoutRenderer] 添加缺失区块到 ${nodeType}:`, missingBlocks.map(b => b.id));
    return [...validLayout, ...newItems];
  }

  function initNodeConfig(): NodeConfig {
    const config = getOrCreateNodeConfig(
      nodeId,
      nodeType,
      defaultFullscreenLayout,
      defaultNormalLayout
    );
    let needsUpdate = false;
    
    // 检查普通模式
    if (!hasSavedLayout(config.normal)) {
      const normalLayout =
        defaultNormalLayout.length > 0
          ? defaultNormalLayout
          : generateNormalLayout();
      if (normalLayout.length > 0) {
        updateGridLayout(nodeType, "normal", normalLayout);
        needsUpdate = true;
      }
    } else {
      // 先过滤无效项
      const validNormal = fixLayoutIds(config.normal.gridLayout);
      // 如果过滤后为空，直接使用默认布局
      if (validNormal.length === 0) {
        const normalLayout = defaultNormalLayout.length > 0 ? defaultNormalLayout : generateNormalLayout();
        if (normalLayout.length > 0) {
          updateGridLayout(nodeType, "normal", normalLayout);
          needsUpdate = true;
        }
      } else {
        // 检查是否有缺失的区块
        const updatedNormal = ensureAllBlocksInLayout(validNormal, 'normal');
        if (updatedNormal.length > validNormal.length) {
          updateGridLayout(nodeType, "normal", updatedNormal);
          needsUpdate = true;
        }
      }
    }
    
    // 检查全屏模式
    if (!hasSavedLayout(config.fullscreen) && defaultFullscreenLayout.length > 0) {
      updateGridLayout(nodeType, "fullscreen", defaultFullscreenLayout);
      needsUpdate = true;
    } else if (hasSavedLayout(config.fullscreen)) {
      // 先过滤无效项
      const validFullscreen = fixLayoutIds(config.fullscreen.gridLayout);
      // 如果过滤后为空，直接使用默认布局
      if (validFullscreen.length === 0) {
        if (defaultFullscreenLayout.length > 0) {
          updateGridLayout(nodeType, "fullscreen", defaultFullscreenLayout);
          needsUpdate = true;
        }
      } else {
        // 检查是否有缺失的区块
        const updatedFullscreen = ensureAllBlocksInLayout(validFullscreen, 'fullscreen');
        if (updatedFullscreen.length > validFullscreen.length) {
          updateGridLayout(nodeType, "fullscreen", updatedFullscreen);
          needsUpdate = true;
        }
      }
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
    } else {
      // 先过滤无效项
      const validLayout = fixLayoutIds(config[currentMode].gridLayout);
      // 检查是否有缺失的区块并添加
      const updatedLayout = ensureAllBlocksInLayout(validLayout, currentMode);
      // 只有当有新区块被添加时才更新
      if (updatedLayout.length > validLayout.length) {
        updateGridLayout(nodeType, currentMode, updatedLayout);
      } else if (validLayout.length < config[currentMode].gridLayout.length) {
        // 如果有无效项被过滤掉了，也需要更新
        updateGridLayout(nodeType, currentMode, validLayout);
      }
    }
  });

  onMount(() => {
    const unsubscribe = subscribeNodeConfig(nodeType, (config) => {
      if (config) {
        // 深拷贝确保 Svelte 5 检测到所有层级的变化
        nodeConfig = {
          ...config,
          fullscreen: { ...config.fullscreen },
          normal: { ...config.normal }
        };
        onConfigChange?.(config);
      }
    });
    return unsubscribe;
  });

  // 过滤掉无效的布局项（没有 id 的项），并确保有默认布局
  let currentLayout = $derived.by(() => {
    const rawLayout = nodeConfig[mode].gridLayout;
    const validLayout = rawLayout.filter(item => item.id && typeof item.id === 'string');
    
    // 如果过滤后为空，使用默认布局
    if (validLayout.length === 0) {
      return mode === 'fullscreen' ? defaultFullscreenLayout : generateNormalLayout();
    }
    return validLayout;
  });
  
  // 节点模式下按 y, x 排序的布局（确保 CSS Grid 正确排列）
  let sortedNormalLayout = $derived(
    isFullscreen 
      ? currentLayout 
      : [...currentLayout].sort((a, b) => {
          if (a.y !== b.y) return a.y - b.y;
          return a.x - b.x;
        })
  );
  
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

  /** 处理区块宽度变化（节点模式下） */
  function handleWidthChange(blockId: string, delta: number) {
    const layout = [...currentLayout];
    const itemIndex = layout.findIndex(item => item.id === blockId);
    if (itemIndex === -1) return;
    
    const item = layout[itemIndex];
    const newW = Math.max(1, Math.min(2, item.w + delta));
    if (newW === item.w) return;
    
    layout[itemIndex] = { ...item, w: newW };
    updateGridLayout(nodeType, mode, layout);
  }

  /** 处理区块高度变化（节点模式下） */
  function handleHeightChange(blockId: string, delta: number) {
    const layout = [...currentLayout];
    const itemIndex = layout.findIndex(item => item.id === blockId);
    if (itemIndex === -1) return;
    
    const item = layout[itemIndex];
    const newH = Math.max(1, Math.min(4, item.h + delta));
    if (newH === item.h) return;
    
    layout[itemIndex] = { ...item, h: newH };
    updateGridLayout(nodeType, mode, layout);
  }

  /** 根据高度值计算 CSS 高度样式 */
  function getHeightStyle(h: number): string {
    // h=1 表示自动高度，h>1 表示固定高度（每单位约 80px）
    if (h <= 1) return '';
    return `min-height: ${h * 80}px;`;
  }

  export function getConfig(): NodeConfig {
    return nodeConfig;
  }
</script>

{#if isFullscreen}
  <!-- 全屏模式：允许垂直滚动 -->
  <div class="h-full overflow-y-auto overflow-x-hidden @container">
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
                {@render renderBlock(blockId)}
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
                  {@render renderBlock(gridItem.id)}
                {/snippet}
              </BlockCard>
            {/if}
          {/if}
        </DashboardItem>
      {/each}
    </DashboardGrid>
  </div>
{:else}
  <div class="flex-1 flex flex-col overflow-hidden p-2 min-w-0 @container">
    <!-- 上部区块：使用 grid 布局，不拉伸 -->
    <div
      class="grid grid-cols-2 gap-2 min-w-0 shrink-0"
      style="grid-auto-rows: minmax(auto, max-content);"
    >
      {#each sortedNormalLayout.slice(0, -1) as gridItem (gridItem.id)}
        {@const colSpan = gridItem.w >= 2 ? 2 : 1}
        {@const tabGroup = tabGroups.find(g => g.blockIds[0] === gridItem.id)}
        {@const isHiddenByTab = hiddenBlockIds.has(gridItem.id)}
        {#if tabGroup}
          <div 
            class="{colSpan === 2 ? 'col-span-2' : ''}"
            style={getHeightStyle(gridItem.h)}
          >
            <TabGroupCard
              group={tabGroup}
              {nodeType}
              isFullscreen={false}
              onSwitch={(index) => handleSwitchTab(tabGroup.id, index)}
              onDissolve={() => handleDissolveTabGroup(tabGroup.id)}
              onRemoveBlock={(blockId) => handleRemoveBlockFromGroup(tabGroup.id, blockId)}
              onReorder={(newOrder) => handleReorderTabGroup(tabGroup.id, newOrder)}
              sizeEditMode={editMode}
              currentW={gridItem.w}
              currentH={gridItem.h}
              onWidthChange={(delta) => handleWidthChange(gridItem.id, delta)}
              onHeightChange={(delta) => handleHeightChange(gridItem.id, delta)}
            >
              {#snippet renderContent(blockId: string)}
                {@render renderBlock(blockId)}
              {/snippet}
            </TabGroupCard>
          </div>
        {:else if !isHiddenByTab}
          {@const blockDef = getBlockDefinition(nodeType, gridItem.id)}
          {#if blockDef}
            <div 
              class={colSpan === 2 ? "col-span-2" : ""}
              style={getHeightStyle(gridItem.h)}
            >
              <BlockCard
                id={gridItem.id}
                title={blockDef.title}
                icon={blockDef.icon as any}
                iconClass={blockDef.iconClass}
                collapsible={blockDef.collapsible}
                defaultExpanded={blockDef.defaultExpanded ?? true}
                fullHeight={gridItem.h > 1}
                {editMode}
                currentW={gridItem.w}
                currentH={gridItem.h}
                onWidthChange={(delta) => handleWidthChange(gridItem.id, delta)}
                onHeightChange={(delta) => handleHeightChange(gridItem.id, delta)}
              >
                {#snippet children()}
                  {@render renderBlock(gridItem.id)}
                {/snippet}
              </BlockCard>
            </div>
          {/if}
        {/if}
      {/each}
    </div>
    <!-- 最后一个区块：可拉伸填充剩余空间 -->
    {#if sortedNormalLayout.length > 0}
      {@const lastItem = sortedNormalLayout[sortedNormalLayout.length - 1]}
      {@const tabGroup = tabGroups.find(g => g.blockIds[0] === lastItem.id)}
      {@const isHiddenByTab = hiddenBlockIds.has(lastItem.id)}
      {#if tabGroup}
        <div class="flex-1 min-h-0 mt-2 flex flex-col overflow-hidden">
          <TabGroupCard
            group={tabGroup}
            {nodeType}
            isFullscreen={false}
            onSwitch={(index) => handleSwitchTab(tabGroup.id, index)}
            onDissolve={() => handleDissolveTabGroup(tabGroup.id)}
            onRemoveBlock={(blockId) => handleRemoveBlockFromGroup(tabGroup.id, blockId)}
            onReorder={(newOrder) => handleReorderTabGroup(tabGroup.id, newOrder)}
            sizeEditMode={editMode}
            currentW={lastItem.w}
            currentH={lastItem.h}
            onWidthChange={(delta) => handleWidthChange(lastItem.id, delta)}
            onHeightChange={(delta) => handleHeightChange(lastItem.id, delta)}
          >
            {#snippet renderContent(blockId: string)}
              {@render renderBlock(blockId)}
            {/snippet}
          </TabGroupCard>
        </div>
      {:else if !isHiddenByTab}
        {@const blockDef = getBlockDefinition(nodeType, lastItem.id)}
        {#if blockDef}
          <div class="flex-1 min-h-0 mt-2 flex flex-col overflow-hidden">
            <BlockCard
              id={lastItem.id}
              title={blockDef.title}
              icon={blockDef.icon as any}
              iconClass={blockDef.iconClass}
              collapsible={blockDef.collapsible}
              defaultExpanded={blockDef.defaultExpanded ?? true}
              fullHeight={true}
              {editMode}
              currentW={lastItem.w}
              currentH={lastItem.h}
              onWidthChange={(delta) => handleWidthChange(lastItem.id, delta)}
              onHeightChange={(delta) => handleHeightChange(lastItem.id, delta)}
            >
              {#snippet children()}
                {@render renderBlock(lastItem.id)}
              {/snippet}
            </BlockCard>
          </div>
        {/if}
      {/if}
    {/if}
  </div>
{/if}
