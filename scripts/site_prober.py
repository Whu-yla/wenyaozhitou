#!/usr/bin/env python3
"""
文鳐智投 站点探测器 v1.0
功能：批量HTTP探测站点可达性，识别公告列表页URL模式
输出：probe_results.json → 存活的站点 + 列表页候选URL
"""
import json, re, sqlite3, time, sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

DB_PATH = Path("/root/.hermes/profiles/wenyaozhitou/data/bidding.db")
OUTPUT = Path("/root/.hermes/profiles/wenyaozhitou/data/probe_results.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
TIMEOUT = 15

# 公告列表页的关键HTML模式
LISTING_PATTERNS = [
    r'href="[^"]*(?:招标公告|采购公告|中标公告|成交公告|jyxx|bulletin|trading|notice|announcement|zbgg|zbxx|cggg|zbgs)[^"]*"',
    r'href="[^"]*(?:/jyxx/|/trade/|/bulletin/|/notice/|/zbxx/|/zbgg/|/cggg/|/zbgs/)[^"]*"',
    r'<a[^>]*(?:招标公告|采购公告|中标公告|结果公告|成交公告)[^<]*</a>',
    r'href="[^"]*\?.*(?:type|category|class|menu|channel).*=.*(?:招标|采购|中标|成交|公告|jyxx|bulletin|trade)[^"]*"',
]

def try_site(site_id, site_name, url):
    """探测单个站点"""
    result = {
        "site_id": site_id,
        "site_name": site_name,
        "url": url,
        "status": "unknown",
        "http_code": None,
        "content_length": 0,
        "listing_urls": [],
        "error": None,
    }
    
    if not url or not url.startswith("http"):
        result["status"] = "invalid_url"
        return result
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, verify=False)
        result["http_code"] = resp.status_code
        result["final_url"] = resp.url
        
        if resp.status_code >= 400:
            result["status"] = f"http_{resp.status_code}"
            return result
        
        ct = resp.headers.get("content-type", "")
        if "text/html" not in ct and "text/plain" not in ct:
            result["status"] = f"not_html"
            result["content_type"] = ct
            return result
        
        html = resp.text
        result["content_length"] = len(html)
        
        if len(html) < 500:
            result["status"] = "too_small"
            return result
        
        # 尝试解析HTML找列表页链接
        soup = BeautifulSoup(html, 'html.parser')
        listing_candidates = set()
        
        # 找包含招标/采购/中标/公告文字的链接
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True).lower()
            href = a['href'].lower()
            combined = text + href
            
            if any(kw in combined for kw in ['招标公告', '采购公告', '中标公告', '成交公告',
                                                '结果公告', '招标', '采购', '中标', 'jyxx',
                                                'bulletin', 'trade', 'zbgg', 'zbxx', 'cggg',
                                                'trading', 'notice', 'announ']):
                full_url = urljoin(resp.url, a['href'])
                listing_candidates.add(full_url)
        
        # 对候选URL做适量截取
        result["listing_urls"] = list(listing_candidates)[:20]
        
        if listing_candidates:
            result["status"] = "listing_found"
        else:
            # 没有明显列表链接但页面足够大
            result["status"] = "no_listing_detected"
            
    except requests.exceptions.Timeout:
        result["status"] = "timeout"
    except requests.exceptions.ConnectionError as e:
        result["status"] = "connection_error"
        result["error"] = str(e)[:200]
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]
    
    return result


def main():
    import urllib3
    urllib3.disable_warnings()
    
    conn = sqlite3.connect(str(DB_PATH))
    sites = conn.execute("SELECT id, site_name, url FROM site_list ORDER BY id").fetchall()
    conn.close()
    
    print(f"开始探测 {len(sites)} 个站点...")
    
    results = []
    for i, (sid, name, urls_raw) in enumerate(sites):
        # 取第一个URL（可能有多行）
        url = urls_raw.split('\n')[0].strip() if urls_raw else ''
        
        print(f"[{i+1}/{len(sites)}] {name[:40]:40s} ", end='', flush=True)
        
        r = try_site(sid, name, url)
        print(f"→ {r['status']:20s} (code={r['http_code']}, len={r['content_length']}, listings={len(r['listing_urls'])})")
        results.append(r)
        
        # 每10个站点保存一次，防止丢失
        if (i+1) % 10 == 0:
            with open(OUTPUT, 'w') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 最终保存
    with open(OUTPUT, 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 统计
    status_counts = {}
    for r in results:
        s = r['status']
        status_counts[s] = status_counts.get(s, 0) + 1
    
    print(f"\n=== 探测完成: {len(results)} 站点 ===")
    for s, c in sorted(status_counts.items(), key=lambda x: -x[1]):
        pct = c / len(results) * 100
        print(f"  {s:30s} | {c:4d} | {pct:5.1f}%")
    
    listing_sites = [r for r in results if r['status'] == 'listing_found']
    print(f"\n=== 发现列表页的站点: {len(listing_sites)} 个 ===")
    for r in listing_sites:
        print(f"  [{r['site_id']}] {r['site_name'][:40]:40s} → {len(r['listing_urls'])} 候选链接")
        for lu in r['listing_urls'][:5]:
            print(f"      {lu[:120]}")


if __name__ == "__main__":
    main()
