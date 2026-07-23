#!/usr/bin/env python3
"""文鳐智投 投标报告生成器 v5 — 专业布局重设计"""
import json, sqlite3, subprocess, sys, os, shutil
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

DB = "/root/.hermes/profiles/wenyaozhitou/data/bidding.db"
RD = Path("/var/www/html/bidding")

def rd(r): return {k:r[k] for k in r.keys()} if r and not isinstance(r,dict) else (r or {})
def s(v): return str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;") if v else ""

def generate():
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    
    allB = [rd(r) for r in conn.execute("SELECT * FROM bidding_notices WHERE relevance_score>0 ORDER BY relevance_score DESC").fetchall()]
    allW = [rd(r) for r in conn.execute("SELECT * FROM winning_notices WHERE relevance_score>0 ORDER BY relevance_score DESC").fetchall()]
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # ── 今日新增：对比昨天归档差集 ──
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_file = RD / yesterday / "data.json"
    yesterday_ids = set()
    if yesterday_file.exists():
        try:
            with open(yesterday_file) as f:
                old = json.load(f)
                for item in old.get('bidding', []) + old.get('winning', []):
                    yesterday_ids.add(item.get('id'))
        except: pass
    todayB = sum(1 for r in allB if r['id'] not in yesterday_ids)
    todayW = sum(1 for r in allW if r['id'] not in yesterday_ids)
    todayH = sum(1 for r in allB if r['id'] not in yesterday_ids and (r.get('relevance_score') or 0) >= 70) + sum(1 for r in allW if r['id'] not in yesterday_ids and (r.get('relevance_score') or 0) >= 70)
    
    provs = Counter(); cats = Counter()
    for i in allB[:500]: 
        if i.get('province'): provs[i['province']] += 1
        if i.get('category'): cats[i['category']] += 1
    
    trends = {"bidding":[], "winning":[], "high":[]}
    now = datetime.now()
    for m in range(5, -1, -1):
        d = (now.replace(day=1) - timedelta(days=28*m)).strftime("%Y-%m")
        b = conn.execute("SELECT COUNT(*) FROM bidding_notices WHERE relevance_score>0 AND substr(fetch_date,1,7)=?",(d,)).fetchone()[0]
        w = conn.execute("SELECT COUNT(*) FROM winning_notices WHERE relevance_score>0 AND substr(fetch_date,1,7)=?",(d,)).fetchone()[0]
        h = conn.execute("SELECT COUNT(*) FROM bidding_notices WHERE relevance_score>=70 AND substr(fetch_date,1,7)=?",(d,)).fetchone()[0]
        trends["bidding"].append([d,b]); trends["winning"].append([d,w]); trends["high"].append([d,h])
    
    try:
        sys.path.insert(0,str(Path(__file__).parent))
        from competitor_tracker import get_competitor_stats, get_big_projects
        comp = get_competitor_stats(90); big = get_big_projects(500,30)
    except: comp={"competitors":[],"categories":[]}; big=[]
    
    lc = rd(conn.execute("SELECT * FROM crawl_log ORDER BY id DESC LIMIT 1").fetchone())
    conn.close()
    
    brief = {"today_total":todayB+todayW,"today_high":todayH,"top_provinces":provs.most_common(5),"top_categories":cats.most_common(5)}
    
    KEEP_NUM = ['id','relevance_score']
    KEEP_STR = ['title','url','source_site','source_department','notice_type','publish_date',
                'procurement_owner','region','province','category','budget_amount',
                'winner_company','winning_amount','content_summary','fetch_date']
    def trim(item):
        result = {}
        for k in KEEP_NUM: result[k] = item.get(k, 0) or 0
        for k in KEEP_STR: result[k] = str(item.get(k) or '')
        # is_new_today: 昨天归档中没有 → 今日真正新增（非日期字段判断）
        result['is_new_today'] = 1 if item.get('id') not in yesterday_ids else 0
        return result
    
    frontend_data = {
        "bidding": [trim(r) for r in allB], "winning": [trim(r) for r in allW],
        "brief": brief, "trends": trends, "competitors": comp, "big_projects": big,
        "total_bidding": len(allB), "total_winning": len(allW),
        "updated": datetime.now().isoformat(), "has_more": len(allB) > 50
    }
    (RD/"data.json").write_text(json.dumps(frontend_data, ensure_ascii=False))
    (RD/"data_full.json").write_text(json.dumps({"bidding":allB,"winning":allW}, ensure_ascii=False, default=str))
    
    # ★ 归档今日数据 — 供明日差集计算
    archive_dir = RD / today
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_ids = {"bidding": [{"id": r['id']} for r in allB], "winning": [{"id": r['id']} for r in allW]}
    (archive_dir / "data.json").write_text(json.dumps(archive_ids, ensure_ascii=False))
    
    # ★ 不再覆盖 index.html — 页面样式由 polish 脚本单独维护
    # html = _html(brief, lc)
    # (RD/"index.html").write_text(html)
    
    print(f"报告: {RD/'data.json'} ({len(allB)}招标+{len(allW)}中标) 归档:{today}")
    
    try:
        r = subprocess.run([sys.executable, str(Path(__file__).parent/"polish_report.py")], timeout=5, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"⚠️ polish_report 失败: {r.stderr.strip()}")
    except Exception as e:
        print(f"❌ polish_report 异常: {e}")
    # 企微推送已禁用（按用户要求）
    # try:
    #     r = subprocess.run([sys.executable,str(Path(__file__).parent/"wecom_push.py")],timeout=15,capture_output=True, text=True)
    #     if r.returncode == 0: print("✅ wecom_push 完成")
    #     else: print(f"⚠️ wecom_push 失败: {r.stderr.strip()}")
    # except Exception as e:
    #     print(f"❌ wecom_push 异常: {e}")
    print("⏸ 企微推送已禁用，跳过")

