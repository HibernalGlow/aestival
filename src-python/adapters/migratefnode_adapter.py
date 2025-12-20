"""
migratefnode 适配器
文件迁移工具 - 扫描并迁移文件到目标目录

支持两阶段操作：
1. scan: 扫描源目录，生成迁移计划
2. migrate: 根据计划执行迁移
"""

import io
import os
import sys
import shutil
import json
from pathlib import Path
from typing import Callable, Dict, List, Optional
from datetime import datetime

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


def _ensure_utf8_output():
    """确保 stdout/stderr 使用 UTF-8 编码，避免 Windows GBK 编码问题"""
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


class MigrateFNodeInput(AdapterInput):
    """migratefnode 输入参数"""
    action: str = Field(default="scan", description="操作类型: scan, migrate, full")
    path: str = Field(default="", description="源目录路径")
    target_path: str = Field(default="", description="目标目录路径")
    pattern: str = Field(default="*", description="文件匹配模式，如 *.jpg, *.png")
    recursive: bool = Field(default=True, description="是否递归扫描子目录")
    overwrite: bool = Field(default=False, description="是否覆盖已存在的文件")
    dry_run: bool = Field(default=True, description="模拟执行，不实际移动文件")
    preserve_structure: bool = Field(default=True, description="保持目录结构")
    config_path: str = Field(default="", description="配置文件路径（用于 migrate 操作）")


class MigrateFNodeOutput(AdapterOutput):
    """migratefnode 输出结果"""
    config_path: str = Field(default="", description="生成的配置文件路径")
    total_files: int = Field(default=0, description="扫描到的文件总数")
    total_size: int = Field(default=0, description="文件总大小（字节）")
    moved_count: int = Field(default=0, description="成功迁移的数量")
    skipped_count: int = Field(default=0, description="跳过的数量")
    failed_count: int = Field(default=0, description="失败的数量")
    file_list: Optional[List[Dict]] = Field(default=None, description="文件列表")


