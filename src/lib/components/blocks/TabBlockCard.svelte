<script lang="ts">
  /**
   * TabBlockCard - Tab 容器区块组件（动态版）
   * 支持运行时动态添加/移除/排序子区块
   * 标签栏替代子区块的标题栏，节省界面空间
   */
  import type { Snippet, Component } from 'svelte';
  import { getTabBlockChildren, getNodeBlockLayout, type BlockDefinition, type TabBlockState } from './blockRegistry';
  import { Plus, X, GripVertical, ChevronDown } from '@lucide/svelte';
  import { flip } from 'svelte/animate';
  import { dndzone } from 'svelte-dnd-action';

  interface Props {
    /** 区块 ID */
    id: string;
    /** 子区块 ID 列表（可绑定） */
    children?: string[];
    /** 节点类型（用于从注册表获取区块定义） */
    nodeType: string;
    /** 是否全屏模式 */
    isFullscreen?: boolean;
    /** 初始活动标签索引 */
    defaultActiveTab?: number;
    /** 标签切换回调 */
    onTabChange?: (index: number) => void;
    /** 状态变化回调（用于持久化） */
    onStateChange?: (state: TabBlockState) => void;
    /** 初始状态（从持久化恢复） */
    initialState?: TabBlockState;
    /** 子区块内容渲染器 */
    renderContent: Snippet<[string]>;
    /** 自定义类名 */
    class?: string;
    /** 删除此 Tab 区块的回调 */
    onRemove?: () => void;
  }

  let {
    id,
    children: initialChildren = [],
    nodeType,
    isFullscreen = false,
    defaultActiveTab = 0,
    onTabChange,
    onStateChange,
    initialState,
    renderContent,
    class: className = '',
    onRemove
  }: Props = $props();

  // 动态子区块列表（从初始状态恢复或使用传入的）
  let childIds = $state<string[]>(initialState?.children ?? initialChildren);
  
  // 从初始状态恢复活动标签
  let activeTab = $state(initialState?.activeTab ?? defaultActiveTab);
  
  // 是否显示添加菜单
  let showAddMenu = $state(false);
  
  // 是否处于编辑模式（可拖拽排序/删除）
  let editMode = $state(false);

  // 从注册表获取有效的子区块定义
  let childBlocks = $derived(getTabBlockChildren(nodeType, childIds));

  // 获取所有可用的区块（用于添加菜单）
  let availableBlocks = $derived(() => {
    const layout = getNodeBlockLayout(nodeType);
    if (!layout) return [];
    // 过滤掉已添加的和 Tab 容器本身
    return layout.blocks.filter(b => 
      !b.isTabContainer && 
      !childIds.includes(b.id)
    );
  });

  // 当前活动的子区块 ID
  let activeBlockId = $derived(childBlocks[activeTab]?.id ?? childBlocks[0]?.id ?? '');

  // 用于 dnd 的数据格式
  let dndItems = $derived(childBlocks.map((b, i) => ({ id: b.id, block: b, index: i })));

  // 切换标签
  function switchTab(index: number) {
    if (index >= 0 && index < childBlocks.length) {
      activeTab = index;
      onTabChange?.(index);
      saveState();
    }
  }

  // 添加子区块
  function addChild(blockId: string) {
    if (!childIds.includes(blockId)) {
      childIds = [...childIds, blockId];
      showAddMenu = false;
      saveState();
    }
  }

  // 移除子区块
  function removeChild(blockId: string) {
    const index = childIds.indexOf(blockId);
    if (index !== -1) {
      childIds = childIds.filter(id => id !== blockId);
      // 调整活动标签
      if (activeTab >= childIds.length && childIds.length > 0) {
        activeTab = childIds.length - 1;
      }
      saveState();
    }
  }

  // 处理拖拽排序
  function handleDndConsider(e: CustomEvent<{ items: typeof dndItems }>) {
    childIds = e.detail.items.map(item => item.id);
  }

  function handleDndFinalize(e: CustomEvent<{ items: typeof dndItems }>) {
    childIds = e.detail.items.map(item => item.id);
    saveState();
  }

  // 保存状态
  function saveState() {
    onStateChange?.({
      activeTab,
      children: childIds
    });
  }

  // 获取当前状态
  export function getState(): TabBlockState {
    return { activeTab, children: childIds };
  }

  // 获取当前子区块列表
  export function getChildren(): string[] {
    return childIds;
  }

  // 确保 activeTab 在有效范围内
  $effect(() => {
    if (activeTab >= childBlocks.length && childBlocks.length > 0) {
      activeTab = 0;
      saveState();
    }
  });
</script>

<div 
  class="tab-block-card h-full flex flex-col {isFullscreen ? 'border border-primary/40 rounded-md bg-card/80 backdrop-blur-sm' : 'bg-card rounded-lg border shadow-sm'} {className}"
