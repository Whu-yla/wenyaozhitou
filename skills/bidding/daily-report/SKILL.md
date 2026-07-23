---
name: daily-report
description: 文鳐智投每日分析报告 — 每日 20:00 生成招标/中标 AI 分析报告并推送企微，含点赞/点踩反馈闭环
category: bidding
---

# 每日分析报告

## 架构

```
cron 20:00 → push_daily_report.sh → daily_report.py → report-{date}.html → 企微推送链接
                               ↓
                          feedback.json ← 用户 👍/👎 ← bookmark_server.py :8090
                               ↓
                          HOT_MEMORY.md → AI 下次会话自动感知 → auto-feedback-fix
```

## 文件清单

| 文件 | 作用 |
|:--|:--|
| `scripts/daily_report.py` | 主生成器 — 读DB+书签 → 逐条AI分析 → 输出HTML |
| `scripts/push_daily_report.sh` | Shell包装 — 调用daily_report.py → 企微webhook推送链接 |
| `scripts/bookmark_server.py` | API微服务(:8090) — 书签同步 + 反馈收集 |
| `/var/www/html/bidding/report-{date}.html` | 日报HTML输出 |
| `/var/www/html/bidding/data/feedback.json` | 反馈记录 |
| `/var/www/html/bidding/data/bookmarks.json` | 服务端书签 |

## 日报HTML功能

### 双Tab切换
- 📋 招标情况报告 / 🏆 中标情况报告
- 上方滑动按钮切换

### 招标卡片（每条）
- 标题（可点击跳转原始页面）
- 招标单位 / 地区 / 预算 / 发布日期 / 来源
- AI分析：匹配度评估 + 建议理由
- 建议等级：🔴重点关注 / 🟡可投标 / 🟠可关注 / ⚪暂不考虑
- ⭐ 收藏标记（书签联动）
- 👍 赞同 / 👎 不认同 按钮

### 中标卡片（每条）
- 标题 + 中标单位 + 招标单位 + 金额
- 竞品分析：本公司中标✅ / 竞品中标⚠️ / 非竞品
- 大标≥500万 💰 自动标记
- ⭐ 收藏提醒

### 反馈系统
- 点赞 → POST /bidding/api/feedback → feedback.json
- 点踩 → 弹出评论框 → 理由写入 feedback.json + HOT_MEMORY.md
- localStorage 记录提交状态，刷新不丢失

### 主题
- 默认明亮风格（白底蓝调）
- ☀️/🌙 按钮切换，localStorage 持久化

## ⚠️ 铁律

1. 无数据时静默跳过不推送
2. 报告文件必须 chmod 644
3. 反馈数据变更后 → **立即重建日报**（`python3 scripts/daily_report.py`）
4. 标题/建议/分析文案来自 `analyze_bidding()` / `analyze_winning()` 规则引擎
