<script lang="ts">
  /**
   * TrenameNode - 批量重命名节点
   * 
   * 功能：
   * 1. 扫描目录生成 JSON 结构
   * 2. 根据 JSON 执行批量重命名
   * 3. 撤销重命名操作
   */
  import { Handle, Position } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Badge } from '$lib/components/ui/badge';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Label } from '$lib/components/ui/label';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';
  import { api } from '$lib/services/api';
  import { 
    Play, 
    LoaderCircle, 
    FolderOpen, 
    Clipboard, 
    FileEdit,
    CheckCircle,
    XCircle,
    Search,
    Undo2,
    Copy,
    Check
  } from '@lucide/svelte';
  
  // Props from SvelteFlow
  export let id: string;
  export let data: {
    config?: {
      path?: string;
    };
    status?: 'idle' | 'running' | 'completed' | 'error';
    logs?: string[];
    label?: string;
  } = {};

  // 执行阶段
  type Phase = 'idle' | 'scanning' | 'scanned' | 'renaming' | 'completed' | 'error';
  
  // 本地状态
  let path = data?.config?.path ?? '';
  let phase: Phase = 'idle';
  let logs: string[] = data?.logs ? [...data.logs] : [];
  let copied = false;
  
  // 选项
  let includeRoot = true;
  let includeHidden = false;
  let excludeExts = '.json,.txt,.html,.htm,.md,.log';
  let dryRun = false;
  
  // 进度状态
  let progress = 0;
  let progressText = '';
  
  // 扫描结果
  let scanResult: {
    jsonContent: string;
    segments: string[];
    totalItems: number;
  } | null = null;
  
  // 重命名结果
  let renameResult: {
    successCount: number;
    failedCount: number;
    skippedCount: number;
    operationId: string;
  } | null = null;

  // 计算按钮状态
  $: canScan = phase === 'idle' && path.trim() !== '';
  $: canRename = phase === 'scanned' && scanResult !== null;
  $: isRunning = phase === 'scanning' || phase === 'renaming';
  
  // 状态样式
  $: borderClass = {
    idle: 'border-border',
    scanning: 'border-blue-500 shadow-blue-500/20 shadow-lg',
    scanned: 'border-yellow-500',
    renaming: 'border-blue-500 shadow-blue-500/20 shadow-lg',
    completed: 'border-green-500',
    error: 'border-red-500'
  }[phase];

  // 打开文件夹选择
  async function selectFolder() {
    try {
      if (window.pywebview?.api?.open_folder_dialog) {
        const selected = await window.pywebview.api.open_folder_dialog();
        if (selected) {
          path = selected;
        }
      } else {
        logs = [...logs, '⚠️ 文件夹选择需要桌面应用'];
      }
    } catch (e) {
      logs = [...logs, `选择文件夹失败: ${e}`];
    }
  }

  // 从剪贴板粘贴
  async function pasteFromClipboard() {
    try {
      if (window.pywebview?.api?.read_clipboard) {
        const text = await window.pywebview.api.read_clipboard();
        if (text) path = text.trim();
      } else {
        const text = await navigator.clipboard.readText();
        path = text.trim();
      }
    } catch (e) {
      logs = [...logs, `读取剪贴板失败: ${e}`];
    }
  }

  // 扫描目录
  async function handleScan() {
    if (!canScan) return;
    
    phase = 'scanning';
    progress = 0;
    progressText = '正在扫描目录...';
    scanResult = null;
    renameResult = null;
    logs = [...logs, `🔍 开始扫描: ${path}`];
    
    try {
      progress = 30;
      
      const response = await api.executeNode('trename', {
        action: 'scan',
        paths: [path],
        include_root: includeRoot,
        include_hidden: includeHidden,
        exclude_exts: excludeExts,
        split_lines: 1000,
        compact: false
      }) as {
        success: boolean;
        message: string;
        data?: {
          json_content?: string;
          segments?: string[];
          total_items?: number;
        }
      };
      
      if (response.success && response.data) {
        phase = 'scanned';
        progress = 100;
        progressText = '扫描完成';
        
        scanResult = {
          jsonContent: response.data.json_content ?? '',
          segments: response.data.segments ?? [],
          totalItems: response.data.total_items ?? 0
        };
        
        logs = [...logs, `✅ 扫描完成，共 ${scanResult.totalItems} 项`];
        logs = [...logs, `📋 JSON 已生成，${scanResult.segments.length} 段`];
      } else {
        phase = 'error';
        progress = 0;
        logs = [...logs, `❌ 扫描失败: ${response.message}`];
      }
    } catch (error) {
      phase = 'error';
      progress = 0;
      logs = [...logs, `❌ 扫描失败: ${error}`];
    }
  }

  // 复制 JSON 到剪贴板
  async function copyJson() {
    if (!scanResult?.jsonContent) return;
    try {
      await navigator.clipboard.writeText(scanResult.jsonContent);
      copied = true;
      logs = [...logs, '📋 JSON 已复制到剪贴板'];
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) {
      logs = [...logs, `复制失败: ${e}`];
    }
  }

  // 执行重命名
  async function handleRename() {
    if (!canRename || !scanResult) return;
    
    phase = 'renaming';
    progress = 0;
    progressText = '正在重命名...';
    logs = [...logs, `✏️ 开始重命名${dryRun ? '（模拟）' : ''}...`];
    
    try {
      progress = 30;
      
      const response = await api.executeNode('trename', {
        action: 'rename',
        json_content: scanResult.jsonContent,
        base_path: '',
        dry_run: dryRun
      }) as {
        success: boolean;
        message: string;
        data?: {
          success_count?: number;
          failed_count?: number;
          skipped_count?: number;
          operation_id?: string;
        }
      };
      
      if (response.success) {
        phase = 'completed';
        progress = 100;
        progressText = '重命名完成';
        
        renameResult = {
          successCount: response.data?.success_count ?? 0,
          failedCount: response.data?.failed_count ?? 0,
          skippedCount: response.data?.skipped_count ?? 0,
          operationId: response.data?.operation_id ?? ''
        };
        
        logs = [...logs, `✅ ${response.message}`];
        if (renameResult.operationId) {
          logs = [...logs, `🔄 撤销 ID: ${renameResult.operationId}`];
        }
      } else {
        phase = 'error';
        progress = 0;
        logs = [...logs, `❌ 重命名失败: ${response.message}`];
      }
    } catch (error) {
      phase = 'error';
      progress = 0;
      logs = [...logs, `❌ 重命名失败: ${error}`];
    }
  }

  // 撤销操作
  async function handleUndo() {
    if (!renameResult?.operationId) return;
    
    logs = [...logs, `🔄 撤销操作: ${renameResult.operationId}`];
    
    try {
      const response = await api.executeNode('trename', {
        action: 'undo',
        batch_id: renameResult.operationId
      }) as {
        success: boolean;
        message: string;
      };
      
      if (response.success) {
        logs = [...logs, `✅ ${response.message}`];
        renameResult = null;
        phase = 'scanned';
      } else {
        logs = [...logs, `❌ 撤销失败: ${response.message}`];
      }
    } catch (error) {
      logs = [...logs, `❌ 撤销失败: ${error}`];
    }
  }

  // 重置
  function handleReset() {
    phase = 'idle';
    progress = 0;
    progressText = '';
    scanResult = null;
    renameResult = null;
    logs = [];
  }

  // 复制日志
  async function copyLogs() {
    const text = logs.join('\n');
    try {
      await navigator.clipboard.writeText(text);
    } catch (e) {
      console.error('复制失败:', e);
    }
  }

  void id;
