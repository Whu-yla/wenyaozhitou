---
name: power-platform-adapters
description: 电力集团招标平台适配器编写工作流。覆盖六大六小发电集团+国网南网+浙能等平台的分析、DOM逆向、适配器编写与测试的完整流程。
category: bidding
---

# 电力集团招标平台适配器编写工作流

## ⚡ 工作原则
- **并行优先：** 多平台同时攻（后台 Chromium 跑一个、浏览器探一个、curl 扫一个）
- **先跑再优化：** 不要逐个平台手动分析→编码→测试的串行流程；快速扫描→批量适配器→后台跑→清洗
- **尽早入库：** 能拿到标题就先入库评分，详情内容可以后续补充

## 触发条件
当需要为以下类型平台编写数据抓取适配器时加载本 skill：
- 六大发电集团（华能、华电、大唐、国电投、国家能源、三峡）
- 六小发电集团（中广核、华润电力、国投电力、中核、中节能、中国电建）
- 电网公司（国网、南网）
- 地方能源（浙能、深圳能源、内蒙古电力等）

## 平台分类与策略

### 类型 A：电能e招采系列（同平台软件）
**识别特征：** iframe 加载公告列表，URL 模式 `/sdny_bulletin/{date}/{id}.html`
**已知平台：** 浙能、国电投

**适配器策略：**
1. 主页面 `{base}/sdny_bulletin/` 包含分类 iframe
2. iframe URL: `{base}/newgdtcms//category/iframe.html?dates=300&categoryId={id}&tabName={name}&page={n}`
3. 分类 ID: 2=招标公告, 3=变更/二次, 4=中标结果, 5=中标候选人
4. 从 iframe HTML 用正则提取 `/sdny_bulletin/{date}/{id}.html` 链接
5. 详情页获取：部分平台为 HTML（浙能），部分为 PDF（国电投）

**WAF 处理：**
- **国电投 iframe 被雷池 WAF (Safeline Bot Challenge) 全局保护** — 返回「WEB 应用防火墙」+ JS 挑战页面。requests 和 Chromium headless 均无法绕过。走 dlzb.com 兜底方案。
- 浙能可直接 requests（无 WAF）

### 类型 B：国家能源集团（国能e招）
**URL 模式：** `/bidweb/001/001001/001001001/{date}/{uuid}.html`
**特征：** 首页 JS 渲染公告列表，详情页公开可访问

**适配器策略：**
1. Chromium dump 首页获取所有详情链接
2. 链接提取正则：`/bidweb/001/[^"]+\.html`
3. 每个详情页用 Chromium 渲染后提取文本
4. 过滤规则：排除标题为"招标网 首页"/"招标计划"/"终止公告"/"招标文件公示"的噪声

### 类型 C：中广核电子商务平台
**URL 模式：** `/Details.html?dataId={uuid}&detailId={uuid}`
**特征：** 纯 JS-SPA，Chromium dump 可获取链接列表但详情页内容为空

**🆕 API 发现 (2026-06-24)：**
- 内容查询 API：`/portalApi/content/queryPage`（在 `js/render.3.0.min.js` 中发现）
- 详情通过 `detailId` 参数访问
- 主页 HTML 中无静态链接，全部通过 JS 模板 `${dataUrl + item.Id}` 动态加载
- **推荐方案：** 直接 HTTP POST 调用 `/portalApi/content/queryPage` 获取公告列表，绕过浏览器渲染

**适配器策略（浏览器方案，备用）：**
1. 浏览器导航至首页 `https://ecp.cgnpc.com.cn/`
2. 等待 JS 渲染完成
3. 用 JS 提取所有 `Details.html` 链接
4. 浏览器依次打开详情页
5. 等 iframe/内容加载后提取文本

### 类型 F：JSP + AJAX 动态加载（蒙西电网）✅ 已攻克

**平台名称**：内蒙古电力（集团）有限责任公司电子商务平台  
**URL**：`http://wzglb.impc.com.cn:82/`  
**WAF**：无 — 裸 JSP，curl 可访问  
**适配器**：`adapter_mengxi.py`

**访问路径**：www.impc.com.cn → 在线服务 → 采购供应 → 跳转至 wzglb.impc.com.cn:82

**适配器策略（已实现）**：
1. `requests.get` 首页 → 正则提取 `showProjectDetail(id)` / `showNewsDetail(id)` 所有公告 ID
2. 逐个拼接详情 URL：`showProjectDetail.jsp?id={id}` / `showNewsDetail.jsp?id={id}`
3. `requests.get` 详情页 → 解析文本提取标题/日期/内容
4. 评分过滤后入库

