#!/usr/bin/env python3
"""
文鳐智投 六大六小专属适配器 v3.0
南网/国网/浙能/能建/国电投/三峡/中广核/中节能/华润/深圳能源/内蒙古电力
每个平台独立适配器，精准提取招标/中标公告
"""
import re, sys, sqlite3, hashlib, json, subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse
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
TIMEOUT = 20
CHROMIUM = "/snap/bin/chromium"
CHROMIUM_ARGS = "--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage --virtual-time-budget=25000 --dump-dom"

def chromium_render(url):
    try:
        r = subprocess.run([CHROMIUM] + CHROMIUM_ARGS.split() + [url],
                          capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout and len(r.stdout) > 500:
            return r.stdout
    except: pass
    return None

def fetch(url, timeout=TIMEOUT):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True, verify=False)
        r.encoding = r.apparent_encoding or 'utf-8'
        return r.text if r.status_code == 200 and len(r.text) > 300 else None
    except: return None

def extract_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()
    return re.sub(r'\s+', ' ', soup.get_text()).strip()

# ═══════════════════════════════════════════
# 南方电网供应链统一服务平台
# ═══════════════════════════════════════════
def crawl_nanwang(max_items=30):
    """南方电网 - bidding.csg.cn + ecsg.com.cn"""
    base = "http://www.bidding.csg.cn"
    categories = {
        'zbgg':    (f'{base}/zbgg/index.jhtml',    '招标公告'),
        'fzbgg':   (f'{base}/fzbgg/index.jhtml',   '非招标公告'),
        'zbhxrgs': (f'{base}/zbhxrgs/index.jhtml', '公示公告'),
        'zbcg':    (f'{base}/zbcg/index.jhtml',    '采购公告'),
        'lxcggg':  (f'{base}/lxcggg/index.jhtml',  '零星采购公告'),
    }
    
    items = []
    seen = set()
    
    for cat_key, (list_url, cat_name) in categories.items():
        html = fetch(list_url)
        if not html:
            continue
        
        # 提取详情链接: <a href="/zbgg/1200433817.jhtml">标题</a>
        for m in re.finditer(r'href\s*=\s*["\'](/' + cat_key + r'/\d+\.jhtml)["\'][^>]*>\s*(.+?)\s*</a>', html):
            rel_url, title = m.groups()
            full_url = urljoin(base, rel_url.strip())
            if full_url in seen:
                continue
            seen.add(full_url)
            
            detail_html = fetch(full_url)
            if not detail_html:
                continue
            
            text = extract_text(detail_html)
            if len(text) < 100:
                continue
            
            # 从详情页提取完整标题（列表页链接文本可能被截断）
            full_title = title.strip()
            full_title = re.sub(r'<[^>]+>', '', full_title)
            
            # 方式1: 从详情页文本中提取"您现在正在浏览：... > 完整标题"
            pos = text.find('您现在正在浏览')
            if pos >= 0:
                rest = text[pos:pos+500]
                m = re.search(r'(?:您现在正在浏览[：:][^>]*>)\s*(.+?)(?:\s*来源|\s*发布时间|\s*$)', rest)
                if m:
                    candidate = m.group(1).strip()
                    if len(candidate) > len(full_title) and len(candidate) < 200:
                        full_title = candidate
            
            # 方式2: 从<title>标签提取
            if len(full_title) < 55:
                tm = re.search(r'<title>([^<]+)</title>', detail_html)
                if tm:
                    t = tm.group(1).strip()
                    t = re.sub(r'.*?[-–—|]\s*', '', t)  # 去掉"非招标公告-中国南方电网-"前缀
                    if len(t) > len(full_title):
                        full_title = t
            
            # 方式3: 从详情页开头提取（南网公告标题在前200字符内）
            if len(full_title) < 55:
                first_lines = text[:400]
                for line in first_lines.split('\n'):
                    line = line.strip()
                    if 20 < len(line) < 200 and any(kw in line for kw in ['招标','中标','采购','公示','公告','项目']):
                        full_title = line
                        break
            
            # 用完整标题重新判断类型
            if any(kw in full_title for kw in ['中标候选人', '中标结果', '中标公示', '成交结果', '成交公示', '中标公告', '成交公告']):
                notice_type = 'winning'
            elif any(kw in full_title for kw in ['中标', '成交', '中选', '定标']):
                notice_type = 'winning'
            else:
                notice_type = 'bidding' if '招标' in cat_name else 'procurement'
            
            # 提取采购人
            owner = ''
            for pat in [r'采购人[：:]\s*(.+?)(?:\s|&nbsp;)*\n', r'招标人[：:]\s*(.+?)(?:\s|&nbsp;)*\n']:
                m2 = re.search(pat, text)
                if m2:
                    owner = m2.group(1).strip()[:60]
                    break
            
            # 提取日期
            date = ''
            m3 = re.search(r'发布时间[：:]\s*(\d{4}-\d{2}-\d{2})', text)
            if m3:
                date = m3.group(1)
            
            # 提取金额（招标用预算、中标用中标金额）
            amount = ''
            # 优先从 HTML 表格提取（已在上面 winning 分支中处理）
            if notice_type == 'bidding':
                m4 = re.search(r'(?:预计采购金额|估算金额)[（(].+?[)）]?\s*[：:]?\s*(\d+(?:\.\d+)?)\s*万', text)
                if m4:
                    amount = m4.group(1) + '万元'
            # 兜底：纯文本金额
            if not amount:
                for pat in [r'(?:中标金额|成交金额|金额)[：:]\s*([\d,.]+)\s*(?:万|元)',
                           r'投标报价[：:]\s*([\d,.]+)\s*(?:万|元)']:
                    m5 = re.search(pat, text)
                    if m5:
                        amt_val = m5.group(1).replace(',', '')
                        if '万' in m5.group(0):
                            amount = amt_val + '万元'
                        else:
                            amount = amt_val + '元'
                        break
            
            # 中标项目提取中标人和金额（优先从HTML表格提取）
            winner = ''
            if notice_type == 'winning':
                # ── 方式1: HTML表格提取（南网等表格型页面）──
                soup = BeautifulSoup(detail_html, 'html.parser')
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    # 找表头行定位列索引
                    col_winner = -1
                    col_amount = -1
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        for i, cell in enumerate(cells):
                            ct = cell.get_text(strip=True)
                            if '中标人' in ct or '成交供应商' in ct or '中标单位' in ct or '供应商名称' in ct or '成交人' in ct:
                                col_winner = i
                            if '中标金额' in ct or '成交金额' in ct or '投标报价' in ct or '报价' in ct:
                                col_amount = i
                        if col_winner >= 0 or col_amount >= 0:
                            break
                    # 如果找到中标人列，从数据行提取
                    if col_winner >= 0:
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) > col_winner:
                                val = cells[col_winner].get_text(strip=True)
                                # 跳过表头行本身
                                if val and '中标人' not in val and '序号' not in val and len(val) >= 2:
                                    winner = val[:80]
                                    break
                    # 如果有金额列
                    if col_amount >= 0:
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) > col_amount:
                                val = cells[col_amount].get_text(strip=True)
                                if val and '金额' not in val and '报价' not in val and re.search(r'\d', val):
                                    # 清理金额文本
                                    amt_clean = re.sub(r'[,\s]', '', val)
                                    m = re.search(r'([\d.]+)', amt_clean)
                                    if m:
                                        amount = m.group(1)
                                        if '万' in val:
                                            amount += '万元'
                                        elif '亿' in val:
                                            amount += '亿元'
                                        else:
                                            amount += '元'
                                    break
                
                # ── 方式2: 纯文本兜底（旧逻辑）──
                if not winner:
                    for pat in [r'(?:中标人|成交供应商|中标单位|供应商名称)[：:]\\s*(.+?)(?:\\s|&nbsp;)*\\n',
                               r'第\\s*一\\s*(?:中标|成交|中选)\\s*(?:候选人|供应商|人)[：:]\\s*(.+?)(?:\\s|&nbsp;)*\\n']:
                        wm = re.search(pat, text)
                        if wm:
                            winner = wm.group(1).strip()[:60]
                            break
            
            items.append({
                'title': full_title[:200],
                'content': text[:1000],
                'source': '南方电网供应链统一平台',
                'source_url': full_url,
                'notice_type': notice_type,
                'publish_date': date,
                'procurement_owner': owner,
                'winner_company': winner,
                'winning_amount': amount,
                'raw_text': text,
            })
            
            if len(items) >= max_items:
                return items
    
    return items


