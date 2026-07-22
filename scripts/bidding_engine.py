#!/usr/bin/env python3
"""
文鳐智投 投标信息抓取引擎 v2.0
功能：从Excel加载网站列表 → 爬取招标/中标公告 → 业务相关性评分 → 去重存库 → 生成HTML报告
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import traceback
import hashlib as hl
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import openpyxl
import requests
from bs4 import BeautifulSoup

# 业务相关性评分引擎
sys.path.insert(0, str(Path(__file__).parent))
from relevance_scorer import score_items, extract_detail_fields
from site_adapters import get_listing_urls, needs_js_render

# ── 路径配置 ──────────────────────────────────────────
BASE_DIR = Path("/root/.hermes/profiles/wenyaozhitou")
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "bidding.db"
EXCEL_PATH = Path("/root/.hermes/profiles/wenyaozhitou/cache/documents/doc_e0d2764cbad6_投标网站注册信息汇总表2026.6月.xlsx")
REPORT_DIR = Path("/var/www/html/bidding")
STATIC_DIR = REPORT_DIR
LOG_FILE = DATA_DIR / "crawler.log"

# ── HTTP 配置 ────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
TIMEOUT = 20
MAX_SITES_PER_RUN = 80  # 每次最多爬取的网站数

# Chromium headless JS 渲染引擎
CHROMIUM_BIN = "/snap/bin/chromium"
CHROMIUM_ARGS = "--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage --virtual-time-budget=15000 --dump-dom"

def chromium_fetch(url: str, timeout: int = 20) -> Optional[str]:
    """使用Chromium渲染JS页面并返回HTML"""
    try:
        result = subprocess.run(
            [CHROMIUM_BIN] + CHROMIUM_ARGS.split() + [url],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0 and result.stdout and len(result.stdout) > 1000:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    return None

# ── 关键词模式 ────────────────────────────────────────
BIDDING_KEYWORDS = [
    "招标", "采购", "询价", "竞争性谈判", "竞争性磋商", "比选",
    "招标公告", "采购公告", "询价公告", "资格预审", "征集",
]

WINNING_KEYWORDS = [
    "中标", "成交", "中标公告", "成交公告", "中标候选人",
    "中标结果", "成交结果", "中标公示", "成交公示",
    "结果公告", "结果公示", "定标", "中选",
]


# ── 数据库 ────────────────────────────────────────────

import sqlite3

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def make_hash(title: str, source_site: str) -> str:
    return hl.sha256(f"{title.strip()}|{source_site.strip()}".encode()).hexdigest()[:16]


def is_duplicate(conn, unique_hash: str) -> bool:
    c = conn.cursor()
    c.execute("SELECT 1 FROM bidding_notices WHERE unique_hash=?", (unique_hash,))
    if c.fetchone():
        return True
    c.execute("SELECT 1 FROM winning_notices WHERE unique_hash=?", (unique_hash,))
    return c.fetchone() is not None


def save_bidding(conn, item: dict) -> bool:
    """返回 True 表示新记录。item需含relevance_score"""
    h = make_hash(item["title"], item.get("source_site", ""))
    if is_duplicate(conn, h):
        return False
    score = item.get("relevance_score", 0)
    # FAQ/帮助/答疑类标题 → 不入库
    title = item.get("title", "")
    if any(kw in title for kw in ["常见问题", "帮助中心", "操作指南", "使用手册", "办事指南", "FQA"]):
        return False
    owner = item.get("procurement_owner", "")
    region = item.get("region", "")
    province = item.get("province", "")
    conn.execute(
        """INSERT INTO bidding_notices 
           (title, url, source_site, source_department, notice_type, 
            publish_date, fetch_date, content_summary, relevance_score,
            procurement_owner, region, province, category, unique_hash)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (item["title"], item.get("url"), item.get("source_site"),
         item.get("source_department"), item.get("notice_type", "招标公告"),
         item.get("publish_date"), item.get("fetch_date"), item.get("content_summary"),
         score, owner, region, province, item.get("category", "⚪ 其他"), h)
    )
    conn.commit()
    return True


