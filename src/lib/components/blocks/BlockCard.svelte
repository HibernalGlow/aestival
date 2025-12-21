<script lang="ts">
  /**
   * BlockCard - 通用区块卡片容器（Bento Grid 风格 + Magic Card 效果）
   * 支持普通模式（Bento Grid）和全屏模式（GridStack）
   * 特性：鼠标跟随聚光灯、悬停动画、精致阴影、暗色模式优化
   */
  import { ChevronDown, ChevronRight, ArrowRight, Plus, Minus } from '@lucide/svelte';
  import { slide } from 'svelte/transition';
  import { settingsManager } from '$lib/settings/settingsManager';
  import { onMount } from 'svelte';
  import type { Snippet } from 'svelte';

  interface Props {
    /** 区块 ID（用于布局持久化等场景） */
    id: string;
    /** 标题 */
    title: string;
    /** Lucide 图标组件 */
    icon?: typeof ChevronDown;
    /** 图标颜色类 */
    iconClass?: string;
    /** 是否可折叠 */
    collapsible?: boolean;
    /** 默认展开状态 */
    defaultExpanded?: boolean;
    /** 是否全屏模式（自动启用 fullHeight） */
    isFullscreen?: boolean;
    /** 隐藏标题栏 */
    hideHeader?: boolean;
    /** 紧凑模式 */
    compact?: boolean;
    /** 占满高度（isFullscreen 时自动为 true） */
    fullHeight?: boolean;
    /** 自定义类名 */
    class?: string;
    /** 内容 */
    children: Snippet;
    /** 标题栏额外内容 */
    headerExtra?: Snippet;
    /** 折叠时显示的迷你内容（摘要信息） */
    miniContent?: Snippet;
    /** Bento 风格：背景组件 */
    background?: Snippet;
    /** Bento 风格：描述文字 */
    description?: string;
    /** Bento 风格：CTA 链接 */
    href?: string;
    /** Bento 风格：CTA 文字 */
    cta?: string;
    /** 启用 Bento 悬停动画 */
    bentoHover?: boolean;
    /** Magic Card：渐变光圈大小（自适应卡片尺寸） */
    magicGradientSize?: number;
    /** Magic Card：渐变颜色（默认使用主题 primary 色） */
    magicGradientColor?: string;
    /** Magic Card：渐变透明度 */
    magicGradientOpacity?: number;
    /** 是否启用尺寸编辑模式（节点模式下） */
    editMode?: boolean;
    /** 当前宽度（grid 列数） */
    currentW?: number;
    /** 宽度变化回调 */
    onWidthChange?: (delta: number) => void;
  }

  let {
    id: _id,
    title,
    icon: Icon,
    iconClass = 'text-muted-foreground',
    collapsible = false,
    defaultExpanded = true,
    isFullscreen = false,
    hideHeader = false,
    compact = false,
    fullHeight: fullHeightProp = false,
    class: className = '',
    children,
    headerExtra,
    miniContent,
    background,
    description,
    href,
    cta,
    bentoHover = false,
    magicGradientSize,
    magicGradientColor = "hsl(var(--primary) / 0.4)",
    magicGradientOpacity = 0.8,
    editMode = false,
    currentW = 1,
    onWidthChange,
  }: Props = $props();

  // isFullscreen 自动启用 fullHeight
  let fullHeight = $derived(fullHeightProp || isFullscreen);
  
  let isExpanded = $state(true);
  
  // 响应 defaultExpanded 变化
  $effect(() => {
    isExpanded = defaultExpanded;
  });

  // 获取面板设置（透明度和模糊）
  let panelSettings = $state(settingsManager.getSettings().panels);
  
  // 计算卡片样式 - 使用 color-mix 实现带颜色的透明效果
  let cardStyle = $derived(
    `background: color-mix(in srgb, var(--card) ${panelSettings.topToolbarOpacity * 0.4}%, transparent); backdrop-filter: blur(${panelSettings.topToolbarBlur}px);`
  );

  // ========== Magic Card 鼠标跟随效果 ==========
  let cardRef: HTMLDivElement | undefined = $state();
  let mouseX = $state(0);
  let mouseY = $state(0);
  let isHovering = $state(false);
  let cardWidth = $state(200);
  let cardHeight = $state(200);

  // 自适应渐变大小：基于卡片对角线长度
  let adaptiveGradientSize = $derived(
    magicGradientSize ?? Math.max(cardWidth, cardHeight) * 0.8
  );

  // 计算渐变背景样式
  let gradientStyle = $derived(
    `radial-gradient(${adaptiveGradientSize}px circle at ${mouseX}px ${mouseY}px, ${magicGradientColor}, transparent 100%)`
  );

  function handleMouseMove(e: MouseEvent) {
    if (!cardRef) return;
    const rect = cardRef.getBoundingClientRect();
    mouseX = e.clientX - rect.left;
    mouseY = e.clientY - rect.top;
  }

  function handleMouseEnter() {
    isHovering = true;
    if (cardRef) {
      cardWidth = cardRef.offsetWidth;
      cardHeight = cardRef.offsetHeight;
    }
  }

  function handleMouseLeave() {
    isHovering = false;
  }

  onMount(() => {
    settingsManager.addListener((s) => {
      panelSettings = s.panels;
    });
    // 初始化卡片尺寸
    if (cardRef) {
      cardWidth = cardRef.offsetWidth;
      cardHeight = cardRef.offsetHeight;
    }
  });

  function toggleExpanded() {
    if (collapsible) isExpanded = !isExpanded;
  }
</script>