# ═══════════════════════════════════════════
# 国家电投(电能易购) ebid.espic.com.cn
# ═══════════════════════════════════════════
def crawl_guodianta(max_items=20):
    """国家电投 — 同浙能电能e招采系统，iframe列表+详情"""
    base = "https://ebid.espic.com.cn"
    items = []
    seen = set()
    
    # 同浙能：列表在 iframe 中
    # 分类: 2=招标公告, 3=变更, 4=中标结果, 5=中标候选人
    categories = [
        (2, '招标公告', 'bidding'),
        (4, '中标结果', 'winning'),
        (5, '中标候选人', 'winning'),
    ]
    
    for cat_id, cat_name, notice_type in categories:
        for page in range(1, 4):  # 每类取3页
            iframe_url = (
                f"{base}/newgdtcms//category/bulletinListNew.html"
                f"?dates=300&categoryId={cat_id}&tenderMethod=01"
                f"&tabName={cat_name}&page={page}"
            )
            
            try:
                r = requests.get(iframe_url, headers=HEADERS, timeout=TIMEOUT, verify=False)
                r.encoding = r.apparent_encoding or 'utf-8'
                html = r.text
            except Exception as e:
                print(f"  [国电投] iframe异常: {e}")
                continue
            
            if not html or len(html) < 500:
                break
            
            # 提取详情链接: /sdny_bulletin/YYYY-MM-DD/ID.html
            detail_urls = re.findall(
                r'(/sdny_\w+/\d{4}-\d{2}-\d{2}/\d+\.html)',
                html
            )
            
            if not detail_urls:
                break
            
            for rel_url in detail_urls:
                full_url = urljoin(base, rel_url)
                if full_url in seen:
                    continue
                seen.add(full_url)
                
                # 详情页 — 优先用 requests，失败则 Chromium
                text = ''
                detail_html = fetch(full_url)
                if detail_html:
                    text = extract_text(detail_html)
                
                # requests 失败则用 Chromium
                if not text or len(text) < 100:
                    detail_html = chromium_render(full_url)
                    if detail_html:
                        text = extract_text(detail_html)
                
                if not text or len(text) < 100:
                    continue
                
                # 标题提取
                title = ''
                m = re.search(
                    r'((?:国家电投|国电投|中电投|电投)\\S{0,80}'
                    r'(?:招标公告|采购公告|中标候选人公示|中标结果公告|成交公告))',
                    text
                )
                if m:
                    title = m.group(1).strip()[:200]
                if not title:
                    m = re.search(
                        r'(?:招标公告|采购公告|中标候选人公示|中标结果公告|成交公告)'
                        r'\\s*(.{10,120}?)(?:\\s{2,}|\\n\\n|已具备招标条件)',
                        text
                    )
                    if m:
                        title = f'{m.group(0)}{m.group(1)}'.strip()[:200]
                if not title:
                    title = text[:120].strip()
                
                # 日期
                date = ''
                d = re.search(r'(\\d{4}[年/-]\\d{1,2}[月/-]\\d{1,2})', text[:500])
                if d:
                    date = re.sub(r'[年月]', '-', d.group(1)).replace('/', '-').replace('日', '')
                
                # 招标人
                owner = ''
                om = re.search(r'招标人[：:]\\s*(.+?)(?:\\s*联系|\\s*\\n|$)', text)
                if om:
                    owner = om.group(1).strip()[:80]
                
                items.append({
                    'title': title[:200],
                    'content': text[:1000],
                    'source': '国家电投电子商务平台',
                    'source_url': full_url,
                    'notice_type': notice_type,
                    'publish_date': date,
                    'procurement_owner': owner,
                    'raw_text': text,
                })
                
                if len(items) >= max_items:
                    break
            
            if len(items) >= max_items:
                break
        
        if len(items) >= max_items:
            break
    
    print(f"  [国电投] ✅ 提取 {len(items)} 条公告")
    return items


