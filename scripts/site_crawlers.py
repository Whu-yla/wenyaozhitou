#!/usr/bin/env python3
"""
文鳐智投 站点适配器 v3.0
为已确认可用的站点编写专属公告列表+详情提取器
"""
import re
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
TIMEOUT = 20

# ── 华润守正电子招标平台 (szecp.crc.com.cn) ──
# 公告列表: /zbxx/006001/006001001/YYYYMMDD/xxx.html
# 首页可解析出公告分类链接

def crawl_huarun_szecp(max_pages=5):
    """
    华润集团守正电子招标平台
    公告类别: 006001001=招标公告, 006001002=变更公告, 006001003=中标候选人, 006001004=中标结果
    """
    base = "https://szecp.crc.com.cn"
    notices = []
    seen = set()
    
    # 从首页获取各公告类型的列表页
    try:
        resp = requests.get(base + "/", headers=HEADERS, timeout=TIMEOUT, verify=False)
        resp.encoding = 'utf-8'
        html = resp.text
        
        # 提取所有 zbxx 链接，特别是具体公告页
        detail_pattern = re.compile(r'/zbxx/006001/\d+/(\d{8})/([a-f0-9-]+)\.html')
        matches = detail_pattern.findall(html)
        
        for date_str, filename in matches:
            url = f"{base}/zbxx/006001/006001001/{date_str}/{filename}.html"
            if url in seen:
                continue
            seen.add(url)
            
            detail = fetch_huarun_detail(url)
            if detail:
                notices.append(detail)
    except Exception as e:
        print(f"[华润守正] 首页抓取失败: {e}")
    
    # 也尝试按分类列表抓取
    categories = [
        ('006001001', '招标公告'),
        ('006001003', '中标候选人'), 
        ('006001004', '中标结果'),
    ]
    
    for cat_id, cat_name in categories:
        try:
            # 列表页URL
            list_url = f"{base}/zbxx/006001/{cat_id}/secondpagejy.html"
            resp = requests.get(list_url, headers=HEADERS, timeout=TIMEOUT)
            resp.encoding = 'utf-8'
            html = resp.text
            
            # 提取详情链接
            detail_pattern = re.compile(r'href=\"(/zbxx/006001/\d+/(\d{8})/([a-f0-9-]+)\.html)\"')
            for match in detail_pattern.finditer(html):
                rel_url, date_str, filename = match.groups()
                url = urljoin(base, rel_url)
                if url in seen:
                    continue
                seen.add(url)
                
                detail = fetch_huarun_detail(url)
                if detail:
                    notices.append(detail)
                
                if len(notices) >= max_pages * 20:
                    break
        except Exception as e:
            print(f"[华润守正/{cat_name}] 抓取失败: {e}")
    
    return notices


