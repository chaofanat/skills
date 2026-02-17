#!/usr/bin/env python
"""
Celery 任务派发脚本
跨平台任务派发工具
"""

import os
import sys
import json
import argparse
import platform
from pathlib import Path
from datetime import datetime, timedelta


# 添加技能路径
skill_dir = Path(__file__).parent.parent
sys.path.insert(0, str(skill_dir))


def get_skill_env():
    """获取技能虚拟环境"""
    venv_dir = skill_dir / ".venv"
    if not venv_dir.exists():
        raise RuntimeError("技能环境未设置，请先运行: python scripts/setup_env.py")
    return venv_dir


def get_python_executable():
    """获取虚拟环境 Python"""
    venv_dir = get_skill_env()
    system = platform.system()
    if system == "Windows":
        return venv_dir / "Scripts" / "python.exe"
    else:
        return venv_dir / "bin" / "python"


def import_worker():
    """导入 worker 模块"""
    try:
        from celery_tasks import worker
        return worker.app
    except ImportError as e:
        raise RuntimeError(f"无法导入 worker 模块: {e}")


def check_services_status():
    """检查服务状态"""
    import socket
    import subprocess

    print(f"\n{'='*60}")
    print("检查服务状态")
    print(f"{'='*60}")

    # 检查 Redis
    redis_ok = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        redis_ok = sock.connect_ex(('localhost', 6379)) == 0
        sock.close()
    except Exception:
        pass

    if redis_ok:
        print("  ✓ Redis/Memurai: 运行中")
    else:
        print("  ✗ Redis/Memurai: 未运行")
        if platform.system() == "Windows":
            print("    启动: net start Memurai")
        else:
            print("    启动: sudo systemctl start redis")

    # 检查 Celery Worker
    worker_ok = False
    try:
        from celery_tasks import worker
        inspector = worker.app.control.inspect(timeout=3)
        stats = inspector.stats()
        worker_ok = stats is not None and len(stats) > 0
        if worker_ok:
            print(f"  ✓ Celery Worker: 运行中 ({list(stats.keys())[0]})")
    except Exception as e:
        pass

    if not worker_ok:
        print("  ✗ Celery Worker: 未运行")
        print("    启动: python scripts/worker.py")

    # 检查 Flower（默认启动）
    flower_ok = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        flower_ok = sock.connect_ex(('localhost', 5555)) == 0
        sock.close()
    except Exception:
        pass

    if flower_ok:
        print("  ✓ Flower 监控: 运行中 (http://localhost:5555)")
    else:
        print("  ⚠ Flower 监控: 未运行，正在自动启动...")
        # 自动启动 Flower
        try:
            skill_dir = Path(__file__).parent.parent
            start_script = skill_dir / "scripts" / "start_monitoring.py"
            subprocess.Popen(
                [sys.executable, str(start_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            # 等待 Flower 启动
            import time
            for _ in range(10):
                time.sleep(0.5)
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.5)
                    if sock.connect_ex(('localhost', 5555)) == 0:
                        sock.close()
                        print("  ✓ Flower 监控: 已启动 (http://localhost:5555)")
                        flower_ok = True
                        break
                    sock.close()
                except Exception:
                    continue
            if not flower_ok:
                print("  ⚠ Flower 启动中，请稍后访问 http://localhost:5555")
        except Exception as e:
            print(f"  ✗ Flower 启动失败: {e}")

    print(f"{'='*60}\n")

    # Redis 和 Worker 必须运行
    if not redis_ok or not worker_ok:
        print("✗ 关键服务未运行，请先启动服务后再派发任务")
        return False

    return True


def dispatch_command(command, delay=None, eta=None, background=False, **kwargs):
    """
    派发命令执行任务

    Args:
        command: 要执行的命令
        delay: 延迟秒数
        eta: 指定执行时间 (ISO-8601 格式)
        background: 是否后台派发（不等待结果）
        **kwargs: 其他任务参数
    """
    # 检查服务状态
    if not check_services_status():
        return None

    app = import_worker()
    from celery_tasks.worker import execute_command

    # 准备任务参数
    task_args = [command]
    task_options = {}

    # 移除 None 值
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    # 设置延迟或定时执行
    if delay:
        task_options['countdown'] = delay
    elif eta:
        # 解析时间并添加时区（修复时区不匹配问题）
        from zoneinfo import ZoneInfo
        eta_dt = datetime.fromisoformat(eta)
        eta_dt = eta_dt.replace(tzinfo=ZoneInfo('Asia/Shanghai'))
        task_options['eta'] = eta_dt

    print(f"\n{'='*60}")
    print("派发任务")
    print(f"{'='*60}")
    print(f"命令: {command}")

    if delay:
        print(f"延迟: {delay} 秒")
        now = datetime.now()
        execute_time = now + timedelta(seconds=delay)
        print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"预计执行: {execute_time.strftime('%Y-%m-%d %H:%M:%S')}")
    elif eta:
        print(f"执行时间: {eta}")

    # 派发任务
    async_result = execute_command.apply_async(
        args=task_args,
        kwargs=kwargs,
        **task_options
    )

    print(f"\n✓ 任务已派发")
    print(f"  任务 ID: {async_result.id}")
    print(f"  状态: {async_result.state}")

    # Flower 监控地址提示
    print(f"\n🌸 Flower 监控: http://localhost:5555")
    print(f"  (如未启动，运行: python scripts/start_monitoring.py)")

    if background:
        print(f"\n后台派发完成")
        print(f"\n使用以下命令查询结果:")
        print(f"  python scripts/dispatch.py --task-id {async_result.id}")
        return async_result.id

    # 等待结果
    print(f"\n等待执行...")
    try:
        timeout = kwargs.get('timeout', 300) + (delay or 0) + 10
        result = async_result.get(timeout=timeout)

        print(f"\n{'='*60}")
        print("执行完成")
        print(f"{'='*60}")
        print(f"成功: {result['success']}")
        print(f"返回码: {result['returncode']}")
        print(f"耗时: {result['duration']} 秒")

        if result.get('stdout'):
            print(f"\n--- 输出 ---")
            print(result['stdout'][:1000])
            if len(result['stdout']) > 1000:
                print(f"\n... (已截断，完整输出 {len(result['stdout'])} 字符)")

        if result.get('stderr'):
            print(f"\n--- 错误 ---")
            print(result['stderr'])

    except Exception as e:
        print(f"\n✗ 获取结果失败: {e}")
        return None

    return async_result.id


def check_task_status(task_id):
    """检查任务状态"""
    app = import_worker()
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=app)

    print(f"\n{'='*60}")
    print("任务状态")
    print(f"{'='*60}")
    print(f"任务 ID: {task_id}")
    print(f"状态: {result.state}")
    print(f"信息: {result.info}")

    if result.ready():
        print(f"\n任务已完成，获取结果...")
        try:
            task_result = result.get(timeout=10)
            print(f"成功: {task_result['success']}")
            print(f"返回码: {task_result['returncode']}")
            if task_result.get('stdout'):
                print(f"\n输出: {task_result['stdout'][:500]}")
        except Exception as e:
            print(f"获取结果失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Celery 任务派发工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('command', nargs='?', help='要执行的命令')
    parser.add_argument('--delay', '-d', type=int, metavar='SECONDS',
                       help='延迟执行（秒）')
    parser.add_argument('--eta', metavar='TIME',
                       help='指定执行时间 (格式: YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--bg', '--background', action='store_true',
                       help='后台派发，不等待结果')
    parser.add_argument('--timeout', '-t', type=int, default=300,
                       help='命令执行超时时间（秒）')
    parser.add_argument('--task-id', metavar='ID',
                       help='查询指定任务的状态')
    parser.add_argument('--cwd', metavar='DIR',
                       help='工作目录')

    args = parser.parse_args()

    # 查询任务状态
    if args.task_id:
        check_task_status(args.task_id)
        return

    # 派发任务
    if not args.command:
        parser.error("需要指定命令或使用 --task-id 查询任务")

    dispatch_command(
        command=args.command,
        delay=args.delay,
        eta=args.eta,
        background=args.bg,
        timeout=args.timeout,
        cwd=args.cwd
    )


if __name__ == "__main__":
    main()
