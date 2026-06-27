# 代理 IP 质量检测 Skill

这是一个可分享的代理节点质量检测 Skill。它会从多个公开来源收集证据，再指导 Agent 判断一个代理出口像不像住宅、商宽、机房/VPS、VPN/代理、多人共享节点，是否适合 OpenAI、Google、WhatsApp、账号登录等场景。

## 会检测什么

- 当前系统代理和终端环境变量代理设置
- 直连出口 IP 和代理出口 IP，多次采样判断是否轮换
- 国家、城市、ASN、ISP、组织、RDAP 官方注册信息
- 五个核心来源的代理/VPN/机房/滥用风险标记：
  - ip-api.com
  - ipapi.is
  - proxycheck.io
  - ipinfo.io 或 api.ip.sb
  - RDAP，例如 rdap.arin.net

## 安装

先克隆这个仓库，然后把 `proxy-ip-reputation` 文件夹复制到对应 Agent 的 skills 目录。

OpenClaw：

```bash
mkdir -p ~/.openclaw/workspace/skills
cp -R proxy-ip-reputation ~/.openclaw/workspace/skills/
```

Codex：

```bash
mkdir -p ~/.codex/skills
cp -R proxy-ip-reputation ~/.codex/skills/
```

Claude Code：

```bash
mkdir -p ~/.claude/skills
cp -R proxy-ip-reputation ~/.claude/skills/
```

Claude Code 项目级安装：

```bash
mkdir -p .claude/skills
cp -R proxy-ip-reputation .claude/skills/
```

## 使用

可以直接问你的 Agent：

```text
帮我查一下当前代理 IP 质量。
```

或者：

```text
帮我看这个 IP 适不适合 OpenAI 和 WhatsApp：216.167.4.111
```

也可以直接运行内置采集脚本：

```bash
python3 proxy-ip-reputation/scripts/proxy_ip_reputation.py --current --json
python3 proxy-ip-reputation/scripts/proxy_ip_reputation.py --ip 216.167.4.111 --json
python3 proxy-ip-reputation/scripts/proxy_ip_reputation.py --proxy http://127.0.0.1:7897 --json
```

脚本只使用 Python 标准库和不需要 API Key 的公开查询接口。部分来源可能会限流或拦截自动请求；Skill 会要求 Agent 把这些来源标记为不可用，并继续使用其他来源交叉判断。

