# -*- coding: utf-8 -*-
import os
import time
import json
import base64
import random
import re
import codecs
import requests
import ddddocr
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ==========================================
# 核心模块：全局认证中心 (统一获取 TGC)
# ==========================================
class NUIST_CAS:
    def __init__(self, username, password, multifactor_browser_fingerprint, multifactor_users):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        # 注入多因素认证 Cookie，绕过二次验证
        self.session.cookies.set("MULTIFACTOR_BROWSER_FINGERPRINT", multifactor_browser_fingerprint, domain="authserver.nuist.edu.cn")
        self.session.cookies.set("MULTIFACTOR_USERS", multifactor_users, domain="authserver.nuist.edu.cn")

        self.cas_login_url = "https://authserver.nuist.edu.cn/authserver/login"
        self.ocr = ddddocr.DdddOcr(show_ad=False)

    def _encrypt_password(self, password, key):
        """AES 加密密码 (前端 encrypt.js 逆向)"""
        def random_string(length):
            chars = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"
            return ''.join(random.choice(chars) for _ in range(length))

        random_prefix = random_string(64)
        iv = random_string(16)
        text = (random_prefix + password).encode('utf-8')
        key = key.strip().encode('utf-8')
        iv = iv.encode('utf-8')

        pad = AES.block_size - len(text) % AES.block_size
        text += bytes([pad] * pad)

        cipher = AES.new(key, AES.MODE_CBC, iv)
        return base64.b64encode(cipher.encrypt(text)).decode('utf-8')

    def _get_and_recognize_captcha(self):
        """获取并识别验证码"""
        print("🧩 [系统] 正在获取并识别验证码...")
        timestamp = int(datetime.now().timestamp() * 1000)
        captcha_url = f'https://authserver.nuist.edu.cn/authserver/getCaptcha.htl?{timestamp}'

        try:
            captcha_img_resp = self.session.get(captcha_url, timeout=5)
            captcha_text = self.ocr.classification(captcha_img_resp.content)
            print(f"📝 [系统] 验证码识别结果: {captcha_text}")
            return captcha_text
        except Exception as e:
            print(f"❌ [系统] 验证码获取或识别失败: {e}")
            return None

    def login(self):
        """核心登录逻辑，获取全局 Cookie (TGC)"""
        print("🚪 [系统] 正在访问信息门户大门...")
        try:
            resp = self.session.get(self.cas_login_url, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')

            execution_tag = soup.find('input', id="execution")
            salt_tag = soup.find('input', id="pwdEncryptSalt")

            if not execution_tag or not salt_tag:
                print("❌ [错误] 无法获取页面加密参数，可能网络异常或已登录。")
                return False

            execution = execution_tag["value"]
            pwdEncryptSalt = salt_tag["value"]
        except Exception as e:
            print(f"❌ [错误] 访问登录页异常: {e}")
            return False

        captcha = self._get_and_recognize_captcha()
        if not captcha:
            return False

        print("🔑 [系统] 正在加密并提交登录表单...")
        enc_password = self._encrypt_password(self.password, pwdEncryptSalt)
        login_data = {
            'username': self.username,
            'password': enc_password,
            'captcha': captcha,
            '_eventId': 'submit',
            'cllt': 'userNameLogin',
            'dllt': 'generalLogin',
            'lt': '',
            'execution': execution,
        }

        self.session.post(
            self.cas_login_url,
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=True
        )

        if 'CASTGC' in self.session.cookies.get_dict():
            print("✅ [系统] 登录成功！已获取全局通行证(TGC)。\n" + "=" * 50)
            return True
        else:
            print("❌ [系统] 登录失败！请检查账号密码或验证码。")
            return False