**关键修复**：
- 列表截取 `[:60]` 会漏掉靠后的数字化项目 → 改为 `[:100]`
- 详情页导航文本会污染标题 → `parse_detail()` 增加噪音清洗
- 门槛从 55 → 50（适配"云平台四期建设"等信息化项目，得分偏低但业务对口）

### 类型 G：验证码弹窗 SPA（UI可见但数据锁死）
**识别特征：** 浏览器渲染出完整页面 chrome（导航栏/分类标签/按钮可见），但公告列表始终为空
**已知平台：** 中石油 cnpcbidding.com、ctbpsp.com

**特征：**
- Vue/React SPA 应用的 UI shell 不依赖数据 API 即可渲染
- 数据接口独立要求验证码（弹窗/滑块/拼图）
- `browser_snapshot` 可见「招标公告」「资格预审公告」等按钮
- `browser_console` 执行 `document.querySelectorAll('a[href]')` 返回 0
- **关键症状**：linkCount=0 但页面结构完整 → 验证码锁，非渲染超时

**不可攻破（当前环境）：**
- 中石油：弹窗提交需人工输入验证码
- ctbpsp.com：滑块拼图需真实鼠标轨迹
- 搜索引擎索引也被上述平台屏蔽

### 类型 E：阿里云 WAF JS 挑战（商业级反爬）
**识别特征：** 所有请求（curl/browser/API）返回 `<textarea id="renderData">` + 阿里云 WAF meta 标签 `aliyun_waf_aa`
**已知平台：** 华能 ec.chng.com.cn、电力招标网 dlzb.com

**特征：**
- 响应 HTML 为 `<body></body>` 空壳，仅含 `<script name="aliyunwaf_6a6f5ea8">` 和加密 `<textarea>`
- 175KB 混淆 JS 执行指纹检测 + AES 解密后才渲染真实页面
- 所有子路径（robots.txt/sitemap/API）均被 WAF 拦截
- Chromium `--dump-dom` 返回 40 bytes 空页面
- 仅真实浏览器（含 ad blocker 例外）能通过挑战

**绕行策略（按优先级）：**
1. **第三方聚合站**：dlzb.com、toobiao.com、北极星电力网(bjx.com.cn) 等转载招标公告
2. **搜索引擎反向索引**：Yahoo/DDG 可索引 WAF 后的页面，用 `web_search` 提取标题+摘要
3. **浏览器实时渲染**：Hermes browser_navigate 可过 JS 挑战，但 systemd timer 独立模式不可用

**华能适配器实现（adapter_huaneng.py）：**
- 双模式：Hermes 内注入 `hermes_tools.web_search` / 独立模式 Bing 搜索兜底
- 关键词过滤：8 组搜索词覆盖数字化/智慧/平台/安防/AI 等
- 排除词库：40+ 硬件采购词（螺栓/阀门/管件/电缆等）快速过滤
- 兜底降级链：dlzb.com 列表页 → 纯文本解析 → 搜索聚合
- 已接入 crawl_pipeline.py 阶段11

### 🔑 dlzb.com — 一站式电力招标聚合平台

**URL 模式：** `https://www.dlzb.com/{company}/`（如 `/huaneng/`, `/huadian/`, `/datang/` 等）
**数据量：** 华能专区 13,886 条/604 页，全站 13,769,892 条
**覆盖范围：** 国电投/华能/华电/国家能源/大唐/国网/南网/核电/电建/能建/国投/晋能/京能/粤电/华润/煤矿/中铁/中交/铁塔通信/国家管网/五矿

**页面结构（浏览器渲染后）：**
- 面包屑：首页 » 招标公告 » {公司名}
- 列表项含：标题 `<a>` 链接、标签、日期 (YYYY-MM-DD)、收藏按钮
- 详情页需登录（银牌以上会员），但列表页公开可访问
- 每项有 `/d-zb-XXXXXXXX.html` 格式详情链接

**限制：** 全站阿里云 WAF，curl 不可达，需浏览器渲染。systemd timer 独立模式无法直接抓取，必须依赖搜索聚合兜底。

## Chromium 工具链

### 基本用法
```python
CHROMIUM = "/snap/bin/chromium"
ARGS = [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--virtual-time-budget=20000",  # JS 渲染等待时间 (ms)
    "--dump-dom"
]

def chromium_fetch(url, timeout=30):
    r = subprocess.run([CHROMIUM] + ARGS + [url],
                       capture_output=True, text=True, timeout=timeout)
    return r.stdout if r.returncode == 0 and len(r.stdout) > 500 else None
```

