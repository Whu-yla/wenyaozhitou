# API/Data.json 双路径分叉陷阱 (V1.39+)

## 背景

前端架构支持两条数据路径：
1. **API 路径** (`useApi=true`): `apiFilter()` → `fetch('/bidding/api/items')` → `renderTable()`
2. **降级路径** (`useApi=false`): `doFilter()` → 客户端过滤 `allB/allW` → 内联渲染

两条路径共用部分函数（`renderTable`, `updateApiStats`, `sw`），但各自有专属逻辑。**任一函数对两条路径的假设不一致，就会导致一条路径正常、另一条崩溃。**

---

## 已知陷阱分类

### 陷阱 1: 守卫条件仅适用单路径

**案例**: `sw()` 中的守卫：
```javascript
if (!allB.length && !allW.length) { toast('数据加载中...'); return; }
```
- 初始加载时：allB/allW 为空，守卫正确拦截
- **收藏 Tab 后**：`starOnly` 客户端过滤导致 `allB = []`，守卫误判为"数据未加载"，拦截所有后续 Tab 切换
- **修复**：移除守卫，信任 `apiFilter()` 重新 fetch

**教训**: 守卫条件依赖可变全局状态时，必须考虑所有路径对其的副作用。

### 陷阱 2: 函数仅存在于降级路径

**案例**: `renderTable()` 调用 `emptyMsg()`：
```javascript
// API 路径 renderTable():
tbody.innerHTML = `<tr>...${emptyMsg()}</tr>`;  // ❌ emptyMsg 不存在!
```
- `emptyMsg` 只在 `doFilter()` 内部定义为局部 `const` 变量
- API 路径的 `renderTable()` 无法访问它 → ReferenceError → catch → `useApi=false` → 全站降级

**教训**: 共享函数中引用的任何标识符，必须确认在两条路径中都可访问。最安全的做法是内联计算而非引用外部函数。

### 陷阱 3: 函数名不一致

**案例**: `init()` 调用 `loadBookmarks()`，但实际函数名为 `loadBookmarksFromServer()`
- 降级路径可能在其他地方有同名兼容函数
- API 路径没有 → ReferenceError → init 中断

**教训**: 全局函数引用必须在两条路径中一致。改名后必须 `grep` 所有引用点。

### 陷阱 4: Async 竞态 + 降级锁死

**案例**: `apiFilter()` 中：
```javascript
} catch(e) {
    useApi = false;  // ⛔ 任何错误都永久降级
    doFilter();
}
```
- 一旦 `renderTable()` 抛异常（如陷阱2），`useApi` 永久 = false
- 虽然后续 `sw()` 重置 `useApi=true`，但如果在同一次 Tab 内出错则无恢复机会

**修复**: 引入 `_apiSeq` 竞态保护 + `sw()` 中重置 `useApi=true`

---

### 陷阱 5: 全局计数被过滤操作污染 (V1.40)

**案例**: `apiFilter()` 中 `totalBidding`/`totalWinning` 被覆盖：
```javascript
// Star 过滤
if (starOnly) {
    allB = allB.filter(i => starIds.has(String(i.id)));
    totalBidding = allB.length;  // ⛔ 把 94 盖成 0！Badge 全错！
}
// Stat 过滤副作用
if (activeStatFilter) {
    // 额外 fetch 另一 Tab 的过滤计数 → totalWinning = 0！
}
```
- `totalBidding`/`totalWinning` 是**可变工作变量**，被 `apiFilter()`、star filter、stat filter 轮番覆盖
- `updateApiStats()` 用它们渲染所有 Badge → 收藏 Tab 激活时招标 Badge 变 0；今日新增取消后中标 Badge 卡在 0

**修复**: 引入 `realBidding`/`realWinning` 不可变锚定变量：
```javascript
let realBidding = 0, realWinning = 0;  // 只在 loadFromApi() / 降级后各设一次

function updateApiStats() {
    // Badge 永远用 real 值，不随过滤变化
    document.getElementById('cntBid').textContent = realBidding;
    document.getElementById('cntWin').textContent = realWinning;
}
```
- `totalBidding`/`totalWinning` → 表格「共 X 条」用（可变）
- `realBidding`/`realWinning` → Badge 用（不可变）

**教训**: 任何被多个过滤器修改的全局计数变量，必须区分「工作值」和「锚定值」。

### 陷阱 6: activeStatFilter 未传递到 API 参数 (V1.40)

**案例**: 点击「今日新增」卡片 → `apiFilter()` 不传 `date_from`：
```javascript
// statClick('today') 设置 activeStatFilter = 'today'
// 但 apiFilter() 只检查了 'high':
if (sc || activeStatFilter === 'high') params.set('min_score', ...);
// 'today' 被忽略！API 返回全部 94 条
```
- `statClick('today')` 还清了 `dateFrom`/`dateTo` 输入框 → `apiFilter()` 更不可能从输入框取到日期
- 用户看到和没点一样的结果

**修复**: `apiFilter()` 中显式处理每个 activeStatFilter 类型：
```javascript
if (activeStatFilter === 'today') {
    const today = new Date().toISOString().slice(0, 10);
    params.set('date_from', today);
}
```

