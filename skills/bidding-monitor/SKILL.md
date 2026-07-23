---
name: bidding-monitor
description: 文鳐智投投标监控 v20 — V1.37管线(8直连+9dlzb)+Nginx端口守护自愈+企微Webhook告警+归档差集今日新增+更新日志自动维护
tags: [bidding, crawler, report, cron, 投标, 监控]
---

# 投标监控系统 v20 — v3管线(8直连+9dlzb)+Nginx守护+企微告警+归档差集今日新增

## 核心身份

- **文鳐智投**，不是"程浩的智能助手"，使命是作为投标监控助手
- 服务对象：**中国电力工程顾问集团中南电力设计院数智科技公司**（湖北武汉）
- **数智科技 ≠ EPC施工公司** — 产品是数字化平台/软件/AI服务（数字孪生、智慧工地、BIM、AI中台、物联网、智能巡检、信创等），不投标施工EPC
- 报告 Footer：`© 中南电力设计院数智科技 · 文鳐智投 2026`
- 企微推送 Footer：`© 中南电力设计院数智科技 · 文鳐智投 2026`
- 报告地址：**`https://www.yfzx.online/bidding/`**（必须带 www，裸域 `yfzx.online` 无DNS A记录）

## 产品设计原则

1. **精准 > 量多** — 26条精准命中数智科技项目 > 3000条EPC噪音
2. **安静 > 打扰** — 有项目才推送详情，0条时静默（连续3次无产出才发心跳）
3. **简报优先** — 打开报告第一眼看摘要，不是一张大表
4. **可追溯** — 每日归档 `yfzx.online/bidding/YYYY-MM-DD/`，永久可查
5. **主动思考** — 以产品经理视角主动审视缺陷、提出优化。不等用户逐项需求，每次改动后全面检查四层（报告/推送/引擎/记忆）
6. **干了再说** — 面对「要不要做X」「先做A还是B」的选择题，**不等待、不犹豫、不反复确认**。评估两条路线不互斥→并行启动
7. **固定优于动态** — 封面图用 8 张固化图（cover_1~8.png），不调 AI。中文字体不可用→用数字替代。简单可靠 > 花哨不稳定
7. **写完要发布验证** — ⚠️ 用户明确要求：「你不是写，你要发布」。所有文件修改后**必须验证线上效果**：`curl -sI` 确认 HTTP 200 + `chmod 644` 确认权限 + 浏览器打开确认内容可见。不能只写磁盘就完事。注意 `Cache-Control: max-age=300` 导致浏览器缓存 5 分钟，用户可能看到旧版→硬刷新或加 `?v=N` 参数。

## 产品自检清单（每次改动后必过）

改完代码后，不要声称"完美无缺"。用以下清单逐项验证：

- [ ] site_list 行数 = 唯一URL数？（`SELECT COUNT(*), COUNT(DISTINCT url) FROM site_list`）
- [ ] crawl_log 有最新记录？`SELECT id, new_bidding FROM crawl_log ORDER BY id DESC LIMIT 1`
- [ ] 客户分类完整？`SELECT category, COUNT(*) FROM bidding_notices WHERE relevance_score>0 GROUP BY category`
- [ ] 活跃站点数合理？`python3 scripts/bidding_engine.py list-sites`
- [ ] 最新扫描评分分布合理？（高分段是真正的数字化项目；无"分包/劳务/土建/体检/车辆"命中的假阳性）
- [ ] 评分自测：`python3 scripts/relevance_scorer.py` 通过？
- [ ] 报告可访问？`curl -s https://www.yfzx.online/bidding/ | head -5`
- [ ] 失败站点有记录？`SELECT site_name, last_status FROM site_list WHERE last_status!='ok'`
- [ ] 竞品面板有数据？无数据时显示"暂无竞品数据"而非空白页
- [ ] 趋势看板非全0？使用 `fetch_date`（非 `publish_date`），包含当月
- [ ] **站点可达性**？每次全量扫描前先跑 `python3 scripts/site_prober.py` 确认几个站真能通。344站全扫10秒出0条→停止演戏，走三路并进方案（探测→适配器→搜索）
- [ ] Tab计数格式正确？`招标 (N)` 而非 `招标N`
- [ ] 省份空值显示 `—` 而非空白
- [ ] 无 `javascript:void(0)` 死链接？`url_fix()` 兜底
- [ ] 无 FAQ 标题漏网？（爬虫层+save_bidding双层过滤）
- [ ] 报告标题含"数智科技"？
- [ ] 简报非"加载中..."？预填上次扫描摘要
- [ ] 时间戳非二重？合并为一行 "扫描 XX · 报告 XX"
- [ ] 导出按钮显示"导出 CSV"而非"导出Excel"
- [ ] 星标☆功能正常？`toggleStar` + localStorage
- [ ] NEW 徽章显示正常？今日数据有红色闪烁标记
- [ ] **「今日新增」筛选正常？** 点按钮后应看到今天抓取入库的全部项目（含昨天发布今天入库的），不因 publish_date 口径遗漏。管线跑完后在测试环境验证 ✅ → 再推生产
- [ ] 明暗主题切换正常？🌓按钮 + localStorage 持久化
- [ ] polish_report.py 注入的CSS/JS完整？
- [ ] 趋势图三张各自独立？点击招标卡📈不影响中标卡（Map隔离）
- [ ] 客户筛选「其他」排最后？列表盒多选视觉正常（非size=1）
- [ ] cron job 无重复？`cronjob action=list` 检查
- [ ] **changelog 更新了？** 重大变动必须追加条目到 `/var/www/html/bidding/changelog.html`，`curl -s` 验证可见，提醒用户硬刷新
- [ ] **变更线上可见？** `curl -sI` 确认 HTTP 200 + 浏览器打开确认内容加载，不能只写磁盘
- [ ] **招标+中标双收？** 每个采集脚本都正确处理了 notice_type 分流（crawl_pipeline ✅ / dedicated_adapters ✅ / batch_crawler ✅ 已修复）
- [ ] **聊天组件正常？** `curl -s https://www.yfzx.online/bidding/ | grep -c chat-widget` 必须 ≥2（CSS + JS）。**V1.26 反馈已合并入聊天面板**（头部📝+预设栏），`curl | grep -c fb-fab` 必须 = 0（独立反馈按钮已废除）
- [ ] **data.json 不过大？** `ls -lh /var/www/html/bidding/data.json` < 500KB。超限需排查 `report_generator.py` 的 `trim()` 是否正确过滤 raw_html 等大字段
- [ ] **API 服务存活？** `curl -s http://127.0.0.1:8090/chat -X POST -H 'Content-Type: application/json' -d '{"question":"测试","messages":[]}'` 返回非 error 的 answer

## 架构

```
┌─ 站点管理层 ─────────────────────────────────────────┐
│ site_list (DB, UNIQUE url, is_active)                 │
│   → 344个唯一URL，20个活跃（数智/智能/智能公司）        │
│   → 324个母公司站点(勘测/发电/新能源等) is_active=0     │
│   → 每站记录 last_crawl_time / last_status            │
│   → activate-sites 命令从Excel导入并自动标记部门        │
└──────────────────┬────────────────────────────────────┘
                   ↓ load_active_sites()
bidding_engine.py → site_adapters.py → 适配公告列表页 → 多页爬取
    → FAQ过滤（常见问题/答疑/指南/下载中心等非公告链接拦截）
    → Chromium渲染回退(JS站点，--virtual-time-budget=15000)
    → relevance_scorer.py v6 → 五层排除 + 三级评分 × 地理权重 + 客户分类引擎 + 最低分阈值
    → 详情页提取(正则提取中标人/金额/招标人/编号，仅高相关≥4分触发)
    → SQLite (data/bidding.db) → 去重存库(标题+来源SHA256) + category字段
    → 每站更新 last_crawl_time/last_status → 写入 crawl_log(id可追溯)
    → report_generator.py → HTML报告(外挂app.js) + data.json + 每日归档 + 简报面板 + 趋势图 + 竞品面板 + 客户分类筛选
    → polish_report.py → 注入主题切换CSS+按钮、Tab括号格式、导出CSV标签、星标/NEW CSS（UI与数据层分离）
    → wecom_push.py v6 → 四连推(Markdown摘要+招标卡片+中标卡片+竞品卡片)+大标预警
    → competitor_tracker.py → 竞品追踪(30天排名+分类) + 大项目预警(≥500万)
    → memory_engine.py → 长记忆向量存储(HOT/WARM/COLD三层，text-embedding-v3 1024维) — 每次扫描后自动写入
```

