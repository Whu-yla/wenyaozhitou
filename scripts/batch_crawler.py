#!/usr/bin/env python3
"""
文鳐智投 批量爬虫 v1.0
从probe结果加载所有 listing_found 站点，逐个爬取详情 → 评分 → 入库
"""
import sys, json, re, sqlite3, time, hashlib
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE_DIR = Path("/root/.hermes/profiles/wenyaozhitou")
sys.path.insert(0, str(BASE_DIR / "scripts"))
import urllib3
urllib3.disable_warnings()

from relevance_scorer import score_items

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
TIMEOUT = 15

def extract_bid_detail_links(html, base_url):
    """从列表页提取公告详情链接"""
    links = set()
    soup = BeautifulSoup(html, 'html.parser')
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        combined = (href + text).lower()
        
        # 招标/中标/成交 相关链接
        bid_signals = ['zbgg', 'zbxx', 'cggg', 'jyxx', 'bulletin', 'notice',
                       'tender', 'bid', 'announcement', 'detail',
                       'zbgs', 'cjgg', 'zbcg', '中标', '招标', '成交']
        
        is_bid = any(s in combined for s in bid_signals)
        
        # 排除列表页、首页、登录页
        exclude = ['login', 'register', 'index', 'search', 'javascript', 'more', 
                   'category', 'bulletinlist', 'listpage', 'purchaselist',
                   '首页', '登录']
        is_excluded = any(s in combined for s in exclude)
        
        # 额外：排除带大量参数的URL(大概率是列表页/分类页)
        if '?' in href and ('category' in href.lower() or 'list' in href.lower()):
            is_excluded = True
        
        if is_bid and not is_excluded:
            full_url = urljoin(base_url, href)
            if full_url.startswith('http') and len(full_url) < 500:
                links.add(full_url)
    
    return list(links)[:30]

