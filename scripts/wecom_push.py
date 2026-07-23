#!/usr/bin/env python3
"""文鳐智投 企微推送 v8 — 精简版：仅招标TOP8卡片"""
import json, sqlite3, os, sys, requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0256f02d-7368-4214-9c99-9c53ce449e92"
KILL_SWITCH = True   # ⏸ 已禁用企微推送（按用户要求）
DB = "/root/.hermes/profiles/wenyaozhitou/data/bidding.db"
REPORT_URL = "https://www.yfzx.online/bidding/"
PUSH_LOCK = "/tmp/wenyao_push.lock"
COVER_BASE = "https://www.yfzx.online/bidding/img_gen/covers"

def cover(idx):
    return f"{COVER_BASE}/cover_{(idx % 8) + 1}.png"

def _send(msgtype, payload, label=""):
    if KILL_SWITCH:
        print(f"  [KILL_SWITCH] {label}: 已拦截")
        return None
    resp = requests.post(WEBHOOK, json={"msgtype": msgtype, **payload}, timeout=10)
    return resp

def dget(row, key, default=""):
    try:
        return row[key] if row[key] is not None else default
    except (IndexError, KeyError):
        return default

def build_card(idx, row):
    item = row
    score = dget(item, "relevance_score", 0) or 0
    emoji = "🟢" if score >= 70 else ("🟡" if score >= 50 else "⚪")
    title = (dget(item, "title") or "").strip()
    if len(title) > 120:
        title = title[:117] + "..."

    desc_parts = []
    cat = dget(item, "category")
    if cat: desc_parts.append(cat)
    prov = dget(item, "province")
    if prov: desc_parts.append(f"📍{prov}")
    owner = dget(item, "procurement_owner")
    if owner: desc_parts.append(f"招标单位：{owner[:25]}")
    desc_parts.append(f"相关性：{score:.1f}分")

    url = dget(item, "url") or REPORT_URL
    if not url or url.startswith("javascript:"):
        url = REPORT_URL

    return {
        "title": f"{emoji} [{score:.0f}分] {title}",
        "description": " · ".join(desc_parts),
        "url": url,
        "picurl": cover(idx),
    }

def push_summary():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    today = datetime.now().strftime("%Y-%m-%d")

    # ── 防重复 ──
    lock_date = ""
    if os.path.exists(PUSH_LOCK):
        with open(PUSH_LOCK) as f:
            lock_date = f.read().strip()
    if lock_date == today:
        print(f"  今日已推送（lock: {today}），跳过")
        conn.close()
        return

    # ── 今日招标 + 近7日补充（避免单日断档推送太少）──
    top_bid = conn.execute(
        "SELECT * FROM bidding_notices WHERE date(fetch_date)=? AND relevance_score>=50 "
        "ORDER BY relevance_score DESC LIMIT 8", (today,)
    ).fetchall()
    
    # Fill gaps with recent high-score items (last 7 days, excluding today)
    if len(top_bid) < 5:
        existing_ids = {r['id'] for r in top_bid}
        fill = conn.execute(
            "SELECT * FROM bidding_notices WHERE date(fetch_date)>=date(?,'-7 days') "
            "AND date(fetch_date)<? AND relevance_score>=50 "
            "ORDER BY relevance_score DESC LIMIT ?", (today, today, 8 - len(top_bid))
        ).fetchall()
        top_bid.extend([r for r in fill if r['id'] not in existing_ids])
        top_bid = top_bid[:8]

    total_all = conn.execute("SELECT COUNT(*) FROM bidding_notices WHERE relevance_score>=50").fetchone()[0]
    total_bid = conn.execute("SELECT COUNT(*) FROM bidding_notices").fetchone()[0]
    total_win = conn.execute("SELECT COUNT(*) FROM winning_notices").fetchone()[0]

    if not top_bid:
        conn.close()
        # Send silent-day status — don't leave the group in the dark
        msg = f"📋 文鳐智投标监控 · 今日无新增≥50分招标\n累计招标 {total_bid} 条 | 中标 {total_win} 条 | ≥50分 {total_all} 条\n👉 {REPORT_URL}"
        resp = _send("text", {"text": {"content": msg}}, "无新增通知")
        if resp:
            print(f"  无新增通知: {resp.status_code} | {resp.json().get('errmsg','?')}")
        else:
            print(f"  无新增通知: 发送失败")
        with open(PUSH_LOCK, 'w') as f:
            f.write(today)
        return

    conn.close()

    # ═══ 推送：引导语 + 卡片 ═══
    today_count = sum(1 for r in top_bid if r['fetch_date'] and str(r['fetch_date'])[:10] == today)
    recent_count = len(top_bid) - today_count
    guide = f"招标相关度 TOP{len(top_bid)}"
    if today_count and recent_count:
        guide += f"（今日{today_count}条 + 近期{recent_count}条）"
    elif today_count:
        guide += f"（今日新增）"
    else:
        guide += f"（近7日）"
    guide += "，请各位领导同事过目。"
    resp = _send("text", {"text": {"content": guide}}, "引导语")
    if resp:
        print(f"  引导语: {resp.status_code} | {resp.json().get('errmsg','?')}")

    articles = [build_card(i, t) for i, t in enumerate(top_bid)]
    resp = _send("news", {"news": {"articles": articles}}, "招标卡片")
    if resp:
        r = resp.json()
        print(f"  招标卡片: {resp.status_code} | {r.get('errmsg','?')} | {len(articles)}张")

    print(f"  推送完成：今日招标TOP{len(top_bid)} · 历史≥50分累计{total_all}")

    with open(PUSH_LOCK, 'w') as f:
        f.write(today)

if __name__ == "__main__":
    push_summary()