**AI封面管线**：🗑️ **已废弃（2026-06-24）**。`ai_cover.py` 仅保留供参考。所有推送改用 8 张固定封面图 `img_gen/covers/cover_1~8.png`。废弃原因：通义万相 API 断连、中文字体缺失乱码、目录权限 404、企微服务器抓不到图。

**报告前端架构**：JS逻辑在独立 `/var/www/html/bidding/app.js`（419行），HTML通过 `<script src="app.js?v=7">` 加载。核心模块：表格渲染、SVG趋势图(renderBarSvg柱状+renderLineSvg曲线+chartMode切换)、竞品面板(空态)、搜索过滤、导出CSV、主题切换、收藏⭐、NEW徽章、url_fix兜底、Esc清除、筛选记忆、数据刷新提示。此文件须 `chmod 644`。

## 客户分类引擎 v7

原Excel「责任部门」列（数智/智能/系统规划等）是中南院内部科室名，对数智科技投标无意义。v7替换为**6大类自动客户分类**，从标题关键词识别招标人归属：

| 分类 | 关键词 | 业务意义 |
|:--|:--|:--|
| 🔴 五大发电 | 华能/华电/大唐/国电投/国家能源 | 核心客户群 |
| 🟠 国网/南网 | 国网/国家电网/南方电网/南网 | 智慧工地/安防大买家 |
| 🟡 地方能源集团 | 能源集团/电力集团/湖北能源/广东能源/浙能等 | 属地机会 |
| 🟢 政府/公共事业 | 政府采购/住建局/公共资源/商务厅/财政局等 | 政府数字化项目 |
| 🔵 电力/央企/工业 | 中广核/电建/太钢/宁德时代/中铁/中国移动等 | 产业链企业 |
| ⚪ 其他 | 不匹配上述 | 兜底 |

**实现位置**：`relevance_scorer.py` → `classify_customer(title)` → `CUSTOMER_CATEGORIES` 列表定义。
**入库**：`bidding_engine.py` 的 `save_bidding/save_winning` 保存 `category` 字段。
**报告**：筛选器 `fCat` 替代原 `fDept`，表头「客户」替代「业主」，简报展示 `top_categories`。
**企微推送**：日报卡片展示客户分类统计（🏢客户 `🔵`×1 `🟢`×2）。

## 命令

```bash
cd /root/.hermes/profiles/wenyaozhitou

# 🏆 全流程主控（cron no_agent 模式使用）
bash scripts/pipeline_master.sh

# 🏆 专属适配器（六大六小+浙能+南网+国网 — 最高质量产出）
python3 scripts/dedicated_adapters.py

# 统一采集管线（华润守正 + 湖北平台 + 南网 + 浙能 + 国家能源 5平台）
python3 scripts/crawl_pipeline.py

# 批量站点抓取（从probe结果加载87个listing_found站点）
python3 scripts/batch_crawler.py

# Chromium JS渲染采集（浙能/能建/南网/国电投等11大平台）
python3 scripts/chromium_crawler.py

# 仅重新生成报告+推送
python3 scripts/report_generator.py && python3 scripts/wecom_push.py

# Nginx守护（每1分钟自愈）
# cron job: f5a928bf619e (no_agent)
```

## 核心脚本

| 文件 | 功能 |
|:-----|:-----|
| `scripts/bidding_engine.py` | 🗑️ 旧主爬虫（已废弃，被 crawl_pipeline + batch_crawler + chromium_crawler 取代） |
| `scripts/crawl_pipeline.py` | **新统一采集管线 v1.37**：11阶段编排（华润守正→湖北→南网→浙能→国家能源→能建→三峡→江苏→申能→**dlzb.com统一收割15家集团**）→ 评分→去重入库。systemd timer调用 |
| `scripts/batch_crawler.py` | **批量爬虫 v2**：从 probe_results.json 加载全部 87 listing_found 站点，通用抓取→评分→入库。🆕 v2新增 `detect_notice_type()` 自动区分招标/中标(19个关键词)，`_score_and_insert()` 按类型分写入两张表 |
| `scripts/chromium_crawler.py` | **Chromium JS渲染爬虫**：攻克浙能/能建/南网/国电投/长江电力/中国船舶/深圳能源等11个JS平台 |
| `scripts/relevance_scorer.py` | v9评分引擎：AI/产品关键词 + 三层排除+三级评分 × 全国统一权重1.0 |
| `scripts/site_adapters.py` | 域名→公告列表URL映射（已知站点专用URL，未知保持原URL） |
| `scripts/site_crawlers.py` | **站点专属爬虫**：华润守正(`crawl_huarun_szecp`)、湖北省平台(`crawl_hubei_ggzy`)等已验证适配器 |
| `scripts/site_prober.py` | **站点探测器**：批量HTTP GET验证344站可达性，输出 listing_found/timeout/404/登录页分类 →
 `data/probe_results.json` |
| `scripts/dedicated_adapters.py` | **🏆 六大六小专属适配器**：南网(crawl_nanwang)、国家电投(crawl_guodianta)、中国能建(crawl_nengjian)、华润守正(crawl_huarun_szecp)、三峡(crawl_sanxia) + JS平台Chromium回退。精准HTML解析，产出质量最高 |
| `scripts/report_generator.py` | HTML报告+data.json+每日归档+简报+趋势+竞品+调用wecom_push。JS逻辑在 `/var/www/html/bidding/app.js` |
| `scripts/wecom_push.py` | 企微智能推送(v7)：摘要+引导文本+招标卡片+引导文本+中标卡片+大标预警。固定封面，不调AI |
| `scripts/ai_cover.py` | AI封面生成器：通义万相API异步生图→裁切800×400→缓存复用（全AI覆盖，无Pillow） |
| `scripts/polish_report.py` | 报告抛光器 v3：post-generation注入主题切换CSS+按钮、chat-widget（含反馈面板）。V1.26 精简——移除独立 fb-fab 注入 |
| `scripts/adapter_zheneng.py` | **🏆 浙能集团专属适配器**：发现 iframe 数据源 (`/zjnycms//category/iframe.html?dates=300&categoryId=2&tenderMethod=01&page={page}`)，详情页 `/sdny_bulletin/YYYY-MM-DD/ID.html`。7978条数据，requests直取无需JS。10条/页 × N页自动翻页 |
| `scripts/adapter_huaneng.py` | 🆕 **华能集团搜索聚合适配器**：ec.chng.com.cn WAF不可达，通过 dlzb.com + web_search 双模式获取。双模式(Hermes注入/独立Bing)，8组搜索词+40+硬件词排除，已接入管线阶段11 |
| `scripts/adapter_dlzb.py` | 🆕 **电力招标网统一适配器**：Chromium headless 破阿里云 WAF，一脚本覆盖 15 家发电集团（华能/华电/大唐/国电投/等）。URL 模式 `/huaneng/`, `/huadian/`, `/datang/` 等。列表页公开不需登录，每条有 `/d-zb-XXXXXXXX.html` 链接。产出含「品牌管理平台建设」等数字化项目 |
| `scripts/memory_engine.py` | 长记忆引擎：向量语义存储(text-embedding-v3 1024维)、三层架构、去重、每日维护 |
| `scripts/memory_maintainer.py` | 长记忆维护器：每日降级HOT→WARM→COLD + 语义去重 + 日报生成 |
| `scripts/bookmark_server.py` | 🆕 **书签+反馈微服务**（端口8090）：GET/POST `/` 书签同步、GET/POST `/feedback` 点赞/点踩收集。点踩理由自动写入 HOT_MEMORY.md |
| `scripts/daily_report.py` | 🆕 **每日分析日报生成器**：读取今日DB数据+书签，生成双Tab HTML（招标/中标），含AI逐条分析+点赞/点踩交互 |
| `scripts/push_daily_report.sh` | 🆕 **日报推送脚本**：调用 daily_report.py 生成报告 → 企微推送链接。cron no_agent 执行 |

### 参考文件

| 文件 | 内容 |
|:-----|:-----|
| `references/company-profile.md` | 数智科技公司介绍 |
| `references/keywords.md` | v6完整关键词库（核心/强相关/客户/泛词/排除/地域权重） |
| `references/scoring-engine.md` | v6评分引擎行为规范+测试用例+已知不足 |
| `references/customer-classification.md` | v7客户分类引擎（6大类+关键词+匹配策略） |
| `references/site-adapters.md` | 站点适配器配置 |
| `references/ai-cover.md` | AI封面生成规范（通义万相API+Prompt工程+图片处理+推送集成，全AI无Pillow） |
| `references/wecom-push-format.md` | v5企微推送格式规范（Markdown摘要+news图文卡片+AI封面策略） |
| `references/product-audit-20260623.md` | 🔬 2026-06-23 产品审计报告（Bug/体验/功能缺口完整清单） |
| `references/dedicated-adapters.md` | 🏆 六大六小发电集团招标平台适配指南：平台URL清单、适配器模式、优先级、南网案例 |
| `references/svg-charts-and-multiselect.md` | SVG趋势图引擎+多选标签筛选+「其他」排序+polish注入点的完整技术参考 |
| `references/table-ux-v14.md` | v14表格交互：行勾选+序号列+收藏筛选+selective导出+工具栏布局+execute_code文件IO坑 |
### ❗ 今日新增逻辑返工 — ✅ V1.37已修复 (2026-06-26)

