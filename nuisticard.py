# -*- coding: utf-8 -*-
import os
import time
import json
import base64
import random
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
# 模块一：全局认证中心与门户信息获取
# ==========================================
class NuistCAS:
    def __init__(self, username, password,multifactor_browser_fingerprint, multifactor_users):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        # # =================【核心修复】=================
        # 注入浏览器中已受信任的多因素认证 (MFA) Cookie，伪装成受信任设备绕过 isMultifactor 二次验证
        # Cookie值提取自你提供的浏览器抓包数据 MULTIFACTOR_BROWSER_FINGERPRINT MULTIFACTOR_USERS
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
        
        # PKCS7 填充
        pad = AES.block_size - len(text) % AES.block_size
        text += bytes([pad] * pad)
        
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return base64.b64encode(cipher.encrypt(text)).decode('utf-8')

    def _get_and_recognize_captcha(self):
        """独立的验证码获取与识别函数"""
        print("🧩 [验证码] 正在获取并识别验证码...")
        timestamp = int(datetime.now().timestamp() * 1000)
        captcha_url = f'https://authserver.nuist.edu.cn/authserver/getCaptcha.htl?{timestamp}'
        
        try:
            captcha_img_resp = self.session.get(captcha_url, timeout=5)
            captcha_text = self.ocr.classification(captcha_img_resp.content)
            print(f"📝 [验证码] 识别结果: {captcha_text}")
            return captcha_text
        except Exception as e:
            print(f"❌ [验证码] 获取或识别失败: {e}")
            return None

    def login(self):
        """核心登录逻辑：获取全局 Cookie (TGC)"""
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
            print("❌ [错误] 验证码环节中断，停止登录。")
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
            print("✅ [系统] 登录成功！已获取全局通行证(TGC)。\n" + "-"*40)
            return True
        else:
            print("❌ [系统] 登录失败！请检查账号密码或验证码是否识别错误。")
            return False
            
