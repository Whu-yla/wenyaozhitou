# 统计卡片跨Tab口径统一 (V1.36)

## 问题

统计卡片「今日新增」和「高相关」的数字来自全局（招标+中标），但点击后只切到招标 Tab，显示的数字对不上。

### 场景1：今日新增
- 卡片显示 "2"（1招标 + 1中标，publish_date=today）
- 点击 → 切到招标 Tab → 过滤 today → 只显示 1 条
- 另一条在中标 Tab 里，用户看不到 → 困惑

### 场景2：高相关
- 卡片显示 "14"（`allB.filter(score>=70).length`）
- 实际有 14 招标 + 3 中标 = 17 条高相关
- 点击 → 只显示招标的 14 条 → 中标的 3 条被遗漏

## 修复（两处）

### 1. statHigh 统计口径
**之前**（3处）：
```javascript
document.getElementById("statHigh").textContent = allB.filter(i => (i.relevance_score||0) >= 70).length;
```

**修复后**：
```javascript
document.getElementById("statHigh").textContent = [...allB, ...allW].filter(i => (i.relevance_score||0) >= 70).length;
```

### 2. renderStatBanner() 横幅显示
**之前**：只显示当前 Tab 的过滤结果数量。

**修复后**：today 和 high 分支计算两 Tab 的数量并拆开展示：
```javascript
const todayBids = allB.filter(i => isNew(i));
const todayWins = allW.filter(i => isNew(i));
const highBids = allB.filter(i => (i.relevance_score || 0) >= 70);
const highWins = allW.filter(i => (i.relevance_score || 0) >= 70);

if (activeStatFilter === 'today') {
    label = '今日新增 · 招标' + todayBids.length + '条 + 中标' + todayWins.length + '条';
    count = todayBids.length + todayWins.length;
} else if (activeStatFilter === 'high') {
    label = '高相关 · 招标' + highBids.length + '条 + 中标' + highWins.length + '条';
    count = highBids.length + highWins.length;
}
```

## 原则

- 任何跨 Tab 的统计指标（今日新增、高相关），卡片数字和横幅都必须统计招标+中标
- 用户点击后在当前 Tab 看不到的部分，横幅要明确告知「还有 X 条在另一个 Tab」
- 统计卡片在 `activeStatFilter` 激活时保持全局计数不变（不随筛选缩小）
