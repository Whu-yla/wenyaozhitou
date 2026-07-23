# Logo 图标生成工作流

## 源文件
用户提供的 Logo 图片（任意格式：JPG/PNG）。存放位置：`/var/www/html/bidding/img/logo.png`

## 生成目标（5 个文件）

| 文件 | 尺寸 | 用途 |
|:--|:--|:--|
| `img/logo.png` | 200px 高（等比缩放） | 页面 Header 左上角 |
| `favicon-32x32.png` | 32×32 | 浏览器标签页图标 |
| `favicon.ico` | 32×32 | Windows/旧浏览器兼容 |
| `apple-touch-icon.png` | 180×180 | iOS 主屏幕 / Safari |
| `img_gen/og-share.png` | 1200×630 | 微信/飞书/社交分享封面 |

## Python 生成脚本

```python
from PIL import Image

src = Image.open('user_logo.jpg').convert('RGBA')

# 1. Header logo — max 200px height
h = 200
w = int(src.width * h / src.height)
logo = src.resize((w, h), Image.LANCZOS)
logo.save('img/logo.png', 'PNG')

# 2. Square crop from center-top for favicons
min_dim = min(src.width, src.height)
left = (src.width - min_dim) // 2
square = src.crop((left, 0, left + min_dim, min_dim))

# 3. favicon-32x32
fav32 = square.resize((32, 32), Image.LANCZOS)
fav32.save('favicon-32x32.png', 'PNG')

# 4. favicon.ico
fav32.save('favicon.ico', 'ICO', sizes=[(32, 32)])

# 5. apple-touch-icon 180×180 (with padding)
apple = Image.new('RGBA', (180, 180), (255, 255, 255, 0))
sq_big = square.resize((140, 140), Image.LANCZOS)
apple.paste(sq_big, (20, 20), sq_big)
apple.save('apple-touch-icon.png', 'PNG')

# 6. OG share 1200×630 (dark bg + centered logo)
og = Image.new('RGBA', (1200, 630), (15, 23, 42, 255))
h_og = 400
w_og = int(src.width * h_og / src.height)
logo_og = src.resize((w_og, h_og), Image.LANCZOS)
x, y = (1200 - w_og) // 2, (630 - h_og) // 2
og.paste(logo_og, (x, y), logo_og if logo_og.mode == 'RGBA' else None)
og.save('img_gen/og-share.png', 'PNG')
```

## ⛔ 权限修复（致命坑）

生成后必须设权限，否则 nginx 403：
```bash
chmod 755 /var/www/html/bidding/img /var/www/html/bidding/img_gen
chmod 644 /var/www/html/bidding/img/logo.png /var/www/html/bidding/favicon-32x32.png /var/www/html/bidding/favicon.ico /var/www/html/bidding/apple-touch-icon.png /var/www/html/bidding/img_gen/og-share.png
```

**根因**：Python `PIL.save()` 创建的文件默认权限由 umask 决定，可能缺少 nginx（www-data）需要的读权限。`img/` 和 `img_gen/` 目录必须有执行位（x）nginx 才能遍历。

## 三个页面一致性

| 页面 | Header Logo | Favicon | Apple | OG | Title |
|:--|:--|:--|:--|:--|:--|
| index.html | `/img/logo.png` | 3 link tags | ✅ | ✅ | 文鳐智投 · 数智科技投标监控 |
| changelog.html | `/img/logo.png` | 3 link tags | ✅ | ✅ | 文鳐智投 · 更新日志 — 数智科技投标监控 |
| manual.html | `/img/logo.png` | 3 link tags | ✅ | ✅ | 文鳐智投 · 操作手册 — 数智科技投标监控 |

**致命坑**：操作手册曾用 `/favicon-32x32.png` 做 Header Logo（32px 太小），必须用 `/img/logo.png`。

## HTML 引用
```html
<link rel="icon" type="image/png" sizes="32x32" href="/bidding/favicon-32x32.png">
<link rel="icon" type="image/x-icon" href="/bidding/favicon.ico">
<link rel="apple-touch-icon" sizes="180x180" href="/bidding/apple-touch-icon.png">
```

## polish_report.py 持久化
```python
if 'favicon-32x32.png' not in html:
    favicon_html = '<link rel="icon" type="image/png" sizes="32x32" href="/bidding/favicon-32x32.png">\n<link rel="icon" type="image/x-icon" href="/bidding/favicon.ico">\n<link rel="apple-touch-icon" sizes="180x180" href="/bidding/apple-touch-icon.png">\n'
    html = html.replace('<title>', favicon_html + '<title>')
```
