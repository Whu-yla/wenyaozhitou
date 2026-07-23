# 报告表格交互 v15

## 行勾选 + 序号

- 表头 `checkAllBid`/`checkAllWin` 全选checkbox → `toggleAll(this)`
- 每行 `row-check` → `onCheckChange(chkAllId)` 联动全选状态 indeterminate
- #序号列 = `st + idx + 1`（分页偏移 + 页内索引 + 1）

## 收藏筛选

- `starOnly` 全局状态 + `swStar()` 切换
- 工具栏 ⭐收藏 按钮切换 `star-filter.ac` 黄色高亮
- `doFilter` 过滤 `stars.includes(String(i.id))`
- `exportExcel` 联动：`getStars().map(String).includes(String(i.id))`
- `resetF` 清除 `starOnly=false` + 移除按钮ac类

## Selective 导出

```javascript
const checked = [...document.querySelectorAll('.row-check:checked')].map(cb => cb.dataset.id);
if (checked.length > 0) data = data.filter(i => checked.includes(String(i.id)));
```

⚠️ `dataset.id` 是字符串，`i.id` 是数字 — 必须 `String(i.id)` 转换。不转换则 strict equality 失败。

## 简报标签高亮

- `updateTagHighlights()` 在 `toggleFilter` 和 `doFilter` 末尾调用
- 解析 `.brief .tag` 的 onclick 属性 → 匹配 `toggleFilter('fCat|fProv','value')`
- 与 `getSelectedValues` 做 includes 比对 → `tag.classList.toggle('ac', selected)`
- CSS: `.tag.ac { background:#3b82f6 !important; color:#fff }`

## 多选列表盒

- 属性: `multiple style="height:auto;max-height:160px;overflow-y:auto"`
- ⚠️ 不用 `size="1"` — 伪装下拉框无法程序刷新视觉
- `toggleFilter` 后 `sel.dispatchEvent(new Event("change"))` 触发视觉更新 + saveFilters
- `getSelectedValues` 过滤空值 `v !== ""`（剔除"全部客户"选项）
- 选中具体项时自动取消"全部"选项

## 搜索栏

- `.search-box { max-width: 240px }` CSS约束
- placeholder: "搜索 标题/业主/省份..."
- `/` 键聚焦，`Esc` 清空

## 文件操作安全

⚠️ `hermes_tools.read_file()` 返回带 `LINE_NUM|` 前缀的内容。直接 `write_file` 污染文件。

正确做法：`terminal` + heredoc 或写独立Python脚本。
