---
name: "proxy-ip-reputation"
description: "Add fixed reputation source checklist for proxy IP audits."
---

# Proxy IP Reputation

Use this skill to audit a proxy exit IP and explain whether the network environment is clean enough for everyday browsing, OpenAI/Codex/OpenClaw, Google, WhatsApp, account login, or more sensitive platform use.

The skill is designed to be shareable: when installed on another machine, use the bundled script first to collect evidence, then interpret the result in plain language.

## Quick Start

When the user asks to check their current proxy, run:

```bash
python3 scripts/proxy_ip_reputation.py --current --json
```

When the user gives a specific IP:

```bash
python3 scripts/proxy_ip_reputation.py --ip 216.167.4.111 --json
```

When the user gives a local proxy endpoint:

```bash
python3 scripts/proxy_ip_reputation.py --proxy http://127.0.0.1:7897 --json
```

Use the JSON as evidence, then produce a human-readable report.

## Inputs

Accept any of these:

- A specific IP address.
- A proxy endpoint such as `http://127.0.0.1:7897` or `socks5h://127.0.0.1:7897`.
- A request like "查现在代理", "这个节点纯不纯", "IP 质量怎么样", "适不适合 OpenAI/WhatsApp".

If no IP is provided, inspect the current machine's proxy settings and determine the current exit IP.

## Core Sources

Use these five core sources by default. If one fails or rate-limits, mark it unavailable and continue.

1. `ip-api.com`
   - Purpose: quick geo, ASN, ISP/org, `proxy`, `hosting`, and `mobile` flags.
   - Key fields: country, city, timezone, ISP/org, AS/asname, reverse, mobile, proxy, hosting.

2. `ipapi.is`
   - Purpose: higher-signal IP type and abuse classification.
   - Key fields: `is_datacenter`, `is_proxy`, `is_vpn`, `is_tor`, `is_abuser`, company type, company abuse score, ASN abuse score.

3. `proxycheck.io`
   - Purpose: explicit proxy/VPN detection, risk score, provider, type, and subnet/device hints.
   - Key fields: `proxy`, `type`, `risk`, provider, ASN, range, devices/subnet.

4. `ipinfo.io` or `api.ip.sb`
   - Purpose: independent geo/ASN/provider cross-check.
   - Use `ipinfo.io` when available; if rate-limited, use `api.ip.sb/geoip`.
   - Key fields: IP, country/region/city, org/ASN, timezone, coordinates.

5. RIR RDAP, usually `rdap.arin.net` for ARIN space.
   - Purpose: official registration owner, allocated range, network name, organization, abuse/NOC contacts.
   - Use the relevant RIR when ARIN is not authoritative.
   - Key fields: network name, CIDR/range, registrant org, allocation/registration dates, status.

Optional supplements:

- `ipwho.is` for another geo/connection check.
- Cloudflare trace (`https://www.cloudflare.com/cdn-cgi/trace`) for current edge location, country, and the IP seen by Cloudflare.
- DNSBL checks only when DNS behavior is trustworthy.

## Workflow

1. Detect proxy configuration.
   - Use the bundled script with `--current` first.
   - On macOS, the script reads `scutil --proxy` and shell proxy environment variables.
   - If the script cannot infer a proxy endpoint, still check direct exit IP and report that no explicit local proxy was detected.
   - Completion criterion: know the proxy host/port, enabled modes, and whether shell environment variables override system proxy.

2. Determine exit IP stability.
   - Compare direct, HTTP-proxy, and SOCKS-proxy exits when available.
   - Repeat 3-5 times when an exit changes or the user cares about stability.
   - Completion criterion: classify the exit as fixed, rotating, or split across HTTP/SOCKS/TUN paths.

3. Run the five-source reputation pass.
   - Query the five core sources above and preserve raw JSON/text evidence where possible.
   - If HTTP/SOCKS/TUN paths have different exits, run the pass for each relevant IP or state which IP was checked.
   - Completion criterion: every core source is represented in the report as success, failed, rate-limited, blocked, or not applicable.

4. Compare source agreement.
   - Consistent clean results across all sources are stronger than a single clean result.
   - Any source marking `proxy=yes`, `VPN`, datacenter, high risk, Tor, or abuse should lower confidence.
   - Treat provider class carefully: business ISP/commercial network is better than generic VPS, but still not residential.
   - Completion criterion: identify where sources agree, disagree, or are inconclusive.

5. Treat blacklist checks carefully.
   - DNSBL results are useful only if DNS resolution looks normal.
   - If DNS returns reserved or suspicious addresses such as `198.18.x.x`, mark DNSBL as unreliable.
   - Do not claim AbuseIPDB, Spamhaus, or protected sites are clean if automation was blocked or data was inconclusive.
   - Completion criterion: either give reliable blacklist findings or explicitly say the blacklist section is inconclusive.

6. Interpret for the user.
   - For OpenAI/Codex/OpenClaw: prefer stable supported-country exits, low proxy/VPN flags, and low abuse scores.
   - For WhatsApp/Google/account login: prefer stable IP, same country over time, low sharing, low risk score, and no obvious VPN flag.
   - For sensitive account registration/payment/e-commerce: residential or high-quality business ISP is better than VPS/datacenter/VPN.
   - Completion criterion: provide a practical recommendation, not just raw data.

## Report Format

Use concise Chinese by default when the user uses Chinese. Lead with the conclusion.

Include:

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

## Scoring Heuristic

Use rough scores only; do not imply certainty.

- 9-10: stable residential/mobile or very clean business ISP, low/no proxy flags, low abuse score.
- 7-8: clean commercial ISP/business network, not residential, not obviously VPN/proxy.
- 5-6: usable but mixed signals, datacenter/VPS or one source flags VPN/proxy.
- 3-4: obvious VPN/proxy/datacenter with moderate risk score or unstable exit pool.
- 1-2: Tor, high-risk abuse signals, blacklisted, or heavily shared/unstable.

## Provider Questions

When relevant, suggest asking:

- Is this IP dedicated or shared?
- How many users share one exit IP?
- Is it fixed IP or rotating pool?
- Is it residential, business ISP, or datacenter/VPS?
- Which ASN/provider and city is it?
- Can they replace the IP if OpenAI/Google/WhatsApp flags it?
- Is the line routed through HTTP proxy, SOCKS, TUN, or mixed paths?

## Safety and Privacy

Do not expose proxy credentials. It is fine to report public exit IPs and ASN data. If commands reveal credentials, redact them and warn the user not to screenshot or share them.

## Failure Handling

If a source rate-limits or fails, continue with other sources and mark that source as unavailable. Do not block the report on one failed API.

If the script cannot detect a current proxy but the user believes one is enabled, ask for the local proxy endpoint or tell them to enable system proxy/TUN and rerun.
