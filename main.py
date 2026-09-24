# -*- coding: utf-8 -*-
"""NUIST 电费查询主入口：引导 + 查询 + 推送。"""

import config
import token_store
from login import get_token, print_token_info
from electric_api import ElectricAPI, TokenInvalidError
from notifier import NotificationCenter


# ---------- 工具 ----------
def _pick(options, prompt, value_key="value", name_key="name"):
    if not options:
        return None
    for i, o in enumerate(options):
        print(f"  [{i}] {o.get(name_key)}  ->  {value_key}={o.get(value_key)}")
    idx = int(input(prompt))
    return options[idx][value_key]


def build_params(feeitemid, xiaoqu_id, loudong_id, room_id):
    """按区域返回正确的查询参数。"""
    if feeitemid in config.TWO_LEVEL_FEEITEMIDS:
        return {
            "type": "IEC",
            "level": "2",
            "feeitemid": feeitemid,
            "building_id": xiaoqu_id,   # 两级里 xiaoqu_id 实际是楼栋
            "room_id": loudong_id,      # 两级里 loudong_id 实际是房间
        }
    return {
        "type": "IEC",
        "level": "3",
        "feeitemid": feeitemid,
        "xiaoqu_id": xiaoqu_id,
        "loudong_id": loudong_id,
        "room_id": room_id,
    }


# ---------- 引导 ----------
def resolve_room(electric, access_token):
    feeitemid = config.feeitemid

    print("\n" + "=" * 50)
    print("🔍 宿舍参数不完整，进入自动引导模式")
    print("=" * 50)

    if not feeitemid:
        print("🏫 请选择你所在的区域：")
        fee_list = list(config.FEEITEM_MAP.keys())
        for i, fid in enumerate(fee_list):
            print(f"  [{i}] {config.FEEITEM_MAP[fid]}  (feeitemid={fid})")
        feeitemid = fee_list[int(input("👉 请选择区域编号: "))]

    print(f"\n💡 已选区域：{config.FEEITEM_MAP.get(feeitemid, '未知')}，"
          f"feeitemid={feeitemid}\n")

    if feeitemid in config.TWO_LEVEL_FEEITEMIDS:
        # ---------- 两级：楼栋 → 房间 ----------
        buildings = electric.get_campuses(access_token, feeitemid)
        if not buildings:
            print("❌ 拉取楼栋列表失败")
            exit(1)
        xiaoqu_id = _pick(buildings, "👉 请选择楼栋编号: ")

        rooms = electric.get_buildings(
            access_token, feeitemid, xiaoqu_id,
            parent_param="building_id",     # ← 568 专用
        )
        if not rooms:
            print("❌ 拉取房间列表失败")
            exit(1)
        loudong_id = _pick(rooms, "👉 请选择房间编号: ")
        room_id = ""

        print("\n✅ 已选定（两级区域）：")
        print(f'feeitemid  = "{feeitemid}"')
        print(f'xiaoqu_id  = "{xiaoqu_id}"   # 对 568 来说是 building_id')
        print(f'loudong_id = "{loudong_id}"  # 对 568 来说是 room_id')
        print(f'room_id    = ""')
        print("（把这几个值填回 config.py，下次就不用再选）\n")
    else:
        # ---------- 三级：校区 → 楼栋 → 房间 ----------
        campuses = electric.get_campuses(access_token, feeitemid)
        if not campuses:
            print("❌ 拉取校区列表失败")
            exit(1)
        xiaoqu_id = _pick(campuses, "👉 请选择校区编号: ")

        buildings = electric.get_buildings(
            access_token, feeitemid, xiaoqu_id,
            parent_param="xiaoqu_id",       # ← 448/429
        )
        if not buildings:
            print("❌ 拉取楼栋列表失败")
            exit(1)
        loudong_id = _pick(buildings, "👉 请选择楼栋编号: ")

        rooms = electric.get_rooms(access_token, feeitemid, xiaoqu_id, loudong_id)
        if not rooms:
            print("❌ 拉取房间列表失败")
            exit(1)
        room_id = _pick(rooms, "👉 请选择房间编号: ")

        print("\n✅ 已选定（三级区域）：")
        print(f'feeitemid  = "{feeitemid}"')
        print(f'xiaoqu_id  = "{xiaoqu_id}"')
        print(f'loudong_id = "{loudong_id}"')
        print(f'room_id    = "{room_id}"')
        print("（把这 4 个值填回 config.py，下次就不用再选）\n")

    return feeitemid, xiaoqu_id, loudong_id, room_id


# ---------- 推送 ----------
def push(balance):
    enabled = {k: v for k, v in config.NOTIFIER_KEYS.items() if v}
    if not enabled:
        print("ℹ️ [通知] 未配置任何通知渠道，跳过推送。")
        return
    notifier = NotificationCenter(config.NOTIFIER_KEYS)
    try:
        notifier.dispatch_all(f"{float(balance):.2f}")
    except (TypeError, ValueError):
        notifier.dispatch_all(str(balance))


# ---------- 核心：带自动重登的流程 ----------
def do_flow(session, access_token):
    electric = ElectricAPI(cas_session=session)

    if not (config.feeitemid and config.xiaoqu_id and config.loudong_id):
        feeitemid, xiaoqu_id, loudong_id, room_id = resolve_room(electric, access_token)
    else:
        feeitemid = config.feeitemid
        xiaoqu_id = config.xiaoqu_id
        loudong_id = config.loudong_id
        room_id = config.room_id
        print(f"💡 [配置] feeitemid={feeitemid}，区域已配置")

    params = build_params(feeitemid, xiaoqu_id, loudong_id, room_id)
    print(f"🧾 [参数] {params}")

    electric.post_data = params
    balance, _ = electric.get_electricity_balance(access_token)
    return balance


def run_with_relogin():
    """最多重登一次。第一次用缓存；服务端说无效就强制重登再跑一遍。"""
    session, access_token = get_token()
    if not access_token:
        exit(1)
    print_token_info(access_token)

    try:
        return do_flow(session, access_token)
    except TokenInvalidError as e:
        print(f"🔄 [Token] 服务端判定 token 无效（{e}），清缓存并重新登录...")
        token_store.clear()
        session, access_token = get_token(force_login=True)
        if not access_token:
            exit(1)
        print_token_info(access_token)
        return do_flow(session, access_token)


if __name__ == '__main__':
    balance = run_with_relogin()
    if balance is not None:
        push(balance)