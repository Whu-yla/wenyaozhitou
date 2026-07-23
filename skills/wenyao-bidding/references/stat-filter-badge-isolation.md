# 统计筛选下的 Tab Badge 隔离模式

## 问题

点击统计卡片（如「今日新增」）后，`activeStatFilter` 激活 → `apiFilter()` 过滤当前 Tab 数据 → `updateApiStats()` 更新 badge。

**旧行为**：`updateApiStats()` 用 `totalBidding`/`totalWinning`（已被 `apiFilter` 覆写为过滤值）同时覆盖两个 Tab badge → 用户看到两个 Tab 的数字都变。

**用户期望**：只改变**当前活跃 Tab** 的 badge，另一个 Tab 保持全局真实总数。切换到另一 Tab 时，才对该 Tab 应用过滤计数。

## 修复

引入 `realBidding`/`realWinning` 锚定变量——在 `loadFromApi()` 中从 stats API 初始化后**永不变更**：

```js
let realBidding = 0, realWinning = 0;

// loadFromApi():
realBidding = stats.bidding_total;
realWinning = stats.winning_total;
```

`updateApiStats()` 按「活跃 Tab」条件选择用过滤值还是锚定值：

```js
function updateApiStats() {
    const showBid = (activeStatFilter && !starOnly && tab === 'bid') 
        ? totalBidding : realBidding;
    const showWin = (activeStatFilter && !starOnly && tab === 'win') 
        ? totalWinning : realWinning;
    document.getElementById('cntBid').textContent = showBid;
    document.getElementById('cntWin').textContent = showWin;
}
```

## 行为矩阵

| 活跃 Tab | activeStatFilter | 招标 badge | 中标 badge |
|:--|:--|:--|:--|
| 招标 | null | realBidding (103) | realWinning (16) |
| 招标 | 'today' | totalBidding (过滤值, 如 2) | realWinning (16) |
| 中标 | 'today' | realBidding (103) | totalWinning (过滤值, 如 3) |
| 收藏 | 'today' | realBidding (103) | realWinning (16) |

## 关键教训

- `totalBidding`/`totalWinning` 是**工作变量**——`apiFilter()` 会覆写它们
- `realBidding`/`realWinning` 是**锚定变量**——只在 init 时赋值，之后永不改变
- Badge 渲染永远用**条件选择**（`condition ? working : anchor`），而非无条件用工作变量
- 此模式和 `activeStatFilter` 快照模式（`const` at entry of async function）协同工作，共同防止竞态污染
