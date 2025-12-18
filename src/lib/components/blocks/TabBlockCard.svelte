<script lang="ts">
  /**
   * TabBlockCard - Tab 容器区块组件
   * 状态管理：使用 nodeLayoutStore 内嵌的 Tab 状态
   */
  import type { Snippet, Component } from 'svelte';
  import { getTabBlockChildren, getNodeBlockLayout } from './blockRegistry';
  import { Plus, X, GripVertical, ChevronDown } from '@lucide/svelte';
  import { flip } from 'svelte/animate';
  import { dndzone } from 'svelte-dnd-action';
  import { getTabState, setActiveTab, addChildToTab, removeChildFromTab, reorderTabChildren, subscribeNodeConfig } from '$lib/stores/nodeLayoutStore';
  import { onMount } from 'svelte';

  interface Props {
    id: string;
    nodeType: string;
    mode: 'fullscreen' | 'normal';
    isFullscreen?: boolean;
    renderContent: Snippet<[string]>;
    class?: string;
    onRemove?: () => void;
  }

  let { id, nodeType, mode, isFullscreen = false, renderContent, class: className = '', onRemove }: Props = $props();

  function getInitialState() {
    const storeState = getTabState(nodeType, mode, id);
    console.log('[TabBlockCard] getInitialState:', { 
      nodeType, 
      mode, 
      id, 
      hasState: !!storeState,
      children: storeState?.children,
      originalPositions: storeState?.originalPositions
    });
    return storeState ? { children: storeState.children, activeTab: storeState.activeTab } : { children: [], activeTab: 0 };
  }

  let childIds = $state<string[]>(getInitialState().children);
  let activeTab = $state(getInitialState().activeTab);
  let showAddMenu = $state(false);
  let editMode = $state(false);

  onMount(() => {
    const unsubscribe = subscribeNodeConfig(nodeType, () => {
      const state = getTabState(nodeType, mode, id);
      if (state) { childIds = state.children; activeTab = state.activeTab; }
    });
    return unsubscribe;
  });

  let childBlocks = $derived(getTabBlockChildren(nodeType, childIds));
  let availableBlocks = $derived(() => {
    const layout = getNodeBlockLayout(nodeType);
    return layout ? layout.blocks.filter(b => !b.isTabContainer && !childIds.includes(b.id)) : [];
  });
  let activeBlockId = $derived(childBlocks[activeTab]?.id ?? childBlocks[0]?.id ?? '');
  let dndItems = $derived(childBlocks.map((b, i) => ({ id: b.id, block: b, index: i })));

  function switchTab(index: number) { if (index >= 0 && index < childBlocks.length) setActiveTab(nodeType, mode, id, index); }
  function addChild(blockId: string) { if (!childIds.includes(blockId)) { addChildToTab(nodeType, mode, id, blockId); showAddMenu = false; } }
  function removeChild(blockId: string) { removeChildFromTab(nodeType, mode, id, blockId); }
  function handleDndConsider(e: CustomEvent<{ items: typeof dndItems }>) { childIds = e.detail.items.map(item => item.id); }
  function handleDndFinalize(e: CustomEvent<{ items: typeof dndItems }>) { reorderTabChildren(nodeType, mode, id, e.detail.items.map(item => item.id)); }

  export function getState() { return { activeTab, children: childIds }; }
  export function getChildren(): string[] { return childIds; }

  $effect(() => { if (activeTab >= childBlocks.length && childBlocks.length > 0) setActiveTab(nodeType, mode, id, 0); });
</script>