>
  <!-- 标签栏 -->
  <div class="tab-bar drag-handle flex items-center {isFullscreen ? 'p-1.5 border-b bg-muted/30' : 'p-1'} shrink-0 cursor-move">
    <!-- 标签列表（支持拖拽排序） -->
    {#if editMode && childBlocks.length > 0}
      <div 
        class="flex items-center gap-0.5 flex-1 overflow-x-auto"
        use:dndzone={{ items: dndItems, flipDurationMs: 200, type: 'tab-items' }}
        onconsider={handleDndConsider}
        onfinalize={handleDndFinalize}
      >
        {#each dndItems as item (item.id)}
          {@const Icon = item.block.icon as Component | undefined}
          <div 
            class="tab-item-edit flex items-center gap-1 px-1.5 py-1 rounded-md text-sm font-medium bg-muted/50 border border-dashed cursor-move"
            animate:flip={{ duration: 200 }}
          >
            <GripVertical class="w-3 h-3 text-muted-foreground" />
            {#if Icon}
              <Icon class="w-3.5 h-3.5 {item.block.iconClass}" />
            {/if}
            <button
              type="button"
              class="p-0.5 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive"
              onclick={() => removeChild(item.id)}
            >
              <X class="w-3 h-3" />
            </button>
          </div>
        {/each}
      </div>
    {:else}
      <div class="flex items-center gap-0.5 flex-1 overflow-x-auto">
        {#each childBlocks as block, index}
          {@const isActive = index === activeTab}
          {@const Icon = block.icon as Component | undefined}
          <button
            type="button"
            class="tab-item flex items-center justify-center p-1.5 rounded-md transition-all
              {isActive 
                ? 'bg-primary text-primary-foreground shadow-sm' 
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}"
            onclick={() => switchTab(index)}
            title={block.title}
          >
            {#if Icon}
              <Icon class="w-4 h-4 {isActive ? '' : block.iconClass}" />
            {/if}
          </button>
        {/each}
      </div>
    {/if}

    <!-- 操作按钮 -->
    <div class="flex items-center gap-1 ml-2 shrink-0">
      <!-- 编辑模式切换 -->
      {#if childBlocks.length > 0}
        <button
          type="button"
          class="p-1.5 rounded-md transition-all {editMode ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}"
          onclick={() => editMode = !editMode}
          title={editMode ? '完成编辑' : '编辑标签'}
        >
          <GripVertical class="w-3.5 h-3.5" />
        </button>
      {/if}

      <!-- 删除此 Tab 区块 -->
      {#if onRemove}
        <button
          type="button"
          class="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all"
          onclick={onRemove}
          title="删除此 Tab 区块"
        >
          <X class="w-3.5 h-3.5" />
        </button>
      {/if}
      
      <!-- 添加按钮 -->
      <div class="relative">
        <button
          type="button"
          class="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all"
          onclick={() => showAddMenu = !showAddMenu}
          title="添加区块"
        >
          <Plus class="w-3.5 h-3.5" />
          <ChevronDown class="w-2.5 h-2.5 absolute -bottom-0.5 -right-0.5" />
        </button>
        
        <!-- 添加菜单 -->
        {#if showAddMenu}
          <div class="absolute right-0 top-full mt-1 z-50 min-w-[160px] bg-popover border rounded-lg shadow-lg p-1">
            {#if availableBlocks().length > 0}
              {#each availableBlocks() as block}
                {@const Icon = block.icon as Component | undefined}
                <button
                  type="button"
                  class="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-muted/50 transition-all"
                  onclick={() => addChild(block.id)}
                >
                  {#if Icon}
                    <Icon class="w-4 h-4 {block.iconClass}" />
                  {/if}
                  <span>{block.title}</span>
                </button>
              {/each}
            {:else}
              <div class="px-3 py-2 text-sm text-muted-foreground">
                所有区块已添加
              </div>
            {/if}
          </div>
        {/if}
      </div>
    </div>
  </div>
  
  <!-- 内容区 -->
  <div class="tab-content flex-1 min-h-0 overflow-auto {isFullscreen ? 'p-2' : 'p-2'}">
    {#if activeBlockId}
      {@render renderContent(activeBlockId)}
    {:else}
      <div class="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
        <Plus class="w-8 h-8 opacity-50" />
        <span class="text-sm">点击 + 添加区块</span>
      </div>
    {/if}
  </div>
</div>

<!-- 点击外部关闭菜单 -->
{#if showAddMenu}
  <button 
    type="button"
    class="fixed inset-0 z-40" 
    onclick={() => showAddMenu = false}
    aria-label="关闭菜单"
  ></button>
{/if}

<style>
  .tab-bar::-webkit-scrollbar {
    height: 4px;
  }
  
  .tab-bar::-webkit-scrollbar-track {
    background: transparent;
  }
  
  .tab-bar::-webkit-scrollbar-thumb {
    background: hsl(var(--muted-foreground) / 0.3);
    border-radius: 2px;
  }
  
  .tab-item-edit {
    user-select: none;
  }
</style>
