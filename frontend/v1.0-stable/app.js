// 文鳐智投 v11 — 快捷键+骨架屏+展开详情+趋势+tooltip
let allB = [], allW = [], tab = "bid", pg = 1, ps = 20, sf = "relevance_score", sd = -1;
let brief = {}, trends = {}, competitors = {}, bigs = [];
let starOnly = false;
let selectedIds = new Set();
let expandedId = null;  // 当前展开详情的行ID

// ═══ Toast ═══
function toast(msg, type='info') {
    const t = document.createElement('div');
    t.className = `toast toast-${type}`;
    t.textContent = msg;
    t.style.cssText = 'position:fixed;top:20px;right:20px;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:600;z-index:9999;animation:slideIn .3s ease;pointer-events:none;';
    if (type==='success') t.style.background='#059669'; else if (type==='warn') t.style.background='#d97706'; else t.style.background='#2563eb';
    t.style.color='#fff'; t.style.boxShadow='0 4px 12px rgba(0,0,0,.3)';
    document.body.appendChild(t);
    setTimeout(() => { t.style.opacity='0'; t.style.transition='opacity .3s'; setTimeout(() => t.remove(), 300); }, 2000);
}

// ═══ Tooltip popup for ? icon ═══
function showTooltip(e) {
    document.querySelectorAll('.custom-tooltip').forEach(el => el.remove());
    const tip = document.createElement('div');
    tip.className = 'custom-tooltip';
    tip.textContent = '相关度 ≥ 70 分，与数智科技业务（智慧工地/安防/数字平台/电力AI等）高度匹配的项目';
    const rect = e.target.getBoundingClientRect();
    const tipW = 260;
    let left = rect.left + rect.width/2 - tipW/2;
    // 边界保护：不超出屏幕
    if (left < 12) left = 12;
    if (left + tipW > window.innerWidth - 12) left = window.innerWidth - tipW - 12;
    tip.style.cssText = `position:fixed;left:${left}px;top:${rect.bottom + 8}px;width:${tipW}px;padding:10px 14px;background:#1e293b;color:#e2e8f0;font-size:12px;line-height:1.5;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,.4);z-index:9999;animation:slideIn .2s ease;`;
    document.body.appendChild(tip);
    const dismiss = () => { tip.remove(); document.removeEventListener('click', dismiss); document.removeEventListener('touchstart', dismiss); };
    setTimeout(() => { document.addEventListener('click', dismiss); document.addEventListener('touchstart', dismiss); }, 50);
}


// ═══ Score legend tooltip ═══
function showScoreLegend(e) {
    document.querySelectorAll('.score-legend-tip').forEach(el => el.remove());
    const tip = document.createElement('div');
    tip.className = 'score-legend-tip';
    tip.innerHTML = `<div style="font-weight:600;margin-bottom:6px">📊 相关度评分说明</div>
        <div style="display:flex;align-items:center;gap:6px;margin:4px 0"><span style="width:24px;height:8px;background:#10b981;border-radius:4px;flex-shrink:0"></span> <b>85+</b> 高度相关 — 数字/AI/平台/安全类</div>
        <div style="display:flex;align-items:center;gap:6px;margin:4px 0"><span style="width:24px;height:8px;background:#f59e0b;border-radius:4px;flex-shrink:0"></span> <b>60-84</b> 中度相关 — 技术服务/智能化</div>
        <div style="display:flex;align-items:center;gap:6px;margin:4px 0"><span style="width:24px;height:8px;background:#94a3b8;border-radius:4px;flex-shrink:0"></span> <b>&lt;60</b> 低度相关 — 通用/边缘匹配</div>`;
    const rect = e.target.getBoundingClientRect();
    let left = rect.left + rect.width/2 - 160;
    if (left < 12) left = 12;
    if (left + 320 > window.innerWidth - 12) left = window.innerWidth - 320 - 12;
    tip.style.cssText = `position:fixed;left:${left}px;top:${rect.bottom + 8}px;width:320px;padding:12px 16px;background:#1e293b;color:#e2e8f0;font-size:12px;line-height:1.6;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.5);z-index:9999;animation:slideIn .2s ease;`;
    document.body.appendChild(tip);
    const dismiss = () => { tip.remove(); document.removeEventListener('click', dismiss); document.removeEventListener('touchstart', dismiss); };
    setTimeout(() => { document.addEventListener('click', dismiss); document.addEventListener('touchstart', dismiss); }, 50);
}

// ═══ Star badge ═══
function updateStarBadge() {
    const cnt = getStars().length;
    const el = document.getElementById('cntStar');
    if (el) el.textContent = cnt;
}

// ═══ Page size ═══
function setPs(n) { ps = n; pg = 1; doFilter(); }
function renderPsSelector(id) {
    const el = document.getElementById(id); if (!el) return;
    el.innerHTML = [20,50,100].map(n => 
        `<button class="pg-btn${ps===n?' active':''}" onclick="setPs(${n})" style="font-size:11px">${n}</button>`
    ).join('');
}

