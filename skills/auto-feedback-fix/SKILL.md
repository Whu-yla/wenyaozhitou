---
name: auto-feedback-fix
description: 文鳐智投反馈自动修复流程 — 用户点赞/点踩后自动诊断并修复
category: bidding
---

# 反馈自动修复流程

## 触发条件
**任何时刻**，只要发现以下信号之一就立即触发（不等用户催）：
1. 用户问"收到反馈了吗"/"有反馈吗"/"反馈"
2. 会话开始时检查 `/var/www/html/bidding/data/feedback.json`
3. 看到 HOT_MEMORY.md 中有未处理的反馈标记

⚠️ **铁律**：触发后立刻切到修复模式，不要只回复"收到了X条反馈"就停住。用户期望你自动修，不是报数。

## 🚨 最常犯的错误
- ❌ 用户问"收到反馈了吗" → 只回复"收到了3条"就停 → 用户暴怒
- ❌ 用户说"修系统" → 只修了数据单条，没追根因 → 用户暴怒
- ❌ **修了数据没展示结果** → 不重生成日报/不 push 企微 → 用户看不到 → 等于没修
- ✅ 正确做法：收到反馈 → 立刻诊断 → 立刻修 → 追根因修系统 → 回填 → 日报 → changelog → 主动报告"全修完了"

## ⛔ 用户暴怒信号（出现任何一条 = 你已经犯了致命错误）
- "我不是让你收到反馈后自己就开始修复吗？！"
- "你动起来啊！！！"
- "你的记忆呢！？？？？"
- "每一个反馈你都要思考自己哪里做的不好！自查问题，不要反复出现！"
- **"我是什么意见！"** → 你只修了表面没追根因
- **"这些修的内容都存数据库啊，别只是改静态的HTML！"** → 你没持久化数据
→ 出现这些信号 = 你停了 / 没追根因 / 没自动动 / 没持久化。立刻加载本 skill，从头开始完整修复。

## 修复流程

### Step 1: 诊断
- 读取每条未处理反馈的 `item_id`、`type`、`reason`
- 从数据库查询对应项目（bidding_notices 或 winning_notices）
- 对比 `reason` 中的问题和数据库实际字段值

### Step 2: 分类 + 根因分析 ⚠️ 最常漏的步骤

**⛔ 铁律：修单条数据 ≠ 修系统。每个反馈必须追到根因。**

| 反馈类型 | 修复方向 | **必须追问的根因** |
|:--|:--|:--|
| "XX没抓出来"/"数据缺失" | 修复提取逻辑 | regex 是否覆盖所有格式变体？为什么 raw_html 为空？ |
| "与业务不匹配" | 调整关键词权重 | 为什么这条标能得高分？哪个关键词误匹配？ |
| "评分不准"/"分类错误" | 调整评分引擎规则 | 是否有其他同类错误？需要批量回填多少条？ |
| "链接打不开" | 检查URL | 是链接真死还是过期页面？是否需要日期衰减？ |
| "建议应该关注XX" | 扩展关键词 | 缺的是哪种格式/同义词？能否覆盖未来同类？ |

**根因分析模板**：
1. 这条反馈暴露了什么系统缺陷？
2. 同类缺陷影响了多少条其他数据？
3. 修复后能否防止未来同类问题？

### Step 3: 修复（双轨：单条回填 + 系统修复）
1. **单条回填**：定位缺失数据 → 从原始URL提取 → UPDATE 单条
2. **系统修复**：定位源码缺陷 → 改代码 → 验证 → **批量回填所有受影响数据**
3. 清理 HOT_MEMORY.md 中已处理的反馈标记
4. **重生成日报**：`python3 scripts/daily_report.py`
5. **主动告知用户**：列出"修了哪几条 + 修了什么系统缺陷 + 日报已更新"

### Step 4: 闭环
1. 在对话中报告修复结果
2. **立即写入 changelog.html**（新版本号，列出所有改动）
3. 如果是关键词调整 → 更新记忆中的评分规则
4. 如果是提取逻辑修复 → 更新对应 adapter skill

## 铁律（2026-06-24 强化）

