<script lang="ts">
  /**
   * aestival - 自定义标题栏组件
   * 无边框窗口的标题栏，支持拖拽移动和窗口控制
   * 符合 shadcn 设计风格
   */
  import { Button } from '$lib/components/ui/button';
  import { Separator } from '$lib/components/ui/separator';
  import { 
    Minus, Square, X, Sun, Moon, Palette, 
    Maximize2, Minimize2, Settings, Workflow
  } from '@lucide/svelte';
  import { themeStore, toggleThemeMode, openThemeImport } from '$lib/stores/theme.svelte';
  import { onMount } from 'svelte';
  import { isTauriEnvironment } from '$lib/api/platform';

  // 窗口 API 类型
  type WindowAPI = {
    minimize: () => void | Promise<void>;
    maximize: () => void | Promise<void>;
    close: () => void | Promise<void>;
    startDrag?: () => void | Promise<void>;
    isMaximized?: () => Promise<boolean>;
  };

  let windowApi: WindowAPI | null = null;
  let isMaximized = $state(false);

  onMount(() => {
    initWindowApi();
  });

  async function initWindowApi() {
    // 优先尝试 Tauri API
    if (isTauriEnvironment()) {
      try {
        const { getCurrentWebviewWindow } = await import('@tauri-apps/api/webviewWindow');
        const appWindow = getCurrentWebviewWindow();
        windowApi = {
          minimize: () => appWindow.minimize(),
          maximize: () => appWindow.toggleMaximize(),
          close: () => appWindow.close(),
          startDrag: () => appWindow.startDragging(),
          isMaximized: () => appWindow.isMaximized(),
        };
        
        // 监听窗口状态变化
        appWindow.onResized(async () => {
          isMaximized = await appWindow.isMaximized();
        });
        
        // 初始化最大化状态
        isMaximized = await appWindow.isMaximized();
        return;
      } catch (e) {
        console.warn('Tauri API 加载失败:', e);
      }
    }

    // 回退到 pywebview API
    const pywebviewApi = (window as any).pywebview?.api;
    if (pywebviewApi) {
      windowApi = {
        minimize: () => pywebviewApi.minimize_window?.(),
        maximize: () => pywebviewApi.toggle_maximize?.(),
        close: () => pywebviewApi.close_window?.(),
        startDrag: () => pywebviewApi.start_drag?.(),
      };
    }
  }

  function minimizeWindow() { windowApi?.minimize(); }
  function maximizeWindow() { windowApi?.maximize(); }
  function closeWindow() { windowApi?.close(); }
  
  // 拖拽处理
  function handleMouseDown(e: MouseEvent) {
    if (e.button !== 0) return;
    const target = e.target as HTMLElement;
    if (target.closest('button') || target.closest('.no-drag') || target.closest('[data-no-drag]')) return;
    windowApi?.startDrag?.();
  }
  
  // 双击最大化
  function handleDoubleClick(e: MouseEvent) {
    const target = e.target as HTMLElement;
    if (target.closest('button') || target.closest('.no-drag') || target.closest('[data-no-drag]')) return;
    maximizeWindow();
  }
</script>

<!-- 标题栏：shadcn 风格 -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<header
  data-tauri-drag-region
  class="h-10 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 flex items-center justify-between px-3 select-none border-b shrink-0"
  onmousedown={handleMouseDown}
  ondblclick={handleDoubleClick}
>
  <!-- 左侧：Logo + 应用名称 -->
  <div class="flex items-center gap-2" data-tauri-drag-region>
    <div class="flex items-center justify-center w-6 h-6 rounded-md bg-primary/10">
      <Workflow class="h-4 w-4 text-primary" />
    </div>
    <span class="text-sm font-medium tracking-tight">aestival</span>
    <span class="text-xs text-muted-foreground hidden sm:inline">flow</span>
  </div>

  <!-- 中间：功能按钮 -->
  <div class="flex items-center gap-0.5 no-drag" data-no-drag>
    <Button 
      variant="ghost" 
      size="icon" 
      class="h-7 w-7 rounded-md" 
      onclick={toggleThemeMode} 
      title={$themeStore.mode === 'dark' ? '切换到亮色模式' : '切换到暗色模式'}
    >
      {#if $themeStore.mode === 'dark'}
        <Sun class="h-4 w-4" />
      {:else}
        <Moon class="h-4 w-4" />
      {/if}
    </Button>
    <Button 
      variant="ghost" 
      size="icon" 
      class="h-7 w-7 rounded-md" 
      onclick={openThemeImport} 
      title="主题设置"
    >
      <Palette class="h-4 w-4" />
    </Button>
  </div>

  <!-- 右侧：窗口控制按钮 -->
  <div class="flex items-center -mr-1 no-drag" data-no-drag>
    <!-- 最小化 -->
    <button
      class="inline-flex items-center justify-center h-10 w-11 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
      onclick={minimizeWindow}
      title="最小化"
    >
      <Minus class="h-4 w-4" />
    </button>
    
    <!-- 最大化/还原 -->
    <button
      class="inline-flex items-center justify-center h-10 w-11 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
      onclick={maximizeWindow}
      title={isMaximized ? '还原' : '最大化'}
    >
      {#if isMaximized}
        <Minimize2 class="h-3.5 w-3.5" />
      {:else}
        <Maximize2 class="h-3.5 w-3.5" />
      {/if}
    </button>
    
    <!-- 关闭 -->
    <button
      class="inline-flex items-center justify-center h-10 w-11 text-muted-foreground hover:bg-destructive hover:text-destructive-foreground transition-colors"
      onclick={closeWindow}
      title="关闭"
    >
      <X class="h-4 w-4" />
    </button>
  </div>
</header>
