# Tab Badge 诱骗点击 —— Badge 数字 ≠ 表格内容

**版本**：V1.41  
**日期**：2026-06-30

## 症状

点「今日新增」→ 中标 tab badge 显示 16，用户以为有 16 条中标。点中标 Tab → badge 立刻从 16 跳为 3，表格只显示 3 条。用户感到被欺骗。

## 根因

`activeStatFilter` 是全局状态，切换 Tab 时不清除。非活跃 Tab 的 badge 用 `realWinning=16`（全局真实值），一旦切过去变活跃，立即切换为 `totalWinning=3`（过滤后值）。用户基于 badge 数字做判断 → 点进去 → 数字变了 → bait-and-switch。

## 两处修复

### 修复 A：updateApiStats() 按活跃 Tab 分流

```js
function updateApiStats() {
    // 只有当前活跃 Tab 显示过滤后计数
    const showBid = (activeStatFilter && !starOnly && tab === 'bid') ? totalBidding : realBidding;
    const showWin = (activeStatFilter && !starOnly && tab === 'win') ? totalWinning : realWinning;
    document.getElementById('cntBid').textContent = showBid;
    document.getElementById('cntWin').textContent = showWin;
    document.getElementById('statBidTotal').textContent = showBid;
    document.getElementById('statWinTotal').textContent = showWin;
}
```

**判定逻辑**：`activeStatFilter` 激活 + 非收藏模式 + 是当前活跃 Tab → 用过滤值。否则用全局真实值 `realBidding`/`realWinning`。

### 修复 B：sw() 切 Tab 时清除 activeStatFilter

```js
function sw(t) {
    // ...
    else { 
        starOnly = false;
        if (activeStatFilter) {
            activeStatFilter = null;           // 清除筛选
            renderStatBanner();                // 隐藏 banner
            document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
        }
    }
    // ...
}
```

**原则**：用户手动切换 Tab 意味着退出筛选视图。残留的 `activeStatFilter` 会导致新 Tab 的内容和 badge 不一致。

### ⚠️ 防自毁：statClick 不调 sw()

`statClick` 内部跳转 Tab 是程序行为，不应触发放 `sw()` 的清除逻辑。详见 `references/stat-click-sw-self-destruct.md`。

## 完整交互流程

| 操作 | 招标 badge | 中标 badge | 表格 |
|:--|:--|:--|:--|
| 初始 | 103 (realBidding) | 16 (realWinning) | 全部 |
| 点「今日新增」| 2 (totalBidding) | 16 (realWinning) | 今日招标 |
| 点「中标」Tab | 103 (realBidding) | 16 (realWinning) | 全部中标 |

✅ badge 数字 = 表格内容，无诱骗。
