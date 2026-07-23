// 文鳐智投 v7 — 客户分类
let allB = [], allW = [], tab = "bid", pg = 1, ps = 50, sf = "relevance_score", sd = -1;
let brief = {}, trends = {}, competitors = {}, bigs = [];
let starOnly = false;

async function init() {
    const r = await fetch("/bidding/data.json");
    const d = await r.json();
    allB = d.bidding || [];
    allW = d.winning || [];
    brief = d.brief || {};
    trends = d.trends || {};
    competitors = d.competitors || {};
    bigs = d.big_projects || [];
    document.getElementById("cntBid").textContent = d.total_bidding || allB.length;
    document.getElementById("cntWin").textContent = d.total_winning || allW.length;
    const cats = new Set(), ps2 = new Set();
    [...allB, ...allW].forEach(i => {
        if (i.category) cats.add(i.category);
        if (i.province) ps2.add(i.province);
    });
    [["fCat", cats], ["fProv", ps2]].forEach(([id, s]) => {
        const sel = document.getElementById(id);
        if (!sel) return;
        // 清空重建 — 确保「其他」永远排在最后
        const defaultLabel = id === "fCat" ? "全部客户" : "全部地域";
        sel.innerHTML = "";
        const allOpt = document.createElement("option");
        allOpt.value = ""; allOpt.textContent = defaultLabel;
        sel.appendChild(allOpt);
        // 排序: 包含「其他」的永远垫底, 其余按拼音
        const sorted = [...s].sort((a, b) => {
            const ao = a.includes("其他"), bo = b.includes("其他");
            if (ao && !bo) return 1;
            if (!ao && bo) return -1;
            return a.localeCompare(b, "zh");
        });
        sorted.forEach(v => {
            const o = document.createElement("option");
            o.value = v; o.textContent = v;
            sel.appendChild(o);
        });
    });
    updateBriefing();
    renderTrends();
    renderComp();
    restoreFilters();  // 恢复上次的筛选条件
    doFilter();
}

