---
name: "proxy-ip-reputation"
description: "用于检测代理/VPN 节点质量、出口国家、ASN、IP 纯净度、住宅/机房/VPN 标记、共享风险，以及是否适合 OpenAI、Google、WhatsApp、账号登录等风控场景。"
---

# 代理 IP 质量检测

使用这个 Skill 审计代理出口 IP，并解释当前网络环境是否适合日常浏览、OpenAI/Codex/OpenClaw、Google、WhatsApp、账号登录，或更敏感的平台使用。

这个 Skill 设计成可分享版本：安装到另一台电脑后，先运行内置脚本收集证据，再把结果解释成普通人能看懂的报告。

## 快速开始

当用户要检查当前代理时，运行：

```bash
python3 scripts/proxy_ip_reputation.py --current --json
```

当用户提供指定 IP 时，运行：

```bash
python3 scripts/proxy_ip_reputation.py --ip 216.167.4.111 --json
```

当用户提供本地代理端口时，运行：

```bash
python3 scripts/proxy_ip_reputation.py --proxy http://127.0.0.1:7897 --json
```

把 JSON 输出作为证据，再生成一份面向用户的可读报告。

## 输入

接受以下任意形式：

- 一个具体 IP 地址。
- 一个代理端点，例如 `http://127.0.0.1:7897` 或 `socks5h://127.0.0.1:7897`。
- 类似“查现在代理”“这个节点纯不纯”“IP 质量怎么样”“适不适合 OpenAI/WhatsApp”的自然语言请求。

如果没有提供 IP，先检查当前机器的代理设置，再确定当前出口 IP。

## 五个核心来源

默认使用下面五个核心来源。某个来源失败或限流时，标记为不可用并继续执行。

1. `ip-api.com`
   - 用途：快速检查地理位置、ASN、ISP/组织、`proxy`、`hosting`、`mobile` 标记。
   - 关键字段：国家、城市、时区、ISP/组织、AS/asname、反向解析、mobile、proxy、hosting。

2. `ipapi.is`
   - 用途：检查更高信号的 IP 类型和滥用风险分类。
   - 关键字段：`is_datacenter`、`is_proxy`、`is_vpn`、`is_tor`、`is_abuser`、公司类型、公司滥用分、ASN 滥用分。

3. `proxycheck.io`
   - 用途：显式检测代理/VPN、风险分、服务商、类型、网段设备数量线索。
   - 关键字段：`proxy`、`type`、`risk`、provider、ASN、range、devices/subnet。

4. `ipinfo.io` 或 `api.ip.sb`
   - 用途：独立交叉验证地理位置、ASN、运营商。
   - `ipinfo.io` 可用时优先使用；如果被限流，使用 `api.ip.sb/geoip` 补充。
   - 关键字段：IP、国家/地区/城市、组织/ASN、时区、坐标。

5. RIR RDAP，通常 ARIN 空间使用 `rdap.arin.net`
   - 用途：查询官方注册主体、分配网段、网络名称、组织、滥用/NOC 联系信息。
   - 如果 ARIN 不是权威注册局，使用对应地区的 RIR。
   - 关键字段：network name、CIDR/range、注册组织、分配/注册日期、状态。

可选补充：

- `ipwho.is`：额外做一次地理位置和连接信息交叉验证。
- Cloudflare trace（`https://www.cloudflare.com/cdn-cgi/trace`）：查看 Cloudflare 看到的出口 IP、国家和边缘机房。
- DNSBL：只在 DNS 解析行为可信时使用。

## 工作流程

1. 检测代理配置。
   - 优先运行内置脚本的 `--current`。
   - macOS 上脚本会读取 `scutil --proxy` 和终端代理环境变量。
   - 如果脚本无法推断代理端口，也要检查直连出口 IP，并说明没有检测到显式本地代理。
   - 完成标准：知道代理 host/port、启用模式，以及终端环境变量是否覆盖系统代理。

2. 判断出口 IP 是否稳定。
   - 可用时分别比较直连、HTTP 代理、SOCKS 代理出口。
   - 如果出口发生变化，或用户关心稳定性，重复采样 3-5 次。
   - 完成标准：把出口归类为固定、轮换，或 HTTP/SOCKS/TUN 路径不一致。