# ═══════════════════════════════════════════
# 中国能建电子采购平台 ec.ceec.net.cn
# ═══════════════════════════════════════════
def crawl_nengjian(max_items=20):
    """中国能建 - GBK编码"""
    base = "https://ec.ceec.net.cn"
    items = []
    
    for page_type, name in [('ZhaoBiaoGG_More.aspx', '招标公告'), ('winDid_More.aspx', '中标公示')]:
        url = f"{base}/HomeInfo/{page_type}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
            r.encoding = 'gbk'
            html = r.text
        except:
            continue
        
        if len(html) < 500:
            continue
        
        # 提取详情链接
        for m in re.finditer(r'href\s*=\s*["\'](HomeInfo/[^"\']*(?:Detail|detail)[^"\']*)["\']', html):
            rel_url = m.group(1)
            full_url = urljoin(base, rel_url)
            
            try:
                r2 = requests.get(full_url, headers=HEADERS, timeout=TIMEOUT, verify=False)
                r2.encoding = 'gbk'
                detail_html = r2.text
            except:
                continue
            
            text = extract_text(detail_html)
            if len(text) < 100:
                continue
            
            title = text[:120]
            date = ''
            d = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', text[:500])
            if d: date = d.group(1)
            
            items.append({
                'title': title,
                'content': text[:800],
                'source': '中国能建电子采购平台',
                'source_url': full_url,
                'notice_type': 'bidding',
                'publish_date': date,
                'procurement_owner': '',
                'raw_text': text,
            })
            if len(items) >= max_items:
                break
    
    return items


