# -*- coding: utf-8 -*-
"""所有配置常量。以后只改这个文件。"""

USERNAME = "2024xxxx"
PASSWORD = "xxxx"

# 🔑 只改这一个参数决定走哪套登录
LOGIN_MODE = "oauth"          # "cas" 或 "oauth"

# ---- 宿舍参数（留空则自动引导选择）----
feeitemid  = ""
xiaoqu_id  = ""
loudong_id = ""
room_id    = ""

# ---- CAS 专用（oauth 登录无需填写）----
MULTIFACTOR_BROWSER_FINGERPRINT = ""
MULTIFACTOR_USERS = (
    ""
)

NOTIFIER_KEYS = {
    "BARK_KEY": "",
    "SERVERCHAN_KEY": "",
    "PUSHPLUS_TOKEN": "",
}

# feeitemid 映射表（仅引导模式用来显示区域名）
FEEITEM_MAP = {
    "448": "本部",
    "429": "天长",
    "568": "沁园42、43栋",
}

# ---- token 缓存 ----
TOKEN_FILE = "token_cache.json"       # ← 从 token.json 改成 token.py
MIN_REMAINING_SECONDS = 300   # 剩余不足 5 分钟就重新登录