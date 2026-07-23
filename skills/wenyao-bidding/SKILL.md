---
name: wenyao-bidding
description: 文鳐智投投标监控系统全生命周期 — 评分引擎校准、站点扫描、报告生成、企微推送、前端交互、文件操作安全规则。
triggers:
  - 评分引擎
  - relevance_scorer
  - score_item
  - bidding_engine
  - 扫描
  - report_generator
  - 报告
  - app.js
  - wecom_push
  - 企微推送
  - polish_report
  - 项目推进卡片
  - 文鳐
  - wenyao
  - 技术规范书
  - 投标文档分析
  - 招标文件
  - 中标情况查询
---

## 投标文档分析

用户发送招标技术规范书（.doc/.docx/.pdf）时，执行四阶段分析工作流：
文档提取 → 数据库相似项目查询 → 公开信息搜索 → 结构化分析报告。

完整 SOP 见 `references/bid-document-analysis-workflow.md`。

**DB 路径**：`/root/.hermes/profiles/wenyaozhitou/data/bidding.db`（不是 `/var/www/html/bidding/data/bidding.db`，后者是 0 字节空文件）。

# 文鳐智投投标监控系统

## 子技能

| 技能 | 触发条件 |
|:--|:--|
| `auto-feedback-fix` | 用户点踩/点赞后自动诊断修复 → 5步闭环 |
| `bidding-monitor` | 评分引擎 v10 详细定义、站点适配器规范 |

## 投标文档分析

用户上传技术规范书/招标文件（.doc/.docx）时，执行投标机会深度分析。完整工作流见 `references/bid-document-analysis.md`，涵盖：
- .doc 文档提取（catdoc）
- 竞争分析数据库查询（中标+招标双库搜索）
- 报告结构模板（项目速览→匹配度→SWOT→风险→行动清单）
- 匹配度评分标准 + 风险等级定义

## OpenCode 自主编码代理

大型重构/新功能开发使用 OpenCode + DeepSeek，日常小修仍用 Hermes 原生工具。配置详见 `references/opencode-deepseek-setup.md`。

便捷命令：`opencode-ds run "任务描述" --model deepseek/deepseek-chat`

## ⛔ V1.0 稳定版 — 生产/测试双环境（2026-06-26 铁律）

**用户明确要求：当前版本冻结为 V1.0 稳定版。以后所有改动先在测试环境验证，确认无误再发布到生产。**

**🚫 生产环境锁定**：未经用户明确「推到生产」命令，绝不改动 `/var/www/html/bidding/` 下任何文件。铁律。

| 环境 | URL | 路径 | 说明 |
|:-----|:-----|:-----|:-----|
| 🟢 **生产** | `yfzx.online/bidding/` | `/var/www/html/bidding/` | 不可直接改动 |
| 🟡 **测试** | `yfzx.online/bidding-test/` | `/var/www/html/bidding-test/` | 随便改 |
| 🔗 data.json | 软链接共享 | 测试→生产共用 | 数据一致 |

**测试环境特征**：页面标题 `🧪 测试环境 · 文鳐智投`，header 橙色 `测试` 徽章。独立文件目录但共享 data.json（软链接）。

**部署铁律**：`改动 → 测试环境 → 验证通过 → promote.sh → 生产环境`。**永不直接改生产文件。**

**发布命令**：`bash scripts/promote.sh`（备份→同步→去掉测试标记→chmod→完成）

---

## 全新挂载技能后以及重大改动后必须自查

**⛔ 铁律（2026-06-25 — 用户明确要求）**：系统开发者的责任是**主动自查**，不等用户逐项指出bug。每次重大改动后，执行 `references/system-audit-checklist.md` 中的 7 项全链路检查。**用户第一次说"修bug"时必须主动跑全链路审计，不等用户指出具体问题。**

**用户连续说"还有BUG"时的正确响应（致命教训 2026-06-25）**：
- ❌ 错误做法：说"已修复全部bug"然后等用户指出下一个
- ✅ 正确做法：**立即打开浏览器实际渲染页面**（`browser_navigate`），不只是 curl 检查。curl 发现不了 async JS 渲染失败、DOMParser 报错、CSS 布局崩坏
- **每轮自查必须包含浏览器渲染验证**：打开监控页 → 等 3 秒 → 检查表格行数、筛选器选项、chat-widget DOM

**触发条件**：评分引擎改动、爬虫调整、Nginx变更、前端组件添加 → 自动跑审计。

**典型漏检bug（历史教训）：**
- ⛔ **DOM元素ID不匹配导致 init() 静默崩溃（2026-06-26 致命坑）：app.js 升级后引用新 DOM 元素 `lastUpdate`，但 index.html 模板未同步更新（仍为静态文本「系统运行中」）→ `document.getElementById('lastUpdate')` 返回 null → TypeError → init() 中断 → doFilter() 永不执行 → 全页显示0条。curl 全部 200 正常、data.json 可访问，唯浏览器渲染发现。修复：①index.html 添加 `id="lastUpdate"` 元素 ②app.js 所有 DOM 引用加防御性 null 检查 `const el = document.getElementById('id'); if (el) el.xxx` ③polish_report.py 双阶段注入：Stage1 检测旧模板「系统运行中」替换为 lastUpdate span，Stage2 在 lastUpdate 存在时注入密度按钮 ④report_generator.py 模板源同步更新。详见 `references/dom-element-mismatch-crash.md`。
- ⛔ **筛选栏多行错乱 → display:contents 修复（2026-06-26）：V1.33 移动端设计引入 `.search-row` + 两个 `.filter-row` 结构，桌面端未合并导致 3 行堆叠。修复：`@media(min-width:769px)` 中 `.filter-row` 设 `display:contents` 将子元素提升到父级 flex 流 + `.filter-bar` 设 `flex-wrap:nowrap` + 隐藏内部 spacer。仅用 CSS，不改 HTML 结构。详见 `references/filter-bar-display-contents-fix.md`。**
- ⛔ **搜索框按钮分离+图标不对齐（2026-06-26）：input 和 button 是独立块元素，各自占行 → 按钮不贴输入框；🔍 图标 top:50% 参考系是 .search-box（含 button）而非 input → 垂直偏移。修复：`.search-box{display:flex}` 并排 input+button，input `border-radius:6px 0 0 6px`，button `border-radius:0 6px 6px 0;border-left:none;background:accent` 形成一体胶囊，icon `top:50%;translateY(-50%)` 在 flex align-items:center 容器内精确定位。详见 `references/search-box-pill-pattern-v35.md`。**
- ⛔ **移动端卡片+滚动回归（2026-06-26）：用户反馈「卡片风格和右滑都没有了」。根因：移动端 CSS 长期缺失——①`tr.data-row{display:grid}` 卡片 Grid 布局从未注入 ②`.filter-scroll-wrapper{overflow:hidden!important}` 锁死滚动（代码注释竟然写"scrollable"）③H5 胶囊样式从未注入。修复：补齐 Grid 卡片布局 + `overflow-x:auto!important` + 44px/34px 胶囊。详见 `references/mobile-card-scroll-regression-v35.md`。**
- 列表页当招标（URL含category/list → 9条，浙能平台 2026-06-25）
- 同URL重复（unique_hash不一致 → 10组，已修复统一 URL-hash 2026-06-25）
- 子目录权限（chmod 644 * 不递归 → data_light.json 404）
- 聊天组件漏引用（report_generator 每次覆盖 → polish_report.py 已永久注入）
- 聊天组件重复注入（polish 非幂等 → 页面 2 个 chat-trigger，2026-06-25 修复）
- bs4 依赖断裂（systemd 用系统 python3 → pipeline 0新增，2026-06-25 全站停摆半天）
- changelog 顺序错乱（V1.7 插到 V1.6 后面）
- **async init() 无错误处理（致命坑 2026-06-25）：页面显示 "(0)" 空表，但 data.json 正常加载，无 console 报错，curl 检查全部 200 — 唯浏览器渲染能发现**
- **unique_hash 迁移灾难（2026-06-25）：改 hash 算法后必须回填所有已有记录的新 hash，否则下次爬虫重爬时 INSERT OR IGNORE 失效，全部重复入库**
- **regex 字符排除集遗漏 `。`（2026-06-25）：region/owner 字段混入正文垃圾，页面肉眼可见**。修复：`REGION_PATTERNS` + `BIDDER_PATTERNS` 排除集从 `[^；;，,\n]` 改为 `[^。；;，,\n]`，同时加 `{1,N}` 长度截断防止跨句子吞并。
- **换行压扁导致 regex `[^\n]` 失效（2026-06-25）：`re.sub(r'\s+', ' ', clean)` 删掉换行符**。修复：`_extract_region_owner()` 和 `extract_detail_fields()` 中删除 `re.sub(r'\s+', ' ', text)` 行，保留原始换行让 `[^\n]` 正常截断。
- **platform首页/导航页误抓为项目（2026-06-25）：13+6=19条垃圾（"欢迎使用XX平台"、"协会年会"、"详情页 首页 主体信息..."）高分入库**。修复：batch_crawler 层加 `DETECT_HOMEPAGE()` 函数过滤，已入库的用 SQL DELETE 清理。识别特征：标题含"欢迎来到/设为首页/收藏此页/平台首页/产品与服务/客服热线"→直接丢弃。
- ⛔ **L1 页面判别器集中化（V1.35）**：L1从分散在各管线→集中到 `relevance_scorer.py` 的 `score_item()` 入口，所有管线共享。详见 `references/l1-page-discriminator-score-item.md`。
- ⛔ **report_generator.py 缺少 `if __name__ == '__main__'`（2026-06-26 致命坑）**：定义了 `generate()` 但从未调用，直接 `python3 scripts/report_generator.py` 返回0但什么都不做。`data.json` 和 `index.html` 永远不会生成。**检查**：每个脚本末尾必须有 `if __name__ == '__main__': main_function()`。
- ⛔ **report_generator 重生成导致 UI 回退（2026-06-26 致命坑）**：`report_generator.py` 用**自己的模板**重写 index.html，模板结构与 polish 脚本累积注入的 V1.33+ 增强 CSS/HTML 不兼容。每次跑 report_generator → UI 筛选栏布局回退到 v5 基础版 → 用户质问「只是改功能？！怎么样式还会变？！！」。
  **最终方案（V1.35）**：`report_generator.py` 的 `generate()` 已改为**只生成 data.json，不再覆盖 index.html**。HTML 样式由 `polish_report.py` 单独维护，二者解耦。
  **如需重建 HTML**：先 `generate()`（生成 data.json），再单独调用 report_generator 的 `_html()` 重建 HTML，然后立即 `polish_report.py`。验证：`grep -c 'filter-scroll-wrapper\\|search-row' index.html` 两项 ≥1。
  **⛔ 测试/生产分离（V1.35）**：所有样式改动在 `/bidding-test/` 测试环境进行，确认后 `bash scripts/promote.sh` 推送到 `/bidding/` 生产。详见 `references/test-prod-environment-split.md`。
  **手机端 CSS 回退专项**：report_generator 模板缺失手机端关键规则（搜索框胶囊、筛选栏水平滚动、滑动动画提示）→ 手机端东倒西歪。修复见 `references/mobile-css-regression-report-generator.md`。
- **标题"采购公告 > xxx >"前缀（2026-06-25）：南网86条全带，页面阅读困难**。修复：`score_item()` 中循环 `re.sub(r'^(?:采购公告|招标公告|...)\s*>\s*', '', title)` 剥离所有层级前缀。
- **polish_report.py 非幂等注入（2026-06-25）：每次运行追加一份 chat-widget 引用→页面2个chat-trigger+2个chat-panel**。修复：注入前检查 `'chat-widget.css' not in html` 和 `'chat-widget.js' not in html`。
- **中标表混入26条平台首页/导航页（2026-06-25）：数智云采、天工招采、连云港/重庆/黄石公共资源交易中心首页被当"中标公告"入库**。修复：SQL DELETE + batch_crawler 加首页检测。
- **中标表12条非数字化项目高分入库（2026-06-25）：锅炉再热器/省煤器增容、空预器改造、煤矿胶带机、脱硫烟道、粉煤灰运输、员工工装洗涤等与数智科技业务完全无关**。根因：评分引擎的 DIGITAL_GATE 太宽（"系统""服务""技术"命中一切）。修复：`relevance_scorer.py` 新增 `NON_DIGITAL_EXCLUDE` 层——锅炉/煤矿/脱硫/洗衣/EPC施工总承包等直接拒掉，除非同时命中数字化强关键词。
- **中标表无评分过滤（2026-06-25）：33条中标裸奔入库，仅7条真正相关**。根因：中标入库前没跑相关性评分。修复：以后中标入库必须和招标一样过 `score_item()`。已有脏数据用 SQL DELETE 清理。
- **layout 布局混乱无审美（2026-06-25）：用户直言「完全没有一点审美！歪歪扭扭！」**。V1.11 全量重设计：统计卡片行(4卡片) + 两行筛选栏(搜索+下拉/日期+操作) + 专业表格(色条相关度+彩色客户标签) + 页码分页器 + 暗色深蓝专业基调。核心文件：`report_generator.py` v5、`app.js` v9、`polish_report.py` v2。

**📐 布局重设计规范（V1.11 — 2026-06-25）**：
- **Header**：Logo(32px) + 标题 `"文鳐智投"`(18px/700) + 副标题 `"中南电力设计院数智科技 · 投标信息智能监控"`(11px/dim) + 右侧系统状态（绿点·脉冲动画 + 运行中 + 站点N/M + 扫描时间 + 🌓）
- **统计卡片行**：4列 grid（`grid-template-columns: repeat(4,1fr)`），卡片含 `stat-value`(28px/800) + `stat-label`(12px/dim)。`.accent`→蓝值 `.green`→绿值 `.amber`→琥珀值。移动端→2列
- **筛选栏(V1.14精简)**：两行 flex。Row1：搜索框(flex:1/min 200px) + 客户下拉 + 地域下拉 + 相关度下拉。Row2：开始日期 + "至" + 结束日期 + spacer(flex:1) + 导出(smartExport智能模式) + 重置。
- **Tab栏（V1.19精简 — 仅3Tab）**：`border-bottom` + `tab-btn`。active状态 `color:#fff` + `border-bottom:2px solid var(--accent)`。Badge：圆角 pill 背景 `var(--surface)`，active时变为 `var(--accent)`。**趋势和竞品Tab已删除**，暂不需要。
- **表格(V1.22)**：11列招标/9列中标。招标：(checkbox32/序号60/相关度80/标题flex/客户100/招标单位120/**预算金额80**/地域80/来源120/日期100/操作60)。中标：(checkbox32/序号60/相关度80/标题flex/中标单位/**中标金额100**/地域80/日期100/操作60)。金额格式化：≥10000显示"XXX万"，否则原值，空"—"。金额列支持排序（`srt('budget_amount')`/`srt('winning_amount')`）和CSV导出。**所有可排序列始终显示双三角 ▴▾**（opacity:.3 默认 → sort-asc/sort-desc 亮起对应三角），详见 `references/sort-triangle-indicators.md`。
- **筛选栏(V1.27 单行紧凑)**：单行 flex。搜索框(flex:1.5) + 客户下拉 + 地域下拉 + 相关度输入(80px) + 日期起(115px) + "至" + 日期止(115px) + 预算输入(85px) + `|` 分隔 + 每页[20|50|100] + 导出 + 重置。gap:6px, flex-wrap:nowrap, overflow-x:auto 窄屏可滚。**不再用两行**，详见 `references/filter-bar-single-row-v27.md`。
- ⛔ **新增数据列必须四步闭环**：表头 → app.js渲染 → CSV导出 → 筛选控件。缺一不可。详见 `references/column-addition-checklist.md`。
- **分页器**：左 `"显示 X-Y 条 / 共 Z 条"` + 右 `« ‹ 1 2 3 › »` 按钮组。`.pg-btn.active` = accent背景白色文字。**每页选择器在筛选栏右侧**（`psSelector`），默认20条，可选20/50/100。HTML占位符+JS渲染+doFilter调用 三步闭环，参见 `references/page-size-selector-pitfall.md`。
- **暗色默认基调**：`--bg:#0f172a --surface:#1e293b --border:#334155 --text:#e2e8f0 --muted:#94a3b8 --dim:#64748b --accent:#3b82f6 --green:#10b981 --amber:#f59e0b`
- **app.js 必须调用 `init()`**：HTML模板末尾必须含 `<script>init();</script>`，不能只加载app.js不调用。否则 allB/allW 为空，页面显示空表但无报错

