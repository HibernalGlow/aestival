"""
aestival-backend 包入口点
支持通过 python -m aestival_backend 启动

用法:
    python -m aestival_backend              # sidecar 模式（Tauri 调用）
    python -m aestival_backend --standalone # 开发模式（热重载）
"""

import sys
import os

# 将父目录添加到 path，以便导入 main 模块
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from main import RUNNING_MODE, run_sidecar, run_standalone, run_pywebview


def main():
    """主入口函数"""
    if RUNNING_MODE == "pywebview":
        run_pywebview()
    elif RUNNING_MODE == "standalone":
        run_standalone()
    else:
        run_sidecar()


if __name__ == "__main__":
    main()
