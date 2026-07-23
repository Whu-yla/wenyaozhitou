# Nginx 端口守护 + 邮件告警系统

## 部署时间
2026-06-26 — mkdocs 占 80 端口导致 nginx 停摆 8 分钟之后部署

## 组件

| 组件 | 路径 | 说明 |
|:--|:--|:--|
| 守护脚本 | `scripts/nginx_guardian.py` | Python urllib.request → 企微 Webhook 推送 |
| systemd service | `/etc/systemd/system/nginx-guardian.service` | Oneshot，每分钟触发 |
| systemd timer | `/etc/systemd/system/nginx-guardian.timer` | `OnCalendar=*:*:00` |

## 检测逻辑

```
每分钟执行:
  1. ss -tlnp sport :80 → 查谁占 80
  2. /proc/{pid}/comm → 判断是否 nginx
  3. 非 nginx → kill -9 + systemctl start nginx
  4. curl -sI yfzx.online/bidding/ → 验证 200
  5. 有异常 → HTTP POST 企微 Webhook Markdown 消息
```

## 告警通道：企业微信 Webhook

**SMTP 邮件尝试失败**（腾讯企业邮 535 认证失败，4 种端口/用户组合全堵，详见 `references/smtp-535-failure-wecom-fallback.md`）→ **改用企微 Webhook 推送。**

- **Webhook URL**: `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0256f02d-7368-4214-9c99-9c53ce449e92`
- **消息格式**: `msgtype=markdown`（支持标题/加粗/链接/emoji）
- **冷却**: 同一故障 30 分钟内不重复告警（`/tmp/nginx_guardian_state.json`）
- **验证**: `curl -X POST webhook_url -d '{"msgtype":"text","text":{"content":"test"}}'` → `errcode=0`

## 静默原则

一切正常时脚本无输出（exit 0），日志不写 journal。仅故障时通过企微 Webhook 发送 Markdown 告警。

## 部署命令

```bash
systemctl enable --now nginx-guardian.timer
systemctl status nginx-guardian.timer
```

## 手动测试

```bash
/usr/local/lib/hermes-agent/venv/bin/python3 scripts/nginx_guardian.py
# 正常 → exit 0，无输出
# 故障 → 打印告警 + 发送邮件
```

## 诊断方法：端口被谁占？

```bash
ss -tlnp | grep ':80 '
# 查看进程名
cat /proc/{PID}/comm
```

## 历史事件

- **2026-06-26 16:39**: `mkdocs serve -a 0.0.0.0:80` 占端口 → nginx 5 次重启失败 → 停摆 8 分钟
- **教训**: 任何长期运行的服务（mkdocs/dev server）禁止用 80/443 端口。用 `>1024` 端口 + nginx 反代。

## 快速修复命令

```bash
# 查谁占 80
ss -tlnp | grep ':80 '
# 杀进程
kill -9 $(ss -tlnp | grep ':80 ' | grep -oP 'pid=\K\d+')
# 起 nginx
systemctl start nginx
```
