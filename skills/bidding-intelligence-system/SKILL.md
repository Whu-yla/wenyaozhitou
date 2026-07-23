---
name: bidding-intelligence-system
description: Architecture, editing conventions, and UX patterns for 文鳐智投 — the bidding intelligence monitoring dashboard. Covers the report pipeline, multi-select UX, SVG trend charts, briefing tag highlighting, export/checkbox logic, theme switching, and AI cover generation.
category: software-development
---

# 文鳐智投 Bid Intelligence System

## Data Quality Defense Architecture (V1.10 — 2026-06-25)

### Root Cause Analysis Discipline

**⛔ 用户铁律**：「你修复BUG都是结果，要深层次的分析原因，以后不要再犯！」

擦地 vs 根治：
| ❌ 擦地（修症状） | ✅ 根治（堵源头） |
|:--|:--|
| 发现平台首页→DELETE删掉 | 追溯管道：batch_crawler无页面类型判别→L1拦截器 |
| 发现锅炉100分→KEYWORD加排除 | 追溯管道：DIGITAL_GATE"系统""服务"太宽→三层架构 |
| 同样问题反复出现 | 写skill文档化根因→下次自查先看skill |

正确流程：定位脏数据→追溯来源(batch_crawler/nanwang_adapter/scoring)→堵源头(最早节点加拦截)→加防护层→写skill+changelog。

### 三层拦截架构

```
数据流 → L1(页面判别器) → 评分引擎 → L2(NON_DIGITAL_EXCLUDE) → L3(中标独立评分)
           ↓命中:丢弃                    ↓命中:丢弃                    ↓不相关:丢弃
```

- **L1**：`crawl_pipeline.py` `insert_notice()` 入口。14个平台信号词（您现在正在浏览/首页 >/APP下载/欢迎来到/公告信息 公告信息...）。命中直接 `return False`
- **L2**：`relevance_scorer.py` `score_item()` 0.5步。锅炉/煤矿/脱硫/洗衣/EPC总承包等直接拒掉，除非同时命中数字化强关键词（智慧工地/BIM/数字孪生）
- **L3**：`score_item()` 中标独立评分块。竞品中标→正常评分；非竞品→须有明确数字化关键词（管理平台/监控系统/APP/BIM）否则丢弃

详见 `data-quality-guard` skill。

### Scoring Engine Non-Digital Exclusion
```
NON_DIGITAL_EXCLUDE = [
    '锅炉','省煤器','空预器','脱硫','烟囱','吸收塔','除尘',
    '煤矿','胶带机','梭车','粉煤灰','罐车运输','矸石',
    '再热器','热网首站','供热管网','保温管道','热电联产',
    '工装洗涤','洗衣','文体馆维修','物业保洁','食堂',
    'EPC总承包','施工总承包','土建','桩基','基坑',
]
```
命中且无 strong_save 关键词 → 直接 return None。

### Winning-Specific Scoring (L3)
中标只关心竞品。`COMPETITOR_NAMES` 同步自 `competitor_tracker.py`：
- 竞品中标 → 基础分25 + 关键词加分
- 非竞品中标 → 基础分15，且必须命中 `STRONG_DIGITAL`（数字化/管理平台/监控系统/APP/BIM等）否则丢弃

## Professional Layout Pattern (V1.11 — 2026-06-25)

### Structural Grid
```
┌── Header (logo+title+status+theme) ──────────────────┐
│                                                        │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                 │
│  │120   │ │14    │ │14    │ │7     │  stats-row(4col) │
│  │招标  │ │今日  │ │高相关│ │中标  │                 │
│  └──────┘ └──────┘ └──────┘ └──────┘                 │
│                                                        │
│  [🔍 搜索________________] [客户▼] [地域▼] [相关▼]    │
│  [日期From] 至 [日期To]  ⭐收藏          [导出] [重置] │
│                                                        │
│  招标 120 │ 中标 7 │ 趋势 │ 竞品        ← tab-bar     │
│  ────────────────────────────────────────────────      │
│  序号│相关度│项目标题│客户│招标单位│地域│来源│日期│操作│
│  ────────────────────────────────────────────────      │
│  1   ████100  ☆ 广东电网...  🔵电力  —  广东  ...    │
│                                                        │
│  显示1-50条/共120条              « ‹ 1 2 3 › »        │
└────────────────────────────────────────────────────────┘
```