function updateBriefing() {
    const el = document.getElementById("briefing");
    // 新数据提示
    const lastVisit = localStorage.getItem("wenyaozhitou_last_visit");
    const now = new Date().toISOString();
    localStorage.setItem("wenyaozhitou_last_visit", now);
    let freshBadge = "";
    if (brief && brief.today_total > 0 && lastVisit) {
        const sinceLast = new Date(now) - new Date(lastVisit);
        if (sinceLast > 3600000) { // >1小时 = 可能有新数据
            freshBadge = ' <span style="background:#10b981;color:#fff;font-size:10px;padding:1px 6px;border-radius:8px;animation:pulse 2s infinite">🆕 新数据</span>';
        }
    }
    if (!brief || !brief.today_total) {
        el.innerHTML = '📊 今日暂无新数据 | <span class="tag" onclick="document.getElementById(\'dateFrom\').value=\'\';document.getElementById(\'dateTo\').value=\'\';doFilter()">查看全部累计</span>' + freshBadge;
        return;
    }
    let h = "📊 <b>今日发现 " + brief.today_total + " 条</b>";
    if (brief.today_high > 0) h += ' 其中<span class="hi">🟢 ' + brief.today_high + ' 个高相关</span>';
    if (brief.top_provinces && brief.top_provinces.length > 0) {
        h += " | 📍";
        brief.top_provinces.forEach(p => {
            h += ' <span class="tag" onclick="toggleFilter(\'fProv\',\'' + p[0] + '\',this)">' + p[0] + '(' + p[1] + ')</span>';
        });
    }
    if (brief.top_categories && brief.top_categories.length > 0) {
        h += " | 🏢";
        brief.top_categories.forEach(c => {
            h += ' <span class="tag" onclick="toggleFilter(\'fCat\',\'' + c[0].replace(/'/g, "\\'") + '\',this)">' + c[0] + '(' + c[1] + ')</span>';
        });
    }
    el.innerHTML = h;
}

// ═══════════════ SVG 趋势图表引擎 — 每张卡片完全独立 ═══════════════
const CHART_COLORS = { bidding: "#3b82f6", winning: "#f59e0b", high: "#10b981" };
const CHART_TITLES = { bidding: "📋 月度招标数", winning: "🏆 月度中标数", high: "🟢 高相关项目数" };
const CHART_IDS = { bidding: "trendBid", winning: "trendWin", high: "trendHigh" };

const chartModes = new Map(); // Map<cardId, "bar"|"line"> 确保完全隔离

function toggleChartMode(cardId) {
    const cur = chartModes.get(cardId) || "bar";
    chartModes.set(cardId, cur === "line" ? "bar" : "line");
    renderTrends();
}
function getChartMode(cardId) {
    return chartModes.get(cardId) || "bar";
}

function renderTrends() {
    ["bidding", "winning", "high"].forEach(k => {
        const data = trends[k];
        if (!data || !data.length) return;
        const cardId = CHART_IDS[k];
        const el = document.getElementById(cardId);
        if (!el) return;
        const mode = getChartMode(cardId);
        const btnBar = `<button class="chart-btn${mode==='bar'?' ac':''}" onclick="toggleChartMode('${cardId}')">📊</button>`;
        const btnLine = `<button class="chart-btn${mode==='line'?' ac':''}" onclick="toggleChartMode('${cardId}')">📈</button>`;
        const svg = mode === "bar" ? renderBarSvg(data, CHART_COLORS[k]) : renderLineSvg(data, CHART_COLORS[k]);
        el.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <span style="font-size:12px;color:#94a3b8">${CHART_TITLES[k]}</span>
            <span>${btnBar}${btnLine}</span>
        </div>${svg}`;
    });
}

function renderBarSvg(data, color) {
    const W = 320, H = 160, pad = { t: 10, r: 10, b: 30, l: 10 };
    const max = Math.max(...data.map(d => d[1]), 1);
    const bw = (W - pad.l - pad.r) / data.length;
    const bars = data.map((d, i) => {
        const h = Math.max(d[1] / max * (H - pad.t - pad.b), 2);
        const x = pad.l + i * bw + bw * 0.15;
        const y = H - pad.b - h;
        const rx = Math.min(bw * 0.15, 3);
        const label = d[0].slice(2);
        return `<g>
            <rect x="${x}" y="${y}" width="${bw * 0.7}" height="${h}" rx="${rx}" fill="${color}" opacity="0.85">
                <animate attributeName="height" from="0" to="${h}" dur="0.5s" fill="freeze"/>
                <animate attributeName="y" from="${H - pad.b}" to="${y}" dur="0.5s" fill="freeze"/>
            </rect>
            <text x="${x + bw * 0.35}" y="${y - 4}" text-anchor="middle" font-size="9" fill="${color}" font-weight="600">${d[1] || ''}</text>
            <text x="${x + bw * 0.35}" y="${H - 8}" text-anchor="middle" font-size="9" fill="#64748b">${label}</text>
        </g>`;
    }).join('');
    return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;max-height:200px">${bars}
        <line x1="${pad.l}" y1="${H - pad.b}" x2="${W - pad.r}" y2="${H - pad.b}" stroke="#334155" stroke-width="0.5"/>
    </svg>`;
}

function renderLineSvg(data, color) {
    const W = 320, H = 160, pad = { t: 20, r: 15, b: 30, l: 35 };
    const pw = (W - pad.l - pad.r) / Math.max(data.length - 1, 1);
    const max = Math.max(...data.map(d => d[1]), 1);
    const range = H - pad.t - pad.b;
    
    // 网格线
    let grid = '';
    for (let i = 0; i <= 4; i++) {
        const y = pad.t + (range * i / 4);
        grid += `<line x1="${pad.l}" y1="${y}" x2="${W - pad.r}" y2="${y}" stroke="#334155" stroke-width="0.3" stroke-dasharray="3,3"/>
            <text x="${pad.l - 4}" y="${y + 3}" text-anchor="end" font-size="8" fill="#475569">${Math.round(max * (4 - i) / 4)}</text>`;
    }
    
    // Y轴
    grid += `<line x1="${pad.l}" y1="${pad.t}" x2="${pad.l}" y2="${H - pad.b}" stroke="#334155" stroke-width="0.5"/>`;
    
    // 折线路径
    const points = data.map((d, i) => {
        const x = pad.l + i * pw;
        const y = pad.t + range * (1 - d[1] / max);
        return `${x},${y}`;
    });
    const pathD = points.map((p, i) => i === 0 ? `M${p}` : `L${p}`).join(' ');
    
    // 填充区域
    const areaD = pathD + ` L${pad.l + (data.length - 1) * pw},${H - pad.b} L${pad.l},${H - pad.b} Z`;
    
    // 数据点
    const dots = data.map((d, i) => {
        const [x, y] = points[i].split(',');
        const label = d[0].slice(2);
        return `<g>
            <circle cx="${x}" cy="${y}" r="4" fill="${color}" stroke="#fff" stroke-width="1.5">
                <animate attributeName="r" from="0" to="4" dur="0.4s" fill="freeze"/>
            </circle>
            <text x="${x}" y="${H - 8}" text-anchor="middle" font-size="9" fill="#64748b">${label}</text>
            <text x="${x}" y="${y - 8}" text-anchor="middle" font-size="9" fill="${color}" font-weight="600">${d[1]}</text>
        </g>`;
    }).join('');
    
    return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;max-height:200px">
        ${grid}
        <path d="${areaD}" fill="${color}" opacity="0.08"/>
        <path d="${pathD}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round"/>
        ${dots}
    </svg>`;
}

function renderComp() {
    // 空态处理
    if (!competitors.categories || !competitors.categories.length) {
        document.getElementById("compCat").innerHTML = '<div style="color:#475569;padding:16px">暂无竞品分类数据</div>';
    } else {
        document.getElementById("compCat").innerHTML = competitors.categories.map(c =>
            '<div class="comp-item"><span>' + c.name + '</span><span style="color:#60a5fa;font-weight:600">' + c.count + '</span></div>'
        ).join('');
    }
    if (!competitors.competitors || !competitors.competitors.length) {
        document.getElementById("compTop").innerHTML = '<div style="color:#475569;padding:16px">暂无中标排行数据</div>';
    } else {
        document.getElementById("compTop").innerHTML = competitors.competitors.slice(0, 10).map((c, i) =>
            '<div class="comp-item"><span>' + (i + 1) + '. ' + c.company + '</span><span class="cat">' + c.category + '</span><span style="color:#f59e0b">' + c.count + '次</span></div>'
        ).join('');
    }
    if (bigs && bigs.length > 0) {
        document.getElementById("bigProj").innerHTML = bigs.slice(0, 8).map(b =>
            '<div class="comp-item"><span title="' + esc(b.title) + '">💰' + b.amount_wan + '万</span><span>' + esc(b.winner || '').substring(0, 15) + '</span><span style="color:#64748b;font-size:10px">' + b.date + '</span></div>'
        ).join('');
    } else {
        document.getElementById("bigProj").innerHTML = '<div style="color:#475569;padding:16px">暂无≥500万项目</div>';
    }
}

// ═══════════════ 多选标签交互 ═══════════════
function toggleFilter(selectId, value) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    const opt = [...sel.options].find(o => o.value === value);
    if (!opt) return;
    // 切换：已选中→取消，未选中→追加
    if (opt.selected) {
        opt.selected = false;
    } else {
        // 如选中「全部」，先取消「全部」
        const allOpt = [...sel.options].find(o => o.value === "");
        if (allOpt && allOpt.selected) allOpt.selected = false;
        opt.selected = true;
    }
    // 强制刷新原生列表盒视觉 + 触发 saveFilters
    sel.dispatchEvent(new Event("change", { bubbles: true }));
    updateTagHighlights();
    doFilter();
}

function updateTagHighlights() {
    const catVals = getSelectedValues("fCat");
    const provVals = getSelectedValues("fProv");
    document.querySelectorAll(".brief .tag").forEach(function(tag) {
        var oc = tag.getAttribute("onclick") || "";
        var m = oc.match(/toggleFilter\('(fCat|fProv)','([^']+)'\)/);
        if (m) {
            var vals = m[1] === "fCat" ? catVals : provVals;
            tag.classList.toggle("ac", vals.includes(m[2]));
        }
    });
}

function getSelectedValues(selectId) {
    const sel = document.getElementById(selectId);
    if (!sel) return [];
    // 过滤掉空值「全部客户/全部地域」
    return [...sel.selectedOptions].map(o => o.value).filter(v => v !== "");
}

function getFilt() {
    let d = tab === "bid" ? [...allB] : [...allW];
    const q = (document.getElementById("search")?.value || "").toLowerCase();
    if (q) {
        d = d.filter(i =>
            (i.title || "").toLowerCase().includes(q) ||
            (i.procurement_owner || "").toLowerCase().includes(q) ||
            (i.winner_company || "").toLowerCase().includes(q) ||
            (i.source_site || "").toLowerCase().includes(q) ||
            (i.category || "").toLowerCase().includes(q)
        );
        const qa = document.getElementById("qaResult");
        if (q.length >= 1 && d.length > 0) {
            qa.style.display = "block";
            qa.innerHTML = '🔍 "<b>' + q + '</b>" → <b>' + d.length + '</b> 条 | 🟢高:' + d.filter(i => i.relevance_score >= 7).length + ' | 📍湖北:' + d.filter(i => i.province === "湖北").length;
        } else {
            qa.style.display = "none";
        }
    }
    const sc = parseFloat(document.getElementById("fScore")?.value || 0);
    if (sc) d = d.filter(i => i.relevance_score >= sc);
    const cats = getSelectedValues("fCat");
    if (cats.length > 0) d = d.filter(i => cats.includes(i.category));
    const provs = getSelectedValues("fProv");
    if (provs.length > 0) d = d.filter(i => provs.includes(i.province));
    const df = document.getElementById("dateFrom")?.value;
    if (df) d = d.filter(i => (i.fetch_date || i.publish_date || "") >= df);
    const dt = document.getElementById("dateTo")?.value;
    if (dt) d = d.filter(i => (i.fetch_date || i.publish_date || "") <= dt + "T23:59:59");
    return d;
}

function srt(f) {
    if (sf === f) sd = -sd;
    else { sf = f; sd = -1; }
    doFilter();
}

function doFilter() {
    if (tab === "trend") { renderTrends(); return; }
    if (tab === "comp") { renderComp(); return; }
    let data = getFilt();
    if (starOnly) {
        const stars = getStars();
        data = data.filter(i => stars.includes(String(i.id)));
    }
    data.sort((a, b) => {
        let va = a[sf] || "", vb = b[sf] || "";
        if (typeof va === "string") va = va.toLowerCase();
        if (typeof vb === "string") vb = vb.toLowerCase();
        return va > vb ? sd : va < vb ? -sd : 0;
    });
    const ti = tab === "bid" ? "Bid" : "Win";
    const el = document.getElementById("c" + ti);
    if (el) el.textContent = data.length;
    document.getElementById("cnt").textContent = "显示 " + Math.min(data.length, pg * ps) + " 条 / 共 " + data.length + " 条";
    const tp = Math.ceil(data.length / ps);
    pg = Math.min(pg, tp || 1);
    const st = (pg - 1) * ps;
    const page = data.slice(st, st + ps);
    const tb = document.getElementById("t" + ti + "Tb");
    const chkAllId = tab === "bid" ? "checkAllBid" : "checkAllWin";
    tb.innerHTML = page.map((i, idx) => {
        const sc = i.relevance_score || 0;
        const cl = sc >= 7 ? "score-hi" : (sc >= 4 ? "score-mid" : "score-lo");
        const cat = i.category || "⚪ 其他";
        const starred = isStarred(i.id);
        const star = `<span style="cursor:pointer;font-size:14px" onclick="event.stopPropagation();toggleStar(${i.id})">${starred ? '⭐' : '☆'}</span>`;
        const newBadge = isNew(i) ? ' <span style="background:#ef4444;color:#fff;font-size:9px;padding:1px 4px;border-radius:2px;vertical-align:middle">NEW</span>' : '';
        if (tab === "bid") {
            return '<tr><td style="text-align:center"><input type="checkbox" class="row-check" data-id="' + i.id + '" onchange="onCheckChange(\'' + chkAllId + '\')"></td>' +
                '<td style="text-align:center;color:#475569;font-size:10px">' + (st + idx + 1) + '</td>' +
                '<td class="' + cl + '">' + sc.toFixed(1) +
                '</td><td title="' + esc(i.title) + '">' + star + esc((i.title || "").substring(0, 48)) + newBadge +
                '</td><td class="hide-mobile">' + cat +
                '</td><td class="hide-mobile">' + (i.region || i.province || "—") +
                '</td><td>' + esc((i.source_site || "").substring(0, 15)) +
                '</td><td>' + (i.publish_date || i.fetch_date || "").substring(0, 10) +
                '</td><td><a href="' + url_fix(i.url) + '" target="_blank">查看</a></td></tr>';
        } else {
            return '<tr><td style="text-align:center"><input type="checkbox" class="row-check" data-id="' + i.id + '" onchange="onCheckChange(\'' + chkAllId + '\')"></td>' +
                '<td style="text-align:center;color:#475569;font-size:10px">' + (st + idx + 1) + '</td>' +
                '<td class="' + cl + '">' + sc.toFixed(1) +
                '</td><td title="' + esc(i.title) + '">' + star + esc((i.title || "").substring(0, 43)) + newBadge +
                '</td><td>' + esc((i.winner_company || "").substring(0, 18)) +
                '</td><td class="hide-mobile">' + cat +
                '</td><td class="hide-mobile">' + (i.region || i.province || "—") +
                '</td><td>' + (i.publish_date || i.fetch_date || "").substring(0, 10) +
                '</td><td><a href="' + url_fix(i.url) + '" target="_blank">查看</a></td></tr>';
        }
    }).join('');
    const pd = document.getElementById("pg" + ti);
    let ph = "";
    if (tp > 1) {
        ph += '<button onclick="pg=1;doFilter()"' + (pg === 1 ? " disabled" : "") + '>⏮</button>';
        ph += '<button onclick="pg=' + Math.max(1, pg - 1) + ';doFilter()"' + (pg === 1 ? " disabled" : "") + '>◀</button>';
        for (let p = Math.max(1, pg - 2); p <= Math.min(tp, pg + 2); p++) {
            ph += '<span class="pn' + (p === pg ? " ac" : "") + '" onclick="pg=' + p + ';doFilter()">' + p + '</span>';
        }
        ph += '<button onclick="pg=' + Math.min(tp, pg + 1) + ';doFilter()"' + (pg === tp ? " disabled" : "") + '>▶</button>';
        ph += '<button onclick="pg=' + tp + ';doFilter()"' + (pg === tp ? " disabled" : "") + '>⏭</button>';
    }
    pd.innerHTML = ph;
}

function sw(t) {
    tab = t;
    pg = 1;
    ["Bid", "Win"].forEach(x => {
        document.getElementById("tab" + x).classList.toggle("ac", t === x.toLowerCase());
        document.getElementById("table" + x).style.display = t === x.toLowerCase() ? "" : "none";
    });
    document.getElementById("tableTrend").style.display = t === "trend" ? "" : "none";
    document.getElementById("tableComp").style.display = t === "comp" ? "" : "none";
    document.getElementById("tabTrend").classList.toggle("ac", t === "trend");
    document.getElementById("tabComp").classList.toggle("ac", t === "comp");
    doFilter();
}

function resetF() {
    ["search", "fScore", "fCat", "fProv", "dateFrom", "dateTo"].forEach(id => {
        const e = document.getElementById(id);
        if (e) e.value = "";
    });
    starOnly = false;
    const btnStar = document.getElementById("btnStar");
    if (btnStar) btnStar.classList.remove("ac");
    pg = 1;
    sf = "relevance_score";
    sd = -1;
    doFilter();
}

function esc(t) {
    return (t || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function url_fix(u) {
    if (!u || u.startsWith("javascript:")) return "/bidding/";
    return u;
}

function exportExcel() {
    try {
    let data = getFilt();
    if (starOnly) data = data.filter(i => getStars().map(String).includes(String(i.id)));
    const checked = [...document.querySelectorAll('.row-check:checked')].map(cb => cb.dataset.id);
    if (checked.length > 0) data = data.filter(i => checked.includes(i.id));
    if (!data.length) { alert("没有数据可导出"); return; }
    const cols = tab === "bid" ?
        ["相关性", "标题", "客户分类", "地域", "来源网站", "发布日期", "链接"] :
        ["相关性", "标题", "中标单位", "客户分类", "地域", "来源网站", "发布日期", "链接"];
    const keys = tab === "bid" ?
        ["relevance_score", "title", "category", "province", "source_site", "publish_date", "url"] :
        ["relevance_score", "title", "winner_company", "category", "province", "source_site", "publish_date", "url"];
    let csv = "\uFEFF" + cols.join(",") + "\n";
    data.forEach(i => {
        csv += keys.map(k => '"' + (esc(i[k] || "")).replace(/"/g, '""') + '"').join(",") + "\n";
    });
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "bidding_export_" + new Date().toISOString().slice(0, 10) + ".csv";
    a.click();
    } catch(e) { alert("\u5bfc\u51fa\u5931\u8d25: " + e.message); }
}

// ═══════════════ Esc 清除搜索 + 键盘快捷键 ═══════════════
document.addEventListener("keydown", e => {
    if (e.key === "/" && document.activeElement !== document.getElementById("search")) {
        e.preventDefault();
        document.getElementById("search").focus();
    }
    if (e.key === "Escape") {
        const s = document.getElementById("search");
        if (s && document.activeElement === s) {
            s.value = "";
            s.blur();
            doFilter();
        }
    }
});

// ═══════════════ 收藏筛选 ═══════════════
function swStar() {
    starOnly = !starOnly;
    const btn = document.getElementById("btnStar");
    if (btn) btn.classList.toggle("ac", starOnly);
    pg = 1;
    doFilter();
}

// ═══════════════ 勾选全选 ═══════════════
function toggleAll(cb) {
    document.querySelectorAll('.row-check').forEach(c => { c.checked = cb.checked; });
}
function onCheckChange(allId) {
    const allCb = document.getElementById(allId);
    if (!allCb) return;
    const checked = document.querySelectorAll('.row-check:checked').length;
    const total = document.querySelectorAll('.row-check').length;
    allCb.checked = checked === total;
    allCb.indeterminate = checked > 0 && checked < total;
}

// ═══════════════ 筛选条件记忆 ═══════════════
const FILTER_KEY = "wenyaozhitou_filters";
function saveFilters() {
    const cats = getSelectedValues("fCat");
    const provs = getSelectedValues("fProv");
    const f = {
        search: document.getElementById("search")?.value || "",
        fScore: document.getElementById("fScore")?.value || "",
        fCat: cats,
        fProv: provs,
        dateFrom: document.getElementById("dateFrom")?.value || "",
        dateTo: document.getElementById("dateTo")?.value || "",
        tab: tab,
        sf: sf, sd: sd
    };
    localStorage.setItem(FILTER_KEY, JSON.stringify(f));
}
function restoreFilters() {
    try {
        const f = JSON.parse(localStorage.getItem(FILTER_KEY));
        if (!f) return;
        if (f.tab) sw(f.tab);
        if (f.fScore) document.getElementById("fScore").value = f.fScore;
        // 恢复多选
        if (f.fCat && f.fCat.length) restoreMultiSelect("fCat", f.fCat);
        if (f.fProv && f.fProv.length) restoreMultiSelect("fProv", f.fProv);
        if (f.search) document.getElementById("search").value = f.search;
        if (f.sf) sf = f.sf;
        if (f.sd) sd = f.sd;
    } catch {}
}
function restoreMultiSelect(selectId, values) {
    const sel = document.getElementById(selectId);
    if (!sel || !values) return;
    [...sel.options].forEach(o => { o.selected = values.includes(o.value); });
}
// 筛选变动时自动保存
["search","fScore","fCat","fProv","dateFrom","dateTo"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("change", saveFilters);
});
const origSw = sw;
sw = function(t) { origSw(t); saveFilters(); };

// ═══════════════ 收藏功能 ═══════════════
const STARS_KEY = "wenyaozhitou_stars";
function getStars() {
    try { return JSON.parse(localStorage.getItem(STARS_KEY) || "[]"); }
    catch { return []; }
}
function toggleStar(id) {
    let stars = getStars();
    const idx = stars.indexOf(id);
    if (idx >= 0) stars.splice(idx, 1);
    else stars.push(id);
    localStorage.setItem(STARS_KEY, JSON.stringify(stars));
    doFilter();
}
function isStarred(id) { return getStars().indexOf(id) >= 0; }

// NEW badge: items fetched today
function isNew(item) {
    const today = new Date().toISOString().slice(0, 10);
    return (item.fetch_date || "").startsWith(today);
}

function toggleTheme() {
    document.body.classList.toggle("light");
    const isLight = document.body.classList.contains("light");
    localStorage.setItem("theme", isLight ? "light" : "dark");
    document.querySelector(".theme-btn").textContent = isLight ? "☀️" : "🌙";
}
(function() {
    const saved = localStorage.getItem("theme");
    if (saved === "dark") {
        document.body.classList.remove("light");
        document.querySelector(".theme-btn").textContent = "🌙";
    }
})();

init();
