# 苹果风格手机卡片设计 (V1.30+)

## 设计来源

学习 Linear、Stripe、Vercel、iOS Settings 的卡片设计规律后落地。

## 核心原则

1. **去色** — 不用彩色按钮，不用 ac accent 色区分统计值，灰阶为主
2. **留白** — 卡片间距 12px，内边距 18px 16px，字段间距 3-4px
3. **克制** — 砍掉冗余列（序号/来源/操作），标题最多 2 行
4. **暗示** — 卡片可点用 `›` 而非按钮，底部元数据无 label（自明字段）

## CSS Grid 4列卡片布局

```css
/* tr 级 Grid，非 td 级 */
tr.data-row{
  display:grid;
  grid-template-columns:1fr auto auto auto;
  gap:3px 10px;
}

/* Row 1: Title — spans all 4 columns */
td.title-cell{grid-column:1/-1; grid-row:1}

/* Row 2: Customer badge (col1, no label) + Budget (col2-4, bold) */
td[data-label="客户"]{grid-column:1; grid-row:2}
td[data-label="预算"]{grid-column:2/span 3; grid-row:2; font-weight:600}

/* Row 3: 招标单位 — spans all */
td[data-label="招标单位"]{grid-column:1/-1; grid-row:3}

/* Row 4: 地域 | 日期 | 相关度 | › — 底部元数据行 */
td[data-label="地域"]{grid-column:1; grid-row:4}
td[data-label="日期"]{grid-column:2; grid-row:4}
td[data-label="相关度"]{grid-column:3; grid-row:4}
tr.data-row::after{grid-column:4; grid-row:4; content:'›'}
```

## 视觉规范

| 元素 | 样式 |
|:--|:--|
| 页面背景 | `#f5f5f7`（苹果系统灰） |
| 卡片 | `#fff` + `border-radius:14px` + `box-shadow:0 1px 3px rgba(0,0,0,.06)` + hairline |
| 标题 | `font-size:17px; font-weight:600; line-height:1.4` |
| 标题截断 | `-webkit-line-clamp:2; display:-webkit-box; overflow:hidden` |
| 标签色 | `#8e8e93`（苹果 secondary label） |
| 正文色 | `#1d1d1f` |
| 元数据行 | `font-size:12px; color:#8e8e93`，无 label，`·` 分隔 |
| 头部 | `background:rgba(255,255,255,.72); backdrop-filter:blur(20px)` 毛玻璃 |
| 输入框 | `background:#f2f2f7; border:none; border-radius:10px; font-size:14-16px` |
| 统计卡片 | `font-size:28px; font-weight:700; color:#1d1d1f` 统一黑（无彩色） |
| `›` 交互暗示 | `font-size:18px; color:#c7c7cc; font-weight:300` |

## 冗余字段砍除

手机端隐藏（`display:none`）：序号、来源、操作（查看链接）。标题中的链接 `<a>` 改为 `color:inherit;text-decoration:none`，卡片整体 onclick 跳转到源 URL。

## 卡片点击行为

手机端（`window.innerWidth <= 768`）：点卡片 → `window.open(url, '_blank')` 跳转源页面。
桌面端：点卡片 → `toggleDetail(id)` 展开详情行。

```javascript
onclick="if(window.innerWidth<=768){window.open('${link}','_blank')}else{toggleDetail(${i.id})}"
```

## 相关度可读性

分数显示须加 `分` 后缀：`85分` 而非 `85`。用户无法从裸数字判断含义。

## 标题字体一致性

`td.title-cell a` 必须用 `font-size:inherit; line-height:inherit`，**禁止**单独指定字号。否则 `-webkit-box` 布局下纯文本节点（🆕☆）和 `<a>` 标签渲染基线不同，视觉上大小不一。

## 暗色模式

```css
body.dark tr.data-row{background:#1c1c1e}
body.dark td{color:#f5f5f7}
body.dark td::before{color:#8e8e93}
body.dark .stat-card{background:#1c1c1e}
body.dark input,body.dark select{background:#2c2c2e; color:#f5f5f7}
```

## 验证清单

- [ ] 所有卡片标题 2 行截断，无溢出
- [ ] 无蓝色按钮或彩色统计值
- [ ] `›` 出现在每张卡片右下角
- [ ] 底部元数据行（地域·日期·分数）无 label
- [ ] 分数带 `分` 后缀
- [ ] 点击卡片打开原始招标页面
- [ ] 标题 `<a>` 标签和前后文字同一字
