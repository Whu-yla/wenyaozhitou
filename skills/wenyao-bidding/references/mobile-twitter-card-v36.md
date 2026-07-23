# 移动端卡片 Twitter 风格 V1.36

## JS 模板字面量变量顺序陷阱（致命坑）

**症状**：中标 Tab 完全无数据，招标 Tab 正常，无 console 报错（模板字面量内 `ReferenceError` 被静默吞掉）。

**根因**：在 win 表 `.map()` 回调中，`menuHtml` 模板字面量用了 `${starred}`，但 `const starred = getStars()...` 定义在它**后面**：
```javascript
// ❌ 错误顺序
const menuHtml = `...${starred}...`;  // ReferenceError: starred 未定义
const starred = getStars().includes(String(i.id));
```

**修复**：变量定义必须在所有使用它的表达式**之前**：
```javascript
// ✅ 正确顺序
const starred = getStars().includes(String(i.id));
const menuHtml = `...${starred}...`;
```

**铁律**：在 `.map()` / 模板字面量 / computed property 中新增变量引用时，**先 grep 确认该变量的定义位置**，确保定义在使用之前。`const`/`let` 有 TDZ（暂时性死区），使用前未定义 = ReferenceError → 整个渲染回调静默失败。

## 背景
用户反馈手机端卡片「字太少看不到内容」「相关度分数没了」「右上角分享按钮没了」「收藏按钮布局奇怪」，要求对标 Twitter 卡片设计。同时发现 kebab（⋯）按钮的 CSS 完全缺失。

## 最终设计

```
┌─────────────────────────────────┐
│ ● 85分                       ⋯  │  ← 相关度分数 + 右上角菜单
│                                 │
│ ★ 智慧工地AI管控平台建设项目     │  ← 标题（最多两行，粗体15px）
│                                 │
│ 💰 500万  📍 湖北  📅 06-25    │  ← 信息胶囊行
│                                 │
│                   ⭐ 收藏  查看  │  ← 操作按钮行
└─────────────────────────────────┘
```

## CSS Grid 布局

```css
tbody tr.data-row {
  display: grid;
  grid-template-columns: 1fr auto auto auto auto;  /* 5列 */
  width: 100%; max-width: 100%; box-sizing: border-box;
  padding: 14px; margin-bottom: 10px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; position: relative;
  gap: 5px 8px;
}
```

### 列映射
| nth-child | 字段 | 显示 |
|:--|:--|:--|
| 1 | checkbox | ❌ 隐藏 |
| 2 | 序号 | ❌ 隐藏 |
| 3 | 相关度 | ✅ 第1行左侧，分数pill + 彩色条 |
| 4 | 标题 | ✅ 第2行全宽，两行截断 |
| 5 | 客户 | ❌ 隐藏 |
| 6 | 招标单位 | ❌ 隐藏 |
| 7 | 预算金额 | ✅ 第3行，绿色加粗 |
| 8 | 地域 | ✅ 第3行 |
| 9 | 来源 | ❌ 隐藏 |
| 10 | 日期 | ✅ 第3行 |
| 11 | 操作 | ✅ 第4行右侧，胶囊按钮 |

## 关键 CSS 规则

### 防溢出三重锁
```css
table { min-width: 0 !important; width: 100% !important; }
.table-wrap { overflow-x: visible !important; }
```

### 隐藏桌面专用单元格
```css
td:nth-child(1), td:nth-child(2),
td:nth-child(5), td:nth-child(6), td:nth-child(9) {
  display: none !important;
}
```

### 分数 Pill
```css
td:nth-child(3) {
  display: flex !important; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 600; white-space: nowrap;
}
td:nth-child(3) .score-bar {
  height: 8px; border-radius: 4px; min-width: 32px;
}
```

### 标题行
```css
td.title-cell {
  grid-column: 1 / -1;  /* 全宽 */
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  font-weight: 600; font-size: 15px; line-height: 1.45;
  white-space: normal;
  padding-right: 28px !important;  /* 给 ⋯ 按钮留空间 */
}
td.title-cell a { font-size: inherit; line-height: inherit; color: var(--text); }
```

