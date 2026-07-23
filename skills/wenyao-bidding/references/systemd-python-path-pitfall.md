# systemd Python 路径陷阱 — 完整诊断与修复

## 现象

- `systemctl list-timers` 显示任务正常触发
- `journalctl -u wenyao-pipeline --since today` 显示 `ModuleNotFoundError: No module named 'bs4'`
- 数据库计数不变（`SELECT COUNT(*) FROM bidding_notices` 同昨天）
- 企微无新推送（因为无新数据）
- 但手动 `python3 scripts/crawl_pipeline.py` 能跑——因为手动时有 venv 环境

## 根因

systemd 运行在干净环境中，PATH 只含系统路径：
```
/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

`which python3` → `/usr/bin/python3`（系统 Python 3.14，受 PEP 668 保护，禁止 `pip install`）

而 Hermes venv Python 在 `/usr/local/lib/hermes-agent/venv/bin/python3`，含 bs4/lxml/requests 等全部依赖。

## 修复

### 方案A：shell 脚本用变量（推荐）

```bash
PY="/usr/local/lib/hermes-agent/venv/bin/python3"
$PY scripts/crawl_pipeline.py
```

### 方案B：systemd service 直接用全路径

```ini
[Service]
ExecStart=/usr/local/lib/hermes-agent/venv/bin/python3 /root/.hermes/profiles/wenyaozhitou/scripts/selfheal_3am.py
```

### 方案C：systemd service 设置 Environment

```ini
[Service]
Environment="PATH=/usr/local/lib/hermes-agent/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=python3 scripts/selfheal_3am.py
```

## 已修复的服务清单（2026-06-25）

| 服务 | 修复方式 |
|:--|:--|
| `wenyao-pipeline` | 方案A：`pipeline_master.sh` 加 `PY=...` + `python3` → `$PY` |
| `wenyao-dailyreport` | 方案A：`push_daily_report.sh` 加 `PY=...` + `python3` → `$PY` |
| `wenyao-selfheal` | 方案B：ExecStart 直接改为 venv Python |
| `wenyao-memory` | 方案B：同上 |

## 验证

```bash
# 1. 模拟 systemd 环境测试
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  /usr/local/lib/hermes-agent/venv/bin/python3 -c "import bs4; print('OK')"

# 2. 手动触发管道看是否有 ModuleNotFoundError
systemctl start wenyao-pipeline && journalctl -u wenyao-pipeline -f

# 3. 确认数据库有新数据
/usr/local/lib/hermes-agent/venv/bin/python3 -c "
import sqlite3
c = sqlite3.connect('/root/.hermes/profiles/wenyaozhitou/data/bidding.db')
print('招标:', c.execute('SELECT COUNT(*) FROM bidding_notices WHERE relevance_score>0').fetchone()[0])
print('中标:', c.execute('SELECT COUNT(*) FROM winning_notices WHERE relevance_score>0').fetchone()[0])
"
```
