# statClick → sw() → activeStatFilter 自毁模式

**版本**：V1.41  
**日期**：2026-06-30

## 症状

点击「今日新增」「高相关」卡片完全无反应，表格不筛选，数据保持全量。

## 根因

`statClick()` 和 `sw()` 之间形成**自毁循环**：

```js
// statClick('today') 流程：
function statClick(type) {
    activeStatFilter = 'today';   // Step 1: 设值
    // ...
    sw('bid');                    // Step 2: 调 sw()
    // ...
    doFilter();                   // Step 4: 筛选——但 activeStatFilter 已经是 null！
}

// sw('bid') 流程：
function sw(t) {
    // ...
    if (activeStatFilter) {       // Step 3: 检测到 activeStatFilter='today'
        activeStatFilter = null;  // ← 清空了 Step 1 刚设的值！
        renderStatBanner();
        // ...
    }
}
```

**时间线**：
1. `statClick` 设 `activeStatFilter = 'today'`
2. `statClick` 调 `sw('bid')`
3. `sw()` 发现 `activeStatFilter` 为真 → 立即清空
4. `statClick` 继续执行 `doFilter()` → 检查 `activeStatFilter` → null → 不筛选

## 为什么 sw() 要清除 activeStatFilter？

`sw()` 新增了清除逻辑是为了**防止 Tab badge 诱骗点击**（用户看到 badge 16 点进去变 3）。这个逻辑本身是正确的——当用户手动切换 Tab 时，应退出 stat 筛选视图。

但 `statClick` 内部调 `sw()` 不是用户行为，是程序内部导航。

## 修复

`statClick` 对 today/high 类型**不调 sw()**，直接操作 tab 变量 + 调 `apiFilter()`：

```js
// statClick 中的导航逻辑：
if (type === 'total') { sw('bid'); }      // 切 Tab 无 filter，可以调 sw()
else if (type === 'win') { sw('win'); }   // 同上
else {
    // today / high: 不调 sw()，直接切 tab + 调 apiFilter
    if (tab !== 'bid') { starOnly = false; tab = 'bid'; pg = 1; }
}

pg = 1; sf = 'relevance_score'; sd = -1;
renderStatBanner();
if (useApi) { apiFilter(); } else { doFilter(); }  // 直接用，不经过 sw()
```

**原则**：`sw()` 的用户 Tab 切换清除逻辑不应被程序内部导航触发。内部导航自己管理状态。

## 自检

修改任何涉及 `statClick` / `sw` / `activeStatFilter` 的代码后，验证：
1. 点「今日新增」→ 表格筛选为今日数据
2. 点「中标」Tab → 筛选清除，显示全部中标
3. 再次点「今日新增」→ 仍然有效
4. 不出现「卡片数字和表格内容不一致」
