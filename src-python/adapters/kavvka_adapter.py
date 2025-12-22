"""
kavvka 适配器
Czkawka 辅助工具 - 处理图片文件夹并生成路径

直接调用 kavvka 源码包的核心函数
"""

import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class KavvkaInput(BaseModel):
    """kavvka 输入参数"""
    action: str = Field(default="process", description="操作类型: process, scan")
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
    kavvka 适配器 - 直接调用源码包
    
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
    
    _kavvka_module = None
    
    def _import_module(self) -> Dict:
        """导入 kavvka 源码模块"""
        if KavvkaAdapter._kavvka_module is not None:
            return {"kavvka": KavvkaAdapter._kavvka_module}
        
        # 添加源码路径
        kavvka_src = Path(__file__).parent.parent.parent.parent / "ImageAll" / "Kavvka" / "src"
        if str(kavvka_src) not in sys.path:
            sys.path.insert(0, str(kavvka_src))
        
        try:
            # 导入源码模块（避免执行 CLI 初始化代码）
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "kavvka_main", 
                kavvka_src / "kavvka" / "__main__.py"
            )
            kavvka = importlib.util.module_from_spec(spec)
            
            # 临时禁用 parse_args 避免命令行解析
            import argparse
            original_parse = argparse.ArgumentParser.parse_args
            argparse.ArgumentParser.parse_args = lambda self, args=None, namespace=None: argparse.Namespace(
                config=None, workers=2, force_update=False
            )
            
            try:
                spec.loader.exec_module(kavvka)
            finally:
                argparse.ArgumentParser.parse_args = original_parse
            
            KavvkaAdapter._kavvka_module = kavvka
            return {"kavvka": kavvka}
        except Exception as e:
            raise ImportError(f"无法导入 kavvka 模块: {e}")
    
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
        
        modules = self._import_module()
        kavvka = modules["kavvka"]
        
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
            
            if not path.is_dir():
                if on_log:
                    on_log(f"❌ 不是目录: {path}")
                continue
            
            if on_log:
                on_log(f"📁 处理: {path.name}")
            
            # 使用源码函数创建比较文件夹（在同级目录）
            compare_folder = path.parent / "#compare"
            compare_folder.mkdir(exist_ok=True)
            
            if on_log:
                on_log(f"📂 比较文件夹: {compare_folder}")
            
            # 获取同级文件夹（排除自身、#compare、画师文件夹）
            siblings = []
            for entry in path.parent.iterdir():
                if (entry.is_dir() and 
                    entry.resolve() != path.resolve() and 
                    entry.name != "#compare" and 
                    not ('[' in entry.name and ']' in entry.name)):
                    siblings.append(entry)
            
            # 移动同级文件夹
            moved = []
            if siblings:
                if on_log:
                    on_log(f"📦 发现 {len(siblings)} 个同级文件夹")
                
                move_result = kavvka.move_folders_to_compare(
                    siblings, path, compare_folder, force=True
                )
                moved = move_result.get("moved_folders", [])
                
                for m in moved:
                    if on_log:
                        on_log(f"✅ 移动: {Path(m.get('source', '')).name} -> #compare")
            
            # 使用源码函数生成路径
            paths_data = kavvka.generate_czkawka_paths(path, compare_folder)
            combined_path = paths_data["combined_path"]
            all_combined_paths.append(combined_path)
            
            results.append({
                "path": str(path),
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
        
        modules = self._import_module()
        kavvka = modules["kavvka"]
        
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
            
            # 使用源码的扫描函数
            found = kavvka.scan_for_keywords(root_path, keywords, max_depth)
            
            for folder_path in found:
                matched_paths.append(str(folder_path))
                results.append({
                    "path": str(folder_path),
                    "name": folder_path.name,
                    "root": str(root_path)
                })
                if on_log:
                    on_log(f"  🎯 匹配: {folder_path.name}")
        
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
