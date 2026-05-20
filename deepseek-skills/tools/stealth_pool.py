#!/usr/bin/env python3
# ~/tools/stealth_pool.py
# 强化代理池 + 反追踪系统
# 用法: python3 stealth_pool.py [min_proxies]

import sys, json, time, random, hashlib
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

POOL_FILE = Path("/tmp/stealth_pool.json")
MIN_PROXIES = int(sys.argv[1]) if len(sys.argv) > 1 else 10

# ═══════════════════════════════════════
# 一、多源代理采集
# ═══════════════════════════════════════

SOURCES = [
    # HTTP/HTTPS 免费源
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=elite",
    "https://www.proxy-list.download/api/v1/get?type=https",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
    # 新增稳定源
    "https://openproxy.space/list/http",
    "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
]

def fetch_all():
    """从所有源采集代理"""
    raw = set()
    for url in SOURCES:
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": random_ua()})
            for line in resp.text.splitlines():
                line = line.strip()
                if line and ":" in line and not line.startswith("#"):
                    # 标准化格式
                    if not line.startswith("http"):
                        line = f"http://{line}"
                    raw.add(line)
        except Exception:
            continue
    return list(raw)

# ═══════════════════════════════════════
# 二、代理质量验证（多维度）
# ═══════════════════════════════════════

TEST_URLS = [
    ("http://httpbin.org/ip", 8),       # 基础连通
    ("https://httpbin.org/ip", 10),     # HTTPS能力
    ("http://httpbin.org/headers", 8),  # 头完整性
]

def validate_single(proxy):
    """单代理多维度验证，返回评分"""
    score = 0
    latency = 999
    ip = None
    
    for url, timeout in TEST_URLS:
        try:
            start = time.time()
            r = requests.get(url,
                proxies={"http": proxy, "https": proxy},
                timeout=timeout,
                headers={"User-Agent": random_ua()}
            )
            if r.status_code == 200:
                score += 1
                lt = time.time() - start
                if lt < latency:
                    latency = lt
                if "httpbin.org/ip" in url:
                    ip = r.json().get("origin", "")
        except Exception:
            continue
    
    # 匿名性检查：返回的IP应该不是我们自己的IP
    return {
        "proxy": proxy,
        "score": score,
        "latency": round(latency, 2),
        "exit_ip": ip,
        "anonymity": "elite" if score >= 2 else "transparent",
    }

def validate_pool(proxies, workers=30):
    """并发验证，按评分排序"""
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(validate_single, p): p for p in proxies[:200]}
        for f in as_completed(futures):
            try:
                r = f.result()
                if r["score"] >= 1:  # 至少通过1项测试
                    results.append(r)
            except Exception:
                continue
    
    # 按评分降序、延迟升序
    results.sort(key=lambda x: (-x["score"], x["latency"]))
    return results

# ═══════════════════════════════════════
# 三、智能代理管理器
# ═══════════════════════════════════════

class StealthManager:
    def __init__(self, min_proxies=MIN_PROXIES):
        self.min_proxies = min_proxies
        self.pool = self._load_or_refresh()
        self.used = {}       # proxy -> last_use_time
        self.failures = {}   # proxy -> fail_count
        self.cooldown = 30   # 失败后冷却秒数
    
    def _load_or_refresh(self):
        """加载缓存或重新采集"""
        if POOL_FILE.exists():
            try:
                data = json.loads(POOL_FILE.read_text())
                age = time.time() - data.get("ts", 0)
                if age < 3600:  # 1小时内有效
                    return data["proxies"]
            except Exception:
                pass
        
        print(f"[*] 刷新代理池 (目标≥{self.min_proxies}个)...")
        raw = fetch_all()
        validated = validate_pool(raw)
        
        proxies = [v for v in validated if v["score"] >= 1]
        print(f"[✓] 采集{len(raw)}→验证通过{len(proxies)}个")
        
        POOL_FILE.write_text(json.dumps({
            "ts": time.time(),
            "proxies": proxies
        }, ensure_ascii=False))
        return proxies
    
    def get_proxy(self):
        """获取最佳代理（避免重复和失败）"""
        now = time.time()
        candidates = []
        
        for p in self.pool:
            proxy = p["proxy"]
            # 跳过冷却中的
            if proxy in self.failures:
                if now - self.failures[proxy] < self.cooldown:
                    continue
                else:
                    del self.failures[proxy]
            # 优先未使用的
            candidates.append(p)
        
        if not candidates:
            print("[!] 代理耗尽，刷新池...")
            self.pool = self._load_or_refresh()
            candidates = self.pool
        
        # 选3个最高分，随机挑一个
        top = candidates[:min(3, len(candidates))]
        chosen = random.choice(top)
        self.used[chosen["proxy"]] = now
        return chosen["proxy"]
    
    def report_failure(self, proxy):
        """报告代理失败"""
        self.failures[proxy] = time.time()
    
    def stats(self):
        return {
            "total": len(self.pool),
            "available": len(self.pool) - len(self.failures),
            "avg_latency": round(sum(p["latency"] for p in self.pool) / max(len(self.pool), 1), 2)
        }

