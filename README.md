# 文鳐智投 (Wenyao Zhitou)

> 中南电力设计院数智科技公司 · 智能投标助手系统

文鳐智投是一个专注于**标书撰写、投标策略分析和招标信息检索**的智能助手系统。通过自动化爬取各类招标/中标公告网站，利用 AI 进行业务相关性评分，生成可视化报告并推送关键信息。

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    文鳐智投 系统架构                      │
├──────────────┬──────────────────────────────────────────┤
│   数据采集层  │ 8 直连适配器 + 9 DLZB 适配器 + Chromium   │
│              │ 覆盖 344+ 招标/中标网站                    │
├──────────────┼──────────────────────────────────────────┤
│   AI 评分层   │ V1.35 集中式页面判别器 (relevance_scorer) │
│              │ 22 个垃圾信号词过滤 + 0-100 分精准评分     │
├──────────────┼──────────────────────────────────────────┤
│   报告生成层  │ 每日 HTML 报告 + data.json 实时数据       │
│              │ polish_report.py 样式精修                  │
├──────────────┼──────────────────────────────────────────┤
│   前端展示层  │ 响应式 Web (Nginx) + AI 对话引擎          │
│              │ https://www.yfzx.online/bidding/          │
├──────────────┼──────────────────────────────────────────┤
│   推送通知层  │ 企微 Webhook 日报推送 + 点赞/点踩反馈      │
├──────────────┼──────────────────────────────────────────┤
│   运维保障层  │ Systemd 定时任务 + Nginx 端口守护自愈      │
│              │ 3 层记忆系统 (HOT/WARM/COLD)              │
└──────────────┴──────────────────────────────────────────┘
```

## 📁 项目结构

```
wenyaozhitou/
├── scripts/                    # 后端 Python 脚本
│   ├── bidding_engine.py       # 核心爬虫引擎
│   ├── relevance_scorer.py     # AI 评分引擎 (V1.35 集中式判别器)
│   ├── report_generator.py     # 报告生成器 (data.json)
│   ├── polish_report.py        # 报告样式精修
│   ├── daily_report.py         # 每日分析报告
│   ├── bookmark_server.py      # API 服务器 (Flask)
│   ├── chat_engine.py          # AI 对话引擎 (GLM-5.2)
│   ├── crawl_pipeline.py       # 采集管线
│   ├── batch_crawler.py        # 批量爬虫
│   ├── chromium_crawler.py     # Chromium 动态渲染爬虫
│   ├── adapter_dlzb.py         # DLZB 平台适配器
│   ├── adapter_guoneng.py      # 国能适配器
│   ├── adapter_huaneng.py      # 华能适配器
│   ├── adapter_mengxi.py       # 蒙西适配器
│   ├── adapter_zheneng.py      # 浙能适配器
│   ├── adapter_supplement.py   # 补充适配器
│   ├── dedicated_adapters.py   # 专用适配器集
│   ├── site_crawlers.py        # 站点爬虫
│   ├── site_adapters.py        # 站点适配器基类
│   ├── site_prober.py          # 站点探测器
│   ├── competitor_tracker.py   # 竞品追踪
│   ├── daily_data.py           # 每日数据
│   ├── wecom_push.py           # 企微推送
│   ├── nginx_guardian.py       # Nginx 端口守护
│   ├── nginx_guard.sh          # Nginx 守护脚本
│   ├── selfheal_3am.py         # 凌晨 3 点自愈
│   ├── ai_cover.py             # AI 封面图生成
│   ├── memory_engine.py        # 长记忆引擎
│   ├── memory_maintainer.py    # 记忆维护
│   ├── pipeline_master.sh      # 管线主脚本
│   ├── promote.sh              # 测试→生产 推送脚本
│   └── push_daily_report.sh    # 日报推送脚本
│
├── frontend/                   # 前端 Web 资源
│   ├── index.html              # 主页（招标/中标双 Tab）
│   ├── app.js                  # 前端核心逻辑
│   ├── chat-widget.js          # AI 对话组件
│   ├── chat-widget.css         # 对话组件样式
│   ├── changelog.html          # 更新日志
│   ├── manual.html             # 操作手册
│   ├── journey.html            # 发展历程
│   ├── wenyao-story.html       # 品牌故事
│   ├── safety.html             # 安全规范
│   ├── training-notice.html    # 培训通知
│   └── data.json               # 实时招标数据
│
├── config/                     # Systemd 服务配置
│   ├── wenyao-pipeline.service # 采集管线服务
│   ├── wenyao-pipeline.timer   # 采集定时器 (08:00)
│   ├── wenyao-memory.service   # 记忆维护服务
│   ├── wenyao-memory.timer     # 记忆定时器 (09:00)
│   ├── wenyao-selfheal.service # 自愈服务
│   ├── wenyao-selfheal.timer   # 自愈定时器 (03:00)
│   ├── nginx-guardian.service  # Nginx 守护服务
│   └── nginx-guardian.timer    # Nginx 守护定时器 (每分钟)
│
├── memory/                     # 三层记忆系统
│   ├── hot/                    # 🔥 HOT - 当前任务/临时上下文
│   ├── warm/                   # 🌡️ WARM - 用户偏好/稳定配置
│   └── daily/                  # 📋 DAILY - 每日活动流水
│
├── cache/                      # 缓存数据
│   └── documents/              # 文档缓存
│
└── .gitignore
```

## 🔧 技术栈

| 层级 | 技术 |
|:-----|:-----|
| 后端语言 | Python 3.11 |
| Web 框架 | Flask (bookmark_server) |
| AI 模型 | GLM-5.2 (对话) / 通义千问 text-embedding-v3 (记忆) |
| 动态渲染 | Chromium / Playwright |
| 前端 | 原生 HTML + CSS + JavaScript |
| Web 服务器 | Nginx |
| 进程管理 | Systemd (4 组 timer) |
| 消息推送 | 企业微信 Webhook |
| 数据库 | SQLite (书签/收藏) |

## 🚀 核心功能

### 1. 招标信息采集
- 覆盖 **344+** 招标/中标网站（六大六小发电集团 + 国网南网 + 77 地方公共资源交易中心）
- 8 个直连适配器 + 9 个 DLZB 适配器 + Chromium 动态渲染
- 每日 08:00 自动执行全量采集

### 2. AI 相关性评分
- V1.35 集中式页面判别器（`relevance_scorer.py`）
- 22 个垃圾信号词过滤
- 0-100 分精准评分，面向数智科技业务方向
- 排除 EPC 总承包/施工类项目

### 3. 可视化报告
- 响应式 Web 界面（招标/中标双 Tab）
- 实时数据更新（data.json）
- 每日 HTML 分析报告
- AI 封面图自动生成

### 4. AI 对话引擎
- GLM-5.2 驱动的智能问答
- 支持多轮对话上下文
- 从 Hermes config.yaml 动态读取 LLM 配置

### 5. 企微推送
- 每日 20:00 自动推送分析报告
- 点赞/点踩反馈闭环
- 异常告警实时推送

### 6. 运维自愈
- Nginx 端口守护（每分钟检测）
- 凌晨 3:00 自愈脚本
- 三层记忆系统（HOT/WARM/COLD）

## ⚙️ 部署

### 前置条件
- Python 3.11+
- Nginx
- Systemd
- Chromium (动态渲染爬虫)

### 安装步骤

```bash
# 1. 克隆仓库
git clone git@github.com:Whu-yla/wenyaozhitou.git
cd wenyaozhitou

