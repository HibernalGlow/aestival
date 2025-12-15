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

  // 使用 $state.raw 创建响应式数组
  let nodes = $state.raw<any[]>([]);
  let edges = $state.raw<any[]>([]);

  // 同步 flowStore 到本地状态
  $effect(() => {
    nodes = $flowStore.nodes as any[];
  });

  $effect(() => {
    edges = $flowStore.edges as any[];
  });

  // 从注册表获取节点类型映射
  const nodeTypes: NodeTypes = getNodeTypes();

  function handleKeyDown(e: KeyboardEvent) {
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
        flowStore.updateNode(targetNode.id, { position: targetNode.position });
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
      <Background gap={20} color="currentColor" class="opacity-10" />
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
  }
  :global(.svelte-flow__background) {
    opacity: 0.3;
  }
</style>