def _html(brief, lc):
    scan_time = s(lc.get('crawl_time',''))[:19] if lc else ''
    today_new = brief.get('today_total', 0)
    today_high = brief.get('today_high', 0)
    total_bid = brief.get('total_bidding', 0)
    total_win = brief.get('total_winning', 0)
    # Header site info — only show if crawl_log has data
    ss = lc.get('success_sites', 0) if lc else 0
    st = lc.get('total_sites', 0) if lc else 0
    site_html = f'<span style="margin-left:8px">站点 {ss}/{st}</span>' if st else ''
    scan_html = f'<span>扫描 {scan_time}</span>' if scan_time else ''
    
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>文鳐智投 · 数智科技投标监控</title>
<style>
:root{{--bg:#0f172a;--surface:#1e293b;--border:#334155;--text:#e2e8f0;--muted:#94a3b8;--dim:#64748b;--accent:#3b82f6;--green:#10b981;--amber:#f59e0b;--red:#ef4444;--radius:8px}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;background:var(--bg);color:var(--text);min-height:100vh;line-height:1.5}}
/* ═══ Header ═══ */
.app-header{{display:flex;align-items:center;justify-content:space-between;padding:12px 24px;background:linear-gradient(135deg,#1e293b,#0f172a);border-bottom:1px solid var(--border)}}
.header-brand{{display:flex;align-items:center;gap:12px}}
.header-brand img{{height:32px;border-radius:6px}}
.header-brand h1{{font-size:18px;font-weight:700;color:#f8fafc;letter-spacing:-0.5px}}
.header-brand .sub{{font-size:11px;color:var(--dim);margin-top:1px}}
.header-right{{display:flex;align-items:center;gap:12px;font-size:11px;color:var(--dim)}}
.header-right .dot{{width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
/* ═══ Stats Row ═══ */
.stats-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:16px 24px;max-width:1400px;margin:0 auto}}
.stat-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px 20px;display:flex;flex-direction:column;gap:4px;position:relative;transition:all .2s ease}}
.stat-card[onclick]:hover{{border-color:var(--accent);box-shadow:0 2px 12px rgba(59,130,246,.15);transform:translateY(-1px)}}
.stat-card[onclick]:active{{transform:translateY(0);box-shadow:none}}
.stat-card[onclick]::after{{content:'›';position:absolute;right:12px;top:50%;transform:translateY(-50%);font-size:18px;color:var(--dim);opacity:.4;transition:opacity .2s}}
.stat-card[onclick]:hover::after{{opacity:1;color:var(--accent)}}
.stat-card .stat-value{{font-size:28px;font-weight:800;letter-spacing:-1px;line-height:1;transition:opacity .4s ease}}
.stat-card.loading .stat-value{{opacity:.3}}
.stat-card .stat-label{{font-size:12px;color:var(--dim)}}
.stat-card.accent .stat-value{{color:var(--accent)}}
.stat-card.green .stat-value{{color:var(--green)}}
.stat-card.amber .stat-value{{color:var(--amber)}}
/* ═══ Filter Bar ═══ */
.filter-bar{{max-width:1400px;margin:0 auto;padding:0 24px 12px}}
.filter-row{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px}}
.filter-row:last-child{{margin-bottom:0}}
.search-box{{flex:1;min-width:200px;position:relative}}
.search-box input{{width:100%;padding:8px 12px 8px 34px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:13px;outline:none;transition:border-color .2s}}
.search-box input:focus{{border-color:var(--accent)}}
.search-box .search-icon{{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--dim);font-size:14px}}
select,input[type=date]{{padding:7px 10px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:12px;outline:none;cursor:pointer}}
.btn{{padding:7px 14px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);cursor:pointer;font-size:12px;white-space:nowrap;transition:all .15s;font-weight:500}}
.btn:hover{{border-color:var(--accent);color:#fff}}
.btn.primary{{background:var(--accent);border-color:var(--accent);color:#fff}}
.btn.primary:hover{{background:#2563eb}}
.btn.success{{background:var(--green);border-color:var(--green);color:#fff}}
.btn.ghost{{background:transparent;border-color:transparent}}
.btn.ghost:hover{{background:var(--surface);border-color:var(--border)}}
/* ═══ Tab Bar ═══ */
.container{{max-width:1400px;margin:0 auto;padding:0 24px 24px}}
.tab-bar{{display:flex;gap:4px;margin-bottom:12px;border-bottom:1px solid var(--border);padding-bottom:0}}
.tab-btn{{padding:8px 20px;border:none;background:transparent;color:var(--dim);cursor:pointer;font-size:13px;font-weight:600;border-bottom:2px solid transparent;transition:all .15s}}
.tab-btn.active,.tab-btn:hover{{color:#fff;border-bottom-color:var(--accent)}}
.tab-btn .badge{{display:inline-block;margin-left:6px;padding:1px 7px;border-radius:10px;font-size:10px;background:var(--surface);color:var(--dim)}}
.tab-btn.active .badge{{background:var(--accent);color:#fff}}
/* ═══ Table ═══ */
.table-wrap{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
table{{width:100%;border-collapse:collapse;font-size:13px;min-width:800px}}
thead th{{background:var(--surface);padding:10px 12px;text-align:left;font-weight:600;color:var(--muted);border-bottom:2px solid var(--border);font-size:11px;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap;cursor:pointer;user-select:none}}
thead th:hover{{color:#fff}}
thead th.w32{{width:32px;text-align:center}}
thead th.w60{{width:60px}}
thead th.w80{{width:80px}}
thead th.w100{{width:100px}}
thead th.w120{{width:120px}}
thead th[onclick]{{padding-right:18px;position:relative}}
thead th[onclick]::before{{content:'▴';position:absolute;right:4px;top:5px;font-size:11px;line-height:1;opacity:.3;pointer-events:none}}
thead th[onclick]::after{{content:'▾';position:absolute;right:4px;top:13px;font-size:11px;line-height:1;opacity:.3;pointer-events:none}}
thead th.sort-asc::before{{opacity:1;color:var(--accent)}}
thead th.sort-asc::after{{opacity:.3}}
thead th.sort-desc::after{{opacity:1;color:var(--accent)}}
thead th.sort-desc::before{{opacity:.3}}
tbody td{{padding:10px 12px;border-bottom:1px solid rgba(51,65,85,.4);vertical-align:middle}}
tbody tr{{transition:background .1s}}
tbody tr:hover{{background:rgba(59,130,246,.06)}}
td.title-cell{{max-width:360px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
td.title-cell a{{color:var(--text);text-decoration:none}}
td.title-cell a:hover{{color:var(--accent)}}
.score-bar{{display:inline-block;height:6px;border-radius:3px;min-width:4px;vertical-align:middle;margin-right:6px}}
.score-hi{{background:var(--green);width:100%}} .score-mid{{background:var(--amber);width:60%}} .score-lo{{background:var(--dim);width:35%}}
.tag-sm{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;white-space:nowrap}}
.tag-blue{{background:rgba(59,130,246,.2);color:#60a5fa}}
.tag-amber{{background:rgba(245,158,11,.2);color:#fbbf24}}
.tag-green{{background:rgba(16,185,129,.2);color:#34d399}}
.tag-gray{{background:rgba(100,116,139,.2);color:#94a3b8}}
.link-btn{{color:var(--accent);text-decoration:none;font-size:12px;font-weight:500}}
.link-btn:hover{{text-decoration:underline}}
.star{{cursor:pointer;font-size:15px;user-select:none;color:var(--dim);transition:all .15s}}
.star.on{{color:#f59e0b}}
.new-badge{{display:inline-block;padding:1px 6px;border-radius:3px;font-size:9px;font-weight:700;color:#fff;background:var(--red);margin-right:6px;vertical-align:middle;line-height:1.5}}
/* ═══ Pagination ═══ */
.pg-bar{{display:flex;justify-content:space-between;align-items:center;padding:12px 0;font-size:12px;color:var(--muted)}}
.pg-btns{{display:flex;gap:4px}}
.pg-btn{{min-width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--muted);cursor:pointer;font-size:12px;transition:all .15s}}
.pg-btn:hover{{border-color:var(--accent);color:#fff}}
.pg-btn.active{{background:var(--accent);border-color:var(--accent);color:#fff}}
.pg-btn:disabled{{opacity:.3;cursor:default}}
/* ═══ Trend / Competitor ═══ */
.trend-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin-bottom:16px}}
.trend-card{{background:var(--surface);border-radius:var(--radius);padding:16px;border:1px solid var(--border)}}
.trend-card h3{{font-size:13px;color:var(--muted);margin-bottom:10px;font-weight:600}}
/* ═══ Footer ═══ */
.app-footer{{text-align:center;padding:20px;color:var(--dim);font-size:11px;border-top:1px solid var(--border);margin-top:32px}}
.app-footer a{{color:var(--dim);text-decoration:none}}
.app-footer a:hover{{color:var(--muted)}}
/* ═══ Mobile ═══ */
@media(max-width:768px){{
.stats-row{{grid-template-columns:repeat(2,1fr);padding:12px 16px;gap:8px}}
.filter-bar,.container{{padding:0 12px 12px}}
tbody td{{padding:8px 6px;font-size:12px}}
.hide-mobile{{display:none}}
}}
@keyframes slideIn{{from{{transform:translateX(100px);opacity:0}}to{{transform:translateX(0);opacity:1}}}}
</style></head><body class="light">

<!-- ═══ Header ═══ -->
<header class="app-header">
  <div class="header-brand">
    <img src="/bidding/img/logo.png" alt="文鳐智投">
    <div>
      <h1>文鳐智投</h1>
      <div class="sub">中南电力设计院数智科技 · 投标信息智能监控</div>
    </div>
  </div>
  <div class="header-right">
    <span class="dot"></span> <span id=\"lastUpdate\">数据更新: —</span>
    {site_html}
    {scan_html}
    <button class="btn ghost" onclick="toggleTheme()" title="切换主题" style="font-size:18px;padding:4px 8px">🌓</button>
  </div>
</header>

<!-- ═══ Stats Row ═══ -->
<div class="stats-row">
  <div class="stat-card accent" onclick="statClick('total')" style="cursor:pointer">
    <div class="stat-value" id="statBidTotal">{total_bid}</div>
    <div class="stat-label">累计招标</div>
  </div>
  <div class="stat-card green" onclick="statClick('today')" style="cursor:pointer">
    <div class="stat-value" id="statToday">{today_new}</div>
    <div class="stat-label">今日新增</div>
  </div>
  <div class="stat-card amber" onclick="statClick('high')" style="cursor:pointer">
    <div class="stat-value" id="statHigh">{today_high}</div>
    <div class="stat-label">高相关项目</div>
  </div>
  <div class="stat-card" onclick="statClick('win')" style="cursor:pointer">
    <div class="stat-value" id="statWinTotal">{total_win}</div>
    <div class="stat-label">累计中标</div>
  </div>
</div>

<!-- ═══ Filter Bar ═══ -->
<div class="filter-bar">
  <div class="filter-row">
    <div class="search-box">
      <span class="search-icon">🔍</span>
      <input id="search" placeholder="搜索标题、招标单位、省份..." oninput="doFilter()">
    </div>
    <select id="fCat" onchange="doFilter()"><option value="">全部客户</option></select>
    <select id="fProv" onchange="doFilter()"><option value="">全部地域</option></select>
    <input type="number" id="fScore" placeholder="最低相关度 0-100" min="0" max="100" onchange="todayOnly=false;doFilter()" style="width:130px;padding:8px 12px;border-radius:var(--radius);border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:12px">
  </div>
  <div class="filter-row">
    <input type="date" id="dateFrom" onchange="todayOnly=false;doFilter()" title="开始日期">
    <span style="color:var(--dim);font-size:12px">至</span>
    <input type="date" id="dateTo" onchange="todayOnly=false;doFilter()" title="结束日期">
    <input type="number" id="fBudget" placeholder="预算≥万元" min="0" step="0.01" onchange="doFilter()" style="width:110px;padding:8px 12px;border-radius:var(--radius);border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:12px">
    <span style="flex:1"></span>
    <button class="btn" onclick="smartExport()" style="background:var(--accent);border-color:var(--accent);color:#fff">导出</button>
    <button class="btn" onclick="resetF()">重置</button>
  </div>
</div>

<div class="container">

<!-- ═══ Tab Bar ═══ -->
<div class="tab-bar">
  <button class="tab-btn active" id="tabBid" onclick="sw('bid')">招标<span class="badge" id="cntBid">{total_bid}</span></button>
  <button class="tab-btn" id="tabWin" onclick="sw('win')">中标<span class="badge" id="cntWin">{total_win}</span></button>
  <button class="tab-btn" id="tabStar" onclick="sw('star')">收藏<span class="badge" id="cntStar">0</span></button>
</div>

<!-- ═══ Bidding Table ═══ -->
<div id="tableBid">
  <div class="table-wrap">
    <table>
      <thead><tr>
        <th class="w32"><input type="checkbox" onclick="toggleSelectAll()" title="全选" style="cursor:pointer;accent-color:var(--accent)"></th>
        <th class="w60">序号</th>
        <th class="w80" onclick="srt('relevance_score')">相关度</th>
        <th onclick="srt('title')">项目标题</th>
        <th class="hide-mobile w100" onclick="srt('category')">客户</th>
        <th class="hide-mobile w120" onclick="srt('procurement_owner')">招标单位</th>
        <th class="w80" onclick="srt('budget_amount')">预算金额</th>
        <th class="w80" onclick="srt('province')">地域</th>
        <th class="hide-mobile w120" onclick="srt('source_site')">来源</th>
        <th class="w100" onclick="srt('publish_date')">发布日期</th>
        <th class="w60">操作</th>
      </tr></thead>
      <tbody id="tBidTb"></tbody>
    </table>
  </div>
  <div class="pg-bar" id="pgBid">
    <span id="pgInfo">显示 0 条</span>
    <div class="pg-btns" id="pgNums"></div>
  </div>
</div>

<!-- ═══ Winning Table ═══ -->
<div id="tableWin" style="display:none">
  <div class="table-wrap">
    <table>
      <thead><tr>
        <th class="w32"><input type="checkbox" onclick="toggleSelectAll()" title="全选" style="cursor:pointer;accent-color:var(--accent)"></th>
        <th class="w60">序号</th>
        <th class="w80" onclick="srt('relevance_score')">相关度</th>
        <th onclick="srt('title')">项目标题</th>
        <th onclick="srt('winner_company')">中标单位</th>
        <th class="w100" onclick="srt('winning_amount')">中标金额</th>
        <th class="hide-mobile w80" onclick="srt('province')">地域</th>
        <th class="w100" onclick="srt('publish_date')">发布日期</th>
        <th class="w60">操作</th>
      </tr></thead>
      <tbody id="tWinTb"></tbody>
    </table>
  </div>
  <div class="pg-bar" id="pgWin">
    <span id="pgInfoW">显示 0 条</span>
    <div class="pg-btns" id="pgNumsW"></div>
  </div>
</div>

</div>

<footer class="app-footer">
  © 中南电力设计院数智科技 · 文鳐智投 2026 · <a href="/bidding/changelog.html">更新日志</a>
</footer>

<script src="app.js"></script>
<script>document.addEventListener('DOMContentLoaded',function(){{init().catch(function(e){{console.error('init failed:',e);}});}});</script></body></html>"""

if __name__ == "__main__":
    generate()
