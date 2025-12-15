"""
trename 适配器
文件批量重命名工具 - 支持扫描、重命名和撤销

功能：
1. scan: 扫描目录生成 JSON 结构
2. rename: 根据 JSON 执行批量重命名
3. undo: 撤销重命名操作
"""

from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


class TrenameInput(AdapterInput):
    """trename 输入参数"""
    # 操作类型
    action: str = Field(default="scan", description="操作类型: scan, rename, undo")
    # scan 参数
    paths: List[str] = Field(default_factory=list, description="要扫描的目录路径列表")
    include_root: bool = Field(default=True, description="将目录本身作为根节点")
    include_hidden: bool = Field(default=False, description="包含隐藏文件")
    exclude_exts: str = Field(default=".json,.txt,.html,.htm,.md,.log", description="排除的扩展名")
    split_lines: int = Field(default=1000, description="分段行数（0=不分段）")
    compact: bool = Field(default=False, description="紧凑格式")
    # rename 参数
    json_content: str = Field(default="", description="重命名 JSON 内容")
    base_path: str = Field(default="", description="基础路径")
    dry_run: bool = Field(default=False, description="只模拟执行")
    # undo 参数
    batch_id: str = Field(default="", description="要撤销的批次 ID")


class TrenameOutput(AdapterOutput):
    """trename 输出结果"""
    json_content: str = Field(default="", description="生成的 JSON 内容")
    segments: List[str] = Field(default_factory=list, description="分段 JSON 列表")
    total_items: int = Field(default=0, description="总项目数")
    success_count: int = Field(default=0, description="成功数量")
    failed_count: int = Field(default=0, description="失败数量")
    skipped_count: int = Field(default=0, description="跳过数量")
    operation_id: str = Field(default="", description="操作 ID（用于撤销）")
    conflicts: List[str] = Field(default_factory=list, description="冲突列表")


