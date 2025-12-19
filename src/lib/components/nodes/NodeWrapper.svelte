<script lang="ts">
  /**
   * 通用节点包装器
   * 提供：关闭、折叠/展开、固定、状态显示、全屏 功能
   * 使用 settingsManager 的面板透明度和模糊设置
   *
   * 全屏模式：自动检测并应用全屏样式，节点组件无需任何修改
   */
  import {
    X,
    ChevronDown,
    ChevronRight,
    Pin,
    PinOff,
    Maximize2,
    Minimize2,
    LayoutGrid,
    RotateCcw,
    Layout,
    Layers,
  } from "@lucide/svelte";
  import { Badge } from "$lib/components/ui/badge";
  import { LayoutPresetSelector } from "$lib/components/ui/dashboard-grid";
  import { TabConfigPanel } from "$lib/components/blocks";
  import type { GridItem } from "$lib/components/ui/dashboard-grid";
  import { flowStore } from "$lib/stores";
  import { fullscreenNodeStore } from "$lib/stores/fullscreenNode.svelte";
  import { settingsManager } from "$lib/settings/settingsManager";
  import { onMount } from "svelte";
  import type { Snippet } from "svelte";

  // 获取面板设置（透明度和模糊）
  let panelSettings = $state(settingsManager.getSettings().panels);
  
  // 计算节点样式 - 使用 color-mix 实现带颜色的透明效果
  let nodeStyle = $derived(
    `background: color-mix(in srgb, var(--card) ${panelSettings.topToolbarOpacity}%, transparent); backdrop-filter: blur(${panelSettings.topToolbarBlur}px);`
  );

  onMount(() => {
    // 监听设置变化
    settingsManager.addListener((s) => {
      panelSettings = s.panels;
    });
  });

  // 状态类型
  type NodeStatus = "idle" | "running" | "completed" | "error" | string;
  type BadgeVariant = "default" | "secondary" | "destructive" | "outline";

  interface Props {
    /** 节点 ID */
    nodeId: string;
    /** 节点标题 */
    title: string;
    /** Lucide 图标组件 */
    icon?: typeof X;
    /** emoji 图标（与 icon 二选一） */
    emoji?: string;
    /** 节点状态 */
    status?: NodeStatus;
    /** 自定义状态标签 */
    statusLabel?: string;
    /** 自定义状态样式 */
    statusVariant?: BadgeVariant;
    /** 是否可折叠，默认 true */
    collapsible?: boolean;
    /** 是否可关闭，默认 true */
    closable?: boolean;
    /** 是否可固定，默认 true */
    pinnable?: boolean;
    /** 是否有全屏功能，默认 true */
    hasFullscreen?: boolean;
    /** 是否是全屏渲染模式（由页面级别传入） */
    isFullscreenRender?: boolean;
    /** 初始折叠状态 */
    defaultCollapsed?: boolean;
    /** 边框样式类 */
    borderClass?: string;
    /** 节点内容 */
    children: Snippet;
    /** 标题栏额外内容（在标准按钮之前） */
    headerExtra?: Snippet;
    /** 折叠回调 */
    onCollapse?: (collapsed: boolean) => void;
    /** 固定回调 */
    onPin?: (pinned: boolean) => void;
    /** 整理布局回调（全屏模式） */
    onCompact?: () => void;
    /** 重置布局回调（全屏模式） */
    onResetLayout?: () => void;
    /** 节点类型（用于布局预设） */
    nodeType?: string;
    /** 当前布局（用于布局预设） */
    currentLayout?: GridItem[];
    /** 当前 Tab 分组（用于布局预设保存） */
    currentTabGroups?: { id: string; blockIds: string[]; activeIndex: number }[];
    /** 应用布局回调（全屏模式，包含 Tab 分组） */
    onApplyLayout?: (layout: GridItem[], tabGroups?: { id: string; blockIds: string[]; activeIndex: number }[]) => void;
    /** 创建 Tab 区块回调（传入选中的区块 ID 列表） */
    onCreateTab?: (blockIds: string[]) => void;
    /** 是否支持创建 Tab 区块 */
    canCreateTab?: boolean;
    /** 当前布局模式（用于 Tab 配置） */
    layoutMode?: 'fullscreen' | 'normal';
  }

  // 默认状态标签映射
  const defaultStatusLabels: Record<string, string> = {
    idle: "就绪",
    running: "运行中",
    completed: "完成",
    error: "错误",
    scanning: "扫描中",
    analyzing: "分析中",
    analyzed: "待压缩",
    compressing: "压缩中",
    ready: "待操作",
    renaming: "执行中",
  };

  // 默认状态样式映射
  const defaultStatusVariants: Record<string, BadgeVariant> = {
    idle: "secondary",
    running: "default",
    completed: "default",
    error: "destructive",
    scanning: "default",
    analyzing: "default",
    analyzed: "secondary",
    compressing: "default",
    ready: "secondary",
    renaming: "default",
  };

  let {
    nodeId,
    title,
    icon: Icon,
    emoji,
    status,
    statusLabel,
    statusVariant,
    collapsible = true,
    closable = true,
    pinnable = true,
    hasFullscreen = true,
    isFullscreenRender = false,
    defaultCollapsed = false,
    borderClass = "border-border",
    children,
    headerExtra,
    onCollapse,
    onPin,
    onCompact,
    onResetLayout,
    nodeType,
    currentLayout,
    currentTabGroups,
    onApplyLayout,
    onCreateTab,
    canCreateTab = false,
    layoutMode = 'fullscreen',
  }: Props = $props();

  // 状态
  let collapsed = $state.raw(false);
  let pinned = $state(false);
  let showLayoutBar = $state(false);  // 布局预设栏展开状态
  let showTabConfig = $state(false);  // Tab 配置面板展开状态

  // 检测是否在全屏模式（原节点需要变淡）
  let isNodeInFullscreen = $derived(
    $fullscreenNodeStore.isOpen && $fullscreenNodeStore.nodeId === nodeId
  );
  // 原节点变淡：当节点在全屏模式但不是全屏渲染版本时
  let shouldFade = $derived(isNodeInFullscreen && !isFullscreenRender);

  // 初始化折叠状态
  $effect(() => {
    if (defaultCollapsed) collapsed = true;
  });

  // 计算状态显示
  let displayLabel = $derived(
    statusLabel ?? (status ? (defaultStatusLabels[status] ?? status) : "")
  );
  let displayVariant = $derived(
    statusVariant ??
      (status ? (defaultStatusVariants[status] ?? "secondary") : "secondary")
  );

  // 关闭节点
  function handleClose() {
    flowStore.removeNode(nodeId);
  }

  // 切换折叠
  function toggleCollapse() {
    if (collapsible) {
      collapsed = !collapsed;
      onCollapse?.(collapsed);
    }
  }

  // 切换固定
  function togglePin() {
    pinned = !pinned;
    flowStore.updateNode(nodeId, { draggable: !pinned });
    onPin?.(pinned);
  }

  // 切换全屏
  function toggleFullscreen() {
    if (hasFullscreen) {
      if (isNodeInFullscreen) {
        fullscreenNodeStore.close();
      } else {
        fullscreenNodeStore.open(nodeId);
      }
    }
  }
