"""
movea 适配器
压缩包分类移动工具 - 扫描目录并将压缩包/文件夹移动到对应的二级文件夹

直接调用 movea 源码的核心函数
"""

import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class MoveaInput(BaseModel):
    """movea 输入参数"""
    action: str = Field(default="scan", description="操作类型: scan, move, move_single")
    root_path: str = Field(default="", description="根目录路径")
    regex_patterns: List[str] = Field(default_factory=list, description="正则表达式列表")
    allow_move_to_unnumbered: bool = Field(default=False, description="允许移动到无编号文件夹")
    enable_folder_moving: bool = Field(default=True, description="启用文件夹移动")
    # 移动操作参数
    level1_name: str = Field(default="", description="一级文件夹名称")
    move_plan: Dict[str, Optional[str]] = Field(default_factory=dict, description="移动计划")


class ScanResultItem(BaseModel):
    """扫描结果项"""
    path: str = Field(description="文件夹路径")
    subfolders: List[str] = Field(default_factory=list, description="二级文件夹列表")
    archives: List[str] = Field(default_factory=list, description="压缩包列表")
    movable_folders: List[str] = Field(default_factory=list, description="可移动文件夹列表")
    warning: Optional[str] = Field(default=None, description="警告信息")


class MoveaOutput(AdapterOutput):
    """movea 输出结果"""
    scan_results: Dict[str, Any] = Field(default_factory=dict, description="扫描结果")
    total_folders: int = Field(default=0, description="一级文件夹总数")
    total_archives: int = Field(default=0, description="压缩包总数")
    total_movable_folders: int = Field(default=0, description="可移动文件夹总数")
    move_success: int = Field(default=0, description="移动成功数")
    move_failed: int = Field(default=0, description="移动失败数")


