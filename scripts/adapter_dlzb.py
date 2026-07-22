#!/usr/bin/env python3
"""
电力招标网(dlzb.com) 统一适配器
通过 Chromium headless 渲染，一次性覆盖全部发电集团。

URL 模式：https://www.dlzb.com/{company_key}/
  - 华能: huaneng
  - 华电: huadian
  - 大唐: datang
  - 国电投: guodianta
  - 国家能源: guojianengyuan
  - 国网: guowang
  - 南网: nanwang
  - 三峡: sanxia
  - 中广核: zhongguanghe
  - 华润: huarun
  - 国投: guotou
  - 中核: zhonghe
  - 中节能: zhongjienen
  - 中石油: zhongshiyou
  - 中石化: zhongshihua
  - 中海油: zhonghaiyou
  - 蒙西电网: mengxi
  （待验证准确路径）

依赖：/snap/bin/chromium (headless)
"""

import subprocess, re, json, hashlib, time, sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from relevance_scorer import score_item, classify_customer

CHROMIUM = "/snap/bin/chromium"
CHROMIUM_ARGS = [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "--virtual-time-budget=30000",
    "--dump-dom",
]

# ── 公司路径映射（仅无直连适配器的平台） ──────
# 已有直连的（南网/浙能/国家能源/华润/三峡/申能/能建）走专属适配器，不入此表
COMPANY_PATHS = {
    '华能集团': 'huaneng',       # WAF封死
    '华电集团': 'huadian',       # 无适配器
    '大唐集团': 'datang',        # SSO锁死
    '国投电力': 'guotou',        # 无适配器
    '中核集团': 'zhonghe',       # 无适配器
    '中节能': 'zhongjienen',     # 无适配器
    '中广核': 'zhongguanghe',    # API不稳定
    '国网': 'guowang',           # 登录锁死
    '国家电投': 'guodianta',      # 雷池WAF
}

# ── 数字关键词（快速过滤） ─────────────────
DIGITAL_KW = [
    '数字化', '智能化', '智慧', '软件', '平台', '系统', '信息',
    '数据', 'AI', '人工智能', '大模型', '网络安全', '安防',
    '监控', '物联网', '传感器', '数字孪生', 'BIM', '数智',
    '计算机', '服务器', '网络设备', '云', '5G', '安全管控',
    '巡检', '无人机', '机器人', '信息化', '信创', '等保',
]

# ── 排除词 ─────────────────────────────────
EXCLUDE_KW = [
    '螺栓', '阀门', '管件', '焊接', '保温', '防腐', '油漆',
    '混凝土', '钢筋', '脚手架', '模板', '电缆', '开关柜',
    '变压器', '断路器', '互感器', '避雷器', '绝缘子',
    '油品', '润滑', '化学试剂', '磨煤机', '给煤机', '风机',
    '皮带', '托辊', '筛分', '破碎', '除尘', '脱硫', '脱硝',
    '滤袋', '滤芯', '密封件', '轴承', '减速机', '联轴器',
    '泵', '压缩机', '换热器', '冷却塔', '空调',
    '电梯', '起重', '行车', '叉车', '装载机',
    '办公桌椅', '物业', '保洁', '保安', '绿化',
    '食堂', '餐饮', '车辆', '汽车', '司机',
    '体检', '医疗', '保险', '消防器材',
    '氨水', '液氨', '尿素', '石灰', '石膏', '水泥',
    '煤炭', '燃油', '柴油', '汽油', '天然气',
    '劳务分包', '土建', '装修', '地基', '打桩',
    '船租赁', '船舶', '锚', '洗涤', '运输服务',
    '人身意外险', '团体意外险', '电镀修复',
]


def chromium_fetch(url: str, timeout: int = 60) -> str:
    """Chromium headless 渲染页面"""
    try:
        r = subprocess.run(
            [CHROMIUM] + CHROMIUM_ARGS + [url],
            capture_output=True, text=True, timeout=timeout,
            env={"HOME": "/root", "DISPLAY": ""}
        )
        if r.returncode == 0 and len(r.stdout) > 2000:
            return r.stdout
        return ""
    except Exception as e:
        print(f"  [Chromium异常] {url}: {e}")
        return ""


