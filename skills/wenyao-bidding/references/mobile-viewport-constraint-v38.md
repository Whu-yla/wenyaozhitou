# 移动端视口约束 — 防横向滚动（V1.38）

## 症状

手机端页面可以左右滑动，卡片/菜单栏/标题栏之间存在多余边距。不应该是这样——正常 App 左右滑不动。

## 根因

`stats-row`、`filter-bar`、`.container` 等容器设了 `max-width:1400px`（桌面居中），但未设 `width:100%`。在 375px 手机屏幕上，元素撑到自然宽度 1265px → 整页横向溢出。

```
HTML: 1265px (instead of 375px viewport)
  BODY: 1265px
    .app-header: 1265px
    .stats-row: 1265px (max-width:1400px, no width:100%)
    .filter-bar: 1265px (same)
```

## 修复（三层防护）

```css
/* 全局锁 */
html, body { overflow-x: hidden }

/* 移动端所有主容器 */
@media(max-width:768px) {
  .stats-row, .filter-bar, .container,
  .app-header, .tab-bar {
    max-width: 100vw !important;
    width: 100% !important;
    box-sizing: border-box;
  }
}
```

## 验证

浏览器 Console：
```js
document.querySelectorAll('*').forEach(el => {
  const w = el.getBoundingClientRect().width;
  if (w > window.innerWidth + 2) console.log(el.tagName, el.className, w);
});
```
正常情况应无输出。

## 同步规则

`index.html` 和 `polish_report.py` 的 `MOBILE_CARD_CSS` 块必须同步包含此约束。
