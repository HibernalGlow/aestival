"""
适配器注册和管理模块
提供适配器的懒加载获取和列表功能
"""

from typing import Dict, List, Optional, Type

from .base import BaseAdapter, AdapterInput, AdapterOutput, AdapterError, safe_execute


# 适配器注册表（懒加载）
# key: 适配器名称, value: 适配器类（延迟导入）
_ADAPTER_REGISTRY: Dict[str, str] = {
    "repacku": "adapters.repacku_adapter.RepackuAdapter",
    "rawfilter": "adapters.rawfilter_adapter.RawfilterAdapter",
    "crashu": "adapters.crashu_adapter.CrashuAdapter",
    "trename": "adapters.trename_adapter.TrenameAdapter",
    "enginev": "adapters.enginev_adapter.EngineVAdapter",
    "migratef": "adapters.migratef_adapter.MigrateFAdapter",
    "formatv": "adapters.formatv_adapter.FormatVAdapter",
    "findz": "adapters.findz_adapter.FindzAdapter",
    "bandia": "adapters.bandia_adapter.BandiaAdapter",
    "dissolvef": "adapters.dissolvef_adapter.DissolvefAdapter",
    "sleept": "adapters.sleept_adapter.SleeptAdapter",
    # EnvU 工具适配器
    "owithu": "adapters.owithu_adapter.OwithuAdapter",
    "linku": "adapters.linku_adapter.LinkuAdapter",
    "scoolp": "adapters.scoolp_adapter.ScoolpAdapter",
    "reinstallp": "adapters.reinstallp_adapter.ReinstallpAdapter",
}

# 适配器实例缓存
_adapter_instances: Dict[str, BaseAdapter] = {}


def _import_adapter_class(adapter_path: str) -> Type[BaseAdapter]:
    """
    动态导入适配器类
    
    Args:
        adapter_path: 适配器类的完整路径，如 "adapters.repacku_adapter.RepackuAdapter"
        
    Returns:
        适配器类
    """
    parts = adapter_path.rsplit(".", 1)
    if len(parts) != 2:
        raise ImportError(f"无效的适配器路径: {adapter_path}")
    
    module_path, class_name = parts
    
    # 动态导入模块
    import importlib
    module = importlib.import_module(module_path)
    
    # 获取类
    adapter_class = getattr(module, class_name)
    return adapter_class


def get_adapter(name: str) -> BaseAdapter:
    """
    获取适配器实例（懒加载）
    
    Args:
        name: 适配器名称
        
    Returns:
        适配器实例
        
    Raises:
        ValueError: 适配器不存在
        ImportError: 适配器导入失败
    """
    # 检查缓存
    if name in _adapter_instances:
        return _adapter_instances[name]
    
    # 检查注册表
    if name not in _ADAPTER_REGISTRY:
        raise ValueError(f"未知的适配器: {name}，可用适配器: {list(_ADAPTER_REGISTRY.keys())}")
    
    # 懒加载导入
    adapter_path = _ADAPTER_REGISTRY[name]
    try:
        adapter_class = _import_adapter_class(adapter_path)
        adapter_instance = adapter_class()
        _adapter_instances[name] = adapter_instance
        return adapter_instance
    except ImportError as e:
        raise ImportError(f"导入适配器 {name} 失败: {e}")


def list_adapters() -> List[Dict]:
    """
    列出所有可用适配器的信息
    
    Returns:
        适配器信息列表
    """
    adapters_info = []
    
    for name in _ADAPTER_REGISTRY.keys():
        try:
            adapter = get_adapter(name)
            adapters_info.append(adapter.get_info())
        except Exception as e:
            # 如果适配器导入失败，添加基本信息
            adapters_info.append({
                "name": name,
                "displayName": name,
                "description": f"加载失败: {str(e)}",
                "category": "error",
                "icon": "❌",
                "error": str(e)
            })
    
    return adapters_info


def get_adapter_names() -> List[str]:
    """
    获取所有已注册的适配器名称
    
    Returns:
        适配器名称列表
    """
    return list(_ADAPTER_REGISTRY.keys())


def register_adapter(name: str, adapter_path: str):
    """
    注册新的适配器
    
    Args:
        name: 适配器名称
        adapter_path: 适配器类的完整路径
    """
    _ADAPTER_REGISTRY[name] = adapter_path
    # 清除缓存（如果存在）
    if name in _adapter_instances:
        del _adapter_instances[name]


def clear_adapter_cache():
    """清除适配器实例缓存"""
    _adapter_instances.clear()


# 导出
__all__ = [
    "BaseAdapter",
    "AdapterInput", 
    "AdapterOutput",
    "AdapterError",
    "safe_execute",
    "get_adapter",
    "list_adapters",
    "get_adapter_names",
    "register_adapter",
    "clear_adapter_cache",
]