### Key CSS Variables
```css
:root{
  --bg:#0f172a; --surface:#1e293b; --border:#334155;
  --text:#e2e8f0; --muted:#94a3b8; --dim:#64748b;
  --accent:#3b82f6; --green:#10b981; --amber:#f59e0b;
  --radius:8px;
}
```

### Light Mode Priority
**必须在首行覆盖CSS变量**，否则 `var(--text)` 等仍为暗色值导致白底浅字：
```css
body.light{--bg:#f8fafc;--surface:#fff;--border:#e2e8f0;
  --text:#1e293b;--muted:#475569;--dim:#64748b;
  background:var(--bg);color:var(--text)}
```

### Table Columns (V1.11 reduced)
9列：序号(60px)/相关度(80px色条+数字)/标题(flex)/客户(100px hide-mobile)/招标单位(120px hide-mobile)/地域(80px)/来源(120px hide-mobile)/日期(100px)/操作(60px)

**不保留全选checkbox列**。收藏用 ★/☆ 在标题列内。

### Critical Init Pattern (V1.38 — DOMContentLoaded + API-first)

**⛔ OLD (fragile)**: `<script>init();</script>` inline after app.js. Async race with chat-widget.js loading, no error handling → silent blank page.

**✅ NEW (V1.38+)**: `DOMContentLoaded` event listener + `.catch()` + API-first with data.json fallback:

```html
<script src="app.js"></script>
<script src="/bidding/chat-widget.js?v=5"></script>
<script>
document.addEventListener('DOMContentLoaded', function(){
  init().catch(function(e){ console.error('init failed:', e); });
});
</script>
```

**Why DOMContentLoaded**: Prevents race condition where `init()` fires before `chat-widget.js` fully loads. The event ensures all scripts are parsed before init runs.

**report_generator.py template** (f-string — double-brace `{}`):
```python
<script src="app.js"></script>
<script>document.addEventListener('DOMContentLoaded',function(){{init().catch(function(e){{console.error('init failed:',e);}});}});</script></body></html>
```

**polish_report.py injection** guards against `init()` → must match `init().catch` not `init();`:
```python
if 'function toggleTheme' not in html:
    if 'init()' in html:
        html = html.replace('init().catch', THEME_JS + '\ninit().catch')
```

## API Performance: Filter → Cache → Prefetch (V1.44+)

When API responses are large relative to what the client actually needs, and network latency is high:

| Layer | Technique | Effect |
|:--|:--|:--|
| L1 Server-side filter | Add query params (`is_new_today=1`) so API returns only needed subset | 306KB→24KB (93%) |
| L2 Browser cache | `Cache-Control: public, max-age=30` in `_json()` | 30s repeat = instant |
| L3 Background prefetch | `fetch()` other tab's URL after init (no await) | First click = cache hit |

**Rule**: When client filters to <10% of data AND payload >100KB, prefer server-side query param over client-side `.filter()`.

**Frontend fast path**: Dedicated code branch in `apiFilter()` for stat-card filter modes, skipping paginated fetch + using `Promise.all` for parallel tab loads.

See `wenyao-bidding` → `references/api-performance-caching-prefetch.md` for full implementation.

### API-First Architecture (V1.38 — SQLite pagination + data.json fallback)

**Problem**: `data.json` grows linearly (333KB for 107 items → 30MB for 10,000). Mobile can't load 30MB.

**Solution**: Frontend loads from API (`/bidding/api/items`), only downloading the current page (~5KB). Falls back to `data.json` if API is down.

```
app.js init()
  → loadFromApi()        // preferred: /bidding/api/stats + /bidding/api/items
    → catch → loadFromJson()  // fallback: data.json full load
```

**API endpoints** (bookmark_server.py v2):
- `GET /bidding/api/stats` → `{bidding_total, winning_total, today_total, high_total, updated}`
- `GET /bidding/api/items?type=bidding&page=1&size=20&q=关键词&min_score=50&sort=relevance_score&sort_dir=desc&date_from=...&date_to=...&category=...&province=...&budget_min=...`

