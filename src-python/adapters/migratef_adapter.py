"""
migratef 适配器
文件迁移工具 - 调用 migratef 包的接口

支持三种迁移模式：
1. preserve: 保持目录结构迁移
2. flat: 扁平迁移（只迁移文件，不保持目录结构）
3. direct: 直接迁移（类似mv命令，整个文件/文件夹作为单位）
"""

import io
import os
import sys
from typing import Callable, Dict, List, Optional

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


def _ensure_utf8_output():
    """确保 stdout/stderr 使用 UTF-8 编码"""
    if sys.platform == 'win32':
        os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, 
                encoding='utf-8', 
                errors='replace',
                line_buffering=True
            )
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, 
                encoding='utf-8', 
                errors='replace',
                line_buffering=True
            )


_ensure_utf8_output()


class MigrateFInput(AdapterInput):
    """migratef 输入参数"""
    path: str = Field(default="", description="源路径")
    source_paths: List[str] = Field(default_factory=list, description="源路径列表")
    target_path: str = Field(default="", description="目标目录路径")
    mode: str = Field(default="preserve", description="迁移模式: preserve/flat/direct")
    action: str = Field(default="move", description="操作类型: copy/move/undo/history")
    max_workers: int = Field(default=16, description="最大线程数")
    # 撤销相关参数
    batch_id: str = Field(default="", description="要撤销的批次 ID")
    history_limit: int = Field(default=10, description="历史记录数量限制")


class MigrateFOutput(AdapterOutput):
    """migratef 输出结果"""
    migrated_count: int = Field(default=0, description="成功迁移数量")
    skipped_count: int = Field(default=0, description="跳过数量")
    error_count: int = Field(default=0, description="失败数量")
    total_count: int = Field(default=0, description="总数量")
    # 撤销相关
    operation_id: str = Field(default="", description="操作 ID（用于撤销）")
    success_count: int = Field(default=0, description="撤销成功数量")
    failed_count: int = Field(default=0, description="撤销失败数量")
    history: List[Dict] = Field(default_factory=list, description="历史记录")


