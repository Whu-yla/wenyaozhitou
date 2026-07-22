#!/usr/bin/env python3
"""
文鳐智投 统一采集管线 v1.0
扫描路径：站点适配器 → 详情抓取 → v8评分 → 去重入库 → 生成报告
"""
import sys, json, sqlite3, time, hashlib
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/root/.hermes/profiles/wenyaozhitou")
sys.path.insert(0, str(BASE_DIR / "scripts"))

import urllib3
urllib3.disable_warnings()

from site_crawlers import crawl_huarun_szecp, crawl_hubei_ggzy
from relevance_scorer import score_items

# ── 已有适配器按平台逐一加载 ──
try:
    from dedicated_adapters import crawl_nanwang
except Exception as e:
    print(f"  ⚠️ 南网适配器加载失败: {e}")
    crawl_nanwang = None
try:
    from dedicated_adapters import crawl_guodianta
except Exception as e:
    print(f"  ⚠️ 国电投适配器加载失败: {e}")
    crawl_guodianta = None
try:
    from dedicated_adapters import crawl_nengjian
except Exception as e:
    print(f"  ⚠️ 能建适配器加载失败: {e}")
    crawl_nengjian = None
try:
    from dedicated_adapters import crawl_sanxia
except Exception as e:
    print(f"  ⚠️ 三峡适配器加载失败: {e}")
    crawl_sanxia = None
try:
    from dedicated_adapters import crawl_js_platforms
except Exception as e:
    print(f"  ⚠️ 江苏平台适配器加载失败: {e}")
    crawl_js_platforms = None
try:
    from adapter_zheneng import crawl_zheneng
except Exception as e:
    print(f"  ⚠️ 浙能适配器加载失败: {e}")
    crawl_zheneng = None
try:
    from adapter_guoneng import crawl_guoneng
except Exception as e:
    print(f"  ⚠️ 国家能源适配器加载失败: {e}")
    crawl_guoneng = None
try:
    from adapter_supplement import crawl_shenneng
except Exception as e:
    print(f"  ⚠️ 申能适配器加载失败: {e}")
    crawl_shenneng = None
try:
    from adapter_huaneng import crawl_huaneng
except Exception as e:
    print(f"  ⚠️ 华能适配器加载失败: {e}")
    crawl_huaneng = None
try:
    from adapter_dlzb import crawl_all as crawl_all_dlzb
except Exception as e:
    print(f"  ⚠️ dlzb统一适配器加载失败: {e}")
    crawl_all_dlzb = None
try:
    from adapter_mengxi import crawl_mengxi
except Exception as e:
    print(f"  ⚠️ 蒙西电网适配器加载失败: {e}")
    crawl_mengxi = None

DB_PATH = BASE_DIR / "data" / "bidding.db"