**Frontend key functions**:
- `loadFromApi()` — fetches stats + first page, calls `apiFilter()`
- `apiFilter()` — builds URLSearchParams from DOM filter values, fetches items, calls `renderTable()`
- `renderTable(data, total)` — renders rows from API response, handles pagination info
- `doFilter()` — delegates to `apiFilter()` when `useApi=true`, falls back to legacy client-side filtering
- `loadFromJson()` — legacy fallback: loads all data.json, populates allB/allW

**SQLite indexes for performance**:
```sql
CREATE INDEX idx_bid_score ON bidding_notices(relevance_score);
CREATE INDEX idx_bid_date ON bidding_notices(publish_date);
CREATE INDEX idx_bid_score_date ON bidding_notices(relevance_score, publish_date);
-- plus: category, province, procurement_owner, fetch_date
```

**Automatic degradation**: If API request fails → `useApi = false` → all subsequent `doFilter()` calls use legacy client-side filtering from the fallback-loaded data.json.

**Pipeline**: `report_generator.py` generates the base HTML → `polish_report.py` (v5) post-processes the HTML to inject theme CSS, filter bar restructuring, density toggle, score legend, OG tags, favicon, chat widget, and keyboard shortcut bindings. The `app.js` is a separate file loaded via `<script src>`. All HTML modifications MUST be mirrored in `polish_report.py` so timed regenerations don't lose them.

## V1.33 Interaction Patterns (2026-06-26)

### Filter Bar Alignment — Flex Parent Restructuring

**PITFALL**: Putting a `flex:1` spacer INSIDE a child that overflows its parent means the spacer operates on the child's intrinsic width, not the parent's constrained width. The spacer pushes nothing.

**Fix**: Move the elements you want right-aligned (export/reset buttons) UP one level to be direct siblings of the container with the `flex:1` spacer. Structure:

```
.filter-bar (display:flex, constrained width)
  .search-row (fixed width)
  .filter-scroll-wrapper (flex:1)
    .filter-row (flex-wrap:nowrap, overflow:visible)
  span (flex:1) ← THIS spacer pushes siblings right
  button 导出
  button 重置
```

Not:
```
.filter-bar
  .filter-scroll-wrapper (flex:1, overflow:visible)
    .filter-row
      span (flex:1) ← INEFFECTIVE: row wider than wrapper
      button 导出
```

### URL State Sync — Shareable Filter Views

Use `history.replaceState` + `URLSearchParams` to encode all filter values in the URL query string. On `init()`, call `restoreUrl()` to read params back. This makes filtered views shareable via link.

```javascript
function syncUrl() {
    const params = new URLSearchParams();
    // encode each filter: ?q=&cat=&prov=&score=&budget=&from=&to=&tab=&sort=&dir=&star=
    const qs = params.toString();
    history.replaceState(null, "", qs ? "?" + qs : window.location.pathname);
}
function restoreUrl() {
    const p = new URLSearchParams(window.location.search);
    // decode back: document.getElementById("search").value = p.get("q");
}
```

Call `syncUrl()` after `doFilter()` and `resetF()`. Must be idempotent — check if search already matches before replacing.

### IME Composition Handling — Chinese Input Safety

Without this, pressing Enter to confirm a Chinese IME candidate word triggers search prematurely.

```javascript
let composing = false;
searchEl.addEventListener('compositionstart', () => { composing = true; });
searchEl.addEventListener('compositionend', () => { composing = false; });
searchEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !composing) doFilter();
});
```

The `composing` variable MUST be scoped inside `init()` (not global) to avoid cross-session pollution.

### Collapsible Filters — "More Filters" Toggle ⛔ REJECTED 2026-06-26

> **USER REJECTED. All code rolled back. Do NOT reintroduce this feature.**

Reduce cognitive load by hiding low-frequency filters (dates, presets, budget) behind a toggle button. The collapsible wrapper uses `display:flex/none` controlled by `toggleMoreFilters()`, with preference persisted in `localStorage('moreFiltersOpen')`.

