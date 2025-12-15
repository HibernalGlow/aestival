<script lang="ts">
  /**
   * 主题导入对话框
   * 支持从剪贴板导入 tweakcn.com 的主题 JSON
   */
  import { Button } from '$lib/components/ui/button';
  import { themeStore, closeThemeImport } from '$lib/stores/theme.svelte';
  import { X, Clipboard, RotateCcw, Check, AlertCircle } from '@lucide/svelte';

  let jsonInput = '';
  let status: 'idle' | 'success' | 'error' = 'idle';
  let errorMessage = '';

  async function pasteFromClipboard() {
    try {
      jsonInput = await navigator.clipboard.readText();
      status = 'idle';
    } catch {
      errorMessage = '无法读取剪贴板';
      status = 'error';
    }
  }

  function handleImport() {
    if (!jsonInput.trim()) {
      errorMessage = '请输入主题 JSON';
      status = 'error';
      return;
    }
    const success = themeStore.importThemeJSON(jsonInput);
    if (success) {
      status = 'success';
      setTimeout(() => { closeThemeImport(); jsonInput = ''; status = 'idle'; }, 500);
    } else {
      errorMessage = '无效的主题格式';
      status = 'error';
    }
  }

  function handleReset() {
    themeStore.setTheme('Default');
    status = 'success';
    setTimeout(() => { closeThemeImport(); status = 'idle'; }, 500);
  }

  function handleClose() {
    closeThemeImport();
    jsonInput = '';
    status = 'idle';
  }
</script>

{#if $themeStore.showImportDialog}
  <div class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" role="dialog">
    <div class="bg-card border rounded-lg shadow-lg w-[500px] max-w-[90vw] max-h-[80vh] flex flex-col">
      <div class="flex items-center justify-between p-4 border-b">
        <h2 class="text-lg font-semibold">导入主题</h2>
        <Button variant="ghost" size="icon" class="h-8 w-8" onclick={handleClose}><X class="h-4 w-4" /></Button>
      </div>
      <div class="p-4 space-y-4 flex-1 overflow-y-auto">
        <p class="text-sm text-muted-foreground">从 tweakcn.com 复制主题 JSON 粘贴到下方：</p>
        <div class="relative">
          <textarea bind:value={jsonInput} placeholder='&#123;"name": "...", "cssVars": &#123;...&#125;&#125;' class="w-full h-48 p-3 text-xs font-mono bg-muted border rounded resize-none focus:outline-none focus:ring-2 focus:ring-ring"></textarea>
          <Button variant="ghost" size="sm" class="absolute top-2 right-2 h-7" onclick={pasteFromClipboard}><Clipboard class="h-3 w-3 mr-1" />粘贴</Button>
        </div>
        {#if status === 'error'}
          <div class="flex items-center gap-2 text-sm text-destructive"><AlertCircle class="h-4 w-4" />{errorMessage}</div>
        {:else if status === 'success'}
          <div class="flex items-center gap-2 text-sm text-green-500"><Check class="h-4 w-4" />主题已应用</div>
        {/if}
        <div class="text-xs text-muted-foreground">当前主题: <span class="font-medium">{$themeStore.themeName}</span></div>
      </div>
      <div class="flex items-center justify-between p-4 border-t">
        <Button variant="outline" size="sm" onclick={handleReset}><RotateCcw class="h-3 w-3 mr-1" />恢复默认</Button>
        <div class="flex gap-2">
          <Button variant="ghost" size="sm" onclick={handleClose}>取消</Button>
          <Button size="sm" onclick={handleImport}>导入</Button>
        </div>
      </div>
    </div>
  </div>
{/if}
