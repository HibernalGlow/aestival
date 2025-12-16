"""
rawfilter 适配器
相似文件过滤工具 - 分析并处理相似的压缩包文件
"""

import os
from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


class RawfilterInput(AdapterInput):
    """rawfilter 输入参数"""
    path: str = Field(..., description="要处理的目录路径")
    name_only_mode: bool = Field(default=False, description="仅名称模式，跳过内部分析")
    create_shortcuts: bool = Field(default=False, description="创建快捷方式而非移动文件")
    trash_only: bool = Field(default=False, description="仅移动到 trash，不创建 multi")


class RawfilterOutput(AdapterOutput):
    """rawfilter 输出结果"""
    moved_to_trash: int = Field(default=0, description="移动到 trash 的文件数")
    moved_to_multi: int = Field(default=0, description="移动到 multi 的文件数")
    created_shortcuts: int = Field(default=0, description="创建的快捷方式数")
    total_groups: int = Field(default=0, description="处理的文件组数")
    skipped_files: int = Field(default=0, description="跳过的文件数")


class RawfilterAdapter(BaseAdapter):
    """
    rawfilter 适配器
    
    功能：分析并处理相似的压缩包文件
    - 识别汉化版本和原版
    - 将重复/低质量版本移动到 trash
    - 将多个汉化版本移动到 multi
    """
    
    name = "rawfilter"
    display_name = "相似文件过滤"
    description = "分析并处理相似的压缩包文件，自动识别汉化版本"
    category = "file"
    icon = "🔍"
    required_packages = ["rawfilter"]  # 依赖的工具包
    input_schema = RawfilterInput
    output_schema = RawfilterOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 rawfilter 模块"""
        # 导入核心函数
        from rawfilter.__main__ import (
            group_similar_files,
            process_file_group,
            ARCHIVE_EXTENSIONS
        )
        
        return {
            'group_similar_files': group_similar_files,
            'process_file_group': process_file_group,
            'ARCHIVE_EXTENSIONS': ARCHIVE_EXTENSIONS
        }
    
    async def execute(
        self,
        input_data: RawfilterInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> RawfilterOutput:
        """
        执行 rawfilter 功能
        
        流程：
        1. 扫描目录中的压缩包文件
        2. 按相似度分组
        3. 处理每个组，移动重复文件
        """
        # 验证路径
        path = Path(input_data.path)
        if not path.exists():
            return RawfilterOutput(
                success=False,
                message=f"路径不存在: {input_data.path}"
            )
        
        if not path.is_dir():
            return RawfilterOutput(
                success=False,
                message=f"路径不是目录: {input_data.path}"
            )
        
        try:
            module = self.get_module()
            group_similar_files = module['group_similar_files']
            process_file_group = module['process_file_group']
            ARCHIVE_EXTENSIONS = module['ARCHIVE_EXTENSIONS']
            
            if on_log:
                on_log(f"开始扫描目录: {input_data.path}")
            if on_progress:
                on_progress(10, "正在扫描文件...")
            
            # 扫描压缩包文件
            archive_files = []
            for file in path.iterdir():
                if file.is_file() and file.suffix.lower() in ARCHIVE_EXTENSIONS:
                    archive_files.append(file.name)
            
            if not archive_files:
                return RawfilterOutput(
                    success=True,
                    message="目录中没有找到压缩包文件",
                    output_path=input_data.path
                )
            
            if on_log:
                on_log(f"找到 {len(archive_files)} 个压缩包文件")
            if on_progress:
                on_progress(30, f"找到 {len(archive_files)} 个文件，正在分组...")
            
            # 分组相似文件
            groups = group_similar_files(archive_files)
            
            if on_log:
                on_log(f"分成 {len(groups)} 个组")
            
            # 创建 trash 目录
            trash_dir = path / "trash"
            trash_dir.mkdir(exist_ok=True)
            
            # 统计结果
            total_stats = {
                'moved_to_trash': 0,
                'moved_to_multi': 0,
                'created_shortcuts': 0
            }
            
            # 处理每个组
            processed_groups = 0
            for group_name, group_files in groups.items():
                if len(group_files) <= 1:
                    # 单文件组，跳过
                    continue
                
                processed_groups += 1
                progress = 30 + int(60 * processed_groups / len(groups))
                
                if on_progress:
                    on_progress(progress, f"处理组 {processed_groups}/{len(groups)}")
                
                if on_log:
                    on_log(f"处理组 [{group_name}]: {len(group_files)} 个文件")
                
                # 处理文件组
                try:
                    result_stats = process_file_group(
                        group_files,
                        str(path),
                        str(trash_dir),
                        create_shortcuts=input_data.create_shortcuts,
                        name_only_mode=input_data.name_only_mode,
                        trash_only=input_data.trash_only
                    )
                    
                    # 累加统计
                    for key in total_stats:
                        if key in result_stats:
                            total_stats[key] += result_stats[key]
                            
                except Exception as e:
                    if on_log:
                        on_log(f"处理组 [{group_name}] 失败: {str(e)}")
            
            if on_progress:
                on_progress(100, "处理完成")
            
            message = (
                f"处理完成: "
                f"{total_stats['moved_to_trash']} 移到 trash, "
                f"{total_stats['moved_to_multi']} 移到 multi"
            )
            
            if on_log:
                on_log(message)
            
            return RawfilterOutput(
                success=True,
                message=message,
                moved_to_trash=total_stats['moved_to_trash'],
                moved_to_multi=total_stats['moved_to_multi'],
                created_shortcuts=total_stats['created_shortcuts'],
                total_groups=processed_groups,
                output_path=input_data.path,
                stats=total_stats
            )
            
        except ImportError as e:
            return RawfilterOutput(
                success=False,
                message=f"rawfilter 模块未安装: {str(e)}"
            )
        except Exception as e:
            if on_log:
                on_log(f"执行失败: {str(e)}")
            return RawfilterOutput(
                success=False,
                message=f"执行失败: {type(e).__name__}: {str(e)}"
            )
