"""
Celery Worker 配置和任务定义
跨平台兼容的命令执行任务
"""

import os
import sys
import subprocess
import platform
from datetime import timedelta
from pathlib import Path
from celery import Celery

# 获取技能虚拟环境的 Python 路径（用于执行任务）
SKILL_PYTHON = sys.executable
SKILL_VENV_DIR = Path(sys.executable).parent.parent

# 创建 Celery 应用
app = Celery('celery_task')

# 基础配置
app.conf.update(
    # Broker 配置
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/1',

    # 序列化配置
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],

    # 时区配置
    timezone='Asia/Shanghai',
    enable_utc=True,

    # 任务确认策略（防止任务丢失）
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # 结果配置
    result_expires=86400,  # 24小时
    result_compression='gzip',
    result_extended=True,

    # 任务追踪
    task_track_started=True,
    task_send_sent_event=True,

    # 任务时间限制
    task_time_limit=3600,
    task_soft_time_limit=3000,

    # Worker 配置
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,

    # 日志配置
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
)


@app.task(bind=True, name='execute_command')
def execute_command(
    self,
    command,
    cwd=None,
    timeout=300,
    env_vars=None,
    shell=True,
    encoding='utf-8',
    capture_output=True
):
    """
    执行终端命令的通用任务

    Args:
        self: Celery 任务实例
        command (str): 要执行的命令
        cwd (str, optional): 工作目录
        timeout (int): 命令超时时间（秒）
        env_vars (dict, optional): 环境变量字典
        shell (bool): 是否使用 shell 执行
        encoding (str): 输出编码
        capture_output (bool): 是否捕获输出

    Returns:
        dict: 执行结果
    """
    import time
    start_time = time.time()

    result = {
        'command': command,
        'cwd': cwd or os.getcwd(),
        'platform': platform.system(),
        'skill_python': SKILL_PYTHON,  # 记录使用的 Python 路径
    }

    # 准备环境变量：确保子进程使用技能虚拟环境
    env = os.environ.copy()

    # 在 Windows 上，确保 PATH 优先使用技能虚拟环境
    if platform.system() == 'Windows':
        scripts_dir = str(SKILL_VENV_DIR / 'Scripts')
        # 将技能虚拟环境的 Scripts 目录放在 PATH 最前面
        path_list = [scripts_dir]
        if 'PATH' in env:
            path_list.append(env['PATH'])
        env['PATH'] = os.pathsep.join(path_list)

    if env_vars:
        env.update(env_vars)

    try:
        # 执行命令
        process = subprocess.run(
            command,
            shell=shell,
            cwd=cwd,
            env=env,
            capture_output=capture_output,
            text=True,
            encoding=encoding,
            timeout=timeout,
        )

        duration = time.time() - start_time

        result.update({
            'success': process.returncode == 0,
            'returncode': process.returncode,
            'stdout': process.stdout if capture_output else '',
            'stderr': process.stderr if capture_output else '',
            'duration': round(duration, 3),
        })

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        result.update({
            'success': False,
            'returncode': -2,
            'stdout': '',
            'stderr': f'命令执行超时（超过 {timeout} 秒）',
            'duration': round(duration, 3),
        })

    except FileNotFoundError as e:
        duration = time.time() - start_time
        result.update({
            'success': False,
            'returncode': -3,
            'stdout': '',
            'stderr': f'文件或目录不存在: {e}',
            'duration': round(duration, 3),
        })

    except Exception as e:
        duration = time.time() - start_time
        result.update({
            'success': False,
            'returncode': -4,
            'stdout': '',
            'stderr': str(e),
            'duration': round(duration, 3),
        })

    # 发送任务完成通知
    try:
        from celery_tasks.ntfy_notifier import notify_task_complete
        import sys
        sent = notify_task_complete('execute_command', command, result)
        # 输出通知发送状态到 stderr（会显示在 Worker 日志中）
        print(f'[ntfy] Notification sent: {sent}', file=sys.stderr)
    except ImportError as e:
        # ntfy 模块不可用，忽略
        import sys
        print(f'[ntfy] Import error: {e}', file=sys.stderr)
    except Exception as e:
        # 通知发送失败不影响任务结果
        import sys
        print(f'[ntfy] Send error: {e}', file=sys.stderr)

    return result


@app.task(name='ping')
def ping():
    """简单的心跳任务，用于测试 Worker 是否正常工作"""
    return {
        'status': 'pong',
        'message': 'Celery Worker is running!',
        'platform': platform.system(),
    }