**教训**: 新增 statFilter 类型时，必须同时在 `apiFilter()` 中添加对应的 API 参数映射。

### 陷阱 7: HTML 版本号未同步 → 浏览器缓存旧 JS (V1.40)

**案例**: `app.js` 已修改 4 轮，但 `index.html` 仍引用 `app.js?v=112`：
```html
<!-- index.html 没更新 -->
<script src="app.js?v=112"></script>  <!-- 浏览器缓存旧代码！ -->
```
- 用户看到的是缓存的旧 JS → 所有修复在前端不生效
- 收藏 Tab 仍显示 94 条、今日新增仍无效

**修复**: 每次改完 `app.js` 后必须同步更新 `index.html` 中的版本号：
```html
<script src="app.js?v=116"></script>  <!-- 强制刷新 -->
```

**教训**: `app.js` 修改 → `index.html` 版本号 bump。两步不可分割。

### 陷阱 8: Async 竞态 — 可变全局在被 await 期间遭篡改 (V1.40)

**案例**: `apiFilter()` 读取 `starOnly`、`tab`、`activeStatFilter` 后执行 `await fetch()`，期间用户切 Tab → `sw('bid')` 把 `starOnly` 改成 `false` → 响应回来时 star filter 跳过 → 收藏 Tab 显示 94 条。

```javascript
async function apiFilter() {
    // ❌ 这些全局变量在 await 期间可被 sw()/statClick() 修改
    params.set('type', tab === 'bid' ? 'bidding' : 'winning');
    const r = await fetch(...);  // ← 此时 tab/starOnly 可能已变！
    // ...
    if (starOnly) { ... }  // ← 读到的可能已是 false
}
```

**修复**: 入口处快照所有可变全局，后续只用快照值：
```javascript
async function apiFilter() {
    const seq = ++_apiSeq;
    // ✅ 快照——不受外部修改影响
    const _starOnly = starOnly;
    const _tab = tab;
    const _activeStatFilter = activeStatFilter;
    // 后续全部用 _starOnly / _tab / _activeStatFilter
}
```

**教训**: 任何 async 函数中读取可变全局变量，必须在第一个 `await` 之前快照到 `const`。包括 `starOnly`、`tab`、`activeStatFilter`、`pg`、`sf`、`sd` 等。

### 陷阱 9: Badge 分层逻辑 — stat 过滤 vs star 模式冲突 (V1.40)

**案例**: `updateApiStats()` 用 `realBidding`（不可变锚定值）渲染 Badge，但用户点「高相关 26」后 Badge 应该显示 21/5（过滤值）。同时收藏 Tab 激活时 Badge 应显示 94/13（真实值），即使 `activeStatFilter` 仍为 'high'。

```javascript
// ❌ 永远用 real → stat 过滤时 Badge 不变
document.getElementById('cntBid').textContent = realBidding;

// ❌ 永远用 totalBidding → 收藏 Tab 受 stat 过滤污染
document.getElementById('cntBid').textContent = totalBidding;
```

**修复**: 三元判定 `activeStatFilter && !starOnly`：
```javascript
function updateApiStats() {
    const showBid = (activeStatFilter && !starOnly) ? totalBidding : realBidding;
    const showWin = (activeStatFilter && !starOnly) ? totalWinning : realWinning;
    // ...
}
```

| 场景 | `activeStatFilter` | `starOnly` | 判定 | 结果 |
|:--|:--|:--|:--|:--|
| 初始加载 | null | false | → realBidding | 94/13 |
| 高相关卡片 | 'high' | false | → totalBidding | 21/5 |
| 收藏 Tab | 'high' (残留) | true | → realBidding | 94/13 |
| 今日新增 | 'today' | false | → totalBidding | 按日期 |

**教训**: Badge 显示逻辑不是二态（过滤/真实），而是三态——需同时考虑 `activeStatFilter` 和 `starOnly` 的组合。

### 陷阱 10: renderTable 翻页信息用错数据源 (V1.40)

**案例**: `renderTable(data, total)` 的第 2 个参数 `total` 来自 `apiFilter()` 中的 `totalBidding`（API 未过滤总数 94）。但 Star 过滤后 `data` 只剩 1 条，翻页栏却显示「共94条」和 5 页按钮：

```javascript
// ❌ 翻页永远用 API total — star filter 后仍显示 94 条
const totalPages = Math.ceil(total / ps);
const pgInfoText = `${pg}/${totalPages} 共${total}条`;
```

- 正常招标 Tab：`total`=94, `data.length`=20 (API 分页) → 用 `total` 正确
- 收藏 Tab (starOnly=true)：`total`=94, `data.length`=1 → 应用 `data.length`
- `data.length` 不能全局替换 `total`：正常 Tab 的 API 分页每页只有 20 条，`data.length`=20 而非 94

**修复**: 按 `starOnly` 分叉：
```javascript
const actualCount = starOnly ? data.length : total;
const totalPages = Math.ceil(actualCount / ps) || 1;
const pgInfoText = `${pg}/${totalPages} 共${actualCount}条`;
```

