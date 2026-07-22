#!/usr/bin/env python3
"""文鳐智投 日报生成器 v1 — 带AI分析+点赞/点踩反馈"""
import json, sqlite3, os, sys
from datetime import datetime
from pathlib import Path

DB = "/root/.hermes/profiles/wenyaozhitou/data/bidding.db"
RD = Path("/var/www/html/bidding")
BOOKMARK_FILE = RD / "data/bookmarks.json"

def s(v):
    return str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;") if v else ""

def dget(row, key, default=""):
    try:
        return row[key] if row[key] is not None else default
    except: return default

def load_bookmarks():
    if BOOKMARK_FILE.exists():
        return json.loads(BOOKMARK_FILE.read_text())
    return []

def analyze_bidding(item, bookmarks):
    """分析单条招标"""
    item_id = str(item["id"])
    score = item.get("relevance_score", 0) or 0
    title = dget(item, "title")[:100]
    owner = dget(item, "procurement_owner") or dget(item, "category") or "未标注"
    cat = dget(item, "category") or "未分类"
    province = dget(item, "province") or "未知"
    amount = dget(item, "budget_amount") or dget(item, "estimated_amount") or "未公示"
    is_starred = item_id in bookmarks

    # 评分级别
    if score >= 8: level, emoji, badge = "高相关", "🟢", "score-hi"
    elif score >= 5: level, emoji, badge = "中等相关", "🟡", "score-mid"
    elif score >= 3: level, emoji, badge = "一般相关", "🟠", "score-lo"
    else: level, emoji, badge = "低相关", "⚪", "score-lo"

    # 建议
    if score >= 8:
        advice = "🔴 <b>重点关注 · 建议投标</b>"
        reason = "高匹配度，涉及核心数字化/智慧工地/AI平台业务，应优先组织投标。"
    elif score >= 5:
        advice = "🟡 <b>可投标 · 需评估</b>"
        reason = "中等匹配，可能涉及部分数字化内容或边缘业务，建议进一步分析招标文件后决定。"
    elif score >= 3:
        advice = "🟠 <b>可关注</b>"
        reason = "关联度一般，可能是信息化硬件采购或非核心数字化服务，保持关注即可。"
    else:
        advice = "⚪ <b>暂不考虑</b>"
        reason = "与数智科技核心业务关联度低，暂不建议投入资源。"

    # 收藏加权
    if is_starred:
        advice = "⭐ " + advice
        reason += " <br>📌 <b>您已收藏此项目</b>，建议密切跟踪招标进展。"

    return {
        "id": item_id, "title": title, "owner": owner, "cat": cat,
        "province": province, "amount": amount, "score": score,
        "level": level, "emoji": emoji, "badge": badge,
        "advice": advice, "reason": reason, "is_starred": is_starred,
        "url": dget(item, "url", ""), "publish_date": dget(item, "publish_date", ""),
        "source_site": dget(item, "source_site", ""),
    }

def analyze_winning(item, bookmarks):
    """分析单条中标"""
    item_id = str(item["id"])
    score = item.get("relevance_score", 0) or 0
    title = dget(item, "title")[:100]
    winner = dget(item, "winner_company") or "未标注"
    owner = dget(item, "procurement_owner") or dget(item, "category") or "未标注"
    amount = dget(item, "winning_amount") or "未公示"
    is_starred = item_id in bookmarks

    # 判断是否中南院
    is_zn = any(kw in str(winner) for kw in ["中南电力", "中南院", "数智科技", "中国电力工程顾问集团中南"])

    # 竞品分析
    competitors = ["中电科", "中国能建", "中国电建", "华为", "阿里云", "腾讯云", "百度",
                   "国网信通", "南瑞", "许继", "四方", "金智", "科远", "朗坤", "太极",
                   "东软", "中软", "浪潮", "中兴", "海康", "大华", "宇视"]
    comp_match = [c for c in competitors if c in str(winner)]
    is_competitor = bool(comp_match)

    if is_zn:
        analysis = "✅ <b>中南院中标！</b>竞标成功，应复盘成功经验。"
        comp_detail = f"中标单位：{winner}（本公司）"
    elif is_competitor:
        analysis = f"⚠️ <b>竞品中标 · {', '.join(comp_match)}</b>。应分析该竞品优势，优化我方方案。"
        comp_detail = f"竞品：{winner}，同类竞品：{', '.join(comp_match)}"
    else:
        analysis = f"📊 非中南院中标 · {winner}。分析市场格局，评估我方差距。"
        comp_detail = f"中标单位：{winner}（非直接竞品）"

    # 收藏提醒
    if is_starred:
        analysis += " <br>⭐ <b>此项目您已收藏</b>，请注意中标结果已公示。"

    # 大标判断
    big_deal = "万" in str(amount) and any(
        int(amount.replace("万元","").replace(",","").replace(" ","").split(".")[0]) >= 500
        for amount in [str(amount)] if amount.replace("万元","").replace(",","").replace(" ","").split(".")[0].isdigit()
    )
    if big_deal:
        analysis += " <br>💰 <b>大标警告 ≥500万</b>"

    return {
        "id": item_id, "title": title, "winner": winner, "owner": owner,
        "amount": amount, "score": score, "is_starred": is_starred,
        "is_zn": is_zn, "is_competitor": is_competitor,
        "analysis": analysis, "comp_detail": comp_detail,
        "big_deal": big_deal,
        "url": dget(item, "url", ""), "publish_date": dget(item, "publish_date", ""),
    }