def save_winning(conn, item: dict) -> bool:
    h = make_hash(item["title"], item.get("source_site", ""))
    if is_duplicate(conn, h):
        return False
    score = item.get("relevance_score", 0)
    # FAQ/帮助/答疑类标题 → 不入库
    title = item.get("title", "")
    if any(kw in title for kw in ["常见问题", "帮助中心", "操作指南", "使用手册", "办事指南", "FQA"]):
        return False
    owner = item.get("procurement_owner", "")
    region = item.get("region", "")
    province = item.get("province", "")
    conn.execute(
        """INSERT INTO winning_notices
           (title, url, source_site, source_department, project_name,
            winner_company, winning_amount, publish_date, fetch_date,
            content_summary, relevance_score, procurement_owner, region, province, category, unique_hash)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (item["title"], item.get("url"), item.get("source_site"),
         item.get("source_department"), item.get("project_name"),
         item.get("winner_company"), item.get("winning_amount"),
         item.get("publish_date"), item.get("fetch_date"),
         item.get("content_summary"), score, owner, region, province,
         item.get("category", "⚪ 其他"), h)
    )
    conn.commit()
    return True


# ── Excel 加载 ────────────────────────────────────────

def load_sites_from_excel(excel_path: Path = None) -> list[dict]:
    """从Excel加载网站列表"""
    path = excel_path or EXCEL_PATH
    if not path.exists():
        log(f"Excel文件不存在: {path}")
        return []

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active

    sites = []
    headers = []

    for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
        vals = [str(c).replace(" ", "").strip() if c else "" for c in row]

        # 跳过标题行 (row 0 是合并标题 "中南院投标网站注册信息汇总表")
        if row_idx == 0:
            continue

        # row 1 是表头
        if row_idx == 1:
            headers = vals
            continue

        if not any(vals):
            continue

        # 补齐长度
        while len(vals) < len(headers):
            vals.append("")
        row_dict = dict(zip(headers, vals))

        # 提取URL — 列索引 [2] 是"网址"
        url = ""
        # 先尝试列名
        for col_name in ["网址", "网站地址", "URL", "链接", "网 址"]:
            if col_name in row_dict and row_dict[col_name]:
                val = row_dict[col_name]
                if val.startswith("http"):
                    url = val
                    break
        # 再尝试列索引
        if not url and len(vals) > 2 and vals[2].startswith("http"):
            url = vals[2]
        # 扫描所有值
        if not url:
            for v in vals:
                if v and v.startswith("http"):
                    url = v
                    break

        if not url:
            continue

        # 标准化URL
        if not url.startswith("http"):
            url = "https://" + url

        # 列索引映射:
        # [1]=网站名称, [5]=用户名, [6]=密码, [8]=CA证书, [11]=联系人, [12]=责任部门
        site_name = (vals[1] if len(vals) > 1 and vals[1] and vals[1] not in ("网站名称", "序号") 
                     else row_dict.get("网站名称", urlparse(url).netloc))

        sites.append({
            "site_name": site_name,
            "url": url,
            "platform_type": row_dict.get("平台类型", "") or row_dict.get("网站类型", ""),
            "responsible_dept": vals[12] if len(vals) > 12 and vals[12] else row_dict.get("责任部门", ""),
            "username": vals[5] if len(vals) > 5 and vals[5] else row_dict.get("用户名", ""),
            "password": vals[6] if len(vals) > 6 and vals[6] else row_dict.get("密码", ""),
            "ca_cert": vals[8] if len(vals) > 8 and vals[8] else row_dict.get("CA证书", ""),
            "contact_person": vals[11] if len(vals) > 11 and vals[11] else row_dict.get("联系人", ""),
            "contact_phone": row_dict.get("联系电话", "") or row_dict.get("电话", ""),
            "notes": vals[13] if len(vals) > 13 and vals[13] else row_dict.get("备注", ""),
        })

    # 去重
    seen_urls = set()
    unique = []
    for s in sites:
        base = urlparse(s["url"]).netloc
        if base not in seen_urls:
            seen_urls.add(base)
            unique.append(s)

    return unique


# ── 从数据库加载活跃站点（默认模式） ────────────────────

def load_active_sites(conn=None) -> list[dict]:
    """从 site_list 加载 is_active=1 的站点"""
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT site_name, url, platform_type, responsible_dept, 
               username, password, ca_cert, contact_person, contact_phone, notes
        FROM site_list WHERE is_active=1 ORDER BY id
    """).fetchall()
    sites = []
    for r in rows:
        sites.append({
            "site_name": r["site_name"] or "",
            "url": r["url"] or "",
            "platform_type": r["platform_type"] or "",
            "responsible_dept": r["responsible_dept"] or "",
            "username": r["username"] or "",
            "password": r["password"] or "",
            "ca_cert": r["ca_cert"] or "",
            "contact_person": r["contact_person"] or "",
            "contact_phone": r["contact_phone"] or "",
            "notes": r["notes"] or "",
        })
    if close_conn:
        conn.close()
    return sites