# ═══════════════════════════════════════════
# 华润守正 (已有，复用)
# ═══════════════════════════════════════════
from site_crawlers import crawl_huarun_szecp


# ═══════════════════════════════════════════
# 三峡集团电子采购平台 eps.ctg.com.cn
# ═══════════════════════════════════════════
def crawl_sanxia(max_items=15):
    """三峡集团"""
    base = "https://eps.ctg.com.cn"
    items = []
    
    html = fetch(base + "/")
    if not html:
        return items
    
    for m in re.finditer(r'href\s*=\s*["\']([^"\']*(?:bulletin|notice|zb|bid|tender|招标|公告|采购)[^"\']*)["\']', html, re.I):
        rel_url = m.group(1)
        full_url = urljoin(base, rel_url)
        
        detail_html = fetch(full_url)
        if not detail_html or len(detail_html) < 500:
            continue
        
        text = extract_text(detail_html)
        if len(text) < 100:
            continue
        
        items.append({
            'title': text[:100],
            'content': text[:800],
            'source': '三峡集团电子采购平台',
            'source_url': full_url,
            'notice_type': 'bidding',
            'publish_date': '',
            'procurement_owner': '',
            'raw_text': text,
        })
        if len(items) >= max_items:
            break
    
    return items


# ═══════════════════════════════════════════
# 中广核 + 浙能 (JS渲染)
# ═══════════════════════════════════════════
def crawl_js_platforms():
    """用Chromium渲染JS平台"""
    targets = {
        '浙能集团': 'https://zsrm.zjenergy.com.cn/zjnycms/category/bulletinListNew.html?dates=300&categoryId=2&tenderMethod=01&page=1',
        '中广核': 'https://ecp.cgnpc.com.cn/',
        '中核集团': 'https://www.cnncecp.com/',
        '大唐集团': 'https://www.cdt-ec.com/home/',
        '国网ECP': 'https://ecp.sgcc.com.cn/',
    }
    
    items = []
    for name, url in targets.items():
        html = chromium_render(url)
        if not html:
            continue
        
        # 提取详情链接
        for m in re.finditer(r'href\s*=\s*["\']([^"\']*(?:detail|bulletin|notice|zb|bid|tender|公告|招标|中标|详情)[^"\']*)["\']', html, re.I):
            full_url = urljoin(url, m.group(1))
            if len(full_url) > 500 or 'javascript' in full_url.lower():
                continue
            
            detail_html = fetch(full_url)
            if not detail_html or len(detail_html) < 500:
                detail_html = chromium_render(full_url)
            if not detail_html:
                continue
            
            text = extract_text(detail_html)
            if len(text) < 80:
                continue
            
            items.append({
                'title': text[:100],
                'content': text[:800],
                'source': name,
                'source_url': full_url,
                'notice_type': 'bidding',
                'publish_date': '',
                'procurement_owner': '',
                'raw_text': text,
            })
            if len(items) >= 30:
                break
    
    return items