class TrenameAdapter(BaseAdapter):
    """
    trename 适配器
    
    功能：文件批量重命名工具
    支持扫描目录生成 JSON、批量重命名、撤销操作
    """
    
    name = "trename"
    display_name = "批量重命名"
    description = "扫描目录生成 JSON，支持批量重命名和撤销"
    category = "file"
    icon = "✏️"
    input_schema = TrenameInput
    output_schema = TrenameOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 trename 模块"""
        from trename.scanner import FileScanner, split_json
        from trename.renamer import FileRenamer
        from trename.undo import UndoManager
        from trename.models import RenameJSON, count_total, count_ready, count_pending
        from trename.clipboard import ClipboardHandler
        
        return {
            'FileScanner': FileScanner,
            'split_json': split_json,
            'FileRenamer': FileRenamer,
            'UndoManager': UndoManager,
            'RenameJSON': RenameJSON,
            'count_total': count_total,
            'count_ready': count_ready,
            'count_pending': count_pending,
            'ClipboardHandler': ClipboardHandler,
        }
    
    async def execute(
        self,
        input_data: TrenameInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> TrenameOutput:
        """执行 trename 功能"""
        action = input_data.action.lower()
        
        if action == "scan":
            return await self._scan(input_data, on_progress, on_log)
        elif action == "rename":
            return await self._rename(input_data, on_progress, on_log)
        elif action == "undo":
            return await self._undo(input_data, on_progress, on_log)
        else:
            return TrenameOutput(
                success=False,
                message=f"未知操作: {action}"
            )
    
    async def _scan(
        self,
        input_data: TrenameInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> TrenameOutput:
        """扫描目录生成 JSON"""
        if not input_data.paths:
            return TrenameOutput(
                success=False,
                message="请指定要扫描的目录"
            )
        
        try:
            module = self.get_module()
            FileScanner = module['FileScanner']
            split_json = module['split_json']
            RenameJSON = module['RenameJSON']
            count_total = module['count_total']
            
            if on_log:
                on_log(f"开始扫描 {len(input_data.paths)} 个目录")
            if on_progress:
                on_progress(10, "正在初始化扫描器...")
            
            # 解析排除扩展名
            exclude_exts = set()
            if input_data.exclude_exts:
                exclude_exts = {
                    ext.strip() if ext.strip().startswith(".") else f".{ext.strip()}"
                    for ext in input_data.exclude_exts.split(",")
                    if ext.strip()
                }
            
            scanner = FileScanner(
                ignore_hidden=not input_data.include_hidden,
                exclude_exts=exclude_exts,
            )
            
            # 扫描所有目录
            rename_json = RenameJSON(root=[])
            for i, path_str in enumerate(input_data.paths):
                path = Path(path_str)
                if not path.exists():
                    if on_log:
                        on_log(f"⚠️ 路径不存在: {path_str}")
                    continue
                
                if on_progress:
                    progress = 10 + int(60 * (i + 1) / len(input_data.paths))
                    on_progress(progress, f"扫描: {path.name}")
                
                if input_data.include_root:
                    result = scanner.scan_as_single_dir(path)
                else:
                    result = scanner.scan(path)
                rename_json.root.extend(result.root)
                
                if on_log:
                    on_log(f"✓ 扫描: {path} ({count_total(result)} 项)")
            
            total = count_total(rename_json)
            
            if on_progress:
                on_progress(80, "生成 JSON...")
            
            # 分段处理
            segments = []
            if input_data.split_lines > 0:
                seg_list = split_json(rename_json, max_lines=input_data.split_lines)
                for seg in seg_list:
                    if input_data.compact:
                        segments.append(scanner.to_compact_json(seg))
                    else:
                        segments.append(scanner.to_json(seg))
            else:
                if input_data.compact:
                    segments.append(scanner.to_compact_json(rename_json))
                else:
                    segments.append(scanner.to_json(rename_json))
            
            if on_progress:
                on_progress(100, "扫描完成")
            
            if on_log:
                on_log(f"✅ 扫描完成，共 {total} 项，{len(segments)} 段")
            
            return TrenameOutput(
                success=True,
                message=f"扫描完成，共 {total} 项",
                json_content=segments[0] if segments else "",
                segments=segments,
                total_items=total,
                data={
                    'json_content': segments[0] if segments else "",
                    'segments': segments,
                    'total_items': total,
                    'segment_count': len(segments),
                }
            )
            
        except ImportError as e:
            return TrenameOutput(
                success=False,
                message=f"trename 模块未安装: {str(e)}"
            )
        except Exception as e:
            if on_log:
                on_log(f"❌ 扫描失败: {str(e)}")
            return TrenameOutput(
                success=False,
                message=f"扫描失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _rename(
        self,
        input_data: TrenameInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> TrenameOutput:
        """执行批量重命名"""
        if not input_data.json_content:
            return TrenameOutput(
                success=False,
                message="请提供重命名 JSON 内容"
            )
        
        try:
            module = self.get_module()
            FileRenamer = module['FileRenamer']
            UndoManager = module['UndoManager']
            RenameJSON = module['RenameJSON']
            count_total = module['count_total']
            count_ready = module['count_ready']
            
            if on_log:
                on_log("开始解析 JSON...")
            if on_progress:
                on_progress(10, "解析 JSON...")
            
            # 解析 JSON
            rename_json = RenameJSON.model_validate_json(input_data.json_content)
            
            total = count_total(rename_json)
            ready = count_ready(rename_json)
            
            if on_log:
                on_log(f"总项目: {total}, 可重命名: {ready}")
            
            if ready == 0:
                return TrenameOutput(
                    success=True,
                    message="没有可重命名的项目",
                    total_items=total,
                )
            
            if on_progress:
                on_progress(30, "执行重命名...")
            
            # 执行重命名
            base = Path(input_data.base_path) if input_data.base_path else Path.cwd()
            undo_manager = UndoManager()
            renamer = FileRenamer(undo_manager)
            
            result = renamer.rename_batch(
                rename_json, 
                base, 
                dry_run=input_data.dry_run
            )
            
            if on_progress:
                on_progress(100, "重命名完成")
            
            conflicts = [c.message for c in result.conflicts] if result.conflicts else []
            
            if on_log:
                on_log(f"✅ 成功: {result.success_count}, 失败: {result.failed_count}, 跳过: {result.skipped_count}")
                if result.operation_id:
                    on_log(f"撤销 ID: {result.operation_id}")
            
            return TrenameOutput(
                success=True,
                message=f"重命名完成: {result.success_count} 成功",
                total_items=total,
                success_count=result.success_count,
                failed_count=result.failed_count,
                skipped_count=result.skipped_count,
                operation_id=result.operation_id,
                conflicts=conflicts,
                data={
                    'success_count': result.success_count,
                    'failed_count': result.failed_count,
                    'skipped_count': result.skipped_count,
                    'operation_id': result.operation_id,
                    'conflicts': conflicts,
                }
            )
            
        except ImportError as e:
            return TrenameOutput(
                success=False,
                message=f"trename 模块未安装: {str(e)}"
            )
        except Exception as e:
            if on_log:
                on_log(f"❌ 重命名失败: {str(e)}")
            return TrenameOutput(
                success=False,
                message=f"重命名失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _undo(
        self,
        input_data: TrenameInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> TrenameOutput:
        """撤销重命名操作"""
        try:
            module = self.get_module()
            UndoManager = module['UndoManager']
            
            if on_log:
                on_log("开始撤销操作...")
            if on_progress:
                on_progress(30, "执行撤销...")
            
            undo_manager = UndoManager()
            
            if input_data.batch_id:
                result = undo_manager.undo(input_data.batch_id)
            else:
                result = undo_manager.undo_latest()
            
            if on_progress:
                on_progress(100, "撤销完成")
            
            if on_log:
                on_log(f"✅ 撤销成功: {result.success_count}, 失败: {result.failed_count}")
            
            return TrenameOutput(
                success=True,
                message=f"撤销完成: {result.success_count} 成功",
                success_count=result.success_count,
                failed_count=result.failed_count,
                data={
                    'success_count': result.success_count,
                    'failed_count': result.failed_count,
                }
            )
            
        except ImportError as e:
            return TrenameOutput(
                success=False,
                message=f"trename 模块未安装: {str(e)}"
            )
        except Exception as e:
            if on_log:
                on_log(f"❌ 撤销失败: {str(e)}")
            return TrenameOutput(
                success=False,
                message=f"撤销失败: {type(e).__name__}: {str(e)}"
            )
