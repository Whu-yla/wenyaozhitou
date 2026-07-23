# 手机端横向滚动可发现性 + 搜索按钮模式 (V1.33 最终版)

## 问题

1. 手机端筛选栏改为 `flex-wrap:nowrap; overflow-x:auto` 横向滚动不换行后，用户不知道可以滑动
2. 搜索框使用 `oninput="doFilter()"` 自动搜，在移动端 IME 输入法下不可靠

## 方案A：搜索按钮（替代自动搜索）

**用户明确要求**：「在搜索栏右侧加一个确认的按钮，点确认就返回」

**⛔ 致命坑 — HTML onclick vs JS addEventListener**：
- ❌ `onclick="doFilter()"` — 移动端不可靠，用户反馈「点这个搜索没反应啊」
- ✅ `addEventListener('click', doFilter)` — 在 `init()` 中绑定，100% 触发

按钮必须加触感反馈：`:active{background:#0056cc}` + `transition:background .15s`

```
桌面端                              手机端
┌──────────────────────────┐       ┌──────────────────────────┐
│ 🔍 搜索标题...  │ 搜索  │       │ 🔍 搜索标题...   │ 搜索 │
│  (6px圆角)   (6px圆角)   │       │ (20px圆角)   (20px圆角)  │
└──────────────────────────┘       └──────────────────────────┘
```

**HTML**：
```html
<div class="search-row">
  <div class="search-box">
    <span class="search-icon">🔍</span>
    <input id="search" placeholder="搜索标题、招标单位、省份...">
    <button class="search-btn" onclick="doFilter()">搜索</button>
  </div>
</div>
```

**JS**（在 init() 中 — ⛔ 必须用 addEventListener，不能用 onclick 属性）：

```js
// ✅ 正确：addEventListener
const searchBtn = document.getElementById('searchBtn');
if (searchBtn) searchBtn.addEventListener('click', doFilter);

// 回车也触发
const searchEl = document.getElementById('search');
if (searchEl) searchEl.addEventListener('keydown', e => { if (e.key === 'Enter') doFilter(); });

// ❌ 错误：onclick 属性在移动端不可靠
// <button onclick="doFilter()"> → 手机上可能不触发
```

**⛔ onclick vs addEventListener 致命坑**：
- HTML `onclick="doFilter()"` → iOS Safari 可能不触发（用户反馈「点这个搜索没反应啊」）
- JS `addEventListener('click', doFilter)` → 可靠触发
- 按钮必须加触感反馈：`:active{background:...}` + `-webkit-tap-highlight-color:transparent`
- 按钮必须加 `type="button"` 防意外表单提交

**CSS 桌面端**：
```css
.search-row .search-box{display:flex;align-items:center}
.search-box input{flex:1;padding:0 12px 0 34px;height:36px;border-radius:6px 0 0 6px;...}
.search-btn{height:36px;padding:0 16px;border-radius:0 6px 6px 0;background:var(--accent);color:#fff;...}
```

**CSS 手机端**：
```css
.search-box input{border-radius:20px 0 0 20px;height:44px;...}
.search-btn{border-radius:0 20px 20px 0;background:#007aff;height:44px;...}
```

## 方案B：横向滚动 affordance（双保险）

### ① 静态 — 右侧渐变淡出遮罩

```
┌───────────────────────────░░░░░░┤
│ ← 客户 ▼  地域 ▼  相关度  ...  │  ← 右边 ░░ 暗示「还有更多」
└──────────────────────────────────┘
```

```css
.filter-scroll-wrapper{position:relative}
.filter-scroll-wrapper::after{
  content:'';position:absolute;right:0;top:0;bottom:4px;width:40px;
  background:linear-gradient(to right,transparent,#f5f5f7);
  pointer-events:none;transition:opacity .3s;z-index:1
}
.filter-scroll-wrapper.scrolled-end::after{opacity:0}
body.dark .filter-scroll-wrapper::after{background:linear-gradient(to right,transparent,#0f172a)}
```

### ② 动态 — 首次进入自动演示滑动

```js
if (window.innerWidth < 768 && !sessionStorage.getItem('scrollHintShown')) {
    const canScroll = filterRow.scrollWidth > filterRow.clientWidth + 10;
    if (canScroll) {
        setTimeout(() => {
            filterRow.scrollTo({left: 100, behavior: 'smooth'});
            setTimeout(() => filterRow.scrollTo({left: 0, behavior: 'smooth'}), 1200);
        }, 1500);
        sessionStorage.setItem('scrollHintShown', '1');
    }
}
```

进入页面 → 1.5s → 右滑100px → 1.2s 弹回。仅手机端，仅溢出时，仅演示一次。

### JS 滚动检测

```js
const filterRow = document.querySelector('.filter-row');
const wrapper = filterRow.parentElement;
const checkScrollEnd = () => {
    const isEnd = filterRow.scrollLeft + filterRow.clientWidth >= filterRow.scrollWidth - 8;
    wrapper.classList.toggle('scrolled-end', isEnd);
};
filterRow.addEventListener('scroll', checkScrollEnd, {passive:true});
checkScrollEnd();
new ResizeObserver(checkScrollEnd).observe(filterRow);
```

## ⛔ 致命陷阱汇总

| 陷阱 | 正确做法 |
|:--|:--|
| 搜索框放在 filter-row 内 → 手机端与胶囊重叠 | 搜索在独立 `.search-row`，筛选在 `.filter-row`，两者是 filter-bar 兄弟 |
| `oninput` 在移动端 IME 不可靠 | 用搜索按钮 + Enter 键，不用自动搜索 |
| 渐变颜色硬编码 | 亮/暗模式分别 `#f5f5f7` / `#0f172a` |
| 无 pointer-events:none | 渐变遮罩拦截点击 |
| 无 ResizeObserver | 窗口旋转/分屏时漏检测 |
| gap=0 | 设 8px 容忍，防浮点精度问题 |
| 只用渐变不够 | 加自动演示动画（双保险） |
| 桌面端搜索框和胶囊高度不一致 | 统一 `height:36px; box-sizing:border-box` |
| 搜索按钮样式与输入框不拼合 | 输入左圆角+按钮右圆角，拼成完整胶囊 |
