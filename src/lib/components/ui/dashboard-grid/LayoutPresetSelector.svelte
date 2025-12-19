<script lang="ts">
  /**
   * 布局预设选择器 - Badge 样式横向布局
   * 点击 Badge 选中并应用，选中后显示操作按钮
   * 支持分别为全屏/节点模式设置默认预设，用圆点指示器显示
   */
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Badge } from '$lib/components/ui/badge';
  import { onMount } from 'svelte';
  import { 
    getAllPresets, savePreset, deletePreset, exportPreset, importPreset,
    renamePreset, updatePreset, setDefaultPreset, unsetDefaultPreset,
    getDefaultPresetId, getPresetDefaultModes, type LayoutPreset, type PresetMode
  } from '$lib/stores/layoutPresets';
  import type { GridItem } from './dashboard-grid.svelte';
  import { 
    Save, Trash2, Download, Upload, Check, X, Pencil, RefreshCw, Maximize2, Minimize2
  } from '@lucide/svelte';

  import type { PresetTabGroup } from '$lib/stores/layoutPresets';

  interface Props {
    nodeType: string;
    currentLayout: GridItem[];
    /** 当前 Tab 分组配置 */
    currentTabGroups?: PresetTabGroup[];
    onApply: (layout: GridItem[], tabGroups?: PresetTabGroup[]) => void;
    /** 当前布局模式（用于高亮当前模式的默认指示器） */
    currentMode?: PresetMode;
  }

  let { nodeType, currentLayout, currentTabGroups = [], onApply, currentMode = 'fullscreen' }: Props = $props();

  let presets = $state<LayoutPreset[]>([]);
  let selectedId = $state<string | null>(null);
  let showSaveInput = $state(false);
  let showRenameInput = $state(false);
  let inputValue = $state('');
  let saveSuccess = $state(false);
  
  // 存储每个预设的默认模式列表（用于显示圆点）
  let presetModes = $state<Record<string, PresetMode[]>>({});

  // 加载预设列表和默认模式
  function refreshPresets() {
    presets = getAllPresets(nodeType);
    // 加载每个预设的默认模式
    const modes: Record<string, PresetMode[]> = {};
    for (const preset of presets) {
      modes[preset.id] = getPresetDefaultModes(nodeType, preset.id);
    }
    presetModes = modes;
  }

  // 初始化：只在挂载时执行一次
  onMount(() => {
    refreshPresets();
    // 默认选中当前模式的默认预设
    const defaultId = getDefaultPresetId(nodeType, currentMode);
    if (defaultId) {
      selectedId = defaultId;
    }
  });

  // 切换默认状态（点击已设为默认则取消，否则设为默认）
  function toggleDefault(mode: PresetMode) {
    if (!selectedId) return;
    const currentModes = presetModes[selectedId] || [];
    if (currentModes.includes(mode)) {
      // 已是默认，取消
      unsetDefaultPreset(nodeType, mode);
    } else {
      // 设为默认
      setDefaultPreset(nodeType, selectedId, mode);
    }
    refreshPresets();
  }

  // 选中并应用预设（点击已选中的不重复应用）
  function selectPreset(preset: LayoutPreset) {
    if (selectedId === preset.id) return; // 已选中则不重复应用
    selectedId = preset.id;
    showRenameInput = false;
    // 应用布局和 Tab 分组
    // 注意：传递空数组 [] 会清除现有 Tab，传递 undefined 会保留现有 Tab
    // 对于有 tabGroups 字段的预设，使用其值；对于没有的（旧预设/内置预设），传递空数组清除 Tab
    onApply(
      JSON.parse(JSON.stringify(preset.layout)),
      preset.tabGroups !== undefined 
        ? JSON.parse(JSON.stringify(preset.tabGroups)) 
        : [] // 旧预设/内置预设没有 Tab，应用时清除现有 Tab
    );
  }

  // 保存当前布局为预设（包含 Tab 分组）
  function handleSave() {
    if (!inputValue.trim()) return;
    const newPreset = savePreset(
      inputValue.trim(), 
      nodeType, 
      currentLayout,
      currentTabGroups.length > 0 ? currentTabGroups : undefined
    );
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

  // 更新预设布局（覆盖当前选中的预设，包含 Tab 分组）
  function handleUpdate() {
    if (!selectedId || !canModify) return;
    const success = updatePreset(
      selectedId, 
      currentLayout,
      currentTabGroups.length > 0 ? currentTabGroups : undefined
    );
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
    {@const modes = presetModes[preset.id] || []}
    {@const isFullscreenDefault = modes.includes('fullscreen')}
    {@const isNormalDefault = modes.includes('normal')}
    {@const isSelected = selectedId === preset.id}
    <button onclick={() => selectPreset(preset)} class="relative">
      <Badge 
        variant={isSelected ? 'default' : 'outline'}
        class="cursor-pointer hover:bg-primary/80 transition-colors pr-5"
      >
        {preset.name}
      </Badge>
      <!-- 模式默认指示器（圆点） -->
      <div class="absolute -right-0.5 top-1/2 -translate-y-1/2 flex flex-col gap-0.5 pr-1">
        {#if isFullscreenDefault}
          <div 
            class="w-1.5 h-1.5 rounded-full {currentMode === 'fullscreen' ? 'bg-blue-500' : 'bg-blue-400/60'}" 
            title="全屏模式默认"
          ></div>
        {/if}
        {#if isNormalDefault}
          <div 
            class="w-1.5 h-1.5 rounded-full {currentMode === 'normal' ? 'bg-green-500' : 'bg-green-400/60'}" 
            title="节点模式默认"
          ></div>
        {/if}
      </div>
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
      {@const selectedModes = presetModes[selectedId] || []}
      <!-- 设为全屏模式默认 -->
      <Button 
        variant="ghost" 
        size="sm" 
        class="h-6 w-6 p-0 {selectedModes.includes('fullscreen') ? 'text-blue-500' : 'hover:text-blue-500'}"
        onclick={() => toggleDefault('fullscreen')}
        title={selectedModes.includes('fullscreen') ? '取消全屏模式默认' : '设为全屏模式默认'}
      >
        <Maximize2 class="h-3 w-3" />
      </Button>
      <!-- 设为节点模式默认 -->
      <Button 
        variant="ghost" 
        size="sm" 
        class="h-6 w-6 p-0 {selectedModes.includes('normal') ? 'text-green-500' : 'hover:text-green-500'}"
        onclick={() => toggleDefault('normal')}
        title={selectedModes.includes('normal') ? '取消节点模式默认' : '设为节点模式默认'}
      >
        <Minimize2 class="h-3 w-3" />
      </Button>
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
