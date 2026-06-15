"""trend-verify gmapi 数据采集 — 公共模块。

职责：
1. token 初始化（从环境变量 GM_TOKEN 读取）
2. 统一的"软失败"装饰器：gmapi 调用失败时记录原因但不中断主流程
3. 数据落盘工具（JSON + Markdown）
"""
import os
import sys
import json
import time
import functools
from datetime import datetime, timezone, timedelta

# 强制使用项目 venv 的 gm SDK（项目根目录在 D:/workspace/股票工作站）
_GM_VENV = r"D:\workspace\股票工作站\.venv\Lib\site-packages"
if _GM_VENV not in sys.path:
    sys.path.insert(0, _GM_VENV)

from gm.api import set_token


# 上海时区
CST = timezone(timedelta(hours=8))


def setup_token():
    """读取环境变量 GM_TOKEN 并设置。失败则退出。"""
    token = os.environ.get("GM_TOKEN")
    if not token:
        print("[FATAL] GM_TOKEN 环境变量未设置", file=sys.stderr)
        sys.exit(1)
    set_token(token)
    return token


def soft_fail(name, fallback_registry):
    """装饰器：gmapi 调用失败时不抛异常，记录到 fallback_registry 列表。

    Args:
        name: 数据项名称（如"龙虎榜营业部"）
        fallback_registry: 共享的 list，失败时追加 dict {name, error, time}
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            t0 = time.time()
            try:
                result = func(*args, **kwargs)
                duration = round(time.time() - t0, 2)
                return {"ok": True, "data": result, "duration_s": duration}
            except Exception as e:
                duration = round(time.time() - t0, 2)
                err = {"name": name, "error": f"{type(e).__name__}: {e}",
                       "time": datetime.now(CST).isoformat(), "duration_s": duration}
                fallback_registry.append(err)
                print(f"[SOFT-FAIL] {name}: {err['error']}", file=sys.stderr)
                return {"ok": False, "data": None, "error": err, "duration_s": duration}
        return wrapper
    return decorator


def today_str():
    """返回 YYYY-MM-DD（CST）。"""
    return datetime.now(CST).strftime("%Y-%m-%d")


def now_ts():
    """返回完整时间戳字符串。"""
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")


def write_json(data, filepath):
    """写 JSON 文件，自动创建父目录。"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    return filepath


def safe_get(df, *cols, default=None):
    """从 DataFrame 取一行，按列优先级返回第一个非空值。"""
    if df is None or (hasattr(df, "empty") and df.empty):
        return default
    row = df.iloc[0]
    for c in cols:
        if c in df.columns:
            v = row[c]
            if v is not None and str(v) != "nan":
                return v
    return default
