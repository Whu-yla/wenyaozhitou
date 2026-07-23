# 统计卡片点击数据一致性铁律

## 致命陷阱：统计口径 ≠ 筛选口径

**V1.16 教训**：四张统计卡片（累计招标/今日新增/高相关/累计中标）的**数字**和**点击筛选条件**使用了不同的数据字段，导致点击结果显示的数据与卡片数字完全对不上。

| 卡片 | 统计口径 | 旧筛选口径（❌错误） | 修复后 |
|:--|:--|:--|:--|
| 今日新增 11 | `COUNT WHERE date(fetch_date)=today` | `filter publish_date=today` | `filter is_new=1`（同为 fetch_date） |
| 高相关 11 | `COUNT WHERE date(fetch_date)=today AND score>=7` | `filter score>=7`（全量，非今日） | `todayOnly=true + fScore=7` |

**根因**：`fetch_date`（爬取日期）≠ `publish_date`（发布日期）。有 2 条今天爬的但发布日期不是今天。

## todayOnly 模式规范

```javascript
let todayOnly = false;

// statClick 设置
function statClick(type) {
    todayOnly = false;  // 先清
    document.getElementById("dateFrom").value = "";
    document.getElementById("dateTo").value = "";
    document.getElementById("fScore").value = "";
    
    if (type === "total") { resetF(); return; }
    if (type === "today") { sw("bid"); todayOnly = true; doFilter(); return; }
    if (type === "high") { sw("bid"); todayOnly = true; document.getElementById("fScore").value = "7"; doFilter(); return; }
    if (type === "win") { sw("win"); return; }
}

// getFilt 中应用
function getFilt() {
    let d = tab === "bid" ? [...allB] : [...allW];
    if (todayOnly) d = d.filter(i => i.is_new === 1 || i.is_new === "1");
    // ... 其他筛选
}

// 手动改筛选 → 退出 todayOnly
// 日期筛选 onchange="todayOnly=false;doFilter()"
// fScore onchange="todayOnly=false;doFilter()"

// resetF 中清理
function resetF() {
    // ...
    todayOnly = false;
}
```

## ⛔ 执行顺序 BUG

```javascript
// ❌ 错误 — todayOnly 立刻被 sw() 清掉
if (type === "today") { todayOnly = true; sw("bid"); return; }

// ✅ 正确 — 先 sw() 再设 todayOnly 再 doFilter()
if (type === "today") { sw("bid"); todayOnly = true; doFilter(); return; }
```

原因：`sw()` 内部曾经有 `todayOnly = false`（已移除），但任何可能清掉 todayOnly 的操作都必须在 todayOnly 赋值**之前**完成。

## 数据就绪守卫（时序竞争）

```javascript
function sw(t) {
    if (!allB.length && !allW.length) { toast('数据加载中，请稍候...', 'info'); return; }
    // ...
}
```

页面刚加载时 `init()` 未完成，`allB`/`allW` 为空。此时点卡片 → 空表。守卫阻止提前操作并提示用户。

## is_new 标志精准化

```python
# ❌ 错误 — DB DEFAULT 1 从不重置，全部 57 条都假 NEW
result['is_new'] = int(item.get('is_new', 0) or 0)

# ✅ 正确 — 用 fetch_date 实时判断
fd = str(item.get('fetch_date') or '')
result['is_new'] = 1 if fd.startswith(today) else 0
```

同时在 `KEEP_STR` 中加 `'fetch_date'`，确保前端 data.json 包含该字段。
