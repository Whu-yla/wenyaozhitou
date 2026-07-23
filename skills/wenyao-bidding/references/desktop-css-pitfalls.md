# 桌面端 CSS 陷阱 (2026-06-26, updated 2026-06-26 pm)

## 1. 筛选栏截断 (filter-scroll-wrapper overflow:hidden)

**症状**：桌面端筛选栏「预算≥万」「导出」「重置」在日期后面被裁剪，不可见。

**根因**：`.filter-scroll-wrapper{overflow:hidden}` 在桌面端也生效，把超出容器宽度的元素切掉。

**修复**：
```css
.filter-scroll-wrapper{overflow:visible}
.filter-row{flex-wrap:nowrap}  /* 单行，不换行 */
.filter-scroll-wrapper::after{display:none}  /* 渐变淡出仅手机端 */
```

## 2. ⋯ (kebab) 按钮桌面端未隐藏 — 两阶方案

### 阶段1: CSS !important（首选）
```css
.kebab-btn{display:none!important}
@media(max-width:768px){
  .kebab-btn{display:flex!important}
}
```

### 阶段2: JS 条件渲染（CSS !important 失效时的兜底）
**致命坑 (2026-06-26)**：某些浏览器环境（Browserbase/远程渲染）中，即使 CSS 写了 `display:none!important`，`getComputedStyle` 仍可能返回 `inline`。此时必须改用 JS 层面不渲染：

```javascript
// app.js — 仅手机端生成 kebab HTML
const menuHtml = window.innerWidth <= 768
  ? `<span class="kebab-btn" onclick="...">⋯</span>`
  : '';
```

**验证**：`document.querySelectorAll('.kebab-btn').length` 桌面端必须 = 0。

## 3. CSS @media 顺序陷阱

**致命坑 (2026-06-26)**：`@media` 隐藏规则放在基础规则**之前**会被覆盖：

```css
/* ❌ 错误：media 在前 → 被后面的 display:flex 覆盖 */
@media(min-width:769px){#pullIndicator{display:none}}
#pullIndicator{display:flex; ...}  /* ← 覆盖了上面的 display:none */

/* ✅ 正确：media 在后 → 覆盖前面的 display:flex */
#pullIndicator{display:flex; ...}
@media(min-width:769px){#pullIndicator{display:none}}
```

**原则**：桌面端隐藏规则（`@media(min-width:769px)`）必须写在所有基础规则的**最后面**，确保覆盖基础规则中的 `display:flex`/`display:block`。

## 4. 移动端专属特性桌面端禁用

以下特性仅适用于手机端（≤768px），桌面端必须禁用：

| 特性 | 桌面端禁用方式 |
|:--|:--|
| 下拉刷新 (Pull-to-refresh) | JS: `if(window.innerWidth>768)return` + CSS: `@media(min-width:769px){#pullIndicator{display:none}}` |
| ⋯ 三点菜单 (Kebab) | JS 条件渲染（见 §2）+ CSS: `display:none!important` |
| 横向滑动筛选 | CSS: `flex-wrap:nowrap`（单行紧凑，不滑动） |

## 5. CSS 修复持久化铁律

每次修改 `index.html` 的内联 `<style>` 块后，必须在 `polish_report.py` 的 `polish()` 函数中加对应的字符串替换逻辑（idempotent），否则下一次 `report_generator.py` 重写 index.html 时修复丢失。

```python
if '旧CSS字符串' in html:
    html = html.replace('旧CSS字符串', '新CSS字符串')
    modified = True
```

**已持久化的修复清单 (polish_report.py §5)**：
- `filter-scroll-wrapper` overflow:hidden → visible
- `filter-row` gap 调整
- `kebab-btn` → display:none!important
- `#pullIndicator` → @media(min-width:769px) hide (AFTER main rules)
- OG tags + Favicon 注入 (§4)