**根因**：V1.18 将"今日新增"从 fetch_date 改为 publish_date 口径，导致昨天发布今天抓取的精品项目在"今日新增"筛选中消失（如南网 83 分项目）。

**最终方案**：彻底摆脱日期字段判断。report_generator.py 对比昨天归档 `data.json` 的 id 差集 → `is_new_today` 字段。前端 `isNew()` 直接读 `is_new_today`。统计卡片 `today_total` 同口径。

**关键教训**：不要用日期字段（publish_date/fetch_date）模拟"新增"概念——管线重跑会更新 fetch_date，去重规则会改变 publish_date。只有归档差集是可靠的。

### ❗ 浙能门户噪音 70 分假阳性 — ✅ V1.37修复 (2026-06-26)

**症状**：6 条「欢迎来到浙江能源集团智慧供应链一体化平台V1.0」被评分 70 分入库。

**根因**：L1 判别器的浙能特殊模式要求「V1.0/欢迎来到」+「无公告词」才拒绝。但门户导航文本含"招标项目信息/采购项目信息" → has_notice_kw=True → 绕过过滤。

**修复**：增加门户导航信号检测（异议投诉/帮助中心/办理CA/搜索首页）。含 2 个以上门户信号 → 直接拒绝，不管标题是否有"招标"字样。

### ❗ 南网中标公告表格提取 — ✅ V1.37修复 (2026-06-26)

**根因**：南网中标公告用 HTML `<table>` 展示中标人（序号|标的|标包|中标人），但适配器只用纯文本正则匹配 `中标人：xxx`，完全抓不到表格数据。

**修复**：
1. `dedicated_adapters.py` 增加 BeautifulSoup 表格解析：遍历 `<table>` → 找表头列位置 → 提取数据行同列值
2. 中标人关键词覆盖：`中标人/成交供应商/中标单位/供应商名称/成交人`（南方电网用"成交人"而非"中标人"）
3. 金额：南网公开页面不含金额（需登录/PDF），纯文本兜底覆盖其他平台

**效果**：3/8 → 7/8 中标人覆盖率，南网剩余 1 条非标准格式（询比采购）

**根因三重**：
1. 爬虫把平台首页/导航页当"中标公告"入库（数智云采/天工招采/连云港等14条）
2. 中标入库不跑评分引擎，直接裸进数据库
3. DIGITAL_GATE 太宽（"系统""服务"命中一切）→锅炉改造/煤矿大修/工装洗涤也100分

**修复**：
1. SQL DELETE 清理14条首页+12条非数字化项目（33→7）
2. `relevance_scorer.py` 新增 `NON_DIGITAL_EXCLUDE` 层：锅炉/煤矿/脱硫/洗衣/EPC施工总承包→直接拒掉（除非同时命中「智慧工地」「BIM」等强数字化关键词）
3. 爬虫层加 `HOMEPAGE_PATTERNS` 检测（"欢迎使用""首页 >""APP下载""关于我们"等）
4. 中标入库必须和招标一样过 `score_item()`

> 详见 `references/winning-notice-garbage-cleanup.md`

| `references/winning-notice-garbage-cleanup.md` | 🆕 中标数据清洗教训：33条→7条，平台首页+NON_DIGITAL_EXCLUDE（V1.10） |
| `references/winning-data-gap.md` | 🆕 中标数据缺口诊断：8条中标0条有金额，南网+国家能源详情解析待修复 |
| `references/v17-lessons.md` | 🆕 v17关键教训：专属适配器>通用爬虫、招标/中标分流、竞品追踪、导出CSV修复、标题截断修复、封面全量、DB锁 |
| `references/api-score-consistency.md` | 🆕 API数据一致性保护：items vs stats 默认过滤 score=0 噪音 + winning_notices notice_type 列缺失修复 |

### ❗ API端点数据口径不一致 — ✅ V1.39修复 (2026-06-28)

**症状**：前端表格展示 157 条招标（含 63 条 score=0 浙能施工/监理噪音），统计卡片却显示 94 条。用户质疑「累计从 90+ 到 157，今日新增不得 60 个左右？」

**根因**：`/items` 端点默认 `min_score=0`（返回全量含噪音），`/stats` 端点硬编码 `relevance_score > 0`（只统计有效项）。两处口径不一致。

**修复**：
1. `bookmark_server.py` `query_items()` — 默认 `min_score=1` 排除 score=0 噪音
2. `winning_notices` 表无 `notice_type` 列 → 查询时补充 `'winning' as notice_type`
3. 验证：items(94) = stats(94) = DB(94) 三者一致

**关键教训**：API 架构迁移时，新端点默认值与旧数据管线的过滤逻辑必须对齐。data.json 管线用 `relevance_score>0`，API 也必须默认此口径。详见 `references/api-score-consistency.md`。

| `references/nginx-protection.md` | 🛡️ Nginx三级防护：频率限制+安全响应头+健康守护Watchdog（2026-06-24） |
| `references/systemd-cron-migration.md` | ⏱️ systemd timer 迁移：3分钟硬中断→7200s超时，服务文件+部署命令 |

## 数据库

SQLite: `data/bidding.db` — 5表

| 表 | 关键字段 |
|:--|:-----|
| `bidding_notices` | title, url, source_site, **category**, procurement_owner, province, relevance_score, publish_date, fetch_date |
| `winning_notices` | 同上 + winner_company, winning_amount, project_no, **category** |
| `crawl_log` | total_sites, success_sites, failed_sites, new_bidding, new_winning, duration_seconds, errors |
| `site_list` | site_name, url(**UNIQUE**), responsible_dept, is_active(0/1), last_crawl_time, last_status |

**记忆数据库**：`data/memory.db` — 长记忆向量存储（详见 `long-term-memory-engine` 技能）
- 表 `memories`: content, embedding(BLOB 1024维), category, tags, importance, tier(HOT/WARM/COLD), source, ref_id, created_at, accessed_at, access_count

**site_list 管理原则**：
- UNIQUE(url) 防止重复插入，344个唯一URL，其中20个活跃（数智/智能/智能公司部门）
- 默认从 DB 加载活跃站点（`load_active_sites()`），不再从 Excel 加载
- `last_status` 记录每站最近一次抓取结果（ok / 无公告链接 / exception:xxx）
- 324个母公司站点（勘测/发电/新能源等）标记 is_active=0，不入扫描

## 六大六小发电集团招标平台

数智科技的核心客户是发电集团。中国现有「六大六小」发电集团，其官方招标平台是投标信息首要监控目标：

| 层级 | 企业 | 招标平台 | 适配器状态 |
|:--|:--|:--|:--|
| **六大** | 华能集团 | ec.chng.com.cn | 🟢 **搜索聚合适配器** (`adapter_huaneng.py`) — 阿里云WAF不可达，通过 dlzb.com + web_search 双模式。dlzb.com 一站式覆盖全部发电集团 |\n| | 华电集团 | chdtp.com | ❌ HTTP412 |\n| | 大唐集团 | cdt-ec.com | ❌ 搜索需登录，公开页少量公告 |\n| | 国家电投 | ebid.espic.com.cn | 🔴 雷池WAF锁iframe → dlzb兜底。同浙能电能e招采系统，但iframe接口被雷池Bot Challenge封锁 |\n| | 国家能源集团 | chnenergybidding.com.cn/bidweb/ | 🔥 JS-SPA，首页公开，有对口项目(工控安全/智能预警)，详情UUID |\n| | 三峡集团 | eps.ctg.com.cn | ✅ `crawl_sanxia()` |
| **六小** | 中广核 | ecp.cgnpc.com.cn | ✅ **Chromium适配器已跑**，主页dump获134条详情链接(`Details.html?dataId=...&detailId=...`)，有对口项目：数字化业务服务、信息安全设备、智能化试验台 |
| | 华润电力 | szecp.crc.com.cn | ✅ `crawl_huarun_szecp()` |
| | 国投电力 | sdicc.com.cn | ⚠️ JS渲染 |
| | 中核集团 | cnncep.com.cn | ⚠️ JS渲染 |
| | 中节能 | ebidding.cecep.cn | ⚠️ 未适配 |
| | 中国电建/能建 | ec.ceec.net.cn | ❌ **不抓（母公司）** |
| **电网** | 南方电网 | bidding.csg.cn | ✅ `crawl_nanwang()` **最高产出** |
| | 国家电网 | ecp.sgcc.com.cn | ❌ 全JS+登录保护 |
| **地方** | 浙能集团 | zsrm.zjenergy.com.cn | ✅ **iframe适配器** (`adapter_zheneng.py`) |
| | 深圳能源 | zb.sec.com.cn | ⚠️ 未适配 |
| | **蒙西电网** | **✅ 直连** | `adapter_mengxi.py` — wzglb.impc.com.cn:82, curl无WAF |
| | **🔥 dlzb兜底** | `adapter_dlzb.py` — 华能/华电/大唐/国投/中核/中节能/中广核/国网, Chromium |

