#!/usr/bin/env python3
"""
轻量代理池 — 从公开源拉取 HTTP 代理，验证可用性，输出 proxychains 格式。
用法:
  python3 proxy_pool.py           # 输出 proxychains 配置
  python3 proxy_pool.py --test    # 测试代理并输出可用列表
  watch -n 300 proxy_pool.py      # 每5分钟刷新

免费代理源（内置）:
  - proxylist.geonode.com
  - api.proxyscrape.com
  - raw.githubusercontent.com (TheSpeedX/PROXY-List)
"""

import requests
import sys
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── 代理源 ──────────────────────────────────────────
SOURCES = [
    # geonode 免费 API（每天限1000次）
    "https://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps",
    # proxyscrape
    "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&proxy_format=protocolipport&format=text&timeout=20000",
    "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=https&proxy_format=protocolipport&format=text&timeout=20000",
]

TEST_URL = "http://httpbin.org/ip"
TEST_TIMEOUT = 8
WORKERS = 20


def fetch_from_sources():
    """拉取所有代理源"""
    proxies = set()
    for url in SOURCES:
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if "geonode" in url:
                data = r.json().get("data", [])
                for item in data:
                    proto = item.get("protocols", ["http"])[0]
                    proxies.add(f"{proto}://{item['ip']}:{item['port']}")
            else:
                for line in r.text.strip().split("\n"):
                    line = line.strip()
                    if line and ":" in line:
                        proxies.add(line if "://" in line else f"http://{line}")
        except Exception:
            continue
    return list(proxies)


def test_proxy(proxy):
    """验证单个代理"""
    try:
        start = time.time()
        r = requests.get(TEST_URL, proxies={"http": proxy, "https": proxy},
                         timeout=TEST_TIMEOUT)
        latency = time.time() - start
        if r.status_code == 200:
            return (proxy, latency)
    except Exception:
        pass
    return None


def main():
    test_mode = "--test" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    # 拉取
    if verbose:
        print(f"[*] 拉取代理源...", file=sys.stderr)
    raw = fetch_from_sources()
    if verbose:
        print(f"[*] 拉取到 {len(raw)} 个代理", file=sys.stderr)

    if not raw:
        print("# 无代理可用，使用直连")
        return

    # 验证
    if verbose:
        print(f"[*] 验证中 (workers={WORKERS}, timeout={TEST_TIMEOUT}s)...", file=sys.stderr)

    good = []
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(test_proxy, p): p for p in raw}
        for f in as_completed(futures):
            result = f.result()
            if result:
                good.append(result)

    good.sort(key=lambda x: x[1])  # 按延迟排序

    if test_mode:
        print(f"\n{'─'*50}")
        print(f"可用代理: {len(good)}/{len(raw)}")
        print(f"{'─'*50}")
        for proxy, latency in good:
            print(f"  {proxy:40s} {latency:.1f}s")
        print(f"{'─'*50}")
        return

    # 输出 proxychains 格式
    for proxy, _ in good[:20]:  # 最多20个
        # 去掉协议前缀
        url = proxy.replace("http://", "").replace("https://", "")
        host, port = url.split(":")
        print(f"http {host} {port}")


if __name__ == "__main__":
    main()
