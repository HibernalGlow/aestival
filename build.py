#!/usr/bin/env python3
"""
aestival 构建脚本
支持 Tauri 桌面应用打包（Python Sidecar + Rust 前端）
使用 uv 管理依赖，nuitka 打包
"""
import sys
import subprocess
import platform
from pathlib import Path


def run_command(command, description, cwd=None, capture=True):
    """运行命令并显示状态"""
    print(f"🔧 {description}...")
    try:
        if capture:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                cwd=cwd,
                capture_output=True,
                text=True
            )
        else:
            # 实时输出
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                cwd=cwd,
            )
        print(f"✅ {description} 完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失败!")
        if capture and e.stderr:
            print(f"错误: {e.stderr}")
        return False


def check_dependencies():
    """检查必要的依赖"""
    print("🔍 检查依赖...")
    
    required_tools = {
        "yarn": "yarn --version",
        "python": "python --version",
        "uv": "uv --version",
        "cargo": "cargo --version",
    }
    
    missing_tools = []
    for tool, check_cmd in required_tools.items():
        try:
            subprocess.run(check_cmd, shell=True, check=True, capture_output=True)
            print(f"  ✅ {tool}")
        except subprocess.CalledProcessError:
            print(f"  ❌ {tool} 未安装")
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"\n❌ 缺少必要工具: {', '.join(missing_tools)}")
        if "uv" in missing_tools:
            print("   请安装 uv: https://docs.astral.sh/uv/getting-started/installation/")
        if "cargo" in missing_tools:
            print("   请安装 Rust: https://rustup.rs/")
        sys.exit(1)
    
    print("✅ 所有依赖已就绪")


def detect_platform():
    """检测当前平台"""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    else:
        print(f"⚠️  未知平台: {system}，默认使用 linux")
        return "linux"


def build_frontend():
    """构建 SvelteKit 前端"""
    return run_command("yarn build", "构建前端")


def install_python_deps():
    """使用 uv 安装 Python 依赖到虚拟环境"""
    src_python = Path("src-python")
    
    # 创建虚拟环境（如果不存在）
    venv_path = src_python / ".venv"
    if not venv_path.exists():
        if not run_command("uv venv", "创建虚拟环境", cwd="src-python"):
            return False
    
    # 使用 uv 同步依赖（包括 dev 依赖，实时输出）
    return run_command("uv sync --dev", "安装 Python 依赖", cwd="src-python", capture=False)


def load_nuitka_config():
    """从 pyproject.toml 加载 Nuitka 配置"""
    try:
        import tomllib as tomli
    except ImportError:
        try:
            import tomli
        except ImportError:
            print("⚠️  tomli 未安装，使用默认配置")
            return {}
    
    pyproject_path = Path("src-python/pyproject.toml")
    if not pyproject_path.exists():
        return {}
    
    with open(pyproject_path, "rb") as f:
        data = tomli.load(f)
    
    return data.get("tool", {}).get("nuitka", {})