Toggle button is placed BETWEEN fScore and dateFrom — essential filters always visible, advanced filters collapsible.

### Density Toggle — Compact/Comfort Modes

A `≡` button in the header toggles `body.dense` CSS class. Compact mode reduces padding/font-size via CSS:

```css
body.dense tbody td { padding:4px 6px!important; font-size:11px!important }
body.dense tbody tr { height:32px!important }
body.dense .score-bar { height:4px!important }
```

Preference stored in `localStorage('density')`. On init, check stored value and apply class + update button text.

### Score Legend Tooltip — Boundary-Safe Positioning

Clicking `ⓘ` on the relevance score table header shows a fixed-position tooltip explaining the three color tiers (🟢85+ / 🟡60-84 / ⚪<60). The tooltip must be boundary-safe:

```javascript
let left = rect.left + rect.width/2 - 160; // center on trigger
if (left < 12) left = 12;
if (left + 320 > window.innerWidth - 12) left = window.innerWidth - 320 - 12;
```

Dismissed by clicking anywhere. Must not propagate click to sorting handler (`event.stopPropagation()`).

### Keyboard Shortcuts — Power User Efficiency

```javascript
/           → focus + select search box (skip if already in input/select)
Esc         → close chat panel OR close kebab menu OR resetF()  
Ctrl+Enter  → smartExport()
Ctrl+←/→    → sw("bid") / sw("win") — tab switching
Ctrl+S      → sw("star") — favorites tab
```

Register on `document` with `keydown`. Check `document.activeElement.tagName` to avoid stealing input focus.

### Empty State Enhancement

When `doFilter()` returns zero results, render a meaningful empty state with:
1. Context-aware message (no data vs filter mismatch vs star-only empty)
2. "清除所有筛选" button calling `resetF()`
3. Different messages for bid tab vs win tab vs star tab

```javascript
function smartEmptyMsg(query, dataCount) {
    const hasFilters = !!(... /* check all filter inputs */);
    const clearBtn = `<button onclick="resetF()">清除所有筛选</button>`;
    if (!query && !hasFilters && !starOnly) return '暂无数据...';
    return `未找到结果` + clearBtn;
}
```

### Hover Preview — Long Title Truncation Relief

Desktop-only: `mouseover` on `.title-cell` sets a 600ms timer. If the title is `>60` chars, show a fixed-position preview tip with full text. `mouseout` clears the timer and removes the tip.

```javascript
let hoverTimer = null, hoverTip = null;
document.addEventListener('mouseover', e => {
    const cell = e.target.closest('.title-cell');
    if (!cell) return;
    hoverTimer = setTimeout(() => { /* create and position tip */ }, 600);
});
document.addEventListener('mouseout', e => {
    if (e.target.closest('.title-cell')) { clearTimeout(hoverTimer); hoverTip?.remove(); }
});
```

Tip has `pointer-events:none` so it doesn't interfere with clicks.

### Polish Script — All HTML Changes Must Be Idempotent

Every HTML structure change must be guarded by an existence check in `polish_report.py`:

```python
if '密度按钮ID或CSS类' not in html:
    html = html.replace('锚点字符串', '替换为含新元素的字符串')
    modified = True
```

**⛔ GUARD CONDITION MUST USE PERMANENT VERSION MARKER**: Embed a CSS comment `/* V1.33-enhance */` at the end of ENHANCE_CSS, and guard injection with `if 'V1.33-enhance' not in html`. This version marker approach is superior to checking for a specific CSS class name because:
1. It's immune to feature rollback (if `hover-preview-tip` CSS is removed in a future update, a class-name guard would break)
2. It's self-documenting — you can see which version injected the CSS
3. It survives any ENHANCE_CSS content change as long as the marker comment remains

**Correct guard**: `if 'V1.33-enhance' not in html:`
**Old (fragile) guard**: `if 'hover-preview-tip' not in html:` — breaks if that rule is ever removed

**PITFALL**: Theme toggle button may use `class="btn ghost"` not `class="theme-toggle"`. Always inspect the ACTUAL generated HTML before writing replacement patterns.

**PITFALL**: `hermes_tools.read_file()` returns content with `LINE_NUM|` prefixes → file corruption.

