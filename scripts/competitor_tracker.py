#!/usr/bin/env python3
"""
文鳐智投 竞品追踪引擎 v1.0
从winning_notices中提取中标公司 → 判竞品 → 排名 → 趋势 → 报告数据
"""
import re, sqlite3, json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict

DB_PATH = Path("/root/.hermes/profiles/wenyaozhitou/data/bidding.db")

# 数智科技的核心竞品（直接竞争对手）
CORE_COMPETITORS = {
    # 电力数字化核心竞品
    "南网数字": "南网数字运营软件科技",
    "南方电网数字": "南方电网数字电网集团",
    "南网科技": "南方电网电力科技",
    "华工精卓": "广东华工精卓数智创新科技",
    # 能源IT上市公司
    "远光软件": "远光软件",
    "朗坤智慧": "朗坤智慧科技",
    "科远智慧": "南京科远智慧科技",
    "金现代": "金现代信息产业",
    "恒华科技": "北京恒华伟业科技",
    "国能信控": "国能信控互联技术",
    # 电力自动化
    "南瑞": "南瑞集团",
    "国电南自": "国电南自",
    "四方继保": "北京四方继保",
    "积成电子": "积成电子",
    "东方电子": "东方电子",
    # IT服务
    "东软": "东软集团",
    "中电普华": "北京中电普华信息技术",
    "中科曙光": "中科曙光",
    "浪潮": "浪潮集团",
    # 数字孪生/BIM
    "达索": "达索系统",
    "奔特力": "Bentley",
    "北京构力": "北京构力科技",
    "广联达": "广联达科技",
    # 智能安防/AI
    "海康威视": "海康威视",
    "大华": "大华技术",
    "商汤": "商汤科技",
    "旷视": "旷视科技",
    "云从": "云从科技",
    # 智慧工地
    "品茗": "品茗科技",
    "广筑": "广筑数字科技",
    "筑业": "筑业软件",
    "鲁班": "鲁班软件",
}

# 竞品分类标识
COMPETITOR_TYPES = {
    "🔴 核心竞品": ["南网数字", "南方电网数字", "华工精卓", "南瑞", "国电南自"],
    "🟠 数字科技": ["远光软件", "朗坤智慧", "科远智慧", "金现代", "恒华科技", "东软"],
    "🟡 电力IT": ["中电普华", "四方继保", "积成电子"],
}

def extract_winner_company(text):
    """从公告文本提取中标公司"""
    # 第一中标候选人
    m = re.search(r'(?:第一中标|中标候选人1|第1中标).*?([\u4e00-\u9fff]{3,20}(?:科技|数字|信息|软件|数据|智能|技术|电力|电子|能源|管理|咨询|工程)(?:有限公司|股份公司|集团公司|[（(][^)）]*[)）]?))', text)
    if m: return m.group(1)
    # 中标人/中标单位
    m = re.search(r'(?:中标人|中标单位|成交供应商)[：:]\s*([\u4e00-\u9fff]{2,40}(?:有限公司|股份公司|集团公司))', text)
    if m: return m.group(1)
    return ""

def extract_winning_amount(text):
    """从公告文本提取中标金额（万元）"""
    # 投标报价 XX万元
    m = re.search(r'(?:投标报价|中标金额|成交金额|响应报价)[：:]?\s*(\d+(?:\.\d+)?)\s*万', text)
    if m: return float(m.group(1))
    # 45万元 模式
    m = re.search(r'(\d+(?:\.\d+)?)\s*万元', text)
    if m:
        amt = float(m.group(1))
        if 1 < amt < 10000: return amt
    return 0

def classify_competitor(name):
    """判断是否是竞品，以及竞品类型"""
    for cat, keywords in COMPETITOR_TYPES.items():
        for kw in keywords:
            if kw in name:
                return cat
    # 自动判断：名字里含 数字/科技/信息/软件/智能 → 潜在竞品
    if any(kw in name for kw in ['数字', '科技', '信息', '软件', '智能', '数据', '智慧']):
        return "⚪ 潜在竞品"
    return None  # 非竞品

def build_competitor_report(days=90):
    """生成竞品追踪报告"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    rows = conn.execute("""
        SELECT winner_company, winning_amount, title, relevance_score, 
               publish_date, province, content_summary
        FROM winning_notices 
        WHERE date(publish_date) >= ? OR date(fetch_date) >= ?
        ORDER BY publish_date DESC
    """, (cutoff, cutoff)).fetchall()
    
    # 补充提取winner_company
    competitors = defaultdict(lambda: {"wins": 0, "total_amount": 0, "projects": [], "categories": Counter()})
    
    for r in rows:
        winner = r["winner_company"] or ""
        if not winner:
            # 尝试从content提取
            text = (r["title"] or "") + " " + (r["content_summary"] or "")
            winner = extract_winner_company(text)
        
        if not winner:
            continue
        
        cat = classify_competitor(winner)
        if not cat:
            continue
        
        comp = competitors[winner]
        comp["wins"] += 1
        comp["type"] = cat
        
        # 金额 - 从content中提取
        amt = 0
        amt_str = r["winning_amount"] or ""
        if not amt_str:
            text = (r["content_summary"] or "")[:3000]
            amt = extract_winning_amount(text)
        else:
            m = re.search(r'(\d+(?:\.\d+)?)\s*万', amt_str)
            if m: amt = float(m.group(1))
        comp["total_amount"] += amt
        
        comp["projects"].append({
            "title": (r["title"] or "")[:100],
            "score": r["relevance_score"] or 0,
            "date": r["publish_date"] or "",
            "province": r["province"] or "",
            "amount": amt_str,
        })
        
        comp["categories"]["total"] += 1
    
    conn.close()
    
    # 排名（按中标次数）
    ranked = sorted(competitors.items(), key=lambda x: (-x[1]["wins"], -x[1]["total_amount"]))
    
    result = []
    for name, data in ranked:
        result.append({
            "name": name,
            "type": data["type"],
            "wins": data["wins"],
            "total_amount": round(data["total_amount"], 1),
            "amount_display": f"{data['total_amount']:.0f}万" if data["total_amount"] > 0 else "未知",
            "recent_projects": data["projects"][:3],
        })
    
    return result[:15]  # TOP15

def main():
    report = build_competitor_report(90)
    print(f"竞品追踪 (90天): 发现 {len(report)} 个竞品\n")
    for c in report:
        print(f"  {c['type']} {c['name']}")
        print(f"    中标{c['wins']}次 | 总金额{c['amount_display']}")
        for p in c['recent_projects']:
            print(f"    → [{p['score']:.0f}分] {p['title'][:60]}")
        print()


# ═══ 供报告生成器调用的接口 ═══
def get_competitor_stats(days=90):
    """返回 {competitors: [...], categories: [...]}"""
    report = build_competitor_report(days)
    categories = Counter()
    for c in report:
        categories[c['type']] += c['wins']
    return {
        "competitors": report,
        "categories": [[k, v] for k, v in categories.most_common()],
        "period_days": days,
        "updated": datetime.now().isoformat(),
    }

def get_big_projects(min_amount=500, days=30):
    """大项目追踪（单项目金额>min_amount万）"""
    return []  # 当前数据量不足，预留

if __name__ == '__main__':
    main()
