<script lang="ts">
  /**
   * AestivalFlow - 自定义标题栏组件
   * 无边框窗口的标题栏，支持拖拽移动和窗口控制
   */
  import { Button } from '$lib/components/ui/button';
  import { Minus, Square, X, Settings, Sun, Moon, Palette } from '@lucide/svelte';
  import { themeStore, toggleThemeMode, openThemeImport } from '$lib/stores/theme.svelte';

  // Tauri API（仅在桌面应用中可用）
  let appWindow: any = null;
  
  // 动态导入 Tauri API
  async function initTauri() {
    try {
      const { getCurrentWebviewWindow } = await import('@tauri-apps/api/webviewWindow');
      appWindow = getCurrentWebviewWindow();
    } catch {
      // 非 Tauri 环境，忽略
    }
  }
  initTauri();

  async function minimizeWindow() {
    await appWindow?.minimize();
  }

  async function maximizeWindow() {
    await appWindow?.toggleMaximize();
  }

  async function closeWindow() {
    await appWindow?.close();
  }
</script>

<div
  data-tauri-drag-region
  class="h-8 bg-secondary/50 flex items-center justify-between px-2 select-none border-b shrink-0"
>
  <!-- 左侧：应用名称 -->
  <div class="flex items-center gap-2" data-tauri-drag-region>
    <span class="text-sm font-semibold">AestivalFlow</span>
  </div>

  <!-- 中间：功能按钮 -->
  <div class="flex items-center gap-1">
    <!-- 主题切换 -->
    <Button variant="ghost" size="icon" class="h-6 w-6" onclick={toggleThemeMode} title="切换明暗模式">
      {#if $themeStore.mode === 'dark'}
        <Sun class="h-3.5 w-3.5" />
      {:else}
        <Moon class="h-3.5 w-3.5" />
      {/if}
    </Button>
    <!-- 导入主题 -->
    <Button variant="ghost" size="icon" class="h-6 w-6" onclick={openThemeImport} title="导入主题">
      <Palette class="h-3.5 w-3.5" />
    </Button>
  </div>

  <!-- 右侧：窗口控制按钮 -->
  <div class="flex items-center">
    <Button variant="ghost" size="icon" class="h-8 w-10 rounded-none hover:bg-muted" onclick={minimizeWindow}>
      <Minus class="h-3.5 w-3.5" />
    </Button>
    <Button variant="ghost" size="icon" class="h-8 w-10 rounded-none hover:bg-muted" onclick={maximizeWindow}>
      <Square class="h-3 w-3" />
    </Button>
    <Button variant="ghost" size="icon" class="h-8 w-10 rounded-none hover:bg-destructive hover:text-destructive-foreground" onclick={closeWindow}>
      <X class="h-4 w-4" />
    </Button>
  </div>
</div>