# ═══════════════════════════════════════
# 四、反追踪工具集
# ═══════════════════════════════════════

UA_LIST = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    # Safari Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    # Mobile
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.81 Mobile Safari/537.36",
]

ACCEPT_LANGUAGE_LIST = [
    "zh-CN,zh;q=0.9,en;q=0.8",
    "zh-CN,zh;q=0.9",
    "en-US,en;q=0.9,zh-CN;q=0.8",
]

REFERER_LIST = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://www.baidu.com/",
    None,  # 无Referer
]

def random_ua():
    return random.choice(UA_LIST)

def stealth_headers():
    """生成逼真的浏览器请求头"""
    return {
        "User-Agent": random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": random.choice(ACCEPT_LANGUAGE_LIST),
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": random.choice(['"Windows"', '"macOS"']),
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }

def human_delay():
    """模拟人类浏览节奏"""
    base = random.uniform(1.0, 3.0)
    # 偶尔长停顿（10%概率）
    if random.random() < 0.1:
        base += random.uniform(3.0, 8.0)
    time.sleep(base)

# ═══════════════════════════════════════
# 五、Playwright 反检测
# ═══════════════════════════════════════

PLAYWRIGHT_STEALTH_JS = """
// 隐藏 webdriver 标记
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
// 伪造 plugins
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
// 伪造 languages
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en']});
// 伪造 platform
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
// 伪造 hardwareConcurrency
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
// 移除 PhantomJS 痕迹
delete window.callPhantom;
"""

def playwright_stealth_launch():
    """启动带反检测的 Playwright 浏览器"""
    from playwright.sync_api import sync_playwright
    
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            f"--user-agent={random_ua()}",
        ]
    )
    context = browser.new_context(
        viewport={"width": random.randint(1280, 1920), "height": random.randint(720, 1080)},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        geolocation={"latitude": 39.9 + random.random(), "longitude": 116.4 + random.random()},
        permissions=["geolocation"],
    )
    page = context.new_page()
    page.add_init_script(PLAYWRIGHT_STEALTH_JS)
    
    return playwright, browser, context, page

# ═══════════════════════════════════════
# 六、请求策略
# ═══════════════════════════════════════

class AutoRetrySession:
    """自动重试 + 代理切换 + 退避"""
    
    def __init__(self, manager=None):
        self.manager = manager or StealthManager()
    
    def get(self, url, max_retries=3, **kwargs):
        for attempt in range(max_retries):
            proxy = self.manager.get_proxy()
            try:
                headers = stealth_headers()
                headers.update(kwargs.pop("headers", {}))
                
                resp = requests.get(
                    url,
                    proxies={"http": proxy, "https": proxy},
                    headers=headers,
                    timeout=15,
                    **kwargs
                )
                
                if resp.status_code == 200:
                    return resp
                elif resp.status_code in (429, 403):
                    # 被限/被封，切换代理
                    self.manager.report_failure(proxy)
                    human_delay()
                elif resp.status_code >= 500:
                    human_delay()
                else:
                    return resp
                    
            except Exception:
                self.manager.report_failure(proxy)
                time.sleep(2 ** attempt)  # 指数退避
        
        return None

# ═══════════════════════════════════════
# CLI
# ═══════════════════════════════════════

if __name__ == "__main__":
    mgr = StealthManager()
    stats = mgr.stats()
    print(f"\n[*] 代理池状态: {stats['total']}个, 可用{stats['available']}, 均延{stats['avg_latency']}s")
    
    # 输出代理列表
    for p in mgr.pool[:10]:
        print(f"  {p['proxy']:40s} | 评分{p['score']} | {p['latency']}s | {p['anonymity']}")
    
    # 保存到文件供其他工具使用
    with open("/tmp/stealth_pool.txt", "w") as f:
        for p in mgr.pool:
            f.write(p["proxy"] + "\n")
    print(f"\n[✓] 代理列表已保存 → /tmp/stealth_pool.txt")
