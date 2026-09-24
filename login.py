# -*- coding: utf-8 -*-
"""统一登录出口：缓存命中 → CAS → OAuth。返回 (session_obj, token)。"""
import requests

from nuist_cas import NUIST_CAS
from nuist_cas_card import NUIST_CAS_Card
from nuist_oauth_card import NUISTPowerAPI

import config
import token_store


class _StubSession:
    """缓存命中时不需要真 session，造个占位对象给 ElectricAPI 用。"""
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False


def _login_cas():
    cas = NUIST_CAS(config.USERNAME, config.PASSWORD,
                    config.MULTIFACTOR_BROWSER_FINGERPRINT,
                    config.MULTIFACTOR_USERS)
    if not cas.login():
        return None, None
    card = NUIST_CAS_Card(cas_session=cas)
    if not card.authorize():
        return None, None
    return cas, card.access_token


def _login_oauth():
    api = NUISTPowerAPI()
    try:
        token = api.login(config.USERNAME, config.PASSWORD)
    except Exception as e:
        print(f"❌ [OAuth] 登录失败：{e}")
        return None, None
    return api, token


def get_token(force_login=False):
    """返回 (session_obj, access_token)；失败 (None, None)。"""
    if not force_login:
        cached = token_store.load()
        if cached:
            remain = token_store.remaining_hours(cached)
            print(f"♻️ [Token] 命中本地缓存，剩余 {remain:.2f} 小时，跳过登录。")
            return _StubSession(), cached

    print("🔐 [Token] 无可用缓存，开始登录...")
    if config.LOGIN_MODE == "cas":
        session_obj, token = _login_cas()
    elif config.LOGIN_MODE == "oauth":
        session_obj, token = _login_oauth()
    else:
        print(f"❌ 未知 LOGIN_MODE: {config.LOGIN_MODE}")
        return None, None

    if not token:
        return None, None

    token_store.save(token, token_store.expire_at_ts(token), config.LOGIN_MODE)
    return session_obj, token


def print_token_info(access_token):
    print(f"⏳ [Token] {token_store.format_info(access_token)}")