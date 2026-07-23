# API 性能优化三层体系

本次会话（V1.42-1.45）沉淀的三层性能优化模式。

## 问题演进

### 症状 1：今日新增 badge=8 但只显示 2 行（V1.42）
- 根因：`allB` 来自 page-1 size=20 的过滤结果（2条），`totalBidding` 来自独立 size=200 请求的计数（8条）
- 修复：在计数循环中同时把全量过滤数据写回 `allB/allW`

### 症状 2：点今日新增 3-4 秒无响应（V1.43）
- 根因：3 个串行 API 请求（page-1 + bidding全量 + winning全量），每次返回 306KB
- 修复：跳过 page-1 请求，`Promise.all` 并行拉取，耗时减 67%

### 症状 3：仍慢（V1.44）
- 根因：API 无过滤参数，返回 306KB 全量（103条），客户端过滤后只需 24KB（8条）——浪费 93%
- 修复：服务端新增 `is_new_today=1` 查询参数，后端直接返回 8 条 24KB

### 症状 4：切 Tab 3-4 秒（V1.45）
- 根因：每次切 Tab 触发公网 API 请求（网络延迟 1.7s）
- 修复：`Cache-Control: public, max-age=30` + 页面加载时预拉中标数据

## 三层架构

| 层 | 机制 | 效果 |
|:--|:--|:--|
| L1 服务端过滤 | `is_new_today=1` 参数，Python 层过滤 | 306KB → 24KB（省93%） |
| L2 浏览器缓存 | `Cache-Control: max-age=30` | 30s内零网络请求 |
| L3 预加载 | `init()` 中后台 fetch 中标 URL | 首次点击即缓存命中 |

## 服务端实现

```python
# bookmark_server.py query_items()
is_new_today = params.get('is_new_today', ['0'])[0] == '1'

# 在 Python 层过滤（is_new_today 是计算字段，无法 SQL 过滤）
if is_new_today:
    rows = [r for r in rows if r['is_new_today']]
    total = sum(1 for r in rows)
```

## 内存缓存

```python
_yesterday_ids_cache = None
def get_yesterday_ids():
    global _yesterday_ids_cache
    if _yesterday_ids_cache is not None:
        return _yesterday_ids_cache
    # ... read archive file ...
    _yesterday_ids_cache = ids
    return ids
```

## 前端快速路径

```javascript
// apiFilter() — today 快速路径
if (_activeStatFilter === 'today') {
    const fetches = ['bidding','winning'].map(async (tt) => {
        const op = new URLSearchParams();
        op.set('type', tt); op.set('size','200'); op.set('min_score','1');
        op.set('is_new_today', '1');
        const r = await fetch('/bidding/api/items?' + op.toString());
        const d = await r.json();
        return d.ok ? { tt, filtered: d.data } : null;
    });
    const results = await Promise.all(fetches);
    // ...
}
```

## 前端预加载

```javascript
// init() → loadFromApi() — 后台预热中标 Tab
await apiFilter();  // 加载招标
fetch('/bidding/api/items?type=winning&page=1&size=20&sort=relevance_score&sort_dir=desc&min_score=1')
  .catch(() => {});  // 落入浏览器缓存
```

## 验证

```bash
# 服务端过滤
curl -s "http://127.0.0.1:8090/items?type=bidding&is_new_today=1&size=200&min_score=1" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'total={d[\"total\"]}, len={len(d[\"data\"])}')"
# 预期: total=8, len=8

# Cache-Control 头
curl -sI "http://127.0.0.1:8090/items?..." | grep Cache-Control
# 预期: Cache-Control: public, max-age=30
```
