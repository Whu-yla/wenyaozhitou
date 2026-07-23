# Chromium 通用爬虫索引页链接混入陷阱（V1.38）

## 症状

chromium_crawler.py 采集深圳能源，`extract_detail_links()` 提取 19 个链接全被 L1 拒绝：
```
🚫 L1拒绝: 变更公告 - 深圳能源电子招标投标平台 您好，欢迎来到...
🚫 L1拒绝: 招标公告 - 深圳能源电子招标投标平台 设为首页 | ...
本平台采集 0 条，L1拒绝 10 条
```

## 根因

`extract_detail_links()` 是通用爬虫 —— 把 Chromium 渲染后列表页所有 `<a href>` 当候选。深圳能源 zb.sec.com.cn 的列表页同时包含：
- **真实详情链接**：`/zbgg/20849.jhtml`、`/jggg/20840.jhtml`
- **导航/索引页链接**：`/zbggs/index.jhtml`、`/zbgg/index.jhtml`、`/jggg/index.jhtml`、`/zbggs/index_2.jhtml`

导航链接也匹配关键字 `zbgg/jggg` → 全被当成详情链接 → 实际是分类导航页 → 全页导航文本触发 L1 拒绝。

## 修复

在 `extract_detail_links()` 的 `links.add(full)` 前加索引页过滤：

```python
# 过滤导航/索引页（如 /zbggs/index.jhtml /zbgg/index.jhtml）
if re.search(r'/index(?:[_\u4e00-\u9fff])?(?:_?\d+)?\.\w+$', full):
    continue
```

## 伴生修复

### .Content div 提取
对于深圳能源等有 `.Content` 主内容区的平台，`fetch_detail_text()` 应优先提取纯净正文：

```python
content_div = soup.find('div', class_='Content')
if content_div:
    text = re.sub(r'\s+', ' ', content_div.get_text()).strip()
    return text, h1_title
```

### h1 标题优先
```python
h1_tag = soup.find('h1')
h1_title = h1_tag.get_text(strip=True)[:200] if h1_tag else ''
# 清理 CMS 模板占位符
title = re.sub(r'@\S+@', '', title).strip()
```

## 适用平台

任何通过 chromium_crawler.py 通用爬虫采集的、列表页和详情页共用 URL 路径前缀的平台都可能中招。典型症状：`extract_detail_links()` 找到 N 个链接但 100% 被 L1 拒绝。

## 验证

修复后验证（深圳能源）：
```
详情: 10
  [1] ⚪ [0分] 河源电厂...（纯硬件，评分正确为0）
  [2] ⚪ [0分] 妈湾电厂...（同上）
  [3] 🟡 [50分] 污染物自动监测监控系统数据传输升级改造
  [4] ⚪ [0分] 汽轮发电机本体检修
  [5] 🟡 [65分] 面向智能楼宇场景鸿蒙化应用关键技术研究与示范应用项目
```
- 0 条 L1 拒绝
- 标题干净无模板占位符
- 鸿蒙智能楼宇 65 分正确入库
