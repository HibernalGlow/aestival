"""
owithu 适配器
Windows 右键菜单注册工具 - 支持从 TOML 配置注册/注销上下文菜单项
"""

from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


class OwithuInput(AdapterInput):
    """owithu 输入参数"""
    path: str = Field(default="", description="TOML 配置文件路径")
    action: str = Field(default="preview", description="操作类型: preview, register, unregister")
    hive: str = Field(default="", description="注册表位置: HKCU, HKCR, HKLM（留空使用配置默认）")
    only_key: str = Field(default="", description="只处理指定的 key（留空处理全部）")


class OwithuOutput(AdapterOutput):
    """owithu 输出结果"""
    entries: List[Dict] = Field(default_factory=list, description="配置条目列表")
    registered_count: int = Field(default=0, description="注册成功数量")
    unregistered_count: int = Field(default=0, description="注销成功数量")


class OwithuAdapter(BaseAdapter):
    """
    owithu 适配器
    
    功能：Windows 右键菜单注册工具
    支持从 TOML 配置文件注册/注销上下文菜单项
    """
    
    name = "owithu"
    display_name = "右键菜单注册"
    description = "从 TOML 配置注册/注销 Windows 右键上下文菜单项"
    category = "system"
    icon = "🖱️"
    required_packages = ["owithu"]
    input_schema = OwithuInput
    output_schema = OwithuOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 owithu 模块"""
        from owithu.manager import (
            load_config,
            register_entries,
            unregister_entries,
            preview,
        )
        return {
            'load_config': load_config,
            'register_entries': register_entries,
            'unregister_entries': unregister_entries,
            'preview': preview,
        }
    
    async def execute(
        self,
        input_data: OwithuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> OwithuOutput:
        """执行 owithu 功能"""
        action = input_data.action.lower()
        
        if action == "preview":
            return await self._preview(input_data, on_progress, on_log)
        elif action == "register":
            return await self._register(input_data, on_progress, on_log)
        elif action == "unregister":
            return await self._unregister(input_data, on_progress, on_log)
        else:
            return OwithuOutput(
                success=False,
                message=f"未知操作: {action}"
            )
    
    async def _preview(
        self,
        input_data: OwithuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> OwithuOutput:
        """预览 TOML 配置中的条目"""
        if not input_data.path:
            return OwithuOutput(
                success=False,
                message="请指定 TOML 配置文件路径"
            )
        
        try:
            module = self.get_module()
            load_config = module['load_config']
            
            if on_log:
                on_log(f"加载配置: {input_data.path}")
            if on_progress:
                on_progress(30, "加载配置...")
            
            toml_path = Path(input_data.path)
            if not toml_path.exists():
                return OwithuOutput(
                    success=False,
                    message=f"配置文件不存在: {toml_path}"
                )
            
            vars_map, defaults, entries = load_config(str(toml_path))
            
            if on_progress:
                on_progress(100, "预览完成")
            
            # 转换为可序列化的字典列表
            entries_data = []
            for e in entries:
                entries_data.append({
                    'key': e.key,
                    'label': e.label,
                    'exe': e.exe,
                    'args': e.args,
                    'icon': e.icon,
                    'scope': e.scope,
                    'enabled': e.enabled,
                    'hives': e.hives,
                })
            
            if on_log:
                on_log(f"✅ 找到 {len(entries)} 个条目")
            
            return OwithuOutput(
                success=True,
                message=f"找到 {len(entries)} 个条目",
                entries=entries_data,
                data={
                    'entries': entries_data,
                    'vars': vars_map,
                    'defaults': defaults,
                }
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 预览失败: {str(e)}")
            return OwithuOutput(
                success=False,
                message=f"预览失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _register(
        self,
        input_data: OwithuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> OwithuOutput:
        """注册右键菜单项"""
        if not input_data.path:
            return OwithuOutput(
                success=False,
                message="请指定 TOML 配置文件路径"
            )
        
        try:
            module = self.get_module()
            load_config = module['load_config']
            register_entries = module['register_entries']
            
            if on_log:
                on_log(f"加载配置: {input_data.path}")
            if on_progress:
                on_progress(20, "加载配置...")
            
            toml_path = Path(input_data.path)
            vars_map, defaults, entries = load_config(str(toml_path))
            
            if on_progress:
                on_progress(50, "注册菜单项...")
            
            hive = input_data.hive if input_data.hive else None
            only_key = input_data.only_key if input_data.only_key else None
            
            register_entries(
                entries,
                hive=hive,
                defaults_hives=defaults.get('hives'),
                only_key=only_key
            )
            
            if on_progress:
                on_progress(100, "注册完成")
            
            count = len([e for e in entries if e.enabled and (not only_key or e.key == only_key)])
            
            if on_log:
                on_log(f"✅ 注册完成: {count} 个条目")
            
            return OwithuOutput(
                success=True,
                message=f"注册完成: {count} 个条目",
                registered_count=count,
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 注册失败: {str(e)}")
            return OwithuOutput(
                success=False,
                message=f"注册失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _unregister(
        self,
        input_data: OwithuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> OwithuOutput:
        """注销右键菜单项"""
        if not input_data.path:
            return OwithuOutput(
                success=False,
                message="请指定 TOML 配置文件路径"
            )
        
        try:
            module = self.get_module()
            load_config = module['load_config']
            unregister_entries = module['unregister_entries']
            
            if on_log:
                on_log(f"加载配置: {input_data.path}")
            if on_progress:
                on_progress(20, "加载配置...")
            
            toml_path = Path(input_data.path)
            vars_map, defaults, entries = load_config(str(toml_path))
            
            if on_progress:
                on_progress(50, "注销菜单项...")
            
            hive = input_data.hive if input_data.hive else None
            only_key = input_data.only_key if input_data.only_key else None
            
            unregister_entries(
                entries,
                hive=hive,
                defaults_hives=defaults.get('hives'),
                only_key=only_key
            )
            
            if on_progress:
                on_progress(100, "注销完成")
            
            count = len([e for e in entries if not only_key or e.key == only_key])
            
            if on_log:
                on_log(f"✅ 注销完成: {count} 个条目")
            
            return OwithuOutput(
                success=True,
                message=f"注销完成: {count} 个条目",
                unregistered_count=count,
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 注销失败: {str(e)}")
            return OwithuOutput(
                success=False,
                message=f"注销失败: {type(e).__name__}: {str(e)}"
            )
