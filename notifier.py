# -*- coding: utf-8 -*-
import requests


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
            "template": "txt"
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
        content = f"剩余电量: {balance} 度"

        print("📱 [通知] 正在通过已配置的渠道分发消息...")

        self.send_bark(title, content)
        self.send_serverchan(title, content)
        self.send_pushplus(title, content)