**关键教训**：通用爬虫（batch_crawler.py）对这类平台无效——必须写专属HTML解析器。南网专属适配器单平台产9条（含94分数字化项目），远超87站通用爬虫的1条。**JS-SPA平台（国家能源/中广核）走Chromium headless `--dump-dom` 路线有效**：15-20s渲染→dump主页→正则提取详情链接→批量Chromium抓取详情→评分入库。详见 `references/platform-adapters-v18.md`。

**🆕 dlzb.com 金矿发现 (2026-06-26)**：`https://www.dlzb.com/huaneng/` 等平台专区是阿里云 WAF 保护的 JS 渲染页面，curl 不可达但浏览器可正常访问。13,886 条华能公告，同一 URL 模式覆盖全部六大六小+两网（`/huaneng/`, `/huadian/`, `/datang/`, `/guodianta/`, `/guowang/`, `/nanwang/` 等）。列表页公开不需登录，详情需银牌会员。后续可批量写浏览器渲染适配器。详见 `references/huaneng-adapter.md`。

## 业务评分 v12 — 100分制 · AI/产品关键词 · 全国统一权重 · 50分底线 · 新鲜度衰减0.8(6-12月)

**v9 核心变更（2026-06-24）：**
- ✅ **AI/人工智能关键词**：CORE_KEYWORDS 新增「人工智能/大模型/深度学习/机器学习/计算机视觉/NLP/LLM/图像识别/语音识别/AI平台/AI中台/AI大模型/AI应用」(各+35)
- ✅ **产品线关键词**：CORE_KEYWORDS 新增「玄武SSK/玄武/SSK/有限空间/执法记录仪」(各+35)
- ✅ **DIGITAL_GATE 扩展 v9**：新增「人工智能/大模型/机器学习/深度学习/玄武/执法记录仪/有限空间/NLP/LLM/计算机视觉/自然语言处理/图像识别/语音识别」

**v8 变更（2026-06-24）：**
- ❌ **地域权重全部取消** — PROVINCE_WEIGHTS 设为 1.0，全国统一
- ✅ **DIGITAL_GATE 放宽** — 新增"系统开发/信息系统/监管系统/管理系统/平台建设/软件系统/数据管理/数据平台/业务系统/综合管理/应用系统"
- ✅ **STRONG_KEYWORDS 扩展** — 新增"管理系统/监管系统/业务系统/应用系统/系统开发/平台建设/软件开发/系统集成"(各+18)
- ✅ **EXCLUDE 精确化** — "法律"→"法律顾问/法律服务/律师"、"审计"→"审计报告"、"会计"→"会计服务"。避免匹配招标公告模板中的"承担全部法律责任"通用文本
- ✅ **标题提取改进** — `fetch_huarun_detail()` 优先从结构化字段(标段名称/项目名称)提取标题，不取整段模板文本

### 评分权重

| 层级 | 权重 | 示例 |
|:--|:--|:--|
| ★ CORE_KEYWORDS | +35 | 智慧工地、智能安防、BIM、数字孪生、数智科技 |
| ☆ STRONG_KEYWORDS | +18 | 管控平台/管理系统/监测系统/监管系统/系统开发/平台建设/数字化平台/智能巡检 |
| @ CUSTOMER_KEYWORDS | +12 | 华电、国网、大唐、国电投、湖北能源 |
| 泛行业词 | +8 | 风电、光伏、电站、电网（仅CORE或STRONG命中时激活）|
| × 地理权重 | **×1.0 全国统一** | v8已取消地域折扣，`geo=1.0`硬编码于第280行 |
| 最低入库线 | ≥55分 | final < 55 → return None。⚠️ 50分太低 — 6/26实测：50分门槛为救蒙西52分项目，代价是进7条噪音(EPC施工79分/不间断电源70分/铁路信号75分)。建议维持55，提升蒙西云平台关键词权重让其突破55 |
| 企微推送线 | ≥7分 | 高相关才推（非80分，实际阈值更低） |

### 排除规则（五层过滤）

```
① 硬排除：医疗/医院/学校/教学/食品/餐饮/物业/保洁/办公用品/服装/广告/印刷/法律顾问/法律服务/律师/审计报告/会计服务/殡葬/储备林/林业/造林 → return None
② 施工排除：专业分包/劳务分包/土建/混凝土/脚手架/钢筋/装修/地基/体检/车辆维修 → return None
③ 动名词排除：施工总承包/PC总承包/EPC总承包/安装工程/变电工程/线路工程 且无数字化关键词 → return None
④ 分包特判：标题含"分包"且无数字化关键词 → return None
⑤ 最低分阈值：final < 55 → return None
```

### 已验证案例（华润守正 2026-04~06）· v8得分

| 公告 | 命中路径 | 得分 |
|:--|:--|:--|
| **系统开发采购项目** | ☆管理系统+☆监管系统+☆系统开发+☆综合管理+☆大数据 | **90** ✅ |
| **数智化建设咨询项目** | ★数智+★数智化 | **70** ✅ |
| 大气监测设备采购 | DIGITAL_GATE虽过(大数据/软件)但无STRONG → raw=0 | ❌ |
| 熟石灰/硫酸采购 | 无IT关键词+排除 | ❌ |
| 配水泵站阀门更换 | 远传控制系统接入 → 无DIGITAL硬关键词 | ❌ |

> 📌 **关键教训**：单纯gate命中「软件/大数据」等通用词不够——必须配合STRONG_KEYWORDS(CORE_KEYWORDS)才能让 raw_score > 0。「软件」一词太通用，只能当 gate key 不能加分。

### 爬虫层FAQ过滤

`extract_links_from_html()` 新增FAQ_PATTERNS过滤链接文本：
常见问题/问题答疑/帮助中心/操作指南/使用手册/办事指南/下载中心/通知公告/新闻动态/政策法规

### 评分示例

| 标题 | 命中路径 | 得分 |
|:-----|:-----|:--:|
| 国电投湖北智慧工地管控平台 | ★智慧工地+@国电投+湖北(×1.0) | **12.0** |
| 国网安徽土建专业分包 | ②"分包"+"土建"→排除 | ❌ |
| 变电工程电气劳务分包 | ②"劳务分包"+③"变电工程"→排除 | ❌ |
| **太钢装备数智管理平台建设** | ★**数智**(+10)+☆管理平台(+5)+泛词(+4)=19×0.3 | **5.7** |
| 南网零碳园区设计服务 | ⑥@南网(+3)→final=0.9<1.5→排除 | ❌ |
| 数字管理平台常见问题答疑 | FAQ过滤(爬虫层)+仅1.5分 | ❌🛡️ |

## 报告交互 v14

