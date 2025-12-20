<script lang="ts">
  import { Handle, Position } from '@xyflow/svelte';
  import { Clipboard, Folder, FileInput } from '@lucide/svelte';
  import NodeWrapper from '../NodeWrapper.svelte';

  interface Props {
    id: string;
    data: {
      label: string;
      config?: Record<string, unknown>;
      status?: 'idle' | 'running' | 'completed' | 'error';
    };
    type: string;
    selected?: boolean;
  }

  let { id, data, type, selected = false }: Props = $props();

  const icons: Record<string, typeof Clipboard> = {
    clipboard_input: Clipboard,
    folder_input: Folder,
    path_input: FileInput
  };

  const Icon = $derived(icons[type] || FileInput);
</script>

<NodeWrapper nodeId={id} title={data.label} icon={Icon}>
  {#snippet children()}
    <div class="p-3">
      {#if data.config?.path}
        <div class="text-xs text-muted-foreground truncate max-w-[160px]" title={String(data.config.path)}>
          {data.config.path}
        </div>
      {:else}
        <div class="text-xs text-muted-foreground">点击配置输入源</div>
      {/if}
    </div>
  {/snippet}
</NodeWrapper>

<Handle type="source" position={Position.Right} class="!bg-green-500 !w-3 !h-3" />
