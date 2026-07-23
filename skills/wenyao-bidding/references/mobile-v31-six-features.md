# 手机端 V1.31 六大功能

## 1. 下拉刷新
- HTML: `<div id="pullIndicator">↓ 下拉刷新</div>` 在 body 最顶部
- CSS: `position:fixed;top:0;transform:translateY(-100%)`。`.show` → `translateY(0)`。`.ready` → 变色+"✓ 释放刷新"
- JS: touchstart(仅scrollY≤5) → touchmove(dy>20显示/dy>80就绪) → touchend(ready时调用init())
- 仅移动端触发（touch事件天然限移动端）

## 2. 日期快捷
- HTML: 3个 `<button class="date-preset">` 在日期范围输入框后
- JS: `setDatePreset('today'|'week'|'month')` → 计算日期格式化 `YYYY-MM-DD` → 设置 dateFrom/dateTo → `doFilter()`
- 本周：周一(dow校正，周日=0→周一=上周日+1)到周日
- 本月：new Date(y,m,1) 到 new Date(y,m+1,0)

## 3. 长按标题看全文
- 触发：`touchstart` on `.title-cell` → 600ms setTimeout → 弹出 `.title-tooltip` 浮层
- 前提：仅 `window.innerWidth <= 768` 且标题长度 ≥ 40 字符
- 浮层：`position:fixed;left:16px;right:16px;bottom:50%` 深色底白字（暗色模式反转）
- 2.5秒自动消失 + click/move 取消
- 注意：`touchend`/`touchmove` 必须 `clearTimeout(timer)`

## 4. 一键分享
- JS: `navigator.share({title, url})` 优先 → `navigator.clipboard.writeText(url)` fallback
- 图标：`<span class="share-btn">↗</span>` 在标题前（opacity:0.5，:active→1）
- onclick: `event.stopPropagation()` 防止触发卡片跳转
- 模板注入：`const shareIcon = \`<span class="share-btn" onclick="...shareItem(${i.id},'${title}','${link}')">↗</span>\``

## 5. 已读/未读
- 存储：localStorage key `bidding_read` = JSON array of item IDs
- 标记：卡片 onclick 手机端时 `markRead(id); this.classList.add('read')`
- 恢复：渲染时 `isRead(id)` → 加 `class="read"` → `tr.data-row.read{opacity:.65}`
- 事件委托：`document.addEventListener('click')` 监听 `tr.data-row` 点击（仅 `innerWidth<=768`）
- 辅助函数：`getReadItems()`, `markRead(id)`, `isRead(id)`

## 6. 搜索智能建议
- 函数：`smartEmptyMsg(query, dataCount)`
- 规则：
  - `!query` → "没有匹配的结果，请调整筛选条件"
  - `query.length <= 2` → "关键词太短，试试更具体的词"
  - 其他 → "没找到相关结果 · 尝试缩短关键词或扩大日期范围"
- 调用：`doFilter()` 空结果时 `smartEmptyMsg(q, data.length)` 替换固定文案
- 仅影响招标表空状态（中标表有独立文案"暂无中标数据"）

## 关键实现细节
- 所有 touch 事件监听器用 `{passive:true}`（除 touchend）
- 分享图标的 `title` 需用 `esc()` + `replace(/'/g,"\\'")` 防 JS 字符串断裂
- 已读状态不影响桌面端（桌面端点击展开详情不标记已读）
- 搜索建议在收藏模式下不触发（有独立引导文案）
