# 桌面/移动端功能分离模式 (updated V1.33)

## Gold Rule: Desktop change → verify mobile FIRST

**用户原话：「你老是这样只顾一边！」**

每改完桌面端 UI 后，必须在移动端视口验证。铁律三步：
1. 改代码 → 刷新桌面验证
2. `window.innerWidth=390` + 检查 CSS 媒体查询是否激活
3. 验证移动端特定样式未被桌面改动覆盖

## 常见跨端破坏案例

### 筛选栏结构重构 → 移动端溢出垃圾
**场景**：为桌面右对齐把导出/重置/psSelector 从 `.filter-scroll-wrapper` 移到 `.filter-bar` 直接子级。
**移动端破坏**：`.filter-bar{display:block}` → 这些元素竖列堆在筛选栏下方。
**修复**：`@media(max-width:768px)` 中隐藏这些元素。
```css
@media(max-width:768px){
.filter-bar > span:not(.search-icon),
.filter-bar > .pg-btns{display:none!important}
.filter-bar > .btn{display:none!important}
.filter-bar > .btn[onclick*="smartExport"]{display:inline-flex!important}
}
```

### polish script 字符串替换过于宽泛
**场景**：`html.replace('overflow:hidden', 'overflow:visible')` 匹配所有出现。
**破坏**：手机端 `.filter-scroll-wrapper{position:relative;overflow:hidden}` 也被改成 `visible` → 横向滚动失效。
**修复**：用完整上下文精确匹配：
```python
# ✅ 精确——只匹配桌面端的 flex 缩写
html = html.replace(
    '.filter-scroll-wrapper{flex:1;min-width:0;overflow:hidden}',
    '.filter-scroll-wrapper{flex:1;min-width:0;overflow:visible}')

# ❌ 宽泛——手机端的也被改了
html = html.replace('overflow:hidden', 'overflow:visible')
```

## 分离模式

### 1. 下拉刷新 (Pull-to-refresh)
**JS 层**：IIFE 中先检查 `window.innerWidth > 768`，桌面端直接 `el.remove()` 删除 DOM 元素。
```javascript
(function(){
    if (window.innerWidth > 768) {
        const el = document.getElementById('pullIndicator');
        if (el) el.remove();
        return;
    }
    // ... mobile touch logic
})();
```
**CSS 层**（兜底）：`@media(min-width:769px){#pullIndicator{display:none}}` **必须写在基础规则之后**。

### 2. ⋯ 菜单 (Kebab button)
**JS 层**：条件渲染，桌面端不生成元素。
```javascript
const menuHtml = window.innerWidth <= 768
    ? `<span class="kebab-btn" onclick="...">⋯</span>`
    : '';
```
**验证**：`document.querySelectorAll('.kebab-btn').length` 桌面端必须 = 0。

### 3. 筛选栏横向滚动 (Mobile only)
桌面端：`.filter-scroll-wrapper{overflow:visible}` + `flex-wrap:nowrap`（单行紧凑）
移动端：`.filter-scroll-wrapper{overflow:hidden}` + `.filter-row{overflow-x:auto;-webkit-overflow-scrolling:touch}` + 渐变淡出 `::after`

### 4. 筛选栏弹性右对齐 (V1.33 修正)
**旧方案（已废弃）**：在 filter-row 内部加 `flex:1` spacer
- 问题：spacer 的 flex 上下文是 filter-row，推不动外层 filter-bar 边界

**新方案（V1.33）**：导出/重置/psSelector 提升到 filter-bar 直接子级
```html
<div class="filter-bar">
  <div class="search-row">...</div>
  <div class="filter-scroll-wrapper">
    <div class="filter-row">...filters...</div>
  </div><!-- /filter-scroll-wrapper -->
  <span style="flex:1;min-width:8px"></span> <!-- spacer at bar level -->
  <span>|</span> <span>每页</span> <div id="psSelector">...</div>
  <button>导出</button> <button>重置</button>
</div>
```
spacer 在 filter-bar 层级 → 与统计卡片同宽 → 精准右对齐。
**polish 检测**：`if '<!-- /filter-scroll-wrapper -->' not in html:` 判断是否需重构。

## 通用铁律
1. **JS > CSS**：桌面端隐藏优先用 JS 条件渲染/移除，不依赖 CSS。
2. **CSS 兜底**：`@media` 隐藏规则必须写在基础规则**之后**。
3. **polish 持久化**：任何 index.html 改动必须同步到 `polish_report.py`，且用精确匹配而非模糊替换。
4. **验证**：`browser_console` 检查实际 DOM 状态，不只看 CSS 声明。
5. **跨端检查**：每次桌面改完，用 `matchMedia('(max-width:768px)')` 验证移动端规则存在且正确。
6. **目录权限**：新建子目录（img_gen/ 等）后立即 `chmod 755`，否则 nginx 403。