def build_python_sidecar():
    """使用 Nuitka 打包 Python Sidecar"""
    platform_name = detect_platform()
    
    # 从 pyproject.toml 加载配置
    config = load_nuitka_config()
    
    # 确保输出目录存在
    bin_dir = Path("src-tauri/bin")
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    # Sidecar 名称
    sidecar_name = config.get("name", "main")
    
    # 根据平台添加后缀
    if platform_name == "windows":
        target_suffix = "-x86_64-pc-windows-msvc"
    elif platform_name == "macos":
        import platform as plat
        arch = plat.machine()
        target_suffix = "-aarch64-apple-darwin" if arch == "arm64" else "-x86_64-apple-darwin"
    else:
        target_suffix = "-x86_64-unknown-linux-gnu"
    
    # 构建 Nuitka 命令
    nuitka_cmd = [
        "uv", "run", "python", "-m", "nuitka",
        f"--output-filename={sidecar_name}",
        f"--output-dir={bin_dir.absolute()}",
    ]
    
    # 基本选项
    if config.get("onefile", True):
        nuitka_cmd.append("--onefile")
    if config.get("standalone", True):
        nuitka_cmd.append("--standalone")
    
    # 添加 include-module
    for module in config.get("include-modules", []):
        nuitka_cmd.append(f"--include-module={module}")
    
    # 添加 include-package
    for package in config.get("include-packages", []):
        nuitka_cmd.append(f"--include-package={package}")
    
    # 添加 nofollow-imports
    for module in config.get("nofollow-imports", []):
        nuitka_cmd.append(f"--nofollow-import-to={module}")
    
    # Windows 特定选项
    if platform_name == "windows":
        nuitka_cmd.append("--windows-console-mode=attach")
        # CI 环境有 MSVC，本地用 MinGW（Nuitka 会自动下载）
        import os
        if os.environ.get("CI"):
            nuitka_cmd.append("--msvc=latest")
        else:
            nuitka_cmd.append("--mingw64")
    
    # 入口文件
    nuitka_cmd.append("main.py")
    
    cmd_str = " ".join(nuitka_cmd)
    if not run_command(cmd_str, f"打包 Python Sidecar ({platform_name})", cwd="src-python", capture=False):
        return False
    
    # 重命名为 Tauri 期望的格式
    src_file = bin_dir / (sidecar_name + (".exe" if platform_name == "windows" else ""))
    dst_file = bin_dir / (sidecar_name + target_suffix + (".exe" if platform_name == "windows" else ""))
    
    if src_file.exists():
        if dst_file.exists():
            dst_file.unlink()
        src_file.rename(dst_file)
        print(f"✅ Sidecar 已重命名为: {dst_file.name}")
    
    return True


def build_tauri():
    """构建 Tauri 应用"""
    return run_command("yarn tauri build", "构建 Tauri 应用")


def show_build_results():
    """显示构建结果"""
    print("\n🎉 构建完成!")
    print("\n📦 构建产物:")
    
    # Tauri 构建产物
    tauri_dist = Path("src-tauri/target/release/bundle")
    if tauri_dist.exists():
        for bundle_type in tauri_dist.iterdir():
            if bundle_type.is_dir():
                print(f"   📁 {bundle_type.name}/")
                for item in bundle_type.iterdir():
                    if item.is_file():
                        size = item.stat().st_size / (1024 * 1024)
                        print(f"      📄 {item.name} ({size:.1f} MB)")
    
    # Sidecar
    sidecar_dir = Path("src-tauri/bin")
    if sidecar_dir.exists():
        print("   📁 sidecar/")
        for item in sidecar_dir.iterdir():
            if item.is_file():
                size = item.stat().st_size / (1024 * 1024)
                print(f"      📄 {item.name} ({size:.1f} MB)")
    
    print("\n🚀 运行方式:")
    print("   开发模式: yarn tauri:dev")
    print("   独立前端: yarn dev:standalone")
    print("   打包应用: 运行 src-tauri/target/release/bundle/ 目录下的安装包")


def main():
    """主函数"""
    print("🏗️  aestival Tauri 构建 (uv + nuitka)")
    print("=" * 50)
    
    args = sys.argv[1:]
    
    # 解析参数
    only_frontend = "--frontend" in args
    only_sidecar = "--sidecar" in args
    only_tauri = "--tauri" in args
    
    check_dependencies()
    print("")
    
    if only_frontend:
        print("🚀 仅构建前端...")
        if not build_frontend():
            sys.exit(1)
        return
    
    if only_sidecar:
        print("🚀 仅打包 Sidecar...")
        if not install_python_deps():
            sys.exit(1)
        if not build_python_sidecar():
            sys.exit(1)
        return
    
    if only_tauri:
        print("🚀 仅构建 Tauri...")
        if not build_tauri():
            sys.exit(1)
        return
    
    # 完整构建
    print("🚀 开始完整构建...\n")
    
    build_steps = [
        ("Python 依赖", install_python_deps),
        ("Python Sidecar", build_python_sidecar),
        ("前端构建", build_frontend),
        ("Tauri 应用", build_tauri)
    ]
    
    for step_name, step_func in build_steps:
        print(f"📋 步骤: {step_name}")
        if not step_func():
            print(f"\n❌ 构建失败: {step_name}")
            sys.exit(1)
        print("")
    
    show_build_results()


if __name__ == "__main__":
    main()