class MigrateFAdapter(BaseAdapter):
    """migratef 适配器 - 调用 migratef 包"""
    
    name = "migratef"
    display_name = "文件迁移"
    description = "保持目录结构迁移文件和文件夹"
    category = "file"
    icon = "📁"
    required_packages = ["migratef"]
    input_schema = MigrateFInput
    output_schema = MigrateFOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 migratef 模块"""
        from migratef.core.migration_service import MigrationService
        return {
            'MigrationService': MigrationService
        }
    
    async def execute(
        self,
        input_data: MigrateFInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MigrateFOutput:
        """执行文件迁移或撤销操作"""
        action = input_data.action.lower()
        
        # 撤销操作
        if action == "undo":
            return await self._undo(input_data, on_progress, on_log)
        
        # 获取历史记录
        if action == "history":
            return await self._get_history(input_data, on_progress, on_log)
        
        # 迁移操作 (move/copy)
        return await self._migrate(input_data, on_progress, on_log)
    
    async def _undo(
        self,
        input_data: MigrateFInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MigrateFOutput:
        """撤销迁移操作"""
        try:
            if on_log:
                on_log("开始撤销操作...")
            if on_progress:
                on_progress(30, "执行撤销...")
            
            module = self._import_module()
            MigrationService = module['MigrationService']
            service = MigrationService()
            
            result = service.undo(input_data.batch_id)
            
            if on_progress:
                on_progress(100, "撤销完成")
            
            success = result['success_count']
            failed = result['failed_count']
            
            if on_log:
                on_log(f"✅ 撤销成功: {success}, 失败: {failed}")
                if result.get('failed_items'):
                    for item in result['failed_items'][:5]:
                        if isinstance(item, (list, tuple)) and len(item) >= 3:
                            src, tgt, err = item[0], item[1], item[2]
                            on_log(f"  ❌ {err}")
                        else:
                            on_log(f"  ❌ {item}")
            
            return MigrateFOutput(
                success=True,
                message=f"撤销完成: {success} 成功, {failed} 失败",
                success_count=success,
                failed_count=failed,
                data={
                    'success_count': success,
                    'failed_count': failed,
                    'failed_items': result.get('failed_items', [])
                }
            )
            
        except ImportError as e:
            return MigrateFOutput(success=False, message=f"migratef 模块未安装: {e}")
        except Exception as e:
            if on_log:
                on_log(f"❌ 撤销失败: {e}")
            return MigrateFOutput(success=False, message=f"撤销失败: {type(e).__name__}: {e}")
    
    async def _get_history(
        self,
        input_data: MigrateFInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MigrateFOutput:
        """获取撤销历史"""
        try:
            module = self._import_module()
            MigrationService = module['MigrationService']
            service = MigrationService()
            
            history = service.get_undo_history(input_data.history_limit or 10)
            
            if on_log:
                on_log(f"获取到 {len(history)} 条历史记录")
            
            return MigrateFOutput(
                success=True,
                message=f"获取到 {len(history)} 条历史记录",
                history=history,
                data={'history': history}
            )
            
        except ImportError as e:
            return MigrateFOutput(success=False, message=f"migratef 模块未安装: {e}")
        except Exception as e:
            if on_log:
                on_log(f"❌ 获取历史失败: {e}")
            return MigrateFOutput(success=False, message=f"获取历史失败: {type(e).__name__}: {e}")
    
    async def _migrate(
        self,
        input_data: MigrateFInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MigrateFOutput:
        """执行文件迁移"""
        
        # 收集源路径，去除引号
        source_paths = list(input_data.source_paths) if input_data.source_paths else []
        if input_data.path:
            path = input_data.path.strip().strip('"')
            if path not in source_paths:
                source_paths.append(path)
        
        # 处理所有路径的引号
        source_paths = [p.strip().strip('"') for p in source_paths]
        
        if not source_paths:
            return MigrateFOutput(success=False, message="未指定源路径")
        
        # 目标路径也去除引号
        target_path = input_data.target_path.strip().strip('"') if input_data.target_path else ""
        if not target_path:
            return MigrateFOutput(success=False, message="未指定目标路径")
        
        # 验证源路径存在
        from pathlib import Path
        valid_paths = []
        for p in source_paths:
            if Path(p).exists():
                valid_paths.append(p)
            elif on_log:
                on_log(f"跳过不存在: {p}")
        
        if not valid_paths:
            return MigrateFOutput(success=False, message="没有有效的源路径")
        
        mode = input_data.mode.lower()
        action = input_data.action.lower()
        action_text = "移动" if action == "move" else "复制"
        mode_text = {"preserve": "保持结构", "flat": "扁平", "direct": "直接"}.get(mode, mode)
        
        if on_log:
            on_log(f"目标: {target_path}")
            on_log(f"模式: {mode_text} ({action_text})")
            on_log(f"源路径: {len(valid_paths)} 个")
        
        if on_progress:
            on_progress(10, "正在迁移...")
        
        try:
            # 调用 migratef 的 MigrationService
            module = self.get_module()
            MigrationService = module['MigrationService']
            
            service = MigrationService()
            result = service.execute_migration(
                source_paths=valid_paths,
                target_dir=target_path,
                migration_mode=mode,
                action_type=action,
                max_workers=input_data.max_workers or 16
            )
            
            if on_progress:
                on_progress(100, "完成")
            
            migrated = result.get('migrated', 0)
            skipped = result.get('skipped', 0)
            error = result.get('error', 0)
            total = migrated + skipped + error
            operation_id = result.get('operation_id', '')
            
            if on_log:
                on_log(f"{action_text}完成: {migrated} 成功")
                if skipped > 0:
                    on_log(f"跳过: {skipped}")
                if error > 0:
                    on_log(f"错误: {error}")
                if operation_id:
                    on_log(f"🔄 撤销 ID: {operation_id}")
            
            return MigrateFOutput(
                success=True,
                message=f"{action_text}完成: {migrated} 成功, {skipped} 跳过, {error} 失败",
                migrated_count=migrated,
                skipped_count=skipped,
                error_count=error,
                total_count=total,
                operation_id=operation_id,
                output_path=target_path,
                data={
                    'migrated_count': migrated,
                    'skipped_count': skipped,
                    'error_count': error,
                    'total_count': total,
                    'operation_id': operation_id
                }
            )
            
        except ImportError as e:
            return MigrateFOutput(
                success=False,
                message=f"migratef 模块未安装: {e}"
            )
        except Exception as e:
            import traceback
            if on_log:
                on_log(f"迁移失败: {e}")
                on_log(traceback.format_exc())
            return MigrateFOutput(
                success=False,
                message=f"迁移失败: {type(e).__name__}: {e}"
            )
