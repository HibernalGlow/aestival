<script lang="ts">
  /**
   * 区块管理设置面板
   * 使用动画下拉选择器切换不同节点的区块配置
   */
  import { Badge } from '$lib/components/ui/badge';
  import { Input } from '$lib/components/ui/input';
  import { AnimatedDropdown } from '$lib/components/ui/animated-dropdown';
  import { nodeBlockRegistry } from '$lib/components/blocks/blockRegistry';
  import { NODE_REGISTRY } from '$lib/stores/nodeRegistry';
  import { LayoutGrid, Eye, EyeOff, Search } from '@lucide/svelte';
  import * as icons from '@lucide/svelte';

  // 获取所有节点类型
  const nodeTypes = Object.keys(nodeBlockRegistry);
  
  // 从 NODE_REGISTRY 获取节点信息
  function getNodeInfo(nodeType: string) {
    const entry = NODE_REGISTRY.find(e => e.type === nodeType);
    return {
      label: entry?.label || nodeType,
      iconName: entry?.icon || 'LayoutGrid',
      description: entry?.description || ''
    };
  }
  
  // 动态获取图标组件
  function getIconComponent(iconName: string) {
    return (icons as Record<string, any>)[iconName] || LayoutGrid;
  }
  
  // 构建下拉菜单项
  const dropdownItems = nodeTypes.map(nodeType => {
    const info = getNodeInfo(nodeType);
    return {
      id: nodeType,
      name: info.label,
      icon: getIconComponent(info.iconName),
      badge: nodeBlockRegistry[nodeType]?.blocks.length || 0
    };
  });
  
  // 当前选中的节点
  let activeNode = $state<string>(nodeTypes[0] || 'repacku');
  
  // 搜索关键词
  let searchQuery = $state('');
  
  // 过滤后的区块列表
  let filteredBlocks = $derived.by(() => {
    const layout = nodeBlockRegistry[activeNode];
    if (!layout) return [];
    
    if (!searchQuery.trim()) return layout.blocks;
    
    const query = searchQuery.toLowerCase();
    return layout.blocks.filter(block => 
      block.id.toLowerCase().includes(query) ||
      block.title.toLowerCase().includes(query)
    );
  });
</script>

<div class="p-6 space-y-4">
  <!-- 标题 -->
  <div>
    <h3 class="text-lg font-semibold flex items-center gap-2">
      <LayoutGrid class="w-5 h-5" />
      区块管理
    </h3>
    <p class="text-sm text-muted-foreground mt-1">管理各节点的区块显示和布局</p>
  </div>

  <!-- 节点选择器和搜索 -->
  <div class="flex gap-2">
    <!-- 动画下拉选择器 -->
    <div class="w-48">
      <AnimatedDropdown
        items={dropdownItems}
        bind:value={activeNode}
        placeholder="选择节点"
        triggerIcon={LayoutGrid}
      />
    </div>

    <!-- 搜索框 -->
    <div class="relative flex-1">
      <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
      <Input 
        bind:value={searchQuery}
        placeholder="搜索区块..."
        class="pl-8"
      />
    </div>
  </div>

  <!-- 统计信息 -->
  {#if nodeBlockRegistry[activeNode]}
    {@const layout = nodeBlockRegistry[activeNode]}
    <div class="flex items-center gap-4 text-xs text-muted-foreground">
      <span>共 {layout.blocks.length} 个区块</span>
      {#if searchQuery.trim()}
        <span>• 匹配 {filteredBlocks.length} 个</span>
      {/if}
    </div>
  {/if}

  <!-- 区块列表 -->
  {#if nodeBlockRegistry[activeNode]}
    <div class="space-y-2 max-h-[400px] overflow-y-auto">
      {#each filteredBlocks as block}
        {@const BlockIcon = block.icon}
        <div class="flex items-center justify-between p-3 rounded-lg border bg-card hover:border-primary/50 transition-colors">
          <div class="flex items-center gap-3">
            {#if BlockIcon}
              <BlockIcon class="w-4 h-4 {block.iconClass || 'text-muted-foreground'}" />
            {/if}
            <div>
              <span class="font-medium text-sm">{block.title}</span>
              <div class="flex gap-1.5 mt-1">
                {#if block.colSpan === 2}
                  <Badge variant="outline" class="text-[10px] px-1.5 py-0">宽</Badge>
                {/if}
                {#if block.fullHeight}
                  <Badge variant="outline" class="text-[10px] px-1.5 py-0">高</Badge>
                {/if}
                {#if block.collapsible}
                  <Badge variant="outline" class="text-[10px] px-1.5 py-0">可折叠</Badge>
                {/if}
              </div>
            </div>
          </div>
          
          <div class="flex items-center gap-3">
            <!-- 普通模式可见性 -->
            <div class="flex items-center gap-1.5 text-xs">
              <span class="text-muted-foreground">普通</span>
              {#if block.visibleInNormal !== false}
                <Eye class="w-3.5 h-3.5 text-green-500" />
              {:else}
                <EyeOff class="w-3.5 h-3.5 text-muted-foreground/50" />
              {/if}
            </div>
            
            <!-- 全屏模式可见性 -->
            <div class="flex items-center gap-1.5 text-xs">
              <span class="text-muted-foreground">全屏</span>
              {#if block.visibleInFullscreen !== false}
                <Eye class="w-3.5 h-3.5 text-green-500" />
              {:else}
                <EyeOff class="w-3.5 h-3.5 text-muted-foreground/50" />
              {/if}
            </div>
          </div>
        </div>
      {:else}
        <div class="text-center py-8 text-muted-foreground">
          {#if searchQuery.trim()}
            没有找到匹配的区块
          {:else}
            暂无区块配置
          {/if}
        </div>
      {/each}
    </div>
    
    <!-- 提示 -->
    <div class="text-xs text-muted-foreground p-3 bg-muted/30 rounded-lg">
      💡 区块配置目前为只读。后续版本将支持自定义区块显示和顺序。
    </div>
  {/if}
</div>
