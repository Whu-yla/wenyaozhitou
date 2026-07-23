# data.json 防爆策略（2026-06-25）

## 问题
153条招标 data.json = 6.2MB，浏览器加载超时30秒，页面空白。

## 解决方案

### 1. 精简字段（report_generator.py trim()）
- 删除：raw_html, raw_text, content_summary, created_at
- 保留且截断：title(80), url(200), source_site(20), procurement_owner(40), region(10)
- 保持类型：id(number), relevance_score(number) — 否则 app.js .toFixed()崩溃
- 效果：6.2MB→87KB（-98.6%）

### 2. 轻量版 data_light.json
```json
[
  {"id": 123, "title": "...", "score": 85, "source": "华润守正"}
]
```
四字段极简，10x加载速度。

### 3. 分页
- data.json: TOP 50招标 + TOP 50中标 + has_more标志
- data_bid_p1.json / data_win_p1.json: 每页100条

### 4. 铁律
- data.json > 1MB → 立即精简
- 禁止 raw_text / raw_html 进前端JSON
- number 字段保持 number，不转 string
- 每次报告生成后 `ls -lh data.json` 确认 < 500KB
