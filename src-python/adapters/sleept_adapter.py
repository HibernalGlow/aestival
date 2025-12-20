"""
sleept 适配器
系统定时器工具 - 支持倒计时、指定时间、网速监控、CPU监控触发电源操作

功能：
- 倒计时模式：设定时间后执行电源操作
- 指定时间模式：在指定时间点执行电源操作
- 网速监控模式：网速低于阈值持续一段时间后执行
- CPU监控模式：CPU使用率低于阈值持续一段时间后执行
- 支持休眠、关机、重启三种电源操作
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class SleeptInput(BaseModel):
    """sleept 输入参数"""
    action: str = Field(default="status", description="操作类型: status, start, cancel, get_stats")
    
    # 计时模式: countdown, specific_time, netspeed, cpu
    timer_mode: str = Field(default="countdown", description="计时模式")
    
    # 电源操作: sleep, shutdown, restart
    power_mode: str = Field(default="sleep", description="电源操作类型")
    
    # 倒计时模式参数
    hours: int = Field(default=0, description="小时数")
    minutes: int = Field(default=30, description="分钟数")
    seconds: int = Field(default=0, description="秒数")
    
    # 指定时间模式参数
    target_datetime: Optional[str] = Field(default=None, description="目标时间 (YYYY-MM-DD HH:MM:SS)")
    
    # 网速监控参数
    upload_threshold: float = Field(default=242, description="上传阈值 (KB/s)")
    download_threshold: float = Field(default=242, description="下载阈值 (KB/s)")
    net_duration: float = Field(default=2, description="持续时间 (分钟)")
    net_trigger_mode: str = Field(default="both", description="触发模式: both, any")
    
    # CPU监控参数
    cpu_threshold: float = Field(default=10, description="CPU阈值 (%)")
    cpu_duration: float = Field(default=2, description="持续时间 (分钟)")
    
    # 通用参数
    dryrun: bool = Field(default=True, description="演练模式，不实际执行电源操作")


class SleeptOutput(AdapterOutput):
    """sleept 输出结果"""
    timer_status: str = Field(default="idle", description="定时器状态: idle, running, completed, cancelled")
    remaining_seconds: int = Field(default=0, description="剩余秒数")
    current_upload: float = Field(default=0, description="当前上传速度 (KB/s)")
    current_download: float = Field(default=0, description="当前下载速度 (KB/s)")
    current_cpu: float = Field(default=0, description="当前CPU使用率 (%)")
    target_time: Optional[str] = Field(default=None, description="目标时间")


# 全局定时器状态（用于跨请求保持状态）
_timer_state = {
    "status": "idle",  # idle, running, completed, cancelled
    "mode": "countdown",
    "power_mode": "sleep",
    "end_time": None,
    "total_seconds": 0,
    "dryrun": True,
    "cancel_flag": False,
    "thread": None,
    # 网速监控
    "net_low_start": None,
    "net_monitoring": False,
    # CPU监控
    "cpu_low_start": None,
    "cpu_monitoring": False,
}


class SleeptAdapter(BaseAdapter):
    """
    sleept 适配器
    
    功能：系统定时器，支持多种触发模式
    """
    
    name = "sleept"
    display_name = "系统定时器"
    description = "定时休眠/关机/重启，支持倒计时、指定时间、网速监控、CPU监控"
    category = "system"
    icon = "⏰"
    required_packages = ["psutil"]
    input_schema = SleeptInput
    output_schema = SleeptOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入模块"""
        import psutil
        return {"psutil": psutil}
    
    async def execute(
        self,
        input_data: SleeptInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> SleeptOutput:
        """执行定时器操作"""
        action = input_data.action
        
        if action == "status":
            return await self._get_status(on_log)
        elif action == "start":
            return await self._start_timer(input_data, on_progress, on_log)
        elif action == "cancel":
            return await self._cancel_timer(on_log)
        elif action == "get_stats":
            return await self._get_stats(on_log)
        else:
            return SleeptOutput(
                success=False,
                message=f"未知操作: {action}"
            )
    
    async def _get_status(self, on_log: Optional[Callable[[str], None]] = None) -> SleeptOutput:
        """获取当前状态"""
        global _timer_state
        
        remaining = 0
        if _timer_state["status"] == "running" and _timer_state["end_time"]:
            remaining = max(0, int(_timer_state["end_time"] - time.time()))
        
        # 获取当前网速和CPU
        current_upload = 0
        current_download = 0
        current_cpu = 0
        
        try:
            psutil = self.get_module()["psutil"]
            current_cpu = psutil.cpu_percent(interval=0.1)
        except:
            pass
        
        return SleeptOutput(
            success=True,
            message=f"状态: {_timer_state['status']}",
            timer_status=_timer_state["status"],
            remaining_seconds=remaining,
            current_cpu=current_cpu,
            target_time=datetime.fromtimestamp(_timer_state["end_time"]).strftime("%Y-%m-%d %H:%M:%S") if _timer_state["end_time"] else None
        )
    
    async def _start_timer(
        self,
        input_data: SleeptInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> SleeptOutput:
        """启动定时器"""
        global _timer_state
        
        if _timer_state["status"] == "running":
            return SleeptOutput(
                success=False,
                message="定时器已在运行中",
                timer_status="running"
            )
        
        mode = input_data.timer_mode
        power_mode = input_data.power_mode
        dryrun = input_data.dryrun
        
        _timer_state["mode"] = mode
        _timer_state["power_mode"] = power_mode
        _timer_state["dryrun"] = dryrun
        _timer_state["cancel_flag"] = False
        
        if on_log:
            on_log(f"⏰ 启动定时器 - 模式: {mode}, 电源操作: {power_mode}, dryrun: {dryrun}")
        
        if mode == "countdown":
            total_seconds = input_data.hours * 3600 + input_data.minutes * 60 + input_data.seconds
            if total_seconds <= 0:
                return SleeptOutput(success=False, message="倒计时时间必须大于0")
            
            _timer_state["total_seconds"] = total_seconds
            _timer_state["end_time"] = time.time() + total_seconds
            _timer_state["status"] = "running"
            
            if on_log:
                on_log(f"⏱️ 倒计时 {input_data.hours}小时{input_data.minutes}分{input_data.seconds}秒")
            
            # 启动倒计时线程
            thread = threading.Thread(
                target=self._countdown_thread,
                args=(total_seconds, on_progress, on_log),
                daemon=True
            )
            _timer_state["thread"] = thread
            thread.start()
            
            return SleeptOutput(
                success=True,
                message=f"倒计时已启动: {total_seconds}秒",
                timer_status="running",
                remaining_seconds=total_seconds,
                target_time=datetime.fromtimestamp(_timer_state["end_time"]).strftime("%Y-%m-%d %H:%M:%S")
            )
        
        elif mode == "specific_time":
            if not input_data.target_datetime:
                return SleeptOutput(success=False, message="请指定目标时间")
            
            try:
                target = datetime.strptime(input_data.target_datetime, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return SleeptOutput(success=False, message="时间格式错误，请使用 YYYY-MM-DD HH:MM:SS")
            
            now = datetime.now()
            if target <= now:
                return SleeptOutput(success=False, message="目标时间必须在当前时间之后")
            
            total_seconds = int((target - now).total_seconds())
            _timer_state["total_seconds"] = total_seconds
            _timer_state["end_time"] = target.timestamp()
            _timer_state["status"] = "running"
            
            if on_log:
                on_log(f"📅 定时到 {input_data.target_datetime}")
            
            thread = threading.Thread(
                target=self._countdown_thread,
                args=(total_seconds, on_progress, on_log),
                daemon=True
            )
            _timer_state["thread"] = thread
            thread.start()
            
            return SleeptOutput(
                success=True,
                message=f"定时已设置: {input_data.target_datetime}",
                timer_status="running",
                remaining_seconds=total_seconds,
                target_time=input_data.target_datetime
            )
        
        elif mode == "netspeed":
            _timer_state["status"] = "running"
            _timer_state["net_monitoring"] = True
            _timer_state["net_low_start"] = None
            
            if on_log:
                on_log(f"📡 网速监控已启动 - 上传阈值: {input_data.upload_threshold}KB/s, 下载阈值: {input_data.download_threshold}KB/s")
            
            thread = threading.Thread(
                target=self._netspeed_monitor_thread,
                args=(input_data, on_progress, on_log),
                daemon=True
            )
            _timer_state["thread"] = thread
            thread.start()
            
            return SleeptOutput(
                success=True,
                message="网速监控已启动",
                timer_status="running"
            )
        
        elif mode == "cpu":
            _timer_state["status"] = "running"
            _timer_state["cpu_monitoring"] = True
            _timer_state["cpu_low_start"] = None
            
            if on_log:
                on_log(f"💻 CPU监控已启动 - 阈值: {input_data.cpu_threshold}%, 持续: {input_data.cpu_duration}分钟")
            
            thread = threading.Thread(
                target=self._cpu_monitor_thread,
                args=(input_data, on_progress, on_log),
                daemon=True
            )
            _timer_state["thread"] = thread
            thread.start()
            
            return SleeptOutput(
                success=True,
                message="CPU监控已启动",
                timer_status="running"
            )
        
        return SleeptOutput(success=False, message=f"未知模式: {mode}")
    
    def _countdown_thread(
        self,
        total_seconds: int,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ):
        """倒计时线程"""
        global _timer_state
        
        end_time = time.time() + total_seconds
        
        while time.time() < end_time and not _timer_state["cancel_flag"]:
            remaining = int(end_time - time.time())
            if remaining <= 0:
                break
            
            hours, remainder = divmod(remaining, 3600)
            minutes, seconds = divmod(remainder, 60)
            progress = int((1 - remaining / total_seconds) * 100)
            
            if on_progress:
                on_progress(progress, f"剩余 {hours:02d}:{minutes:02d}:{seconds:02d}")
            
            time.sleep(1)
        
        if _timer_state["cancel_flag"]:
            _timer_state["status"] = "cancelled"
            if on_log:
                on_log("❌ 定时已取消")
        else:
            _timer_state["status"] = "completed"
            if on_progress:
                on_progress(100, "时间到！")
            self._execute_power_action(on_log)
    
    def _netspeed_monitor_thread(
        self,
        input_data: SleeptInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ):
        """网速监控线程"""
        global _timer_state
        
        psutil = self.get_module()["psutil"]
        last = psutil.net_io_counters()
        last_time = time.time()
        duration_seconds = input_data.net_duration * 60
        
        while _timer_state["net_monitoring"] and not _timer_state["cancel_flag"]:
            time.sleep(1)
            
            now = psutil.net_io_counters()
            now_time = time.time()
            interval = now_time - last_time
            
            up_speed = (now.bytes_sent - last.bytes_sent) / interval / 1024
            down_speed = (now.bytes_recv - last.bytes_recv) / interval / 1024
            
            low_up = up_speed < input_data.upload_threshold
            low_down = down_speed < input_data.download_threshold
            
            trigger = False
            if input_data.net_trigger_mode == "both":
                trigger = low_up and low_down
            else:
                trigger = low_up or low_down
            
            if trigger:
                if _timer_state["net_low_start"] is None:
                    _timer_state["net_low_start"] = now_time
                    if on_log:
                        on_log(f"📉 网速低于阈值，开始计时...")
                
                elapsed = now_time - _timer_state["net_low_start"]
                progress = min(100, int(elapsed / duration_seconds * 100))
                
                if on_progress:
                    on_progress(progress, f"低速持续 {int(elapsed)}s / {int(duration_seconds)}s")
                
                if elapsed >= duration_seconds:
                    if on_log:
                        on_log(f"⏰ 网速低于阈值已持续 {input_data.net_duration} 分钟")
                    _timer_state["status"] = "completed"
                    _timer_state["net_monitoring"] = False
                    self._execute_power_action(on_log)
                    break
            else:
                if _timer_state["net_low_start"] is not None:
                    if on_log:
                        on_log(f"📈 网速恢复 (↑{up_speed:.1f} ↓{down_speed:.1f} KB/s)")
                    _timer_state["net_low_start"] = None
                
                if on_progress:
                    on_progress(0, f"↑{up_speed:.1f} ↓{down_speed:.1f} KB/s")
            
            last = now
            last_time = now_time
        
        if _timer_state["cancel_flag"]:
            _timer_state["status"] = "cancelled"
            _timer_state["net_monitoring"] = False
    
    def _cpu_monitor_thread(
        self,
        input_data: SleeptInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ):
        """CPU监控线程"""
        global _timer_state
        
        psutil = self.get_module()["psutil"]
        duration_seconds = input_data.cpu_duration * 60
        
        while _timer_state["cpu_monitoring"] and not _timer_state["cancel_flag"]:
            time.sleep(1)
            
            cpu_percent = psutil.cpu_percent(interval=None)
            now_time = time.time()
            
            if cpu_percent < input_data.cpu_threshold:
                if _timer_state["cpu_low_start"] is None:
                    _timer_state["cpu_low_start"] = now_time
                    if on_log:
                        on_log(f"📉 CPU使用率 {cpu_percent:.1f}% 低于阈值，开始计时...")
                
                elapsed = now_time - _timer_state["cpu_low_start"]
                progress = min(100, int(elapsed / duration_seconds * 100))
                
                if on_progress:
                    on_progress(progress, f"CPU {cpu_percent:.1f}% - 低使用率持续 {int(elapsed)}s")
                
                if elapsed >= duration_seconds:
                    if on_log:
                        on_log(f"⏰ CPU低使用率已持续 {input_data.cpu_duration} 分钟")
                    _timer_state["status"] = "completed"
                    _timer_state["cpu_monitoring"] = False
                    self._execute_power_action(on_log)
                    break
            else:
                if _timer_state["cpu_low_start"] is not None:
                    if on_log:
                        on_log(f"📈 CPU使用率恢复 ({cpu_percent:.1f}%)")
                    _timer_state["cpu_low_start"] = None
                
                if on_progress:
                    on_progress(0, f"CPU {cpu_percent:.1f}%")
        
        if _timer_state["cancel_flag"]:
            _timer_state["status"] = "cancelled"
            _timer_state["cpu_monitoring"] = False
    
    def _execute_power_action(self, on_log: Optional[Callable[[str], None]] = None):
        """执行电源操作"""
        global _timer_state
        
        power_mode = _timer_state["power_mode"]
        dryrun = _timer_state["dryrun"]
        
        action_text = {"sleep": "休眠", "shutdown": "关机", "restart": "重启"}.get(power_mode, power_mode)
        
        if dryrun:
            if on_log:
                on_log(f"🔔 [dryrun] 模拟执行: {action_text}")
            return
        
        if on_log:
            on_log(f"⚡ 执行电源操作: {action_text}")
        
        if sys.platform == 'win32':
            if power_mode == "sleep":
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif power_mode == "shutdown":
                os.system("shutdown /s /t 1")
            elif power_mode == "restart":
                os.system("shutdown /r /t 1")
        elif sys.platform == 'darwin':
            if power_mode == "sleep":
                os.system("pmset sleepnow")
            elif power_mode == "shutdown":
                os.system("osascript -e 'tell app \"System Events\" to shut down'")
            elif power_mode == "restart":
                os.system("osascript -e 'tell app \"System Events\" to restart'")
        else:
            if power_mode == "sleep":
                os.system("systemctl suspend")
            elif power_mode == "shutdown":
                os.system("systemctl poweroff")
            elif power_mode == "restart":
                os.system("systemctl reboot")
    
    async def _cancel_timer(self, on_log: Optional[Callable[[str], None]] = None) -> SleeptOutput:
        """取消定时器"""
        global _timer_state
        
        if _timer_state["status"] != "running":
            return SleeptOutput(
                success=False,
                message="没有正在运行的定时器",
                timer_status=_timer_state["status"]
            )
        
        _timer_state["cancel_flag"] = True
        _timer_state["net_monitoring"] = False
        _timer_state["cpu_monitoring"] = False
        
        if on_log:
            on_log("❌ 正在取消定时器...")
        
        # 等待线程结束
        if _timer_state["thread"] and _timer_state["thread"].is_alive():
            _timer_state["thread"].join(timeout=2)
        
        _timer_state["status"] = "cancelled"
        _timer_state["end_time"] = None
        
        return SleeptOutput(
            success=True,
            message="定时器已取消",
            timer_status="cancelled"
        )
    
    async def _get_stats(self, on_log: Optional[Callable[[str], None]] = None) -> SleeptOutput:
        """获取系统状态统计"""
        psutil = self.get_module()["psutil"]
        
        # 获取网速
        net1 = psutil.net_io_counters()
        time.sleep(0.5)
        net2 = psutil.net_io_counters()
        
        up_speed = (net2.bytes_sent - net1.bytes_sent) / 0.5 / 1024
        down_speed = (net2.bytes_recv - net1.bytes_recv) / 0.5 / 1024
        cpu = psutil.cpu_percent(interval=0.1)
        
        return SleeptOutput(
            success=True,
            message=f"CPU: {cpu:.1f}%, 上传: {up_speed:.1f}KB/s, 下载: {down_speed:.1f}KB/s",
            timer_status=_timer_state["status"],
            current_upload=up_speed,
            current_download=down_speed,
            current_cpu=cpu
        )