# ── 爬虫核心 ──────────────────────────────────────────

def fetch_page(url: str, timeout: int = TIMEOUT) -> Optional[str]:
    """获取页面HTML"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True,
                           verify=False)
        resp.raise_for_status()
        # 检测编码
        if resp.encoding and resp.encoding.lower() != "utf-8":
            resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.Timeout:
        return None
    except requests.RequestException as e:
        return None


def extract_links_from_html(html: str, base_url: str) -> list[dict]:
    """从HTML中提取可能是招标/中标公告的链接"""
    soup = BeautifulSoup(html, "lxml")
    links = []

    # ── 非公告页面过滤（FAQ、帮助、答疑、指南等）──
    FAQ_PATTERNS = [
        "常见问题", "问题答疑", "帮助中心", "操作指南", "使用手册",
        "办事指南", "下载中心", "通知公告", "新闻动态", "政策法规",
        "联系我们", "关于我们", "网站地图",
    ]
    page_text = soup.get_text()[:500]

    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]

        # 跳过非内容链接
        if not text or len(text) < 4 or len(text) > 200:
            continue

        # 跳过明显的导航链接
        skip_patterns = ["首页", "上一页", "下一页", "尾页", "返回", "登录", "注册",
                        "更多", "查看详情", "点击查看", ">>", "<<"]
        if any(p == text for p in skip_patterns):
            continue

        # 跳过FAQ/帮助类链接
        if any(p in text for p in FAQ_PATTERNS):
            continue

        full_url = urljoin(base_url, href)

        # 判断类型
        link_type = "其他"
        if any(kw in text for kw in BIDDING_KEYWORDS):
            link_type = "招标公告"
        elif any(kw in text for kw in WINNING_KEYWORDS):
            link_type = "中标公告"

        # 提取日期
        date_match = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)', text)
        pub_date = date_match.group(1) if date_match else ""

        links.append({
            "title": text,
            "url": full_url,
            "type": link_type,
            "publish_date": pub_date,
        })

    return links


def crawl_site(site: dict) -> dict:
    """爬取单个网站（使用站点适配器获取公告列表页）"""
    result = {
        "site_name": site["site_name"],
        "url": site["url"],
        "bidding_items": [],
        "winning_items": [],
        "status": "failed",
        "error": None,
    }

    # 使用适配器找到真正的公告列表URL，尝试多页
    list_urls = get_listing_urls(site["url"], max_pages=3)
    if not list_urls:
        list_urls = [site["url"]]
    
    all_links = []
    for list_url in list_urls:
        html = fetch_page(list_url)
        if html:
            links = extract_links_from_html(html, site["url"])
            all_links.extend(links)
    
    # JS渲染回退：如果requests没抓到链接，用Chromium渲染
    if not all_links and list_urls:
        for list_url in list_urls[:1]:  # 只试第一页，省时间
            html = chromium_fetch(list_url, timeout=25)
            if html:
                links = extract_links_from_html(html, site["url"])
                all_links.extend(links)
                if all_links:
                    break
    
    if not all_links:
        html = fetch_page(site["url"])
        if html:
            all_links = extract_links_from_html(html, site["url"])
    
    if not all_links:
        result["error"] = "无公告链接"
        return result

    result["status"] = "success"

    # 分类 + 日期过滤（仅保留近7天）
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    for link in all_links:
        # 日期检查：有日期且超过7天则跳过
        pub_date = link.get("publish_date", "")
        if pub_date:
            # 标准化日期格式
            pub_clean = re.sub(r'[年月]', '-', pub_date).replace('日','').replace('/','-').strip()
            if pub_clean and pub_clean < week_ago:
                continue  # 太旧的跳过
        
        item = {
            "title": link["title"],
            "url": link["url"],
            "source_site": site["site_name"],
            "source_department": site.get("responsible_dept", ""),
            "publish_date": link.get("publish_date", ""),
            "fetch_date": datetime.now().isoformat(),
        }

        if link["type"] == "招标公告":
            result["bidding_items"].append(item)
        elif link["type"] == "中标公告":
            result["winning_items"].append(item)

    return result


# ── 主运行流程 ────────────────────────────────────────

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass


def run_crawl(excel_path: Path = None, max_sites: int = MAX_SITES_PER_RUN, use_db: bool = True):
    """主爬取流程。use_db=True则从site_list(is_active=1)加载，否则从Excel加载。"""
    start_time = time.time()
    today = datetime.now().strftime("%Y-%m-%d")
    log(f"=== 开始投标信息抓取 {today} ===")

    conn = get_db()

    # 1. 加载网站 — 默认从DB加载活跃站点
    if use_db and excel_path is None:
        sites = load_active_sites(conn)
        log(f"从DB加载活跃站点: {len(sites)} 个")
        if not sites:
            log("⚠️ 无活跃站点！回退到Excel加载...")
            sites = load_sites_from_excel(excel_path)
            log(f"从Excel加载: {len(sites)} 个")
    else:
        sites = load_sites_from_excel(excel_path)
        log(f"从Excel加载: {len(sites)} 个")
        # 同步到数据库
        sync_sites_to_db(conn, sites)
        conn.commit()

    if max_sites and len(sites) > max_sites:
        # 轮转：根据日期选择不同的网站段
        day_of_year = datetime.now().timetuple().tm_yday
        start_idx = (day_of_year * max_sites) % len(sites)
        segment = sites[start_idx:start_idx + max_sites]
        if len(segment) < max_sites:
            segment += sites[:max_sites - len(segment)]
        sites = segment
        log(f"本轮爬取: {len(sites)} 个 (第{start_idx+1}个起)")

    # 2. 爬取
    total_bidding = 0
    total_winning = 0
    success_count = 0
    fail_count = 0
    errors = []

    for i, site in enumerate(sites):
        site_name = site['site_name'][:40]
        log(f"[{i+1}/{len(sites)}] {site_name}...")
        try:
            result = crawl_site(site)
            if result["status"] == "success":
                success_count += 1
                # 更新站点最后成功时间
                conn.execute(
                    "UPDATE site_list SET last_crawl_time=?, last_status='ok' WHERE url=?",
                    (datetime.now().isoformat(), site.get('url', ''))
                )
            else:
                fail_count += 1
                err_msg = f"{site_name}: {result.get('error', 'unknown')}"
                errors.append(err_msg)
                log(f"  ❌ {err_msg}")
                conn.execute(
                    "UPDATE site_list SET last_status=? WHERE url=?",
                    (result.get('error', 'failed')[:200], site.get('url', ''))
                )

            # 业务相关性评分 + 过滤
            scored_bidding = score_items(result["bidding_items"])
            scored_winning = score_items(result["winning_items"])

            # 入库（只存相关的）
            for item in scored_bidding:
                if save_bidding(conn, item):
                    total_bidding += 1

            for item in scored_winning:
                # 高相关中标→进入详情页提取招标人/中标人/金额
                if item.get('relevance_score', 0) >= 4 and item.get('url'):
                    try:
                        detail_html = fetch_page(item['url'], timeout=15)
                        if detail_html:
                            detail_fields = extract_detail_fields(detail_html)
                            for k, v in detail_fields.items():
                                if v:
                                    item[k] = v
                    except:
                        pass
                if save_winning(conn, item):
                    total_winning += 1

        except Exception as e:
            fail_count += 1
            err_msg = f"{site_name}: {str(e)[:100]}"
            errors.append(err_msg)
            log(f"  ❌ 异常: {err_msg}")
            conn.execute(
                "UPDATE site_list SET last_status=? WHERE url=?",
                (f"exception: {str(e)[:200]}", site.get('url', ''))
            )

        # 礼貌延迟
        time.sleep(0.5)

    conn.commit()

    # 3. 记录抓取日志
    duration = round(time.time() - start_time, 1)
    error_text = "\n".join(errors[:100]) if errors else ""
    conn.execute(
        """INSERT INTO crawl_log (total_sites, success_sites, failed_sites,
           new_bidding, new_winning, duration_seconds, errors)
           VALUES (?,?,?,?,?,?,?)""",
        (len(sites), success_count, fail_count, total_bidding, total_winning,
         duration, error_text)
    )
    conn.commit()

    # 验证crawl_log写入
    log_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    log(f"📋 crawl_log id={log_id}: {success_count}成功/{fail_count}失败, "
         f"新招标{total_bidding}, 新中标{total_winning}, 耗时{duration}s")

    # 4. 长记忆：保存本次扫描的关键观察
    try:
        from memory_engine import add_memory, init_db as mem_init
        mem_init()
        # 高相关项目入记忆
        for item in scored_bidding[:3]:  # TOP3 高相关招标
            if item.get('relevance_score', 0) >= 4:
                add_memory(
                    f"招标: {item.get('title','')[:80]} | 客户: {item.get('client_category','未知')} | 评分: {item.get('relevance_score',0):.1f}",
                    category='招标', tags='高相关,招标',
                    importance=min(item.get('relevance_score', 4)/3, 3.0),
                    source='scan', ref_id=f"bid_{item.get('url','')[:50]}"
                )
        # 扫描摘要
        if total_bidding + total_winning > 0:
            add_memory(
                f"扫描摘要 {datetime.now():%Y-%m-%d}: {success_count}/{len(sites)}站点成功, "
                f"新招标{total_bidding}条, 新中标{total_winning}条, 高相关{sum(1 for b in scored_bidding if b.get('relevance_score',0)>=4)}条",
                category='扫描', tags='摘要,扫描',
                importance=1.0,
                source='scan', ref_id=f"summary_{datetime.now():%Y-%m-%d}"
            )
        # 异常站点记忆
        for err in errors[:5]:
            add_memory(f"站点异常: {err[:120]}", category='异常', tags='站点,异常', importance=0.5,
                       source='scan', ref_id=f"err_{err[:30]}")
    except Exception as e:
        log(f"⚠️ 记忆写入失败: {e}")

    conn.close()

    log(f"=== 抓取结束: {success_count}成功 {fail_count}失败 | "
         f"新招标 {total_bidding} | 新中标 {total_winning} | 耗时 {duration}s | 日志#{log_id} ===")

    return {
        "total_sites": len(sites),
        "success": success_count,
        "failed": fail_count,
        "new_bidding": total_bidding,
        "new_winning": total_winning,
        "duration": duration,
        "crawl_log_id": log_id,
    }


def sync_sites_to_db(conn, sites: list[dict]):
    """同步网站列表到数据库"""
    for s in sites:
        conn.execute(
            """INSERT OR REPLACE INTO site_list 
               (site_name, url, platform_type, responsible_dept, username, password,
                ca_cert, contact_person, contact_phone, notes, last_crawl_time)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (s["site_name"], s["url"], s.get("platform_type"), s.get("responsible_dept"),
             s.get("username"), s.get("password"), s.get("ca_cert"),
             s.get("contact_person"), s.get("contact_phone"), s.get("notes"),
             datetime.now().isoformat())
        )
    conn.commit()


