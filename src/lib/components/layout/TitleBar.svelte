<script lang="ts">
  /**
   * aestival - 自定义标题栏组件
   * 无边框窗口的标题栏，支持拖拽移动和窗口控制
   * 优先使用 Tauri API
   */
  import { Button } from '$lib/components/ui/button';
  import { Minus, Square, X, Sun, Moon, Palette } from '@lucide/svelte';
  import { themeStore, toggleThemeMode, openThemeImport } from '$lib/stores/theme.svelte';
  import { onMount } from 'svelte';
  import { isTauriEnvironment } from '$lib/api/platform';

  // 窗口 API 类型
  type WindowAPI = {
    minimize: () => void | Promise<void>;
    maximize: () => void | Promise<void>;
    close: () => void | Promise<void>;
    startDrag?: () => void | Promise<void>;
  };

  let windowApi: WindowAPI | null = null;

  onMount(() => {
    initWindowApi();
  });

  async function initWindowApi() {
    // 1. 优先尝试 Tauri API
    if (isTauriEnvironment()) {
      try {
        const { getCurrentWebviewWindow } = await import('@tauri-apps/api/webviewWindow');
        const appWindow = getCurrentWebviewWindow();
        windowApi = {
          minimize: () => appWindow.minimize(),
          maximize: () => appWindow.toggleMaximize(),
          close: () => appWindow.close(),
          startDrag: () => appWindow.startDragging(),
        };
        console.log('✅ 使用 Tauri 窗口 API');
        return;
      } catch (e) {
        console.warn('Tauri API 加载失败:', e);
      }
    }

    // 2. 回退到 pywebview API（兼容旧代码）
    const pywebviewApi = (window as any).pywebview?.api;
    if (pywebviewApi) {
      windowApi = {
        minimize: () => pywebviewApi.minimize_window?.(),
        maximize: () => pywebviewApi.toggle_maximize?.(),
        close: () => pywebviewApi.close_window?.(),
        startDrag: () => pywebviewApi.start_drag?.(),
      };
      console.log('✅ 使用 pywebview 窗口 API');
      return;
    }

    console.log('⚠️ 无窗口 API（浏览器模式）');
  }

  function minimizeWindow() { windowApi?.minimize(); }
  function maximizeWindow() { windowApi?.maximize(); }
  function closeWindow() { windowApi?.close(); }
  
  // 拖拽处理
  function handleMouseDown(e: MouseEvent) {
    // 只响应左键，且不在按钮上
    if (e.button !== 0) return;
    const target = e.target as HTMLElement;
    if (target.closest('button') || target.closest('.no-drag')) return;
    
    // 调用原生拖拽
    windowApi?.startDrag?.();
  }
  
  // 双击最大化
  function handleDoubleClick(e: MouseEvent) {
    const target = e.target as HTMLElement;
    if (target.closest('button') || target.closest('.no-drag')) return;
    maximizeWindow();
  }
</script>

<!-- 标题栏：支持拖拽移动窗口 -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  data-tauri-drag-region
  class="h-8 bg-secondary/50 flex items-center justify-between px-2 select-none border-b shrink-0"
  onmousedown={handleMouseDown}
  ondblclick={handleDoubleClick}
>
  <!-- 左侧：应用名称（拖拽区域） -->
  <div class="flex items-center gap-2" data-tauri-drag-region>
    <span class="text-sm font-semibold">aestival</span>
  </div>

  <!-- 中间：功能按钮（不可拖拽） -->
  <div class="flex items-center gap-1 no-drag">
    <Button variant="ghost" size="icon" class="h-6 w-6" onclick={toggleThemeMode} title="切换明暗模式">
      {#if $themeStore.mode === 'dark'}
        <Sun class="h-3.5 w-3.5" />
      {:else}
        <Moon class="h-3.5 w-3.5" />
      {/if}
    </Button>
    <Button variant="ghost" size="icon" class="h-6 w-6" onclick={openThemeImport} title="导入主题">
      <Palette class="h-3.5 w-3.5" />
    </Button>
  </div>

  <!-- 右侧：窗口控制按钮（不可拖拽） -->
  <div class="flex items-center no-drag">
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