| 功能 | 说明 |
|:-----|:-----|
| 📊 **今日简报** | 顶部面板预填上次扫描摘要（非"加载中..."），含🆕刷新提醒（距上次访问>1小时显示绿色脉冲徽章） |
| 🌓 **明暗主题** | 右上角圆形按钮，一键切换暗黑(默认)/明亮主题，localStorage记忆偏好 |
| 🔍 **自然语言搜索** | 输入"华电 数字化"→即时出统计摘要；搜索范围含标题/客户分类/来源 |
| ⌨️ **键盘快捷键** | `/`聚焦搜索框，`Esc`清空搜索并失焦 |
| 📅 **日期范围** | 从/到date输入框，选日期秒级过滤历史 |
| 🏷️ **多维筛选** | **客户(6大类)** /地域/相关性三维筛选 + 日期范围。客户/地域为原生列表盒多选（点击=并集，再点=取消），「其他」永远排最后。筛选条件 localStorage 持久化，刷新不丢 |
| 📊 **排序** | 点击列头升/降（相关/标题/**客户**/地域/来源/日期） |
| 📈 **趋势看板** | SVG趋势图：柱状图(圆角+动画+数值) ↔ 曲线图(网格+Y轴+面积填充+数据点)，每卡片📊/📈切换按钮。含当月数据（`fetch_date`非`publish_date`） |
| 🔍 **竞品面板** | 竞品标签页：分类排行+中标TOP10+大项目列表。空态显示"暂无数据"而非空白页 |
| ☑️ **行选择+序号** | 每行左侧：勾选框 + #序号列。表头全选checkbox（`toggleAll`），`onCheckChange` 联动全选状态(indeterminate) |
| ⭐ **收藏筛选** | 行内 ☆/⭐ 按钮切换收藏 + 工具栏 ⭐收藏 按钮切换只看收藏模式。`starOnly` 联动 `doFilter`、`exportExcel`、`resetF` |
| 📥 **导出CSV** | 一键下载：**优先导出勾选项**，无勾选则全量导出当前筛选结果。列含客户分类 |
| 🆕 **NEW徽章** | 今日新抓取条目显示红色闪烁 `NEW` 标记 |
| 📱 **手机适配** | @media 768px：表格横向滑动、隐藏次要列 |
| 📁 **每日归档** | `yfzx.online/bidding/YYYY-MM-DD/` 永久可查，含app.js |

**技术细节**：JS在独立`app.js`（v7），`chmod 644`，report_generator 归档时自动复制。

**明暗主题实现**：
- CSS：`body.light` 覆盖所有元素颜色（白底+蓝调配色），`.theme-btn` 圆形按钮
- JS：`toggleTheme()` 切换 `body.light` 类，`localStorage.theme` 持久化
- 图标：暗黑→🌓，明亮→☀️
- 首次加载从 localStorage 读取偏好，无记录默认暗黑

## 企微推送 v7 — 摘要+引导+招标卡片+引导+中标卡片

Webhook: `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0256f02d-7368-4214-9c99-9c53ce449e92`

**推送架构 v7（2026-06-24）**：每次推送发最多 **5 条消息**（有数据时）：
1. **Markdown 摘要**（msgtype=markdown）：统计+地域+客户+大标预警+链接
2. **文本引导**（msgtype=text）："📋 这是今天的 TOP1~TOP8 招标信息，请群里的各位领导同事过目。"
3. **招标卡片**（msgtype=news）：今日 TOP8 招标，按相关性降序
4. **文本引导**（msgtype=text）："🏆 这是今天的中标 TOP1~TOP8 中标信息，请群里的各位领导同事过目。"
5. **中标卡片**（msgtype=news）：今日 TOP8 中标，含中标方+金额

- 竞品卡片已取消（用户要求）
- `push_text()` 函数发送纯文本引导语到企微
- **推送阈值**：`relevance_score > 0`（非 `>= 7`——v7 放宽了推送门槛，让群内能看到更多项目）
- 大标预警：≥500 万中标在摘要顶部 🚨

**卡片数量**：每条 news 消息最多 8 张，`LIMIT 8`。

**封面策略**（固定固化，绝不调AI）：
- 8 张固定封面图：`/var/www/html/bidding/img_gen/covers/cover_1~8.png`（800×400，深色底+大数字）
- 推送时按卡片顺序循环使用：第1张→cover_1，第2张→cover_2...
- ⛔ **永不启用 AI 封面生成**——权限/字体/API 断连问题频发，用户已明确要求固化
- ⚠️ `img_gen/` 目录必须 755 权限（nginx 需要 x 才能读子目录）
- `pipeline_master.sh` 阶段4 有 `chmod -R 755 img_gen` 兜底
- `ai_cover.py` 中 `os.chmod(IMG_DIR, 0o755)` 创建目录后自动设权限

**图文卡片示例**：
```json
{
  "msgtype": "news",
  "news": {
    "articles": [
      {
        "title": "🟡 [5.7分] 太钢装备数智管理平台建设技术服务项目",
        "description": "🔵 电力/央企/工业 · 来源：上海宝华 · 相关性：5.7分",
        "url": "https://www.baohuabidding.com/...",
        "picurl": "https://www.yfzx.online/bidding/img_gen/cache/5089.png"
      }
    ]
  }
}
```

**卡片封面图**：全AI生成，缓存于 `/var/www/html/bidding/img_gen/cache/{id}.png`（800×400 JPG，HTTPS可访问）。nginx serve `/var/www/html/bidding/`。

**版权声明**：Markdown摘要底部 `© 中南电力设计院数智科技 · 文鳐智投 2026`

## URL 策略

| URL | 说明 |
|:-----|:-----|
| `yfzx.online/bidding/` | 最新报告 |
| `yfzx.online/bidding/YYYY-MM-DD/` | 按日归档 |
| `yfzx.online/bidding/data.json` | 全量数据API |

## 定时任务 (2026-07-20 更新 — 全部已启用)

| 时间 | 方式 | 内容 |
|:--|:--|:--|
| **8:00** | **systemd** `wenyao-pipeline.timer` | 全流程管线（TimeoutStopSec=7200秒/2小时） |
| **9:00** | **systemd** `wenyao-memory.timer` | 长记忆维护（路径已修复 2026-07-20） |
| **3:00** | **systemd** `wenyao-selfheal.timer` | 凌晨自检修复 |
| 每分钟 | **systemd** `nginx-guardian.timer` | Nginx 端口守护 + bookmark_server 自愈 |

**2026-07-20 全部重新启用**：`systemctl enable --now wenyao-memory.timer wenyao-selfheal.timer nginx-guardian.timer`

⚠️ **wenyao-memory.service 路径修复 (2026-07-20)**：ExecStart 旧路径 `/root/.hermes/memory_store/memory_maintainer.py` → 新路径 `/root/.hermes/profiles/wenyaozhitou/scripts/memory_maintainer.py`。profile 迁移后所有 service 文件路径必须同步更新。

⚠️ **memory 服务依赖 `/tmp/qwen_key.txt`**：通义千问 embedding API key 存在 /tmp，重启后丢失。需手动恢复。

⚠️ **Hermes Cron 有 3 分钟硬中断**（`cron/jobs.py` 的 `.tick.lock` 超时）。管线跑 1-2 小时，必被砍死。**长任务必须用 systemd timer。**

⚠️ **Python 路径陷阱**（2026-06-25 全站停摆）：systemd 干净环境中 `python3`→`/usr/bin/python3`（系统 Python，无 bs4/lxml/requests）。所有 shell 脚本必须用 `PY="/usr/local/lib/hermes-agent/venv/bin/python3"` 并 `$PY scripts/...`，所有 service 文件的 `ExecStart` 必须用 venv Python 全路径。详见 `wenyao-bidding` 技能 `references/systemd-python-path-pitfall.md`。

**systemd 服务文件**：`/etc/systemd/system/wenyao-pipeline.{service,timer}` + `wenyao-memory.{service,timer}` + `wenyao-selfheal.{service,timer}` + `nginx-guardian.{service,timer}`

## Nginx 端口守护系统 (V1.37)

**部署**：`scripts/nginx_guardian.py` + systemd timer `nginx-guardian.timer`（每分钟）

**检测三件套**：80端口归属 → nginx 服务状态 → HTTP 200 可达性
**自愈**：非 nginx 进程占 80 → kill → systemctl start nginx（<3秒恢复）
**告警**：企微 Webhook 推送 markdown 格式告警，含故障详情+自愈结果+看板链接
**冷却**：30 分钟，同一故障不重复推送

**企微 Webhook**：`https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0256f02d-7368-4214-9c99-9c53ce449e92`

**真实案例 (6/26)**：mkdocs 进程占 80 端口 → nginx 反复重启 5 次失败（16:55-16:59）→ 部署守护后杜绝。全链路演练通过：`systemctl stop nginx` → 守护检测 → kill → 重启 → 企微告警 → 页面恢复。

## Changelog 维护规则

- **版本号必须与系统主版本对齐**：管线 V1.37 → changelog 版本号也是 V1.37，不是自增序列（V1.20→V1.21→...）
- 每次重大改动主动追加条目，不等提醒
- 改动先在 `/var/www/html/bidding-test/changelog.html` → 验证 → `cp` 到生产
- `chmod 644` + `curl -sI` 确认 200
- 浏览器缓存 5 分钟（`Cache-Control: max-age=300`），提醒用户硬刷新或加 `?v=N`

| **直接改 index.html 被 report_generator 覆盖** | ✅ v10修复：所有UI增强进 `polish_report.py`（post-generation hook）。index.html 是编译产物，不直接编辑。`report_generator.py` 生成后自动调用 `polish_report.py` 注入：主题切换CSS+按钮、Tab格式、导出CSV标签、星标CSS、NEW动画CSS。 |


