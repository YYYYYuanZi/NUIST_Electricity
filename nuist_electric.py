# -*- coding: utf-8 -*-
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class NUIST_Electric:
    BASE_URL = "https://icard.nuist.edu.cn"
    QUERY_URL = f"{BASE_URL}/charge/feeitem/getThirdData"

    def __init__(self, cas_session, post_data=None):
        self.session = cas_session.session
        self.post_data = post_data or {}

    def _headers(self, access_token):
        return {
            "Content-Type": "application/x-www-form-urlencoded",
            "synjones-auth": f"bearer {access_token}",
            "Origin": self.BASE_URL,
            "Referer": f"{self.BASE_URL}/",
        }

    def _post(self, access_token, data):
        return self.session.post(
            self.QUERY_URL, data=data, headers=self._headers(access_token)
        )

    # ==========================================
    # 级联查询：校区 / 楼栋 / 房间
    # ==========================================
    def _select(self, access_token, params):
        resp = self._post(access_token, params)
        if resp.status_code != 200:
            print(f"❌ [级联] HTTP {resp.status_code}")
            return []
        data = resp.json()
        if str(data.get("code")) != "200":
            print("❌ [级联] 接口返回异常：", data)
            return []
        return data.get("map", {}).get("data", []) or []

    def get_campuses(self, access_token, feeitemid):
        print(f"🏫 [级联] 拉取校区列表（feeitemid={feeitemid}）...")
        return self._select(access_token, {
            "type": "select", "level": "0",
            "feeitemid": feeitemid,
        })

    def get_buildings(self, access_token, feeitemid, xiaoqu_id):
        print(f"🏢 [级联] 拉取楼栋列表（feeitemid={feeitemid}）...")
        return self._select(access_token, {
            "type": "select", "level": "1",
            "feeitemid": feeitemid,
            "xiaoqu_id": xiaoqu_id,
        })

    def get_rooms(self, access_token, feeitemid, xiaoqu_id, loudong_id):
        print(f"🚪 [级联] 拉取房间列表（feeitemid={feeitemid}）...")
        return self._select(access_token, {
            "type": "select", "level": "2",
            "feeitemid": feeitemid,
            "xiaoqu_id": xiaoqu_id,
            "loudong_id": loudong_id,
        })

    # ==========================================
    # 电费查询
    # ==========================================
    def get_electricity_balance(self, access_token):
        if not access_token:
            print("❌ [电费] 未提供 access_token。")
            return None, True
        if not self.post_data.get("room_id"):
            print("⚠️ [电费] 宿舍参数为空，无法查询。")
            return None, False

        print("⚡ [电费] 正在查询当前电费...")
        resp = self._post(access_token, self.post_data)

        if resp.status_code in (401, 403):
            print(f"⚠️ [电费] token 失效（HTTP {resp.status_code}）")
            return None, True
        if resp.status_code != 200:
            print("❌ [电费] 请求失败，状态码：", resp.status_code)
            return None, False

        data = resp.json()
        if str(data.get("code")) != "200" or "map" not in data:
            print("❌ [电费] 接口返回异常：", data)
            return None, False

        info = data["map"]["showData"]
        balance = info.get("剩余电量", "未知")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ld_name = self.post_data.get("loudong_id", "").split("&")[-1]
        rm_name = self.post_data.get("room_id", "").split("&")[-1]
        print(f"💰 {now} | {ld_name} {rm_name}室 剩余电量：{balance} 度")
        return balance, False