# Chromium 通用爬虫陷阱

`chromium_crawler.py` 负责 Chromium headless 批量渲染 JS 平台列表页 → 提取详情链接 → requests 抓取正文。以下为其反复出现的陷阱及修复模式。

## 陷阱 1: 导航/索引页链接被当成详情

**场景**：平台列表页（如 `zb.sec.com.cn/zbggs/index.jhtml`）经 Chromium 渲染后，`extract_detail_links()` 同时提取到：
- 真实详情：`/zbgg/20849.jhtml`
- 导航链接：`/zbggs/index.jhtml`、`/zbgg/index.jhtml`、`/jggg/index.jhtml`

两者都命中 `zbgg`/`jggg` 关键词。导航链接优先填满 10 槽位 → L1 全部拒绝。

**修复**：在 `extract_detail_links()` 中追加：
```python
if re.search(r'/index(?:[_\u4e00-\u9fff])?(?:_?\d+)?\.\w+$', full):
    continue
```

**已知命中平台**：深圳能源 zb.sec.com.cn

## 陷阱 2: 门户导航文本污染详情正文

**场景**：`fetch_detail_text()` 全页 soup.get_text() 后，门户导航栏文本（「欢迎来到XX平台」「设为首页」「收藏此页」）混入正文 → L1 `is_valid_notice_page()` 噪声计数 ≥3 → 拒绝。

**修复**：优先提取 `<div class="Content">` 主内容区：
```python
content_div = soup.find('div', class_='Content')
if content_div:
    text = re.sub(r'\s+', ' ', content_div.get_text()).strip()
```

**已知命中平台**：深圳能源 zb.sec.com.cn（.Content div）

## 陷阱 3: 标题提取走正文首行 → CMS 模板占位符

**场景**：`.Content` div 首行含 CMS 模板标记 `@项目公告信息.项目名称@` → 标题变成「@项目公告信息.项目名称@招标公告 面向智能…」

**修复**：
1. 优先 `<h1>` 标签提取标题（`h1_tag.get_text(strip=True)`）
2. `title = re.sub(r'@\S+@', '', title).strip()` 清理残留

**已知命中平台**：深圳能源 zb.sec.com.cn

## 已知平台的 Content 提取模式

| 平台 | 正文区选择器 | 标题选择器 | 备注 |
|:--|:--|:--|:--|
| 深圳能源 zb.sec.com.cn | `div.Content` | `h1` | 需清理 `@\S+@` 模板占位符 |
| 国家能源集团 | 全页 soup | 首行 | Chromium dump-dom，无特殊 div |

## 通用检查清单

编写新 Chromium 适配器时逐项检查：
- [ ] `extract_detail_links` 是否过滤了 `/index*\.\w+$` 导航链接？
- [ ] `fetch_detail_text` 是否优先提取了 `.Content` / 主内容 div？
- [ ] 标题是否用了 `<h1>` 而非正文首行？
- [ ] 是否清理了 `@\S+@` / `【】` / `{{}}` 等模板占位符？
