# chmod 644 * 目录权限陷阱

## 致命场景

```bash
# ❌ 这行命令会把目录也改成 644，抹掉执行权限
chmod 644 /var/www/html/bidding/*
```

`*` glob 匹配**所有东西**——文件 + 目录。目录被改 644（`drw-r--r--`）后：
- Linux 目录无 `x` 位 = 无法遍历（`opendir` 失败）
- Nginx `stat()` 返回 `Permission denied (13)`
- 浏览器看到 404，但文件实际存在
- `ls -l` 能看到文件列表（读权限还在），但 `cat` 不进目录

## 症状

```bash
$ curl -sI https://www.yfzx.online/bidding/img/logo.png
HTTP/1.1 404 Not Found

$ ls -la /var/www/html/bidding/img/logo.png
-rw-r--r-- 1 root root 16876 Jun 26 10:03 logo.png  # 文件存在！

$ ls -ld /var/www/html/bidding/img/
drw-r--r-- 2 root root 4096 Jun 23 23:03 img/  # 目录无 x！
```

Nginx error log：
```
stat() "/var/www/html/bidding/img/logo.png" failed (13: Permission denied)
```

## 正确做法

```bash
# 只 chmod 文件，不碰目录
find /var/www/html/bidding -type f \
  \( -name '*.html' -o -name '*.js' -o -name '*.css' -o -name '*.json' -o -name '*.png' -o -name '*.ico' \) \
  -exec chmod 644 {} +

# 目录单独保证 755
chmod 755 /var/www/html/bidding/img /var/www/html/bidding/img_gen
```

## polish_report.py v6 内置修复

```python
# 写完 index.html 后安全设置权限
for f in Path("/var/www/html/bidding").glob("*"):
    if f.is_file():
        f.chmod(0o644)
for d in ["/var/www/html/bidding/img", "/var/www/html/bidding/img_gen"]:
    subprocess.run(["chmod", "755", d])
```

## 验证

```bash
ls -ld /var/www/html/bidding/img/     # 必须是 drwxr-xr-x
ls -ld /var/www/html/bidding/img_gen/ # 必须是 drwxr-xr-x
curl -sI https://www.yfzx.online/bidding/img/logo.png | head -1  # HTTP/1.1 200 OK
```
