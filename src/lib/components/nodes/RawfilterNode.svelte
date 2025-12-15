<script lang="ts">
  import BaseNode from './BaseNode.svelte';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Label } from '$lib/components/ui/label';
  import { api } from '$lib/services/api';
  
  // Props from SvelteFlow
  export let id: string;
  export let data: {
    config?: {
      path?: string;
      name_only_mode?: boolean;
      create_shortcuts?: boolean;
      trash_only?: boolean;
    };
    status?: 'idle' | 'running' | 'completed' | 'error';
    hasInputConnection?: boolean;
    logs?: string[];
    label?: string;
  } = {};

  // 本地状态 - 直接从 data 获取默认值
  let localPath = data?.config?.path ?? '';
  let localNameOnlyMode = data?.config?.name_only_mode ?? false;
  let localCreateShortcuts = data?.config?.create_shortcuts ?? false;
  let localTrashOnly = data?.config?.trash_only ?? false;
  let localStatus: 'idle' | 'running' | 'completed' | 'error' = data?.status ?? 'idle';
  let localLogs: string[] = data?.logs ? [...data.logs] : [];
  let localHasInputConnection = data?.hasInputConnection ?? false;
  
  // 执行节点
  async function handleExecute() {
    localStatus = 'running';
    localLogs = [...localLogs, `开始执行 rawfilter...`];
    
    try {
      const result = await api.executeNode('rawfilter', {
        path: localPath,
        name_only_mode: localNameOnlyMode,
        create_shortcuts: localCreateShortcuts,
        trash_only: localTrashOnly
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
  icon="🔍"
  displayName="相似文件过滤"
  bind:status={localStatus}
  bind:hasInputConnection={localHasInputConnection}
  bind:path={localPath}
  bind:logs={localLogs}
  onExecute={handleExecute}
>
  <div slot="config" class="space-y-2">
    <!-- 仅名称模式 -->
    <div class="flex items-center gap-2">
      <Checkbox 
        id="name-only-{id}" 
        bind:checked={localNameOnlyMode}
        disabled={localStatus === 'running'}
      />
      <Label for="name-only-{id}" class="text-xs cursor-pointer">
        仅名称模式（跳过内部分析）
      </Label>
    </div>
    
    <!-- 创建快捷方式 -->
    <div class="flex items-center gap-2">
      <Checkbox 
        id="shortcuts-{id}" 
        bind:checked={localCreateShortcuts}
        disabled={localStatus === 'running'}
      />
      <Label for="shortcuts-{id}" class="text-xs cursor-pointer">
        创建快捷方式而非移动
      </Label>
    </div>
    
    <!-- 仅移动到 trash -->
    <div class="flex items-center gap-2">
      <Checkbox 
        id="trash-only-{id}" 
        bind:checked={localTrashOnly}
        disabled={localStatus === 'running'}
      />
      <Label for="trash-only-{id}" class="text-xs cursor-pointer">
        仅移动到 trash
      </Label>
    </div>
  </div>
</BaseNode>
