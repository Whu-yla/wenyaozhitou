# 文鳐智投 - Code Wiki 文档

## 1. 项目概述

**文鳐智投** 是中南电力设计院数智科技公司的智能投标助手系统，专注于标书撰写、投标策略分析和招标信息检索。该系统通过自动化爬取各类招标/中标公告网站，利用AI进行业务相关性评分，生成可视化报告并推送关键信息。

### 核心使命
- 智能采集全国电力行业招标/中标公告
- AI驱动的业务相关性评分与过滤
- 竞品追踪与市场分析
- 可视化报告生成与企微推送

### 技术栈
- **语言**: Python 3.11
- **数据库**: SQLite3（轻量级、嵌入式）
- **爬虫**: Requests + BeautifulSoup + Chromium Headless
- **AI服务**: 火山引擎ARK API (GLM-5模型)
- **向量嵌入**: 通义千问 text-embedding-v3 (1024维)
- **前端**: HTML + CSS + JavaScript（响应式设计）

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        文鳐智投 系统架构                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │  数据采集层   │    │  数据处理层   │    │  数据服务层   │                  │
│  ├──────────────┤    ├──────────────┤    ├──────────────┤                  │
│  │site_adapters │    │relevance     │    │chat_engine   │                  │
│  │dedicated_    │    │  _scorer     │    │memory_engine │                  │
│  │adapters      │    │competitor    │    │report_       │                  │
│  │chromium_     │    │  _tracker    │    │ generator    │                  │
│  │crawler       │    │polish_report │    │wecom_push    │                  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                  │
│         │                   │                   │                          │
│         ▼                   ▼                   ▼                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        数据存储层 (SQLite3)                            │  │
│  │  bidding.db          memory.db          sites.db                      │  │
│  │  ├─bidding_notices   ├─memories         ├─site_list                   │  │
│  │  ├─winning_notices   └─...              └─...                         │  │
│  │  ├─site_list                                                          │  │
│  │  └─crawl_log                                                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│         │                                                                  │
│         ▼                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        前端展示层                                      │  │
│  │  index.html + app.js (响应式、暗色/亮色主题切换)                       │  │
│  │  统计卡片 + 数据表格 + 趋势图表 + 竞品排行                             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 架构特点

| 特点 | 说明 |
|-----|------|
| **轻量级** | 纯Python实现，SQLite嵌入式数据库，无外部依赖 |
| **分层设计** | 采集→处理→服务→展示，职责清晰 |
| **模块化** | 每个功能独立模块，易于扩展和维护 |
| **AI驱动** | GLM模型对话 + 向量语义检索 + 相关性评分引擎 |
| **自动化** | 定时任务自动爬取、生成报告、推送通知 |

---

## 3. 主要模块职责

### 3.1 爬虫引擎模块

#### `bidding_engine.py` - 主爬取引擎
**职责**: 从Excel/数据库加载网站列表，爬取招标/中标公告，评分过滤后入库，生成HTML报告

**核心流程**:
1. **加载站点**: 从数据库`site_list`表加载活跃站点（默认）或从Excel导入
2. **轮转策略**: 每次最多爬取80个站点，按日期轮转选择不同站点段
3. **爬取执行**: 对每个站点调用`crawl_site()`，支持普通HTTP和Chromium JS渲染
4. **评分过滤**: 使用`relevance_scorer`对爬取结果进行业务相关性评分
5. **入库存储**: 去重后存入`bidding_notices`和`winning_notices`表
6. **长记忆**: 将高相关项目和扫描摘要写入长记忆引擎
7. **生成报告**: 调用`report_generator.py`生成数据JSON和归档

**关键函数**:
- `run_crawl()` - 主爬取流程
- `crawl_site()` - 爬取单个网站
- `fetch_page()` - 获取页面HTML
- `extract_links_from_html()` - 提取公告链接
- `save_bidding()` / `save_winning()` - 入库函数

#### `site_adapters.py` - 站点适配器
**职责**: 为已知网站提供优化的公告列表页URL

**核心功能**:
- 维护`SITE_ADAPTERS`字典，映射域名到专用列表页URL
- `get_listing_urls()` - 获取公告列表页URL列表（支持分页）
- `needs_js_render()` - 判断是否需要JS渲染

#### `dedicated_adapters.py` - 专属平台适配器
**职责**: 针对六大六小核心平台的精准爬取（南方电网、国电投、能建、三峡等）

**支持平台**:
| 平台 | 函数 | 说明 |
|-----|------|------|
| 南方电网 | `crawl_nanwang()` | 完整HTML表格解析，提取中标人/金额 |
| 国家电投 | `crawl_guodianta()` | iframe列表，支持Chromium回退 |
| 中国能建 | `crawl_nengjian()` | GBK编码处理 |
| 华润守正 | `crawl_huarun_szecp()` | 复用site_crawlers模块 |
| 三峡集团 | `crawl_sanxia()` | 主页链接提取 |
| JS平台 | `crawl_js_platforms()` | Chromium渲染（浙能、中广核、大唐、国网） |

---

### 3.2 评分引擎模块

#### `relevance_scorer.py` - 业务相关性评分引擎 (v11)
**职责**: 100分制评分，过滤非数字化业务，提取详情字段

**评分体系**:

| 层级 | 关键词类型 | 分值 | 示例 |
|-----|-----------|------|------|
| **基础分** | 通过数字门槛 | 25分 | 含"智慧"、"智能"、"数字"等 |
| **一级核心** | CORE_KEYWORDS | +12分/个（上限3个） | "智慧工地管控平台"、"玄武SSK" |
| **二级强相关** | STRONG_KEYWORDS | +6分/个（上限5个） | "管控平台"、"软件开发" |
| **三级客户** | CUSTOMER_KEYWORDS | +5分/个 | "华能"、"国网"、"南网" |
| **泛行业** | GENERAL_KEYWORDS | +3分/个（上限8个） | "风电"、"光伏"、"电厂" |
| **多样性奖励** | 跨层级匹配 | +4分/类型 | 同时命中核心+强相关+泛行业 |
| **新鲜度奖励** | 近7天发布 | +1~5分 | 越新分值越高 |

**硬门槛**: 标题+正文必须包含至少1个`DIGITAL_GATE`关键词，否则直接丢弃

**排除机制**:
- `EXCLUDE_KEYWORDS` - 非业务领域（医疗、教育、食品、物业等）
- `CONSTRUCTION_EXCLUDE` - 施工劳务类（土建、劳务分包、脚手架等）
- `NON_DIGITAL_EXCLUDE` - 非数字化业务（锅炉、煤矿、土建工程等）

**输出字段**:
- `relevance_score` - 最终评分（0-100）
- `province` / `region` - 地域信息
- `category` - 客户分类（五大发电、国网/南网、地方能源集团等）
- `procurement_owner` - 招标人
- `winner_company` - 中标人（仅中标公告）
- `winning_amount` - 中标金额
- `matched_tags` - 匹配的关键词标签

---

### 3.3 对话引擎模块

#### `chat_engine.py` - AI对话引擎 (v3)
**职责**: 基于火山引擎ARK API，提供投标相关的自然语言查询服务

**核心功能**:
- **数据库快照**: `get_db_snapshot()` 获取全量统计、高相关TOP10招标/中标、中标单位排行、客户分类分布
- **SQL执行**: `execute_sql()` 安全执行SELECT查询（禁止危险操作）
- **LLM对话**: `chat_with_llm()` 调用GLM-5模型进行多轮对话

**对话规则**:
- 必须附带可点击的项目链接
- 引用数据库中的具体数字
- 诚实告知数据缺失情况

---

### 3.4 记忆引擎模块

#### `memory_engine.py` - 长记忆引擎
**职责**: 向量语义存储与检索，支持HOT→WARM→COLD三级记忆体系

**记忆层级**:

| 层级 | 时间范围 | 用途 |
|-----|---------|------|
| 🔥 HOT | <7天 | 当前任务、待办、临时上下文 |
| 🌡️ WARM | 7-30天 | 用户偏好、API参考、关键路径 |
| ❄️ COLD | >30天 | 全部历史知识、语义检索 |

**核心功能**:
- `add_memory()` - 添加记忆（支持去重、语义去重）
- `search_memory()` - 语义搜索（加权余弦相似度）
- `maintain()` - 每日维护（降级旧记忆）
- `deduplicate()` - 去重（删除高度相似的旧记忆）

**嵌入模型**: 通义千问 text-embedding-v3（1024维，L2归一化）

---

### 3.5 报告生成模块

#### `report_generator.py` - 报告生成器 (v5)
**职责**: 从数据库提取数据，生成JSON数据文件和归档

**输出内容**:
- `data.json` - 前端交互数据（招标/中标列表、统计摘要、趋势、竞品）
- `data_full.json` - 全量原始数据
- `YYYY-MM-DD/data.json` - 每日归档（用于明日差集计算）

**调用链**:
1. 提取招标/中标数据
2. 计算今日新增（对比昨日归档差集）
3. 统计省份分布、客户分类
4. 生成6个月趋势数据
5. 获取竞品统计
6. 调用`polish_report.py`增强报告
7. 调用`wecom_push.py`推送企微

#### `polish_report.py` - 报告抛光器 (v4)
**职责**: 增强报告页面，添加主题切换、移动端适配、交互优化

**增强功能**:
- 亮色/暗色主题切换（localStorage持久化）
- 移动端卡片式布局 + 横向滚动
- 桌面端单行紧凑筛选栏
- 密度切换按钮
- 评分图例提示
- Favicon + OG标签
- Chat widget集成

---

### 3.6 竞品追踪模块

#### `competitor_tracker.py` - 竞品追踪引擎 (v1.0)
**职责**: 从中标公告中提取竞品信息，生成排名报告

**核心竞品列表**（30+家）:
- **核心竞品**: 南网数字、南方电网数字、华工精卓、南瑞、国电南自
- **数字科技**: 远光软件、朗坤智慧、科远智慧、金现代、恒华科技、东软
- **电力IT**: 中电普华、四方继保、积成电子

**输出**:
- 中标次数排名
- 总金额统计
- 近期项目列表
- 竞品分类统计

---

### 3.7 企微推送模块

#### `wecom_push.py` - 企微推送 (v8)
**职责**: 每日推送招标TOP8卡片到企业微信

**推送规则**:
- 今日新增≥50分招标TOP8
- 不足5条时补充近7日高相关项目
- 防重复推送（日期锁文件）
- 无新增时发送静默通知

**卡片格式**:
- 标题: 评分 + emoji + 项目名称
- 描述: 客户分类 · 地域 · 招标单位 · 相关性分数
- 图片: 随机封面图

---

## 4. 关键类与函数说明

### 4.1 数据库操作函数

#### `bidding_engine.py`

| 函数 | 说明 | 参数 | 返回值 |
|-----|------|------|-------|
| `get_db()` | 获取数据库连接 | 无 | sqlite3.Connection |
| `make_hash()` | 生成唯一哈希 | title, source_site | str (16位) |
| `is_duplicate()` | 检查重复记录 | conn, unique_hash | bool |
| `save_bidding()` | 保存招标公告 | conn, item | bool (是否新记录) |
| `save_winning()` | 保存中标公告 | conn, item | bool (是否新记录) |
| `load_sites_from_excel()` | 从Excel加载站点 | excel_path | list[dict] |
| `load_active_sites()` | 从数据库加载活跃站点 | conn | list[dict] |

#### `relevance_scorer.py`

| 函数 | 说明 | 参数 | 返回值 |
|-----|------|------|-------|
| `score_item()` | 单条评分 | item(dict) | dict or None |
| `score_items()` | 批量评分 | items(list) | list[dict] |
| `classify_customer()` | 客户分类 | title(str) | str (分类标签) |
| `extract_province()` | 提取省份 | title(str) | tuple (province, region) |
| `extract_detail_fields()` | 提取详情字段 | text(str) | dict |
| `normalize_amount()` | 金额标准化 | raw(str) | float or None |

#### `memory_engine.py`

