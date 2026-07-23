# dlzb.com — 一站式电力招标聚合源

## URL: https://www.dlzb.com/

## 数据规模
- 全站: 13,769,892 条
- 华能专区: 13,886 条/604 页
- 每页约 20-25 条

## 覆盖企业
国电投 / 华能 / 华电 / 国家能源 / 大唐 / 国网 / 南网 / 核电 /
中国电建 / 中国能建 / 国投 / 晋能 / 京能 / 粤电 / 华润 /
煤矿 / 中铁 / 中交 / 铁塔通信 / 国家管网 / 五矿

## 访问方式
- **必须 Chromium headless**，curl/requests 被阿里云 WAF 拦截
- 关键参数: `--disable-blink-features=AutomationControlled`
- virtual-time-budget: 30000ms
- subprocess timeout: 60s

## 页面结构（渲染后）
- 面包屑: 首页 » 招标公告 » {公司名}
- 列表项: 标题 `<a>` 链接、标签、日期 (YYYY-MM-DD)、收藏按钮
- 链接格式: `https://www.dlzb.com/d-zb-XXXXXXXX.html`
- 详情页需登录（银牌以上会员），列表页公开

## 数据提取正则
```python
pattern = r'href="(https://www\.dlzb\.com/d-zb-\d+\.html)"[^>]*>\s*(.*?)\s*</a>'
matches = re.findall(pattern, html)
```

## 限制
- 仅标题级数据（无正文/金额/中标人）
- 需数字关键词快速过滤
- 需排除词清洗（硬件采购/设备类噪音）

## 适配器文件
`scripts/adapter_dlzb.py` — 统一适配器，覆盖9个WAF/SSO封锁平台

## 管线接入
crawl_pipeline.py 阶段11 — 在全部直连适配器之后运行，仅兜底无直连的平台