async function init() {
    document.querySelectorAll('.stat-card').forEach(c => c.classList.add('loading'));
    // 显示骨架屏
    document.getElementById("tBidTb").innerHTML = skeletonRows(ps);
    // ── 搜索框：回车触发 + 按钮点击 ──
    // ── Search: IME-aware Enter + button click ──
    let composing = false;
    const searchEl = document.getElementById('search');
    if (searchEl) {
        searchEl.addEventListener('compositionstart', () => { composing = true; });
        searchEl.addEventListener('compositionend', () => { composing = false; });
        searchEl.addEventListener('keydown', e => { if (e.key === 'Enter' && !composing) doFilter(); });
    }
    const searchBtn = document.getElementById('searchBtn');
    if (searchBtn) searchBtn.addEventListener('click', doFilter);
    try {
    const r = await fetch("/bidding/data.json");
    const d = await r.json();
    allB = d.bidding || [];
    allW = d.winning || [];
    brief = d.brief || {};
    trends = d.trends || {};
    competitors = d.competitors || {};
    bigs = d.big_projects || [];
    // Stats cards + trend indicators + update time
    document.getElementById("statBidTotal").textContent = allB.length;
    document.getElementById("statWinTotal").textContent = allW.length;
    document.getElementById("statToday").textContent = brief.today_total || 0;
    document.getElementById("statHigh").textContent = allB.filter(i => (i.relevance_score||0) >= 70).length;
    // Last update time
    const fetches = [...allB, ...allW].map(i => i.fetch_date).filter(Boolean).sort();
    const latestFetch = fetches[fetches.length-1] || '';
    const dt = latestFetch ? latestFetch.substring(0,16).replace('T',' ') : '—';
    document.getElementById('lastUpdate').textContent = '数据更新: ' + dt;
    renderTrendIndicators();
    document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('loading'));
    // Tab badges
    document.getElementById("cntBid").textContent = allB.length;
    document.getElementById("cntWin").textContent = allW.length;
    // Populate dropdowns
    const cats = new Set(), ps2 = new Set();
    [...allB, ...allW].forEach(i => {
        if (i.category) cats.add(i.category);
        if (i.province) ps2.add(i.province);
    });
    [["fCat", cats], ["fProv", ps2]].forEach(([id, s]) => {
        const sel = document.getElementById(id);
        if (!sel) return;
        sel.innerHTML = "";
        const allOpt = document.createElement("option");
        allOpt.value = ""; allOpt.textContent = id === "fCat" ? "全部客户" : "全部地域";
        sel.appendChild(allOpt);
        const sorted = [...s].sort((a, b) => {
            const ao = a.includes("其他"), bo = b.includes("其他");
            if (ao && !bo) return 1; if (!ao && bo) return -1;
            return a.localeCompare(b, "zh");
        });
        sorted.forEach(v => { const o = document.createElement("option"); o.value = v; o.textContent = v; sel.appendChild(o); });
    });
    
    loadBookmarksFromServer().then(() => updateStarBadge());
    restoreFilters();
    restoreUrl();
    doFilter();
    // ── 横向滚动提示：滚动到末尾时隐藏右侧渐变淡出 ──
    const filterRow = document.querySelector('.filter-row');
    if (filterRow) {
        const wrapper = filterRow.parentElement;
        const checkScrollEnd = () => {
            const gap = 8; // 容忍像素
            const isEnd = filterRow.scrollLeft + filterRow.clientWidth >= filterRow.scrollWidth - gap;
            wrapper.classList.toggle('scrolled-end', isEnd);
        };
        filterRow.addEventListener('scroll', checkScrollEnd, {passive: true});
        checkScrollEnd();
        new ResizeObserver(checkScrollEnd).observe(filterRow);
        // ── 首次进入自动演示横向滑动 ──
        if (window.innerWidth < 768 && !sessionStorage.getItem('scrollHintShown')) {
            const canScroll = filterRow.scrollWidth > filterRow.clientWidth + 10;
            if (canScroll) {
                setTimeout(() => {
                    filterRow.scrollTo({left: 100, behavior: 'smooth'});
                    setTimeout(() => {
                        filterRow.scrollTo({left: 0, behavior: 'smooth'});
                    }, 1200);
                }, 1500);
                sessionStorage.setItem('scrollHintShown', '1');
            }
        }
    }
    // ── 回到顶部按钮（移动端）──
    if (!document.getElementById('btnBackTop')) {
        const btn = document.createElement('button');
        btn.id = 'btnBackTop';
        btn.innerHTML = '↑';
        btn.title = '回到顶部';
        btn.onclick = () => window.scrollTo({top:0,behavior:'smooth'});
        document.body.appendChild(btn);
        let scrollTicking = false;
        window.addEventListener('scroll', () => {
            if (!scrollTicking) {
                requestAnimationFrame(() => {
                    btn.classList.toggle('show', window.scrollY > 300);
                    scrollTicking = false;
                });
                scrollTicking = true;
            }
        }, {passive:true});
    }
    } catch(e) {
        console.error('init failed:', e);
        document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('loading'));
        document.getElementById('tBidTb').innerHTML = '<tr><td colspan="11" style="text-align:center;color:#ef4444;padding:20px">⚠️ 数据加载失败，请刷新页面重试</td></tr>';
    }
}

// ═══ Trend indicators for stat cards ═══
function renderTrendIndicators() {
    const today = todayStr();
    const yesterday = (d => { d.setDate(d.getDate()-1); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); })(new Date());
    const todayCount = allB.filter(i => (i.publish_date||'').substring(0,10) === today).length;
    const yesterdayCount = allB.filter(i => (i.publish_date||'').substring(0,10) === yesterday).length;
    const diff = todayCount - yesterdayCount;
    const el = document.getElementById('statTodayTrend');
    if (el && diff !== 0) {
        el.textContent = diff > 0 ? `↑${diff}` : `↓${Math.abs(diff)}`;
        el.style.color = diff > 0 ? 'var(--green)' : 'var(--red)';
    } else if (el) {
        el.textContent = '—';
        el.style.color = 'var(--dim)';
    }
    // High trend
    const todayHigh = allB.filter(i => (i.publish_date||'').substring(0,10) === today && (i.relevance_score||0) >= 70).length;
    const yesterdayHigh = allB.filter(i => (i.publish_date||'').substring(0,10) === yesterday && (i.relevance_score||0) >= 70).length;
    const hDiff = todayHigh - yesterdayHigh;
    const hel = document.getElementById('statHighTrend');
    if (hel && hDiff !== 0) {
        hel.textContent = hDiff > 0 ? `↑${hDiff}` : `↓${Math.abs(hDiff)}`;
        hel.style.color = hDiff > 0 ? 'var(--green)' : 'var(--red)';
    } else if (hel) {
        hel.textContent = '—';
        hel.style.color = 'var(--dim)';
    }
}

// ═══ Skeleton loading rows ═══
function skeletonRows(n) {
    let html = '';
    for (let i = 0; i < Math.min(n, 10); i++) {
        html += `<tr class="skel-row">
            <td style="text-align:center;width:32px"><span class="skel" style="width:16px;height:16px"></span></td>
            <td style="text-align:center"><span class="skel" style="width:20px;height:12px"></span></td>
            <td><span class="skel" style="width:50px;height:8px"></span></td>
            <td><span class="skel" style="width:${180+Math.random()*120|0}px;height:12px"></span></td>
            <td class="hide-mobile"><span class="skel" style="width:60px;height:16px"></span></td>
            <td class="hide-mobile"><span class="skel" style="width:80px;height:12px"></span></td>
            <td><span class="skel" style="width:55px;height:12px"></span></td>
            <td><span class="skel" style="width:30px;height:12px"></span></td>
            <td class="hide-mobile"><span class="skel" style="width:70px;height:12px"></span></td>
            <td><span class="skel" style="width:60px;height:12px"></span></td>
            <td><span class="skel" style="width:30px;height:12px"></span></td>
        </tr>`;
    }
    return html;
}

