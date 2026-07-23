# Systemd定时迁移 — 3分钟硬中断解决方案

## 问题

Hermes Cron 调度器有 **3 分钟硬中断**（`cron/jobs.py` 的 `.tick.lock`），无论 `no_agent` 还是 Agent 模式，只要脚本执行超过 3 分钟就被无情 kill。文鳐智投标管线跑 1-2 小时，每次都被砍死，表现为 `last_status: error`。

## 解决方案

迁移长任务到 **systemd timer**（无超时限制，可设 7200 秒 TimeoutStopSec）。

## systemd 服务文件

### `/etc/systemd/system/wenyao-pipeline.service`
```ini
[Unit]
Description=文鳐智投 全流程采集管线
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/root/.hermes/profiles/wenyaozhitou
ExecStart=/bin/bash /root/.hermes/profiles/wenyaozhitou/scripts/pipeline_master.sh
TimeoutStopSec=7200
User=root
Restart=on-failure
RestartSec=60
```

### `/etc/systemd/system/wenyao-pipeline.timer`
```ini
[Unit]
Description=文鳐智投 定时采集（每天9:00 + 18:00）

[Timer]
OnCalendar=*-*-* 09:00:00
OnCalendar=*-*-* 18:00:00
Persistent=true
RandomizedDelaySec=120

[Install]
WantedBy=timers.target
```

### 日报服务
`wenyao-dailyreport.service`（TimeoutStopSec=600）+ `wenyao-dailyreport.timer`（20:00）

## 部署命令
```bash
sudo cp /tmp/wenyao-pipeline.service /etc/systemd/system/
sudo cp /tmp/wenyao-pipeline.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wenyao-pipeline.timer
sudo systemctl enable --now wenyao-dailyreport.timer
```

## Hermes Cron 保留项

仅保留短任务（<3分钟）：
- `f5a928bf619e`：Nginx 守护（每1分钟，no_agent）
- `eba2fa280224`：记忆维护（每天9:00）

已删除的旧 job：
- `46346e624040`（早间管线）
- `b2373b8d777d`（晚间管线）
- `04bf3bdc6aa6`（日报）