### ⚠️ 超时调参（关键！）
JS-SPA 平台需要**大幅提高**超时参数，否则 `--dump-dom` 只能抓到空壳页面：

| 平台类型 | virtual-time-budget | 总超时 | 说明 |
|:--|:--|:--|:--|
| 普通 HTML（浙能、华润守正） | 15,000ms | 20s | 默认即可 |
| 混合渲染（国家能源） | 20,000ms | 30s | 首页 JS 渲染链接 |
| **纯 JS-SPA（中广核）** | **35,000ms** | **50s** | 全 AJAX 加载，需长等待 |
| 纯 JS-SPA（华能） | 40,000ms+ | 60s+ | 即使长超时也可能 0 中文文本 |
| **dlzb.com（阿里云WAF）** | **30,000ms** | **60s** | 需加 `--disable-blink-features=AutomationControlled` 绕过反自动化检测 |

### 🛡️ Chromium 绕过阿里云 WAF 的关键参数

dlzb.com 使用阿里云 WAF（JS 挑战），普通 Chromium `--dump-dom` 返回 40 字节空壳。
**必须加 `--disable-blink-features=AutomationControlled`** 才能伪装成真实浏览器：

```python
CHROMIUM = "/snap/bin/chromium"
ARGS = [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",  # ← 核心！绕过反自动化检测
    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "--virtual-time-budget=30000",
    "--dump-dom",
]
```

**验证方法**：渲染后 HTML > 100KB 且不含 `aliyun_waf` 字符串即成功。
**限制**：systemd timer 独立模式可使用 Chromium headless；subprocess timeout 设为 60s 足够。

### 🔑 dlzb.com 公司路径速查表

| 公司 | dlzb.com 路径 | 验证状态 |
|:--|:--|:--|
| 华能集团 | `/huaneng/` | ✅ 13,886条 |
| 华电集团 | `/huadian/` | ✅ 有数据 |
| 大唐集团 | `/datang/` | ✅ 有数据 |
| 国家电投 | `/guodianta/` | ✅ 200 OK |
| 国家能源集团 | `/guojianengyuan/` | ✅ 有数据(较少) |
| 南方电网 | `/nanwang/` | ✅ 有数据(较少) |
| 华润电力 | `/huarun/` | ✅ 200 OK |
| 国网 | `/guowang/` | 待验证 |
| 三峡集团 | `/sanxia/` | 待验证 |

### 🆕 南网中标公告 HTML 表格提取

**问题**：南网中标公告详情页用 `<table>` 展示中标人（序号|标的|标包|中标人），纯文本正则 `中标人：xxx` 完全匹配不到。部分页面表头为「成交人」而非「中标人」。

**解决方案**：BeautifulSoup 跨行表格提取（`dedicated_adapters.py` 已实现）：

```python
soup = BeautifulSoup(detail_html, 'html.parser')
for table in soup.find_all('table'):
    rows = table.find_all('tr')
    # 找表头行定位列索引
    col_idx = -1
    for row in rows:
        cells = row.find_all(['td', 'th'])
        for i, cell in enumerate(cells):
            ct = cell.get_text(strip=True)
            if '中标人' in ct or '成交人' in ct or '成交供应商' in ct:
                col_idx = i
                break
        if col_idx >= 0: break
    # 从数据行提取同列值
    if col_idx >= 0:
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) > col_idx:
                val = cells[col_idx].get_text(strip=True)
                if val and '中标人' not in val and '序号' not in val and len(val) >= 2:
                    winner = val[:80]
                    break
```

**覆盖关键词**：`中标人/成交人/成交供应商/中标单位/供应商名称`  
**金额**：南网公开页面不含中标金额（需登录或下载 PDF），该平台金额字段始终为空。

### 陷阱 0: score_item 返回字段名是 `relevance_score` 非 `final_score`

**症状**：评分引擎明明算出了 57 分，但适配器 `sc.get('final_score', 0)` 总是 0。

**根因**：`relevance_scorer.score_item()` 返回 dict 的评分字段是 `relevance_score`，不是 `final_score`。

```python
# ❌ 始终返回 0
sc = score_item(item)
if sc and sc.get('final_score', 0) >= 55:  # 永远不会 ≥55

# ✅ 正确
if sc and sc.get('relevance_score', 0) >= 55:
```

**影响范围**：adapter_dlzb.py / adapter_huaneng.py / crawl_pipeline.py 中所有评分调用。
**同理**：`score_item()` 接受单个 dict 参数，不是 `(title, content)` 两个参数。

