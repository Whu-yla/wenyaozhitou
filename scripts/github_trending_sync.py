#!/usr/bin/env python3
"""
文鳐智投 GitHub Trending 真实同步脚本
==========================================
数据源：
  - 主：GitHub REST API (Search/repositories) 按 weekly 增长排序
  - 备：gh-trending-api（第三方解析 trending 页面）

功能：
  1. 拉取 weekly trending 热门仓库
  2. 对每个 Repo 做能源场景匹配 (复用 tech_matcher.match_github_to_energy)
  3. 写入 DB github_energy 表
  4. 提供 cron 模式: 每周一 04:00 自动执行 (配合操作系统 cron)
"""
import os
import re
import sys
import json
import time
import sqlite3
import logging
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import requests

# ── 配置 ────────────────────────────────────────────────────
BASE_DIR = Path("/root/.hermes/profiles/wenyaozhitou")
DB = BASE_DIR / "data" / "bidding.db"

# GitHub Token (可选，匿名 60 次/小时，认证 5000 次/小时)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
# gh-trending-api 地址 (第三方)
GH_TRENDING_API = os.getenv("GH_TRENDING_API", "https://gh-trending-api.herokuapp.com")

# 搜索关键词组合 — 飙升榜策略：聚焦近 3 个月内创建的新项目 + 低 stars 门槛 + stars 上限
# 目标：发现"刚冒头"的新技术，而非已成熟的老牌框架（排除 stars>5000 的成熟项目）
# 匿名 API 限流 60req/h，共 9 条查询，每条 per_page=30
SEARCH_TOPICS = [
    # ── 飙升榜：近 3 个月创建、已有一定 stars 但还没爆火的新项目 ──
    # 注意：GitHub Search API 不支持 "stars:>N stars:<M" 两个并列限定符（上界会被忽略），
    # 必须用 range 语法 "stars:N..M" 才能正确限定区间。
    # AI/大模型/Agent 新星（20~5000 stars，刚冒头的）
    ("(llm OR rag OR agent OR vllm OR mcp) stars:20..5000 created:>2026-05-01", "weekly"),
    # AI 视觉/识别 新星
    ("(yolo OR ocr OR detection OR segmentation OR \"vision-language\") stars:15..5000 created:>2026-05-01", "weekly"),
    # IoT/边缘计算/工业 新星
    ("(iot OR mqtt OR \"edge-ai\" OR \"industrial-iot\" OR opcua) stars:10..3000 created:>2026-05-01", "weekly"),
    # 数据库/时序/大数据 新星
    ("(database OR olap OR timeseries OR \"data-lake\" OR vector-db) stars:15..5000 created:>2026-05-01", "weekly"),
    # 3D/可视化/数字孪生/GIS 新星
    ("(visualization OR \"3d\" OR gis OR \"digital-twin\" OR threejs) stars:15..5000 created:>2026-05-01", "weekly"),
    # 安全/零信任/工控安全 新星
    ("(security OR \"zero-trust\" OR siem OR ics OR scada) stars:10..3000 created:>2026-05-01", "weekly"),
    # 能源/电力/光伏/风电 预测 新星
    ("(energy OR solar OR wind OR power-grid OR forecasting) stars:8..3000 created:>2026-05-01", "weekly"),
    # ── 飙升榜补充：近 6 个月创建、stars 50~5000 的成长期项目 ──
    ("(ai OR llm OR agent) stars:50..5000 created:>2026-02-01", "weekly"),
    # ── 近期活跃：近 1 周 push、stars 100~5000、created 近 1 年 ──
    ("(llm OR rag OR agent OR iot OR visualization) stars:100..5000 pushed:>2026-08-03 created:>2025-08-01", "weekly"),
]

LANG_WEIGHT = {"Python": 1.2, "TypeScript": 1.1, "JavaScript": 1.0,
               "Go": 1.15, "Rust": 1.2, "Java": 1.05, "C++": 1.0, "C": 0.95}

# ── logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("gh_trending")

# ── 让 tech_matcher 可被 import ────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))

