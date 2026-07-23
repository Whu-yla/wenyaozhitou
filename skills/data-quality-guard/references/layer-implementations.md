# 三层拦截架构 — 实现参考

## L1: 页面类型判别器

位置: `crawl_pipeline.py` → `insert_notice()` 入口

```python
PLATFORM_SIGNALS = [
    '您现在正在浏览', '首页 >', 'APP下载', '关于我们',
    '返回首页', '平台首页', '设为首页', '收藏此页',
    '欢迎来到', '您好！欢迎', '框架协议采购 首页',
    '公告信息 公告信息', '交易信息 -',
    '电子保函综合服务平台', '搜 索 返回天工开物',
]
if any(sig in check_text for sig in PLATFORM_SIGNALS):
    return False  # 平台页，静默丢弃
```

## L2: NON_DIGITAL_EXCLUDE

位置: `relevance_scorer.py` → `score_item()` 第285行

```python
NON_DIGITAL_EXCLUDE = [
    '锅炉', '省煤器', '空预器', '脱硫', '烟囱', '吸收塔', '除尘',
    '煤矿', '胶带机', '梭车', '粉煤灰', '罐车运输', '矸石',
    '再热器', '热网首站', '供热管网', '保温管道', '热电联产',
    '工装洗涤', '洗衣', '文体馆维修', '物业保洁', '食堂',
    'EPC总承包', '施工总承包', '土建', '桩基', '基坑',
]
```

命中后检查强数字化关键词白名单（智慧工地/BIM/数字孪生等），有则放行。

## L3: 中标独立评分

位置: `relevance_scorer.py` → `score_item()` 第315行

三逻辑：
1. 竞品中标 → 基础分25
2. 非竞品但含强数字化关键词 → 基础分15
3. 非竞品且无数字化关键词 → 直接丢弃

竞品名单与 `competitor_tracker.py` 同步维护。

## 验证命令

```bash
# 检查是否有平台首页漏网
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/profiles/wenyaozhitou/data/bidding.db')
for t in ['bidding_notices','winning_notices']:
    for r in conn.execute(f\"SELECT id,title FROM {t} WHERE title LIKE '%首页%' OR title LIKE '%欢迎%'\").fetchall():
        print(f'{t} id={r[0]}: {r[1][:80]}')
"

# 检查中标表是否有非数字项目
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/profiles/wenyaozhitou/data/bidding.db')
for r in conn.execute(\"SELECT id,title FROM winning_notices WHERE title LIKE '%锅炉%' OR title LIKE '%煤矿%' OR title LIKE '%洗涤%'\").fetchall():
    print(f'BAD: id={r[0]}: {r[1][:80]}')
"
```