⚠️ **收到反馈 → 立即加载本 skill → 诊断 → 系统根因分析 → 修代码+修数据 → 批量回填 → 重生成日报 → 更新changelog → 主动报告**

**8步闭环，缺一不可。** 最致命错误：
1. ❌ 只回复"收到了X条反馈"就停住 → 用户暴怒  
2. ❌ 修了单条数据就以为完成 → **每个反馈必须追到系统根因**（为什么 regex 没匹配？为什么 raw_html 为空？为什么旧标100分？）
3. ❌ 修完不重生成日报 → 用户看不到数据变化
4. ❌ 修完不更新 changelog → 等于没做

**今天新增的系统根因 checklist**（每次修反馈必须对照）：
- [ ] 预算缺失 → `extract_budget_from_content()` regex 是否覆盖该平台格式？raw_html 是否保存了？
- [ ] 招标人/地区缺失 → `_extract_region_owner()` 是否在评分时调用了？南网"招标人为 XXX"无冒号格式？
- [ ] 过期旧标高分 → 日期衰减是否生效？`relevance_scorer.score_item()` 衰减逻辑？
- [ ] 同类数据有多少条受影响？→ 必须 `SELECT COUNT` + 批量 `UPDATE` 回填
- [ ] **数据是否真正入库了？** → 修改后必须 `SELECT` 验证 SQLite 字段值，不能只看日志输出
- [ ] **日报是否重生了？** → `python3 scripts/daily_report.py` 确认输出 `(N招标+M中标)`
- [ ] **企微推送是否发了？** → `python3 scripts/wecom_push.py` 确认有状态简报

## 新增常见根因模式（2026-06-25）

### 预算提取陷阱
- **南网 "最高投标限价（万元）"**：HTML 表格跨 `<td>` 格式，regex 必须跨标签匹配
  → 正解: `r'最高(?:投标)?限价[^<]*?</td>\s*<td[^>]*>\s*(\d+\.?\d*)'`
- **CSS 误抓**：`font-size:10.5pt` / `border-width:0.67px` 被当成金额
  → 必须过滤 `<1.0` 的值和 `10.5` 这样的固定字体值
- **raw_html 为空**：南网适配器没保存 raw_html，无法回溯提取 → 修复适配器

### 招标人提取陷阱
- 南网格式："招标人为 南方电网科学研究院有限责任公司"（无冒号）
  → BIDDER_PATTERNS 需加 `[：:为是]` 而非仅 `[：:]`

### 日期衰减
- 2年前旧标 100 分排第一 → 用户"看不懂为什么排这"
  → `score_item()` 强制衰减: >2年×0.3, >1年×0.5, >6月×0.7

### 沉默推送
- 今日无新增→不发→用户以为什么都没跑
  → 必须发状态简报："系统正常，今日无新增，累计N条"

### Hermes Cron 3分钟硬中断
- 任何 Hermes cron（含 no_agent）超3分钟必杀
  → 长任务必须用 systemd timer: `TimeoutStopSec=7200`

## 关键文件
- 反馈源: `/var/www/html/bidding/data/feedback.json`
- HOT记忆: `/root/.hermes/profiles/wenyaozhitou/memory/hot/HOT_MEMORY.md`
- 数据库: `/root/.hermes/profiles/wenyaozhitou/data/bidding.db`
- 预算提取模式库: `references/budget-extraction-patterns.md` ← 南网/国能/浙能格式 + 误抓陷阱
- 评分引擎: `scripts/relevance_scorer.py` (含 v11 日期衰减 + `_extract_region_owner()`)
- 采集管线: `scripts/crawl_pipeline.py` (含 `extract_budget_from_content()`)
- 日报生成: `scripts/daily_report.py` → 输出 `/var/www/html/bidding/report-{date}.html`
- 凌晨自检: `scripts/selfheal_3am.py` → systemd timer `wenyao-selfheal`

## 已知修复案例 (供参考)
- **中标人缺失（Item 8）**: adapter_guoneng.py 未提取 winner_company → 新增 `_extract_from_table()` HTML表格跨行解析
- **预算金额缺失（Item 273）**: bidding_notices 无 budget_amount 列 → 加列 + `extract_budget_from_content()` regex + 管线自动填充