def ensure_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bidding_notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, url TEXT, source_site TEXT, source_department TEXT,
            notice_type TEXT, publish_date TEXT, fetch_date TEXT,
            content_summary TEXT, raw_html TEXT, is_new INTEGER DEFAULT 1,
            unique_hash TEXT UNIQUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            relevance_score REAL, procurement_owner TEXT, region TEXT,
            province TEXT, category TEXT, budget_amount TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS winning_notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, url TEXT, source_site TEXT, source_department TEXT,
            project_name TEXT, winner_company TEXT, winning_amount TEXT,
            publish_date TEXT, fetch_date TEXT, content_summary TEXT,
            raw_html TEXT, is_new INTEGER DEFAULT 1,
            unique_hash TEXT UNIQUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            relevance_score REAL, procurement_owner TEXT, region TEXT,
            province TEXT, category TEXT
        )
    """)
    conn.commit()
    return conn

def hash_item(title, url, source_site):
    # v2: 只用URL，跨爬虫一致，防止字段截断导致重复
    return hashlib.md5((url or '').encode()).hexdigest()

def extract_budget_from_content(text):
    """从公告正文中提取预算/最高限价"""
    if not text: return ''
    import re
    patterns = [
        # 南网HTML表格格式: 最高投标限价（万元）</td><td>55.79</td>
        r'最高(?:投标)?限价[^<]*?</td>\s*<td[^>]*>\s*(\d+\.?\d*)',
        r'最高(?:投标)?限价[（(][^)）]*万元[）)]\s*(\d+\.?\d*)',
        r'最高投标限价[：:]\s*(\d+\.?\d*)\s*万',
        r'最高限价[：:]\s*(\d+\.?\d*)\s*万',
        r'预算金额[：:]\s*(\d+\.?\d*)\s*万',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            val = m.group(1)
            if re.match(r'^\d+\.?\d*$', val):
                return val + '万元'
    return ''


def insert_notice(conn, item):
    """插入单条公告，去重"""
    # ── L1 页面类型判别器：拦截平台首页/导航页/列表页 ──
    title = item.get('title','') or ''
    content = item.get('content','') or item.get('raw_text','') or ''
    check_text = title + ' ' + content
    
    PLATFORM_SIGNALS = [
        '您现在正在浏览', '首页 >', 'APP下载', '关于我们',
        '返回首页', '平台首页', '设为首页', '收藏此页',
        '欢迎来到', '您好！欢迎', '框架协议采购 首页',
        '公告信息 公告信息', '交易信息 -',
        '电子保函综合服务平台', '搜 索 返回天工开物',
    ]
    if any(sig in check_text for sig in PLATFORM_SIGNALS):
        return False  # 平台页，静默丢弃
    
    h = hash_item(item.get('title',''), item.get('source_url',''), item.get('source',''))
    try:
        if item['notice_type'] == 'winning':
            conn.execute("""
                INSERT OR IGNORE INTO winning_notices 
                (title, url, source_site, project_name, winner_company, winning_amount,
                 publish_date, fetch_date, content_summary, is_new, unique_hash,
                 relevance_score, procurement_owner, region, province, category)
                VALUES (?,?,?,?,?,?,?,?,?,1,?,?,?,?,?,?)
            """, (
                item.get('title','')[:500],
                item.get('source_url','')[:500],
                item.get('source','')[:200],
                item.get('project_name','')[:300],
                item.get('winner_company','')[:200],
                item.get('winning_amount','')[:50],
                item.get('publish_date',''),
                datetime.now().isoformat(),
                (item.get('content','') or item.get('raw_text',''))[:2000],
                h,
                item.get('relevance_score', 0),
                item.get('procurement_owner','')[:200],
                item.get('region',''),
                item.get('province',''),
                item.get('category',''),
            ))
        else:
            conn.execute("""
                INSERT OR IGNORE INTO bidding_notices
                (title, url, source_site, notice_type, publish_date, fetch_date,
                 content_summary, is_new, unique_hash, relevance_score,
                 procurement_owner, region, province, category, budget_amount)
                VALUES (?,?,?,?,?,?,?,1,?,?,?,?,?,?,?)
            """, (
                item.get('title','')[:500],
                item.get('source_url','')[:500],
                item.get('source','')[:200],
                item.get('notice_type','bidding'),
                item.get('publish_date',''),
                datetime.now().isoformat(),
                (item.get('content','') or item.get('raw_text',''))[:2000],
                h,
                item.get('relevance_score', 0),
                item.get('procurement_owner','')[:200],
                item.get('region',''),
                item.get('province',''),
                item.get('category',''),
                extract_budget_from_content(item.get('content','') or item.get('raw_text','') or ''),
            ))
        return True
    except Exception as e:
        return False

def main():
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] === 文鳐智投 统一采集管线启动 ===")
    conn = ensure_db()
    
    total_fetched = 0
    total_scored = 0
    total_inserted = 0
    
    # ── 阶段1: 华润守正 ──
    print("\n── 华润集团守正电子招标平台 ──")
    notices = crawl_huarun_szecp(max_pages=5)
    valid = [n for n in notices if '404' not in n.get('title','') and n.get('content','')]
    print(f"  抓取 {len(notices)} 条，过滤404后 {len(valid)} 条")
    total_fetched += len(valid)
    
    # 评分
    if valid:
        scored = score_items(valid)
        total_scored += len(scored)
        print(f"  评分通过 {len(scored)} 条")
        
        for s in scored:
            ok = insert_notice(conn, s)
            if ok:
                total_inserted += 1
                print(f"    ✅ [{s.get('relevance_score',0):.0f}分] {s.get('title','')[:50]}")
        conn.commit()
    
    # ── 阶段2: 湖北省平台 ──
    print("\n── 湖北省公共资源交易平台 ──")
    hb_notices = crawl_hubei_ggzy(max_pages=3)
    valid_hb = [n for n in hb_notices if n.get('content','') and '404' not in n.get('title','')]
    print(f"  抓取 {len(hb_notices)} 条，有效 {len(valid_hb)} 条")
    total_fetched += len(valid_hb)
    
    if valid_hb:
        scored_hb = score_items(valid_hb)
        total_scored += len(scored_hb)
        print(f"  评分通过 {len(scored_hb)} 条")
        
        for s in scored_hb:
            ok = insert_notice(conn, s)
            if ok:
                total_inserted += 1
                print(f"    ✅ [{s.get('relevance_score',0):.0f}分] {s.get('title','')[:50]}")
        conn.commit()
    
    # ── 阶段3: 南方电网 ──
    print("\n── 南方电网供应链统一平台 ──")
    if crawl_nanwang:
        nw_items = crawl_nanwang(max_items=30)
        print(f"  抓取 {len(nw_items)} 条")
        total_fetched += len(nw_items)
        if nw_items:
            scored_nw = score_items(nw_items)
            total_scored += len(scored_nw)
            print(f"  评分通过 {len(scored_nw)} 条")
            for s in scored_nw:
                ok = insert_notice(conn, s)
                if ok:
                    total_inserted += 1
                    print(f"    ✅ [{s.get('relevance_score',0):.0f}分] {s.get('title','')[:50]}")
            conn.commit()
    else:
        print("  ⚠️ 适配器未加载")
    
    # ── 阶段4: 浙能集团 ──
    print("\n── 浙能集团智慧供应链平台 ──")
    if crawl_zheneng:
        zn_items = crawl_zheneng(max_pages=5)  # reduced for daily
        print(f"  抓取 {len(zn_items)} 条")
        total_fetched += len(zn_items)
        if zn_items:
            scored_zn = score_items(zn_items)
            total_scored += len(scored_zn)
            print(f"  评分通过 {len(scored_zn)} 条")
            for s in scored_zn:
                ok = insert_notice(conn, s)
                if ok:
                    total_inserted += 1
                    print(f"    ✅ [{s.get('relevance_score',0):.0f}分] {s.get('title','')[:50]}")
            conn.commit()
    else:
        print("  ⚠️ 适配器未加载")
    
    # ── 阶段5: 国家能源集团 ──
    print("\n── 国家能源集团国能e招 ──")
    if crawl_guoneng:
        gn_items = crawl_guoneng(max_pages=3)
        print(f"  抓取 {len(gn_items)} 条")
        total_fetched += len(gn_items)
        if gn_items:
            scored_gn = score_items(gn_items)
            total_scored += len(scored_gn)
            print(f"  评分通过 {len(scored_gn)} 条")
            for s in scored_gn:
                ok = insert_notice(conn, s)
                if ok:
                    total_inserted += 1
                    print(f"    ✅ [{s.get('relevance_score',0):.0f}分] {s.get('title','')[:50]}")
            conn.commit()
    else:
        print("  ⚠️ 适配器未加载")
    
    # ── 阶段6: 国电投 → 雷池WAF，走dlzb兜底 ──
    print("\n── 国家电投 → dlzb兜底 ──")
    print("  ⏭️ 雷池WAF封锁，已纳入阶段11")
    
    # ── 阶段7: 能建 ──
    print("\n── 中国能建电子采购平台 ──")
    if crawl_nengjian:
        nj_items = crawl_nengjian(max_items=20)
        print(f"  抓取 {len(nj_items)} 条")
        total_fetched += len(nj_items)
        if nj_items:
            scored_nj = score_items(nj_items)
            total_scored += len(scored_nj)
            print(f"  评分通过 {len(scored_nj)} 条")
            for s in scored_nj:
                ok = insert_notice(conn, s)
                if ok:
                    total_inserted += 1
                    print(f"    ✅ [{s.get('relevance_score',0):.0f}分] {s.get('title','')[:50]}")
            conn.commit()
    else:
        print("  ⚠️ 适配器未加载")
    
    # ── 阶段8: 三峡 ──
    print("\n── 三峡集团电子采购平台 ──")
    if crawl_sanxia:
        sx_items = crawl_sanxia(max_items=15)
        print(f"  抓取 {len(sx_items)} 条")
        total_fetched += len(sx_items)
        if sx_items:
            scored_sx = score_items(sx_items)
            total_scored += len(scored_sx)
            print(f"  评分通过 {len(scored_sx)} 条")
            for s in scored_sx:
                ok = insert_notice(conn, s)
                if ok:
                    total_inserted += 1
                    print(f"    ✅ [{s.get('relevance_score',0):.0f}分] {s.get('title','')[:50]}")
            conn.commit()
    else:
        print("  ⚠️ 适配器未加载")
    
    # ── 阶段9: 江苏平台 ──
    print("\n── 江苏电力招标平台 ──")
    if crawl_js_platforms:
        js_items = crawl_js_platforms()
        print(f"  抓取 {len(js_items)} 条")
        total_fetched += len(js_items)
        if js_items:
            scored_js = score_items(js_items)
            total_scored += len(scored_js)
            print(f"  评分通过 {len(scored_js)} 条")
            for s in scored_js:
                ok = insert_notice(conn, s)
                if ok:
                    total_inserted += 1
                    print(f"    ✅ [{s.get('relevance_score',0):.0f}分] {s.get('title','')[:50]}")
            conn.commit()
    else:
        print("  ⚠️ 适配器未加载")
    
    # ── 阶段10: 申能 ──
    print("\n── 申能集团招标平台 ──")
    if crawl_shenneng:
        sn_items = crawl_shenneng(max_items=20)
        print(f"  抓取 {len(sn_items)} 条")
        total_fetched += len(sn_items)
        if sn_items:
            scored_sn = score_items(sn_items)
            total_scored += len(scored_sn)
            print(f"  评分通过 {len(scored_sn)} 条")
            for s in scored_sn:
                ok = insert_notice(conn, s)
                if ok:
                    total_inserted += 1
                    print(f"    ✅ [{s.get('relevance_score',0):.0f}分] {s.get('title','')[:50]}")
            conn.commit()
    else:
        print("  ⚠️ 适配器未加载")
    
    # ── 阶段10.5: 蒙西电网 ──
    print("\n── 蒙西电网(内蒙古电力集团) ──")
    if crawl_mengxi:
        mx_items = crawl_mengxi(max_items=30)
        print(f"  抓取 {len(mx_items)} 条")
        total_fetched += len(mx_items)
        if mx_items:
            total_scored += len(mx_items)
            print(f"  评分通过 {len(mx_items)} 条")
            for s in mx_items:
                ok = insert_notice(conn, s)
                if ok:
                    total_inserted += 1
                    print(f"    ✅ [{s.get('relevance_score',0):.0f}分] {s.get('title','')[:50]}")
            conn.commit()
    else:
        print("  ⚠️ 适配器未加载")
    
    # ── 阶段11: dlzb.com 兜底
    print("\n── dlzb.com 电力招标网(兜底9平台) ──")
    print("  覆盖: 华能/华电/大唐/国电投/国投/中核/中节能/中广核/国网")
    if crawl_all_dlzb:
        dlzb_items = crawl_all_dlzb(max_per_company=15)
        print(f"  抓取 {len(dlzb_items)} 条")
        total_fetched += len(dlzb_items)
        if dlzb_items:
            total_scored += len(dlzb_items)
            print(f"  评分通过 {len(dlzb_items)} 条")
            for s in dlzb_items[:30]:  # 最多显示30条
                ok = insert_notice(conn, s)
                if ok:
                    total_inserted += 1
                    print(f"    ✅ [{s.get('relevance_score',0):.0f}分] [{s.get('source','')}] {s.get('title','')[:50]}")
            conn.commit()
    else:
        print("  ⚠️ dlzb适配器未加载")
    
    # ── 统计 ──
    print(f"\n{'='*60}")
    print(f"  采集完成: 抓取{total_fetched} → 评分通过{total_scored} → 入库{total_inserted}")
    
    # ── 查询当前库 ──
    bidding_count = conn.execute("SELECT count(*) FROM bidding_notices WHERE relevance_score > 0").fetchone()[0]
    winning_count = conn.execute("SELECT count(*) FROM winning_notices WHERE relevance_score > 0").fetchone()[0]
    print(f"  库内总计: 招标 {bidding_count} + 中标 {winning_count} = {bidding_count + winning_count}")
    
    conn.close()

if __name__ == "__main__":
    main()
