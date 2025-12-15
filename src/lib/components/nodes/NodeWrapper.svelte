<script lang="ts">
  /**
   * 通用节点包装器
   * 提供：关闭、折叠/展开、固定 功能
   */
  import { X, ChevronDown, ChevronRight, Pin, PinOff } from '@lucide/svelte';
  import { flowStore } from '$lib/stores';
  import type { Snippet } from 'svelte';

  interface Props {
    /** 节点 ID */
    nodeId: string;
    /** 节点标题 */
    title: string;
    /** 标题图标 */
    icon?: typeof X;
    /** 是否可折叠，默认 true */
    collapsible?: boolean;
    /** 是否可关闭，默认 true */
    closable?: boolean;
    /** 是否可固定，默认 true */
    pinnable?: boolean;
    /** 初始折叠状态 */
    defaultCollapsed?: boolean;
    /** 节点内容 */
    children: Snippet;
    /** 标题栏额外内容 */
    headerExtra?: Snippet;
  }

  let {
    nodeId,
    title,
    icon: Icon,
    collapsible = true,
    closable = true,
    pinnable = true,
    defaultCollapsed = false,
    children,
    headerExtra
  }: Props = $props();

  // 状态 - 使用函数初始化避免警告
  let collapsed = $state.raw(false);
  let pinned = $state(false);
  
  // 初始化折叠状态
  $effect(() => {
    if (defaultCollapsed) collapsed = true;
  });

  // 关闭节点
  function handleClose() {
    flowStore.removeNode(nodeId);
  }

  // 切换折叠
  function toggleCollapse() {
    if (collapsible) {
      collapsed = !collapsed;
    }
  }

  // 切换固定
  function togglePin() {
    pinned = !pinned;
  }
</script>

<div class="bg-card/95 backdrop-blur border rounded-lg shadow-lg overflow-hidden min-w-[200px]">
  <!-- 标题栏 -->
  <div 
    class="flex items-center justify-between px-3 py-2 bg-muted/50 border-b cursor-move select-none"
  >
    <!-- 左侧：折叠按钮 + 图标 + 标题 -->
    <div class="flex items-center gap-2 flex-1 min-w-0">
      {#if collapsible}
        <button
          class="p-0.5 rounded hover:bg-muted transition-colors"
          onclick={toggleCollapse}
          title={collapsed ? '展开' : '折叠'}
        >
          {#if collapsed}
            <ChevronRight class="w-4 h-4" />
          {:else}
            <ChevronDown class="w-4 h-4" />
          {/if}
        </button>
      {/if}
      
      {#if Icon}
        <Icon class="w-4 h-4 text-muted-foreground shrink-0" />
      {/if}
      
      <span class="text-sm font-medium truncate">{title}</span>
    </div>

    <!-- 右侧：操作按钮 -->
    <div class="flex items-center gap-0.5 ml-2">
      {#if headerExtra}
        {@render headerExtra()}
      {/if}
      
      {#if pinnable}
        <button
          class="p-1 rounded hover:bg-muted transition-colors {pinned ? 'text-primary' : 'text-muted-foreground'}"
          onclick={togglePin}
          title={pinned ? '取消固定' : '固定'}
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

  <!-- 内容区 -->
  {#if !collapsed}
    <div class="nodrag">
      {@render children()}
    </div>
  {/if}
</div>
