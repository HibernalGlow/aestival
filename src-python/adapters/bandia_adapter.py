"""
bandia 适配器
批量解压工具 - 使用 Bandizip (bz.exe) 进行批量解压

功能：
- 从路径列表批量解压压缩包
- 支持解压后删除源文件（可选移入回收站）
- 支持 .zip .7z .rar .tar .gz .bz2 .xz 格式
- 支持 WebSocket 实时进度推送（带节流，减少性能影响）
"""

import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


# ============ 节流进度回调 ============

class ThrottledProgress:
    """
    节流进度回调器
    减少 WebSocket 消息频率，降低对解压速度的影响
    """
    
    def __init__(
        self, 
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
        min_interval: float = 0.15  # 最小间隔 150ms
    ):
        self.on_progress = on_progress
        self.on_log = on_log
        self.min_interval = min_interval
        self._last_progress_time = 0.0
        self._last_progress_value = -1
        self._pending_progress: Optional[tuple] = None  # (progress, message, current_file)
    
    def progress(self, progress: int, message: str, current_file: str = ""):
        """
        发送进度（带节流）
        - 进度变化 >= 5% 或距上次 >= min_interval 才发送
        - 100% 和 0% 总是立即发送
        """
        if not self.on_progress:
            return
        
        now = time.time()
        should_send = (
            progress == 0 or 
            progress == 100 or
            progress - self._last_progress_value >= 5 or
            now - self._last_progress_time >= self.min_interval
        )
        
        # 构建带文件名的消息
        full_message = f"{message}|{current_file}" if current_file else message
        
        if should_send:
            self.on_progress(progress, full_message)
            self._last_progress_time = now
            self._last_progress_value = progress
            self._pending_progress = None
        else:
            # 保存待发送的进度（确保最终状态能发送）
            self._pending_progress = (progress, full_message, current_file)
    
    def flush(self):
        """刷新待发送的进度"""
        if self._pending_progress and self.on_progress:
            progress, message, _ = self._pending_progress
            self.on_progress(progress, message)
            self._pending_progress = None
    
    def log(self, message: str):
        """发送日志（不节流，但日志本身应该较少）"""
        if self.on_log:
            self.on_log(message)


# Bandizip 可执行文件名
BZ_EXECUTABLE_NAMES = ["bz.exe", "bandizip", "Bandizip", "BZ.exe"]

# 支持的压缩格式
ARCHIVE_EXTENSIONS = {'.zip', '.7z', '.rar', '.tar', '.gz', '.bz2', '.xz'}


def find_bz_executable() -> Optional[Path]:
    """尝试自动定位 bz.exe
    
    查找顺序：
    1. 环境变量 BANDIZIP_PATH
    2. PATH 中的可执行文件
    3. 常见安装目录
    """
    # 1. 环境变量
    env = os.getenv("BANDIZIP_PATH")
    if env:
        p = Path(env)
        if p.is_file():
            return p
        for name in BZ_EXECUTABLE_NAMES:
            cand = p / name
            if cand.is_file():
                return cand

    # 2. PATH
    for name in BZ_EXECUTABLE_NAMES:
        path = shutil.which(name)
        if path:
            return Path(path)

    # 3. 常见安装目录
    common_dirs = [
        Path("C:/Program Files/Bandizip"),
        Path("C:/Program Files (x86)/Bandizip"),
        Path.home() / "AppData/Local/Programs/Bandizip",
    ]
    for d in common_dirs:
        for name in BZ_EXECUTABLE_NAMES:
            cand = d / name
            if cand.is_file():
                return cand
    
    return None


class BandiaInput(BaseModel):
    """bandia 输入参数（不继承 AdapterInput，因为使用 paths 而非 path）"""
    action: str = Field(default="extract", description="操作类型: extract")
    paths: List[str] = Field(default_factory=list, description="压缩包路径列表")
    delete_after: bool = Field(default=True, description="解压成功后删除源文件")
    use_trash: bool = Field(default=True, description="使用回收站而非物理删除")


class BandiaOutput(AdapterOutput):
    """bandia 输出结果"""
    extracted_count: int = Field(default=0, description="成功解压的数量")
    failed_count: int = Field(default=0, description="失败的数量")
    total_count: int = Field(default=0, description="总数量")
    results: List[Dict] = Field(default_factory=list, description="每个文件的处理结果")


