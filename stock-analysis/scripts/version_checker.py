#!/usr/bin/env python3
"""
Version Checker Module for stock-analysis skill
Automatically checks for aishare-txt package updates from PyPI
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta


# Cache file path
CACHE_FILE = Path(__file__).parent.parent / ".version_cache.json"
# Check interval: 24 hours
CHECK_INTERVAL_HOURS = 24


def get_installed_version(package_name="aishare-txt"):
    """Get the currently installed version of the package"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='ignore'
        )
        for line in result.stdout.split('\n'):
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def get_latest_version(package_name="aishare-txt"):
    """Get the latest version from PyPI"""
    try:
        import urllib.request
        url = f"https://pypi.org/pypi/{package_name}/json"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data["info"]["version"]
    except Exception:
        return None


def load_cache():
    """Load cached version information"""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_cache(cache_data):
    """Save version information to cache"""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def should_check_update():
    """Check if enough time has passed since last check"""
    cache = load_cache()
    if not cache:
        return True

    last_check = cache.get("last_check")
    if not last_check:
        return True

    try:
        last_check_time = datetime.fromisoformat(last_check)
        elapsed = datetime.now() - last_check_time
        return elapsed.total_seconds() >= CHECK_INTERVAL_HOURS * 3600
    except Exception:
        return True


def check_update(package_name="aishare-txt", force=False):
    """
    Check for package updates

    Args:
        package_name: Package name to check
        force: Force check even if within interval

    Returns:
        dict with keys:
        - has_update: bool
        - current_version: str
        - latest_version: str
        - message: str
    """
    if not force and not should_check_update():
        cache = load_cache()
        return {
            "has_update": cache.get("has_update", False),
            "current_version": cache.get("current_version"),
            "latest_version": cache.get("latest_version"),
            "message": "使用缓存版本信息"
        }

    current_version = get_installed_version(package_name)
    latest_version = get_latest_version(package_name)

    result = {
        "current_version": current_version,
        "latest_version": latest_version,
        "has_update": False,
        "message": ""
    }

    if not current_version:
        result["message"] = f"⚠️  未找到 {package_name} 包，请先安装依赖"
    elif not latest_version:
        result["message"] = f"⚠️  无法获取 {package_name} 最新版本信息"
    elif current_version != latest_version:
        result["has_update"] = True
        result["message"] = (
            f"📦 发现新版本！\n"
            f"   当前版本: {current_version}\n"
            f"   最新版本: {latest_version}\n"
            f"   更新命令: venv/Scripts/python.exe -m pip install --upgrade {package_name}"
        )
    else:
        result["message"] = f"✅ {package_name} 已是最新版本 ({current_version})"

    # Save to cache
    cache_data = {
        "last_check": datetime.now().isoformat(),
        "current_version": current_version,
        "latest_version": latest_version,
        "has_update": result["has_update"]
    }
    save_cache(cache_data)

    return result


def print_version_check(package_name="aishare-txt"):
    """Print version check result with formatting"""
    result = check_update(package_name)
    if result["message"]:
        print(result["message"])
    return result


if __name__ == "__main__":
    # Standalone usage
    print("检查 aishare-txt 版本更新...")
    print("-" * 50)
    print_version_check("aishare-txt")
