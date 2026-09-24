# -*- coding: utf-8 -*-
"""
Token 一站式模块：
    - 解析：decode_jwt / remaining_hours / expire_time / expire_at_ts / format_info
    - 缓存：load / save / clear

注意：
    load() 只做“时间层面”的预判，用于快速跳过登录。
    真正的有效性以服务端返回为准（401/403 由 ElectricAPI 抛 TokenInvalidError）。
"""
import base64
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

import config


# ==========================================
# 一、Token 解析
# ==========================================
def decode_jwt(token: str) -> Optional[dict]:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return None


def remaining_hours(token: str) -> float:
    data = decode_jwt(token)
    if not data or "exp" not in data:
        return 0.0
    remaining = data["exp"] - time.time()
    return max(0.0, remaining / 3600)


def expire_time(token: str) -> Optional[datetime]:
    data = decode_jwt(token)
    if not data or "exp" not in data:
        return None
    return datetime.fromtimestamp(data["exp"], tz=timezone.utc)


def expire_at_ts(token: str) -> float:
    data = decode_jwt(token)
    if not data:
        return 0.0
    return float(data.get("exp", 0))


def format_info(token: str) -> str:
    remain = remaining_hours(token)
    exp = expire_time(token)
    if exp:
        return (f"剩余有效期：{remain:.2f} 小时 "
                f"（过期时间 UTC：{exp.strftime('%Y-%m-%d %H:%M:%S')}）")
    return "无法解析有效期（payload 中无 exp）"


# ==========================================
# 二、Token 本地缓存
# ==========================================
def _path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        config.TOKEN_FILE)


def load():
    """
    仅按“本地记录的时间”判断是否可用，用于快速跳过登录。
    时间没过 ≠ 服务端一定认；调用方必须对 401/403 做兜底重登。
    """
    p = _path()
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    token = data.get("access_token")
    expire_at = data.get("expire_at", 0)
    if not token:
        return None
    if expire_at - time.time() < config.MIN_REMAINING_SECONDS:
        return None
    return token


def save(token, expire_at, login_mode):
    data = {
        "access_token": token,
        "expire_at": expire_at or 0,
        "login_mode": login_mode,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        with open(_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 [Token] 已缓存到 {config.TOKEN_FILE}")
    except Exception as e:
        print(f"⚠️ [Token] 缓存写入失败：{e}")


def clear():
    try:
        p = _path()
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass