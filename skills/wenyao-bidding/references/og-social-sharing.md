# OG 社交分享标签规范 (2026-06-26)

## 三页面必须覆盖

| 页面 | URL | og:title |
|:--|:--|:--|
| 主看板 | `/bidding/` | 文鳐智投 · 数智科技投标监控 |
| 操作手册 | `/bidding/manual.html` | 文鳐智投 · 操作手册 |
| 更新日志 | `/bidding/changelog.html` | 文鳐智投 · 更新日志 |

## 必需元标签（7条）

```html
<meta property="og:title" content="...">
<meta property="og:description" content="...">
<meta property="og:image" content="https://www.yfzx.online/bidding/img_gen/og-share.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="https://www.yfzx.online/bidding/...">
<meta property="og:type" content="website">
<meta property="og:site_name" content="文鳐智投">
```

## 封面图生成

`img_gen/og-share.png` (1200×630) 使用 Pillow 从真 Logo (`img/logo.png` 651×383) 生成：
- 背景：深蓝 `#0f172a`
- 顶部 4px 蓝色渐变 accent 线
- Logo 居中，等比缩放至 200px 宽
- 标题「文鳐智投」52px 白色粗体
- 副标题「中南电力设计院数智科技 · 投标监控系统」24px
- 底部署名「© 中南电力设计院数智科技 2026」16px

## 持久化

主看板的 OG 标签由 `polish_report.py` §4 注入（idempotent：检查 `og:title` 是否存在）。
manual.html 和 changelog.html 手动写入 `<head>`，不在定时任务管线内。

## 验证

```bash
curl -s https://www.yfzx.online/bidding/ | grep -c 'og:title'   # must be >= 1
curl -sI https://www.yfzx.online/bidding/img_gen/og-share.png | head -1  # 200 OK
```
