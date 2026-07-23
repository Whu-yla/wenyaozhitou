# 六大六小发电集团招标平台适配指南

## 背景

中国电力行业由「六大六小」发电集团主导。这些集团及其下属公司的招标公告集中在各自的官方电子采购平台上。数智科技的核心客户就是这些发电集团（智慧工地、智能安防、数字化平台），因此这些平台是**投标信息最高优先级来源**。

## 六大（6 Major Power Groups）

| 集团 | 简称 | 招标平台URL | 平台特征 |
|:--|:--|:--|:--|
| 中国华能集团 | 华能 | chnzb.cn / ec.chng.com.cn | 连接拒绝/HTTP412，需登录 |
| 中国华电集团 | 华电 | chdtp.com | HTTP412 反爬 |
| 中国大唐集团 | 大唐 | cdt-ec.com | JS-SHELL，需 Chromium |
| 国家电力投资集团 | 国电投 | ebid.espic.com.cn | ⚠️ **与浙能同平台**（电能e招采），iframe同模式但WAF保护+详情页PDF |
| 国家能源集团 | 国家能源 | chnenergybidding.com.cn/bidweb/ | ✅ **Chromium适配器已达**。JS-SPA，Chromium `--dump-dom` 获339条详情链接。对口：工控信息安全/智能预警/数智科技 |
| 中国三峡集团 | 三峡 | eps.ctg.com.cn | ✅ 已适配 `crawl_sanxia()` |

## 六小（6 Smaller Power Groups）

| 集团 | 简称 | 招标平台URL | 平台特征 |
|:--|:--|:--|:--|
| 中国广核集团 | 中广核 | ecp.cgnpc.com.cn | JS-SHELL，需 Chromium |
| 华润电力控股 | 华润 | szecp.crc.com.cn | ✅ **已适配** `crawl_huarun_szecp()` |
| 国投电力控股 | 国投 | sdicc.com.cn | 177KB页面但链接为JS动态加载 |
| 中国核工业集团 | 中核 | cnncecp.com.cn | JS-SHELL |
| 中国节能环保集团 | 中节能 | ebidding.cecep.cn | 403 WAF拦截，需Chromium |
| 中国电力建设集团 | 电建/能建 | ec.ceec.net.cn | ❌ **不抓**（中南院母公司） |

## 电网公司（Grid Companies）

| 公司 | 招标平台URL | 特征 |
|:--|:--|:--|
| 南方电网 | bidding.csg.cn | ✅ **已适配** `crawl_nanwang()` — 单平台7条招标+3条中标 |
| 国家电网 | ecp.sgcc.com.cn | 全站JS渲染+登录保护，最难攻克 |

## 地方重要能源集团

| 集团 | 招标平台URL | 特征 |
|:--|:--|:--|
| 浙能集团 | zsrm.zjenergy.com.cn | ✅ **已适配** `adapter_zheneng.py` — **41条入库，含2个100分项目** |
| 深圳能源 | zb.sec.com.cn | ✅ 已适配 `crawl_shenneng()`，但13条全不相关（施工设备） |
| 内蒙古电力 | impc.e-bidding.org | ⚠️ Chromium渲染后文本质量差 |

## 🔑 关键发现：电能e招采共享平台 (2026-06-24)

**浙能集团**和**国电投**使用同一套「电能e招采」平台软件，URL结构完全一致：

| 特征 | 浙能 | 国电投 |
|:--|:--|:--|
| 主页 | `zsrm.zjenergy.com.cn` | `ebid.espic.com.cn` |
| iframe数据源 | `/zjnycms//category/iframe.html?categoryId=2&...` | `/newgdtcms//category/iframe.html?categoryId=2&...` |
| 详情页URL | `/sdny_bulletin/YYYY-MM-DD/ID.html` | `/sdny_bulletin/YYYY-MM-DD/ID.html` |
| 详情页内容 | HTML文本 ✅ | **PDF** ❌ |
| requests访问 | 直接可访 ✅ | WAF拦截 ❌ |
| 浏览器session | 可用 | 可用 |

**关键区别**：国电投详情页是PDF（iframe src → PDF viewer → `/bidprocurement/datacenter-cebpubserver/.../openFileById?fileType=2&id=<uuid>`），需要下载PDF→OCR/文本提取，比浙能HTML提取复杂很多。

## 国家能源集团（国能e招）平台特征 (2026-06-24)

