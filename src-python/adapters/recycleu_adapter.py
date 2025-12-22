"""
recycleu 适配器
回收站自动清理工具 - 定时清空 Windows 回收站

功能：
- 定时自动清空回收站
- 支持设置清理间隔
- 支持立即清空
- 支持启动/暂停/停止控制
"""

import os
import sys
import time
import ctypes
import asyncio
from typing import Callable, Dict, Optional

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


# Windows API 常量
SHERB_NOCONFIRMATION = 0x00000001
SHERB_NOPROGRESSUI = 0x00000002
SHERB_NOSOUND = 0x00000004


class RecycleuInput(BaseModel):
    """recycleu 输入参数"""
    action: str = Field(default="status", description="操作类型: status, start, stop, pause, resume, clean_now")
    interval: int = Field(default=10, description="清理间隔（秒）")


class RecycleuOutput(AdapterOutput):
    """recycleu 输出结果"""
    timer_status: str = Field(default="idle", description="定时器状态: idle, running, paused, completed")
    clean_count: int = Field(default=0, description="清理次数")
    last_clean_time: Optional[str] = Field(default=None, description="上次清理时间")


class RecycleuAdapter(BaseAdapter):
    """
    recycleu 适配器
    
    功能：回收站自动清理
    """
    
    name = "recycleu"
    display_name = "回收站清理"
    description = "定时自动清空 Windows 回收站"
    category = "system"
    icon = "🗑️"
    required_packages = []  # 无外部依赖
    input_schema = RecycleuInput
    output_schema = RecycleuOutput
    
    # 内部状态
    _last_bin_empty = False
    _clean_count = 0
    
    def _import_module(self) -> Dict:
        """无需导入外部模块"""
        return {}
    
    def _empty_recycle_bin(self, on_log: Optional[Callable[[str], None]] = None) -> bool:
        """清空回收站"""
        if sys.platform != 'win32':
            if on_log:
                on_log("❌ 此功能仅支持 Windows 系统")
            return False
        
        try:
            shell32 = ctypes.windll.shell32
            flags = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
            result = shell32.SHEmptyRecycleBinW(None, None, flags)
            
            if result == 0:
                self._last_bin_empty = False
                self._clean_count += 1
                if on_log:
                    on_log("🗑️ 回收站已清空")
                return True
            elif result == -2147418113:  # 回收站已空
                if not self._last_bin_empty:
                    if on_log:
                        on_log("📭 回收站已经是空的")
                    self._last_bin_empty = True
                return True
            else:
                self._last_bin_empty = False
                if on_log:
                    on_log(f"❌ 清空回收站失败，错误码: {result}")
                return False
        except Exception as e:
            self._last_bin_empty = False
            if on_log:
                on_log(f"❌ 清空回收站时出错: {e}")
            return False
    
    async def execute(
        self,
        input_data: RecycleuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> RecycleuOutput:
        """执行回收站清理操作"""
        action = input_data.action
        
        if action == "status":
            return RecycleuOutput(
                success=True,
                message="状态获取成功",
                timer_status="idle",
                clean_count=self._clean_count
            )
        
        elif action == "clean_now":
            # 立即清空
            success = self._empty_recycle_bin(on_log)
            from datetime import datetime
            return RecycleuOutput(
                success=success,
                message="回收站已清空" if success else "清空失败",
                timer_status="idle",
                clean_count=self._clean_count,
                last_clean_time=datetime.now().strftime("%H:%M:%S") if success else None
            )
        
        elif action == "start":
            # 启动定时清理
            return await self._run_auto_clean(input_data, on_progress, on_log)
        
        else:
            return RecycleuOutput(
                success=False,
                message=f"未知操作: {action}"
            )
    
    async def _run_auto_clean(
        self,
        input_data: RecycleuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> RecycleuOutput:
        """运行自动清理循环"""
        interval = input_data.interval
        
        if interval < 5:
            return RecycleuOutput(
                success=False,
                message="清理间隔不能小于5秒"
            )
        
        if on_log:
            on_log(f"🚀 启动自动清理，间隔 {interval} 秒")
        
        self._clean_count = 0
        max_cycles = 360  # 最多运行1小时 (360 * 10秒)
        cycle = 0
        
        from datetime import datetime
        last_clean_time = None
        
        while cycle < max_cycles:
            # 执行清理
            success = self._empty_recycle_bin(on_log)
            if success:
                last_clean_time = datetime.now().strftime("%H:%M:%S")
            
            # 更新进度
            if on_progress:
                on_progress(
                    min(99, int(cycle / max_cycles * 100)),
                    f"已清理 {self._clean_count} 次，下次清理 {interval}s 后"
                )
            
            # 等待间隔
            for i in range(interval):
                await asyncio.sleep(1)
                if on_progress:
                    remaining = interval - i - 1
                    on_progress(
                        min(99, int(cycle / max_cycles * 100)),
                        f"已清理 {self._clean_count} 次，{remaining}s 后清理"
                    )
            
            cycle += 1
        
        if on_progress:
            on_progress(100, "自动清理完成")
        
        return RecycleuOutput(
            success=True,
            message=f"自动清理完成，共清理 {self._clean_count} 次",
            timer_status="completed",
            clean_count=self._clean_count,
            last_clean_time=last_clean_time
        )