**教训**: `renderTable` 的 `total` 参数语义是「API 总条数」，仅对 API 分页路径有意义。Star 过滤是客户端操作，翻页必须反映过滤后的实际数量。

### 陷阱 11: 空数据时翻页按钮未清空 (V1.40)

**案例**: `renderTable` 空数据分支只设了 `pgInfo='0/0'`，但**没有清空 `pgNums`**（翻页按钮容器）。上一次渲染的 `« ‹ 1 2 3 4 5 › »` 按钮残留在页面上。

```javascript
if (data.length === 0) {
    tbody.innerHTML = `<tr class="empty-msg">...</tr>`;
    pgInfo.textContent = '0/0';     // ✅ 更新了
    // ⛔ pgNums.innerHTML 没清空 → 残留旧按钮！
    return;
}
```

- 正常 Tab → 收藏 Tab（0条）→ 翻页按钮残留「« ‹ 1 2 3 4 5 › »
- 正常 Tab → 「今日新增」（0条）→ 同上

**修复**: 空数据分支同时清空 `pgNums` 和 `pgNumsW`：

```javascript
if (data.length === 0) {
    ...
    pgInfo.textContent = '0/0';
    const pgNums = document.getElementById('pgNums');
    if (pgNums) pgNums.innerHTML = '';
    const pgNumsW = document.getElementById('pgNumsW');
    if (pgNumsW) pgNumsW.innerHTML = '';
    return;
}
```

**教训**: 空数据状态需要清空的内容不仅是文本信息，还包括交互控件（按钮组）。`pgNums` 和 `pgInfo` 是独立的 DOM 元素，必须分别处理。

### 陷阱 12: sw('star') 未清除 activeStatFilter — stat 过滤泄漏入收藏视图 (V1.40)

**案例**: 用户先点「今日新增」→ `activeStatFilter='today'`，再点「收藏」Tab → `sw('star')` 不清除 `activeStatFilter` → `apiFilter()` 快照到 `_activeStatFilter='today'` → 拿着 `date_from=today` 查 API → 0 条 → 收藏永远空。退出收藏切回招标，`activeStatFilter` 仍为 'today' → 招标也只显示今日 0 条。

```javascript
function sw(t) {
    // ❌ 未清除 activeStatFilter
    if (t === "star") { starOnly = true; tab = "bid"; }
    else { starOnly = false; }
    // ...
}
```

**修复**：`sw('star')` 入口主动清除：
```javascript
if (t === "star") { 
    starOnly = true; tab = "bid";
    // Stat filters don't apply to starred view — deactivate
    activeStatFilter = null;
    renderStatBanner();
    document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
}
```

**教训**: 每个 Tab 对 stat 过滤的语义不同——招标/中标 Tab stat 过滤有意义，收藏 Tab 不应受 stat 过滤影响。切换入口时必须显式清除不兼容的全局状态。

---

## 自检清单 (V1.40 扩充)

每次在 `app.js` 中改动共享函数时：

1. [ ] 新增的全局变量引用 — 是否在两路径中都 defined？
2. [ ] 修改了 `sw()` — 守卫条件是否考虑了 star 过滤后的空状态？
3. [ ] 修改了 `renderTable()` — 所有调用的函数是否在两路径中都可访问？
4. [ ] 新增/改名了全局函数 — 是否 `grep` 确认所有调用点一致？
5. [ ] `apiFilter()` 的 catch 块 — 是否设置了 `useApi=false` 导致锁死？
6. [ ] `starOnly` 客户端过滤后 — 是否修改了 `allB/allW` 导致全局状态污染？
7. [ ] **新增**: 过滤操作是否覆盖了 `totalBidding`/`totalWinning`？Badge 应用 `realBidding`/`realWinning` 锚定值
8. [ ] **新增**: 新增 `activeStatFilter` 类型时 — `apiFilter()` 是否添加了对应的 API 参数映射？
9. [ ] **新增**: 改完 `app.js` 后 — `index.html` 中的 `app.js?v=N` 版本号是否已 bump？
10. [ ] **新增**: 异步函数中读取可变全局（`starOnly`/`tab`/`activeStatFilter`）— 是否在第一个 `await` 前快照为 `const`？
11. [ ] **新增**: `updateApiStats()` Badge 逻辑 — 是否正确处理 `activeStatFilter && !starOnly` 三态判定？
12. [ ] **新增**: `renderTable` 翻页计算 — `starOnly` 时是否用了 `data.length` 而非 `total`？
13. [ ] **新增**: 空数据分支 — 是否同时清空了 `pgNums`（翻页按钮）而不只是 `pgInfo`？
14. [ ] **新增**: `sw('star')` — 是否清除了 `activeStatFilter` 并去掉了 stat 卡片高亮？收藏视图不受 stat 过滤影响。

---

## 调试技巧

```javascript
// 在浏览器 Console 中快速诊断
// 1. 检查当前路径
console.log('useApi:', useApi, 'starOnly:', starOnly);

// 2. 手动触发 API 路径
useApi = true; apiFilter();

// 3. 检查是否有 stale 错误
// 打开 DevTools Console，查看是否有 ReferenceError
```
