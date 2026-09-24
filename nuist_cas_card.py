# -*- coding: utf-8 -*-
import json
import time
import base64
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse, parse_qs
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 模块二：一卡通授权 (依赖全局 Session 换 Token)
# ==========================================
class NUIST_CAS_Card:
    def __init__(self, cas_session):
        self.session = cas_session.session
        self.access_token = None

    def authorize(self):
        """利用全局 TGC 免密获取一卡通 access_token"""
        print("🎫 [一卡通] 正在使用全局通行证换取业务 Token...")
        target_service = (
            "https://icard.nuist.edu.cn/berserker-auth/cas/login/wisedu"
            "?targetUrl=https://icard.nuist.edu.cn/plat/?name=loginTransit"
        )
        auth_url = f"https://authserver.nuist.edu.cn/authserver/login?service={target_service}"

        resp = self.session.get(auth_url, allow_redirects=True)
        ticket = parse_qs(urlparse(resp.url).query).get("ticket", [None])[0]

        if not ticket:
            print("❌ [一卡通] 未能获取 ticket，TGC 可能已失效或重定向失败。")
            return False

        token_resp = self.session.post(
            "https://icard.nuist.edu.cn/berserker-auth/oauth/token",
            headers={
                "Authorization": "Basic bW9iaWxlX3NlcnZpY2VfcGxhdGZvcm06bW9iaWxlX3NlcnZpY2VfcGxhdGZvcm1fc2VjcmV0",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://icard.nuist.edu.cn",
                "Referer": "https://icard.nuist.edu.cn/plat/loginTransit"
            },
            data={
                "username": ticket, "password": ticket, "grant_type": "password",
                "scope": "all", "loginFrom": "h5", "logintype": "sso",
                "device_token": "h5", "synAccessSource": "h5"
            }
        )

        try:
            self.access_token = token_resp.json().get("access_token")
        except Exception:
            print("❌ [一卡通] Token 解析失败:", token_resp.text)
            return False

        if self.access_token:
            print("🎉 [一卡通] Token 换取成功！具备查电费权限。")
            return True
        return False
    
