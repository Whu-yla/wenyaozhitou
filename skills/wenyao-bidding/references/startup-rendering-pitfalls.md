# 启动态渲染陷阱

## 假数据闪烁（V1.15 修复）

**症状**：统计卡片显示 120 → 闪跳为 57。用户质问 "这么多BUG你都不修复的吗？"

**根因**：`report_generator.py` 模板用硬编码默认值 `lc.get('total_processed', 120)`。crawl_log 为空时灌假数字 120/7。

**修复**：
1. 模板默认值改为 0（诚实值）
2. CSS loading 态：`.stat-card.loading` opacity:0.3 → 数据就绪后移除 class → 平滑过渡

```css
.stat-card .stat-value{transition:opacity .4s ease}
.stat-card.loading .stat-value{opacity:.3}
```

```javascript
async function init() {
    document.querySelectorAll('.stat-card').forEach(c => c.classList.add('loading'));
    // ... fetch data ...
    document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('loading'));
}
```

## 日期筛选跨会话残留（V1.15 修复）

**症状**：第二次打开页面只显示 11 条（非全量 57 条）。

**根因**：`saveFilters()` 把 `dateFrom`/`dateTo` 存进 localStorage。上一个会话点过"今日新增"卡片设置了当天日期，跨会话恢复。

**修复**：`saveFilters/restoreFilters` 不再保存/恢复日期字段。日期是临时上下文，24小时后无意义。

```javascript
// ❌ 错误
function saveFilters() {
    const f = { dateFrom: ..., dateTo: ..., tab, sf, sd };
}

// ✅ 正确
function saveFilters() {
    const f = { search, fScore, fCat, fProv, tab, sf, sd };
}
```

## 统计数据 vs 筛选数据 字段错位（V1.16 修复）

**症状**：今日新增卡片显示11，点击后显示的数据与统计数不对应。

**根因**：统计用 `fetch_date` 计数，点击用 `publish_date` 筛选——两个完全不同的字段。

**修复**：引入 `todayOnly` 模式，用 `is_new`（基于 fetch_date 计算）统一统计口径和筛选口径。

详见 `references/stat-card-click-consistency.md`

## 数据就绪守卫（V1.16 修复）

**症状**：用户点击累计中标卡片看到空表。

**根因**：页面加载时 `init()` 未完成，`allB`/`allW` 为空数组。点击卡片触发 `sw('win')`，渲染空表。

**修复**：`sw()` 开头加数据就绪检查：

```javascript
function sw(t) {
    if (!allB.length && !allW.length) {
        toast('数据加载中，请稍候...', 'info');
        return;
    }
    // ... 正常切换逻辑
}
```

## 模板默认值铁律

| ❌ 禁止 | ✅ 允许 |
|:--|:--|
| 硬编码看起来像真实数据的假数字（120、7 等） | 0、\"—\"、空字符串 |
| 依赖 crawl_log 兜底的假站点数 | crawl_log 为空时不展示站点信息 |