### Post-Edit Safety — chmod Without Destroying Directories

**⛔ FORBIDDEN**: `chmod 644 /var/www/html/bidding/*` — the `*` glob matches DIRECTORIES, stripping their execute (`x`) bit. Nginx (running as `www-data`) cannot `stat()` files inside directories without `x` permission.

**✅ CORRECT**: Only chmod files, never directories:
```bash
find /var/www/html/bidding -maxdepth 1 -type f -exec chmod 644 {} \;
chmod 755 /var/www/html/bidding/img /var/www/html/bidding/img_gen
```

### Mobile/Desktop Isolation After Each Change

Every CSS or HTML structure change MUST be verified on BOTH viewports:
- Desktop (1280px): flex layouts, right-aligned buttons, 10-column table
- Mobile (≤768px): block layout, card-view table, horizontal-scroll filters

Common regression patterns:
1. Moving elements from `.filter-row` to `.filter-bar` (desktop alignment fix) → breaks mobile because `.filter-bar` is `display:block` on mobile
2. Adding global CSS rules (like `body.dense td`) → applies to mobile cards too
3. **localStorage crossover**: dense mode toggled on desktop, `localStorage('density')` persists, opening on mobile applies `body.dense` → mobile cards shrink. Defense: JS checks `innerWidth > 768` before restoring, CSS overrides `body.dense` inside `@media(max-width:768px)`.
4. Changing `overflow:hidden` to `overflow:visible` on `.filter-scroll-wrapper` → breaks mobile horizontal scroll
5. Injecting `@media` blocks with broken idempotency guard → duplicates stack up

```bash
cd /var/www/html/bidding && python3 << 'EOF'
with open('app.js') as f:
    js = f.read()
# ... modifications ...
with open('app.js', 'w') as f:
    f.write(js)
EOF
```

Or use the `patch` tool directly, which reads the file without line number contamination.

## Key Files

| File | Role |
|:--|:--|
| `scripts/report_generator.py` | Python f-string template → HTML + data.json |
| `scripts/polish_report.py` | v5 Post-process HTML: theme CSS, filter-bar restructuring, density toggle, score legend, OG/favicon, chat widget, keyboard shortcut bindings |
| `scripts/wecom_push.py` | WeChat Work push: AI covers + news cards |
| `scripts/bidding_engine.py` | Crawler + scoring engine v6 |
| `scripts/ai_cover.py` | Tongyi Wanxiang AI image generation |
| `/var/www/html/bidding/app.js` | All frontend logic (v=7 cache-busted) |
| `/var/www/html/bidding/index.html` | Generated report (do NOT edit directly — regenerated each time) |
| `/var/www/html/bidding/data.json` | Data payload for frontend |

## Frontend Patterns

### Multi-Select with Tag Highlighting

