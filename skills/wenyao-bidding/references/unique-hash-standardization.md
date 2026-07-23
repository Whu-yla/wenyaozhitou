# unique_hash 标准化（2026-06-25 修复）

## 问题
6 个爬虫使用不同的字段组合计算 `unique_hash`：
- `crawl_pipeline.py`：`md5(title|url|source_site)`
- `batch_crawler.py`：`md5(title|source_url|source)`
- `chromium_crawler.py`：`md5(title|source_url)`
- `dedicated_adapters.py`：`md5(title|source_url)`
- `adapter_zheneng.py`：`md5(title|source_url)`
- `adapter_supplement.py`：`md5(title|source_url)`

同一URL被不同爬虫抓取时，标题截断不同 / source_site 字段名不同 → 不同 hash → `INSERT OR IGNORE` 失效 → **同URL出现2条**。

## 修复
**全部统一为 URL-only hash**：

```python
h = hashlib.md5((url or '').encode()).hexdigest()
```

URL 是唯一能跨爬虫保持一致且不可变的标识符。

## 涉及文件
- `scripts/crawl_pipeline.py` (hash_item 函数)
- `scripts/batch_crawler.py` (_score_and_insert 函数)
- `scripts/chromium_crawler.py` (_score_batch 函数)
- `scripts/dedicated_adapters.py` (插入循环)
- `scripts/adapter_zheneng.py` (插入循环)
- `scripts/adapter_supplement.py` (插入循环)

## 收益
- 10 组同URL重复 → 0（全部去重）
- 中标表 1 组重复 → 0
- 任何爬虫路径抓同一URL都自动去重，无需协调

## ⚠️ 副作用
- 不同招标项目如果发布在同一页面URL下，会被视为同一条（这种情况极少）
- 如果某个招标平台复用URL发布新公告，新公告不会被入库（可接受——这种情况极少）
