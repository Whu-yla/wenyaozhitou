# 新增数据列检查清单

> 用户原话：「加了预算金额字段，搜索的条件里面却没有预算的筛选条件！相关度 100 分制却只有 ≥7」

## 四步铁律

每次给表格新增数据列，必须同步完成以下 4 项：

| # | 位置 | 操作 | 验证方法 |
|:--|:--|:--|:--|
| 1 | 表头 | `report_generator.py` 模板加 `<th>` | `grep '▴.*列名.*▾' index.html` |
| 2 | 渲染 | `app.js` 行渲染加 `<td>` | 浏览器 `getComputedStyle(td).textContent` |
| 3 | 导出 | `app.js` `smartExport()` 加 cols+keys | 点击导出 → 打开CSV检查列数 |
| 4 | **筛选** | 模板加 `<input>` + `app.js` `getFilt()` 加过滤逻辑 + `resetF()` 加清理 | 填入值 → 检查结果数 |

## 筛选控件设计原则

- **数字/金额列**：用 `<input type="number">` 设下限（如"预算≥ 万元"），不设固定下拉选项
- **分数/评级列**：用 `<input type="number">` 自由输入（如"最低相关度 0-100"），不设固定阈值
- **自由输入优于固定下拉**：用户可能需要任意阈值（如 85 分、50 万元），固定选项无法覆盖

## 示例：添加预算金额列

```html
<!-- 模板：filter-row 加输入框 -->
<input type="number" id="fBudget" placeholder="预算≥万元" min="0" step="0.01" 
       onchange="doFilter()" style="width:110px">
```

```javascript
// app.js getFilt()：加过滤逻辑
const bgt = parseFloat(document.getElementById("fBudget")?.value || 0);
if (bgt) d = d.filter(i => { 
    const v = parseFloat(i.budget_amount); 
    return v && v >= bgt; 
});

// app.js resetF()：加清理
["search","fScore","fCat","fProv","fBudget","dateFrom","dateTo"].forEach(...)
```

## 历史教训

| 事件 | 错误 | 正确做法 |
|:--|:--|:--|
| V1.21 加预算金额列 | 只加了表头+渲染+导出，漏了筛选 | V1.22 补 `fBudget` 输入框 |
| V1.11 相关度筛选 | 固定下拉 ≥4/≥7 | V1.22 改为 0-100 自由输入 |
