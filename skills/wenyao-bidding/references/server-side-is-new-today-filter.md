# 服务端 is_new_today 过滤 — 响应体积 306KB→24KB（93%削减）

## 问题

前端「今日新增」卡片点击后响应 3-4 秒——服务端 API 每次返回全量 103 条招标（306KB JSON），
客户端过滤后只用到 8 条（24KB）。306KB × 2（招标+中标并行）= 612KB 网络传输。

## 根因

`bookmark_server.py` 的 `query_items()` 不支持 `is_new_today` 过滤参数。
前端只能客户端过滤——下载全部数据再筛。

## 修复 (V1.40)

### 1. 服务端新增 `is_new_today` 查询参数

```python
# bookmark_server.py → query_items()
is_new_today = params.get('is_new_today', ['0'])[0] == '1'

# ... SQL查询 + is_new_today 计算 ...

# 服务端过滤今日新增
if is_new_today:
    rows = [r for r in rows if r['is_new_today']]
    total = sum(1 for r in rows)
```

### 2. 内存缓存 yesterday_ids

```python
_yesterday_ids_cache = None

def get_yesterday_ids():
    global _yesterday_ids_cache
    if _yesterday_ids_cache is not None:
        return _yesterday_ids_cache
    # ... 读归档文件 ...
    _yesterday_ids_cache = ids
    return ids
```

### 3. 前端传参

```javascript
// apiFilter() → today 快速路径
op.set('is_new_today', '1');  // 服务端过滤
```

## 效果

| | 之前 | 之后 |
|:--|:--|:--|
| 招标响应 | 306KB (103条) | 24KB (8条) |
| 中标响应 | ~100KB (16条) | 7KB (3条) |
| 并行总量 | ~406KB | 31KB |
| 节省 | — | **93%** |
