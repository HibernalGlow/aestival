<script lang="ts">
  import { Handle, Position } from '@xyflow/svelte';
  import { Terminal } from '@lucide/svelte';
  import NodeWrapper from '../NodeWrapper.svelte';

  interface Props {
    id: string;
    data: {
      label: string;
      status?: 'idle' | 'running' | 'completed' | 'error';
    };
    type: string;
    selected?: boolean;
  }

  let { id, data, type, selected = false }: Props = $props();
</script>

<Handle type="target" position={Position.Left} class="!bg-amber-500 !w-3 !h-3" />

<NodeWrapper nodeId={id} title={data.label} icon={Terminal}>
  {#snippet children()}
    <div class="p-3 text-xs text-muted-foreground">
      输出节点
    </div>
  {/snippet}
</NodeWrapper>
