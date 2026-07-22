# 🌡️ WARM MEMORY — 文鳐智投

> 稳定配置、用户偏好、API参考、关键坑点 | 变化时更新 · 几乎不删

## 用户信息
- 名称：文鳐智投
- 归属：中南电力设计院数智科技
- 核心使命：投标 (bidding/tendering) 智能助手

## 编程约定
- 语言：中文
- 风格：简洁、友好、专业、高效
- 运行环境：Linux, Python 3.11
- ⚠️ 必须用 venv Python: `/usr/local/lib/hermes-agent/venv/bin/python3`

## API 配置位置
- Qwen Embedding API Key: `/tmp/qwen_key.txt`
- DeepSeek API: 系统配置 (config.yaml)

## 投标监控系统

**报告地址**：https://www.yfzx.online/bidding/ （必须带 www）
**测试环境**：https://www.yfzx.online/bidding-test/

| 用途 | 路径 |
|:-----|:-----|
| 全流程管线 | `scripts/pipeline_master.sh` |
| 专属适配器 | `scripts/dedicated_adapters.py` |
| 采集管线 | `scripts/crawl_pipeline.py` |
| 批量爬虫 | `scripts/batch_crawler.py` |
| Chromium爬虫 | `scripts/chromium_crawler.py` |
| 评分引擎 | `scripts/relevance_scorer.py` |
| 报告生成 | `scripts/report_generator.py` |
| UI抛光 | `scripts/polish_report.py` |
| 企微推送 | `scripts/wecom_push.py` |
| 竞品追踪 | `scripts/competitor_tracker.py` |
| 数据库 | `data/bidding.db` |
| HTML报告 | `/var/www/html/bidding/index.html` |
| 测试报告 | `/var/www/html/bidding-test/index.html` |
| 网站Excel | `cache/documents/...投标网站注册信息汇总表2026.6月.xlsx` |

**定时任务（systemd timer）**：
| 定时器 | 时间 | 用途 |
|:--|:--|:--|
| wenyao-pipeline.timer | 每天 08:00 | 全管线(采集→评分→竞品→报告→推送) |
| wenyao-selfheal.timer | 每天 03:00 | 凌晨自检+反馈修复 |
| wenyao-memory.timer | 每天 09:00 | 记忆维护 |

**核心规则**：
- 每次抓取必须存库（自动去重，unique_hash=URL-only MD5）
- 数据库持续累积，用于长期统计分析
- 覆盖87个listing_found站点+77地方公共资源交易中心
- 评分≥55入库，推送≥50

## 长记忆引擎

**新路径（已迁移）**：

| 用途 | 路径 |
|:-----|:-----|
| 引擎 | `scripts/memory_engine.py` |
| 维护 | `scripts/memory_maintainer.py` |
| 向量DB | `data/memory.db` |
| 日报 | `data/memory_logs/digest_YYYY-MM-DD.md` |
| HOT | `memory/hot/HOT_MEMORY.md` |
| WARM | `memory/warm/WARM_MEMORY.md` |
| 每日日志 | `memory/YYYY-MM-DD.md` |

所有路径相对于 `HERMES_HOME=/root/.hermes/profiles/wenyaozhitou/`

```bash
# 存储/搜索（使用新路径）
cd /root/.hermes/profiles/wenyaozhitou
python3 scripts/memory_engine.py search "查询" --top 5
python3 scripts/memory_maintainer.py
```

## 关键坑点
- ⛔ systemd 必须用 venv Python（系统 python3 无 bs4）
- ⛔ report_generator 只生成 data.json，不覆盖 index.html
- ⛔ 生产环境锁定：先改测试环境 /bidding-test/，验证后才能推生产
- ⛔ Feishu 链接不能用 Markdown 星号包裹
- ⛔ data.json > 1MB 立即生成 data_light.json
