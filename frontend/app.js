// 文鳐智投 v125 — API缓存30s + 预加载中标Tab
let allB = [], allW = [], tab = "bid", pg = 1, ps = 20, sf = "relevance_score", sd = -1;
let brief = {}, totalBidding = 0, totalWinning = 0;
let realBidding = 0, realWinning = 0;  // immutable real totals from stats API (badges use these)
let starOnly = false;
let selectedIds = new Set();
let expandedId = null;
let useApi = true;  // 优先走API，失败降级data.json

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
    document.getElementById("tBidTb").innerHTML = skeletonRows(ps);
    let composing = false;
    const searchEl = document.getElementById('search');
    if (searchEl) {
        searchEl.addEventListener('compositionstart', () => { composing = true; });
        searchEl.addEventListener('compositionend', () => { composing = false; });
        searchEl.addEventListener('keydown', e => { if (e.key === 'Enter' && !composing) { pg=1; apiFilter(); } });
    }
    const searchBtn = document.getElementById('searchBtn');
    if (searchBtn) searchBtn.addEventListener('click', () => { pg=1; apiFilter(); });
    try {
        // 优先尝试API
        await loadFromApi();
    } catch(e) {
        console.warn('API不可用，降级data.json:', e.message);
        useApi = false;
        await loadFromJson();
    }
    // IME + keyboard shortcuts
    const input = document.getElementById('search');
    if (input) {
        input.addEventListener('compositionstart', () => composing = true);
        input.addEventListener('compositionend', () => composing = false);
        input.addEventListener('keydown', e => { if (e.key === 'Enter' && !composing) { pg=1; apiFilter(); } });
    }
    document.addEventListener('keydown', e => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
        if (e.key === '/' && !e.ctrlKey && !e.metaKey) { e.preventDefault(); document.getElementById('search')?.focus(); }
        if (e.key === 'Escape') resetF();
        if (e.ctrlKey && e.key === 'Enter') smartExport();
    });
    renderPsSelector('psSelBid'); renderPsSelector('psSelWin');
    // ── Back to top button ──
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
    // ── Mobile filter toggle ──
    const filterToggleBtn = document.getElementById('filterToggleBtn');
    if (filterToggleBtn) {
        const wrapper = document.querySelector('.filter-scroll-wrapper');
        filterToggleBtn.addEventListener('click', () => {
            if (wrapper) {
                const expanded = wrapper.classList.toggle('expanded');
                filterToggleBtn.textContent = expanded ? '✕ 关闭' : '☰ 筛选';
                filterToggleBtn.classList.toggle('active', expanded);
            }
        });
    }
    restoreFilters();
    loadBookmarksFromServer();
}

async function loadFromApi() {
    // 加载统计
    const sr = await fetch('/bidding/api/stats');
    const stats = await sr.json();
    if (!stats.ok) throw new Error('stats failed');
    totalBidding = stats.bidding_total;
    totalWinning = stats.winning_total;
    realBidding = stats.bidding_total;   // immutable real total for badges
    realWinning = stats.winning_total;
    brief = { today_total: stats.today_total, today_high: stats.high_total };
    document.getElementById("statBidTotal").textContent = totalBidding;
    document.getElementById("statWinTotal").textContent = totalWinning;
    document.getElementById("statToday").textContent = stats.today_total || 0;
    document.getElementById("statHigh").textContent = stats.high_total || 0;
    const el = document.getElementById('lastUpdate');
    if (el) el.textContent = '数据更新: ' + (stats.updated ? stats.updated.substring(0,16).replace('T',' ') : '—');
    document.getElementById("cntBid").textContent = totalBidding;
    document.getElementById("cntWin").textContent = totalWinning;
    document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('loading'));
    // 加载首页数据
    await apiFilter();
    // 后台预加载中标 Tab 数据到浏览器缓存（Cache-Control: max-age=30）
    fetch('/bidding/api/items?type=winning&page=1&size=20&sort=relevance_score&sort_dir=desc&min_score=1')
      .catch(() => {});
    // 加载下拉选项
    loadDropdowns();
}