### JS-SPA 诊断方法
判断 Chromium dump-dom 是否对某平台有效：
```python
# 渲染后检查实际中文文本量
text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', text)
cn_fragments = re.findall(r'[\u4e00-\u9fff]{5,}', text)
print(f"中文片段数: {len(cn_fragments)}")

if len(cn_fragments) == 0:
    # 纯 JS-SPA，dump-dom 无效 → 需要浏览器交互或直接调 API
```
- 中广核：主页有中文文本（项目标题在 JS 模板外可见），但详情页需更长超时
- **华能**：0 个中文片段 → dump-dom 完全无效，必须浏览器实时交互
- **🆕 中石油 (cnpcbidding.com)**：浏览器渲染出完整页面结构（导航栏/分类标签可见），但 0 条公告链接 → **验证码弹窗阻塞 API**。Vue SPA 渲染 UI chrome 不依赖数据 API，而数据接口独立要求验证码。症状：`browser_snapshot` 显示「招标公告」「资格预审公告」等按钮，但 `browser_console` 执行后 `linkCount=0` 且页面有验证码弹窗 → 此为验证码锁，非超时或 JS 渲染问题。**不可误判为「页面已渲染=数据可达」**

## 文本提取

```python
from bs4 import BeautifulSoup
import re

def extract_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    for t in soup(['script','style','nav','footer','header','link','meta']):
        t.decompose()
    return re.sub(r'\s+',' ',soup.get_text()).strip()
```

## 标题提取优先级

1. `<h1>` 标签内容
2. 正则 `(?:招标|采购|中标|资格预审|询价|竞谈|竞争性)[^\n]{10,200}`
3. 文本首句（截断至 `。`）

## 噪声过滤规则

```python
NOISE_PATTERNS = [
    "平台 UI 名称开头（如"招标网 "、"国能e招 "）",
    "包含"首页"/"变更公告 暂无"",
    "包含"终止公告"",
    "包含"招标计划"/"招标文件提前公示"",
    "通知/收费/指引/注册/办理类",
]
```

## 已知平台适配状态 (V1.36)

| 平台 | 类型 | 状态 | 入库 | 说明 |
|:--|:--|:--|:--|:--|
| 南方电网 | 自有API | ✅ 已接入管线 | ~39 | dedicated_adapters.crawl_nanwang(max_items=30) |
| 浙能集团 | A-HTML | ✅ 已接入管线 | 41 | adapter_zheneng |
| 华润守正 | 自有 | ✅ 已接入管线 | 2 | site_crawlers.crawl_huarun_szecp |
| 国家能源 | B-Chromium | ✅ 已接入管线 | 48 | adapter_guoneng — 首页 Chromium dump 提取链接 |
| 能建 | 自有 | ✅ 已接入管线 | 13+ | dedicated_adapters.crawl_nengjian 🆕 |
| 三峡 | 自有 | ✅ 已接入管线 | 1 | dedicated_adapters.crawl_sanxia 🆕 |
| 申能 | 自有 | ✅ 已接入管线 | 5 | adapter_supplement.crawl_shenneng 🆕 |
| **蒙西电网** | **F-JSP直连** | **✅ 已接入管线** | **0+** | `adapter_mengxi.py` + 管线阶段10.5 — curl直连 wzglb.impc.com.cn:82。⚠️ 平台确诊：100% 电力设备/基建工程采购（变电站、ONU、接地变保护、技改设备），无一件数字化/IT项目。适配器无代码 bug，评分全拒属平台特性。仅「云平台四期建设」1 条特例（历史入库） |
| **深圳能源** | **Chromium** | **✅ 已接入管线** | **5+** | `chromium_crawler.py` — zb.sec.com.cn。V1.38 修复：`extract_detail_links()` 过滤 `/index*\.\w+$` 导航页 + `fetch_detail_text()` 提取 `.Content` div + `<h1>` 标题 + `@\S+@` 模板清理。鸿蒙智能楼宇 65 分入库。JS_TARGETS 覆盖招标+结果公告双链路 |
| 江苏平台 | 自有 | ✅ 已接入管线 | 0(无匹配) | dedicated_adapters.crawl_js_platforms 🆕 |
| 国电投 | A-雷池WAF | 🔴 雷池WAF封锁 → dlzb兜底 | 0 | 同浙能电能e招采，但雷池WAF封iframe |
| 中广核 | C-JS-SPA | 🟡 需浏览器/API | 2 | ecp.cgnpc.com.cn，API `/portalApi/content/queryPage` 已发现 |
| 大唐 | D | 🔒 SSO | 0 | 全部详情走SSO认证 |
| 国网 | - | 🔒 登录 | 0 | 需登录 |
| 华能 | E-阿里云WAF | 🟢 dlzb兜底 | 有产出 | `adapter_dlzb.py` Chromium破WAF |
| 华电 | E-阿里云WAF | 🟢 dlzb兜底 | 有产出 | 同上 |
| **中石油** | **E-验证码** | **🔴 验证码弹窗** | 0 | cnpcbidding.com — Vue SPA，浏览器可渲染但数据接口被验证码锁死 |
| **中石化** | **网络不可达** | **🔴 CDP超时** | 0 | bidding.sinopec.com — ECS网段连不上，疑似供应商白名单 |
| **中海油** | **C-JS空壳** | **🔴 193B JS壳** | 0 | buy.cnooc.com.cn — 纯前端渲染无静态HTML |
| **ctbpsp** | **聚合平台** | **🔴 滑块验证码** | 0 | 搜索即触发拼图验证，全站不可用 |
| 中国中化/中国化学/延长石油/恒力/万华 | - | ❌ 不可达 | 0 | 超时或企业官网非招标平台 |
| 🔴 ctbpsp聚合 | - | 🔴 滑块验证码 | 0 | 中国招标投标公共服务平台，搜索即触发拼图验证码，全站不可用 |
| **蒙西电网** | **F-JSP-AJAX** | **✅ 直连适配器** | **1** | `adapter_mengxi.py` — curl直连 wzglb.impc.com.cn:82，解析 showProjectDetail/showNewsDetail ID，云平台四期52分入库 |
| 中国中化/中国化学/延长石油/恒力/万华 | - | ❌ 不可达 | 0 | 超时或企业官网非招标平台 |

