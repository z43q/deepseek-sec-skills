---
name: web-crawler
description: 网站爬虫、API数据采集、批量信息提取 — 基于 Scrapy/Playwright 的定向数据抓取。触发词：爬虫、采集、抓取、Scrapy、Playwright、API数据提取。
metadata:
  short-description: 定向采集爬虫工具集
---

# Web Crawler Skill

定向数据采集工具集，用于授权测试中的数据提取。

## 工具选择

| 工具 | 适用场景 |
|------|---------|
| Scrapy | 结构化数据/分页API |
| httpx | URL存活检测/指纹 |
| wget | 整站镜像/静态下载 |
| curl | 单次请求/手动验证 |
| katana | URL发现/JS解析 |
| Playwright | JavaScript 渲染/SPA/点击翻页 |

---

## 快速选择

```
目标是什么?
├── API返回JSON → Scrapy Spider
├── 发现隐藏URL → katana + httpx
├── 整站下载     → wget -r
├── 手动验证     → curl
└── 定制需求     → 模板改
```

---

## Scrapy 模板

### 通用分页API爬虫

```python
import scrapy

class ApiSpider(scrapy.Spider):
    name = "api_spider"
    
    def __init__(self, target=None, limit=50, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target or "http://localhost:8000/api/v1/items"
        self.limit = int(limit)
        self.start_urls = [f"{self.target}?page=1&limit={self.limit}"]
    
    def parse(self, response):
        data = response.json()
        items = data.get("items") or data.get("data") or data.get("results") or []
        for item in items:
            yield item
        
        if items:
            page = response.meta.get("page", 1) + 1
            url = f"{self.target}?page={page}&limit={self.limit}"
            yield scrapy.Request(url, meta={"page": page})
```

```bash
scrapy runspider spider.py -a target="https://target.com/api/v1/items" -o output.csv
```

---

## 代理池配置

### 代理轮换中间件

```python
class RotatingProxyMiddleware:
    def __init__(self, proxy_file="proxy_pool.txt"):
        with open(proxy_file) as f:
            self.proxies = [l.strip() for l in f if l.strip()]
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls()
    
    def process_request(self, request, spider):
        import random
        proxy = random.choice(self.proxies)
        request.meta['proxy'] = f"http://{proxy}"
```

---

## 数据存储

| 方案 | 适用 | 优点 | 缺点 |
|------|------|------|------|
| CSV | <10万条 | Excel可读 | 不支持嵌套 |
| JSONL | API数据 | 保结构 | 文件大 |
| SQLite | >10万条 | 可查询 | 需写SQL |

### JSONL（推荐API数据）

```python
import json

def save_jsonl(items, path):
    with open(path, 'w', encoding='utf-8') as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def load_jsonl(path):
    items = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            items.append(json.loads(line.strip()))
    return items
```

### SQLite（大数据）

```python
import sqlite3
conn = sqlite3.connect("crawled.db")
conn.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY,
        title TEXT, category TEXT, location TEXT,
        contact_info TEXT, created_at TEXT, raw_json TEXT
    )
""")

def save_items(items):
    for item in items:
        conn.execute("INSERT OR IGNORE INTO items VALUES (?,?,?,?,?,?,?)",
            (item.get("id"), item.get("title"), item.get("category"),
             item.get("location"), item.get("contact_info"),
             item.get("created_at"), json.dumps(item, ensure_ascii=False)))
    conn.commit()
```

---

## 礼貌爬取规则

```python
import time, random

def polite_delay(min_sec=0.3, max_sec=1.5):
    time.sleep(random.uniform(min_sec, max_sec))

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
]

def random_ua():
    return random.choice(UA_LIST)
```

---

## JavaScript 渲染

### Playwright 渲染引擎

```python
from playwright.sync_api import sync_playwright

def render_page(url, wait_sec=3):
    """渲染JS页面，返回HTML"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(wait_sec * 1000)
        html = page.content()
        browser.close()
        return html
```

### Scrapy + Playwright

```python
import scrapy
from scrapy_playwright.page import PageMethod

class JSSpider(scrapy.Spider):
    name = "js_spider"
    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        }
    }
    
    def start_requests(self):
        yield scrapy.Request(
            "https://example.com/spa",
            meta={"playwright": True}
        )
```

### 纯 Playwright 爬虫（无 Scrapy）

```python
from playwright.sync_api import sync_playwright
import json

def crawl_spa(url, max_items=100):
    items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        
        for _ in range(max_items):
            cards = page.query_selector_all(".item-card")
            for card in cards:
                items.append({
                    "title": card.query_selector(".title").inner_text(),
                    "link": card.query_selector("a").get_attribute("href"),
                })
            
            next_btn = page.query_selector(".next-page:not(.disabled)")
            if not next_btn:
                break
            next_btn.click()
            page.wait_for_timeout(2000)
        
        browser.close()
    return items
```

---

## 注意事项

```
1. 遵守 robots.txt — 先 curl /robots.txt
2. 单IP延迟 — 0.3~1.5秒/请求
3. 代理轮换 — 高并发用代理池
4. 断点续传 — 大任务记录last_page
5. 数据脱敏 — 爬到的用户隐私不落地
6. 免责声明 — 仅用于授权测试
```