def fetch_huarun_detail(url):
    """从华润守正详情页提取结构化的招标信息"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.encoding = 'utf-8'
        html = resp.text
        
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        text_clean = re.sub(r'\s+', ' ', text).strip()
        
        # 提取标题 - 优先用"项目名称"/"标段名称"字段
        title = ''
        # 方式1: 从"标段名称："字段提取
        m = re.search(r'标段名称[：:]\s*(.+?)(?:\s|&nbsp;)*\n', text_clean)
        if m:
            title = m.group(1).strip()
        if not title:
            # 方式2: 从"项目名称："字段提取
            m = re.search(r'项目名称[：:]\s*(.+?)(?:\s|&nbsp;)*\n', text_clean)
            if m:
                title = m.group(1).strip()
        if not title:
            # 方式3: 从"XXX项目已具备招标条件"提取
            m = re.search(r'(?:有限公司|公司)\s*(.+?项目)\s*已具备招标条件', text_clean)
            if m:
                title = m.group(1).strip()
        if not title:
            # 方式4: 提取招标公告编号后的内容
            m = re.search(r'(?:招标公告|中标公告)[（(][^)）]*[)）]\s*(.+?)(?:\s*根据项目进度|\s*&nbsp)', text_clean)
            if m:
                title = m.group(1).strip()[:80]
        if not title:
            # 方式5: HTML标题标签
            for tag in soup.find_all(['h1', 'h2', 'h3', 'title']):
                t = tag.get_text(strip=True)
                if t and len(t) > 5 and ('招标' in t or '中标' in t or '采购' in t):
                    title = t
                    break
        if not title:
            title = text_clean[:80]
        
        # 提取关键字段
        fields = {}
        field_patterns = {
            '招标人': r'招标人[：:]\s*(.+?)(?:\s|&nbsp;)*\n',
            '招标编号': r'招标编号[：:]\s*(\S+)',
            '项目名称': r'项目名称[：:]\s*(.+?)(?:\s|&nbsp;)*\n',
            '标段名称': r'标段名称[：:]\s*(.+?)(?:\s|&nbsp;)*\n',
            '招标内容和范围': r'招标内容和范围[：:]\s*(.+?)(?:\s*二[、.]|\s*注[：:]|\s*\n\s*\n)',
            '建设地点': r'建设地点[：:]\s*(.+?)(?:\s|&nbsp;)*\n',
            '项目资金来源': r'项目资金来源[：:]\s*(.+?)(?:\s|&nbsp;)*\n',
            '交货期/工期': r'交货期[／/]工期[：:]\s*(.+?)(?:\s|&nbsp;)*\n',
        }
        
        for key, pattern in field_patterns.items():
            m = re.search(pattern, text_clean)
            if m:
                fields[key] = m.group(1).strip()
        
        # 判断类型
        notice_type = 'bidding'
        if '中标' in text_clean[:500] or '成交' in text_clean[:500]:
            notice_type = 'winning'
        
        # 提取日期
        publish_date = ''
        date_match = re.search(r'发稿时间[：:]\s*(\d{4}-\d{2}-\d{2})', text_clean)
        if not date_match:
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text_clean[:2000])
            if date_match:
                publish_date = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
        if not date_match:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text_clean[:1000])
        if date_match:
            publish_date = date_match.group(1) if hasattr(date_match, 'group') else publish_date
        
        summary = text_clean[:500]
        
        return {
            'source': '华润守正电子招标平台',
            'source_url': url,
            'title': title or text_clean[:80],
            'notice_type': notice_type,
            'publish_date': publish_date,
            'procurement_owner': fields.get('招标人', ''),
            'project_name': fields.get('项目名称', ''),
            'bid_number': fields.get('招标编号', ''),
            'content': fields.get('招标内容和范围', '') or summary,
            'location': fields.get('建设地点', ''),
            'deadline': fields.get('交货期/工期', ''),
            'raw_text': text_clean,
        }
        
    except Exception as e:
        print(f"[华润守正详情] {url} 失败: {e}")
        return None


# ── 湖北省公共资源交易平台 (hbggzyfwpt.cn) ──
# 公告列表API: JSON格式，支持分页

def crawl_hubei_ggzy(max_pages=5):
    """
    湖北省公共资源交易平台
    使用API接口获取公告列表
    """
    notices = []
    base = "https://www.hbggzyfwpt.cn"
    
    # API端点（推测 - 需要验证）
    api_url = f"{base}/jyxx/jsgcZbgg"
    
    try:
        # 先获取列表页，找API调用
        resp = requests.get(
            f"{api_url}?currentArea=&page=1&area=000&pageSize=30",
            headers=HEADERS, timeout=TIMEOUT
        )
        resp.encoding = 'utf-8'
        html = resp.text
        
        # 找列表中的详情链接
        detail_links = re.findall(r'href=\"(/jyxx/jsgcZbggDetail\?guid=[^\"]+)\"', html)
        detail_links.extend(re.findall(r'href=\"(/jyxx/[^\"]*(?:Zbgg|Zbjggs|Kbjl|pbjggs)[^\"]*Detail[^\"]*)\"', html))
        
        for rel_url in detail_links[:max_pages * 15]:
            url = urljoin(base, rel_url)
            detail = fetch_hubei_detail(url)
            if detail:
                notices.append(detail)
        
        # 也尝试政府采购等分类
        for cat in ['zfcg/cggg', 'jsgcZbjggs', 'jsgcKbjl']:
            try:
                cat_url = f"{base}/jyxx/{cat}?currentArea=&page=1&area=000&pageSize=30"
                resp = requests.get(cat_url, headers=HEADERS, timeout=TIMEOUT)
                resp.encoding = 'utf-8'
                html2 = resp.text
                more_links = re.findall(r'href=\"(/jyxx/[^\"]*Detail\?guid=[^\"]+)\"', html2)
                for rel_url in more_links[:max_pages * 10]:
                    url = urljoin(base, rel_url)
                    detail = fetch_hubei_detail(url)
                    if detail:
                        notices.append(detail)
            except:
                pass
                
    except Exception as e:
        print(f"[湖北平台] 抓取失败: {e}")
    
    return notices


def fetch_hubei_detail(url):
    """从湖北省平台详情页提取信息"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.encoding = 'utf-8'
        html = resp.text
        
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        text_clean = re.sub(r'\s+', ' ', text).strip()
        
        # 标题通常在详情页的某个区域
        title = ''
        for tag in soup.find_all(['h1', 'h2', 'h3', 'td', 'span']):
            if tag.get('class') and any(c in str(tag.get('class')).lower() for c in ['title', 'bt', 'biaoti']):
                title = tag.get_text(strip=True)
                break
        
        if not title:
            # 找页面中明显的标题
            lines = [l.strip() for l in text_clean.split('\n') if l.strip()]
            for line in lines:
                if any(kw in line for kw in ['招标', '中标', '采购', '公告']) and len(line) < 200:
                    title = line
                    break
        
        if not title:
            title = text_clean[:100]
        
        notice_type = 'bidding'
        if any(kw in text_clean[:500] for kw in ['中标', '成交', '中选']):
            notice_type = 'winning'
        
        publish_date = ''
        date_match = re.search(r'(\d{4}[年/-]\d{1,2}[月/-]\d{1,2})', text_clean[:2000])
        if date_match:
            publish_date = date_match.group(1)
        
        return {
            'source': '湖北省公共资源交易平台',
            'source_url': url,
            'title': title,
            'notice_type': notice_type,
            'publish_date': publish_date,
            'procurement_owner': '',
            'project_name': title,
            'content': text_clean[:500],
            'raw_text': text_clean,
        }
    except Exception as e:
        print(f"[湖北详情] {url} 失败: {e}")
        return None


