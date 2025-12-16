"""
适配器基类定义
提供工具适配器的抽象接口，支持懒加载和直接 import 模式
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
import importlib
from pydantic import BaseModel, Field


# ============== 工具包可用性检测 ==============

def check_tool_available(tool_name: str) -> bool:
    """
    检查工具包是否已安装
    
    Args:
        tool_name: 工具包名称（如 'repacku', 'trename'）
        
    Returns:
        工具包是否可用
    """
    try:
        importlib.import_module(tool_name)
        return True
    except ImportError:
        return False


def get_missing_tools(tool_names: List[str]) -> List[str]:
    """
    获取缺失的工具包列表
    
    Args:
        tool_names: 要检查的工具包名称列表
        
    Returns:
        缺失的工具包名称列表
    """
    return [name for name in tool_names if not check_tool_available(name)]


def get_missing_tools_message(missing: List[str]) -> str:
    """
    生成缺失工具的安装提示消息
    
    Args:
        missing: 缺失的工具包名称列表
        
    Returns:
        友好的安装提示消息
    """
    if not missing:
        return ""
    return (
        f"缺少工具包: {', '.join(missing)}。\n"
        f"请运行以下命令安装:\n"
        f"  pip install aestival-backend[tools]\n"
        f"或单独安装缺失的包。"
    )


# 已知的工具包映射（适配器名称 -> 包名）
TOOL_PACKAGE_MAP = {
    "repacku": "repacku",
    "rawfilter": "rawfilter", 
    "crashu": "crashu",
    "trename": "trename",
    "enginev": "enginev",
    "autorepack": "autorepack",
    "imagefilter": "imagefilter",
    "previewa": "previewa",
    "nameu": "nameu",
}


class AdapterInput(BaseModel):
    """适配器输入基类"""
    path: str = Field(..., description="输入路径")


class AdapterOutput(BaseModel):
    """适配器输出基类"""
    success: bool = Field(..., description="执行是否成功")
    message: str = Field(..., description="执行结果消息")
    data: Any = Field(default=None, description="输出数据")
    stats: Dict[str, int] = Field(default_factory=dict, description="统计信息")
    output_path: Optional[str] = Field(default=None, description="输出路径（用于传递给下游节点）")


class AdapterError(Exception):
    """适配器执行错误"""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class BaseAdapter(ABC):
    """
    工具适配器基类 - 直接导入模式
    
    所有工具适配器都应继承此类，实现懒加载和统一的执行接口。
    """
    
    # 子类必须定义的属性
    name: str = ""                    # 工具名称（唯一标识）
    display_name: str = ""            # 显示名称
    description: str = ""             # 工具描述
    category: str = "other"           # 分类: file, video, other
    icon: str = "📦"                  # 图标 emoji
    
    # 依赖的工具包名称（子类可覆盖）
    required_packages: List[str] = []
    
    # 输入输出 Schema（子类可覆盖）
    input_schema: type[AdapterInput] = AdapterInput
    output_schema: type[AdapterOutput] = AdapterOutput
    
    # 懒加载的模块引用
    _module: Optional[Dict] = None
    
    def __init__(self):
        """初始化适配器"""
        pass
    
    def is_available(self) -> bool:
        """
        检查适配器依赖的工具包是否可用
        
        Returns:
            所有依赖包是否都已安装
        """
        if not self.required_packages:
            return True
        return len(get_missing_tools(self.required_packages)) == 0
    
    def get_availability_message(self) -> Optional[str]:
        """
        获取工具包可用性消息
        
        Returns:
            如果有缺失的包，返回安装提示；否则返回 None
        """
        if not self.required_packages:
            return None
        missing = get_missing_tools(self.required_packages)
        if missing:
            return get_missing_tools_message(missing)
        return None
    
    @abstractmethod
    def _import_module(self) -> Dict:
        """
        懒加载导入工具模块
        
        子类必须实现此方法，返回包含所需函数/类的字典。
        只有在首次调用 execute() 时才会执行导入。
        
        Returns:
            包含工具函数/类的字典
        """
        pass
    
    def get_module(self) -> Dict:
        """
        获取工具模块（带懒加载）
        
        Returns:
            包含工具函数/类的字典
        """
        if self._module is None:
            self._module = self._import_module()
        return self._module
    
    @abstractmethod
    async def execute(
        self,
        input_data: AdapterInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> AdapterOutput:
        """
        执行工具功能
        
        Args:
            input_data: 输入数据
            on_progress: 进度回调函数 (progress: 0-100, message: str)
            on_log: 日志回调函数 (message: str)
            
        Returns:
            执行结果
        """
        pass
    
    def get_schema(self) -> Dict:
        """
        获取输入参数 Schema（用于前端生成表单）
        
        Returns:
            JSON Schema 字典
        """
        return self.input_schema.model_json_schema()
    
    def get_output_schema(self) -> Dict:
        """
        获取输出参数 Schema
        
        Returns:
            JSON Schema 字典
        """
        return self.output_schema.model_json_schema()
    
    def get_info(self) -> Dict:
        """
        获取适配器信息
        
        Returns:
            适配器元信息字典
        """
        return {
            "name": self.name,
            "displayName": self.display_name,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "inputSchema": self.get_schema(),
            "outputSchema": self.get_output_schema(),
            "available": self.is_available(),
            "availabilityMessage": self.get_availability_message(),
            "requiredPackages": self.required_packages,
        }
    
    def validate_input(self, input_data: Dict) -> bool:
        """
        验证输入数据
        
        Args:
            input_data: 输入数据字典
            
        Returns:
            是否有效
        """
        try:
            self.input_schema(**input_data)
            return True
        except Exception:
            return False


async def safe_execute(
    adapter: BaseAdapter, 
    input_data: AdapterInput,
    on_progress: Optional[Callable[[int, str], None]] = None,
    on_log: Optional[Callable[[str], None]] = None
) -> AdapterOutput:
    """
    安全执行适配器，捕获所有异常
    
    Args:
        adapter: 适配器实例
        input_data: 输入数据
        on_progress: 进度回调
        on_log: 日志回调
        
    Returns:
        执行结果（即使出错也返回 AdapterOutput）
    """
    try:
        return await adapter.execute(input_data, on_progress, on_log)
    except ImportError as e:
        # 检查是否是工具包缺失
        missing_pkg = str(e).split("'")[-2] if "'" in str(e) else str(e)
        if missing_pkg in TOOL_PACKAGE_MAP.values():
            return AdapterOutput(
                success=False,
                message=get_missing_tools_message([missing_pkg])
            )
        return AdapterOutput(
            success=False,
            message=f"模块导入失败: {str(e)}"
        )
    except FileNotFoundError as e:
        return AdapterOutput(
            success=False,
            message=f"路径不存在: {str(e)}"
        )
    except PermissionError as e:
        return AdapterOutput(
            success=False,
            message=f"权限不足: {str(e)}"
        )
    except AdapterError as e:
        return AdapterOutput(
            success=False,
            message=e.message,
            data=e.details
        )
    except Exception as e:
        return AdapterOutput(
            success=False,
            message=f"执行异常: {type(e).__name__}: {str(e)}"
        )
