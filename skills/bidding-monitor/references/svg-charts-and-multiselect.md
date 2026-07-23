# SVG 趋势图表 + 多选筛选 实现参考 (v13)

## SVG 趋势图引擎 (app.js)

### 独立切换模式 — 用 Map 而非 {}
```javascript
// ❌ 错误：普通 {} 对象可能被 prototype 链污染
let chartModes = {};

// ✅ 正确：Map 完全隔离，get/set 明确
const chartModes = new Map();
function toggleChartMode(cardId) {
    const cur = chartModes.get(cardId) || "bar";
    chartModes.set(cardId, cur === "line" ? "bar" : "line");
    renderTrends(); // 全量重绘，但每张卡读自己的 mode
}
function getChartMode(cardId) {
    return chartModes.get(cardId) || "bar";
}
```

### ID 映射 — 显式数组避免 Object.keys 不确定性
```javascript
const CHART_IDS = { bidding: "trendBid", winning: "trendWin", high: "trendHigh" };

function renderTrends() {
    ["bidding", "winning", "high"].forEach(k => {
        const data = trends[k];
        const cardId = CHART_IDS[k];
        const el = document.getElementById(cardId);
        const mode = getChartMode(cardId); // 各自独立读取
        // ... 渲染逻辑
    });
}
```

### SVG 视图
- `viewBox="0 0 320 160"` + `style="width:100%;height:auto;max-height:200px"`
- 柱状图：`<rect rx>` 圆角 + `<animate>` 从 0 长起
- 曲线图：`<path>` 折线 + `<path>` 面积填充 (opacity 0.08) + Y轴网格 `<line>` + `<circle>` 数据点

---

## 多选标签筛选 (app.js, v13)

### 核心函数
```javascript
// 切换选中状态 + 自动取消「全部」+ 强制刷新视觉
function toggleFilter(selectId, value) {
    const sel = document.getElementById(selectId);
    const opt = [...sel.options].find(o => o.value === value);
    if (!opt) return;
    if (opt.selected) {
        opt.selected = false;
    } else {
        // 切换具体项时自动取消「全部」空选项
        const allOpt = [...sel.options].find(o => o.value === "");
        if (allOpt && allOpt.selected) allOpt.selected = false;
        opt.selected = true;
    }
    sel.dispatchEvent(new Event("change", { bubbles: true })); // 强制视觉刷新 + 触发 saveFilters
    doFilter();
}

// 获取选中值 — 过滤「全部」空字符串
function getSelectedValues(selectId) {
    const sel = document.getElementById(selectId);
    return [...sel.selectedOptions].map(o => o.value).filter(v => v !== "");
}

// 恢复多选
function restoreMultiSelect(selectId, values) {
    const sel = document.getElementById(selectId);
    [...sel.options].forEach(o => { o.selected = values.includes(o.value); });
}
```

### getFilt() 多选并集
```javascript
// ❌ 旧：单选等值
const cat = document.getElementById("fCat")?.value;
if (cat) d = d.filter(i => i.category === cat);

// ✅ 新：多选 includes (OR 并集)
const cats = getSelectedValues("fCat");
if (cats.length > 0) d = d.filter(i => cats.includes(i.category));
```

### HTML 多选属性 (polish_report.py 注入)
```html
<!-- ❌ 错误：size="1" 伪装下拉框 → 程序改 selected 后视觉不刷新 -->
<select id="fCat" multiple size="1">

<!-- ✅ 正确：原生列表盒，max-height 限制高度不撑破布局 -->
<select id="fCat" multiple style="height:auto;max-height:160px;overflow-y:auto">
```

### 简报标签点击
```javascript
// ❌ 旧：直接设 value 无切换
h += ' <span class="tag" onclick="fCat.value=\'' + c[0] + '\';doFilter()">...'

// ✅ 新：toggleFilter 切换+自动取消「全部」
h += ' <span class="tag" onclick="toggleFilter(\'fCat\',\'' + c[0] + '\')">...'
```

---

## 「其他」排序 + 初始化重建

### 关键：先清空再重建
```javascript
// ❌ 错误：仅 appendChild 追加 → 排在 Python 生成的旧选项之后，等于白排
[["fCat", cats], ["fProv", ps2]].forEach(([id, s]) => {
    const sel = document.getElementById(id);
    const sorted = [...s].sort(...);
    sorted.forEach(v => sel.appendChild(createOption(v))); // BUG: 追加在后面
});

// ✅ 正确：先 sel.innerHTML="" 完全清空，再加默认选项，再排序追加
[["fCat", cats], ["fProv", ps2]].forEach(([id, s]) => {
    const sel = document.getElementById(id);
    sel.innerHTML = ""; // 清空所有旧选项（包括 Python 生成的）
    // 加「全部」默认选项
    const allOpt = document.createElement("option");
    allOpt.value = ""; allOpt.textContent = id === "fCat" ? "全部客户" : "全部地域";
    sel.appendChild(allOpt);
    // 排序：其他垫底，其余拼音
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
```

---

## Polish 脚本注入点 (v13 修正)

| 注入 | 操作 |
|:--|:--|
| 主题 CSS | `html.replace("</style>", THEME_CSS + "\n</style>")` |
| 主题按钮 | 在 `</h1>` 后插入 `<button class="theme-btn">🌓</button>` |
| 多选属性 | `<select id="fCat"` → `<select id="fCat" multiple style="height:auto;max-height:160px;overflow-y:auto"` |
| 导出标签 | `导出Excel` → `导出CSV` |
| 趋势卡片 | 移除 `<h3>` 双标题，让 renderTrends 自行管理 |

⚠️ **绝对不要加 `size="1"`** — 这将导致程序修改 `option.selected` 后浏览器视觉不刷新，用户看到选中态没变化。