# ── 通用公告链接探测 ──

def probe_site_listing(site_url, html_content):
    """
    给一个站点首页HTML，探测可能的分页公告列表URL
    返回候选URL列表
    """
    candidates = set()
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        combined = (href + text).lower()
        
        # 寻找公告列表特征
        signals = [
            'zbgg', 'zbxx', 'cggg', 'jyxx', 'bulletin', 'notice', 'tender',
            '招标公告', '采购公告', '中标公告', '成交公告', '结果公告',
            '交易信息', '采购信息', '招标采购',
            '/trade/', '/jyxx/', '/zbxx/', '/bulletin/',
        ]
        
        if any(s in combined for s in signals):
            full_url = urljoin(site_url, href)
            candidates.add(full_url)
    
    # 也尝试常见分页URL模式
    common_patterns = [
        '/jyxx/jsgcZbgg',
        '/jyxx/zfcg/cggg',
        '/zbxx/006001/006001001/',
        '/trade/bulletin/',
        '/biddingBulletin/',
        '/search/searchzbw/',
        '/announcement/',
    ]
    
    for pattern in common_patterns:
        test_url = urljoin(site_url, pattern)
        candidates.add(test_url)
    
    return list(candidates)


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    
    print("=== 华润守正 ===")
    notices = crawl_huarun_szecp(max_pages=3)
    print(f"抓取 {len(notices)} 条公告")
    for n in notices[:10]:
        print(f"  [{n['notice_type']}] {n['title'][:60]}")
        print(f"    招标人: {n.get('procurement_owner', 'N/A')}")
        print(f"    日期: {n.get('publish_date', 'N/A')}")
        print(f"    内容: {n.get('content', '')[:100]}")
        print()
