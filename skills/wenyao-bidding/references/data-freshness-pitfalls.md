# 数据新鲜度陷阱 — is_new 全员腐败案例 (V1.16 → V1.18)

## 时间
2026-06-26 00:05 → 2026-06-25 23:27 (两次修复)

## 触发
用户质问：「今日新增的11个是不是应该有个new的图标！」

## V1.16 诊断：is_new DB 字段腐败

### 发现
```
$ python3 -c "import json; d=json.load(open('data.json')); new=[i for i in d['bidding'] if i.get('is_new')]; print(len(new))"
57
```

全部 57 条招标数据 `is_new=1`，但「今日新增」统计显示只有 11 条。矛盾。

### 根因
DB schema 定义 `is_new INTEGER DEFAULT 1`。每次爬虫 INSERT 新行时 is_new 自动=1。但**爬虫从不设置旧数据的 is_new=0**。

### V1.16 修复
不再信任 DB 的 `is_new` 列，改为在 `report_generator.py` 生成 data.json 时用 `fetch_date` 实时判断：
```python
fd = str(item.get('fetch_date') or '')
result['is_new'] = 1 if fd.startswith(today) else 0
```

---

## V1.17 统计卡片数据维度错位

### 症状
统计卡片"今日新增 11"点击后显示的数据与统计数不一致。

### 根因
统计和筛选用了两个不同字段：
```
统计卡片 → brief.today_total → SQL: WHERE date(fetch_date)=today  → 11条
卡片点击 → statClick('today') → JS:  filter publish_date=today      → 不同结果！
```

### V1.17 修复：todayOnly 模式
新增 `todayOnly` 标志，卡片点击用 `is_new=1`（即 `fetch_date=today`）过滤。

**关键执行顺序**：`statClick` 中必须先 `sw()` 再设 `todayOnly` 再 `doFilter()`——颠倒则被 `sw()` 内部清掉。

---

## V1.17 双重信任链断裂 — isNew() + todayOnly 双重信任静态 is_new

### 症状
```
日期筛选 publish_date=2026-06-25 → 11 条，其中 2 条无 NEW 标签
点击今日新增卡片 → 同一项目出现 NEW 标签（用户困惑）
```

### 根因
- `isNew()` 检查 `i.is_new===1`（JSON 静态值）— 不是实时计算
- `getFilt()` todayOnly 也检查 `i.is_new===1`
- 项目 publish_date=2026-06-25、fetch_date=2026-06-24（昨天抓的）→ 后端设 `is_new=0` → 日期筛选出现但无 NEW
- 两个不同项目标题极度相似（「招标公告浙江浙能浙江」×2），用户误以为是同一项目

### V1.17b 修复：前端实时计算替代静态字段
```javascript
function isNew(i) { const fd=(i.fetch_date||'').substring(0,10); return fd===todayStr(); }
function todayStr() { return new Date().toISOString().substring(0,10); }
if (todayOnly) d = d.filter(i => isNew(i));
```

---

## ⛔ V1.18 终极修正 — fetch_date → publish_date（用户心智纠正）

### 触发
用户说 V1.17 的 bug 没修复："还是搜索今天抓到的招标数据，一共显示11条，只有相关度评分前9的项目显示了new"

### 诊断
V1.17 用 `fetch_date`（抓取日）判断 NEW。id=316/312 是 6.24 爬取但 6.25 发布 → `isNew()` 返回 false → 无 NEW。

但用户期望：**今天发布 = NEW**。用户不关心爬虫什么时候抓到数据。

### 根因
**用户心智模型 = 今天发布 = NEW，不是今天抓取 = NEW。**

| 字段 | 含义 | 用户关心？ |
|:--|:--|:--|
| publish_date | 招标公告在平台上发布的日期 | ✅ |
| fetch_date | 爬虫抓取到的日期 | ❌ 内部技术细节 |

### V1.18 修复：三处统一改用 publish_date

```javascript
// 前端 isNew()
function isNew(i) { 
  const pd = (i.publish_date || '').substring(0, 10); 
  return pd === todayStr(); 
}

// 后端 report_generator.py
todayB = conn.execute(
  "SELECT COUNT(*) FROM bidding_notices WHERE substr(publish_date,1,10)=? AND relevance_score>0",
  (today,)
).fetchone()[0]
// todayW 和 todayH 同样改为 publish_date
```

### 验证
- 日期筛选今天 → 11条，全部NEW ✅
- 今日新增卡片 → 11条，全部NEW ✅  
- 非今天发布 → 0条误显NEW ✅
- 统计卡片 today_total=11，与前端一致 ✅

---

## 教训汇总
1. **NEW = 今天发布日期** — 面向用户而非面向系统
2. **前后端三处必须一致**：isNew() + todayOnly过滤 + backend SQL — 全部用 publish_date
3. **永远不要信任预计算的布尔标志位** — 基于时间戳实时比较
4. **publish_date 可能为空** — SQL用 `substr(publish_date,1,10)=?` 而非 `date(publish_date)=?`
5. **两轮修复才找到真正根因** — V1.17 只改了数据源（静态字段→fetch_date），V1.18 才改对语义（fetch_date→publish_date）
