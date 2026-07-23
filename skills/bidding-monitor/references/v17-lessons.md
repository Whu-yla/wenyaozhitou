# v17 关键教训与架构决策 (2026-06-24)

## 专属适配器 > 通用爬虫
通用爬虫（batch_crawler.py）对六大六小发电集团平台无效。87站通用抓数百条只入库1-2条。专属适配器单平台产9条（南网）。
**核心架构**：`dedicated_adapters.py` 是主驱动，每个平台独立函数 + 精准HTML解析。

## 招标/中标分流
- `winning_notices` 表独立存储中标结果
- 企微卡片只推招标（bidding），不推中标
- `notice_type` 从详情页完整标题判断（非列表页截断标题）
- 中标数据用于竞品追踪

## 竞品追踪引擎
`competitor_tracker.py`：
- 从 `winning_notices.content_summary` 提取中标公司
- 已知竞品库（南网数字/南瑞/国电南自等）→ 核心竞品
- 公司名含「数字/科技/信息/软件/智能」→ 自动标记潜在竞品
- 接口：`get_competitor_stats(days=90)` → `{competitors, categories}`

## 导出CSV修复历程
v1: `esc(i[k] || "").replace(/"/g, '""')` → HTML转义污染CSV + number类型报错
v3: `String(i[k] ?? "")` + `.replace(/"/g, '""')` → 纯CSV转义，类型安全

## 中国能建不可抓
中南院母公司 = 中国能建。`ec.ceec.net.cn` 从 `dedicated_adapters.py` 移除。

## 标题截断导致中标误判
南网列表页 `<a>` 文本截断50字符，丢失"中标候选人公示"后缀。
修复：从详情页提取完整标题（面包屑导航 / `<title>` 标签 / 详情页前400字符文本）。

## 封面全量
`for t in top:` 替代 `for t in top[:6]`，所有招标卡片都生成AI封面。
企微 news 最多8条，`LIMIT 8`。

## DB锁
旧 `bidding_engine.py` 进程持有 `bidding.db` 不释放。
`fuser data/bidding.db` + `kill -9 <PID>` 解决。

## 评分引擎 v9 新增关键词
AI/人工智能：大模型/深度学习/机器学习/计算机视觉/NLP/LLM/图像识别/语音识别/AI平台
产品线：玄武SSK/玄武/SSK/有限空间/执法记录仪

## owner 变量必须初始化
`dedicated_adapters.py` `crawl_nanwang()` 中 `owner = ''` 必须在 for 循环前初始化，否则无匹配时变量未绑定→崩溃。
