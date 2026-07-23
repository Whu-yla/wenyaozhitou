# 排序三角指示器 — ▴▾ V1.20 最终方案

## 演变历史

| 版本 | 方案 | 问题 |
|:--|:--|:--|
| pre-V1.20 | 排序后 `::after` 显示 ↑ 或 ↓ | 用户看不出可排序 |
| V1.20 初版 | `::before`(▴) + `::after`(▾) inline，8px，左右夹文字 | 太小看不见；三角没有上下叠放 |
| **V1.20 终版** | position:absolute 右对齐叠放，11px，独立高亮 | ✅ |

用户反馈：「方向对了，点击应该三角形有反应的，比如下面的三角形高亮啊，或者上面的三角形高亮啊，表示是正序或者倒序，然后这个三角形要能看见！你现在太小了，完全看不见」

## 最终 CSS

```css
/* 所有可排序列：留右侧空间 + 相对定位 */
thead th[onclick]{padding-right:18px;position:relative}

/* ::before = ▴ 上三角，定位在列头右上 */
thead th[onclick]::before{content:'▴';position:absolute;right:4px;top:5px;font-size:11px;line-height:1;opacity:.3;pointer-events:none}

/* ::after = ▾ 下三角，定位在列头右下 */
thead th[onclick]::after{content:'▾';position:absolute;right:4px;top:13px;font-size:11px;line-height:1;opacity:.3;pointer-events:none}

/* 升序：上三角亮起 */
thead th.sort-asc::before{opacity:1;color:var(--accent)}
thead th.sort-asc::after{opacity:.3}

/* 降序：下三角亮起 */
thead th.sort-desc::after{opacity:1;color:var(--accent)}
thead th.sort-desc::before{opacity:.3}
```

## ⛔ 致命坑：JS 从未添加 sort-asc/sort-desc class！

CSS 写了 `thead th.sort-asc::before`，但 `srt()` 函数只切换了 `sf`/`sd` 状态变量，**从未给 `<th>` 元素添加过 class**。三角的亮/灭 CSS 永远不会被触发。

### 修复：在 doFilter() 中添加排序指示器管理

```javascript
// doFilter() 中，在 data.sort() 之前：
document.querySelectorAll('thead th').forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc');
});
const sortTh = document.querySelector('thead th[onclick*="' + sf + '"]');
if (sortTh && sd === 1) sortTh.classList.add('sort-asc');
if (sortTh && sd === -1) sortTh.classList.add('sort-desc');
```

### 关键设计要点

1. **onclick*=" 子串匹配** — `th[onclick]` 的 `onclick` 属性值为 `srt('relevance_score')`，用 `[onclick*="relevance_score"]` 匹配。不能用 `[data-sort]` 因为 HTML 没有自定义属性
2. **先清全部再设当前** — `querySelectorAll` 遍历所有 `th` 清除 class，再给当前排序列加
3. **sf 是排序字段名**（如 `relevance_score`、`publish_date`），sd 是方向（1=asc, -1=desc）
4. **pointer-events:none** — 防止三角遮挡点击区域

## 不可排序列自动排除

`全选`、`序号`、`操作` 三列的 `<th>` 没有 `onclick` 属性，CSS 选择器 `th[onclick]` 自动跳过它们，自然不显示三角。无需额外操作。

## 文件位置

- CSS：`report_generator.py` 的 `<style>` 块内（f-string 模板，注意 `{{}}` 转义）
- JS：`app.js` 的 `doFilter()` 函数中，`data.sort()` 之前

## 修改此 CSS 时的注意事项

`report_generator.py` 是 Python f-string，CSS 中的花括号必须用 `{{` `}}` 转义。
用 `terminal + Python heredoc` 方式修改，old/new 字符串中的 `{` `}` 需要双写。
