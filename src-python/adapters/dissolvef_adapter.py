"""
dissolvef 适配器
文件夹解散工具 - 解散嵌套/单媒体/单压缩包/直接解散文件夹

功能：
- nested: 解散嵌套的单一文件夹（支持相似度限制）
- media: 解散单媒体文件夹
- archive: 解散单压缩包文件夹（支持相似度限制）
- direct: 直接解散指定文件夹
- undo: 撤销操作
"""

import json
import os
import shutil
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


def calculate_similarity(str1: str, str2: str) -> float:
    """计算两个字符串的相似度 (0.0 - 1.0)"""
    if not str1 or not str2:
        return 0.0
    # 移除扩展名进行比较
    name1 = Path(str1).stem if '.' in str1 else str1
    name2 = Path(str2).stem if '.' in str2 else str2
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()


class DissolveOperation(BaseModel):
    """单个解散操作记录"""
    type: str  # 'move' | 'delete_dir'
    src: str
    dst: Optional[str] = None
    timestamp: str


class DissolveUndoRecord(BaseModel):
    """撤销记录"""
    id: str
    timestamp: str
    mode: str  # 'nested' | 'archive' | 'media' | 'direct'
    path: str
    operations: List[DissolveOperation]
    count: int


class DissolvefInput(BaseModel):
    """dissolvef 输入参数"""
    action: str = Field(default="dissolve", description="操作类型: dissolve, undo, list_undo")
    path: str = Field(default="", description="要处理的文件夹路径")
    nested: bool = Field(default=True, description="解散嵌套的单一文件夹")
    media: bool = Field(default=True, description="解散单媒体文件夹")
    archive: bool = Field(default=True, description="解散单压缩包文件夹")
    direct: bool = Field(default=False, description="直接解散指定文件夹")
    preview: bool = Field(default=False, description="预览模式，不实际执行")
    exclude: Optional[str] = Field(default=None, description="排除关键词，逗号分隔")
    file_conflict: str = Field(default="auto", description="文件冲突处理: auto/skip/overwrite/rename")
    dir_conflict: str = Field(default="auto", description="目录冲突处理: auto/skip/overwrite/rename")
    # 相似度限制
    similarity_threshold: float = Field(default=0.6, description="相似度阈值 (0.0-1.0)，只有超过此值才解散")
    enable_similarity: bool = Field(default=True, description="是否启用相似度检测")
    # 撤销参数
    undo_id: str = Field(default="", description="要撤销的操作 ID")


class DissolvefOutput(AdapterOutput):
    """dissolvef 输出结果"""
    nested_count: int = Field(default=0, description="解散的嵌套文件夹数量")
    media_count: int = Field(default=0, description="解散的单媒体文件夹数量")
    archive_count: int = Field(default=0, description="解散的单压缩包文件夹数量")
    direct_files: int = Field(default=0, description="直接解散移动的文件数")
    direct_dirs: int = Field(default=0, description="直接解散移动的目录数")
    skipped_count: int = Field(default=0, description="因相似度不足跳过的数量")
    operation_id: str = Field(default="", description="操作 ID（用于撤销）")
    undo_records: List[Dict] = Field(default_factory=list, description="撤销记录列表")


