# 前端 async init() 静默失败 + unique_hash 迁移陷阱

## async init() 无错误处理 → 页面空表零报错（2026-06-25）

**症状**：监控页显示「📋 招标 (0)」「🏆 中标 (0)」，表格只有表头无数据行。
但 `curl` 检查 data.json 返回 200，`app.js` 正常加载，浏览器 console 无任何错误。

**根因**：`app.js` 的 `init()` 是 `async function`，内部 `await fetch(...)` 可能因网络/缓存/CORS 失败。
但函数没有 try-catch，Promise rejection 被静默吞掉，`doFilter()` 从未执行。

**修复**：
```javascript
async function init() {
    try {
        // ... 原有逻辑 ...
        doFilter();
    } catch(e) {
        console.error('init failed:', e);
        document.getElementById('tBidTb').innerHTML = 
            '<tr><td colspan="10" style="text-align:center;color:#ef4444;padding:20px">⚠️ 数据加载失败，请刷新页面重试</td></tr>';
    }
}
```

**审计验证**：curl 不足以发现此 bug。必须用 `browser_navigate` 打开实际页面，等 3 秒 async 完成，
`browser_snapshot` 检查表格是否含数据行。

## unique_hash 迁移陷阱（2026-06-25）

**场景**：修改 hash 算法（如从 `md5(title|url|source)` 改为 `md5(url)`）。
所有爬虫的 hash 函数已更新，但数据库中已有记录的 hash 仍然是旧算法生成。
下次爬虫重爬同一 URL 时，新 hash ≠ 旧 hash → `INSERT OR IGNORE` 失效 → 全部重复入库。

**修复 SOP**：改 hash 算法后，立即回填所有已有记录：
```python
import sqlite3, hashlib
c = sqlite3.connect('data/bidding.db')
for table in ['bidding_notices', 'winning_notices']:
    rows = c.execute(f'SELECT id, url FROM {table}').fetchall()
    for id, url in rows:
        new_hash = hashlib.md5((url or '').encode()).hexdigest()
        c.execute(f'UPDATE {table} SET unique_hash=? WHERE id=?', (new_hash, id))
c.commit()
```
验证：回填后 `SELECT COUNT(*) FROM t GROUP BY unique_hash HAVING COUNT(*)>1` 必须返回 0。

## 自检中浏览器验证的必要性

curl 检查全部 200 不等于页面正常。async JS 渲染失败、DOMParser 报错、CSS 布局崩坏均无法通过 curl 发现。
每次系统改动后必须 `browser_navigate` + `browser_snapshot` 验证：
- 表格行数 > 0
- 筛选器选项已填充（非仅"全部"）
- chat-widget DOM 存在
- 主题按钮 🌓 可点击
