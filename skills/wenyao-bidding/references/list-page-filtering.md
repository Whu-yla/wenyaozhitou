# 列表页误抓防护（2026-06-25）

## 症状

浙能平台 9 条记录是**分类列表页**而非实际招标项目：
- `https://zsrm.zjenergy.com.cn/zjnycms/category/bulletinListNew.html`
- `https://zsrm.zjenergy.com.cn/zjnycms/category/otherBulletinList.html`
- `https://zsrm.zjenergy.com.cn/zjnycms/category/coalPurchaseList.html`

标题都是「浙江能源集团智慧供应链一体化平台V1.0 欢迎来到...」——这是列表页的 `<title>` 标签内容。

## 根因

`batch_crawler.py` 的 `extract_bid_detail_links()` 排除列表里有 `'list'` 和 `'page'`，但 `combined` 已做 `lower()` 转换，`'BulletinList'` → `'bulletinlist'` → 不含小写 `'list'`（因为 `'bulletinlist'.find('list')` 找不到——`'list'` 不是 `'bulletinlist'` 的子串）。

实际上：`'list' in 'bulletinlist'` → **返回 True**！`'bulletinlist'` 确实包含 `'list'`。

真正原因：这些链接**不是从 `batch_crawler` 来的**，而是从 `chromium_crawler.py` 或某个适配器抓的。source_site 显示「浙能集团」（不是「浙能集团智慧供应链平台」），说明来自不同的爬虫。

## 修复

在 `batch_crawler.py` 的 `extract_bid_detail_links()` 加强过滤：

```python
# 排除列表页
exclude = ['login', 'register', 'index', 'search', 'javascript', 'more', 
           'category', 'bulletinlist', 'listpage', 'purchaselist',
           '首页', '登录']

# 额外：排除带大量参数且含category/list的URL
if '?' in href and ('category' in href.lower() or 'list' in href.lower()):
    is_excluded = True
```

## 清理历史数据

```sql
DELETE FROM bidding_notices 
WHERE url LIKE '%category%' OR url LIKE '%listPage%' OR url LIKE '%bulletinList%';
```

## 预防

- 每次新适配器上线后，抽查 URL 清单，确认没有 `category`/`list` 型 URL
- `pipeline_master.sh` 阶段2清洗中可加自动检测