# ═══════════════════════════════════════════
# 统一入库
# ═══════════════════════════════════════════
def save_to_db(items, conn):
    scored = score_items(items)
    inserted_bid = 0
    inserted_win = 0
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
                    (s.get('title','') or '')[:200],
                    s.get('winner_company','') or s.get('procurement_owner','') or '',
                    s.get('winning_amount','') or '',
                    s.get('publish_date',''),
                    datetime.now().isoformat(),
                    (s.get('content','') or s.get('raw_text',''))[:2000],
                    h, s.get('relevance_score', 0),
                    s.get('procurement_owner','')[:200],
                    s.get('region',''), s.get('province',''),
                    s.get('category',''),
                ))
                inserted_win += 1
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
                    notice_type, s.get('publish_date',''),
                    datetime.now().isoformat(),
                    (s.get('content','') or s.get('raw_text',''))[:2000],
                    h, s.get('relevance_score', 0),
                    s.get('procurement_owner','')[:200],
                    s.get('region',''), s.get('province',''),
                    s.get('category',''),
                ))
                inserted_bid += 1
        except: pass
    conn.commit()
    return inserted_bid + inserted_win


# ═══════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════
def main():
    print(f"[{datetime.now():%H:%M:%S}] 六大六小专属适配器启动")
    conn = sqlite3.connect(str(BASE_DIR / 'data' / 'bidding.db'))
    total = 0
    
    platforms = [
        ('🏭 南方电网', crawl_nanwang),
        ('⚡ 国家电投', crawl_guodianta),
        ('🏗️ 华润守正', crawl_huarun_szecp),
        ('🌊 三峡集团', crawl_sanxia),
    ]
    
    for name, crawler in platforms:
        print(f"\n── {name} ──")
        try:
            items = crawler()
            if items:
                n = save_to_db(items, conn)
                total += n
                print(f"  抓取{len(items)}条 → 入库{n}条")
            else:
                print(f"  无数据")
        except Exception as e:
            print(f"  ❌ {e}")
    
    # JS平台（慢，放最后）
    print(f"\n── JS渲染平台 ──")
    try:
        js_items = crawl_js_platforms()
        if js_items:
            n = save_to_db(js_items, conn)
            total += n
            print(f"  抓取{len(js_items)}条 → 入库{n}条")
    except Exception as e:
        print(f"  ❌ {e}")
    
    bidding = conn.execute("SELECT count(*) FROM bidding_notices").fetchone()[0]
    print(f"\n{'='*50}")
    print(f"  本轮新增: {total} 条")
    print(f"  库内总计: {bidding}")
    conn.close()

if __name__ == '__main__':
    main()