class BandiaAdapter(BaseAdapter):
    """
    bandia 适配器
    
    功能：使用 Bandizip 批量解压压缩包
    """
    
    name = "bandia"
    display_name = "批量解压"
    description = "使用 Bandizip 批量解压压缩包，支持解压后删除源文件"
    category = "file"
    icon = "📦"
    required_packages = []  # 不需要额外包，使用系统安装的 Bandizip
    input_schema = BandiaInput
    output_schema = BandiaOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入模块（bandia 不需要额外模块）"""
        return {}
    
    async def execute(
        self,
        input_data: BandiaInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> BandiaOutput:
        """执行批量解压"""
        return await self._extract(input_data, on_progress, on_log)
    
    async def _extract(
        self,
        input_data: BandiaInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> BandiaOutput:
        """
        执行解压操作
        使用节流进度回调，减少 WebSocket 消息频率
        """
        # 创建节流进度回调器
        throttled = ThrottledProgress(on_progress, on_log, min_interval=0.15)
        
        # 查找 Bandizip
        bz_path = find_bz_executable()
        if not bz_path:
            return BandiaOutput(
                success=False,
                message="未找到 Bandizip (bz.exe)，请安装 Bandizip 或设置环境变量 BANDIZIP_PATH"
            )
        
        throttled.log(f"使用 Bandizip: {bz_path}")
        
        # 过滤有效的压缩包路径
        paths = self._filter_archives(input_data.paths)
        if not paths:
            return BandiaOutput(
                success=False,
                message="没有有效的压缩包路径"
            )
        
        total = len(paths)
        throttled.log(f"开始解压 {total} 个压缩包...")
        throttled.progress(0, f"准备解压 {total} 个文件...")
        
        results = []
        extracted = 0
        failed = 0
        
        for idx, archive_path in enumerate(paths):
            p = Path(archive_path)
            # 计算进度百分比 (5% - 95%)
            progress_pct = int(5 + (idx / total) * 90)
            
            # 发送进度，包含当前文件名
            throttled.progress(
                progress_pct, 
                f"解压 {idx + 1}/{total}", 
                current_file=p.name
            )
            
            if not p.exists():
                throttled.log(f"❌ 文件不存在: {p}")
                results.append({'path': str(p), 'success': False, 'error': '文件不存在'})
                failed += 1
                continue
            
            if p.is_dir():
                throttled.log(f"⚠️ 跳过目录: {p}")
                results.append({'path': str(p), 'success': False, 'error': '是目录'})
                failed += 1
                continue
            
            # 执行解压
            cmd = [str(bz_path), "x", "-target:auto", str(p)]
            start_time = time.time()
            
            try:
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                duration = time.time() - start_time
                
                if proc.returncode == 0:
                    throttled.log(f"✅ 成功 ({duration:.2f}s): {p.name}")
                    
                    # 删除源文件
                    if input_data.delete_after:
                        try:
                            if input_data.use_trash:
                                try:
                                    from send2trash import send2trash
                                    send2trash(str(p))
                                    # 删除成功不发日志，减少消息量
                                except ImportError:
                                    p.unlink()
                            else:
                                p.unlink()
                        except Exception as e:
                            throttled.log(f"⚠️ 删除失败 {p.name}: {e}")
                    
                    results.append({'path': str(p), 'success': True, 'duration': duration})
                    extracted += 1
                else:
                    error_msg = proc.stderr or proc.stdout or f"返回码 {proc.returncode}"
                    throttled.log(f"❌ 失败: {p.name} - {error_msg[:100]}")
                    results.append({'path': str(p), 'success': False, 'error': error_msg})
                    failed += 1
                    
            except Exception as e:
                throttled.log(f"❌ 执行失败 {p.name}: {e}")
                results.append({'path': str(p), 'success': False, 'error': str(e)})
                failed += 1
        
        # 刷新待发送的进度
        throttled.flush()
        throttled.progress(100, "解压完成")
        
        success = failed == 0
        message = f"解压完成: {extracted} 成功, {failed} 失败"
        throttled.log(f"📊 {message}")
        
        return BandiaOutput(
            success=success,
            message=message,
            extracted_count=extracted,
            failed_count=failed,
            total_count=total,
            results=results,
            data={
                'extracted_count': extracted,
                'failed_count': failed,
                'total_count': total
            }
        )
    
    def _filter_archives(self, paths: List[str]) -> List[str]:
        """过滤出有效的压缩包路径"""
        valid = []
        for path_str in paths:
            # 清理路径字符串
            cleaned = path_str.strip().strip('"\'')
            if not cleaned:
                continue
            
            p = Path(cleaned)
            if p.suffix.lower() in ARCHIVE_EXTENSIONS:
                valid.append(cleaned)
        
        return valid
