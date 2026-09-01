# ⚡ NUIST iCard Electricity Notifier | 南信大宿舍电费自动推送助手

基于 Python 的南京信息工程大学 (NUIST) 宿舍电费自动查询与推送脚本。通过模拟登录校园统一身份认证系统 (CAS)，抓取一卡通大厅接口数据，实现每日定时查询电费，并通过微信、iOS 等多种渠道将结果自动推送到你的手机上。

---

## 📝 更新日志

### 2026-09-01
- **适配 CAS 新设备二次认证拦截**：新增 `MULTIFACTOR_BROWSER_FINGERPRINT` 与 `MULTIFACTOR_USERS` 环境变量，通过注入受信任设备 Cookie 指纹绕过二次验证拦截。
- 新增 MFA 参数抓取指引。

---

## ✨ 核心特性

* 🔐 **CAS 全自动认证**：内置前端 `encrypt.js` 的 AES 逆向加密算法，自动换取全局 TGC 通行证，实现免密访问下游业务。
* 🖼️ **本地 OCR 验证码识别**：无缝集成 `ddddocr`，全自动光速识别登录验证码，无需人工干预或第三方打码平台。
* 💰 **电费精准查询**：直接对接南信大一卡通业务接口，可灵活配置抓取指定校区、指定楼栋、具体宿舍的电量数据。
* 📢 **多渠道消息触达**：
    * [PushPlus](https://www.pushplus.plus/) (微信公众号免签推送)
    * [Bark](https://github.com/Finb/Bark) (iOS 专属系统级无缝推送)
    * [Server酱](https://sct.ftqq.com/) (全平台跨生态支持)
* ☁️ **完美适配云端部署**：账号、推送密钥及所有宿舍参数全部抽离为环境变量 (Env) 注入，代码零入侵，完美适配 GitHub Actions 或各类 Serverless 云函数，实现零成本自动化挂机。

---

## 🚀 快速开始

### 1. 环境准备

确保你的设备上安装了 Python 3.8+。将本项目克隆到本地后，安装必需的依赖包：

```bash
pip install requests ddddocr beautifulsoup4 pycryptodome
```

### 2. 获取宿舍参数 (关键抓包步骤)

由于每个人的宿舍对应唯一的 ID，你需要先通过浏览器抓包获取属于你自己的 5 个宿舍参数。

> **💡 抓包提示：**
> 1. 在电脑浏览器登录 [南信大一卡通网页版](https://icard.nuist.edu.cn/plat-pc/businesslobby?synjones-auth=&visitor=0&synAccessSource=pc&source=pc&type=url)。
> 2. 按 `F12` 打开开发者工具，进入“网络 (Network)”面板。
> 3. 在页面上手动查询一次电费。
> 4. 找到名为 `getThirdData` 的网络请求，查看其 **负载 (Payload)** 或 **表单数据 (Form Data)**。
> 5. 记录下里面的 `level`, `feeitemid`, `xiaoyu_id`, `loudong_id`, `room_id` 这 5 个对应的值。

### 3. 获取 MFA 多因素认证指纹 (2026.9.1 新增)

> **⚠️ 重要**：自 2026 年 9 月 1 日起，南信大 CAS 统一身份认证系统正式启用 **新设备二次验证 (MFA)**。若直接使用账号密码登录，接口将返回 `isMultifactor: true` 并拦截自动化请求。

本项目通过 **伪造受信任设备指纹** 的方式绕过 MFA 二次验证。你需要从浏览器中抓取两个指纹标识：

1. 使用 **电脑浏览器** (建议 Chrome/Edge) 正常登录 [南信大融合门户](https://authserver.nuist.edu.cn)。
2. 在登录过程中 **完成 MFA 二次验证** (短信/邮箱/人脸等)，确保当前浏览器被系统标记为“受信任设备”。
3. 登录成功后，按 `F12` 打开开发者工具，进入 **应用程序 (Application)** 面板。
4. 在左侧菜单找到 **存储 → Cookie**，选中 `authserver.nuist.edu.cn` 域名。
5. 查找并记录以下两个 Cookie 的值：

| Cookie 名称 | 说明 |
| --- | --- |
| `MULTIFACTOR_BROWSER_FINGERPRINT` | 浏览器设备指纹 (MFA 信任标识) |
| `MULTIFACTOR_USERS` | 多因素用户凭证 (包含设备绑定信息) |

> 📌 抓取后配置到环境变量中，脚本将自动携带这些 Cookie 发起登录，从而绕过 `isMultifactor` 校验。

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
# 1. 账号与 MFA 指纹配置 (2026.9.1 起必须)
export NUIST_USER="2024xxxxxxxx"
export NUIST_PWD="YourPassword"
export MULTIFACTOR_BROWSER_FINGERPRINT="a1b2c3d4e5f6g7h8i9j0"
export MULTIFACTOR_USERS="%7B%22userId%22%3A%222024xxxxxx%22%2C%22type%22%3A%22sms%22%7D"

# 2. 推送配置 (选填)
export PUSHPLUS_TOKEN="YourPushPlusToken"

# 3. 宿舍专属参数配置 (注意：含特殊字符 & 的中文字符串必须加双引号)
export ICARD_LEVEL="3"
export ICARD_FEEITEMID="448"
export ICARD_XIAOYU="3&沁园"
export ICARD_LOUDONG="23&沁园30号栋"
export ICARD_ROOM="4186&135"

# 4. 运行脚本
python main.py
```

> ⚠️ **注意**：若未配置 `MULTIFACTOR_BROWSER_FINGERPRINT` 与 `MULTIFACTOR_USERS`，脚本在遇到 MFA 拦截时将自动报错提示，需手动补充后方可继续使用。

---

## ⚠️ 免责声明

1. 本项目仅供学习 Python 爬虫接口调用、密码学逆向与自动化脚本参考，**严禁用于任何商业用途或对校园服务器发起恶意高频攻击**。
2. 验证码识别模块 `ddddocr` 为纯本地离线执行，用户的账号与密码仅在与南信大官方服务器 (authserver.nuist.edu.cn) 通信时使用，**本项目不收集、不存储、不上传任何个人隐私数据**。
3. 使用本项目及相关代码所带来的风险和后果由使用者自行承担。
```

---
