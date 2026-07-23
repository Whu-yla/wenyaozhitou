# 移动端 CSS 溢出陷阱 (V1.29)

## 核心陷阱一览

### 1. CSS `calc()` 空格语法陷阱（无声失败）
```css
/* ❌ 语法错误 — 浏览器静默丢弃整条规则，不报错 */
width: calc(100vw-16px);

/* ✅ 运算符两侧必须有空格 */
width: calc(100vw - 16px);
```
CSS 规范要求 `calc()` 中 `+` `-` 运算符两侧必须有空格。`calc(100vw-16px)` 被解析为 token "100vw-16px" 而非减法运算。

### 2. JS 内联样式覆盖 CSS 媒体查询
```javascript
// ❌ JS 内联 style 优先级 > CSS 类/媒体查询
w.style.right = '20px';         // 手机端也被设成 20px → 溢出
w.style.bottom = '20px';

// ✅ 手机端清空内联，让 CSS 媒体查询接管
if (window.innerWidth <= 768) {
  w.style.bottom = ''; w.style.right = ''; w.style.left = ''; w.style.top = '';
} else {
  w.style.bottom = '20px'; w.style.right = '20px';
}
```
**铁律**：任何 `element.style.xxx = 'val'` 操作，如果该元素在手机端有不同定位，必须加 `window.innerWidth` 判断或清空内联样式。

### 3. 手机端触屏拖动冲突
```javascript
// ❌ mousedown/mousemove/mouseup 在触屏上坐标异常 → 面板震动
// ✅ 手机端彻底禁拖动
if (window.innerWidth <= 768 || 'ontouchstart' in window) return;
```
`ontouchstart` 检测比 `innerWidth` 更可靠（覆盖平板、混合设备）。

### 4. iOS 输入框自动放大
**症状**：手机端点击 `<input>`/`<textarea>`，页面突然 zoom in。
**根因**：iOS Safari 对 `font-size` < 16px 的输入框自动触发缩放。
**修复**：在 `@media(max-width:768px)` 中强制输入框字号 ≥16px：
```css
.chat-input-v2 input{font-size:16px}
.chat-fb-body textarea{font-size:16px}
.filter-row select{font-size:14px}         /* select 也受益 */
.filter-row input[type=number],
.filter-row input[type=date]{font-size:14px}
```

### 5. 内联 `<style>` 覆盖外部 CSS 文件
`index.html` 的内联 `<style>` 块 > 外部 `<link>` 的 `chat-widget.css`。
**禁止在 index.html 中重复定义 chat-widget 的移动端样式。**
排查：`grep 'chat-trigger\|chat-panel' index.html` → 如有定义（非引用），删除。

## 移动端溢出三重锁

任一页面手机端出界，同时加：
```css
@media(max-width:768px){
  body{overflow-x:hidden;max-width:100vw}
  *, *::before, *::after{max-width:100vw}
}
html{overflow-x:hidden}
```

## 聊天面板手机专用规则（V1.29 最终版）

```css
@media(max-width:768px){
  /* 容器右对齐，不拉伸 */
  .chat-widget-all{right:12px;bottom:16px;left:auto;max-width:100vw}

  /* 面板占满宽度，从底部弹出，顶部圆角 */
  .chat-panel-v2{width:auto;left:0;right:0;bottom:0;
    max-height:75vh;max-height:75dvh; /* dvh 兜底动态视口 */
    border-radius:16px 16px 0 0;
    animation:none;transition:none}    /* 禁动画防抖动 */

  /* 折叠触发条：紧凑药丸 */
  .chat-trigger{
    max-width:calc(100vw - 24px);      /* ✅ 空格 */
    padding:8px 14px;border-radius:24px;gap:6px;
    /* left:auto 确保不拉伸 */
  }
  .chat-trigger .trigger-text{display:none}
  .chat-trigger img{width:32px;height:32px}
  .chat-trigger .trigger-badge{font-size:11px;padding:3px 10px}

  /* 输入防 zoom */
  .chat-input-v2 input{font-size:16px}
  .chat-fb-body textarea{font-size:16px}

  /* 消息区限高 */
  .chat-messages-v2{max-height:40vh;max-height:40dvh}
}
```

## 更新日志页面手机 CSS

```css
@media(max-width:768px){
  body{overflow-x:hidden;max-width:100vw}
  header{padding:12px 14px;gap:8px}
  header h1{font-size:17px}
  .container{padding:16px 12px}
  .timeline{padding-left:24px}
  .changes{padding:12px 14px}
  .changes li{font-size:12px;word-break:break-word}
  code{word-break:break-all;font-size:10px}
}
```

## 必须检查的页面

每次改 CSS 后，以下页面**全部**需要在手机端验证不出界：
- `/bidding/` (index.html) — 数据看板
- `/bidding/changelog.html` — 更新日志
- `/bidding/report-*.html` — 日报

**验证命令**：
```bash
# 检查所有 calc() 空格
grep -rn 'calc(' /var/www/html/bidding/ | grep -v 'calc([0-9]' | grep -v 'calc(100vw -'
# 检查冲突的 chat 样式
grep -rn 'chat-trigger\|chat-panel' /var/www/html/bidding/index.html
# 检查 iOS zoom 漏洞
grep -rn 'input\|textarea' /var/www/html/bidding/chat-widget.css | grep -v 'font-size:1[6-9]'
```

## 历史案例

| 日期 | 页面 | 症状 | 根因 |
|:--|:--|:--|:--|
| 2026-06-26 | index.html | 手机左右滑动出界 | body 缺 `overflow-x:hidden` + table `min-width:800px` 残留 |
| 2026-06-26 | changelog.html | 手机可左右滑动 | 零手机 CSS，完全无 `@media` 块 |
| 2026-06-26 | chat-widget | 面板比屏幕大+震动 | `calc(100vw-16px)` 缺空格 + 拖动在触屏异常 + JS 内联覆盖 CSS |
| 2026-06-26 | chat-widget | 手机输入框聚焦→全屏放大 | iOS Safari `<input>` font-size=12px < 16px 阈值 |
| 2026-06-26 | chat-widget | 折叠触发条拥挤 | 手机端 `left:8px` 拉伸过宽，需 `left:auto` 固定在右下 |
| 2026-06-26 | index.html | chat-trigger 样式异常 | index.html 内联样式覆盖 chat-widget.css 的移动端规则 |
| 2026-06-26 | index.html | 「查看」按钮不好点、每页按钮太小 | 28px 触控目标 < 36px 最低标准；文字链接无按钮形态 |
