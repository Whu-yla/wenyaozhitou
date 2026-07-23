# 平台首页/导航页 垃圾过滤

## 症状
爬虫从平台首页抓到的非项目页面以高分入库：
- `浙江能源集团智慧供应链一体化平台V1.0 欢迎来到...` (score 58-62, 6条)
- `南方电网电子采购交易平台 您好！欢迎使用...` (score 63)
- `中国招标投标协会 2026年年会在深圳召开 年会报道...` (score 95)
- `易招标-首页 产品与服务 产品与服务 企业采购...` (score 95)
- `深圳能源电子招标投标平台 - 预中标公告 您好，欢迎来到...` (score 80)
- `详情页 首页 主体信息 信用信息...` (score 61)

## 过滤规则（batch_crawler 层）

在 `batch_crawler.py` 的 `_score_and_insert()` 之前检查：

```python
HOMEPAGE_GARBAGE = [
    '欢迎来到', '欢迎使用', '设为首页', '收藏此页', '联系我们',
    '平台首页', '产品与服务', '客服热线', '注销', '个人中心',
    '全部信息', '全部公告', '政策法规', '服务中心', '首页 >',
    '您现在所在位置', '年会报道', '年会召开', '杂志编委',
    'V1.0 欢迎', '首页 产品', '预中标公告 您好',
]

def is_homepage_garbage(title, content=''):
    text = title + ' ' + (content or '')
    for kw in HOMEPAGE_GARBAGE:
        if kw in text:
            return True
    return False
```

## 已入库清理

```sql
DELETE FROM bidding_notices WHERE 
    title LIKE '%欢迎来到%' OR title LIKE '%欢迎使用%' 
    OR title LIKE '%设为首页%' OR title LIKE '%收藏此页%'
    OR title LIKE '%平台首页%产品%服务%' 
    OR title LIKE '%客服热线%' OR title LIKE '%年会%召开%';
```

## 预防

- 每次新增爬虫平台后，检查入库数据中是否有该平台的导航页/首页文本
- 特征：标题短而通用（如"首页"、"招标公告"不加具体项目名），正文纯导航菜单
