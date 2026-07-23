# 统计卡片独立视图模式 — V1.31

> 2026-06-26：用户反馈「点高相关项目不应污染搜索框」→ 重构为独立 banner 模式

## 旧模式 ❌ (V1.17-V1.30)

点击统计卡片 → 直接修改筛选输入框的值 → 调用 doFilter() — **污染搜索/筛选状态**

```javascript
// ❌ 旧行为 — 污染筛选器
function statClick(type) {
    if (type === 'high') {
        document.getElementById('fScore').value = '70';  // 污染！
        doFilter();
    }
}
```

**问题**：
1. 搜索框/相关度输入被填入 "70" — 用户困惑
2. `updateStats()` 检测到 hasFilter=true → 所有统计卡片变为过滤后数字 — 全局视角丢失
3. 没有「我在看子集」的明确提示 — banner 缺失

## 新模式 ✅ (V1.31+)

点击统计卡片 → 设置 `activeStatFilter` → 渲染专属 banner → 统计卡片保持全局计数不变

```javascript
// ✅ 新行为 — 独立视图
let activeStatFilter = null;  // 'total'|'today'|'high'|'win'

function statClick(type) {
    if (activeStatFilter === type) {
        // 再点同一卡片 → 取消筛选
        activeStatFilter = null;
        renderStatBanner();
        resetF();
        return;
    }
    activeStatFilter = type;
    // ⛔ 不碰任何筛选输入框！
    // 高亮点击的卡片
    // sw() 切到对应 Tab
    renderStatBanner();
    doFilter();
}
```

## 三层联动

| 组件 | 行为 | 原因 |
|:--|:--|:--|
| **统计卡片** | 保持全局计数不变 | banner 已告知子集信息 |
| **筛选 banner** | 显示 `📊 高相关招标 · 12 条` + `✕ 显示全部` | 提供上下文和退出路径 |
| **Tab 徽标** | 反映实际过滤后数量 | 表格内容与徽标一致 |
| **搜索/筛选输入** | 清空、不污染 | 独立视图不干扰手动筛选 |

## getFilt() 修改

```javascript
function getFilt() {
    let d = tab === 'bid' ? [...allB] : [...allW];
    // Stat filter 优先于手动 filter
    if (activeStatFilter === 'high') d = d.filter(i => (i.relevance_score || 0) >= 70);
    if (activeStatFilter === 'today') d = d.filter(i => isNew(i));
    // 仅当无 stat filter 时 todayOnly 才生效
    if (todayOnly && !activeStatFilter) d = d.filter(i => isNew(i));
    // 手动筛选条件继续正常应用...
}
```

## updateStats() 分支

```javascript
function updateStats(data) {
    if (activeStatFilter) {
        // 统计卡片 → 全局计数（不变）
        // Tab 徽标 → 过滤后计数
        document.getElementById('statBidTotal').textContent = allB.length;  // 全局
        document.getElementById('cntBid').textContent = getFiltFor(allB).length; // 过滤后
        return;
    }
    // 普通筛选模式 → 全部联动
}
```

## Banner HTML/CSS

```html
<div id="statFilterBanner" class="stat-filter-banner" style="display:none"></div>
```

```css
.stat-filter-banner {
    max-width: 1400px; margin: 0 auto 8px; padding: 8px 24px;
    display: flex; align-items: center; justify-content: space-between;
    background: rgba(59,130,246,.1); border: 1px solid rgba(59,130,246,.2);
    border-radius: var(--radius); font-size: 13px; color: var(--accent);
    animation: slideIn .2s ease;
}
.stat-card.active {
    border-color: var(--accent);
    box-shadow: 0 0 0 1px var(--accent);
}
```

## resetF() 必须清除

```javascript
function resetF() {
    activeStatFilter = null;
    renderStatBanner();
    document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
    // ... 其他重置
}
```

## 自检清单

- [ ] 点高相关卡片 → banner 弹出，搜索框无 "70"
- [ ] 统计卡片数字不变（全局计数）
- [ ] Tab 徽标反映过滤后数量
- [ ] 点 ✕ 回到全量
- [ ] 再点同一卡片取消筛选
- [ ] 点不同卡片切换筛选
- [ ] 点「重置」清除 stat filter
- [ ] 手机端 banner 间距适配
