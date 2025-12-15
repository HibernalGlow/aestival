<script lang="ts">
  /**
   * TerminalNode - 终端输出节点
   * 
   * 通过 WebSocket 连接后端，实时显示所有终端输出
   */
  import { Handle, Position } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Badge } from '$lib/components/ui/badge';
  import { onMount, onDestroy } from 'svelte';
  import { 
    Terminal, 
    Trash2, 
    Copy, 
    Check,
    Wifi,
    WifiOff,
    Pause,
    Play
  } from '@lucide/svelte';
  
  // Props from SvelteFlow
  export let id: string;
  export let data: {
    label?: string;
    maxLines?: number;
  } = {};

  // 状态
  let connected = false;
  let paused = false;
  let copied = false;
  let lines: string[] = [];
  let ws: WebSocket | null = null;
  let terminalEl: HTMLDivElement;
  
  const maxLines = data?.maxLines ?? 200;
  const wsUrl = `ws://localhost:8009/ws/terminal`;

  // 连接 WebSocket
  function connect() {
    if (ws) {
      ws.close();
    }
    
    try {
      ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        connected = true;
        addLine('🟢 已连接到终端');
      };
      
      ws.onmessage = (event) => {
        if (paused) return;
        
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'output') {
            addLine(data.text);
          } else if (data.type === 'connected') {
            addLine(`📡 ${data.message || '连接成功'}`);
          }
        } catch {
          // 纯文本消息
          addLine(event.data);
        }
      };
      
      ws.onclose = () => {
        connected = false;
        addLine('🔴 连接已断开');
      };
      
      ws.onerror = () => {
        connected = false;
        addLine('❌ 连接错误');
      };
    } catch (e) {
      addLine(`❌ 无法连接: ${e}`);
    }
  }

  // 添加一行输出
  function addLine(text: string) {
    // 处理多行文本
    const newLines = text.split('\n').filter(l => l.length > 0);
    lines = [...lines, ...newLines].slice(-maxLines);
    
    // 自动滚动到底部
    requestAnimationFrame(() => {
      if (terminalEl) {
        terminalEl.scrollTop = terminalEl.scrollHeight;
      }
    });
  }

  // 清空终端
  function clear() {
    lines = [];
  }

  // 复制内容
  async function copyContent() {
    const text = lines.join('\n');
    try {
      await navigator.clipboard.writeText(text);
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) {
      console.error('复制失败:', e);
    }
  }

  // 切换暂停
  function togglePause() {
    paused = !paused;
    addLine(paused ? '⏸️ 已暂停' : '▶️ 已恢复');
  }

  // 重新连接
  function reconnect() {
    addLine('🔄 正在重新连接...');
    connect();
  }

  onMount(() => {
    connect();
  });

  onDestroy(() => {
    if (ws) {
      ws.close();
    }
  });

  // 忽略未使用的 id 警告
  void id;
</script>

<div class="rounded-lg border-2 bg-card min-w-[400px] max-w-[600px] {connected ? 'border-green-500/50' : 'border-border'}">
  <!-- 输入端口 -->
  <Handle type="target" position={Position.Left} class="bg-primary!" />
  
  <!-- 标题栏 -->
  <div class="flex items-center justify-between p-3 border-b border-border">
    <div class="flex items-center gap-2">
      <Terminal class="w-5 h-5 text-green-500" />
      <span class="font-semibold">{data?.label ?? '终端输出'}</span>
    </div>
    <div class="flex items-center gap-2">
      <Badge variant={connected ? 'default' : 'secondary'} class="text-xs">
        {#if connected}
          <Wifi class="w-3 h-3 mr-1" />
          已连接
        {:else}
          <WifiOff class="w-3 h-3 mr-1" />
          未连接
        {/if}
      </Badge>
    </div>
  </div>
  
  <!-- 终端内容 -->
  <div 
    bind:this={terminalEl}
    class="bg-zinc-900 text-zinc-100 p-3 font-mono text-xs h-[300px] overflow-y-auto select-text cursor-text"
  >
    {#each lines as line, i}
      <div class="whitespace-pre-wrap break-all leading-relaxed {line.startsWith('❌') ? 'text-red-400' : line.startsWith('✅') ? 'text-green-400' : line.startsWith('⚠️') ? 'text-yellow-400' : ''}">{line}</div>
    {/each}
    {#if lines.length === 0}
      <div class="text-zinc-500 italic">等待输出...</div>
    {/if}
  </div>
  
  <!-- 工具栏 -->
  <div class="flex items-center justify-between p-2 border-t border-border bg-muted/50">
    <div class="flex items-center gap-1">
      <Button 
        variant="ghost" 
        size="icon" 
        class="h-7 w-7"
        onclick={togglePause}
        title={paused ? '恢复' : '暂停'}
      >
        {#if paused}
          <Play class="h-4 w-4" />
        {:else}
          <Pause class="h-4 w-4" />
        {/if}
      </Button>
      <Button 
        variant="ghost" 
        size="icon" 
        class="h-7 w-7"
        onclick={clear}
        title="清空"
      >
        <Trash2 class="h-4 w-4" />
      </Button>
      <Button 
        variant="ghost" 
        size="icon" 
        class="h-7 w-7"
        onclick={copyContent}
        title="复制"
      >
        {#if copied}
          <Check class="h-4 w-4 text-green-500" />
        {:else}
          <Copy class="h-4 w-4" />
        {/if}
      </Button>
    </div>
    <div class="flex items-center gap-2">
      <span class="text-xs text-muted-foreground">{lines.length} 行</span>
      {#if !connected}
        <Button 
          variant="outline" 
          size="sm" 
          class="h-7 text-xs"
          onclick={reconnect}
        >
          重新连接
        </Button>
      {/if}
    </div>
  </div>
  
  <!-- 输出端口 -->
  <Handle type="source" position={Position.Right} class="bg-primary!" />
</div>
