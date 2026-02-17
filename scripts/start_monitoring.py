#!/usr/bin/env python
"""
Flower 监控启动脚本
跨平台 Flower 启动工具
"""

import os
import sys
import platform
import subprocess
from pathlib import Path


def get_skill_env():
    """获取技能虚拟环境"""
    skill_dir = Path(__file__).parent.parent
    venv_dir = skill_dir / ".venv"

    if not venv_dir.exists():
        raise RuntimeError(
            f"技能环境未找到: {venv_dir}\n"
            f"请先运行: python scripts/setup_env.py"
        )

    return venv_dir


def get_python_executable(venv_dir):
    """获取虚拟环境中的 Python 可执行文件"""
    system = platform.system()
    if system == "Windows":
        return venv_dir / "Scripts" / "python.exe"
    else:
        return venv_dir / "bin" / "python"


def start_flower(port=5555):
    """
    启动 Flower 监控服务

    Args:
        port: 监听端口，默认 5555
    """
    venv_dir = get_skill_env()
    python_exe = get_python_executable(venv_dir)

    # 构建 flower 命令
    cmd = [
        str(python_exe),
        "-m", "celery",
        "-A", "celery_tasks.worker",
        "flower",
        f"--port={port}"
    ]

    print(f"\n{'='*60}")
    print("启动 Flower 监控")
    print(f"{'='*60}")
    print(f"虚拟环境: {venv_dir}")
    print(f"Python: {python_exe}")
    print(f"端口: {port}")
    print(f"\n访问地址: http://localhost:{port}")
    print(f"\n按 Ctrl+C 停止 Flower")
    print(f"{'='*60}\n")

    try:
        # 启动 Flower（前台运行）
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\nFlower 已停止")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Flower 启动失败: {e}")
        sys.exit(1)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="启动 Flower 监控")
    parser.add_argument("--port", "-p", type=int, default=5555,
                       help="监听端口（默认: 5555）")

    args = parser.parse_args()

    start_flower(port=args.port)


if __name__ == "__main__":
    main()
