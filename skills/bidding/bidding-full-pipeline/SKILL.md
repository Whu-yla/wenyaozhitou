---
name: bidding-full-pipeline
description: 文鳐智投完整定时任务管线——采集→评分(v11)→竞品追踪→趋势→报告→推送。每次 systemd 定时任务必须执行全部 6 阶段，覆盖全部 87 个 listing_found 站点。⚠️ 必须使用 venv Python。
category: bidding
---

# 文鳐智投 · 完整定时任务管线 v5
# ⚠️ Python 依赖：必须用 venv Python（/usr/local/lib/hermes-agent/venv/bin/python3）
# ⚠️ 评分引擎 v12（V1.11）— 精细化评分+三层拦截架构

## 站点全景

| 层级 | 数量 | 说明 |
|:--|:--|:--|
| 📋 Excel 全量 | 344 站 | 投标网站注册信息汇总表 |
| ✅ listing_found | **87 站** | HTTP 探测通过，有公告列表页 |
| ❌ no_listing | 125 站 | 无公告列表 |
| ❌ 连接失败/超时 | 97 站 | 不可达 |
| 🏆 专属适配器 | 8 站 | 精准 HTML 解析，产出最高 |
| 🔄 通用爬虫覆盖 | 87 站 | batch_crawler 逐站爬（含专属适配器站点双保险） |

## 触发条件

**每天 8:00 一次**，systemd timer 自动触发，执行全部 6 阶段（含企微推送）。

> ⚠️ 2026-07-01 精简：原 8:30 单独推送定时器（`wenyao-push.timer`）已删除——推送已内嵌在管线阶段5，不需要独立定时器。分离推送容易导致「管线没跑完但推送触发」或「重复推送」。

## 执行流程

### 阶段 1：全平台采集 —— 四连跑

**主控脚本（推荐，no_agent cron 使用）**：
```bash
bash /root/.hermes/profiles/wenyaozhitou/scripts/pipeline_master.sh
```
内部顺序执行四脚本，每步有 timeout 保护，出错不中断。

**手动分步执行**：

第一路：专属适配器
```bash
cd /root/.hermes/profiles/wenyaozhitou && PY=/usr/local/lib/hermes-agent/venv/bin/python3 && $PY scripts/crawl_pipeline.py
```
覆盖：华润守正、湖北公共资源、南网、浙能、国家能源
```bash
cd /root/.hermes/profiles/wenyaozhitou && $PY scripts/dedicated_adapters.py
```
覆盖：三峡集团、国家电投、中广核 + 南网/华润双保险

**第二路：87 站通用批量爬虫（全覆盖！）**
```bash
cd /root/.hermes/profiles/wenyaozhitou && timeout 900 $PY scripts/batch_crawler.py
```
从 `data/probe_results.json` 加载全部 87 个 listing_found 站点逐个爬取，timeout 15 分钟。

**第三路：Chromium JS 渲染增强**
```bash
cd /root/.hermes/profiles/wenyaozhitou && timeout 300 $PY scripts/chromium_crawler.py
```
中广核等 JS-SPA 平台兜底。

## 去重机制

**v2 (2026-06-25)**: unique_hash 统一为 URL-only。6个爬虫全部使用：
```python
h = hashlib.md5((url or '').encode()).hexdigest()
```
不再混入 title/source_site 等易截断字段。详见 `wenyao-bidding` 的 `references/unique-hash-standardization.md`。

## 列表页误抓防护

batch_crawler 自动排除 `category`/`bulletinList`/`purchaseList` 等分类页URL。详见 `wenyao-bidding` 的 `references/list-page-filtering.md`。

## 数据策略

data.json > 1MB → 立即生成 data_light.json（id/title/score/source，4字段极简）。
data/ 子目录权限：`find /var/www/html/bidding -type f -exec chmod 644 {} \;` — 必须递归！详见 `references/data-strategy.md`。

### 阶段 2：数据清洗
```bash
cd /root/.hermes/profiles/wenyaozhitou && PY=/usr/local/lib/hermes-agent/venv/bin/python3 && $PY -c "
import sqlite3
conn = sqlite3.connect('data/bidding.db')
cur = conn.cursor()
cur.execute(\"DELETE FROM bidding_notices WHERE title LIKE '%终止公告%'\")
cur.execute(\"DELETE FROM bidding_notices WHERE title LIKE '招标网%' OR title LIKE '国能e招%'\")
conn.commit()
conn.close()
print('清洗完成')
"
```

### 阶段 3：竞品追踪（必须执行！）
```bash
cd /root/.hermes/profiles/wenyaozhitou && $PY scripts/competitor_tracker.py
```

### 阶段 4：生成报告
```bash
cd /root/.hermes/profiles/wenyaozhitou && $PY scripts/report_generator.py
chmod -R 755 /var/www/html/bidding/
find /var/www/html/bidding -type f -exec chmod 644 {} \;
```

### 阶段 5：企微推送
```bash
cd /root/.hermes/profiles/wenyaozhitou && $PY scripts/wecom_push.py
```

### 阶段 6：数据库维护
```bash
cd /root/.hermes/profiles/wenyaozhitou && python3 -c "
import sqlite3
conn = sqlite3.connect('data/bidding.db')
conn.execute('ANALYZE')
conn.execute(\"DELETE FROM crawl_log WHERE crawl_time < datetime('now','-90 days')\")
conn.commit()
conn.close()
print('DB维护完成')
"
```

## 🔧 调试模式（禁止企微推送）

当需要手动跑管线但**不推送到企微群**时，使用双重保险：

