"""
linedup 适配器
行去重工具 - 过滤包含特定内容的行

直接调用 linedup 源码的核心函数
"""

import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class LinedupInput(BaseModel):
    """linedup 输入参数"""
    action: str = Field(default="filter", description="操作类型: filter, filter_files")
    source_lines: List[str] = Field(default_factory=list, description="源行列表")
    filter_lines: List[str] = Field(default_factory=list, description="过滤行列表")
    source_file: str = Field(default="", description="源文件路径")
    filter_file: str = Field(default="", description="过滤文件路径")
    output_file: str = Field(default="", description="输出文件路径")


class LinedupOutput(AdapterOutput):
    """linedup 输出结果"""
    filtered_lines: List[str] = Field(default_factory=list, description="过滤后的行")
    removed_count: int = Field(default=0, description="移除的行数")
    kept_count: int = Field(default=0, description="保留的行数")


class LinedupAdapter(BaseAdapter):
    """
    linedup 适配器 - 直接调用源码函数
    
    功能：行去重工具，过滤包含特定内容的行
    """
    
    name = "linedup"
    display_name = "Linedup"
    description = "行去重工具，过滤包含特定内容的行"
    category = "text"
    icon = "📝"
    required_packages = []
    input_schema = LinedupInput
    output_schema = LinedupOutput
    
    _linedup_module = None
    
    def _import_module(self) -> Dict:
        """导入 linedup 源码模块"""
        if LinedupAdapter._linedup_module is not None:
            return {"linedup": LinedupAdapter._linedup_module}
        
        # 添加源码路径
        linedup_src = Path(__file__).parent.parent.parent.parent / "ImageAll" / "MangaClassify" / "ArtistPreview" / "src"
        if str(linedup_src) not in sys.path:
            sys.path.insert(0, str(linedup_src))
        
        try:
            from linedup import __main__ as linedup
            LinedupAdapter._linedup_module = linedup
            return {"linedup": linedup}
        except Exception as e:
            raise ImportError(f"无法导入 linedup 模块: {e}")
    
    async def execute(
        self,
        input_data: LinedupInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> LinedupOutput:
        """执行 linedup 操作"""
        action = input_data.action
        
        modules = self._import_module()
        linedup = modules["linedup"]
        
        if action == "filter":
            return await self._filter_lines(input_data, linedup, on_progress, on_log)
        elif action == "filter_files":
            return await self._filter_files(input_data, linedup, on_progress, on_log)
        else:
            return LinedupOutput(success=False, message=f"未知操作: {action}")
    
    async def _filter_lines(
        self,
        input_data: LinedupInput,
        linedup,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> LinedupOutput:
        """直接过滤行列表"""
        if not input_data.source_lines:
            return LinedupOutput(success=False, message="源内容为空")
        
        if on_progress:
            on_progress(10, "开始过滤")
        
        # 使用源码的 normalize_line 标准化
        source_set: Set[str] = {
            linedup.normalize_line(line) 
            for line in input_data.source_lines 
            if line.strip()
        }
        filter_set: Set[str] = {
            linedup.normalize_line(line) 
            for line in input_data.filter_lines 
            if line.strip()
        }
        
        if on_log:
            on_log(f"📄 源内容: {len(source_set)} 行")
            on_log(f"🔍 过滤条件: {len(filter_set)} 行")
        
        if on_progress:
            on_progress(30, "过滤中")
        
        # 调用源码的核心函数（无 console 输出）
        filtered_set, removed_count = linedup.filter_lines_core(source_set, filter_set)
        filtered_list = sorted(list(filtered_set))
        
        if on_log:
            on_log(f"✅ 保留 {len(filtered_list)} 行，移除 {removed_count} 行")
        
        if on_progress:
            on_progress(100, "过滤完成")
        
        return LinedupOutput(
            success=True,
            message=f"过滤完成，保留 {len(filtered_list)} 行，移除 {removed_count} 行",
            filtered_lines=filtered_list,
            removed_count=removed_count,
            kept_count=len(filtered_list),
            data={
                "filtered_lines": filtered_list,
                "removed_count": removed_count,
                "kept_count": len(filtered_list)
            }
        )
    
    async def _filter_files(
        self,
        input_data: LinedupInput,
        linedup,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> LinedupOutput:
        """从文件过滤"""
        source_path = Path(input_data.source_file)
        filter_path = Path(input_data.filter_file)
        
        if not source_path.exists():
            return LinedupOutput(success=False, message=f"源文件不存在: {input_data.source_file}")
        
        if not filter_path.exists():
            return LinedupOutput(success=False, message=f"过滤文件不存在: {input_data.filter_file}")
        
        if on_progress:
            on_progress(10, "读取文件")
        
        if on_log:
            on_log(f"📄 读取源文件: {source_path}")
            on_log(f"🔍 读取过滤文件: {filter_path}")
        
        # 调用源码的核心函数（无 console 输出）
        source_set = linedup.read_lines_core(source_path)
        filter_set = linedup.read_lines_core(filter_path)
        
        if on_log:
            on_log(f"📄 源文件: {len(source_set)} 行")
            on_log(f"🔍 过滤条件: {len(filter_set)} 行")
        
        if on_progress:
            on_progress(40, "过滤中")
        
        # 调用源码的核心函数
        filtered_set, removed_count = linedup.filter_lines_core(source_set, filter_set)
        filtered_list = sorted(list(filtered_set))
        
        if on_log:
            on_log(f"✅ 保留 {len(filtered_list)} 行，移除 {removed_count} 行")
        
        # 写入输出文件
        if input_data.output_file:
            output_path = Path(input_data.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                for line in filtered_list:
                    f.write(f"{line}\n")
            if on_log:
                on_log(f"💾 已保存到: {output_path}")
        
        if on_progress:
            on_progress(100, "过滤完成")
        
        return LinedupOutput(
            success=True,
            message=f"过滤完成，保留 {len(filtered_list)} 行，移除 {removed_count} 行",
            filtered_lines=filtered_list,
            removed_count=removed_count,
            kept_count=len(filtered_list),
            data={
                "filtered_lines": filtered_list,
                "removed_count": removed_count,
                "kept_count": len(filtered_list),
                "output_file": input_data.output_file or None
            }
        )
