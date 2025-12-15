"""
系统功能桥接 API
提供前端调用系统功能的接口（文件对话框、剪贴板等）

注意：
- Tauri 模式下，这些功能通过 Tauri API 直接调用
- 此模块主要用于 pywebview 独立模式或后端 API 端点
"""

import os
from typing import Optional

import webview


class BridgeAPI:
    """
    pywebview JS-Python 桥接接口
    
    前端可通过 window.pywebview.api.xxx() 调用这些方法
    """
    
    def __init__(self):
        """初始化桥接 API"""
        self._window: Optional[webview.Window] = None
    
    def set_window(self, window: webview.Window):
        """
        设置窗口引用
        
        Args:
            window: pywebview 窗口实例
        """
        self._window = window
    
    def open_folder_dialog(self, title: str = "选择文件夹") -> Optional[str]:
        """
        打开文件夹选择对话框
        
        Args:
            title: 对话框标题
            
        Returns:
            选中的文件夹路径，如果取消则返回 None
        """
        if not self._window:
            return None
        
        try:
            result = self._window.create_file_dialog(
                webview.FOLDER_DIALOG,
                directory="",
                allow_multiple=False
            )
            
            if result and len(result) > 0:
                return result[0]
            return None
            
        except Exception as e:
            print(f"[BridgeAPI] 打开文件夹对话框失败: {e}")
            return None
    
    def open_file_dialog(
        self, 
        title: str = "选择文件",
        file_types: tuple = ("All files (*.*)",),
        allow_multiple: bool = False
    ) -> Optional[list]:
        """
        打开文件选择对话框
        
        Args:
            title: 对话框标题
            file_types: 文件类型过滤器
            allow_multiple: 是否允许多选
            
        Returns:
            选中的文件路径列表，如果取消则返回 None
        """
        if not self._window:
            return None
        
        try:
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                directory="",
                allow_multiple=allow_multiple,
                file_types=file_types
            )
            
            if result:
                return list(result)
            return None
            
        except Exception as e:
            print(f"[BridgeAPI] 打开文件对话框失败: {e}")
            return None
    
    def read_clipboard(self) -> str:
        """
        读取系统剪贴板内容
        
        Returns:
            剪贴板文本内容，如果失败则返回空字符串
        """
        try:
            import pyperclip
            content = pyperclip.paste()
            return content if content else ""
        except ImportError:
            print("[BridgeAPI] pyperclip 未安装，尝试使用备用方案")
            return self._read_clipboard_fallback()
        except Exception as e:
            print(f"[BridgeAPI] 读取剪贴板失败: {e}")
            return ""
    
    def write_clipboard(self, text: str) -> bool:
        """
        写入内容到系统剪贴板
        
        Args:
            text: 要写入的文本内容
            
        Returns:
            是否成功写入
        """
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except ImportError:
            print("[BridgeAPI] pyperclip 未安装，尝试使用备用方案")
            return self._write_clipboard_fallback(text)
        except Exception as e:
            print(f"[BridgeAPI] 写入剪贴板失败: {e}")
            return False
    
    def validate_path(self, path: str) -> dict:
        """
        验证路径是否有效
        
        Args:
            path: 要验证的路径
            
        Returns:
            包含验证结果的字典:
            - valid: 路径是否有效
            - exists: 路径是否存在
            - is_dir: 是否为目录
            - is_file: 是否为文件
            - message: 验证消息
        """
        if not path or not path.strip():
            return {
                "valid": False,
                "exists": False,
                "is_dir": False,
                "is_file": False,
                "message": "路径为空"
            }
        
        path = path.strip()
        exists = os.path.exists(path)
        is_dir = os.path.isdir(path) if exists else False
        is_file = os.path.isfile(path) if exists else False
        
        if not exists:
            message = "路径不存在"
        elif is_dir:
            message = "有效的文件夹路径"
        elif is_file:
            message = "有效的文件路径"
        else:
            message = "路径存在但类型未知"
        
        return {
            "valid": exists,
            "exists": exists,
            "is_dir": is_dir,
            "is_file": is_file,
            "message": message
        }
    
    def get_clipboard_path(self) -> dict:
        """
        从剪贴板读取并验证路径
        
        Returns:
            包含路径和验证结果的字典:
            - path: 剪贴板内容（如果是有效路径）
            - valid: 是否为有效路径
            - message: 提示消息
        """
        content = self.read_clipboard()
        
        if not content:
            return {
                "path": None,
                "valid": False,
                "message": "剪贴板为空"
            }
        
        # 清理路径（去除引号和空白）
        cleaned_path = content.strip().strip('"').strip("'")
        
        # 验证路径
        validation = self.validate_path(cleaned_path)
        
        if validation["exists"]:
            return {
                "path": cleaned_path,
                "valid": True,
                "message": validation["message"]
            }
        else:
            return {
                "path": None,
                "valid": False,
                "message": "剪贴板内容不是有效路径"
            }
    
    def _read_clipboard_fallback(self) -> str:
        """
        剪贴板读取备用方案（Windows）
        """
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""
    
    def _write_clipboard_fallback(self, text: str) -> bool:
        """
        剪贴板写入备用方案（Windows）
        """
        try:
            import subprocess
            process = subprocess.Popen(
                ["powershell", "-command", "Set-Clipboard"],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(input=text, timeout=5)
            return process.returncode == 0
        except Exception:
            return False

    # ==================== 窗口控制 API ====================

    def minimize_window(self):
        """最小化窗口"""
        if self._window:
            self._window.minimize()

    def toggle_maximize(self):
        """切换最大化/还原窗口"""
        if self._window:
            # pywebview 没有 toggle_maximize，用 maximize/restore 模拟
            try:
                if getattr(self, '_is_maximized', False):
                    self._window.restore()
                    self._is_maximized = False
                else:
                    self._window.maximize()
                    self._is_maximized = True
            except Exception as e:
                print(f"[BridgeAPI] 切换最大化失败: {e}")

    def close_window(self):
        """关闭窗口"""
        if self._window:
            self._window.destroy()

    def start_drag(self):
        """开始拖拽窗口（Windows 原生拖拽）"""
        if self._window:
            try:
                # pywebview 4.x 支持 start_drag
                if hasattr(self._window, 'start_drag'):
                    self._window.start_drag()
                else:
                    # 备用方案：使用 Windows API
                    import ctypes
                    hwnd = self._window.hwnd if hasattr(self._window, 'hwnd') else None
                    if hwnd:
                        # 发送 WM_NCLBUTTONDOWN 消息模拟标题栏拖拽
                        WM_NCLBUTTONDOWN = 0x00A1
                        HTCAPTION = 2
                        ctypes.windll.user32.ReleaseCapture()
                        ctypes.windll.user32.SendMessageW(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0)
            except Exception as e:
                print(f"[BridgeAPI] 拖拽窗口失败: {e}")

    def move_window(self, x: int, y: int):
        """移动窗口到指定位置"""
        if self._window:
            try:
                self._window.move(x, y)
            except Exception as e:
                print(f"[BridgeAPI] 移动窗口失败: {e}")
