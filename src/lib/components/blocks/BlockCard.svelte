<script lang="ts">
  /**
   * BlockCard - 通用区块卡片容器
   * 支持普通模式（Bento Grid）和全屏模式（GridStack）
   * 使用 settingsManager 的面板透明度和模糊设置
   */
  import { ChevronDown, ChevronRight } from '@lucide/svelte';
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
    miniContent
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
  // 乘以 0.6 让透明度效果更明显
  let cardStyle = $derived(
    `background: color-mix(in srgb, var(--card) ${panelSettings.topToolbarOpacity * 0.4}%, transparent); backdrop-filter: blur(${panelSettings.topToolbarBlur}px);`
  );

  onMount(() => {
    // 监听设置变化
    settingsManager.addListener((s) => {
      panelSettings = s.panels;
    });
  });

  function toggleExpanded() {
    if (collapsible) isExpanded = !isExpanded;
  }
</script>

<div 
  class="block-card rounded-{isFullscreen ? 'md' : 'lg'} border {isFullscreen ? 'h-full flex flex-col border-primary/40' : 'shadow-sm'} {fullHeight ? 'h-full flex flex-col' : ''} {className}"
  style={cardStyle}
>
  <!-- 标题栏 -->
  {#if !hideHeader}
    <div 
      class="flex items-center justify-between {compact ? 'px-2 py-1' : (isFullscreen ? 'p-3 border-b bg-muted/30' : 'p-3')} shrink-0"
    >
      <button
        type="button"
        class="flex items-center gap-1.5 text-left"
        onclick={toggleExpanded}
        disabled={!collapsible}
      >
        {#if collapsible}
          {#if isExpanded}
            <ChevronDown class="h-3 w-3 text-muted-foreground" />
          {:else}
            <ChevronRight class="h-3 w-3 text-muted-foreground" />
          {/if}
        {/if}
        
        {#if Icon}
          <Icon class="w-4 h-4 {iconClass}" />
        {/if}
        
        <span class="{isFullscreen ? 'font-semibold' : 'text-xs font-semibold'}">{title}</span>
      </button>
      
      {#if headerExtra}
        <div class="flex items-center gap-1">
          {@render headerExtra()}
        </div>
      {/if}
    </div>
  {/if}
  
  <!-- 内容区 -->
  {#if isExpanded || hideHeader}
    <div 
      class="{hideHeader ? '' : (compact ? 'px-2 pb-2' : (isFullscreen ? 'flex-1 overflow-auto p-2' : 'px-3 pb-3'))} {fullHeight ? 'flex-1 min-h-0 flex flex-col overflow-hidden' : ''}"
      transition:slide={{ duration: 150 }}
    >
      {@render children()}
    </div>
  {:else if miniContent}
    <!-- 折叠时的迷你内容 -->
    <div class="px-3 pb-2 text-sm text-muted-foreground">
      {@render miniContent()}
    </div>
  {/if}
</div>