class MoveaAdapter(BaseAdapter):
    """
    movea 适配器 - 直接调用源码函数
    
    功能：压缩包分类移动工具，扫描目录并将压缩包/文件夹移动到对应的二级文件夹
    """
    
    name = "movea"
    display_name = "Movea"
    description = "压缩包分类移动工具，扫描目录并将压缩包/文件夹移动到对应的二级文件夹"
    category = "file"
    icon = "📦"
    required_packages = []
    input_schema = MoveaInput
    output_schema = MoveaOutput
    
    _scanner_module = None
    _file_ops_module = None
    _config_module = None
    
    def _import_module(self) -> Dict:
        """导入 movea 源码模块"""
        if MoveaAdapter._scanner_module is not None:
            return {
                "scanner": MoveaAdapter._scanner_module,
                "file_ops": MoveaAdapter._file_ops_module,
                "config": MoveaAdapter._config_module
            }
        
        # 添加源码路径
        movea_src = Path(__file__).parent.parent.parent.parent / "ImageAll" / "MangaClassify" / "ArtistPreview" / "src"
        if str(movea_src) not in sys.path:
            sys.path.insert(0, str(movea_src))
        
        try:
            from movea import scanner, file_ops, config
            MoveaAdapter._scanner_module = scanner
            MoveaAdapter._file_ops_module = file_ops
            MoveaAdapter._config_module = config
            return {
                "scanner": scanner,
                "file_ops": file_ops,
                "config": config
            }
        except Exception as e:
            raise ImportError(f"无法导入 movea 模块: {e}")
    
    async def execute(
        self,
        input_data: MoveaInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MoveaOutput:
        """执行 movea 操作"""
        action = input_data.action
        
        modules = self._import_module()
        
        if action == "scan":
            return await self._scan_directory(input_data, modules, on_progress, on_log)
        elif action == "move":
            return await self._execute_moves(input_data, modules, on_progress, on_log)
        elif action == "move_single":
            return await self._execute_single_move(input_data, modules, on_progress, on_log)
        elif action == "match":
            return await self._match_archive(input_data, modules, on_progress, on_log)
        else:
            return MoveaOutput(success=False, message=f"未知操作: {action}")
    
    async def _scan_directory(
        self,
        input_data: MoveaInput,
        modules: Dict,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MoveaOutput:
        """扫描目录"""
        root_path = input_data.root_path
        
        if not root_path:
            return MoveaOutput(success=False, message="请输入根路径")
        
        if on_progress:
            on_progress(10, "开始扫描目录...")
        
        if on_log:
            on_log(f"📂 扫描目录: {root_path}")
        
        try:
            # 调用源码的扫描函数（需要绕过 streamlit 依赖）
            scanner = modules["scanner"]
            config = modules["config"]
            file_ops = modules["file_ops"]
            
            import os
            import re
            
            # 直接实现扫描逻辑（避免 streamlit 依赖）
            if not os.path.exists(root_path):
                return MoveaOutput(success=False, message=f"路径不存在: {root_path}")
            
            # 加载黑名单
            blacklist = set()
            try:
                blacklist = config.load_blacklist()
            except:
                pass
            
            results = {}
            items = os.listdir(root_path)
            total_items = len(items)
            
            for idx, item in enumerate(items):
                if on_progress:
                    progress = 10 + int((idx / total_items) * 80)
                    on_progress(progress, f"扫描: {item}")
                
                level1_path = os.path.join(root_path, item)
                if not os.path.isdir(level1_path):
                    continue
                
                # 跳过黑名单
                if item in blacklist:
                    continue
                
                # 获取二级文件夹、压缩包和可移动文件夹
                subfolders = []
                archives = []
                movable_folders = []
                
                for subitem in os.listdir(level1_path):
                    subitem_path = os.path.join(level1_path, subitem)
                    if os.path.isdir(subitem_path):
                        subfolders.append(subitem)
                    elif os.path.isfile(subitem_path) and file_ops.is_archive(subitem_path):
                        archives.append(subitem)
                
                # 可移动的文件夹：不以数字开头的文件夹
                for folder in subfolders[:]:
                    if not re.match(r'^\d+[\.\)\]\s]*', folder):
                        movable_folders.append(folder)
                        subfolders.remove(folder)
                
                if (archives or movable_folders) and subfolders:
                    # 检查是否有"同人志"文件夹
                    has_doujinshi = any("同人志" in folder for folder in subfolders)
                    warning_message = None if has_doujinshi else "⚠️ 此文件夹没有'同人志'二级文件夹"
                    
                    results[item] = {
                        'path': level1_path,
                        'subfolders': sorted(subfolders),
                        'archives': archives,
                        'movable_folders': movable_folders,
                        'warning': warning_message
                    }
            
            if on_progress:
                on_progress(100, "扫描完成")
            
            total_archives = sum(len(data['archives']) for data in results.values())
            total_movable = sum(len(data.get('movable_folders', [])) for data in results.values())
            
            if on_log:
                on_log(f"✅ 扫描完成，找到 {len(results)} 个一级文件夹")
                on_log(f"📦 压缩包: {total_archives} 个")
                on_log(f"📁 可移动文件夹: {total_movable} 个")
            
            return MoveaOutput(
                success=True,
                message=f"扫描完成，找到 {len(results)} 个一级文件夹",
                scan_results=results,
                total_folders=len(results),
                total_archives=total_archives,
                total_movable_folders=total_movable,
                data={
                    "scan_results": results,
                    "total_folders": len(results),
                    "total_archives": total_archives,
                    "total_movable_folders": total_movable
                }
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 扫描失败: {e}")
            return MoveaOutput(success=False, message=f"扫描失败: {e}")
    
    async def _match_archive(
        self,
        input_data: MoveaInput,
        modules: Dict,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MoveaOutput:
        """匹配压缩包到目标文件夹"""
        scanner = modules["scanner"]
        
        # 这里可以调用 scanner.match_archive_to_folder
        # 但由于需要传入具体参数，这个功能主要在前端实现
        return MoveaOutput(success=True, message="匹配功能在前端实现")
    
    async def _execute_single_move(
        self,
        input_data: MoveaInput,
        modules: Dict,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MoveaOutput:
        """执行单个文件夹的移动"""
        import os
        import shutil
        
        level1_name = input_data.level1_name
        move_plan = input_data.move_plan
        root_path = input_data.root_path
        
        if not level1_name or not move_plan:
            return MoveaOutput(success=False, message="缺少移动参数")
        
        level1_path = os.path.join(root_path, level1_name)
        if not os.path.exists(level1_path):
            return MoveaOutput(success=False, message=f"文件夹不存在: {level1_path}")
        
        if on_progress:
            on_progress(10, f"开始移动 {level1_name}...")
        
        success_count = 0
        error_count = 0
        total_items = len([k for k, v in move_plan.items() if v is not None])
        processed = 0
        
        for item_key, target_folder in move_plan.items():
            if target_folder is None:
                continue
            
            # 检查是文件还是文件夹
            if item_key.startswith("folder_"):
                item_name = item_key[7:]  # 移除"folder_"前缀
                item_type = "文件夹"
            else:
                item_name = item_key
                item_type = "文件"
            
            source_path = os.path.join(level1_path, item_name)
            target_path = os.path.join(level1_path, target_folder, item_name)
            
            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.move(source_path, target_path)
                success_count += 1
                if on_log:
                    on_log(f"✅ {item_name} ({item_type}) -> {target_folder}")
            except Exception as e:
                error_count += 1
                if on_log:
                    on_log(f"❌ 移动失败 {item_name}: {e}")
            
            processed += 1
            if on_progress:
                progress = 10 + int((processed / total_items) * 90)
                on_progress(progress, f"移动中: {item_name}")
        
        if on_progress:
            on_progress(100, "移动完成")
        
        return MoveaOutput(
            success=True,
            message=f"移动完成，成功: {success_count}，失败: {error_count}",
            move_success=success_count,
            move_failed=error_count,
            data={
                "move_success": success_count,
                "move_failed": error_count
            }
        )
    
    async def _execute_moves(
        self,
        input_data: MoveaInput,
        modules: Dict,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MoveaOutput:
        """执行批量移动（预留接口）"""
        return MoveaOutput(success=False, message="批量移动请使用 move_single 逐个执行")
