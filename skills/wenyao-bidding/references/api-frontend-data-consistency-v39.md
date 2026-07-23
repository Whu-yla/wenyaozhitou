# API 前端数据一致性修复 — V1.39-V1.40

## 问题1: API items 端点 score=0 噪音混入 (V1.39)

**症状**：前端表格展示 157 条招标（含 63 条 score=0 噪音），统计卡片显示 94 条——数字打架。

**根因**：`bookmark_server.py` `query_items()` 默认 `min_score=0`，L1 判别器拒绝的浙能施工/监理/保险类项目全量返回。

**修复**：
```python
# bookmark_server.py query_items()
- min_score = float(params.get('min_score', ['0'])[0])
+ min_score = float(params.get('min_score', ['1'])[0])  # 默认排除0分噪音
```

**中标查询崩溃**：`winning_notices` 表无 `notice_type` 列，查询 500。
```python
if table == 'winning_notices':
    cols = cols.replace('notice_type', "'winning' as notice_type")
```

## 问题2: 统计卡片跨Tab计数不一致 (V1.39)

**症状**：点击「高相关项目 26」→ 累计招标=21（正确），累计中标=13（错误，应为 5 条高分中标）。

**根因**：`apiFilter()` 只查当前 Tab（type=bidding），`totalWinning` 未更新。`updateApiStats()` 无脑用两个全局变量覆盖四张卡片。

**修复**：`activeStatFilter` 激活时额外 fetch 另一 Tab 的 filtered total：
```javascript
if (activeStatFilter) {
    const otherType = tab === 'bid' ? 'winning' : 'bidding';
    const otherParams = new URLSearchParams(params);
    otherParams.set('type', otherType);
    otherParams.set('size', '0');
    const or = await fetch('/bidding/api/items?' + otherParams.toString());
    const od = await or.json();
    if (od.ok) {
        if (otherType === 'bidding') totalBidding = od.total;
        else totalWinning = od.total;
    }
}
```

## 问题3: API 迁移 UI 组件回归四件套 (V1.39)

前端切到 API 模式 `renderTable()` 后，四个组件静默丢失：

| 组件 | 原因 | 修复 |
|:--|:--|:--|
| 🔝 回到顶部按钮 | `init()` 未创建 `btnBackTop` | 在 `init()` 中动态创建 + scroll 监听 |
| 📄 页码按钮 « ‹ N › » | `renderTable()` 未调用 `renderPg()` | 补 `renderPg('pgNums', pg, totalPages)` |
| 📊 页码信息卡死 | `.pg-info` class → HTML 用 `pgInfo` ID | 改用 `getElementById('pgInfo')`/`getElementById('pgInfoW')` |
| ⭐ ⋯ 收藏+Kebab | 星独立列、kebab 完全不渲染 | 星移入 title-cell 左侧 + kebab JS条件渲染 + 补回操作列 |

**关键教训**：`renderTable` 是 API 模式专用渲染路径。任何在旧 `doFilter()` 中的 UI 功能都需要在此函数中重新实现。**绝对不能用 `document.querySelectorAll('.pg-info')` 去匹配 `id="pgInfo"` 的元素**——class 和 ID 选择器是不同的。

## 问题4: 移动端筛选按钮错 target (V1.39)

**症状**：手机点「☰ 筛选」→ 筛选栏直接消失。

**根因**：toggle handler 操作了 `.filter-bar` 的 `display`，而不是 toggle `.filter-scroll-wrapper` 的 `.expanded` class。筛选项（相关度、日期、金额）在 `.filter-scroll-wrapper` 里，移动端该容器默认 `display:none`。

**修复**：
```javascript
const expanded = wrapper.classList.toggle('expanded');
filterToggleBtn.textContent = expanded ? '✕ 关闭' : '☰ 筛选';
filterToggleBtn.classList.toggle('active', expanded);
```

## 问题5: 收藏 Tab 无反应 — starOnly 被 API 路径忽略 (V1.40)

**症状**：点「收藏」Tab → 表格仍显示全部招标，未过滤。

**根因**：`sw('star')` 设置 `starOnly = true`，但 `apiFilter()` 完全不知道这个标志。`starOnly` 只在 `doFilter()` 的旧路径中被使用。API 模式 fetch 全部 bidding items，不做收藏过滤。

**修复**：在 `apiFilter()` 获取 API 响应后添加客户端收藏过滤：
```javascript
if (starOnly) {
    const starIds = new Set(getStars());
    if (tab === 'bid') {
        allB = allB.filter(i => starIds.has(String(i.id)));
        totalBidding = allB.length;
    } else {
        allW = allW.filter(i => starIds.has(String(i.id)));
        totalWinning = allW.length;
    }
}
```

**连锁 bug**：`renderTable(d.data, d.total)` 用了原始 API 数据 `d.data`，而不是 star 过滤后的 `allB/allW`。修复后 `renderTable` 改为使用 `tab === 'bid' ? allB : allW` 和对应的 `totalBidding/totalWinning`。

## 问题6: renderTable 使用原始数据而非过滤后全局变量 (V1.40)

**症状**：starOnly 过滤后 `totalBidding=1` 但表格仍显示 20 行。

**根因**：`renderTable(d.data, d.total)` — `d.data` 是 API 原始返回（20 条未过滤），`d.total` 是 API 原始 total（94）。

**修复**：
```javascript
- renderTable(d.data, d.total);
+ const renderData = tab === 'bid' ? allB : allW;
+ const renderTotal = tab === 'bid' ? totalBidding : totalWinning;
+ renderTable(renderData, renderTotal);
```

**铁律**：`apiFilter()` 中任何对 `allB/allW/totalBidding/totalWinning` 的客户端后处理（starOnly 过滤、统计卡片筛选等）必须在 `renderTable()` 调用前完成，且 `renderTable` 必须使用处理后的全局变量而非原始 `d.data/d.total`。

## API 迁移完整检查清单

每次修改 `renderTable()` 或 `apiFilter()` 后验证：

- [ ] 表格行渲染
- [ ] 页码信息（**用 ID 选择器！不是 class！**）
- [ ] 页码按钮 `renderPg()`
- [ ] 每页选择器 `renderPsSelector()`
- [ ] 回到顶部按钮 `btnBackTop`
- [ ] 统计卡片更新（含跨 Tab 计数）
- [ ] 收藏星在 title-cell 左侧
- [ ] Kebab 省略号（手机端 `innerWidth <= 768` 条件渲染）
- [ ] 操作列「查看」链接
- [ ] ⭐ **收藏 Tab 过滤** — starOnly 客户端后处理
- [ ] ⭐ **renderTable 使用过滤后数据** — 不是原始 d.data
- [ ] ☰ 筛选按钮 toggle `.filter-scroll-wrapper.expanded`（不是 `.filter-bar`）
