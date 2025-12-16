"""
repacku 适配器
文件重打包工具 - 分析目录结构并打包为压缩文件

支持两阶段操作：
1. analyze: 分析目录结构，生成配置文件
2. compress: 根据配置文件执行压缩
"""

import io
import os
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


def _ensure_utf8_output():
    """确保 stdout/stderr 使用 UTF-8 编码，避免 Windows GBK 编码问题"""
    if sys.platform == 'win32':
        # 设置环境变量强制 Python 使用 UTF-8
        os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
        
        # 重新包装 stdout/stderr 使用 UTF-8 编码，忽略无法编码的字符
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


# 在模块加载时执行编码适配
_ensure_utf8_output()


class RepackuInput(AdapterInput):
    """repacku 输入参数"""
    # 操作类型：analyze（分析）或 compress（压缩）
    action: str = Field(default="full", description="操作类型: analyze, compress, full")
    path: str = Field(default="", description="要处理的目录路径")
    types: List[str] = Field(default_factory=list, description="文件类型过滤，如 ['image', 'document']")
    delete_after: bool = Field(default=False, description="压缩成功后删除源文件")
    display_tree: bool = Field(default=True, description="显示目录树结构")
    config_path: str = Field(default="", description="配置文件路径（用于 compress 操作）")


class RepackuOutput(AdapterOutput):
    """repacku 输出结果"""
    config_path: str = Field(default="", description="生成的配置文件路径")
    compressed_count: int = Field(default=0, description="成功压缩的数量")
    failed_count: int = Field(default=0, description="失败的数量")
    total_folders: int = Field(default=0, description="分析的文件夹总数")
    entire_count: int = Field(default=0, description="整体压缩的文件夹数")
    selective_count: int = Field(default=0, description="选择性压缩的文件夹数")
    skip_count: int = Field(default=0, description="跳过的文件夹数")
    folder_tree: Optional[Dict] = Field(default=None, description="文件夹树结构")


