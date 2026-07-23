# 中标数据提取修复手册 (2026-06-26)

## 问题
8 条中标数据，仅 3 条有中标人，0 条有金额。南网和国家能源两个来源。

## 根因分析

### 南网 (dedicated_adapters.py crawl_nanwang)
- 详情页用 HTML `<table>` 展示中标结果，非纯文本
- 表头关键词变体：`中标人` / `成交人` / `成交供应商`
- 旧代码用纯文本正则 `r'中标人[：:]\s*(.+?)\n'` 匹配，在 HTML 文本化后的格式中完全失效
- 中标金额在南网公开 HTML 中**不显示**（需登录或 PDF 附件），这是平台特性

### 国家能源 (adapter_guoneng.py)
- `_extract_from_table()` 函数逻辑正确，但详情链接有时效性
- 链接过期后返回 404，无法回填
- **预防**：必须确保抓取时立即提取，不能依赖事后回填

## 修复方案

### BS4 表格提取函数（已加入 dedicated_adapters.py）

```python
soup = BeautifulSoup(detail_html, 'html.parser')
for table in soup.find_all('table'):
    # 1. 从表头行找列索引
    col_winner = -1
    col_amount = -1
    for row in table.find_all('tr'):
        cells = row.find_all(['td', 'th'])
        for i, cell in enumerate(cells):
            ct = cell.get_text(strip=True)
            if any(kw in ct for kw in ['中标人','成交人','成交供应商','中标单位','供应商名称']):
                col_winner = i
            if any(kw in ct for kw in ['中标金额','成交金额','投标报价','报价']):
                col_amount = i
    # 2. 从数据行提取值（跳过表头行）
    if col_winner >= 0:
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) > col_winner:
                val = cells[col_winner].get_text(strip=True)
                if val and keyword not in val and '序号' not in val and len(val) >= 2:
                    winner = val[:80]
```

### 关键词覆盖清单
中标人列可能的表头文本：
- `中标人` — 标准格式
- `成交人` — 询比/谈判采购格式（id=70 案例：文体馆维修）
- `成交供应商` — 采购类
- `中标单位` — 工程施工类
- `供应商名称` — 通用

### 金额困境
- **南网**：金额不在公开 HTML 中（平台设计），目前无法提取
- **国家能源**：链接有时效性，需在抓取时即时提取
- **浙能**：可能存在表格金额，待验证
- **远期方案**：考虑接入招标数据 API 付费服务补充金额

## 回填流程

```bash
# 1. 修复适配器（dedicated_adapters.py）
# 2. 逐条回填已有数据
cd /root/.hermes/profiles/wenyaozhitou
/usr/local/lib/hermes-agent/venv/bin/python3 << 'PYEOF'
import requests, sqlite3
from bs4 import BeautifulSoup

conn = sqlite3.connect('data/bidding.db')
for row in conn.execute("SELECT id,url FROM winning_notices WHERE winner_company IS NULL OR winner_company=''"):
    resp = requests.get(row[1], timeout=15)
    winner = extract_from_table(resp.text)  # 使用上面的函数
    if winner:
        conn.execute('UPDATE winning_notices SET winner_company=? WHERE id=?', (winner, row[0]))
conn.commit()
PYEOF

# 3. 重生成报告
/usr/local/lib/hermes-agent/venv/bin/python3 scripts/report_generator.py
/usr/local/lib/hermes-agent/venv/bin/python3 scripts/polish_report.py
```

## 结果
回填完成：8 条中标 → 7 条有中标人。金额 0（南网平台限制）。
