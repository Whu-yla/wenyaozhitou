#!/usr/bin/env python3
"""国家能源集团（国能e招）适配器 v2 — 含中标人/金额提取"""
import subprocess, re, hashlib, sys
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

CHROMIUM = "/snap/bin/chromium"
ARGS = ["--headless=new", "--no-sandbox", "--disable-gpu",
        "--disable-dev-shm-usage", "--virtual-time-budget=20000", "--dump-dom"]
BASE_URL = "https://www.chnenergybidding.com.cn/bidweb/"


def chromium_fetch(url, timeout=30):
    try:
        r = subprocess.run([CHROMIUM] + ARGS + [url],
                          capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 and len(r.stdout) > 500 else None
    except:
        return None


def extract_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    for t in soup(['script', 'style', 'nav', 'footer', 'header', 'link', 'meta']):
        t.decompose()
    return re.sub(r'\s+', ' ', soup.get_text()).strip()


def _extract_from_table(html, text, keyword):
    """从HTML表格中提取关键词对应的值
    支持跨行表格: 表头行含关键词 → 找到列位置 → 数据行读取同列值
    """
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')

    # 方案1: 先找表头行列位置
    col_idx = None
    for row in rows:
        cells = row.find_all(['td', 'th'])
        for i, cell in enumerate(cells):
            ct = cell.get_text(strip=True)
            if keyword in ct:
                col_idx = i
                break
        if col_idx is not None:
            break

    # 找到了列位置，扫描后续数据行
    if col_idx is not None:
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) > col_idx:
                val = cells[col_idx].get_text(strip=True)
                # 跳过表头行（值仍含关键词或为空白）
                if val and keyword not in val and len(val) > 1:
                    # 清理 <br> 等
                    val = re.sub(r'<[^>]+>', '', str(cells[col_idx])).strip()
                    return val[:200]

    # 方案2: 同行相邻 td（备用）
    for row in rows:
        cells = row.find_all(['td', 'th'])
        for i, cell in enumerate(cells):
            ct = cell.get_text(strip=True)
            if keyword in ct and i + 1 < len(cells):
                val = cells[i + 1].get_text(strip=True)
                if val and keyword not in val and len(val) > 1:
                    return re.sub(r'<[^>]+>', '', str(cells[i+1])).strip()[:200]

    # 方案3: 纯文本正则
    patterns = {
        '中标人': [
            r'中标人[：:]\s*([\u4e00-\u9fa5（）()有限公司责任集团]{4,40})',
            r'中标供应商[：:]\s*([\u4e00-\u9fa5（）()有限公司责任集团]{4,40})',
        ],
        '中标金额': [
            r'中标金额[：:]\s*(\d+\.?\d*)\s*万',
            r'中标价[：:]\s*(\d+\.?\d*)\s*万',
        ],
        '最高限价': [
            r'最高限价[（(]万元[）)]\s*[：:]?\s*(\d+\.?\d*)',
            r'最高投标限价[：:]\s*(\d+\.?\d*)\s*万',
            r'预算金额[：:]\s*(\d+\.?\d*)\s*万',
        ],
    }
    if keyword in patterns:
        for pat in patterns[keyword]:
            m = re.search(pat, text)
            if m:
                val = m.group(1).strip()
                if '金额' in keyword or '限价' in keyword or '预算' in keyword:
                    val = val + '万元'
                return val[:200]
    return ''


def crawl_guoneng(max_pages=3):
    """爬取国家能源集团国能e招公告"""
    items = []

    home_html = chromium_fetch(BASE_URL, timeout=40)
    if not home_html:
        return items

    links = re.findall(r'href\s*=\s*["\']([^"\']*\.html[^"\']*)["\']', home_html)
    detail_urls = set()
    for l in links:
        full = urljoin(BASE_URL, l)
        if '/bidweb/001/' in full and 'javascript' not in l.lower():
            detail_urls.add(full)

    seen = set()
    for url in list(detail_urls)[:50]:
        html = chromium_fetch(url, timeout=25)
        if not html or len(html) < 300:
            continue

        text = extract_text(html)
        if len(text) < 30:
            continue

        # 提取标题
        title = ""
        h1 = re.search(r'<h1[^>]*>(.+?)</h1>', html)
        if h1:
            title = re.sub(r'<[^>]+>', '', h1.group(1)).strip()
        if not title:
            m = re.search(r'(?:招标|采购|中标|资格预审|询价|竞谈|竞争性)[^\n]{10,200}', text)
            if m:
                title = m.group(0)[:200]
        if not title:
            title = text.split('。')[0][:200]

        # 跳过噪声
        if any(x in title[:30] for x in ['招标网', '国能e招', '招标计划', '招标文件']):
            continue
        if '首页' in title[:20]:
            continue

        hk = hashlib.md5(title[:100].encode()).hexdigest()
        if hk in seen:
            continue
        seen.add(hk)

        ntype = 'winning' if ('中标' in title or '候选人' in title or '结果' in title) else 'bidding'
        dm = re.search(r'(\d{4}-\d{2}-\d{2})', text)

        items.append({
            'title': title[:200],
            'content': text[:1000],
            'source': '国家能源集团国能e招',
            'source_url': url,
            'notice_type': ntype,
            'publish_date': dm.group(1) if dm else '',
            'procurement_owner': '',
            'winner_company': _extract_from_table(html, text, '中标人') if ntype == 'winning' else '',
            'winning_amount': _extract_from_table(html, text, '中标金额') if ntype == 'winning' else '',
            'budget_amount': _extract_from_table(html, text, '最高限价') if ntype == 'bidding' else '',
            'raw_text': text,
        })

    return items


if __name__ == "__main__":
    items = crawl_guoneng()
    print(f"抓取 {len(items)} 条")
    for item in items[:10]:
        extra = ''
        wc = item.get('winner_company')
        wa = item.get('winning_amount')
        if wc: extra += ' 中标人:' + wc
        if wa: extra += ' 金额:' + wa
        print(f"  [{item['notice_type']}] {item['title'][:60]}{extra}")