</script>

<!-- 全屏时原节点变淡，页面级别会渲染全屏版本 -->
<div
  class="{shouldFade
    ? 'opacity-30 pointer-events-none'
    : ''} {isFullscreenRender
    ? 'h-full flex flex-col'
    : 'h-full flex flex-col min-w-[160px]'} border rounded-lg shadow-lg overflow-hidden {borderClass}"
  style={nodeStyle}
>
  <!-- 标题栏 -->
  <div
    class="flex items-center justify-between px-3 py-2 border-b select-none {pinned
      ? 'cursor-not-allowed'
      : 'cursor-move'} shrink-0"
  >
    <!-- 左侧：折叠按钮 + 图标 + 标题 + 状态 -->
    <div class="flex items-center gap-2 flex-1 min-w-0">
      {#if collapsible}
        <button
          class="p-0.5 rounded hover:bg-muted transition-colors"
          onclick={toggleCollapse}
          title={collapsed ? "展开" : "折叠"}
        >
          {#if collapsed}
            <ChevronRight class="w-4 h-4" />
          {:else}
            <ChevronDown class="w-4 h-4" />
          {/if}
        </button>
      {/if}

      {#if emoji}
        <span class="text-lg shrink-0">{emoji}</span>
      {:else if Icon}
        <Icon class="w-4 h-4 text-muted-foreground shrink-0" />
      {/if}

      <span class="text-sm font-semibold truncate">{title}</span>

      {#if status && displayLabel}
        <Badge variant={displayVariant} class="text-xs ml-1">
          {displayLabel}
        </Badge>
      {/if}
    </div>

    <!-- 右侧：操作按钮 -->
    <div class="flex items-center gap-0.5 ml-2">
      {#if headerExtra}
        {@render headerExtra()}
      {/if}

      <!-- 创建 Tab 区块按钮（两种模式都支持） -->
      {#if canCreateTab && onCreateTab && nodeType}
        <button
          class="p-1 rounded hover:bg-muted transition-colors {showTabConfig ? 'text-primary' : 'text-muted-foreground'}"
          onclick={() => showTabConfig = !showTabConfig}
          title="创建 Tab 区块"
        >
          <Layers class="w-3.5 h-3.5" />
        </button>
      {/if}

      <!-- 布局预设按钮（两种模式都支持） -->
      {#if nodeType && currentLayout && onApplyLayout}
        <button
          class="p-1 rounded hover:bg-muted transition-colors {showLayoutBar ? 'text-primary' : 'text-muted-foreground'}"
          onclick={() => showLayoutBar = !showLayoutBar}
          title="布局预设"
        >
          <Layout class="w-3.5 h-3.5" />
        </button>
      {/if}

      {#if hasFullscreen}
        <button
          class="p-1 rounded hover:bg-muted transition-colors text-muted-foreground"
          onclick={toggleFullscreen}
          title={isNodeInFullscreen ? "退出全屏" : "全屏"}
        >
          {#if isNodeInFullscreen}
            <Minimize2 class="w-3.5 h-3.5" />
          {:else}
            <Maximize2 class="w-3.5 h-3.5" />
          {/if}
        </button>
      {/if}

      {#if pinnable}
        <button
          class="p-1 rounded hover:bg-muted transition-colors {pinned
            ? 'text-primary'
            : 'text-muted-foreground'}"
          onclick={togglePin}
          title={pinned ? "取消固定" : "固定"}
        >
          {#if pinned}
            <Pin class="w-3.5 h-3.5" />
          {:else}
            <PinOff class="w-3.5 h-3.5" />
          {/if}
        </button>
      {/if}

      {#if closable}
        <button
          class="p-1 rounded hover:bg-destructive hover:text-destructive-foreground transition-colors text-muted-foreground"
          onclick={handleClose}
          title="关闭"
        >
          <X class="w-3.5 h-3.5" />
        </button>
      {/if}
    </div>
  </div>

  <!-- 布局预设横向展开栏（两种模式都支持，标题栏下方） -->
  {#if showLayoutBar && nodeType && currentLayout && onApplyLayout}
    <div class="px-3 py-2 bg-muted/20 border-b shrink-0">
      <div class="flex items-center gap-2">
        <LayoutPresetSelector 
          {nodeType}
          {currentLayout}
          {currentTabGroups}
          onApply={onApplyLayout}
          currentMode={layoutMode}
        />
        <!-- 重置布局按钮 -->
        {#if onResetLayout}
          <button
            class="px-2 py-1 text-xs rounded border border-border hover:bg-muted transition-colors flex items-center gap-1"
            onclick={onResetLayout}
            title="重置布局"
          >
            <RotateCcw class="w-3 h-3" />
            重置
          </button>
        {/if}
        <!-- 整理布局按钮（全屏模式） -->
        {#if isFullscreenRender && onCompact}
          <button
            class="px-2 py-1 text-xs rounded border border-border hover:bg-muted transition-colors flex items-center gap-1"
            onclick={onCompact}
            title="整理布局"
          >
            <LayoutGrid class="w-3 h-3" />
            整理
          </button>
        {/if}
      </div>
    </div>
  {/if}

  <!-- Tab 配置面板（两种模式都支持，标题栏下方） -->
  {#if showTabConfig && nodeType && onCreateTab}
    <div class="px-3 py-2 bg-muted/20 border-b shrink-0">
      <TabConfigPanel 
        {nodeType}
        mode={layoutMode}
        onCreate={(blockIds) => { onCreateTab(blockIds); }}
        onCancel={() => showTabConfig = false}
      />
    </div>
  {/if}

  <!-- 内容区 -->
  {#if !collapsed || isFullscreenRender}
    <div class="nodrag flex-1 min-h-0 overflow-hidden">
      {@render children()}
    </div>
  {/if}
</div>
