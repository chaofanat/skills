"""
Celery 配置模板
根据实际需求修改配置
"""

# Broker 配置
broker_url = 'redis://localhost:6379/0'

# 结果后端配置
result_backend = 'redis://localhost:6379/1'

# 序列化配置
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']

# 时区配置
timezone = 'Asia/Shanghai'
enable_utc = True

# 持久化相关配置
result_expires = 86400  # 24小时
task_ignore_result = False

# 任务确认策略（确保任务不丢失）
task_acks_late = True
task_reject_on_worker_lost = True

# 任务重试配置
task_acks_on_failure_or_timeout = True
task_send_sent_event = True

# 结果存储配置
result_compression = 'gzip'
result_extended = True

# 任务执行配置
task_time_limit = 3600  # 硬限制（秒）
task_soft_time_limit = 3000  # 软限制（秒）

# Worker 配置
worker_prefetch_multiplier = 1

# 任务结果追踪
task_track_started = True
task_send_sent_event = True

# 安全配置（可选）
# 允许执行的命令（白名单模式）
ALLOWED_COMMANDS = []

# 禁止执行的命令（黑名单）
FORBIDDEN_COMMANDS = [
    'rm -rf /',
    'del /f /s /q',
    'format',
    'shutdown',
    'reboot',
]

# 日志配置
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'
