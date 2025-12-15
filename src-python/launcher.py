"""
aestival 独立启动器（可选）
用于开发模式或不使用 Tauri 时的独立运行
注意：生产环境请使用 Tauri 构建

依赖：pip install pywebview（可选）
"""

import os
import sys
import time
import socket
import threading
from typing import Optional

import webview
import uvicorn
from uvicorn import Config, Server

from bridge import BridgeAPI


class aestivalApp:
    """aestival 应用程序主入口类"""
    
    # 默认配置
    DEFAULT_PORT = 8009
    DEFAULT_HOST = "127.0.0.1"
    FRONTEND_DEV_PORT = 5175  # Vite 开发服务器端口
    WINDOW_TITLE = "aestival"
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 900
    SERVER_TIMEOUT = 10  # 等待服务器启动的超时时间（秒）
    
    def __init__(self, port: int = DEFAULT_PORT, host: str = DEFAULT_HOST, dev_mode: bool = False):
        """
        初始化应用程序
        
        Args:
            port: FastAPI 服务器端口
            host: FastAPI 服务器主机地址
            dev_mode: 开发模式，使用前端开发服务器
        """
        self.port = port
        self.host = host
        self.dev_mode = dev_mode
        self.server_thread: Optional[threading.Thread] = None
        self.server: Optional[Server] = None
        self.window: Optional[webview.Window] = None
        self.api: Optional[BridgeAPI] = None
        self._server_started = threading.Event()
    
    def start(self):
        """启动应用程序"""
        print(f"🚀 启动 aestival...")
        
        # 1. 查找可用端口
        self.port = self._find_available_port()
        print(f"📡 使用端口: {self.port}")
        
        # 2. 启动 FastAPI 后端服务器（后台线程）
        self.server_thread = threading.Thread(
            target=self._run_server, 
            daemon=True,
            name="FastAPI-Server"
        )
        self.server_thread.start()
        
        # 3. 等待服务器就绪
        if not self._wait_for_server():
            print("❌ 服务器启动超时")
            sys.exit(1)
        
        print(f"✅ 服务器已就绪: http://{self.host}:{self.port}")
        
        # 4. 创建 pywebview 窗口
        self._create_window()
        
        # 5. 启动 pywebview 事件循环（阻塞）
        print(f"🖥️ 启动窗口...")
        webview.start(debug=self._is_debug_mode())
        
        # 6. 窗口关闭后清理资源
        self._cleanup()
    
    def _run_server(self):
        """在后台线程运行 FastAPI 服务器"""
        try:
            # 延迟导入 app，避免循环导入
            from main import app
            
            config = Config(
                app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=False  # 减少日志噪音
            )
            self.server = Server(config)
            
            # 标记服务器即将启动
            self._server_started.set()
            
            # 运行服务器（阻塞当前线程）
            import asyncio
            asyncio.run(self.server.serve())
            
        except Exception as e:
            print(f"❌ 服务器启动失败: {e}")
            self._server_started.set()  # 即使失败也要设置，避免主线程永久等待
    
    def _wait_for_server(self, timeout: float = None) -> bool:
        """
        等待服务器就绪
        
        Args:
            timeout: 超时时间（秒），默认使用 SERVER_TIMEOUT
            
        Returns:
            服务器是否成功启动
        """
        timeout = timeout or self.SERVER_TIMEOUT
        start_time = time.time()
        
        # 首先等待服务器线程开始运行
        self._server_started.wait(timeout=timeout)
        
        # 然后轮询检查服务器是否可以接受连接
        while time.time() - start_time < timeout:
            if self._is_server_ready():
                return True
            time.sleep(0.1)
        
        return False
    
    def _is_server_ready(self) -> bool:
        """检查服务器是否已准备好接受连接"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((self.host, self.port))
                return True
        except (socket.error, socket.timeout):
            return False
    
    def _find_available_port(self, start_port: int = None, max_attempts: int = 10) -> int:
        """
        查找可用端口
        
        Args:
            start_port: 起始端口，默认使用 DEFAULT_PORT
            max_attempts: 最大尝试次数
            
        Returns:
            可用的端口号
        """
        start_port = start_port or self.DEFAULT_PORT
        
        for offset in range(max_attempts):
            port = start_port + offset
            if self._is_port_available(port):
                return port
        
        # 如果没有找到可用端口，返回默认端口
        return start_port
    
    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((self.host, port))
                return True
        except OSError:
            return False
    
    def _create_window(self):
        """创建 pywebview 窗口"""
        # 创建桥接 API 实例
        self.api = BridgeAPI()
        
        # 确定窗口 URL
        if self.dev_mode:
            # 开发模式：使用前端开发服务器
            window_url = f"http://{self.host}:{self.FRONTEND_DEV_PORT}"
            print(f"🔧 开发模式: 使用前端服务器 {window_url}")
        else:
            # 生产模式：使用后端服务器（需要构建前端）
            window_url = f"http://{self.host}:{self.port}"
        
        # 创建窗口（使用原生标题栏）
        self.window = webview.create_window(
            title=self.WINDOW_TITLE,
            url=window_url,
            width=self.WINDOW_WIDTH,
            height=self.WINDOW_HEIGHT,
            js_api=self.api,
            min_size=(800, 600)
        )
        
        # 将窗口引用传递给桥接 API
        self.api.set_window(self.window)
    
    def _cleanup(self):
        """清理资源"""
        print("🛑 正在关闭...")
        
        # 停止服务器
        if self.server:
            self.server.should_exit = True
        
        print("👋 再见!")
    
    def _is_debug_mode(self) -> bool:
        """检查是否为调试模式"""
        return (
            "--debug" in sys.argv or
            os.getenv("DEBUG", "").lower() == "true"
        )


def main():
    """主入口函数"""
    # 检查是否为开发模式
    dev_mode = "--dev" in sys.argv or os.getenv("DEV_MODE", "").lower() == "true"
    
    if dev_mode:
        print("🔧 开发模式启动")
        print("📝 请确保前端开发服务器已运行: yarn dev")
    
    app = aestivalApp(dev_mode=dev_mode)
    app.start()


if __name__ == "__main__":
    main()
