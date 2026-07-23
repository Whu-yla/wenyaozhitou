# 站点适配器框架

## 设计原则

- 只对**已确认可用的站点**配置专用公告列表URL
- 未匹配站点 → 保持原始URL，**不瞎试模式**
- 每个站点最多爬取 2-3 页公告列表

## 当前适配站点

| 站点 | 公告列表URL模式 |
|:-----|:-----|
| hbggzyfwpt.cn | `/jyxx/jsgcZbgg?pageNo={page}&pageSize=30` |
| ggzy.hubei.gov.cn | `/hubei/jyxx/004002/004002001/?pageNo={page}` |
| ggzy.hunan.gov.cn | `/trade/bulletin/index.html?type=1` |
| ggzy.guizhou.gov.cn | `/trade/bulletin/index.html?type=1` |
| ggzy.ah.gov.cn | `/jyxx/002001/002001001/?pageNo={page}` |
| chnzb.cn (华能) | `/search/?q=&type=zbgg&page={page}` |
| cebpubservice.com | `/biddingBulletin/...` |
| chinabidding.com.cn | `/search/searchzbw/searchpro?page={page}` |

## 添加新站点

在 `site_adapters.py` 的 `SITE_ADAPTERS` 字典中添加一行：

```python
"域名关键字": "https://完整URL?pageNo={page}&pageSize=30",
```

## JS渲染站点

以下站点是SPA前端渲染，requests无法获取内容：
`ecp.sgcc.com.cn`, `sgcc.com.cn`

## 公共资源交易中心模式参考

大多数省市级公共资源中心遵循类似URL结构：
- `/jyxx/jsgcZbgg?pageNo={page}&pageSize=30` — 工程招标
- `/jyxx/002001/002001001/?pageNo={page}` — 另一种格式
- `/trade/bulletin/index.html?type=1` — 政府采购类
