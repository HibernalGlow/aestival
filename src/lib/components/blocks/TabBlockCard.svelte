<script lang="ts">
  /**
   * TabBlockCard - 旧版 Tab 容器区块组件（已废弃）
   * 
   * @deprecated 请使用 TabGroupCard 替代
   * 此组件保留用于兼容性，将在后续版本移除
   */
  import type { Snippet, Component } from 'svelte';
  import type { TabGroup } from '$lib/stores/nodeLayoutStore';
  import { getBlockDefinition } from './blockRegistry';
  import { 
    getEffectiveTabGroups, 
    switchTabGroupActive, 
    removeBlockFromTabGroup, 
    reorderTabGroupBlocks,
    subscribeNodeConfig 
  } from '$lib/stores/nodeLayoutStore';
  import { Plus, X, GripVertical, ChevronDown, Ungroup } from '@lucide/svelte';
  import { flip } from 'svelte/animate';
  import { dndzone } from 'svelte-dnd-action';
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

  // 查找对应的 TabGroup
  function findGroup(): TabGroup | undefined {
    const groups = getEffectiveTabGroups(nodeType);
    return groups.find(g => g.id === id || g.blockIds.includes(id));
  }

  let group = $state<TabGroup | undefined>(findGroup());
  let editMode = $state(false);

  onMount(() => {
    const unsubscribe = subscribeNodeConfig(nodeType, () => {
      group = findGroup();
    });
    return unsubscribe;
  });

  // 获取区块定义
  let blockDefs = $derived(
    group ? group.blockIds.map(blockId => ({
      id: blockId,
      def: getBlockDefinition(nodeType, blockId)
    })).filter(item => item.def !== undefined) : []
  );

  let activeBlockId = $derived(group ? (group.blockIds[group.activeIndex] ?? group.blockIds[0] ?? '') : '');
  let dndItems = $derived(blockDefs.map((item, i) => ({ id: item.id, def: item.def!, index: i })));

  function switchTab(index: number) { 
    if (group && index >= 0 && index < group.blockIds.length) {
      switchTabGroupActive(nodeType, group.id, index);
    }
  }

  function removeChild(blockId: string) { 
    if (group) {
      removeBlockFromTabGroup(nodeType, group.id, blockId);
    }
  }

  function handleDndConsider(e: CustomEvent<{ items: typeof dndItems }>) {
    // 临时更新用于视觉反馈
  }

  function handleDndFinalize(e: CustomEvent<{ items: typeof dndItems }>) {
    if (group) {
      const newOrder = e.detail.items.map(item => item.id);
      reorderTabGroupBlocks(nodeType, group.id, newOrder);
    }
  }

  export function getState() { 
    return group ? { activeTab: group.activeIndex, children: group.blockIds } : { activeTab: 0, children: [] }; 
  }
  export function getChildren(): string[] { 
    return group?.blockIds ?? []; 
  }
</script>

{#if group}
<div class="tab-block-card h-full flex flex-col {isFullscreen ? 'border border-primary/40 rounded-md bg-card/80 backdrop-blur-sm' : 'bg-card rounded-lg border shadow-sm'} {className}">
  <div class="tab-bar drag-handle flex items-center {isFullscreen ? 'p-1.5 border-b bg-muted/30' : 'p-1'} shrink-0 cursor-move">
    {#if editMode && blockDefs.length > 0}
      <div class="flex items-center gap-0.5 flex-1 overflow-x-auto" use:dndzone={{ items: dndItems, flipDurationMs: 200, type: 'tab-items' }} onconsider={handleDndConsider} onfinalize={handleDndFinalize}>
        {#each dndItems as item (item.id)}
          {@const Icon = item.def.icon as Component | undefined}
          <div class="tab-item-edit flex items-center gap-1 px-1.5 py-1 rounded-md text-sm font-medium bg-muted/50 border border-dashed cursor-move" animate:flip={{ duration: 200 }}>
            <GripVertical class="w-3 h-3 text-muted-foreground" />
            {#if Icon}<Icon class="w-3.5 h-3.5 {item.def.iconClass}" />{/if}
            {#if blockDefs.length > 2}
              <button type="button" class="p-0.5 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive" onclick={() => removeChild(item.id)}><X class="w-3 h-3" /></button>
            {/if}
          </div>
        {/each}
      </div>
    {:else}
      <div class="flex items-center gap-0.5 flex-1 overflow-x-auto">
        {#each blockDefs as item, index}
          {@const isActive = index === group.activeIndex}
          {@const Icon = item.def?.icon as Component | undefined}
          <button type="button" class="tab-item flex items-center justify-center p-1.5 rounded-md transition-all {isActive ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}" onclick={() => switchTab(index)} title={item.def?.title}>
            {#if Icon}<Icon class="w-4 h-4 {isActive ? '' : item.def?.iconClass}" />{/if}
          </button>
        {/each}
      </div>
    {/if}
    <div class="flex items-center gap-1 ml-2 shrink-0">
      {#if blockDefs.length > 0}
        <button type="button" class="p-1.5 rounded-md transition-all {editMode ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}" onclick={() => editMode = !editMode} title={editMode ? '完成编辑' : '编辑标签'}><GripVertical class="w-3.5 h-3.5" /></button>
      {/if}
      {#if onRemove}
        <button type="button" class="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all" onclick={onRemove} title="解散分组"><Ungroup class="w-3.5 h-3.5" /></button>
      {/if}
    </div>
  </div>
  <div class="tab-content flex-1 min-h-0 overflow-auto {isFullscreen ? 'p-2' : 'p-2'}">
    {#if activeBlockId}{@render renderContent(activeBlockId)}{:else}
      <div class="flex flex-col items-center justify-center h-full text-muted-foreground gap-2"><Plus class="w-8 h-8 opacity-50" /><span class="text-sm">无可用区块</span></div>
    {/if}
  </div>
</div>
{:else}
<div class="h-full flex items-center justify-center text-muted-foreground">
  <span class="text-sm">Tab 分组不存在</span>
</div>
{/if}

<style>
  .tab-bar::-webkit-scrollbar { height: 4px; }
  .tab-bar::-webkit-scrollbar-track { background: transparent; }
  .tab-bar::-webkit-scrollbar-thumb { background: hsl(var(--muted-foreground) / 0.3); border-radius: 2px; }
  .tab-item-edit { user-select: none; }
</style>
