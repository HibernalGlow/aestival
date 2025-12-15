<script lang="ts">
  /**
   * 浮动工具栏 - 可拖拽的工具面板
   */
  import { flowStore, taskStore, isRunning } from '$lib/stores';
  import { api } from '$lib/services/api';
  import { Save, Play, Square, RotateCcw, FileDown, FileUp, Sun, Moon, Monitor, Palette, GripHorizontal } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { themeStore, toggleThemeMode, openThemeImport } from '$lib/stores/theme.svelte';

  // 拖拽状态
  let isDragging = $state(false);
  let position = $state({ x: 20, y: 20 });
  let dragOffset = { x: 0, y: 0 };

  function onMouseDown(e: MouseEvent) {
    if ((e.target as HTMLElement).closest('button, input')) return;
    isDragging = true;
    dragOffset = { x: e.clientX - position.x, y: e.clientY - position.y };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }

  function onMouseMove(e: MouseEvent) {
    if (!isDragging) return;
    position = { x: e.clientX - dragOffset.x, y: e.clientY - dragOffset.y };
  }

  function onMouseUp() {
    isDragging = false;
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('mouseup', onMouseUp);
  }

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
    } catch (e) { console.error('保存失败:', e); }
  }

  async function executeFlow() {
    const state = flowStore.getState();
    if (!state.id) await saveFlow();
    try {
      const { taskId } = await api.executeFlow(flowStore.getState().id!);
      taskStore.startTask(taskId);
    } catch (e) { console.error('执行失败:', e); }
  }

  function stopExecution() {
    const taskId = taskStore.getState?.()?.taskId;
    if (taskId) { api.cancelTask(taskId); taskStore.cancel(); }
  }

  function resetFlow() {
    if (confirm('确定要重置流程吗？')) { flowStore.reset(); taskStore.reset(); }
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
        flowStore.load(JSON.parse(text));
      }
    };
    input.click();
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="fixed z-50 bg-card/95 backdrop-blur border rounded-lg shadow-lg select-none"
  style="left: {position.x}px; top: {position.y}px;"
  onmousedown={onMouseDown}
>
  <!-- 拖拽手柄 -->
  <div class="flex items-center gap-2 px-3 py-2 border-b cursor-move">
    <GripHorizontal class="w-4 h-4 text-muted-foreground" />
    <input
      type="text"
      class="text-sm font-semibold bg-transparent border-none focus:outline-none focus:ring-1 focus:ring-primary rounded px-1 w-32"
      value={$flowStore.name}
      onchange={(e) => flowStore.setName(e.currentTarget.value)}
      placeholder="未命名流程"
    />
    {#if $flowStore.isDirty}
      <span class="text-xs text-amber-600 bg-amber-100 dark:bg-amber-900/30 px-1.5 py-0.5 rounded">*</span>
    {/if}
  </div>

  <!-- 工具按钮 -->
  <div class="flex items-center gap-1 p-2">
    <Button variant="ghost" size="icon" class="h-7 w-7" onclick={toggleThemeMode} title="主题">
      {#if $themeStore.mode === 'dark'}<Moon class="w-3.5 h-3.5" />
      {:else if $themeStore.mode === 'light'}<Sun class="w-3.5 h-3.5" />
      {:else}<Monitor class="w-3.5 h-3.5" />{/if}
    </Button>
    <Button variant="ghost" size="icon" class="h-7 w-7" onclick={openThemeImport} title="导入主题">
      <Palette class="w-3.5 h-3.5" />
    </Button>
    <div class="w-px h-5 bg-border mx-0.5"></div>
    <Button variant="ghost" size="icon" class="h-7 w-7" onclick={importFlow} title="导入流程">
      <FileUp class="w-3.5 h-3.5" />
    </Button>
    <Button variant="ghost" size="icon" class="h-7 w-7" onclick={exportFlow} title="导出流程">
      <FileDown class="w-3.5 h-3.5" />
    </Button>
    <Button variant="ghost" size="icon" class="h-7 w-7" onclick={resetFlow} title="重置">
      <RotateCcw class="w-3.5 h-3.5" />
    </Button>
    <div class="w-px h-5 bg-border mx-0.5"></div>
    <Button variant="ghost" size="icon" class="h-7 w-7" onclick={saveFlow} disabled={!$flowStore.isDirty} title="保存">
      <Save class="w-3.5 h-3.5" />
    </Button>
    {#if $isRunning}
      <Button variant="destructive" size="icon" class="h-7 w-7" onclick={stopExecution} title="停止">
        <Square class="w-3.5 h-3.5" />
      </Button>
    {:else}
      <Button variant="default" size="icon" class="h-7 w-7" onclick={executeFlow} disabled={$flowStore.nodes.length === 0} title="执行">
        <Play class="w-3.5 h-3.5" />
      </Button>
    {/if}
  </div>
</div>