## 快速扫描命令

对未知平台快速判断是否值得深入：

```python
import subprocess, re

C = "/snap/bin/chromium"
A = ["--headless=new","--no-sandbox","--disable-gpu",
     "--disable-dev-shm-usage","--virtual-time-budget=15000","--dump-dom"]

KEYWORDS = ['数字化','智能化','智慧','软件','平台','系统开发','AI','人工智能',
            '大模型','信息','数据','网络安全','安防','监控','数智','计算机']

def quick_scan(name, url):
    r = subprocess.run([C]+A+[url], capture_output=True, text=True, timeout=25)
    size = len(r.stdout)
    if size < 500: return f"❌ {name}: 无内容 ({size}B)"
    
    text = re.sub(r'<script[^>]*>.*?</script>', '', r.stdout, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    cn = len(re.findall(r'[\u4e00-\u9fff]{5,}', text))
    hits = [kw for kw in KEYWORDS if kw in text]
    
    if cn == 0:
        return f"🔴 {name}: 纯JS壳(0中文) → 需浏览器方案"
    if not hits:
        return f"⚪ {name}: {size}B, 无数字关键词"
    
    titles = re.findall(r'【(.+?)】', text)[:10]
    urls = len(re.findall(r'href\s*=\s*["\']([^"\']*(?:detail|notice|bulletin|bid|tender)[^"\']*)["\']', r.stdout))
    
    lines = [f"🟢 {name}: {size}B, 命中{len(hits)}词: {hits[:5]}"]
    for t in titles[:3]: lines.append(f"    📋 {t[:100]}")
    if urls: lines.append(f"    🔗 {urls}公告链接")
    return '\n'.join(lines)
```

## JS-SPA 诊断模板

```python
# 判断 dump-dom 是否有效
text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', text)
cn = re.findall(r'[\u4e00-\u9fff]{5,}', text)

if len(cn) == 0:
    decision = "纯JS-SPA → dump-dom无效 → 浏览器方案"
elif len(cn) < 10:
    decision = "极少中文文本 → 尝试延长超时到35s+"
else:
    decision = f"有{len(cn)}中文片段 → 可正则提取标题"
```

统一管线脚本：`scripts/crawl_pipeline.py` — 11路适配器 (V1.37, 两段式架构)

```python
# ── 直连适配器（高质量，有正文/金额/日期） ──
from site_crawlers import crawl_huarun_szecp, crawl_hubei_ggzy   # 华润守正 + 湖北
from dedicated_adapters import crawl_nanwang        # 南方电网
from dedicated_adapters import crawl_nengjian        # 能建
from dedicated_adapters import crawl_sanxia          # 三峡
from dedicated_adapters import crawl_js_platforms    # 江苏平台
from adapter_zheneng import crawl_zheneng            # 浙能集团
from adapter_guoneng import crawl_guoneng            # 国家能源(Chromium)
from adapter_supplement import crawl_shenneng        # 申能

# ── dlzb.com 兜底适配器（WAF封锁平台走电力招标网聚合） ──
from adapter_dlzb import crawl_all as crawl_all_dlzb # 华能/华电/大唐/国电投/国投/中核/中节能/中广核/国网

from relevance_scorer import score_items
```

