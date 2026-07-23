---
name: long-term-memory-engine
description: 文鳐智投长记忆系统 — HOT/WARM/COLD 三层架构 + 通义千问 text-embedding-v3 语义检索 + 每日自动维护
tags: [memory, embedding, vector-search, hot-warm-cold, daily-log, wenyaozhitou]
---

# 文鳐智投长记忆系统

## 架构总览

```
bidding_engine.py（每次扫描后）
        │
        ▼ memory_engine.add_memory()
┌──────────────────────────────────────┐
│  SQLite data/memory.db               │
│  ┌─────────┬──────────┬──────────┐   │
│  │ 🔥 HOT  │ 🌤 WARM  │ ❄️ COLD │   │
│  │ <7天    │ 7-30天   │ >30天    │   │
│  └─────────┴──────────┴──────────┘   │
│                                      │
│  通义千问 text-embedding-v3 (1024维)  │
│  L2归一化 → 余弦相似度搜索             │
│  importance加权 → 语义去重（阈值0.92） │
└──────────────────────────────────────┘
        │
        ▼ 每日9:00 cron (eba2fa280224)
memory_maintainer.py
  → 降级 HOT→WARM→COLD
  → 语义去重
  → 生成日报 data/memory_logs/digest_YYYY-MM-DD.md
```

## 文件位置（实际部署）

| 文件 | 路径 |
|:-----|:-----|
| 核心引擎 | `scripts/memory_engine.py` |
| 维护脚本 | `scripts/memory_maintainer.py` |
| 向量数据库 | `data/memory.db` |
| 日报归档 | `data/memory_logs/digest_YYYY-MM-DD.md` |
| API Key | `/tmp/qwen_key.txt`（`sk-...` 格式） |

所有路径相对于 `~/.hermes/profiles/wenyaozhitou/`。

## 三层记忆

| 层级 | 存储 | 用途 | 维护 |
|:----|:-----|:-----|:-----|
| 🔥 HOT | memory.db (tier=HOT) | 最近7天：扫描摘要、高相关招标、异常 | 每日自动降级 |
| 🌤 WARM | memory.db (tier=WARM) | 7-30天：稳定偏好、经验 | 30天后降级到COLD |
| ❄️ COLD | memory.db (tier=COLD) | 30天前：历史决策、里程碑 | 永久保留 |

## 核心 API

### Python 调用

```python
import sys
sys.path.insert(0, '/root/.hermes/profiles/wenyaozhitou/scripts')
from memory_engine import *

init_db()

# 写入（source+ref_id 唯一去重，语义去重阈值0.92）
mid = add_memory(
    "内容文本",
    category="分类名",      # 规范/架构/功能/业务/评分/招标/扫描/异常
    tags="标签1,标签2",
    importance=1.5,         # 0.1~5.0，越高越重要
    source="scan",          # user/system/decision/scan
    ref_id="unique_ref"     # source+ref_id 组合唯一
)

# 语义搜索（加权分 = cosine × importance）
results = search_memory("查询", top_k=5, category="", min_similarity=0.3)
for score, mid, content, cat, tags, tier, created, ac in results:
    print(f"[{cat}] #{mid} {score:.2f} {content[:60]}")

# 原始余弦搜索（去重用，不加importance权重）
results = search_memory("查询", top_k=5, raw_cosine=True)

# 统计
stats()  # → {"total": N, "tiers": {...}, "categories": {...}}

# 维护
maintain()     # 降级
deduplicate()  # 语义去重
```

### CLI 命令

```bash
cd /root/.hermes/profiles/wenyaozhitou/scripts

python3 memory_engine.py                     # 统计
python3 memory_engine.py init                # 初始化DB
python3 memory_engine.py add "内容" "分类"   # 添加记忆
python3 memory_engine.py search "查询"       # 搜索（加权分）
python3 memory_engine.py maintain            # 降级
python3 memory_engine.py dedup               # 语义去重

python3 memory_maintainer.py                 # 完整维护（降级+去重+日报）
```

## 嵌入 API

- **模型**：通义千问 text-embedding-v3（1024维）
- **端点**：`POST https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding`
- **认证**：`Authorization: Bearer {key}`（Key 从 `/tmp/qwen_key.txt` 读取）
- **归一化**：L2 归一化后存储和搜索，余弦相似度 = `np.dot(q_vec, db_vec)`
- **缓存**：内存缓存（按文本前200字符），同会话内复用

## 与投标引擎集成

`bidding_engine.py` 每次扫描后自动调用 `add_memory()`：

1. **TOP3 高相关招标** → `category='招标'`，importance = relevance_score/3
2. **扫描摘要** → `category='扫描'`，含成功/失败/新增数
3. **异常站点** → `category='异常'`，前5条

### 集成代码位置

`bidding_engine.py` → `run_crawl()` → 在 `crawl_log` 写入之后、`conn.close()` 之前：
```python
try:
    from memory_engine import add_memory, init_db as mem_init
    mem_init()
    # ... 写入记忆
except Exception as e:
    log(f"⚠️ 记忆写入失败: {e}")
```

## 定时任务

| Job ID | 时间 | 内容 |
|:---|:-----|:-----|
| `eba2fa280224` | 每日 9:00 | 记忆维护（降级+去重+日报） |

## 排坑记录

### 1. 余弦相似度 > 1.0
**原因**：text-embedding-v3 返回的向量未归一化，`cosine=dot(a,b)/(|a|×|b|)` 在向量非单位时仍可能 >1（浮点精度），且 `search_memory` 返回加权分 = cosine × importance，importance=2.0 时轻松 >1。
**修复**：
- `get_embedding()` 返回前 L2 归一化
- `add_memory()` 去重检查改用 `raw_cosine=True`（不加权）
- `search_memory()` 的余弦简化为 `np.dot(q_vec, vec)`（归一化后直接点积）

### 2. 6条记忆全被当重复
**原因**：第一条 importance=2.0，后续搜索返回加权分 0.46×2.0=0.92，刚好等于去重阈值0.92。
**修复**：add_memory 语义去重改为 `raw_cosine=True`，只用纯余弦 >0.92 判定。

### 3. Python 兼容
向量运算用 numpy，JSON 序列化用标准库，HTTP 请求用 requests。需要 `numpy` 和 `requests`。

### 4. API Key 格式
Key 在 `/tmp/qwen_key.txt`，纯文本无换行。DashScope Bearer 认证。

### 5. Memory DB 位置
`data/memory.db`，SQLite + WAL 模式。第一次调用 `init_db()` 自动建表。

### 6. 语义去重阈值
默认 0.92。太低会漏过相似的，太高会在 update 时误判为新记忆。当前值经过 6 条不同类别记忆的写入测试，各类内容（版权/AI/主题/业务/评分/客户）互不误判。

### 7. raw_cosine 参数的必要性
`search_memory()` 默认返回加权分（cosine × importance），用于展示排序。但去重判定必须用原始余弦相似度，否则高 importance 记忆会导致所有新记忆被误判为重复。调用 `search_memory(query, raw_cosine=True)` 获取纯余弦值做去重比较。

### 8. 路径迁移与桥接模式（2026-07-02）
Hermes 系统提示词注入了旧版绝对路径 CLI 命令（`/root/.hermes/memory_store/`），而实际实现已迁移到 profile 内（`scripts/memory_engine.py`）。解决方案：在旧路径放置 thin wrapper 桥接脚本，委托到新版实现。同时需维护 `memory/hot/HOT_MEMORY.md`、`memory/warm/WARM_MEMORY.md`、每日日志的完整性。

> 详见 `references/path-migration-bridge.md`
