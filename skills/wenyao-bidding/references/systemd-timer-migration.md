# Systemd Timer 替代 Hermes Cron — 迁移指南

> 🔴 Hermes Cron 有 3 分钟硬中断，任何 job（含 no_agent）超3分钟必被 kill。
> 所有需长时运行的定时任务必须用 systemd timer。

## 模板

### Service 文件 (`/etc/systemd/system/wenyao-<name>.service`)
```ini
[Unit]
Description=文鳐智投 <描述>
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/root/.hermes/profiles/wenyaozhitou
ExecStart=/bin/bash /root/.hermes/profiles/wenyaozhitou/scripts/<script>.sh
StandardOutput=journal
StandardError=journal
TimeoutStopSec=<秒>   # 根据任务预估时间 ×2 设置
User=root
```

### Timer 文件 (`/etc/systemd/system/wenyao-<name>.timer`)
```ini
[Unit]
Description=文鳐智投 <描述>

[Timer]
OnCalendar=*-*-* HH:MM:00   # 每天固定时间
Persistent=true              # 错过后补跑
RandomizedDelaySec=120       # 分散负载

[Install]
WantedBy=timers.target
```

## 当前已部署

| Timer | 时间 | 超时 | 用途 |
|:--|:--|:--|:--|
| `wenyao-pipeline` | 9:00+18:00 | 7200s | 全流程采集 |
| `wenyao-dailyreport` | 20:00 | 600s | 日报生成 |
| `wenyao-selfheal` | 3:00 | 600s | 自检修复 |
| `wenyao-memory` | 9:00 | 300s | 记忆维护 |

## 命令

```bash
# 部署
sudo cp /tmp/xxx.service /etc/systemd/system/
sudo cp /tmp/xxx.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable xxx.timer
sudo systemctl start xxx.timer

# 查看
systemctl list-timers 'wenyao-*'
sudo journalctl -u wenyao-pipeline.service --since "1 hour ago" -n 20

# 手动触发
sudo systemctl start wenyao-pipeline.service
```

## 迁移时务必做的事
1. 创建 service + timer → deploy
2. `hermes cron remove <id>` 删除旧 Hermes cron
3. 验证 `systemctl list-timers` 有两个触发时间（如 9:00 + 18:00 需配两个 OnCalendar 行）
4. 手动 `systemctl start` 测试一次
