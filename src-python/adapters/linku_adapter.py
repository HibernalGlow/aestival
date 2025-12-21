"""
linku 适配器
软链接管理工具 - 支持创建、移动、恢复软链接
"""

from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


class LinkuInput(AdapterInput):
    """linku 输入参数"""
    path: str = Field(default="", description="源路径（要移动或链接的目录/文件）")
    action: str = Field(default="info", description="操作类型: info, create, move_link, list, recover")
    target: str = Field(default="", description="目标路径（链接位置或移动目标）")
    config_path: str = Field(default="", description="配置文件路径（用于 list/recover）")


class LinkuOutput(AdapterOutput):
    """linku 输出结果"""
    path_info: Dict = Field(default_factory=dict, description="路径信息")
    links: List[Dict] = Field(default_factory=list, description="已记录的链接列表")
    created: bool = Field(default=False, description="是否创建成功")
    recovered_count: int = Field(default=0, description="恢复成功数量")
    failed_count: int = Field(default=0, description="失败数量")


class LinkuAdapter(BaseAdapter):
    """
    linku 适配器
    
    功能：软链接管理工具
    支持创建软链接、移动并创建链接、查看已记录链接、恢复链接
    """
    
    name = "linku"
    display_name = "软链接管理"
    description = "创建、移动、恢复软链接，管理链接记录"
    category = "file"
    icon = "🔗"
    required_packages = ["linku"]
    input_schema = LinkuInput
    output_schema = LinkuOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 linku 模块"""
        from linku.manager import SymlinkManager
        from linku.config import ConfigStore
        from linku.symlink_ops import (
            is_admin,
            create_symlink,
            delete_symlink,
        )
        return {
            'SymlinkManager': SymlinkManager,
            'ConfigStore': ConfigStore,
            'is_admin': is_admin,
            'create_symlink': create_symlink,
            'delete_symlink': delete_symlink,
        }
    
    async def execute(
        self,
        input_data: LinkuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> LinkuOutput:
        """执行 linku 功能"""
        action = input_data.action.lower()
        
        if action == "info":
            return await self._get_info(input_data, on_progress, on_log)
        elif action == "create":
            return await self._create_link(input_data, on_progress, on_log)
        elif action == "move_link":
            return await self._move_and_link(input_data, on_progress, on_log)
        elif action == "list":
            return await self._list_links(input_data, on_progress, on_log)
        elif action == "recover":
            return await self._recover_links(input_data, on_progress, on_log)
        else:
            return LinkuOutput(
                success=False,
                message=f"未知操作: {action}"
            )
    
    async def _get_info(
        self,
        input_data: LinkuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> LinkuOutput:
        """获取路径信息"""
        if not input_data.path:
            return LinkuOutput(
                success=False,
                message="请指定路径"
            )
        
        try:
            import os
            
            if on_progress:
                on_progress(30, "获取路径信息...")
            
            path = Path(input_data.path)
            info = {
                'path': str(path),
                'exists': path.exists(),
                'is_file': path.is_file() if path.exists() else False,
                'is_dir': path.is_dir() if path.exists() else False,
                'is_symlink': path.is_symlink(),
            }
            
            if path.is_symlink():
                try:
                    target = path.readlink()
                    info['link_target'] = str(target)
                    info['target_exists'] = target.exists()
                except Exception:
                    info['link_target'] = '无法读取'
            
            if path.exists():
                if path.is_file():
                    info['size_mb'] = path.stat().st_size / (1024 * 1024)
                elif path.is_dir():
                    # 计算目录大小
                    total_size = 0
                    file_count = 0
                    for dirpath, _, filenames in os.walk(path):
                        file_count += len(filenames)
                        for f in filenames:
                            try:
                                total_size += (Path(dirpath) / f).stat().st_size
                            except Exception:
                                pass
                    info['size_mb'] = total_size / (1024 * 1024)
                    info['file_count'] = file_count
            
            if on_progress:
                on_progress(100, "完成")
            
            if on_log:
                on_log(f"✅ 路径信息: {path}")
            
            return LinkuOutput(
                success=True,
                message=f"路径信息获取成功",
                path_info=info,
                data=info,
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 获取信息失败: {str(e)}")
            return LinkuOutput(
                success=False,
                message=f"获取信息失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _create_link(
        self,
        input_data: LinkuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> LinkuOutput:
        """创建软链接（直接模式）"""
        if not input_data.path or not input_data.target:
            return LinkuOutput(
                success=False,
                message="请指定源路径和目标路径"
            )
        
        try:
            module = self.get_module()
            create_symlink = module['create_symlink']
            ConfigStore = module['ConfigStore']
            
            if on_progress:
                on_progress(30, "创建软链接...")
            
            source = Path(input_data.path)  # 实际文件/目录位置
            link = Path(input_data.target)   # 软链接位置
            
            if not source.exists():
                return LinkuOutput(
                    success=False,
                    message=f"源路径不存在: {source}"
                )
            
            if link.exists():
                return LinkuOutput(
                    success=False,
                    message=f"链接路径已存在: {link}"
                )
            
            ok, err = create_symlink(source, link)
            
            if ok:
                # 记录到配置
                config = ConfigStore()
                config.record_link(link, source, '目录' if source.is_dir() else '文件')
                
                if on_progress:
                    on_progress(100, "创建成功")
                if on_log:
                    on_log(f"✅ 软链接创建成功: {link} -> {source}")
                
                return LinkuOutput(
                    success=True,
                    message=f"软链接创建成功: {link} -> {source}",
                    created=True,
                )
            else:
                if on_log:
                    on_log(f"❌ 创建失败: {err}")
                return LinkuOutput(
                    success=False,
                    message=f"创建失败: {err}",
                    created=False,
                )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 创建失败: {str(e)}")
            return LinkuOutput(
                success=False,
                message=f"创建失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _move_and_link(
        self,
        input_data: LinkuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> LinkuOutput:
        """移动并创建软链接"""
        if not input_data.path or not input_data.target:
            return LinkuOutput(
                success=False,
                message="请指定源路径和目标路径"
            )
        
        try:
            module = self.get_module()
            SymlinkManager = module['SymlinkManager']
            
            if on_progress:
                on_progress(20, "准备移动...")
            
            manager = SymlinkManager()
            source = Path(input_data.path)
            target = Path(input_data.target)
            
            if not source.exists():
                return LinkuOutput(
                    success=False,
                    message=f"源路径不存在: {source}"
                )
            
            if on_log:
                on_log(f"移动 {source} 到 {target}...")
            
            if on_progress:
                on_progress(50, "移动中...")
            
            ok = manager.move_and_link(source, target)
            
            if ok:
                if on_progress:
                    on_progress(100, "完成")
                if on_log:
                    on_log(f"✅ 移动并创建链接成功")
                
                return LinkuOutput(
                    success=True,
                    message=f"移动并创建链接成功: {source} -> {target}",
                    created=True,
                )
            else:
                return LinkuOutput(
                    success=False,
                    message="移动或创建链接失败",
                    created=False,
                )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 操作失败: {str(e)}")
            return LinkuOutput(
                success=False,
                message=f"操作失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _list_links(
        self,
        input_data: LinkuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> LinkuOutput:
        """列出已记录的链接"""
        try:
            module = self.get_module()
            ConfigStore = module['ConfigStore']
            
            if on_progress:
                on_progress(50, "读取记录...")
            
            config = ConfigStore()
            links = config.get_links()
            
            if on_progress:
                on_progress(100, "完成")
            
            if on_log:
                on_log(f"✅ 找到 {len(links)} 条记录")
            
            return LinkuOutput(
                success=True,
                message=f"找到 {len(links)} 条链接记录",
                links=links,
                data={'links': links},
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 读取失败: {str(e)}")
            return LinkuOutput(
                success=False,
                message=f"读取失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _recover_links(
        self,
        input_data: LinkuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> LinkuOutput:
        """恢复/修复已记录的链接"""
        try:
            module = self.get_module()
            ConfigStore = module['ConfigStore']
            create_symlink = module['create_symlink']
            delete_symlink = module['delete_symlink']
            
            if on_progress:
                on_progress(20, "检查链接状态...")
            
            config = ConfigStore()
            records = config.get_links()
            
            if not records:
                return LinkuOutput(
                    success=True,
                    message="没有记录需要恢复",
                    recovered_count=0,
                )
            
            recovered = 0
            failed = 0
            
            for i, item in enumerate(records):
                link_p = Path(item.get('link', ''))
                target_p = Path(item.get('target', ''))
                
                progress = 20 + int(70 * (i + 1) / len(records))
                if on_progress:
                    on_progress(progress, f"检查: {link_p.name}")
                
                try:
                    # 检查状态
                    link_exists = link_p.exists()
                    is_link = link_p.is_symlink() if link_exists else False
                    target_exists = target_p.exists()
                    
                    if not target_exists:
                        if on_log:
                            on_log(f"⚠️ 目标不存在，跳过: {target_p}")
                        continue
                    
                    if not link_exists:
                        # 链接缺失，创建
                        ok, err = create_symlink(target_p, link_p)
                        if ok:
                            recovered += 1
                            if on_log:
                                on_log(f"✅ 创建链接: {link_p}")
                        else:
                            failed += 1
                            if on_log:
                                on_log(f"❌ 创建失败: {link_p}: {err}")
                    elif not is_link:
                        # 不是软链接，跳过
                        if on_log:
                            on_log(f"⚠️ 不是软链接，跳过: {link_p}")
                    else:
                        # 检查指向
                        try:
                            real_target = link_p.readlink()
                            if str(real_target).lower() != str(target_p).lower():
                                # 指向错误，重建
                                delete_symlink(link_p)
                                ok, err = create_symlink(target_p, link_p)
                                if ok:
                                    recovered += 1
                                    if on_log:
                                        on_log(f"✅ 修复链接: {link_p}")
                                else:
                                    failed += 1
                        except Exception:
                            pass
                            
                except Exception as e:
                    failed += 1
                    if on_log:
                        on_log(f"❌ 处理失败: {link_p}: {e}")
            
            if on_progress:
                on_progress(100, "恢复完成")
            
            return LinkuOutput(
                success=True,
                message=f"恢复完成: 成功 {recovered}, 失败 {failed}",
                recovered_count=recovered,
                failed_count=failed,
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 恢复失败: {str(e)}")
            return LinkuOutput(
                success=False,
                message=f"恢复失败: {type(e).__name__}: {str(e)}"
            )