# ═══════════════════════════════════════════════════════════════
# 数据源 A：GitHub 官方 Search API
# ═══════════════════════════════════════════════════════════════

def gh_search(session: requests.Session, query: str = "",
              sort: str = "stars", order: str = "desc",
              created: str = None, per_page: int = 20,
              page: int = 1) -> List[Dict]:
    """
    GitHub Search API (官方, 更稳定)
    默认按 stars 排序，筛选条件可加 created:>YYYY-MM-DD
    """
    params = {"q": query or "stars:>500", "sort": sort,
              "order": order, "per_page": per_page, "page": page}
    if created:
        params["q"] += f" created:>{created}"
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    try:
        r = session.get("https://api.github.com/search/repositories",
                       params=params, headers=headers, timeout=30)
        if r.status_code == 200:
            items = r.json().get("items", [])
            log.info(f"Search [{query[:30]}…] 返回 {len(items)} 条")
            return items
        elif r.status_code == 403:
            log.warning(f"GitHub API 限流 (403): {r.text[:100]}")
            return []
        else:
            log.warning(f"Search API HTTP {r.status_code}: {r.text[:120]}")
            return []
    except Exception as e:
        log.error(f"Search 请求异常: {e}")
        return []

def gh_single_repo(session: requests.Session, full_name: str) -> Optional[Dict]:
    """查询单个 repo 的详细信息（topics、description、star数等）"""
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    try:
        r = session.get(f"https://api.github.com/repos/{full_name}",
                       headers=headers, timeout=20)
        if r.status_code == 200:
            return r.json()
        log.warning(f"repo {full_name}: HTTP {r.status_code}")
    except Exception as e:
        log.error(f"repo 请求异常 {full_name}: {e}")
    return None

# ═══════════════════════════════════════════════════════════════
# 数据源 B：第三方 gh-trending-api（解析 trending 页面）
# ═══════════════════════════════════════════════════════════════

