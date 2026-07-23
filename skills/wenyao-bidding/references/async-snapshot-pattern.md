# Async 竞态快照模式

## 问题

`apiFilter()` 是 `async` 函数，内部有 `await fetch()`。函数读取的全局变量（`starOnly`、`tab`、`activeStatFilter`）可能在 await 期间被其他操作修改：

```javascript
// ❌ 错误：全局变量在 await 后被污染
async function apiFilter() {
    params.set('type', tab === 'bid' ? 'bidding' : 'winning');  // tab 可能已变
    const r = await fetch('/bidding/api/items?' + params);
    if (starOnly) { allB = allB.filter(...); }  // starOnly 可能已被翻转
}
```

**典型触发场景**：用户快速点击 Tab → `sw('star')` 设 `starOnly=true` → `apiFilter()` 启动 → 用户立即点 `sw('bid')` 设 `starOnly=false` → `apiFilter()` 的 await 返回时 `starOnly` 已是 `false` → 星标过滤跳过 → 收藏 Tab 显示 94 条。

## 修复：入口快照

```javascript
// ✅ 正确：在 await 之前用 const 快照捕获所有可变全局
async function apiFilter() {
    if (!useApi) { doFilter(); return; }
    const seq = ++_apiSeq;
    // Snapshot mutable globals
    const _starOnly = starOnly;
    const _tab = tab;
    const _activeStatFilter = activeStatFilter;
    // 后续全部用 _starOnly / _tab / _activeStatFilter
    params.set('type', _tab === 'bid' ? 'bidding' : 'winning');
    ...
    const r = await fetch(...);
    if (seq !== _apiSeq) return;  // 双重保险：新调用已启动则丢弃
    if (_starOnly) { ... }
}
```

## 三条原则

1. **所有 async 函数入口处对可变全局做 `const` 快照**
2. **快照后用 `++_apiSeq` 做竞态检测**——新调用启动时递增，旧响应回来时 `seq !== _apiSeq` 丢弃
3. **`sw()` 和 `statClick()` 入口重置 `useApi=true`**——防止之前 catch 块设 `useApi=false` 永久降级

## 相关 Bug 列表

| Bug | 触发条件 | 后果 |
|:--|:--|:--|
| 收藏显示 94 条 | 快速切 收藏→招标，`starOnly` 在 await 后被翻转 | 表显全量数据 |
| 收藏翻页显示 94 条 | `renderTable` 用 `total` 非 `data.length` | 翻页信息错 |
| Badge 污染 | `updateApiStats()` 用被过滤覆盖的 `totalBidding` | 数字互串 |
| stat 过滤泄漏进收藏 | `activeStatFilter` 未在 `sw('star')` 清除 | 收藏 Tab 空 |
| 切换 Tab 卡死 | `sw()` 守卫 `!allB.length && !allW.length` 在空数据时误拦截 | 切不动 |
