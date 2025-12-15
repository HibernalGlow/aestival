"""
终端 WebSocket API
捕获并推送所有终端输出（stdout/stderr）
"""

import sys
import asyncio
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from io import StringIO
import threading

router = APIRouter(tags=["terminal"])


class TerminalCapture:
    """
    终端输出捕获器
    
    捕获 stdout 和 stderr，并通过 WebSocket 推送给所有连接的客户端
    """
    
    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self._original_stdout = None
        self._original_stderr = None
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop = None
        self._buffer: list[str] = []
        self._installed = False
    
    def install(self, loop: asyncio.AbstractEventLoop):
        """安装输出捕获"""
        if self._installed:
            return
            
        self._loop = loop
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        
        # 创建自定义的输出流
        sys.stdout = OutputCapture(self, self._original_stdout, "stdout")
        sys.stderr = OutputCapture(self, self._original_stderr, "stderr")
        
        self._installed = True
        print("🖥️ 终端输出捕获已启动")
    
    def uninstall(self):
        """卸载输出捕获"""
        if not self._installed:
            return
            
        if self._original_stdout:
            sys.stdout = self._original_stdout
        if self._original_stderr:
            sys.stderr = self._original_stderr
        
        self._installed = False
    
    async def connect(self, websocket: WebSocket):
        """添加 WebSocket 连接"""
        await websocket.accept()
        self.connections.add(websocket)
        
        # 发送缓冲区中的历史消息
        if self._buffer:
            for text in self._buffer[-50:]:  # 最近50条
                try:
                    await websocket.send_json({
                        "type": "output",
                        "text": text
                    })
                except:
                    pass
    
    def disconnect(self, websocket: WebSocket):
        """移除 WebSocket 连接"""
        self.connections.discard(websocket)
    
    def on_output(self, text: str, stream: str = "stdout"):
        """处理输出"""
        if not text.strip():
            return
        
        # 添加到缓冲区
        with self._lock:
            self._buffer.append(text)
            # 限制缓冲区大小
            if len(self._buffer) > 500:
                self._buffer = self._buffer[-500:]
        
        # 异步发送给所有连接
        if self._loop and self.connections:
            asyncio.run_coroutine_threadsafe(
                self._broadcast(text, stream),
                self._loop
            )
    
    async def _broadcast(self, text: str, stream: str):
        """广播消息给所有连接"""
        dead_connections = set()
        
        for ws in self.connections:
            try:
                await ws.send_json({
                    "type": "output",
                    "text": text,
                    "stream": stream
                })
            except:
                dead_connections.add(ws)
        
        # 清理断开的连接
        self.connections -= dead_connections


class OutputCapture:
    """自定义输出流，捕获写入的内容"""
    
    def __init__(self, capture: TerminalCapture, original, stream_name: str):
        self._capture = capture
        self._original = original
        self._stream_name = stream_name
    
    def write(self, text: str):
        # 写入原始流
        if self._original:
            self._original.write(text)
            self._original.flush()
        
        # 通知捕获器
        if text.strip():
            self._capture.on_output(text, self._stream_name)
    
    def flush(self):
        if self._original:
            self._original.flush()
    
    def fileno(self):
        if self._original:
            return self._original.fileno()
        return -1
    
    # 代理其他属性
    def __getattr__(self, name):
        return getattr(self._original, name)


# 全局捕获器实例
terminal_capture = TerminalCapture()


@router.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket):
    """
    终端 WebSocket 端点
    
    连接后接收所有终端输出
    """
    # 确保捕获器已安装
    loop = asyncio.get_event_loop()
    terminal_capture.install(loop)
    
    await terminal_capture.connect(websocket)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "已连接到终端输出"
        })
        
        # 保持连接
        while True:
            try:
                data = await websocket.receive_text()
                # 可以处理客户端命令
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data == "clear":
                    terminal_capture._buffer.clear()
                    
            except WebSocketDisconnect:
                break
                
    finally:
        terminal_capture.disconnect(websocket)


# 导出
__all__ = ["router", "terminal_capture"]
