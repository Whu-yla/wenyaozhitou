# 筛选栏 display:contents 合并修复

**日期**：2026-06-26  
**版本**：V1.35  
**问题**：V1.33 移动端设计引入 `.search-row` + 两个 `.filter-row` 结构，桌面端未合并导致 3 行堆叠。

## 症状
桌面端筛选栏显示为 3 行：
```
🔍 [搜索框] [搜索]              ← .search-row
[全部客户] [全部地域] [相关度]    ← .filter-row 1
[日期起] 至 [日期止] [预算]      ← .filter-row 2
```
用户期望单行：搜索 + 客户 + 地域 + 相关度 + 日期 + 预算全部在一行。

## 根因
HTML 结构为三组独立的块级/行内块元素，`.filter-bar` 不是 flex 容器，子元素默认块级排列。

## 修复 — CSS Only（不改 HTML）

```css
@media(min-width:769px){
  /* 1. filter-bar 变成 flex 单行容器 */
  .filter-bar{display:flex;flex-wrap:nowrap;align-items:center;gap:6px;overflow-x:auto}
  
  /* 2. 搜索行紧贴不缩放 */
  .search-row{flex-shrink:0}
  
  /* 3. filter-scroll-wrapper 也变成 flex */
  .filter-scroll-wrapper{display:flex!important;flex-wrap:nowrap;align-items:center;gap:6px;overflow:visible!important;flex-shrink:0}
  
  /* 4. ★核心★ filter-row → display:contents 将子元素提升到父级 flex 流 */
  .filter-scroll-wrapper .filter-row{display:contents}
  .filter-scroll-wrapper .filter-row > *{flex-shrink:0}
  
  /* 5. 隐藏内部 spacer */
  .filter-scroll-wrapper .filter-row span[style*="flex:1"]{display:none}
  
  /* 6. 统一高度 */
  select,input[type=date],input[type=number]{height:36px;box-sizing:border-box}
}
```

**`display:contents` 原理**：元素本身从渲染树消失，但其子元素提升到父容器层级。两个 `.filter-row` div 消失，它们的所有子元素（select、input、span）直接成为 `.filter-scroll-wrapper` 的 flex 子项 → 全部在一行显示。

## 搜索框胶囊附加修复
搜索框也需要修复以形成「输入框 + 按钮」胶囊：
```css
.search-box{display:flex;align-items:center;flex:1.2;min-width:240px;max-width:400px;position:relative}
.search-box input{flex:1;height:36px;border-radius:6px 0 0 6px;padding:8px 12px 8px 34px}
.search-btn{height:36px;border-radius:0 6px 6px 0;border-left:none;background:var(--accent);color:#fff}
.search-box .search-icon{position:absolute;left:10px;top:50%;transform:translateY(-50%);z-index:1;pointer-events:none}
```

## 移动端保护
移动端 CSS（`@media(max-width:768px)`）不被影响，因为所有新规则都在 `@media(min-width:769px)` 内。
