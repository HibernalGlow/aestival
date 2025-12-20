"""
migratef 适配器
文件迁移工具 - 保持目录结构迁移文件和文件夹

支持三种迁移模式：
1. preserve: 保持目录结构迁移
2. flat: 扁平迁移（只迁移文件，不保持目录结构）
3. direct: 直接迁移（类似mv命令，整个文件/文件夹作为单位）
"""

import io
import os
import sys
import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


def _ensure_utf8_output():
    """确保 stdout/stderr 使用 UTF-8 编码"""
    if sys.platform == 'win32':
        os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, 
                encoding='utf-8', 
                errors='replace',
                line_buffering=True
            )
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, 
                encoding='utf-8', 
                errors='replace',
                line_buffering=True
            )


_ensure_utf8_output()


class MigrateFInput(AdapterInput):
    """migratef 输入参数"""
    path: str = Field(default="", description="源路径")
    source_paths: List[str] = Field(default_factory=list, description="源路径列表")
    target_path: str = Field(default="", description="目标目录路径")
    mode: str = Field(default="preserve", description="迁移模式: preserve/flat/direct")
    action: str = Field(default="move", description="操作类型: copy/move")
    max_workers: int = Field(default=8, description="最大线程数")
    existing_dir: str = Field(default="merge", description="目录冲突处理: merge/skip")


class MigrateFOutput(AdapterOutput):
    """migratef 输出结果"""
    migrated_count: int = Field(default=0, description="成功迁移数量")
    skipped_count: int = Field(default=0, description="跳过数量")
    error_count: int = Field(default=0, description="失败数量")
    total_count: int = Field(default=0, description="总数量")


