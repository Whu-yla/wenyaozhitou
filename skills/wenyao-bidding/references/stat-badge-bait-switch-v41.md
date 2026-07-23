# 统计卡片 Badge 诱骗点击 + 数字不一致（V1.41 修复记录）

## 症状

1. 「今日新增」卡片显示 11，点击后招标=2 + 中标=16 ≠ 11
2. 中标 Tab badge 显示 16（全局总数），点进去变 3（今日过滤数）→ 诱骗点击
3. 两个 Tab 的 badge 加起来不等于卡片上的数字

## 根因链

### 坑①：stats 与 items API 评分阈值不一致
- `bookmark_server.py` stats 用 `relevance_score > 0` 计数
- items API 默认 `min_score >= 1`
- 0~1 分项目被 stats 计入 today_total 但不被 items 返回 → 数字打架
- **修复**：stats 三处 SQL 统一改为 `>= 1`

### 坑②：totalBidding 是页码级非全量级
- `apiFilter()` 中 `totalBidding = allB.length` 是**当前页过滤后**数量
- 如果 8 条 today-new 招标分布在不同页，badge 只显示当前页的 2 条
- **修复**：独立请求两个 Tab 的全量数据（size=200）+ 客户端计数 `is_new_today`

### 坑③：statClick 调 sw() 自毁
- `statClick('today')` 设 `activeStatFilter = 'today'` 后调 `sw('bid')`
- `sw()` 检测到 `activeStatFilter` 非空 → 清除它
- 回到 `statClick` 后 `activeStatFilter` 已为 null → `doFilter()` 不应用任何过滤
- **修复**：`statClick` 对 today/high 类型不调 `sw()`，直接 `apiFilter()`

### 坑④：updateApiStats 双 Tab 同时覆盖
- 旧代码：`showBid = (activeStatFilter && tab==='bid') ? totalBidding : realBidding`
- 非活跃 Tab 用 `realBidding`（全局总数）→ badge 数字与实际内容不一致
- **修复**：`activeStatFilter` 激活时**两个 Tab** badge 都显示过滤计数
  ```js
  const showBid = (activeStatFilter && !starOnly) ? totalBidding : realBidding;
  const showWin = (activeStatFilter && !starOnly) ? totalWinning : realWinning;
  ```

## 最终方案

| 修复 | 文件 | 内容 |
|:--|:--|:--|
| SQL 统一 | `bookmark_server.py` | `> 0` → `>= 1` |
| 全量计数 | `app.js` → `apiFilter()` | 独立 fetch 两个 Tab + 客户端计数 `is_new_today` |
| 防自毁 | `app.js` → `statClick()` | today/high 不调 `sw()`，直接 `apiFilter()` |
| 双 Tab 过滤 | `app.js` → `updateApiStats()` | 两个 Tab 都显示过滤计数 |

## 验证标准

点击「今日新增」后必须满足：
```
招标 badge + 中标 badge = 今日新增卡片数字
```
且切换 Tab 后 badge 不变。
