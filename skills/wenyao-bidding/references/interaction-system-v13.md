# 交互系统 v13 技术规范

> 2026-06-25 — 用户明确要求：「这不是静态页面！要交互逻辑！」

## 交互闭环模板

每个操作必须走完整闭环：

```
用户点击 → DOM即时变化 → 数据持久化 → Badge/计数更新 → Toast提示 → 跨Tab可见
```

## Toast 系统

```js
function toast(msg, type='info') {
    // type: 'success'(绿) / 'warn'(橙) / 'info'(蓝)
    // 固定定位右上角，2秒自动消失
    // CSS动画: @keyframes slideIn (translateX + opacity)
}
```

## 收藏联动

| 调用点 | 动作 |
|:--|:--|
| `toggleStar(id)` | localStorage更新 → `updateStarBadge()` → `toast()` → `syncBookmarkToServer()` → `doFilter()` |
| `init()` | `loadBookmarksFromServer().then(() => updateStarBadge())` |
| `sw('star')` | `starOnly=true; tab='bid'` — 复用招标表格，过滤 `getStars()` |

**Badge更新**：`updateStarBadge()` 从 `getStars().length` 读值并写入 `cntStar` 元素。

## 批量选择

```js
let selectedIds = new Set();  // 全局状态

toggleSelectAll()  // 全选/取消 — 比较 selectedIds.size === data.length
toggleSelect(id)   // 单选 — Set add/delete
exportSelected()   // 导出已选 — 过滤 selectedIds，生成 CSV，toast 提示条数
```

## 表头变更

V1.13 新增 checkbox 列：

- 招标表: 10列 (checkbox32 + 序号60 + 相关度80 + 标题 + 客户100 + 招标单位120 + 地域80 + 来源120 + 日期100 + 操作60)
- 中标表: 8列 (checkbox32 + 序号60 + 相关度80 + 标题 + 中标单位 + 地域80 + 日期100 + 操作60)
- 错误提示 colspan 同步更新: 招标=10, 中标=8

## 版本号同步

改 app.js 后必须 bump HTML 中的 `?v=N` 参数，确保浏览器不载入缓存旧版。