def gh_trending_page(session: requests.Session, since: str = "weekly",
                     language: str = "") -> List[Dict]:
    """
    调 gh-trending-api 拿官网 trending 页面的实时结果
    since: daily / weekly / monthly
    """
    url = f"{GH_TRENDING_API}/repositories"
    params = {"since": since}
    if language:
        params["language"] = language
    try:
        r = session.get(url, params=params, timeout=30)
        if r.status_code == 200:
            items = r.json() or []
            log.info(f"gh-trending [{since}] 返回 {len(items)} 条")
            return items
        log.warning(f"gh-trending-api HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        log.error(f"gh-trending 请求异常: {e}")
    return []

# ═══════════════════════════════════════════════════════════════
# 去重 & 合并 & 评分
# ═══════════════════════════════════════════════════════════════

def extract_repo_week_growth(gh_item: Dict, session: requests.Session) -> int:
    """
    估算每周新增 Stars：gh-trending-api 有 currentPeriodStars，
    官方 API 没有，则按 stars/age_weeks 粗略估算（保守方案）
    """
    if "currentPeriodStars" in gh_item:
        return int(gh_item["currentPeriodStars"] or 0)
    stars = gh_item.get("stargazers_count", 0)
    created = gh_item.get("created_at")
    if not created:
        return stars // 100
    try:
        cd = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=None)
        weeks = max(1, (datetime.utcnow() - cd).days // 7)
        # 取每周平均，再乘一个波动系数 1.5-2.0 (热门榜假设比平均高)
        return int(stars / weeks * 1.5)
    except Exception:
        return stars // 100

def normalize_repo(item: Dict, source: str, session: requests.Session) -> Optional[Dict]:
    """
    把两种来源的数据统一格式
    """
    # gh-trending-api 的字段结构
    if source == "trending_page":
        full_name = f"{item.get('author','')}/{item.get('name','')}".strip("/")
        if not full_name or full_name == "/":
            return None
        return {
            "full_name": full_name,
            "description": (item.get("description") or "")[:500],
            "language": item.get("language") or "",
            "stars": int(item.get("stars") or 0),
            "week_growth": int(item.get("currentPeriodStars") or 0),
            "topics": [],  # trending api 没有 topics，需二次查询
            "url": f"https://github.com/{full_name}",
            "forks": int(item.get("forks") or 0),
            "_raw": item,
        }
    # 官方 search api 的字段
    full_name = item.get("full_name")
    if not full_name:
        return None
    return {
        "full_name": full_name,
        "description": (item.get("description") or "")[:500],
        "language": item.get("language") or "",
        "stars": int(item.get("stargazers_count") or 0),
        "week_growth": extract_repo_week_growth(item, session),
        "topics": list(item.get("topics") or []) or [],
        "url": item.get("html_url") or f"https://github.com/{full_name}",
        "forks": int(item.get("forks_count") or 0),
        "_raw": item,
    }

def compute_tech_heat_score(nrepo: Dict) -> float:
    """
    飙升榜热度分：偏重「增长比」(week_growth/stars) 而非绝对 stars
    → 新项目 100 stars 但周增 30 → 增长比 30%，得分远高于老项目 100k stars 周增 100
    """
    stars = nrepo.get("stars", 0)
    growth = nrepo.get("week_growth", 0)
    lang = (nrepo.get("language") or "")
    lang_k = LANG_WEIGHT.get(lang, 1.0)
    topics = nrepo.get("topics") or []
    topic_bonus = 0
    for hot_t in ["llm", "ai", "rag", "agent", "yolo", "mqtt", "iot",
                  "bim", "digital-twin", "gis", "3d", "database",
                  "visualization", "security", "timeseries",
                  "vllm", "mcp", "edge-ai", "vector-db", "opcua", "scada"]:
        if any(hot_t in t.lower() for t in topics):
            topic_bonus += 200
    import math
    # 增长比（核心指标）：周增长占总 stars 的比例，越高说明越"飙升"
    growth_ratio = (growth / max(stars, 1)) * 100  # 百分比
    # 增长比权重最高（飙升榜核心），绝对 stars 对数缩放做辅助
    ratio_val = math.log1p(max(0, growth_ratio)) * 120
    growth_val = math.log1p(max(0, growth)) * 80
    stars_val = math.log1p(max(0, stars)) * 15  # 降权：老牌大项目不再霸榜
    return (ratio_val + growth_val + stars_val + topic_bonus) * lang_k

# ═══════════════════════════════════════════════════════════════
# 能源匹配 + 入DB
# ═══════════════════════════════════════════════════════════════

def ensure_db():
    conn = sqlite3.connect(str(DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS github_energy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_name TEXT UNIQUE,
            description TEXT,
            language TEXT,
            stars INTEGER DEFAULT 0,
            week_growth INTEGER DEFAULT 0,
            topics_json TEXT,
            matched_scenes_json TEXT,
            top_scene TEXT,
            confidence REAL,
            why_it_matters TEXT,
            url TEXT,
            heat_score REAL DEFAULT 0,
            fetch_source TEXT,
            fetch_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # ── 迁移：老表新增列 ──
    for col, dtype in [
        ("heat_score", "REAL DEFAULT 0"),
        ("fetch_source", "TEXT"),
        ("fetch_date", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE github_energy ADD COLUMN {col} {dtype}")
        except sqlite3.OperationalError:
            pass  # 列已存在，忽略
    conn.commit()
    return conn

def sync_to_db(repo_list: List[Dict]):
    """
    repo_list: 已经 normalize 好的 repo 数组
    对每个 repo:
      1. 能源场景匹配 match_github_to_energy
      2. INSERT OR REPLACE 进 DB
    """
    from tech_matcher import match_github_to_energy
    conn = ensure_db()
    added = updated = skipped = 0
    fetch_date = datetime.now().strftime("%Y-%m-%d")
    for nrepo in repo_list:
        try:
            energy_result = match_github_to_energy(
                nrepo["full_name"],
                nrepo["description"],
                nrepo["language"],
                nrepo.get("topics") or [],
                nrepo.get("topics") or [],
            )
            heat = compute_tech_heat_score(nrepo)
            cursor = conn.execute(
                "SELECT id, stars, week_growth FROM github_energy WHERE repo_name=?",
                (nrepo["full_name"],)
            )
            exists = cursor.fetchone()
            if exists:
                updated += 1
                conn.execute("""
                    UPDATE github_energy SET
                      description=?, language=?, stars=?, week_growth=?,
                      topics_json=?, matched_scenes_json=?, top_scene=?,
                      confidence=?, why_it_matters=?, url=?, heat_score=?,
                      fetch_source=?, fetch_date=?, updated_at=CURRENT_TIMESTAMP
                    WHERE repo_name=?
                """, (
                    nrepo["description"][:500],
                    nrepo["language"],
                    nrepo["stars"],
                    nrepo["week_growth"],
                    json.dumps(nrepo.get("topics") or [], ensure_ascii=False),
                    json.dumps(energy_result["matched_scenes"], ensure_ascii=False),
                    energy_result["top_scene"],
                    energy_result["confidence"],
                    energy_result["why_it_matters"],
                    nrepo["url"],
                    heat,
                    nrepo.get("_source",""),
                    fetch_date,
                    nrepo["full_name"],
                ))
            else:
                added += 1
                conn.execute("""
                    INSERT INTO github_energy
                    (repo_name, description, language, stars, week_growth,
                     topics_json, matched_scenes_json, top_scene,
                     confidence, why_it_matters, url, heat_score,
                     fetch_source, fetch_date)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    nrepo["full_name"],
                    nrepo["description"][:500],
                    nrepo["language"],
                    nrepo["stars"],
                    nrepo["week_growth"],
                    json.dumps(nrepo.get("topics") or [], ensure_ascii=False),
                    json.dumps(energy_result["matched_scenes"], ensure_ascii=False),
                    energy_result["top_scene"],
                    energy_result["confidence"],
                    energy_result["why_it_matters"],
                    nrepo["url"],
                    heat,
                    nrepo.get("_source",""),
                    fetch_date,
                ))
        except Exception as e:
            skipped += 1
            log.warning(f"  ⚠️ DB写失败 {nrepo.get('full_name')}: {e}")
    conn.commit()
    conn.close()
    log.info(f"✅ DB同步完成: 新增={added} 更新={updated} 失败={skipped}")
    return {"added": added, "updated": updated, "skipped": skipped}

# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def fetch_trending_weekly(max_per_source: int = 25,
                          use_search: bool = True,
                          use_trending_page: bool = True) -> List[Dict]:
    """
    从多个数据源拉 weekly trending，统一格式，去重合并
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "wenyao-zhitou/github-trending-sync/1.0 "
                      "(+https://github.com/Whu-yla/wenyaozhitou)"
    })

    all_repos: Dict[str, Dict] = {}
    week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

    # ── A. GitHub Official Search API ──
    if use_search:
        log.info("📡 [数据源 A] GitHub Search API")
        for topic_q, _ in SEARCH_TOPICS:
            q = topic_q  # 每条 query 已自带 stars 条件，直接使用
            items = gh_search(session, query=q, sort="stars",
                              created=None, per_page=max_per_source)
            for it in items:
                norm = normalize_repo(it, "search_api", session)
                if norm:
                    norm["_source"] = "github_search_api"
                    key = norm["full_name"].lower()
                    if key not in all_repos or \
                       norm["week_growth"] > all_repos[key]["week_growth"]:
                        all_repos[key] = norm
            # 官方 API rate limit 60 req/h（匿名），稍作间隔
            time.sleep(1.5)

    # ── B. gh-trending-api (第三方解析真实 trending 页) ──
    if use_trending_page:
        log.info("📡 [数据源 B] gh-trending-api (trending页面解析)")
        for lang in ["", "python", "typescript", "javascript", "go", "rust",
                     "java", "cpp"]:
            tp_items = gh_trending_page(session, since="weekly", language=lang)
            for it in tp_items:
                norm = normalize_repo(it, "trending_page", session)
                if norm:
                    norm["_source"] = "gh_trending_page"
                    key = norm["full_name"].lower()
                    if key not in all_repos or \
                       norm["week_growth"] > all_repos[key]["week_growth"]:
                        all_repos[key] = norm
            time.sleep(0.5)

    # 按热度分排序
    ranked = sorted(all_repos.values(), key=compute_tech_heat_score, reverse=True)
    log.info(f"🎯 合并完成: 共 {len(ranked)} 个独立 Repo")
    return ranked

def fill_topics_for_missing(session: requests.Session, repos: List[Dict]) -> None:
    """
    从 trending page 来的 repo 没有 topics，二次调官方 API 补 topics
    只补前 TOP-N 条，避免触发限流
    """
    for idx, r in enumerate(repos):
        if r.get("topics"):
            continue
        if idx >= 30:  # 限流保护，最多补前 30 条
            break
        full = r["full_name"]
        detail = gh_single_repo(session, full)
        if detail and detail.get("topics"):
            r["topics"] = list(detail["topics"])
            r["stars"] = detail.get("stargazers_count", r["stars"])
            r["language"] = detail.get("language") or r["language"]
            r["description"] = detail.get("description") or r["description"]
            log.info(f"  ✔ 补全 topics: {full} ({len(r['topics'])} topics)")
            time.sleep(0.6)

def re_match_all_energy():
    """
    对 DB 中全部已有 Repo 重新跑能源匹配（场景匹配库更新后使用）
    """
    from tech_matcher import match_github_to_energy
    conn = ensure_db()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM github_energy").fetchall()
    updated = 0
    for r in rows:
        try:
            topics = json.loads(r["topics_json"] or "[]")
            result = match_github_to_energy(
                r["repo_name"], r["description"] or "", r["language"] or "",
                topics, topics
            )
            conn.execute("""
                UPDATE github_energy SET
                  matched_scenes_json=?, top_scene=?,
                  confidence=?, why_it_matters=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (
                json.dumps(result["matched_scenes"], ensure_ascii=False),
                result["top_scene"],
                result["confidence"],
                result["why_it_matters"],
                r["id"]
            ))
            updated += 1
        except Exception as e:
            log.warning(f"  ⚠️ 重匹配失败 #{r['id']}: {e}")
    conn.commit()
    conn.close()
    log.info(f"✅ 能源场景重匹配完成: {updated} 条")

def cli():
    parser = argparse.ArgumentParser(description="文鳐智投 GitHub Trending 同步")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sync = sub.add_parser("sync", help="从真实 API 拉 weekly trending 并匹配入库")
    p_sync.add_argument("--limit", type=int, default=80, help="每个数据源最多多少条")
    p_sync.add_argument("--no-search", action="store_true", help="禁用官方 Search API")
    p_sync.add_argument("--no-trending", action="store_true", help="禁用 gh-trending-page")

    sub.add_parser("rematch", help="对DB内全部Repo重跑能源场景匹配（更新匹配规则后使用）")

    p_demo = sub.add_parser("demo", help="植入演示数据（离线模式）")

    args = parser.parse_args()

    if args.cmd == "sync":
        log.info(f"{'═'*50}\n🚀 开始每周 GitHub Trending 同步\n{'═'*50}")
        repos = fetch_trending_weekly(
            max_per_source=args.limit,
            use_search=not args.no_search,
            use_trending_page=not args.no_trending,
        )
        # 补全部分缺失的 topics
        session = requests.Session()
        session.headers.update({"User-Agent": "wenyao-zhitou/1.0"})
        fill_topics_for_missing(session, repos[:80])
        # 入库 + 能源匹配
        result = sync_to_db(repos[:100])

        # 前端 JSON 同步导出
        try:
            from tech_matcher import export_for_frontend
            export_for_frontend()
        except Exception as e:
            log.warning(f"前端导出跳过: {e}")
        log.info(f"🎉 全部完成：新增 {result['added']} / 更新 {result['updated']}")

    elif args.cmd == "rematch":
        re_match_all_energy()

    elif args.cmd == "demo":
        from tech_matcher import add_demo_github_data, export_for_frontend
        add_demo_github_data()
        export_for_frontend()

if __name__ == "__main__":
    cli()
