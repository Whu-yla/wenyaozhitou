# 全平台可达性探测矩阵 (2026-06-26)

## 探测方法
- curl -sI + HTTP GET 内容分析
- Chromium headless `--dump-dom --disable-blink-features=AutomationControlled`
- 浏览器导航交互

## 结果矩阵

### ✅ 直连可用（无WAF或WAF可破）
| 平台 | URL | 方式 | 数据量 |
|:--|:--|:--|:--|
| 华润守正 | szecp.crc.com.cn | curl | 丰富 |
| 南网 | bidding.csg.cn | curl API | 高 |
| 浙能 | zsrm.zjenergy.com.cn | curl iframe | 7978条 |
| 国家能源 | neep.shop/bidweb/ | Chromium | 48+ |
| 能建 | ec.ceec.net.cn | curl GBK | 13+ |
| 三峡 | eps.ctg.com.cn | curl | 少量 |
| 申能 | shenenergy.com.cn | curl | 5 |
| **蒙西电网** | **wzglb.impc.com.cn:82** | **curl** | **116条/首页** |
| **深圳能源** | **zb.sec.com.cn** | **curl** | **19条/首页 (9招标+10结果)** |

### 🔗 dlzb.com Chromium 兜底（原平台WAF/SSO封锁）
| 平台 | 原平台URL | 封锁类型 | dlzb路径 |
|:--|:--|:--|:--|
| 华能 | ec.chng.com.cn | 阿里云WAF 412 | /huaneng/ |
| 华电 | chdtp.com | 412 WAF | /huadian/ |
| 大唐 | cdt-ec.com | SSO | /datang/ |
| 国电投 | ebid.espic.com.cn | 雷池WAF iframe | /guodianta/ |
| 国网 | ecp.sgcc.com.cn | 登录锁死 | /guowang/ |
| 中广核 | ecp.cgnpc.com.cn | JS-SPA壳 | /zhongguanghe/ |
| 国投电力 | sdic.com.cn | 302重定向 | /guotou/ |
| 中核 | cnncecp.com | 302重定向 | /zhonghe/ |
| 中节能 | ebidding.cecep.cn | 超时 | /zhongjienen/ |

### ❌ 完全不可达 (6/26 复测)
| 平台 | URL | 6/26复测结果 |
|:--|:--|:--|
| 🔴 中石油 | cnpcbidding.com | **Vue SPA + 验证码弹窗** — 浏览器渲染成功但数据接口被验证码锁死，不提交=0条公告。搜索引擎屏蔽爬虫索引 |
| 🔴 中石化 | bidding.sinopec.com | **CDP 超时** — 浏览器无法建立连接，疑似供应商白名单/VPN准入。dlzb 无此板块(404) |
| 🔴 中海油 | buy.cnooc.com.cn | **193B JS空壳** — 纯前端渲染无静态HTML。dlzb 无此板块(404)。搜索引擎屏蔽爬虫 |
| 🔴 ctbpsp | ctbpsp.com | **滑块拼图验证码** — 搜索即触发，全站不可用 |
| 中国中化 | ec.sinochem.com | 超时不可达 |
| 中国化学工程 | cncecyc.com | 超时不可达 |
| 延长石油 | ecp.sxycpc.com | 超时不可达 |
| 恒力石化 | hengli.com | 企业官网，非招标平台 |
| 万华化学 | whchem.com | 企业官网，非招标平台 |

### dlzb.com 不覆盖的平台（404或假数据）
- 中石油(zhongshiyou): 404
- 中石化(zhongshihua): 404
- 中海油(zhonghaiyou): 404
- 蒙西(mengxi): 404
- 万华(wanhua): 404
- 中化(sinochem): 200但只有假数据
- 延长(yanchang): 同上
- 恒力(hengli): 同上

## 服务器网络限制
以下域名从阿里云ECS (yfzx.online) 无法访问（超时/网络不可达）：
- bidding.sinopec.com
- buy.cnooc.com.cn
- ec.sinochem.com
- cncecyc.com
- ecp.sxycpc.com
- mxdl.cn
- *.impc.com.cn 子域名（仅www和wzglb可访问）
