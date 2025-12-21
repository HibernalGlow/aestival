"""
reinstallp 适配器
Python 可编辑包重新安装工具 - 扫描并重新安装 pyproject.toml 项目
"""

from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


class ReinstallpInput(AdapterInput):
    """reinstallp 输入参数"""
    path: str = Field(default="", description="要扫描的根目录路径")
    action: str = Field(default="scan", description="操作类型: scan, install")
    use_system: bool = Field(default=True, description="是否使用系统安装 (--system)")
    projects: List[str] = Field(default_factory=list, description="要安装的项目路径列表（install 时使用）")


class ReinstallpOutput(AdapterOutput):
    """reinstallp 输出结果"""
    projects: List[Dict] = Field(default_factory=list, description="找到的项目列表")
    installed_count: int = Field(default=0, description="安装成功数量")
    failed_count: int = Field(default=0, description="安装失败数量")


class ReinstallpAdapter(BaseAdapter):
    """
    reinstallp 适配器
    
    功能：Python 可编辑包重新安装工具
    扫描目录查找 pyproject.toml 项目并重新安装为可编辑包
    """
    
    name = "reinstallp"
    display_name = "Python 包重装"
    description = "扫描并重新安装 Python 可编辑包 (pip install -e)"
    category = "dev"
    icon = "🐍"
    required_packages = []  # 不依赖外部包，使用内置功能
    input_schema = ReinstallpInput
    output_schema = ReinstallpOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入模块"""
        import subprocess
        import re
        return {
            'subprocess': subprocess,
            're': re,
        }
    
    def _should_exclude(self, path: Path) -> bool:
        """检查路径是否应该被排除"""
        exclude_patterns = [
            '.venv', 'venv', '.env', '__pycache__', '.git',
            'node_modules', '.pytest_cache', '.mypy_cache',
            '.egg-info', 'build', 'dist', '.tox',
        ]
        path_str = str(path).lower()
        for pattern in exclude_patterns:
            if pattern in path_str:
                return True
        return False
    
    async def execute(
        self,
        input_data: ReinstallpInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> ReinstallpOutput:
        """执行 reinstallp 功能"""
        action = input_data.action.lower()
        
        if action == "scan":
            return await self._scan(input_data, on_progress, on_log)
        elif action == "install":
            return await self._install(input_data, on_progress, on_log)
        else:
            return ReinstallpOutput(
                success=False,
                message=f"未知操作: {action}"
            )
    
    async def _scan(
        self,
        input_data: ReinstallpInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> ReinstallpOutput:
        """扫描目录查找 pyproject.toml 项目"""
        if not input_data.path:
            return ReinstallpOutput(
                success=False,
                message="请指定要扫描的目录"
            )
        
        try:
            if on_progress:
                on_progress(10, "开始扫描...")
            
            root = Path(input_data.path)
            if not root.exists():
                return ReinstallpOutput(
                    success=False,
                    message=f"目录不存在: {root}"
                )
            
            projects = []
            
            if on_log:
                on_log(f"扫描目录: {root}")
            
            for pyproject in root.rglob("pyproject.toml"):
                folder = pyproject.parent
                
                if self._should_exclude(folder):
                    continue
                
                # 读取项目名称
                project_name = folder.name
                try:
                    import tomllib
                    with open(pyproject, 'rb') as f:
                        data = tomllib.load(f)
                        project_name = data.get('project', {}).get('name', folder.name)
                except Exception:
                    pass
                
                projects.append({
                    'path': str(folder),
                    'name': project_name,
                    'pyproject': str(pyproject),
                })
                
                if on_log:
                    on_log(f"找到项目: {project_name} ({folder})")
            
            if on_progress:
                on_progress(100, "扫描完成")
            
            if on_log:
                on_log(f"✅ 找到 {len(projects)} 个项目")
            
            return ReinstallpOutput(
                success=True,
                message=f"找到 {len(projects)} 个项目",
                projects=projects,
                data={'projects': projects},
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 扫描失败: {str(e)}")
            return ReinstallpOutput(
                success=False,
                message=f"扫描失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _install(
        self,
        input_data: ReinstallpInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> ReinstallpOutput:
        """安装项目"""
        if not input_data.projects:
            return ReinstallpOutput(
                success=False,
                message="请指定要安装的项目"
            )
        
        try:
            module = self.get_module()
            subprocess = module['subprocess']
            
            installed = 0
            failed = 0
            results = []
            
            for i, project_path in enumerate(input_data.projects):
                progress = int(100 * (i + 1) / len(input_data.projects))
                if on_progress:
                    on_progress(progress, f"安装: {Path(project_path).name}")
                
                # 构建命令
                if input_data.use_system:
                    cmd = ['uv', 'pip', 'install', '-e', project_path, '--system']
                else:
                    cmd = ['uv', 'pip', 'install', '-e', project_path]
                
                if on_log:
                    on_log(f"执行: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                )
                
                project_name = Path(project_path).name
                
                if result.returncode == 0:
                    installed += 1
                    results.append({
                        'path': project_path,
                        'name': project_name,
                        'status': 'success',
                    })
                    if on_log:
                        on_log(f"✅ 安装成功: {project_name}")
                else:
                    failed += 1
                    results.append({
                        'path': project_path,
                        'name': project_name,
                        'status': 'failed',
                        'error': result.stderr,
                    })
                    if on_log:
                        on_log(f"❌ 安装失败: {project_name}")
            
            if on_progress:
                on_progress(100, "完成")
            
            return ReinstallpOutput(
                success=failed == 0,
                message=f"安装完成: 成功 {installed}, 失败 {failed}",
                installed_count=installed,
                failed_count=failed,
                projects=results,
                data={'results': results},
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 安装失败: {str(e)}")
            return ReinstallpOutput(
                success=False,
                message=f"安装失败: {type(e).__name__}: {str(e)}"
            )
