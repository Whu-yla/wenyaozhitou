#!/usr/bin/env python3
"""日报数据导出 — 给 LLM Agent 用"""
import json, sqlite3, sys
from datetime import datetime
from collections import defaultdict

DB = "/root/.hermes/profiles/wenyaozhitou/data/bidding.db"
TODAY = datetime.now().strftime("%Y-%m-%d")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# 收藏
conn.execute("CREATE TABLE IF NOT EXISTS starred_items (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL, item_type TEXT DEFAULT 'bidding', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(item_id, item_type))")
conn.commit()
starred = set(r[0] for r in conn.execute("SELECT item_id FROM starred_items WHERE item_type='bidding'"))
starred_win = set(r[0] for r in conn.execute("SELECT item_id FROM starred_items WHERE item_type='winning'"))

# 招标（高相关 ≥4）
bids = []
for r in conn.execute("SELECT * FROM bidding_notices WHERE date(fetch_date)=? AND relevance_score>=4 ORDER BY relevance_score DESC", (TODAY,)):
    d = dict(r)
    d["_starred"] = d["id"] in starred
    bids.append(d)

# 中标
wins = []
for r in conn.execute("SELECT * FROM winning_notices WHERE date(fetch_date)=? AND relevance_score>0 ORDER BY relevance_score DESC", (TODAY,)):
    d = dict(r)
    d["_starred"] = d["id"] in starred_win
    wins.append(d)

# 竞品汇总
comp_wins = defaultdict(lambda: {"count": 0, "total_amt": "", "recent": []})
for r in conn.execute("SELECT winner_company, winning_amount, title, publish_date FROM winning_notices WHERE relevance_score>0 ORDER BY publish_date DESC LIMIT 200"):
    name = (r["winner_company"] or "").strip()
    if len(name) >= 4:
        comp_wins[name]["count"] += 1
        comp_wins[name]["total_amt"] = r["winning_amount"] or ""
        if len(comp_wins[name]["recent"]) < 3:
            comp_wins[name]["recent"].append({"title": (r["title"] or "")[:60], "date": r["publish_date"] or ""})

top_comps = sorted(comp_wins.items(), key=lambda x: x[1]["count"], reverse=True)[:10]

conn.close()

data = {
    "date": TODAY,
    "bids": bids,
    "wins": wins,
    "bid_count": len(bids),
    "win_count": len(wins),
    "high_bid": sum(1 for b in bids if (b.get("relevance_score") or 0) >= 7),
    "starred_count": len([b for b in bids if b["_starred"]]),
    "starred_win_count": len([w for w in wins if w["_starred"]]),
    "top_competitors": [{"name": n, "count": d["count"], "recent": d["recent"]} for n, d in top_comps],
}
print(json.dumps(data, ensure_ascii=False, default=str))