| 层 | 机制 | 说明 |
|:--|:--|:--|
| L1 | `KILL_SWITCH = True` | `wecom_push.py` 全局拦截 |
| L2 | `/tmp/wenyao_push.lock` | 日锁，同天第二次自动跳过 |

**三步 SOP**：开 KILL_SWITCH → 跑管线 → 恢复 KILL_SWITCH。

> 完整 SOP 见 `references/debug-mode-no-webhook.md`

## 覆盖矩阵（87站）

| 分类 | 站点 | 适配方式 | 状态 |
|:--|:--|:--|:--|
| 🏆 六大发电 | 华能、华电、大唐、国电投、国家能源、三峡 | 专属+通用 | 能爬尽爬 |
| 🏆 六小发电 | 中广核、华润、国投、中核、中节能、中国电建 | 专属+通用 | 能爬尽爬 |
| 🏆 电网 | 南网、国网 | 专属+通用 | 南网✅ |
| 🏆 地方能源 | 浙能、深圳能源、内蒙古电力等 | 专属+通用 | 浙能✅ |
| 🔄 公共资源 | 77 地方公共资源交易中心 | 通用批量 | batch_crawler |
| 🔄 其他 | 中国采购招标网、中招联合等 | 通用批量 | batch_crawler |

## ⚠️ Cron 执行机制 —— 已迁移至 systemd（2026-06-24）

### 🔴 致命坑：Hermes Cron 3 分钟硬中断

**无论 `no_agent` 还是 Agent 模式，Hermes cron 对所有任务有 3 分钟硬中断。** 管线需要 1-2 小时，每次在第 3 分钟被 kill，状态显示 `error`。这是 Hermes scheduler 层限制，无法通过配置绕过。

### ✅ 解决方案：systemd timer

管线已迁移至 Linux systemd timer，不受 Hermes 限制：

**服务文件：`/etc/systemd/system/wenyao-pipeline.service`**
```ini
[Service]
Type=oneshot
WorkingDirectory=/root/.hermes/profiles/wenyaozhitou
ExecStart=/bin/bash .../scripts/pipeline_master.sh
TimeoutStopSec=7200    # ← 2 小时，管线实际需 1-2h
```

**定时器：`/etc/systemd/system/wenyao-pipeline.timer`**
```ini
[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true        # 错过时间点补跑
RandomizedDelaySec=60  # 错峰 1 分钟
```

**当前定时器全景**（3个）：

| 定时器 | 时间 | 用途 |
|:--|:--|:--|
| `wenyao-pipeline.timer` | 每天 08:00 | 全管线(采集→评分→竞品→报告→**推送**) |
| `wenyao-selfheal.timer` | 每天 03:00 | 凌晨自检+反馈修复 |
| `wenyao-memory.timer` | 每天 09:00 | 记忆维护 |

### Hermes cron 保留项

仅保留短任务：
- `nginx_guard.sh`（每1分钟，`no_agent=true`）— nginx + bookmark_server 守护
- 记忆维护脚本（每天 9:00）— 数秒完成

> 完整 systemd 配置文件见 `references/systemd-cron-migration.md`

## ⚠️ Systemd 管线铁律（2026-06-24 建立，2026-07-01 精简）

1. 任何预计运行 **超过 2 分钟** 的定时任务 → **必须用 systemd timer**，不能用 Hermes cron
2. **所有 systemd 服务和定时脚本必须用 venv Python**：`PY="/usr/local/lib/hermes-agent/venv/bin/python3"`
3. **管线每天只跑一次**（08:00），6阶段全跑。不要拆出独立推送定时器——推送是管线阶段5
4. **数据策略**：data.json > 1MB 时立即生成 data_light.json（id/title/score/source），禁止 raw_text/raw_html 进前端 JSON
5. Hermes cron 只跑秒级/分钟级 watchdog 型脚本（`nginx_guard.sh`）
6. 阶段 1 必须跑四脚本（pipeline + dedicated + batch_crawler + chromium），覆盖全部 87 站
7. 出错不中断，逐阶段 `|| log "⚠️"` 继续
8. 总耗时 10-20 分钟正常，systemd `TimeoutStopSec=7200` 兜底
9. 去重靠 `unique_hash`（URL-only），重复爬不产生脏数据
10. **企业微信防重复**：`wecom_push.py` 内置 `/tmp/wenyao_push.lock` 日锁，同天第二次调用自动跳过
11. **⛔ 不要为推送建独立 systemd 定时器**——推送必须在管线内作为阶段5执行，分离会导致时序混乱

## ⛔ 致命坑：systemd Python 路径陷阱（2026-06-25 — 全站停摆一天）

**症状**：定时任务准时跑，日志显示 `ModuleNotFoundError: No module named 'bs4'`，三路采集全部崩溃，数据永远停在旧值。用户质问「定时任务都在干嘛？？」

**根因**：systemd 运行在干净环境中，`python3` → `/usr/bin/python3`（PEP 668 锁死，无 bs4）。依赖只装在 Hermes venv：`/usr/local/lib/hermes-agent/venv/bin/python3`

**修复**：
1. 所有 shell 脚本定义 `PY="/usr/local/lib/hermes-agent/venv/bin/python3"`，全局替换 `python3` → `$PY`
2. systemd service 的 `ExecStart` 使用 venv Python 绝对路径
3. 验证：`env -i PATH=/usr/local/bin:/usr/bin python3 -c "import bs4"` 必须成功

**受影响脚本（已修复）**：
- `pipeline_master.sh` — 采集管线主控
- `push_daily_report.sh` — 日报生成+推送
- `wenyao-selfheal.service` — 凌晨自检
- `wenyao-memory.service` — 记忆维护

> 详细排查过程见 `wenyao-bidding` skill 的「⛔ systemd 服务 Python 路径陷阱」章节。
