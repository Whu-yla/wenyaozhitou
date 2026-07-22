#!/usr/bin/env python3
"""
华能集团招标公告适配器 — dlzb.com 聚合模式
数据源：电力招标网 (dlzb.com) → chng.toobiao.com 华能专区
ec.chng.com.cn 全站商业级 WAF 不可直接抓取，走第三方聚合。

策略：
  1. 从 chng.toobiao.com/zhaobiao/ 获取招标公告列表
  2. 详情在 dlzb.com/d-zb-XXXXXXXX.html（JS加密渲染）
  3. 兜底用列表页标题+摘要
  4. 评分→去重→入库

双模式：
  - Hermes 内：注入 hermes_tools.web_search 并尝试浏览器渲染
  - 独立模式：requests + 列表页解析
"""

import re, json, hashlib, time, sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from relevance_scorer import score_item, classify_customer

# ── 华能专区 URL ───────────────────────────
HUANENG_LIST_URL = "http://chng.toobiao.com/zhaobiao/"
HUANENG_WIN_URL = "http://chng.toobiao.com/zhongbiao/"

# ── 数字业务关键词（列表页过滤用） ──────
DIGITAL_KEYWORDS = [
    '数字化', '智能化', '智慧', '软件', '平台', '系统', '信息',
    '数据', 'AI', '人工智能', '大模型', '网络安全', '安防',
    '监控', '物联网', '传感器', '数字孪生', 'BIM', '数智',
    '计算机', '服务器', '网络设备', '云', '5G'
]

# ── 排除词（列表页级别快速过滤） ──────
EXCLUDE_KEYWORDS = [
    '螺栓', '阀门', '管件', '焊接', '保温', '防腐', '油漆',
    '混凝土', '钢筋', '脚手架', '模板', '电缆', '开关柜',
    '变压器', '断路器', '互感器', '避雷器', '绝缘子',
    '油品', '润滑', '化学试剂', '磨煤机', '给煤机', '风机',
    '皮带', '托辊', '筛分', '破碎', '除尘', '脱硫', '脱硝',
    '滤袋', '滤芯', '密封件', '轴承', '减速机', '联轴器',
    '泵', '压缩机', '换热器', '冷却塔', '冷却', '空调',
    '电梯', '起重', '行车', '叉车', '装载机',
    '办公桌椅', '空调', '物业', '保洁', '保安', '绿化',
    '食堂', '餐饮', '保洁', '车辆', '汽车', '司机',
    '体检', '医疗', '保险', '体检', '消防器材',
    '氨水', '液氨', '尿素', '石灰', '石膏', '水泥',
    '煤炭', '燃油', '柴油', '汽油', '天然气',
    '劳务分包', '土建', '装修', '地基', '打桩',
    '船租赁', '船舶', '锚', '海上风电项目拖锚',
]


def _fetch_list_page(url: str) -> str:
    """抓取列表页 HTML"""
    try:
        import requests
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = 'utf-8'
        return r.text
    except Exception as e:
        print(f"  [列表页异常] {url}: {e}")
        return ""


