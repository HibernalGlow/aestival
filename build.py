#!/usr/bin/env python3
"""
aestival 构建脚本
支持 Tauri 桌面应用打包（Python Sidecar + Rust 前端）
"""
import json
import sys
import subprocess
import platform
import shutil
from pathlib import Path


def run_command(command, description, cwd=None):
    """运行命令并显示状态"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        print(f"✅ {description} 完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失败!")
        print(f"错误: {e.stderr}")
        return False


def check_dependencies():
    """检查必要的依赖"""
    print("🔍 检查依赖...")
    
    required_tools = {
        "yarn": "yarn --version",
        "python": "python --version",
        "pip": "pip --version",
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
    """安装 Python 依赖"""
    return run_command(
        "pip install -r requirements.txt",
        "安装 Python 依赖",
        cwd="src-python"
    )


def build_python_sidecar():
    """使用 PyInstaller 打包 Python Sidecar"""
    platform_name = detect_platform()
    
    # 检查 PyInstaller
    try:
        subprocess.run("pyinstaller --version", shell=True, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("📦 安装 PyInstaller...")
        if not run_command("pip install pyinstaller", "安装 PyInstaller"):
            return False
    
    # 确保输出目录存在
    bin_dir = Path("src-tauri/bin")
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    # Sidecar 名称（Tauri 要求特定格式）
    sidecar_name = "main"
    
    # 根据平台添加后缀
    if platform_name == "windows":
        # Windows 需要 -x86_64-pc-windows-msvc 后缀
        target_suffix = "-x86_64-pc-windows-msvc"
    elif platform_name == "macos":
        # macOS 需要架构后缀
        import platform as plat
        arch = plat.machine()
        if arch == "arm64":
            target_suffix = "-aarch64-apple-darwin"
        else:
            target_suffix = "-x86_64-apple-darwin"
    else:
        # Linux
        target_suffix = "-x86_64-unknown-linux-gnu"
    
    # PyInstaller 构建命令
    pyinstaller_cmd = [
        "pyinstaller",
        "--name", sidecar_name,
        "--onefile",
        "--clean",
        "--distpath", str(bin_dir.absolute()),
        "main.py"
    ]
    
    cmd_str = " ".join(pyinstaller_cmd)
    if not run_command(cmd_str, f"打包 Python Sidecar ({platform_name})", cwd="src-python"):
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
    print("🏗️  aestival Tauri 构建")
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
