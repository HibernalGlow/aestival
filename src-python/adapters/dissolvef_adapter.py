"""
dissolvef 适配器
文件夹解散工具 - 解散嵌套/单媒体/单压缩包/直接解散文件夹

功能：
- nested: 解散嵌套的单一文件夹
- media: 解散单媒体文件夹（只有一个视频/压缩包的文件夹）
- archive: 解散单压缩包文件夹
- direct: 直接解散指定文件夹（将内容移到父目录）
"""

from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class DissolvefInput(BaseModel):
    """dissolvef 输入参数"""
    action: str = Field(default="dissolve", description="操作类型: dissolve")
    path: str = Field(..., description="要处理的文件夹路径")
    nested: bool = Field(default=True, description="解散嵌套的单一文件夹")
    media: bool = Field(default=True, description="解散单媒体文件夹")
    archive: bool = Field(default=True, description="解散单压缩包文件夹")
    direct: bool = Field(default=False, description="直接解散指定文件夹")
    preview: bool = Field(default=False, description="预览模式，不实际执行")
    exclude: Optional[str] = Field(default=None, description="排除关键词，逗号分隔")
    file_conflict: str = Field(default="auto", description="文件冲突处理: auto/skip/overwrite/rename")
    dir_conflict: str = Field(default="auto", description="目录冲突处理: auto/skip/overwrite/rename")


class DissolvefOutput(AdapterOutput):
    """dissolvef 输出结果"""
    nested_count: int = Field(default=0, description="解散的嵌套文件夹数量")
    media_count: int = Field(default=0, description="解散的单媒体文件夹数量")
    archive_count: int = Field(default=0, description="解散的单压缩包文件夹数量")
    direct_files: int = Field(default=0, description="直接解散移动的文件数")
    direct_dirs: int = Field(default=0, description="直接解散移动的目录数")


class DissolvefAdapter(BaseAdapter):
    """
    dissolvef 适配器
    
    功能：文件夹解散工具
    """
    
    name = "dissolvef"
    display_name = "文件夹解散"
    description = "解散嵌套文件夹、单媒体文件夹、单压缩包文件夹或直接解散"
    category = "file"
    icon = "📂"
    required_packages = ["dissolvef"]
    input_schema = DissolvefInput
    output_schema = DissolvefOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 dissolvef 模块"""
        from dissolvef import (
            flatten_single_subfolder,
            release_single_media_folder,
            dissolve_folder
        )
        from dissolvef.archive import release_single_archive_folder
        return {
            "flatten_single_subfolder": flatten_single_subfolder,
            "release_single_media_folder": release_single_media_folder,
            "dissolve_folder": dissolve_folder,
            "release_single_archive_folder": release_single_archive_folder
        }
    
    async def execute(
        self,
        input_data: DissolvefInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> DissolvefOutput:
        """执行文件夹解散"""
        return await self._dissolve(input_data, on_progress, on_log)
    
    async def _dissolve(
        self,
        input_data: DissolvefInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> DissolvefOutput:
        """执行解散操作"""
        path = Path(input_data.path)
        
        if not path.exists():
            return DissolvefOutput(
                success=False,
                message=f"路径不存在: {path}"
            )
        
        if not path.is_dir():
            return DissolvefOutput(
                success=False,
                message=f"路径不是文件夹: {path}"
            )
        
        # 获取模块
        try:
            mod = self.get_module()
        except ImportError as e:
            return DissolvefOutput(
                success=False,
                message=f"导入 dissolvef 失败: {e}，请确保已安装 dissolvef 包"
            )
        
        # 处理排除关键词
        exclude_keywords = []
        if input_data.exclude:
            exclude_keywords = [kw.strip() for kw in input_data.exclude.split(',') if kw.strip()]
        
        nested_count = 0
        media_count = 0
        archive_count = 0
        direct_files = 0
        direct_dirs = 0
        
        mode_prefix = "预览" if input_data.preview else ""
        
        if on_log:
            on_log(f"📂 {mode_prefix}开始处理: {path}")
        
        try:
            if input_data.direct:
                # 直接解散模式
                if on_progress:
                    on_progress(10, "直接解散文件夹...")
                if on_log:
                    on_log(f"🔄 {mode_prefix}直接解散文件夹...")
                
                success, files_count, dirs_count = mod["dissolve_folder"](
                    path,
                    file_conflict=input_data.file_conflict,
                    dir_conflict=input_data.dir_conflict,
                    preview=input_data.preview,
                    use_status=False
                )
                
                direct_files = files_count
                direct_dirs = dirs_count
                
                if on_log:
                    on_log(f"✅ {mode_prefix}移动 {files_count} 个文件, {dirs_count} 个目录")
                
            else:
                # 其他解散模式
                total_steps = sum([input_data.nested, input_data.media, input_data.archive])
                current_step = 0
                
                if input_data.media:
                    current_step += 1
                    progress_pct = int((current_step / total_steps) * 80) + 10
                    if on_progress:
                        on_progress(progress_pct, "解散单媒体文件夹...")
                    if on_log:
                        on_log(f"🎬 {mode_prefix}解散单媒体文件夹...")
                    
                    media_count = mod["release_single_media_folder"](
                        path, exclude_keywords, input_data.preview
                    )
                    
                    if on_log:
                        on_log(f"✅ {mode_prefix}处理 {media_count} 个单媒体文件夹")
                
                if input_data.nested:
                    current_step += 1
                    progress_pct = int((current_step / total_steps) * 80) + 10
                    if on_progress:
                        on_progress(progress_pct, "解散嵌套文件夹...")
                    if on_log:
                        on_log(f"📁 {mode_prefix}解散嵌套文件夹...")
                    
                    nested_count = mod["flatten_single_subfolder"](
                        path, exclude_keywords
                    )
                    
                    if on_log:
                        on_log(f"✅ {mode_prefix}处理 {nested_count} 个嵌套文件夹")
                
                if input_data.archive:
                    current_step += 1
                    progress_pct = int((current_step / total_steps) * 80) + 10
                    if on_progress:
                        on_progress(progress_pct, "解散单压缩包文件夹...")
                    if on_log:
                        on_log(f"📦 {mode_prefix}解散单压缩包文件夹...")
                    
                    archive_count = mod["release_single_archive_folder"](
                        path, exclude_keywords, input_data.preview
                    )
                    
                    if on_log:
                        on_log(f"✅ {mode_prefix}处理 {archive_count} 个单压缩包文件夹")
            
            if on_progress:
                on_progress(100, "处理完成")
            
            # 构建结果消息
            if input_data.direct:
                message = f"{mode_prefix}直接解散完成: 移动 {direct_files} 个文件, {direct_dirs} 个目录"
            else:
                parts = []
                if input_data.nested:
                    parts.append(f"嵌套 {nested_count}")
                if input_data.media:
                    parts.append(f"媒体 {media_count}")
                if input_data.archive:
                    parts.append(f"压缩包 {archive_count}")
                message = f"{mode_prefix}解散完成: {', '.join(parts)}"
            
            if on_log:
                on_log(f"📊 {message}")
            
            return DissolvefOutput(
                success=True,
                message=message,
                nested_count=nested_count,
                media_count=media_count,
                archive_count=archive_count,
                direct_files=direct_files,
                direct_dirs=direct_dirs,
                data={
                    'nested_count': nested_count,
                    'media_count': media_count,
                    'archive_count': archive_count,
                    'direct_files': direct_files,
                    'direct_dirs': direct_dirs
                }
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 处理失败: {e}")
            return DissolvefOutput(
                success=False,
                message=f"处理失败: {e}"
            )
