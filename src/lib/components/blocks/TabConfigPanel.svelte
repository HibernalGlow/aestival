<script lang="ts">
  /**
   * TabConfigPanel - Tab 区块配置面板
   * 用于选择要合并到 Tab 的区块和排序
   */
  import type { Component } from 'svelte';
  import { onMount } from 'svelte';
  import { getNodeBlockLayout, type BlockDefinition } from './blockRegistry';
  import { subscribeNodeConfig, type NodeConfig } from '$lib/stores/nodeLayoutStore';
  import { Plus, X, GripVertical, Check } from '@lucide/svelte';
  import { flip } from 'svelte/animate';
  import { dndzone } from 'svelte-dnd-action';

  interface Props {
    /** 节点类型 */
    nodeType: string;
    /** 创建回调 */
    onCreate: (blockIds: string[]) => void;
    /** 取消回调 */
    onCancel: () => void;
  }

  let { nodeType, onCreate, onCancel }: Props = $props();
  
  // 订阅 store 变化，响应式获取已使用的区块 ID
  let nodeConfig = $state<NodeConfig | undefined>(undefined);
  let usedBlockIds = $derived(
    nodeConfig?.fullscreen.tabGroups.flatMap(g => g.blockIds) ?? []
  );
  
  onMount(() => {
    return subscribeNodeConfig(nodeType, (config) => {
      nodeConfig = config;
    });
  });

  // 获取所有可用区块
  let allBlocks = $derived(() => {
    const layout = getNodeBlockLayout(nodeType);
    if (!layout) return [];
    return layout.blocks.filter(b => !b.isTabContainer);
  });

  // 已选择的区块（用于排序）
  let selectedBlocks = $state<{ id: string; block: BlockDefinition }[]>([]);
  
  // 可选择的区块（未选中的）
  let availableBlocks = $derived(() => {
    const selectedIds = new Set(selectedBlocks.map(s => s.id));
    return allBlocks().filter(b => !selectedIds.has(b.id) && !usedBlockIds.includes(b.id));
  });

  // 添加区块到选择列表
  function addBlock(block: BlockDefinition) {
    selectedBlocks = [...selectedBlocks, { id: block.id, block }];
  }

  // 从选择列表移除
  function removeBlock(blockId: string) {
    selectedBlocks = selectedBlocks.filter(s => s.id !== blockId);
  }

  // 拖拽排序处理
  function handleDndConsider(e: CustomEvent<{ items: typeof selectedBlocks }>) {
    selectedBlocks = e.detail.items;
  }

  function handleDndFinalize(e: CustomEvent<{ items: typeof selectedBlocks }>) {
    selectedBlocks = e.detail.items;
  }

  // 创建 Tab
  function handleCreate() {
    if (selectedBlocks.length < 2) return;
    onCreate(selectedBlocks.map(s => s.id));
    // 创建后清空已选列表，准备创建下一个
    selectedBlocks = [];
  }
</script>

<div class="tab-config-panel flex items-center gap-3 flex-wrap">
  <!-- 可选区块列表 -->
  <div class="flex items-center gap-1">
    <span class="text-xs text-muted-foreground mr-1">可选:</span>
    {#each availableBlocks() as block}
      {@const Icon = block.icon as Component | undefined}
      <button
        type="button"
        class="flex items-center gap-1 px-2 py-1 rounded-md text-xs border border-dashed hover:border-primary hover:bg-primary/10 transition-all"
        onclick={() => addBlock(block)}
        title="点击添加"
      >
        {#if Icon}
          <Icon class="w-3 h-3 {block.iconClass}" />
        {/if}
        <span>{block.title}</span>
        <Plus class="w-3 h-3 text-muted-foreground" />
      </button>
    {/each}
    {#if availableBlocks().length === 0}
      <span class="text-xs text-muted-foreground">无可用区块</span>
    {/if}
  </div>

  <!-- 分隔线 -->
  <div class="h-6 w-px bg-border"></div>

  <!-- 已选区块（可拖拽排序） -->
  <div class="flex items-center gap-1">
    <span class="text-xs text-muted-foreground mr-1">已选:</span>
    {#if selectedBlocks.length > 0}
      <div 
        class="flex items-center gap-1"
        use:dndzone={{ items: selectedBlocks, flipDurationMs: 150, type: 'tab-config' }}
        onconsider={handleDndConsider}
        onfinalize={handleDndFinalize}
      >
        {#each selectedBlocks as item (item.id)}
          {@const Icon = item.block.icon as Component | undefined}
          <div 
            class="flex items-center gap-1 px-2 py-1 rounded-md text-xs bg-primary/20 border border-primary/40 cursor-move"
            animate:flip={{ duration: 150 }}
          >
            <GripVertical class="w-3 h-3 text-muted-foreground" />
            {#if Icon}
              <Icon class="w-3 h-3 {item.block.iconClass}" />
            {/if}
            <span>{item.block.title}</span>
            <button
              type="button"
              class="p-0.5 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive"
              onclick={() => removeBlock(item.id)}
            >
              <X class="w-3 h-3" />
            </button>
          </div>
        {/each}
      </div>
    {:else}
      <span class="text-xs text-muted-foreground">拖拽或点击添加至少2个区块</span>
    {/if}
  </div>

  <!-- 分隔线 -->
  <div class="h-6 w-px bg-border"></div>

  <!-- 操作按钮 -->
  <div class="flex items-center gap-2">
    <button
      type="button"
      class="flex items-center gap-1 px-3 py-1 rounded-md text-xs bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
      onclick={handleCreate}
      disabled={selectedBlocks.length < 2}
    >
      <Check class="w-3 h-3" />
      创建 Tab
    </button>
    <button
      type="button"
      class="flex items-center gap-1 px-3 py-1 rounded-md text-xs border hover:bg-muted transition-all"
      onclick={onCancel}
    >
      <X class="w-3 h-3" />
      取消
    </button>
  </div>
</div>
