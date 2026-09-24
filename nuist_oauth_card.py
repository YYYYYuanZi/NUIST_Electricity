# -*- coding: utf-8 -*-
"""
OAuth 直登模块：只负责登录拿一卡通 access_token，并可查看 token 剩余有效期。
查询、级联、推送全部交给项目里已有的 nuist_electric.py / notifier.py。
"""
import base64
import json
import time
from datetime import datetime, timezone
from typing import Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class NUISTPowerAPI:
    BASE_URL = "https://icard.nuist.edu.cn"
    AUTH_URL = f"{BASE_URL}/berserker-auth/oauth/token"
    CLIENT_AUTH = (
        "Basic bW9iaWxlX3NlcnZpY2VfcGxhdGZvcm06"
        "bW9iaWxlX3NlcnZpY2VfcGxhdGZvcm1fc2VjcmV0"
    )
    TIMEOUT = 15

    def __init__(self, proxy: str = None):
        self.proxy = proxy
        self.session = requests.Session()
        self.session.verify = False
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    # ==========================================
    # 底层
    # ==========================================
    def _post(self, url: str, *, headers: dict, data: dict) -> requests.Response:
        return self.session.post(url, headers=headers, data=data, timeout=self.TIMEOUT)

    @staticmethod
    def _json_response(resp: requests.Response, operation: str) -> dict:
        try:
            try:
                text = resp.content.decode("utf-8")
            except UnicodeDecodeError:
                text = resp.content.decode("gb18030")
            result = json.loads(text)
        except (UnicodeDecodeError, ValueError) as exc:
            raise RuntimeError(
                f"{operation} failed: HTTP {resp.status_code}, invalid JSON response"
            ) from exc
        if not isinstance(result, dict):
            raise RuntimeError(f"{operation} failed: unexpected response format")
        if not 200 <= resp.status_code < 300:
            detail = (
                result.get("error_description")
                or result.get("message")
                or result.get("msg")
                or result.get("error")
                or result
            )
            raise RuntimeError(
                f"{operation} failed: HTTP {resp.status_code}: {detail}"
            )
        return result

    # ==========================================
    # 认证：OAuth 密码模式直登
    # ==========================================
    def login(self, student_id: str, password: str) -> str:
        print("🚪 [OAuth] 正在登录...")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": self.CLIENT_AUTH,
            "synaccesssource": "pc",
            "origin": self.BASE_URL,
            "referer": f"{self.BASE_URL}/",
            "accept": "application/json, text/plain, */*",
            "user-agent": "Mozilla/5.0 (AstrBot NUIST Power Plugin)",
        }
        data = {
            "username": student_id,
            "password": password,
            "grant_type": "password",
            "scope": "all",
            "loginFrom": "pc",
            "logintype": "snoNew",
        }
        resp = self._post(self.AUTH_URL, headers=headers, data=data)
        result = self._json_response(resp, "login")
        token = result.get("access_token")
        if not token:
            detail = (
                result.get("error_description")
                or result.get("message")
                or result.get("msg")
                or result.get("error")
                or result
            )
            raise RuntimeError(f"login failed: {detail}")
        print("✅ [OAuth] 登录成功")
        return token

