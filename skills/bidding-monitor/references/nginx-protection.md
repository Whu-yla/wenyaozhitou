# Nginx 三级防护体系 (2026-06-24)

## 配置文件：`/etc/nginx/sites-enabled/wiki`

```
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=static:10m rate=8r/s;
limit_conn_zone $binary_remote_addr zone=connlimit:10m;
```

### 第一级：频率限制
- `/bidding/` 页面：`limit_req zone=static burst=12 nodelay`（8r/s）
- 全局：`limit_req zone=general burst=20 nodelay`（10r/s）
- 连接数：`limit_conn connlimit 20`（每IP最大20并发）

### 第二级：安全响应头
每个 `location` 块必须显式声明（`add_header` 子块覆盖父块）：
```nginx
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
```

### 第三级：端口守护 + 企微告警（2026-06-26 升级）
- 脚本：`scripts/nginx_guardian.py` — Python urllib.request → 企微 Webhook Markdown 推送
- 方式：systemd timer `nginx-guardian.timer`，每分钟触发（`OnCalendar=*:*:00`）
- 检测：80端口归属 → nginx 服务状态 → HTTP 200 可达性
- 自愈：杀侵占进程 → `systemctl start nginx`
- 告警：企微 Webhook（SMTP 邮件 535 认证失败，已弃用）
- 冷却：同一故障 30 分钟不重复告警
- 详见 `wenyao-bidding/references/nginx-guardian-system.md`

### ⚠️ 致命坑

1. **`add_header` 子块全覆盖父块**：server 层的 `add_header` 会被 location 层的 `add_header` 完全替换。必须在每个 location 显式声明所有安全头
2. **`alias` + `try_files` 在 regex location 中不兼容**：`try_files $uri` 在 alias 下路径不对 → 404。单 `location /bidding/` prefix 方案最稳
3. **HTML 缓存已全局禁用**：`Cache-Control: no-cache, no-store, must-revalidate`。文件很小不需要缓存，更新立即可见
