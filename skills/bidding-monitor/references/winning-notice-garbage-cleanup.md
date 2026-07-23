# 中标数据清洗 — V1.10 教训

## 症状

用户原话：
> "明明是招标信息你放到中标信息里面了！然后中标抓到的网站都是采购的首页，有什么用？！"

## 根因三重

### 1. 平台首页/导航页误抓为中标

中标表（winning_notices）混入大量非公告页面：

| 平台 | 垃圾特征 | 数量 |
|:--|:--|:--|
| 数智云采云采购平台 | "框架协议采购 首页 >公告信息" | 5条 |
| 天工招采平台 | "天工招采标平台 搜 索 返回天工开物" | 3条 |
| 连云港市公共资源交易中心 | "交易信息 - 连云港市公共资源交易平台 首页 > 交易信息" | 2条 |
| 重庆市公共资源交易网 | "重庆市公共资源交易中心APP下载" | 1条 |
| 黄石公共资源交易中心 | "黄石市电子保函综合服务平台 - 关于我们" | 1条 |
| 南方电网供应链统一平台 | "招标公告-中国南方电网-供应链统一服务平台 您现在正在浏览：首页 > 采购公告 > 招标公告" | 2条 |

**特征**：标题含"首页 >""APP下载""关于我们""欢迎使用""您现在正在浏览""产品与服务""政策法规"等平台UI文本。

### 2. 中标入库不跑评分引擎

**致命根因**：`crawl_pipeline.py` 的 `insert_notice()` 对 `notice_type == 'winning'` 直接 `INSERT INTO winning_notices`，不经过 `score_item()` 的相关性过滤。

对比：
- 招标路径：爬虫 → `score_items()` → DIGITAL_GATE 过滤 → `insert_notice()` → `bidding_notices`
- 中标路径（错误）：爬虫 → 直接 `insert_notice()` → `winning_notices` ❌

### 3. DIGITAL_GATE 对中标也失效

即使以后让中标也跑 `score_item()`，DIGITAL_GATE 关键词太宽：
- "系统""服务""技术""平台" → 命中锅炉改造/煤矿大修/粉煤灰运输等一切中标正文
- 导致 100 分的项目可能是"贵州公司织金电厂2号炉再热器增容改造"（跟数智科技毫无关系）

## 修复三连

### 修复1：清理历史脏数据（V1.10）

```sql
-- 平台首页/导航页
DELETE FROM winning_notices WHERE title LIKE '%首页 >%' OR title LIKE '%APP下载%' OR title LIKE '%您现在正在浏览%';

-- 非数字化项目
DELETE FROM winning_notices WHERE title LIKE '%锅炉%' OR title LIKE '%省煤器%' OR title LIKE '%空预器%'
  OR title LIKE '%脱硫%' OR title LIKE '%煤矿%' OR title LIKE '%胶带机%'
  OR title LIKE '%粉煤灰%' OR title LIKE '%工装洗涤%' OR title LIKE '%文体馆%';
```

结果：33条 → 7条净数据。

### 修复2：评分引擎新增 NON_DIGITAL_EXCLUDE（V1.10）

在 `relevance_scorer.py` 的 `score_item()` 中，DIGITAL_GATE 检查后立即追加：

```python
NON_DIGITAL_EXCLUDE = [
    '锅炉', '省煤器', '空预器', '脱硫', '烟囱', '吸收塔', '除尘',
    '煤矿', '胶带机', '梭车', '粉煤灰', '罐车运输', '矸石',
    '再热器', '热网首站', '供热管网', '保温管道', '热电联产',
    '工装洗涤', '洗衣', '文体馆维修', '物业保洁', '食堂',
    'EPC总承包', '施工总承包', '土建', '桩基', '基坑',
]
if any(kw in text_for_check for kw in NON_DIGITAL_EXCLUDE):
    strong_save = ['数字化', '数智', '智慧工地', 'BIM', '数字孪生', '人工智能']
    if not any(kw in text_for_check for kw in strong_save):
        return None  # 直接拒掉
```

**逻辑**：锅炉/煤矿等非数字化关键词命中→直接打回。但允许「智慧工地 EPC总承包」（同时命中数字化强关键词）通过。

### 修复3：爬虫层首页检测（预防未来）

在 `batch_crawler.py` 和 `dedicated_adapters.py` 中添加：

```python
HOMEPAGE_PATTERNS = [
    '欢迎来到', '欢迎使用', '设为首页', '收藏此页', '平台首页',
    '您现在正在浏览', '首页 >', 'APP下载', '关于我们',
    '产品与服务', '政策法规', '帮助中心', '异议投诉',
    '客服热线', '注销', '个人中心',
]

def is_homepage(title, content=''):
    text = title + ' ' + (content or '')
    return any(p in text for p in HOMEPAGE_PATTERNS)
```

## 最终数据（V1.10）

| 表 | 清洗前 | 清洗后 | 净数据 |
|:--|:--|:--|:--|
| bidding_notices | 133 | 120 | 删除13条平台首页+协会新闻 |
| winning_notices | 33 | 7 | 删除14条首页+12条非数字项目 |

保留的7条中标全部是数字化/APP/OMS运维/安防监控类相关项目。