# 2. 安装 Python 依赖
pip install flask requests beautifulsoup4 lxml playwright

# 3. 配置 Nginx
sudo cp frontend/* /var/www/html/bidding/
sudo chmod 644 /var/www/html/bidding/*

# 4. 配置 Systemd 服务
sudo cp config/*.service config/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wenyao-pipeline.timer
sudo systemctl enable --now wenyao-memory.timer
sudo systemctl enable --now wenyao-selfheal.timer
sudo systemctl enable --now nginx-guardian.timer

# 5. 配置 API 密钥
echo "your_qwen_api_key" > /tmp/qwen_key.txt

# 6. 配置企微 Webhook (编辑 scripts/wecom_push.py)
# 替换 YOUR_WEBHOOK_KEY 为你的企微机器人 key
```

## 📊 数据流

```
招标网站 → 适配器采集 → 原始数据 → AI 评分 → data.json → Nginx 前端
                                    ↓
                              每日报告 → 企微推送 → 用户反馈
                                    ↓
                              三层记忆系统
```

## 🔒 安全说明

- 企微 Webhook key 已脱敏，部署时需替换 `YOUR_WEBHOOK_KEY`
- API 密钥从文件/环境变量动态读取，不硬编码在代码中
- 投标网站注册信息汇总表（含用户名/密码/CA）不纳入版本控制

## 📝 版本

当前版本: V1.37 (2026-07-20)

## 📄 License

MIT
