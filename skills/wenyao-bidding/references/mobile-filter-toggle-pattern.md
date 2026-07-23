# 移动端筛选条件折叠/展开 (Filter Toggle) — V1.36

## 模式说明
手机端默认隐藏筛选条件（客户、地域、相关度、日期、预算），页面干净不拥挤。搜索框右侧放「☰ 筛选」按钮，点击展开筛选行，带下滑动画。展开后所有筛选 pill 在一条水平线上可横向滑动，右侧渐变淡出提示。

## HTML 结构

```html
<div class="search-row">
  <div class="search-box">
    <span class="search-icon">🔍</span>
    <input id="search" placeholder="搜索标题、招标单位、省份...">
    <button class="search-btn" id="searchBtn" type="button">搜索</button>
  </div>
  <!-- 筛选切换按钮，仅手机端可见 -->
  <button class="filter-toggle-btn" id="filterToggleBtn" type="button">☰ 筛选</button>
</div>
<!-- filter-scroll-wrapper 默认隐藏，点击切换按钮后展开 -->
<div class="filter-scroll-wrapper" id="filterScrollWrapper">
  <div class="filter-row">...</div>
  <div class="filter-row">...</div>
</div>
```

## CSS 要点

### 手机端（`@media(max-width:768px)`）

**搜索行 + 切换按钮：**
```css
.search-row { display: flex; align-items: center; gap: 8px; width: 100%; }
.search-box { display: flex; align-items: center; flex: 1; position: relative; }
.search-box input {
  flex: 1; height: 44px; border-radius: 22px;
  padding: 0 72px 0 40px;  /* 左留空间给🔍，右留给搜索按钮 */
  font-size: 16px;
}
.search-box .search-icon {
  position: absolute; left: 14px; top: 50%;
  transform: translateY(-50%); font-size: 16px; z-index: 1;
}
.search-btn {
  position: absolute; right: 2px; top: 2px; height: 40px;
  border-radius: 0 20px 20px 0; padding: 0 18px; font-size: 14px;
  border: none; background: var(--accent); color: #fff;
}
.filter-toggle-btn {
  display: flex; align-items: center; gap: 4px;
  height: 44px; padding: 0 14px; border-radius: 22px;
  border: 1px solid var(--border); background: var(--surface);
  color: var(--text); font-size: 14px; flex-shrink: 0;
  transition: all .2s;
}
.filter-toggle-btn:active, .filter-toggle-btn.active {
  background: var(--accent); color: #fff; border-color: var(--accent);
}
```

**筛选包裹器（默认隐藏，展开时显示）：**
```css
.filter-scroll-wrapper { display: none; margin-top: 10px; }
.filter-scroll-wrapper.expanded {
  display: flex; flex-wrap: nowrap; overflow-x: auto;
  -webkit-overflow-scrolling: touch; scrollbar-width: none;
  gap: 10px; position: relative;
  -webkit-mask-image: linear-gradient(to right, black 85%, transparent 100%);
  mask-image: linear-gradient(to right, black 85%, transparent 100%);
  animation: filterSlideDown .25s ease;
}
.filter-scroll-wrapper::-webkit-scrollbar { display: none; }
/* 两个 filter-row 合并到同一行 */
.filter-scroll-wrapper .filter-row { display: contents; }
.filter-scroll-wrapper .filter-row > * { flex-shrink: 0; }
```

**筛选 Pill 样式：**
```css
.filter-scroll-wrapper select,
.filter-scroll-wrapper input[type=date],
.filter-scroll-wrapper input[type=number] {
  height: 38px; border-radius: 19px;
  background: var(--surface); border: 1px solid var(--border);
  font-size: 13px; padding: 0 14px; flex-shrink: 0;
  color: var(--text); white-space: nowrap;
}
```

**亮色主题：**
```css
body.light .filter-toggle-btn {
  background: #fff; border-color: #cbd5e1; color: #334155;
}
body.light .filter-toggle-btn:active,
body.light .filter-toggle-btn.active {
  background: #2563eb; color: #fff; border-color: #2563eb;
}
body.light .filter-scroll-wrapper select,
body.light .filter-scroll-wrapper input[type=date],
body.light .filter-scroll-wrapper input[type=number] {
  background: #e8e8ed; border: none;
}
```

**动画：**
```css
@keyframes filterSlideDown {
  from { opacity: 0; transform: translateY(-8px); }
  to   { opacity: 1; transform: translateY(0);   }
}
```

### 桌面端（`@media(min-width:769px)`）
```css
.filter-toggle-btn { display: none !important; }
/* filter-scroll-wrapper 在桌面端始终可见 */
```

## JS 切换逻辑

```javascript
// ⛔ 正确：toggle .filter-scroll-wrapper 的 .expanded class
const filterToggleBtn = document.getElementById('filterToggleBtn');
if (filterToggleBtn) {
    const wrapper = document.querySelector('.filter-scroll-wrapper');
    filterToggleBtn.addEventListener('click', () => {
        if (wrapper) {
            const expanded = wrapper.classList.toggle('expanded');
            filterToggleBtn.textContent = expanded ? '✕ 关闭' : '☰ 筛选';
            filterToggleBtn.classList.toggle('active', expanded);
        }
    });
}
```

## ⛔ 致命坑：toggle 错 target

**症状**：点击「☰ 筛选」→ 整个筛选栏消失（包括搜索框和导出/重置按钮）。

**根因**：写成了 `filterBar.style.display = ...` toggle 整个 `.filter-bar`，而不是 toggle `.filter-scroll-wrapper.expanded` class。

**错误示例（❌ 绝不用）**：
```javascript
const filterBar = document.querySelector('.filter-bar');
filterBar.style.display = hidden ? 'flex' : 'none'; // 干掉全部！
```

**为什么错了**：
- `.filter-bar` 包含搜索框 + filter-scroll-wrapper + 导出/重置 → toggle 它会导致桌面端筛选栏也消失
- `.filter-scroll-wrapper` 在移动端 CSS 中默认 `display:none`，通过 `.expanded` class 的 `display:flex` 覆盖来展开
- 检查 `style.display`（而非 `getComputedStyle`）在初始状态是空字符串 → `=== 'none'` 为 false → 反而执行 `display = 'none'` → 什么都没展开反而加了个内联隐藏
- 第二次点击时 `style.display === 'none'` 为 true → 设为 `'flex'` → 但 className 不符 → 筛选栏显示但样式不对

## 设计原则
- **默认隐藏**：给用户干净的搜索体验，需要时再展开
- **按钮可见**：「☰ 筛选」胶囊按钮紧贴搜索框右侧，高度 44px 与搜索框一致
- **激活反馈**：点击后按钮变蓝（active class），再次点击收起
- **展开动画**：filterSlideDown 下滑淡入 0.25s
- **双重保险**：展开后如有滚动空间 + 未看过演示 → 自动滑动提示
- **间距不拥挤**：pill 高度 38px、gap 10px、搜索行与筛选行 margin-top 10px
