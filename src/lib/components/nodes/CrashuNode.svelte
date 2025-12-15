<script lang="ts">
  import BaseNode from './BaseNode.svelte';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Label } from '$lib/components/ui/label';
  import { Input } from '$lib/components/ui/input';
  import { api } from '$lib/services/api';
  
  // Props from SvelteFlow
  export let id: string;
  export let data: {
    config?: {
      path?: string;
      target_path?: string;
      destination_path?: string;
      similarity_threshold?: number;
      auto_move?: boolean;
    };
    status?: 'idle' | 'running' | 'completed' | 'error';
    hasInputConnection?: boolean;
    logs?: string[];
    label?: string;
  } = {};

  // 本地状态 - 直接从 data 获取默认值
  let localPath = data?.config?.path ?? '';
  let localSimilarityThreshold = data?.config?.similarity_threshold ?? 0.8;
  let localAutoMove = data?.config?.auto_move ?? false;
  let localStatus: 'idle' | 'running' | 'completed' | 'error' = data?.status ?? 'idle';
  let localLogs: string[] = data?.logs ? [...data.logs] : [];
  let localHasInputConnection = data?.hasInputConnection ?? false;
  
  // 执行节点
  async function handleExecute() {
    localStatus = 'running';
    localLogs = [...localLogs, `开始执行 crashu...`];
    
    try {
      const result = await api.executeNode('crashu', {
        path: localPath,
        similarity_threshold: localSimilarityThreshold,
        auto_move: localAutoMove
      });
      
      if (result.success) {
        localStatus = 'completed';
        localLogs = [...localLogs, result.message];
      } else {
        localStatus = 'error';
        localLogs = [...localLogs, `错误: ${result.message}`];
      }
    } catch (error) {
      localStatus = 'error';
      localLogs = [...localLogs, `执行失败: ${error}`];
    }
  }
</script>

<BaseNode
  {id}
  icon="💥"
  displayName="crashu"
  bind:status={localStatus}
  bind:hasInputConnection={localHasInputConnection}
  bind:path={localPath}
  bind:logs={localLogs}
  onExecute={handleExecute}
>
  <div slot="config" class="space-y-3">
    <!-- 相似度阈值 -->
    <div class="space-y-1">
      <Label class="text-xs">相似度阈值: {localSimilarityThreshold}</Label>
      <Input 
        type="range" 
        min="0" 
        max="1" 
        step="0.1"
        bind:value={localSimilarityThreshold}
        disabled={localStatus === 'running'}
        class="h-2"
      />
    </div>
    
    <!-- 自动移动 -->
    <div class="flex items-center gap-2">
      <Checkbox 
        id="auto-move-{id}" 
        bind:checked={localAutoMove}
        disabled={localStatus === 'running'}
      />
      <Label for="auto-move-{id}" class="text-xs cursor-pointer">
        自动执行移动操作
      </Label>
    </div>
  </div>
</BaseNode>
