# Proxy IP Reputation Skill

A shareable skill for checking proxy/VPN exit IP quality. It collects evidence from multiple public sources, then guides an agent to explain whether a node looks residential, business ISP, datacenter/VPS, VPN/proxy, shared, risky, or clean enough for OpenAI, Google, WhatsApp, and account-login use.

## What It Checks

- Current system proxy and shell proxy settings
- Direct and proxied exit IP samples
- Geo, ASN, ISP, organization, and RDAP registration
- Proxy/VPN/datacenter/abuse flags from five core sources:
  - ip-api.com
  - ipapi.is
  - proxycheck.io
  - ipinfo.io or api.ip.sb
  - RDAP, such as rdap.arin.net

## Install

Clone this repo, then copy the `proxy-ip-reputation` folder into your agent's skills directory.

OpenClaw:

```bash
mkdir -p ~/.openclaw/workspace/skills
cp -R proxy-ip-reputation ~/.openclaw/workspace/skills/
```

Codex:

```bash
mkdir -p ~/.codex/skills
cp -R proxy-ip-reputation ~/.codex/skills/
```

Claude Code:

```bash
mkdir -p ~/.claude/skills
cp -R proxy-ip-reputation ~/.claude/skills/
```

Project-local Claude Code:

```bash
mkdir -p .claude/skills
cp -R proxy-ip-reputation .claude/skills/
```

## Use

Ask your agent:

```text
Check my current proxy IP quality.
```

Or:

```text
Is this IP clean enough for OpenAI and WhatsApp: 216.167.4.111?
```

You can also run the bundled collector directly:

```bash
python3 proxy-ip-reputation/scripts/proxy_ip_reputation.py --current --json
python3 proxy-ip-reputation/scripts/proxy_ip_reputation.py --ip 216.167.4.111 --json
python3 proxy-ip-reputation/scripts/proxy_ip_reputation.py --proxy http://127.0.0.1:7897 --json
```

The script uses only the Python standard library and public no-key endpoints. Some sources may rate-limit or block automated requests; the skill tells the agent to mark those sources unavailable and continue.

