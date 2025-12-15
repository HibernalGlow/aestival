<script lang="ts">
  import { Input } from '$lib/components/ui/input';
  import { Button } from '$lib/components/ui/button';
  import { Folder, Clipboard, Check, X } from '@lucide/svelte';
  import { platform } from '$lib/api/platform';
  
  // Props
  export let value: string = '';
  export let placeholder: string = '输入路径...';
  export let disabled: boolean = false;
  
  // 路径验证状态
  let validationStatus: 'idle' | 'valid' | 'invalid' = 'idle';
  let validationMessage: string = '';
  
  // 打开文件夹选择对话框
  async function handleFolderSelect() {
    try {
      const path = await platform.openFolderDialog('选择文件夹');
      if (path) {
        value = path;
        await validatePath(path);
      }
    } catch (error) {
      console.error('打开文件夹对话框失败:', error);
    }
  }
  
  // 从剪贴板读取路径
  async function handleClipboard() {
    try {
      const text = await platform.readClipboard();
      if (text && text.trim()) {
        const cleanedPath = text.trim().replace(/^["']|["']$/g, '');
        value = cleanedPath;
        await validatePath(cleanedPath);
      } else {
        validationStatus = 'invalid';
        validationMessage = '剪贴板为空';
      }
    } catch (error) {
      console.error('读取剪贴板失败:', error);
      validationStatus = 'invalid';
      validationMessage = '读取剪贴板失败';
    }
  }
  
  // 验证路径
  async function validatePath(path: string) {
    if (!path || !path.trim()) {
      validationStatus = 'idle';
      validationMessage = '';
      return;
    }
    
    try {
      const result = await platform.validatePath(path);
      validationStatus = result.valid ? 'valid' : 'invalid';
      validationMessage = result.message;
    } catch (error) {
      validationStatus = 'idle';
      validationMessage = '';
    }
  }
  
  // 输入变化时验证
  function handleInput(event: Event) {
    const target = event.target as HTMLInputElement;
    value = target.value;
    // 延迟验证，避免频繁调用
    clearTimeout(validateTimeout);
    validateTimeout = setTimeout(() => validatePath(value), 500);
  }
  
  let validateTimeout: ReturnType<typeof setTimeout>;
</script>

<div class="flex flex-col gap-1">
  <div class="flex gap-1">
    <div class="relative flex-1">
      <Input 
        {value}
        {placeholder}
        {disabled}
        on:input={handleInput}
        class="pr-8 {validationStatus === 'valid' ? 'border-green-500' : validationStatus === 'invalid' ? 'border-red-500' : ''}"
      />
      {#if validationStatus === 'valid'}
        <Check class="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-green-500" />
      {:else if validationStatus === 'invalid'}
        <X class="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-red-500" />
      {/if}
    </div>
    <Button 
      variant="outline" 
      size="icon" 
      on:click={handleFolderSelect}
      {disabled}
      title="选择文件夹"
    >
      <Folder class="h-4 w-4" />
    </Button>
    <Button 
      variant="outline" 
      size="icon" 
      on:click={handleClipboard}
      {disabled}
      title="从剪贴板粘贴"
    >
      <Clipboard class="h-4 w-4" />
    </Button>
  </div>
  {#if validationMessage && validationStatus !== 'idle'}
    <p class="text-xs {validationStatus === 'valid' ? 'text-green-600' : 'text-red-600'}">
      {validationMessage}
    </p>
  {/if}
</div>
