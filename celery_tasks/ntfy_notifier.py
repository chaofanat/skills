"""
ntfy 通知模块
用于在任务完成时发送推送通知
"""

import os
import requests
from pathlib import Path
from datetime import datetime


class NtfyNotifier:
    """ntfy 通知发送器"""

    # 默认配置
    DEFAULT_CONFIG = {
        'enabled': False,          # 是否启用通知
        'server': 'http://127.0.0.1',  # ntfy 服务器地址
        'topic': 'celery-tasks',   # 默认主题
        'priority': 3,             # 默认优先级 (1-5)
    }

    # 配置文件路径
    CONFIG_FILE = Path(__file__).parent.parent / 'config' / 'ntfy.yml'

    def __init__(self):
        """初始化通知器"""
        self.config = self.DEFAULT_CONFIG.copy()
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if self.CONFIG_FILE.exists():
            try:
                import yaml
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        self.config.update(user_config)
            except ImportError:
                # yaml 未安装，使用默认配置
                pass
            except Exception:
                # 配置文件读取失败，使用默认配置
                pass

    def is_enabled(self):
        """检查通知是否启用"""
        return self.config.get('enabled', False)

    def send(self, title, message, priority=None, topic=None):
        """
        发送通知

        Args:
            title (str): 通知标题
            message (str): 通知内容
            priority (int, optional): 优先级 (1-5)
            topic (str, optional): 主题名称

        Returns:
            bool: 发送是否成功
        """
        if not self.is_enabled():
            return False

        # 使用配置的优先级和主题
        priority = priority or self.config.get('priority', 3)
        topic = topic or self.config.get('topic', 'celery-tasks')
        server = self.config.get('server', 'http://127.0.0.1')

        # 构建消息
        if title:
            full_message = f"【{title}】\n{message}"
        else:
            full_message = message

        headers = {
            "Content-Type": "text/plain; charset=utf-8"
        }

        if priority:
            headers["Priority"] = str(priority)

        try:
            # 发送纯文本消息
            response = requests.post(
                f"{server}/{topic}",
                data=full_message,
                headers=headers,
                timeout=5
            )
            response.raise_for_status()
            return True
        except Exception:
            # 发送失败不影响任务执行
            return False

    def notify_task_complete(self, task_name, command, result):
        """
        任务完成通知（简化版，截断输出）

        Args:
            task_name (str): 任务名称
            command (str): 执行的命令
            result (dict): 任务执行结果

        Returns:
            bool: 发送是否成功
        """
        success = result.get('success', False)
        returncode = result.get('returncode', 0)
        duration = result.get('duration', 0)
        stdout = result.get('stdout', '')
        stderr = result.get('stderr', '')

        # 根据结果确定标题和优先级
        if success:
            title = "✅ 任务完成"
            priority = 2
        else:
            title = "❌ 任务失败"
            priority = 5

        # 构建消息内容（截断输出为200字符）
        message = f"""任务: {task_name}
命令: {command}
状态: {'成功' if success else '失败'}
返回码: {returncode}
耗时: {duration}秒"""

        # 添加截断的标准输出
        if stdout:
            stdout_preview = stdout[:200] + '...' if len(stdout or '') > 200 else stdout
            message += f"\n\n📤 输出:\n{stdout_preview}"

        # 添加截断的错误输出
        if stderr:
            stderr_preview = stderr[:200] + '...' if len(stderr or '') > 200 else stderr
            message += f"\n\n⚠️ 错误:\n{stderr_preview}"

        # 提示查看完整输出
        if len(stdout or '') > 200 or len(stderr or '') > 200:
            message += f"\n\n📋 查看完整输出: http://localhost:5555"

        return self.send(title, message, priority)

    def notify_task_scheduled(self, task_name, command, eta):
        """
        任务调度通知

        Args:
            task_name (str): 任务名称
            command (str): 执行的命令
            eta (datetime): 执行时间

        Returns:
            bool: 发送是否成功
        """
        if isinstance(eta, str):
            eta_str = eta
        else:
            eta_str = eta.strftime('%Y-%m-%d %H:%M:%S')

        title = "⏰ 任务已调度"
        message = f"""任务: {task_name}
命令: {command[:80]}{'...' if len(command) > 80 else ''}
执行时间: {eta_str}"""

        return self.send(title, message, priority=3)


# 全局单例
_notifier = None


def get_notifier():
    """获取通知器单例"""
    global _notifier
    if _notifier is None:
        _notifier = NtfyNotifier()
    return _notifier


def notify_task_complete(task_name, command, result):
    """快捷方法：发送任务完成通知"""
    notifier = get_notifier()
    if notifier.is_enabled():
        return notifier.notify_task_complete(task_name, command, result)
    return False


def notify_task_scheduled(task_name, command, eta):
    """快捷方法：发送任务调度通知"""
    notifier = get_notifier()
    if notifier.is_enabled():
        return notifier.notify_task_scheduled(task_name, command, eta)
    return False
