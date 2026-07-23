# Apple 移动端卡片设计 V1.30-V1.32

## 核心原则

参考 Linear / Stripe / Vercel / Apple Settings 的卡片设计：
- **去色灰阶**：无彩色按钮、无彩色统计值，纯灰阶 (#1d1d1f / #8e8e93 / #f5f5f7)
- **留白呼吸**：卡片 padding 18px 16px，gap 12px
- **层次轻影**：`box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 0 0 .5px rgba(0,0,0,.04)` (hairline + 微阴影)
- **交互暗示**：`›` chevron 而非彩色按钮，卡片本身可点
- **克制裁切**：标题 2 行截断，元数据底部小字

## CSS Grid 卡片布局 (V1.30)

```css
tr.data-row{
  display:grid;
  grid-template-columns:1fr auto auto auto;
  gap:3px 10px;
}
```

**4 行布局：**
| 行 | 列 | 内容 |
|:--|:--|:--|
| 1 | 1/-1 (span all) | 标题 (16px bold, 2-line clamp) |
| 2 | 1 / 2/span 3 | 客户 tag / 预算金额 |
| 3 | 1/-1 | 招标单位 |
| 4 | 1 / 2 / 3 / 4 | 地域 · 日期 · 分数 · › |

**禁止** `td{display:grid}`（每个 td 自己成 grid 导致布局混乱）。

## 自明字段隐藏 label (V1.30)

地域、日期、相关度三个字段不显示 `::before` label，用 `·` 分隔符连成一行：
```css
td[data-label="地域"]::before,
td[data-label="日期"]::before,
td[data-label="相关度"]::before{display:none}
td[data-label="日期"]::before{content:'·';display:inline}
td[data-label="相关度"]::before{content:'·';display:inline}
```

## 苹果调色板 (V1.30)

```css
body.light{--bg:#f5f5f7;--text:#1d1d1f;--muted:#86868b;--dim:#8e8e93}
```
- 卡片背景: `#fff`
- 卡片阴影: `0 1px 3px rgba(0,0,0,.06)` + hairline
- 标签色: `#8e8e93` (Apple secondary label)
- 毛玻璃头部: `background:rgba(255,255,255,.72); backdrop-filter:blur(20px)`

## 输入框可见性 (V1.32 致命教训)

**❌ 错误**: `border:1px solid rgba(0,0,0,.08)` — 8% 黑在 `#f5f5f7` 背景上肉眼不可见
**❌ 错误**: `background:#f2f2f7; border:none` — 灰色填充无边框，与页面底色太接近
**✅ 正确**: `background:#fff; border:1px solid #d1d1d6` — 纯白底 + Apple 标准实色灰边框

```css
/* 明亮模式 */
.filter-row select,
.filter-row input[type=number],
.filter-row input[type=date],
.search-box input{
  background:#fff;
  border:1px solid #d1d1d6;
}
/* 暗色模式 */
body.dark .filter-row select,
body.dark .filter-row input{ border-color:#545458; }
```

**验证**: 手机端明亮模式下每个 input/select 的边框轮廓清晰可见。

## CSS 层叠顺序陷阱 (V1.32 致命教训)

**症状**: 在 `@media(max-width:768px)` 中定义了输入框边框，但明亮模式下框不可见。

**根因**: `body.light .search-box input{border-color:transparent}` 写在 `@media` 块**之后**，优先级高于移动端规则，把边框抹成透明。

**✅ 修复**: light theme 输入规则改为 `border-color:#d1d1d6`，不再用 `transparent`。

**铁律**: `@media` 块后方的全局样式（如 `body.light` 规则）会覆盖 `@media` 内的样式。排查此类问题：
```bash
grep -n 'border.*transparent\|border.*none' index.html | grep -A2 -B2 'light'
```

## Kebab 菜单 ⋯ (V1.32)

替代长按分享（用户反馈「反人类」）和丑 ↗ 图标（用户反馈「可读性太差」）。

**位置**: 卡片右上角 `top:12px; right:12px`（28px 圆，z-index:3）

**NEW badge 冲突解决**: NEW badge 移到左上角 `left:14px`，kebab 独占右上角，互不遮挡。

**菜单结构**:
```html
<div class="kebab-overlay"> <!-- 全屏透明，点击关闭 -->
<div class="kebab-menu">    <!-- position:fixed，getBoundingClientRect 定位 -->
  <button>📤 分享</button>
  <button>🔗 复制链接</button>
  <button>📋 复制标题</button>
  <button>⭐ 收藏</button>   <!-- 动态切换 ☆/⭐ 取消收藏/收藏 -->
</div>
```

**CSS**:
```css
.kebab-menu{
  position:fixed;
  background:#fff;
  border-radius:12px;
  box-shadow:0 4px 24px rgba(0,0,0,.15);
  z-index:9999;
  min-width:140px;
  animation:menuIn .15s ease;
}
.kebab-menu button{
  width:100%;padding:12px 16px;
  border-bottom:1px solid rgba(0,0,0,.06);
}
.kebab-menu button:last-child{border-bottom:none}
```

## 筛选栏对齐 (V1.32)

所有输入框统一高度，完美居中对齐：
```css
.filter-row{align-items:center;gap:8px}
.filter-row select{height:40px;box-sizing:border-box}
.filter-row input[type=number],
.filter-row input[type=date]{height:40px;box-sizing:border-box}
.filter-row .btn{height:40px;line-height:40px;box-sizing:border-box}
.search-box input{height:42px;box-sizing:border-box}
```

## 搜索图标防重叠 (V1.32)

🔍 图标绝对定位 `left:10px; top:50%; transform:translateY(-50%)`，输入框 `padding-left:34px`。
缺 `padding-left` → 图标和 placeholder 文字重叠。

## 页码居中 (V1.32)

```css
.pg-bar{justify-content:center}
.pg-btn{min-width:36px;height:36px;line-height:36px;padding:0;text-align:center}
```

## 标题字体继承 (V1.31)

`td.title-cell a{font-size:inherit;line-height:inherit}` — **禁止**单独指定字号。
`-webkit-box` 布局下纯文本节点和 `<a>` 如字号不同，渲染基线偏差，视觉上大小不一。

## 分数语义化 (V1.31)

显示 `85分` 而非 `85`。模板: `${sc.toFixed(0)}分`。

## 卡片点击双态 (V1.31)

```html
onclick="if(window.innerWidth<=768){window.open(url,'_blank')}else{toggleDetail(id)}"
```
手机端跳转源页面，桌面端展开详情。

## 已读/未读追踪 (V1.31)

```js
function markRead(id) { localStorage.setItem('bidding_read', JSON.stringify([...reads, id])); }
```
CSS: `tr.data-row.read{opacity:.65}` — 已读卡片半透明。