| 函数 | 说明 | 参数 | 返回值 |
|-----|------|------|-------|
| `init_db()` | 初始化数据库表 | 无 | None |
| `add_memory()` | 添加记忆 | content, category, tags, importance | int (记忆ID) |
| `search_memory()` | 语义搜索 | query, top_k, category, min_similarity | list |
| `get_recent()` | 获取最近记忆 | n, category | list[dict] |
| `maintain()` | 每日维护 | 无 | dict (统计) |
| `deduplicate()` | 去重 | threshold | int (删除数量) |
| `stats()` | 统计信息 | 无 | dict |

---

## 5. 依赖关系

### 5.1 模块依赖图

```
bidding_engine.py
    ├── relevance_scorer.py
    ├── site_adapters.py
    ├── memory_engine.py
    └── report_generator.py (subprocess)
            ├── competitor_tracker.py
            ├── polish_report.py (subprocess)
            └── wecom_push.py (subprocess)

dedicated_adapters.py
    ├── relevance_scorer.py
    └── site_crawlers.py

chat_engine.py
    └── config.yaml

memory_engine.py
    └── requests (通义千问API)

wecom_push.py
    └── requests (企微Webhook)
```

### 5.2 Python包依赖

| 包名 | 用途 | 版本要求 |
|-----|------|---------|
| `requests` | HTTP请求 | - |
| `beautifulsoup4` | HTML解析 | - |
| `openpyxl` | Excel文件处理 | - |
| `numpy` | 向量计算 | - |
| `lxml` | HTML解析器 | - |
| `pyyaml` | YAML配置解析 | - |

### 5.3 外部依赖

| 依赖 | 用途 | 路径 |
|-----|------|------|
| **Chromium** | JS渲染引擎 | `/snap/bin/chromium` |
| **火山引擎ARK API** | LLM对话 | `https://ark.cn-beijing.volces.com/api/coding/v3` |
| **通义千问Embedding** | 向量嵌入 | `https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding` |
| **企微Webhook** | 消息推送 | `https://qyapi.weixin.qq.com/cgi-bin/webhook/send` |

---

## 6. 项目运行方式

### 6.1 目录结构

```
wenyaozhitou/
├── bin/                    # 执行脚本
│   └── tirith
├── config/                 # 配置文件
│   └── qwen_api.json
├── data/                   # 数据库文件
│   ├── bidding.db          # 主数据库（招标/中标/站点/日志）
│   ├── memory.db           # 长记忆数据库
│   ├── sites.db            # 站点信息
│   └── memory_logs/        # 记忆日志
├── scripts/                # 核心脚本模块
│   ├── bidding_engine.py   # 主爬取引擎
│   ├── chat_engine.py      # AI对话引擎
│   ├── relevance_scorer.py # 相关性评分引擎
│   ├── site_adapters.py    # 站点适配器
│   ├── dedicated_adapters.py # 专属平台适配器
│   ├── memory_engine.py    # 长记忆引擎
│   ├── report_generator.py # 报告生成器
│   ├── polish_report.py    # 报告抛光器
│   ├── competitor_tracker.py # 竞品追踪
│   ├── wecom_push.py       # 企微推送
│   ├── site_crawlers.py    # 站点爬虫
│   ├── chromium_crawler.py # Chromium爬虫
│   └── ...
├── memories/               # HOT/WARM记忆文件
│   ├── hot/HOT_MEMORY.md
│   ├── warm/WARM_MEMORY.md
│   ├── YYYY-MM-DD.md
│   └── USER.md
├── logs/                   # 日志文件
│   ├── agent.log
│   ├── gateway.log
│   └── curator/
├── skills/                 # Hermes技能定义
│   └── bidding/            # 投标相关技能
├── cache/reports/          # 报告缓存
├── cron/                   # 定时任务配置
│   └── jobs.json
├── config.yaml             # 主配置文件
└── SOUL.md                 # 身份定义文件
```

### 6.2 配置文件说明

#### `config.yaml` - 主配置

```yaml
agent:
  api_max_retries: 3          # API最大重试次数
  max_turns: 150              # 最大对话轮数
  verbose: false              # 详细日志模式

memory:
  memory_char_limit: 2200     # 记忆字符限制
  memory_enabled: true        # 启用记忆系统
  user_profile_enabled: true  # 启用用户画像

model:
  api_key: ark-xxx            # 火山引擎ARK API Key
  base_url: https://ark.cn-beijing.volces.com/api/coding/v3
  default: glm-5-2-260617     # 默认模型
  provider: custom

platforms:
  feishu:
    streaming: true           # 飞书流式响应
```

