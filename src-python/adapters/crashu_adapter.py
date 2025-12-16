"""
crashu 适配器
文件夹相似度检测与批量移动工具
"""

import os
from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


class CrashuInput(AdapterInput):
    """crashu 输入参数"""
    path: str = Field(..., description="要扫描的源目录路径")
    target_path: str = Field(default="", description="目标文件夹路径（用于匹配）")
    destination_path: str = Field(default="", description="移动目标路径")
    similarity_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="相似度阈值")
    auto_move: bool = Field(default=False, description="自动执行移动操作")


class CrashuOutput(AdapterOutput):
    """crashu 输出结果"""
    total_scanned: int = Field(default=0, description="扫描的文件夹总数")
    similar_found: int = Field(default=0, description="找到的相似文件夹数")
    moved_count: int = Field(default=0, description="移动的文件夹数")
    pairs_file: str = Field(default="", description="生成的配对 JSON 文件路径")


class CrashuAdapter(BaseAdapter):
    """
    crashu 适配器
    
    功能：检测文件夹相似度并批量移动
    - 扫描源目录中的文件夹
    - 与目标文件夹名称进行相似度匹配
    - 生成移动路径或执行移动操作
    """
    
    name = "crashu"
    display_name = "相似文件夹检测"
    description = "检测文件夹相似度并批量移动，用于整理重复内容"
    category = "file"
    icon = "💥"
    required_packages = ["crashu"]  # 依赖的工具包
    input_schema = CrashuInput
    output_schema = CrashuOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 crashu 模块"""
        from crashu.core.folder_manager import FolderManager
        from crashu.core.output_manager import OutputManager
        
        return {
            'FolderManager': FolderManager,
            'OutputManager': OutputManager
        }
    
    async def execute(
        self,
        input_data: CrashuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> CrashuOutput:
        """
        执行 crashu 功能
        
        流程：
        1. 扫描源目录中的文件夹
        2. 与目标文件夹进行相似度匹配
        3. 生成配对结果
        4. 可选：执行移动操作
        """
        # 验证路径
        source_path = Path(input_data.path)
        if not source_path.exists():
            return CrashuOutput(
                success=False,
                message=f"源路径不存在: {input_data.path}"
            )
        
        if not source_path.is_dir():
            return CrashuOutput(
                success=False,
                message=f"源路径不是目录: {input_data.path}"
            )
        
        try:
            module = self.get_module()
            FolderManager = module['FolderManager']
            OutputManager = module['OutputManager']
            
            if on_log:
                on_log(f"开始扫描目录: {input_data.path}")
            if on_progress:
                on_progress(10, "正在初始化...")
            
            # 初始化管理器
            folder_manager = FolderManager()
            output_manager = OutputManager()
            
            # 获取目标文件夹列表
            target_folder_names = []
            target_folder_fullpaths = []
            
            if input_data.target_path and Path(input_data.target_path).exists():
                # 从目标路径自动获取文件夹名称
                target_path = Path(input_data.target_path)
                for item in target_path.iterdir():
                    if item.is_dir():
                        target_folder_names.append(item.name)
                        target_folder_fullpaths.append(str(item))
                
                if on_log:
                    on_log(f"从目标路径获取 {len(target_folder_names)} 个文件夹名称")
            else:
                # 使用源目录中的文件夹作为目标
                for item in source_path.iterdir():
                    if item.is_dir():
                        target_folder_names.append(item.name)
                
                if on_log:
                    on_log(f"使用源目录中的 {len(target_folder_names)} 个文件夹")
            
            if not target_folder_names:
                return CrashuOutput(
                    success=True,
                    message="没有找到要处理的文件夹",
                    output_path=input_data.path
                )
            
            if on_progress:
                on_progress(30, f"扫描 {len(target_folder_names)} 个文件夹...")
            
            # 扫描相似文件夹
            source_paths = [str(source_path)]
            auto_get = bool(input_data.target_path)
            
            similar_folders = folder_manager.scan_similar_folders(
                source_paths,
                target_folder_names,
                target_folder_fullpaths if auto_get else None,
                input_data.similarity_threshold,
                auto_get
            )
            
            if on_log:
                on_log(f"找到 {len(similar_folders)} 个相似文件夹")
            if on_progress:
                on_progress(70, f"找到 {len(similar_folders)} 个相似项")
            
            # 生成输出路径
            pairs_file = ""
            moved_count = 0
            
            if similar_folders:
                # 确定目标路径
                dest_path = input_data.destination_path or str(source_path / "similar_moved")
                os.makedirs(dest_path, exist_ok=True)
                
                # 生成输出路径
                output_paths = output_manager.generate_output_paths(
                    similar_folders,
                    "move",  # 默认移动模式
                    dest_path,
                    auto_get
                )
                
                # 保存到文件
                output_manager.save_to_file(output_paths)
                
                if on_log:
                    on_log(f"生成 {len(output_paths)} 个移动路径")
                
                # 如果启用自动移动，执行移动操作
                if input_data.auto_move:
                    try:
                        from crashp import PairManager
                        pair_manager = PairManager()
                        pairs = pair_manager.build_pairs(similar_folders, auto_get, dest_path)
                        
                        # 保存配对 JSON
                        pairs_file = str(Path(dest_path) / "folder_pairs.json")
                        pair_manager.save_pairs_to_json(pairs, pairs_file)
                        
                        # 执行移动
                        result = pair_manager.move_contents(
                            pairs,
                            direction="to_target",
                            conflict="skip",
                            dry_run=False
                        )
                        moved_count = result.moved_count if hasattr(result, 'moved_count') else len(pairs)
                        
                        if on_log:
                            on_log(f"移动完成: {moved_count} 个文件夹")
                    except Exception as e:
                        if on_log:
                            on_log(f"移动操作失败: {str(e)}")
            
            if on_progress:
                on_progress(100, "处理完成")
            
            message = f"扫描完成: 找到 {len(similar_folders)} 个相似文件夹"
            if moved_count > 0:
                message += f", 移动 {moved_count} 个"
            
            return CrashuOutput(
                success=True,
                message=message,
                total_scanned=len(target_folder_names),
                similar_found=len(similar_folders),
                moved_count=moved_count,
                pairs_file=pairs_file,
                output_path=input_data.path,
                stats={
                    'scanned': len(target_folder_names),
                    'similar': len(similar_folders),
                    'moved': moved_count
                }
            )
            
        except ImportError as e:
            return CrashuOutput(
                success=False,
                message=f"crashu 模块未安装: {str(e)}"
            )
        except Exception as e:
            if on_log:
                on_log(f"执行失败: {str(e)}")
            return CrashuOutput(
                success=False,
                message=f"执行失败: {type(e).__name__}: {str(e)}"
            )
