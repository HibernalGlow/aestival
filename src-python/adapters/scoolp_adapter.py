"""
scoolp 适配器
Scoop 包管理工具 - 支持初始化、安装、清理、同步
"""

from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


class ScoolpInput(AdapterInput):
    """scoolp 输入参数"""
    path: str = Field(default="", description="配置文件路径（可选）")
    action: str = Field(default="status", description="操作类型: status, init, install, clean, sync")
    packages: List[str] = Field(default_factory=list, description="要安装的包列表")
    buckets: List[str] = Field(default_factory=list, description="要添加的 bucket 列表")
    clean_cache: bool = Field(default=True, description="是否清理缓存")
    clean_old_versions: bool = Field(default=True, description="是否清理旧版本")


class ScoolpOutput(AdapterOutput):
    """scoolp 输出结果"""
    installed_packages: List[str] = Field(default_factory=list, description="已安装的包")
    added_buckets: List[str] = Field(default_factory=list, description="已添加的 bucket")
    cleaned_size_mb: float = Field(default=0.0, description="清理的空间大小 (MB)")
    scoop_installed: bool = Field(default=False, description="Scoop 是否已安装")


class ScoolpAdapter(BaseAdapter):
    """
    scoolp 适配器
    
    功能：Scoop 包管理工具
    支持检查状态、初始化、安装包、清理缓存、同步配置
    """
    
    name = "scoolp"
    display_name = "Scoop 管理"
    description = "Scoop 包管理工具 - 初始化、安装、清理、同步"
    category = "system"
    icon = "📦"
    required_packages = ["scoolp"]
    input_schema = ScoolpInput
    output_schema = ScoolpOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 scoolp 模块"""
        # scoolp 使用 typer CLI，我们需要导入底层函数
        import subprocess
        import shutil
        return {
            'subprocess': subprocess,
            'shutil': shutil,
        }
    
    def _check_scoop_installed(self) -> bool:
        """检查 Scoop 是否已安装"""
        module = self.get_module()
        shutil = module['shutil']
        return shutil.which('scoop') is not None
    
    def _run_scoop_command(self, args: List[str], on_log: Optional[Callable[[str], None]] = None) -> tuple[bool, str]:
        """运行 scoop 命令"""
        module = self.get_module()
        subprocess = module['subprocess']
        
        try:
            cmd = ['scoop'] + args
            if on_log:
                on_log(f"执行: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=True,
            )
            
            output = result.stdout + result.stderr
            return result.returncode == 0, output
            
        except Exception as e:
            return False, str(e)
    
    async def execute(
        self,
        input_data: ScoolpInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> ScoolpOutput:
        """执行 scoolp 功能"""
        action = input_data.action.lower()
        
        if action == "status":
            return await self._check_status(input_data, on_progress, on_log)
        elif action == "init":
            return await self._init_scoop(input_data, on_progress, on_log)
        elif action == "install":
            return await self._install_packages(input_data, on_progress, on_log)
        elif action == "clean":
            return await self._clean(input_data, on_progress, on_log)
        elif action == "sync":
            return await self._sync_buckets(input_data, on_progress, on_log)
        else:
            return ScoolpOutput(
                success=False,
                message=f"未知操作: {action}"
            )
    
    async def _check_status(
        self,
        input_data: ScoolpInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> ScoolpOutput:
        """检查 Scoop 状态"""
        try:
            if on_progress:
                on_progress(30, "检查 Scoop 状态...")
            
            scoop_installed = self._check_scoop_installed()
            
            if not scoop_installed:
                if on_progress:
                    on_progress(100, "完成")
                return ScoolpOutput(
                    success=True,
                    message="Scoop 未安装",
                    scoop_installed=False,
                )
            
            # 获取已安装的包
            ok, output = self._run_scoop_command(['list'], on_log)
            installed = []
            if ok:
                lines = output.strip().split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('Installed'):
                        parts = line.split()
                        if parts:
                            installed.append(parts[0])
            
            # 获取 buckets
            ok, output = self._run_scoop_command(['bucket', 'list'], on_log)
            buckets = []
            if ok:
                lines = output.strip().split('\n')
                for line in lines:
                    if line.strip():
                        buckets.append(line.strip())
            
            if on_progress:
                on_progress(100, "完成")
            
            if on_log:
                on_log(f"✅ Scoop 已安装，{len(installed)} 个包，{len(buckets)} 个 bucket")
            
            return ScoolpOutput(
                success=True,
                message=f"Scoop 已安装: {len(installed)} 个包, {len(buckets)} 个 bucket",
                scoop_installed=True,
                installed_packages=installed,
                added_buckets=buckets,
                data={
                    'installed_packages': installed,
                    'buckets': buckets,
                }
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 检查失败: {str(e)}")
            return ScoolpOutput(
                success=False,
                message=f"检查失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _init_scoop(
        self,
        input_data: ScoolpInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> ScoolpOutput:
        """初始化/安装 Scoop"""
        try:
            if self._check_scoop_installed():
                return ScoolpOutput(
                    success=True,
                    message="Scoop 已安装，无需初始化",
                    scoop_installed=True,
                )
            
            if on_progress:
                on_progress(30, "安装 Scoop...")
            
            module = self.get_module()
            subprocess = module['subprocess']
            
            # 使用 PowerShell 安装 Scoop
            install_cmd = "Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force; irm get.scoop.sh | iex"
            
            if on_log:
                on_log("正在安装 Scoop...")
            
            result = subprocess.run(
                ['powershell', '-Command', install_cmd],
                capture_output=True,
                text=True,
            )
            
            if on_progress:
                on_progress(100, "完成")
            
            if result.returncode == 0:
                if on_log:
                    on_log("✅ Scoop 安装成功")
                return ScoolpOutput(
                    success=True,
                    message="Scoop 安装成功",
                    scoop_installed=True,
                )
            else:
                if on_log:
                    on_log(f"❌ 安装失败: {result.stderr}")
                return ScoolpOutput(
                    success=False,
                    message=f"安装失败: {result.stderr}",
                    scoop_installed=False,
                )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 初始化失败: {str(e)}")
            return ScoolpOutput(
                success=False,
                message=f"初始化失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _install_packages(
        self,
        input_data: ScoolpInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> ScoolpOutput:
        """安装包"""
        if not input_data.packages:
            return ScoolpOutput(
                success=False,
                message="请指定要安装的包"
            )
        
        try:
            if not self._check_scoop_installed():
                return ScoolpOutput(
                    success=False,
                    message="Scoop 未安装，请先初始化",
                    scoop_installed=False,
                )
            
            installed = []
            failed = []
            
            for i, pkg in enumerate(input_data.packages):
                progress = int(100 * (i + 1) / len(input_data.packages))
                if on_progress:
                    on_progress(progress, f"安装: {pkg}")
                
                ok, output = self._run_scoop_command(['install', pkg], on_log)
                
                if ok or 'already installed' in output.lower():
                    installed.append(pkg)
                    if on_log:
                        on_log(f"✅ 安装成功: {pkg}")
                else:
                    failed.append(pkg)
                    if on_log:
                        on_log(f"❌ 安装失败: {pkg}")
            
            if on_progress:
                on_progress(100, "完成")
            
            return ScoolpOutput(
                success=len(failed) == 0,
                message=f"安装完成: 成功 {len(installed)}, 失败 {len(failed)}",
                scoop_installed=True,
                installed_packages=installed,
                data={
                    'installed': installed,
                    'failed': failed,
                }
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 安装失败: {str(e)}")
            return ScoolpOutput(
                success=False,
                message=f"安装失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _clean(
        self,
        input_data: ScoolpInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> ScoolpOutput:
        """清理缓存和旧版本"""
        try:
            if not self._check_scoop_installed():
                return ScoolpOutput(
                    success=False,
                    message="Scoop 未安装",
                    scoop_installed=False,
                )
            
            cleaned_size = 0.0
            
            if input_data.clean_cache:
                if on_progress:
                    on_progress(30, "清理缓存...")
                if on_log:
                    on_log("清理缓存...")
                
                ok, output = self._run_scoop_command(['cache', 'rm', '*'], on_log)
                if on_log:
                    on_log(f"缓存清理: {'成功' if ok else '失败'}")
            
            if input_data.clean_old_versions:
                if on_progress:
                    on_progress(70, "清理旧版本...")
                if on_log:
                    on_log("清理旧版本...")
                
                ok, output = self._run_scoop_command(['cleanup', '*'], on_log)
                if on_log:
                    on_log(f"旧版本清理: {'成功' if ok else '失败'}")
            
            if on_progress:
                on_progress(100, "完成")
            
            if on_log:
                on_log("✅ 清理完成")
            
            return ScoolpOutput(
                success=True,
                message="清理完成",
                scoop_installed=True,
                cleaned_size_mb=cleaned_size,
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 清理失败: {str(e)}")
            return ScoolpOutput(
                success=False,
                message=f"清理失败: {type(e).__name__}: {str(e)}"
            )
    
    async def _sync_buckets(
        self,
        input_data: ScoolpInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> ScoolpOutput:
        """同步/添加 buckets"""
        try:
            if not self._check_scoop_installed():
                return ScoolpOutput(
                    success=False,
                    message="Scoop 未安装",
                    scoop_installed=False,
                )
            
            added = []
            
            if input_data.buckets:
                for i, bucket in enumerate(input_data.buckets):
                    progress = int(100 * (i + 1) / len(input_data.buckets))
                    if on_progress:
                        on_progress(progress, f"添加 bucket: {bucket}")
                    
                    ok, output = self._run_scoop_command(['bucket', 'add', bucket], on_log)
                    
                    if ok or 'already been added' in output.lower():
                        added.append(bucket)
                        if on_log:
                            on_log(f"✅ Bucket 添加成功: {bucket}")
                    else:
                        if on_log:
                            on_log(f"❌ Bucket 添加失败: {bucket}")
            
            # 更新所有 buckets
            if on_progress:
                on_progress(90, "更新 buckets...")
            
            ok, output = self._run_scoop_command(['update'], on_log)
            
            if on_progress:
                on_progress(100, "完成")
            
            if on_log:
                on_log("✅ 同步完成")
            
            return ScoolpOutput(
                success=True,
                message=f"同步完成: 添加 {len(added)} 个 bucket",
                scoop_installed=True,
                added_buckets=added,
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 同步失败: {str(e)}")
            return ScoolpOutput(
                success=False,
                message=f"同步失败: {type(e).__name__}: {str(e)}"
            )
