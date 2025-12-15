<script lang="ts">
  import { flowStore, taskStore, isRunning } from '$lib/stores';
  import { api } from '$lib/services/api';
  import { Save, Play, Square, RotateCcw, FileDown, FileUp, Sun, Moon, Monitor, Palette } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { themeStore, toggleThemeMode, openThemeImport } from '$lib/stores/theme.svelte';

  async function saveFlow() {
    const flow = flowStore.toFlow();
    try {
      if (flow.id && flowStore.getState().id) {
        await api.updateFlow(flow.id, flow);
      } else {
        const saved = await api.createFlow(flow);
        flowStore.load(saved);
      }
      flowStore.markSaved();
    } catch (e) {
      console.error('保存失败:', e);
    }
  }

  async function executeFlow() {
    const state = flowStore.getState();
    if (!state.id) {
      await saveFlow();
    }
    
    try {
      const { taskId } = await api.executeFlow(flowStore.getState().id!);
      taskStore.startTask(taskId);
    } catch (e) {
      console.error('执行失败:', e);
    }
  }

  function stopExecution() {
    const taskId = taskStore.getState?.()?.taskId;
    if (taskId) {
      api.cancelTask(taskId);
      taskStore.cancel();
    }
  }

  function resetFlow() {
    if (confirm('确定要重置流程吗？未保存的更改将丢失。')) {
      flowStore.reset();
      taskStore.reset();
    }
  }

  function exportFlow() {
    const flow = flowStore.toFlow();
    const blob = new Blob([JSON.stringify(flow, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${flow.name || 'flow'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function importFlow() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const text = await file.text();
        const flow = JSON.parse(text);
        flowStore.load(flow);
      }
    };
    input.click();
  }
</script>

<div class="h-14 bg-card border-b flex items-center justify-between px-4">
  <div class="flex items-center gap-2">
    <input
      type="text"
      class="text-lg font-semibold bg-transparent border-none focus:outline-none focus:ring-2 focus:ring-primary rounded px-2 py-1"
      value={$flowStore.name}
      onchange={(e) => flowStore.setName(e.currentTarget.value)}
      placeholder="未命名流程"
    />
    {#if $flowStore.isDirty}
      <span class="text-xs text-amber-600 bg-amber-100 dark:bg-amber-900/30 px-2 py-0.5 rounded">未保存</span>
    {/if}
  </div>

  <div class="flex items-center gap-2">
    <!-- 主题切换 -->
    <Button variant="ghost" size="icon" class="h-8 w-8" onclick={toggleThemeMode} title="切换主题模式">
      {#if $themeStore.mode === 'dark'}
        <Moon class="w-4 h-4" />
      {:else if $themeStore.mode === 'light'}
        <Sun class="w-4 h-4" />
      {:else}
        <Monitor class="w-4 h-4" />
      {/if}
    </Button>
    <Button variant="ghost" size="icon" class="h-8 w-8" onclick={openThemeImport} title="导入主题">
      <Palette class="w-4 h-4" />
    </Button>
    <div class="w-px h-6 bg-border mx-1"></div>
    
    <Button variant="outline" size="sm" onclick={importFlow}>
      <FileUp class="w-4 h-4 mr-1" />
      导入
    </Button>
    <Button variant="outline" size="sm" onclick={exportFlow}>
      <FileDown class="w-4 h-4 mr-1" />
      导出
    </Button>
    <Button variant="outline" size="sm" onclick={resetFlow}>
      <RotateCcw class="w-4 h-4 mr-1" />
      重置
    </Button>
    <div class="w-px h-6 bg-border mx-1"></div>
    <Button variant="outline" size="sm" onclick={saveFlow} disabled={!$flowStore.isDirty}>
      <Save class="w-4 h-4 mr-1" />
      保存
    </Button>
    {#if $isRunning}
      <Button variant="destructive" size="sm" onclick={stopExecution}>
        <Square class="w-4 h-4 mr-1" />
        停止
      </Button>
    {:else}
      <Button size="sm" onclick={executeFlow} disabled={$flowStore.nodes.length === 0}>
        <Play class="w-4 h-4 mr-1" />
        执行
      </Button>
    {/if}
  </div>
</div>