### 6.3 数据库表结构

#### `bidding_notices` - 招标公告

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | INTEGER | 主键 |
| title | TEXT | 公告标题 |
| url | TEXT | 详情链接 |
| source_site | TEXT | 来源网站 |
| source_department | TEXT | 责任部门 |
| notice_type | TEXT | 公告类型 |
| publish_date | TEXT | 发布日期 |
| fetch_date | TEXT | 抓取日期 |
| content_summary | TEXT | 内容摘要 |
| relevance_score | REAL | 相关度评分 |
| procurement_owner | TEXT | 招标人 |
| region | TEXT | 地区 |
| province | TEXT | 省份 |
| category | TEXT | 客户分类 |
| unique_hash | TEXT | 去重哈希 |

#### `winning_notices` - 中标公告

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | INTEGER | 主键 |
| title | TEXT | 公告标题 |
| url | TEXT | 详情链接 |
| source_site | TEXT | 来源网站 |
| project_name | TEXT | 项目名称 |
| winner_company | TEXT | 中标单位 |
| winning_amount | TEXT | 中标金额 |
| publish_date | TEXT | 发布日期 |
| fetch_date | TEXT | 抓取日期 |
| content_summary | TEXT | 内容摘要 |
| relevance_score | REAL | 相关度评分 |
| procurement_owner | TEXT | 招标人 |
| region | TEXT | 地区 |
| province | TEXT | 省份 |
| category | TEXT | 客户分类 |
| unique_hash | TEXT | 去重哈希 |

#### `site_list` - 站点列表

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | INTEGER | 主键 |
| site_name | TEXT | 站点名称 |
| url | TEXT | 站点URL |
| platform_type | TEXT | 平台类型 |
| responsible_dept | TEXT | 责任部门 |
| username | TEXT | 用户名 |
| password | TEXT | 密码 |
| ca_cert | TEXT | CA证书 |
| contact_person | TEXT | 联系人 |
| contact_phone | TEXT | 联系电话 |
| notes | TEXT | 备注 |
| is_active | INTEGER | 是否活跃 |
| last_crawl_time | TEXT | 最后抓取时间 |
| last_status | TEXT | 最后状态 |

#### `crawl_log` - 抓取日志

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | INTEGER | 主键 |
| total_sites | INTEGER | 总站点数 |
| success_sites | INTEGER | 成功站点数 |
| failed_sites | INTEGER | 失败站点数 |
| new_bidding | INTEGER | 新增招标数 |
| new_winning | INTEGER | 新增中标数 |
| duration_seconds | REAL | 耗时(秒) |
| errors | TEXT | 错误信息 |

### 6.4 命令行接口

#### `bidding_engine.py`

```bash
# 完整流程：爬取 + 评分 + 入库 + 报告
python3 bidding_engine.py full

# 仅爬取
python3 bidding_engine.py crawl

# 仅生成报告
python3 bidding_engine.py report

# 导出数据JSON
python3 bidding_engine.py export-data

# 统计信息
python3 bidding_engine.py stats

# 列出活跃站点
python3 bidding_engine.py list-sites

# 从Excel同步站点到数据库
python3 bidding_engine.py sync-sites --excel /path/to/sites.xlsx

# 批量激活站点（仅数智/智能部门）
python3 bidding_engine.py activate-sites --excel /path/to/sites.xlsx
```

#### `memory_engine.py`

```bash
# 查看统计
python3 memory_engine.py

# 添加记忆
python3 memory_engine.py add "内容" "分类"

# 语义搜索
python3 memory_engine.py search "查询关键词"

# 每日维护（降级旧记忆）
python3 memory_engine.py maintain

# 去重
python3 memory_engine.py dedup
```

#### `dedicated_adapters.py`

```bash
# 执行专属平台爬取
python3 dedicated_adapters.py
```

#### `competitor_tracker.py`

```bash
# 生成竞品报告（90天）
python3 competitor_tracker.py
```

### 6.5 定时任务

系统通过Cron定时执行以下任务：

