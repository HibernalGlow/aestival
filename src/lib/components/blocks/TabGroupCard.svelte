<script lang="ts">
  /**
   * TabGroupCard - Tab 分组卡片组件
   * 
   * 虚拟分组模式：区块始终在 gridLayout 中，这里只负责渲染和切换
   */
  import type { Snippet, Component } from 'svelte';
  import type { TabGroup } from '$lib/stores/nodeLayoutStore';
  import { getBlockDefinition } from './blockRegistry';
  import { X, GripVertical, Ungroup } from '@lucide/svelte';
  import { flip } from 'svelte/animate';
  import { dndzone } from 'svelte-dnd-action';

  interface Props {
    /** Tab 分组配置 */
    group: TabGroup;
    /** 节点类型 */
    nodeType: string;
    /** 是否全屏模式 */
    isFullscreen?: boolean;
    /** 切换活动区块 */
    onSwitch: (index: number) => void;
    /** 解散分组 */
    onDissolve: () => void;
    /** 从分组移除区块 */
    onRemoveBlock?: (blockId: string) => void;
    /** 重排序区块 */
    onReorder?: (newOrder: string[]) => void;
    /** 渲染区块内容 */
    renderContent: Snippet<[string]>;
    class?: string;
  }

  let { 
    group, 
    nodeType, 
    isFullscreen = false, 
    onSwitch, 
    onDissolve, 
    onRemoveBlock,
    onReorder,
    renderContent, 
    class: className = '' 
  }: Props = $props();

  let editMode = $state(false);

  // 获取区块定义
  let blockDefs = $derived(
    group.blockIds.map(id => ({
      id,
      def: getBlockDefinition(nodeType, id)
    })).filter(item => item.def !== undefined)
  );

  // 当前活动区块 ID
  let activeBlockId = $derived(group.blockIds[group.activeIndex] ?? group.blockIds[0] ?? '');

  // 拖拽项
  let dndItems = $derived(blockDefs.map((item, i) => ({ id: item.id, def: item.def!, index: i })));

  function handleDndConsider(e: CustomEvent<{ items: typeof dndItems }>) {
    // 临时更新用于视觉反馈
  }

  function handleDndFinalize(e: CustomEvent<{ items: typeof dndItems }>) {
    const newOrder = e.detail.items.map(item => item.id);
    onReorder?.(newOrder);
  }
</script>

<div class="tab-group-card h-full flex flex-col {isFullscreen ? 'border-2 border-primary/60 rounded-md bg-card shadow-md' : 'bg-card rounded-lg border shadow-sm'} {className}">
  <!-- 标签栏 -->
  <div class="tab-bar drag-handle flex items-center {isFullscreen ? 'p-1.5 border-b bg-muted/30' : 'p-1'} shrink-0 cursor-move">
    {#if editMode && blockDefs.length > 0}
      <!-- 编辑模式：可拖拽排序和移除 -->
      <div 
        class="flex items-center gap-0.5 flex-1 overflow-x-auto" 
        use:dndzone={{ items: dndItems, flipDurationMs: 200, type: 'tab-group-items' }} 
        onconsider={handleDndConsider} 
        onfinalize={handleDndFinalize}
      >
        {#each dndItems as item (item.id)}
          {@const Icon = item.def.icon as Component | undefined}
          <div 
            class="tab-item-edit flex items-center gap-1 px-1.5 py-1 rounded-md text-sm font-medium bg-muted/50 border border-dashed cursor-move" 
            animate:flip={{ duration: 200 }}
          >
            <GripVertical class="w-3 h-3 text-muted-foreground" />
            {#if Icon}<Icon class="w-3.5 h-3.5 {item.def.iconClass}" />{/if}
            {#if onRemoveBlock && blockDefs.length > 2}
              <button 
                type="button" 
                class="p-0.5 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive" 
                onclick={() => onRemoveBlock(item.id)}
                title="从分组移除"
              >
                <X class="w-3 h-3" />
              </button>
            {/if}
          </div>
        {/each}
      </div>
    {:else}
      <!-- 普通模式：点击切换 -->
      <div class="flex items-center gap-0.5 flex-1 overflow-x-auto">
        {#each blockDefs as item, index}
          {@const isActive = index === group.activeIndex}
          {@const Icon = item.def?.icon as Component | undefined}
          <button 
            type="button" 
            class="tab-item flex items-center justify-center p-1.5 rounded-md transition-all {isActive ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}" 
            onclick={() => onSwitch(index)} 
            title={item.def?.title}
          >
            {#if Icon}<Icon class="w-4 h-4 {isActive ? '' : item.def?.iconClass}" />{/if}
          </button>
        {/each}
      </div>
    {/if}

    <!-- 操作按钮 -->
    <div class="flex items-center gap-1 ml-2 shrink-0">
      {#if blockDefs.length > 0}
        <button 
          type="button" 
          class="p-1.5 rounded-md transition-all {editMode ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}" 
          onclick={() => editMode = !editMode} 
          title={editMode ? '完成编辑' : '编辑标签'}
        >
          <GripVertical class="w-3.5 h-3.5" />
        </button>
      {/if}
      <button 
        type="button" 
        class="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all" 
        onclick={onDissolve} 
        title="解散分组"
      >
        <Ungroup class="w-3.5 h-3.5" />
      </button>
    </div>
  </div>

  <!-- 内容区域 -->
  <div class="tab-content flex-1 min-h-0 overflow-auto {isFullscreen ? 'p-2' : 'p-2'}">
    {#if activeBlockId}
      {@render renderContent(activeBlockId)}
    {:else}
      <div class="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
        <span class="text-sm">无可用区块</span>
      </div>
    {/if}
  </div>
</div>

<style>
  .tab-bar::-webkit-scrollbar { height: 4px; }
  .tab-bar::-webkit-scrollbar-track { background: transparent; }
  .tab-bar::-webkit-scrollbar-thumb { background: hsl(var(--muted-foreground) / 0.3); border-radius: 2px; }
  .tab-item-edit { user-select: none; }
</style>