管线顺序：华润守正 → 湖北省平台 → 南方电网 → 浙能 → 国家能源 → ~~国电投(跳过)~~ → 能建 → 三峡 → 江苏 → 申能 → **dlzb兜底9平台**

**两段式架构原则**：直连适配器优先（数据质量高），WAF/SSO封锁平台走 dlzb.com Chromium 聚合（仅标题级数据）。dlzb 已去重——有直连的平台（南网/浙能/华润/三峡/申能/能建/国家能源）不在 dlzb 中重复抓取。

⛔ **crawl_nanwang 在 dedicated_adapters.py 不是 site_adapters.py！** 旧代码从 `site_adapters` 导入导致南网适配器从未运行。

每个适配器模块输出标准 dict 格式：
```python
{
    'title': str,        # 公告标题
    'content': str,      # 正文摘要 (≤1000字符)
    'source': str,       # 来源平台名
    'source_url': str,   # 详情页URL
    'notice_type': str,  # 'bidding' | 'winning'
    'publish_date': str, # YYYY-MM-DD
    'procurement_owner': str, # 采购单位
    'winner_company': str,    # 🆕 中标人（winning时必填）
    'winning_amount': str,    # 🆕 中标金额（winning时必填）
    'budget_amount': str,     # 🆕 预算/最高限价（bidding时必填）
    'raw_text': str,     # 原始全文
}
```

## 🆕 HTML 表格数据提取

**适用场景：** 中标公告页用 `<td>` 表格展示「中标人」「中标金额」等字段，关键词在表头行，值在下一行同列。

### 跨行表格提取函数

```python
def _extract_from_table(html, text, keyword):
    """从HTML表格中提取关键词对应的值（中标人/中标金额/最高限价等）
    支持跨行表格: 表头行含关键词 → 找到列位置 → 数据行读取同列值
    """
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')

    # 方案1: 先找表头行列位置
    col_idx = None
    for row in rows:
        cells = row.find_all(['td', 'th'])
        for i, cell in enumerate(cells):
            ct = cell.get_text(strip=True)
            if keyword in ct:
                col_idx = i
                break
        if col_idx is not None:
            break

    # 找到了列位置，扫描后续数据行
    if col_idx is not None:
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) > col_idx:
                val = cells[col_idx].get_text(strip=True)
                if val and keyword not in val and len(val) > 1:
                    val = re.sub(r'<[^>]+>', '', str(cells[col_idx])).strip()
                    return val[:200]

    # 方案2: 同行相邻 td（备用）
    for row in rows:
        cells = row.find_all(['td', 'th'])
        for i, cell in enumerate(cells):
            ct = cell.get_text(strip=True)
            if keyword in ct and i + 1 < len(cells):
                val = cells[i + 1].get_text(strip=True)
                if val and keyword not in val and len(val) > 1:
                    return re.sub(r'<[^>]+>', '', str(cells[i+1])).strip()[:200]
    return ''
```

**使用示例（adapter_guoneng.py）：**
```python
items.append({
    ...
    'winner_company': _extract_from_table(html, text, '中标人') if ntype == 'winning' else '',
    'winning_amount': _extract_from_table(html, text, '中标金额') if ntype == 'winning' else '',
    'budget_amount': _extract_from_table(html, text, '最高限价') if ntype == 'bidding' else '',
})
```

## 🆕 预算/最高限价提取（纯文本）

**适用场景：** 公告正文中包含"最高限价（万元）169.7909"等格式。

```python
def extract_budget_from_content(text):
    """从公告正文中提取预算/最高限价"""
    if not text: return ''
    patterns = [
        r'最高限价[（(]万元[）)](.*?)(\\d+\\.?\\d+)(?:/|\\s|$)',
        r'最高投标限价[：:]\\s*(\\d+\\.?\\d*)\\s*万',
        r'预算金额[：:]\\s*(\\d+\\.?\\d*)\\s*万',
        r'最高限价\\s*[：:]\\s*(\\d+\\.?\\d*)\\s*万',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            groups = m.groups()
            for g in groups:
                if re.match(r'^\\d+\\.?\\d*$', str(g)):
                    return str(g) + '万元'
    return ''
```

## ⛔ 管线静默停摆检测 (V1.36)

**症状**：用户质疑「数据相关性这么少？」→ 发现 `crawl_log` 完全为空，Hermes Cron 中无采集任务。

**定时采集是系统命脉**——管线停摆不会被主动发现（页面依然显示存量数据，企微推送无法区分新旧）。

