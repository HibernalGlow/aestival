"""
FastAPI Server for AestivalFlow
支持三种运行模式:
- pywebview 模式: 作为桌面应用运行（推荐）
- standalone 模式: 独立运行带热重载（开发用）
- sidecar 模式: 作为 Tauri sidecar 运行（兼容旧版）
"""

import os
import signal
import sys
import asyncio
import threading
import socket
import subprocess
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import Config, Server

from api.endpoints import router as api_router
from api.flows import router as flows_router
from api.tasks import router as tasks_router
from api.tools import router as tools_router
from api.nodes import router as nodes_router
from api.execution import router as execution_router
from api.websocket import router as websocket_router
from api.terminal_ws import router as terminal_router

PORT_API = 8009
server_instance = None


def detect_running_mode() -> str:
    """
    检测当前运行模式
    
    Returns:
        运行模式: 'pywebview', 'standalone', 或 'sidecar'
    """
    # pywebview 模式检测
    if (
        "--pywebview" in sys.argv or
        os.getenv("PYWEBVIEW_MODE", "").lower() == "true"
    ):
        return "pywebview"
    
    # standalone 模式检测
    if (
        "--standalone" in sys.argv or 
        "--reload" in sys.argv or
        os.getenv("STANDALONE_MODE", "").lower() == "true" or
        os.getenv("UVICORN_RELOAD", "").lower() == "true"
    ):
        return "standalone"
    
    # 默认 sidecar 模式
    return "sidecar"


def is_standalone_mode():
    """Detect if running in standalone mode vs sidecar mode (兼容旧版)"""
    return detect_running_mode() == "standalone"


def is_pywebview_mode():
    """检测是否为 pywebview 模式"""
    return detect_running_mode() == "pywebview"


RUNNING_MODE = detect_running_mode()
STANDALONE_MODE = RUNNING_MODE == "standalone"
mode_label = RUNNING_MODE

# Create FastAPI app
app = FastAPI(title="Test App API", version="1.0.0")

# CORS 配置
# 根据运行模式配置允许的来源
cors_origins = [
    "http://localhost:5173",   # SvelteKit dev server
    "http://localhost:5174",   # Vite dev server (备用端口)
    "http://localhost:5175",   # Vite dev server (备用端口)
    "http://localhost:1420",   # Tauri dev server
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:1420",
    "http://127.0.0.1:8009",   # pywebview 本地服务器
    "http://localhost:8009",
    "tauri://localhost",
]

# pywebview 模式下允许所有本地来源
if is_pywebview_mode():
    # pywebview 使用本地 WebView，需要更宽松的 CORS
    cors_origins.extend([
        f"http://127.0.0.1:{PORT_API + i}" for i in range(10)
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/v1")
app.include_router(flows_router, prefix="/v1")
app.include_router(tasks_router, prefix="/v1")
app.include_router(tools_router, prefix="/v1")
app.include_router(nodes_router, prefix="/v1")
app.include_router(execution_router, prefix="/v1")
app.include_router(websocket_router, prefix="/v1")
app.include_router(terminal_router)  # 终端 WebSocket，无前缀

@app.get("/")
async def root():
    return {
        "message": "Test App API", 
        "status": "running",
        "mode": mode_label,
        "port": PORT_API
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "mode": mode_label}

def is_port_available(port):
    """Check if a port is available"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False

def find_available_port():
    """Find an available port starting from PORT_API"""
    port = PORT_API
    while port < PORT_API + 10:  # Try 10 ports
        if is_port_available(port):
            print(f"[{mode_label}] Using available port {port}", flush=True)
            return port
        port += 1
    
    # If no port is available, use the default
    print(f"[{mode_label}] No available ports found, using default {PORT_API}", flush=True)
    return PORT_API

def start_api_server(**kwargs):
    """Start the FastAPI server"""
    global server_instance
    port = kwargs.get("port", find_available_port())
    
    try:
        if server_instance is None:
            print(f"[{mode_label}] Starting API server on port {port}...", flush=True)
            print(f"[{mode_label}] Server will be available at http://127.0.0.1:{port}", flush=True)
            
            config = Config(app, host="127.0.0.1", port=port, log_level="info")
            server_instance = Server(config)
            asyncio.run(server_instance.serve())
        else:
            print(f"[{mode_label}] Server instance already running.", flush=True)
    except Exception as e:
        print(f"[{mode_label}] Error starting API server on port {port}: {e}", flush=True)

def stdin_loop():
    """Handle stdin commands in sidecar mode"""
    print(f"[{mode_label}] Waiting for commands...", flush=True)
    while True:
        try:
            user_input = sys.stdin.readline().strip()
            if user_input == "sidecar shutdown":
                print(f"[{mode_label}] Received 'sidecar shutdown' command.", flush=True)
                os.kill(os.getpid(), signal.SIGINT)
            else:
                print(f"[{mode_label}] Invalid command [{user_input}]. Try again.", flush=True)
        except EOFError:
            break
        except Exception as e:
            print(f"[{mode_label}] Error in stdin loop: {e}", flush=True)
            break

def start_input_thread():
    """Start stdin monitoring thread (only in sidecar mode)"""
    if not STANDALONE_MODE:
        try:
            input_thread = threading.Thread(target=stdin_loop, daemon=True)
            input_thread.start()
        except Exception as e:
            print(f"[{mode_label}] Failed to start input handler: {e}", flush=True)

def run_standalone():
    """Run in standalone mode with uvicorn auto-reload"""
    port = find_available_port()
    
    print(f"🚀 Starting standalone development mode")
    print(f"🔗 API server starting at http://127.0.0.1:{port}")
    print(f"📖 API docs will be at http://127.0.0.1:{port}/docs")
    print(f"🔄 Auto-reload enabled")
    print(f"💡 Press Ctrl+C to stop\n")
    
    try:
        uvicorn.run(
            "main:app", 
            host="127.0.0.1", 
            port=port, 
            reload=True,
            reload_dirs=["./"],
            reload_excludes=["*.pyc", "__pycache__", "*.log"],
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting API server: {e}")
        sys.exit(1)

def run_sidecar():
    """Run in sidecar mode with stdin handling"""
    start_input_thread()
    start_api_server()


def run_pywebview():
    """Run in pywebview mode as desktop application"""
    print(f"🚀 启动 pywebview 桌面应用模式")
    print(f"💡 使用 launcher.py 启动完整的桌面应用")
    
    # 如果直接运行 main.py --pywebview，提示使用 launcher.py
    try:
        from launcher import main as launcher_main
        launcher_main()
    except ImportError:
        print("❌ 请使用 launcher.py 启动 pywebview 模式")
        print("   运行: python launcher.py")
        sys.exit(1)


if __name__ == "__main__":
    if RUNNING_MODE == "pywebview":
        run_pywebview()
    elif RUNNING_MODE == "standalone":
        run_standalone()
    else:
        run_sidecar()