# L1 页面判别器 — 集中化方案 (V1.35)

## 设计决策

**之前**：L1 分散在多个管线中
- `crawl_pipeline.py` → insert_notice() 入口有判别
- `batch_crawler.py` → DETECT_HOMEPAGE() 函数
- `chromium_crawler.py` → **无判别** ← 漏洞

**现在 (V1.35)**：L1 集中到 `relevance_scorer.py` 的 `score_item()` 入口
- 所有管线（crawl_pipeline + dedicated_adapters + batch_crawler + chromium_crawler）都经过 `score_item()` → `score_items()`
- 一次改一处，全管线生效
- chromium_crawler 同时保留自身的 L1（双重保险，提前拦截减少详情页抓取）

## 实现位置

`relevance_scorer.py` → `score_item()` 函数，第279-296行（DIGITAL_GATE 之前）

```python
# ═══ L1 页面类型判别 — 拒绝平台首页/导航/欢迎页 ═══
L1_REJECT_SIGNALS = [
    '欢迎来到', '欢迎您', '欢迎光临', 'V1.0欢迎您', 'V1.0 欢迎',
    '设为首页', '收藏此页', '平台首页', '网站首页',
    '电子采购平台首页', '平台操作流程', 'CA办理',
    '易招标-首页', '易招标', '产品与服务',
    '中国招标投标协会', '年会报道', '年会召开',
    '三十而立', '岁月答卷', '三峡小微',
    '您当前访问的是', '访问正式平台',
]
l1_hits = [s for s in L1_REJECT_SIGNALS if s in text_for_check]
# 3个以上L1信号 + 标题不含公告词 → 平台导航页
notice_kw = ['招标', '中标', '采购', '公告', '公示', '投标', '项目']
has_notice_kw = any(kw in title for kw in notice_kw)
if len(l1_hits) >= 3 and not has_notice_kw:
    return None
# 浙能/深圳能源 特殊模式
if ('V1.0' in title or '欢迎来到' in title) and not has_notice_kw:
    return None
```

## 垃圾信号词库（持续积累）

| 信号词 | 来源平台 | 发现日期 |
|:--|:--|:--|
| 欢迎来到( | 深圳能源 | 2026-06-26 |
| V1.0欢迎您 | 内蒙古电力、浙能 | 2026-06-26 |
| V1.0 欢迎 | 浙能 | 2026-06-26 |
| 设为首页 | 深圳能源 | 2026-06-26 |
| 收藏此页 | 深圳能源 | 2026-06-26 |
| 电子采购平台首页 | 中国能建 | 2026-06-26 |
| 您当前访问的是 | 中国能建 | 2026-06-26 |
| 访问正式平台 | 中国能建 | 2026-06-26 |
| 平台操作流程 | 内蒙古电力 | 2026-06-26 |
| CA办理 | 内蒙古电力、浙能 | 2026-06-26 |
| 易招标-首页 | 三峡集团 | 2026-06-26 |
| 产品与服务 | 易招标 | 2026-06-26 |
| 中国招标投标协会 | 重庆交易网 | 2026-06-26 |
| 年会报道/年会召开 | 重庆交易网 | 2026-06-26 |
| 三十而立 | 三峡 | 2026-06-26 |

## 判别策略

1. **3+信号原则**：至少3个L1信号同时命中才拒绝 → 防止单信号误伤（如公告正文提到"首页"）
2. **公告词豁免**：标题含「招标/中标/采购/公告/公示/投标/项目」→ 即使L1信号多也放行
3. **特殊模式**：「V1.0」或「欢迎来到」在标题中 + 无公告词 → 直接拒绝（浙能/深圳能源特征）

## chromium_crawler 双重保险

`chromium_crawler.py` 同时保留 `is_valid_notice_page()` 函数，在详情页抓取后立即检查——在进入 `_score_batch()` → `score_items()` → `score_item()` 之前就拦截，减少无意义的评分计算。

## 新增垃圾信号 SOP

发现新垃圾模式时：
1. 将信号词加入 `relevance_scorer.py` 的 `L1_REJECT_SIGNALS` 列表
2. 将信号词加入 `chromium_crawler.py` 的 `PAGE_SIGNALS_REJECT` 列表
3. 用实际垃圾数据测试 `score_item()` 确认返回 None
4. 更新本文件信号词库
5. SQL DELETE 清已入库的同类垃圾
