# Celery 跨平台部署指南

## 目录

1. [系统要求](#系统要求)
2. [Redis 安装](#redis-安装)
3. [平台差异](#平台差异)
4. [常见问题](#常见问题)

---

## 系统要求

### 通用要求

- Python 3.8+
- pip 包管理器
- 网络连接（用于安装依赖）

### 平台特定要求

| 平台 | 最低版本 | 备注 |
|------|----------|------|
| Windows | Windows 10+ | 需要 Memurai |
| Linux | 内核 3.10+ | 支持 Redis |
| macOS | 10.14+ | 支持 Redis |

---

## Redis 安装

### Windows

**使用 Memurai（推荐）**

Memurai 是 Redis 的 Windows 原生版本，完全兼容 Redis 协议。

1. 访问 https://www.memurai.com/get-memurai
2. 下载 Memurai Developer（免费）
3. 运行安装程序
4. 启动服务：
   ```bash
   net start Memurai
   ```

**验证安装：**
```bash
memurai-cli ping
# 应返回: PONG
```

### Linux

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**CentOS/RHEL:**
```bash
sudo yum install redis
sudo systemctl start redis
sudo systemctl enable redis
```

**验证安装：**
```bash
redis-cli ping
# 应返回: PONG
```

### macOS

**使用 Homebrew:**
```bash
brew install redis
brew services start redis
```

**验证安装：**
```bash
redis-cli ping
# 应返回: PONG
```

---

## 平台差异

### 路径分隔符

| 平台 | 分隔符 | 示例 |
|------|--------|------|
| Windows | `\` | `C:\path\to\file` |
| Linux/macOS | `/` | `/path/to/file` |

**跨平台处理：**
```python
import os
# 使用 os.path.join 自动处理
config_path = os.path.join("config", "app.conf")

# 或使用 pathlib（推荐）
from pathlib import Path
config_path = Path("config") / "app.conf"
```

### Python 虚拟环境

| 平台 | Scripts 目录 | Python 可执行文件 |
|------|--------------|------------------|
| Windows | `Scripts/` | `venv\Scripts\python.exe` |
| Linux/macOS | `bin/` | `venv/bin/python` |

**跨平台检测：**
```python
import platform
import sys
from pathlib import Path

system = platform.system()
venv = Path(".venv")

if system == "Windows":
    python_exe = venv / "Scripts" / "python.exe"
else:
    python_exe = venv / "bin" / "python"
```

### 后台运行

**Windows:**
```bash
start "Celery Worker" cmd /k "python scripts/worker.py"
```

**Linux/macOS:**
```bash
python scripts/worker.py &
# 或使用 nohup
nohup python scripts/worker.py > worker.log 2>&1 &
```

### 服务管理

**Windows:**
```bash
# 安装服务
memurai --service-install

# 启动服务
net start Memurai

# 停止服务
net stop Memurai
```

**Linux (systemd):**
```bash
# 启动服务
sudo systemctl start redis

# 停止服务
sudo systemctl stop redis

# 查看状态
sudo systemctl status redis
```

**macOS (launchctl):**
```bash
# 启动服务
brew services start redis

# 停止服务
brew services stop redis

# 重启服务
brew services restart redis
```

---

## 并发池选择

### 平台推荐

| 平台 | 推荐池 | 说明 |
|------|--------|------|
| Windows | `solo` | 单线程，避免 fork 问题 |
| Linux | `prefork` | 多进程，充分利用多核 |
| macOS | `solo` 或 `prefork` | 根据任务类型选择 |

### 并发池类型

| 池类型 | 说明 | 适用场景 |
|--------|------|----------|
| `solo` | 单线程执行 | CPU 密集型、Windows |
| `prefork` | 多进程执行 | IO 密集型、Linux |
| `eventlet` | 协程（需安装） | 高并发网络任务 |
| `gevent` | 协程（需安装） | 高并发网络任务 |

---

## 常见问题

### Q: Windows 上 Worker 无法启动

**A:** 确保使用 `solo` pool：
```bash
python scripts/worker.py --pool solo
```

### Q: 任务执行失败，找不到命令

**A:** 使用完整路径：
```python
# Windows
execute_command.delay(r'C:\path\to\command.exe args')

# Linux/macOS
execute_command.delay('/path/to/command args')
```

### Q: 延时任务不执行

**A:** 检查时区配置，使用 `countdown` 参数：
```python
# 推荐
execute_command.apply_async(args=['command'], countdown=60)

# 或使用 UTC 时间
from datetime import datetime, timedelta
eta = datetime.utcnow() + timedelta(minutes=1)
execute_command.apply_async(args=['command'], eta=eta)
```

### Q: Flower 显示统计为 0

**A:** 确保 Worker 启用了事件追踪：
```bash
python scripts/worker.py  # 默认启用 -E
```

### Q: Redis 连接被拒绝

**A:**
1. 检查 Redis 是否运行：
   - Windows: `memurai-cli ping`
   - Linux/macOS: `redis-cli ping`

2. 检查端口占用：
   ```bash
   netstat -an | grep 6379  # Linux/macOS
   netstat -an | findstr 6379  # Windows
   ```

3. 检查防火墙设置

### Q: 虚拟环境激活后命令找不到

**A:** 使用完整路径调用 Python：
```bash
# 直接调用
/path/to/.venv/bin/python script.py

# 或使用 python -m
.venv/bin/python -m module
```

---

## 快速参考

### 检查系统信息

```python
import platform
import sys

print(f"系统: {platform.system()}")
print(f"版本: {platform.release()}")
print(f"Python: {sys.version}")
print(f"架构: {platform.machine()}")
```

### 跨平台命令执行

```python
import subprocess
import shlex
import platform

def run_command(command):
    system = platform.system()

    if system == "Windows":
        # Windows: 使用 shell=True
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
    else:
        # Linux/macOS: 使用 shlex 安全分割
        args = shlex.split(command)
        result = subprocess.run(
            args,
            capture_output=True,
            text=True
        )

    return result
```

### 跨平台路径处理

```python
from pathlib import Path

# 获取用户主目录
home = Path.home()

# 获取当前工作目录
cwd = Path.cwd()

# 构建路径
config = cwd / "config" / "app.conf"

# 检查路径存在
if config.exists():
    content = config.read_text()
```
