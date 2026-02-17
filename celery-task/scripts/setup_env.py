#!/usr/bin/env python
"""
Celery 技能环境设置脚本
自动创建独立的虚拟环境并安装所需依赖
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def run_command(cmd, description):
    """执行命令并显示进度"""
    print(f"\n{'='*60}")
    print(f"[{description}]")
    print(f"{'='*60}")
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"✗ 失败: {result.stderr}")
        return False
    print(f"✓ 成功")
    return True


def setup_skill_env():
    """设置技能环境"""

    print("\n" + "="*60)
    print("Celery 技能环境设置")
    print("="*60)

    # 技能环境目录
    skill_env_dir = Path.home() / ".claude" / "skills" / "celery-task" / ".venv"

    # 检测平台
    system = platform.system()
    print(f"\n检测到系统: {system}")

    # 创建虚拟环境
    if not skill_env_dir.exists():
        print(f"\n创建虚拟环境: {skill_env_dir}")
        subprocess.run([sys.executable, "-m", "venv", str(skill_env_dir)], check=True)
        print("✓ 虚拟环境创建成功")
    else:
        print(f"✓ 虚拟环境已存在: {skill_env_dir}")

    # 确定 Python 可执行文件路径
    if system == "Windows":
        python_exe = skill_env_dir / "Scripts" / "python.exe"
        pip_exe = skill_env_dir / "Scripts" / "pip.exe"
    else:
        python_exe = skill_env_dir / "bin" / "python"
        pip_exe = skill_env_dir / "bin" / "pip"

    # 升级 pip
    print("\n升级 pip...")
    subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"],
                   capture_output=True)

    # 安装依赖
    dependencies = ["celery", "redis", "flower"]
    print(f"\n安装依赖: {', '.join(dependencies)}")

    for dep in dependencies:
        print(f"  - 安装 {dep}...")
        result = subprocess.run([str(pip_exe), "install", dep],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"    ✓ {dep} 安装成功")
        else:
            print(f"    ✗ {dep} 安装失败: {result.stderr}")
            return False

    # 创建环境标记文件
    env_marker = skill_env_dir.parent / ".env_ready"
    env_marker.write_text(f"System: {system}\nPython: {sys.version}\n")

    print("\n" + "="*60)
    print("✓ 技能环境设置完成！")
    print("="*60)
    print(f"\n虚拟环境位置: {skill_env_dir}")
    print(f"\n下一步:")
    print(f"  1. 参考 references/platform-guide.md 安装 Redis")
    print(f"  2. 使用 scripts/worker.py 启动 Worker")
    print(f"  3. 使用 scripts/dispatch.py 派发任务")

    return True


if __name__ == "__main__":
    setup_skill_env()