# ── HTML 报告 ─────────────────────────────────────────

def row_to_dict(row) -> dict:
    """sqlite3.Row → dict"""
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    return {k: row[k] for k in row.keys()}


def generate_html_report() -> Path:
    """生成HTML报告"""
    conn = get_db()

    # 获取今日新增 — 按相关性降序
    today = datetime.now().strftime("%Y-%m-%d")
    bidding_rows_raw = conn.execute(
        "SELECT * FROM bidding_notices WHERE date(fetch_date)=? AND relevance_score > 0 ORDER BY relevance_score DESC LIMIT 200",
        (today,)
    ).fetchall()
    bidding = [row_to_dict(r) for r in bidding_rows_raw]

    winning_rows_raw = conn.execute(
        "SELECT * FROM winning_notices WHERE date(fetch_date)=? AND relevance_score > 0 ORDER BY relevance_score DESC LIMIT 200",
        (today,)
    ).fetchall()
    winning = [row_to_dict(r) for r in winning_rows_raw]

    # 统计
    total_bidding = conn.execute("SELECT COUNT(*) FROM bidding_notices").fetchone()[0]
    total_winning = conn.execute("SELECT COUNT(*) FROM winning_notices").fetchone()[0]
    recent_bidding = conn.execute(
        "SELECT COUNT(*) FROM bidding_notices WHERE date(fetch_date)>=date('now','-7 days')"
    ).fetchone()[0]
    recent_winning = conn.execute(
        "SELECT COUNT(*) FROM winning_notices WHERE date(fetch_date)>=date('now','-7 days')"
    ).fetchone()[0]

    # 最近一次爬取
    last_crawl_raw = conn.execute(
        "SELECT * FROM crawl_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    last_crawl = row_to_dict(last_crawl_raw)

    # 按来源统计
    source_stats_raw = conn.execute(
        """SELECT source_site, COUNT(*) as cnt 
           FROM bidding_notices 
           WHERE date(fetch_date)=date('now')
           GROUP BY source_site ORDER BY cnt DESC LIMIT 20"""
    ).fetchall()
    source_stats = [row_to_dict(r) for r in source_stats_raw]

    conn.close()

    # ── 生成HTML ──
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    bidding_rows = ""
    for b in bidding:
        score = b.get('relevance_score', 0)
        score_badge = f"{score:.1f}" if score >= 7 else f"{score:.1f}"
        score_color = "#10b981" if score >= 7 else ("#f59e0b" if score >= 4 else "#6b7280")
        row_class = ' class="new-row"' if b["is_new"] else ""
        bidding_rows += f"""<tr{row_class}>
            <td style="color:{score_color};font-weight:600">{score_badge}</td>
            <td>{safe_str(b.get('title'), 55)}</td>
            <td>{safe_str(b.get('source_site'), 18)}</td>
            <td>{safe_str(b.get('source_department'), 10)}</td>
            <td>{safe_str(b.get('publish_date'), 10)}</td>
            <td><a href="{safe_str(b.get('url'), 500) or '#'}" target="_blank">查看</a></td>
        </tr>"""

    winning_rows = ""
    for w in winning:
        score = w.get('relevance_score', 0)
        score_badge = f"{score:.1f}"
        score_color = "#10b981" if score >= 7 else ("#f59e0b" if score >= 4 else "#6b7280")
        row_class = ' class="new-row"' if w["is_new"] else ""
        winning_rows += f"""<tr{row_class}>
            <td style="color:{score_color};font-weight:600">{score_badge}</td>
            <td>{safe_str(w.get('title'), 55)}</td>
            <td>{safe_str(w.get('source_site'), 18)}</td>
            <td>{safe_str(w.get('winner_company'), 22)}</td>
            <td>{safe_str(w.get('winning_amount'), 12)}</td>
            <td>{safe_str(w.get('publish_date'), 10)}</td>
            <td><a href="{safe_str(w.get('url'), 500) or '#'}" target="_blank">查看</a></td>
        </tr>"""

    stats_rows = ""
    for s in source_stats:
        stats_rows += f"""<tr>
            <td>{safe_str(s.get('source_site'), 40)}</td>
            <td>{s['cnt']}</td>
        </tr>"""

    last_crawl_info = ""
    if last_crawl:
        last_crawl_info = f"""
        <div class="crawl-info">
            <span>最近抓取: {safe_str(last_crawl.get('crawl_time'), 19)}</span>
            <span>成功 {last_crawl.get('success_sites',0)}/{last_crawl.get('total_sites',0)}</span>
            <span>新招标 +{last_crawl.get('new_bidding',0)}</span>
            <span>新中标 +{last_crawl.get('new_winning',0)}</span>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="300">
<title>文鳐智投 · 投标信息监控</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #e2e8f0; min-height:100vh; }}
header {{ background: linear-gradient(135deg, #1e293b, #0f172a); border-bottom: 2px solid #3b82f6; padding: 20px 32px; }}
header h1 {{ font-size: 28px; color: #60a5fa; }}
header .subtitle {{ color: #94a3b8; font-size: 14px; margin-top: 4px; }}
.crawl-info {{ display:flex; gap: 20px; margin-top: 12px; font-size: 13px; color: #94a3b8; }}
.container {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}
.stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
.stat-card {{ background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; }}
.stat-card .value {{ font-size: 32px; font-weight: 700; color: #60a5fa; }}
.stat-card .label {{ font-size: 13px; color: #94a3b8; margin-top: 4px; }}
.stat-card.highlight .value {{ color: #f59e0b; }}
.section {{ margin-bottom: 32px; }}
.section h2 {{ font-size: 20px; color: #e2e8f0; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #334155; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th {{ background: #1e293b; padding: 12px 16px; text-align: left; font-weight: 600; color: #94a3b8; border-bottom: 2px solid #334155; }}
td {{ padding: 10px 16px; border-bottom: 1px solid #1e293b; }}
tr:hover {{ background: #1e293b; }}
.new-row {{ background: rgba(59,130,246,0.08); }}
.new-row td:first-child::before {{ content: "🆕 "; }}
a {{ color: #60a5fa; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
footer {{ text-align: center; padding: 24px; color: #475569; font-size: 12px; }}
.tabs {{ display: flex; gap: 8px; margin-bottom: 16px; }}
.tab {{ padding: 8px 20px; border-radius: 8px; cursor: pointer; background: #1e293b; border: 1px solid #334155; color: #94a3b8; }}
.tab.active {{ background: #3b82f6; color: white; border-color: #3b82f6; }}
.empty {{ text-align: center; padding: 40px; color: #475569; }}
@media (max-width: 768px) {{ .stats-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
</style>
</head>
<body>
<header>
    <h1>📡 文鳐智投 · 投标信息监控系统</h1>
    <div class="subtitle">中南电力设计院 · 全品类招标+中标 · 更新于 {now_str}</div>
    {last_crawl_info}
</header>
<div class="container">
    <div class="stats-grid">
        <div class="stat-card">
            <div class="value">{total_bidding}</div>
            <div class="label">累计招标公告</div>
        </div>
        <div class="stat-card highlight">
            <div class="value">{total_winning}</div>
            <div class="label">累计中标公告</div>
        </div>
        <div class="stat-card">
            <div class="value">{recent_bidding}</div>
            <div class="label">近7日新增招标</div>
        </div>
        <div class="stat-card highlight">
            <div class="value">{recent_winning}</div>
            <div class="label">近7日新增中标</div>
        </div>
    </div>

    <div class="section">
        <h2>📋 今日招标公告 ({len(bidding)}条 · 仅展示业务相关)</h2>
        {f'<table><thead><tr><th>相关</th><th>标题</th><th>来源</th><th>部门</th><th>日期</th><th>链接</th></tr></thead><tbody>{bidding_rows}</tbody></table>' if bidding else '<div class="empty">今日暂无非业务相关招标公告</div>'}
    </div>

    <div class="section">
        <h2>🏆 今日中标公告 ({len(winning)}条 · 仅展示业务相关)</h2>
        {f'<table><thead><tr><th>相关</th><th>标题</th><th>来源</th><th>中标单位</th><th>金额</th><th>日期</th><th>链接</th></tr></thead><tbody>{winning_rows}</tbody></table>' if winning else '<div class="empty">今日暂无非业务相关中标公告</div>'}
    </div>

    <div class="section">
        <h2>📊 今日各来源招标分布</h2>
        {f'<table><thead><tr><th>来源网站</th><th>数量</th></tr></thead><tbody>{stats_rows}</tbody></table>' if stats_rows else '<div class="empty">暂无数据</div>'}
    </div>
</div>
<footer>© 中南电力设计院数智科技 · 文鳐智投 2026</footer>
</body>
</html>"""

    # 写入文件
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    index_path = REPORT_DIR / "index.html"
    index_path.write_text(html, encoding="utf-8")

    log(f"HTML报告已生成: {index_path}")
    # 同时导出数据JSON供前端交互
    export_data_json()
    return index_path


def escape_html(text) -> str:
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def safe_str(val, max_len=None) -> str:
    """安全转字符串，可截断"""
    s = escape_html(val)
    if max_len and len(s) > max_len:
        return s[:max_len]
    return s


# ── CLI ──────────────────────────────────────────────

def export_data_json():
    """导出数据JSON供前端交互式报告使用"""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    bidding = [dict(r) for r in conn.execute(
        "SELECT id,title,url,source_site,source_department,publish_date,relevance_score FROM bidding_notices WHERE relevance_score>0 ORDER BY relevance_score DESC LIMIT 2000"
    ).fetchall()]
    winning = [dict(r) for r in conn.execute(
        "SELECT id,title,url,source_site,source_department,winner_company,winning_amount,publish_date,relevance_score FROM winning_notices WHERE relevance_score>0 ORDER BY relevance_score DESC LIMIT 1000"
    ).fetchall()]
    sources = conn.execute("SELECT source_site, COUNT(*) as cnt FROM bidding_notices WHERE relevance_score>0 GROUP BY source_site ORDER BY cnt DESC LIMIT 30").fetchall()
    departments = conn.execute("SELECT source_department, COUNT(*) as cnt FROM bidding_notices WHERE relevance_score>0 AND source_department!='' GROUP BY source_department ORDER BY cnt DESC").fetchall()
    data = {"bidding":bidding,"winning":winning,"sources":[dict(r) for r in sources],"departments":[dict(r) for r in departments]}
    import json as _json
    json_path = REPORT_DIR / "data.json"
    json_path.write_text(_json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")
    conn.close()
    log(f"数据JSON已导出: {json_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="文鳐智投 投标抓取引擎")
    parser.add_argument("action", nargs="?", default="full",
                       choices=["full", "crawl", "report", "export-data", "stats", "sync-sites", "list-sites", "activate-sites"],
                       help="full=爬取+报告, crawl=仅爬取, report=仅报告, stats=统计, list-sites=列出活跃站点, activate-sites=从Excel导入并标记部门")
    parser.add_argument("--max-sites", type=int, default=MAX_SITES_PER_RUN)
    parser.add_argument("--excel", type=str, default=None)
    parser.add_argument("--excel-mode", action="store_true", help="强制从Excel加载（而非DB）")
    args = parser.parse_args()

    # 禁用SSL警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    excel_path = Path(args.excel) if args.excel else None

    if args.action in ("full", "crawl"):
        use_db = not args.excel_mode
        result = run_crawl(excel_path=excel_path, max_sites=args.max_sites, use_db=use_db)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.action in ("full", "report"):
        import subprocess
        subprocess.run([sys.executable, str(Path(__file__).parent / "report_generator.py")], check=False)
        print(f"报告: /var/www/html/bidding/index.html")

    if args.action == "stats":
        conn = get_db()
        bidding_count = conn.execute("SELECT COUNT(*) FROM bidding_notices").fetchone()[0]
        winning_count = conn.execute("SELECT COUNT(*) FROM winning_notices").fetchone()[0]
        crawl_count = conn.execute("SELECT COUNT(*) FROM crawl_log").fetchone()[0]
        last_crawl = conn.execute("SELECT crawl_time, total_sites, success_sites, failed_sites, new_bidding, new_winning, duration_seconds FROM crawl_log ORDER BY id DESC LIMIT 1").fetchone()
        active_sites = conn.execute("SELECT COUNT(*) FROM site_list WHERE is_active=1").fetchone()[0]
        conn.close()
        print(f"招标公告: {bidding_count} | 中标公告: {winning_count}")
        print(f"抓取日志: {crawl_count}条 | 活跃站点: {active_sites}个")
        if last_crawl:
            print(f"最近抓取: {last_crawl['crawl_time']} | {last_crawl['success_sites']}/{last_crawl['total_sites']}成功 | 新招标{last_crawl['new_bidding']} 新中标{last_crawl['new_winning']} | {last_crawl['duration_seconds']}s")

    if args.action == "export-data":
        export_data_json()
        print(f"数据已导出到 {REPORT_DIR / 'data.json'}")

    if args.action == "sync-sites":
        sites = load_sites_from_excel(excel_path)
        conn = get_db()
        sync_sites_to_db(conn, sites)
        conn.commit()
        conn.close()
        print(f"已同步 {len(sites)} 个网站到数据库")

    if args.action == "list-sites":
        conn = get_db()
        rows = conn.execute("SELECT site_name, url, responsible_dept, last_crawl_time, last_status FROM site_list WHERE is_active=1 ORDER BY responsible_dept, site_name").fetchall()
        conn.close()
        for r in rows:
            status = r['last_status'] or '未爬取'
            print(f"  [{r['responsible_dept']:6s}] {r['site_name'][:35]:35s} | {status}")

    if args.action == "activate-sites":
        """批量激活站点：从Excel加载→入库并标记active(仅数智/智能/智能公司部门)"""
        sites = load_sites_from_excel(excel_path)
        conn = get_db()
        for s in sites:
            is_active = 1 if s.get("responsible_dept", "") in ("数智", "智能", "智能公司") else 0
            conn.execute(
                """INSERT OR REPLACE INTO site_list 
                   (site_name, url, platform_type, responsible_dept, username, password,
                    ca_cert, contact_person, contact_phone, notes, is_active)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (s["site_name"], s["url"], s.get("platform_type"), s.get("responsible_dept"),
                 s.get("username"), s.get("password"), s.get("ca_cert"),
                 s.get("contact_person"), s.get("contact_phone"), s.get("notes"), is_active)
            )
        conn.commit()
        active = conn.execute("SELECT COUNT(*) FROM site_list WHERE is_active=1").fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM site_list").fetchone()[0]
        conn.close()
        print(f"站点导入完成: 总计{total}个, 活跃{active}个")


if __name__ == "__main__":
    main()