def fetch_and_extract_text(url):
    """获取页面纯文本"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, verify=False)
        if resp.status_code >= 400:
            return None, None
        ct = resp.headers.get('content-type', '')
        if 'text/html' not in ct:
            return None, None
        html = resp.text
        if len(html) < 500:
            return None, None
        soup = BeautifulSoup(html, 'html.parser')
        # 移除脚本和样式
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        text = soup.get_text()
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:3000], html[:20000]
    except:
        return None, None

def detect_notice_type(title, text=''):
    """从标题/正文检测招标/中标类型"""
    combined = (title + ' ' + (text or '')[:500])
    winning_patterns = [
        '中标', '成交', '中标候选人', '中标公告', '中标结果', '成交公告',
        '成交结果', '中标公示', '成交公示', '中标通知', '中标人',
        '结果公告', '评标结果', '采购结果', '预中标', '候选中标',
        '招标结果', '中标单位', '中标供应商', '项目结果',
    ]
    for p in winning_patterns:
        if p in combined:
            return 'winning'
    return 'bidding'


def main():
    # 加载probe结果
    with open(BASE_DIR / 'data' / 'probe_results.json') as f:
        probe_data = json.load(f)
    
    listing_sites = [r for r in probe_data if r['status'] == 'listing_found']
    print(f"加载 {len(listing_sites)} 个 listing_found 站点")
    
    conn = sqlite3.connect(str(BASE_DIR / 'data' / 'bidding.db'))
    all_notices = []
    total_links = 0
    
    for i, site in enumerate(listing_sites):
        name = site['site_name'][:40]
        listing_urls = site.get('listing_urls', [])[:5]  # 每个站最多5个列表页
        
        if not listing_urls:
            continue
        
        site_notices = 0
        for lu in listing_urls[:3]:  # 每个列表页最多抓3个
            try:
                resp = requests.get(lu, headers=HEADERS, timeout=TIMEOUT, verify=False)
                if resp.status_code >= 400 or len(resp.text) < 300:
                    continue
                
                detail_links = extract_bid_detail_links(resp.text, lu)
                total_links += len(detail_links)
                
                for dl in detail_links[:5]:  # 每个列表页最多5条详情
                    text, html = fetch_and_extract_text(dl)
                    if not text or len(text) < 50:
                        continue
                    
                    # 构建item
                    title = text.split('\n')[0][:100] if '\n' in text else text[:100]
                    notice_type = detect_notice_type(title, text)
                    item = {
                        'title': title,
                        'content': text[:500],
                        'source': name,
                        'source_url': dl,
                        'notice_type': notice_type,
                        'publish_date': '',
                        'procurement_owner': '',
                        'raw_text': text,
                        'raw_html': html,
                    }
                    all_notices.append(item)
                    site_notices += 1
                    
            except Exception:
                continue
        
        if site_notices > 0:
            print(f"  [{i+1}/{len(listing_sites)}] {name:40s} → {site_notices} 条")
        
        # 每10个站点评一次分
        if len(all_notices) >= 50 or (i > 0 and i % 10 == 0 and all_notices):
            _score_and_insert(conn, all_notices)
            all_notices = []
    
    # 最后一批
    if all_notices:
        _score_and_insert(conn, all_notices)
    
    # 统计
    bidding = conn.execute("SELECT count(*) FROM bidding_notices").fetchone()[0]
    winning = conn.execute("SELECT count(*) FROM winning_notices").fetchone()[0]
    print(f"\n{'='*60}")
    print(f"  库内总计: 招标 {bidding} + 中标 {winning} = {bidding + winning}")
    conn.close()

def _score_and_insert(conn, items):
    scored = score_items(items)
    bid_count = 0
    win_count = 0
    for s in scored:
        h = hashlib.md5((s.get('source_url','') or '').encode()).hexdigest()
        notice_type = s.get('notice_type', 'bidding')
        try:
            if notice_type == 'winning':
                conn.execute("""
                    INSERT OR IGNORE INTO winning_notices
                    (title, url, source_site, project_name, winner_company, winning_amount,
                     publish_date, fetch_date, content_summary, is_new, unique_hash,
                     relevance_score, procurement_owner, region, province, category)
                    VALUES (?,?,?,?,?,?,?,?,?,1,?,?,?,?,?,?)
                """, (
                    (s.get('title','') or '')[:200],
                    (s.get('source_url','') or '')[:500],
                    (s.get('source','') or '')[:200],
                    s.get('project_name','') or s.get('title','')[:100],
                    s.get('winner_company','') or '',
                    s.get('winning_amount','') or '',
                    s.get('publish_date',''),
                    datetime.now().isoformat(),
                    (s.get('content','') or s.get('raw_text',''))[:2000],
                    h,
                    s.get('relevance_score', 0),
                    s.get('procurement_owner','')[:200],
                    s.get('region',''),
                    s.get('province',''),
                    s.get('category',''),
                ))
                win_count += 1
            else:
                conn.execute("""
                    INSERT OR IGNORE INTO bidding_notices
                    (title, url, source_site, notice_type, publish_date, fetch_date,
                     content_summary, is_new, unique_hash, relevance_score,
                     procurement_owner, region, province, category)
                    VALUES (?,?,?,?,?,?,?,1,?,?,?,?,?,?)
                """, (
                    (s.get('title','') or '')[:200],
                    (s.get('source_url','') or '')[:500],
                    (s.get('source','') or '')[:200],
                    'bidding',
                    s.get('publish_date',''),
                    datetime.now().isoformat(),
                    (s.get('content','') or s.get('raw_text',''))[:2000],
                    h,
                    s.get('relevance_score', 0),
                    s.get('procurement_owner','')[:200],
                    s.get('region',''),
                    s.get('province',''),
                    s.get('category',''),
                ))
                bid_count += 1
        except:
            pass
    conn.commit()
    if bid_count or win_count:
        print(f"    → 评分入库 {win_count}中标 + {bid_count}招标 = {win_count+bid_count} 条")

if __name__ == '__main__':
    main()
