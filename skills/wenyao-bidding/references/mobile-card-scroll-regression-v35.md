# V1.35 移动端卡片+滚动回归修复

**日期**：2026-06-26

## 问题

用户反馈移动端原有功能消失：
1. 卡片风格（Grid 布局）不见了，退回普通表格
2. 搜索栏不能右滑，筛选选项不可达

## 根因

移动端 CSS 严重缺失，`polish_report.py` 的 `ENHANCE_CSS` 注入仅覆盖了少量样式（密度模式、element hiding），**完全缺少**：

1. **卡片 Grid 布局**：`tr.data-row{display:grid}` — 从未注入
2. **横向滚动**：`.filter-scroll-wrapper{overflow:hidden!important}` — 反而是锁死的
3. **H5 胶囊风格**：搜索44px圆角、筛选34px圆角 — 从未注入

## 修复的 CSS 块

### 卡片 Grid 布局
```css
@media(max-width:768px){
  thead{display:none}
  tr.data-row{display:grid;grid-template-columns:1fr auto auto auto;
    padding:16px 14px;margin-bottom:10px;border-radius:14px}
  td.title-cell{grid-column:1/-1;-webkit-line-clamp:2}
  tr.empty-msg{display:flex!important;...;border-radius:14px!important}
}
```

### 横向滚动恢复
```css
.filter-scroll-wrapper{overflow-x:auto!important;-webkit-overflow-scrolling:touch;
  scrollbar-width:none}
.filter-row{flex-wrap:nowrap;gap:8px}
```

### H5 胶囊风格
```css
.search-box input{height:44px;border-radius:20px;font-size:16px}
.search-btn{height:44px;border-radius:0 20px 20px 0;padding:0 20px}
.filter-row select,input{height:34px;border-radius:17px;...}
body.light .filter-row select,input{background:#e8e8ed;border:none}
```

## 关键教训

1. **`overflow:hidden` 注释写「scrollable」但实际锁死** — 代码注释迷惑性极强，必须验证真实行为
2. **移动端 CSS 不能只靠 polish 注入** — `ENHANCE_CSS` 太精简，大量 V1.30+ 移动端样式从未被持久化
3. **`@media(min-width:769px)` 桌面规则不能替代移动端规则** — 两者是互补关系，各写各的
4. **验证方式**：`curl | grep` 检查关键 CSS 属性是否存在（`display:grid`、`overflow-x:auto`、`border-radius:20px`）

## V1.36 进阶模式：搜索框胶囊 + 筛选扁平化 + 渐变淡出

**日期**：2026-06-26（同一天第二波修复）

### 问题
生产环境 fork 到测试环境后，手机端三处 CSS 仍不正确：
1. 🔍 放大镜在搜索框外 — `.search-box` 没有 `display:flex`
2. 搜索按钮在框外独立一行 — 按钮不是 `position:absolute` 嵌入胶囊
3. 两个 `.filter-row` 各自换行 — 筛选胶囊东倒西歪

### 搜索框胶囊（手机端）
```css
.search-box{display:flex;align-items:center;width:100%;position:relative}
.search-box input{flex:1;height:44px;border-radius:22px;padding:0 72px 0 40px;
  font-size:16px;border:1px solid var(--border)}
/* 🔍 图标浮在 input 左侧 */
.search-box .search-icon{position:absolute;left:14px;top:50%;
  transform:translateY(-50%);font-size:16px;z-index:1;pointer-events:none}
/* 搜索按钮嵌入胶囊右侧 */
.search-btn{position:absolute;right:2px;top:2px;height:40px;
  border-radius:0 20px 20px 0;padding:0 18px;font-size:14px;
  border:none;background:var(--accent);color:#fff;cursor:pointer}
```
⚠️ **关键**：按钮用 `position:absolute; right:2px; top:2px` 嵌入 input 的胶囊内，形成 2px 间隙的内嵌效果。不能只用 flex 并排（会导致按钮在胶囊外）。

### 筛选行扁平化（手机端）
```css
/* wrapper 是 flex 容器，单行不换行 */
.filter-scroll-wrapper{display:flex;flex-wrap:nowrap;overflow-x:auto;
  -webkit-overflow-scrolling:touch;scrollbar-width:none;gap:8px;
  position:relative;
  /* 右侧渐变淡出暗示可滚动 */
  -webkit-mask-image:linear-gradient(to right,black 85%,transparent 100%);
  mask-image:linear-gradient(to right,black 85%,transparent 100%)}
/* 多个 .filter-row 用 display:contents 摊平到 wrapper 的 flex 流 */
.filter-scroll-wrapper .filter-row{display:contents}
.filter-scroll-wrapper .filter-row > *{flex-shrink:0}
/* 隐藏内部的 spacer span */
.filter-row span[style*="flex:1"]{display:none!important}
```
⚠️ **关键**：`display:contents` 让两个 `.filter-row` 的所有子元素变成 wrapper 的直接 flex 子项，全部在同一水平线上滚动。

### JS 滚动动画目标修正
```javascript
// ❌ 旧：querySelector('.filter-row') — 只取第一个，且 display:contents 不可滚动
// ✅ 新：querySelector('.filter-scroll-wrapper') — 实际的可滚动容器
const filterRow = document.querySelector('.filter-scroll-wrapper');
```
`display:contents` 的元素自身不可滚动（它从布局树中移除），必须对 wrapper 操作。

### 手机端隐藏桌面专属控件
```css
@media(max-width:768px){
  /* 隐藏分隔符、每页选择器、导出、重置按钮 */
  .filter-bar > span:not(.search-icon),
  .filter-bar > .pg-btns,
  .filter-bar > .btn{display:none!important}
}
```
⚠️ 不再保留导出按钮 — 手机端筛选栏空间宝贵，仅保留 search-row + filter-scroll-wrapper。