**健康检查 SOP**：
1. `cronjob(action='list')` 确认采集任务存在
2. `sqlite3 bidding.db "SELECT COUNT(*) FROM crawl_log"` 确认日志在增长
3. 用户问「数据少」时第一步查管线状态而非改评分

**当前 Cron**：`ec61bb478859` — 每天 9:00/18:00 运行 `crawl_pipeline.py`（no_agent=true, profile=wenyaozhitou）

**适配器参数名不一致陷阱**：
- `crawl_nanwang(max_items=N)` 非 `max_pages`
- `crawl_guodianta(max_items=N)` 非 `max_pages`
- 运行前确认参数名匹配，否则 TypeError 崩管线

### 陷阱 0: chromium_crawler 索引页误抓 + .Content 正文提取（V1.38）

**症状**：`extract_detail_links()` 提取 19 个链接，全部是 `/zbggs/index.jhtml`、`/jggg/index.jhtml`、`/zbgg/index.jhtml` 等导航/索引页而非详情页。L1 判别器全部拒绝 → 0 条入库。

**根因**：
1. `extract_detail_links()` 只按 URL 路径关键词（zbgg/jggg）匹配，不区分索引页和详情页
2. `fetch_detail_text()` 用全页 soup 提取 → 门户导航混入正文 → L1 假阳性

**修复**：
```python
# extract_detail_links() — 过滤索引/导航页
if re.search(r'/index(?:[_\u4e00-\u9fff])?(?:_?\d+)?\.\w+$', full):
    continue

# fetch_detail_text() — 返回 (text, h1_title) 元组
content_div = soup.find('div', class_='Content')
if content_div:
    text = re.sub(r'\s+', ' ', content_div.get_text()).strip()

h1_tag = soup.find('h1')
h1_title = h1_tag.get_text(strip=True)[:200] if h1_tag else ''
return text, h1_title

# main() — h1 优先 + 模板清理
text, h1_title = fetch_detail_text(dl)
title = h1_title if h1_title else ''
title = re.sub(r'@\S+@', '', title).strip()
```

**验证**：深圳能源修复前 0/10 → 修复后 鸿蒙智能楼宇 65 分。详见 `wenyao-bidding/references/chromium-crawler-l1-guard-gap-v38.md`。

**根因**：关键词匹配 `any(kw in combined for kw in ['zbgg','jggg','cggg',...])` 太宽——索引页 URL 也含这些词。深圳能源详情页格式为 `/zbgg/20849.jhtml`（含数字ID），索引页为 `/zbggs/index.jhtml` 或 `/zbgg/index.jhtml`。

**修复**：在 `extract_detail_links()` 末尾加索引页过滤：
```python
# 过滤导航/索引页（如 /zbggs/index.jhtml /zbgg/index.jhtml）
if re.search(r'/index(?:[_\u4e00-\u9fff])?(?:_?\d+)?\.\w+$', full):
    continue
```

**提取正文**：`fetch_detail_text()` 优先从 `.Content` div 提取（深圳能源等平台），兜底全页 soup：
```python
content_div = soup.find('div', class_='Content')
if content_div:
    text = re.sub(r'\s+', ' ', content_div.get_text()).strip()
    return text[:3000] if len(text) > 80 else None
```

**标题清洁**：优先 `<h1>` 标签 + `re.sub(r'@\S+@', '', title)` 清理 CMS 模板占位符。

> 案例：深圳能源 zb.sec.com.cn，19 个导航链接全部变真实详情，鸿蒙智能楼宇 65 分入库。

### 陷阱 1: JS 平台诊断——确认非适配器bug（V1.38 蒙西）

**症状**：标题被截断为「招标公告浙江」而非完整标题。

**根因**：`.+?` 非贪婪模式 + 停止条件包含公司名常见片段：
```python
# ❌ 危险 — 停止条件中的「浙能」在司名中被命中
m = re.search(r'(?:招标公告)\\s*(.+?)'
              r'(?:\\s*招标公告|\\s*\\n|\\s*浙能)', text)
# 输入：「招标公告浙江浙能中煤舟山煤电有限责任公司…」
# 结果：.+? → "浙江"，停止于 "浙能" → 标题截断
```

**修复**：停止条件不能包含公司名常见片段（`浙能`、`华能`、`国网`、`南网`、`中电投`、`大唐`）。改用自然边界：
- 段落结束：`\\n\\n`、`\\n    `
- 固定短语：`已具备招标条件`、`项目所在地区`
- 直接匹配完整模式：「XX公司XXX招标公告」

