<script lang="ts">
  import {
    SvelteFlow,
    SvelteFlowProvider,
    Background,
    Controls,
    MiniMap,
    type NodeTypes
  } from '@xyflow/svelte';
  import '@xyflow/svelte/dist/style.css';

  import { flowStore } from '$lib/stores';
  import { getNodeTypes } from '$lib/stores/nodeRegistry';

  let nodeIdCounter = 1;
  let containerRef: HTMLDivElement;

  // 使用 $derived 确保节点变化时自动更新
  // 深拷贝节点确保 SvelteFlow 检测到属性变化（如 draggable）
  let nodes = $derived($flowStore.nodes.map(n => ({ ...n })) as any[]);
  let edges = $derived($flowStore.edges.map(e => ({ ...e })) as any[]);

  // 从注册表获取节点类型映射
  const nodeTypes: NodeTypes = getNodeTypes();

  function handleKeyDown(e: KeyboardEvent) {
    // 如果焦点在输入框、文本域等可编辑元素内，不处理删除键
    const target = e.target as HTMLElement;
    const isEditable = target.tagName === 'INPUT' || 
                       target.tagName === 'TEXTAREA' || 
                       target.isContentEditable ||
                       target.closest('input, textarea, [contenteditable="true"]');
    
    if (isEditable) {
      return; // 让输入框正常处理 Backspace/Delete
    }
    
    if ((e.key === 'Delete' || e.key === 'Backspace') && $flowStore.selectedNodeId) {
      e.preventDefault();
      flowStore.removeNode($flowStore.selectedNodeId);
    }
  }

  // 处理拖拽放置
  function handleDrop(event: DragEvent) {
    event.preventDefault();

    const data = event.dataTransfer?.getData('application/json');
    if (!data) return;

    try {
      const { type, label } = JSON.parse(data);

      // 获取容器的边界
      const bounds = containerRef?.getBoundingClientRect();
      if (!bounds) return;

      // 计算相对于容器的位置
      const position = {
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top
      };

      const node = {
        id: `node-${nodeIdCounter++}-${Date.now()}`,
        type,
        position,
        data: { label, status: 'idle' as const }
      };

      flowStore.addNode(node);
    } catch (e) {
      console.error('Failed to parse drop data:', e);
    }
  }

  function handleDragOver(event: DragEvent) {
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'move';
    }
  }
  
  // 记录节点的原始位置，用于固定节点时恢复
  let pinnedPositions: Map<string, { x: number; y: number }> = new Map();
  
  // 监听 flowStore 变化，记录固定节点的位置
  $effect(() => {
    $flowStore.nodes.forEach(node => {
      if (node.draggable === false && node.position) {
        pinnedPositions.set(node.id, { ...node.position });
      } else {
        pinnedPositions.delete(node.id);
      }
    });
  });
</script>

<svelte:window onkeydown={handleKeyDown} />

<SvelteFlowProvider>
  <div
    bind:this={containerRef}
    class="h-full w-full"
    ondrop={handleDrop}
    ondragover={handleDragOver}
    role="application"
  >
    <SvelteFlow
      {nodes}
      {edges}
      {nodeTypes}
      onnodeclick={({ node }) => flowStore.selectNode(node.id)}
      onnodedragstop={({ targetNode }) => {
        // 检查节点是否被固定
        const originalPos = pinnedPositions.get(targetNode.id);
        if (originalPos) {
          // 固定节点：恢复到原始位置
          flowStore.updateNode(targetNode.id, { position: originalPos });
        } else {
          // 非固定节点：更新到新位置
          flowStore.updateNode(targetNode.id, { position: targetNode.position });
        }
      }}
      onpaneclick={() => flowStore.selectNode(null)}
      onconnect={(conn) => {
        flowStore.addEdge({
          id: `e-${conn.source}-${conn.target}-${Date.now()}`,
          source: conn.source,
          target: conn.target,
          sourceHandle: conn.sourceHandle,
          targetHandle: conn.targetHandle,
          animated: true
        });
      }}
      ondelete={({ nodes: deletedNodes, edges: deletedEdges }) => {
        deletedNodes?.forEach(n => flowStore.removeNode(n.id));
        deletedEdges?.forEach(e => flowStore.removeEdge(e.id));
      }}
      fitView
      snapGrid={[15, 15]}
    >
      <Background gap={20} class="opacity-10" />
      <Controls />
      <MiniMap
        nodeColor={(node) => {
          if (node.type === 'repacku' || node.type === 'rawfilter' || node.type === 'crashu' || node.type === 'trename') return '#3b82f6';
          if (node.type?.includes('input')) return '#22c55e';
          if (node.type?.includes('output') || node.type === 'terminal') return '#f59e0b';
          return '#64748b';
        }}
      />
    </SvelteFlow>
  </div>
</SvelteFlowProvider>

<style>
  :global(.svelte-flow) {
    background: transparent !important;
  }
  :global(.svelte-flow__node) {
    cursor: pointer;
    overflow: hidden !important;
  }
  /* 确保节点内容正确继承高度 */
  :global(.svelte-flow__node > div) {
    height: 100% !important;
    overflow: hidden !important;
  }
  :global(.svelte-flow__background) {
    opacity: 0.3;
  }
  /* Controls 工具栏样式 */
  :global(.svelte-flow__controls) {
    background: color-mix(in srgb, var(--card) 85%, transparent) !important;
    backdrop-filter: blur(12px);
    border: none !important;
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  }
  :global(.svelte-flow__controls-button) {
    background: transparent !important;
    border: none !important;
    color: var(--foreground) !important;
    fill: var(--foreground) !important;
  }
  :global(.svelte-flow__controls-button:hover) {
    background: color-mix(in srgb, var(--muted) 80%, transparent) !important;
  }
  :global(.svelte-flow__controls-button svg) {
    fill: currentColor !important;
  }
  /* MiniMap 样式 */
  :global(.svelte-flow__minimap) {
    background: color-mix(in srgb, var(--card) 85%, transparent) !important;
    backdrop-filter: blur(12px);
    border: none !important;
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  }
  :global(.svelte-flow__minimap-mask) {
    fill: color-mix(in srgb, var(--background) 60%, transparent) !important;
  }
</style>