**☀️ 明亮主题CSS变量陷阱（致命坑 2026-06-25）**：
- **问题**：light mode 只改 `body.light{background:#f8fafc;color:#1e293b}` 但表格单元格用 `var(--text)`(暗色值#e2e8f0)，继承不了body的color→文字灰蒙蒙看不清
- **修复**：第一行覆盖全部CSS变量 `body.light{--bg:#f8fafc;--surface:#fff;--border:#e2e8f0;--text:#1e293b;--muted:#475569;--dim:#64748b}`
- **必须显式覆盖的元素**：`td.title-cell a`→`color:#1e293b`、`thead th`→`color:#64748b`、`tbody td`→`color:#1e293b`、`.tab-btn`→`color:#64748b`、`.tab-btn.active`→`color:#1d4ed8`、`.pg-btn`→所有状态、`.stat-value`→非accent卡片用`#1e293b`、`.btn`→`color:#334155`
- **验证**：`document.body.classList.add('light')` 后 `getComputedStyle(td).color` 必须是 `rgb(30,41,59)` 不是 `rgb(100,116,139)`

**⛔ 用户核心要求（2026-06-25）：修复BUG要深层次分析根因，不是擦地**

> 用户原话：「你修复BUG都是结果，要深层次的分析原因，以后不要再犯！」

**三层拦截架构（根治非擦地）**：

| 层 | 位置 | 拦截内容 |
|:--|:--|:--|
| L1 页面判别器 | `crawl_pipeline.py` insert_notice() 入口 | 平台首页/导航页/列表页（14个信号词） |
| L2 非数字排除 | `relevance_scorer.py` score_item() 第285行 | 锅炉/煤矿/脱硫/洗衣/EPC施工 |
| L3 中标独立评分 | `relevance_scorer.py` score_item() 第315行 | 非竞品且无数字化关键词的中标 |

详见 `data-quality-guard` skill 和 `references/root-cause-pattern.md`。

**正确的修复流程**：
1. 定位脏数据→追溯来源（batch_crawler / nanwang_adapter / scoring）
2. 堵源头：在数据进入管道的**最早节点**加拦截
3. 加防护层：L1→L2→L3
4. 写skill文档 + 更新changelog → 确保不重犯

> 用户原话：「你修复BUG都是结果，要深层次的分析原因，以后不要再犯！」
> 
> **擦地 vs 根治对照表**：
> 
> | ❌ 擦地（修症状） | ✅ 根治（堵源头） |
> |:--|:--|
> | 发现平台首页→DELETE删掉 | 追溯管道：batch_crawler无页面类型判别→L1拦截器 |
> | 发现锅炉100分→NON_DIGITAL_EXCLUDE加词 | 追溯管道：DIGITAL_GATE"系统""服务"太宽→三层架构 |
> | 同样问题反复出现 | 写skill文档化根因→下次自查先看skill |
> 
> **正确的修复流程**：
> 1. 定位脏数据→追溯来源（batch_crawler / nanwang_adapter / scoring）
> 2. 堵源头：在数据进入管道的**最早节点**加拦截
> 3. 加防护层：L1(页面判别器)→L2(非数字排除)→L3(中标独立评分)
> 4. 写skill文档 + 更新changelog → 确保不重犯
- ❌ 错误做法：发现垃圾→DELETE删除→结束
- ✅ 正确做法：追溯垃圾从哪条管道进来的→堵源头→加防护层→写skill文档
- 三层拦截架构见 `data-quality-guard` skill（L1页面判别器→L2非数字排除→L3中标独立评分）
- 每次改完评分/爬虫引擎后，必须跑 `references/system-audit-checklist.md` 全链路验证

> 审计 SOP 见 `references/system-audit-checklist.md`<br>
> 三层拦截架构见 `data-quality-guard` skill<br>

> 审计 SOP 见 `references/system-audit-checklist.md`<br>
> unique_hash 修复记录见 `references/unique-hash-standardization.md`<br>
> async init 陷阱见 `references/frontend-async-pitfalls.md`<br>
> regex 中文提取陷阱见 `references/regex-pitfalls-chinese-text.md`<br>
> 平台首页垃圾过滤见 `references/homepage-garbage-filtering.md`

> 审计 SOP 见 `references/system-audit-checklist.md`<br>
> unique_hash 修复记录见 `references/unique-hash-standardization.md`

```
scripts/
  bidding_engine.py    — 主爬虫引擎 (run_crawl -> score_item -> save_bidding)
  relevance_scorer.py  — 评分引擎 (100分制 / 数字门槛 / 55分底线) + L1页面判别器
  report_generator.py  — 只生成 data.json（不再覆盖 index.html）
  polish_report.py     — UI抛光 (主题/CSS/多选/卡片注入)
  wecom_push.py        — 企微推送 v8 (简化版：仅招标TOP8卡片 + 引导语)
  promote.sh           — 测试→生产一键发布

/var/www/html/bidding/
  index.html           — 报告 (由 report_generator.py 生成)
  app.js               — 前端交互 (独立文件, 通过 <script src> 加载)
  data.json            — API数据
  changelog.html       — 更新日志
  manual.html          — 操作手册（培训用，12章，详见 references/operation-manual.md）
  img/logo.png         — 自定义Logo（源文件见 references/favicon-spec.md）
  img_gen/og-share.png — 社交分享封面（1200×630，见 references/og-social-sharing.md）
```

## 评分引擎 — 权威定义

**v12 精细化（2026-06-25 — V1.11）**：步长缩小、加多样性+新鲜度奖励、拉开区分度。

| v11 | v12 |
|:--|:--|
| +35/core | **+12/core** (上限3) |
| +18/strong | **+6/strong** (上限5) |
| +8/weak | **+3/weak** (上限8) |
| 无 | **多样性奖励** +4×匹配类型数 |
| 无 | **新鲜度奖励** 今天+5/3天内+3/7天内+1 |
| 100分扎堆8条 | **100分散到4条，分布20+档** |

代码位置：`relevance_scorer.py` → `score_item()` 第346-375行。

**⛔ 本节已精简。v9 完整评分定义（关键词权重、排除规则、阈值、案例）见 `bidding-monitor` 技能。**

**v11 关键参数 (2026-06-25) — 扩宽IT信息化覆盖：**
- CORE_KEYWORDS: +35 — 含数智/智慧工地/智能安防/AI/大模型/深度学习/玄武SSK/执法记录仪/有限空间
- STRONG_KEYWORDS: +18 — 含管理系统/监管系统/系统开发/平台建设/软件开发/系统集成/信息技术/网络设备/服务器/虚拟化/数据库/运维管理/通信系统/SCADA/协同办公/OA系统等
- CUSTOMER_KEYWORDS: +12 — 华能/华电/国网/南网/中广核等
- GENERAL_KEYWORDS: +8 — 风电/光伏/储能/电厂/电网/矿山等
- 记录底线: ≥50（v11从55降至50，允许IT服务/运维/网络类项目入库）
- DIGITAL_GATE 新增 30+ 关键词（v11）：信息技术/信息化服务/软件开发/技术开发/数据中心/数据库/网络设备/服务器/虚拟化/容器/微服务/通信系统/SCADA/协同办公/OA系统/统一认证/容灾/灾备/实施服务/集成服务 等
- batch_crawler 87站预期通过率：v10 前 ~1.5% → v11 后目标 ~5-8%

## 文件操作安全规则

### 布局崩溃快速诊断
当页面"完全没法看"时，按以下顺序排查：
1. **HTML结构缺失闭合标签** — 用 `search_files` 搜 `<div class="tab-bar">` 和 `</div>` 配对。最常见：tab-bar 缺 `</div>` 导致整表嵌套进 flex 容器
2. **polish_report.py 重复注入** — 搜 `Light Theme` 出现次数（>1即重复），`toggleTheme` 出现次数
3. **CSS变量残留** — 用 browser_console 检查 `getComputedStyle(document.body).backgroundColor`
4. **修复后必须重新生成** — 改 report_generator.py 模板后需手动调 `generate()`，再 polish
5. **模板的保护机制**：polish_report.py 注入前必须幂等检查（'Light Theme' not in html），report_generator.py 的 HTML 模板每处 `<div>` 必须有对应 `</div>`

### ⛔ 前端交互铁律（V1.13 — 用户明确要求）

> 用户原话：「这就是个静态的界面而已啊！要交互逻辑的！！！」

**交互系统三原则**：
1. **每一个操作必须有即时反馈**：点击=视觉变化+状态更新+提示。不能「点了没反应」
2. **Badge/计数必须实时联动**：收藏数、Tab标注数必须在操作后立即更新，不能永远是0
3. **批量操作必须有**：checkbox + 全选 + 导出已选，是投标平台的基本功

**交互闭环模板**（每次加新按钮/操作时按此检查）：
```
点击 → DOM即时变化 → 数据持久化(localStorage/server) → Badge/计数更新 → Toast提示 → 切Tab可见
```

**Toast 系统**：`toast(msg, type)` — type='success'(绿)/'warn'(橙)/'info'(蓝)，2秒自动消失。CSS 动画 `@keyframes slideIn`。

**收藏系统规范**：
- `toggleStar(id)` → 更新 localStorage → `updateStarBadge()` 更新 `cntStar` → `toast()` → `syncBookmarkToServer()` → `doFilter()`
- `init()` 中 `loadBookmarksFromServer().then(() => updateStarBadge())` 初始化 Badge
- 收藏 Tab 通过 `starOnly=true` + 复用招标表格实现，非独立 DOM

**批量选择规范**：
- 表头 `<th class="w32"><input type="checkbox" onclick="toggleSelectAll()"></th>`
- 每行 `<td><input type="checkbox" onclick="event.stopPropagation();toggleSelect(id)"></td>`
- 全选逻辑：`selectedIds.size === data.length` 时清空，否则全选
- 导出已选按钮：筛选栏新增 `exportSelected()` 按钮（蓝色 accent 样式）

**表格列数变更规范**：加复选框列后，招标表 9列→10列，中标表 7列→8列。错误提示的 `colspan` 必须同步更新。app.js 版本号 bump。

### ⛔ 启动态渲染铁律（V1.15 — 用户质问责备）

> 用户原话：「开始我进去显示数字是累计招标120，然后一下就跳到数字57，然后只显示11条！这么多BUG你都不修复的吗？」

**两个致命启动态BUG**：

| BUG | 症状 | 根因 | 修复 |
|:--|:--|:--|:--|
| 假数据闪烁 | 统计卡片 120→57 闪跳 | `report_generator.py` 模板用硬编码默认值 `lc.get('total_processed', 120)` | 默认值改为 0 + CSS loading 态（`.stat-card.loading` opacity:.3→1 过渡） |
| 日期残留 | 只显示 11 条（非全量） | `saveFilters()` 把 `dateFrom/dateTo` 存进 localStorage，跨会话恢复 | 日期不再持久化——`saveFilters` 不存 date、`restoreFilters` 不读 date |

**模板默认值铁律**：模板中任何数字默认值必须是 0 或 "—"，**严禁硬编码看起来像真实数据的假数字**（120、7 等）。

**筛选持久化铁律**：`saveFilters/restoreFilters` 只保存**跨会话有意义的持久化偏好**（Tab、排序字段、客户/地域下拉）。日期筛选是临时上下文，24小时后毫无意义，**严禁持久化**。

> 详细技术规范见 `references/startup-rendering-pitfalls.md`
> 详细案例见 `references/data-freshness-pitfalls.md`

### ⛔ 统计卡片交互设计铁律（V1.17 — 用户质问「这些数字都不能点击吗？」）

> 用户原话：「累计招标57 今日新增11 高相关项目11 累计中标6 这些数字都不能点击吗？点击能不能展示对应的数据呢？？？」

**问题**：统计卡片有 onclick 但视觉上毫无交互暗示——无 hover 效果、无光标变化、无箭头指引。用户根本不知道可以点。

**修复四件套**（每张统计卡片必须全有）：
1. `cursor:pointer` — 鼠标悬停变手型
2. `:hover` — 边框变蓝 + 阴影 + 微微上浮 1px（`transform:translateY(-1px)`）
3. `:active` — 按下回弹（`translateY(0)`）
4. `::after` — 右上角 `›` 箭头，hover 时变蓝全显

```css
.stat-card[onclick]:hover{border-color:var(--accent);box-shadow:0 2px 12px rgba(59,130,246,.15);transform:translateY(-1px)}
.stat-card[onclick]:active{transform:translateY(0);box-shadow:none}
.stat-card[onclick]::after{content:'›';position:absolute;right:12px;top:50%;transform:translateY(-50%);font-size:18px;color:var(--dim);opacity:.4;transition:opacity .2s}
.stat-card[onclick]:hover::after{opacity:1;color:var(--accent)}
```

**统计卡片点击逻辑规范**：
| 卡片 | onclick | 行为 |
|:--|:--|:--|
| 累计招标 | `statClick('total')` | 重置全部筛选 + 切回招标 Tab |
| 今日新增 | `statClick('today')` | 设日期=今天 + doFilter |
| 高相关 | `statClick('high')` | 设 fScore=7 + doFilter |
| 累计中标 | `sw('win')` | 切到中标 Tab |

⚠️ `statClick('total')` 必须调用 `resetF()` 清空所有筛选——不能只是 `sw('bid')`。

### ⛔ NEW 标签视觉规范

> 用户原话：「不要用红点，太不显目了，换成new的标签」

**红点 `new-dot`**（5px 圆点）→ 已废弃。**`new-badge`**（红底白字 `NEW`）是标准：
```css
.new-badge{display:inline-block;padding:1px 6px;border-radius:3px;font-size:9px;font-weight:700;color:#fff;background:var(--red);margin-right:6px;vertical-align:middle;line-height:1.5}
```
渲染：`isNew(i) ? '<span class="new-badge">NEW</span>' : ''`

> 用户原话：「今日新增的11个是不是应该有个new的图标！怎么判断是今日新增呢？你作为产品经理 要注重这些细节！」

**is_new 标志全员腐败（致命坑）**：

| 症状 | 根因 | 影响 |
|:--|:--|:--|
| 全部57条都带NEW红点 | DB schema `is_new INTEGER DEFAULT 1`，插入即=1，爬虫从不重置旧数据 | NEW图标完全失去意义 |
| 管线重跑后 fetch_date 全变今天 | `INSERT OR REPLACE` 更新 fetch_date | 基于 fetch_date 的"今日新增"全部误判 |

**V1.37 最终方案 — 归档差集**：不再依赖日期字段，改为对比昨天归档 `data.json` 的 ID 差集。`is_new_today = id not in yesterday_ids`。详见 `references/today-new-archive-diff.md`。

**修复**：不在 DB 层信 `is_new`。在 `report_generator.py` 的 `trim()` 中用 `fetch_date` 实时判断：
```python
fd = str(item.get('fetch_date') or '')
result['is_new'] = 1 if fd.startswith(today) else 0
```
同时在 `KEEP_STR` 中加入 `'fetch_date'`，让前端 data.json 包含该字段。

**Header crawl_log 为空时的处理**：
- `crawl_log` 表为空 → `lc.get('total_sites', 0)` = 0 → "站点 0/0" 永远显示 → 误导用户
- 修复：`st` 为 0 时 `site_html = ''`，不展示站点信息行

**累计中标统计卡片交互缺口**：
- 4 张统计卡片中唯独「累计中标」缺少 `onclick="sw('win')"`——交互不一致
- 修复：补 `onclick` + `style="cursor:pointer"`

**PM 细节自检清单（每次改完前端/数据管道的必查项）**：
1. ⛔ **`isNew()` 是否用 `publish_date` 实时计算**（而非读取静态 `is_new` 字段或 `fetch_date`）？**`todayOnly` 过滤是否复用 `isNew()`**？两处口径必须一致！**用户心智 = 今天发布 = NEW，不是今天抓取 = NEW。**（2026-06-25 修正：初版错用 fetch_date，用户纠正）
2. NEW 标签是否醒目（红底白字 `NEW` badge，不是不起眼的红点）？
3. 统计卡片4张是否都可点击？**是否每张有 hover 动效 + `›` 箭头暗示可交互？**
4. ⛔ **统计卡片点击数据一致性**：卡片统计数和点击结果必须用同一字段过滤。今日新增统计 publish_date=today → 点击必须筛选 isNew()（同为 publish_date），后端 report_generator.py 的 SQL 也必须用 substr(publish_date,1,10)=?。三处口径必须一致！
5. 点累计招标是否重置全部筛选？点今日新增是否精准对应统计数？
6. Header 信息是否为空时不展示假数据（站点 0/0、扫描 —）？
7. `data.json` 是否包含了前端渲染需要的所有字段（含 `fetch_date`）？
8. 交互操作后 Badge/计数是否实时联动？（收藏数、Tab 标注数）
9. 空状态是否有友好引导文案（而非空白页）？
10. ⛔ **todayOnly 执行顺序**：`statClick` 中必须先 `sw()` 再设 `todayOnly` 再 `doFilter()`——颠倒则被 `sw()` 内部清掉。详见 `references/stat-card-click-consistency.md`
11. ⛔ **数据就绪守卫**：`sw()` 开头必须检查 `if (!allB.length && !allW.length) { toast('数据加载中...'); return; }`——防止 init() 未完成时用户点击卡片看到空表
12. ⛔ **排序三角 class 管理（V1.20 致命坑）**：CSS 用 `::before`/`::after` + `sort-asc`/`sort-desc` 控制三角亮灭，但 `srt()` 只改了 `sf`/`sd` 变量，从未给 `<th>` 加 class → 三角永远不亮。修复：在 `doFilter()` 的 `data.sort()` 前遍历所有 `th` 清除旧 class，再用 `sd` 给当前排序列加 `sort-asc` 或 `sort-desc`。详见 `references/sort-triangle-indicators.md`
13. ⛔ **新增数据列四步闭环（V1.22 致命坑）**：加列表头+渲染+导出后**必须加筛选控件**，否则用户无法按此列过滤。筛选用 `<input type="number">`（自由输入）而非固定下拉。同时更新 `resetF()` 清理新控件。详见 `references/column-addition-checklist.md`
15. ⛔ **CSS 修复是否已写入 polish_report.py**？改完 index.html 样式后必须检查 polish 脚本有无对应替换逻辑。
16. ⛔ **用户文档是否含具体人名/团队名**？操作手册和 FAQ 中禁止出现「程浩/量子纪元」等，统一用「反馈入口提交」。
17. ⛔ **分享链接有无封面图**？新 HTML 页面必须含 `og:image` 等 7 条 OG 元标签，`curl | grep 'og:'` 验证。
- **适配器正则陷阱**：正则停止条件不能包含公司名常见片段（`浙能`、`华能`、`国网` 等），详见 `references/zheneng-adapter-regex-fix.md`
- **table-layout 排序跳变（V1.26 修复）**：点击排序列头→整表跳动。根因是 `table-layout: auto`（默认），innerHTML 替换行时浏览器重新计算列宽。修复：`table-layout: fixed` 锁死列宽。验证：点任意排序列头，框体不应跳动。
16. ⛔ **反馈组件（V1.26 — 已合并入聊天面板）**：反馈入口不再独立悬浮，而是集成在 chat-widget v4 内（头部 📝 按钮 + 预设栏「📝 反馈问题」+ 欢迎消息提示）。`polish_report.py` 仅注入 chat-widget CSS/JS，**不注入独立 fb-fab**。`curl | grep -c fb-fab` 必须 = 0，`grep -c chat-widget` 必须 ≥2。详见 `references/chat-widget-v4-feedback-merge.md`
18. ⛔ **table-layout: fixed 防排序跳变 (V1.26)**：表格排序时 innerHTML 替换 → `table-layout: auto` 重新计算列宽 → 整表跳动。修复：table 加 `table-layout: fixed`，列宽由 th 的 w80/w100/w120 锁定。每次改表格结构后验证：点任意排序列头，框体不应跳动。
19. ⛔ **UI组件定义≠可见（致命坑 V1.27）**：`renderPsSelector()` 函数存在但从未被调用→分页选择器永远不显示。铁律：任何 UI 组件必须**三步闭环**——HTML 占位符(id) + JS 渲染函数 + `init()`/`doFilter()` 中实际调用。验证：页面加载后肉眼确认所有预期控件可见。详见 `references/page-size-selector-pitfall.md`
20. ⛔ **筛选栏单行布局 (V1.27)**：筛选栏必须是**单行**，所有条件紧凑排列（search flex:1.5 + 下拉 + 输入 + `|` + 每页 + 按钮），gap:6px, flex-wrap:nowrap。**禁止两行**。新增控件时确保单行能放下，否则用 overflow-x:auto。详见 `references/filter-bar-single-row-v27.md`
21. ⛔ **chat-widget 拖动规范 v5 (V1.35)**：**仅头部标题栏可拖**（`#chatDragHandle`），内容/对话区不可拖 — 用户明确表示「框内是为了阅读」。`mousedown`/`touchstart` 绑定在 `#chatDragHandle` 而非 `#chatWidgetAll` wrapper。头部内的按钮（📝反馈、✕关闭）排除拖动（`e.target.closest('button,input,textarea,a')`），但 Logo `<img>` 可拖。**⛔ touchmove 必须 `e.preventDefault()`** 防背景页面跟随滚动（用户反馈「移动框，背景也在上下滑动」）。3px 防抖死区保留。详见 `references/chat-widget-drag-v5.md`。
22. ⛔ **Esc 快捷键优先级 (V1.27)**：`Esc` 必须**先关闭聊天面板**（如果打开），再清空搜索。顺序反了会清空搜索但聊天面板还挡着。
23. ⛔ **favicon 三步闭环 (V1.27)**：所有页面必须用 Logo 做标签页图标。步骤：PIL 生成 32×32 PNG + ICO + 180×180 Apple → HTML `<head>` 注入 3 条 `<link>` → `polish_report.py` 幂等注入防丢失。验证：`curl -sI URL | grep favicon` 返回 200。
24. ⛔ **骨架屏首屏体验 (V1.27)**：`init()` 第一步注入 `skeletonRows(ps)` 替换空 tbody，避免「显示 0 条」闪跳。shimmer 动画需暗/亮双主题。详见 `references/skeleton-loading-pattern.md`
25. ⛔ **移动端卡片化 (V1.28)**：≤768px 时表格→竖排卡片（thead 隐藏、tr→block 卡片、td→flex 行 + `::before` 取 data-label 做标签）。每个 td 必须有 `data-label` 属性。详见 `references/mobile-card-layout-v28.md`
26. ⛔ **行展开详情 (V1.27)**：点击行 → `toggleDetail(id)` → `expandedId` 状态切换 → `doFilter()` 重渲染带 `<tr class="detail-row">` 的详情卡。详情卡用 `colspan="11"` 跨全列，含 grid 布局字段组 + 摘要 + 原始链接。
27. ⛔ **统计卡片趋势指示器 (V1.27)**：今日新增/高相关旁显示 ↑N/↓N（对比昨日 publish_date），实时计算而非依赖后端 brief。`stat-card.loading` 期间 trend opacity:0。
28. ⛔ **数据更新时间 (V1.28)**：头部「系统运行中」→「数据更新: MM-DD HH:MM」，取 `max(fetch_date)`。用户一秒判断数据新鲜度。
29. ⛔ **高相关统计口径 (V1.28) — ⛔ V1.31 已重构**：「高相关项目」= 全部 ≥70 分项目（非仅今日），标签与数值语义一致。点击不限 todayOnly。**V1.31 起 statClick('high') 不再设 fScore=70**——改用独立 banner 模式（`activeStatFilter`），搜索框保持干净。详见 `references/stat-card-independent-view-v31.md`。
30. ⛔ **Nginx alias + try_files $uri 陷阱 (V1.28)**：`alias` 改根但 `try_files $uri` 仍用请求 URI → 路径拼接错误 → 静态文件 404。修复：`alias` → `root /var/www/html`。详见 `references/nginx-alias-tryfiles-pitfall.md`
31. ⛔ **目录缺 x 执行位导致 nginx 403/404 (V1.28)**：`drw-r--r--`(644) 目录 nginx 无法遍历 → 内部文件全部 404。修复：`chmod 755 dir/`。每次创建新子目录必须设 755。
32. ⛔ **手机端聊天面板禁止自动弹出 (V1.28)**：`window.innerWidth > 768` 检测，≤768 宽度跳过 `openChat()`。否则手机一打开就被面板遮挡全屏。
33. ⛔ **头部 sticky 固定 (V1.28)**：`.app-header{position:sticky;top:0;z-index:100}`。向下滚动时筛选栏和更新时间始终可见。详见 `references/mobile-header-sticky.md`
34. ⛔ **移动端 CSS 溢出三重锁 (V1.29)**：手机端出界必查三处——(a) `calc()` 运算符两侧必须有空格，`calc(100vw-16px)` 是语法错误整条规则被静默丢弃；(b) JS `element.style.right='20px'` 内联样式优先级 > CSS 媒体查询，手机端必须清空内联；(c) 触屏设备禁拖动（`'ontouchstart' in window`）。**任何页面手机端左右可滑动 → 三锁齐出**：`body{overflow-x:hidden}` + `*{max-width:100vw}` + 专锁。**每次改 CSS 后 `index.html`、`changelog.html`、`report-*.html` 全部验证**。详见 `references/mobile-css-overflow-pitfalls.md`
35. ⛔ **iOS 输入框自动放大 (V1.29)**：手机点击输入框→全屏放大。根因：iOS Safari 对 `font-size` < 16px 的 `<input>`/`<textarea>` 自动缩放。修复：`@media(max-width:768px)` 中所有输入元素设 `font-size:16px`。排查：`grep -n 'input|textarea' *.css | grep -v 'font-size:1[6-9]'`。详见 `references/mobile-css-overflow-pitfalls.md`
36. ⛔ **手机卡片 data-label 完整性 (V1.29)**：每列 `<td>` 必须有 `data-label` 属性（序号→"序号"，操作→"操作"）。`hide-mobile` 禁止用于关键业务列（客户、招标单位、地域）。缺失则用户看到裸数字和裸按钮。详见 `references/mobile-card-layout-v28.md`
37. ⛔ **chat-widget 手机触发条 (V1.29)**：折叠态 `left:auto`（不拉伸）、`padding:8px 14px`、`gap:6px`，紧凑药丸形固定在右下。不要 `left:8px` 让它横跨屏幕。
38. ⛔ **「查看」按钮手机端药丸化 (V1.29)**：手机卡片中隐藏 `data-label="操作"` 的 `::before` 标签，`.link-btn` 设为全宽蓝色药丸（`padding:8px 20px; border-radius:20px; min-height:36px; background:var(--accent); color:#fff`），居中显示。**不再是文字链接**。点击态 `:active{transform:scale(.96)}`。
39. ⛔ **手机端触控目标 ≥36px (V1.29)**：每页选择按钮 `min-width:36px;height:36px`（原 28px）、筛选栏按钮 `height:36px`。所有可交互元素应达到此标准。低于此值 = 用户手指无法精准命中。
40. ⛔ **筛选栏输入框字号 ≥14px (V1.29)**：`filter-row select/input[type=number]/input[type=date]` 手机端 `font-size:14px`。虽然 iOS zoom 阈值是 16px，但 14px 对 select/dropdown 足够（select 用原生控件不触发 zoom），且比 12px 更可读。
41. ⛔ **index.html 内联样式禁重复 chat-widget 规则 (V1.29)**：`index.html` 的 `<style>` 块优先级 > 外部 `chat-widget.css`。**禁止在 index.html 中定义 `.chat-trigger`、`.chat-panel` 等样式**。chat-widget 所有样式统一在 `chat-widget.css` 管理。排查：`grep -n 'chat-trigger\|chat-panel' index.html`。
42. ⛔ **统计卡片手机端加阴影 (V1.29)**：`.stat-card{box-shadow:0 1px 3px rgba(0,0,0,.08)}` — 提供层次感，手机端卡片不再是扁平白块。
43. ⛔ **Apple设计铁律 (V1.30): 禁止彩色按钮和彩色统计值**。`link-btn` 手机端 `display:none`，卡片本身可点击，用 `::after{content:'›'}` 暗示交互（苹果 Settings 风格）。统计卡片数字统一 `#1d1d1f`，不用 accent/green/amber 区分。详见 `references/apple-mobile-design-v30.md`
44. ⛔ **CSS Grid 卡片布局 (V1.30): tr 级 Grid，非 td 级**。`tr.data-row{display:grid;grid-template-columns:1fr auto auto auto}`，每个 td 用 `grid-row`/`grid-column` 精确定位。4行布局：标题(row1 span4) → 客户+预算(row2) → 招标单位(row3 span4) → 地域·日期·相关度·›(row4)。**禁止**用 `td{display:grid}`（每个 td 自己成 grid 导致 label/value 都在同一个单元格内挤）。详见 `references/apple-mobile-design-v30.md`
45. ⛔ **自明字段隐藏 label (V1.30)**：地域、日期、相关度三个字段不显示 `::before` label（用户一眼就知道是什么），用 `·` 分隔符连成一行。底部行 `font-size:12px; color:#8e8e93`。
46. ⛔ **Apple 毛玻璃头部 (V1.30)**：`body.light .app-header{background:rgba(255,255,255,.72);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px)}`。不再用蓝色渐变。
47. ⛔ **Apple 调色板 (V1.30)**：亮色 `--bg:#f5f5f7;--text:#1d1d1f;--muted:#86868b;--dim:#8e8e93`。输入框 `background:#f2f2f7` 无边框 10px 圆角。
48. ⛔ **标题行数截断 (V1.31)**：`td.title-cell` 必须加 `overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical`。所有现代浏览器（含 iOS Safari）支持，标题最多 2 行，超出 `…`。不截断则超长标题撑破卡片。
49. ⛔ **分数语义化 (V1.31)**：App.js 渲染分数时显示 `85分` 而非 `85`。用户无法从裸数字判断含义。模板：`${sc.toFixed(0)}分`。
50. ⛔ **卡片点击双态 (V1.31)**：手机端（`innerWidth<=768`）点卡片 → `window.open(url,'_blank')` 跳转源页面。桌面端保留 `toggleDetail(id)` 展开详情。`onclick="if(window.innerWidth<=768){window.open('${link}','_blank')}else{toggleDetail(${i.id})}"`
51. ⛔ **标题字体继承一致性 (V1.31)**：`td.title-cell a{font-size:inherit;line-height:inherit}` **禁止**单独指定字号。`-webkit-box` 布局下纯文本节点（🆕☆）和 `<a>` 标签如字号不同则渲染基线偏差，视觉上大小不一。
52. ⛔ **手机端星标可见 (V1.31)**：`.star{display:none}` 必须移除。手机端星标 `font-size:18px`、`z-index:2`、`position:relative`，位于标题前可点击（`event.stopPropagation()` 防跳转）。已收藏显示 ★(金色 `#f59e0b`)，未收藏 ☆。不得因卡片 `onclick` 跳转而牺牲收藏功能。
53. ⛔ **卡片底部行格式 (V1.31)**：地域·日期·相关度分为一行，用 `::before{content:'·'}` 伪元素做分隔符。三个字段均隐藏 `data-label`（自明字段）。相关度必须带 `分` 后缀（模板：`${sc.toFixed(0)}分`）。
54. ⛔ **回到顶部按钮 (V1.31)**：`init()` 中注入 `<button id="btnBackTop">↑</button>`（40px 圆，fixed bottom:80px right:16px）。scroll 监听（passive:true + rAF 节流）：`window.scrollY > 300` 时 `classList.add('show')`。默认 `opacity:0;transform:translateY(10px);pointer-events:none`，`.show` 时 `opacity:1;transform:translateY(0);pointer-events:auto`。smooth scroll to top。暗色背景适配。
55. ⛔ **Toast 手机端移位 (V1.31)**：`@media(max-width:768px)` 中 `.toast{top:auto!important;bottom:100px!important;right:50%!important;transform:translateX(50%)!important}`。桌面端 toast 在右上角（`top:20px;right:20px`），手机端移到底部居中，不被刘海/导航栏遮挡。
56. ⛔ **空状态卡片化 (V1.31)**：招标/中标无结果时必须用 `<tr class="empty-msg"><td colspan="N">提示文案</td></tr>`。CSS 手机端：`display:flex!important;justify-content:center;padding:48px 20px!important;background:#fff!important;border-radius:14px!important`。中标表此前无空状态检测→直接空白，已补 `if(!page.length)` 守卫。
57. ⛔ **列表底部标记 (V1.31)**：最后一页数据末尾显示 `.end-marker` 提示（`text-align:center;padding:12px;font-size:12px;color:#c7c7cc`），文案「已显示全部」或自定义。仅手机端 CSS 有此样式。
58. ⛔ **Kebab 菜单 ⋯ 模式 (V1.32)**：卡片右上角 `⋯` 按钮（28px圆、z-index:3、绝对定位 top:12px right:12px），点击弹出菜单（📤分享/🔗复制链接/📋复制标题/⭐收藏/取消收藏）。菜单 `position:fixed`，带透明 overlay 点击外部关闭，`getBoundingClientRect()` 精确定位。**禁止**用长按触发分享（用户反馈「反人类」），**禁止**用丑陋图标（用户反馈「可读性太差」）。菜单按钮 `border-bottom:1px solid rgba(0,0,0,.06)` 分隔，最后一项无边框。暗/亮双主题适配（`.kebab-menu button:active` 背景变化）。**NEW badge 和 kebab 定位冲突解决**：NEW badge 左上角（`left:14px`），kebab 右上角（`right:12px`），互不遮挡。详见 `references/kebab-menu-card-pattern.md`。

59. ⛔ **Apple 设计平衡铁律 (V1.32 修正)**：①**禁止彩色按钮**——`link-btn` 手机端 `display:none`，卡片本身可点击；②**禁止彩色统计值**——所有 stat-value 统一 `#1d1d1f`；③**布局用 Apple 美学**——CSS Grid、毛玻璃、留白、灰阶、SF 风格字距；④**功能控件必须可见**——**禁止** `rgba(0,0,0,.08)` 透明边框（用户直言「框都看不见」），输入框必须用实色边框 `#d1d1d6` + 纯白背景 `#fff`，与页面灰底 `#f5f5f7` 形成清晰对比；⑤**搜索图标不重叠**——搜索框 `padding-left:34px`（为绝对定位的 🔍 留空间），缺失则图标和文字重叠。

60. ⛔ **移动端筛选栏 H5 风格 (V1.33) + 筛选折叠模式 (V1.36)**：对标 Twitter/Alibaba H5。**V1.36 新增筛选折叠**：默认隐藏筛选条件，搜索框右侧「☰ 筛选」按钮点击展开/收起，带下滑动画。展开态 = 单行横向滚动 + 右侧渐变淡出。详见 `references/mobile-filter-toggle-pattern.md`。 — 搜索框独占一行（全宽胶囊44px），筛选行 `flex-wrap:nowrap; overflow-x:auto` 横向滚动不换行，隐藏滚动条。**⛔ 搜索框必须独立于 filter-row**——搜索放在 `.search-row`（filter-bar 的直接子节点），筛选胶囊放在 `.filter-row`。如果搜索框也在 `.filter-row` 里，`nowrap` 会阻止它换行，导致与「客户」下拉重叠。所有输入/选择/按钮统一 pill 样式：`height:34px; border-radius:17px; background:#e8e8ed; border:none`。搜索框 `height:44px; border-radius:20px`。日期预设按钮 34px pill。暗色模式 `background:#2c2c2e`。**禁止**用 `flex-wrap:wrap`（多行歪扭）、**禁止**白底灰框（视觉噪声）。`setDatePreset()` 需 toggle `.active` class（黑底白字），手动改日期时清除 `.active`。**⛔ 横向滚动必须有视觉 affordance（双保险）**：① 静态 — wrapper `::after` 渐变淡出（40px, transparent→背景色），scroll + ResizeObserver 检测 `scrolled-end` 时 `opacity:0`；② 动态 — 首次进入自动演示滑动（右滑100px→1.2s弹回），`sessionStorage` 标记仅演示一次。详见 `references/mobile-horizontal-scroll-affordance.md`。

61. ⛔ **桌面端筛选栏高度对齐 (V1.33)**：搜索框、select、input[type=number/date] 必须统一 `height:36px; box-sizing:border-box`。所有元素都用 `box-sizing:border-box` + 显式 height，不依赖 padding 隐形定高。手机端保持搜索44px/胶囊34px的差异（有意设计）。

62. ⛔ **搜索字段覆盖不完整（致命坑 V1.34）**：搜索仅查 `title`/`owner`/`winner`/`source` 四个字段 → 中标数据的省份在 `province` 字段 → 搜「广东」搜不到中标。**修复**：搜索扩展至 7 字段 — `title`、`procurement_owner`、`winner_company`、`source_site`、**`province`**、**`region`**、**`category`**。`getFilt()` 和 `getFiltFor()` 同步更新。

63. ⛔ **手机端搜索框自动搜索不可靠 → 用搜索按钮（致命坑 V1.33）**：HTML 属性 `oninput=\"doFilter()\"` 和 JS `addEventListener('input')` + `compositionend` 在移动端均不可靠 — iOS Safari 中文拼音输入阶段可能不触发、IME 组合输入时频繁触发导致闪烁。**用户明确要求**：在搜索框右侧加一个「搜索」确认按钮，输入完点按钮或按回车触发。**最终方案（V1.33 最终版）**：① 搜索框右侧放 `<button class=\"search-btn\" id=\"searchBtn\" type=\"button\">搜索</button>`（桌面端36px蓝色、手机端44px iOS蓝 #007aff，input左圆右方拼胶囊）；② `init()` 中用 **`addEventListener('click', doFilter)`** 绑定按钮 — ⛔ 必须用 JS addEventListener，不能用 HTML onclick 属性（移动端不可靠，用户反馈「点这个搜索没反应啊」）；③ `searchEl.addEventListener('keydown', ...)` 回车也触发；④ 移除 `oninput` 属性、移除 compositionend 弹幕监听；⑤ **按钮必须加触感反馈**：`:active{background:#0056cc}` + `-webkit-tap-highlight-color:transparent` + `transition:background .15s` — 用户明确要求「点了要有反应」。

64. ⛔ **统计卡片数字联动筛选 + 跨Tab徽标（V1.34 致命坑）**：用户搜索「浙江」→ 卡片显示「招标 56」而非实际匹配的「5 条」→ 用户困惑「没联动起来」+ 「收藏显示2实际只有1」+ 「中标Tab搜广东无结果」。**修复三合一**：① `doFilter()` 末尾调用 `updateStats(data)` — 有筛选时统计卡片+三个Tab徽标全部显示过滤后数字；② 新增 `getFiltFor(arr)` 将同样筛选独立应用到 allB/allW → 跨Tab徽标同步；③ 搜索字段从 4 扩展到 **7**（+province/+region/+category）。详见 `references/dynamic-stat-cards-v34.md`。

65. ⛔ **统计卡片污染搜索框 → 独立 banner 视图（V1.31）**：用户点「高相关招标 12」→ 搜索框被塞 "70" → 所有卡片数字变过滤后值 → 用户困惑「逻辑不对，应该是单独界面」。**根因**：`statClick('high')` 直接设 `fScore.value='70'` → `doFilter()` → `updateStats()` 检测到 hasFilter=true → 全局卡片全变。**修复**：引入 `activeStatFilter` 状态 + 专属 banner + 统计卡片保持全局计数不变。`getFilt()`/`getFiltFor()` 优先检查 `activeStatFilter`（在手动筛选之前）。`updateStats()` 中 `activeStatFilter` 分支→统计卡片给全局值。`resetF()` 清除 `activeStatFilter`。点击同一卡片 → 取消；点击 ✕ → 取消。详见 `references/stat-card-independent-view-v31.md`。

66. ⛔ **CSS 修复持久化铁律 (V1.32)**：任何对 `index.html` 内联 `<style>` 的修改，必须在 `polish_report.py` 中加对应的字符串替换逻辑（idempotent），否则 `report_generator.py` 下次重写时修复丢失。模式：`if '旧CSS' in html: html = html.replace('旧CSS', '新CSS')`。典型案例：筛选栏 overflow:hidden→visible、kebab-btn display:none→!important。

67. ⛔ **桌面端 CSS !important 陷阱 (V1.32)**：动态注入 HTML（JS 渲染表格行）场景下，浏览器可能静默忽略 `display:none`（getComputedStyle 返回 inline）。必须用 `!important` 强制优先级。同时在 `@media(max-width:768px)` 中用 `!important` 反向覆盖。详见 `references/desktop-css-pitfalls.md`。

68. ⛔ **文档内容策略 (V1.32)**：用户文档（操作手册、FAQ、changelog）中**禁止**出现具体人员/团队名称（如「程浩团队/量子纪元」）。反馈入口统一表述为「通过右下角浮动面板中的反馈入口提交」。内部运维文档不在此限制内。

69. ⛔ **OG 社交分享标签 (V1.32)**：操作手册、changelog、主看板三个页面必须有 `og:title/description/image/url` 元标签。主看板的 OG 已写入 `polish_report.py` 持久化。封面图 `img_gen/og-share.png` 1200×630 从真 Logo 生成。详见 `references/og-social-sharing.md`。
70. ⛔ **CSS @media 隐藏规则顺序 (V1.32)**：桌面端隐藏规则的 `@media(min-width:769px){display:none}` **必须写在基础规则之后**。写在基础规则之前会被后面的 `display:flex/block` 覆盖（同等特异性下后者胜）。正确顺序：先写基础规则 → 再写 @media 隐藏。修复案例：pullIndicator 的 @media 从 `#pullIndicator{...}` 前面移到 `body.dark #pullIndicator.ready{...}` 后面。
71. ⛔ **CSS display:none!important 失效 → JS 条件渲染兜底 (V1.32)**：Browserbase 等远程浏览器中，即使内联 `<style>` 含 `display:none!important`，`getComputedStyle` 仍可能返回 `inline`。此时必须用 JS 层面条件渲染：`window.innerWidth <= 768 ? '<span class="kebab-btn">...</span>' : ''`。验证：`document.querySelectorAll('.kebab-btn').length` 桌面端必须 = 0。详见 `references/desktop-css-pitfalls.md`。
72. ⛔ **文档内容策略 (V1.32)**：用户文档（操作手册、FAQ、changelog）中**禁止**出现具体人员/团队名称（如「程浩团队/量子纪元」）。反馈入口统一表述为「通过右下角浮动面板中的反馈入口提交」。内部运维文档不在此限制内。
73. ⛔ **桌面端 Pull-to-refresh 禁止 (V1.32)**：桌面端（>768px）必须在 IIFE 中用 `el.remove()` 删除 `#pullIndicator` 元素，不仅依赖 CSS。仅在移动端激活 touch 事件监听器。详见 `references/desktop-mobile-separation.md`。
74. ⛔ **筛选栏弹性右对齐 (V1.32→V1.33 修正)**：导出/重置必须与统计卡片右边缘平齐。**错误做法（V1.32 已废弃）**：在 filter-row 内部加 `flex:1` spacer — 此 spacer 在 `.filter-scroll-wrapper{overflow:visible}` 环境下 flex 上下文是 filter-row 本身，推不动外层 filter-bar 边界，导出/重置会溢出。**正确做法（V1.33）**：将导出/重置/psSelector 移出 `.filter-scroll-wrapper`，作为 `.filter-bar` 直接子级，在 wrapper 后加 `<span style="flex:1;min-width:8px">`。此时 spacer 在 filter-bar 层级（与 stat cards 同宽），自然对齐。同时调宽 `.search-row` 至 340px 给筛选胶囊留呼吸空间。polish_report.py 中检测 `<!-- /filter-scroll-wrapper -->` 标记来判断是否已完成结构重构。详见 `references/filter-bar-right-alignment.md`。
75. ⛔ **Logo 源文件位置 (V1.32)**：文鳐智投真 Logo 位于 `img/logo.png`（651×383 RGBA）。从它生成 favicon-32x32(32×32)、apple-touch-icon(180×180)、favicon.ico、og-share(1200×630)。生成后用 `chmod 755` 确保 `img_gen/` 目录可遍历。详见 `references/favicon-spec.md`。
76. ⛔ **flex:1 spacer 上下文陷阱 (V1.33)**：嵌套 flex 容器中，`flex:1` 的扩展空间取决于其**直接父 flex 容器**。当子容器的内容溢出（`overflow:visible` + `flex-wrap:nowrap`）时，子容器内部 spacer 无法推动外层边界。解决方案：将需要右对齐的元素提升到目标 flex 层级的直接子级，spacer 也放在同一层级。典型案例：筛选栏导出/重置从 filter-row 提升到 filter-bar。详见 `references/filter-bar-right-alignment.md`。
77. ⛔ **桌面改动 → 移动端必验证 (V1.33)**：用户明确反感「你老是这样只顾一边」+「手机端又出问题了」。每次改 `index.html` CSS/HTML 后必须验证移动端未受破坏。三步：①改完刷新桌面验证 → ②用 `matchMedia('(max-width:768px)')` 检查移动端规则存在 → ③验证移动端特定样式未被宽泛的 polish 替换覆盖。**典型漏检案例：筛选栏右对齐重构 → 手机端竖列堆叠；V1.33 密度切换 → 手机卡片压扁**。
78. ⛔ **polish_report.py 字符串替换必须精确 (V1.33)**：`html.replace('overflow:hidden', 'overflow:visible')` 会同时命中桌面端和手机端的 filter-scroll-wrapper。**必须用完整上下文**：`html.replace('.filter-scroll-wrapper{flex:1;min-width:0;overflow:hidden}', '.filter-scroll-wrapper{flex:1;min-width:0;overflow:visible}')`。手机端的 `position:relative;overflow:hidden` 不会被误伤。
79. ⛔ **筛选栏右对齐移动端适配 (V1.33)**：桌面端将导出/重置提级到 `filter-bar` 直接子级后，手机端 `filter-bar{display:block}` 导致这些元素竖列堆叠。修复：`@media(max-width:768px)` 中隐藏 bar 级 extras（`filter-bar > span:not(.search-icon), filter-bar > .pg-btns, filter-bar > .btn`），仅保留导出按钮（`filter-bar > .btn[onclick*=\"smartExport\"]`）。详见 `references/desktop-mobile-separation.md`。
80. ⛔ **密度模式必须手机端豁免 (V1.33)**：`body.dense` 的全局规则（行高32px、字号11px）会把手机端卡片视图的 Grid 布局也压扁——padding/font-size 全塌。修复：`@media(max-width:768px)` 内覆盖 `body.dense` 所有关键属性为正常卡片值（`td{padding:0;font-size:13px} tr{height:auto;padding:18px 16px} .star{font-size:16px} .score-bar{display:none}`）。不可用 `display:none` 屏蔽整个 dense 模式——会丢失桌面端用户的密度偏好 localStorage 状态。
81. ⛔ **全站 Logo 替换 SOP (V1.33)**：用户提供新 Logo 图片 → 用 PIL 生成 5 种尺寸（header logo 200px高、favicon 32×32、ICO、apple-touch-icon 180×180、og-share 1200×630）→ `chmod 755` 目录 + `chmod 644` 文件 → 验证 `curl -sI` 全部 200 → 三页面（看板/changelog/手册）统一引用。`report_generator.py` 的 logo src 已是 `/bidding/img/logo.png` 无需改动。⛔ **chmod 644 * 致命陷阱**：`chmod 644 /var/www/html/bidding/*` glob 命中 img/、img_gen/ 目录→抹掉 x 位→nginx 403。polish v6 已内置安全修复（仅 chmod 文件、目录保 755）。详见 references/chmod-directory-trap.md。
82. ⛔ **桌面改动 → 移动端必验证 (V1.33 — 用户原话「你老是这样只顾一边」)**：每次改 index.html CSS/HTML 后必须三步验证：①桌面端确认 → ②`matchMedia('(max-width:768px)')` 检查规则 → ③确认移动端样式未被 polish 宽泛替换覆盖。**典型漏检**：筛选栏右对齐→手机竖列堆叠；密度切换→手机卡片压扁；overflow:hidden→visible 全局替换误伤手机端。

83. ⛔ **移动端卡片 Twitter 风格重设计 (V1.36 — 最终版: 2列 Grid)**：用户反馈「字太少」「分数没了」「⋯菜单没有」「卡片挤成一坨」→ 多轮迭代最终方案：(a) **2列 Grid** (`1fr auto`)，每个 td 用 `grid-row/column` 精确定位；(b) **kebab-btn CSS 从无到有**——28px 圆 + 弹出菜单 + overlay + kebabIn 动画 + 双主题；(c) 分数独立一行 (`font-weight:700;14px`) + 10px 彩条；(d) 查看按钮蓝色胶囊；(e) **`#btnBackTop` CSS 必须显式定义**——JS 创建按钮但无 CSS 则不可见；(f) **桌面端隐藏 td** (checkbox/序号/客户/招标单位/来源) + 标题 `padding-right:32px` 留 kebab 空间；(g) **`table{min-width:0!important}`** 干掉 800px 最小宽度防溢出。详见 `references/mobile-twitter-card-v36.md`。

84. ⛔ **移动端筛选折叠模式 (V1.36)**：手机端默认隐藏筛选条件，搜索框右侧「☰ 筛选」按钮点击展开/收起。pill 高度 38px、gap 10px、margin-top 10px 保证不拥挤。展开带 filterSlideDown 动画。详见 `references/mobile-filter-toggle-pattern.md`。

85. ⛔ **Feishu 消息链接格式铁律**：在飞书（Feishu/Lark）对话中发送 URL 时，**禁止**用 Markdown 粗体/斜体/星号包裹链接。直接发送裸 URL（如 `https://www.yfzx.online/bidding-test/`），不要用 `**https://...**` 或 `*https://...*`。飞书会自动渲染可点击链接。用户反馈「不要带星号」「打不开」。此规则同时适用于企微推送中的链接。

86. ⛔ **生产环境锁定铁律 (V1.36)**：`/var/www/html/bidding/` 已锁定。未经用户明确下令，绝不改动生产环境任何文件。所有修改先在测试环境 `/var/www/html/bidding-test/` 进行，确认后等用户说「推到生产」才能动。`bash scripts/promote.sh` 执行备份→同步→清理→权限修复。

87. ⛔ **统计卡片今日新增跨Tab口径 (V1.36)**：`brief.today_total = 今天招标数 + 今天中标数`。用户点击「今日新增 2」但表格只显示 1 条 → 另一条在另一个 Tab 里。修复：`renderStatBanner()` 中 today 分支计算 `todayBids` + `todayWins`，横幅显示「📊 今日新增 · 招标X条 + 中标Y条 · 共Z条」。统计卡片保持全局计数不变（`activeStatFilter` 分支），Tab 切换可见另一条。

88. ⛔ **统计卡片高相关跨Tab口径 (V1.36)**：`statHigh` 原先只数 `allB.filter(score>=70)`，漏了 `allW` 中高相关中标。用户点「高相关 14」但中标 Tab 还有 3 条 → 逻辑不统一。修复：全部 `statHigh` 赋值改为 `[...allB, ...allW].filter(i => score>=70).length`（3处：init/updateStats activeStatFilter分支/非分支）。`renderStatBanner()` 中 high 分支参照 today 显示「高相关 · 招标X条 + 中标Y条 · 共Z条」。

89. ⛔ **#btnBackTop CSS 缺失 (V1.36)**：JS 动态创建按钮并监听 scroll 切换 `.show` class，但 CSS 从未定义 → 永远不可见。修复：fixed 定位 40px 圆 opacity 过渡 + light/dark 双主题。铁律：JS 创建的 DOM 元素必须同时写 CSS。

62. ⛔ **Kebab ⋯ 锚定层级 (V1.33)**：kebab（`right:12px;top:12px`）和 NEW badge（`left:14px;top:14px`）必须锚定 `tr.data-row`（`position:relative`）而非 `td.title-cell`。`td.title-cell` **移除** `position:relative`。原因：① kebab 和 NEW 同在 title-cell 内绝对定位 → 重叠不可见；② title-cell 有 `-webkit-box` line-clamp，padding-right 对绝对定位元素无约束力 → kebab 与标题文字重叠。锚定卡片层级后二者永远在卡片边缘，互不干扰。

63. ⛔ **Chat widget 手机端拖动 (V1.33)**：`touchstart/touchmove/touchend`  + `mousedown/mousemove/mouseup` 双支持。`getPos(e)` 归一化坐标（`e.touches?.[0]` or `e.clientX/Y`）。`{passive:false}` 防止页面滚动。`webkitUserSelect` 防止 iOS 选字。拖动时立即切换到 `position:fixed; left/right: px`，松手停在原位。

61. ⛔ **桌面端筛选栏高度对齐 (V1.33)**：搜索框、select、input[type=number/date] 必须统一 `height:36px; box-sizing:border-box`。所有元素都用 `box-sizing:border-box` + 显式 height，不依赖 padding 隐形定高。手机端保持搜索44px/胶囊34px的差异（有意设计）。

62. ⛔ **搜索字段覆盖不完整（致命坑 V1.34）**：搜索仅查 `title`/`owner`/`winner`/`source` 四个字段 → 中标数据的省份在 `province` 字段 → 搜「广东」搜不到中标。**修复**：搜索扩展至 7 字段 — `title`、`procurement_owner`、`winner_company`、`source_site`、**`province`**、**`region`**、**`category`**。`getFilt()` 和 `getFiltFor()` 同步更新。

63. ⛔ **手机端搜索框自动搜索不可靠 → 用搜索按钮（致命坑 V1.33）**：HTML 属性 `oninput=\"doFilter()\"` 和 JS `addEventListener('input')` + `compositionend` 在移动端均不可靠 — iOS Safari 中文拼音输入阶段可能不触发、IME 组合输入时频繁触发导致闪烁。**用户明确要求**：在搜索框右侧加一个「搜索」确认按钮，输入完点按钮或按回车触发。**最终方案（V1.33 最终版）**：① 搜索框右侧放 `<button class=\"search-btn\" id=\"searchBtn\" type=\"button\">搜索</button>`（桌面端36px蓝色、手机端44px iOS蓝 #007aff，input左圆右方拼胶囊）；② `init()` 中用 **`addEventListener('click', doFilter)`** 绑定按钮 — ⛔ 必须用 JS addEventListener，不能用 HTML onclick 属性（移动端不可靠，用户反馈「点这个搜索没反应啊」）；③ `searchEl.addEventListener('keydown', ...)` 回车也触发；④ 移除 `oninput` 属性、移除 compositionend 弹幕监听；⑤ **按钮必须加触感反馈**：`:active{background:#0056cc}` + `-webkit-tap-highlight-color:transparent` + `transition:background .15s` — 用户明确要求「点了要有反应」。

64. ⛔ **统计卡片数字联动筛选 + 跨Tab徽标（V1.34 致命坑）**：用户搜索「浙江」→ 卡片显示「招标 56」而非实际匹配的「5 条」→ 用户困惑「没联动起来」+ 「收藏显示2实际只有1」+ 「中标Tab搜广东无结果」。**修复三合一**：① `doFilter()` 末尾调用 `updateStats(data)` — 有筛选时统计卡片+三个Tab徽标全部显示过滤后数字；② 新增 `getFiltFor(arr)` 将同样筛选独立应用到 allB/allW → 跨Tab徽标同步；③ 搜索字段从 4 扩展到 **7**（+province/+region/+category）。详见 `references/dynamic-stat-cards-v34.md`。

65. ⛔ **统计卡片污染搜索框 → 独立 banner 视图（V1.31）**：用户点「高相关招标 12」→ 搜索框被塞 "70" → 所有卡片数字变过滤后值 → 用户困惑「逻辑不对，应该是单独界面」。**根因**：`statClick('high')` 直接设 `fScore.value='70'` → `doFilter()` → `updateStats()` 检测到 hasFilter=true → 全局卡片全变。**修复**：引入 `activeStatFilter` 状态 + 专属 banner + 统计卡片保持全局计数不变。`getFilt()`/`getFiltFor()` 优先检查 `activeStatFilter`（在手动筛选之前）。`updateStats()` 中 `activeStatFilter` 分支→统计卡片给全局值。`resetF()` 清除 `activeStatFilter`。点击同一卡片 → 取消；点击 ✕ → 取消。详见 `references/stat-card-independent-view-v31.md`。

66. ⛔ **CSS 修复持久化铁律 (V1.32)**：任何对 `index.html` 内联 `<style>` 的修改，必须在 `polish_report.py` 中加对应的字符串替换逻辑（idempotent），否则 `report_generator.py` 下次重写时修复丢失。模式：`if '旧CSS' in html: html = html.replace('旧CSS', '新CSS')`。典型案例：筛选栏 overflow:hidden→visible、kebab-btn display:none→!important。

67. ⛔ **桌面端 CSS !important 陷阱 (V1.32)**：动态注入 HTML（JS 渲染表格行）场景下，浏览器可能静默忽略 `display:none`（getComputedStyle 返回 inline）。必须用 `!important` 强制优先级。同时在 `@media(max-width:768px)` 中用 `!important` 反向覆盖。详见 `references/desktop-css-pitfalls.md`。

68. ⛔ **文档内容策略 (V1.32)**：用户文档（操作手册、FAQ、changelog）中**禁止**出现具体人员/团队名称（如「程浩团队/量子纪元」）。反馈入口统一表述为「通过右下角浮动面板中的反馈入口提交」。内部运维文档不在此限制内。

69. ⛔ **OG 社交分享标签 (V1.32)**：操作手册、changelog、主看板三个页面必须有 `og:title/description/image/url` 元标签。主看板的 OG 已写入 `polish_report.py` 持久化。封面图 `img_gen/og-share.png` 1200×630 从真 Logo 生成。详见 `references/og-social-sharing.md`。
70. ⛔ **CSS @media 隐藏规则顺序 (V1.32)**：桌面端隐藏规则的 `@media(min-width:769px){display:none}` **必须写在基础规则之后**。写在基础规则之前会被后面的 `display:flex/block` 覆盖（同等特异性下后者胜）。正确顺序：先写基础规则 → 再写 @media 隐藏。修复案例：pullIndicator 的 @media 从 `#pullIndicator{...}` 前面移到 `body.dark #pullIndicator.ready{...}` 后面。
71. ⛔ **CSS display:none!important 失效 → JS 条件渲染兜底 (V1.32)**：Browserbase 等远程浏览器中，即使内联 `<style>` 含 `display:none!important`，`getComputedStyle` 仍可能返回 `inline`。此时必须用 JS 层面条件渲染：`window.innerWidth <= 768 ? '<span class="kebab-btn">...</span>' : ''`。验证：`document.querySelectorAll('.kebab-btn').length` 桌面端必须 = 0。详见 `references/desktop-css-pitfalls.md`。
72. ⛔ **文档内容策略 (V1.32)**：用户文档（操作手册、FAQ、changelog）中**禁止**出现具体人员/团队名称（如「程浩团队/量子纪元」）。反馈入口统一表述为「通过右下角浮动面板中的反馈入口提交」。内部运维文档不在此限制内。
73. ⛔ **桌面端 Pull-to-refresh 禁止 (V1.32)**：桌面端（>768px）必须在 IIFE 中用 `el.remove()` 删除 `#pullIndicator` 元素，不仅依赖 CSS。仅在移动端激活 touch 事件监听器。详见 `references/desktop-mobile-separation.md`。
74. ⛔ **筛选栏弹性右对齐 (V1.32→V1.33 修正)**：导出/重置必须与统计卡片右边缘平齐。**错误做法（V1.32 已废弃）**：在 filter-row 内部加 `flex:1` spacer — 此 spacer 在 `.filter-scroll-wrapper{overflow:visible}` 环境下 flex 上下文是 filter-row 本身，推不动外层 filter-bar 边界，导出/重置会溢出。**正确做法（V1.33）**：将导出/重置/psSelector 移出 `.filter-scroll-wrapper`，作为 `.filter-bar` 直接子级，在 wrapper 后加 `<span style="flex:1;min-width:8px">`。此时 spacer 在 filter-bar 层级（与 stat cards 同宽），自然对齐。同时调宽 `.search-row` 至 340px 给筛选胶囊留呼吸空间。polish_report.py 中检测 `<!-- /filter-scroll-wrapper -->` 标记来判断是否已完成结构重构。详见 `references/filter-bar-right-alignment.md`。
75. ⛔ **Logo 源文件位置 (V1.32)**：文鳐智投真 Logo 位于 `img/logo.png`（651×383 RGBA）。从它生成 favicon-32x32(32×32)、apple-touch-icon(180×180)、favicon.ico、og-share(1200×630)。生成后用 `chmod 755` 确保 `img_gen/` 目录可遍历。详见 `references/favicon-spec.md`。
76. ⛔ **flex:1 spacer 上下文陷阱 (V1.33)**：嵌套 flex 容器中，`flex:1` 的扩展空间取决于其**直接父 flex 容器**。当子容器的内容溢出（`overflow:visible` + `flex-wrap:nowrap`）时，子容器内部 spacer 无法推动外层边界。解决方案：将需要右对齐的元素提升到目标 flex 层级的直接子级，spacer 也放在同一层级。典型案例：筛选栏导出/重置从 filter-row 提升到 filter-bar。详见 `references/filter-bar-right-alignment.md`。
77. ⛔ **桌面改动 → 移动端必验证 (V1.33)**：用户明确反感「你老是这样只顾一边」+「手机端又出问题了」。每次改 `index.html` CSS/HTML 后必须验证移动端未受破坏。三步：①改完刷新桌面验证 → ②用 `matchMedia('(max-width:768px)')` 检查移动端规则存在 → ③验证移动端特定样式未被宽泛的 polish 替换覆盖。**典型漏检案例：筛选栏右对齐重构 → 手机端竖列堆叠；V1.33 密度切换 → 手机卡片压扁**。
78. ⛔ **polish_report.py 字符串替换必须精确 (V1.33)**：`html.replace('overflow:hidden', 'overflow:visible')` 会同时命中桌面端和手机端的 filter-scroll-wrapper。**必须用完整上下文**：`html.replace('.filter-scroll-wrapper{flex:1;min-width:0;overflow:hidden}', '.filter-scroll-wrapper{flex:1;min-width:0;overflow:visible}')`。手机端的 `position:relative;overflow:hidden` 不会被误伤。
79. ⛔ **筛选栏右对齐移动端适配 (V1.33)**：桌面端将导出/重置提级到 `filter-bar` 直接子级后，手机端 `filter-bar{display:block}` 导致这些元素竖列堆叠。修复：`@media(max-width:768px)` 中隐藏 bar 级 extras（`filter-bar > span:not(.search-icon), filter-bar > .pg-btns, filter-bar > .btn`），仅保留导出按钮（`filter-bar > .btn[onclick*=\"smartExport\"]`）。详见 `references/desktop-mobile-separation.md`。
80. ⛔ **密度模式必须手机端豁免 (V1.33)**：`body.dense` 的全局规则（行高32px、字号11px）会把手机端卡片视图的 Grid 布局也压扁——padding/font-size 全塌。修复：`@media(max-width:768px)` 内覆盖 `body.dense` 所有关键属性为正常卡片值（`td{padding:0;font-size:13px} tr{height:auto;padding:18px 16px} .star{font-size:16px} .score-bar{display:none}`）。不可用 `display:none` 屏蔽整个 dense 模式——会丢失桌面端用户的密度偏好 localStorage 状态。
81. ⛔ **全站 Logo 替换 SOP (V1.33)**：用户提供新 Logo 图片 → 用 PIL 生成 5 种尺寸（header logo 200px高、favicon 32×32、ICO、apple-touch-icon 180×180、og-share 1200×630）→ `chmod 755` 目录 + `chmod 644` 文件 → 验证 `curl -sI` 全部 200 → 三页面（看板/changelog/手册）统一引用。`report_generator.py` 的 logo src 已是 `/bidding/img/logo.png` 无需改动。⛔ **chmod 644 * 致命陷阱**：`chmod 644 /var/www/html/bidding/*` glob 命中 img/、img_gen/ 目录→抹掉 x 位→nginx 403。polish v6 已内置安全修复（仅 chmod 文件、目录保 755）。详见 references/chmod-directory-trap.md。
82. ⛔ **桌面改动 → 移动端必验证 (V1.33 — 用户原话「你老是这样只顾一边」)**：每次改 index.html CSS/HTML 后必须三步验证：①桌面端确认 → ②`matchMedia('(max-width:768px)')` 检查规则 → ③确认移动端样式未被 polish 宽泛替换覆盖。**典型漏检**：筛选栏右对齐→手机竖列堆叠；密度切换→手机卡片压扁；overflow:hidden→visible 全局替换误伤手机端。

83. ⛔ **移动端卡片 Twitter 风格重设计 (V1.36 — 最终版: 2列 Grid)**：用户反馈「字太少」「分数没了」「⋯菜单没有」「卡片挤成一坨」→ 多轮迭代最终方案：(a) **2列 Grid** (`1fr auto`)，每个 td 用 `grid-row/column` 精确定位；(b) **kebab-btn CSS 从无到有**——28px 圆 + 弹出菜单 + overlay + kebabIn 动画 + 双主题；(c) 分数独立一行 (`font-weight:700;14px`) + 10px 彩条；(d) 查看按钮蓝色胶囊；(e) **`#btnBackTop` CSS 必须显式定义**——JS 创建按钮但无 CSS 则不可见；(f) **桌面端隐藏 td** (checkbox/序号/客户/招标单位/来源) + 标题 `padding-right:32px` 留 kebab 空间；(g) **`table{min-width:0!important}`** 干掉 800px 最小宽度防溢出。详见 `references/mobile-twitter-card-v36.md`。

84. ⛔ **移动端筛选折叠模式 (V1.36)**：手机端默认隐藏筛选条件，搜索框右侧「☰ 筛选」按钮点击展开/收起。pill 高度 38px、gap 10px、margin-top 10px 保证不拥挤。展开带 filterSlideDown 动画。详见 `references/mobile-filter-toggle-pattern.md`。

85. ⛔ **Feishu 消息链接格式铁律**：在飞书（Feishu/Lark）对话中发送 URL 时，**禁止**用 Markdown 粗体/斜体/星号包裹链接。直接发送裸 URL（如 `https://www.yfzx.online/bidding-test/`），不要用 `**https://...**` 或 `*https://...*`。飞书会自动渲染可点击链接。用户反馈「不要带星号」「打不开」。此规则同时适用于企微推送中的链接。

86. ⛔ **生产环境锁定铁律 (V1.36)**：`/var/www/html/bidding/` 已锁定。未经用户明确下令，绝不改动生产环境任何文件。所有修改先在测试环境 `/var/www/html/bidding-test/` 进行，确认后等用户说「推到生产」才能动。`bash scripts/promote.sh` 执行备份→同步→清理→权限修复。

87. ⛔ **统计卡片今日新增跨Tab口径 (V1.36)**：`brief.today_total = 今天招标数 + 今天中标数`。用户点击「今日新增 2」但表格只显示 1 条 → 另一条在另一个 Tab 里。修复：`renderStatBanner()` 中 today 分支计算 `todayBids` + `todayWins`，横幅显示「📊 今日新增 · 招标X条 + 中标Y条 · 共Z条」。统计卡片保持全局计数不变（`activeStatFilter` 分支），Tab 切换可见另一条。

88. ⛔ **统计卡片高相关跨Tab口径 (V1.36)**：`statHigh` 原先只数 `allB.filter(score>=70)`，漏了 `allW` 中高相关中标。用户点「高相关 14」但中标 Tab 还有 3 条 → 逻辑不统一。修复：全部 `statHigh` 赋值改为 `[...allB, ...allW].filter(i => score>=70).length`（3处：init/updateStats activeStatFilter分支/非分支）。`renderStatBanner()` 中 high 分支参照 today 显示「高相关 · 招标X条 + 中标Y条 · 共Z条」。

89. ⛔ **#btnBackTop CSS 缺失 (V1.36)**：JS 动态创建按钮并监听 scroll 切换 `.show` class，但 CSS 从未定义 → 永远不可见。修复：fixed 定位 40px 圆 opacity 过渡 + light/dark 双主题。铁律：JS 创建的 DOM 元素必须同时写 CSS。

90. ⛔ **搜索框 Flex Pill 模式 (V1.38)**：移动端搜索框**禁止**用 `position:absolute` 定位按钮——产生 2px 间隙 + 高度不匹配。正确做法：父容器 `.search-box` 持有 `border-radius:22px;border;overflow:hidden`（pill 外壳），按钮变为 `flex-shrink:0` 自然 flex 子元素。border 在父容器上，input 和 btn 无独立边框。light 主题只需改父容器 border-color。详见 `references/search-box-flex-pill-v38.md`。

91. ⛔ **移动端视口约束 (V1.38)**：手机端横向滚动 → 查三处：(a) `html,body{overflow-x:hidden}` 全局截断；(b) `@media(max-width:768px)` 中所有主容器 `max-width:100vw!important;width:100%!important;box-sizing:border-box`；(c) `polish_report.py` 同步注入防回退。根因是 `max-width:1400px` 未配 `width:100%` → 元素撑到内容自然宽度。详见 `references/mobile-viewport-constraint-v38.md`。

92. ⛔ **CSS 改动双写铁律 (V1.38 强化)**：任何 `index.html` 内联 `<style>` 修改，必须在 `polish_report.py` 对应的 CSS 字符串模板中同步修改。屏蔽 pipeline 重生成覆盖风险。

93. ⛔ **NEW 标签全量误判 — 归档文件从未写入（V1.38 致命坑）**：症状：全部 94 条招标+13 条中标都显示 NEW。根因：`report_generator.py` 打印「归档:2026-06-27」但**从未创建归档目录和文件**。`yesterday_file.exists()` 永远 False → `yesterday_ids` 为空 set → 所有 `id not in yesterday_ids` 都为 True → 全量判 NEW。修复：`generate()` 末尾新增 `archive_dir.mkdir(parents=True, exist_ok=True)` + 写入 `archive_ids`。验证：`ls /var/www/html/bidding/2026-06-2*/data.json` 每日归档文件必须存在。

94. ⛔ **async init() 竞态 + chat-widget 干扰（V1.38 致命坑）**：症状：页面显示0条，统计卡片为0，但 `data.json` 正常返回数据。根因：`<script>init();</script>` 异步调用无 await，且 `chat-widget.js` 在 init() 之后同步加载 → 可能干扰 init() 的 fetch 完成。修复三合一：(a) init() 改用 `DOMContentLoaded` 事件触发 + `.catch()` 错误处理；(b) chat-widget.js 在 init 脚本之前加载；(c) `report_generator.py` 模板 + `polish_report.py` + `index.html` 三处同步。验证：页面刷新后 3 秒内统计卡片从 0 变为实际数。

95. ⛔ **API items 端点 score=0 噪音混入（V1.39 致命坑）**：症状：前端表格展示 157 条招标（含 63 条 score=0 噪音），统计卡片显示 94 条——数字打架。根因：`bookmark_server.py` `query_items()` 默认 `min_score=0`，L1 判别器拒绝的浙能施工/监理/保险类项目全量返回。修复：默认 `min_score=1` 排除 0 分噪音。**中标查询崩溃**：`winning_notices` 表无 `notice_type` 列，查询 500。修复：`'winning' as notice_type`。详见 `references/api-frontend-data-consistency-v39.md`。

95c. ⛔ **今日新增 badge 数字不一致 + Tab badge 诱骗点击（V1.41 四连坑）**：症状：今日新增卡片显示 11，点击后招标=2+中标=16≠11；中标 badge=16 点进去变 3（诱骗）。四重根因——① stats `> 0` vs items `>= 1` 口径不一致 ② `totalBidding = allB.length` 是页码级非全量级 ③ `statClick` 内调 `sw()` 清除刚设的 `activeStatFilter`（自毁）④ `updateApiStats` 非活跃 Tab 用 `realTotal` 而非过滤值 → badge 与实际内容不一致。修复：stats SQL → `>= 1`、独立 fetch 两个 Tab 全量计数、statClick 不调 sw() 直接 apiFilter()、双 Tab 均显示过滤计数。详见 `references/stat-badge-bait-switch-v41.md`。

95d. ⛔ **allB 分页数据 vs totalBidding 全量计数分叉（V1.42→V1.43 性能优化）**：症状：badge=8 但表格只渲染 2 行。根因：`apiFilter()` 中 `allB` 来自 page-1 size=20 的过滤结果（2条），而 `totalBidding` 来自独立 size=200 全量请求的计数（8条）。修复 V1.42：在计数循环中同时把全量过滤数据写回 `allB/allW`。优化 V1.43：为 `activeStatFilter==='today'` 加快速路径——跳过 page-1 请求，用 `Promise.all` 并行拉取两个 tab 全量数据，3 串行→2 并行，HTTP 耗时减少 67%。详见 `references/apiFilter-allB-page1-vs-total-full-divergence.md` 和 `references/apiFilter-today-fast-path-parallel.md`。

95e. ⛔ **大型 JSON 客户端过滤浪费带宽 → 服务端应做过滤（V1.44）**：点今日新增 3-4 秒无响应。API 返回 306KB 全量（103条），客户端过滤后只需 24KB（8条）——浪费 93%。修复：`bookmark_server.py` 新增 `is_new_today=1` 查询参数 + `get_yesterday_ids()` 内存缓存。铁律：客户端过滤场景优先在服务端支持查询参数。详见 `references/api-performance-caching-prefetch.md`（含三层优化：服务端过滤→Cache-Control→后台预加载）。

95f. ⛔ **API 响应无缓存 → 每次切Tab重拉（V1.45）**：`Cache-Control: public, max-age=30` 让浏览器 30s 内从 disk cache 返回，零网络耗时。`_json()` 方法统一注入。配合 `init()` 中后台 `fetch()` 预热中标 Tab URL，首次点击即缓存命中。

> 📖 今日新增性能优化完整文档见 `references/api-performance-caching-prefetch.md`<br>
> 📖 allB/totalBidding 分叉修复见 `references/apiFilter-allB-page1-vs-total-full-divergence.md`<br>
> 📖 PPT/演示文稿制作规范见 `references/ppt-presentation-style.md`

95b. ⛔ **今日新增 is_new_today 与 publish_date 不一致 + stats 口径偏差（V1.40-1.41 致命坑）**：①症状：统计卡片「今日新增」显示 1，点进去空白。根因：stats API 用「ID 昨天不存在」(`get_yesterday_ids()`) 算 today_total → 给每个 item 设 `is_new_today` 标志。但前端 `apiFilter()` 给服务器传 `date_from=today`，服务器按 `publish_date` 过滤 → 很多新标的 `publish_date` 为空 → 0 结果。修复：前端不用 `date_from` 传日期参数，改为客户端按 `is_new_today === 1` 过滤，与 stats 同源同算法 100% 一致。②症状：stats today_total 与 items API 过滤结果数量不一致（如 today_total=11 但实际过滤出 18 条）。根因：stats 用 `relevance_score > 0` 计数，items 默认 `min_score >= 1`。0~1 分之间项目被 stats 计入但不被 items 返回。修复：stats 三处 SQL 改为 `>= 1`。详见 `references/api-dual-path-divergence-pitfalls.md`。

96. ⛔ **统计卡片跨Tab计数不一致（V1.39 致命坑）**：症状：点击「高相关项目 26」→ 累计招标=21（正确），累计中标=13（错误，应为 5 条高分中标）。根因：`apiFilter()` 只查当前 Tab（type=bidding），`totalWinning` 未更新。`updateApiStats()` 无脑用两个全局变量覆盖四张卡片。修复：`activeStatFilter` 激活时额外 fetch 另一 Tab 的 filtered total，使 `totalBidding` 和 `totalWinning` 同时反映筛选后计数。详见 `references/api-frontend-data-consistency-v39.md`。

97. ⛔ **API 迁移 UI 回归防范 (V1.39)**：为已有功能添加并行代码路径时（如 data.json 全量 → API 分页），必须逐项对比旧路径的 UI 组件——回到顶部、页码按钮、页码信息、收藏星、Kebab ⋯、查看链接、筛选折叠、Star 过滤、数据源、Async 竞态。**添加新代码路径后必须跑 10 项自检清单**。详见 `references/api-migration-regression-checklist.md`。

98. ⛔ **API/降级双路径分叉陷阱 (V1.40)**：`app.js` 支持两条数据路径（API + data.json 降级），共享 `renderTable`/`sw`/`updateApiStats`。**任一共享函数对路径假设不一致 → 一条路径崩溃**。**12 大陷阱**：①守卫条件依赖可变全局（star 过滤后 `allB=[]` 误封 `sw()`）②函数仅存在降级路径（`emptyMsg` 局部变量被 API 路径引用）③函数名不一致（`loadBookmarks` vs `loadBookmarksFromServer`）④catch 块永久锁死 `useApi=false` ⑤全局计数被过滤覆盖（`totalBidding` 被 star/stat 过滤污染 Badge）⑥activeStatFilter 类型未传递 API 参数（今日新增未设 `date_from`）⑦HTML 版本号未同步 → 浏览器缓存旧 JS ⑧**Async 竞态 — 可变全局在 await 期间被篡改**（`starOnly`/`tab`/`activeStatFilter` 需在入口快照为 `const`，详见 `references/async-snapshot-pattern.md`）⑨**Badge 三态判定**（`activeStatFilter && !starOnly` 过滤值，否则锚定值）⑩renderTable 翻页信息 star 过滤时用错数据源（应用 `data.length` 非 `total`）⑪空数据时翻页按钮未清空（漏清 `pgNums`）⑫`sw('star')` 未清除 `activeStatFilter`（stat 过滤泄漏入收藏视图）。⑬**`is_new_today` vs `publish_date` 过滤口径不一致**（stats 用 ID 差集 → API 用 date_from → 空 publish_date 导致空白）。⑭**stats `>0` vs API `>=1` 口径偏差**（0~1分被 stats 计入但不被 items 返回 → today_total≠ 过滤结果和）。⑮**`statClick` 调 `sw()` 自毁 `activeStatFilter`**（内部导航触发用户切Tab清除逻辑 → filter 设完即被清 → 筛选失效，详见 `references/stat-click-sw-self-destruct.md`）。⑯**Tab badge 诱骗点击**（非活跃 Tab badge=全局值，切过去变过滤值 → 数字欺骗，详见 `references/tab-badge-bait-switch.md`）。⑰**allB 页面数据 vs totalBidding 全量计数分叉**（badge=8 卡片=2 → allB 是 page-1 过滤结果，totalBidding 是全量计数，详见 `references/apiFilter-allB-page1-vs-total-full-divergence.md`）。详见 `references/api-dual-path-divergence-pitfalls.md`。

91. ⛔ **crawl_pipeline 10路适配器 + 导入路径修复 (V1.36)**：管线原先只有 5 路，且南网适配器导入路径错误(`site_adapters` 应为 `dedicated_adapters`)从未运行。修复后接入 10 路：+国电投、+能建、+三峡、+江苏平台、+申能。参数名匹配：`crawl_nanwang(max_items=N)` 非 `max_pages`。

92. ⛔ **JS 模板字符串 TDZ 陷阱 (V1.36)**：`const` 变量在模板字符串 `${var}` 中先引用后声明 → ReferenceError 中断 doFilter() → 页面静默显示 0 条。排查：浏览器 Console 手动 `init()` 找报错。详见 `references/js-template-literal-tdz-pitfall.md`。
59. ⛔ **Apple 设计迭代铁律 (V1.30-V1.32)**：①**禁止彩色按钮**——`link-btn` 手机端 `display:none`，卡片本身可点击；②**禁止彩色统计值**——所有 stat-value 统一 `#1d1d1f`，不用 accent/green/amber 区分；③**Grid 在 tr 层非 td 层**——`tr.data-row{display:grid;grid-template-columns:1fr auto auto auto}`，每个 td 用 `grid-row/column` 定位；④**自明字段隐藏 label**——地域/日期/相关度不显示 `::before` 标签，用 `·` 分隔成一行；⑤**标题 2 行截断**——`-webkit-line-clamp:2`；⑥**分数带语义后缀**——显示 `85分` 非 `85`；⑦**手机端交互用菜单非长按**——用户明确表示「长按分享反人类」，改用 ⋯ 按钮+弹出菜单；⑧**卡片点击双态**——手机端 `window.open(url)`，桌面端 `toggleDetail`。

> 详细案例见 `references/data-freshness-pitfalls.md`
> ⛔ NEW 语义设计原则见 `references/new-badge-semantics-v18.md`
> 适配器正则陷阱见 `references/zheneng-adapter-regex-fix.md`
> todayOnly 模式规范见 `references/stat-card-click-consistency.md`

> 用户原话：「现在有了单独的收藏TAB，那之前那个只看收藏的按钮就没有意义了吗？删掉，你作为产品经理再审视一下交互，还有问题吗？？？用点心」

**每次加Tab/新功能后的PM自检清单**：

1. **冗余入口检查**：新Tab上线后，旧有的同功能filter/sidebar按钮是否成了多余入口？→ 立即删除，避免认知负担
2. **Tab切换状态清理**：`selectedIds.clear()` — 勾选不跨Tab污染。`starOnly` 离开收藏Tab必须 `false`
3. **空状态设计**：收藏Tab 0条 → "⭐ 暂无收藏，在招标列表中点击 ☆ 即可收藏"（引导性文字，不是空白页）。搜索无结果 → "🔍 没有匹配的结果，请调整筛选条件"
4. **上下文保持**：统计卡片点击不强制跳Tab——在收藏Tab点"今日新增"应保持收藏视图
5. **死代码清理**：删按钮 → 同时删函数 + DOM引用 + resetF()引用。不删干净 = 控制台报错
数据新鲜度：is_new 是否基于 publish_date 实时判断（不是 DB DEFAULT 1 也不是 fetch_date）？NEW 图标是否只出现在今日发布项？
7. **统计卡片交互一致性**：4 张卡片是否都有 `onclick` + `cursor:pointer`？
8. **Header 空状态**：`crawl_log` 为空时站点信息是否隐藏（不显示"0/0"）？
9. **日期筛选持久化**：日期禁止进 `saveFilters`——它是临时上下文，24小时后无意义

**交互冗余典型案例**：
| ❌ 冗余 | ✅ 精简后 |
|:--|:--|
| 筛选栏 `⭐ 收藏` 按钮 + 收藏Tab 两个收藏入口 | 仅保留收藏Tab，筛选栏按钮删除 |
| `swStar()` toggle 函数 + `btnStar` DOM引用 | 全部删除，`resetF()` 清理引用 |

> 详细技术规范见 `references/interaction-system-v13.md`
> PM审查详细案例见 `references/pm-interaction-review-v14.md`

## 交互技术参考

## 🤖 OpenCode 编程代理 — DeepSeek 驱动

自 2026-06-29 起，所有前端/后端代码修改**优先委托 OpenCode**（provider-agnostic 编程代理），DeepSeek API 驱动。不再手工逐行 patch。

### 安装配置（已完成）

```bash
npm install -g opencode-ai@latest  # v1.17.11
```

**配置**：`~/.config/opencode/opencode.jsonc`：
```json
{
  "provider": {
    "deepseek": {
      "provider": "openai-compatible",
      "baseURL": "https://api.deepseek.com/v1"
    }
  }
}
```

**关键点**：① provider 类型必须用 `openai-compatible`（非 `openai`）；② 不在 config 中写 apiKey——通过 `DEEPSEEK_API_KEY` 环境变量注入（AI SDK 约定：`{PROVIDER}_API_KEY`）。

### 便捷命令

```bash
opencode-ds run "修复 app.js 的分页 bug" --model deepseek/deepseek-chat
```

`opencode-ds` 包装器（`/usr/local/bin/opencode-ds`）自动从 Hermes `.env` 读取 key 并注入。

### 使用模式

| 场景 | 命令 |
|:--|:--|
| 修 Bug / 小改动 | `opencode-ds run "..." --model deepseek/deepseek-chat` |
| 大型重构 | `opencode-ds run "..." --model deepseek/deepseek-v4-pro` |
| 只读分析 | `opencode-ds run "Read X and report..." --model deepseek/deepseek-chat` |

### 目录权限

OpenCode 只能访问工作目录内的文件。要操作 `/var/www/html/bidding-test/` 下的文件，必须 `cd` 到该目录再调 `opencode-ds`。访问外部目录需 `--add-dir` 或提前 `cp` 文件到工作目录。

### 陷阱

- **不要用 Claude Code**：已安装（v2.1.195）但只认 Anthropic API，DeepSeek 不可用。
- **`--model` 格式**：`deepseek/deepseek-chat`、`deepseek/deepseek-v4-pro`、`deepseek/deepseek-reasoner`
- **Hermes 输出 redaction**：bash 脚本中的 API key 会被替换为 `***`。Python 包装器可通过运行时读文件规避。

## 文件操作安全规则

### 禁止操作
- 不要用 read_file / hermes_tools.read_file 读取后直接 write_file 写回 -- read_file 输出含 LINE_NUM| 行号前缀, 写回会永久污染文件
- 不要在 execute_code 中操作含 f-string 转义的文件 -- escaped-drift 导致匹配失败
- ⛔ **patch 工具跨行替换陷阱**：`patch(mode='replace')` 的 `new_string` 跨多行时，换行符会被写成字面量 `\\n` → SyntaxError。JS/Python 文件跨行替换改用 `terminal + python3 heredoc`。详见 `references/patch-tool-literal-newline-pitfall.md`

### 致命坑: report_generator.py 的 f-string 花括号转义
`report_generator.py` 的 HTML 模板是 Python f-string，CSS 中的花括号必须用 `{{` `}}` 转义。
**用 terminal + Python heredoc 修改此文件时**，old_string/new_string 中必须包含 `{{` 双花括号。
用 patch 工具操作此文件时正则易 escape-drift，**优先用 terminal + Python heredoc**。

### 致命坑: extract_detail_fields 缺失
修改 relevance_scorer.py 时 **必须保留** `extract_detail_fields(text) -> dict` 函数及配套正则 (BIDDER_PATTERNS / WINNER_PATTERNS / AMOUNT_PATTERNS)。bidding_engine.py 依赖此函数从详情页提取招标人/中标人/金额，缺失则 `ImportError` 扫描崩溃。
验证: `python3 -c "from scripts.relevance_scorer import extract_detail_fields"`

### 正确操作
- 读取+写回: 用 terminal + python3 -c "open('f').read()" 或直接 cat
- 修改文件: 用 patch 工具 (短片段) 或 terminal + Python heredoc 脚本
- 修复已污染文件: python3 逐行 re.sub(r'^\d+\|', '', ...)

## 用户偏好

### 默认风格
- 默认明亮主题 (body class="light") -- 不是暗黑
- 切换按钮显示 🌓 (暗黑模式显示 ☀️)
- localStorage key: theme

- 版权格式固定：© 中南电力设计院数智科技 · 文鳐智投 2026
  所有页面和推送统一: (c) 中南电力设计院数智科技 · 文鳐智投 2026

### 品牌与署名铁律

⛔ **用户文档和页面中禁止出现「量子纪元」「程浩团队」等内部团队/人名**。所有面向用户的页面（看板、更新日志、操作手册、FAQ、培训PPT、培训通知等）统一署名为「中南电力设计院数智科技」。内部运维文档（如本 skill、运维脚本注释）可保留内部命名。

V0.1 changelog 中「程浩团队 · 量子纪元」是历史记录，但新创建的对外页面不得照搬。

### Favicon / 标签页图标

所有页面必须用文鳐智投 Logo 做 favicon。从 `img/logo.png` 生成 3 个尺寸（32×32 PNG, ICO, 180×180 Apple），在 `<head>` 中注入 3 条 `<link rel="icon">`。`polish_report.py` 幂等注入保持报告重生成后不丢失。详见 `references/favicon-spec.md`。

**企微推送 v8.2 — 精简版+近7日补位+无新增保底**

**v8.2（2026-06-29）三大改进**：
1. **不足 5 条时近 7 日补位**：今日新增不足 5 条时，自动从近 7 日 ≥50 分项目中补位至 8 条。引导语区分「（今日N条 + 近期M条）」/「（今日新增）」/「（近7日）」。解决单日断档推送太少的问题。
2. **无新增时仍然推送**：不再静默 return。发送文本状态消息 `📋 文鳐智投标监控 · 今日无新增≥50分招标\n累计招标 X 条 | 中标 Y 条 | ≥50分 Z 条\n👉 {REPORT_URL}`。⛔ 铁律：**每天至少有一条可见推送**。
3. **conn.close() 顺序修复**：统计查询（total_bid/total_win）必须在 `conn.close()` 之前执行，否则 SQLite 报错。

**推送内容**：1 条引导语 + 最多 8 张招标卡片。引导语自动标注数据来源（今日/近期混合/全近期）。

**已删除**：摘要 Markdown、中标引导语+卡片、大标预警 ≥500万、早晚间分段（☀️/🌙）。

**⛔ 企微推送防重复锁**：

**问题**：同一天内多次调用 `wecom_push.py`（管道调用 + 手动补推 + batch_crawler 补推）导致群消息爆炸。

**机制**：`/tmp/wenyao_push.lock` 记录最后推送日期，同一天第二次调用直接跳过。
```python
PUSH_LOCK = "/tmp/wenyao_push.lock"
lock_date = open(PUSH_LOCK).read().strip() if os.path.exists(PUSH_LOCK) else ""
if lock_date == today:
    print("今日已推送过，跳过")
    return
with open(PUSH_LOCK, 'w') as f:
    f.write(today)
```
- 每天首次 push 创建锁，同天后续全部拦截
- 锁文件当天有效，第二天自动失效

**评分阈值适配（⛔ 致命坑）**：旧版用 `>=7`（10分制），新评分引擎用100分制。v8 修复：SQL `>=50`、emoji `≥70🟢 / ≥50🟡 / <50⚪`。

**封面已固化**：8 张固定图 `/bidding/img_gen/covers/cover_1~8.png`，循环使用。⛔ **不要再启用 AI 封面生成**。

**KILL_SWITCH**：`wecom_push.py` 中 `KILL_SWITCH = False`（2026-06-26 已开启）。恢复推送前确保删除 `/tmp/wenyao_push.lock`。

**⛔ 静态资源目录权限（致命坑）**
**所有 `/var/www/html/bidding/` 下的子目录必须是 755 权限**（nginx 需要 x 执行位才能遍历目录读取文件）。644 文件 + 755 目录 = 正确；754 目录 = nginx 403/404。

已知易出问题目录：
- `img_gen/` — 封面图目录（pipeline 阶段4 有 `chmod -R 755` 兜底）
  - ⚠️ **企微推送封面 404 典型症状**：桌面端 Webhook 能显示数字封面，手机端显示乱码/空白。根因 90% 是 `img_gen/` 或 `covers/` 目录缺 x 位 → nginx 无法遍历。修复：`chmod 755 /var/www/html/bidding/img_gen /var/www/html/bidding/img_gen/covers`。手机端 Webhook 客户端对网络错误的容忍度低于桌面端。详见 `references/nginx-config-pitfalls.md`。
- `img/` — Logo 等静态图（容易遗忘，导致 changelog 等页面的 logo.png 404）
- `data/` — bookmarks.json 等

**修复命令**：`chmod 755 /var/www/html/bidding/{img,img_gen,data}`

**预防**：每次创建新子目录后立即 `os.chmod(path, 0o755)`。如有新HTML引用静态资源，生成报告后一并检查 `curl -sI` 确认200。

**⛔ systemd 服务 Python 路径陷阱（2026-06-25 致命教训 — 全站停摆）**

**症状**：定时任务每天准时跑，日志显示 `ModuleNotFoundError: No module named 'bs4'`，三路采集（1a/1b/1c）全部崩溃，仅 chromium 勉强跑但 0 入库。数据永远停在旧值，企微不推新数据。用户质问「定时任务都在干嘛？？」

**根因**：systemd 服务运行在干净环境中，`python3` 解析为系统 Python（`/usr/bin/python3`），它受 PEP 668 保护，未安装 `bs4`/`lxml`/`requests` 等爬虫依赖。这些包只装在 Hermes venv（`/usr/local/lib/hermes-agent/venv/bin/python3`）。

**错误路径**：`/usr/bin/python3`（系统 Python，无 bs4）  
**正确路径**：`/usr/local/lib/hermes-agent/venv/bin/python3`（Hermes venv，含全部依赖）

**修复 SOP**：
1. 所有 shell 脚本（`pipeline_master.sh`、`push_daily_report.sh`）定义 `PY="/usr/local/lib/hermes-agent/venv/bin/python3"` 并全局替换 `python3` → `$PY`
2. 所有 systemd service 文件设置 `ExecStart=/usr/local/lib/hermes-agent/venv/bin/python3 /path/to/script.py`
3. `systemctl daemon-reload` 后验证：`systemctl start wenyao-pipeline && journalctl -u wenyao-pipeline -f` 确认无 ModuleNotFoundError

**验证命令**：
```bash
# 检查哪个 python3 有问题
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin which python3
# 模拟 systemd 环境测试导入
env -i PATH=... python3 -c "import bs4; print('OK')"
```

**已修复的服务/脚本**：
- `/etc/systemd/system/wenyao-pipeline.service` — `ExecStart` 通过 `pipeline_master.sh` 的 `$PY` 变量
- `/etc/systemd/system/wenyao-dailyreport.service` — `ExecStart` → `push_daily_report.sh` 的 `$PY`
- `/etc/systemd/system/wenyao-selfheal.service` — `ExecStart` 直接改为 venv Python
- `/etc/systemd/system/wenyao-memory.service` — `ExecStart` 直接改为 venv Python
- `scripts/nginx_guard.sh` — Hermes cron 调用的 watchdog，重启 bookmark_server 时必须用 venv Python（`/usr/local/lib/hermes-agent/venv/bin/python3`），不能用裸 `python3`。2026-07-02 修复。

**⛔ Nginx 配置崩溃恢复（2026-06-25 致命教训）**

**❌ 错误操作导致整站 404**：
- `cp /etc/nginx/sites-available/wiki /etc/nginx/sites-enabled/wiki` 时，`sites-available/wiki` 只有 Wiki 代理配置，覆盖掉了 bidding location
- 恢复后 `limit_req zone=static` 不存在导致 nginx 启动失败
- 整个 bidding 站点全站 404，Nginx guard 报警

**✅ 安全操作 SOP**：
1. **永远先备份**：`cp /etc/nginx/sites-enabled/wiki /etc/nginx/sites-available/wiki`（从 enabled 往 available 备份，不是反过来！）
2. **修改后立即 `nginx -t`**：语法错误比配置丢失好一万倍
3. **验证所有关键端点**：改完 nginx 后 `curl -sI` 检查 `/bidding/`、`/bidding/img/logo.png`、`/bidding/data.json`、`/bidding/api/`
4. **limit_req zone 必须先在 nginx.conf 的 http 块定义**：`limit_req_zone $binary_remote_addr zone=static:10m rate=8r/s;`
5. **location 不可嵌套**：`location = /bidding/data.json` 不能放在 `location /bidding/` 内部

**⛔ data.json 尺寸策略（2026-06-25 关键优化）**

**问题**：`data.json` 包含完整的 DB 行（含 `raw_html` 等大字段），153 条招标 → **6.2MB**。浏览器加载超时 30 秒，页面显示空数据。

**解决方案**：
1. **精简字段**（`report_generator.py` 的 `trim()` 函数）：
   - 数值字段保持 number 类型：`id, relevance_score`（否则 `app.js` 的 `sc.toFixed()` 崩溃）
   - 文本字段截断：`title, url, source_site, procurement_owner, region, category, budget_amount` 等
   - 删除 `raw_html`、`created_at` 等前端不需要的字段
   - 结果：6.2MB → **87KB**（减少 98.6%）
2. **首页只给 TOP 50**：`data.json` 含50条招标+50条中标，前端 `has_more` 标识
3. **分页文件**：`data_bid_p{1..N}.json` + `data_win_p{1..N}.json`（每页100条精简字段）
4. **全量保留**：`data_full.json` 保留完整字段（仅归档用，不由前端加载）

### 关键修复 (2026-06-24)

**⛔ 主动更新 changelog（最易遗忘）：**
每次代码改动后，必须立即更新 `/var/www/html/bidding/changelog.html`。用户已多次催促「日志更新了没有？！不要让我老提醒你」。这是铁律：
- 新功能 → 新版本号 (V1.X) → 写入 changelog
- 修复反馈 → 修复完 → 写入 changelog
- 任何可见变化 → 写入 changelog
- 不写入 = 用户看不到 = 等于没做
- **⛔ changelog 版本号必须和管线主版本对齐**：如果管线是 V1.37，changelog 写 V1.37，不能自创版本序列（如 V1.21）。用户会纠正。

**自然语言对话系统（V4 - GLM-5.2 驱动 + 可点击链接 + 反馈合并 + 拖动）：**

⚠️ **v4 当前状态（2026-07-20）**：chat_engine.py v4 直接从 Hermes `config.yaml` 读取 LLM 配置，与文鳐智投本体完全同款（GLM-5.2 @ szkj.site）。v3 的 ARK 变量名/注释/默认值已全部清除。

⛔ **v4 关键要点（2026-07-20）**：
- 变量名：`LLM_API_KEY / LLM_BASE_URL / LLM_MODEL`（不再用 `ARK_*`）
- 当前 config: `base_url=https://www.szkj.site:18002/v1`, `model=GLM-5.2`, `provider=custom`
- 换 provider 只需改 config.yaml + 重启 bookmark_server，不需要改代码
- ⛔ **前后端文案同步铁律**：切换 LLM provider 后必须同步更新 `chat-widget.js` 欢迎语中的模型名称。历史教训：后端早已切到 GLM，前端还写着「DeepSeek 大模型」
- GLM 模型可能返回 `reasoning_content` 而非 `content`，需要 fallback 取值
- ⚠️ nginx_guardian 已关闭，bookmark_server 挂了不会自动重启，需手动用 `terminal(background=true)` 启动
- 完整诊断流程、provider 切换 SOP、历史记录详见 `references/chat-engine-provider-switch.md`

**架构四层**：
1. **后端 `chat_engine.py` v3**：
   - 从 `config.yaml` 读取 ARK API key / base_url / model（与 Hermes 共用）
   - `get_db_snapshot()` 对每条招标/中标输出 `🔗 {url}` 行
   - System Prompt 强制规则：「提到任何具体项目时，必须用 `[项目名称](完整URL)` 格式附带链接」
   - GLM 返回 `reasoning_content` fallback：`content = message["content"] or message.get("reasoning_content")`
2. **前端 `chat-widget.js` v4**：
   - `addMsgV2()` 渲染 Markdown 链接：`[text](url)` → `<a href="url" target="_blank" class="chat-link" rel="noopener">`
   - 链接在新标签页打开，不影响对话面板
3. **样式 `chat-widget.css` v5**：
   - 新增加 feedback mode 样式（`.chat-fb-panel`、`.chat-fb-submit`、`.chat-preset-fb` 橙色高亮）
   - 拖动光标 `cursor:grab/grabbing`
   - 暗/亮双主题适配
4. **拖动系统**：`mousedown` on wrapper全局（排除交互元素）→ `mousemove` 移动 → `mouseup` 释放。**折叠触发条+展开面板都必须能拖**。3px防抖死区。`openChat()` 重置到默认右下角。

**⚠️ 监控页面 chat-widget.js 丢失（致命坑 — 2026-06-25）**：

**症状**：监控页面 `index.html` 右下角无对话按钮，AI 助手不出现。`curl | grep chat-widget` 返回空。

**根因**：`report_generator.py` 生成的 `index.html` **不包含** `<script src="chat-widget.js">` 引用。每次重新生成监控页面后，聊天组件脚本标签丢了。

**修复**：在 `index.html` 底部 `</body>` 前添加：
```html
<script src="chat-widget.js?v=4"></script>
```

**预防**：
- `polish_report.py` 的 `polish()` 函数已永久注入聊天组件引用（2026-06-25），**幂等检查**：
  ```python
  # 幂等注入 —— 已存在则跳过，防止重复
  if 'chat-widget.css' not in html:
      html = html.replace("</head>", '<link rel="stylesheet" href="/bidding/chat-widget.css?v=4">\n</head>')
  if 'chat-widget.js' not in html:
      html = html.replace("</body>", '<script src="/bidding/chat-widget.js?v=4"></script>\n</body>')
  ```
- ⛔ **非幂等注入的后果 (2026-06-25)**：每次 `polish_report.py` 运行都会追加一份 chat-widget 引用，导致页面同时出现 2 个 chat-trigger + 2 个 chat-panel，对话组件互相覆盖。
- `report_generator.py` 生成后自动调用 `polish_report.py`，此后无需手动添加
- 每次重新生成监控页面后，`curl -s https://www.yfzx.online/bidding/ | grep -c chat-widget` 必须返回 ≥2

**💬 用户反馈系统（V1.26 — 已合并入聊天面板 + 可拖动）：**

**V1.26 架构**（反馈集成进 chat-widget v4）：
```
chat-widget (v4) ─── 对话模式 (chat-normal-area)
               └── 反馈模式 (chat-fb-panel) — toggleFeedbackMode() 切换
               └── 拖动 — mousedown on #chatWidgetAll wrapper（折叠触发条+展开面板都能拖）
```
- **反馈入口**：头部 📝 按钮 + 预设栏「📝 反馈问题」（橙色边框高亮）+ 欢迎消息提示
- **切换逻辑**：`window.toggleFeedbackMode()` → 隐藏 `chat-normal-area`，显示 `chat-fb-panel`，📝 按钮变红
- **提交**：`window.submitChatFeedback()` → POST `/bidding/api/feedback` type=general
- **拖动**：监听 wrapper 全局 mousedown（排除 button/input/textarea/a/preset/img），3px 防抖死区。`openChat()` 重置到默认右下角 fixed 定位。**折叠和展开双状态都必须能拖**。详见 `references/chat-widget-v4-feedback-merge.md`

**V1.25 架构**（已废除，仅供历史参考）：
```
独立悬浮按钮 💬 → 侧滑面板(400px) → POST /bidding/api/feedback
    → bookmark_server.py(type=general) → feedback.json + HOT_MEMORY.md
    → 凌晨 selfheal_3am.py 读取分析 → 自动修复
```

**V1.26 组件清单**：
| 层级 | 文件 | 注入方式 |
|:--|:--|:--|
| CSS | `chat-widget.css?v=5` | `polish_report.py` 注入 `<link>` |
| JS | `chat-widget.js?v=5` | `polish_report.py` 注入 `<script>` |
| 反馈API | `bookmark_server.py` `handle_post_feedback` | 直接修改源文件，支持 `type=general` |

> 详细架构见 `references/chat-widget-v4-feedback-merge.md`

**API 变更**：`bookmark_server.py` `handle_post_feedback` 新增 `type='general'` 支持：
- `type='general'` 时 `item_id` 可选（默认 `'general'`）
- 不限频提交（仅 `like`/`dislike` 有 IP 去重）
- 通用反馈和点踩都写入 HOT 记忆

**验证**：
```bash
# 检查页面包含反馈组件
curl -s https://www.yfzx.online/bidding/ | grep -c "fb-fab"
# 必须 ≥1
# 测试反馈提交
curl -s -X POST https://www.yfzx.online/bidding/api/feedback \
  -H 'Content-Type: application/json' \
  -d '{"type":"general","reason":"测试"}'
# 预期：{"ok": true, "entry": {...}}
```

> 完整架构见 `references/feedback-system-architecture.md`

**⚠️ API 服务器架构澄清（避免混淆）**：
- **没有** 独立的 `api_server.py` 文件（如已丢失，不必寻找或重建）
- 端口 8090 上运行的是 `bookmark_server.py`，它统一处理所有 API 路由：
  - `GET/POST /chat` - 自然语言对话（导入 chat_engine.py v4 -> GLM-5.2 @ szkj.site）
  - `GET /data` - 数据查询 API
  - `GET/POST /feedback` - 反馈收集（点踩自动写入 HOT_MEMORY.md）
  - `GET/POST /` - 书签同步
- 进程名在 `ps` 中显示为 `bookmark_server.py`，不是 `api_server.py`
- Nginx 反代：`/bidding/api/` -> `127.0.0.1:8090`
- ⛔ 改完 `chat_engine.py` 必须重启 `bookmark_server.py`（kill + 用 Hermes venv python 重启）
- ⛔ `chat_engine.py` v4 的 LLM 配置从 `config.yaml` 动态读取（变量名 `LLM_*`），换 provider 只需改 config.yaml + 重启 bookmark_server，不需要改代码
- ⛔ 换 provider 后必须同步更新 `chat-widget.js` 欢迎语中的模型名称（前后端文案同步铁律）
- nginx_guardian.timer 已重新启用 (2026-07-20)，每分钟检测 bookmark_server 并自动重启
- 诊断流程和 provider 切换 SOP 详见 `references/chat-engine-provider-switch.md`

**⚠️ 版本号同步铁律（致命坑）**：
修改 `chat-widget.js` 或 `chat-widget.css` 后，必须在 **5 处** 同步 bump 版本号：
- `chat-widget.js` 内部的 CSS link（`chat-widget.css?v=N`）
- `index.html` 的 `<link rel="stylesheet" href="chat-widget.css?v=N">` + `<script src="chat-widget.js?v=N">`
- `changelog.html` 的 `<script src="chat-widget.js?v=N">`
- `daily_report.py` 模板中的 CSS + JS 两处 `?v=N`
- 已生成的 `report-*.html` 文件中的 CSS + JS 引用

修改流程：`patch` 工具分别改4处 → 验证 `grep -r 'chat-widget.*v=' /var/www/html/bidding/` 确认版本号一致。

**v4 基础（当前）**：
- `chat_engine.py` v4：从 `config.yaml` 读取 LLM 配置（当前 GLM-5.2 @ szkj.site），变量名 `LLM_*`（非 `ARK_*`）。注入实时数据库快照。v2 DeepSeek 已废弃（欠费），v3 ARK coding endpoint 已废弃。
- 多轮对话：前端维护 `chatHistory` 数组，每次携带最近10轮
- API 端点：`POST /bidding/api/chat` 接收 `{"question":"...", "messages":[...]}`
- 预设问题 6 条来自 `chat_engine.PRESET_QUESTIONS`
- 前端触发条 + 3秒首次自动弹出
- ⛔ GLM 返回字段：优先取 `message.content`，为空时 fallback 到 `message.reasoning_content`
- ⛔ 换 provider 只需改 config.yaml + 重启 bookmark_server，不需要改 chat_engine.py 代码
- ⛔ 前端 `chat-widget.js` 欢迎语必须与实际后端模型名一致（当前显示「GLM-5.2 大模型」）
- nginx_guardian.timer 已重新启用 (2026-07-20)，每分钟检测并自动重启 bookmark_server

**反馈→修复→日报→日志 闭环（致命坑）：**
⚠️ 修完爬虫/评分逻辑后，DB 中的**旧数据不会自动更新**。必须：
1. 修改适配器提取逻辑
2. 用原始 URL 验证提取正确
3. `UPDATE` 语句回填已存在的旧记录
4. **重生成日报**：`python3 scripts/daily_report.py`（否则用户看到的是旧报告）
5. 用 `grep` 确认新数据出现在报告中

此流程已固化为 `auto-feedback-fix` skill——每次会话启动时自动检查 `feedback.json`，有新反馈直接走这5步。

**书签服务端同步 + 反馈闭环 + 日报系统 + 数据API（V1.7）：**

**数据查询 API（新增 2026-06-24）：**
- `GET /bidding/api/data?type=bidding|winning&limit=50&min_score=50&days=30&q=关键词`
- 返回实时 JSON：`{ok, type, total, data: [{id, title, url, budget_amount, region, procurement_owner, ...}]}`
- 实现在 `bookmark_server.py` 的 `handle_get_data()` 方法
- Nginx 反向代理 `/bidding/api/` → `127.0.0.1:8090`

**书签同步 API：**
- `bookmark_server.py`（端口8090）：Python HTTP 微服务，Nginx 反向代理 `/bidding/api/` → `127.0.0.1:8090`
- `app.js` v8：`toggleStar()` 后自动 `syncBookmarksToServer()` POST 书签；`loadBookmarksFromServer()` 初始化时 GET 恢复，合并本地+服务端
- 服务端存储：`/var/www/html/bidding/data/bookmarks.json`
- Nginx 守护脚本已扩展：检测 `bookmark_server` 进程，挂了自动重启

**反馈闭环系统：**
- 日报每条分析卡片带 👍点赞 / 👎点踩 按钮
- 点踩弹出评论框，理由必填
- POST `/bidding/api/feedback` → 存储到 `data/feedback.json`
- ⚠️ 点踩理由**自动写入 HOT_MEMORY.md** → 下次会话AI自动感知 → 迭代评分关键词
- 点赞/点踩状态 localStorage 持久化（`daily_feedback`），防重复提交

**每日分析日报：**
- `daily_report.py`：读取 DB 今日数据 + 书签 → 生成 HTML 报告（双 Tab：招标情况报告/中标情况报告）
- 每条卡片含：招标人/内容/金额/相关度/AI建议（重点关注/可投标/可关注/暂不考虑）
- 中标卡片含：中标人/招标单位/金额/竞品分析（本公司✅/竞品⚠️/非中南院📊）/收藏提醒/大标预警💰
- `push_daily_report.sh`：cron no_agent 脚本，生成日报 → 企微 text 推送链接
- cron：每晚 20:00（`04bf3bdc6aa6`，no_agent=true）
- 报告 URL：`yfzx.online/bidding/report-YYYY-MM-DD.html`

**v12 (2026-06-25): 企微推送 Webhook 全局暂停开关 + changelog 排序纪律**

**🔴 KILL_SWITCH 暂停/恢复 SOP：**
- 暂停：`wecom_push.py` 设置 `KILL_SWITCH = True` + `push_daily_report.sh` 注释 webhook curl
- 恢复：改回 `False` + 取消注释
- 验证暂停：运行 `wecom_push.py` 应看到所有行 `[KILL_SWITCH] XXX: 已拦截`
- 注意：恢复推送前删除 `/tmp/wenyao_push.lock`，否则当天锁还在

**⛔ changelog 排序纪律（致命坑 — 2026-06-25）：**
- changelog **必须严格按版本号降序排列**：V1.8 → V1.7 → V1.6 → ... → V1.0
- 插入新版本时插入到已有内容**上方**，不可插到中间或底部
- 修改后立即 `curl -s URL | grep -o "V1\.[0-9]"` 验证顺序
- ⚠️ 旧版本块（如 V1.7）被误插到错误位置时，先复制到正确位置，再删除旧位置——避免重复块
- **日期新鲜度衰减**（`relevance_scorer.py` score_item）：>2年×0.3, >1年×0.5, >6月×0.7。避免两年前旧标100分排第一
- **从内容提取地区+招标人**（新增 `_extract_region_owner()`）：评分时自动从正文提取"招标项目所在地区：广州"和"招标人为XXX"
- **预算提取增强**：`extract_budget_from_content()` 新增南网格式"最高投标限价（万元）"的HTML表格解析
- **凌晨3点自检**：`selfheal_3am.py` + `wenyao-selfheal.timer`，读反馈→聚类根因→自动修（链接检测/预算回填/过期降权）→写HOT记忆

**Cron 管线重构（2026-06-24 全部迁移至 systemd → 2026-07-20 全部恢复）：**  
- Hermes cron 有 **3 分钟硬中断**（所有 job 包括 no_agent 都在第 3 分钟被 kill）
- **全部定时已迁移至 systemd timer**，Hermes cron 仅保留 nginx_guard（每1分钟）
- 定时器（2026-07-20 全部 active）：`wenyao-pipeline`(08:00) + `wenyao-selfheal`(03:00) + `wenyao-memory`(09:00) + `nginx-guardian`(每分钟)
- **2026-07-01 精简**：删除 `wenyao-push`(8:30独立推送)和 `wenyao-dailyreport`(20:00日报)——推送已内嵌在管线阶段5
- **2026-07-18 曾短暂关闭** selfheal/memory/nginx-guardian，**2026-07-20 全部恢复**
- 服务文件：`/etc/systemd/system/wenyao-*` + `nginx-guardian.*`
- `TimeoutStopSec=7200`（管线）、`600`（自检）、`300`（记忆维护）
- 命令：`systemctl list-timers 'wenyao-*'` 查看所有
- 完整迁移模板：`references/systemd-timer-migration.md`
- Nginx 配置安全操作：`references/nginx-config-pitfalls.md`
- data.json 防爆策略：`references/data-json-strategy.md`
- ⛔ 时区一致性陷阱：`references/timezone-utc-pitfall.md`（V1.23 — todayStr() UTC vs CST）

**⛔ app.js 版本参数缓存（致命坑 — 2026-06-25）**：
- `app.js?v=10` 这样的版本查询参数使浏览器认为它是唯一资源，即使 Nginx 设了 `no-cache`，浏览器仍会缓存旧版 JS
- **修复**：`<script src="app.js"></script>` 去掉版本参数，让 Nginx 的 `Cache-Control: no-cache` 正确生效。index.html 可保留 `?v=N`（用于区分页面版本），但 app.js 的引用不收此参数
- 模板中的 script 标签永远不要硬编码 `?v=N` 参数

- ⛔ **polish_report.py 跳过检测误判（2026-06-25）**：
 - 症状：report_generator 生成含 chat-widget/LIGHT_THEME 等标记的 HTML → polish 脚本检查到这些标记 → 误判为"已抛光" → 跳过 → 页面缺失 polish 注入的功能
 - **修复**：重新生成报告前先 `rm /var/www/html/bidding/index.html`，确保生成的 HTML 不含 polish 标记，再单独运行 polish
 - **polish 注入清单**（幂等检查，共 4 项）：Light Theme CSS → Theme JS → Chat Widget (CSS+JS) → **Favicon (3 link tags)**。详见 `references/favicon-spec.md`
- polish 脚本的幂等检查过于简单，需改进为 hash-based 检测
**⚠️ 当前产品状态（V1.35 — 2026-06-26）**：
- Tab：招标 / 中标 / 收藏（3个）
- 招标表 11 列 / 中标表 9 列
- **桌面端筛选栏单行紧凑**：search + 客户 + 地域 + 相关度 + 日期 + 预算 + 导出 + 重置全部在一行（`display:contents` 合并 filter-row，详见 `references/filter-bar-display-contents-fix.md`）
- **搜索框胶囊**：`display:flex` 使 input + button 并排，input 左圆角、button 右圆角 + 蓝色背景 + border-left:none，形成视觉一体胶囊。🔍 图标 `position:absolute;top:50%;transform:translateY(-50%)` 垂直居中。详见 `references/filter-bar-display-contents-fix.md`
- **polish_report.py 双阶段注入模式**：Stage1 检测并修复旧模板（如「系统运行中」→lastUpdate span），Stage2 在修复后的 DOM 上注入增强（如 densityBtn）。每阶段用唯一标记做幂等检查。
- **移动端 H5 横向滚动筛选栏** + **搜索框独占首行**
- **搜索交互（最终方案）**：搜索框右侧搜索按钮 + `addEventListener('click', doFilter)` 绑定 + 回车键触发。不再用 onclick 属性或 oninput/compositionend — 移动端不可靠且用户明确要求确认按钮。
- 筛选栏输入框 `background:#fff; border:1px solid #d1d1d6`（light theme 不再覆盖为 transparent）
- **Kebab ⋯ + NEW badge 均锚定 tr.data-row**（非 td.title-cell），互不遮挡
- **Chat widget 手机端可拖**（touch+mouse 双事件支持）
- **日期预设按钮 toggle active class**（黑底白字高亮），手动改日期自动清除
- **横向滚动 affordance**：右侧渐变淡出 + 首次进入自动演示滑动（双保险），见 `references/mobile-horizontal-scroll-affordance.md`
- **企微推送 V1.30**：精简为仅今日招标 TOP8 卡片（无摘要/中标/大标），KILL_SWITCH=False，`>=50` 阈值适配 100 分制
- 桌面端筛选栏统一高度 36px（搜索框+select+input 全部对齐）
- 页码居中：`.pg-bar{justify-content:center}`
- 标题 2 行截断、分数带"分"后缀、星标可见 18px、卡片点击手机端跳转源页面
- 回到顶部按钮、下拉刷新、已读追踪、智能空状态、日期快捷预设
**Nginx 防护体系（V1.37 — 2026-06-26 升级）：**
- 频率限制：`limit_req zone=static rate=8r/s burst=12` + 全局 `general 10r/s`
- 安全响应头：HSTS / X-Frame / X-Content-Type / Referrer / XSS / Permissions 六层
- **端口守护 + 企微告警**：`nginx_guardian.py` + systemd timer 每分钟检测 — 80 被非 nginx 占 → kill 侵占者 → 重启 nginx → 企微 Webhook Markdown 推送。冷却 30 分钟防骚扰。SMTP 邮件未通（腾讯企业邮 535 认证失败）。详见 `references/nginx-guardian-system.md`
- **HTML 缓存已全局禁用**：`Cache-Control: no-cache, no-store, must-revalidate`——更新立即可见
- ⚠️ `add_header` 在子块覆盖父块——安全头必须在每个 location 内显式声明

**采集管线：**
- **导出 CSV**: `esc()` HTML转义换 `String()+??` 纯CSV转义，修复 number 类型 `.replace()` 报错
- **标题截断**: 南网等平台列表页标题50字截断→从详情页面包屑/`<title>` 提取完整标题
- **中国能建**: 母公司平台不抓（自己不能投自己标）
- **DB 锁**: `fuser data/bidding.db` → `kill -9` 释放旧进程持有的连接
- **竞品面板空白**: `renderComp()` 字段名 `c.name`→`c[0]`(categories)、`c.company`→`c.name`(competitors)、`c.category`→`c.type`、`c.count`→`c.wins`
- **竞品库扩充**: 35+竞品含AI安防/智慧工地BIM/数字孪生/能源IT全赛道
- **batch_crawler 中标检测**: 新增 `detect_notice_type()` 19 个关键词，分写 bidding_notices / winning_notices

### 项目推进卡片 (用户明确要求)
报告页须有"项目推进卡片"区域，展示高相关项目独立卡片（含AI封面+进度信息）。
这是系统配套功能，不可遗漏。会话中用户质问"项目推进卡片呢？怎么没了！" 确认为必须保留的特性。

## GitHub 仓库部署

仓库地址：`git@github.com:Whu-yla/wenyaozhitou.git`（首次推送 2026-07-22）

关键要点：
- ⛔ **Hermes HOME 重定向陷阱**：`~/.ssh/` 展开为 profile 目录下不存在的路径，SSH 密钥必须用显式 `/root/.ssh/` 路径
- ⛔ **推送前脱敏（3 处）**：`wecom_push.py` 和 `nginx_guardian.py` 中的企微 webhook key + `config.yaml` 中的 `api_key` 字段，全部替换为 `YOUR_*` 占位符
- ⛔ **用户要求全量推送**：用户明确要求「整个工程都推过去」。`.gitignore` 只排除敏感文件（密码 Excel、密钥）和垃圾文件（__pycache__/日志/备份），**不排除**项目数据文件（data_full.json、data_bid_p*.json、report-*.html 等）。首次推送因 .gitignore 过度排除导致 70 个文件缺失，用户追问后才补推。
- ⛔ **推送前必须 diff 检查**：临时目录策略导致生产文件和 git 仓库容易不同步。每次推送前必须对比生产环境 vs git 仓库的文件列表和 md5，确保没有遗漏或过时文件。

> 完整部署流程（SSH 配置、脱敏脚本、推送命令、目录结构、同步检查）见 `references/github-deployment.md`