| 任务 | 频率 | 说明 |
|-----|------|------|
| 爬取+报告 | 每日定时 | 完整爬取流程，生成报告并推送 |
| 专属平台爬取 | 每日定时 | 南方电网、国电投等核心平台单独爬取 |
| 记忆维护 | 每日定时 | HOT→WARM→COLD降级，去重 |
| 企微推送 | 每日定时 | 推送招标TOP8 |

### 6.6 前端访问

报告页面部署在 `http://<host>/bidding/`，功能包括：

- **统计卡片**: 累计招标/中标、今日新增、高相关项目
- **搜索筛选**: 按标题、招标单位、省份、相关度、日期、预算筛选
- **数据表格**: 招标/中标/收藏三个标签页，支持排序和分页
- **趋势图表**: 6个月招标/中标趋势
- **竞品排行**: 中标单位排名和金额统计
- **主题切换**: 亮色/暗色模式
- **密度切换**: 紧凑/标准行密度

---

## 7. 启动加载序列

每次会话开始时自动执行：

```
1. 确认身份 → SOUL.md
2. 读取用户记忆 → memory/USER.md
3. 读取今日日志 → memory/YYYY-MM-DD.md（不存在则创建）
4. 读取HOT记忆 → memory/hot/HOT_MEMORY.md（恢复当前状态）
5. 读取WARM记忆 → memory/warm/WARM_MEMORY.md（加载稳定配置）
6. 语义搜索长记忆 → 获取相关历史记忆
7. 开始处理任务
```

---

## 8. 扩展指南

### 8.1 添加新站点

1. **在`site_adapters.py`中添加适配器**:
   ```python
   SITE_ADAPTERS = {
       "example.com": "https://www.example.com/bidding-list?page={page}",
   }
   ```

2. **如果需要JS渲染**:
   ```python
   JS_SITES = {"example.com", ...}
   ```

3. **如果需要专属爬取逻辑**: 在`dedicated_adapters.py`中添加`crawl_example()`函数

### 8.2 修改评分规则

1. **在`relevance_scorer.py`中修改关键词列表**:
   - `DIGITAL_GATE` - 数字/智慧硬门槛
   - `CORE_KEYWORDS` - 一级核心产品（+12分）
   - `STRONG_KEYWORDS` - 二级强相关（+6分）
   - `CUSTOMER_KEYWORDS` - 三级客户（+5分）
   - `GENERAL_KEYWORDS` - 泛行业词（+3分）
   - `EXCLUDE_KEYWORDS` - 排除词

2. **调整评分逻辑**: 修改`score_item()`函数中的评分权重

### 8.3 添加竞品

在`competitor_tracker.py`的`CORE_COMPETITORS`字典中添加新竞品：

```python
CORE_COMPETITORS = {
    "新竞品名称": "公司全称",
}
```

---

## 9. 常见问题

### Q1: 爬取失败怎么办？
**A**: 检查站点是否需要JS渲染，尝试使用`chromium_fetch()`。检查网络连接和网站反爬策略。

### Q2: 评分不准确怎么办？
**A**: 调整`relevance_scorer.py`中的关键词列表，添加或修改评分规则。

### Q3: 报告不更新怎么办？
**A**: 检查`report_generator.py`是否正常执行，检查数据库连接是否正常。

### Q4: 企微推送失败怎么办？
**A**: 检查Webhook URL是否正确，检查KILL_SWITCH是否关闭，检查网络连接。

---

## 10. 版本历史

| 版本 | 日期 | 主要变更 |
|-----|------|---------|
| v1 | - | 初始版本，基础爬虫功能 |
| v2 | - | 切换到DeepSeek API（已废弃） |
| v3 | - | 切换到火山引擎ARK API |
| v5 | - | 报告生成器重设计 |
| v7 | - | 100分制评分，数字门槛 |
| v8 | - | 放宽硬门槛，增加IT项目 |
| v9 | - | AI & 产品线关键词 |
| v10 | - | 信息安全 & 等保关键词 |
| v11 | - | IT信息化服务关键词，日期新鲜度衰减 |

---

*文档生成时间: 2026-07-20*
*项目归属: 中南电力设计院数智科技公司 / 研发中心团队*
