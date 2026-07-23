# chromium_crawler.py L1 页面判别器缺失 → 已修复

**发现日期**：2026-06-26 09:00 定时任务
**修复日期**：2026-06-26 16:00
**严重程度**：高危 — 18条新数据中 16 条（89%）是垃圾

## 症状

2026-06-26 9:00 管线跑完后，DB 新增 18 条记录，其中 16 条为平台导航页/首页垃圾：

| 垃圾标题示例 | 实际情况 | 评分 |
|:--|:--|:--|
| 深圳能源电子招标投标平台 - 结果公告 您好，欢迎来到... | 平台首页 | 52-66 |
| 内蒙古电力集团电子商务系统V1.0欢迎您 | 欢迎页 | 50 |
| 中国能源建设集团电子采购平台首页 | 平台首页 | 63 |

16/18 条 publish_date 为空 → 明显非真实公告。

## 根因

三层拦截架构中的 L1（页面判别器）仅在 `crawl_pipeline.py` 实现。`chromium_crawler.py` 作为四连跑中最后加入的组件，从未接入 L1 守卫。数据路径：`fetch_detail_text()` → `_score_batch()` → `score_items()` → `INSERT OR IGNORE`，全程无页面类型检查。

## 垃圾为何通过评分

平台首页文本包含"系统""管理""电子采购平台"等词 → 命中 DIGITAL_GATE 和 STRONG_KEYWORDS → 评分 50-66 分 → 高于阈值 50 → 入库。

## 新发现的垃圾特征

```
V1.0欢迎您, 欢迎来到(, 设为首页, 收藏此页, 电子采购平台首页, 平台首页|, 首页|
```

## 修复实现（2026-06-26）

### 1. L1 判别器函数 `is_valid_notice_page(text, title='')`

在 `chromium_crawler.py` 中新增，位于 `from relevance_scorer import score_items` 之后：

```python
PAGE_SIGNALS_REJECT = [
    # 平台欢迎/首页信号
    '欢迎来到', '欢迎您', '欢迎光临', 'V1.0欢迎您',
    '设为首页', '收藏此页', '平台首页', '网站首页',
    # 导航/面包屑（没有实际公告内容）
    '您当前访问的是', '访问正式平台', '请点击 https://',
    '电子采购平台首页', '平台操作流程', 'CA办理',
    # 非公告页面
    '易招标-首页', '产品与服务', '成功案例',
    '中国招标投标协会', '年会报道', '年会召开',
    # 企业宣传/文章
    '三十而立', '岁月答卷', '三峡小微', '小说阅读',
    # 空列表/无内容
    '暂无数据', '没有找到', '无相关公告',
]

def is_valid_notice_page(text, title=''):
    combined = (title + ' ' + text)[:2000]
    # 1. 必须足够长
    if len(text) < 100:
        return False
    # 2. 必须含公告核心词
    notice_keywords = ['招标', '中标', '采购', '公告', '公示', '投标', '项目']
    if not any(kw in combined for kw in notice_keywords):
        return False
    # 3. 拒绝平台导航/欢迎/首页信号 — 3个以上命中即拒
    rejection_count = 0
    for signal in PAGE_SIGNALS_REJECT:
        if signal in combined:
            rejection_count += 1
    if rejection_count >= 3:
        return False
    # 4. 拒绝纯导航（标题太短且含平台名）
    if len(title) < 15 and any(kw in title for kw in ['平台', '首页', '系统', '易招标']):
        return False
    return True
```

### 2. 接入采集管线

在 `main()` 的详情页循环中，标题提取后立即调用判别器：

```python
# ★ L1 页面类型判别 — 拒绝平台首页/导航/欢迎页
if not is_valid_notice_page(text, title):
    site_rejected += 1
    print(f"    🚫 L1拒绝: {title[:50]}")
    continue
```

统计输出：`print(f"  本平台采集 {site_items} 条，L1拒绝 {site_rejected} 条")`

### 3. 误伤保护设计

- **3 命中阈值**：单个信号（如「首页」出现在正经公告页面导航栏）不会误杀
- **公告核心词前置**：不含「招标/中标/采购/公告/公示/投标/项目」的直接放行前返回 False
- 真实案例：南网公告页导航含「首页」= 1 命中，不触发拒绝

### 4. 同时修复

- `_score_batch()` 中 `except: pass` → `except Exception as e: print(...)`

## 垃圾数据清理 SOP

```sql
-- 按信号词删垃圾
DELETE FROM bidding_notices 
WHERE title LIKE '%欢迎来到%' OR title LIKE '%首页%' 
  OR title LIKE '%V1.0欢迎您%' OR title LIKE '%设为首页%'
  OR title LIKE '%电子采购平台首页%' OR title LIKE '%易招标-首页%'
  OR title LIKE '%中国招标投标协会%年会%' OR title LIKE '%三十而立%';

-- 兜底：无publish_date的今日入库记录
DELETE FROM bidding_notices 
WHERE date(fetch_date) = date('now','localtime')
  AND (publish_date IS NULL OR length(publish_date) < 5);
```

⚠️ 注意：`%首页%` 可能误伤正文含导航的合法公告——优先用信号词组合 + 无日期双重条件过滤。
