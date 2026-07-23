# score_item 调用陷阱 (2026-06-26)

## 症状
适配器中评分调用看似正常，但所有项目评分始终为 0，`final_score` 字段不存在。

## 根因

### 陷阱 1: 字段名错误
`relevance_scorer.score_item()` 返回 dict 中的评分字段是 `relevance_score`，不是 `final_score`。

```python
# ❌ 永远返回 0
sc = score_item(item)
if sc and sc.get('final_score', 0) >= 55:
    item['relevance_score'] = sc['final_score']

# ✅ 正确
if sc and sc.get('relevance_score', 0) >= 55:
    item['relevance_score'] = sc['relevance_score']
```

### 陷阱 2: 函数签名错误
`score_item()` 只接受一个 dict 参数，不是 `(title, content)` 两个参数。

```python
# ❌ TypeError: score_item() takes 1 positional argument but 2 were given
sc = score_item(item['title'], item['content'])

# ✅ 正确
sc = score_item(item)  # item 必须是完整的 dict
```

### 陷阱 3: dict 缺少必要字段
item dict 必须包含 `notice_type` 和 `publish_date` 字段，否则评分引擎可能返回异常或 0 分。

```python
# 最小有效 item
item = {
    'title': '...',
    'content': '...',
    'notice_type': 'bidding',  # 或 'winning'
    'publish_date': '2026-06-26',
}
```

## 影响范围
- `adapter_dlzb.py` — crawl_all, crawl_huaneng, crawl_huadian, crawl_datang
- `adapter_huaneng.py` — crawl_huaneng
- `crawl_pipeline.py` — 所有适配器的评分调用

## 修复方法
```bash
# 全局搜索旧模式
grep -rn "final_score" scripts/
grep -rn "score_item(item\['title'\]" scripts/
# 替换为 relevance_score + score_item(item)
```
