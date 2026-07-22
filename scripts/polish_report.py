#!/usr/bin/env python3
"""文鳐智投 报告抛光器 v4 — 只做必要增强，不破坏原生布局"""
from pathlib import Path

INDEX = Path("/var/www/html/bidding/index.html")

THEME_JS = """
function toggleTheme(){document.body.classList.toggle('light');var l=document.body.classList.contains('light');localStorage.setItem('theme',l?'light':'dark');}
(function(){if(localStorage.getItem('theme')==='dark'){document.body.classList.remove('light');}})();
"""

LIGHT_THEME_CSS = """
/* ═══ Light Theme — 覆盖 CSS 变量 ═══ */
body.light{--bg:#f8fafc;--surface:#fff;--border:#e2e8f0;--text:#1e293b;--muted:#475569;--dim:#64748b;background:var(--bg);color:var(--text)}
body.light .app-header{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#e2e8f0}
body.light .header-brand h1{color:#1d4ed8}
body.light .header-brand .sub{color:#64748b}
body.light .header-right{color:#64748b}
body.light .stat-card{background:#fff;border-color:#e2e8f0}
body.light .stat-card .stat-label{color:#64748b}
body.light .stat-card .stat-value{color:#1e293b}
body.light .stat-card.accent .stat-value{color:#2563eb}
body.light .stat-card.green .stat-value{color:#059669}
body.light .stat-card.amber .stat-value{color:#d97706}
body.light select,body.light input[type=date]{background:#fff;border-color:#cbd5e1;color:#1e293b}
body.light .search-box{border-color:#cbd5e1}
body.light .search-box input{background:#fff;color:#1e293b}
body.light .btn{background:#fff;border-color:#cbd5e1;color:#334155}
body.light .btn:hover{background:#f1f5f9;color:#1e293b}
body.light .btn.primary{background:#2563eb;border-color:#2563eb;color:#fff}
body.light .btn.success{background:#059669;border-color:#059669;color:#fff}
body.light .btn.ghost{background:transparent;border-color:transparent;color:#64748b}
body.light thead th{background:#f8fafc;border-color:#e2e8f0;color:#64748b}
body.light tbody td{color:#1e293b;border-color:#f1f5f9}
body.light tbody tr:hover{background:#f1f5f9}
body.light tbody tr:hover td{color:#0f172a}
body.light td.title-cell a{color:#1e293b}
body.light td.title-cell a:hover{color:#2563eb}
body.light .tab-bar{border-color:#e2e8f0}
body.light .tab-btn{color:#64748b}
body.light .tab-btn.active,.light .tab-btn:hover{color:#1d4ed8;border-bottom-color:#2563eb}
body.light .tab-btn .badge{background:#f1f5f9;color:#64748b}
body.light .tab-btn.active .badge{background:#2563eb;color:#fff}
body.light .pg-btn{background:#fff;border-color:#cbd5e1;color:#475569}
body.light .pg-btn:hover{background:#f1f5f9;color:#1e293b;border-color:#94a3b8}
body.light .pg-btn.active{background:#2563eb;border-color:#2563eb;color:#fff}
body.light .pg-bar{color:#64748b}
body.light .trend-card{background:#fff;border-color:#e2e8f0}
body.light .trend-card h3{color:#475569}
body.light .app-footer{border-color:#e2e8f0;color:#94a3b8}
body.light .comp-item{border-color:#f1f5f9}
body.light .tag-blue{background:rgba(37,99,235,.1);color:#2563eb}
body.light .tag-amber{background:rgba(217,119,6,.1);color:#d97706}
body.light .tag-green{background:rgba(5,150,105,.1);color:#059669}
body.light .tag-gray{background:rgba(100,116,139,.1);color:#475569}
body.light .link-btn{color:#2563eb}
body.light .star{color:#94a3b8}
body.light .star.on{color:#d97706}
body.light .score-hi{background:#10b981} body.light .score-mid{background:#f59e0b} body.light .score-lo{background:#94a3b8}
body.light .filter-row span{color:#64748b}
"""

