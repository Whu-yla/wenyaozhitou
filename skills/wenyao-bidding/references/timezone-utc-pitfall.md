# todayStr() 时区陷阱 — V1.23 最终修正

## 时间
2026-06-26 00:20

## 触发
用户报告：今日新增卡片显示**1**，点击却出现**11条全部带NEW**。数字和实际数据完全不一致。

## 症状

| 组件 | 值 | 依据 |
|:--|:--|:--|
| 统计卡片 "今日新增" | 1 | `brief.today_total`（后端Python生成，CST时区） |
| 点击卡片后过滤结果 | 11条，全部NEW | `isNew()` → `todayStr()`（前端JS，UTC时区） |

## 根因：前后端时区不一致

```javascript
// ❌ 错误：toISOString() 返回 UTC 时间
function todayStr() { return new Date().toISOString().substring(0,10); }
```

```python
# 正确：datetime.now() 使用系统时区（CST/UTC+8）
today = datetime.now().strftime("%Y-%m-%d")
```

北京时间 06-26 00:20 → UTC 时间 06-25 16:20 → `Date.toISOString()` 返回 `"2026-06-25"`。

**后果**：后端统计的是 6/26 的 1 条数据，前端 `isNew()` 却把所有 publish_date=6/25 的 11 条都标为 NEW。统计卡片（后端生成）和表格渲染（前端过滤）完全不同。

## 修复

```javascript
// ✅ 正确：使用浏览器本地时间（与服务器CST时区对齐）
function todayStr() { 
  const d = new Date();
  return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
}
```

## 设计原则

1. **永远不要在浏览器端用 UTC 时间做日期比较** — `toISOString()` 返回 UTC，`getFullYear/getMonth/getDate` 返回本地时间
2. **前后端时间函数必须对齐**：
   - 后端 Python：`datetime.now().strftime("%Y-%m-%d")` — 系统时区（CST）
   - 前端 JS：`new Date().getFullYear() + '-' + ...` — 浏览器本地时区（通常也是 CST）
   - **禁止**：`new Date().toISOString().substring(0,10)` — 这是 UTC，差 8 小时
3. **服务器和浏览器必须在同一时区** — 此规则假设服务器和用户都在 UTC+8。如果未来跨时区部署，需要统一用 `Intl.DateTimeFormat` 指定时区

## 影响范围

- `isNew()` — NEW 标签渲染
- `getFilt()` 中的 `todayOnly` 过滤
- 与后端 `brief.today_total`、`todayH` 的 SQL `substr(publish_date,1,10)=?` 口径对齐

## 验证方法

```javascript
console.log('Local:', todayStr());  // 应返回如 "2026-06-26"（本地时间）
console.log('UTC:', new Date().toISOString().substring(0,10));  // 可能返回前一天
```

浏览器中测试：
1. 看统计卡片 "今日新增" 数字
2. 点击卡片 → 表格行数必须与卡片数字一致
3. 所有行的 NEW 标签必须与 `publish_date` 列一致
