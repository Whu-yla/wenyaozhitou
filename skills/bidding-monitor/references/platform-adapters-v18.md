# 六大六小+国网+南网 平台适配详情 (v18)

最后更新：2026-06-24

## 已适配平台

### 南方电网供应链统一平台
- 主页: `https://bidding.csg.cn/`
- 列表页: `/zbgg/index.jhtml` (招标) / `/zbgs/index.jhtml` (公示)
- 详情页: `https://bidding.csg.cn/zbgg/{id}.jhtml`
- 适配器: `dedicated_adapters.py` → `crawl_nanwang()`
- 产出: 5招标+3中标, 含94分数字化项目

### 华润守正电子招标平台
- 主页: `https://szecp.crc.com.cn/`
- 列表页: `/szecp/notice/noticeController/noticeListMore` (不同tab参数)
- 详情页: `/szecp/notice/noticeController/toNoticeDetail?noticeId=...`
- 适配器: `site_crawlers.py` → `crawl_huarun_szecp()`
- 产出: 2招标

### 浙能集团智慧供应链平台
- 主页: `https://zsrm.zjenergy.com.cn/zjnycms/category/bulletinListNew.html`
- **iframe数据源**: `https://zsrm.zjenergy.com.cn/zjnycms//category/iframe.html?dates=300&categoryId=2&tenderMethod=01&page={page}`
  - categoryId: 2=招标公告, 3=变更, 4=中标结果, 5=中标候选人
- 详情页: `https://zsrm.zjenergy.com.cn/sdny_bulletin/{YYYY-MM-DD}/{id}.html`
- 适配器: `adapter_zheneng.py`
- 产出: 41招标, 含2个100分项目(智能大坝/智能调控平台)
- 注意: categoryId=2 对应「招标公告」但实际内容可能是采购公告，需验证

### 国家能源集团国能e招 🆕
- 主页: `https://www.chnenergybidding.com.cn/bidweb/`
- 技术: JS-SPA, requests直接访问返回WAF拦截。**必须用Chromium headless**
- **Chromium命令**: `/snap/bin/chromium --headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage --virtual-time-budget=20000 --dump-dom https://www.chnenergybidding.com.cn/bidweb/`
- 列表提取: 从渲染后HTML用正则 `href=['\"]/bidweb/001/[^\"']*\.html` 提取详情链接，约339条
- 详情页: `https://www.chnenergybidding.com.cn/bidweb/001/001001/001001001/{YYYYMMDD}/{uuid}.html`
- 对口项目: 工控信息安全设备、控制系统智能预警、数智科技技术服务商、中间件软件框架
- 注意: 大量详情页是"终止公告"/"通知"/"计划公示"类，需从标题过滤

### 中广核电子商务平台 🆕
- 主页: `https://ecp.cgnpc.com.cn/`
- 技术: JS-SPA, requests直接访问无内容。**必须用Chromium headless**
- **Chromium命令**: `/snap/bin/chromium --headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage --virtual-time-budget=15000 --dump-dom https://ecp.cgnpc.com.cn/`
- 列表提取: 从渲染后HTML用正则提取 `Details.html?dataId=...&detailId=...` 链接，约134条
- 详情页: `https://ecp.cgnpc.com.cn/Details.html?dataId={uuid}&detailId={uuid}`
- 对口项目: 数字化业务服务、信息安全设备、智能化试验台、监测控制系统
- 页面大小: 279KB HTML (大量CSS/JS)，纯文本约7KB

## 待攻克平台

### 国电投电能e招采 (与浙能同平台)
- 主页: `https://ebid.espic.com.cn/sdny_bulletin/`
- iframe: `https://ebid.espic.com.cn/newgdtcms//category/iframe.html?dates=300&categoryId=2&tabName=招标公告&page={page}`
- 详情页: `https://ebid.espic.com.cn/sdny_bulletin/{YYYY-MM-DD}/{id}.html`
- **卡点**: 
  1. iframe需在父页面context下才能加载数据（直接访问只显示搜索框）
  2. 详情页为PDF（iframe内PDF.js viewer）：`/bidprocurement/datacenter-cebpubserver/cebpubserver/dataCeboubServerCommonController/openFileById?fileType=2&id={uuid}`
  3. requests直连iframe被WAF拦截（返回`WEB 应用防火墙` captcha页）
- 内容特征: 以硬件/设备采购为主(弯头法兰、减速机、橡胶板等)，低ROI

### 大唐电商门户
- 主页: `https://www.cdt-ec.com/home/`
- 首页显示少量公告(计划公示、询比采购等)
- **卡点**: 搜索功能和详情页全部走SSO认证 (`/tangyhtsso/bip/sso/auth`)
- 详情链接统一跳转到 `cweme.cn` 平台且id参数恒为1
- 有对口项目线索: 网络安全保障服务、态势感知平台扩容（仅在首页标题可见）

### 中核集团
- 主页: `https://www.cnncecp.com/`
- 状态: Chromium返回40B，完全不可达（可能需VPN/内网）

### 国投电力
- 主页: `https://www.sdicc.com.cn/`
- 状态: 188KB JS-rendered, 命中智慧/软件/平台/大模型等关键词，但无项目标题

### 三峡集团
- 主页: `https://eps.ctg.com.cn/`
- 状态: 48KB，命中数据/监控/计算机关键词

## Chromium 快速扫描法 🆕

对未知平台判断是否值得投入适配器：

```python
CHROMIUM = "/snap/bin/chromium"
ARGS = ["--headless=new","--no-sandbox","--disable-gpu",
        "--disable-dev-shm-usage","--virtual-time-budget=15000","--dump-dom"]

KEYWORDS = ['数字化','智能化','智慧','软件','平台','系统开发','AI','人工智能',
            '大模型','信息','数据','网络安全','安防','监控','执法记录',
            '数智','集成','信息化','计算机']

def quick_scan(url):
    r = subprocess.run([CHROMIUM]+ARGS+[url], capture_output=True, text=True, timeout=20)
    html = r.stdout
    if len(html) < 500: return None  # 不可达
    text = re.sub(r'<[^>]+>', ' ', html)
    hits = [kw for kw in KEYWORDS if kw in text]
    titles = re.findall(r'【(.+?)】', text)[:20]
    return {'size': len(html), 'keyword_hits': hits, 'titles': titles}
```

## 噪声处理 🆕

### 平台UI文本被误当公告
Chromium dump的HTML包含导航/菜单/header文本。SPA平台常见噪声:
- "欢迎来到XX平台 V1.0"
- "异议投诉" / "帮助中心" / "办理CA"  
- "政策法规" / "关于我们" / "注册 登录"
- "招标网 首页 公告信息..."
- "招标文件提前公示通知" / "招标计划发布通知"

**过滤方法**: 入库后 `DELETE FROM bidding_notices WHERE title LIKE '%首页%' OR title LIKE '招标网%'`
**预防方法**: 适配器标题提取时排除 `title.startswith('招标网') or title.startswith('国能e招') or '首页' in title[:20]`

### 终止公告噪声
国家能源等平台首页大量显示"终止公告"，适配器捕获为公告。需在评分前过滤: `if '终止公告' in title: skip`
