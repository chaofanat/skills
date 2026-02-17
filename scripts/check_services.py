#!/usr/bin/env python
"""
服务状态检查脚本
检查 Redis、Celery Worker、Flower 服务状态
"""

import sys
import platform
import socket
import subprocess
from pathlib import Path


# 添加技能路径
skill_dir = Path(__file__).parent.parent
sys.path.insert(0, str(skill_dir))


def check_redis_connection(host='localhost', port=6379, timeout=2):
    """检查 Redis 连接是否可用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_redis_process():
    """检查 Redis/Memurai 进程是否运行"""
    system = platform.system()

    try:
        if system == "Windows":
            result = subprocess.run(
                ['tasklist'],
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='ignore'
            )
            output = result.stdout.lower()
            return 'memurai.exe' in output or 'redis-server.exe' in output
        else:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )
            output = result.stdout.lower()
            return 'redis-server' in output or 'memurai' in output
    except Exception:
        return False


def check_celery_worker():
    """检查 Celery Worker 是否运行"""
    system = platform.system()

    try:
        if system == "Windows":
            # 使用 PowerShell 获取进程命令行（替代已弃用的 wmic）
            cmd = [
                'powershell', '-Command',
                'Get-CimInstance Win32_Process -Filter "Name=\'python.exe\'" | '
                'Select-Object CommandLine | ConvertTo-Json'
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            output = result.stdout.lower()
            # 检查是否有 celery worker 进程
            return 'celery' in output and 'worker' in output
        else:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )
            output = result.stdout.lower()
            # 检查是否有 celery worker 进程
            return 'celery' in output and 'worker' in output
    except Exception:
        return False


def check_celery_worker_ping():
    """通过 Celery ping 检查 Worker 是否响应"""
    try:
        from celery_tasks import worker
        import time

        # 尝试 ping worker
        inspector = worker.app.control.inspect(timeout=2)
        stats = inspector.stats()

        if stats:
            # 有 worker 响应
            return True, list(stats.keys())
        return False, []
    except Exception as e:
        return False, []


def check_flower(host='localhost', port=5555, timeout=2):
    """检查 Flower 是否运行"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            # 尝试 HTTP 请求
            import urllib.request
            try:
                response = urllib.request.urlopen(f'http://{host}:{port}/', timeout=2)
                return response.status == 200
            except Exception:
                return True  # 端口开放但可能不是 HTTP
        return False
    except Exception:
        return False


def print_status(name, status, detail=None):
    """打印状态信息"""
    if status:
        print(f"  ✓ {name}: 运行中")
        if detail:
            print(f"    {detail}")
    else:
        print(f"  ✗ {name}: 未运行")


def main():
    """主函数"""
    print(f"\n{'='*60}")
    print("Celery 服务状态检查")
    print(f"{'='*60}\n")

    all_ok = True

    # 检查 Redis
    print("Redis/Memurai:")
    redis_process = check_redis_process()
    redis_conn = check_redis_connection()
    print_status("进程", redis_process)
    print_status("连接", redis_conn)
    if not redis_process or not redis_conn:
        all_ok = False
        if platform.system() == "Windows":
            print("\n  启动命令: net start Memurai")
            print("  或直接运行: memurai.exe")
        else:
            print("\n  启动命令: sudo systemctl start redis")
    print()

    # 检查 Celery Worker
    print("Celery Worker:")
    worker_process = check_celery_worker()
    worker_ping, workers = check_celery_worker_ping()
    print_status("进程", worker_process)
    print_status("响应", worker_ping, f"Worker: {', '.join(workers) if workers else '无'}")
    if not worker_ping:
        all_ok = False
        print("\n  启动命令: python scripts/worker.py")
    print()

    # 检查 Flower（可选服务）
    print("Flower 监控:")
    flower_status = check_flower()
    print_status("服务", flower_status)
    # Flower 不影响 all_ok，是可选服务
    if not flower_status:
        print("\n  启动命令: python scripts/start_monitoring.py")
        print(f"  访问地址: http://localhost:5555")
    print()

    # 总结
    print(f"{'='*60}")
    if all_ok:
        print("✓ 所有服务运行正常")
    else:
        print("✗ 部分服务未运行，请先启动后再派发任务")
    print(f"{'='*60}\n")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
