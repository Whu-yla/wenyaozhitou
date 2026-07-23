# data.json 防爆策略

## 问题
153条招标 + 24条中标的全量 DB 行（含 `raw_html`、`created_at` 等）直接 dump → **6.2MB JSON**
浏览器加载超时 30 秒 → 页面显示 0 条数据

## 解决方案（已实现在 report_generator.py）

### 1. 字段精简（trim 函数）
```
NUMERIC (保持 number 类型, 否则 app.js 的 .toFixed() 崩溃):
  id, relevance_score, is_new

TEXT (转为 string):
  title, url, source_site, procurement_owner, region, province, 
  category, budget_amount, winner_company, winning_amount, 
  content_summary, publish_date

删除:
  raw_html, content_summary (过长版), created_at, 所有冗余字段
```

### 2. 分页策略
- `data.json` — 首页 TOP 50 招标 + TOP 50 中标（87KB）
- `data_bid_p{1..N}.json` — 招标分页，每页 100 条精简字段
- `data_win_p{1..N}.json` — 中标分页
- `data_full.json` — 全量保留（仅归档，不加载）

### 3. 前端影响
- `allB.length` = 实际数据条数（不会因超时而为 0）
- `doFilter()` 正常渲染表格
- `sc.toFixed(1)` 需要 score 是 number 而非 string

## 关键教训
- ⚠️ `str()` 所有字段会破坏 `relevance_score` 的数值类型 → app.js `toFixed` 崩溃
- ⚠️ `int()` 会丢失浮点精度 → 用原始值
- ⚠️ 数据库行含二进制/大文本 → 必须过滤
- ⚠️ **每次修改 `report_generator.py` 后必须验证 data.json 尺寸**：`ls -lh /var/www/html/bidding/data.json`，超过 500KB 立即排查
- ⚠️ **report_generator.py 重新生成监控页后，必须补上 chat-widget.js**：`grep chat-widget /var/www/html/bidding/index.html` 确认存在
- ⚠️ **doFilter() 崩溃常见根因**：`relevance_score` 在 data.json 中是字符串 → `.toFixed()` 报错。修复：`trim()` 函数保持 score 为 number 类型
