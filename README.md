# ⚡ NUIST iCard Electricity Notifier | 南信大宿舍电费自动推送助手

[![Python](https://img.shields.io/badge/Python-3.9%2B-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

基于 Python 的南京信息工程大学 (NUIST) 宿舍电费自动查询与推送脚本。支持两种登录方式：

- **CAS 统一身份认证跳转登录**：模拟浏览器走 authserver 认证流程，需要**手动抓取 MFA 指纹参数**（`MULTIFACTOR_BROWSER_FINGERPRINT` / `MULTIFACTOR_USERS`）
- **OAuth 一卡通账号密码直登**：直接向 icard 接口提交学号 + 密码，**无需 MFA 参数**

宿舍参数通过脚本内置的**交互式引导**自动获取，**无需手动抓包**。查询指定宿舍电量，并通过 Bark / Server酱 / PushPlus 推送到手机。

---

## 📝 更新日志

### 2026-09-24

- **项目结构重构**：拆分为 `config` / `token_store` / `login` / `main` / `electric_api` / `notifier`，职责单一。
- **新增 Token 本地缓存**：登录成功后缓存 token 到 `token_cache.json`，有效期内跳过登录，避免重复识别验证码 / 提交密码。
- **新增一卡通账号密码直登**：`LOGIN_MODE = "oauth"` 可绕过验证码，直接密码模式登录。
- **新增 Token 失效自动重登**：查询返回 401/403 时自动清缓存、重新登录、重试一次。

### 2026-09-01

- **适配 CAS 新设备二次认证拦截**：新增 `MULTIFACTOR_BROWSER_FINGERPRINT` 与 `MULTIFACTOR_USERS`，通过注入受信任设备 Cookie 指纹绕过二次验证。

### 2026-06-13

- **CAS 自动登录查询**：实现 CAS 统一身份认证自动登录，集成验证码识别，打通电费查询链路。

---

## ✨ 核心特性

- 🔐 **双登录模式**
  - `cas` —— **统一身份认证跳转登录**：模拟 authserver 认证，走验证码 + AES + TGC，需手动抓取 MFA 指纹
  - `oauth` —— **一卡通账号密码直登**：直接向 icard 提交学号密码，无需 MFA
- 🖼️ **本地 OCR 验证码识别**：集成 `ddddocr`，CAS 模式下全自动识别验证码，无需人工干预。
- 💾 **Token 本地缓存**：登录后缓存 token，有效期内直接复用，重复运行零成本。
- 🔁 **Token 失效自动重登**：查询返回 401/403 时自动清缓存、重登、重试一次。
- ⏳ **Token 有效期可视化**：运行时打印剩余有效小时数与过期时间（UTC）。
- 💰 **电费精准查询**：对接一卡通接口，可查指定园区、楼栋、房间的电量。
- 📢 **多渠道推送**：[PushPlus](https://www.pushplus.plus/) / [Bark](https://github.com/Finb/Bark) / [Server酱](https://sct.ftqq.com/)，按需配置，未填的渠道自动跳过。
- 🧭 **交互式引导**：宿舍参数留空时自动进入引导模式，逐级选择园区 → 楼栋 → 房间，输出可直接粘贴到 `config.py` 的配置，**全程无需抓包**。

### 两种登录模式怎么选？

| 模式 | 登录入口 | 需要抓 MFA 参数 | 优点 | 缺点 |
|---|---|---|---|---|
| `"oauth"` | 一卡通 icard 接口 | ❌ 不需要 | 配置最简单，一行搞定 | 密码明文提交给 icard 接口 |
| `"cas"` | 学校统一身份认证 authserver | ✅ **必须手动抓取** | 走官方认证入口，不直接暴露密码 | 需抓 MFA 指纹，验证码可能识别失败 |

---

## 📂 项目结构

```
NUIST-iCard/
├── config.py              # ⚙️ 所有配置常量
├── token_store.py         # 💾 Token 解析 + 本地缓存
├── login.py               # 🔐 登录分发（缓存 → CAS → OAuth）
├── main.py                # 🚀 主流程（引导 + 查询 + 推送）
│
├── nuist_cas.py           # CAS 统一身份认证登录
├── nuist_cas_card.py      # 用 CAS登录的 TGC 换一卡通 token
├── nuist_oauth_card.py    # 直接 Oauth 一卡通账号密码直登
├── electric_api.py        # 电费查询（级联 + 余额）
├── notifier.py            # 通知推送
│
├── token_cache.json       # 💾 运行时生成的 token 缓存
└── requirements.txt       # 依赖清单
```

---

## 🚀 快速开始

### 1. 环境准备

确保 Python 3.9+，然后安装依赖：

```bash
pip install requests ddddocr beautifulsoup4 pycryptodome urllib3
```

或直接：

```bash
pip install -r requirements.txt
```

### 2. 获取宿舍参数（自动引导）

**不需要抓包。** 直接跑一次脚本，它会引导你逐级选择：

```bash
python main.py
```

进入引导模式后，按提示依次选择：

```
🔍 宿舍参数不完整，进入自动引导模式
==================================================
🏫 请选择你所在的区域：
  [0] 本部  (feeitemid=448)
  [1] 天长  (feeitemid=429)
  [2] 沁园42、43栋  (feeitemid=568)
👉 请选择区域编号: 0

💡 已选区域：本部，feeitemid=448

🏫 [级联] 拉取校区列表（feeitemid=448）...
  [0] 晖园  ->  xiaoyu_id=1&晖园
  [1] 沁园  ->  xiaoyu_id=3&沁园
👉 请选择校区编号: 0

🏢 [级联] 拉取楼栋列表（feeitemid=448）...
  [0] 晖园11栋  ->  loudong_id=5&晖园11栋
  ...
👉 请选择楼栋编号: 0

🚪 [级联] 拉取房间列表（feeitemid=448）...
  [0] 101  ->  room_id=14030&101
  ...
👉 请选择房间编号: 0

✅ 已选定：
feeitemid  = "448"
xiaoyu_id  = "1&晖园"
loudong_id = "5&晖园11栋"
room_id    = "14030&101"
（把这 4 个值填回 config.py 顶部，下次就不用再选）
```

把这 4 行**原样复制**到 `config.py` 顶部的对应位置：

```python
feeitemid  = "448"
xiaoyu_id  = "1&晖园"
loudong_id = "5&晖园11栋"
room_id    = "14030&101"
```

下次运行就会跳过引导，直接查询。

<details>
<summary>💡 备选：手动抓包（一般不需要）</summary>

如果引导模式因接口变更等原因无法使用，可以手动抓包：

1. 电脑浏览器登录 [南信大一卡通网页版](https://icard.nuist.edu.cn/plat-pc/businesslobby)。
2. 按 `F12` → **Network** 面板。
3. 页面手动查询一次电费。
4. 找到 `getThirdData` 请求，查看 **Payload / Form Data**。
5. 记录 `feeitemid`、`xiaoyu_id`、`loudong_id`、`room_id`。

</details>

### 3. 获取 MFA 多因素认证指纹（仅 CAS 模式必需）

> ⚠️ 如果你用 **一卡通账号密码直登**（`LOGIN_MODE = "oauth"`），**可跳过本节**，OAuth 不需要任何 MFA 参数。
>
> ⚠️ 自 2026-09-01 起，南信大 **CAS 统一身份认证** 启用 **新设备二次验证 (MFA)**。用 CAS 模式登录**必须**提供两个 Cookie 指纹，否则会被 `isMultifactor: true` 拦截。

抓取步骤：

1. 用 **电脑浏览器** 正常登录 [南信大融合门户](https://authserver.nuist.edu.cn)（走的是 CAS 统一身份认证）。
2. 完成 MFA 二次验证（短信 / 邮箱 / 人脸等），让浏览器被标记为「受信任设备」。
3. 按 `F12` → **Application** → **Cookies** → `authserver.nuist.edu.cn`。
4. 找到并复制这两个 Cookie 的值：

| Cookie 名称 | 说明 |
| --- | --- |
| `MULTIFACTOR_BROWSER_FINGERPRINT` | 浏览器设备指纹 |
| `MULTIFACTOR_USERS` | 多因素用户凭证 |

5. 填进 `config.py` 的对应常量。

### 4. 配置环境变量与运行

为了保护账号隐私与方便云端部署，本脚本采用环境变量读取配置。你无需修改代码，只需在运行前配置以下环境变量：

| 变量名 | 说明 | 必填状态 |
| --- | --- | --- |
| `NUIST_USER` | 南信大统一身份认证账号 (学号) | ✅ 必填 |
| `NUIST_PWD` | 统一身份认证密码 | ✅ 必填 |
| `MULTIFACTOR_BROWSER_FINGERPRINT` | 受信任设备的浏览器指纹 (抓取自 Cookie) | ✅ 必填 (2026.9.1+) |
| `MULTIFACTOR_USERS` | 多因素用户凭证 (抓取自 Cookie) | ✅ 必填 (2026.9.1+) |
| `ICARD_LEVEL` | 宿舍层级参数 (对应抓包的 `level`) | ✅ 必填 |
| `ICARD_FEEITEMID` | 缴费项目号 (对应抓包的 `feeitemid`) | ✅ 必填 |
| `ICARD_XIAOYU` | 校区/园区 ID (对应抓包的 `xiaoyu_id`) | ✅ 必填 |
| `ICARD_LOUDONG` | 楼栋 ID (对应抓包的 `loudong_id`) | ✅ 必填 |
| `ICARD_ROOM` | 房间号 ID (对应抓包的 `room_id`) | ✅ 必填 |
| `PUSHPLUS_TOKEN` | PushPlus 的 Token (微信接收) | 选填 |
| `BARK_KEY` | Bark 的专属 URL Key (iOS 接收) | 选填 |
| `SERVERCHAN_KEY` | Server酱 SendKey | 选填 |

*本地运行测试示例 (Linux/macOS):*

```bash
python main.py
```

首次运行会走完整登录 → 写缓存 → 查询电费：

```
🔐 [Token] 无可用缓存，开始登录...
🚪 [OAuth] 正在登录...
✅ [OAuth] 登录成功
💾 [Token] 已缓存到 token_cache.json
⏳ [Token] 剩余有效期：1680.00 小时（过期时间 UTC：2026-12-03 00:07:06）
💡 [配置] feeitemid=448，区域已配置
⚡ [电费] 正在查询当前电费...
💰 2026-09-24 08:07:18 | 晖园11栋 101室 剩余电量：721.75 度
📱 [通知] 正在通过已配置的渠道分发消息...
```

第二次运行（缓存有效）：

```
♻️ [Token] 命中本地缓存，剩余 1679.xx 小时，跳过登录。
⏳ [Token] 剩余有效期：1679.xx 小时（过期时间 UTC：2026-12-03 00:07:06）
💡 [配置] feeitemid=448，区域已配置
⚡ [电费] 正在查询当前电费...
💰 2026-09-24 08:10:02 | 晖园11栋 101室 剩余电量：721.75 度
```

---

## 📢 通知渠道配置

在 `config.py` 的 `NOTIFIER_KEYS` 里填入对应 key，**填了哪个走哪个，全空则跳过推送**。

| 渠道 | key | 获取方式 |
|---|---|---|
| Bark (iOS) | `BARK_KEY` | [Bark App](https://github.com/Finb/Bark) 里的 URL Key |
| Server酱 | `SERVERCHAN_KEY` | [sct.ftqq.com](https://sct.ftqq.com/) 的 SendKey |
| PushPlus (微信) | `PUSHPLUS_TOKEN` | [pushplus.plus](https://www.pushplus.plus/) 的 Token |

---

## ⏰ 定时运行

### macOS / Linux（crontab）

每天 8:00 自动跑一次：

```bash
crontab -e
```

加入：

```cron
0 8 * * * cd /Users/zy/Desktop/NUIST-iCard && /opt/anaconda3/envs/pycharm/bin/python main.py >> run.log 2>&1
```

### Windows（任务计划程序）

1. 打开「任务计划程序」→ 创建基本任务
2. 触发器：每天 8:00
3. 操作：启动程序 → `python.exe`，参数填 `main.py`，起始位置填项目目录

---

## ⚠️ 免责声明

1. 本项目仅供学习 Python 爬虫、密码学逆向与自动化脚本参考，**严禁用于商业用途或对校园服务器发起恶意高频攻击**。
2. 验证码识别模块 `ddddocr` 为纯本地离线执行；账号密码仅在与南信大官方服务器通信时使用，**本项目不收集、不存储、不上传任何个人隐私数据**。
3. `token_cache.json` 含访问凭证，请勿公开分享。
4. 使用本项目及相关代码所带来的风险和后果由使用者自行承担。

---

## 📄 License

[MIT](LICENSE)
