"""
kavvka 适配器
Czkawka 辅助工具 - 处理图片文件夹并生成路径

功能：
- 查找画师文件夹（包含[]标记的文件夹）
- 移动同级文件夹到 #compare 文件夹
- 生成 Czkawka 路径字符串
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class KavvkaInput(BaseModel):
    """kavvka 输入参数"""
    action: str = Field(default="process", description="操作类型: process, find_artist, scan")
    paths: List[str] = Field(default_factory=list, description="源路径列表")
    force: bool = Field(default=False, description="强制移动，不询问确认")
    keywords: List[str] = Field(default_factory=list, description="扫描关键词列表")
    scan_depth: int = Field(default=3, description="扫描深度")


class KavvkaOutput(AdapterOutput):
    """kavvka 输出结果"""
    all_combined_paths: List[str] = Field(default_factory=list, description="所有合并路径")
    results: List[Dict] = Field(default_factory=list, description="处理结果列表")


class KavvkaAdapter(BaseAdapter):
    """
    kavvka 适配器
    
    功能：Czkawka 辅助工具
    """
    
    name = "kavvka"
    display_name = "Kavvka"
    description = "Czkawka 辅助工具，处理图片文件夹并生成路径"
    category = "image"
    icon = "🖼️"
    required_packages = []
    input_schema = KavvkaInput
    output_schema = KavvkaOutput
    
    def _import_module(self) -> Dict:
        """无需导入外部模块"""
        return {}
    
    def _is_artist_folder(self, path: Path) -> bool:
        """判断是否为画师文件夹（包含[]标记）- 仅用于过滤同级文件夹"""
        return '[' in path.name and ']' in path.name
    
    def _get_target_folder(self, path: Path) -> Optional[Path]:
        """
        获取目标文件夹（用于创建 #compare）
        
        直接使用输入路径作为目标文件夹，不再强制查找 [] 标记的文件夹
        """
        # 如果是压缩包，使用其所在目录
        if path.is_file() and path.suffix.lower() in ['.zip', '.7z', '.rar']:
            return path.parent
        
        # 如果是目录，直接使用
        if path.is_dir():
            return path
        
        return None
    
    def _get_siblings_to_move(self, path: Path, target_folder: Path) -> List[Path]:
        """获取需要移动的同级文件夹"""
        siblings = []
        parent_dir = target_folder.parent
        
        if not parent_dir.is_dir():
            return siblings
        
        for entry in parent_dir.iterdir():
            if (entry.is_dir() and 
                entry.resolve() != target_folder.resolve() and 
                entry.name != "#compare" and 
                not self._is_artist_folder(entry)):  # 跳过画师文件夹
                siblings.append(entry)
        
        return siblings
    
    def _create_compare_folder(self, artist_folder: Path) -> Path:
        """创建比较文件夹"""
        compare_folder = artist_folder / "#compare"
        compare_folder.mkdir(exist_ok=True)
        return compare_folder
    
    def _move_folders(
        self, 
        folders: List[Path], 
        compare_folder: Path,
        on_log: Optional[Callable[[str], None]] = None
    ) -> List[Dict]:
        """移动文件夹到比较文件夹"""
        moved = []
        
        for folder in folders:
            try:
                target = compare_folder / folder.name
                
                # 如果目标已存在，添加时间戳
                if target.exists():
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    target = compare_folder / f"{folder.name}_{timestamp}"
                
                shutil.move(str(folder), str(target))
                moved.append({
                    "source": str(folder),
                    "target": str(target),
                    "success": True
                })
                if on_log:
                    on_log(f"✅ 移动: {folder.name} -> #compare")
            except Exception as e:
                moved.append({
                    "source": str(folder),
                    "error": str(e),
                    "success": False
                })
                if on_log:
                    on_log(f"❌ 移动失败 {folder.name}: {e}")
        
        return moved
    
    async def execute(
        self,
        input_data: KavvkaInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> KavvkaOutput:
        """执行 kavvka 操作"""
        action = input_data.action
        
        if action == "process":
            return await self._process(input_data, on_progress, on_log)
        elif action == "find_artist":
            return await self._find_artist(input_data, on_progress, on_log)
        elif action == "scan":
            return await self._scan_keywords(input_data, on_progress, on_log)
        else:
            return KavvkaOutput(
                success=False,
                message=f"未知操作: {action}"
            )
    
    async def _process(
        self,
        input_data: KavvkaInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> KavvkaOutput:
        """处理路径，移动文件夹并生成 Czkawka 路径"""
        if not input_data.paths:
            return KavvkaOutput(success=False, message="请提供路径")
        
        all_combined_paths: List[str] = []
        results: List[Dict] = []
        success_count = 0
        total = len(input_data.paths)
        
        for i, path_str in enumerate(input_data.paths):
            path = Path(path_str)
            
            if on_progress:
                on_progress(int((i / total) * 100), f"处理 {path.name}")
            
            if not path.exists():
                if on_log:
                    on_log(f"❌ 路径不存在: {path}")
                continue
            
            # 获取目标文件夹
            target_folder = self._get_target_folder(path)
            if not target_folder:
                if on_log:
                    on_log(f"❌ 无效路径: {path}")
                continue
            
            if on_log:
                on_log(f"📁 目标文件夹: {target_folder.name}")
            
            # 创建比较文件夹
            compare_folder = self._create_compare_folder(target_folder)
            
            # 获取并移动同级文件夹
            siblings = self._get_siblings_to_move(path, target_folder)
            moved = []
            if siblings:
                if on_log:
                    on_log(f"📦 发现 {len(siblings)} 个同级文件夹")
                moved = self._move_folders(siblings, compare_folder, on_log)
            
            # 生成 Czkawka 路径
            input_path = str(path).replace('\\', '/')
            compare_path = str(compare_folder).replace('\\', '/')
            combined_path = f"{input_path};{compare_path}"
            all_combined_paths.append(combined_path)
            
            results.append({
                "path": str(path),
                "target_folder": str(target_folder),
                "compare_folder": str(compare_folder),
                "moved_folders": moved,
                "combined_path": combined_path
            })
            
            success_count += 1
            if on_log:
                on_log(f"✅ 路径: {combined_path}")
        
        if on_progress:
            on_progress(100, "处理完成")
        
        return KavvkaOutput(
            success=success_count > 0,
            message=f"处理完成，成功 {success_count}/{total}",
            all_combined_paths=all_combined_paths,
            results=results,
            data={"all_combined_paths": all_combined_paths, "results": results}
        )
    
    async def _find_artist(
        self,
        input_data: KavvkaInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> KavvkaOutput:
        """仅查找目标文件夹，不移动"""
        if not input_data.paths:
            return KavvkaOutput(success=False, message="请提供路径")
        
        results: List[Dict] = []
        
        for path_str in input_data.paths:
            path = Path(path_str)
            if not path.exists():
                continue
            
            target_folder = self._get_target_folder(path)
            if target_folder:
                results.append({
                    "path": str(path),
                    "target_folder": str(target_folder)
                })
                if on_log:
                    on_log(f"✅ {path.name} -> {target_folder.name}")
        
        return KavvkaOutput(
            success=len(results) > 0,
            message=f"找到 {len(results)} 个目标文件夹",
            results=results,
            data={"results": results}
        )

    async def _scan_keywords(
        self,
        input_data: KavvkaInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> KavvkaOutput:
        """扫描包含特定关键词的文件夹"""
        if not input_data.paths:
            return KavvkaOutput(success=False, message="请提供扫描路径")
        
        if not input_data.keywords:
            return KavvkaOutput(success=False, message="请提供关键词")
        
        results: List[Dict] = []
        matched_paths: List[str] = []
        
        keywords = input_data.keywords
        max_depth = input_data.scan_depth
        
        if on_log:
            on_log(f"🔍 扫描关键词: {', '.join(keywords)}")
            on_log(f"📂 扫描深度: {max_depth}")
        
        total = len(input_data.paths)
        
        for i, path_str in enumerate(input_data.paths):
            root_path = Path(path_str)
            
            if on_progress:
                on_progress(int((i / total) * 50), f"扫描 {root_path.name}")
            
            if not root_path.exists() or not root_path.is_dir():
                if on_log:
                    on_log(f"❌ 路径无效: {path_str}")
                continue
            
            if on_log:
                on_log(f"📁 扫描目录: {root_path}")
            
            # 递归扫描
            found_in_path = []
            self._scan_directory(root_path, keywords, max_depth, 0, found_in_path, on_log)
            
            for folder_path in found_in_path:
                matched_paths.append(str(folder_path))
                results.append({
                    "path": str(folder_path),
                    "name": folder_path.name,
                    "root": str(root_path)
                })
        
        if on_progress:
            on_progress(100, "扫描完成")
        
        if on_log:
            on_log(f"✅ 找到 {len(matched_paths)} 个匹配文件夹")
        
        return KavvkaOutput(
            success=len(matched_paths) > 0,
            message=f"扫描完成，找到 {len(matched_paths)} 个匹配文件夹",
            all_combined_paths=matched_paths,
            results=results,
            data={"matched_paths": matched_paths, "results": results}
        )
    
    def _scan_directory(
        self,
        path: Path,
        keywords: List[str],
        max_depth: int,
        current_depth: int,
        found: List[Path],
        on_log: Optional[Callable[[str], None]] = None
    ) -> None:
        """递归扫描目录查找关键词"""
        if current_depth > max_depth:
            return
        
        try:
            for entry in path.iterdir():
                if not entry.is_dir():
                    continue
                
                # 跳过隐藏文件夹和特殊文件夹
                if entry.name.startswith('.') or entry.name.startswith('#'):
                    continue
                
                # 检查是否匹配关键词
                folder_name = entry.name.lower()
                for keyword in keywords:
                    if keyword.lower() in folder_name:
                        found.append(entry)
                        if on_log:
                            on_log(f"  🎯 匹配: {entry.name} (关键词: {keyword})")
                        break
                
                # 继续递归
                self._scan_directory(entry, keywords, max_depth, current_depth + 1, found, on_log)
        except PermissionError:
            pass  # 忽略权限错误
        except Exception as e:
            if on_log:
                on_log(f"  ⚠️ 扫描错误: {e}")
