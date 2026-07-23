# V1.0 稳定版 — 生产/测试双环境架构

> 建立于 2026-06-26 11:49 CST。用户明确要求：当前版本冻结为 V1.0 稳定版，以后改动先走测试环境。

## 环境清单

| 环境 | URL | 文件路径 | 用途 |
|:-----|:-----|:-----|:-----|
| 🟢 生产 | `https://www.yfzx.online/bidding/` | `/var/www/html/bidding/` | 面向用户，不动就是不动 |
| 🟡 测试 | `https://www.yfzx.online/bidding-test/` | `/var/www/html/bidding-test/` | 所有改动先部署到这里 |
| 💾 快照 | — | `/var/www/html/bidding/v1.0-stable/` | 完整备份，可随时恢复 |

## 测试环境特征

- **橙色横幅**：页面顶部固定 `⚠️ 测试环境 — 改动不会影响生产`（橙底黑字，z-index:9999）
- **独立文件**：完全独立的 index.html / app.js / chat-widget.css / chat-widget.js / data.json
- **独立 API**：`/bidding-test/api/` → 同端口 8090（`bookmark_server.py`）
- **独立静态资源**：img/logo.png、img_gen/covers/ 等均为独立副本

## 部署铁律

```
改动 → 测试环境 → 验证 → promote.sh → 生产环境
```

**永不直接改生产文件。**

## promote.sh 一键发布

```bash
bash /root/.hermes/profiles/wenyaozhitou/skills/wenyao-bidding/scripts/promote.sh
```

该脚本：
1. 检查测试和生产差异
2. 列出将要同步的文件
3. 要求确认（`read -p`）
4. 同步 index.html / app.js / chat-widget.* / changelog.html / manual.html
5. 自动 chmod 644 所有文件 + chmod 755 目录
6. 更新 VERSION.txt
7. 写入 changelog 条目

## Nginx 配置

测试环境 location 已在 `/etc/nginx/sites-enabled/wiki`：
```
location /bidding-test/ {
    root /var/www/html;
    index index.html;
    try_files $uri $uri/ =404;
    # 安全头同上...
}
location /bidding-test/api/ {
    proxy_pass http://127.0.0.1:8090/;
    # ...
}
```

## 恢复流程

如果生产环境被意外破坏：
```bash
# 从 V1.0 快照恢复
cp /var/www/html/bidding/v1.0-stable/index.html /var/www/html/bidding/
cp /var/www/html/bidding/v1.0-stable/app.js /var/www/html/bidding/
cp /var/www/html/bidding/v1.0-stable/chat-widget.* /var/www/html/bidding/
cp /var/www/html/bidding/v1.0-stable/changelog.html /var/www/html/bidding/
chmod 644 /var/www/html/bidding/*.html /var/www/html/bidding/*.js /var/www/html/bidding/*.css
chmod 755 /var/www/html/bidding/img /var/www/html/bidding/img_gen /var/www/html/bidding/data
```

## 注意事项

- report_generator.py 只生成 data.json，不覆盖 index.html（V1.35）
- polish_report.py 是唯一维护 HTML 样式的脚本
- data.json 是共享的（测试环境可通过 symlink 指向生产或独立生成）
- 企微推送只从生产环境 data.json 读取
