# allB 分页数据 vs totalBidding 全量计数分叉

## 症状
- 今日新增卡片显示 11
- 点进去招标 badge=8 但表格只渲染 2 行
- 中标 badge=16 点进去变 3

## 根因分析（四重）

### ① stats SQL 口径不一致
- stats 使用 `relevance_score > 0` 计数
- items API 使用 `min_score >= 1`
- 0~1 分之间项目被 stats 计入但不被 items 返回

### ② allB 是页码级数据
- `apiFilter()` 中 `allB = d.data` → 来自 page-1, size=20
- 客户端过滤 `allB.filter(i => i.is_new_today)` → 筛出 2 条
- `totalBidding` 来自独立 size=200 请求的过滤计数 → 8 条
- 两者不同源：`allB.length`(2) ≠ `totalBidding`(8)

### ③ statClick 内调 sw() 自毁 activeStatFilter
- `statClick('today')` → 设 `activeStatFilter='today'` → 调 `sw('bid')` → `sw()` 内部清除 `activeStatFilter`
- Filter 设完即被清，筛选失效

### ④ Tab badge 诱骗点击
- 非活跃 Tab badge 使用 `realTotal`（全局值）
- 切过去后 badge 变过滤值
- 数字欺骗：中标显示 16，点进去只有 3

## 修复（V1.40-1.41 完整闭环）

1. stats SQL: `> 0` → `>= 1`
2. apiFilter today 分支：跳过 page-1 请求，独立 fetch 两个 Tab 全量数据写入 allB/allW
3. statClick：不再调 sw()，直接 apiFilter() + swRawTab()
4. updateApiStats：双 Tab 均显示过滤计数 totalBidding/totalWinning
5. sw()：切 Tab 时不清除 activeStatFilter（仅 star 模式清除）

## 验证
```
今日新增 11 = 招标 8 + 中标 3 ✓
两个 Tab 均可独立浏览今日数据 ✓
数字不再打架 ✓
```
