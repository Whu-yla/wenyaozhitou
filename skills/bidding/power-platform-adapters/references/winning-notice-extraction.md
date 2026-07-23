# 中标公告详情提取 — HTML表格解析模式

## 问题场景
南网/浙能等平台中标公告用 HTML `<table>` 展示中标结果。纯文本正则 `中标人[：:]` 匹配不到表格中的值。

## BS4 表格列定位提取

```python
from bs4 import BeautifulSoup

def extract_winner_from_table(html):
    soup = BeautifulSoup(html, 'html.parser')
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        # 1. 从表头行定位列索引
        col_idx = -1
        for row in rows:
            cells = row.find_all(['td', 'th'])
            for i, cell in enumerate(cells):
                ct = cell.get_text(strip=True)
                if any(kw in ct for kw in ['中标人','成交人','成交供应商','中标单位','供应商名称']):
                    col_idx = i
                    break
            if col_idx >= 0:
                break
        # 2. 从数据行提取值
        if col_idx >= 0:
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) > col_idx:
                    val = cells[col_idx].get_text(strip=True)
                    if val and '中标人' not in val and '序号' not in val and len(val) >= 2:
                        return val[:80]
    return ''
```

## 表头关键词变体（南网真实案例）

| 关键词 | 出现场景 | 案例 |
|:--|:--|:--|
| `中标人` | 公开招标中标公告 | 深圳供电局生产监控系统 |
| `成交人` | 询比/谈判采购 | 海南文体馆维修项目 |
| `成交供应商` | 框架采购 | — |
| `中标单位` | 工程类 | — |

⚠️ **铁律**：关键词列表必须覆盖全部变体。今天只搜"中标人"漏掉"成交人"，导致 id=70 提取失败。

## 金额提取困境

- **南网**：中标金额不在公开 HTML 中，需登录或下载 PDF 附件
- **国家能源**：详情链接有时效性，必须抓取时即时提取，不能依赖事后回填
- 纯文本兜底：`r'(?:中标金额|成交金额|金额)[：:]\s*([\d,.]+)\s*(?:万|元)'`

## 实现位置
`dedicated_adapters.py` → `crawl_nanwang()` → detail page parsing（第150-210行）