class RepackuAdapter(BaseAdapter):
    """
    repacku 适配器
    
    功能：分析目录结构并打包为压缩文件
    支持两阶段操作：analyze -> compress
    """
    
    name = "repacku"
    display_name = "文件重打包"
    description = "分析目录结构并打包为压缩文件，支持类型过滤"
    category = "file"
    icon = "📦"
    required_packages = ["repacku"]  # 依赖的工具包
    input_schema = RepackuInput
    output_schema = RepackuOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 repacku 模块"""
        from repacku.core.folder_analyzer import FolderAnalyzer, analyze_folder
        from repacku.core.zip_compressor import ZipCompressor
        
        return {
            'FolderAnalyzer': FolderAnalyzer,
            'analyze_folder': analyze_folder,
            'ZipCompressor': ZipCompressor
        }
    
    async def execute(
        self,
        input_data: RepackuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> RepackuOutput:
        """
        执行 repacku 功能
        
        支持三种操作模式：
        - analyze: 仅分析目录，生成配置文件
        - compress: 根据配置文件执行压缩
        - full: 分析 + 压缩（默认）
        """
        action = input_data.action.lower()
        
        if action == "analyze":
            return await self._analyze(input_data, on_progress, on_log)
        elif action == "compress":
            return await self._compress(input_data, on_progress, on_log)
        else:
            # full 模式：先分析再压缩
            return await self._full(input_data, on_progress, on_log)
    
    async def _analyze(
        self,
        input_data: RepackuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> RepackuOutput:
        """阶段1：分析目录结构"""
        path = Path(input_data.path)
        
        if not path.exists():
            return RepackuOutput(
                success=False,
                message=f"路径不存在: {input_data.path}"
            )
        
        if not path.is_dir():
            return RepackuOutput(
                success=False,
                message=f"路径不是目录: {input_data.path}"
            )
        
        try:
            module = self.get_module()
            FolderAnalyzer = module['FolderAnalyzer']
            
            if on_log:
                on_log(f"开始分析目录: {input_data.path}")
            if on_progress:
                on_progress(10, "正在分析目录结构...")
            
            # 创建分析器
            analyzer = FolderAnalyzer()
            
            # 准备类型过滤参数
            target_types = input_data.types if input_data.types else None
            
            if on_progress:
                on_progress(30, "正在扫描文件类型...")
            
            # 分析文件夹结构
            root_info = analyzer.analyze_folder_structure(path, target_file_types=target_types)
            
            if root_info is None:
                return RepackuOutput(
                    success=False,
                    message="无法分析文件夹（可能在黑名单中）"
                )
            
            if on_progress:
                on_progress(70, "正在生成配置文件...")
            
            # 生成配置文件
            config_path = analyzer.generate_config_json(
                path,
                output_path=None,
                target_file_types=target_types,
                root_info=root_info
            )
            
            # 统计压缩模式
            stats = self._count_compress_modes(root_info)
            
            if on_progress:
                on_progress(100, "分析完成")
            
            if on_log:
                on_log(f"分析完成，配置文件: {config_path}")
                on_log(f"整体压缩: {stats['entire']}, 选择性: {stats['selective']}, 跳过: {stats['skip']}")
            
            return RepackuOutput(
                success=True,
                message=f"分析完成，共 {stats['total']} 个文件夹",
                config_path=str(config_path),
                total_folders=stats['total'],
                entire_count=stats['entire'],
                selective_count=stats['selective'],
                skip_count=stats['skip'],
                folder_tree=root_info.to_tree_dict() if root_info else None,
                output_path=input_data.path,
                # 把数据也放到 data 字段，供前端使用
                data={
                    'config_path': str(config_path),
                    'total_folders': stats['total'],
                    'entire_count': stats['entire'],
                    'selective_count': stats['selective'],
                    'skip_count': stats['skip'],
                    'folder_tree': root_info.to_tree_dict() if root_info else None
                }
            )
            
        except ImportError as e:
            return RepackuOutput(
                success=False,
                message=f"repacku 模块未安装: {str(e)}"
            )
        except Exception as e:
            if on_log:
                on_log(f"分析失败: {str(e)}")
            return RepackuOutput(
                success=False,
                message=f"分析失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _compress(
        self,
        input_data: RepackuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> RepackuOutput:
        """阶段2：根据配置文件执行压缩"""
        config_path = Path(input_data.config_path)
        
        if not config_path.exists():
            return RepackuOutput(
                success=False,
                message=f"配置文件不存在: {input_data.config_path}"
            )
        
        try:
            module = self.get_module()
            ZipCompressor = module['ZipCompressor']
            
            if on_log:
                on_log(f"开始压缩，配置文件: {input_data.config_path}")
            if on_progress:
                on_progress(10, "正在读取配置...")
            
            # 创建压缩器
            compressor = ZipCompressor()
            
            if on_progress:
                on_progress(30, "正在执行压缩...")
            
            # 执行压缩
            results = compressor.compress_from_json(
                config_path,
                delete_after_success=input_data.delete_after
            )
            
            # 统计结果
            success_count = sum(1 for r in results if r.success)
            fail_count = len(results) - success_count
            
            if on_progress:
                on_progress(100, "压缩完成")
            
            if on_log:
                on_log(f"压缩完成: {success_count} 成功, {fail_count} 失败")
            
            return RepackuOutput(
                success=True,
                message=f"压缩完成: {success_count} 成功, {fail_count} 失败",
                config_path=str(config_path),
                compressed_count=success_count,
                failed_count=fail_count,
                total_folders=len(results),
                stats={
                    'success': success_count,
                    'failed': fail_count,
                    'total': len(results)
                },
                # 把数据也放到 data 字段，供前端使用
                data={
                    'compressed_count': success_count,
                    'failed_count': fail_count,
                    'total_folders': len(results)
                }
            )
            
        except ImportError as e:
            return RepackuOutput(
                success=False,
                message=f"repacku 模块未安装: {str(e)}"
            )
        except Exception as e:
            if on_log:
                on_log(f"压缩失败: {str(e)}")
            return RepackuOutput(
                success=False,
                message=f"压缩失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _full(
        self,
        input_data: RepackuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> RepackuOutput:
        """完整流程：分析 + 压缩"""
        # 先分析
        analyze_result = await self._analyze(input_data, on_progress, on_log)
        
        if not analyze_result.success:
            return analyze_result
        
        # 再压缩
        input_data.config_path = analyze_result.config_path
        compress_result = await self._compress(input_data, on_progress, on_log)
        
        # 合并结果
        compress_result.entire_count = analyze_result.entire_count
        compress_result.selective_count = analyze_result.selective_count
        compress_result.skip_count = analyze_result.skip_count
        compress_result.folder_tree = analyze_result.folder_tree
        
        return compress_result
    
    def _count_compress_modes(self, folder_info) -> Dict[str, int]:
        """递归统计压缩模式"""
        stats = {'entire': 0, 'selective': 0, 'skip': 0, 'total': 0}
        
        def count(info):
            if info is None:
                return
            
            stats['total'] += 1
            mode = info.compress_mode or 'skip'
            if mode == 'entire':
                stats['entire'] += 1
            elif mode == 'selective':
                stats['selective'] += 1
            else:
                stats['skip'] += 1
            
            for child in info.children:
                count(child)
        
        count(folder_info)
        return stats
