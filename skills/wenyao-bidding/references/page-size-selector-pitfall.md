# 每页条数选择器 — 定义但未调用陷阱

## 症状

用户问"选择器在哪？用户应该可以自主选择"。功能代码存在但页面上看不到控件。

## 根因

`renderPsSelector(id)` 函数已定义，HTML 占位符 `id="psSelector"` 也存在，但函数**从未被调用**——`doFilter()` 只调了 `renderPg()`，漏掉 `renderPsSelector()`。

## 架构 (V1.27+)

选择器在**筛选栏**（表格上方），不在分页栏：

```
[搜索] [客户▼] [地域▼] [相关度≥] [日期起] 至 [日期止] [预算≥万] │ 每页 [20|50|100] [导出] [重置]
```

- HTML 占位符：`<div class="pg-btns" id="psSelector"></div>`（在 filter-row 内）
- JS 渲染：`renderPsSelector("psSelector")` 在 `doFilter()` 中调用
- 默认值：`ps = 20`（V1.26 之前是 50）
- 选项：`[20, 50, 100]`

## 调用位置

```javascript
// app.js doFilter() — bid 分支
renderPsSelector("psSelector");  // 在 renderPg() 之前
// win 分支同样调用
renderPsSelector("psSelector");
```

统一使用同一个 id，因为 `ps` 是全局变量，招标和中标共用同一页大小。

## 教训：UI 组件三步闭环

任何新 UI 组件必须**三处齐全**：
1. HTML 占位符（带 `id`）
2. JS 渲染函数（`renderXxx(id)`）
3. **调用点**（`init()` 或 `doFilter()` 中实际调用）

只定义不调用 = 对用户来说不存在。

## 验证

```bash
curl -s https://www.yfzx.online/bidding/ | grep -c "psSelector"  # 必须 ≥1
curl -s https://www.yfzx.online/bidding/ | grep -c "每页"        # 必须 ≥1
```
