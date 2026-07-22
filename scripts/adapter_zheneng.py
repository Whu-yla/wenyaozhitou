#!/usr/bin/env python3
"""
浙能集团专属适配器 — zsrm.zjenergy.com.cn
7978条公告数据，按日期分页
"""
import re, sys, sqlite3, hashlib
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

HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/125.0.0.0"}
TIMEOUT = 20
BASE = "https://zsrm.zjenergy.com.cn"

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
        return r.text if r.status_code==200 and len(r.text)>300 else None
    except: return None

def extract_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    for t in soup(['script','style','nav','footer','header']): t.decompose()
    return re.sub(r'\s+',' ',soup.get_text()).strip()

def crawl_zheneng(max_pages=30):
    """浙能集团 - 招标公告列表 → 详情页 → 结构化提取"""
    items = []
    seen = set()
    
    # 招标公告列表（使用iframe数据源）
    list_base = f"{BASE}/zjnycms//category/iframe.html"
    
    for page in range(1, max_pages + 1):
        list_url = f"{list_base}?dates=300&categoryId=2&tenderMethod=01&page={page}"
        html = fetch(list_url)
        if not html: break
        
        # 提取详情链接: /sdny_bulletin/YYYY-MM-DD/ID.html
        detail_urls = re.findall(r'(/sdny_\w+/\d{4}-\d{2}-\d{2}/\d+\.html)', html)
        
        if not detail_urls:
            break
        
        for rel_url in detail_urls[:20]:
            full_url = urljoin(BASE, rel_url)
            if full_url in seen: continue
            seen.add(full_url)
            
            detail_html = fetch(full_url)
            if not detail_html: continue
            
            text = extract_text(detail_html)
            if len(text) < 100: continue
            
            # 提取标题 - 从页面中找招标公告标题
            title = ''
            # 方式1: 匹配"XX公司XXX采购招标公告"完整标题模式（不因"浙能"在司名中截断）
            m = re.search(r'((?:浙江|浙能|国家能源|华能|华电|大唐|国电|中电投|南方电网|国网)\S{0,80}(?:招标公告|采购公告|中标候选人公示|中标结果公告))', text)
            if m: title = m.group(1).strip()[:200]
            if not title:
                # 方式2: 从 text 中提取第一段含"招标公告"/"采购公告"的完整句子（排除标题中包含的"浙能"截断）
                m = re.search(r'(?:招标公告|采购公告|中标候选人公示|中标结果公告|变更公告)\s*(.+?)(?:\s{2,}|\n\n|已具备招标条件)', text)
                if m: title = (m.group(0) + m.group(1)).strip()[:200]
            if not title:
                # 方式3: 直接从详情页顶部提取
                lines = text.split('\n')
                for line in lines[:10]:
                    line = line.strip()
                    if len(line) > 15 and any(kw in line for kw in ['招标','采购','中标','公告']):
                        title = line
                        break
            if not title:
                title = text[:120]
            
            # 判断类型
            notice_type = 'bidding'
            if any(kw in title for kw in ['中标候选人','中标结果','中标公示','成交结果']):
                notice_type = 'winning'
            elif any(kw in title for kw in ['变更','澄清','更正']):
                notice_type = 'procurement'
            
            # 提取招标人
            owner = ''
            m = re.search(r'招标人[：:]\s*(.+?)(?:\s*联系|\s*\n|$)', text)
            if m: owner = m.group(1).strip()[:60]
            
            # 提取日期 - 优先从URL提取，再从公告内容提取
            date = ''
            m_url = re.search(r'/(\d{4}-\d{2}-\d{2})/', full_url)
            # 从正文提取：找公告落款日期，通常出现在"202X年X月X日"且靠近"招标人"或"招标代理机构"
            m_doc = re.search(r'(?:招标人|招标代理机构|采购人|采购代理机构).{0,300}?(\d{4})年(\d{1,2})月(\d{1,2})日', text[:3000])
            if m_doc:
                date = f"{m_doc.group(1)}-{int(m_doc.group(2)):02d}-{int(m_doc.group(3)):02d}"
            if not date:
                # 兜底：正文中第一个中文日期
                m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text[:2000])
                if m: date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            if not date and m_url:
                # 最后兜底：URL中的日期
                date = m_url.group(1)
            
            items.append({
                'title': title,
                'content': text[:1000],
                'source': '浙能集团智慧供应链平台',
                'source_url': full_url,
                'notice_type': notice_type,
                'publish_date': date,
                'procurement_owner': owner,
                'raw_text': text,
            })
            
            if len(items) >= 200:
                return items
        
        if len(items) >= 200:
            break
    
    return items

def save(items, conn):
    scored = score_items(items)
    n_bid = n_win = 0
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
                n_win += 1
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
                n_bid += 1
        except: pass
    conn.commit()
    return n_bid + n_win

def main():
    print(f"[{datetime.now():%H:%M:%S}] 浙能适配器")
    conn = sqlite3.connect(str(BASE_DIR/'data'/'bidding.db'))
    
    items = crawl_zheneng(max_pages=30)
    print(f"  抓取{len(items)}条")
    
    n = save(items, conn)
    b = conn.execute("SELECT count(*) FROM bidding_notices").fetchone()[0]
    w = conn.execute("SELECT count(*) FROM winning_notices").fetchone()[0]
    print(f"  入库{n}条 | 库内: 招标{b}+中标{w}={b+w}")
    conn.close()

if __name__ == '__main__':
    main()