def polish():
    html = INDEX.read_text(encoding="utf-8")
    modified = False
    
    # 1. Light theme CSS (idempotent)
    if 'Light Theme' not in html:
        if '</style>' in html:
            html = html.replace("</style>", LIGHT_THEME_CSS + "\n</style>")
            modified = True
    
    # 2. Theme toggle JS + init() wrapper (idempotent)
    if 'function toggleTheme' not in html:
        if 'init()' in html:
            # Replace init() call with theme JS + DOMContentLoaded wrapper
            html = html.replace(
                'init().catch',
                THEME_JS + '\ninit().catch'
            )
            modified = True
    
    # 3. Chat widget (idempotent)
    if 'chat-widget.css' not in html:
        html = html.replace("</head>", '<link rel="stylesheet" href="/bidding/chat-widget.css?v=5">\n</head>')
        modified = True
    if 'chat-widget.js' not in html:
        html = html.replace("</body>", '<script src="/bidding/chat-widget.js?v=5"></script>\n</body>')
        modified = True
    
    # 4. Favicon + OG tags (idempotent)
    if 'favicon-32x32.png' not in html:
        favicon_html = '<link rel="icon" type="image/png" sizes="32x32" href="/bidding/favicon-32x32.png">\n<link rel="icon" type="image/x-icon" href="/bidding/favicon.ico">\n<link rel="apple-touch-icon" sizes="180x180" href="/bidding/apple-touch-icon.png">\n'
        html = html.replace('<title>', favicon_html + '<title>')
        modified = True
    if 'og:title' not in html:
        og_html = '<meta property="og:title" content="文鳐智投 · 数智科技投标监控">\n<meta property="og:description" content="中南电力设计院数智科技 — 智能采集、AI评分、可视化投标监控看板">\n<meta property="og:image" content="https://www.yfzx.online/bidding/img_gen/og-share.png">\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n<meta property="og:url" content="https://www.yfzx.online/bidding/">\n<meta property="og:type" content="website">\n<meta property="og:site_name" content="文鳐智投">\n'
        html = html.replace('<title>', og_html + '<title>')
        modified = True
    
    # 5. Desktop filter bar restructuring — search-row + filter-scroll-wrapper + export/reset aligned right
    #    After report_generator regenerates, the bar is flat. Restructure it.
    if 'class="filter-scroll-wrapper"' not in html:
        # Wrap search-box in search-row
        html = html.replace(
            '<div class="filter-bar">\n  <div class="filter-row">\n    <div class="search-box">',
            '<div class="filter-bar">\n  <div class="search-row">\n    <div class="search-box">')
        # Close search-row after search-box, open filter-scroll-wrapper > filter-row
        html = html.replace(
            '      <input id="search" placeholder="搜索标题、招标单位、省份..." oninput="doFilter()">\n    </div>',
            '      <input id="search" placeholder="搜索标题、招标单位、省份...">\n      <button class="search-btn" id="searchBtn" type="button">搜索</button>\n    </div>\n  </div>\n  <div class="filter-scroll-wrapper">\n  <div class="filter-row">')
        modified = True
    # Ensure spacer + export/reset are siblings of filter-scroll-wrapper, not inside filter-row
    if '<!-- /filter-scroll-wrapper -->' not in html:
        # Close filter-row and filter-scroll-wrapper before | separator, add flex spacer
        html = html.replace(
            '<span style="flex:1"></span>\n    <button class="btn" onclick="smartExport()"',
            '<span style="flex:1;min-width:0"></span>\n  </div>\n  </div><!-- /filter-scroll-wrapper -->\n    <span style="flex:1;min-width:8px"></span>\n    <span style="color:var(--border);font-size:16px;flex-shrink:0">|</span>\n    <span style="font-size:11px;color:var(--dim);flex-shrink:0">每页</span>\n    <div class="pg-btns" id="psSelector"></div>\n    <button class="btn" onclick="smartExport()"')
        modified = True
    # Desktop CSS: overflow visible, tight gap, hide kebab/pullIndicator, wider search
    if '.filter-scroll-wrapper{flex:1;min-width:0;overflow:hidden}' in html:
        html = html.replace(
            '.filter-scroll-wrapper{flex:1;min-width:0;overflow:hidden}',
            '.filter-scroll-wrapper{flex:1;min-width:0;overflow:visible}')
        modified = True
    if '.filter-row{display:flex;gap:6px;align-items:center;flex-wrap:nowrap}' in html:
        html = html.replace('gap:6px', 'gap:4px')
        modified = True
    if '.kebab-btn{' in html and 'display:none!important' not in html:
        html = html.replace('.kebab-btn{', '.kebab-btn{display:none!important;')
        modified = True
    if '#pullIndicator' in html and '@media(min-width:769px){#pullIndicator{display:none}}' not in html:
        html = html.replace(
            'body.dark #pullIndicator.ready{',
            '@media(min-width:769px){#pullIndicator{display:none}}body.dark #pullIndicator.ready{')
        modified = True
    if '.search-row{flex:0 1 240px;min-width:180px}' in html:
        html = html.replace(
            '.search-row{flex:0 1 240px;min-width:180px}',
            '.search-row{flex:0 1 340px;min-width:220px}')
        modified = True
    
    # 6. V1.33 features: more-filters toggle, density toggle, score legend, hover preview
    ENHANCE_CSS = '''
/* ═══ Compact density mode ═══ */
body.dense tbody td{padding:4px 6px!important;font-size:11px!important}
body.dense thead th{padding:6px 4px!important;font-size:11px!important}
body.dense .score-bar{height:4px!important}
body.dense .tag-sm{font-size:10px!important;padding:1px 6px!important}
body.dense .star{font-size:13px!important}
body.dense .link-btn{font-size:11px!important}
body.dense tbody tr{height:32px!important}
/* ═══ Score legend + hover preview light ═══ */
body.light .score-legend-tip{background:#fff!important;color:#1e293b!important;border:1px solid #e2e8f0!important}
.hover-preview-tip{font-family:inherit;pointer-events:none}
body.light .hover-preview-tip{background:#fff!important;color:#1e293b!important;border-color:#e2e8f0!important}
.header-right{gap:6px!important}
/* ── Mobile: hide filter-bar extra children ── */
@media(max-width:768px){
.filter-bar > span:not(.search-icon),
.filter-bar > .pg-btns{display:none!important}
.filter-bar > .btn{display:none!important}
.filter-bar > .btn[onclick*="smartExport"]{display:inline-flex!important}
/* Keep filter-scroll-wrapper scrollable on mobile */
.filter-scroll-wrapper{overflow-x:auto!important;-webkit-overflow-scrolling:touch}
/* Density toggle hidden on mobile */
#densityBtn{display:none!important}
/* Dense mode safety net: never shrink mobile cards */
body.dense tr.data-row{padding:18px 16px!important;height:auto!important}
body.dense tbody td{padding:0!important;font-size:13px!important}
body.dense .star{font-size:18px!important}
}/* V1.33-enhance */
/* ── Global: prevent horizontal overflow ── */
html,body{overflow-x:hidden}'''
    if 'V1.33-enhance' not in html:
        html = html.replace('</style>', ENHANCE_CSS + '\n</style>')
        modified = True
    # Inject mobile card layout + horizontal scroll (V1.35 fix)
    MOBILE_CARD_CSS = '''/* ── Mobile: card grid layout + horizontal scroll ── */
@media(max-width:768px){
/* ── Viewport constraint — prevent horizontal scroll ── */
body{overflow-x:hidden}
.stats-row,.filter-bar,.container,.app-header,.tab-bar{max-width:100vw!important;width:100%!important;box-sizing:border-box}
/* Card layout (Grid on tr) */
thead{display:none}
tbody tr.data-row{display:grid;grid-template-columns:1fr auto auto auto;padding:16px 14px;margin-bottom:10px;background:var(--surface);border:1px solid var(--border);border-radius:14px;position:relative;gap:6px 10px}
tbody tr.data-row td{display:block;padding:0;border:none;font-size:13px}
td.title-cell{grid-column:1/-1;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;font-weight:500;font-size:14px;line-height:1.4}
td.title-cell a{font-size:inherit;line-height:inherit;color:var(--text)}
tr.empty-msg{display:flex!important;justify-content:center;padding:48px 20px!important;background:var(--surface)!important;border-radius:14px!important}
/* Filter horizontal scroll */
.filter-scroll-wrapper{overflow-x:auto!important;-webkit-overflow-scrolling:touch;scrollbar-width:none}
.filter-scroll-wrapper::-webkit-scrollbar{display:none}
.filter-row{flex-wrap:nowrap;gap:8px}
/* Search row full width */
.search-row{width:100%}
.search-box{width:100%}
.search-box input{height:44px;font-size:16px}
.search-btn{height:44px;padding:0 20px;font-size:14px}
/* Filter pill style */
.filter-row select,.filter-row input[type=date],.filter-row input[type=number]{height:34px;border-radius:17px;background:var(--surface);border:1px solid var(--border);font-size:13px;padding:0 12px;flex-shrink:0}
body.light .filter-row select,body.light .filter-row input[type=date],body.light .filter-row input[type=number]{background:#e8e8ed;border:none}
}/* V1.35-mobile-card */'''
    if 'V1.35-mobile-card' not in html:
        html = html.replace('</style>', MOBILE_CARD_CSS + '\n</style>')
        modified = True
    # Inject desktop single-row filter bar CSS (V1.35 fix)
    DESKTOP_FILTER_CSS = '''/* ── Desktop: single-row compact filter bar (all inline) ── */
@media(min-width:769px){
  .filter-bar{display:flex;flex-wrap:nowrap;align-items:center;gap:6px;overflow-x:auto}
  .search-row{flex-shrink:0}
  .search-box{display:flex;align-items:center;flex:1.2;min-width:240px;max-width:400px;position:relative}
  .search-box input{flex:1;height:36px;box-sizing:border-box;border-radius:6px 0 0 6px;padding:8px 12px 8px 34px;font-size:13px}
  .search-btn{height:36px;flex-shrink:0;padding:0 16px;border-radius:0 6px 6px 0;border:1px solid var(--border);border-left:none;background:var(--accent);color:#fff;cursor:pointer;font-size:13px;white-space:nowrap}
  .search-btn:hover{background:#2563eb}
  .search-box .search-icon{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--dim);font-size:14px;z-index:1;pointer-events:none}
  .filter-scroll-wrapper{display:flex!important;flex-wrap:nowrap;align-items:center;gap:6px;overflow:visible!important;flex-shrink:0}
  .filter-scroll-wrapper .filter-row{display:contents}
  .filter-scroll-wrapper .filter-row > *{flex-shrink:0}
  .filter-scroll-wrapper .filter-row span[style*="flex:1"]{display:none}
  select,input[type=date],input[type=number]{height:36px;box-sizing:border-box}
}/* V1.35-filter-row */'''
    if 'V1.35-filter-row' not in html:
        html = html.replace('</style>', DESKTOP_FILTER_CSS + '\n</style>')
        modified = True
    # Stage 1: Fix old template that has static "系统运行中" instead of lastUpdate
    if '系统运行中' in html and 'id="lastUpdate"' not in html:
        html = html.replace(
            '<span class="dot"></span> 系统运行中',
            '<span class="dot"></span> <span id="lastUpdate">数据更新: —</span>')
        modified = True
    # Stage 2: Add density toggle button in header (requires lastUpdate to exist)
    if 'densityBtn' not in html and 'id="lastUpdate"' in html:
        html = html.replace(
            '<span class="dot"></span> <span id="lastUpdate">',
            '<span class="dot"></span> <span id="lastUpdate">\n    <button class="btn ghost" id="densityBtn" onclick="toggleDensity()" title="切换行密度" style="font-size:14px;padding:4px 8px">≡</button>')
        modified = True
    # Add ⓘ legend to relevance_score headers
    if 'showScoreLegend' not in html:
        html = html.replace(
            '<th class="w80" onclick="srt(\'relevance_score\')">相关度</th>',
            '<th class="w80" onclick="srt(\'relevance_score\')">相关度 <span onclick="event.stopPropagation();showScoreLegend(event)" style="cursor:help;font-size:10px;opacity:.5" title="评分说明">ⓘ</span></th>')
        modified = True
    
    if modified:
        INDEX.write_text(html, encoding="utf-8")
        # Safely fix file permissions WITHOUT touching directories (644 on dirs kills x-bit → nginx 403)
        import os, subprocess
        for f in Path("/var/www/html/bidding").glob("*"):
            if f.is_file():
                f.chmod(0o644)
        for d in ["/var/www/html/bidding/img", "/var/www/html/bidding/img_gen"]:
            subprocess.run(["chmod", "755", d])
        print(f"✅ 报告抛光完成: {INDEX}")
    else:
        print(f"⏭️ 报告已抛光，跳过: {INDEX}")

if __name__ == "__main__":
    polish()
