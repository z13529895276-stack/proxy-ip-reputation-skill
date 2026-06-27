#!/usr/bin/env python3
"""采集代理出口 IP 和信誉分析证据。

脚本不依赖 API Key，只使用公开查询接口，并设置较短超时时间。
输出 JSON，方便 Agent 基于证据生成可读分析报告。
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from typing import Any

TIMEOUT = 12
USER_AGENT = "proxy-ip-reputation-skill/1.1"


def run(cmd: list[str], timeout: int = 8) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"ok": proc.returncode == 0, "code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def build_opener(proxy: str | None):
    if proxy:
        return urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener()


def fetch_json(url: str, proxy: str | None = None) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with build_opener(proxy).open(req, timeout=TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return {"ok": True, "status": resp.status, "json": json.loads(body)}
            except json.JSONDecodeError:
                return {"ok": True, "status": resp.status, "text": body[:4000]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def fetch_text(url: str, proxy: str | None = None) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with build_opener(proxy).open(req, timeout=TIMEOUT) as resp:
            return {"ok": True, "status": resp.status, "text": resp.read().decode("utf-8", errors="replace")[:4000]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def parse_scutil_proxy(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ["HTTP", "HTTPS", "SOCKS"]:
        enabled = re.search(rf"{key}Enable\s*:\s*(\d+)", text)
        host = re.search(rf"{key}Proxy\s*:\s*(\S+)", text)
        port = re.search(rf"{key}Port\s*:\s*(\d+)", text)
        result[key.lower()] = {
            "enabled": enabled.group(1) == "1" if enabled else False,
            "host": host.group(1) if host else None,
            "port": int(port.group(1)) if port else None,
        }
    return result


def detect_proxy() -> dict[str, Any]:
    data: dict[str, Any] = {
        "platform": platform.platform(),
        "env": {k: v for k, v in os.environ.items() if k.lower() in {"http_proxy", "https_proxy", "all_proxy", "no_proxy"}},
    }
    if sys.platform == "darwin":
        scutil = run(["scutil", "--proxy"])
        data["scutil"] = scutil
        if scutil.get("stdout"):
            data["system_proxy"] = parse_scutil_proxy(scutil["stdout"])
    return data


def inferred_http_proxy(detected: dict[str, Any]) -> str | None:
    env = detected.get("env") or {}
    for key in ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"]:
        if env.get(key):
            return env[key]
    http = ((detected.get("system_proxy") or {}).get("http") or {})
    if http.get("enabled") and http.get("host") and http.get("port"):
        return f"http://{http['host']}:{http['port']}"
    return None


def get_exit_samples(proxy: str | None, repeats: int) -> list[dict[str, Any]]:
    samples = []
    for _ in range(repeats):
        samples.append(fetch_json("https://api.ipify.org?format=json", proxy=proxy))
        if repeats > 1:
            time.sleep(1)
    return samples


def extract_ip(samples: list[dict[str, Any]]) -> str | None:
    for sample in samples:
        payload = sample.get("json") if sample.get("ok") else None
        if isinstance(payload, dict) and payload.get("ip"):
            return str(payload["ip"])
    return None


def collect_cloudflare(proxy: str | None) -> dict[str, Any]:
    trace = fetch_text("https://www.cloudflare.com/cdn-cgi/trace", proxy=proxy)
    if trace.get("ok") and trace.get("text"):
        parsed = {}
        for line in trace["text"].splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                parsed[key] = value
        trace["parsed"] = parsed
    return trace


def collect_ip_reputation(ip: str, proxy: str | None) -> dict[str, Any]:
    encoded = urllib.parse.quote(ip)
    return {
        "core_sources": {
            "ip_api": fetch_json(
                "http://ip-api.com/json/"
                + encoded
                + "?fields=status,message,query,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,asname,reverse,mobile,proxy,hosting",
                proxy=proxy,
            ),
            "ipapi_is": fetch_json(f"https://ipapi.is/{encoded}", proxy=proxy),
            "proxycheck": fetch_json(f"https://proxycheck.io/v2/{encoded}?vpn=1&asn=1&risk=1&node=1&time=1&inf=1", proxy=proxy),
            "ipinfo_or_ip_sb": {
                "ipinfo": fetch_json(f"https://ipinfo.io/{encoded}/json", proxy=proxy),
                "ip_sb": fetch_json(f"https://api.ip.sb/geoip/{encoded}", proxy=proxy),
            },
            "rdap_arin": fetch_json(f"https://rdap.arin.net/registry/ip/{encoded}", proxy=proxy),
        },
        "supplements": {
            "ipwhois": fetch_json(f"https://ipwho.is/{encoded}?security=1", proxy=proxy),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="以 JSON 形式采集代理 IP 信誉分析证据。", add_help=False)
    parser._optionals.title = "选项"
    parser.add_argument("-h", "--help", action="help", help="显示帮助信息并退出。")
    parser.add_argument("--current", action="store_true", help="检测当前系统/终端代理和当前出口 IP。")
    parser.add_argument("--ip", help="检测指定 IP 地址。")
    parser.add_argument("--proxy", help="使用指定代理 URL，例如 http://127.0.0.1:7897。")
    parser.add_argument("--repeats", type=int, default=5, help="当前出口/代理出口的 IP 采样次数。")
    parser.add_argument("--json", action="store_true", help="输出 JSON。这也是默认输出格式。")
    args = parser.parse_args()

    detected = detect_proxy() if args.current or not args.ip else {}
    proxy = args.proxy or inferred_http_proxy(detected)

    direct_samples = get_exit_samples(None, args.repeats if args.current else 1)
    proxy_samples = get_exit_samples(proxy, args.repeats) if proxy else []

    target_ip = args.ip or extract_ip(proxy_samples) or extract_ip(direct_samples)
    reputation = collect_ip_reputation(target_ip, proxy) if target_ip else {}

    output = {
        "input": {"current": args.current, "ip": args.ip, "proxy": args.proxy, "repeats": args.repeats},
        "detected_proxy": detected,
        "used_proxy": proxy,
        "direct_exit_samples": direct_samples,
        "proxy_exit_samples": proxy_samples,
        "target_ip": target_ip,
        "cloudflare_trace": collect_cloudflare(proxy),
        "reputation": reputation,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
