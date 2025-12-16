"""
enginev 适配器
Wallpaper Engine 工坊管理工具 - 支持扫描、过滤、预览、批量重命名

完整流程：
1. scan: 扫描工坊目录，读取 project.json
2. filter: 按条件过滤壁纸
3. rename: 批量重命名文件夹
4. export: 导出数据
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


class EngineVInput(AdapterInput):
    """enginev 输入参数"""
    # 覆盖基类的 path 字段，设为可选
    path: str = Field(default="", description="输入路径（兼容基类）")
    # 操作类型
    action: str = Field(default="scan", description="操作类型: scan, filter, rename, export")
    # scan 参数
    workshop_path: str = Field(default="", description="工坊目录路径")
    max_workers: int = Field(default=4, description="并发扫描线程数")
    # filter 参数
    filters: Dict[str, Any] = Field(default_factory=dict, description="过滤条件")
    # rename 参数
    workshop_ids: List[str] = Field(default_factory=list, description="要重命名的壁纸 ID 列表")
    template: str = Field(default="[#{id}]{original_name}+{title}", description="命名模板")
    desc_max_length: int = Field(default=18, description="描述截断长度")
    name_max_length: int = Field(default=120, description="名称最大长度")
    dry_run: bool = Field(default=True, description="模拟执行")
    copy_mode: bool = Field(default=False, description="复制模式（保留原文件）")
    target_path: str = Field(default="", description="复制模式的目标路径")
    # export 参数
    export_format: str = Field(default="json", description="导出格式: json, paths")
    export_path: str = Field(default="", description="导出文件路径")


class EngineVOutput(AdapterOutput):
    """enginev 输出结果"""
    wallpapers: List[Dict[str, Any]] = Field(default_factory=list, description="壁纸列表")
    total_count: int = Field(default=0, description="总数量")
    filtered_count: int = Field(default=0, description="过滤后数量")
    success_count: int = Field(default=0, description="成功数量")
    failed_count: int = Field(default=0, description="失败数量")
    type_stats: Dict[str, int] = Field(default_factory=dict, description="类型统计")
    rating_stats: Dict[str, int] = Field(default_factory=dict, description="评级统计")


class EngineVAdapter(BaseAdapter):
    """
    enginev 适配器
    
    功能：Wallpaper Engine 工坊管理工具
    支持扫描工坊目录、过滤壁纸、批量重命名、导出数据
    """
    
    name = "enginev"
    display_name = "壁纸工坊管理"
    description = "Wallpaper Engine 工坊管理：扫描、过滤、预览、批量重命名"
    category = "file"
    icon = "🖼️"
    required_packages = ["enginev"]  # 依赖的工具包
    input_schema = EngineVInput
    output_schema = EngineVOutput
    
    # 缓存扫描结果
    _service = None
    _last_workshop_path = None
    
    def _import_module(self) -> Dict:
        """懒加载导入 enginev 模块"""
        from enginev.core.services import WallpaperService
        from enginev.core.models import WallpaperFolder
        from enginev.core.renamer import FolderRenamer
        
        return {
            'WallpaperService': WallpaperService,
            'WallpaperFolder': WallpaperFolder,
            'FolderRenamer': FolderRenamer,
        }
    
    def _get_service(self, workshop_path: str):
        """获取或创建 WallpaperService 实例"""
        module = self.get_module()
        WallpaperService = module['WallpaperService']
        
        # 如果路径变化，重新创建服务
        if self._service is None or self._last_workshop_path != workshop_path:
            self._service = WallpaperService(workshop_path)
            self._last_workshop_path = workshop_path
        
        return self._service
    
    async def execute(
        self,
        input_data: EngineVInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> EngineVOutput:
        """执行 enginev 功能"""
        action = input_data.action.lower()
        
        if action == "scan":
            return await self._scan(input_data, on_progress, on_log)
        elif action == "filter":
            return await self._filter(input_data, on_progress, on_log)
        elif action == "rename":
            return await self._rename(input_data, on_progress, on_log)
        elif action == "export":
            return await self._export(input_data, on_progress, on_log)
        else:
            return EngineVOutput(
                success=False,
                message=f"未知操作: {action}"
            )
    
    async def _scan(
        self,
        input_data: EngineVInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> EngineVOutput:
        """扫描工坊目录"""
        workshop_path = input_data.workshop_path or input_data.path
        if not workshop_path:
            return EngineVOutput(
                success=False,
                message="请指定工坊目录路径"
            )
        
        path = Path(workshop_path)
        if not path.exists():
            return EngineVOutput(
                success=False,
                message=f"路径不存在: {workshop_path}"
            )
        
        try:
            if on_log:
                on_log(f"开始扫描工坊目录: {workshop_path}")
            if on_progress:
                on_progress(10, "正在初始化...")
            
            service = self._get_service(workshop_path)
            
            if on_progress:
                on_progress(30, "扫描中...")
            
            result = service.scan(max_workers=input_data.max_workers, force=True)
            
            if on_progress:
                on_progress(80, "处理数据...")
            
            # 转换为字典列表
            wallpapers = [w.to_dict() for w in result.wallpapers]
            
            # 统计信息
            stats = service.aggregate_counts()
            
            if on_progress:
                on_progress(100, "扫描完成")
            
            if on_log:
                on_log(f"✅ 扫描完成: {result.count} 个壁纸")
            
            return EngineVOutput(
                success=True,
                message=f"扫描完成: {result.count} 个壁纸",
                wallpapers=wallpapers,
                total_count=result.count,
                filtered_count=result.count,
                type_stats=stats.get("type", {}),
                rating_stats=stats.get("content_rating", {}),
                data={
                    'wallpapers': wallpapers,
                    'total_count': result.count,
                    'type_stats': stats.get("type", {}),
                    'rating_stats': stats.get("content_rating", {}),
                }
            )
            
        except ImportError as e:
            return EngineVOutput(
                success=False,
                message=f"enginev 模块未安装: {str(e)}"
            )
        except Exception as e:
            if on_log:
                on_log(f"❌ 扫描失败: {str(e)}")
            return EngineVOutput(
                success=False,
                message=f"扫描失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _filter(
        self,
        input_data: EngineVInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> EngineVOutput:
        """过滤壁纸"""
        if self._service is None:
            return EngineVOutput(
                success=False,
                message="请先扫描工坊目录"
            )
        
        try:
            if on_log:
                on_log(f"应用过滤条件: {input_data.filters}")
            if on_progress:
                on_progress(30, "过滤中...")
            
            filtered = self._service.filter(input_data.filters)
            wallpapers = [w.to_dict() for w in filtered]
            
            if on_progress:
                on_progress(100, "过滤完成")
            
            if on_log:
                on_log(f"✅ 过滤完成: {len(filtered)} 个壁纸")
            
            return EngineVOutput(
                success=True,
                message=f"过滤完成: {len(filtered)} 个壁纸",
                wallpapers=wallpapers,
                total_count=len(self._service.wallpapers),
                filtered_count=len(filtered),
                data={
                    'wallpapers': wallpapers,
                    'filtered_count': len(filtered),
                }
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 过滤失败: {str(e)}")
            return EngineVOutput(
                success=False,
                message=f"过滤失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _rename(
        self,
        input_data: EngineVInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> EngineVOutput:
        """批量重命名"""
        if self._service is None:
            return EngineVOutput(
                success=False,
                message="请先扫描工坊目录"
            )
        
        if not input_data.workshop_ids:
            return EngineVOutput(
                success=False,
                message="请指定要重命名的壁纸"
            )
        
        try:
            module = self.get_module()
            FolderRenamer = module['FolderRenamer']
            
            if on_log:
                mode = "模拟" if input_data.dry_run else "执行"
                on_log(f"{mode}重命名 {len(input_data.workshop_ids)} 个壁纸")
            if on_progress:
                on_progress(10, "准备重命名...")
            
            # 获取要重命名的壁纸
            id_set = set(input_data.workshop_ids)
            wallpapers = [w for w in self._service.wallpapers if w.workshop_id in id_set]
            
            if not wallpapers:
                return EngineVOutput(
                    success=False,
                    message="未找到指定的壁纸"
                )
            
            # 使用 FolderRenamer 进行批量重命名
            renamer = FolderRenamer(dry_run=input_data.dry_run)
            target_dir = input_data.target_path if input_data.copy_mode else None
            
            if on_progress:
                on_progress(30, "执行重命名...")
            
            results = renamer.rename_folders(
                wallpapers,
                input_data.template,
                target_base_dir=target_dir
            )
            
            success_count = sum(1 for r in results if r.get('status') in ('renamed', 'copied', 'planned'))
            failed_count = sum(1 for r in results if r.get('status') == 'error')
            
            if on_log:
                for r in results:
                    if r.get('status') == 'error':
                        on_log(f"  ❌ {r.get('old_name')}: {r.get('error')}")
                    else:
                        on_log(f"  {r.get('old_name')} -> {r.get('new_name')}")
            
            if on_progress:
                on_progress(100, "重命名完成")
            
            if on_log:
                on_log(f"✅ 完成: 成功 {success_count}, 失败 {failed_count}")
            
            return EngineVOutput(
                success=True,
                message=f"重命名完成: 成功 {success_count}, 失败 {failed_count}",
                success_count=success_count,
                failed_count=failed_count,
                data={
                    'success_count': success_count,
                    'failed_count': failed_count,
                }
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 重命名失败: {str(e)}")
            return EngineVOutput(
                success=False,
                message=f"重命名失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _export(
        self,
        input_data: EngineVInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> EngineVOutput:
        """导出数据"""
        if self._service is None:
            return EngineVOutput(
                success=False,
                message="请先扫描工坊目录"
            )
        
        if not input_data.export_path:
            return EngineVOutput(
                success=False,
                message="请指定导出路径"
            )
        
        try:
            if on_log:
                on_log(f"导出数据到: {input_data.export_path}")
            if on_progress:
                on_progress(30, "导出中...")
            
            # 获取要导出的壁纸（如果有过滤条件则使用过滤结果）
            if input_data.filters:
                wallpapers = self._service.filter(input_data.filters)
            else:
                wallpapers = self._service.wallpapers
            
            export_path = self._service.export(
                wallpapers,
                input_data.export_path,
                input_data.export_format
            )
            
            if on_progress:
                on_progress(100, "导出完成")
            
            if on_log:
                on_log(f"✅ 导出完成: {len(wallpapers)} 个壁纸 -> {export_path}")
            
            return EngineVOutput(
                success=True,
                message=f"导出完成: {len(wallpapers)} 个壁纸",
                output_path=str(export_path),
                data={
                    'export_path': str(export_path),
                    'count': len(wallpapers),
                }
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 导出失败: {str(e)}")
            return EngineVOutput(
                success=False,
                message=f"导出失败: {type(e).__name__}: {str(e)}"
            )