# ==========================================
# 模块二：一卡通业务 (依赖全局 Session 换 Token)
# ==========================================
class NuistICard:
    def __init__(self, cas_session, post_data):
        self.session = cas_session.session 
        self.post_data = post_data
        self.access_token = None

    def authorize(self):
        """利用全局 TGC 免密获取一卡通 access_token"""
        print("🎫 [一卡通] 正在使用全局通行证换取业务 Token...")
        target_service = "https://icard.nuist.edu.cn/berserker-auth/cas/login/wisedu?targetUrl=https://icard.nuist.edu.cn/plat/?name=loginTransit"
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

    def get_electricity_balance(self):
        """查询电费"""
        if not self.access_token:
            print("❌ 请先执行 authorize() 获取 token！")
            return None, None
            
        print("⚡ [一卡通] 正在查询当前电费...")
        url = "https://icard.nuist.edu.cn/charge/feeitem/getThirdData"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "synjones-auth": f"bearer {self.access_token}",
            "Origin": "https://icard.nuist.edu.cn",
            "Referer": "https://icard.nuist.edu.cn/"
        }
        
        response = self.session.post(url, data=self.post_data, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200 and "map" in data:
                info = data["map"]["showData"]
                balance = info.get('剩余电量', '未知')
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                ld_name = self.post_data.get("loudong_id", "").split('&')[-1]
                rm_name = self.post_data.get("room_id", "").split('&')[-1]
                
                print(f"💰 {now} | {ld_name} {rm_name}室 剩余电量：{balance} 度")
                return balance
            else:
                print("❌ [一卡通] 接口返回异常：", data)
                return None, None
        else:
            print("❌ [一卡通] 请求失败，状态码：", response.status_code)
            return None, None

# ==========================================
# 模块三：多渠道统一消息通知中心 (高扩展性)
# ==========================================
class NotificationCenter:
    def __init__(self, keys_config):
        """
        :param keys_config: 包含所有通道密钥的字典
        """
        self.keys = keys_config

    def send_bark(self, title, content):
        """渠道一：Bark 推送"""
        key = self.keys.get("BARK_KEY")
        if not key:
            return
        url = f"https://api.day.app/{key}/"
        data = {
            "title": title,
            "body": content,
            "group": "电费",
            "sound": "minuet",
        }
        try:
            resp = requests.post(url, json=data, timeout=10)
            if resp.status_code == 200:
                print("✅ [通知] Bark 消息推送成功")
            else:
                print(f"❌ [通知] Bark 推送失败：{resp.text}")
        except Exception as e:
            print(f"❌ [通知] Bark 推送异常：{e}")

    def send_serverchan(self, title, content):
        """渠道二：Server酱 推送"""
        key = self.keys.get("SERVERCHAN_KEY")
        if not key:
            return
        url = f"https://sctapi.ftqq.com/{key}.send"
        data = {
            "title": title,
            "desp": content 
        }
        try:
            resp = requests.post(url, data=data, timeout=10)
            if resp.status_code == 200 and resp.json().get("code") == 0:
                print("✅ [通知] Server酱 消息推送成功")
            else:
                print(f"❌ [通知] Server酱 推送失败：{resp.text}")
        except Exception as e:
            print(f"❌ [通知] Server酱 推送异常：{e}")

    def send_pushplus(self, title, content):
        """渠道三：PushPlus 推送"""
        key = self.keys.get("PUSHPLUS_TOKEN")
        if not key:
            return
        
        url = "http://www.pushplus.plus/send"
        data = {
            "token": key,
            "title": title,
            "content": content,
            "template": "txt"  # 使用纯文本模板展示更直接
        }
        try:
            resp = requests.post(url, json=data, timeout=10)
            if resp.status_code == 200 and resp.json().get("code") == 200:
                print("✅ [通知] PushPlus 微信消息推送成功")
            else:
                print(f"❌ [通知] PushPlus 推送失败：{resp.text}")
        except Exception as e:
            print(f"❌ [通知] PushPlus 推送异常：{e}")

    def dispatch_all(self, balance):

        title = "⚡ NUIST 电费每日推送"
        # 移除了时间的拼接，仅保留电量
        content = f"剩余电量: {balance} 度"

        print("📱 [通知] 正在通过已配置的渠道分发消息...")
        
        # 触发各个发送方法
        self.send_bark(title, content)
        self.send_serverchan(title, content)
        self.send_pushplus(title, content)



# ==========================
# 🚀 主程序运行入口
# ==========================
if __name__ == '__main__':
    # 1. 账号基础配置
    USERNAME = os.getenv("NUIST_USER", "20241xxxxx") 
    PASSWORD = os.getenv("NUIST_PWD", "xxxxx")

    # 多因素认证 Cookie（同样支持环境变量 + 默认值）
    MULTIFACTOR_BROWSER_FINGERPRINT = os.getenv(
        "NUIST_MULTIFACTOR_FINGERPRINT", 
        ""
    )
    MULTIFACTOR_USERS = os.getenv(
        "NUIST_MULTIFACTOR_USERS",
        ""
    )

    # 2. 集中管理你的所有通知 Token，填入后自动激活对应渠道
    notifier_keys = {
        "BARK_KEY": os.getenv("BARK_KEY", "whCj9QnqwPvT5mtY8PH7AQ"), 
        "SERVERCHAN_KEY": os.getenv("SERVERCHAN_KEY", ""),  
        "PUSHPLUS_TOKEN": os.getenv("PUSHPLUS_TOKEN", "c5c07b214d6c41d59aa832c40c212333")  # 在这里填入 PushPlus 的 token
    }
    # 初始化认证大厅
    cas = NuistCAS(USERNAME, PASSWORD,MULTIFACTOR_BROWSER_FINGERPRINT,MULTIFACTOR_USERS)
    
    if cas.login(): 
        # 宿舍请求体参数
        icard_data = {
            "type": "IEC",  # 费用类型一般固定不变
            "level": os.getenv("ICARD_LEVEL", "3"),                        
            "feeitemid": os.getenv("ICARD_FEEITEMID", "448"),                  
            "xiaoyu_id": os.getenv("ICARD_XIAOYU", "3&沁园"),                
            "loudong_id": os.getenv("ICARD_LOUDONG", "23&沁园30号栋"),        
            "room_id": os.getenv("ICARD_ROOM", "4186&135")                
        }
        
        # 授权并查询
        icard = NuistICard(cas_session=cas, post_data=icard_data)
        
        if icard.authorize():
            # 仅接收 balance
            balance = icard.get_electricity_balance()
            
            # 3. 交给通知中心一键分发
            if balance is not None:
                balance = f"{float(balance):.2f}"
                notifier = NotificationCenter(notifier_keys)
                notifier.dispatch_all(balance)
    