<div 
  bind:this={cardRef}
  onmousemove={handleMouseMove}
  onmouseenter={handleMouseEnter}
  onmouseleave={handleMouseLeave}
  class="block-card group relative overflow-hidden rounded-xl
    {isFullscreen ? 'h-full flex flex-col' : ''} 
    {fullHeight ? 'h-full flex flex-col' : ''} 
    {bentoHover ? 'bento-card' : ''}
    {className}"
  style={cardStyle}
>
  <!-- Bento 背景层 -->
  {#if background}
    <div class="absolute inset-0 z-0 overflow-hidden">
      {@render background()}
    </div>
  {/if}
  
  <!-- 悬停遮罩层 -->
  <div class="pointer-events-none absolute inset-0 z-[1] transition-all duration-300 group-hover:bg-black/[.03] dark:group-hover:bg-neutral-800/10"></div>
  
  <!-- Magic Card 渐变光效层 -->
  <div
    class="magic-glow pointer-events-none absolute -inset-px rounded-xl z-[2]"
    style="--glow-bg: {gradientStyle}; --glow-opacity: {isHovering ? magicGradientOpacity : 0};"
  ></div>
  
  <!-- 标题栏 -->
  {#if !hideHeader}
    <div 
      class="relative z-10 flex items-center justify-between shrink-0 transition-all duration-300
        {compact ? 'px-2 py-1' : (isFullscreen ? 'p-3 border-b border-border/50' : 'p-3')}
        {bentoHover ? 'group-hover:-translate-y-1' : ''}"
    >
      <button
        type="button"
        class="flex items-center gap-1.5 text-left"
        onclick={toggleExpanded}
        disabled={!collapsible}
      >
        {#if collapsible}
          {#if isExpanded}
            <ChevronDown class="h-3 w-3 text-muted-foreground transition-transform duration-300" />
          {:else}
            <ChevronRight class="h-3 w-3 text-muted-foreground transition-transform duration-300" />
          {/if}
        {/if}
        
        {#if Icon}
          <Icon class="w-4 h-4 origin-left transition-all duration-300 ease-in-out {iconClass}
            {bentoHover ? 'group-hover:scale-90' : ''}" />
        {/if}
        
        <span class="transition-colors duration-300 {isFullscreen ? 'font-semibold text-foreground' : 'text-xs font-semibold text-foreground/90'}">{title}</span>
      </button>
      
      {#if headerExtra}
        <div class="flex items-center gap-1">
          {@render headerExtra()}
        </div>
      {/if}
      
      <!-- 尺寸编辑按钮（节点模式下） -->
      {#if editMode && onWidthChange}
        <div class="flex items-center gap-0.5 ml-1">
          <button
            type="button"
            class="p-0.5 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
            onclick={() => onWidthChange(-1)}
            disabled={currentW <= 1}
            title="减小宽度"
          >
            <Minus class="w-3 h-3" />
          </button>
          <span class="text-xs text-muted-foreground min-w-[1.5rem] text-center">{currentW}</span>
          <button
            type="button"
            class="p-0.5 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
            onclick={() => onWidthChange(1)}
            disabled={currentW >= 2}
            title="增大宽度"
          >
            <Plus class="w-3 h-3" />
          </button>
        </div>
      {/if}
    </div>
  {/if}
  
  <!-- Bento 描述文字 -->
  {#if description && !hideHeader}
    <p class="relative z-10 px-3 pb-2 text-sm text-muted-foreground transition-all duration-300
      {bentoHover ? 'group-hover:-translate-y-1' : ''}">
      {description}
    </p>
  {/if}
  
  <!-- 内容区 -->
  {#if isExpanded || hideHeader}
    <div 
      class="relative z-10 transition-all duration-300 {hideHeader ? '' : (compact ? 'px-2 pb-2' : 'px-3 pb-3')} {fullHeight ? 'flex-1 min-h-0 flex flex-col overflow-hidden' : ''} {bentoHover ? 'group-hover:-translate-y-1' : ''}"
      transition:slide={{ duration: 150 }}
    >
      {@render children()}
    </div>
  {:else if miniContent}
    <div class="relative z-10 px-3 pb-2 text-sm text-muted-foreground">
      {@render miniContent()}
    </div>
  {/if}
  
  <!-- Bento CTA 按钮（悬停显示） -->
  {#if cta && href && bentoHover}
    <div class="pointer-events-none absolute bottom-0 left-0 right-0 z-10 flex translate-y-10 transform-gpu flex-row items-center p-3 opacity-0 transition-all duration-300 group-hover:translate-y-0 group-hover:opacity-100">
      <a 
        {href} 
        class="pointer-events-auto inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium text-foreground/80 hover:text-foreground hover:bg-muted/50 transition-colors"
      >
        {cta}
        <ArrowRight class="h-4 w-4" />
      </a>
    </div>
  {/if}
</div>

<style>
  /* Magic Card 渐变光效 */
  .magic-glow {
    background: var(--glow-bg);
    opacity: var(--glow-opacity);
    transition: opacity 0.3s ease;
  }
  
  /* Bento 卡片样式 - 精致阴影和边框 */
  .bento-card {
    /* 亮色模式 */
    box-shadow: 
      0 0 0 1px rgba(0, 0, 0, 0.03),
      0 2px 4px rgba(0, 0, 0, 0.05),
      0 12px 24px rgba(0, 0, 0, 0.05);
    border: 1px solid transparent;
  }
  
  /* 暗色模式 */
  :global(.dark) .bento-card {
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 -20px 80px -20px rgba(255, 255, 255, 0.12) inset;
  }
  
  /* 普通卡片保持原有边框 */
  .block-card:not(.bento-card) {
    border: 1px solid hsl(var(--border));
  }
  
  /* 全屏模式特殊边框 */
  .block-card:not(.bento-card).h-full {
    border-color: hsl(var(--primary) / 0.4);
  }
</style>
