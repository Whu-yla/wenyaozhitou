# 筛选栏单行布局 v27 (2026-06-26)

## 触发背景

用户对两行筛选栏评价「不伦不类」，要求所有条件放在一条水平线上，对标专业投标平台。

## 最终布局

```
🔍 [搜索框 flex:1.5] [客户▼] [地域▼] [相关度≥ 80px] [起始日期 115px] 至 [结束日期 115px] [预算≥万 85px] │ 每页 [20|50|100] [导出] [重置]
```

全部在一行，`|` 竖线分隔筛选区和操作区。

## CSS 要点

```css
.filter-row {
  display: flex;
  gap: 6px;              /* 紧凑间距 */
  align-items: center;
  flex-wrap: nowrap;     /* 不换行 */
  overflow-x: auto;      /* 窄屏可滚 */
}
.filter-row input[type="number"],
.filter-row input[type="date"] {
  padding: 7px 8px;
  flex-shrink: 0;        /* 不被压缩 */
  /* 统一输入框样式，不需要每个元素内联 style */
}
```

## 分页选择器位置

**V1.26 之前**：放在底部 `.pg-bar` 分页栏（不合理——用户看不到）

**V1.27 之后**：放在筛选栏右侧，导出按钮左边，用 `|` 竖线与筛选区分隔。

HTML 占位符：`<div class="pg-btns" id="psSelector"></div>`（在 filter-row 内）

JS 渲染：`renderPsSelector("psSelector")` 在 `doFilter()` 中调用（招标和中标分支都调用同一个 id）

## 检验清单

```bash
# 确认筛选栏是单行
curl -s URL | grep -c "filter-row"  # 应该只有 CSS + 1 个 HTML div

# 确认分页选择器在筛选栏而非底部
curl -s URL | grep "psSelector" | grep -c "filter-bar"  # 必须 = 1

# 确认 table-layout 是 fixed
curl -s URL | grep "table-layout:fixed"
```
