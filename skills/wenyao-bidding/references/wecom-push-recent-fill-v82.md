# 企微推送 v8.2 — 近7日补位机制

## 背景

管线每天可能仅有 0-2 条新增 ≥50 分项目（去重率高、平台更新节奏慢），推送仅发 1 张卡片太寒酸。

## v8.2 改进（2026-06-29）

### 补位逻辑

```python
# 1. 先查今日 ≥50 分项目（LIMIT 8）
top_bid = conn.execute(
    "SELECT * FROM bidding_notices WHERE date(fetch_date)=? AND relevance_score>=50 "
    "ORDER BY relevance_score DESC LIMIT 8", (today,)
).fetchall()

# 2. 不足 5 条时，从近 7 日补位（排除今日已有 ID）
if len(top_bid) < 5:
    existing_ids = {r['id'] for r in top_bid}
    fill = conn.execute(
        "SELECT * FROM bidding_notices WHERE date(fetch_date)>=date(?,'-7 days') "
        "AND date(fetch_date)<? AND relevance_score>=50 "
        "ORDER BY relevance_score DESC LIMIT ?", (today, today, 8 - len(top_bid))
    ).fetchall()
    top_bid.extend([r for r in fill if r['id'] not in existing_ids])
    top_bid = top_bid[:8]
```

### 引导语自适应

```python
today_count = sum(1 for r in top_bid if str(r['fetch_date'])[:10] == today)
recent_count = len(top_bid) - today_count
guide = f"招标相关度 TOP{len(top_bid)}"
if today_count and recent_count:
    guide += f"（今日{today_count}条 + 近期{recent_count}条）"
elif today_count:
    guide += f"（今日新增）"
else:
    guide += f"（近7日）"
```

### 无新增通知（v8.1）

即使完全无新增，也推送一条汇总消息：

```
📋 文鳐智投标监控 · 今日无新增≥50分招标
累计招标 X 条 | 中标 Y 条 | ≥50分 Z 条
👉 https://www.yfzx.online/bidding/
```

**铁律**：每天至少有一条可见推送。群不能静默。

### 防重复锁

`/tmp/wenyao_push.lock` 记录日期，同日跳过。手动补推前 `rm -f /tmp/wenyao_push.lock`。

### 数据库查询关键

推送查询用 `date(fetch_date)=?`（抓取日期），不是 `publish_date`。因为管线去重逻辑保留了原始的 `fetch_date`，大部分入库项不会更新 `fetch_date` 为当天日期。