class DissolvefAdapter(BaseAdapter):
    """
    dissolvef 适配器
    
    功能：文件夹解散工具，支持相似度限制和撤销
    """
    
    name = "dissolvef"
    display_name = "文件夹解散"
    description = "解散嵌套文件夹、单媒体文件夹、单压缩包文件夹或直接解散，支持相似度限制和撤销"
    category = "file"
    icon = "📂"
    required_packages = ["dissolvef"]
    input_schema = DissolvefInput
    output_schema = DissolvefOutput
    
    # 撤销记录存储路径
    _undo_dir: Path = Path.home() / ".dissolvef" / "undo"
    
    def __init__(self):
        super().__init__()
        self._undo_dir.mkdir(parents=True, exist_ok=True)
    
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
        action = input_data.action.lower()
        
        if action == "undo":
            return await self._undo(input_data, on_progress, on_log)
        elif action == "list_undo":
            return await self._list_undo(on_log)
        else:
            return await self._dissolve(input_data, on_progress, on_log)
    
    def _save_undo_record(self, record: DissolveUndoRecord):
        """保存撤销记录"""
        file_path = self._undo_dir / f"{record.id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(record.model_dump_json(indent=2))
    
    def _load_undo_records(self) -> List[DissolveUndoRecord]:
        """加载所有撤销记录"""
        records = []
        for file_path in self._undo_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    records.append(DissolveUndoRecord(**data))
            except Exception:
                pass
        # 按时间倒序排列
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:20]  # 只保留最近20条
    
    def _delete_undo_record(self, undo_id: str):
        """删除撤销记录"""
        file_path = self._undo_dir / f"{undo_id}.json"
        if file_path.exists():
            file_path.unlink()
    
    async def _list_undo(self, on_log: Optional[Callable[[str], None]] = None) -> DissolvefOutput:
        """列出撤销记录"""
        records = self._load_undo_records()
        if on_log:
            on_log(f"📋 找到 {len(records)} 条撤销记录")
        
        return DissolvefOutput(
            success=True,
            message=f"找到 {len(records)} 条撤销记录",
            undo_records=[{
                'id': r.id,
                'timestamp': r.timestamp,
                'mode': r.mode,
                'path': r.path,
                'count': r.count
            } for r in records]
        )
    
    async def _undo(
        self,
        input_data: DissolvefInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> DissolvefOutput:
        """撤销操作"""
        undo_id = input_data.undo_id
        if not undo_id:
            # 获取最新的撤销记录
            records = self._load_undo_records()
            if not records:
                return DissolvefOutput(success=False, message="没有可撤销的操作")
            undo_id = records[0].id
        
        file_path = self._undo_dir / f"{undo_id}.json"
        if not file_path.exists():
            return DissolvefOutput(success=False, message=f"撤销记录不存在: {undo_id}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                record = DissolveUndoRecord(**json.load(f))
        except Exception as e:
            return DissolvefOutput(success=False, message=f"读取撤销记录失败: {e}")
        
        if on_log:
            on_log(f"🔄 开始撤销操作: {record.mode} ({record.count} 项)")
        
        success_count = 0
        failed_count = 0
        
        # 逆序执行撤销操作
        for i, op in enumerate(reversed(record.operations)):
            if on_progress:
                progress = int((i + 1) / len(record.operations) * 100)
                on_progress(progress, f"撤销 {i + 1}/{len(record.operations)}")
            
            try:
                if op.type == 'move' and op.dst:
                    # 移动回原位置
                    dst_path = Path(op.dst)
                    src_path = Path(op.src)
                    if dst_path.exists():
                        # 确保源目录存在
                        src_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(dst_path), str(src_path))
                        success_count += 1
                        if on_log:
                            on_log(f"  ↩️ {dst_path.name} -> {src_path.parent.name}/")
                    else:
                        failed_count += 1
                        if on_log:
                            on_log(f"  ⚠️ 文件不存在: {dst_path}")
                elif op.type == 'delete_dir':
                    # 重新创建目录
                    dir_path = Path(op.src)
                    dir_path.mkdir(parents=True, exist_ok=True)
                    success_count += 1
            except Exception as e:
                failed_count += 1
                if on_log:
                    on_log(f"  ❌ 撤销失败: {e}")
        
        # 删除撤销记录
        self._delete_undo_record(undo_id)
        
        if on_log:
            on_log(f"✅ 撤销完成: {success_count} 成功, {failed_count} 失败")
        
        return DissolvefOutput(
            success=True,
            message=f"撤销完成: {success_count} 成功, {failed_count} 失败",
            data={'success_count': success_count, 'failed_count': failed_count}
        )
    
    async def _dissolve(
        self,
        input_data: DissolvefInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> DissolvefOutput:
        """执行解散操作"""
        path = Path(input_data.path)
        
        if not path.exists():
            return DissolvefOutput(success=False, message=f"路径不存在: {path}")
        
        if not path.is_dir():
            return DissolvefOutput(success=False, message=f"路径不是文件夹: {path}")
        
        # 处理排除关键词
        exclude_keywords = []
        if input_data.exclude:
            exclude_keywords = [kw.strip() for kw in input_data.exclude.split(',') if kw.strip()]
        
        nested_count = 0
        media_count = 0
        archive_count = 0
        direct_files = 0
        direct_dirs = 0
        skipped_count = 0
        
        mode_prefix = "预览" if input_data.preview else ""
        operations: List[DissolveOperation] = []
        
        if on_log:
            on_log(f"📂 {mode_prefix}开始处理: {path}")
            if input_data.enable_similarity:
                on_log(f"📊 相似度阈值: {input_data.similarity_threshold:.0%}")
        
        try:
            if input_data.direct:
                # 直接解散模式（使用原有逻辑）
                try:
                    mod = self.get_module()
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
                except ImportError as e:
                    return DissolvefOutput(success=False, message=f"导入 dissolvef 失败: {e}")
                
            else:
                # 其他解散模式（带相似度检测）
                total_steps = sum([input_data.nested, input_data.media, input_data.archive])
                current_step = 0
                
                if input_data.media:
                    current_step += 1
                    progress_pct = int((current_step / total_steps) * 80) + 10
                    if on_progress:
                        on_progress(progress_pct, "解散单媒体文件夹...")
                    if on_log:
                        on_log(f"🎬 {mode_prefix}解散单媒体文件夹...")
                    
                    try:
                        mod = self.get_module()
                        media_count = mod["release_single_media_folder"](
                            path, exclude_keywords, input_data.preview
                        )
                    except ImportError:
                        pass
                    
                    if on_log:
                        on_log(f"✅ {mode_prefix}处理 {media_count} 个单媒体文件夹")
                
                if input_data.nested:
                    current_step += 1
                    progress_pct = int((current_step / total_steps) * 80) + 10
                    if on_progress:
                        on_progress(progress_pct, "解散嵌套文件夹...")
                    if on_log:
                        on_log(f"📁 {mode_prefix}解散嵌套文件夹...")
                    
                    # 使用带相似度检测的嵌套解散
                    count, skipped, ops = await self._dissolve_nested_with_similarity(
                        path, exclude_keywords, input_data.preview,
                        input_data.similarity_threshold if input_data.enable_similarity else 0.0,
                        on_log
                    )
                    nested_count = count
                    skipped_count += skipped
                    operations.extend(ops)
                    
                    if on_log:
                        msg = f"✅ {mode_prefix}处理 {nested_count} 个嵌套文件夹"
                        if skipped > 0:
                            msg += f"，跳过 {skipped} 个（相似度不足）"
                        on_log(msg)
                
                if input_data.archive:
                    current_step += 1
                    progress_pct = int((current_step / total_steps) * 80) + 10
                    if on_progress:
                        on_progress(progress_pct, "解散单压缩包文件夹...")
                    if on_log:
                        on_log(f"📦 {mode_prefix}解散单压缩包文件夹...")
                    
                    # 使用带相似度检测的压缩包解散
                    count, skipped, ops = await self._dissolve_archive_with_similarity(
                        path, exclude_keywords, input_data.preview,
                        input_data.similarity_threshold if input_data.enable_similarity else 0.0,
                        on_log
                    )
                    archive_count = count
                    skipped_count += skipped
                    operations.extend(ops)
                    
                    if on_log:
                        msg = f"✅ {mode_prefix}处理 {archive_count} 个单压缩包文件夹"
                        if skipped > 0:
                            msg += f"，跳过 {skipped} 个（相似度不足）"
                        on_log(msg)
            
            if on_progress:
                on_progress(100, "处理完成")
            
            # 保存撤销记录（非预览模式且有操作）
            operation_id = ""
            if not input_data.preview and operations:
                operation_id = f"dissolve-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                mode = "nested" if input_data.nested else ("archive" if input_data.archive else "media")
                record = DissolveUndoRecord(
                    id=operation_id,
                    timestamp=datetime.now().isoformat(),
                    mode=mode,
                    path=str(path),
                    operations=operations,
                    count=len(operations)
                )
                self._save_undo_record(record)
                if on_log:
                    on_log(f"🔄 撤销 ID: {operation_id}")
            
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
                if skipped_count > 0:
                    message += f"，跳过 {skipped_count}"
            
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
                skipped_count=skipped_count,
                operation_id=operation_id,
                data={
                    'nested_count': nested_count,
                    'media_count': media_count,
                    'archive_count': archive_count,
                    'direct_files': direct_files,
                    'direct_dirs': direct_dirs,
                    'skipped_count': skipped_count,
                    'operation_id': operation_id
                }
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 处理失败: {e}")
            return DissolvefOutput(success=False, message=f"处理失败: {e}")
    
    async def _dissolve_nested_with_similarity(
        self,
        path: Path,
        exclude_keywords: List[str],
        preview: bool,
        threshold: float,
        on_log: Optional[Callable[[str], None]] = None
    ) -> Tuple[int, int, List[DissolveOperation]]:
        """带相似度检测的嵌套文件夹解散"""
        processed_count = 0
        skipped_count = 0
        operations: List[DissolveOperation] = []
        
        for root, dirs, files in os.walk(path):
            root_path = Path(root)
            
            # 检查排除关键词
            if any(keyword in str(root) for keyword in exclude_keywords):
                continue
            
            # 只有一个子文件夹且没有文件
            if len(dirs) == 1 and not files:
                subfolder_name = dirs[0]
                subfolder_path = root_path / subfolder_name
                parent_name = root_path.name
                
                # 计算相似度
                similarity = calculate_similarity(parent_name, subfolder_name)
                
                if threshold > 0 and similarity < threshold:
                    skipped_count += 1
                    if on_log:
                        on_log(f"  ⏭️ 跳过: {parent_name}/{subfolder_name} (相似度 {similarity:.0%} < {threshold:.0%})")
                    continue
                
                # 找到最深层的单一子文件夹
                current_subfolder = subfolder_path
                while True:
                    sub_items = list(current_subfolder.iterdir())
                    sub_dirs = [item for item in sub_items if item.is_dir()]
                    sub_files = [item for item in sub_items if item.is_file()]
                    
                    if len(sub_dirs) == 1 and not sub_files:
                        current_subfolder = sub_dirs[0]
                    else:
                        break
                
                if on_log:
                    on_log(f"  📁 解散: {parent_name}/{subfolder_name} (相似度 {similarity:.0%})")
                
                if not preview:
                    try:
                        # 移动内容到父文件夹
                        for item in current_subfolder.iterdir():
                            dst_path = root_path / item.name
                            # 处理名称冲突
                            if dst_path.exists():
                                counter = 1
                                while dst_path.exists():
                                    new_name = f"{item.stem}_{counter}{item.suffix}" if item.suffix else f"{item.name}_{counter}"
                                    dst_path = root_path / new_name
                                    counter += 1
                            
                            shutil.move(str(item), str(dst_path))
                            operations.append(DissolveOperation(
                                type='move',
                                src=str(item),
                                dst=str(dst_path),
                                timestamp=datetime.now().isoformat()
                            ))
                        
                        # 删除空文件夹
                        if not any(current_subfolder.iterdir()):
                            shutil.rmtree(str(subfolder_path))
                            operations.append(DissolveOperation(
                                type='delete_dir',
                                src=str(subfolder_path),
                                timestamp=datetime.now().isoformat()
                            ))
                        
                        processed_count += 1
                    except Exception as e:
                        if on_log:
                            on_log(f"  ❌ 失败: {e}")
                else:
                    processed_count += 1
        
        return processed_count, skipped_count, operations
    
    async def _dissolve_archive_with_similarity(
        self,
        path: Path,
        exclude_keywords: List[str],
        preview: bool,
        threshold: float,
        on_log: Optional[Callable[[str], None]] = None
    ) -> Tuple[int, int, List[DissolveOperation]]:
        """带相似度检测的单压缩包文件夹解散"""
        ARCHIVE_FORMATS = {'.zip', '.rar', '.7z', '.cbz', '.cbr'}
        
        processed_count = 0
        skipped_count = 0
        operations: List[DissolveOperation] = []
        
        for root, dirs, files in os.walk(path, topdown=False):
            root_path = Path(root)
            
            # 检查排除关键词
            if any(keyword in str(root) for keyword in exclude_keywords):
                continue
            
            try:
                items = list(root_path.iterdir())
                file_items = [item for item in items if item.is_file()]
                dir_items = [item for item in items if item.is_dir()]
                
                # 过滤压缩包文件
                archive_files = [f for f in file_items if f.suffix.lower() in ARCHIVE_FORMATS]
                
                # 只有一个压缩包且没有其他文件和文件夹
                if len(archive_files) == 1 and len(file_items) == 1 and len(dir_items) == 0:
                    archive_file = archive_files[0]
                    folder_name = root_path.name
                    archive_name = archive_file.stem
                    
                    # 计算相似度
                    similarity = calculate_similarity(folder_name, archive_name)
                    
                    if threshold > 0 and similarity < threshold:
                        skipped_count += 1
                        if on_log:
                            on_log(f"  ⏭️ 跳过: {folder_name}/{archive_file.name} (相似度 {similarity:.0%} < {threshold:.0%})")
                        continue
                    
                    parent_dir = root_path.parent
                    target_path = parent_dir / archive_file.name
                    
                    # 处理名称冲突
                    if target_path.exists():
                        counter = 1
                        while target_path.exists():
                            new_name = f"{archive_file.stem}_{counter}{archive_file.suffix}"
                            target_path = parent_dir / new_name
                            counter += 1
                    
                    if on_log:
                        on_log(f"  📦 解散: {folder_name}/{archive_file.name} (相似度 {similarity:.0%})")
                    
                    if not preview:
                        try:
                            shutil.move(str(archive_file), str(target_path))
                            operations.append(DissolveOperation(
                                type='move',
                                src=str(archive_file),
                                dst=str(target_path),
                                timestamp=datetime.now().isoformat()
                            ))
                            
                            os.rmdir(str(root_path))
                            operations.append(DissolveOperation(
                                type='delete_dir',
                                src=str(root_path),
                                timestamp=datetime.now().isoformat()
                            ))
                            
                            processed_count += 1
                        except Exception as e:
                            if on_log:
                                on_log(f"  ❌ 失败: {e}")
                    else:
                        processed_count += 1
                        
            except Exception as e:
                if on_log:
                    on_log(f"  ❌ 处理失败: {root_path} - {e}")
        
        return processed_count, skipped_count, operations
