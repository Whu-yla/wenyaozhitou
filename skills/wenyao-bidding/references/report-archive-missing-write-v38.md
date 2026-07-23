# NEW 标签全量误判 — 归档文件从未写入 (V1.38)

## 症状
手机端所有招标/中标项目都显示 NEW 标签。`data.json` 中 `is_new_today` 全为 `true`。

## 根因
`report_generator.py` 第 87 行打印：
```python
print(f"报告: {RD/'data.json'} ({len(allB)}招标+{len(allW)}中标) 归档:{today}")
```

但**从未创建归档目录和文件**。归档写入代码完全缺失。

`trim()` 函数中计算 `is_new_today` 的逻辑：
```python
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
yesterday_file = RD / yesterday / "data.json"
yesterday_ids = set()
if yesterday_file.exists():
    # 加载昨天的 ID...
# ⚠️ yesterday_file 永远不存在 → yesterday_ids 永远为空
# → 所有 item['id'] not in yesterday_ids 都是 True
# → 全部判为 NEW
```

## 修复
在 `generate()` 函数末尾（`data.json` 写入之后）新增：
```python
# ★ 归档今日数据 — 供明日差集计算
archive_dir = RD / today
archive_dir.mkdir(parents=True, exist_ok=True)
archive_ids = {"bidding": [{"id": r['id']} for r in allB], 
               "winning": [{"id": r['id']} for r in allW]}
(archive_dir / "data.json").write_text(json.dumps(archive_ids, ensure_ascii=False))
```

## 验证
```bash
# 归档目录必须存在
ls /var/www/html/bidding/2026-06-2*/data.json

# 归档内容（仅含 ID）
head /var/www/html/bidding/2026-06-27/data.json
# {"bidding": [{"id": 588}, {"id": 410}, ...

# is_new_today 归零（今日和昨天数据相同时）
python3 -c "
import json
with open('/var/www/html/bidding/data.json') as f:
    d = json.load(f)
new_b = sum(1 for i in d['bidding'] if i.get('is_new_today'))
print(f'NEW招标={new_b}')  # 期望 0
"
```

## 历史影响
此 bug 从 V1.36「今日新增差集」方案引入以来一直存在。归档功能在代码注释中设计好了，但写入逻辑从未实现。
