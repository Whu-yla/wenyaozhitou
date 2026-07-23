# 评分引擎常见缺陷 (v11 诊断手册)

## 触发表单（收到反馈后必须逐一自查）

| 反馈现象 | 可能根因 | 检查位置 |
|:--|:--|:--|
| 预算没抓 | regex 不覆盖变体格式 | `crawl_pipeline.py:extract_budget_from_content()` |
| 招标人空白 | 正文没存 raw_html 或 regex 不匹配 | `relevance_scorer.py:_extract_region_owner()` |
| 地区空白 | 没从内容提取（只靠标题） | 同上 |
| 旧公告排第一 | 无日期衰减 | `relevance_scorer.py:score_item()` 316行 |
| 过期资格预审高分 | 无截止日期过滤 | 同上 |
| 链接打不开 | 需登录/JS渲染/真死链 | `selfheal_3am.py` link check |

## 预算提取 regex 已知缺陷

已知不匹配的格式（需持续补充）：
- ✅ "最高限价：55万"
- ✅ "最高投标限价：55万"  
- ✅ "最高投标限价（万元）55.79" (南网HTML表格)
- ❌ "最高投标限价（万元）\n 55.79" (跨行格式)
- ❌ "采购预算：人民币伍拾伍万元整" (中文大写)

## 招标人提取 regex 已知缺陷

- ✅ "招标人：南方电网科学研究院有限责任公司"
- ✅ "招标人为 南方电网科学研究院有限责任公司" (南网格式)
- ❌ "招标人\n南方电网科学研究院有限责任公司" (跨行)
- ❌ 正文无招标人字段，需从详情页提取

## ⛔ Regex 字符排除集遗漏 `。` 导致数据垃圾 (2026-06-25 致命教训)

**症状**：5条南网公告的 region 字段显示 "广州2.4资格审查方式：资格后审2.5招" 而非 "广东"；3条 procurement_owner 混入 "项目已具备招标条件" 尾缀。

**根因**：`REGION_PATTERNS` 和 `BIDDER_PATTERNS` 的字符排除集使用了 `[^；;，,\n]`，遗漏了 `。`（中文句号）。南网正文格式为 "招标项目所在地区：广州。2.4资格审查方式：资格后审"——regex 匹配到 "地区：" 后因 `。` 不在排除集中，继续吞噬后续内容直到遇到 `，` 或 `\n`。

**修复 (relevance_scorer.py)**：
```python
# ❌ 错误 —— 少了 。 
re.compile(r'(?:招标项目|项目)所在地区[：:]\s*([^；;，,\n]+)')
# ✅ 正确 —— 加 。 + 长度限制
re.compile(r'(?:招标项目|项目)所在地区[：:]\s*([^。；;，,\n]{1,20})')
```

**适用范围**：`REGION_PATTERNS`（3条）和 `BIDDER_PATTERNS`（5条，第385行定义）均需同步修复。`extract_detail_fields()` 中引用的 BIDDER_PATTERNS（第222行定义）使用 `(?:[，。,.)）]|$)` 终止符，已含 `。`，无需改动。

## ⛔ 换行符被压扁导致 `[^\n]` 失效 (2026-06-25)

**症状**：修复排除集后仍有12条 owner 字段不干净。

**根因**：`_extract_region_owner()` 函数中 `clean = re.sub(r'\s+', ' ', clean)` 把换行 `\n` 压成空格 ` `，导致 regex 中 `[^\n]` 无法截断——整个正文变成一行，capture group 从头吞到尾。

**修复**：删除 `re.sub(r'\s+', ' ', clean)` 这行。`extract_detail_fields()` 中有同样的问题（第446行），一并删除。

## ⛔ 南网标题 "采购公告 >" 前缀 (2026-06-25)

**症状**：86条南网标题带 "采购公告 > 招标公告 >" 或 "采购公告 > 公示公告 >" 前缀，冗长难读。

**修复 (relevance_scorer.py score_item)**：添加循环剥离逻辑：
```python
clean_title = re.sub(r'^(?:采购公告|招标公告|中标公告|成交公告|公示公告|非招标公告|零星采购公告)\s*>\s*', '', title)
while clean_title != title:
    title = clean_title
    clean_title = re.sub(r'^(?:采购公告|招标公告|中标公告|成交公告|公示公告|非招标公告|零星采购公告)\s*>\s*', '', title)
result['title'] = title[:200]
```

## 日期衰减参数

```
age_days > 730  → ×0.3  (>2年)
age_days > 365  → ×0.5  (1-2年)  
age_days > 180  → ×0.7  (6-12月)
else            → ×1.0
```

衰减在评分最后一步（min(round(...), 100) 之前），与 geo 权重叠加。

## 凌晨自检脚本

`selfheal_3am.py` 每凌晨3点运行，做的事：
1. 读24h新反馈 → 聚类 (link_dead/budget_missing/region_missing/owner_missing/expired_notice)
2. 链接检测 → HEAD请求 → 40x/超时 → 降权×0.3
3. 预算回填 → 对缺预算高相关项目用增强regex重新提取
4. 过期清理 → 超1年高评分公告统一降权×0.5
5. 写入HOT_MEMORY.md 供下次会话感知
