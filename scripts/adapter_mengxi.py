#!/usr/bin/env python3
"""
蒙西电网(内蒙古电力集团) 适配器
平台: http://wzglb.impc.com.cn:82/
特点: 无 WAF，curl 直连，公开可访问

策略:
  1. curl 首页 → 正则提取 project/news ID
  2. 逐个获取详情页 /html/project/{col}/{id}.html
  3. 提取标题/日期/类型/正文
  4. 评分→入库
"""

import re, sys, os, time
from datetime import datetime
from urllib.parse import urljoin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from relevance_scorer import score_item, classify_customer

BASE = "http://wzglb.impc.com.cn:82"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def fetch(url: str, timeout: int = 20) -> str:
    """HTTP GET"""
    try:
        import requests
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.encoding = r.apparent_encoding or 'utf-8'
        return r.text if r.status_code == 200 and len(r.text) > 300 else ''
    except Exception as e:
        print(f"  [蒙西] fetch异常: {url[:80]} → {e}")
        return ''


def parse_ids(html: str) -> list:
    """从 HTML 提取所有项目/公告 ID"""
    ids = []
    
    # 招标项目: showProjectDetail('col','id')
    for m in re.finditer(r"showProjectDetail\s*\(\s*'(\d+)'\s*,\s*'(\d+)'\s*\)", html):
        ids.append(('project', m.group(1), m.group(2)))
    
    # 结果公告: showNewsDetail('col','id')
    for m in re.finditer(r"showNewsDetail\s*\(\s*'(\d+)'\s*,\s*'(\d+)'\s*\)", html):
        ids.append(('news', m.group(1), m.group(2)))
    
    # 去重
    seen = set()
    unique = []
    for typ, col, nid in ids:
        key = f"{typ}|{col}|{nid}"
        if key not in seen:
            seen.add(key)
            unique.append((typ, col, nid))
    
    return unique


def parse_detail(html: str, source_url: str) -> dict:
    """解析详情页"""
    # 去标签
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 清除导航噪音
    noise = ['全站搜索', '招标公告', '非招标公告', '结果公告', '废标公告', 
             '合同服务', '物资调配', '竞价公告', '核实公告', '公共信息',
             '登录', '注册', '收藏网站', '收藏本站', '首页', '招标采购',
             '服务采购', '物资采购', '物资供应', '质量监督', '供应商管理',
             '关于我们', '业务公告', '政策法规', '工作动态', '年度采购计划预安排',
             '推荐的中标候选人公示', '中标（成交）结果公告', '否决公告',
             '组织结构', '规范标准', '不良行为处理', '监造标准', '检测标准',
             '质量监督信息发布', '绩效评价', '电子钥匙办理及安装', '操作手册及视频演示',
             '下载专区', '友情链接', '联系我们', '法律声明', '网站地图',
             '国采全流程电子化交易平台', '内蒙古电力集团电子商务系统']
    for n in noise:
        text = text.replace(n, '')
    text = re.sub(r'\s+', ' ', text).strip()
    
    if len(text) < 100:
        return None
    
    # 标题 — 通常在页面 title 或第一个 h1/title 标签中
    title = ''
    tm = re.search(r'<title>\s*(?:【|［|\[)?(.{15,200}?)(?:】|］|\])?\s*(?:-|—)?\s*</title>', html, re.DOTALL)
    if tm:
        title = tm.group(1).strip()
    
    if not title:
        # 从正文开头提取
        tm = re.search(r'(?:采购公告|招标公告|成交结果|中标候选人|结果公告)\s+(.{10,200})', text)
        if tm:
            title = f'{tm.group(0)}'.strip()[:200]
    
    if not title:
        title = text[:150].strip()
    
    # 日期
    date = ''
    dm = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', text[:1000])
    if dm:
        date = re.sub(r'[年月]', '-', dm.group(1)).replace('/', '-').replace('日', '')
    
    # 类型判断
    notice_type = 'bidding'
    if any(kw in title for kw in ['中标', '成交', '结果', '候选人', '公示']):
        notice_type = 'winning'
    
    # 招标人
    owner = ''
    om = re.search(r'(?:招标人|采购人|采购单位)[：:]\s*(.{5,60}?)(?:\s|$)', text)
    if om:
        owner = om.group(1).strip()[:80]
    if not owner:
        # 从标题提取公司名
        om = re.search(r'(?:内蒙古电力|蒙电|鄂尔多斯供电|呼和浩特供电|包头供电|乌兰察布供电|巴彦淖尔供电)\S{0,30}', title)
        if om:
            owner = om.group(0)
    
    return {
        'title': title[:200],
        'content': text[:1000],
        'source': '蒙西电网',
        'source_url': source_url,
        'notice_type': notice_type,
        'publish_date': date,
        'procurement_owner': owner or '内蒙古电力集团',
        'winner_company': '',
        'winning_amount': '',
        'budget_amount': '',
        'raw_text': text[:2000],
    }


def crawl_mengxi(max_items: int = 30) -> list:
    """蒙西电网主适配器"""
    print("[蒙西电网] 抓取首页...")
    
    html = fetch(f"{BASE}/")
    if not html:
        print("  ❌ 首页抓取失败")
        return []
    
    # 提取 ID
    id_list = parse_ids(html)
    print(f"  提取 {len(id_list)} 个公告ID")
    
    # 获取详情
    items = []
    for typ, col, nid in id_list[:max_items * 5]:
        if typ == 'project':
            url = f"{BASE}/html/project/{col}/{nid}.html"
        else:
            url = f"{BASE}/html/news/{col}/{nid}.html"
        
        detail_html = fetch(url)
        if not detail_html:
            continue
        
        parsed = parse_detail(detail_html, url)
        if parsed:
            items.append(parsed)
    
    print(f"  获取 {len(items)} 条详情")
    
    # 评分过滤
    scored = []
    for item in items:
        sc = score_item(item)
        if sc and sc.get('relevance_score', 0) >= 50:
            item['relevance_score'] = sc['relevance_score']
            item['category'] = classify_customer(item['title'])
            scored.append(item)
    
    scored.sort(key=lambda x: x['relevance_score'], reverse=True)
    print(f"  评分通过 {len(scored)}/{len(items)} 条 (≥55分)")
    return scored[:max_items]


if __name__ == '__main__':
    items = crawl_mengxi(20)
    for i, item in enumerate(items):
        print(f"[{i+1}] [{item.get('relevance_score',0):.0f}分] {item['title'][:80]}")
        print(f"    类型:{item['notice_type']} | 日期:{item['publish_date']}")
