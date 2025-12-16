<script lang="ts">
  /**
   * BlockCard - 通用区块卡片容器
   * 支持普通模式（Bento Grid）和全屏模式（GridStack）
   * 参考 neoview 的 CollapsibleCard 设计
   */
  import { ChevronDown, ChevronRight } from '@lucide/svelte';
  import { slide } from 'svelte/transition';
  import type { Snippet } from 'svelte';

  interface Props {
    /** 区块 ID */
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
    /** 是否全屏模式 */
    isFullscreen?: boolean;
    /** 隐藏标题栏 */
    hideHeader?: boolean;
    /** 紧凑模式 */
    compact?: boolean;
    /** 占满高度 */
    fullHeight?: boolean;
    /** 自定义类名 */
    class?: string;
    /** 内容 */
    children: Snippet;
    /** 标题栏额外内容 */
    headerExtra?: Snippet;
  }

  let {
    id,
    title,
    icon: Icon,
    iconClass = 'text-muted-foreground',
    collapsible = false,
    defaultExpanded = true,
    isFullscreen = false,
    hideHeader = false,
    compact = false,
    fullHeight = false,
    class: className = '',
    children,
    headerExtra
  }: Props = $props();

  let isExpanded = $state(defaultExpanded);

  function toggleExpanded() {
    if (collapsible) isExpanded = !isExpanded;
  }
</script>

<div 
  class="block-card {isFullscreen ? 'h-full flex flex-col border border-primary/40 rounded-md bg-card/80 backdrop-blur-sm' : 'bg-card rounded-lg border shadow-sm'} {fullHeight ? 'flex-1 min-h-0' : ''} {className}"
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
  {/if}
</div>
