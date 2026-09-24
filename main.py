# -*- coding: utf-8 -*-
"""NUIST 电费查询主入口：引导 + 查询 + 推送。"""

import config
import token_store
from login import get_token, print_token_info
from electric_api import ElectricAPI
from notifier import NotificationCenter


def resolve_room(electric, access_token):
    feeitemid = config.feeitemid
    xiaoyu_id = config.xiaoyu_id
    loudong_id = config.loudong_id
    room_id = config.room_id

    print("\n" + "=" * 50)
    print("🔍 宿舍参数不完整，进入自动引导模式")
    print("=" * 50)

    if not feeitemid:
        print("🏫 请选择你所在的区域：")
        fee_list = list(config.FEEITEM_MAP.keys())
        for i, fid in enumerate(fee_list):
            print(f"  [{i}] {config.FEEITEM_MAP[fid]}  (feeitemid={fid})")
        feeitemid = fee_list[int(input("👉 请选择区域编号: "))]

    print(f"\n💡 已选区域：{config.FEEITEM_MAP.get(feeitemid, '未知')}，feeitemid={feeitemid}\n")

    campuses = electric.get_campuses(access_token, feeitemid)
    if not campuses:
        print("❌ 拉取校区列表失败")
        exit(1)
    for i, c in enumerate(campuses):
        print(f"  [{i}] {c.get('name')}  ->  xiaoyu_id={c.get('value')}")
    xiaoyu_id = campuses[int(input("👉 请选择校区编号: "))]["value"]

    buildings = electric.get_buildings(access_token, feeitemid, xiaoyu_id)
    if not buildings:
        print("❌ 拉取楼栋列表失败")
        exit(1)
    for i, b in enumerate(buildings):
        print(f"  [{i}] {b.get('name')}  ->  loudong_id={b.get('value')}")
    loudong_id = buildings[int(input("👉 请选择楼栋编号: "))]["value"]

    rooms = electric.get_rooms(access_token, feeitemid, xiaoyu_id, loudong_id)
    if not rooms:
        print("❌ 拉取房间列表失败")
        exit(1)
    for i, r in enumerate(rooms):
        print(f"  [{i}] {r.get('name')}  ->  room_id={r.get('value')}")
    room_id = rooms[int(input("👉 请选择房间编号: "))]["value"]

    print("\n✅ 已选定：")
    print(f'feeitemid  = "{feeitemid}"')
    print(f'xiaoyu_id  = "{xiaoyu_id}"')
    print(f'loudong_id = "{loudong_id}"')
    print(f'room_id    = "{room_id}"')
    print("（把这 4 个值填回 config.py 顶部，下次就不用再选）\n")
    return feeitemid, xiaoyu_id, loudong_id, room_id


def query_balance(electric, access_token, params):
    electric.post_data = params
    return electric.get_electricity_balance(access_token)


def push(balance):
    enabled = {k: v for k, v in config.NOTIFIER_KEYS.items() if v}
    if not enabled:
        print("ℹ️ [通知] 未配置任何通知渠道，跳过推送。")
        return
    notifier = NotificationCenter(config.NOTIFIER_KEYS)
    notifier.dispatch_all(f"{float(balance):.2f}")


if __name__ == '__main__':
    session, access_token = get_token()
    if not access_token:
        exit(1)
    print_token_info(access_token)

    electric = ElectricAPI(cas_session=session)

    if not (config.feeitemid and config.xiaoyu_id
            and config.loudong_id and config.room_id):
        feeitemid, xiaoyu_id, loudong_id, room_id = resolve_room(electric, access_token)
    else:
        feeitemid = config.feeitemid
        xiaoyu_id = config.xiaoyu_id
        loudong_id = config.loudong_id
        room_id = config.room_id
        print(f"💡 [配置] feeitemid={feeitemid}，区域已配置")

    params = {
        "type": "IEC", "level": "3",
        "feeitemid": feeitemid,
        "xiaoyu_id": xiaoyu_id,
        "loudong_id": loudong_id,
        "room_id": room_id,
    }

    balance, token_invalid = query_balance(electric, access_token, params)

    if token_invalid:
        print("🔄 [Token] 查询时发现 token 失效，清缓存并重新登录...")
        token_store.clear()
        session, access_token = get_token(force_login=True)
        if not access_token:
            exit(1)
        print_token_info(access_token)
        electric = NUIST_Electric(cas_session=session)
        balance, token_invalid = query_balance(electric, access_token, params)

    if balance is not None:
        push(balance)