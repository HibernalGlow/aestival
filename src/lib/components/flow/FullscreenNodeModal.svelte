<script lang="ts">
  /**
   * 全屏节点模态框
   * 自动从 nodeRegistry 获取组件，无需手动导入
   */
  import { fullscreenNodeStore } from '$lib/stores/fullscreenNode.svelte';
  import { getNodeComponent, getNodeDefinition } from '$lib/stores/nodeRegistry';
  import { X, Minimize2 } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';

  function handleClose() {
    fullscreenNodeStore.close();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      handleClose();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if $fullscreenNodeStore.isOpen && $fullscreenNodeStore.nodeType}
  {@const FullscreenComponent = getNodeComponent($fullscreenNodeStore.nodeType)}
  {@const nodeDef = getNodeDefinition($fullscreenNodeStore.nodeType)}
  {@const title = nodeDef?.label || $fullscreenNodeStore.nodeType}
  
  <!-- 背景遮罩 -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div 
    class="fixed inset-0 z-[100] bg-background/80 backdrop-blur-sm"
    onclick={handleClose}
  ></div>
  
  <!-- 全屏内容 -->
  <div class="fixed inset-4 z-[101] bg-card border rounded-lg shadow-2xl flex flex-col overflow-hidden">
    <!-- 标题栏 -->
    <div class="flex items-center justify-between px-4 py-2 border-b bg-muted/30 shrink-0">
      <span class="font-semibold">{title} - 全屏模式</span>
      <div class="flex items-center gap-1">
        <Button variant="ghost" size="icon" class="h-7 w-7" onclick={handleClose} title="退出全屏">
          <Minimize2 class="w-4 h-4" />
        </Button>
        <Button variant="ghost" size="icon" class="h-7 w-7" onclick={handleClose} title="关闭">
          <X class="w-4 h-4" />
        </Button>
      </div>
    </div>
    
    <!-- 节点内容 -->
    <div class="flex-1 overflow-auto">
      {#if FullscreenComponent}
        <svelte:component 
          this={FullscreenComponent} 
          nodeId={$fullscreenNodeStore.nodeId}
          data={$fullscreenNodeStore.nodeData}
          fullscreen={true}
        />
      {:else}
        <div class="text-muted-foreground text-center py-8">
          暂不支持全屏显示: {$fullscreenNodeStore.nodeType}
        </div>
      {/if}
    </div>
  </div>
{/if}