// ═══ Filter / Sort ═══
function getFilt() {
    let d = tab === "bid" ? [...allB] : [...allW];
    // Stat-card filter (applied first, before manual filters)
    if (activeStatFilter === 'high') d = d.filter(i => (i.relevance_score || 0) >= 70);
    if (activeStatFilter === 'today') d = d.filter(i => isNew(i));
    if (todayOnly && !activeStatFilter) d = d.filter(i => isNew(i));
    const q = (document.getElementById("search")?.value || "").toLowerCase();
    if (q) d = d.filter(i =>
        (i.title||"").toLowerCase().includes(q) || (i.procurement_owner||"").toLowerCase().includes(q) ||
        (i.winner_company||"").toLowerCase().includes(q) || (i.source_site||"").toLowerCase().includes(q) ||
        (i.province||"").toLowerCase().includes(q) || (i.region||"").toLowerCase().includes(q) ||
        (i.category||"").toLowerCase().includes(q)
    );
    const sc = parseFloat(document.getElementById("fScore")?.value || 0);
    if (sc) d = d.filter(i => (i.relevance_score||0) >= sc);
    const bgt = parseFloat(document.getElementById("fBudget")?.value || 0);
    if (bgt) d = d.filter(i => { const v = parseFloat(i.budget_amount); return v && v >= bgt; });
    const cat = document.getElementById("fCat")?.value;
    if (cat) d = d.filter(i => i.category === cat);
    const prov = document.getElementById("fProv")?.value;
    if (prov) d = d.filter(i => i.province === prov);
    const df = document.getElementById("dateFrom")?.value;
    if (df) d = d.filter(i => (i.publish_date||"") >= df);
    const dt = document.getElementById("dateTo")?.value;
    if (dt) d = d.filter(i => (i.publish_date||"") <= dt);
    return d;
}

// ═══ Dynamic stat cards — reflect filtered counts ═══
function updateStats(data) {
    // When stat-card filter is active, stat cards stay at GLOBAL counts
    // (the banner already tells you what subset you're viewing)
    if (activeStatFilter) {
        document.getElementById("statBidTotal").textContent = allB.length;
        document.getElementById("statToday").textContent = brief.today_total || 0;
        document.getElementById("statHigh").textContent = allB.filter(i => (i.relevance_score||0) >= 70).length;
        document.getElementById("statWinTotal").textContent = allW.length;
        // Tab badges still reflect actual filtered data
        document.getElementById("cntBid").textContent = getFiltFor(allB).length;
        document.getElementById("cntWin").textContent = getFiltFor(allW).length;
        const stars = new Set(getStars());
        document.getElementById("cntStar").textContent = [...allB, ...allW].filter(i => stars.has(String(i.id))).length;
        const trendEls = [document.getElementById("statTodayTrend"), document.getElementById("statHighTrend")];
        trendEls.forEach(el => { if (el) el.style.opacity = ""; });
        return;
    }
    const hasFilter = !!(document.getElementById("search")?.value
        || document.getElementById("fCat")?.value
        || document.getElementById("fProv")?.value
        || parseFloat(document.getElementById("fScore")?.value || 0)
        || parseFloat(document.getElementById("fBudget")?.value || 0)
        || document.getElementById("dateFrom")?.value
        || document.getElementById("dateTo")?.value);
    const today = todayStr();
    const trendEls = [document.getElementById("statTodayTrend"), document.getElementById("statHighTrend")];
    if (hasFilter) {
        // Apply same filters to BOTH bid and win for cross-tab badges
        const filtBid = getFiltFor(allB);
        const filtWin = getFiltFor(allW);
        document.getElementById("statBidTotal").textContent = filtBid.length;
        document.getElementById("statToday").textContent = filtBid.filter(i => (i.publish_date||"").substring(0,10) === today).length;
        document.getElementById("statHigh").textContent = filtBid.filter(i => (i.relevance_score||0) >= 70).length;
        document.getElementById("statWinTotal").textContent = filtWin.length;
        document.getElementById("cntBid").textContent = filtBid.length;
        document.getElementById("cntWin").textContent = filtWin.length;
        // Star badge: count starred items matching current filter
        const stars = new Set(getStars());
        const filtStar = [...filtBid, ...filtWin].filter(i => stars.has(String(i.id))).length;
        document.getElementById("cntStar").textContent = filtStar;
        trendEls.forEach(el => { if (el) el.style.opacity = "0"; });
    } else {
        document.getElementById("statBidTotal").textContent = allB.length;
        document.getElementById("statToday").textContent = brief.today_total || 0;
        document.getElementById("statHigh").textContent = allB.filter(i => (i.relevance_score||0) >= 70).length;
        document.getElementById("statWinTotal").textContent = allW.length;
        document.getElementById("cntBid").textContent = allB.length;
        document.getElementById("cntWin").textContent = allW.length;
        document.getElementById("cntStar").textContent = getStars().length;
        trendEls.forEach(el => { if (el) el.style.opacity = ""; });
    }
}

// Helper: apply active filters to arbitrary dataset (for cross-tab counts)
function getFiltFor(arr) {
    let d = [...arr];
    // Stat-card filter
    if (activeStatFilter === 'high') d = d.filter(i => (i.relevance_score || 0) >= 70);
    if (activeStatFilter === 'today') d = d.filter(i => isNew(i));
    const q = (document.getElementById("search")?.value || "").toLowerCase();
    if (q) d = d.filter(i =>
        (i.title||"").toLowerCase().includes(q) || (i.procurement_owner||"").toLowerCase().includes(q) ||
        (i.winner_company||"").toLowerCase().includes(q) || (i.source_site||"").toLowerCase().includes(q) ||
        (i.province||"").toLowerCase().includes(q) || (i.region||"").toLowerCase().includes(q) ||
        (i.category||"").toLowerCase().includes(q)
    );
    const sc = parseFloat(document.getElementById("fScore")?.value || 0);
    if (sc) d = d.filter(i => (i.relevance_score||0) >= sc);
    const cat = document.getElementById("fCat")?.value;
    if (cat) d = d.filter(i => i.category === cat);
    const prov = document.getElementById("fProv")?.value;
    if (prov) d = d.filter(i => i.province === prov);
    const df = document.getElementById("dateFrom")?.value;
    if (df) d = d.filter(i => (i.publish_date||"") >= df);
    const dt = document.getElementById("dateTo")?.value;
    if (dt) d = d.filter(i => (i.publish_date||"") <= dt);
    return d;
}

