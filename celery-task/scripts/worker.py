#!/usr/bin/env python
"""
Celery Worker 跨平台启动脚本
自动检测平台并使用正确的配置启动 Worker
"""

import os
import sys
import platform
import subprocess
from pathlib import Path


def get_skill_env():
    """获取技能虚拟环境路径"""
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


def start_worker(log_level="info", enable_events=True, concurrency="solo"):
    """
    启动 Celery Worker

    Args:
        log_level: 日志级别 (debug, info, warning, error)
        enable_events: 是否启用事件追踪（Flower 监控需要）
        concurrency: 并发模式 (solo, prefork, eventlet, gevent)
    """
    venv_dir = get_skill_env()
    python_exe = get_python_executable(venv_dir)

    # 构建 celery 命令
    cmd = [
        str(python_exe),
        "-m", "celery",
        "-A", "celery_tasks.worker",  # 使用技能中的 worker 模块
        "worker",
        "-l", log_level,
        f"--pool={concurrency}"
    ]

    # 启用事件追踪（用于 Flower 监控）
    if enable_events:
        cmd.append("-E")

    print(f"\n{'='*60}")
    print("启动 Celery Worker")
    print(f"{'='*60}")
    print(f"虚拟环境: {venv_dir}")
    print(f"Python: {python_exe}")
    print(f"日志级别: {log_level}")
    print(f"事件追踪: {'启用' if enable_events else '禁用'}")
    print(f"并发模式: {concurrency}")
    print(f"\n命令: {' '.join(cmd)}")
    print(f"\n按 Ctrl+C 停止 Worker")
    print(f"{'='*60}\n")

    try:
        # 启动 Worker（前台运行）
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\nWorker 已停止")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Worker 启动失败: {e}")
        sys.exit(1)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="启动 Celery Worker")
    parser.add_argument("-l", "--log-level", default="info",
                       choices=["debug", "info", "warning", "error"],
                       help="日志级别")
    parser.add_argument("--no-events", action="store_true",
                       help="禁用事件追踪（Flower 将无法监控）")
    parser.add_argument("--pool", default="solo",
                       choices=["solo", "prefork", "eventlet", "gevent"],
                       help="并发池类型")

    args = parser.parse_args()

    # Windows 推荐使用 solo pool
    system = platform.system()
    if system == "Windows" and args.pool != "solo":
        print("⚠ 警告: Windows 上推荐使用 solo pool")

    start_worker(
        log_level=args.log_level,
        enable_events=not args.no_events,
        concurrency=args.pool
    )


if __name__ == "__main__":
    main()