### 信息胶囊行
```css
td:nth-child(7), td:nth-child(8), td:nth-child(10) {
  display: flex !important; align-items: center;
  font-size: 12px; color: var(--muted); white-space: nowrap; gap: 2px;
}
td:nth-child(7) { font-weight: 600; color: var(--green); }  /* 预算金额绿色 */
```

### 操作按钮行
```css
td:nth-child(11) {
  display: flex !important; align-items: center;
  justify-content: flex-end; gap: 6px; font-size: 13px;
}
td:nth-child(11) .link-btn {
  font-size: 13px; padding: 4px 10px; border-radius: 16px;
  background: var(--accent); color: #fff !important;
  text-decoration: none; font-weight: 500;
}
```

## Kebab 菜单 (⋯)

### 按钮
```css
.kebab-btn {
  position: absolute; top: 10px; right: 10px;
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%; font-size: 16px;
  color: var(--dim); cursor: pointer; z-index: 2;
  transition: all .15s; line-height: 1; user-select: none;
}
.kebab-btn:active { background: var(--border); color: var(--text); }
```

### 弹出菜单
```css
.kebab-menu {
  position: fixed;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,.35);
  z-index: 10000; min-width: 160px;
  padding: 6px;
  animation: kebabIn .15s ease;
}
.kebab-menu button {
  display: block; width: 100%;
  padding: 10px 14px; border: none;
  background: transparent; color: var(--text);
  font-size: 14px; text-align: left; cursor: pointer;
  border-radius: 8px; transition: background .1s;
}
.kebab-menu button:active { background: var(--border); }
.kebab-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: transparent;
}
@keyframes kebabIn {
  from { opacity: 0; transform: scale(.95); }
  to   { opacity: 1; transform: scale(1); }
}
```

### 亮色主题
```css
body.light .kebab-menu {
  background: #fff; border-color: #e2e8f0;
  box-shadow: 0 8px 32px rgba(0,0,0,.12);
}
body.light .kebab-menu button { color: #334155; }
body.light .kebab-menu button:active { background: #f1f5f9; }
```

## JS Kebab 菜单逻辑
```javascript
function toggleKebab(e, id, title, url, starred) {
    document.querySelectorAll('.kebab-menu,.kebab-overlay').forEach(el => el.remove());
    const overlay = document.createElement('div');
    overlay.className = 'kebab-overlay';
    overlay.onclick = () => { overlay.remove(); document.querySelector('.kebab-menu')?.remove(); };
    const menu = document.createElement('div');
    menu.className = 'kebab-menu';
    const items = [
        {label: '📤 分享', action: () => shareItem(id, title, url)},
        {label: '🔗 复制链接', action: () => { navigator.clipboard?.writeText(url).then(() => toast('链接已复制','success')); }},
        {label: '📋 复制标题', action: () => { navigator.clipboard?.writeText(title).then(() => toast('标题已复制','success')); }},
        {label: (starred?'☆':'⭐')+' '+(starred?'取消收藏':'收藏'), action: () => { toggleStar(id); }}
    ];
    items.forEach(item => {
        const btn = document.createElement('button');
        btn.textContent = item.label;
        btn.onclick = () => { item.action(); overlay.remove(); menu.remove(); };
        menu.appendChild(btn);
    });
    document.body.appendChild(overlay);
    document.body.appendChild(menu);
    const btnRect = e.target.getBoundingClientRect();
    menu.style.top = (btnRect.bottom + 4) + 'px';
    menu.style.right = (window.innerWidth - btnRect.right) + 'px';
}
```

## 修复清单

| 问题 | 根因 | 修复 |
|:--|:--|:--|
| 卡片超出屏幕 | `table{min-width:800px}` + grid 只有4列装不下5个可见单元 | `min-width:0` + 5列 grid |
| 相关度不见了 | grid 溢出导致分数被挤出可视区域 | 5列 grid + 分数独立一行 |
| ⋯ 菜单没有 | kebab-btn CSS 完全缺失 | 完整的按钮+弹窗+遮罩+动画 CSS |
| 信息太少 | 4列 grid 让单元格被截断/挤出 | 5列 grid 承载全部字段 |
| 收藏布局奇怪 | star 和 kebab 都在 title-cell 内排版混乱 | 明确的行布局：分数行→标题行→信息行→操作行 |
