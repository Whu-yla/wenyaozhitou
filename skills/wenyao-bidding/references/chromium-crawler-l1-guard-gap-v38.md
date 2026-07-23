# V1.38 chromium_crawler.py 索引页过滤 + .Content正文提取

## 问题

`chromium_crawler.py` 的 `extract_detail_links()` 把列表页的所有 `<a>` 链接（包括导航链接如 `/zbggs/index.jhtml`、`/jggg/index.jhtml`）当成了详情链接。深圳能源 10/10 被 L1 拒绝——全是「欢迎来到深圳能源电子招标投标平台」导航页。

## 根因

1. `extract_detail_links()` 只按 href+text 关键词匹配（`zbgg/jggg/cggg` 等），不区分索引页和详情页
2. `fetch_detail_text()` 用全页 soup 提取文本，门户导航（设为首页/收藏此页/联系我们）混入正文 → L1 假阳性

## 修复（chromium_crawler.py）

### 1. extract_detail_links() — 过滤索引/导航页

```python
# 过滤导航/索引页（如 /zbggs/index.jhtml /zbgg/index.jhtml）
if re.search(r'/index(?:[_\u4e00-\u9fff])?(?:_?\d+)?\.\w+$', full):
    continue
```

### 2. fetch_detail_text() — 返回 (text, h1_title) 元组

```python
def fetch_detail_text(url):
    """返回 (text, h1_title)"""
    # ...解析 HTML...
    h1_tag = soup.find('h1')
    h1_title = h1_tag.get_text(strip=True)[:200] if h1_tag else ''
    
    # 优先 .Content 主内容区
    content_div = soup.find('div', class_='Content')
    if content_div:
        text = re.sub(r'\s+', ' ', content_div.get_text()).strip()
        return (text[:3000] if len(text) > 80 else None), h1_title
    # 兜底全文...
    return text, h1_title
```

### 3. main() 标题提取 — h1 优先，清理模板占位符

```python
text, h1_title = fetch_detail_text(dl)
title = h1_title if h1_title else ''
# ...fallback...
title = re.sub(r'@\S+@', '', title).strip()  # 清理 @项目公告信息.项目名称@
```

## 验证

深圳能源修复后：10/10 真详情链接 → 鸿蒙智能楼宇 65 分入库（修复前 0/10）。