def parse_list_page(html: str) -> list:
    """从 dlzb.com 列表页提取招标条目"""
    items = []
    
    # 提取完整链接 + 标题
    pattern = r'href="(https://www\.dlzb\.com/d-zb-\d+\.html)"[^>]*>\s*(.*?)\s*</a>'
    matches = re.findall(pattern, html)
    
    seen = set()
    for url, title_raw in matches:
        title = re.sub(r'<[^>]+>', '', title_raw).strip()
        if not title or len(title) < 10:
            continue
        if title in seen:
            continue
        seen.add(title)
        
        # 快速过滤
        has_digital = any(kw in title for kw in DIGITAL_KW)
        has_exclude = any(kw in title for kw in EXCLUDE_KW)
        
        if has_exclude:
            continue
        
        items.append({
            'title': title,
            'url': url,
            'has_digital': has_digital,
        })
    
    return items


def crawl_company(company_name: str, company_key: str, max_items: int = 20) -> list:
    """抓取单个公司的招标公告"""
    url = f"https://www.dlzb.com/{company_key}/"
    print(f"  [{company_name}] {url}")
    
    html = chromium_fetch(url)
    if not html:
        print(f"    ❌ 渲染失败")
        return []
    
    items = parse_list_page(html)
    print(f"    ✅ {len(items)} 条 (含数字关键词: {sum(1 for i in items if i['has_digital'])})")
    
    # 构造标准输出
    results = []
    for item in items[:max_items]:
        title = item['title']
        
        # 判断招标/中标
        notice_type = 'bidding'
        if re.search(r'中标|成交|结果|候选人', title):
            notice_type = 'winning'
        
        results.append({
            'title': title[:200],
            'content': title[:1000],
            'source': company_name,
            'source_url': item['url'],
            'notice_type': notice_type,
            'publish_date': datetime.now().strftime('%Y-%m-%d'),
            'procurement_owner': company_name,
            'winner_company': '',
            'winning_amount': '',
            'budget_amount': '',
            'raw_text': title,
            'has_digital': item['has_digital'],
        })
    
    return results


def crawl_all(max_per_company: int = 20) -> list:
    """抓取全部发电集团，评分入库"""
    all_items = []
    
    print(f"\n{'='*60}")
    print("电力招标网(dlzb.com) 全平台统一采集")
    print(f"{'='*60}")
    
    for name, key in COMPANY_PATHS.items():
        items = crawl_company(name, key, max_per_company)
        all_items.extend(items)
    
    # 评分过滤
    scored = []
    for item in all_items:
        sc = score_item(item)
        if sc and sc.get('relevance_score', 0) >= 55:
            item['relevance_score'] = sc['relevance_score']
            item['category'] = classify_customer(item['title'])
            scored.append(item)
    
    print(f"\n  总计: 抓取{len(all_items)} → 评分通过{len(scored)} (≥55分)")
    
    scored.sort(key=lambda x: x['relevance_score'], reverse=True)
    return scored


def crawl_huaneng(max_items: int = 30) -> list:
    """华能集团 - 兼容旧接口"""
    items = crawl_company('华能集团', 'huaneng', max_items)
    
    # 评分
    scored = []
    for item in items:
        sc = score_item(item)
        if sc and sc.get('relevance_score', 0) >= 55:
            item['relevance_score'] = sc['relevance_score']
            item['category'] = classify_customer(item['title'])
            scored.append(item)
    
    scored.sort(key=lambda x: x['relevance_score'], reverse=True)
    return scored


def crawl_huadian(max_items: int = 30) -> list:
    """华电集团"""
    items = crawl_company('华电集团', 'huadian', max_items)
    scored = []
    for item in items:
        sc = score_item(item)
        if sc and sc.get('relevance_score', 0) >= 55:
            item['relevance_score'] = sc['relevance_score']
            item['category'] = classify_customer(item['title'])
            scored.append(item)
    scored.sort(key=lambda x: x['relevance_score'], reverse=True)
    return scored


def crawl_datang(max_items: int = 30) -> list:
    """大唐集团"""
    items = crawl_company('大唐集团', 'datang', max_items)
    scored = []
    for item in items:
        sc = score_item(item)
        if sc and sc.get('relevance_score', 0) >= 55:
            item['relevance_score'] = sc['relevance_score']
            item['category'] = classify_customer(item['title'])
            scored.append(item)
    scored.sort(key=lambda x: x['relevance_score'], reverse=True)
    return scored


if __name__ == '__main__':
    print("="*60)
    print("dlzb.com 统一适配器 - 独立测试")
    print("="*60)
    
    # 测试华能
    items = crawl_huaneng(20)
    for i, item in enumerate(items[:10]):
        print(f"\n[{i+1}] [{item.get('relevance_score',0):.0f}分] {item['title'][:80]}")
        print(f"    来源: {item['source']} | 类型: {item['notice_type']}")
