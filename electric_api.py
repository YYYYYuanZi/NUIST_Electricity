# -*- coding: utf-8 -*-
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TokenInvalidError(Exception):
    """服务端判定 token 无效（401/403）时抛出，由上层负责重登。"""
    pass


class ElectricAPI:
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
        resp = self.session.post(
            self.QUERY_URL, data=data, headers=self._headers(access_token)
        )
        if resp.status_code in (401, 403):
            raise TokenInvalidError(f"HTTP {resp.status_code}")
        return resp

    # ==========================================
    # 级联查询
    #   level=0：首次
    #   level=1：448/429 参数名 xiaoqu_id；568 参数名 building_id
    #   level=2：仅 448/429 用
    # ==========================================
    def _select(self, access_token, params):
        resp = self._post(access_token, params)
        if resp.status_code != 200:
            print(f"❌ [级联] HTTP {resp.status_code}")
            return []
        try:
            data = resp.json()
        except Exception:
            print("❌ [级联] 响应不是 JSON：", resp.text[:200])
            return []
        if str(data.get("code")) != "200":
            print("❌ [级联] 接口返回异常：", data)
            return []
        return data.get("map", {}).get("data", []) or []

    def get_campuses(self, access_token, feeitemid):
        print(f"🏫 [级联] 拉取 level=0（feeitemid={feeitemid}）...")
        return self._select(access_token, {
            "type": "select", "level": "0",
            "feeitemid": feeitemid,
        })

    def get_buildings(self, access_token, feeitemid, parent_value,
                      parent_param="xiaoqu_id"):
        """
        level=1 级联。
        448/429：parent_param="xiaoqu_id"
        568：    parent_param="building_id"
        """
        print(f"🏢 [级联] 拉取 level=1（feeitemid={feeitemid}，"
              f"{parent_param}={parent_value}）...")
        return self._select(access_token, {
            "type": "select", "level": "1",
            "feeitemid": feeitemid,
            parent_param: parent_value,
        })

    def get_rooms(self, access_token, feeitemid, xiaoqu_id, loudong_id):
        print(f"🚪 [级联] 拉取 level=2（feeitemid={feeitemid}）...")
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
            raise TokenInvalidError("access_token 为空")
        if not self.post_data:
            print("⚠️ [电费] 宿舍参数为空，无法查询。")
            return None, False

        print("⚡ [电费] 正在查询当前电费...")
        resp = self._post(access_token, self.post_data)

        if resp.status_code != 200:
            print("❌ [电费] 请求失败，状态码：", resp.status_code)
            return None, False

        try:
            data = resp.json()
        except Exception:
            print("❌ [电费] 响应不是 JSON：", resp.text[:200])
            return None, False

        if str(data.get("code")) != "200":
            print("❌ [电费] 接口返回异常：", data)
            return None, False

        map_data = data.get("map") or {}
        show = map_data.get("showData") or {}

        # 448/429 → 剩余电量（度）；568 → 剩余金额（元）
        if "剩余电量" in show:
            balance = show["剩余电量"]
            unit = "度"
            label = "剩余电量"
        elif "剩余金额" in show:
            balance = show["剩余金额"]
            unit = "元"
            label = "剩余金额"
        else:
            print("❌ [电费] showData 里没找到余额字段：", show)
            return None, False

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ld_raw = (self.post_data.get("building_id")
                  or self.post_data.get("loudong_id", ""))
        rm_raw = self.post_data.get("room_id", "")
        ld_name = ld_raw.split("&")[-1] if ld_raw else ""
        rm_name = rm_raw.split("&")[-1] if rm_raw else ""
        print(f"💰 {now} | {ld_name} {rm_name}室 {label}：{balance} {unit}")
        return balance, False