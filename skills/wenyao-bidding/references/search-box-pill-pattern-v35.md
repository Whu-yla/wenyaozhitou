# V1.35 搜索框胶囊模式 — input + button 视觉一体

**日期**：2026-06-26

## 问题

用户指出两个 UI 缺陷：
1. 🔍 放大镜图标与输入框文字不在同一水平线
2. 「搜索」按钮独立在搜索框外，不是一体胶囊

## 根因

`.search-box` 不是 flex 容器，input 和 button 作为块元素各自占行。icon 用 `position:absolute;top:50%` 但参考系是 `.search-box` 的整体高度（含 button 撑开的高度），不是 input 的高度。

## 修复（桌面端 @media(min-width:769px)）

```css
/* 搜索框变 flex，input+button 并排 */
.search-box{display:flex;align-items:center;flex:1.2;min-width:240px;max-width:400px;position:relative}

/* input 只圆左角、flex:1 占满空间 */
.search-box input{flex:1;height:36px;box-sizing:border-box;
  border-radius:6px 0 0 6px;padding:8px 12px 8px 34px}

/* button 只圆右角、蓝色背景、无左边框 */
.search-btn{height:36px;border-radius:0 6px 6px 0;
  border:1px solid var(--border);border-left:none;
  background:var(--accent);color:#fff}

/* 🔍 图标绝对定位在 input 上方 */
.search-box .search-icon{position:absolute;left:10px;top:50%;
  transform:translateY(-50%);z-index:1;pointer-events:none}
```

## 视觉效果

```
修复前：
🔍 [_____搜索框_____]
[  搜索  ]           ← 按钮独立在外

修复后：
🔍 [_____搜索框_____][搜索]   ← 一体胶囊，左圆右方
```

## 关键教训

1. **input + button 拼胶囊**：必须 `.search-box{display:flex}`，input `flex:1`，button `flex-shrink:0`
2. **边框拼接**：input `border-radius:6px 0 0 6px` + button `border-radius:0 6px 6px 0;border-left:none`
3. **icon 垂直居中**：`top:50%;transform:translateY(-50%)` 在 `display:flex;align-items:center` 的容器内可靠
4. **移动端不同**：手机端搜索框 `height:44px;border-radius:20px`（全圆角胶囊，button `border-radius:0 20px 20px 0`）
5. **不要用 max-width 死限搜索框** — 用 `flex:1.2;min-width:240px` 让它弹性伸缩
