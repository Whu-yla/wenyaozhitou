# 动态统计卡片 + 跨Tab徽标联动 (V1.34)

## 根因

用户反馈两个致命UX缺陷：
1. 「搜索浙江 → 卡片显示招标56，实际匹配5条」→ 统计卡片不联动筛选
2. 「招标Tab搜广东，中标Tab数字没变」→ Tab徽标不跨Tab联动
3. 「收藏显示2，实际搜索后只有1个」→ 收藏徽标不联动过滤
4. 「中标Tab搜东西，有问题」→ 搜索字段不覆盖 `province`/`region`/`category`

## 架构

### `updateStats(data)` — 每个 `doFilter()` 末尾调用

```js
function updateStats(data) {
    const hasFilter = !!(document.getElementById("search")?.value
        || document.getElementById("fCat")?.value
        || document.getElementById("fProv")?.value
        || parseFloat(document.getElementById("fScore")?.value || 0)
        || parseFloat(document.getElementById("fBudget")?.value || 0)
        || document.getElementById("dateFrom")?.value
        || document.getElementById("dateTo")?.value);

    const today = todayStr();
    const trendEls = [statTodayTrend, statHighTrend];

    if (hasFilter) {
        // ⛔ 跨Tab：同样的筛选应用到两个数据集
        const filtBid = getFiltFor(allB);
        const filtWin = getFiltFor(allW);

        statBidTotal.textContent = filtBid.length;
        statToday.textContent = filtBid.filter(i => isToday(i)).length;
        statHigh.textContent = filtBid.filter(i => score>=70).length;
        statWinTotal.textContent = filtWin.length;

        // 所有Tab徽标同步
        cntBid.textContent = filtBid.length;
        cntWin.textContent = filtWin.length;
        // 收藏: 过滤结果中取交集已收藏
        cntStar.textContent = [...filtBid, ...filtWin].filter(i => stars.has(i.id)).length;

        trendEls.forEach(el => el.style.opacity = "0");
    } else {
        // 恢复全局
        statBidTotal.textContent = allB.length;
        statToday.textContent = brief.today_total || 0;
        statHigh.textContent = allB.filter(i => score>=70).length;
        statWinTotal.textContent = allW.length;
        cntBid.textContent = allB.length;
        cntWin.textContent = allW.length;
        cntStar.textContent = getStars().length;
        trendEls.forEach(el => el.style.opacity = "");
    }
}
```

### `getFiltFor(arr)` — 将当前筛选应用到任意数据集

```js
function getFiltFor(arr) {
    let d = [...arr];
    const q = search.value.toLowerCase();
    if (q) d = d.filter(i =>
        title.includes(q) || owner.includes(q) || winner.includes(q) ||
        source.includes(q) || province.includes(q) || region.includes(q) ||
        category.includes(q)  // ⛔ 7字段全覆盖
    );
    if (sc) d = d.filter(i => (i.relevance_score||0) >= sc);
    if (cat) d = d.filter(i => i.category === cat);
    if (prov) d = d.filter(i => i.province === prov);
    if (df) d = d.filter(i => (i.publish_date||"") >= df);
    if (dt) d = d.filter(i => (i.publish_date||"") <= dt);
    return d;
}
```

## 搜索字段覆盖

| 修复前 | 修复后 |
|:--|:--|
| `title` + `procurement_owner` + `winner_company` + `source_site` (4字段) | + `province` + `region` + `category` (7字段) |

中标数据的「广东」存在 `province` 字段，旧搜索查不到 → 用户切中标Tab搜"广东"无结果。

## hasFilter 检测

以下任意一项非空 → 有筛选，触发动态统计：
- `search` value
- `fCat` value  
- `fProv` value
- `fScore` > 0
- `fBudget` > 0
- `dateFrom` / `dateTo`

## 趋势箭头

有筛选 → `opacity:0` 隐藏（全局趋势对过滤数据无意义）
无筛选 → 恢复显示

## 调用位置

```js
function doFilter() {
    let data = getFilt();
    // ... 排序、渲染 ...
    updateStats(data);  // ← 在所有渲染之后、saveFilters 之前
    saveFilters();
}
```

## 已知陷阱

| 陷阱 | 症状 | 修复 |
|:--|:--|:--|
| `cntBid`/`cntWin` 不联动 | 招标Tab搜完，中标徽标不变 | `getFiltFor(allW)` 独立计算 |
| `cntStar` 用 `getStars().length` | 收藏显示全局2，实际过滤后只有1 | 取 `filtBid + filtWin` 交集 stars |
| 搜索不覆盖 province | 中标Tab搜"广东"无结果 | 扩展至7字段 |
| `getFiltFor` 和 `getFilt` 不同步 | 中标Tab徽标与实际数据不一致 | 两函数内搜索逻辑必须相同 |