function srt(f) { if (sf===f) sd=-sd; else {sf=f;sd=-1;} expandedId = null; doFilter(); }

function doFilter() {
    let data = getFilt();
    if (starOnly) data = data.filter(i => getStars().includes(String(i.id)));
    // Update sort indicators
    document.querySelectorAll('thead th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    const sortTh = document.querySelector('thead th[onclick*="' + sf + '"]');
    if (sortTh && sd === 1) sortTh.classList.add('sort-asc');
    if (sortTh && sd === -1) sortTh.classList.add('sort-desc');

    data.sort((a,b) => {
        let va=a[sf]||"", vb=b[sf]||"";
        if (typeof va==="string") va=va.toLowerCase();
        if (typeof vb==="string") vb=vb.toLowerCase();
        return va>vb?sd:va<vb?-sd:0;
    });
    const tp = Math.ceil(data.length/ps);
    pg = Math.min(pg, tp||1);
    const st = (pg-1)*ps;
    const page = data.slice(st, st+ps);
    
    if (tab==="bid") {
        if (!page.length) {
            const q = document.getElementById("search")?.value || "";
            const emptyMsg = starOnly ? '⭐ 暂无收藏，在招标列表中点击 ☆ 即可收藏' : smartEmptyMsg(q, data.length);
            document.getElementById("tBidTb").innerHTML = `<tr class="empty-msg"><td colspan="11">${emptyMsg}</td></tr>`;
            document.getElementById("pgInfo").textContent = '显示 0 条';
            document.getElementById("pgNums").innerHTML = '';
            return;
        }
        document.getElementById("tBidTb").innerHTML = page.map((i,idx) => {
            const sc = i.relevance_score||0;
            const barCl = sc>=70?"score-hi":(sc>=40?"score-mid":"score-lo");
            const barW = sc>=70?"width:100%":(sc>=40?"width:60%":"width:35%");
            const starred = isStarred(i.id);
            const checked = selectedIds.has(String(i.id)) ? 'checked' : '';
            const star = `<span class="star${starred?' on':''}" onclick="event.stopPropagation();toggleStar(${i.id})">${starred?'★':'☆'}</span>`;
            const newDot = isNew(i) ? '<span class="new-badge">NEW</span>' : '';
            const title = esc(i.title||"");
            const link = url_fix(i.url);
            const cat = i.category||"⚪ 其他";
            const amt = i.budget_amount||'';
            const amtDisp = amt ? (parseFloat(amt)>=10000 ? (parseFloat(amt)/10000).toFixed(0)+'万' : amt) : '—';
            const catCl = cat.includes("电力")||cat.includes("央企")?"tag-blue":(cat.includes("南网")||cat.includes("国网")?"tag-amber":(cat.includes("能源")?"tag-green":"tag-gray"));
            const rowId = 'row_'+i.id;
            const isExpanded = expandedId === i.id;
            const readCls = isRead(i.id) ? ' read' : '';
            const starredMenu = starred ? '取消收藏' : '收藏';
            const menuHtml = window.innerWidth <= 768 ? `<span class="kebab-btn" onclick="event.stopPropagation();toggleKebab(event,${i.id},'${esc(title).replace(/'/g,"\\'")}','${link.replace(/'/g,"\\'")}',${starred})">⋯</span>` : '';
            return `<tr id="${rowId}" class="data-row${readCls}" onclick="if(window.innerWidth<=768){markRead(${i.id});this.classList.add('read');window.open('${link}','_blank')}else{toggleDetail(${i.id})}" style="cursor:pointer">
                <td style="text-align:center;width:32px"><input type="checkbox" ${checked} onclick="event.stopPropagation();toggleSelect(${i.id})" style="cursor:pointer;accent-color:var(--accent)"></td>
                <td data-label="序号" style="text-align:center;color:var(--dim);font-size:11px">${st+idx+1}</td>
                <td data-label="相关度"><span class="score-bar ${barCl}" style="${barW}"></span><span style="font-size:11px;color:var(--muted)">${sc.toFixed(0)}分</span></td>
                <td class="title-cell">${newDot}${star} ${menuHtml} <a href="${link}" target="_blank" onclick="event.stopPropagation()">${title}</a></td>
                <td data-label="客户"><span class="tag-sm ${catCl}">${catLabel(cat)}</span></td>
                <td data-label="招标单位">${i.procurement_owner?esc(i.procurement_owner.substring(0,22)):'—'}</td>
                <td data-label="预算" style="font-weight:600;color:var(--green)">${amtDisp}</td>
                <td data-label="地域">${i.region||i.province||'—'}</td>
                <td class="hide-mobile" data-label="来源">${esc((i.source_site||'').substring(0,18))}</td>
                <td data-label="日期">${(i.publish_date||'').substring(0,10)}</td>
                <td data-label="操作"><a href="${link}" target="_blank" class="link-btn" onclick="event.stopPropagation()">查看</a></td>
            </tr>
            ${isExpanded ? renderDetailRow(i) : ''}`;
        }).join('');
        document.getElementById("pgInfo").textContent = `显示 ${st+1}-${Math.min(st+ps,data.length)} 条 / 共 ${data.length} 条`;
        renderPsSelector("psSelector");
        renderPg("pgNums", pg, tp);
    } else {
        if (!page.length) {
            document.getElementById("tWinTb").innerHTML = `<tr class="empty-msg"><td colspan="9">📭 暂无中标数据</td></tr>`;
            document.getElementById("pgInfoW").textContent = '显示 0 条';
            document.getElementById("pgNumsW").innerHTML = '';
            return;
        }
        document.getElementById("tWinTb").innerHTML = page.map((i,idx) => {
            const sc = i.relevance_score||0;
            const barCl = sc>=70?"score-hi":(sc>=40?"score-mid":"score-lo");
            const barW = sc>=70?"width:100%":(sc>=40?"width:60%":"width:35%");
            const checked = selectedIds.has(String(i.id)) ? 'checked' : '';
            const title = esc(i.title||"");
            const link = url_fix(i.url);
            const readCls = isRead(i.id) ? ' read' : '';
            const menuHtml = window.innerWidth <= 768 ? `<span class="kebab-btn" onclick="event.stopPropagation();toggleKebab(event,${i.id},'${esc(title).replace(/'/g,"\\'")}','${link.replace(/'/g,"\\'")}',false)">⋯</span>` : '';
            const amt = i.winning_amount||i.budget_amount||'';
            const amtDisp = amt ? (parseFloat(amt)>=10000 ? (parseFloat(amt)/10000).toFixed(0)+'万' : amt) : '—';
            return `<tr class="data-row${readCls}" onclick="if(window.innerWidth<=768){markRead(${i.id});this.classList.add('read');window.open('${link}','_blank')}else{toggleDetail(${i.id})}" style="cursor:pointer">
                <td style="text-align:center;width:32px"><input type="checkbox" ${checked} onclick="event.stopPropagation();toggleSelect(${i.id})" style="cursor:pointer;accent-color:var(--accent)"></td>
                <td data-label="序号" style="text-align:center;color:var(--dim);font-size:11px">${st+idx+1}</td>
                <td data-label="相关度"><span class="score-bar ${barCl}" style="${barW}"></span><span style="font-size:11px;color:var(--muted)">${sc.toFixed(0)}分</span></td>
                <td class="title-cell">${menuHtml} <a href="${link}" target="_blank" onclick="event.stopPropagation()">${title}</a></td>
                <td data-label="中标单位">${esc((i.winner_company||'').substring(0,22))||'—'}</td>
                <td data-label="中标金额" style="font-weight:600;color:var(--green)">${amtDisp}</td>
                <td data-label="地域">${i.region||i.province||'—'}</td>
                <td data-label="日期">${(i.publish_date||'').substring(0,10)}</td>
                <td data-label="操作"><a href="${link}" target="_blank" class="link-btn" onclick="event.stopPropagation()">查看</a></td>
            </tr>`;
        }).join('');
        document.getElementById("pgInfoW").textContent = `显示 ${st+1}-${Math.min(st+ps,data.length)} 条 / 共 ${data.length} 条`;
        renderPsSelector("psSelector");
        renderPg("pgNumsW", pg, tp);
    }
    updateStats(data);
    saveFilters();
    syncUrl();
}

// ═══ Row detail expansion ═══
function toggleDetail(id) {
    // 不拦截按钮和复选框
    if (expandedId === id) { expandedId = null; }
    else { expandedId = id; }
    doFilter();
}

function renderDetailRow(i) {
    const amt = i.budget_amount||i.winning_amount||'';
    const amtDisp = amt ? (parseFloat(amt)>=10000 ? (parseFloat(amt)/10000).toFixed(2)+'万元' : amt+'元') : '—';
    const owner = i.procurement_owner || i.winner_company || '—';
    const site = i.source_site || '—';
    const dept = i.source_department || '—';
    const notice = i.notice_type || '—';
    const summary = i.content_summary || '';
    const link = url_fix(i.url);
    return `<tr class="detail-row">
        <td colspan="11">
            <div class="detail-card">
                <div class="detail-grid">
                    <div class="detail-item"><span class="detail-label">招标单位</span><span class="detail-val">${esc(owner)}</span></div>
                    <div class="detail-item"><span class="detail-label">公告类型</span><span class="detail-val">${notice==='procurement'?'采购公告':notice==='winning'?'中标公告':notice}</span></div>
                    <div class="detail-item"><span class="detail-label">预算/金额</span><span class="detail-val" style="color:var(--green);font-weight:600">${amtDisp}</span></div>
                    <div class="detail-item"><span class="detail-label">发布部门</span><span class="detail-val">${esc(dept)}</span></div>
                    <div class="detail-item"><span class="detail-label">来源平台</span><span class="detail-val">${esc(site)}</span></div>
                    <div class="detail-item"><span class="detail-label">抓取时间</span><span class="detail-val">${(i.fetch_date||'').substring(0,16)}</span></div>
                </div>
                ${summary ? `<div class="detail-summary">${esc(summary.substring(0,200))}${summary.length>200?'...':''}</div>` : ''}
                <div style="text-align:right;margin-top:8px"><a href="${link}" target="_blank" class="link-btn">🔗 查看原始公告 →</a></div>
            </div>
        </td>
    </tr>`;
}

function renderPg(id, pg, tp) {
    const el = document.getElementById(id); if (!el) return;
    if (tp <= 1) { el.innerHTML = ''; return; }
    let h = '';
    h += `<button class="pg-btn" onclick="pg=1;doFilter()" ${pg===1?'disabled':''}>«</button>`;
    h += `<button class="pg-btn" onclick="pg=${Math.max(1,pg-1)};doFilter()" ${pg===1?'disabled':''}>‹</button>`;
    for (let p=Math.max(1,pg-2); p<=Math.min(tp,pg+2); p++) {
        h += `<button class="pg-btn${p===pg?' active':''}" onclick="pg=${p};doFilter()">${p}</button>`;
    }
    h += `<button class="pg-btn" onclick="pg=${Math.min(tp,pg+1)};doFilter()" ${pg===tp?'disabled':''}>›</button>`;
    h += `<button class="pg-btn" onclick="pg=${tp};doFilter()" ${pg===tp?'disabled':''}>»</button>`;
    el.innerHTML = h;
}

// ═══ Tab Switch ═══
function sw(t) {
    if (!allB.length && !allW.length) { toast('数据加载中，请稍候...', 'info'); return; }
    selectedIds.clear(); expandedId = null;
    tab = t; pg = 1;
    if (t === "star") { starOnly = true; tab = "bid"; }
    else { starOnly = false; }
    ["Bid","Win","Star"].forEach(x => {
        const btn = document.getElementById("tab"+x);
        const panel = document.getElementById("table"+x);
        if (btn) btn.classList.toggle("active", (x==="Star"?t==="star":t===x.toLowerCase()));
        if (panel) panel.style.display = (x==="Star"?t==="star":t===x.toLowerCase())?"":"none";
    });
    document.getElementById("tableBid").style.display = (t==="bid"||t==="star")?"":"none";
    doFilter();
}

// ═══ Stat card click ═══
let todayOnly = false;
let activeStatFilter = null;  // 'total'|'today'|'high'|'win' — null means no stat filter active
function statClick(type) {
    // Click same card again → deactivate stat filter
    if (activeStatFilter === type) {
        activeStatFilter = null;
        renderStatBanner();
        document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
        resetF();
        return;
    }
    // Activate stat filter — DON'T touch search/filter inputs!
    activeStatFilter = type;
    todayOnly = false;
    starOnly = false;
    selectedIds.clear(); expandedId = null;
    document.getElementById("dateFrom").value = "";
    document.getElementById("dateTo").value = "";
    document.getElementById("fScore").value = "";
    
    // Highlight clicked card
    document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
    const idx = {total:0, today:1, high:2, win:3}[type];
    const cards = document.querySelectorAll('.stat-card');
    if (idx !== undefined && cards[idx]) cards[idx].classList.add('active');
    
    // Navigate to appropriate tab
    if (type === 'total') { sw('bid'); }
    else if (type === 'today') { sw('bid'); }
    else if (type === 'high') { sw('bid'); }
    else if (type === 'win') { sw('win'); }
    
    pg = 1; sf = 'relevance_score'; sd = -1;
    renderStatBanner();
    doFilter();
}

// Render the stat filter banner
function renderStatBanner() {
    const banner = document.getElementById('statFilterBanner');
    if (!banner) return;
    if (!activeStatFilter) {
        banner.style.display = 'none';
        document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
        return;
    }
    let data = tab === 'bid' ? [...allB] : [...allW];
    if (activeStatFilter === 'high') data = data.filter(i => (i.relevance_score || 0) >= 70);
    if (activeStatFilter === 'today') data = data.filter(i => isNew(i));
    
    const labels = { total: '全部招标', today: '今日新增招标', high: '高相关招标', win: '全部中标' };
    const label = labels[activeStatFilter] || activeStatFilter;
    banner.innerHTML = `<span>📊 ${label} · ${data.length} 条</span>
        <button class="banner-close" onclick="activeStatFilter=null;renderStatBanner();resetF();">✕ 显示全部</button>`;
    banner.style.display = 'flex';
}

// ═══ Cat label ═══
function catLabel(cat) {
    if (!cat) return "其他";
    return cat.replace(/^[🔵🟠🟡🟢⚪]\s*/, '');
}

// ═══ Reset ═══
function resetF() {
    ["search","fScore","fCat","fProv","fBudget","dateFrom","dateTo"].forEach(id => {
        const e = document.getElementById(id); if (e) e.value = "";
    });
    starOnly = false; selectedIds.clear(); todayOnly = false; expandedId = null;
    activeStatFilter = null;
    renderStatBanner();
    document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
    pg=1; sf="relevance_score"; sd=-1;
    doFilter();
    syncUrl();
}

// ═══ Batch select ═══
function toggleSelectAll() {
    const data = getFilt();
    if (starOnly) data = data.filter(i => getStars().includes(String(i.id)));
    if (selectedIds.size === data.length) { selectedIds.clear(); }
    else { data.forEach(i => selectedIds.add(String(i.id))); }
    doFilter();
}
function toggleSelect(id) {
    const sid = String(id);
    if (selectedIds.has(sid)) selectedIds.delete(sid);
    else selectedIds.add(sid);
    doFilter();
}
function smartExport() {
    let data = getFilt();
    if (starOnly) data = data.filter(i => getStars().map(String).includes(String(i.id)));
    if (selectedIds.size) data = data.filter(i => selectedIds.has(String(i.id)));
    if (!data.length) { toast('没有数据可导出', 'warn'); return; }
    const cols = tab==='win'?
        ["相关度","标题","中标单位","中标金额","地域","发布日期","链接"] :
        ["相关度","标题","客户分类","预算金额","地域","来源","发布日期","链接"];
    const keys = tab==='win'?
        ["relevance_score","title","winner_company","winning_amount","province","publish_date","url"] :
        ["relevance_score","title","category","budget_amount","province","source_site","publish_date","url"];
    let csv = "\uFEFF"+cols.join(",")+"\n";
    data.forEach(i => { csv += keys.map(k => { const v=String(i[k]??""); return '"'+v.replace(/"/g,'""')+'"'; }).join(",")+"\n"; });
    const blob = new Blob([csv],{type:"text/csv;charset=utf-8"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "bidding_export_"+new Date().toISOString().slice(0,10)+".csv";
    a.click();
    const label = selectedIds.size ? `已导出 ${data.length} 条（选中）` : `已导出全部 ${data.length} 条`;
    toast(label, 'success');
    selectedIds.clear(); doFilter();
}

// ═══ Helpers ═══
function esc(t) { return (t||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function url_fix(u) { return (!u||u.startsWith("javascript:"))?"/bidding/":u; }
function isNew(i) { const pd=(i.publish_date||'').substring(0,10); return pd===todayStr(); }
function todayStr() { const d=new Date(); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }




// ═══ Row density toggle ═══
function toggleDensity() {
    document.body.classList.toggle('dense');
    const isDense = document.body.classList.contains('dense');
    localStorage.setItem('density', isDense ? 'dense' : 'comfort');
    const btn = document.getElementById('densityBtn');
    if (btn) btn.textContent = isDense ? '≡ 舒适' : '≡ 紧凑';
}
(function(){
    if (window.innerWidth > 768 && localStorage.getItem('density') === 'dense') {
        document.body.classList.add('dense');
        const btn = document.getElementById('densityBtn');
        if (btn) btn.textContent = '≡ 舒适';
    }
})();

// ═══ Keyboard shortcuts ═══
document.addEventListener("keydown", e => {
    // / 聚焦搜索框
    if (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA" && document.activeElement.tagName !== "SELECT") {
        e.preventDefault();
        const s = document.getElementById("search");
        if (s) { s.focus(); s.select(); }
    }
    // Esc: 关闭聊天面板 OR 清除筛选
    if (e.key === "Escape") {
        // 优先关闭聊天面板
        if (typeof closeChat !== 'undefined' && document.getElementById('chatPanel')?.classList.contains('open')) {
            closeChat();
            return;
        }
        // 关闭 kebab 菜单
        document.querySelectorAll('.kebab-menu,.kebab-overlay').forEach(el => el.remove());
        // 清除搜索 + 重置筛选
        const s = document.getElementById("search");
        if (s && document.activeElement === s) { s.blur(); }
        resetF();
    }
    // Ctrl+Enter / Cmd+Enter: 导出
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        smartExport();
    }
    // ← → 切换 Tab
    if ((e.ctrlKey || e.metaKey) && e.key === "ArrowLeft") { e.preventDefault(); sw("bid"); }
    if ((e.ctrlKey || e.metaKey) && e.key === "ArrowRight") { e.preventDefault(); sw("win"); }
    // Ctrl+S 收藏Tab
    if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); sw("star"); }
});

// ═══ Filter persistence ═══
const FILTER_KEY = "wenyaozhitou_filters_v2";
function saveFilters() {
    const f = {
        search: document.getElementById("search")?.value||"",
        fScore: document.getElementById("fScore")?.value||"",
        fCat: document.getElementById("fCat")?.value||"",
        fProv: document.getElementById("fProv")?.value||"",
        tab, sf, sd
    };
    localStorage.setItem(FILTER_KEY, JSON.stringify(f));
}
function restoreFilters() { try { const f=JSON.parse(localStorage.getItem(FILTER_KEY)); if(!f)return; if(f.search)document.getElementById("search").value=f.search; if(f.fScore)document.getElementById("fScore").value=f.fScore; if(f.fCat)document.getElementById("fCat").value=f.fCat; if(f.fProv)document.getElementById("fProv").value=f.fProv; if(f.tab)sw(f.tab); if(f.sf){sf=f.sf;sd=f.sd;} } catch(e){} }
// ═══ URL state sync — shareable filtered views ═══
function syncUrl() {
    const params = new URLSearchParams();
    const search = document.getElementById("search")?.value || "";
    const cat = document.getElementById("fCat")?.value || "";
    const prov = document.getElementById("fProv")?.value || "";
    const score = document.getElementById("fScore")?.value || "";
    const budget = document.getElementById("fBudget")?.value || "";
    const df = document.getElementById("dateFrom")?.value || "";
    const dt = document.getElementById("dateTo")?.value || "";
    if (search) params.set("q", search);
    if (cat) params.set("cat", cat);
    if (prov) params.set("prov", prov);
    if (score) params.set("score", score);
    if (budget) params.set("budget", budget);
    if (df) params.set("from", df);
    if (dt) params.set("to", dt);
    if (tab !== "bid") params.set("tab", tab);
    if (sf !== "relevance_score") params.set("sort", sf);
    if (sd === 1) params.set("dir", "asc");
    if (starOnly) params.set("star", "1");
    const qs = params.toString();
    const url = qs ? "?" + qs : window.location.pathname;
    if (window.location.search !== (qs ? "?" + qs : "")) {
        history.replaceState(null, "", url);
    }
}
function restoreUrl() {
    const p = new URLSearchParams(window.location.search);
    if (p.has("q")) document.getElementById("search").value = p.get("q");
    if (p.has("cat")) document.getElementById("fCat").value = p.get("cat");
    if (p.has("prov")) document.getElementById("fProv").value = p.get("prov");
    if (p.has("score")) document.getElementById("fScore").value = p.get("score");
    if (p.has("budget")) document.getElementById("fBudget").value = p.get("budget");
    if (p.has("from")) document.getElementById("dateFrom").value = p.get("from");
    if (p.has("to")) document.getElementById("dateTo").value = p.get("to");
    if (p.has("tab")) sw(p.get("tab"));
    if (p.has("sort")) { sf = p.get("sort"); sd = p.get("dir") === "asc" ? 1 : -1; }
    if (p.has("star")) { starOnly = true; tab = "bid"; }
}


// ═══ Star / Bookmark ═══
function getStars() { try { return JSON.parse(localStorage.getItem("bidding_stars")||"[]"); } catch(e) { return []; } }
function isStarred(id) { return getStars().map(String).includes(String(id)); }
function toggleStar(id) {
    let stars = getStars(); const sid = String(id);
    let added;
    if (stars.includes(sid)) { stars = stars.filter(s => s!==sid); added = false; }
    else { stars.push(sid); added = true; }
    localStorage.setItem("bidding_stars", JSON.stringify(stars));
    updateStarBadge();
    toast(added ? '⭐ 已收藏' : '取消收藏', added ? 'success' : 'warn');
    syncBookmarkToServer(id, added);
    doFilter();
}
async function loadBookmarksFromServer() { try { const r=await fetch("/bidding/api/bookmarks"); if(!r.ok)return; const d=await r.json(); if(d.bookmarks&&d.bookmarks.length){ const ids=d.bookmarks.map(b=>String(b.item_id)); localStorage.setItem("bidding_stars",JSON.stringify(ids)); } } catch(e){} }
async function syncBookmarkToServer(id, add) { try { const method=add?"POST":"DELETE"; await fetch(`/bidding/api/bookmarks?id=${id}`,{method}); } catch(e){} }

// ═══ Theme ═══
(function(){ if(localStorage.getItem('theme')==='dark'){ document.body.classList.remove('light'); } })();

// ═══ Date presets ═══
function setDatePreset(type) {
    todayOnly = false;
    const now = new Date();
    const fmt = d => d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
    // Toggle active class on date preset buttons
    document.querySelectorAll('.date-preset').forEach(b => b.classList.remove('active'));
    if (type === 'today') {
        const t = fmt(now);
        document.getElementById('dateFrom').value = t;
        document.getElementById('dateTo').value = t;
        document.querySelector('.date-preset[onclick*=\"today\"]')?.classList.add('active');
    } else if (type === 'week') {
        const dow = now.getDay();
        const mon = new Date(now); mon.setDate(now.getDate() - (dow===0?6:dow-1));
        const sun = new Date(mon); sun.setDate(mon.getDate()+6);
        document.getElementById('dateFrom').value = fmt(mon);
        document.getElementById('dateTo').value = fmt(sun);
        document.querySelector('.date-preset[onclick*=\"week\"]')?.classList.add('active');
    } else if (type === 'month') {
        const first = new Date(now.getFullYear(), now.getMonth(), 1);
        const last = new Date(now.getFullYear(), now.getMonth()+1, 0);
        document.getElementById('dateFrom').value = fmt(first);
        document.getElementById('dateTo').value = fmt(last);
        document.querySelector('.date-preset[onclick*=\"month\"]')?.classList.add('active');
    }
    doFilter();
}


// ═══ Desktop hover preview ═══
(function(){
    if (window.innerWidth <= 768) return;
    let hoverTimer = null, hoverTip = null;
    document.addEventListener('mouseover', e => {
        const cell = e.target.closest('.title-cell');
        if (!cell) return;
        const link = cell.querySelector('a');
        if (!link) return;
        const title = link.textContent;
        if (title.length < 60) return; // short titles don't need preview
        hoverTimer = setTimeout(() => {
            if (hoverTip) hoverTip.remove();
            hoverTip = document.createElement('div');
            hoverTip.className = 'hover-preview-tip';
            hoverTip.textContent = title;
            const rect = link.getBoundingClientRect();
            hoverTip.style.cssText = `position:fixed;left:${rect.left}px;top:${rect.bottom + 4}px;max-width:500px;padding:8px 12px;background:var(--surface);color:var(--text);font-size:13px;line-height:1.5;border:1px solid var(--border);border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,.3);z-index:9998;word-break:break-word;`;
            document.body.appendChild(hoverTip);
        }, 600);
    }, {passive: true});
    document.addEventListener('mouseout', e => {
        if (e.target.closest('.title-cell')) {
            clearTimeout(hoverTimer);
            if (hoverTip) { hoverTip.remove(); hoverTip = null; }
        }
    }, {passive: true});
})();


// ═══ Pull-to-refresh (mobile only) ═══
(function(){
    if (window.innerWidth > 768) {
        const el = document.getElementById('pullIndicator');
        if (el) el.remove();
        return;  // desktop: skip
    }
    const indicator = document.getElementById('pullIndicator');
    if (!indicator) return;
    let startY = 0, pulling = false, ready = false;
    document.addEventListener('touchstart', e => {
        if (window.scrollY > 5) return;
        startY = e.touches[0].clientY;
        pulling = true;
    }, {passive:true});
    document.addEventListener('touchmove', e => {
        if (!pulling) return;
        const dy = e.touches[0].clientY - startY;
        if (dy > 20) { indicator.classList.add('show'); }
        if (dy > 80) { indicator.classList.add('ready'); indicator.textContent = '✓ 释放刷新'; ready = true; }
        else { indicator.classList.remove('ready'); indicator.textContent = '↓ 下拉刷新'; ready = false; }
    }, {passive:true});
    document.addEventListener('touchend', () => {
        if (!pulling) return;
        if (ready) { init(); toast('已刷新', 'success'); }
        indicator.classList.remove('show','ready');
        indicator.textContent = '↓ 下拉刷新';
        pulling = false; ready = false;
    });
})();

// ═══ Kebab menu toggle ═══
function toggleKebab(e, id, title, url, starred) {
    // Remove existing menus
    document.querySelectorAll('.kebab-menu,.kebab-overlay').forEach(el => el.remove());
    const overlay = document.createElement('div');
    overlay.className = 'kebab-overlay';
    overlay.onclick = () => { overlay.remove(); document.querySelector('.kebab-menu')?.remove(); };
    const menu = document.createElement('div');
    menu.className = 'kebab-menu';
    const items = [
        {label: '📤 分享', action: () => shareItem(id, title, url)},
        {label: '🔗 复制链接', action: () => { navigator.clipboard?.writeText(url).then(() => toast('链接已复制','success')); }},
        {label: '📋 复制标题', action: () => { navigator.clipboard?.writeText(title).then(() => toast('标题已复制','success')); }},
        {label: (starred?'☆':'⭐')+' '+(starred?'取消收藏':'收藏'), action: () => { toggleStar(id); }}
    ];
    items.forEach(item => {
        const btn = document.createElement('button');
        btn.textContent = item.label;
        btn.onclick = () => { item.action(); overlay.remove(); menu.remove(); };
        menu.appendChild(btn);
    });
    document.body.appendChild(overlay);
    document.body.appendChild(menu);
    // Position menu near the kebab button
    const btnRect = e.target.getBoundingClientRect();
    menu.style.top = (btnRect.bottom + 4) + 'px';
    menu.style.right = (window.innerWidth - btnRect.right) + 'px';
}

// ═══ Share ═══
function shareItem(id, title, url) {
    if (navigator.share) {
        navigator.share({title: title, url: url}).catch(() => {});
    } else {
        navigator.clipboard?.writeText(url).then(() => toast('链接已复制', 'success')).catch(() => {});
    }
}

// ═══ Read tracking ═══
function getReadItems() { try { return JSON.parse(localStorage.getItem('bidding_read')||'[]'); } catch(e) { return []; } }
function markRead(id) {
    const reads = getReadItems();
    if (!reads.includes(id)) { reads.push(id); localStorage.setItem('bidding_read', JSON.stringify(reads)); }
}
function isRead(id) { return getReadItems().includes(id); }
// Mark read on card click (mobile navigation) and apply class to existing rows
(function(){
    const origOpen = window.open;
    // Observe card clicks via event delegation
    document.addEventListener('click', e => {
        const row = e.target.closest('tr.data-row');
        if (!row || window.innerWidth > 768) return;
        const idMatch = row.id?.match(/row_(\d+)/);
        if (idMatch) { markRead(parseInt(idMatch[1])); row.classList.add('read'); }
    });
})();

// ═══ Smart empty state ═══
function smartEmptyMsg(query, dataCount) {
    const hasFilters = !!(document.getElementById("fCat")?.value
        || document.getElementById("fProv")?.value
        || document.getElementById("dateFrom")?.value
        || document.getElementById("dateTo")?.value
        || parseFloat(document.getElementById("fScore")?.value || 0)
        || parseFloat(document.getElementById("fBudget")?.value || 0));
    const clearBtn = `<div style="margin-top:12px"><button class="btn primary" onclick="resetF()" style="font-size:13px;padding:6px 20px">清除所有筛选</button></div>`;
    if (!query && !hasFilters && !starOnly) {
        if (tab === "win") return '📭 暂无中标数据，招标数据请切换到「招标」Tab查看';
        return '📭 暂无招标数据，系统正在持续采集，请稍后再来查看';
    }
    if (starOnly && !query && !hasFilters) return '⭐ 暂无收藏，点击列表中的 ☆ 即可收藏项目' + clearBtn;
    if (!query || query.length <= 2) return `🔍 未找到匹配结果 · 尝试更具体的关键词` + clearBtn;
    return `🔍 未找到「${query}」相关结果 · 尝试缩短关键词或扩大日期范围` + clearBtn;
}
