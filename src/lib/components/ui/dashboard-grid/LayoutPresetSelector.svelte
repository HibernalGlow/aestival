<script lang="ts">
  /**
   * 布局预设选择器 - Badge 样式横向布局
   * 点击 Badge 选中并应用，选中后显示操作按钮
   */
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Badge } from '$lib/components/ui/badge';
  import { 
    getAllPresets, savePreset, deletePreset, exportPreset, importPreset,
    renamePreset, updatePreset, setDefaultPreset, getDefaultPresetId, type LayoutPreset 
  } from '$lib/stores/layoutPresets';
  import type { GridItem } from './dashboard-grid.svelte';
  import { 
    Save, Trash2, Download, Upload, Check, X, Pencil, Pin, RefreshCw
  } from '@lucide/svelte';

  interface Props {
    nodeType: string;
    currentLayout: GridItem[];
    onApply: (layout: GridItem[]) => void;
  }

  let { nodeType, currentLayout, onApply }: Props = $props();

  let presets = $state<LayoutPreset[]>([]);
  let selectedId = $state<string | null>(null);
  let defaultId = $state<string | null>(null);
  let showSaveInput = $state(false);
  let showRenameInput = $state(false);
  let inputValue = $state('');
  let saveSuccess = $state(false);

  // 加载预设列表
  function refreshPresets() {
    presets = getAllPresets(nodeType);
    defaultId = getDefaultPresetId(nodeType);
  }

  // 初始化
  $effect(() => {
    refreshPresets();
  });

  // 设为默认
  function handleSetDefault() {
    if (!selectedId) return;
    setDefaultPreset(nodeType, selectedId);
    defaultId = selectedId;
  }

  // 选中并应用预设
  function selectPreset(preset: LayoutPreset) {
    selectedId = preset.id;
    showRenameInput = false;
    onApply(JSON.parse(JSON.stringify(preset.layout)));
  }

  // 保存当前布局为预设
  function handleSave() {
    if (!inputValue.trim()) return;
    const newPreset = savePreset(inputValue.trim(), nodeType, currentLayout);
    inputValue = '';
    showSaveInput = false;
    saveSuccess = true;
    selectedId = newPreset.id;
    setTimeout(() => saveSuccess = false, 2000);
    refreshPresets();
  }

  // 重命名预设
  function handleRename() {
    if (!inputValue.trim() || !selectedId) return;
    renamePreset(selectedId, inputValue.trim());
    inputValue = '';
    showRenameInput = false;
    refreshPresets();
  }

  // 删除预设
  function handleDelete() {
    if (!selectedId) return;
    const preset = presets.find(p => p.id === selectedId);
    if (preset?.isBuiltin) return;
    deletePreset(selectedId);
    selectedId = null;
    refreshPresets();
  }

  // 导出预设
  function handleExport() {
    if (!selectedId) return;
    const json = exportPreset(selectedId);
    if (json) {
      navigator.clipboard.writeText(json);
    }
  }

  // 导入预设
  async function handleImport() {
    try {
      const json = await navigator.clipboard.readText();
      const preset = importPreset(json);
      if (preset) {
        selectedId = preset.id;
        refreshPresets();
      }
    } catch (e) {
      console.error('导入失败:', e);
    }
  }

  // 更新预设布局（覆盖当前选中的预设）
  function handleUpdate() {
    if (!selectedId || !canModify) return;
    const success = updatePreset(selectedId, currentLayout);
    if (success) {
      saveSuccess = true;
      setTimeout(() => saveSuccess = false, 2000);
      refreshPresets();
    }
  }

  // 获取选中的预设
  let selectedPreset = $derived(presets.find(p => p.id === selectedId));
  let canModify = $derived(selectedPreset && !selectedPreset.isBuiltin);
</script>

<div class="flex items-center gap-2 flex-wrap">
  <!-- 预设 Badge 列表 -->
  <span class="text-xs text-muted-foreground shrink-0">预设:</span>
  {#each presets as preset}
    {@const isDefault = defaultId === preset.id}
    {@const isSelected = selectedId === preset.id}
    <button onclick={() => selectPreset(preset)}>
      <Badge 
        variant={isSelected ? 'default' : 'outline'}
        class="cursor-pointer hover:bg-primary/80 transition-colors {isDefault ? 'ring-2 ring-primary ring-offset-1' : ''}"
      >
        {preset.name}
      </Badge>
    </button>
  {/each}

  <!-- 分隔线 -->
  <div class="w-px h-4 bg-border mx-1"></div>

  <!-- 操作按钮区 -->
  {#if showSaveInput || showRenameInput}
    <!-- 输入框 -->
    <div class="flex items-center gap-1">
      <Input 
        bind:value={inputValue} 
        placeholder={showRenameInput ? '新名称...' : '预设名称...'} 
        class="h-6 text-xs w-24"
        onkeydown={(e) => e.key === 'Enter' && (showRenameInput ? handleRename() : handleSave())}
      />
      <Button size="sm" class="h-6 w-6 p-0" onclick={showRenameInput ? handleRename : handleSave}>
        <Check class="h-3 w-3" />
      </Button>
      <Button variant="ghost" size="sm" class="h-6 w-6 p-0" onclick={() => { showSaveInput = false; showRenameInput = false; inputValue = ''; }}>
        <X class="h-3 w-3" />
      </Button>
    </div>
  {:else}
    <!-- 保存按钮 -->
    <Button 
      variant="ghost" 
      size="sm" 
      class="h-6 w-6 p-0"
      onclick={() => { showSaveInput = true; inputValue = ''; }}
      title="保存当前布局"
    >
      <Save class="h-3 w-3" />
    </Button>

    <!-- 选中预设后的操作按钮 -->
    {#if selectedId}
      <!-- 设为默认 -->
      {#if defaultId !== selectedId}
        <Button 
          variant="ghost" 
          size="sm" 
          class="h-6 w-6 p-0 hover:text-primary"
          onclick={handleSetDefault}
          title="设为默认"
        >
          <Pin class="h-3 w-3" />
        </Button>
      {/if}
      {#if canModify}
        <Button 
          variant="ghost" 
          size="sm" 
          class="h-6 w-6 p-0 hover:text-primary"
          onclick={handleUpdate}
          title="更新布局（覆盖当前预设）"
        >
          <RefreshCw class="h-3 w-3" />
        </Button>
        <Button 
          variant="ghost" 
          size="sm" 
          class="h-6 w-6 p-0"
          onclick={() => { showRenameInput = true; inputValue = selectedPreset?.name ?? ''; }}
          title="重命名"
        >
          <Pencil class="h-3 w-3" />
        </Button>
        <Button 
          variant="ghost" 
          size="sm" 
          class="h-6 w-6 p-0 hover:text-destructive"
          onclick={handleDelete}
          title="删除"
        >
          <Trash2 class="h-3 w-3" />
        </Button>
      {/if}
      <Button 
        variant="ghost" 
        size="sm" 
        class="h-6 w-6 p-0"
        onclick={handleExport}
        title="导出到剪贴板"
      >
        <Download class="h-3 w-3" />
      </Button>
    {/if}

    <!-- 导入按钮 -->
    <Button 
      variant="ghost" 
      size="sm" 
      class="h-6 w-6 p-0"
      onclick={handleImport}
      title="从剪贴板导入"
    >
      <Upload class="h-3 w-3" />
    </Button>
  {/if}
</div>