```python
# ✅ 安全 — 匹配完整公告模式
m = re.search(r'((?:浙江|浙能|国家能源|华能|华电|大唐|国电|'
              r'中电投|南方电网|国网)\\S{0,80}'
              r'(?:招标公告|采购公告|中标候选人公示|中标结果公告))', text)
```

### 陷阱 3: Chromium extract_detail_links 抓取导航/索引页

**症状**：列表页 Chromium 渲染 → 发现 19 个「详情链接」→ 全部被 L1 拒绝（「欢迎来到XX平台」「设为首页」等）。实际公告列表有真实条目，但被导航链接抢满 10 槽位。

**根因**：`extract_detail_links()` 的通用正则匹配忽略了一个关键差异 — 平台列表页同时包含：
- 真实详情链接：`/zbgg/20849.jhtml`（含数字 ID）
- 导航/索引链接：`/zbggs/index.jhtml`、`/zbgg/index.jhtml`、`/jggg/index.jhtml`（不含 ID）

两者都命中 `zbgg`/`jggg` 关键词过滤，导航链接优先被提取。

**修复** — 在 `extract_detail_links()` 中新增索引页正则过滤：
```python
# 过滤导航/索引页（如 /zbggs/index.jhtml /zbgg/index.jhtml /zbggs/index_2.jhtml）
if re.search(r'/index(?:[_\u4e00-\u9fff])?(?:_?\d+)?\.\w+$', full):
    continue
```

**验证方法**：修复后提取的链接应全部为 `/zbgg/\d+\.jhtml` 或 `/jggg/\d+\.jhtml` 格式，无 `/index` 路径。

### 🆕 详情页内容提取：Content div + h1 标题

**适用场景**：平台详情页用 `<div class="Content">` 包裹正文、`<h1>` 承载标题（深圳能源、国家能源等）。

**模式**：
```python
soup = BeautifulSoup(html, 'html.parser')

# 标题：h1 优先
h1_tag = soup.find('h1')
title = h1_tag.get_text(strip=True)[:200] if h1_tag else ''

# 正文：优先 .Content div（避免门户导航污染）
content_div = soup.find('div', class_='Content')
if content_div:
    text = re.sub(r'\s+', ' ', content_div.get_text()).strip()
else:
    # 兜底全页
    for tag in soup(['script','style','nav','footer','header']):
        tag.decompose()
    text = re.sub(r'\s+', ' ', soup.get_text()).strip()

# 清理 CMS 模板占位符（如 @项目公告信息.项目名称@）
title = re.sub(r'@\S+@', '', title).strip()
```

**关键点**：
- `.Content` div 提取可避免门户导航文本混入正文导致 L1 假阳性
- `<h1>` 标题比正文首行更可靠（正文首行可能含模板占位符）
- `@\S+@` 清理覆盖 CMS 模板标记（深圳能源、蒙西等 JSP 平台常见）

> 完整 Chromium 通用爬虫陷阱 → `references/chromium-crawler-pitfalls.md`

**症状**：日期显示为平台当天日期（2026-06-26）而非公告落款（2026-06-24）。

**根因**：全文字段扫描 `\\d{4}年\\d{1,2}月\\d{1,2}日` 命中页面模板头部展示的「当前日期」，而非公告正文落款日期。正则无上下文约束 → 第一个日期获胜：
```python
# ❌ 危险 — 无上下文，命中平台模板日期
m = re.search(r'(\\d{4})年(\\d{1,2})月(\\d{1,2})日', text[:2000])
```

**修复**：日期提取必须有上下文锚点，按优先级递减：
```python
# ✅ 1. 优先 — 在公告落款附近找（靠近「招标人」「招标代理机构」）
m = re.search(r'(?:招标人|招标代理机构|采购人).{0,300}?'
              r'(\\d{4})年(\\d{1,2})月(\\d{1,2})日', text)
# 2. 兜底 — 第一个中文日期（正文内而非模板头）
# 3. 最后兜底 — URL 中的日期（/2026-06-25/）
```

### 设计原则（所有适配器适用）

| 原则 | 说明 |
|:--|:--|
| **停止条件不含公司名** | `浙能`/`华能`/`国网`/`南网` 常见于公司名中，不可用作正则停止边界 |
| **日期提取有上下文** | 全文找第一个日期 = 随机。优先在「招标人/采购人」附近匹配 |
| **URL 日期作兜底** | URL 中的日期通常比落款晚 1-2 天，比模板日期可靠 |
| **修复后必回填** | `UPDATE` 已入库的错误记录，不可只改代码不改数据 |

> 完整案例见 `wenyao-bidding` → `references/zheneng-adapter-regex-fix.md`