async function loadDropdowns() {
    try {
        const [br, wr] = await Promise.all([
            fetch('/bidding/api/items?type=bidding&size=0'),
            fetch('/bidding/api/items?type=winning&size=0')
        ]);
        const cats = new Set(), provs = new Set();
        // 从首页数据提取
        [...allB, ...allW].forEach(i => {
            if (i.category) cats.add(i.category);
            if (i.province) provs.add(i.province);
        });
        [["fCat", cats], ["fProv", provs]].forEach(([id, s]) => {
            const sel = document.getElementById(id);
            if (!sel) return;
            sel.innerHTML = '<option value="">全部' + (id==='fCat'?'客户':'地域') + '</option>';
            [...s].sort().forEach(v => { const o = document.createElement('option'); o.value = v; o.textContent = v; sel.appendChild(o); });
        });
    } catch(e) { console.warn('dropdowns failed:', e); }
}

async function loadFromJson() {
    const r = await fetch("/bidding/data.json");
    const d = await r.json();
    allB = d.bidding || [];
    allW = d.winning || [];
    brief = d.brief || {};
    totalBidding = allB.length;
    totalWinning = allW.length;
    realBidding = allB.length;
    realWinning = allW.length;
    document.getElementById("statBidTotal").textContent = allB.length;
    document.getElementById("statWinTotal").textContent = allW.length;
    document.getElementById("statToday").textContent = brief.today_total || 0;
    document.getElementById("statHigh").textContent = [...allB, ...allW].filter(i => (i.relevance_score||0) >= 70).length;
    const fetches = [...allB, ...allW].map(i => i.fetch_date).filter(Boolean).sort();
    const latestFetch = fetches[fetches.length-1] || '';
    const dt = latestFetch ? latestFetch.substring(0,16).replace('T',' ') : '—';
    const el = document.getElementById('lastUpdate');
    if (el) el.textContent = '数据更新: ' + dt;
    document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('loading'));
    document.getElementById("cntBid").textContent = allB.length;
    document.getElementById("cntWin").textContent = allW.length;
    renderTrendIndicators();
    // 下拉
    const cats = new Set(), provs = new Set();
    [...allB, ...allW].forEach(i => { if (i.category) cats.add(i.category); if (i.province) provs.add(i.province); });
    [["fCat", cats], ["fProv", provs]].forEach(([id, s]) => {
        const sel = document.getElementById(id);
        if (!sel) return;
        sel.innerHTML = '<option value="">全部' + (id==='fCat'?'客户':'地域') + '</option>';
        [...s].sort().forEach(v => { const o = document.createElement('option'); o.value = v; o.textContent = v; sel.appendChild(o); });
    });
    doFilter();
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
// ═══ API-based filtering ═══
let _apiSeq = 0;  // prevent stale async callbacks
async function apiFilter() {
    if (!useApi) { doFilter(); return; }
    const seq = ++_apiSeq;  // capture version before async
    // Snapshot mutable globals — prevent async race (e.g. starOnly flipped during fetch)
    const _starOnly = starOnly;
    const _tab = tab;
    const _activeStatFilter = activeStatFilter;
    
    // ═══ Fast path: 'today' filter — skip page-1 fetch, load both tabs in parallel ═══
    if (_activeStatFilter === 'today') {
        try {
            const fetches = ['bidding', 'winning'].map(async (tt) => {
                const op = new URLSearchParams(); op.set('type', tt); op.set('size', '200'); op.set('min_score', '1');
                op.set('is_new_today', '1');  // 服务端过滤，响应从306KB→24KB
                const r = await fetch('/bidding/api/items?' + op.toString());
                const d = await r.json();
                if (d.ok) { return { tt, filtered: d.data }; }
                return null;
            });
            const results = await Promise.all(fetches);
            if (seq !== _apiSeq) return;
            for (const res of results) {
                if (!res) continue;
                if (res.tt === 'bidding') { totalBidding = res.filtered.length; allB = res.filtered; }
                else { totalWinning = res.filtered.length; allW = res.filtered; }
            }
            const renderData = _tab === 'bid' ? allB : allW;
            const renderTotal = _tab === 'bid' ? totalBidding : totalWinning;
            renderTable(renderData, renderTotal);
            updateApiStats();
            saveFilters();
        } catch(e) {
            console.error('apiFilter today failed:', e);
            useApi = false; doFilter();
        }
        return;
    }
    
    // ═══ Normal path: paginated fetch ═══
    const params = new URLSearchParams();
    params.set('type', _tab === 'bid' ? 'bidding' : 'winning');
    params.set('page', String(pg));
    params.set('size', String(ps));
    params.set('sort', sf);
    params.set('sort_dir', sd > 0 ? 'asc' : 'desc');
    
    const q = (document.getElementById('search')?.value || '').trim();
    if (q) params.set('q', q);
    
    const sc = parseFloat(document.getElementById('fScore')?.value || 0);
    if (sc || _activeStatFilter === 'high') params.set('min_score', _activeStatFilter === 'high' ? '70' : String(sc));

    const bgt = parseFloat(document.getElementById('fBudget')?.value || 0);
    if (bgt) params.set('budget_min', String(bgt));
    
    const cat = document.getElementById('fCat')?.value;
    if (cat) params.set('category', cat);
    const prov = document.getElementById('fProv')?.value;
    if (prov) params.set('province', prov);
    const df = document.getElementById('dateFrom')?.value;
    if (df) params.set('date_from', df);
    const dt = document.getElementById('dateTo')?.value;
    if (dt) params.set('date_to', dt);
    
    try {
        const r = await fetch('/bidding/api/items?' + params.toString());
        const d = await r.json();
        if (!d.ok) throw new Error('API error');
        
        // Drop stale response if a newer apiFilter() was launched
        if (seq !== _apiSeq) return;
        
        if (_tab === 'bid') { allB = d.data; totalBidding = d.total; }
        else { allW = d.data; totalWinning = d.total; }
        
        // Star filter — client-side (API doesn't know about bookmarks)
        if (_starOnly) {
            const starIds = new Set(getStars());
            if (_tab === 'bid') { allB = allB.filter(i => starIds.has(String(i.id))); }
            else { allW = allW.filter(i => starIds.has(String(i.id))); }
        }
        
        // Stat filters
        if (_activeStatFilter === 'high') {
            if (_tab === 'bid') { allB = allB.filter(i => (i.relevance_score||0) >= 70); totalBidding = allB.length; }
            else { allW = allW.filter(i => (i.relevance_score||0) >= 70); totalWinning = allW.length; }
            // Also fetch other tab total for badge
            const otherType = _tab === 'bid' ? 'winning' : 'bidding';
            const op = new URLSearchParams(); op.set('type', otherType); op.set('size', '0'); op.set('min_score', '70');
            try {
                const or = await fetch('/bidding/api/items?' + op.toString());
                const od = await or.json();
                if (od.ok) {
                    if (otherType === 'bidding') totalBidding = od.total;
                    else totalWinning = od.total;
                }
            } catch(_) {}
        }
        
        const renderData = _tab === 'bid' ? allB : allW;
        const renderTotal = _tab === 'bid' ? totalBidding : totalWinning;
        renderTable(renderData, renderTotal);
        updateApiStats();
        saveFilters();
    } catch(e) {
        console.error('apiFilter failed:', e);
        useApi = false;  // temporary — sw() resets on next tab switch
        doFilter();
    }
}