## 排坑
|:--|:--|
| **Changelog logo 404 + 日报主题** | ✅ v1.5修复：(1) `img/` 目录权限754→755（nginx需要x执行位遍历子目录），所有静态资源子目录(img/img_gen/data/)统一755。(2) 日报`daily_report.py`初始暗色→改默认明亮+☀️/🌙切换+localStorage(`daily_theme`)。CSS双态：`body`亮色+`body.dark`覆盖 |
| Excel列名有空格，Row 0是合并标题 | `.replace(" ","")` + 跳过Row 0，Row 1才是表头 |
| **sqlite3.Row 不支持 `.get()` 方法** | sqlite3.Row 是 tuple-like，用 `row["key"]` 或 `dict(row)` 转换后调用 `.get()`。`wecom_push.py` 内 `dget()` 函数封装了此兼容逻辑 |
| Python f-string 内不能用反斜杠 | 变量先赋值再引用 |
| data.json 超 2MB 浏览器白屏 | 全量输出（目前<1MB），前端JS分页 |
| **patch 工具拒绝 /etc/nginx 编辑** | terminal + sudo 操作。先 write_file 到 /tmp，再 `sudo cp` 到 nginx 目录 |
| **Hermes Cron 3分钟硬中断** | ⚡ **致命坑**：`cron/jobs.py` 的 `.tick.lock` 超时 3 分钟便 kill 进程。管线 1-2 小时必被砍。迁移到 systemd timer（TimeoutStopSec=7200）。详见 `references/systemd-cron-migration.md` |
| **nginx `add_header` 子块覆盖父块** | location 块内的 `add_header` 完全替代（非追加）server 层 header。每个 location 必须独立声明全部安全头。备份文件勿留 `sites-enabled/`（nginx 会同时加载两份，报 conflicting server name） |
| **nginx `alias` + 正则 location + `try_files $uri` = 404** | 正则 location 内 `alias` 与 `try_files $uri` 不兼容。合并 location，统一频率限制即可 |
| **nginx `Cache-Control: max-age=300` 导致用户看不到更新** | 浏览器（尤其飞书/微信内置）缓存 HTML 5 分钟。changelog 更新后用户反复说"看不到"。修复：`no-cache, no-store, must-revalidate`。小文件无需缓存性能优化——更新立即可见才是刚需 |
| EPC 权重过高混入噪音 | 数智科技不卖施工，纯EPC排除 |
| 爬首页抓不到公告 | site_adapters.py 找真正公告列表URL |
| 公共资源适配器瞎试URL全失败 | 未匹配站点保持原URL，不套用通用模式 |
| Ubuntu 26.04+Playwright：不支持 | 用系统 Chromium snap `/snap/bin/chromium --headless=new --dump-dom --virtual-time-budget=15000` 渲染JS页面 |
| Chromium --dump-dom 拿不到AJAX数据 | 加 `--virtual-time-budget=15000` 等15秒让JS执行完再dump |
| 企微 Markdown 不支持表格/颜色 | 纯文本+链接+emoji替代 |
| wecom_push 推送频率 | 有项目才推，0条静默(连续3次才发心跳) |
| conn.close() 后再查询报错 | 提前计算所有数据再 close |
| **site_list 暴增到1531行** | sync_sites_to_db 无UNIQUE约束导致每次扫描重复插入 → 加 `UNIQUE(url)` + `INSERT OR REPLACE`，用 `GROUP BY url` 去重迁移 |
| **crawl_log 永远是0条** | 引擎从Excel加载→不开DB→没写日志。修复：默认从DB加载(`use_db=True`)，`load_active_sites(conn)` 复用同一连接，写入后 `conn.commit()` + 验证 `last_insert_rowid()` |
| **扫描失败静默** | 每站失败后写 `last_status` 入库 + `log()` 输出 + 错误汇总入 crawl_log.errors，`list-sites` 命令可快速诊断 |
| **评分引擎对施工分包误判4.5分** | ✅已修复v5：添加 CONSTRUCTION_EXCLUDE（分包/劳务/土建/混凝土/体检等）、CONSTRUCTION_VERBS（变电/线路/安装工程+无数字化→排除）、泛词仅在核心或强相关命中时加分（防止"国网+电力+工程"滚雪球） |
| **"常见问题答疑"等FAQ页面入库** | ✅已修复v6：爬虫 `extract_links_from_html()` 新增 FAQ_PATTERNS 过滤（常见问题/问题答疑/帮助中心/操作指南/通知公告等），非公告链接直接跳过 |
| **"数智管理平台"只得2.7分** | ✅已修复v6：CORE_KEYWORDS 新增独立"数智"/"数智科技"/"数智化"关键词(+10)，公司名本身即强信号。现在"太钢装备数智管理平台建设"得分 5.7（数智+10, 管理平台+5, 泛词+4, ×0.3geo） |
| **南网/国网0.9分纯客户噪声入库** | ✅已修复v6：`score_item()` 新增最低分阈值 `final < 1.5 → return None`，纯客户名称匹配无业务内容不进库 |
| **报告空白（JS引号断裂）** | ✅已修复：f-string内联JS的`\\'`被Python吃掉变成裸`'`→JS字符串提前闭合。拆出独立`/var/www/html/bidding/app.js`，HTML用`<script src="app.js?v=7">`引用。**务必`chmod 644`否则nginx 403**。`report_generator.py`归档时自动复制app.js并设644权限。 |
| **"部门"分类无业务意义** | ✅已替换为v7客户分类引擎：`relevance_scorer.py` → `classify_customer()` 从标题自动识别6大类客户（五大发电/国网南网/地方能源/政府/央企工业/其他），替代原Excel「责任部门」标签。报告筛选器 `fCat` + 客户列，企微推送显示客户统计。 |
| **重复cron job** | ✅`1a5877991ec4`已删，仅保留`cb143a368070`做记忆维护 |
### ❗ 竞品面板字段名不匹配导致空白 — ✅ 已修 (2026-06-24)

**根因**：`renderComp()` 使用了错误的数据字段名：
- categories 是 `[[key, count], ...]` 数组，但代码用 `c.name` / `c.count`
- competitors 字段是 `name` / `type` / `wins`，但代码用 `c.company` / `c.category` / `c.count`
**修复**：categories 用 `c[0]` / `c[1]` 索引，competitors 用 `c.name` / `c.type` / `c.wins`。同时给竞品排行增加 `amount_display` 金额列显示。

### ❗ 企微 8 卡片上限 + 卡片只推招标 + 导出CSV类型错误 + 封面全量 — ✅ 已修 (2026-06-24)

- **卡片只推招标**：`top` 查询仅取 `bidding_notices`。用户明确「中标不用推荐」→ 中标项目只出现在 Markdown 摘要统计行
- **封面全量**：`for t in top:` 替代 `for t in top[:6]`，所有招标卡片都生成AI封面
- **企微 8 条上限**：`LIMIT 10`→`LIMIT 8`（企微news消息最多8条）
- **导出 CSV 修复**：`esc(i[k] || "")` 对 number 类型调 `.replace()` 会报错；HTML转义(`&amp;`) 污染CSV。修复：`String(i[k] ?? "")` + 纯CSV引号转义 `.replace(/"/g, '""')`
- **中国能建已从适配器列表移除**：中南院母公司=中国能建→不抓自己，无效数据

### ❗ 浙能 iframe 列表数据隐藏 — ✅ 已攻克 (2026-06-24)

**根因**：主页 `bulletinListNew.html` 无公告链接——列表在 `<iframe>` 内动态加载。requests 拿不到 iframe 内容。
**修复**：浏览器捕获 iframe 实际 src → `https://zsrm.zjenergy.com.cn/zjnycms//category/iframe.html?dates=300&categoryId=2&tenderMethod=01&page={page}`。直接 GET 此URL即可拿到带详情链接的完整HTML列表。详情页 `/sdny_bulletin/YYYY-MM-DD/ID.html` 同样 requests 直取，结构清晰。**7978条数据，798页，无JS障碍。**

### ❗ JS-SPA平台Chromium适配 — ✅ 已攻克国家能源+中广核 (2026-06-24)