def generate():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    today = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    report_date_str = datetime.now().strftime("%m月%d日")

    # 今天的数据
    bids_raw = conn.execute(
        "SELECT * FROM bidding_notices WHERE date(fetch_date)=? AND relevance_score>0 "
        "ORDER BY relevance_score DESC LIMIT 50", (today,)
    ).fetchall()

    # 若今日无数据，展示最近3天
    if not bids_raw:
        bids_raw = conn.execute(
            "SELECT * FROM bidding_notices WHERE relevance_score>0 AND date(fetch_date)>=date('now','-3 days') "
            "ORDER BY relevance_score DESC LIMIT 50"
        ).fetchall()

    wins_raw = conn.execute(
        "SELECT * FROM winning_notices WHERE date(fetch_date)=? AND relevance_score>0 "
        "ORDER BY relevance_score DESC LIMIT 50", (today,)
    ).fetchall()

    if not wins_raw:
        wins_raw = conn.execute(
            "SELECT * FROM winning_notices WHERE relevance_score>0 AND date(fetch_date)>=date('now','-3 days') "
            "ORDER BY relevance_score DESC LIMIT 50"
        ).fetchall()

    # 统计
    total_bid = conn.execute("SELECT COUNT(*) FROM bidding_notices WHERE date(fetch_date)=?", (today,)).fetchone()[0]
    total_win = conn.execute("SELECT COUNT(*) FROM winning_notices WHERE date(fetch_date)=?", (today,)).fetchone()[0]
    conn.close()

    bookmarks = load_bookmarks()

    # 分析
    bidding_analyses = [analyze_bidding(dict(r), bookmarks) for r in bids_raw]
    winning_analyses = [analyze_winning(dict(r), bookmarks) for r in wins_raw]

    # 统计标签
    starred_bids = [a for a in bidding_analyses if a["is_starred"]]
    starred_wins = [a for a in winning_analyses if a["is_starred"]]

    html = build_html(today, report_date_str, now_str, bidding_analyses, winning_analyses,
                      total_bid, total_win, starred_bids, starred_wins)

    report_path = RD / f"report-{today}.html"
    report_path.write_text(html)
    report_path.chmod(0o644)

    print(f"日报: {report_path} ({len(bidding_analyses)}招标+{len(winning_analyses)}中标)")

    return report_path, bidding_analyses, winning_analyses

def build_html(today, date_str, now_str, bids, wins, total_bid, total_win, sbids, swins):
    bid_cards = "\n".join(build_bid_card(a) for a in bids) if bids else '<div class="empty">📭 今日暂无相关招标信息</div>'
    win_cards = "\n".join(build_win_card(a) for a in wins) if wins else '<div class="empty">📭 今日暂无相关中标信息</div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>文鳐智投 · {date_str} 日报</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
