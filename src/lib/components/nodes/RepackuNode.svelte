<script lang="ts">
  /**
   * RepackuNode - 文件重打包节点组件
   * 
   * 完整流程：
   * 1. 分析阶段：扫描目录结构，生成配置文件
   * 2. 压缩阶段：根据配置执行压缩
   * 
   * 功能：
   * - 路径输入（支持文件夹选择和剪贴板）
   * - 文件类型过滤
   * - 分析结果预览
   * - 压缩后删除源文件选项
   * - 实时进度显示
   * - 执行结果统计
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
    Package,
    CheckCircle,
    XCircle,
    FileArchive,
    Search,
    FolderTree,
    Trash2,
    Copy,
    Check
  } from '@lucide/svelte';
  
  // 复制状态
  let copied = false;
  
  // Props from SvelteFlow
  export let id: string;
  export let data: {
    config?: {
      path?: string;
      types?: string[];
      delete_after?: boolean;
    };
    status?: 'idle' | 'running' | 'completed' | 'error';
    hasInputConnection?: boolean;
    logs?: string[];
    label?: string;
  } = {};

  // 执行阶段
  type Phase = 'idle' | 'analyzing' | 'analyzed' | 'compressing' | 'completed' | 'error';
  
  // 本地状态
  let path = data?.config?.path ?? '';
  let deleteAfter = data?.config?.delete_after ?? false;
  let phase: Phase = 'idle';
  let logs: string[] = data?.logs ? [...data.logs] : [];
  let hasInputConnection = data?.hasInputConnection ?? false;
  
  // 进度状态
  let progress = 0;
  let progressText = '';
  
  // 分析结果
  let analysisResult: {
    configPath: string;
    totalFolders: number;
    entireCount: number;
    selectiveCount: number;
    skipCount: number;
    folderTree?: any;
  } | null = null;
  
  // 压缩结果
  let compressionResult: {
    success: boolean;
    compressed: number;
    failed: number;
    total: number;
  } | null = null;

  // 文件类型选项
  const typeOptions = [
    { value: 'image', label: '图片' },
    { value: 'document', label: '文档' },
    { value: 'video', label: '视频' },
    { value: 'audio', label: '音频' }
  ];
  
  let selectedTypes: string[] = [];

  // 计算按钮是否可用
  $: canAnalyze = phase === 'idle' && (path.trim() !== '' || hasInputConnection);
  $: canCompress = phase === 'analyzed' && analysisResult !== null;
  $: isRunning = phase === 'analyzing' || phase === 'compressing';
  
  // 状态样式
  $: borderClass = {
    idle: 'border-border',
    analyzing: 'border-blue-500 shadow-blue-500/20 shadow-lg',
    analyzed: 'border-yellow-500',
    compressing: 'border-blue-500 shadow-blue-500/20 shadow-lg',
    completed: 'border-green-500',
    error: 'border-red-500'
  }[phase];

  // 打开文件夹选择对话框
  async function selectFolder() {
    try {
      if (window.pywebview?.api?.open_folder_dialog) {
        const selected = await window.pywebview.api.open_folder_dialog();
        if (selected) {
          path = selected;
        }
      } else {
        logs = [...logs, '⚠️ 文件夹选择功能需要在桌面应用中使用'];
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
        if (text) {
          path = text.trim();
        }
      } else {
        const text = await navigator.clipboard.readText();
        path = text.trim();
      }
    } catch (e) {
      logs = [...logs, `读取剪贴板失败: ${e}`];
    }
  }

  // 切换类型选择
  function toggleType(type: string) {
    if (selectedTypes.includes(type)) {
      selectedTypes = selectedTypes.filter(t => t !== type);
    } else {
      selectedTypes = [...selectedTypes, type];
    }
  }

  // 阶段1：分析目录
  async function handleAnalyze() {
    if (!canAnalyze) return;
    
    phase = 'analyzing';
    progress = 0;
    progressText = '正在扫描目录结构...';
    analysisResult = null;
    compressionResult = null;
    logs = [...logs, `🔍 开始分析目录: ${path}`];
    
    if (selectedTypes.length > 0) {
      logs = [...logs, `📋 类型过滤: ${selectedTypes.join(', ')}`];
    }
    
    try {
      progress = 30;
      progressText = '正在分析文件类型分布...';
      
      // 调用分析 API
      const response = await api.executeNode('repacku', {
        action: 'analyze',
        path: path,
        types: selectedTypes.length > 0 ? selectedTypes : [],
        display_tree: true
      }) as {
        success: boolean;
        message: string;
        data?: {
          config_path?: string;
          total_folders?: number;
          entire_count?: number;
          selective_count?: number;
          skip_count?: number;
          folder_tree?: any;
        }
      };
      
      if (response.success && response.data) {
        phase = 'analyzed';
        progress = 100;
        progressText = '分析完成';
        
        analysisResult = {
          configPath: response.data.config_path ?? '',
          totalFolders: response.data.total_folders ?? 0,
          entireCount: response.data.entire_count ?? 0,
          selectiveCount: response.data.selective_count ?? 0,
          skipCount: response.data.skip_count ?? 0,
          folderTree: response.data.folder_tree
        };
        
        logs = [...logs, `✅ 分析完成`];
        logs = [...logs, `📊 整体压缩: ${analysisResult.entireCount}, 选择性: ${analysisResult.selectiveCount}, 跳过: ${analysisResult.skipCount}`];
      } else {
        phase = 'error';
        progress = 0;
        logs = [...logs, `❌ 分析失败: ${response.message}`];
      }
    } catch (error) {
      phase = 'error';
      progress = 0;
      logs = [...logs, `❌ 分析失败: ${error}`];
    }
  }

  // 阶段2：执行压缩
  async function handleCompress() {
    if (!canCompress || !analysisResult) return;
    
    phase = 'compressing';
    progress = 0;
    progressText = '正在压缩文件...';
    logs = [...logs, `📦 开始压缩...`];
    
    try {
      progress = 20;
      
      // 调用压缩 API
      const response = await api.executeNode('repacku', {
        action: 'compress',
        config_path: analysisResult.configPath,
        delete_after: deleteAfter
      }) as {
        success: boolean;
        message: string;
        data?: {
          compressed_count?: number;
          failed_count?: number;
          total_folders?: number;
        }
      };
      
      if (response.success) {
        phase = 'completed';
        progress = 100;
        progressText = '压缩完成';
        
        compressionResult = {
          success: true,
          compressed: response.data?.compressed_count ?? 0,
          failed: response.data?.failed_count ?? 0,
          total: response.data?.total_folders ?? 0
        };
        
        logs = [...logs, `✅ ${response.message}`];
        logs = [...logs, `📊 成功: ${compressionResult.compressed}, 失败: ${compressionResult.failed}`];
      } else {
        phase = 'error';
        progress = 0;
        logs = [...logs, `❌ 压缩失败: ${response.message}`];
      }
    } catch (error) {
      phase = 'error';
      progress = 0;
      logs = [...logs, `❌ 压缩失败: ${error}`];
    }
  }

  // 重置状态
  function handleReset() {
    phase = 'idle';
    progress = 0;
    progressText = '';
    analysisResult = null;
    compressionResult = null;
    logs = [];
  }

  // 复制日志到剪贴板
  async function copyLogs() {
    const text = logs.join('\n');
    try {
      await navigator.clipboard.writeText(text);
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) {
      console.error('复制失败:', e);
    }
  }

  // 忽略未使用的 id 警告
  void id;
</script>

<div class="rounded-lg border-2 bg-card p-4 min-w-[340px] max-w-[420px] {borderClass}">
  <!-- 输入端口 -->
  <Handle type="target" position={Position.Left} class="bg-primary!" />
  
  <!-- 标题栏 -->
  <div class="flex items-center justify-between mb-3">
    <div class="flex items-center gap-2">
      <Package class="w-5 h-5 text-blue-500" />
      <span class="font-semibold">文件重打包</span>
    </div>
    <Badge variant={phase === 'error' ? 'destructive' : phase === 'completed' ? 'default' : 'secondary'}>
      {phase === 'idle' ? '就绪' : 
       phase === 'analyzing' ? '分析中' : 
       phase === 'analyzed' ? '待压缩' :
       phase === 'compressing' ? '压缩中' : 
       phase === 'completed' ? '完成' : '错误'}
    </Badge>
  </div>
  
  <!-- 路径输入区域 -->
  {#if !hasInputConnection}
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
  {:else}
    <div class="text-sm text-muted-foreground mb-3 p-2 bg-muted rounded flex items-center gap-2">
      <span>←</span>
      <span>输入来自上游节点</span>
    </div>
  {/if}
  
  <!-- 文件类型过滤 -->
  <div class="mb-3 space-y-2">
    <Label class="text-xs text-muted-foreground">文件类型过滤（留空处理全部）</Label>
    <div class="flex flex-wrap gap-2">
      {#each typeOptions as option}
        <button
          class="px-2 py-1 text-xs rounded border transition-colors {selectedTypes.includes(option.value) ? 'bg-primary text-primary-foreground border-primary' : 'bg-background border-border hover:border-primary'}"
          onclick={() => toggleType(option.value)}
          disabled={isRunning}
        >
          {option.label}
        </button>
      {/each}
    </div>
  </div>
  
  <!-- 选项 -->
  <div class="mb-3 flex items-center gap-2">
    <Checkbox 
      id="delete-after-{id}" 
      bind:checked={deleteAfter}
      disabled={isRunning}
    />
    <Label for="delete-after-{id}" class="text-xs cursor-pointer flex items-center gap-1">
      <Trash2 class="w-3 h-3" />
      压缩成功后删除源文件
    </Label>
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
  
  <!-- 分析结果 -->
  {#if analysisResult && phase !== 'idle'}
    <div class="mb-3 p-2 rounded bg-muted space-y-2">
      <div class="flex items-center gap-2 text-sm font-medium">
        <FolderTree class="w-4 h-4 text-yellow-500" />
        <span>分析结果</span>
      </div>
      <div class="grid grid-cols-3 gap-2 text-xs">
        <div class="text-center p-1 bg-background rounded">
          <div class="font-semibold text-green-600">{analysisResult.entireCount}</div>
          <div class="text-muted-foreground">整体压缩</div>
        </div>
        <div class="text-center p-1 bg-background rounded">
          <div class="font-semibold text-yellow-600">{analysisResult.selectiveCount}</div>
          <div class="text-muted-foreground">选择性</div>
        </div>
        <div class="text-center p-1 bg-background rounded">
          <div class="font-semibold text-gray-500">{analysisResult.skipCount}</div>
          <div class="text-muted-foreground">跳过</div>
        </div>
      </div>
    </div>
  {/if}
  
  <!-- 压缩结果 -->
  {#if compressionResult}
    <div class="mb-3 p-2 rounded bg-muted space-y-1">
      <div class="flex items-center gap-2 text-sm">
        {#if compressionResult.success}
          <CheckCircle class="w-4 h-4 text-green-500" />
          <span class="text-green-600">压缩完成</span>
        {:else}
          <XCircle class="w-4 h-4 text-red-500" />
          <span class="text-red-600">压缩失败</span>
        {/if}
      </div>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <div class="text-center p-1 bg-background rounded">
          <div class="font-semibold text-green-600">{compressionResult.compressed}</div>
          <div class="text-muted-foreground">成功</div>
        </div>
        <div class="text-center p-1 bg-background rounded">
          <div class="font-semibold text-red-600">{compressionResult.failed}</div>
          <div class="text-muted-foreground">失败</div>
        </div>
      </div>
    </div>
  {/if}
  
  <!-- 操作按钮 -->
  <div class="flex gap-2">
    {#if phase === 'idle' || phase === 'error'}
      <!-- 分析按钮 -->
      <Button 
        class="flex-1" 
        onclick={handleAnalyze}
        disabled={!canAnalyze}
      >
        <Search class="h-4 w-4 mr-2" />
        扫描分析
      </Button>
    {:else if phase === 'analyzing'}
      <!-- 分析中 -->
      <Button class="flex-1" disabled>
        <LoaderCircle class="h-4 w-4 mr-2 animate-spin" />
        分析中...
      </Button>
    {:else if phase === 'analyzed'}
      <!-- 压缩按钮 -->
      <Button 
        class="flex-1" 
        onclick={handleCompress}
        disabled={!canCompress}
      >
        <FileArchive class="h-4 w-4 mr-2" />
        开始压缩
      </Button>
      <Button 
        variant="outline"
        onclick={handleReset}
      >
        重置
      </Button>
    {:else if phase === 'compressing'}
      <Button class="flex-1" disabled>
        <LoaderCircle class="h-4 w-4 mr-2 animate-spin" />
        压缩中...
      </Button>
    {:else if phase === 'completed'}
      <Button 
        class="flex-1" 
        variant="outline"
        onclick={handleReset}
      >
        <Play class="h-4 w-4 mr-2" />
        重新开始
      </Button>
    {/if}
  </div>
  
  <!-- 日志输出 -->
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
          {#if copied}
            <Check class="h-3 w-3 text-green-500" />
          {:else}
            <Copy class="h-3 w-3" />
          {/if}
        </Button>
      </div>
      <div class="p-2 pr-8 bg-muted rounded text-xs font-mono max-h-24 overflow-y-auto space-y-0.5 select-text cursor-text">
        {#each logs.slice(-6) as log}
          <div class="text-muted-foreground break-all whitespace-pre-wrap">{log}</div>
        {/each}
      </div>
    </div>
  {/if}
  
  <!-- 输出端口 -->
  <Handle type="source" position={Position.Right} class="bg-primary!" />
</div>
