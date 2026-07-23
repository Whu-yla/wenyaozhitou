# 筛选栏弹性右对齐 (V1.33 最终方案)

## 目标
导出/重置按钮右边缘与上方统计卡片右边缘精准对齐。

## 演进

### ❌ V1.32 方案（已废弃）
在 `.filter-row` 内部 fBudget 后插入 `<span style="flex:1">` spacer。
```html
<div class="filter-bar">
  <div class="filter-row">
    ...controls...
    <input id="fBudget">
    <span style="flex:1"></span>  <!-- 这个 spacer 没用！-->
    <button>导出</button>
    <button>重置</button>
  </div>
</div>
```

**失败原因**：spacer 的 flex 上下文是 `.filter-row`，它只能推到 filter-row 的右边界。但 `.filter-scroll-wrapper{overflow:visible}` 环境下 filter-row 宽度由其内容决定，不由外层 filter-bar 约束。结果：导出/重置溢出 filter-bar 边界，无法与卡片对齐。

### ✅ V1.33 方案（当前）
将导出/重置/psSelector 提升到 `.filter-bar` 直接子级，spacer 放在同一层级。

```html
<div class="filter-bar">                     <!-- display:flex, 与 stats-row 同宽 -->
  <div class="search-row">搜索框</div>
  <div class="filter-scroll-wrapper">
    <div class="filter-row">
      ...所有筛选控件（fCat, fProv, fScore, dateFrom, dateTo, presets, fBudget）...
      <span style="flex:1;min-width:0"></span>  <!-- filter-row 内部 spacer -->
    </div>
  </div><!-- /filter-scroll-wrapper -->
  <span style="flex:1;min-width:8px"></span>   <!-- ⭐ bar 级 spacer，推右对齐 -->
  <span>|</span> <span>每页</span>
  <div id="psSelector"></div>
  <button onclick="smartExport()">导出</button>
  <button onclick="resetF()">重置</button>
</div>
```

**关键**：bar 级 spacer 的 flex 父容器 = `.filter-bar`（与 stats-row 同视为 max-width:1400px），所以 spacer 自然推到卡片右边缘。

## CSS 要求

### 桌面端
```css
.filter-bar{display:flex;gap:6px;align-items:center;flex-wrap:nowrap;max-width:1400px;margin:0 auto;padding:0 24px 12px}
.search-row{flex:0 1 340px;min-width:220px}
.filter-scroll-wrapper{flex:1;min-width:0;overflow:visible}
.filter-row{display:flex;gap:4px;align-items:center;flex-wrap:nowrap}
```

### 手机端 (≤768px)
```css
.filter-bar{display:block;padding:0 12px 10px}
/* 隐藏 bar 级 extras */
.filter-bar > span:not(.search-icon),
.filter-bar > .pg-btns{display:none!important}
.filter-bar > .btn{display:none!important}
.filter-bar > .btn[onclick*="smartExport"]{display:inline-flex!important}
```

## polish_report.py 持久化

### 结构检测
```python
if '<!-- /filter-scroll-wrapper -->' not in html:
    # 旧结构 → 重构为 bar 级对齐
```

### 精确替换（非模糊）
```python
# ✅ 对：完整上下文匹配
html = html.replace(
    '<span style="flex:1"></span>\n    <button class="btn" onclick="smartExport()"',
    '<span style="flex:1;min-width:0"></span>\n  </div>\n  </div><!-- /filter-scroll-wrapper -->\n    <span style="flex:1;min-width:8px"></span>\n    <span>|</span>...')

# ❌ 错：模糊匹配会误伤其他位置
html = html.replace('overflow:hidden', 'overflow:visible')  # 手机端的也被改
```

## 验证
```javascript
// 右边缘差值 ≤ 2px
fbRect.right - statsRect.right  // 应该 ≈ 0
// 重置按钮在 bar 内（不溢出）
resetRect.right <= fbRect.right  // true
```
