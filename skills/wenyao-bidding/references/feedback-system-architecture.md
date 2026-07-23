# 用户反馈系统架构 (V1.25 — 已被 V1.26 替代)

> ⚠️ **V1.26 已重写反馈系统**：独立悬浮按钮 + 侧滑面板已废除，反馈入口合并进 chat-widget v4。
> 新架构见 `references/chat-widget-v4-feedback-merge.md`。
> 本文档保留作为历史参考。

## 触发
用户质问：「难道不能有一个提交反馈的地方吗？是不是应该要有一个醒目的提交用户反馈的地方？」

## 架构全景

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (index.html)                      │
│  ┌──────────┐    ┌──────────────────────────────────┐   │
│  │ 💬 悬浮按钮│───▶│ 侧滑面板 (400px)                    │   │
│  │ 右下角固定 │    │ • textarea 反馈内容                  │   │
│  │ z-index:9999│   │ • hint "AI凌晨自检修复"              │   │
│  └──────────┘    │ • 提交/取消按钮                       │   │
│                  └───────────┬──────────────────────┘   │
│                              │ fetch POST                │
└──────────────────────────────┼──────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────┐
│            bookmark_server.py :8090                       │
│  POST /feedback {type:"general", reason:"..."}           │
│  → handle_post_feedback()                                │
│    → 写入 data/feedback.json                             │
│    → 写入 HOT_MEMORY.md（供下次会话感知）                  │
└──────────────────────┬───────────────────────────────────┘
                       │ 文件系统
                       ▼
┌──────────────────────────────────────────────────────────┐
│  凌晨 3:00 自检                                           │
│  selfheal_3am.py                                         │
│  → 读取 feedback.json                                    │
│  → 聚类分析 + 根因匹配                                    │
│  → 自动修复（评分调整/脏数据清理/适配器修补）               │
│  → 写入 HOT_MEMORY.md                                    │
└──────────────────────────────────────────────────────────┘
```

## 组件清单

### 前端三件套

| 文件 | 注入位置 | 注入方式 |
|:--|:--|:--|
| CSS | `index.html` `<style>` 内 `@keyframes slideIn` 前 | `polish_report.py` 字符串替换 |
| HTML | `index.html` `<script src="app.js">` 前 | `polish_report.py` 字符串替换 |
| JS | `app.js` 末尾 `// FEEDBACK_JS_MARKER` | `polish_report.py` 字符串替换 |

### CSS 要点
- `.fb-fab` — 固定右下角 52×52 圆形蓝色按钮，hover 放大 1.1×
- `.fb-panel` — fixed right:-420px → open → right:0，transition .3s cubic-bezier
- `.fb-overlay` — 全屏半透明遮罩，opacity:0 → show → 1
- 暗/亮双主题：`body.light .fb-*` 覆盖 key 属性
- 移动端：`.fb-panel{width:100vw;right:-100vw}`

### JS 函数
- `toggleFeedback()` — 打开/关闭面板 + 遮罩 + body overflow
- `submitFeedback()` — fetch POST → showFbToast → 关闭面板
- `showFbToast(msg, type)` — 底部居中 toast，3 秒自动消失

### API 变更
`bookmark_server.py` `handle_post_feedback` 新增 `type='general'`:
- `type='general'` → `item_id` 默认 `'general'`，不限频
- `type='like'/'dislike'` → 原有逻辑不变，IP 去重
- 通用反馈和点踩都写入 HOT_MEMORY.md

## 持久化保障

`polish_report.py` 第 4 步注入，幂等检查：
```python
if 'fb-fab' not in html:
    # 首次注入 CSS + HTML + JS
else:
    # 检查 JS 是否被重新生成剥离
    if 'function toggleFeedback()' not in html:
        # 重新注入 JS
```

**验证命令**：
```bash
# 确认反馈组件存在
curl -s https://www.yfzx.online/bidding/ | grep -c fb-fab  # ≥1
curl -s https://www.yfzx.online/bidding/ | grep -c toggleFeedback  # ≥1
# 测试提交
curl -s -X POST https://www.yfzx.online/bidding/api/feedback \
  -H 'Content-Type: application/json' \
  -d '{"type":"general","reason":"测试"}'
# → {"ok": true, "entry": {...}}
```

## 设计原则

1. **醒目但不侵略** — 悬浮按钮固定在右下角，不干扰阅读
2. **降低提交门槛** — 无 item_id 要求，不限频，随便写
3. **闭环自愈** — 提交 → HOT记忆 → 凌晨自检 → 自动修复
4. **双主题适配** — 暗/亮 theme 均需测试
5. **持久化** — 报告重新生成不丢失，polish 幂等注入
