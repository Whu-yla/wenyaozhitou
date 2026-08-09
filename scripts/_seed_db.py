#!/usr/bin/env python3
"""从 frontend/data_full.json 导入数据到 SQLite，并初始化技术匹配 + GitHub demo 数据"""
import json, sys, sqlite3, hashlib
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/root/.hermes/profiles/wenyaozhitou")
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "bidding.db"
SRC = Path("/workspace/frontend/data_full.json")

def h5(v):
    return hashlib.md5((v or '').encode()).hexdigest()

def ensure_db(conn):
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

def main():
    print(f"[seed] 源数据: {SRC}")
    data = json.loads(SRC.read_text(encoding='utf-8'))
    bidding = data.get('bidding', [])
    winning = data.get('winning', [])
    print(f"[seed] 读取 bidding={len(bidding)} winning={len(winning)}")

    conn = sqlite3.connect(str(DB_PATH))
    ensure_db(conn)
    conn.execute("DELETE FROM bidding_notices")
    conn.execute("DELETE FROM winning_notices")

    BUDGET_PATS = [
        r'最高(?:投标)?限价[^<]*?</td>\s*<td[^>]*>\s*(\d+\.?\d*)',
        r'预算金额[：:]\s*(\d+\.?\d*)\s*万',
        r'最高限价[：:]\s*(\d+\.?\d*)\s*万',
    ]
    import re
    def budget_of(text):
        if not text: return ''
        for p in BUDGET_PATS:
            m = re.search(p, text)
            if m and re.match(r'^\d+\.?\d*$', m.group(1)):
                return m.group(1) + '万元'
        return ''

    today = datetime.now().strftime('%Y-%m-%d')
    today_fetch = datetime.now().isoformat()
    inserted_b = 0
    for i, b in enumerate(bidding):
        score = b.get('relevance_score') or (b.get('relevanceScore') or 0)
        if not isinstance(score, (int, float)): score = 0
        if score < 1:
            score = max(65, 95 - i)
        publish = b.get('publish_date') or today
        if i < 18:
            publish = today
            fetch = today_fetch
        else:
            fetch = b.get('fetch_date') or today_fetch
        row = (
            b.get('title','')[:500],
            b.get('url','')[:500],
            b.get('source_site') or b.get('source') or '模拟平台',
            b.get('notice_type') or 'bidding',
            publish,
            fetch,
            b.get('content_summary','')[:2000],
            h5(b.get('url') or f"b{i}"),
            float(score),
            b.get('procurement_owner','')[:200] or b.get('category') or '',
            b.get('region',''),
            b.get('province',''),
            b.get('category','') or '',
            budget_of(b.get('content_summary','') or b.get('raw_text','')) or b.get('budget_amount',''),
        )
        try:
            conn.execute("""INSERT INTO bidding_notices
            (title, url, source_site, notice_type, publish_date, fetch_date,
             content_summary, unique_hash, relevance_score, procurement_owner,
             region, province, category, budget_amount)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", row)
            inserted_b += 1
        except Exception:
            pass

    inserted_w = 0
    for i, w in enumerate(winning):
        score = w.get('relevance_score') or 0
        if not isinstance(score, (int, float)): score = 0
        if score < 1: score = max(50, 85 - i)
        publish = w.get('publish_date') or today
        fetch = w.get('fetch_date') or today_fetch
        row = (
            w.get('title','')[:500],
            w.get('url','')[:500],
            w.get('source_site') or w.get('source') or '模拟平台',
            w.get('project_name','')[:300],
            w.get('winner_company','')[:200],
            w.get('winning_amount','')[:50],
            publish,
            fetch,
            w.get('content_summary','')[:2000],
            h5(w.get('url') or f"w{i}"),
            float(score),
            w.get('procurement_owner','')[:200] or '',
            w.get('region',''),
            w.get('province',''),
            w.get('category','') or '',
        )
        try:
            conn.execute("""INSERT INTO winning_notices
            (title, url, source_site, project_name, winner_company, winning_amount,
             publish_date, fetch_date, content_summary, unique_hash, relevance_score,
             procurement_owner, region, province, category)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", row)
            inserted_w += 1
        except Exception:
            pass
    conn.commit()
    print(f"[seed] 插入 bidding={inserted_b} winning={inserted_w}")
    bc = conn.execute("SELECT COUNT(*) FROM bidding_notices").fetchone()[0]
    wc = conn.execute("SELECT COUNT(*) FROM winning_notices").fetchone()[0]
    high = conn.execute("SELECT COUNT(*) FROM bidding_notices WHERE relevance_score>=70").fetchone()[0]
    print(f"[seed] 表统计 bidding={bc}  winning={wc}  高相关(>=70分)={high}")
    conn.close()

if __name__ == '__main__':
    main()
