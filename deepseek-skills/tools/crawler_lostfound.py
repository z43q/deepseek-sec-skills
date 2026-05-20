#!/usr/bin/env python3
# ~/tools/crawler_lostfound.py
# 高校失物招领系统爬虫
# 用法: python3 crawler_lostfound.py [API_BASE_URL]

import sys, json, time, csv
import requests
from datetime import datetime

API = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.179.70:8000"
ITEMS_URL = f"{API}/api/v1/items"
OUTPUT = f"lostfound_items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

def crawl_items(limit=50, max_pages=None):
    """分页爬取所有物品，返回去重列表"""
    items = []
    seen_ids = set()
    page = 1
    
    while True:
        url = f"{ITEMS_URL}?page={page}&limit={limit}"
        resp = requests.get(url, timeout=10)
        
        if resp.status_code != 200:
            print(f"[!] page={page} HTTP {resp.status_code}，停止")
            break
        
        data = resp.json()
        batch = data.get("items", [])
        total = data.get("total", 0)
        
        if not batch:
            print(f"[✓] page={page} 空页，停止。共获取 {len(items)} 条")
            break
        
        new = 0
        for item in batch:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                items.append(item)
                new += 1
        
        print(f"[{datetime.now():%H:%M:%S}] page={page}: {len(batch)}条, 新增{new}, 累计{len(items)}/{total}")
        
        if max_pages and page >= max_pages:
            break
        page += 1
        time.sleep(0.3)  # 礼貌延迟
    
    return items

def save_csv(items, path):
    """保存为CSV"""
    if not items:
        print("[!] 无数据可保存")
        return
    
    fields = ["id", "item_type", "category", "title", "description", 
              "location", "contact_info", "status", "created_at", "publisher_id"]
    
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(items)
    
    print(f"[✓] 已保存 {len(items)} 条 → {path}")

if __name__ == "__main__":
    print(f"[*] 目标: {API}")
    print(f"[*] 爬取中...")
    items = crawl_items(limit=50)
    save_csv(items, OUTPUT)