Categories and provinces use native `<select multiple>` listboxes (NOT `size="1"` dropdowns — those don't visually update on programmatic selection changes).

```css
select[multiple] { height: auto; max-height: 160px; overflow-y: auto; }
select[multiple] option:checked { background: linear-gradient(to right, #1d4ed8, #3b82f6); color: #fff; }
```

Briefing tags (`.brief .tag`) call `toggleFilter(selectId, value, this)`. The `updateTagHighlights()` function syncs `.tag.ac` class based on current select state:

```javascript
function updateTagHighlights() {
    const catVals = getSelectedValues("fCat");
    const provVals = getSelectedValues("fProv");
    document.querySelectorAll(".brief .tag").forEach(tag => {
        const oc = tag.getAttribute("onclick") || "";
        const m = oc.match(/toggleFilter\('(fCat|fProv)','([^']+)'\)/);
        if (m) {
            const vals = m[1] === "fCat" ? catVals : provVals;
            tag.classList.toggle("ac", vals.includes(m[2]));
        }
    });
}
```

Called from `toggleFilter()` after each selection change.

### SVG Trend Charts (Independent per card)

Each chart card (trendBid, trendWin, trendHigh) has INDEPENDENT bar/line mode using `new Map()`:

```javascript
const chartModes = new Map();
function toggleChartMode(cardId) {
    const cur = chartModes.get(cardId) || "bar";
    chartModes.set(cardId, cur === "line" ? "bar" : "line");
    renderTrends();
}
function getChartMode(cardId) { return chartModes.get(cardId) || "bar"; }
```

Do NOT use a plain `{}` object — use `Map` to guarantee isolation between cards.

### Checkbox + Row Numbers + Selective Export

Each table row has a checkbox with `data-id` attribute and a row number column. Export filters to checked rows or exports all if none checked:

```javascript
function exportExcel() {
    try {
        let data = getFilt();
        if (starOnly) data = data.filter(i => getStars().map(String).includes(String(i.id)));
        const checked = [...document.querySelectorAll(".row-check:checked")].map(cb => cb.dataset.id);
        if (checked.length > 0) data = data.filter(i => checked.includes(String(i.id)));
        // ... CSV generation with _idx column ...
    } catch(e) { alert("导出失败: " + e.message); }
}
```

### Type Coercion Safety

- `dataset.id` from HTML attributes is ALWAYS a string
- `i.id` from `data.json` is typically an integer
- `getStars()` returns JSON-parsed array (preserves original type)
- ALWAYS use `String()` or `.map(String)` before `includes()`/`indexOf()` comparisons
- NEVER use `parseInt(cb.dataset.id)` — just use `cb.dataset.id` and compare as strings

### Star Filter

`starOnly` global flag toggled by `swStar()`. Applied in both `doFilter()` and `exportExcel()`. Reset by `resetF()`. Stars persist in `localStorage` as `wenyaozhitou_stars`.

### Theme Toggle

Dark default, light mode via `body.light` CSS class. Persisted in `localStorage.theme`. Toggle button 🌓 in header. CSS in `polish_report.py` THEME_CSS variable.

### Category Sort Order

In `init()`, categories are sorted with "其他" always last:

```javascript
const sorted = [...s].sort((a, b) => {
    const ao = a.includes("其他"), bo = b.includes("其他");
    if (ao && !bo) return 1;
    if (!ao && bo) return -1;
    return a.localeCompare(b, "zh");
});
```

Select options are CLEARED and rebuilt (`sel.innerHTML = ""`) — never appended on top of existing options.

## Cache Busting

`app.js` is loaded with version parameter: `app.js?v=106`. Bump this in `index.html` line 457 whenever `app.js` changes significantly. Also bump in `report_generator.py` base template.

**Chat widget version sync**: When `chat-widget.js` or `chat-widget.css` changes, bump the `?v=N` in ALL of:
- `chat-widget.js` internal CSS link (`chat-widget.css?v=N`)
- `index.html` `<script src="chat-widget.js?v=N">`
- Any existing `report-*.html` files

Verify with: `grep -r 'chat-widget.*v=' /var/www/html/bidding/` — all must match.

## Archive Creation — Silent Data Bug (V1.37 fix)

**⛔ PITFALL**: `report_generator.py` line 87 prints `归档:{today}` but NEVER writes the archive file. This causes ALL items to be marked `is_new_today=true` because the yesterday-archive comparison finds an empty set.

**Root cause**: The code was:
```python
print(f"报告: {RD/'data.json'} ({len(allB)}招标+{len(allW)}中标) 归档:{today}")
# ← archive write was MISSING here
```

**Fix**: Add archive write after data.json generation:
```python
archive_dir = RD / today
archive_dir.mkdir(parents=True, exist_ok=True)
archive_ids = {"bidding": [{"id": r['id']} for r in allB], "winning": [{"id": r['id']} for r in allW]}
(archive_dir / "data.json").write_text(json.dumps(archive_ids, ensure_ascii=False))
```

**Bootstrap**: On first fix, manually create yesterday's archive from today's data so the diff produces correct `today_total`. Without this, the first run after the fix still shows all items as NEW.

## Copyright

Fixed format across all outputs: `© 中南电力设计院数智科技 · 文鳐智投 2026`

## User Preferences — UX Design Rules

### ⛔ DO NOT hide filters behind toggles

**2026-06-26**: 用户明确否决「更多筛选」折叠功能，要求回滚。用户偏好所有筛选控件始终可见、直接操作，不接受需要额外点击才能访问的隐藏式设计。筛选栏拥挤时用紧凑间距+减小字号解决，不用折叠。

### ✅ DO keep the filter bar flat and inline

- 所有筛选控件（搜索/客户/地域/相关度/日期/预算/导出/重置）一览无余
- 通过精简 padding、缩小字号、缩短 placeholder 来节省空间
- 不引入任何 toggle/accordion/collapse 隐藏控件

## Logo Management — Icon Replacement Workflow

When a new logo is provided:
1. Convert to PNG with max 200px height → `/bidding/img/logo.png`
2. Generate square favicon (32×32) → `/bidding/favicon-32x32.png` + `/bidding/favicon.ico`
3. Generate apple-touch-icon (180×180, white padded) → `/bidding/apple-touch-icon.png`
4. Generate OG share image (1200×630, dark bg + centered logo) → `/bidding/img_gen/og-share.png`
5. **Critical**: `chmod 755` the parent directories (`img/`, `img_gen/`) and `chmod 644` all new files. Nginx runs as `www-data` and cannot `stat()` files without execute permission on ancestor directories.
6. Verify: `curl -sI https://www.yfzx.online/bidding/img/logo.png` must return 200, not 403/404.
7. The chat widget automatically references `/bidding/img/logo.png` — no code change needed.

## Common Code Bugs (V1.33 audit — 2026-06-26)

### 1. sys.path.insert() Per-Request Pollution
**File**: `bookmark_server.py`
**Symptom**: `sys.path.insert(0, ...)` called inside request handler methods (`handle_get_chat`, `handle_post_chat`). After N requests, sys.path has N duplicate entries.
**Fix**: Move `sys.path.insert()` and `from chat_engine import ...` to module top-level. Run once at import time.

### 2. Bare `except: pass` Swallowing Errors
**File**: `report_generator.py`
**Symptom**: `subprocess.run()` calls to `polish_report.py` and `wecom_push.py` wrapped in `try: ... except: pass`. If either fails, zero diagnostic output.
**Fix**: Catch `Exception as e`, capture stderr, print `⚠️ polish_report 失败: {e}`.

### 3. Subprocess `text=True` Omission
**Related to #2**: `subprocess.run(..., capture_output=True)` without `text=True` returns bytes. stderr inspection becomes garbled. Always add `text=True` for readable error output.

## Common Fix Recipes

### "Export button does nothing"
→ Check: `parseInt(cb.dataset.id)` should be `cb.dataset.id` (string)
→ Add try-catch around export logic
→ Ensure `String()` coercion on ID comparisons

### "Trend charts linked together"
→ Check: is `chartModes` a `new Map()` or a plain `{}`?
→ Each cardId must have independent get/set

### "Tag click shows no highlight"
→ Check: `updateTagHighlights()` exists and is called from `toggleFilter()`
→ Check: `.tag.ac` CSS class exists with visible background

### "Other label not at bottom"
→ Check: `init()` uses `sel.innerHTML = ""` before rebuilding
→ Check: sort function has explicit `ao/bo` comparison for "其他"

### "Multi-select looks wrong after click"
→ Check: select has `multiple` but NOT `size="1"`
→ Use `max-height: 160px; overflow-y: auto` for scrollable listbox
→ Ensure `dispatchEvent(new Event("change"))` fires after programmatic selection

### "Export/Reset buttons don't align with stat cards"
→ Check: are they inside `.filter-scroll-wrapper` > `.filter-row`? The `flex:1` spacer INSIDE filter-row is ineffective because the row overflows the wrapper.
→ Fix: Move export/reset UP to be direct children of `.filter-bar`, with a `flex:1` spacer between `.filter-scroll-wrapper` and the right controls.
→ Verify: `reset_right_edge ≈ filterBar_right - 24px(padding) ≈ statsRow_content_right`

### "Theme toggle button CSS class not matching"
→ The theme button may be `<button class="btn ghost" onclick="toggleTheme()">` NOT `<button class="theme-toggle">`. Always inspect the actual HTML before writing `.replace()` patterns.
→ Use `browser_console` with `document.querySelector('[onclick*="toggleTheme"]').outerHTML` to verify.
