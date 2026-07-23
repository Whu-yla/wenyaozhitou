# API数据一致性保护 — score=0噪音过滤

## 问题场景

前端切换到 API 优先架构后，两个端点返回不同口径的数据：

| 端点 | 过滤条件 | 返回 |
|:--|:--|:--|
| `/items` | 默认 `min_score=0`（不过滤） | 157条（含63条score=0噪音） |
| `/stats` | 硬编码 `relevance_score > 0` | 94条（仅有效项） |

前端表格展示 157 条，统计卡片展示 94 条 → 数字打架，用户困惑。

## 根因

1. `query_items()` 的 `min_score` 默认值设为 `0`，返回全部入库项（包括被 L1 判别器拒绝的 score=0 项）
2. `handle_stats()` 使用 `relevance_score > 0` 过滤，只统计有效项
3. 两处口径不一致

## 修复

### 1. items API 默认 min_score=1

```python
# bookmark_server.py → query_items()
# 修改前
min_score = float(params.get('min_score', ['0'])[0])
# 修改后
min_score = float(params.get('min_score', ['1'])[0])  # 默认排除0分噪音
```

### 2. winning_notices 表缺少 notice_type 列

`winning_notices` 表结构中没有 `notice_type` 列，但 `query_items()` 的 SELECT 列表中包含它。修复：

```python
if table == 'winning_notices':
    cols = cols.replace('notice_type', "'winning' as notice_type")
    cols = cols.replace('budget_amount', "'' as budget_amount")
    cols = cols.replace('procurement_owner', "'' as procurement_owner")
    cols = cols.replace('category', "'' as category")
    cols = cols.replace('province', "'' as province")
```

## 数字一致性自检

每次修改 API 后必须验证三个来源一致：

```bash
# 1. items API
curl -s 'http://127.0.0.1:8090/items?type=bidding&size=0' | python3 -c "import sys,json;print(json.load(sys.stdin)['total'])"

# 2. stats API
curl -s 'http://127.0.0.1:8090/stats' | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['bidding_total'])"

# 3. 直接查库
python3 -c "import sqlite3;c=sqlite3.connect('data/bidding.db');print(c.execute('SELECT COUNT(*) FROM bidding_notices WHERE relevance_score>0').fetchone()[0])"
```

三个数字必须完全一致。

## 关键原则

- **score=0 项不应出现在任何面向用户的界面**。它们已被 L1 判别器拒绝，入库仅用于审计追溯
- **API 所有端点默认过滤 score=0**，仅在需要调试时通过 `min_score=0` 显式暴露
- **data.json 降级后备也必须过滤 score=0**（`report_generator.py` 的 SQL 使用 `relevance_score>0`）
