# Nginx 配置操作 SOP（2026-06-25 + 2026-06-26 教训）

## 致命错误复盘

### 2026-06-25：配置覆盖导致全站 404
1. 想加 `gzip_static on` 和 data.json 单独缓存 → 误用 sed 破坏配置
2. 尝试 `cp /etc/nginx/sites-available/wiki /etc/nginx/sites-enabled/wiki` 恢复
3. `sites-available/wiki` 只有 Wiki proxy，不含 bidding location
4. 结果：全站 `/bidding/*` → 404，Nginx guard 报警 HTTP 301

### 2026-06-26：alias + try_files $uri 导致静态资源 404
1. `location /bidding/ { alias /var/www/html/bidding/; try_files $uri =404; }`
2. 请求 `/bidding/img/logo.png` → `$uri` = `/bidding/img/logo.png`
3. nginx 拼接：`/var/www/html/bidding/` + `/bidding/img/logo.png` = ❌ 双路径错误
4. **`alias` 不剥离 location 前缀，`try_files $uri` 用原始 URI → 路径重复**

### 2026-06-26：目录缺少执行权限 (x bit)
1. `img/` 目录权限 `drw-r--r--`(644) — **缺执行位**
2. nginx (www-data) 无法 traverse 目录 → 404
3. 文件本身 755 没用 — 父目录也必须 755

## 安全操作流程

### 修改前
```bash
# ✅ 从 enabled 往 available 备份
sudo cp /etc/nginx/sites-enabled/wiki /etc/nginx/sites-available/wiki
```

### 修改后
```bash
# ✅ 语法检查
sudo nginx -t

# ✅ 验证所有端点
curl -sI https://yfzx.online/bidding/ | grep HTTP
curl -sI https://yfzx.online/bidding/img/logo.png | grep HTTP
curl -sI https://yfzx.online/bidding/data.json | grep HTTP
curl -sI https://yfzx.online/bidding/api/ | grep HTTP

# ✅ reload
sudo systemctl reload nginx
```

## 常见 Nginx 坑

### `alias` + `try_files $uri` — 必用 `root` 替代
```nginx
# ❌ 错误：alias 不剥离前缀，$uri 仍含 /bidding/
location /bidding/ {
    alias /var/www/html/bidding/;
    try_files $uri $uri/ =404;  # 路径拼接错误
}

# ✅ 正确：用 root，nginx 自动拼接 document_root + $uri
location /bidding/ {
    root /var/www/html;               # 注意：不包含 /bidding
    index index.html;
    try_files $uri $uri/ =404;        # $uri = /bidding/xxx → root + $uri = /var/www/html/bidding/xxx ✓
}
```

**规则**：能用 `root` 就不用 `alias`。`alias` 只在需要映射到不同路径名时才用（如 `/static/` → `/opt/assets/`），且 try_files 必须用 `$request_filename` 而非 `$uri`。

### 目录执行权限 (x bit) 导致 404
```bash
# ❌ 644 目录 — nginx 无法进入
drw-r--r-- root root img/

# ✅ 755 目录 — nginx 可以遍历
drwxr-xr-x root root img/

# 修复
chmod 755 /var/www/html/bidding/{img,img_gen,data}
```

**铁律**：`/var/www/html/bidding/` 下所有子目录必须是 755。每次创建新目录后：
```python
os.chmod(path, 0o755)
# 或
subprocess.run(['chmod', '755', path])
```

### limit_req zone 未定义
```
limit_req zone=static burst=12 nodelay;  # ❌ zone "static" 不存在
```
必须先定义：
```nginx
http {
    limit_req_zone $binary_remote_addr zone=static:10m rate=8r/s;
}
```

### location 不可嵌套
```nginx
location /bidding/ {
    location = /bidding/data.json { ... }  # ❌ 语法错误
}
```
替代：在 `location /bidding/` 块外定义 `location = /bidding/data.json`

### add_header 覆盖
子块 `add_header` 覆盖父块，安全头需在每个 location 内显式声明。

## 当前完整配置
`/etc/nginx/sites-enabled/wiki`:
- `location /bidding/` — `root /var/www/html` + try_files + 安全头 + no-cache
- `location /bidding/api/` — proxy_pass 127.0.0.1:8090
- `location /` — proxy_pass 127.0.0.1:8080 (Wiki)
- **注意**：不再有独立的 `/bidding/img/` location，统一由 `/bidding/` 处理
