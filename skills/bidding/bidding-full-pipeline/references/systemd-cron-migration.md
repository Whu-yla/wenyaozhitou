# Systemd 定时任务迁移指南（替代 Hermes Cron 长任务）

## 问题根因

Hermes Cron 对所有任务（包括 `no_agent=true`）有 **3 分钟硬中断**。管线需要 10-20 分钟，每次在第 3 分钟被 kill，状态显示 `error`。这是 Hermes scheduler 层限制，无法通过配置绕过。

## 当前定时器全景（2026-07-01 精简）

| 定时器 | 时间 | 用途 | TimeoutStopSec |
|:--|:--|:--|:--|
| `wenyao-pipeline.timer` | 每天 08:00 | 全管线(采集→评分→竞品→报告→**推送**) | 7200 |
| `wenyao-selfheal.timer` | 每天 03:00 | 凌晨自检+反馈修复 | 600 |
| `wenyao-memory.timer` | 每天 09:00 | 记忆维护 | 300 |

> ⚠️ 2026-07-01 删除：`wenyao-push.timer`（8:30独立推送）和 `wenyao-dailyreport.timer`（20:00日报）——推送已内嵌在管线阶段5。

## 管线采集（每天 8:00）

**`/etc/systemd/system/wenyao-pipeline.service`**
```ini
[Unit]
Description=文鳐智投 全流程采集管线
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/root/.hermes/profiles/wenyaozhitou
ExecStart=/bin/bash /root/.hermes/profiles/wenyaozhitou/scripts/pipeline_master.sh
StandardOutput=journal
StandardError=journal
TimeoutStopSec=7200
User=root

Restart=on-failure
RestartSec=60
RestartMax=1
```

**`/etc/systemd/system/wenyao-pipeline.timer`**
```ini
[Unit]
Description=文鳐智投 定时采集（每天8:00）

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true
RandomizedDelaySec=60

[Install]
WantedBy=timers.target
```

## 凌晨自检（每天 03:00）

**服务**：`wenyao-selfheal.service`（`TimeoutStopSec=600`）
**定时器**：`wenyao-selfheal.timer`（`OnCalendar=*-*-* 03:00:00`）

## 记忆维护（每天 09:00）

**服务**：`wenyao-memory.service`（`TimeoutStopSec=300`）
**定时器**：`wenyao-memory.timer`（`OnCalendar=*-*-* 09:00:00`）

## 部署命令

```bash
sudo cp /tmp/wenyao-*.service /etc/systemd/system/
sudo cp /tmp/wenyao-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wenyao-pipeline.timer wenyao-selfheal.timer wenyao-memory.timer
sudo systemctl start wenyao-pipeline.timer wenyao-selfheal.timer wenyao-memory.timer
```

## 查看状态

```bash
systemctl list-timers 'wenyao-*' --no-pager
systemctl status wenyao-pipeline.service
journalctl -u wenyao-pipeline.service -f
```

## ⛔ 不要为推送建独立定时器

推送是管线阶段5，**必须在采集→评分→竞品→报告之后执行**。独立推送定时器会导致：
- 时序混乱（管线没跑完推送先触发 → 推空/推旧数据）
- 重复推送（管线推送 + 独立推送 → 群消息爆炸）
- 维护负担（多一个定时器多一个故障点）

## Hermes Cron 保留项

仅保留秒级/分钟级 watchdog 型脚本：
- `nginx_guard.sh`（每1分钟）— nginx + bookmark_server 守护
