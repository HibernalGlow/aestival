"""
crashu 适配器
文件夹名称相似度检测与批量移动工具

功能：
- 扫描源目录中的文件夹
- 与目标文件夹名称进行相似度匹配（支持别名解析）
- 生成配对结果或执行移动操作
"""

import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


class CrashuInput(AdapterInput):
    """crashu 输入参数"""
    source_paths: List[str] = Field(default_factory=list, description="源目录路径列表")
    target_path: str = Field(default="", description="目标文件夹路径（自动获取子文件夹名称）")
    target_names: List[str] = Field(default_factory=list, description="手动指定的目标文件夹名称列表")
    destination_path: str = Field(default="", description="移动目标路径")
    similarity_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="相似度阈值")
    auto_move: bool = Field(default=False, description="自动执行移动操作")
    move_direction: str = Field(default="to_target", description="移动方向: to_target 或 to_source")
    conflict_policy: str = Field(default="skip", description="冲突策略: skip, overwrite, rename")


class CrashuOutput(AdapterOutput):
    """crashu 输出结果"""
    total_scanned: int = Field(default=0, description="扫描的文件夹总数")
    similar_found: int = Field(default=0, description="找到的相似文件夹数")
    moved_count: int = Field(default=0, description="移动的文件夹数")
    pairs_file: str = Field(default="", description="生成的配对 JSON 文件路径")
    similar_folders: List[Dict[str, Any]] = Field(default_factory=list, description="相似文件夹列表")


class CrashuAdapter(BaseAdapter):
    """
    crashu 适配器
    
    功能：检测文件夹名称相似度并批量移动
    - 扫描源目录中的文件夹
    - 与目标文件夹名称进行相似度匹配（支持别名解析）
    - 生成移动路径或执行移动操作
    """
    
    name = "crashu"
    display_name = "文件夹相似度检测"
    description = "检测文件夹名称相似度并批量移动，用于整理相似命名的文件夹"
    category = "file"
    icon = "💥"
    required_packages = ["crashu"]
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
        """执行 crashu 功能"""
        
        # 验证输入
        source_paths = input_data.source_paths
        if not source_paths:
            return CrashuOutput(
                success=False,
                message="请指定至少一个源目录路径"
            )
        
        # 验证源路径
        valid_sources = []
        for sp in source_paths:
            p = Path(sp)
            if p.exists() and p.is_dir():
                valid_sources.append(str(p))
            elif on_log:
                on_log(f"⚠️ 跳过无效路径: {sp}")
        
        if not valid_sources:
            return CrashuOutput(
                success=False,
                message="没有有效的源目录路径"
            )
        
        try:
            module = self.get_module()
            FolderManager = module['FolderManager']
            OutputManager = module['OutputManager']
            
            if on_log:
                on_log(f"📂 源目录: {len(valid_sources)} 个")
            if on_progress:
                on_progress(10, "正在初始化...")
            
            # 获取目标文件夹列表
            target_folder_names = []
            target_folder_fullpaths = []
            auto_get = False
            
            if input_data.target_path and Path(input_data.target_path).exists():
                # 从目标路径自动获取文件夹名称
                auto_get = True
                target_path = Path(input_data.target_path)
                for item in target_path.iterdir():
                    if item.is_dir():
                        target_folder_names.append(item.name)
                        target_folder_fullpaths.append(str(item))
                
                if on_log:
                    on_log(f"🎯 从目标路径获取 {len(target_folder_names)} 个文件夹名称")
            elif input_data.target_names:
                # 使用手动指定的名称
                target_folder_names = input_data.target_names
                if on_log:
                    on_log(f"🎯 使用手动指定的 {len(target_folder_names)} 个目标名称")
            else:
                return CrashuOutput(
                    success=False,
                    message="请指定目标路径或目标名称列表"
                )
            
            if not target_folder_names:
                return CrashuOutput(
                    success=True,
                    message="没有找到要匹配的目标文件夹",
                    output_path=valid_sources[0] if valid_sources else ""
                )
            
            if on_progress:
                on_progress(30, f"扫描 {len(target_folder_names)} 个目标...")
            if on_log:
                on_log(f"🔍 相似度阈值: {input_data.similarity_threshold:.0%}")
            
            # 扫描相似文件夹
            similar_folders = FolderManager.scan_similar_folders(
                valid_sources,
                target_folder_names,
                target_folder_fullpaths if auto_get else None,
                input_data.similarity_threshold,
                auto_get
            )
            
            if on_log:
                on_log(f"✨ 找到 {len(similar_folders)} 个相似文件夹")
            if on_progress:
                on_progress(70, f"找到 {len(similar_folders)} 个相似项")
            
            # 处理结果
            pairs_file = ""
            moved_count = 0
            
            if similar_folders and input_data.auto_move and input_data.destination_path:
                try:
                    from crashp import PairManager
                    
                    dest_path = input_data.destination_path
                    os.makedirs(dest_path, exist_ok=True)
                    
                    pair_manager = PairManager()
                    pairs = pair_manager.build_pairs(similar_folders, auto_get, dest_path)
                    
                    # 保存配对 JSON
                    pairs_file = str(Path(dest_path) / "folder_pairs.json")
                    pair_manager.save_pairs_to_json(pairs, pairs_file)
                    
                    if on_log:
                        on_log(f"📝 保存配对文件: {pairs_file}")
                    
                    # 执行移动
                    result = pair_manager.move_contents(
                        pairs,
                        direction=input_data.move_direction,
                        conflict=input_data.conflict_policy,
                        dry_run=False
                    )
                    moved_count = result.moved_count if hasattr(result, 'moved_count') else len(pairs)
                    
                    if on_log:
                        on_log(f"📦 移动完成: {moved_count} 个文件夹")
                        
                except ImportError:
                    if on_log:
                        on_log("⚠️ crashp 模块未安装，跳过移动操作")
                except Exception as e:
                    if on_log:
                        on_log(f"⚠️ 移动操作失败: {str(e)}")
            
            if on_progress:
                on_progress(100, "处理完成")
            
            # 构建消息
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
                similar_folders=similar_folders,
                output_path=valid_sources[0] if valid_sources else "",
                stats={
                    'source_count': len(valid_sources),
                    'target_count': len(target_folder_names),
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
                on_log(f"❌ 执行失败: {str(e)}")
            return CrashuOutput(
                success=False,
                message=f"执行失败: {type(e).__name__}: {str(e)}"
            )