function updateApiStats() {
    // When stat filter active: BOTH tabs show filtered counts (so they add up to card number)
    // When inactive: both tabs show real totals
    const showBid = (activeStatFilter && !starOnly) ? totalBidding : realBidding;
    const showWin = (activeStatFilter && !starOnly) ? totalWinning : realWinning;
    document.getElementById('cntBid').textContent = showBid;
    document.getElementById('cntWin').textContent = showWin;
    document.getElementById('statBidTotal').textContent = showBid;
    document.getElementById('statWinTotal').textContent = showWin;
    document.getElementById('cntStar').textContent = getStars().length;
}

function renderTable(data, total) {
    const tb = tab === 'bid' ? 'tBidTb' : 'tWinTb';
    const tbody = document.getElementById(tb);
    if (!tbody) return;
    
    if (data.length === 0) {
        const msg = starOnly ? '⭐ 暂无收藏，在招标列表中点击 ☆ 即可收藏' : (document.getElementById('search')?.value ? '未找到匹配结果' : '暂无数据');
        tbody.innerHTML = `<tr class="empty-msg"><td colspan="11">${msg}</td></tr>`;
        // Update pagination
        const pgInfo = document.getElementById('pgInfo');
        if (pgInfo) pgInfo.textContent = '0/0';
        const pgInfoW = document.getElementById('pgInfoW');
        if (pgInfoW) pgInfoW.textContent = '0/0';
        const pgNums = document.getElementById('pgNums');
        if (pgNums) pgNums.innerHTML = '';
        const pgNumsW = document.getElementById('pgNumsW');
        if (pgNumsW) pgNumsW.innerHTML = '';
        return;
    }
    
    // Sort client-side for secondary sort stability
    if (sf !== 'relevance_score') {
        data.sort((a, b) => {
            const va = a[sf] || '', vb = b[sf] || '';
            return sd > 0 ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
        });
    }
    
    const stars = new Set(getStars());
    let html = '';
    data.forEach((i, idx) => {
        const n = (pg - 1) * ps + idx + 1;
        const sc = i.relevance_score || 0;
        const scoreColor = sc >= 85 ? '#10b981' : sc >= 60 ? '#f59e0b' : '#94a3b8';
        const scoreBar = `<span class="score-bar" style="width:${Math.min(sc,100)}%;background:${scoreColor}"></span>`;
        const newBadge = (i.is_new_today) ? '<span class="new-badge">NEW</span> ' : '';
        const title = esc(i.title || '').substring(0, 120);
        const owner = (i.procurement_owner || '').substring(0, 40);
        const cat = (i.category || '').replace(/^[^\u4e00-\u9fff]+/, '');
        const budget = i.budget_amount ? (parseFloat(i.budget_amount) >= 10000 ? (parseFloat(i.budget_amount)/10000).toFixed(1)+'万' : i.budget_amount) : '—';
        const pubDate = (i.publish_date || '').substring(0, 10);
        const source = (i.source_site || '').substring(0, 20);
        const url = i.source_url || '#';
        const isStarred = stars.has(String(i.id));
        const isChecked = selectedIds.has(String(i.id));
        const star = `<span class="star${isStarred?' active':''}" onclick="event.stopPropagation();toggleStar('${i.id}')">${isStarred?'⭐':'☆'}</span>`;
        const menuHtml = window.innerWidth <= 768 ? `<span class="kebab-btn" onclick="event.stopPropagation();toggleKebab(event,${i.id},'${esc(title).replace(/'/g,"\\'")}','${url.replace(/'/g,"\\'")}',${isStarred})">⋯</span>` : '';
        
        html += `<tr id="row_${i.id}" class="data-row">
            <td style="text-align:center"><input type="checkbox" onchange="toggleSelect('${i.id}',this.checked)" ${isChecked?'checked':''}></td>
            <td style="text-align:center;color:var(--dim)">${n}</td>
            <td><div class="score-bar-wrap">${scoreBar}</div><span class="score-num">${sc.toFixed(0)}</span></td>
            <td class="title-cell">${newBadge}${star} ${menuHtml} <a href="${url}" target="_blank" onclick="markRead(${i.id})">${title}</a></td>
            <td class="hide-mobile"><span class="cat-tag">${cat||'—'}</span></td>
            <td class="hide-mobile">${owner||'—'}</td>
            <td class="hide-mobile">${budget}</td>
            <td class="hide-mobile">${i.region||i.province||'—'}</td>
            <td class="hide-mobile">${source}</td>
            <td class="hide-mobile">${pubDate}</td>
            <td><a href="${url}" target="_blank" class="link-btn" onclick="event.stopPropagation()">查看</a></td>
        </tr>`;
    });
    
    tbody.innerHTML = html;
    
    // Pagination info — when star filtering, use filtered data count; otherwise use API total
    const actualCount = starOnly ? data.length : total;
    const totalPages = Math.ceil(actualCount / ps) || 1;
    const pgInfoText = `${pg}/${totalPages} 共${actualCount}条`;
    const pgInfo = document.getElementById('pgInfo');
    if (pgInfo) pgInfo.textContent = pgInfoText;
    const pgInfoW = document.getElementById('pgInfoW');
    if (pgInfoW) pgInfoW.textContent = pgInfoText;
    renderPsSelector('psSelBid');
    if (document.getElementById('psSelWin')) renderPsSelector('psSelWin');
    // Pagination buttons
    renderPg('pgNums', pg, totalPages);
    if (tab === 'win') renderPg('pgNumsW', pg, totalPages);
}

