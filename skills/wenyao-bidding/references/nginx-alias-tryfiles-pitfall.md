# Nginx alias + try_files $uri 陷阱

## 症状
- 文件明确存在（`/var/www/html/bidding/img/logo.png`），权限正确
- 但 nginx 返回 404
- 安全头正常出现（说明 location 匹配到了）

## 根因
`alias` + `try_files $uri` 组合不能正常工作。

```nginx
# ❌ 错误
location /bidding/ {
    alias /var/www/html/bidding/;
    try_files $uri $uri/ =404;  # $uri 仍是 /bidding/img/logo.png
}
# nginx 实际查找: /var/www/html/bidding//bidding/img/logo.png (双斜杠)

# ❌ 更差 —— 单独 location 也不行
location /bidding/img/ {
    alias /var/www/html/bidding/img/;
    try_files $uri =404;  # $uri 仍是 /bidding/img/logo.png
}
# alias 改根但 try_files 仍用请求 URI
```

## 修复
**方案1（推荐）**：`alias` → `root`

```nginx
# ✅ 正确
location /bidding/ {
    root /var/www/html;           # 不是 alias!
    try_files $uri $uri/ =404;    # $uri = /bidding/img/logo.png
}                                 # root + $uri = /var/www/html/bidding/img/logo.png ✓
```

**方案2**：不用 `try_files` 用 `$request_filename`

```nginx
location /bidding/img/ {
    alias /var/www/html/bidding/img/;
    try_files $request_filename =404;  # 用 $request_filename 而非 $uri
}
```

## 关联问题：目录缺少执行位
nginx 用户（`www-data`）需要目录有 `x` 执行位才能遍历读取文件。

```bash
# 检查
namei -l /var/www/html/bidding/img/logo.png
sudo -u www-data cat /var/www/html/bidding/img/logo.png

# ❌ drw-r--r-- (644) — 缺 x
# ✅ drwxr-xr-x (755)

# 修复
chmod 755 /var/www/html/bidding/img/
```

## 验证
```bash
curl -sI https://www.yfzx.online/bidding/img/logo.png | head -3
# 预期: HTTP/1.1 200 OK
```
