# Nginx 缓存导致更新不可见

## 根因

Nginx `Cache-Control: max-age=300` 让浏览器（尤其飞书/微信内置浏览器）缓存 HTML 5 分钟。
用户反复说"看不到更新"，因为浏览器拿着旧版不松手。

## 修复

```
add_header Cache-Control "no-cache, no-store, must-revalidate";
add_header Pragma "no-cache";
add_header Expires "0";
```

## 关键认知

- `/bidding/` 下文件都很小（最大 data.json 240KB），**不需要缓存性能优化**
- **更新立即可见**才是核心需求
- 用户说过「访问不了了」很多次，根因都是缓存

## 排坑记录

| 症状 | 根因 | 修复 |
|:--|:--|:--|
| 用户说 changelog 看不到 V1.2 | Cache-Control: max-age=300 | 改为 no-cache |
| 用户说封面图 404 | img_gen 目录权限 754 (缺x) | chmod 755 |
| 用户说报告标题不是链接 | app.js 渲染为纯文本 | 改为 `<a>` 超链接 |