// ═══ Dynamic stat cards — reflect filtered counts ═══
function updateStats(data) {
    // When stat-card filter is active, stat cards stay at GLOBAL counts
    // (the banner already tells you what subset you're viewing)
    if (activeStatFilter) {
        document.getElementById("statBidTotal").textContent = allB.length;
        document.getElementById("statToday").textContent = brief.today_total || 0;
        document.getElementById("statHigh").textContent = [...allB, ...allW].filter(i => (i.relevance_score||0) >= 70).length;
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
        document.getElementById("statHigh").textContent = [...allB, ...allW].filter(i => (i.relevance_score||0) >= 70).length;
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
    if (activeStatFilter === 'today') d = d.filter(i => (i.is_new_today || 0) === 1);
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
    if (useApi) { apiFilter(); return; }
    // Legacy: client-side filter (data.json fallback)
    let data = getFiltFor(tab === 'bid' ? allB : allW);
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
            const starred = getStars().includes(String(i.id));
            const menuHtml = window.innerWidth <= 768 ? `<span class="kebab-btn" onclick="event.stopPropagation();toggleKebab(event,${i.id},'${esc(title).replace(/'/g,"\\'")}','${link.replace(/'/g,"\\'")}',${starred})">⋯</span>` : '';
            const newDot = isNew(i) ? '<span class="new-badge">NEW</span>' : '';
            const amt = i.winning_amount||i.budget_amount||'';
            const amtDisp = amt ? (parseFloat(amt)>=10000 ? (parseFloat(amt)/10000).toFixed(0)+'万' : amt) : '—';
            return `<tr class="data-row${readCls}" onclick="if(window.innerWidth<=768){markRead(${i.id});this.classList.add('read');window.open('${link}','_blank')}else{toggleDetail(${i.id})}" style="cursor:pointer">
                <td style="text-align:center;width:32px"><input type="checkbox" ${checked} onclick="event.stopPropagation();toggleSelect(${i.id})" style="cursor:pointer;accent-color:var(--accent)"></td>
                <td data-label="序号" style="text-align:center;color:var(--dim);font-size:11px">${st+idx+1}</td>
                <td data-label="相关度"><span class="score-bar ${barCl}" style="${barW}"></span><span style="font-size:11px;color:var(--muted)">${sc.toFixed(0)}分</span></td>
                <td class="title-cell">${newDot} ${menuHtml} <a href="${link}" target="_blank" onclick="event.stopPropagation()">${title}</a></td>
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
    // DROP stale guard: empty data after star filter was blocking tab switch
    selectedIds.clear(); expandedId = null; useApi = true;  // always retry API on tab switch
    tab = t; pg = 1;
    if (t === "star") { 
        starOnly = true; tab = "bid";
        // Stat filters don't apply to starred view — deactivate
        activeStatFilter = null;
        renderStatBanner();
        document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
    }
    else { 
        starOnly = false;
    }
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
    else if (type === 'win') { sw('win'); }
    // For 'today'/'high': stay on current tab, just apply filter
    // (DON'T call sw() — it clears activeStatFilter, self-defeating)
    else {
        // Ensure we're on bid tab without clearing the filter
        if (tab !== 'bid') { starOnly = false; tab = 'bid'; pg = 1; }
    }
    
    pg = 1; sf = 'relevance_score'; sd = -1;
    renderStatBanner();
    if (useApi) { apiFilter(); } else { doFilter(); }
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
    const todayBids = allB.filter(i => isNew(i));
    const todayWins = allW.filter(i => isNew(i));
    const highBids = allB.filter(i => (i.relevance_score || 0) >= 70);
    const highWins = allW.filter(i => (i.relevance_score || 0) >= 70);
    let data = tab === 'bid' ? [...allB] : [...allW];
    if (activeStatFilter === 'high') data = data.filter(i => (i.relevance_score || 0) >= 70);
    if (activeStatFilter === 'today') data = data.filter(i => (i.is_new_today || 0) === 1);
    
    let label, count;
    if (activeStatFilter === 'today') {
        const parts = [];
        if (todayBids.length) parts.push(`招标${todayBids.length}条`);
        if (todayWins.length) parts.push(`中标${todayWins.length}条`);
        label = '今日新增 · ' + parts.join(' + ');
        count = todayBids.length + todayWins.length;
    } else if (activeStatFilter === 'high') {
        const parts = [];
        if (highBids.length) parts.push(`招标${highBids.length}条`);
        if (highWins.length) parts.push(`中标${highWins.length}条`);
        label = '高相关 · ' + parts.join(' + ');
        count = highBids.length + highWins.length;
    } else {
        const labels = { total: '全部招标', high: '高相关招标', win: '全部中标' };
        label = labels[activeStatFilter] || activeStatFilter;
        count = data.length;
    }
    banner.innerHTML = `<span>📊 ${label} · ${count} 条</span>
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
// NEW badge: 今天新入库（区别于"今天发布"）——基于 is_new_today 字段
function isNew(i) {
    return (i.is_new_today || 0) === 1;
}
function isTodayFetched(i) { const fd=(i.fetch_date||'').substring(0,10); return fd===todayStr(); }
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