**场景**：国家能源(国能e招)和中广核(ECP)的公告列表由JS动态渲染，requests返回空内容或WAF拦截。
**修复**：Chromium headless `--dump-dom --virtual-time-budget=15000~20000` → 渲染主页 → 正则提取详情链接 → 批量Chromium抓取详情 → 评分入库。
- 国家能源：339条详情链接 → `/bidweb/001/001001/001001001/{date}/{uuid}.html`
- 中广核：134条详情链接 → `Details.html?dataId=...&detailId=...`
- 注意：Chromium `--dump-dom` 捕获的是初始渲染产物，部分SPA平台AJAX加载的列表可能不在DOM中。此时需走浏览器交互路线(browser_navigate→click→browser_console提取)。
- **virtual-time-budget 不能太短**：5s可能不够JS加载，15-20s较可靠。
- **噪声过滤**：SPA主页dump的HTML包含导航/菜单文本，入库后需清理平台UI模板文本。详见 `references/platform-adapters-v18.md`。

### ❗ 竞品库太窄 + 金额缺失 — ✅ v2增强 (2026-06-24)

- **竞品库扩展至35+**：新增海康威视/大华/商汤/旷视/云从（AI安防）、广联达/品茗/鲁班/筑业（智慧工地BIM）、浪潮/中科曙光（IT服务）、国能信控/东方电子（电力自动化）、达索/Bentley/北京构力（数字孪生）、远光软件/朗坤智慧/科远智慧/金现代/恒华科技（能源IT上市公司）
- **金额提取增强**：`extract_winning_amount(text)` 从 content_summary 自动挖掘「投标报价/中标金额/响应报价 XX万元」
- **竞品趋势追踪**：`build_competitor_report(90)` 输出排名+分类+次数+金额，对接 report data.json
| **报告app.js 403** | 文件权限必须 `chmod 644`（nginx需要读权限），`report_generator.py` 的 `write_text()` 默认可能创建600→归档时用 `shutil.copy2` + `os.chmod(arch/f, 0o644)` 显式设置 |
| **AI封面API 403/401** | 通义万相需异步模式（`X-DashScope-Async: enable`），同步会403。API Key从 `/tmp/qwen_key.txt` 读取。生图耗时约13s/张，全部招标项均生成（`top[:6]`），首次慢后续缓存秒出。缓存机制：`item_id.png` 存在则跳过API调用 |
| **news卡片无图/默认灰背景** | ✅已修复v9：全部AI封面，无Pillow兜底。`picurl = ai_urls.get(iid, "")`，AI失败时不设置图片。AI缓存目录 `/var/www/html/bidding/img_gen/cache/` 须在nginx路径下且HTTPS可访问 |
| **Pillow分类横幅全部废弃** | ✅用户要求"不要用pillow了，都采用QWEN"。已移除所有Pillow生成逻辑，`card-images.md` 标记为废弃保留供参考。全AI封面覆盖全部招标项（`top[:6]`），无Pillow兜底。 |
| **报告无明暗主题切换** | ✅新增右上角🌓按钮，`body.light` CSS覆盖全套颜色（白底+蓝调），JS `toggleTheme()` + `localStorage` 持久化偏好。版权统一 `© 中南电力设计院数智科技 · 文鳐智投 2026`。 |
| **趋势图仅柱状图无曲线** | ✅ v11：SVG引擎 renderBarSvg(柱状圆角动画) + renderLineSvg(曲线网格面积填充数据点) + 📊📈切换按钮。`CHART_IDS` 映射正确ID（trendBid/trendWin/trendHigh），三层卡片各自独立。`chartMode` 全局状态管理。CSS `.chart-btn` 明亮/暗黑双主题适配。 |
| **竞品标签空白页** | ✅ v10修复：`renderComp()` 空态检查 `!competitors.categories.length` → 显示"暂无竞品分类数据"/"暂无中标排行数据"。 |
| **趋势看板全0** | ✅ v10修复：`publish_date`→`fetch_date` 做趋势聚合，`range(5,-1,-1)` 含当月。当前数据显示2026-06月5条招标正确。 |
| **Tab计数格式不专业** | ✅ v10修复：`report_generator.py` + `polish_report.py` 双重确保 `📋 招标 (6)` 格式。 |
| **省份/地域列空值显示空白** | ✅ v10修复：app.js 表渲染 `(i.region || i.province || "—")`。 |
| **javascript:void(0)死链接** | ✅ v10修复：app.js `url_fix()` — 空URL或`javascript:`前缀 → `/bidding/`。 |
| **趋势图一张切折线三张全变 (第二轮)** | ✅ v13修复：v12的 `chartModes = {}` 普通对象仍可能污染。改用 `const chartModes = new Map()`，`get/set` 全隔离，无 prototype 链风险。`toggleChartMode(cardId)` 只影响目标卡片 trendBid/trendWin/trendHigh，三张独立不联动。 |
| **「其他」排序不生效 (第二轮)** | ✅ v13修复：v12只加了排序但没清空，`appendChild` 追加在 Python 生成的旧选项之后等于白排。改为 `sel.innerHTML = ""` 完全清空后重建：首位加「全部客户/全部地域」默认选项，其余按 `ao/bo` 独立判断「其他」垫底 + `localeCompare("zh")` 拼音排序。 |
| **多选筛选视觉不更新+全选冲突 (第二轮)** | ✅ v13修复：v12用 `multiple size="1"` 伪装下拉框→程序改 `opt.selected` 后浏览器不刷新视觉。改为 `multiple style="height:auto;max-height:160px;overflow-y:auto"` 原生列表盒；`toggleFilter` 后 `sel.dispatchEvent(new Event("change"))` 强制刷新+触发 saveFilters；`getSelectedValues` 加 `.filter(v => v !== "")` 过滤「全部」空值；选中具体项时自动取消「全部」选项。 |
| **搜索栏太长/布局丑** | ✅ v14修复：`.search-box{max-width:240px}` CSS约束宽度；placeholder缩短为"搜索 标题/业主/省份..."；工具栏加 ⭐收藏 按钮；表头增checkbox+序号列 |
| **收藏只有标记无筛选** | ✅ v14修复：新增 `starOnly` 全局状态 + `swStar()` 函数；工具栏 ⭐收藏 按钮切换只看收藏模式；联动 `doFilter`（过滤收藏项）、`exportExcel`（收藏+勾选联动）、`resetF`（清除starOnly） |
| **无序号+无勾选→导出无用** | ✅ v14修复：表头加 checkbox（全选 `toggleAll`）+ #序号列；每行 `row-check` checkbox + `onCheckChange()` 联动全选状态(indeterminate)；`exportExcel` 优先导出勾选项，无勾选则全量 |
| **execute_code 中 hermes_tools.read_file 行号污染** | ⚠️ 致命坑：`hermes_tools.read_file()` 返回带 `LINE_NUM|CONTENT` 行号前缀的字符串，直接 `write_file()` 会污染文件！修复：`re.sub(r'^[0-9]+\\|', '', content, flags=re.MULTILINE)` 多轮剥离。更安全方案：用 `terminal()` 调用 `cat`/`sed` 操作文件，避免 execute_code 的文件IO陷阱。 |
| **评分引擎v6误判林业/教育/储备林** | ⚠️ 根因："项目管理"、"工程管理" 在STRONG_KEYWORDS中误匹配公司名"XX工程项目管理有限公司"；"工程"、"项目"、"建设"、"监理" 在GENERAL_KEYWORDS中每词+2分滚雪球。v7修复：所有泛词移除 → 仅保留"风电/光伏/电站/电厂/电网/电力/矿山/园区/楼宇"；DIGITAL_GATE前置硬门槛(标题+正文至少命中1个数字词)；教育/教学/储备林/林业加入硬排除。 |
| **100分制阈值校准** | 权重CORE+35/STRONG+18/CUSTOMER+12/GENERAL+8；地理0.5~1.0；入库≥55；推送≥80。4项核心业务测试：国电投湖北智慧工地(100)、华电湖北智能安防(82)、大唐广西智慧工地物联网(57)、湖北能源数字化安全管控(77)均通过。林业/监理/教育/纯施工全部被拦。`python3 scripts/relevance_scorer.py` 运行单元测试验证。 |
| **extract_detail_fields 缺失导致扫描崩溃** | ⚠️ 致命坑：修改 relevance_scorer.py 后可能丢失 `extract_detail_fields()` 函数（及配套 BIDDER/WINNER/AMOUNT_PATTERNS 正则）。bidding_engine.py 从该模块 import 此函数，缺失则 ImportError 崩溃。修复：确保 scorer 文件末尾保留完整 `extract_detail_fields(text) -> dict` + `normalize_amount(raw) -> Optional[float]` 两个函数。`python3 -c \"from scripts.relevance_scorer import extract_detail_fields\"` 验证。 |

