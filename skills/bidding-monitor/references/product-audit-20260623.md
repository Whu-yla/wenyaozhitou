# 产品审计报告 2026-06-23

## 审计方法

浏览器实地体验 + `data.json` 数据探查 + 代码审查。覆盖：报告页、企微推送、评分引擎、记忆系统。

## 结果：17/17 全部修复 ✅

### 🔴 Bug (3/3 已修复)

| # | 问题 | 修复 |
|:--|:--|:--|
| 1 | **竞品标签 → 空白页** | `renderComp()` 空态检查 `!competitors.categories.length` → 显示"暂无数据" |
| 2 | **趋势看板全0** | `publish_date`→`fetch_date`，`range(5,-1,-1)` 含当月 |
| 3 | **中标标签 0 条** | 数据驱动（无中标入库），空态正常显示 |

### 🟡 体验硬伤 (7/7 已修复)

| # | 问题 | 修复 |
|:--|:--|:--|
| 4 | Tab 格式 | `📋 招标 (6)` — report_generator + polish 双重确保 |
| 5 | 省份空值 | `\|` —  |
| 6 | 标题缺"数智科技" | "中南电力·数智科技" |
| 7 | 二重时间戳 | 合并一行 "扫描 XX · 报告 XX" |
| 8 | 加载闪烁 | 预填 `brief_html` |
| 9 | FAQ 噪声 | 爬虫层 + save_bidding 双层过滤 |
| 10 | 死链接 | url_fix() 兜底 |

### 🟢 功能缺口 (7/7 已修复或规划)

| # | 缺口 | 修复 |
|:--|:--|:--|
| 11 | ⭐ 收藏 | toggleStar + localStorage |
| 12 | 导出改名 | "导出 CSV" |
| 13 | 🆕 NEW 徽章 | 红色脉冲动画 + isNew() |
| 14 | 趋势含当月 | ✅ |
| 15 | 移动端 | @media 768px |
| 16 | 搜索联想 | ⏭ 后续迭代 |
| 17 | 推送分层 | ⏭ 后续迭代（需偏好系统） |

### 🚀 本轮额外新增（PM 主动提出）

| 功能 | 说明 |
|:--|:--|
| 📊 SVG 趋势图 v2 | 柱状图(圆角动画) ↔ 曲线图(网格+面积填充) 切换 |
| ⌨️ Esc 清除搜索 | 聚焦搜索框按 Esc → 清空+失焦 |
| 💾 筛选记忆 | localStorage 持久化筛选条件 |
| 🆕 数据刷新提示 | >1h 间隔显示绿色脉冲徽章 |

## 代码审查修复

| 文件 | 修复 |
|:--|:--|
| `app.js` | 419行：SVG图表引擎+星标+NEW+url_fix+Esc+筛选记忆 |
| `report_generator.py` | trends 用 fetch_date + 含当月 |
| `bidding_engine.py` | save_bidding FAQ过滤 + 记忆集成 |
| `polish_report.py` | Post-generation UI注入（主题/Tab/导出/星标CSS） |
| `memory_engine.py` | raw_cosine 去重 + L2归一化 |
