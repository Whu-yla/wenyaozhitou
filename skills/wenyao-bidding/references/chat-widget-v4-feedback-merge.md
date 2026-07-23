# Chat Widget v4 — 反馈合并 + 拖动

## 架构

```
chat-widget.js v4 (IIFE) — 单文件自包含
├── 对话模式 (chat-normal-area)
│   ├── 预设快捷问题（含 "📝 反馈问题" 橙色高亮按钮）
│   ├── 消息区 (chat-messages-v2)
│   └── 输入区 (chat-input-v2)
├── 反馈模式 (chat-fb-panel) — toggleFeedbackMode() 切换
│   ├── 文本域 (chat-fb-text)
│   ├── 提示文案
│   └── 提交/取消按钮
└── 拖动系统 — mousedown/mousemove/mouseup on #chatWidgetAll wrapper（折叠+展开都能拖）

## 关键函数

| 函数 | 用途 |
|:--|:--|
| `window.toggleFeedbackMode()` | 切换对话↔反馈模式，修改 fbBtn 样式为红色 |
| `window.submitChatFeedback()` | POST `/bidding/api/feedback` type=general |
| `window.openChat()` | 打开面板，重置 position 为 fixed bottom:20px right:20px |
| `window.closeChat()` | 关闭面板 |
| Drag handlers | wrapper全局 mousedown → mousemove移动 → mouseup释放。排除 button/input/textarea/a/.chat-preset-v2/img 防止误触；3px防抖死区防止点击误判为拖动；拖动后 suppress click 防止误开面板 |

## ⚠️ 拖动必须在两个状态都工作

用户明确要求：折叠的触发条和展开的面板都必须能拖动。

**错误实现（V1.26 初版）**：只监听 `#chatDragHandle`（展开面板头部）→ 折叠时拖不动
**正确实现**：监听 `#chatWidgetAll` wrapper 全局 `mousedown`，排除交互元素

```javascript
// ✅ 正确 — 全局监听，排除按钮/输入框/预设/图片
wrapperEl.addEventListener('mousedown', function(e) {
  if (e.target.closest('button, input, textarea, a, .chat-preset-v2, .chat-trigger img')) return;
  // ... start drag
});
```

## 反馈入口（3处）

1. **头部 📝 按钮** (`.chat-fb-btn`) — 右上角，蓝色圆形
2. **预设栏 "📝 反馈问题"** (`.chat-preset-fb`) — 橙色边框高亮
3. **欢迎消息提示** — "💡 发现数据有误？点击右上角 📝 直接反馈！"

## 与旧版（V1.25 独立反馈）的差异

| V1.25（独立） | V1.26（合并） |
|:--|:--|
| 独立悬浮按钮 fb-fab + 侧滑面板 fb-panel | 集成进 chat-widget，无独立 DOM |
| 右下角两个按钮碰撞（💬 + 🤖） | 仅 🤖 触发条 |
| polish_report.py 注入 FB CSS/HTML/JS | 仅注入 chat-widget CSS/JS |
| 固定不可移动 | 头部可拖动 |

## 样式类

```css
.chat-fb-btn          /* 头部反馈按钮 */
.chat-fb-panel        /* 反馈模式面板（flex column，与对话模式互斥） */
.chat-fb-body         /* 反馈面板主体 */
.chat-fb-text         /* 反馈文本域 */
.chat-fb-submit       /* 提交按钮（橙色渐变） */
.chat-fb-cancel       /* 取消按钮 */
.chat-preset-fb       /* 预设栏反馈入口（橙色边框高亮） */
```

## 验证命令

```bash
# 确认页面加载
curl -s https://www.yfzx.online/bidding/ | grep -c "chat-widget"
# 必须 ≥2（CSS + JS）

# 确认无旧 fb-fab
curl -s https://www.yfzx.online/bidding/ | grep -c "fb-fab"
# 必须 = 0

# 确认反馈 API 可用
curl -s -X POST https://www.yfzx.online/bidding/api/feedback \
  -H 'Content-Type: application/json' \
  -d '{"type":"general","reason":"测试"}'
# 预期：{"ok": true, "entry": {...}}
```