**首页公开，内容丰富**：`chnenergybidding.com.cn/bidweb/` 首页展示13条/类目，无需登录。
- 发现的**对口项目**：工控信息安全设备框架招标、控制系统升级+智能预警、生产数据采集设备
- 详情页URL模式：`/bidweb/001/001001/001001001/{YYYYMMDD}/{uuid}.html`
- **主要障碍**：详情页通过SPA弹窗加载，URL含UUID（非自增ID），直接构造URL困难；Chromium headless返回空页

## 大唐集团平台特征 (2026-06-24)
- 主页 `cdt-ec.com/home/` 公开显示部分采购公告
- 搜索功能需要登录（搜索关键词即跳转登录页）
- 公告类型混杂：计划公示、招标、非招标、竞拍等

## 浙能集团适配器 — 关键技术突破 (2026-06-24)

**问题**：主页 `bulletinListNew.html` GET 返回只有导航框架，无公告链接。
**根因**：公告列表在 `<iframe>` 内动态加载，requests 拿不到 iframe 内容。
**突破**：浏览器 DevTools 捕获 iframe 实际 `src`：
```
https://zsrm.zjenergy.com.cn/zjnycms//category/iframe.html?dates=300&categoryId=2&tenderMethod=01&page={page}
```

直接 GET 此URL → 拿到完整HTML列表（10条/页 × 798页 = 7978条）。

**详情页URL模式**：`/sdny_bulletin/YYYY-MM-DD/ID.html`
- 招标公告：`/sdny_bulletin/2026-06-23/232643.html`
- 中标候选人：`/sdny_zbhxrgs/YYYY-MM-DD/ID.html`
- 变更公告：`/sdny_bggg/YYYY-MM-DD/ID.html`

**详情页内容**：requests 直取，结构化文本（2348 chars），含招标人/日期/编号/招标内容。无JS障碍。

## 适配器开发优先级 (2026-06-24 更新)

### Tier 1 — 已适配，持续产出
- ✅ 浙能集团 — **41条入库 (2个100分项目)**
- ✅ 南方电网 — 7条招标 + 3条中标
- ✅ 华润守正 — 稳定产出

### Tier 2 — 近期攻克（有对口项目迹象）
- 🔥 国家能源 — 首页有工控安全/智能预警/数据采集项目，需解决UUID详情页
- ⚠️ 国电投 — 同浙能平台但PDF详情页，需PDF提取管道
- ⚠️ 中广核/中核 — JS渲染适配

### Tier 3 — 需特殊方案
- ❌ 大唐 — 搜索需登录，公开页仅展示少量公告
- ❌ 国网ECP — 需浏览器自动化+登录
- ❌ 华能/华电 — 需VPN或代理
- ❌ 中节能 — 403 WAF需Chromium绕过

## 适配器模式

### 通用步骤
1. **获取列表页HTML**：优先 `requests.get()`，失败用 `chromium_render()`
2. **提取详情链接**：正则匹配 `<a href="..">`，过滤登录/列表/首页
3. **抓取详情页**：requests获取HTML
4. **结构化提取**：正则提取标题/招标人/日期/金额/正文
5. **评分入库**：`score_items()` → `INSERT INTO bidding_notices`

### 南网适配器示例（最高效）
```python
def crawl_nanwang(max_items=30):
    categories = {'zbgg': '招标公告', 'fzbgg': '非招标公告', ...}
    for cat_key, (list_url, cat_name) in categories.items():
        html = fetch(list_url)
        for m in re.finditer(r'href=["\'](/' + cat_key + r'/\d+\.jhtml)', html):
            detail = fetch(urljoin(base, m.group(1)))
            text = extract_text(detail)
            owner = re.search(r'采购人[：:]\s*(.+?)\n', text)
            date = re.search(r'发布时间[：:]\s*(\d{4}-\d{2}-\d{2})', text)
            items.append({...})
```

### 浙能 iframe 模式（攻克隐藏数据源）
```python
# 关键：直接访问iframe src，而非主页URL
list_url = f"{BASE}/zjnycms//category/iframe.html?dates=300&categoryId=2&tenderMethod=01&page={page}"
html = fetch(list_url)  # 10条/页，requests直取
detail_urls = re.findall(r'(/sdny_\w+/\d{4}-\d{2}-\d{2}/\d+\.html)', html)
for rel in detail_urls:
    detail = fetch(urljoin(BASE, rel))
    text = extract_text(detail)
    ...
```

### 为什么通用爬虫不行
- 通用提取拿到链接太杂（导航页/通知/新闻）
- 详情页文本提取质量差（混入大量导航文本）
- 评分后噪声率99%+（87站几百条只入库1条）
- **专属适配器噪声率~30%**（南网30条入库9条）
