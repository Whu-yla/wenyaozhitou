# 手机端卡片布局 (V1.30 — CSS Grid)

## 布局演进

| 版本 | 方案 | 问题 |
|:--|:--|:--|
| V1.28 | `td{display:flex}` + `td::before{content:attr(data-label)}` 逐行排列 | 标签宽度不一致导致对不齐 |
| V1.29 | `td{display:grid; grid-template-columns:56px 1fr}` 每 td 独立 grid | 每个 td 都是自己的 grid，label/value 在各自单元格但不跨 td 对齐 |
| **V1.30** | **tr 级 CSS Grid：`display:grid; grid-template-columns:1fr auto auto auto`** | 所有 td 在同一个 grid 上下文中精确对齐 |

## 当前布局（V1.30）

```
┌──────────────────────────────────────┐
│ 标题文字（最多2行，超长…）           │  ← Row 1: td.title-cell (col:1/-1)
│                                      │
│ 国网/南网         预算 55.79万元     │  ← Row 2: 客户(col1) + 预算(col2-4)
│ 招标单位 南方电网科学研究院有限…     │  ← Row 3: td[data-label="招标单位"] (col:1/-1)
│                                      │
│ 广东  ·  2026-06-25  ·  85分   ›    │  ← Row 4: 地域(col1) | 日期(col2) | 分数(col3) | ›(col4)
└──────────────────────────────────────┘
```

## 关键 CSS

```css
tr.data-row{
  display:grid;
  grid-template-columns:1fr auto auto auto;
  gap:3px 10px;
}

/* 标题跨所有列 */
td.title-cell{grid-column:1/-1; grid-row:1}

/* 客户标签无 label，预算跨列加粗 */
td[data-label="客户"]{grid-column:1; grid-row:2}
td[data-label="客户"]::before{display:none}
td[data-label="预算"]{grid-column:2/span 3; grid-row:2; font-weight:600}

/* 招标单位跨列 */
td[data-label="招标单位"]{grid-column:1/-1; grid-row:3}

/* 底部元数据行 */
td[data-label="地域"]{grid-column:1; grid-row:4}
td[data-label="日期"]{grid-column:2; grid-row:4}
td[data-label="相关度"]{grid-column:3; grid-row:4}
td[data-label="地域"]::before,
td[data-label="日期"]::before,
td[data-label="相关度"]::before{display:none}

/* · 分隔符 */
td[data-label="日期"]::before{content:'·';display:inline;margin:0 6px}
td[data-label="相关度"]::before{content:'·';display:inline;margin:0 6px}

/* › 交互提示 */
tr.data-row::after{grid-column:4; grid-row:4; content:'›'; font-size:18px; color:#c7c7cc}
```

## 隐藏列

手机端 `display:none` 的列：`td:first-child`（checkbox）、`td[data-label="序号"]`、`.hide-mobile`（来源）、`td[data-label="操作"]`、`.link-btn`