<div class="tab-block-card h-full flex flex-col {isFullscreen ? 'border border-primary/40 rounded-md bg-card/80 backdrop-blur-sm' : 'bg-card rounded-lg border shadow-sm'} {className}">
  <div class="tab-bar drag-handle flex items-center {isFullscreen ? 'p-1.5 border-b bg-muted/30' : 'p-1'} shrink-0 cursor-move">
    {#if editMode && childBlocks.length > 0}
      <div class="flex items-center gap-0.5 flex-1 overflow-x-auto" use:dndzone={{ items: dndItems, flipDurationMs: 200, type: 'tab-items' }} onconsider={handleDndConsider} onfinalize={handleDndFinalize}>
        {#each dndItems as item (item.id)}
          {@const Icon = item.block.icon as Component | undefined}
          <div class="tab-item-edit flex items-center gap-1 px-1.5 py-1 rounded-md text-sm font-medium bg-muted/50 border border-dashed cursor-move" animate:flip={{ duration: 200 }}>
            <GripVertical class="w-3 h-3 text-muted-foreground" />
            {#if Icon}<Icon class="w-3.5 h-3.5 {item.block.iconClass}" />{/if}
            <button type="button" class="p-0.5 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive" onclick={() => removeChild(item.id)}><X class="w-3 h-3" /></button>
          </div>
        {/each}
      </div>
    {:else}
      <div class="flex items-center gap-0.5 flex-1 overflow-x-auto">
        {#each childBlocks as block, index}
          {@const isActive = index === activeTab}
          {@const Icon = block.icon as Component | undefined}
          <button type="button" class="tab-item flex items-center justify-center p-1.5 rounded-md transition-all {isActive ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}" onclick={() => switchTab(index)} title={block.title}>
            {#if Icon}<Icon class="w-4 h-4 {isActive ? '' : block.iconClass}" />{/if}
          </button>
        {/each}
      </div>
    {/if}
    <div class="flex items-center gap-1 ml-2 shrink-0">
      {#if childBlocks.length > 0}
        <button type="button" class="p-1.5 rounded-md transition-all {editMode ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}" onclick={() => editMode = !editMode} title={editMode ? '完成编辑' : '编辑标签'}><GripVertical class="w-3.5 h-3.5" /></button>
      {/if}
      {#if onRemove}<button type="button" class="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all" onclick={onRemove} title="删除此 Tab 区块"><X class="w-3.5 h-3.5" /></button>{/if}
      <div class="relative">
        <button type="button" class="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all" onclick={() => showAddMenu = !showAddMenu} title="添加区块"><Plus class="w-3.5 h-3.5" /><ChevronDown class="w-2.5 h-2.5 absolute -bottom-0.5 -right-0.5" /></button>
        {#if showAddMenu}
          <div class="absolute right-0 top-full mt-1 z-50 min-w-[160px] bg-popover border rounded-lg shadow-lg p-1">
            {#if availableBlocks().length > 0}
              {#each availableBlocks() as block}
                {@const Icon = block.icon as Component | undefined}
                <button type="button" class="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-muted/50 transition-all" onclick={() => addChild(block.id)}>
                  {#if Icon}<Icon class="w-4 h-4 {block.iconClass}" />{/if}<span>{block.title}</span>
                </button>
              {/each}
            {:else}<div class="px-3 py-2 text-sm text-muted-foreground">所有区块已添加</div>{/if}
          </div>
        {/if}
      </div>
    </div>
  </div>
  <div class="tab-content flex-1 min-h-0 overflow-auto {isFullscreen ? 'p-2' : 'p-2'}">
    {#if activeBlockId}{@render renderContent(activeBlockId)}{:else}
      <div class="flex flex-col items-center justify-center h-full text-muted-foreground gap-2"><Plus class="w-8 h-8 opacity-50" /><span class="text-sm">点击 + 添加区块</span></div>
    {/if}
  </div>
</div>
{#if showAddMenu}<button type="button" class="fixed inset-0 z-40" onclick={() => showAddMenu = false} aria-label="关闭菜单"></button>{/if}

<style>
  .tab-bar::-webkit-scrollbar { height: 4px; }
  .tab-bar::-webkit-scrollbar-track { background: transparent; }
  .tab-bar::-webkit-scrollbar-thumb { background: hsl(var(--muted-foreground) / 0.3); border-radius: 2px; }
  .tab-item-edit { user-select: none; }
</style>
