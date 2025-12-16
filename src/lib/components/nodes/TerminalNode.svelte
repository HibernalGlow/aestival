<script lang="ts">
  /**
   * TerminalNode - 终端输出节点
   * 
   * 通过 WebSocket 连接后端，实时显示所有终端输出
   * 支持 ANSI 颜色转换，自动获取后端端口
   */
  import { Handle, Position } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { onMount, onDestroy } from 'svelte';
  import NodeWrapper from './NodeWrapper.svelte';
  import { 
    Terminal, Trash2, Copy, Check, Wifi, WifiOff, Pause, Play
  } from '@lucide/svelte';
  import AnsiToHtml from 'ansi-to-html';
  import { invoke } from '@tauri-apps/api/core';
  
  export let id: string;
  export let data: {
    label?: string;
    maxLines?: number;
  } = {};

  // ANSI 转 HTML 转换器
  const ansiConverter = new AnsiToHtml({
    fg: '#d4d4d4',
    bg: '#18181b',
    colors: {
      0: '#18181b', 1: '#ef4444', 2: '#22c55e', 3: '#eab308',
      4: '#3b82f6', 5: '#a855f7', 6: '#06b6d4', 7: '#d4d4d4',
      8: '#71717a', 9: '#f87171', 10: '#4ade80', 11: '#facc15',
      12: '#60a5fa', 13: '#c084fc', 14: '#22d3ee', 15: '#fafafa'
    }
  });

  // 状态
  let connected = false;
  let paused = false;
  let copied = false;
  let lines: { text: string; html: string }[] = [];
  let ws: WebSocket | null = null;
  let terminalEl: HTMLDivElement;
  let backendPort = 8009;  // 默认端口
  
  const maxLines = data?.maxLines ?? 200;
  
  // 动态获取 WebSocket URL
  $: wsUrl = `ws://localhost:${backendPort}/ws/terminal`;

  // 边框样式
  $: borderClass = connected ? 'border-primary/50' : 'border-border';

  function connect() {
    retryCount = 0;
    connectWithRetry();
  }

  function addLine(text: string) {
    const newLines = text.split('\n')
      .filter(l => l.length > 0)
      .map(l => ({
        text: l.replace(/\x1B\[[0-9;]*[a-zA-Z]/g, '').replace(/\[[\d;]*m/g, ''),
        html: ansiConverter.toHtml(l)
      }));
    lines = [...lines, ...newLines].slice(-maxLines);
    
    requestAnimationFrame(() => {
      if (terminalEl) terminalEl.scrollTop = terminalEl.scrollHeight;
    });
  }

  function clear() { lines = []; }

  async function copyContent() {
    const text = lines.map(l => l.text).join('\n');
    try {
      await navigator.clipboard.writeText(text);
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) {
      console.error('复制失败:', e);
    }
  }

  function togglePause() {
    paused = !paused;
    addLine(paused ? '⏸️ 已暂停' : '▶️ 已恢复');
  }

  function reconnect() {
    addLine('🔄 正在重新连接...');
    connect();
  }

  // 获取后端端口并连接（带重试）
  let retryCount = 0;
  const maxRetries = 5;
  
  async function initConnection() {
    try {
      // 从 Tauri 获取实际端口
      backendPort = await invoke<number>('get_backend_port');
      addLine(`📍 后端端口: ${backendPort}`);
    } catch (e) {
      // 非 Tauri 环境或获取失败，使用默认端口
      addLine(`⚠️ 使用默认端口: ${backendPort}`);
    }
    // 等待服务启动
    await new Promise(r => setTimeout(r, 500));
    connectWithRetry();
  }
  
  function connectWithRetry() {
    if (ws) ws.close();
    
    try {
      ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        connected = true;
        retryCount = 0;
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
          addLine(event.data);
        }
      };
      
      ws.onclose = () => {
        connected = false;
        if (retryCount < maxRetries) {
          retryCount++;
          addLine(`🔄 重试连接 (${retryCount}/${maxRetries})...`);
          setTimeout(connectWithRetry, 1000 * retryCount);
        } else {
          addLine('🔴 连接已断开');
        }
      };
      
      ws.onerror = () => {
        connected = false;
        // onclose 会处理重试
      };
    } catch (e) {
      addLine(`❌ 无法连接: ${e}`);
    }
  }

  onMount(() => { initConnection(); });
  onDestroy(() => { 
    retryCount = maxRetries; // 阻止重试
    if (ws) ws.close(); 
  });
</script>

<div class="min-w-[280px] max-w-[400px]">
  <Handle type="target" position={Position.Left} class="bg-primary!" />
  
  <NodeWrapper
    nodeId={id}
    title={data?.label ?? '终端输出'}
    icon={Terminal}
    status={connected ? 'connected' : 'disconnected'}
    statusLabel={connected ? '已连接' : '未连接'}
    statusVariant={connected ? 'default' : 'secondary'}
    {borderClass}
  >
    {#snippet headerExtra()}
      {#if connected}
        <Wifi class="w-3 h-3 text-green-500 mr-1" />
      {:else}
        <WifiOff class="w-3 h-3 text-muted-foreground mr-1" />
      {/if}
    {/snippet}
    
    {#snippet children()}
      <!-- 终端内容 -->
      <div 
        bind:this={terminalEl}
        class="bg-zinc-900 text-zinc-100 p-2 font-mono text-xs h-[180px] overflow-y-auto select-text cursor-text"
      >
        {#each lines as line}
          <div class="whitespace-pre-wrap break-all leading-relaxed">{@html line.html}</div>
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
          <span class="text-xs text-muted-foreground" title="后端端口">:{backendPort}</span>
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
    {/snippet}
  </NodeWrapper>
  
  <Handle type="source" position={Position.Right} class="bg-primary!" />
</div>
