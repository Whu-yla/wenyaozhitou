# 统计卡片 + NEW标签 细节打磨

> 源自 V1.16-V1.17，用户连续两次质问细节问题。

## 统计卡片可发现性

**问题**：4 张统计卡片（累计招标/今日新增/高相关/累计中标）都有 onclick，但用户完全不知道。

**根因**：没有视觉暗示。浏览器默认对 `div` 元素不显示 `cursor:pointer`，无 hover 效果。

**修复**：
```css
.stat-card[onclick] {
  cursor: pointer;
  position: relative;
  transition: all .2s ease;
}
.stat-card[onclick]:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 12px rgba(59,130,246,.15);
  transform: translateY(-1px);
}
.stat-card[onclick]:active {
  transform: translateY(0);
  box-shadow: none;
}
.stat-card[onclick]::after {
  content: '›';
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
  color: var(--dim);
  opacity: .4;
  transition: opacity .2s;
}
.stat-card[onclick]:hover::after {
  opacity: 1;
  color: var(--accent);
}
```

**statClick 行为规范（V1.17-V1.30 — ⛔ 已于 V1.31 弃用）**：
- `total` → `resetF()` 重置全部筛选
- `today` → `dateFrom=dateTo=today` + `doFilter()`
- `high` → `fScore=7` + `doFilter()`
- `win` → `sw('win')`

> ⛔ **V1.31 已重构**：以上行为会污染搜索框，已替换为独立 banner 模式。
> 详见 `references/stat-card-independent-view-v31.md`。

## NEW 图标

**问题**：红点（5px 圆点 `.new-dot`）太不起眼。

**用户反馈**：「不要用红点，太不显目了，换成 new 的标签」

**修复**：`.new-badge` — 红底白字 `NEW`，9px 加粗，圆角 3px。

## is_new 腐败

**问题**：`is_new INTEGER DEFAULT 1` 导致所有旧数据永葆 NEW 状态。

**修复**：不读 DB 的 `is_new`，在 `report_generator.py` 的 `trim()` 中根据 `fetch_date` 实时计算。
