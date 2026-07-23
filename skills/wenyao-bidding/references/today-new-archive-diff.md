# 今日新增: 归档差集设计 (V1.37)

## 语义定义

**"今日新增"** ≠ `publish_date` = 今天  
**"今日新增"** ≠ `fetch_date` = 今天  
**"今日新增"** = 昨天归档 data.json 中没有、今天 `data.json` 中有的项目

## 根因

管线每次运行会用 `INSERT OR REPLACE` 更新 fetch_date，导致所有 71 条历史项目的 fetch_date 都变成今天。直接用 fetch_date 判断 → 全部标记为新增 → 完全失效。

## 实现

### 后端 (report_generator.py)

```python
# 读取昨天归档，收集所有 id
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
yesterday_file = RD / yesterday / "data.json"
yesterday_ids = set()
if yesterday_file.exists():
    old = json.load(open(yesterday_file))
    for item in old.get('bidding', []) + old.get('winning', []):
        yesterday_ids.add(item.get('id'))

# 统计卡片数字 — 基于差集
todayB = sum(1 for r in allB if r['id'] not in yesterday_ids)
todayW = sum(1 for r in allW if r['id'] not in yesterday_ids)
todayH = sum(1 for r in allB if r['id'] not in yesterday_ids and score>=70) + ...

# data.json 字段 — 每条标记
def trim(item):
    result['is_new_today'] = 1 if item.get('id') not in yesterday_ids else 0
```

### 前端 (app.js)

**双模式 NEW 徽章**:
```javascript
function isNew(i) {
    const pd = (i.publish_date || '').substring(0, 10);
    if (pd === todayStr()) return true;  // 今天发布 = NEW
    if ((todayOnly || activeStatFilter === 'today') && (i.is_new_today || 0) === 1) return true;
    return false;
}
```

**筛选入口统一** — 所有入口都查 `is_new_today`:
- 统计卡片点击: `activeStatFilter === 'today'`
- 按钮筛选: `todayOnly`
- 两个走同一代码: `d.filter(i => (i.is_new_today || 0) === 1)`

## 陷阱

- **入口分裂**：统计卡片 `statClick('today')` 和按钮 `todayOnly` 曾走不同逻辑 → 点数不一致。必须统一。
- **重复逻辑**：`yesterday_ids` 计算只需一次，不可在 `trim()` 中重复。
- **无昨天归档**：`yesterday_file` 不存在时 `yesterday_ids` 为空 → 所有项目标记新增（第一天运行正常行为）。
