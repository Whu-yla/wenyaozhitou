# NEW 标签语义设计原则 — V1.18 最终定论

## 时间
2026-06-25 23:27

## 触发
用户报告：日期筛选今天→11条，只有前9条有NEW。点击今日新增卡片→同一个项目出现NEW。修复V1.17（改为fetch_date）后用户说bug没修复。

## V1.17 的错误假设
V1.17 将NEW定义从静态is_new字段改为基于fetch_date实时计算：
```javascript
function isNew(i) { const fd=(i.fetch_date||'').substring(0,10); return fd===todayStr(); }
```
这导致 id=316/312（6.24爬取但6.25发布）在日期筛选视图中无NEW标签。用户认为这是bug。

## 根因：用户心智模型是「今天发布=NEW」，不是「今天抓取=NEW」

| 字段 | 含义 | 用户关心？ |
|:--|:--|:--|
| publish_date | 招标公告在平台上发布的日期 | ✅ 这是用户想知道的"新" |
| fetch_date | 爬虫抓取到该公告的日期 | ❌ 内部技术细节 |

## V1.18 最终修正

### 前端 isNew()
```javascript
// 最终版本：基于发布日期的实时计算
function isNew(i) { 
  const pd = (i.publish_date || '').substring(0, 10); 
  return pd === todayStr(); 
}
function todayStr() { 
  // ⛔ V1.23 修复：必须用 getFullYear/getMonth/getDate（本地时间）
  // 禁止用 toISOString()（返回UTC，比CST慢8小时）
  const d = new Date();
  return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
}
```

### 后端统计
```python
# report_generator.py
today = datetime.now().strftime("%Y-%m-%d")
todayB = conn.execute(
  "SELECT COUNT(*) FROM bidding_notices WHERE substr(publish_date,1,10)=? AND relevance_score>0",
  (today,)
).fetchone()[0]
# 同样改 todayW 和 todayH
```

### 前端过滤
```javascript
// getFilt() 中的 todayOnly 复用 isNew()
if (todayOnly) d = d.filter(i => isNew(i));
```

## 设计原则

1. **NEW = 今天发布日期，不是今天抓取日** — 面向用户而非面向系统
2. **前后端三处必须一致**：isNew() 、todayOnly过滤 、backend SQL — 全部用 publish_date
3. **永远不要信任预计算的布尔标志位**（如is_new字段），始终基于时间戳实时比较
4. **publish_date可能为空** — SQL用substr而非date()函数，前端?? ''兜底
5. **⛔ V1.23 时区陷阱**：`todayStr()` 严禁用 `toISOString()`（返回UTC），必须用 `getFullYear/getMonth/getDate`（本地时间）。详见 `references/timezone-utc-pitfall.md`。

## 验证结果
- 日期筛选 publish_date=2026-06-25 → 11条，全部NEW ✅
- 今日新增卡片 → 11条，全部NEW ✅
- 非今天发布 → 0条误显NEW ✅
- 统计卡片 today_total=11，与前端todayOnly过滤一致 ✅
