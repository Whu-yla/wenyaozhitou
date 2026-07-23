# apiFilter() today 快速路径：串行→并行优化

## 问题

点击「今日新增」卡片后，`apiFilter()` 发出 **3 个串行 HTTP 请求**：

1. `GET /items?type=bidding&page=1&size=20` — 仅获取第1页20条
2. `GET /items?type=bidding&size=200` — 获取全量招标（算 badge 数字）
3. `GET /items?type=winning&size=200` — 获取全量中标（算 badge 数字）

请求 1 的数据被请求 2 完全覆盖——纯浪费。且 3 个串行请求叠加网络延迟（Browserbase 环境单次 ~900ms，本地 ~100-300ms）。

## 根因

`apiFilter()` 最初设计为分页查询（`page=1, size=20`），但「今日新增」需要**全量数据**（8 招标 + 3 中标跨多条）。旧代码在分页请求之后再用 for 循环补拉两个 Tab 全量，3 串行。

## 修复方案：快速路径 + Promise.all 并行

当 `activeStatFilter === 'today'` 时，跳过分页请求，直接进入**快速路径**：

```javascript
if (_activeStatFilter === 'today') {
    // 并行拉取招标+中标全量数据（size=200）
    const fetches = ['bidding', 'winning'].map(async (tt) => {
        const op = new URLSearchParams();
        op.set('type', tt); op.set('size', '200'); op.set('min_score', '1');
        const r = await fetch('/bidding/api/items?' + op.toString());
        const d = await r.json();
        if (d.ok) {
            const filtered = d.data.filter(i => i.is_new_today);
            return { tt, filtered };
        }
        return null;
    });
    const results = await Promise.all(fetches);
    // 将全量过滤数据写回 allB/allW 和 totalBidding/totalWinning
    for (const res of results) {
        if (!res) continue;
        if (res.tt === 'bidding') { totalBidding = res.filtered.length; allB = res.filtered; }
        else { totalWinning = res.filtered.length; allW = res.filtered; }
    }
    renderTable(renderData, renderTotal);
    return; // 提前返回，不跑正常分页路径
}
```

## 效果

| | 之前 | 之后 |
|:--|:--|:--|
| HTTP 请求数 | 3 串行 | 2 并行 |
| 浪费请求 | page-1 被后续覆盖 | 无 |
| 本地耗时 | ~600ms | ~200-300ms |
| Browserbase 耗时 | ~2700ms | ~1800ms |

## 关键点

1. **`Promise.all` 而非 `for...await`**：两个请求无依赖关系，必须并行。
2. **`allB/allW` 直接设为全量过滤结果**：不再需要分页拼接，因为过滤后的数据通常很少（<20 条）。
3. **`totalBidding/totalWinning` = `filtered.length`**：直接取长度，不再依赖独立计数请求。
4. **提前 `return`**：快速路径执行完不继续跑正常分页代码。

## 相关陷阱

- 参见 `apiFilter-allB-page1-vs-total-full-divergence.md` — badge 与卡片分叉的根因分析
- 参见 `api-dual-path-divergence-pitfalls.md` — API 双路径 12 大陷阱总览
- 参见 `stat-badge-bait-switch-v41.md` — Tab badge 诱骗点击修复