/* 默认明亮 */
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f8fafc;color:#1e293b;min-height:100vh;line-height:1.6;transition:background .3s,color .3s}}
body.dark{{background:#0f172a;color:#e2e8f0}}
header{{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-bottom:2px solid #3b82f6;padding:16px 24px;display:flex;align-items:center;justify-content:space-between}}
body.dark header{{background:linear-gradient(135deg,#1e293b,#0f172a)}}
.header-left{{display:flex;align-items:center;gap:10px}}
header h1{{font-size:20px;color:#1d4ed8}}
body.dark header h1{{color:#60a5fa}}
header .sub{{font-size:12px;color:#64748b}}
body.dark header .sub{{color:#94a3b8}}
.summary-bar{{display:flex;gap:16px;padding:12px 24px;background:#fff;border-bottom:1px solid #e2e8f0;flex-wrap:wrap;justify-content:center;font-size:13px;border-radius:0}}
body.dark .summary-bar{{background:#1e293b;border-color:#334155}}
.summary-bar span{{padding:4px 12px;border-radius:12px;background:#f1f5f9;border:1px solid #e2e8f0;color:#334155}}
body.dark .summary-bar span{{background:#0f172a;border-color:#334155;color:#cbd5e1}}
.summary-bar .hi{{color:#10b981;font-weight:600}}
.summary-bar .star{{color:#f59e0b}}

/* Tab切换 */
.tab-bar{{display:flex;gap:4px;padding:12px 24px;justify-content:center}}
.tab-btn{{padding:10px 32px;border-radius:20px;border:1px solid #cbd5e1;background:#fff;color:#64748b;cursor:pointer;font-size:14px;font-weight:600;transition:all .2s}}
body.dark .tab-btn{{border-color:#334155;background:#1e293b;color:#94a3b8}}
.tab-btn.active{{background:#3b82f6;border-color:#3b82f6;color:#fff}}
.tab-btn:hover:not(.active){{border-color:#3b82f6;color:#1e293b}}
body.dark .tab-btn:hover:not(.active){{border-color:#60a5fa;color:#e2e8f0}}

.container{{max-width:900px;margin:0 auto;padding:0 20px 40px}}
.tab-panel{{display:none}}
.tab-panel.active{{display:block}}

/* 卡片 */
.card{{background:#fff;border-radius:12px;padding:20px;margin:12px 0;border:1px solid #e2e8f0;transition:all .2s;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
body.dark .card{{background:#1e293b;border-color:#334155;box-shadow:none}}
.card:hover{{border-color:#3b82f6;box-shadow:0 2px 8px rgba(59,130,246,.1)}}
body.dark .card:hover{{border-color:#475569;box-shadow:none}}
.card.starred{{border-color:#f59e0b;box-shadow:0 0 12px rgba(245,158,11,0.15)}}
.card-header{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:10px;flex-wrap:wrap}}
.card-title{{font-size:15px;font-weight:600;flex:1;min-width:200px}}
.card-title a{{color:#1e293b;text-decoration:none}}
.card-title a:hover{{color:#3b82f6}}
body.dark .card-title a{{color:#e2e8f0}}
body.dark .card-title a:hover{{color:#60a5fa}}
.card-badge{{display:flex;gap:6px;flex-shrink:0}}
.badge{{padding:2px 10px;border-radius:10px;font-size:11px;font-weight:600;white-space:nowrap}}
.badge-star{{background:#f59e0b22;color:#f59e0b;border:1px solid #f59e0b44}}
.badge-hi{{background:#10b98122;color:#10b981;border:1px solid #10b98144}}
.badge-mid{{background:#f59e0b22;color:#f59e0b;border:1px solid #f59e0b44}}
.badge-lo{{background:#6b728022;color:#9ca3af;border:1px solid #6b728044}}
.badge-zn{{background:#3b82f622;color:#60a5fa;border:1px solid #3b82f644}}
.card-meta{{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:#64748b;margin-bottom:10px}}
body.dark .card-meta{{color:#94a3b8}}
.card-meta span{{display:flex;align-items:center;gap:4px}}
.card-body{{font-size:13px;color:#475569;line-height:1.7;padding:10px 0;border-top:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;margin:10px 0}}
body.dark .card-body{{color:#cbd5e1;border-color:#334155}}
.card-advice{{font-size:13px;padding:6px 0}}
.card-actions{{display:flex;gap:10px;margin-top:12px;align-items:center}}
.btn-like,.btn-dislike{{padding:6px 16px;border-radius:16px;border:1px solid #334155;background:transparent;color:#94a3b8;cursor:pointer;font-size:12px;transition:all .2s;display:flex;align-items:center;gap:4px}}
.btn-like:hover{{background:#10b98122;border-color:#10b981;color:#10b981}}
.btn-dislike:hover{{background:#ef444422;border-color:#ef4444;color:#ef4444}}
.btn-like.active{{background:#10b98144;border-color:#10b981;color:#10b981}}
.btn-dislike.active{{background:#ef444444;border-color:#ef4444;color:#ef4444}}
.btn-like:disabled,.btn-dislike:disabled{{opacity:.5;cursor:not-allowed}}
.feedback-msg{{font-size:11px;color:#10b981;margin-left:8px}}

/* 点踩弹框 */
.overlay{{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.6);z-index:100;justify-content:center;align-items:center}}
.overlay.show{{display:flex}}
.dialog{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;max-width:420px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,.15)}}
body.dark .dialog{{background:#1e293b;border-color:#334155;box-shadow:0 8px 32px rgba(0,0,0,.5)}}
.dialog h3{{color:#1e293b;margin-bottom:12px;font-size:15px}}
body.dark .dialog h3{{color:#e2e8f0}}
.dialog textarea{{width:100%;height:100px;background:#f8fafc;border:1px solid #cbd5e1;border-radius:8px;color:#1e293b;padding:10px;font-size:13px;resize:vertical;font-family:inherit}}
body.dark .dialog textarea{{background:#0f172a;border-color:#334155;color:#e2e8f0}}
.dialog-btns button{{padding:8px 20px;border-radius:8px;border:1px solid #cbd5e1;cursor:pointer;font-size:13px}}
body.dark .dialog-btns button{{border-color:#334155}}
.dialog .btn-submit{{background:#ef4444;border-color:#ef4444;color:#fff}}
.dialog .btn-cancel{{background:transparent;color:#64748b}}
body.dark .dialog .btn-cancel{{color:#94a3b8}}
.dialog .error{{color:#ef4444;font-size:11px;margin-top:6px;display:none}}

.empty{{text-align:center;padding:60px 20px;color:#64748b;font-size:15px}}

footer{{text-align:center;padding:20px;color:#94a3b8;font-size:11px;border-top:1px solid #e2e8f0;margin-top:40px}}
body.dark footer{{color:#475569;border-color:#1e293b}}
footer a{{color:#94a3b8}}
body.dark footer a{{color:#475569}}

/* 主题切换按钮 */
.theme-btn{{width:36px;height:36px;border-radius:50%;border:1px solid #cbd5e1;background:#fff;color:#f59e0b;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;transition:all .2s;flex-shrink:0}}
body.dark .theme-btn{{border-color:#334155;background:#1e293b;color:#fbbf24}}
.theme-btn:hover{{border-color:#3b82f6}}

@media(max-width:600px){{
  .card-header{{flex-direction:column}}
  .card-meta{{gap:8px}}
}}
</style>
<link rel="stylesheet" href="/bidding/chat-widget.css?v=4">
</head>
<body>

<header>
  <div class="header-left">
    <h1>📊 文鳐智投 · 日报</h1>
    <div class="sub">{date_str} · 生成于 {now_str} · 中南电力·数智科技</div>
  </div>
  <button class="theme-btn" onclick="toggleTheme()" title="切换主题">☀️</button>
</header>

<div class="summary-bar">
  <span>📋 招标 <b>{total_bid}</b> 条</span>
  <span>🏆 中标 <b>{total_win}</b> 条</span>
  <span class="hi">⭐ 收藏招标 <b>{len(sbids)}</b> 条</span>
  <span class="star">⭐ 收藏中标 <b>{len(swins)}</b> 条</span>
</div>

<div class="tab-bar">
  <button class="tab-btn active" onclick="switchTab('bidding')" id="tabBidding">📋 招标情况报告</button>
  <button class="tab-btn" onclick="switchTab('winning')" id="tabWinning">🏆 中标情况报告</button>
</div>

<div class="container">
  <div class="tab-panel active" id="panelBidding">
    {bid_cards}
  </div>
  <div class="tab-panel" id="panelWinning">
    {win_cards}
  </div>
</div>

<!-- 点踩弹框 -->
<div class="overlay" id="dislikeOverlay">
  <div class="dialog">
    <h3>👎 请告诉我们原因</h3>
    <textarea id="dislikeReason" placeholder="例如：这个项目与数智科技业务不匹配、评分不准确、建议应该关注XX方向..."></textarea>
    <div class="error" id="dislikeError">请填写点踩理由</div>
    <div class="dialog-btns">
      <button class="btn-cancel" onclick="closeDislike()">取消</button>
      <button class="btn-submit" onclick="submitDislike()">提交反馈</button>
    </div>
  </div>
</div>

<footer>
  © 中南电力设计院数智科技 · 文鳐智投 2026 · <a href="/bidding/">返回监控</a> · <a href="/bidding/changelog.html">更新日志</a>
</footer>

<script>
const REPORT_DATE = "{today}";
const API = "/bidding/api/feedback";
let currentDislikeId = null;
let currentDislikeSection = null;
const submitted = JSON.parse(localStorage.getItem("daily_feedback") || "{{}}");

// 主题切换
function toggleTheme() {{
  const isDark = document.body.classList.toggle('dark');
  localStorage.setItem('daily_theme', isDark ? 'dark' : 'light');
  document.querySelector('.theme-btn').textContent = isDark ? '🌙' : '☀️';
}}
(function() {{
  const saved = localStorage.getItem('daily_theme');
  if (saved === 'dark') {{
    document.body.classList.add('dark');
    document.querySelector('.theme-btn').textContent = '🌙';
  }}
}})();

function switchTab(tab) {{
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab' + tab.charAt(0).toUpperCase() + tab.slice(1)).classList.add('active');
  document.getElementById('panel' + tab.charAt(0).toUpperCase() + tab.slice(1)).classList.add('active');
}}

function submitLike(itemId, section) {{
  const btn = document.getElementById('btnLike_' + itemId);
  const disBtn = document.getElementById('btnDislike_' + itemId);
  if (btn.disabled || (submitted[itemId] && submitted[itemId].type === 'like')) return;
  btn.disabled = true;
  if (disBtn) disBtn.disabled = true;
  btn.classList.add('active');
  fetch(API, {{
    method: 'POST', headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify({{item_id:itemId, type:'like', reason:'', report_date:REPORT_DATE, section:section}})
  }}).then(r => r.json()).then(d => {{
    if (d.ok) {{
      submitted[itemId] = {{type:'like', time:new Date().toISOString()}};
      localStorage.setItem("daily_feedback", JSON.stringify(submitted));
      btn.innerHTML = '👍 已点赞';
      const msg = document.getElementById('msg_' + itemId);
      if (msg) msg.textContent = '✓ 感谢反馈';
    }}
  }}).catch(e => console.warn(e));
}}

function openDislike(itemId, section) {{
  currentDislikeId = itemId;
  currentDislikeSection = section;
  document.getElementById('dislikeReason').value = '';
  document.getElementById('dislikeError').style.display = 'none';
  document.getElementById('dislikeOverlay').classList.add('show');
}}

function closeDislike() {{
  document.getElementById('dislikeOverlay').classList.remove('show');
  currentDislikeId = null;
}}

function submitDislike() {{
  const reason = document.getElementById('dislikeReason').value.trim();
  if (!reason) {{
    document.getElementById('dislikeError').style.display = 'block';
    return;
  }}
  document.getElementById('dislikeError').style.display = 'none';
  const btn = document.getElementById('btnDislike_' + currentDislikeId);
  const likeBtn = document.getElementById('btnLike_' + currentDislikeId);
  if (btn) {{ btn.disabled = true; btn.classList.add('active'); }}
  if (likeBtn) likeBtn.disabled = true;
  fetch(API, {{
    method: 'POST', headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify({{item_id:currentDislikeId, type:'dislike', reason:reason, report_date:REPORT_DATE, section:currentDislikeSection}})
  }}).then(r => r.json()).then(d => {{
    if (d.ok) {{
      submitted[currentDislikeId] = {{type:'dislike', time:new Date().toISOString(), reason:reason}};
      localStorage.setItem("daily_feedback", JSON.stringify(submitted));
      if (btn) btn.textContent = '👎 已反馈';
      const msg = document.getElementById('msg_' + currentDislikeId);
      if (msg) msg.textContent = '✓ 已记录，感谢反馈';
    }}
  }}).catch(e => console.warn(e));
  closeDislike();
}}

// 加载已提交的反馈状态
(function() {{
  Object.keys(submitted).forEach(id => {{
    const fb = submitted[id];
    if (fb.type === 'like') {{
      const btn = document.getElementById('btnLike_' + id);
      if (btn) {{ btn.disabled = true; btn.classList.add('active'); btn.innerHTML = '👍 已点赞'; }}
    }} else if (fb.type === 'dislike') {{
      const btn = document.getElementById('btnDislike_' + id);
      if (btn) {{ btn.disabled = true; btn.classList.add('active'); btn.textContent = '👎 已反馈'; }}
    }}
  }});
}})();
</script>
<script src="/bidding/chat-widget.js?v=4"></script>
</body>
</html>"""

def build_bid_card(a):
    star_cls = " starred" if a["is_starred"] else ""
    star_badge = ' <span class="badge badge-star">⭐ 收藏</span>' if a["is_starred"] else ""
    return f"""<div class="card{star_cls}">
  <div class="card-header">
    <div class="card-title">
      {a["emoji"]} <a href="{s(a['url']) or '#'}" target="_blank">{s(a['title'])}</a>
    </div>
    <div class="card-badge">
      <span class="badge {a['badge']}">{a["score"]:.1f}分 · {a['level']}</span>{star_badge}
    </div>
  </div>
  <div class="card-meta">
    <span>🏢 招标单位：{s(a['owner'][:30])}</span>
    <span>📍 {s(a['province'])}</span>
    <span>💰 预算：{s(a['amount'])}</span>
    <span>📅 {s(a['publish_date'][:10])}</span>
    <span>📡 {s(a['source_site'][:20])}</span>
  </div>
  <div class="card-body">
    <b>📝 分析</b>：{a['reason']}
  </div>
  <div class="card-advice">{a['advice']}</div>
  <div class="card-actions">
    <button class="btn-like" id="btnLike_{a['id']}" onclick="submitLike('{a['id']}','bidding')">👍 赞同</button>
    <button class="btn-dislike" id="btnDislike_{a['id']}" onclick="openDislike('{a['id']}','bidding')">👎 不认同</button>
    <span class="feedback-msg" id="msg_{a['id']}"></span>
  </div>
</div>"""

def build_win_card(a):
    star_cls = " starred" if a["is_starred"] else ""
    star_badge = ' <span class="badge badge-star">⭐ 收藏</span>' if a["is_starred"] else ""
    zn_badge = ' <span class="badge badge-zn">本公司中标</span>' if a["is_zn"] else ""
    big_badge = ' <span class="badge" style="background:#ef444422;color:#ef4444;border:1px solid #ef444444">💰 大标</span>' if a["big_deal"] else ""
    return f"""<div class="card{star_cls}">
  <div class="card-header">
    <div class="card-title">
      🏆 <a href="{s(a['url']) or '#'}" target="_blank">{s(a['title'])}</a>
    </div>
    <div class="card-badge">
      <span class="badge badge-mid">{a["score"]:.1f}分</span>{zn_badge}{star_badge}{big_badge}
    </div>
  </div>
  <div class="card-meta">
    <span>🏢 中标单位：{s(a['winner'][:30])}</span>
    <span>📋 招标单位：{s(a['owner'][:25])}</span>
    <span>💰 金额：{s(a['amount'])}</span>
    <span>📅 {s(a['publish_date'][:10])}</span>
  </div>
  <div class="card-body">
    <b>🔍 竞品分析</b>：{a['comp_detail']}<br>
    {a['analysis']}
  </div>
  <div class="card-actions">
    <button class="btn-like" id="btnLike_{a['id']}" onclick="submitLike('{a['id']}','winning')">👍 赞同</button>
    <button class="btn-dislike" id="btnDislike_{a['id']}" onclick="openDislike('{a['id']}','winning')">👎 不认同</button>
    <span class="feedback-msg" id="msg_{a['id']}"></span>
  </div>
</div>"""

if __name__ == "__main__":
    generate()
