<script lang="ts">
  /**
   * BlockCard - 单个区块卡片
   * 提供统一的卡片样式，支持标题、图标、折叠
   */
  import type { BlockDefinition } from './types';
  import { ChevronDown, ChevronRight } from '@lucide/svelte';
  import type { Snippet } from 'svelte';

  interface Props {
    block: BlockDefinition;
    isFullscreen?: boolean;
    collapsed?: boolean;
    onToggleCollapse?: () => void;
    children: Snippet;
    /** 标题栏额外内容 */
    headerExtra?: Snippet;
  }

  let {
    block,
    isFullscreen = false,
    collapsed = false,
    onToggleCollapse,
    children,
    headerExtra
  }: Props = $props();

  const Icon = block.icon;
  const canCollapse = block.collapsible && !isFullscreen;
</script>

<div class="h-full flex flex-col">
  <!-- 标题栏 -->
  <div class="flex items-center gap-1.5 mb-2 shrink-0">
    {#if canCollapse}
      <button 
        class="p-0.5 rounded hover:bg-muted transition-colors"
        onclick={onToggleCollapse}
      >
        {#if collapsed}
          <ChevronRight class="w-3 h-3" />
        {:else}
          <ChevronDown class="w-3 h-3" />
        {/if}
      </button>
    {/if}
    
    {#if Icon}
      <Icon class="w-4 h-4 text-primary shrink-0" />
    {/if}
    
    <span class="text-xs font-semibold flex-1 truncate">{block.title}</span>
    
    {#if headerExtra}
      {@render headerExtra()}
    {/if}
  </div>
  
  <!-- 内容区 -->
  {#if !collapsed}
    <div class="flex-1 overflow-auto {isFullscreen ? '' : 'min-h-0'}">
      {@render children()}
    </div>
  {/if}
</div>
