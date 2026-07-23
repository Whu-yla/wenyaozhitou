# Chat Widget 拖动规范 v5 (V1.35)

## 核心变更

用户明确反馈三个问题：
1. 「框内不能拖，框内是为了阅读」→ 仅头部标题栏可拖，内容区不可拖
2. 「移动框，背景也在上下滑动」→ touchmove 缺 `preventDefault()`
3. 「收起来的图标拖不动了」→ 收起态 `#chatTrigger` 也要可拖

## 实现规范

### 1. 拖动触发区域 — 双元素

```js
// ✅ 正确：头部 + 收起态图标都可拖
const dragHandle = document.getElementById('chatDragHandle');
const dragTrigger = document.getElementById('chatTrigger');
if (dragHandle) dragHandle.addEventListener('mousedown', onStart);
if (dragTrigger) dragTrigger.addEventListener('mousedown', onStart);
// touch 同理

// ❌ 错误1：整个 wrapper 可拖（内容区也被拖走）
wrapperEl.addEventListener('mousedown', onStart);
// ❌ 错误2：只有 chatDragHandle 可拖（收起态图标拖不动）
```

### 2. 拖动排除规则

```js
function onStart(e) {
    // 排除交互元素：按钮、输入框、链接
    // 但 Logo <img> 可拖（它是头部装饰，不是交互控件）
    if (e.target.closest('button, input, textarea, a')) return;
    // ...
}
```

⚠️ 不要排除 `img` — 头部 Logo 点按应该也能拖动面板。  
⚠️ `#chatTrigger` 有 `onclick="window.openChat()"` — 拖动/点击由 `hasMoved` 标志区分：拖动了 → 阻止 click；纯点击 → 打开面板。

### 3. 阻止背景页面滚动

```js
function onMove(e) {
    if (!dragging) return;
    const dx = pos.x - startX, dy = pos.y - startY;
    if (Math.abs(dx) < 3 && Math.abs(dy) < 3) return;  // 3px 防抖
    hasMoved = true;
    e.preventDefault();  // ← 关键！防止背景页面跟随滚动
    wrapperEl.style.left = (origLeft + dx) + 'px';
    wrapperEl.style.top = (origTop + dy) + 'px';
}
```

### 4. 完整架构

```
chat-widget.js initDrag():
├── mousedown on #chatDragHandle + #chatTrigger (桌面)
├── touchstart on #chatDragHandle + #chatTrigger {passive:false} (手机)
├── mousemove/touchmove on document {passive:false}
├── mouseup/touchend on document
└── click suppress on wrapper (拖动后防止误触发打开/关闭)
```

### 5. 已知陷阱

| 陷阱 | 症状 | 修复 |
|:--|:--|:--|
| wrapper 全局监听 | 框内阅读时手指一滑就拖动 | 改为 `#chatDragHandle` + `#chatTrigger` |
| 缺 `e.preventDefault()` | 拖框时背景页面跟着滚 | 在 hasMoved=true 后加 preventDefault |
| `img` 在排除列表 | 点 Logo 不触发拖动 | 排除列表去掉 `img` |
| 未设 `{passive:false}` | iOS 上 preventDefault 无效 | touchstart + touchmove 都设 passive:false |
| `webkitUserSelect` 缺失 | iOS 拖动时选中文字 | onStart 设 `none`，onEnd 恢复 |
| 只监听 chatDragHandle | 收起态图标拖不动 | 同时监听 `#chatDragHandle` + `#chatTrigger` |

## 相关文件

- 实现：`/var/www/html/bidding/chat-widget.js` → `initDrag()` 函数
- 样式：`/var/www/html/bidding/chat-widget.css` → `#chatDragHandle` 含 `cursor:grab`
