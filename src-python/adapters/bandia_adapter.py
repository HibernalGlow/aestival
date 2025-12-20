"""
bandia 适配器
批量解压工具 - 使用 Bandizip (bz.exe) 进行批量解压

功能：
- 从路径列表批量解压压缩包
- 支持解压后删除源文件（可选移入回收站）
- 支持 .zip .7z .rar .tar .gz .bz2 .xz 格式
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
        """执行解压操作"""
        # 查找 Bandizip
        bz_path = find_bz_executable()
        if not bz_path:
            return BandiaOutput(
                success=False,
                message="未找到 Bandizip (bz.exe)，请安装 Bandizip 或设置环境变量 BANDIZIP_PATH"
            )
        
        if on_log:
            on_log(f"使用 Bandizip: {bz_path}")
        
        # 过滤有效的压缩包路径
        paths = self._filter_archives(input_data.paths)
        if not paths:
            return BandiaOutput(
                success=False,
                message="没有有效的压缩包路径"
            )
        
        total = len(paths)
        if on_log:
            on_log(f"开始解压 {total} 个压缩包...")
        if on_progress:
            on_progress(5, f"准备解压 {total} 个文件...")
        
        results = []
        extracted = 0
        failed = 0
        
        for idx, archive_path in enumerate(paths):
            p = Path(archive_path)
            progress_pct = int(10 + (idx / total) * 85)
            
            if on_progress:
                on_progress(progress_pct, f"解压 {idx + 1}/{total}: {p.name}")
            
            if not p.exists():
                if on_log:
                    on_log(f"❌ 文件不存在: {p}")
                results.append({'path': str(p), 'success': False, 'error': '文件不存在'})
                failed += 1
                continue
            
            if p.is_dir():
                if on_log:
                    on_log(f"⚠️ 跳过目录: {p}")
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
                    if on_log:
                        on_log(f"✅ 成功 ({duration:.2f}s): {p.name}")
                    
                    # 删除源文件
                    if input_data.delete_after:
                        try:
                            if input_data.use_trash:
                                # 尝试使用 send2trash
                                try:
                                    from send2trash import send2trash
                                    send2trash(str(p))
                                    if on_log:
                                        on_log(f"🗑️ 已移入回收站: {p.name}")
                                except ImportError:
                                    # 如果没有 send2trash，直接删除
                                    p.unlink()
                                    if on_log:
                                        on_log(f"🗑️ 已删除: {p.name}")
                            else:
                                p.unlink()
                                if on_log:
                                    on_log(f"🗑️ 已删除: {p.name}")
                        except Exception as e:
                            if on_log:
                                on_log(f"⚠️ 删除失败 {p.name}: {e}")
                    
                    results.append({'path': str(p), 'success': True, 'duration': duration})
                    extracted += 1
                else:
                    error_msg = proc.stderr or proc.stdout or f"返回码 {proc.returncode}"
                    if on_log:
                        on_log(f"❌ 失败: {p.name} - {error_msg[:100]}")
                    results.append({'path': str(p), 'success': False, 'error': error_msg})
                    failed += 1
                    
            except Exception as e:
                if on_log:
                    on_log(f"❌ 执行失败 {p.name}: {e}")
                results.append({'path': str(p), 'success': False, 'error': str(e)})
                failed += 1
        
        if on_progress:
            on_progress(100, "解压完成")
        
        success = failed == 0
        message = f"解压完成: {extracted} 成功, {failed} 失败"
        if on_log:
            on_log(f"📊 {message}")
        
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
