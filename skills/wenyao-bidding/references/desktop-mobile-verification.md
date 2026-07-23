# 桌面端改动 → 移动端必验证

## 铁律

用户原话：「你老是这样只顾一边！」「手机端又出问题了」

每次修改 `index.html` 的 CSS/HTML 结构后，必须同时验证桌面端和移动端。

## 三步验证流程

```
1. 改完 → 浏览器 1280px 验证桌面端
2. matchMedia('(max-width:768px)') 确认移动端 CSS 规则存在且正确
3. 确认移动端特定样式未被宽泛的 polish 替换覆盖
```

## 典型漏检案例

### 案例 1：筛选栏右对齐重构 → 手机端竖列堆叠
- 桌面端：导出/重置提级到 `.filter-bar` 直接子级，右对齐完美
- 手机端：`.filter-bar{display:block}` → 导出/重置变成竖列堆在筛选行下面
- 修复：`@media(max-width:768px)` 隐藏 bar 级 extras

### 案例 2：密度切换 → 手机卡片压扁
- 桌面端：`body.dense tbody td{padding:4px;font-size:11px}` 紧凑模式正常
- 手机端：卡片 Grid 布局也被压扁，18px padding → 4px，卡片挤成一坨
- 修复：`@media(max-width:768px)` 覆盖 `body.dense` 恢复卡片正常间距

### 案例 3：overflow 全局替换误伤
- polish 的 `html.replace('overflow:hidden', 'overflow:visible')` 同时命中桌面端和手机端的 filter-scroll-wrapper
- 手机端需要 `overflow:hidden` 才能横向滚动
- 修复：精确匹配 `flex:1;min-width:0;overflow:hidden` 而非裸 `overflow:hidden`

## 验证命令

```javascript
// 在浏览器 console 执行
JSON.stringify({
  mobileActive: window.matchMedia('(max-width: 768px)').matches,
  denseCardsOk: !document.body.classList.contains('dense') || 
    getComputedStyle(document.querySelector('tr.data-row')).padding === '18px 16px',
  noExtraRows: document.querySelectorAll('.filter-bar > span:not(.search-icon)').length === 0 ||
    window.matchMedia('(min-width: 769px)').matches
})
```