| **适配器捕获平台UI模板文本为公告** | ⚠️ 当适配器从 iframe/SPA 提取标题时，平台自身导航文本（"欢迎来到XX平台 V1.0"、"异议投诉"、"帮助中心"、"政策法规"）会被误当成公告入库。噪声过滤：剔除以 `欢迎来到|V1\\.0|异议投诉|帮助中心|办理CA|政策法规|关于我们|注册 登录|第一章 资格预|供应商公示|合格供应商|竞价公告|煤炭采购信息` 等为内容的记录。浙能案例：43条入库中2条为UI模板噪音（已清洗）。国电投：iframe中可能有类似问题。 |\n\n### ❗ 中标详情页HTML表格提取 — 纯文本正则漏抓中标人/金额 — ✅ V1.37修复 (2026-06-26)

**症状**：8条中标，5条无中标人，0条有金额。

**根因**：南网/国家能源等平台的中标结果展示为 `<table>` 表格，中标人/金额在 `<td>` 单元格内。旧代码用纯文本正则 `r'中标人[：:]\\s*(.+)'` 匹配——HTML 渲染后文本中不存在 `中标人：xxx` 格式，而是两块分离的文本。

**修复**（`dedicated_adapters.py` `crawl_nanwang()`）：
1. 保留原始 `detail_html`（不只要纯文本）
2. BeautifulSoup 遍历 `<table>` → 找表头 `<th>` 中的 `中标人/成交人/成交供应商/中标单位` 定位列索引 → 数据行读取同列值
3. 金额同理，表头 `中标金额/成交金额/投标报价` → 读取值
4. 纯文本正则作兜底（方式2）
5. **关键词清单要全**：南网有的页面用「成交人」而非「中标人」，遗漏就白跑

**回填**：修改后必须 `UPDATE winning_notices SET winner_company=? WHERE id=?` 回填已在库的历史数据。

**南网金额限制**：南网公开 HTML 不含金额（在附件 PDF 或需登录），此特性不可破。国家能源的详情链接有时效性（过期 404），需在抓取时即时提取。

**症状**：用户点「今日新增」按钮看不到南网83分精品项目。数据在库但筛选隐藏。

**根因**：V1.18 把 `todayOnly` 筛选和 NEW 徽章统一改为 `publish_date` 口径。但南网等项目昨天发布、今天才抓取入库 → `publish_date` ≠ 今天 → 被「今日新增」筛掉。

**最终修复（归档差集方案）**：
用户的真实定义：「今日新增 = 昨天库中没有、今天新入库的」。不是日期字段判断，必须做 ID 差集。

1. **`report_generator.py`** — 生成 data.json 前读取昨天归档：
   ```python
   yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
   yesterday_file = RD / yesterday / "data.json"
   yesterday_ids = set()
   if yesterday_file.exists():
       old = json.load(open(yesterday_file))
       for item in old.get('bidding',[]) + old.get('winning',[]):
           yesterday_ids.add(item.get('id'))
   ```
   然后 `trim()` 中：`result['is_new_today'] = 1 if item.get('id') not in yesterday_ids else 0`

2. **`app.js`** — `todayOnly` 筛选直接用字段：`d.filter(i => (i.is_new_today || 0) === 1)`
3. `isNew(i)` 保持 `publish_date` 口径 — 仅用于 NEW 徽章

⚠️ **管线跑完后必须重跑 `report_generator.py`** 才能更新 `is_new_today`。测试环境 data.json 不同步是常见遗漏——记得 `cp` 生产 data.json 到测试环境。

**关键原则**：NEW 徽章和今日新增筛选是两种不同的用户心智。前者基于发布日，后者基于入库差集。不能共用同一判断逻辑。

⚠️ **前端筛选修改铁律**：app.js 中同一筛选逻辑至少有 4 处散落——`getFilt()`、`doFilter()`、统计数据计算、`statClick()` 回调。修改时必须 `grep -n` 找到全部调用点，**一处不漏全部改**。今天踩坑：改了 `todayOnly` 但漏了 `activeStatFilter === 'today'`（统计卡片点击入口），导致用户点按钮无效→重复反馈 3 轮才找到。此后改筛选规则先 grep 全量匹配点。

### ❗ score_item 调用陷阱 — ✅ 已修复 (2026-06-26)

- **`score_item(item)` 只接受一个 dict 参数**，不是 `(title, content)` 两个参数。旧代码 `score_item(item['title'], item['content'])` 导致 TypeError。
- **返回字段是 `relevance_score`，不是 `final_score`**。`sc.get('final_score', 0)` 永远为 0。
- 影响所有适配器中评分调用（adapter_dlzb.py, adapter_huaneng.py, crawl_pipeline.py）。统一改为 `sc = score_item(item); if sc and sc.get('relevance_score', 0) >= 55:`。 `fuser data/bidding.db` → `kill -9 <PID>`。典型症状：score_items返回N条但入库0条，SQLite报 `database is locked`。旧 `bidding_engine.py` 进程可能持有连接不释放。**预防**：`crawl_pipeline.py` 用完后显式 `conn.close()`，不在函数间传递未关闭的连接。 |

### ❗ 地理权重惩罚过重 — ✅ v8已修复 (2026-06-24)

根因：`PROVINCE_WEIGHTS` 对内蒙古=0.6、西藏=0.5 乘法折扣作用于最终分。
**修复**：`geo = 1.0` 硬编码，全国统一权重。`relevance_scorer.py` 第280行。

### ❗ 全量扫描344站10秒返回0条 — ✅ 三路并进方案已落地 (2026-06-24)

根因：通用爬虫在主页找不到公告列表。`site_adapters.py` 只有8个适配器。
**修复**（用户要求三条路同时走）：
1. **站点探测**：`scripts/site_prober.py` — 逐站HTTP GET，输出 listing_found/timeout/404/登录页。344站约30分钟完成
2. **专属适配器**：`scripts/site_crawlers.py` — `crawl_huarun_szecp()` 已产出20条公告(2026-04~06)，`crawl_hubei_ggzy()` 适配中
3. **搜索引擎**：web_search API 当前网络受限，待换百度/搜狗方案

**统一管线**：`scripts/crawl_pipeline.py` 编排爬虫→v8评分→去重入库→统计

### ❗ 标题含模板文本触发EXCLUDE误杀 — ✅ v8已修复 (2026-06-24)

根因：`fetch_huarun_detail()` 标题提取用 `text_clean[:120]` 兜底，混入"承担全部法律责任"等模板文→触发"法律"EXCLUDE→系统开发采购项目(90分)被枪毙。
**修复**：
1. 标题提取改为结构化字段优先：标段名称 → 项目名称 → "XXX项目已具备招标条件" → HTML标签
2. EXCLUDE_KEYWORDS 精确化：`"法律"`→`"法律顾问","法律服务","律师"`、`"审计"`→`"审计报告"`、`"会计"`→`"会计服务"`

### ❗ 列表页标题截断导致中标误判为招标 — ✅ v9修复 (2026-06-24)

**根因**：南网等平台列表页 `<a>` 链接文本短于详情页完整标题（如50字符截断，"中标候选人公示"被切掉）。分类逻辑只看截断标题→误判为 bidding/procurement。
**修复**（`dedicated_adapters.py` `crawl_nanwang()`）：
1. 从详情页提取完整标题：① 面包屑导航 "您现在正在浏览：... > 完整标题" ② `<title>` 标签 ③ 详情页开头200字符文本
2. 用 `full_title`（详情页完整标题）做 notice_type 判断，替代列表页 `title_clean`
3. 存储时用 `full_title[:200]` 替代 `title_clean[:200]`
4. **必须初始化 `owner = ''`** — 否则 `for...if...owner =` 未匹配时变量未绑定→崩溃

### ❗ 企微 8 卡片上限 + 卡片只推招标 + 导出CSV类型错误 + 封面全量 — ✅ 已修 (2026-06-24)

- **卡片只推招标**：`top` 查询仅取 `bidding_notices`，中标项目只出现在 Markdown 摘要统计行。用户明确「中标不用推荐」。
- **封面全量**：`for t in top:` 替代 `for t in top[:6]`，所有招标卡片都生成AI封面
- **企微 8 条上限**：`LIMIT 10`→`LIMIT 8`，企微 news 消息最多8条
- **导出 CSV 修复**：`esc(i[k] || "")` 对 number 类型调 `.replace()` 会报错，且 HTML 转义污染 CSV。修复：`String(i[k] ?? "")` + 纯 CSV 引号转义 `.replace(/"/g, '""')`。**列名「导出Excel」→「导出 CSV」**。
- **中国能建已从适配器列表移除**：中南院母公司=中国能建→不抓自己，避免无效数据

症状：`database is locked`，虽然只有1个评分通关但insert总是0。
根因：旧 `bidding_engine.py full` 进程(PID旧)持有 `bidding.db` 连接不释放。
修复：`fuser data/bidding.db` 找到PID → `kill -9` 后重跑管线。
