---
name: celery-task
description: Celery 异步任务派发和管理技能，支持跨平台部署（Windows/Linux/macOS）。提供独立的技能环境自动配置、命令执行任务、延时调度、任务监控等功能。适用场景：(1) 异步执行命令或脚本，(2) 延时或定时执行任务，(3) 任务队列管理和监控，(4) 分布式任务处理。内置跨平台兼容处理，自动检测系统类型并适配配置。**三个必要服务**：Redis/Memurai、Celery Worker、Flower 监控都是必要的，任何一个未运行都应该自动启动。**AI 助手自动启动服务**：派发任务前自动检查并启动未运行的任何服务，无需用户手动干预。使用前需先安装 Redis/Memurai（Windows）。
---
# Celery 任务派发技能

> Celery 异步任务管理和派发技能，支持跨平台部署和独立技能环境。

> **⚠️ 重要提醒**
>
> 本技能使用**独立的虚拟环境**（`.venv`），所有命令必须使用技能虚拟环境中的 Python 执行，**不能使用系统 Python**。
>
> | 系统        | Python 路径                  |
> | ----------- | ---------------------------- |
> | Windows     | `.venv\Scripts\python.exe` |
> | Linux/macOS | `.venv/bin/python`         |

## 目录

- [快速开始](#快速开始)
- [核心概念](#核心概念)
- [脚本工具](#脚本工具)
- [定时任务](#定时任务)
- [使用场景](#使用场景)
- [配置说明](#配置说明)
- [ntfy 通知推送](#ntfy-通知推送)
- [跨平台支持](#跨平台支持)
- [常见问题](#常见问题)

---

## 快速开始

### 首次使用

**1. 安装 Redis**

| 系统              | 安装方式                                    | 启动命令                       |
| ----------------- | ------------------------------------------- | ------------------------------ |
| **Windows** | [Memurai](https://www.memurai.com/get-memurai) | `net start Memurai`          |
| **Linux**   | `sudo apt-get install redis-server`       | `sudo systemctl start redis` |
| **macOS**   | `brew install redis`                      | `brew services start redis`  |

**2. 设置技能环境**

```bash
# 进入技能目录
cd C:\Users\YourName\.claude\skills\celery-task    # Windows(建议使用powershell语法)
cd ~/.claude/skills/celery-task                    # Linux/macOS

# 使用系统 Python 创建技能虚拟环境
python scripts/setup_env.py
```

### 日常使用

> **⚠️ 三个必要服务**
>
> 技能需要以下**三个服务同时运行**才能正常工作：
> - **Redis/Memurai**：消息队列和任务存储
> - **Celery Worker**：任务执行进程
> - **Flower 监控**：Web 监控界面
>
> **🤖 AI 助手职责**：检查服务状态时，如果发现任何一个服务未运行，必须立即启动它。三个服务都是必要的，缺一不可。

**1. 进入技能目录**

```bash
# Windows
cd C:\Users\YourName\.claude\skills\celery-task

# Linux/macOS
cd ~/.claude/skills/celery-task
```

**2. 检查服务状态**

```bash
# Windows（技能目录下）
.venv\Scripts\python.exe scripts/check_services.py

# Linux/macOS（技能目录下）
.venv/bin/python scripts/check_services.py
```

**3. 启动 Worker（后台运行）**

> **🤖 AI 助手自动处理**：当检测到 Worker 未运行时，AI 助手应自动在后台启动 Worker。

```bash
# Windows（技能目录下）- 后台运行
.venv\Scripts\python.exe scripts/worker.py

# Linux/macOS（技能目录下）- 后台运行
.venv/bin/python scripts/worker.py
```

> **提示**：Worker 需要持续运行。使用后台运行模式，无需保持终端窗口开启。

**4. 启动 Flower 监控（后台运行）**

> **🤖 AI 助手自动处理**：当检测到 Flower 监控未运行时，AI 助手应自动在后台启动 Flower。

```bash
# Windows（技能目录下）
.venv\Scripts\python.exe scripts/start_monitoring.py

# Linux/macOS（技能目录下）
.venv/bin/python scripts/start_monitoring.py
```

**5. 派发任务预检查**

用户要求派发任务执行的任何命令或者脚本或者你自己编写的 Python 脚本在派发任务前必须先运行一遍以保证不会出错，如果当前不适合直接运行，编写可从其他角度验证任务命令是否正确的脚本进行验证。(额外的验证脚本验证完成后需要删除)

**6. 派发任务**

> **🤖 AI 助手自动处理**：
> - 派发任务前检查服务状态
> - 发现**任何一个服务未运行**时，**自动启动**该服务
> - 三个必要服务：Redis/Memurai、Celery Worker、Flower 监控
> - 不应要求用户手动启动服务
> - 只有在无法自动启动（如权限问题）时才提示用户

```bash
# Windows（技能目录下） - 立即执行
.venv\Scripts\python.exe scripts/dispatch.py "echo 'Hello'"

# Windows（技能目录下） - 延迟执行（推荐使用 --bg）
.venv\Scripts\python.exe scripts/dispatch.py "echo 'Hello'" --delay 60 --bg

# Linux/macOS（技能目录下）
.venv/bin/python scripts/dispatch.py "echo 'Hello'"
.venv/bin/python scripts/dispatch.py "echo 'Hello'" --delay 60 --bg
```

*注意：派发完成任务后，需要立即检查任务状态，确认任务是否已被接受，另外再次告诉用户可以访问 http://localhost:5555 查看任务状态。*

### 在项目环境执行命令

当需要执行项目中的命令时，使用完整路径指定项目的可执行文件。示例：

```bash
# 派发前先测试命令
"C:\project\.venv\Scripts\aishare.exe" 002957

# 确认可执行后派发（使用技能虚拟环境）
.venv\Scripts\python.exe scripts/dispatch.py "C:\project\.venv\Scripts\aishare.exe 002957" --delay 60 --bg
```

> 详见 [跨平台部署指南](references/platform-guide.md)

---

## 核心概念

### 三个必要服务

| 服务              | 作用                           | 必要性             |
| ----------------- | ------------------------------ | ------------------ |
| **Redis/Memurai** | 消息队列和任务存储             | ✅ 必要            |
| **Celery Worker** | 执行任务的进程，需要持续运行   | ✅ 必要            |
| **Flower 监控**   | Web 监控界面，实时查看任务状态 | ✅ 必要            |

> **重要**：三个服务都是必要的，任何一个未运行都会影响技能的正常使用。AI 助手必须确保所有服务都在运行。

### 其他概念

| 术语                   | 说明                               |
| ---------------------- | ---------------------------------- |
| **countdown**    | 延迟执行参数（秒），推荐使用       |
| **eta**          | 指定具体执行时间（一次性定时任务）   |
| **solo pool**    | 单进程并发模式（Windows 默认）     |
| **prefork pool** | 多进程并发模式（Linux/macOS 默认） |

---

## 脚本工具

> **前提条件**：执行以下命令前，必须先进入技能目录。
>
> **Windows：**
>
> ```bash
> cd C:\Users\YourName\.claude\skills\celery-task
> ```
>
> **Linux/macOS：**
>
> ```bash
> cd ~/.claude/skills/celery-task
> ```
>
> 然后使用技能虚拟环境的 Python 执行脚本。

### setup_env.py - 环境设置

```bash
# 使用系统 Python 创建技能虚拟环境
python scripts/setup_env.py
```

自动创建虚拟环境并安装依赖（celery、redis、flower）。

### worker.py - 启动 Worker

```bash
# Windows（技能目录下）
.venv\Scripts\python.exe scripts/worker.py

# Linux/macOS（技能目录下）
.venv/bin/python scripts/worker.py

# 调试模式（技能目录下）
.venv\Scripts\python.exe scripts/worker.py -l debug

# 禁用事件追踪（技能目录下）
.venv\Scripts\python.exe scripts/worker.py --no-events
```

> **注意**：Worker 需要在新终端窗口中保持运行。

### dispatch.py - 任务派发

```bash
# Windows（技能目录下）
.venv\Scripts\python.exe scripts/dispatch.py "command"
.venv\Scripts\python.exe scripts/dispatch.py "command" --delay 60 --bg
.venv\Scripts\python.exe scripts/dispatch.py --task-id <task-id>

# Linux/macOS（技能目录下）
.venv/bin/python scripts/dispatch.py "command"
.venv/bin/python scripts/dispatch.py "command" --delay 60 --bg
.venv/bin/python scripts/dispatch.py --task-id <task-id>
```

**参数说明：**

| 参数                   | 说明                                |
| ---------------------- | ----------------------------------- |
| `command`            | 要执行的命令（必填）                |
| `--delay, -d`        | 延迟执行（秒）                      |
| `--eta`              | 指定执行时间（YYYY-MM-DD HH:MM:SS） |
| `--bg, --background` | 后台派发，不等待结果                |
| `--timeout, -t`      | 命令超时时间（秒，默认 300）        |
| `--cwd`              | 指定工作目录                        |
| `--task-id`          | 查询指定任务状态                    |

### check_services.py - 服务检查

```bash
# Windows（技能目录下）
.venv\Scripts\python.exe scripts/check_services.py

# Linux/macOS（技能目录下）
.venv/bin/python scripts/check_services.py
```

**检查内容：**

- Redis/Memurai 进程和连接状态
- Celery Worker 进程和响应状态
- Flower 监控服务状态

> **重要**：三个服务都是必要的。如果检查结果显示任何服务未运行，AI 助手必须立即启动该服务。

### start_monitoring.py - 启动监控

> **重要**：Flower 监控是三个必要服务之一。如果未运行，AI 助手必须启动它。

```bash
# Windows（技能目录下）
.venv\Scripts\python.exe scripts/start_monitoring.py

# Linux/macOS（技能目录下）
.venv/bin/python scripts/start_monitoring.py

# 自定义端口（技能目录下）
.venv\Scripts\python.exe scripts/start_monitoring.py --port 8888
```

访问地址：http://localhost:5555

---

## 使用场景

### 定时任务（使用 eta 参数）

使用 `--eta` 参数指定任务的具体执行时间（一次性执行）：

```bash
# Windows - 明天早上8点执行
.venv\Scripts\python.exe scripts/dispatch.py "backup.py" --eta "2026-02-16 08:00:00" --bg

# Linux/macOS - 下周一早上9点执行
.venv/bin/python scripts/dispatch.py "weekly_report.py" --eta "2026-02-17 09:00:00" --bg

# 2小时后执行
.venv\Scripts\python.exe scripts/dispatch.py "python system_update.py" --delay 7200 --bg
```

**eta 参数说明**：
- 指定具体执行时间（格式：`YYYY-MM-DD HH:MM:SS`）
- 任务只执行**一次**，执行完毕后结束
- 适合临时性延迟任务（如"明天下午3点执行"、"下周执行"）
- 配合 `--bg` 参数使用，派发后立即返回

---

---

> **前提条件**：执行以下命令前，必须先进入技能目录并使用技能虚拟环境的 Python。
>
> **Windows：**
>
> ```bash
> cd C:\Users\YourName\.claude\skills\celery-task
> ```
>
> **Linux/macOS：**
>
> ```bash
> cd ~/.claude/skills/celery-task
> ```

### 场景 1：在项目环境中执行命令

**区分命令行工具和 Python 模块：**

```bash
# 命令行工具 - 直接使用完整路径
# Windows（在技能目录执行）
.venv\Scripts\python.exe scripts/dispatch.py "C:\project\.venv\Scripts\aishare.exe 002957" --delay 60 --bg

# Linux/macOS（在技能目录执行）
.venv/bin/python scripts/dispatch.py "/home/user/project/.venv/bin/aishare 002957" --delay 60 --bg

# Python 模块 - 使用 python.exe -m
# Windows（在技能目录执行）
.venv\Scripts\python.exe scripts/dispatch.py "C:\project\.venv\Scripts\python.exe -m module_name args" --delay 60 --bg

# Linux/macOS（在技能目录执行）
.venv/bin/python scripts/dispatch.py "/home/user/project/.venv/bin/python -m module_name args" --delay 60 --bg
```

### 场景 2：执行特定目录下的脚本

```bash
# 使用 --cwd 指定工作目录
# Windows（在技能目录执行）
.venv\Scripts\python.exe scripts/dispatch.py "python data_process.py" --cwd "C:\project" --delay 120

# Linux/macOS（在技能目录执行）
.venv/bin/python scripts/dispatch.py "python data_process.py" --cwd "/home/user/project" --delay 120
```

### 场景 3：批量派发多个任务

```bash
# Windows（在技能目录执行）
.venv\Scripts\python.exe scripts/dispatch.py "python task1.py" --delay 60
.venv\Scripts\python.exe scripts/dispatch.py "python task2.py" --delay 120
.venv\Scripts\python.exe scripts/dispatch.py "python task3.py" --delay 180

# Linux/macOS（在技能目录执行）
.venv/bin/python scripts/dispatch.py "python task1.py" --delay 60
.venv/bin/python scripts/dispatch.py "python task2.py" --delay 120
.venv/bin/python scripts/dispatch.py "python task3.py" --delay 180
```

### 场景 4：使用 eta 进行一次性定时任务

当只需要在特定时间执行一次任务时，使用 `--eta` 参数：

```bash
# 明天早上 8 点执行数据导出
.venv\Scripts\python.exe scripts/dispatch.py \
  "python export_data.py" \
  --eta "2026-02-17 08:00:00" \
  --bg

# 下周五下午 6 点发送周报
.venv\Scripts\python.exe scripts/dispatch.py \
  "python send_report.py weekly" \
  --eta "2026-02-21 18:00:00" \
  --bg

# 2 小时后执行系统更新
.venv\Scripts\python.exe scripts/dispatch.py \
  "python system_update.py" \
  --delay 7200 \
  --bg
```

---

## 配置说明

### 基础配置

配置文件位于 `celery_tasks/worker.py`：

```python
# Broker
broker_url = 'redis://localhost:6379/0'

# 时区
timezone = 'Asia/Shanghai'
enable_utc = True

# 任务确认
task_acks_late = True
task_reject_on_worker_lost = True
```

### 自定义配置

```bash
# 复制配置模板
cp assets/config/celery_config.py your_project/

# 修改并使用
from celery import Celery
app = Celery('myapp')
app.config_from_object('celery_config')
```

详见 [配置参考](references/config.md)

---

## ntfy 通知推送

技能已集成 **ntfy** 推送通知功能，任务完成时自动发送通知到手机。

### 功能特性

- **任务完成通知**：任务执行成功/失败时自动推送
- **后台推送**：支持锁屏/后台状态接收通知
- **多端同步**：手机、电脑同时订阅
- **优先级支持**：根据任务状态自动设置通知优先级

### 配置方法

**1. 安装 ntfy 服务端（可选）**

| 系统 | 安装方式 |
|------|---------|
| Windows | 下载 [ntfy.exe](https://github.com/binwiederhier/ntfy/releases) 或 `scoop install ntfy` |
| Linux | `wget https://github.com/binwiederhier/ntfy/releases/download/v2.17.0/ntfy_2.17.0_linux_amd64.tar.gz` |
| macOS | `brew install ntfy` |

或使用官方服务器：`https://ntfy.sh`（已配置 FCM，无需安装）

**2. 启动 ntfy 服务端**

```bash
# Windows
ntfy serve

# Linux/macOS
ntfy serve
```

**3. 配置技能通知**

编辑 `config/ntfy.yml`：

```yaml
# 是否启用通知
enabled: true

# ntfy 服务器地址
server: http://127.0.0.1          # 本地服务器
# server: https://ntfy.sh         # 官方服务器（有速率限制）

# 主题名称（手机 App 订阅的主题）
topic: mytest

# 默认优先级 (1=min, 2=low, 3=default, 4=high, 5=max)
priority: 3
```

**4. 手机订阅主题**

- 下载 **ntfy.sh** App（iOS/Android）
- 打开 App，点击订阅
- 输入服务器地址和主题名称

### 通知格式

**任务成功：**
```
【✅ 任务完成】
任务: execute_command
命令: echo 'Hello'
状态: 成功
返回码: 0
耗时: 0.018秒
```

**任务失败：**
```
【❌ 任务失败】
任务: execute_command
命令: invalid_command
状态: 失败
返回码: 1
耗时: 0.5秒
错误: command not found
```

### 使用场景

| 场景 | 优先级 | 示例 |
|------|--------|------|
| 定时任务 | 2 | 每日数据备份完成 |
| 任务失败 | 5 | 命令执行错误，需要处理 |
| 普通任务 | 3 | 常规脚本执行完成 |

---

## 跨平台支持

技能自动检测并适配不同操作系统：

| 系统              | Broker  | Pool 类型    | 可执行文件路径 |
| ----------------- | ------- | ------------ | -------------- |
| **Windows** | Memurai | solo         | `Scripts/`   |
| **Linux**   | Redis   | prefork      | `bin/`       |
| **macOS**   | Redis   | solo/prefork | `bin/`       |

路径分隔符、并发池类型等自动处理。

windows下强烈建议使用PowerShell语法执行任何终端命令。

详见 [跨平台部署指南](references/platform-guide.md)

---

## 常见问题

### Q: 技能环境未设置

```bash
# 使用系统 Python 创建技能虚拟环境
python scripts/setup_env.py
```

### Q: 如何检查服务是否运行？

**检查 Redis：**

```bash
# Windows
tasklist | grep -i redis
memurai-cli ping

# Linux/macOS
ps aux | grep redis
redis-cli ping
```

**检查 Worker：**

```bash
# Windows
tasklist | grep -i python

# Linux/macOS
ps aux | grep celery
```

### Q: Redis 连接失败

```bash
# Windows - 启动 Memurai（需管理员权限）
net start Memurai

# Linux
sudo systemctl start redis

# macOS
brew services start redis
```

### Q: 在项目环境执行命令失败

**原因：** Worker 使用技能环境，找不到项目命令

**解决方案：** 使用完整路径或 `--cwd`

```bash
# 方式1：完整路径（推荐）
# 先测试命令是否可执行
"C:\project\.venv\Scripts\aishare.exe" 002957

# 再派发任务（使用技能虚拟环境的 Python）
.venv\Scripts\python.exe scripts/dispatch.py "C:\project\.venv\Scripts\aishare.exe 002957" --delay 60 --bg

# 方式2：使用 --cwd
.venv\Scripts\python.exe scripts/dispatch.py "aishare 002957" --cwd "C:\project"
```

---

## 技能结构

```
celery-task/
├── SKILL.md                    # 本文件
├── celery_tasks/               # 任务模块
│   ├── __init__.py
│   ├── worker.py               # Celery app 和任务定义
│   └── ntfy_notifier.py        # ntfy 通知模块
├── config/                     # 配置文件
│   └── ntfy.yml                # ntfy 通知配置
├── scripts/                    # 脚本工具
│   ├── setup_env.py           # 环境设置
│   ├── worker.py              # Worker 启动
│   ├── dispatch.py            # 任务派发
│   ├── check_services.py      # 服务检查
│   └── start_monitoring.py    # 监控启动
├── references/                 # 参考文档
│   ├── platform-guide.md      # 跨平台指南
│   └── config.md              # 配置参考
└── assets/                     # 资产文件
    └── config/                # 配置模板
        ├── celery_config.py
        └── redis.conf
```