class MigrateFNodeAdapter(BaseAdapter):
    """
    migratefnode 适配器
    
    功能：扫描并迁移文件到目标目录
    支持两阶段操作：scan -> migrate
    """
    
    name = "migratefnode"
    display_name = "文件迁移"
    description = "扫描并迁移文件到目标目录，支持模式匹配和目录结构保持"
    category = "file"
    icon = "📁"
    required_packages = []  # 无外部依赖
    input_schema = MigrateFNodeInput
    output_schema = MigrateFNodeOutput
    
    def _import_module(self) -> Dict:
        """无需外部模块，返回空字典"""
        return {}
    
    async def execute(
        self,
        input_data: MigrateFNodeInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MigrateFNodeOutput:
        """执行 migratefnode 功能"""
        action = input_data.action.lower()
        
        if action == "scan":
            return await self._scan(input_data, on_progress, on_log)
        elif action == "migrate":
            return await self._migrate(input_data, on_progress, on_log)
        else:
            # full 模式：先扫描再迁移
            return await self._full(input_data, on_progress, on_log)
    
    async def _scan(
        self,
        input_data: MigrateFNodeInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MigrateFNodeOutput:
        """阶段1：扫描源目录"""
        try:
            normalized_path = os.path.normpath(input_data.path)
            source_path = Path(normalized_path)
        except Exception as e:
            return MigrateFNodeOutput(
                success=False,
                message=f"路径格式错误: {str(e)}"
            )
        
        if not source_path.exists():
            return MigrateFNodeOutput(
                success=False,
                message=f"源路径不存在: {input_data.path}"
            )
        
        if not source_path.is_dir():
            return MigrateFNodeOutput(
                success=False,
                message=f"源路径不是目录: {input_data.path}"
            )
        
        try:
            if on_log:
                on_log(f"开始扫描目录: {input_data.path}")
            if on_progress:
                on_progress(10, "正在扫描文件...")
            
            # 扫描文件
            file_list = []
            total_size = 0
            pattern = input_data.pattern
            
            if input_data.recursive:
                files = list(source_path.rglob(pattern))
            else:
                files = list(source_path.glob(pattern))
            
            if on_progress:
                on_progress(30, f"找到 {len(files)} 个文件，正在分析...")
            
            for i, file_path in enumerate(files):
                if file_path.is_file():
                    try:
                        file_size = file_path.stat().st_size
                        rel_path = file_path.relative_to(source_path)
                        
                        file_list.append({
                            'source': str(file_path),
                            'relative': str(rel_path),
                            'size': file_size,
                            'status': 'pending'
                        })
                        total_size += file_size
                    except Exception as e:
                        if on_log:
                            on_log(f"跳过文件 {file_path}: {e}")
                
                if on_progress and i % 100 == 0:
                    progress = 30 + int((i / len(files)) * 40)
                    on_progress(progress, f"已扫描 {i}/{len(files)} 个文件")
            
            if on_progress:
                on_progress(80, "正在生成配置文件...")
            
            # 生成配置文件
            config = {
                'source_path': str(source_path),
                'target_path': input_data.target_path,
                'pattern': pattern,
                'recursive': input_data.recursive,
                'preserve_structure': input_data.preserve_structure,
                'overwrite': input_data.overwrite,
                'files': file_list,
                'created_at': datetime.now().isoformat()
            }
            
            config_filename = f"migrate_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            config_path = source_path / config_filename
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            if on_progress:
                on_progress(100, "扫描完成")
            
            if on_log:
                on_log(f"扫描完成，共 {len(file_list)} 个文件")
                on_log(f"配置文件: {config_path}")
            
            return MigrateFNodeOutput(
                success=True,
                message=f"扫描完成，共 {len(file_list)} 个文件",
                config_path=str(config_path),
                total_files=len(file_list),
                total_size=total_size,
                file_list=file_list,
                output_path=input_data.path,
                data={
                    'config_path': str(config_path),
                    'total_files': len(file_list),
                    'total_size': total_size,
                    'file_list': file_list[:100]  # 限制返回数量
                }
            )
            
        except Exception as e:
            import traceback
            if on_log:
                on_log(f"扫描失败: {str(e)}")
                on_log(f"详细错误: {traceback.format_exc()}")
            return MigrateFNodeOutput(
                success=False,
                message=f"扫描失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _migrate(
        self,
        input_data: MigrateFNodeInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MigrateFNodeOutput:
        """阶段2：执行迁移"""
        config_path = Path(input_data.config_path)
        
        if not config_path.exists():
            return MigrateFNodeOutput(
                success=False,
                message=f"配置文件不存在: {input_data.config_path}"
            )
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if on_log:
                on_log(f"开始迁移，配置文件: {input_data.config_path}")
            if on_progress:
                on_progress(10, "正在读取配置...")
            
            target_path = Path(input_data.target_path or config.get('target_path', ''))
            if not target_path:
                return MigrateFNodeOutput(
                    success=False,
                    message="未指定目标路径"
                )
            
            source_path = Path(config['source_path'])
            files = config.get('files', [])
            preserve_structure = config.get('preserve_structure', True)
            overwrite = input_data.overwrite or config.get('overwrite', False)
            dry_run = input_data.dry_run
            
            moved_count = 0
            skipped_count = 0
            failed_count = 0
            
            if on_progress:
                on_progress(20, f"准备迁移 {len(files)} 个文件...")
            
            for i, file_info in enumerate(files):
                src = Path(file_info['source'])
                
                if preserve_structure:
                    rel_path = file_info.get('relative', src.name)
                    dst = target_path / rel_path
                else:
                    dst = target_path / src.name
                
                try:
                    if not src.exists():
                        file_info['status'] = 'skipped'
                        file_info['reason'] = '源文件不存在'
                        skipped_count += 1
                        continue
                    
                    if dst.exists() and not overwrite:
                        file_info['status'] = 'skipped'
                        file_info['reason'] = '目标已存在'
                        skipped_count += 1
                        continue
                    
                    if not dry_run:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(src), str(dst))
                    
                    file_info['status'] = 'moved'
                    file_info['target'] = str(dst)
                    moved_count += 1
                    
                except Exception as e:
                    file_info['status'] = 'failed'
                    file_info['reason'] = str(e)
                    failed_count += 1
                    if on_log:
                        on_log(f"迁移失败 {src}: {e}")
                
                if on_progress and i % 50 == 0:
                    progress = 20 + int((i / len(files)) * 70)
                    on_progress(progress, f"已处理 {i}/{len(files)} 个文件")
            
            # 更新配置文件
            config['files'] = files
            config['migrated_at'] = datetime.now().isoformat()
            config['dry_run'] = dry_run
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            if on_progress:
                on_progress(100, "迁移完成")
            
            mode_text = "模拟" if dry_run else "实际"
            if on_log:
                on_log(f"{mode_text}迁移完成: {moved_count} 成功, {skipped_count} 跳过, {failed_count} 失败")
            
            return MigrateFNodeOutput(
                success=True,
                message=f"{mode_text}迁移完成: {moved_count} 成功, {skipped_count} 跳过, {failed_count} 失败",
                config_path=str(config_path),
                total_files=len(files),
                moved_count=moved_count,
                skipped_count=skipped_count,
                failed_count=failed_count,
                stats={
                    'moved': moved_count,
                    'skipped': skipped_count,
                    'failed': failed_count,
                    'total': len(files)
                },
                data={
                    'moved_count': moved_count,
                    'skipped_count': skipped_count,
                    'failed_count': failed_count,
                    'total_files': len(files),
                    'dry_run': dry_run
                }
            )
            
        except Exception as e:
            if on_log:
                on_log(f"迁移失败: {str(e)}")
            return MigrateFNodeOutput(
                success=False,
                message=f"迁移失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _full(
        self,
        input_data: MigrateFNodeInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MigrateFNodeOutput:
        """完整流程：扫描 + 迁移"""
        # 先扫描
        scan_result = await self._scan(input_data, on_progress, on_log)
        
        if not scan_result.success:
            return scan_result
        
        # 再迁移
        input_data.config_path = scan_result.config_path
        migrate_result = await self._migrate(input_data, on_progress, on_log)
        
        # 合并结果
        migrate_result.total_size = scan_result.total_size
        
        return migrate_result