</script>

<div class="rounded-lg border-2 bg-card p-4 min-w-[340px] max-w-[420px] {borderClass}">
  <Handle type="target" position={Position.Left} class="bg-primary!" />
  
  <!-- 标题栏 -->
  <div class="flex items-center justify-between mb-3">
    <div class="flex items-center gap-2">
      <FileEdit class="w-5 h-5 text-purple-500" />
      <span class="font-semibold">批量重命名</span>
    </div>
    <Badge variant={phase === 'error' ? 'destructive' : phase === 'completed' ? 'default' : 'secondary'}>
      {phase === 'idle' ? '就绪' : 
       phase === 'scanning' ? '扫描中' : 
       phase === 'scanned' ? '待重命名' :
       phase === 'renaming' ? '重命名中' : 
       phase === 'completed' ? '完成' : '错误'}
    </Badge>
  </div>
  
  <!-- 路径输入 -->
  <div class="mb-3 space-y-2">
    <Label class="text-xs text-muted-foreground">目标路径</Label>
    <div class="flex gap-1">
      <Input 
        bind:value={path}
        placeholder="输入或选择文件夹路径..."
        disabled={isRunning}
        class="flex-1 h-8 text-sm"
      />
      <Button 
        variant="outline" 
        size="icon" 
        class="h-8 w-8 shrink-0"
        onclick={selectFolder}
        disabled={isRunning}
        title="选择文件夹"
      >
        <FolderOpen class="h-4 w-4" />
      </Button>
      <Button 
        variant="outline" 
        size="icon" 
        class="h-8 w-8 shrink-0"
        onclick={pasteFromClipboard}
        disabled={isRunning}
        title="从剪贴板粘贴"
      >
        <Clipboard class="h-4 w-4" />
      </Button>
    </div>
  </div>
  
  <!-- 选项 -->
  <div class="mb-3 space-y-2">
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-2">
        <Checkbox 
          id="include-root-{id}" 
          bind:checked={includeRoot}
          disabled={isRunning}
        />
        <Label for="include-root-{id}" class="text-xs cursor-pointer">包含根目录</Label>
      </div>
      <div class="flex items-center gap-2">
        <Checkbox 
          id="include-hidden-{id}" 
          bind:checked={includeHidden}
          disabled={isRunning}
        />
        <Label for="include-hidden-{id}" class="text-xs cursor-pointer">包含隐藏文件</Label>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <Checkbox 
        id="dry-run-{id}" 
        bind:checked={dryRun}
        disabled={isRunning}
      />
      <Label for="dry-run-{id}" class="text-xs cursor-pointer">模拟执行（不实际重命名）</Label>
    </div>
  </div>
  
  <!-- 进度条 -->
  {#if isRunning}
    <div class="mb-3 space-y-1">
      <div class="flex justify-between text-xs text-muted-foreground">
        <span>{progressText}</span>
        <span>{progress}%</span>
      </div>
      <Progress value={progress} class="h-2" />
    </div>
  {/if}
  
  <!-- 扫描结果 -->
  {#if scanResult && phase !== 'idle'}
    <div class="mb-3 p-2 rounded bg-muted space-y-2">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2 text-sm font-medium">
          <Search class="w-4 h-4 text-purple-500" />
          <span>扫描结果</span>
        </div>
        <Button 
          variant="ghost" 
          size="icon" 
          class="h-6 w-6"
          onclick={copyJson}
          title="复制 JSON"
        >
          {#if copied}
            <Check class="h-3 w-3 text-green-500" />
          {:else}
            <Copy class="h-3 w-3" />
          {/if}
        </Button>
      </div>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <div class="text-center p-1 bg-background rounded">
          <div class="font-semibold">{scanResult.totalItems}</div>
          <div class="text-muted-foreground">总项目</div>
        </div>
        <div class="text-center p-1 bg-background rounded">
          <div class="font-semibold">{scanResult.segments.length}</div>
          <div class="text-muted-foreground">分段数</div>
        </div>
      </div>
    </div>
  {/if}
  
  <!-- 重命名结果 -->
  {#if renameResult}
    <div class="mb-3 p-2 rounded bg-muted space-y-2">
      <div class="flex items-center gap-2 text-sm">
        {#if renameResult.failedCount === 0}
          <CheckCircle class="w-4 h-4 text-green-500" />
          <span class="text-green-600">重命名完成</span>
        {:else}
          <XCircle class="w-4 h-4 text-yellow-500" />
          <span class="text-yellow-600">部分失败</span>
        {/if}
      </div>
      <div class="grid grid-cols-3 gap-2 text-xs">
        <div class="text-center p-1 bg-background rounded">
          <div class="font-semibold text-green-600">{renameResult.successCount}</div>
          <div class="text-muted-foreground">成功</div>
        </div>
        <div class="text-center p-1 bg-background rounded">
          <div class="font-semibold text-red-600">{renameResult.failedCount}</div>
          <div class="text-muted-foreground">失败</div>
        </div>
        <div class="text-center p-1 bg-background rounded">
          <div class="font-semibold text-yellow-600">{renameResult.skippedCount}</div>
          <div class="text-muted-foreground">跳过</div>
        </div>
      </div>
      {#if renameResult.operationId}
        <Button 
          variant="outline" 
          size="sm" 
          class="w-full h-7 text-xs"
          onclick={handleUndo}
        >
          <Undo2 class="h-3 w-3 mr-1" />
          撤销操作
        </Button>
      {/if}
    </div>
  {/if}
  
  <!-- 操作按钮 -->
  <div class="flex gap-2">
    {#if phase === 'idle' || phase === 'error'}
      <Button 
        class="flex-1" 
        onclick={handleScan}
        disabled={!canScan}
      >
        <Search class="h-4 w-4 mr-2" />
        扫描目录
      </Button>
    {:else if phase === 'scanning'}
      <Button class="flex-1" disabled>
        <LoaderCircle class="h-4 w-4 mr-2 animate-spin" />
        扫描中...
      </Button>
    {:else if phase === 'scanned'}
      <Button 
        class="flex-1" 
        onclick={handleRename}
        disabled={!canRename}
      >
        <Play class="h-4 w-4 mr-2" />
        执行重命名
      </Button>
      <Button variant="outline" onclick={handleReset}>重置</Button>
    {:else if phase === 'renaming'}
      <Button class="flex-1" disabled>
        <LoaderCircle class="h-4 w-4 mr-2 animate-spin" />
        重命名中...
      </Button>
    {:else if phase === 'completed'}
      <Button class="flex-1" variant="outline" onclick={handleReset}>
        <Play class="h-4 w-4 mr-2" />
        重新开始
      </Button>
    {/if}
  </div>
  
  <!-- 日志 -->
  {#if logs.length > 0}
    <div class="mt-3 relative">
      <div class="absolute top-1 right-1 z-10">
        <Button 
          variant="ghost" 
          size="icon" 
          class="h-6 w-6 opacity-60 hover:opacity-100"
          onclick={copyLogs}
          title="复制日志"
        >
          <Copy class="h-3 w-3" />
        </Button>
      </div>
      <div class="p-2 pr-8 bg-muted rounded text-xs font-mono max-h-24 overflow-y-auto space-y-0.5 select-text cursor-text">
        {#each logs.slice(-6) as log}
          <div class="text-muted-foreground break-all whitespace-pre-wrap">{log}</div>
        {/each}
      </div>
    </div>
  {/if}
  
  <Handle type="source" position={Position.Right} class="bg-primary!" />
</div>
