# Celery 配置参考

## 目录

1. [核心配置](#核心配置)
2. [Broker 配置](#broker-配置)
3. [结果后端配置](#结果后端配置)
4. [任务配置](#任务配置)
5. [Worker 配置](#worker-配置)
6. [时区配置](#时区配置)

---

## 核心配置

### 最小配置

```python
from celery import Celery

app = Celery('myapp')
app.config_from_object('celery_config')
```

### 基础配置项

```python
# Broker URL
broker_url = 'redis://localhost:6379/0'

# 结果后端
result_backend = 'redis://localhost:6379/1'

# 序列化方式
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
```

---

## Broker 配置

### Redis Broker

```python
# 基础配置
broker_url = 'redis://localhost:6379/0'

# 带密码
broker_url = 'redis://:password@localhost:6379/0'

# 带数据库
broker_url = 'redis://localhost:6379/0'

# 完整配置
broker_url = 'redis://:password@localhost:6379/0'
broker_connection_retry_on_startup = True
broker_connection_max_retries = 5
```

### 连接池配置

```python
broker_pool_limit = 10  # 连接池大小
broker_connection_timeout = 30  # 连接超时（秒）
```

---

## 结果后端配置

### Redis 后端

```python
result_backend = 'redis://localhost:6379/1'

# 结果过期时间
result_expires = 86400  # 24小时

# 压缩结果
result_compression = 'gzip'

# 扩展结果信息
result_extended = True
```

### 结果编码

```python
result_serializer = 'json'
result_accept_content = ['json']
```

### 结果追踪

```python
# 任务结果追踪
task_track_started = True
task_send_sent_event = True

# 忽略结果
task_ignore_result = False
```

---

## 任务配置

### 任务确认策略

```python
# 任务完成后才确认（防止任务丢失）
task_acks_late = True

# Worker 断线时重新入队
task_reject_on_worker_lost = True

# 失败时确认
task_acks_on_failure_or_timeout = True
```

### 任务重试

```python
# 默认重试配置
task_autoretry_for = (Exception,)
task_retry_kwargs = {'max_retries': 3, 'countdown': 60}

# 重试延迟
task_default_retry_delay = 60  # 秒
task_max_retries = 3
```

### 任务执行限制

```python
# 执行时间限制（秒）
task_time_limit = 3600  # 硬限制
task_soft_time_limit = 3000  # 软限制

# 任务过期
taskExpires = 3600  # 任务本身过期
```

### 任务路由

```python
# 简单路由
task_routes = {
    'tasks.heavy_task': {'queue': 'heavy'},
    'tasks.light_task': {'queue': 'light'},
}

# 高级路由
task_routes = {
    'tasks.*': {
        'queue': 'default',
        'exchange': 'default',
        'routing_key': 'default',
    }
}
```

### 任务优先级

```python
# 任务优先级范围 0-9（9 最高）
task_default_priority = 5
```

---

## Worker 配置

### 并发配置

```python
# 预取任务数量
worker_prefetch_multiplier = 1

# 并发数量（自动检测）
worker_concurrency = None  # None = CPU 核心数

# 最大任务数
worker_max_tasks_per_child = 1000
```

### Worker 性能

```python
# 优化性能
worker_disable_rate_limits = False
worker_max_memory_per_child = 200000  # KB
```

### Worker 日志

```python
# 日志格式
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# 日志级别
worker_log_color = True
```

---

## 时区配置

### 启用 UTC

```python
# 使用 UTC 时间
enable_utc = True
timezone = 'UTC'
```

### 使用本地时区

```python
# 使用本地时区
enable_utc = False
timezone = 'Asia/Shanghai'
```

### 常用时区

```python
timezone = 'Asia/Shanghai'  # 北京时间
timezone = 'Asia/Tokyo'      # 东京时间
timezone = 'America/New_York'  # 纽约时间
timezone = 'Europe/London'     # 伦敦时间
```

---

## 完整配置示例

### 基础配置

```python
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/1'

task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']

timezone = 'Asia/Shanghai'
enable_utc = True

task_acks_late = True
task_reject_on_worker_lost = True
```

### 生产配置

```python
broker_url = 'redis://:password@localhost:6379/0'
result_backend = 'redis://:password@localhost:6379/1'

task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']

timezone = 'Asia/Shanghai'
enable_utc = True

result_expires = 86400
result_compression = 'gzip'
result_extended = True

task_acks_late = True
task_reject_on_worker_lost = True
task_track_started = True
task_send_sent_event = True

task_time_limit = 3600
task_soft_time_limit = 3000

worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000

worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'
```

---

## 配置文件加载

### 从对象加载

```python
app.config_from_object('celery_config')
```

### 从字典加载

```python
app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/1',
    task_serializer='json',
)
```

### 从环境变量加载

```python
import os

app.conf.broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
app.conf.result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
```

---

## 环境变量

```bash
# Broker
export CELERY_BROKER_URL='redis://localhost:6379/0'

# 结果后端
export CELERY_RESULT_BACKEND='redis://localhost:6379/1'

# 时区
export TZ='Asia/Shanghai'
```

---

## 配置验证

### 检查配置

```python
from celery import Celery

app = Celery('myapp')
app.config_from_object('celery_config')

# 打印配置
print(app.conf)
```

### 验证 Broker 连接

```python
from celery import Celery

app = Celery('myapp', broker='redis://localhost:6379/0')

try:
    app.connection().ensure_connection(max_retries=3)
    print("✓ Broker 连接成功")
except Exception as e:
    print(f"✗ Broker 连接失败: {e}")
```
