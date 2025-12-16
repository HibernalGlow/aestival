<script lang="ts">
  /**
   * PathBlock - 路径输入区块
   * 支持普通模式和全屏模式的统一渲染
   */
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { FolderOpen, Clipboard, RefreshCw, Download, LoaderCircle } from '@lucide/svelte';

  interface Props {
    isFullscreen?: boolean;
    scanPath: string;
    isRunning: boolean;
    isScanning: boolean;
    onPathChange: (path: string) => void;
    onSelectFolder: () => void;
    onPastePath: () => void;
    onScan: (merge: boolean) => void;
  }

  let {
    isFullscreen = false,
    scanPath,
    isRunning,
    isScanning,
    onPathChange,
    onSelectFolder,
    onPastePath,
    onScan
  }: Props = $props();
</script>

{#if isFullscreen}
  <!-- 全屏模式 -->
  <div class="h-full flex flex-col p-2">
    <div class="flex items-center gap-2 mb-3">
      <FolderOpen class="w-5 h-5 text-primary" />
      <span class="font-semibold">扫描路径</span>
    </div>
    <div class="flex gap-2 mb-4">
      <Input value={scanPath} oninput={(e) => onPathChange(e.currentTarget.value)} placeholder="输入目录路径..." disabled={isRunning} class="flex-1 h-10" />
      <Button variant="outline" size="icon" class="h-10 w-10 shrink-0" onclick={onSelectFolder} disabled={isRunning}>
        <FolderOpen class="h-4 w-4" />
      </Button>
      <Button variant="outline" size="icon" class="h-10 w-10 shrink-0" onclick={onPastePath} disabled={isRunning}>
        <Clipboard class="h-4 w-4" />
      </Button>
    </div>
    <div class="flex gap-2">
      <Button variant="outline" class="flex-1 h-12" onclick={() => onScan(false)} disabled={isRunning}>
        {#if isScanning}<LoaderCircle class="h-4 w-4 mr-2 animate-spin" />{:else}<RefreshCw class="h-4 w-4 mr-2" />{/if}替换扫描
      </Button>
      <Button variant="outline" class="flex-1 h-12" onclick={() => onScan(true)} disabled={isRunning}>
        <Download class="h-4 w-4 mr-2" />合并扫描
      </Button>
    </div>
  </div>
{:else}
  <!-- 普通模式 -->
  <div class="flex items-center gap-1.5 mb-2">
    <FolderOpen class="w-4 h-4 text-primary" />
    <span class="text-xs font-semibold">路径</span>
  </div>
  <div class="flex gap-1">
    <Input value={scanPath} oninput={(e) => onPathChange(e.currentTarget.value)} placeholder="输入路径..." disabled={isRunning} class="flex-1 h-7 text-xs" />
    <Button variant="outline" size="icon" class="h-7 w-7 shrink-0" onclick={onSelectFolder} disabled={isRunning}>
      <FolderOpen class="h-3 w-3" />
    </Button>
    <Button variant="outline" size="icon" class="h-7 w-7 shrink-0" onclick={onPastePath} disabled={isRunning}>
      <Clipboard class="h-3 w-3" />
    </Button>
  </div>
{/if}