def _parse_list_titles(html: str) -> list:
    """从列表页 HTML 提取公告条目"""
    results = []
    
    # 提取标题+链接
    # dlzb.com 列表页格式：标题在 <a> 标签中，链接为 /d-zb-XXXXXXXX.html
    items = re.findall(
        r'<a[^>]*href="(/d-zb-\d+\.html)"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )
    
    seen = set()
    for url_path, title_raw in items:
        title = re.sub(r'<[^>]+>', '', title_raw).strip()
        if not title or len(title) < 8:
            continue
        if title in seen:
            continue
        seen.add(title)
        
        url = f"https://www.dlzb.com{url_path}"
        
        # 快速过滤：至少命中一个数字关键词
        has_digital = any(kw in title for kw in DIGITAL_KEYWORDS)
        has_exclude = any(kw in title for kw in EXCLUDE_KEYWORDS)
        
        if has_digital and not has_exclude:
            results.append({
                'title': title,
                'url': url,
            })
    
    # 如果没有命中数字关键词，退而求其次取全部
    if not results:
        for url_path, title_raw in items:
            title = re.sub(r'<[^>]+>', '', title_raw).strip()
            if title and len(title) >= 8:
                url = f"https://www.dlzb.com{url_path}"
                has_exclude = any(kw in title for kw in EXCLUDE_KEYWORDS)
                if not has_exclude:
                    results.append({'title': title, 'url': url})
    
    return results


def _extract_from_plaintext(text: str) -> list:
    """从纯文本中提取公告条目（兜底方案）"""
    results = []
    
    # 从文本中找类似公告的条目
    # pattern: 华能XXX项目...招标/采购/中标公告
    patterns = [
        r'(华能\S{0,80}(?:招标|采购|中标|成交|询价|竞谈|竞争性)\S{0,40}(?:公告|公示))',
        r'((?:华能|中国华能)\S{0,80}(?:公告|公示))',
    ]
    
    for pat in patterns:
        matches = re.findall(pat, text)
        for m in matches:
            title = m.strip()
            if len(title) >= 10:
                has_exclude = any(kw in title for kw in EXCLUDE_KEYWORDS)
                if not has_exclude:
                    results.append({
                        'title': title,
                        'url': 'http://chng.toobiao.com/zhaobiao/',
                    })
    
    return results


def crawl_huaneng(max_items: int = 30) -> list:
    """
    华能集团招标公告适配器主函数
    
    数据来源：
      1. chng.toobiao.com（华能招标专区，dlzb.com合作站）
      2. 搜索聚合兜底
    
    返回标准 dict 列表
    """
    results = []
    all_raw = []
    
    print(f"[华能适配器] 抓取华能招标专区...")
    
    # ── 第1步：列表页直接抓取 ──
    for url in [HUANENG_LIST_URL, HUANENG_WIN_URL]:
        html = _fetch_list_page(url)
        if html:
            items = _parse_list_titles(html)
            print(f"  {url} → {len(items)} 条")
            all_raw.extend(items)
        else:
            print(f"  {url} → 抓取失败")
    
    # ── 第2步：兜底——纯文本解析 ──
    if not all_raw:
        print("  列表解析无结果，尝试纯文本兜底...")
        for url in [HUANENG_LIST_URL, HUANENG_WIN_URL]:
            html = _fetch_list_page(url)
            if html:
                # 去除 HTML 标签
                text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text)
                items = _extract_from_plaintext(text)
                print(f"  {url} → 纯文本解析 {len(items)} 条")
                all_raw.extend(items)
    
    # ── 第3步：搜索聚合兜底 ──
    if not all_raw:
        print("  列表+文本均无结果，启用搜索兜底...")
        search_fn = getattr(sys.modules[__name__], '_search_fn', None)
        if search_fn:
            queries = [
                "华能 招标公告 数字化 智能化 智慧 软件 平台",
                "华能 中标公告 数字化 智慧 软件 平台",
                "华能集团 采购 信息系统 网络安全",
            ]
            for q in queries:
                try:
                    r = search_fn(q, limit=5)
                    if r and r.get('data', {}).get('web'):
                        for item in r['data']['web']:
                            title = item.get('title', '')
                            url = item.get('url', '')
                            desc = item.get('description', '')
                            if title and len(title) >= 8:
                                all_raw.append({
                                    'title': title,
                                    'url': url,
                                    'description': desc,
                                })
                    time.sleep(0.3)
                except Exception as e:
                    print(f"  搜索异常: {e}")
    
    print(f"[华能适配器] 总计收集 {len(all_raw)} 条原始数据")
    
    # ── 构造标准输出 ──
    for item in all_raw:
        title = item.get('title', '')
        url = item.get('url', '')
        desc = item.get('description', '')
        
        if not title:
            continue
        
        # 判断招标/中标
        notice_type = 'bidding'
        if re.search(r'中标|成交|结果公告|中标候选人|评标结果', title):
            notice_type = 'winning'
        
        # 内容：优先用摘要，否则用标题
        content = desc if desc else title
        
        # 日期提取
        publish_date = ''
        date_m = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', title + desc)
        if date_m:
            publish_date = f"{date_m.group(1)}-{date_m.group(2).zfill(2)}-{date_m.group(3).zfill(2)}"
        
        # 采购单位提取
        owner = '华能集团'
        owner_m = re.search(r'(华能\S{0,30}(?:公司|集团|电厂|分公司|中心))', title)
        if owner_m:
            owner = owner_m.group(1)
        
        results.append({
            'title': title[:200],
            'content': content[:1000],
            'source': '华能集团',
            'source_url': url,
            'notice_type': notice_type,
            'publish_date': publish_date,
            'procurement_owner': owner,
            'winner_company': '',
            'winning_amount': '',
            'budget_amount': '',
            'raw_text': f"{title}\n{content}",
        })
    
    # ── 评分过滤 ──
    scored = []
    for r in results:
        sc = score_item(r)
        if sc and sc.get('relevance_score', 0) >= 55:
            r['relevance_score'] = sc['relevance_score']
            r['category'] = classify_customer(r['title'])
            scored.append(r)
    
    print(f"[华能适配器] 评分通过 {len(scored)}/{len(results)} 条 (≥55分)")
    
    # 按分数降序，截取
    scored.sort(key=lambda x: x['relevance_score'], reverse=True)
    return scored[:max_items]


if __name__ == '__main__':
    print("=" * 60)
    print("华能集团适配器 — 独立测试")
    print("=" * 60)
    items = crawl_huaneng(max_items=20)
    for i, item in enumerate(items):
        print(f"\n[{i+1}] [{item.get('relevance_score',0):.0f}分] {item['title'][:80]}")
        print(f"    类型: {item['notice_type']} | 来源: {item['source']}")
        print(f"    URL: {item['source_url'][:100]}")
