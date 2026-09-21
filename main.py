# -*- coding: utf-8 -*-

from nuist_cas import NUIST_CAS
from nuist_card import NUIST_Card
from nuist_electric import NUIST_Electric
from notifier import NotificationCenter

# ==========================
# ⚙️ 配置区
# ==========================
USERNAME = "xxxxx"
PASSWORD = "xxxxx"

MULTIFACTOR_BROWSER_FINGERPRINT = ""
MULTIFACTOR_USERS = (
    ""
)

# ---- 宿舍参数（留空则自动引导选择）----
feeitemid  = ""
xiaoyu_id  = ""
loudong_id = ""
room_id    = ""


NOTIFIER_KEYS = {
    "BARK_KEY": "",
    "SERVERCHAN_KEY": "",
    "PUSHPLUS_TOKEN": "",
}

# ==========================



# ==========================
# 🚀 主程序运行入口
# ==========================
if __name__ == '__main__':
    # 1. 登录
    nuistcas = NUIST_CAS(USERNAME, PASSWORD,
                         MULTIFACTOR_BROWSER_FINGERPRINT,
                         MULTIFACTOR_USERS)
    if not nuistcas.login():
        exit(1)

    # 2. 换一卡通 token
    card = NUIST_Card(cas_session=nuistcas)
    if not card.authorize():
        exit(1)

    electric = NUIST_Electric(cas_session=nuistcas)

    # 3. 引导模式
    need_resolve = not (feeitemid and xiaoyu_id and loudong_id and room_id)

    if need_resolve:
        # feeitemid 映射表（仅引导模式用来显示区域名）
        FEEITEM_MAP = {
            "448": "本部",
            "429": "天长",
            "568": "沁园42、43栋",
        }

        print("\n" + "=" * 50)
        print("🔍 宿舍参数不完整，进入自动引导模式")
        print("=" * 50)

        # 3.1 选区域（决定 feeitemid）
        if not feeitemid:
            print("🏫 请选择你所在的区域：")
            feeitem_list = list(FEEITEM_MAP.keys())
            for i, fid in enumerate(feeitem_list):
                print(f"  [{i}] {FEEITEM_MAP[fid]}  (feeitemid={fid})")
            fee_idx = int(input("👉 请选择区域编号: "))
            feeitemid = feeitem_list[fee_idx]

        print(f"\n💡 已选区域：{FEEITEM_MAP.get(feeitemid, '未知')}，feeitemid={feeitemid}\n")

        # 3.2 拉校区
        campuses = electric.get_campuses(card.access_token, feeitemid)
        if not campuses:
            print("❌ 拉取校区列表失败")
            exit(1)
        for i, c in enumerate(campuses):
            print(f"  [{i}] {c.get('name')}  ->  xiaoyu_id={c.get('value')}")
        campus_idx = int(input("👉 请选择校区编号: "))
        xiaoyu_id = campuses[campus_idx]["value"]

        # 3.3 拉楼栋
        buildings = electric.get_buildings(card.access_token, feeitemid, xiaoyu_id)
        if not buildings:
            print("❌ 拉取楼栋列表失败")
            exit(1)
        for i, b in enumerate(buildings):
            print(f"  [{i}] {b.get('name')}  ->  loudong_id={b.get('value')}")
        b_idx = int(input("👉 请选择楼栋编号: "))
        loudong_id = buildings[b_idx]["value"]

        # 3.4 拉房间
        rooms = electric.get_rooms(card.access_token, feeitemid, xiaoyu_id, loudong_id)
        if not rooms:
            print("❌ 拉取房间列表失败")
            exit(1)
        for i, r in enumerate(rooms):
            print(f"  [{i}] {r.get('name')}  ->  room_id={r.get('value')}")
        r_idx = int(input("👉 请选择房间编号: "))
        room_id = rooms[r_idx]["value"]

        print("\n✅ 已选定：")
        print(f'   feeitemid  = "{feeitemid}"')
        print(f'   xiaoyu_id  = "{xiaoyu_id}"')
        print(f'   loudong_id = "{loudong_id}"')
        print(f'   room_id    = "{room_id}"')
        print("   （把这 4 个值填回 main.py 顶部，下次就不用再选）\n")

    else:
        print(f"💡 [配置] feeitemid={feeitemid}，区域已配置")

    # 4. 组装请求参数并查询
    ICARD_DATA = {
        "type": "IEC",
        "level": "3",
        "feeitemid": feeitemid,
        "xiaoyu_id": xiaoyu_id,
        "loudong_id": loudong_id,
        "room_id": room_id,
    }
    electric.post_data = ICARD_DATA
    balance, token_invalid = electric.get_electricity_balance(card.access_token)

    # 5. 推送
    if balance is not None:
        enabled = {k: v for k, v in NOTIFIER_KEYS.items() if v}
        if enabled:
            balance = f"{float(balance):.2f}"
            notifier = NotificationCenter(NOTIFIER_KEYS)
            notifier.dispatch_all(balance)
        else:
            print("ℹ️ [通知] 未配置任何通知渠道，跳过推送。")