class MigrateFAdapter(BaseAdapter):
    """migratef 适配器 - 文件迁移工具"""
    
    name = "migratef"
    display_name = "文件迁移"
    description = "保持目录结构迁移文件和文件夹"
    category = "file"
    icon = "📁"
    required_packages = []
    input_schema = MigrateFInput
    output_schema = MigrateFOutput
    
    def _import_module(self) -> Dict:
        return {}
    
    async def execute(
        self,
        input_data: MigrateFInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MigrateFOutput:
        """执行文件迁移"""
        mode = input_data.mode.lower()
        
        # 收集源路径，去除引号
        source_paths = list(input_data.source_paths) if input_data.source_paths else []
        if input_data.path:
            path = input_data.path.strip().strip('"')
            if path not in source_paths:
                source_paths.append(path)
        
        # 处理所有路径的引号
        source_paths = [p.strip().strip('"') for p in source_paths]
        
        if not source_paths:
            return MigrateFOutput(success=False, message="未指定源路径")
        
        # 目标路径也去除引号
        target_path = input_data.target_path.strip().strip('"') if input_data.target_path else ""
        if not target_path:
            return MigrateFOutput(success=False, message="未指定目标路径")
        
        # 更新 input_data 的 target_path
        input_data.target_path = target_path
        
        # 验证源路径
        valid_paths = []
        for p in source_paths:
            path = Path(p)
            if path.exists():
                valid_paths.append(str(path.resolve()))
            elif on_log:
                on_log(f"跳过不存在: {p}")
        
        if not valid_paths:
            return MigrateFOutput(success=False, message="没有有效的源路径")
        
        if mode == "direct":
            return await self._migrate_direct(valid_paths, input_data, on_progress, on_log)
        else:
            return await self._migrate_files(valid_paths, input_data, on_progress, on_log)
    
    async def _migrate_direct(
        self,
        source_paths: List[str],
        input_data: MigrateFInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MigrateFOutput:
        """直接迁移模式"""
        try:
            target_root = Path(input_data.target_path).resolve()
            target_root.mkdir(parents=True, exist_ok=True)
            
            action = input_data.action.lower()
            action_text = "移动" if action == "move" else "复制"
            existing_dir = input_data.existing_dir.lower()
            
            if on_log:
                on_log(f"目标: {target_root}")
                on_log(f"模式: 直接迁移 ({action_text})")
            
            counters = {'migrated': 0, 'skipped': 0, 'error': 0}
            total = len(source_paths)
            
            for i, source_path_str in enumerate(source_paths):
                source_path = Path(source_path_str)
                item_name = source_path.name
                target_path = target_root / item_name
                
                if on_progress:
                    progress = int((i / total) * 100)
                    on_progress(progress, f"{action_text}: {item_name}")
                
                try:
                    if not source_path.exists():
                        if on_log:
                            on_log(f"跳过: {item_name} 不存在")
                        counters['skipped'] += 1
                        continue
                    
                    if target_path.exists():
                        if source_path.is_dir() and target_path.is_dir():
                            if existing_dir == "merge":
                                self._merge_directories(source_path, target_path, action)
                                counters['migrated'] += 1
                                if on_log:
                                    on_log(f"合并: {item_name}")
                            else:
                                counters['skipped'] += 1
                                if on_log:
                                    on_log(f"跳过(已存在): {item_name}")
                            continue
                        else:
                            counters['skipped'] += 1
                            if on_log:
                                on_log(f"跳过(已存在): {item_name}")
                            continue
                    
                    if action == "move":
                        shutil.move(str(source_path), str(target_path))
                    else:
                        if source_path.is_file():
                            shutil.copy2(source_path, target_path)
                        else:
                            shutil.copytree(source_path, target_path)
                    
                    counters['migrated'] += 1
                    if on_log:
                        on_log(f"{action_text}: {item_name}")
                        
                except Exception as e:
                    counters['error'] += 1
                    if on_log:
                        on_log(f"错误 {item_name}: {e}")
            
            if on_progress:
                on_progress(100, "完成")
            
            return MigrateFOutput(
                success=True,
                message=f"{action_text}完成: {counters['migrated']} 成功, {counters['skipped']} 跳过, {counters['error']} 失败",
                migrated_count=counters['migrated'],
                skipped_count=counters['skipped'],
                error_count=counters['error'],
                total_count=total,
                output_path=str(target_root),
                data={
                    'migrated_count': counters['migrated'],
                    'skipped_count': counters['skipped'],
                    'error_count': counters['error'],
                    'total_count': total
                }
            )
        except Exception as e:
            return MigrateFOutput(success=False, message=f"迁移失败: {e}")
    
    async def _migrate_files(
        self,
        source_paths: List[str],
        input_data: MigrateFInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MigrateFOutput:
        """文件级迁移模式"""
        try:
            target_root = Path(input_data.target_path).resolve()
            target_root.mkdir(parents=True, exist_ok=True)
            
            action = input_data.action.lower()
            action_text = "移动" if action == "move" else "复制"
            preserve_structure = input_data.mode.lower() == "preserve"
            mode_text = "保持结构" if preserve_structure else "扁平"
            
            if on_log:
                on_log(f"目标: {target_root}")
                on_log(f"模式: {mode_text} ({action_text})")
            
            if on_progress:
                on_progress(5, "收集文件...")
            
            all_files = self._collect_files(source_paths, preserve_structure, on_log)
            
            if not all_files:
                return MigrateFOutput(success=False, message="没有找到可迁移的文件")
            
            if on_log:
                on_log(f"共 {len(all_files)} 个文件")
            
            counters = {'migrated': 0, 'skipped': 0, 'error': 0}
            lock = Lock()
            total = len(all_files)
            processed = [0]
            
            def process_file(file_info):
                source_file, rel_path = file_info
                source_path = Path(source_file)
                file_name = source_path.name
                
                try:
                    if not source_path.is_file():
                        with lock:
                            counters['skipped'] += 1
                            processed[0] += 1
                        return
                    
                    if preserve_structure and rel_path:
                        target_file = target_root / rel_path
                    else:
                        target_file = target_root / file_name
                    
                    with lock:
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    if action == "move":
                        shutil.move(str(source_path), str(target_file))
                    else:
                        shutil.copy2(source_path, target_file)
                    
                    with lock:
                        counters['migrated'] += 1
                        processed[0] += 1
                        if on_progress:
                            progress = int((processed[0] / total) * 95) + 5
                            on_progress(progress, f"{action_text}: {file_name}")
                            
                except Exception as e:
                    with lock:
                        counters['error'] += 1
                        processed[0] += 1
                        if on_log:
                            on_log(f"错误 {file_name}: {e}")
            
            max_workers = input_data.max_workers or 8
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                executor.map(process_file, all_files)
            
            if on_progress:
                on_progress(100, "完成")
            
            if on_log:
                on_log(f"{action_text}完成: {counters['migrated']} 成功")
                if counters['skipped'] > 0:
                    on_log(f"跳过: {counters['skipped']}")
                if counters['error'] > 0:
                    on_log(f"错误: {counters['error']}")
            
            return MigrateFOutput(
                success=True,
                message=f"{action_text}完成: {counters['migrated']} 成功, {counters['skipped']} 跳过, {counters['error']} 失败",
                migrated_count=counters['migrated'],
                skipped_count=counters['skipped'],
                error_count=counters['error'],
                total_count=total,
                output_path=str(target_root),
                data={
                    'migrated_count': counters['migrated'],
                    'skipped_count': counters['skipped'],
                    'error_count': counters['error'],
                    'total_count': total
                }
            )
        except Exception as e:
            return MigrateFOutput(success=False, message=f"迁移失败: {e}")
    
    def _collect_files(
        self,
        source_paths: List[str],
        preserve_structure: bool,
        on_log: Optional[Callable[[str], None]] = None
    ) -> List[tuple]:
        """收集所有文件"""
        all_files = []
        
        for path_str in source_paths:
            path = Path(path_str)
            
            if path.is_file():
                all_files.append((str(path), path.name))
            elif path.is_dir():
                if preserve_structure:
                    try:
                        for file_path in path.rglob('*'):
                            if file_path.is_file():
                                drive, path_without_drive = os.path.splitdrive(file_path)
                                rel_parts = path_without_drive.strip(os.sep).split(os.sep)
                                rel_path = Path(*rel_parts)
                                all_files.append((str(file_path), str(rel_path)))
                    except Exception as e:
                        if on_log:
                            on_log(f"扫描出错 {path}: {e}")
                else:
                    try:
                        for item in path.iterdir():
                            if item.is_file():
                                all_files.append((str(item), item.name))
                    except Exception as e:
                        if on_log:
                            on_log(f"扫描出错 {path}: {e}")
        
        return all_files
    
    def _merge_directories(self, src: Path, dst: Path, action: str):
        """合并目录"""
        for root, dirs, files in os.walk(src):
            rel = Path(root).relative_to(src)
            target_dir = dst / rel
            target_dir.mkdir(parents=True, exist_ok=True)
            
            for f in files:
                s_file = Path(root) / f
                t_file = target_dir / f
                try:
                    if action == 'move':
                        if t_file.exists():
                            if t_file.is_file():
                                t_file.unlink()
                            else:
                                shutil.rmtree(t_file)
                        shutil.move(str(s_file), str(t_file))
                    else:
                        if t_file.exists() and not t_file.is_file():
                            shutil.rmtree(t_file)
                        shutil.copy2(s_file, t_file)
                except Exception:
                    pass
        
        if action == 'move':
            try:
                shutil.rmtree(src)
            except Exception:
                pass
