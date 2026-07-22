#!/usr/bin/env python3
"""
文鳐智投 全平台适配器补充包
新增: 深圳能源、国电投、中节能、国投电力、内蒙电力
+ Chromium批量渲染: 浙能/中广核/中核/大唐/国网
+ 竞品追踪增强
"""
import re, sys, sqlite3, hashlib, subprocess
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

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0"}
TIMEOUT = 20
CHROMIUM = "/snap/bin/chromium"
CHROMIUM_ARGS = "--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage --virtual-time-budget=30000 --dump-dom"

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
        return r.text if r.status_code==200 and len(r.text)>300 else None
    except: return None

def chromium(url, timeout=35):
    try:
        r = subprocess.run([CHROMIUM]+CHROMIUM_ARGS.split()+[url],
                          capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode==0 and len(r.stdout)>500 else None
    except: return None

def extract_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    for t in soup(['script','style','nav','footer','header']): t.decompose()
    return re.sub(r'\s+',' ',soup.get_text()).strip()

# ═══════════ 深圳能源 ═══════════
def _parse_shenneng_detail(html, url):
    """从深圳能源详情页提取正文（跳过导航/页眉/页脚）"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # 优先取 .Content 主内容区（避免门户导航污染）
    content_div = soup.find('div', class_='Content')
    if not content_div:
        content_div = soup
    
    raw = content_div.get_text(separator=' ', strip=True)
    if len(raw) < 80:
        return None
    
    # 日期提取
    date = ''
    dm = re.search(r'发布时间[：:]\s*(\d{4}-\d{1,2}-\d{1,2})', html)
    if dm:
        date = dm.group(1)
    else:
        dm = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', raw[:500])
        if dm:
            date = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
    
    # 招标人提取 — 遇到"招标代理/代理机构/地址/联系人"就截断
    owner = ''
    om = re.search(r'(?:招标人|采购人)(?:名称)?[：:]\s*([^。；;，,\n]{3,60}?)(?:\s+(?:招标代理|代理机构|地址|联系人|电话|日期))', raw)
    if not om:
        om = re.search(r'(?:招标人|采购人)(?:名称)?[：:]\s*([^。；;，,\n]{3,60}?)(?:\s+(?:招标代理|代理机构|地址|联系人|电话|日期))', html)
    if not om:
        om = re.search(r'(?:招标人|采购人)[：:]\s*([^。；;，,\n]{3,60})', raw)
    if om:
        owner = om.group(1).strip()[:60]
    
    # 中标人提取
    winner = ''
    wm = re.search(r'中标人[：:]\s*([^。；;，,\n]{3,50})', raw)
    if wm:
        winner = wm.group(1).strip()[:60]
    
    # 金额提取
    amount = ''
    am = re.search(r'(?:中标金额|成交金额)[：:]\s*([^。；;，,\n]{2,40})', raw)
    if am:
        amount = am.group(1).strip()[:40]
    
    return {
        'content': raw[:1000],
        'raw_text': raw,
        'publish_date': date,
        'procurement_owner': owner,
        'winner_company': winner,
        'winning_amount': amount,
    }


def crawl_shenneng(max_items=20):
    """深圳能源电子招标投标平台 zb.sec.com.cn"""
    base = "https://zb.sec.com.cn"
    items = []
    seen = set()
    
    for cat, name in [('/zbggs/index.jhtml','招标公告'),('/jggg/index.jhtml','结果公告')]:
        html = fetch(base + cat)
        if not html: continue
        
        ntype = 'winning' if 'jggg' in cat else 'bidding'
        
        for m in re.finditer(r'href\s*=\s*["\'](/(?:zbgg|jggg)/\d+\.jhtml)["\x27][^>]*>\s*(.+?)\s*</a>', html):
            rel_url, title = m.groups()
            full_url = urljoin(base, rel_url)
            if full_url in seen: continue
            seen.add(full_url)
            
            detail = fetch(full_url)
            if not detail: continue
            
            parsed = _parse_shenneng_detail(detail, full_url)
            if not parsed: continue
            
            items.append({
                'title': title.strip()[:200],
                'content': parsed['content'],
                'source': '深圳能源电子招标平台',
                'source_url': full_url,
                'notice_type': ntype,
                'publish_date': parsed['publish_date'],
                'procurement_owner': parsed['procurement_owner'],
                'winner_company': parsed['winner_company'],
                'winning_amount': parsed['winning_amount'],
                'raw_text': parsed['raw_text'],
            })
            if len(items) >= max_items: return items
    return items

# ═══════════ Chromium批量渲染 ═══════════
JS_PLATFORMS = {
    '国电投': 'https://ebid.espic.com.cn/sdny_bulletin/',
    '中节能': 'https://www.ebidding.cecep.cn/jyxx/001006/001006001/',
    '国投电力': 'https://www.sdicc.com.cn/',
    '浙能集团': 'https://zsrm.zjenergy.com.cn/zjnycms/category/bulletinListNew.html?dates=300&categoryId=2&tenderMethod=01&page=1',
    '中广核': 'https://ecp.cgnpc.com.cn/',
    '中核集团': 'https://www.cnncecp.com/',
    '大唐集团': 'https://www.cdt-ec.com/home/',
    '内蒙古电力': 'http://impc.e-bidding.org/nmcms/category/bulletinList.html?dates=300&categoryId=88&page=1',
}

def crawl_all_js():
    """Chromium批量渲染所有JS平台"""
    all_items = []
    for name, url in JS_PLATFORMS.items():
        print(f"  Chromium {name}...")
        html = chromium(url)
        if not html:
            print(f"    ❌ 渲染失败")
            continue
        
        print(f"    ✅ {len(html)}B")
        
        # 智能链接提取
        detail_urls = set()
        for m in re.finditer(r'href\s*=\s*["\x27]([^"\x27]*(?:detail|bulletin|notice|zb|bid|tender|view|info|公告|招标|中标|详情|公示)[^"\x27]*)["\x27]', html, re.I):
            full = urljoin(url, m.group(1))
            if len(full)<500 and full.startswith('http') and 'javascript' not in full:
                detail_urls.add(full)
        
        # 也尝试数据链接模式
        for pat in [r'data-(?:url|href|link)\s*=\s*["\x27]([^"\x27]+)["\x27]',
                     r'(?:location\.href|window\.open)\s*=\s*["\x27]([^"\x27]+)["\x27]',
                     r'(?:showDetail|openDetail|viewDetail)\s*\(["\x27]([^"\x27]+)["\x27]']:
            for m in re.finditer(pat, html):
                full = urljoin(url, m.group(1))
                if len(full)<500 and full.startswith('http'):
                    detail_urls.add(full)
        
        print(f"    发现{len(detail_urls)}个详情链接")
        
        site_items = 0
        for du in list(detail_urls)[:15]:
            detail_html = fetch(du) or chromium(du)
            if not detail_html or len(detail_html) < 300: continue
            
            text = extract_text(detail_html)
            if len(text) < 50: continue
            
            all_items.append({
                'title': text[:100],
                'content': text[:800],
                'source': name,
                'source_url': du,
                'notice_type': 'bidding',
                'publish_date': '',
                'procurement_owner': '',
                'raw_text': text,
            })
            site_items += 1
        
        print(f"    采集{site_items}条")
    
    return all_items

# ═══════════ 入库 ═══════════
def save(items, conn):
    scored = score_items(items)
    n = 0
    for s in scored:
        h = hashlib.md5((s.get('source_url','') or '').encode()).hexdigest()
        try:
            if s.get('notice_type') == 'winning':
                conn.execute("""INSERT OR IGNORE INTO winning_notices
                    (title,url,source_site,project_name,winner_company,winning_amount,
                     publish_date,fetch_date,content_summary,is_new,unique_hash,
                     relevance_score,procurement_owner,region,province,category)
                    VALUES(?,?,?,?,?,?,?,?,?,1,?,?,?,?,?,?)""",
                    ((s.get('title','') or '')[:200], (s.get('source_url','') or '')[:500],
                     (s.get('source','') or '')[:200], (s.get('title','') or '')[:200],
                     s.get('winner_company','') or '', s.get('winning_amount','') or '',
                     s.get('publish_date',''), datetime.now().isoformat(),
                     (s.get('content','') or '')[:2000], h, s.get('relevance_score',0),
                     s.get('procurement_owner','')[:200], '','',''))
            else:
                conn.execute("""INSERT OR IGNORE INTO bidding_notices
                    (title,url,source_site,notice_type,publish_date,fetch_date,
                     content_summary,is_new,unique_hash,relevance_score,
                     procurement_owner,region,province,category)
                    VALUES(?,?,?,?,?,?,?,1,?,?,?,?,?,?)""",
                    ((s.get('title','') or '')[:200], (s.get('source_url','') or '')[:500],
                     (s.get('source','') or '')[:200], 'bidding', s.get('publish_date',''),
                     datetime.now().isoformat(), (s.get('content','') or '')[:2000],
                     h, s.get('relevance_score',0), s.get('procurement_owner','')[:200],
                     '','',''))
            n += 1
        except: pass
    conn.commit()
    return n

def main():
    print(f"[{datetime.now():%H:%M:%S}] 补充适配器启动\n")
    conn = sqlite3.connect(str(BASE_DIR/'data'/'bidding.db'))
    
    # 深圳能源（requests直取）
    print("── 深圳能源 ──")
    sn = crawl_shenneng()
    print(f"  抓取{len(sn)}条 → 入库{save(sn, conn)}条")
    
    # Chromium批量
    print("\n── Chromium批量渲染 ──")
    js = crawl_all_js()
    print(f"\n  总抓取{len(js)}条 → 入库{save(js, conn)}条")
    
    b = conn.execute("SELECT count(*) FROM bidding_notices").fetchone()[0]
    w = conn.execute("SELECT count(*) FROM winning_notices").fetchone()[0]
    print(f"\n库内: 招标{b}+中标{w}={b+w}")
    conn.close()

if __name__ == '__main__':
    main()