3. 执行五源信誉检查。
   - 查询上面的五个核心来源，并尽量保留原始 JSON/text 证据。
   - 如果 HTTP/SOCKS/TUN 路径出口不同，要分别检查相关 IP，或明确说明本次检查的是哪个 IP。
   - 完成标准：报告中每个核心来源都要有状态：成功、失败、限流、被拦截或不适用。

4. 比较来源一致性。
   - 所有来源都显示干净，比单个来源显示干净更可信。
   - 任何来源标记 `proxy=yes`、`VPN`、机房、高风险、Tor、滥用，都要降低信心。
   - 谨慎判断服务商类型：商宽/商业 ISP 通常比普通 VPS 好，但仍然不等于住宅 IP。
   - 完成标准：指出哪些来源一致、哪些来源冲突、哪些来源不确定。

5. 谨慎处理黑名单检查。
   - DNSBL 结果只有在 DNS 解析正常时才有参考价值。
   - 如果 DNS 返回 `198.18.x.x` 这类保留地址或可疑地址，要标记 DNSBL 不可靠。
   - 如果 AbuseIPDB、Spamhaus 或类似网站阻止自动化查询，不能声称它们显示干净。
   - 完成标准：要么给出可靠黑名单结论，要么明确说黑名单部分无法确认。

6. 面向用户解释。
   - OpenAI/Codex/OpenClaw：优先稳定、支持地区出口、低代理/VPN 标记、低滥用分。
   - WhatsApp/Google/账号登录：优先固定 IP、长期同国家、低共享、低风险分、无明显 VPN 标记。
   - 敏感注册/支付/电商账号：住宅或高质量商宽优于 VPS/机房/VPN。
   - 完成标准：给出实际使用建议，而不是只堆原始数据。

## 报告格式

用户使用中文时默认用简洁中文回答。开头先给结论。

包含：

```text
结论：一句话说明这个 IP/节点质量。

当前代理/出口：
- 代理端口/模式
- 当前出口 IP 或出口池
- 是否固定/轮换

地理与归属：
- 国家/城市/时区
- ASN/运营商/组织
- 是否机房/VPS/商宽/住宅/移动

五源信誉/风控结果：
- ip-api：proxy / hosting / mobile / ISP / ASN
- ipapi.is：datacenter / proxy / vpn / tor / abuser / abuse score
- proxycheck.io：proxy / type / risk / provider / subnet devices
- ipinfo.io 或 ip.sb：geo / org / ASN 交叉验证
- RDAP：官方注册组织 / 网段 / network name

纯净度判断：
- 代理识别风险
- 滥用风险
- 住宅纯净度
- 共享/轮换风险
- 平台友好度

适合/不适合：
- OpenAI / Google / WhatsApp / 日常浏览 / 敏感账号

注意事项：
- 不一致来源
- DNSBL 不可靠或查询受限
- 代理池变化

建议问代理商的问题。
```

## 评分口径

分数只是粗略估计，不要表达成确定事实。

- 9-10：稳定住宅/移动网络，或非常干净的商宽；几乎没有代理标记，滥用分低。
- 7-8：干净商业 ISP/商宽；不是住宅，但也没有明显 VPN/代理标记。
- 5-6：可用但信号混杂；可能是机房/VPS，或有一个来源标记 VPN/代理。
- 3-4：明显 VPN/代理/机房，中等风险分，或出口池不稳定。
- 1-2：Tor、高滥用信号、黑名单、严重共享或非常不稳定。

## 建议询问代理商

需要时建议用户询问：

- 这个 IP 是独享还是共享？
- 一个出口 IP 最多多少人同时使用？
- 是固定 IP 还是轮换池？
- 是住宅、商宽，还是机房/VPS？
- ASN、服务商和城市分别是什么？
- 如果被 OpenAI/Google/WhatsApp 风控，能不能更换 IP？
- 线路是通过 HTTP 代理、SOCKS、TUN，还是混合路径？

## 安全和隐私

不要暴露代理凭证。公开出口 IP 和 ASN 信息可以报告。如果命令输出里包含账号、密码、token 或完整代理 URL，要先打码，并提醒用户不要截图或外发。

## 失败处理

如果某个来源限流或失败，继续使用其他来源，并把该来源标记为不可用。不要因为一个 API 失败就中断报告。

如果脚本无法检测当前代理，但用户认为代理已启用，询问本地代理端点，或提醒用户开启系统代理/TUN 后重试。

