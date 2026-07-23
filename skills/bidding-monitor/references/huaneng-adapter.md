# 华能集团适配器 — 搜索聚合模式

## 背景

`ec.chng.com.cn`（华能电子商务平台）全站部署阿里云 WAF（Aliyun WAF），所有请求返回 JS Challenge：
- curl → 412 Precondition Failed
- Chromium `--dump-dom` → 40 bytes 空页面
- 真实浏览器 → 也需通过指纹检测+ AES 解密

## 绕行方案

### 第1选择：dlzb.com 聚合平台

`https://www.dlzb.com/huaneng/` — 华能专区，13,886 条公告。

**优势：**
- 浏览器渲染后公开可访问（不需登录）
- 每条有标题+链接+日期+标签
- 覆盖全部六大六小+两网（同一套 URL 模式：`/huaneng/`, `/huadian/`, `/datang/` 等）

**限制：** 阿里云 WAF 保护，curl/requests 不可达，需浏览器渲染

### 第2选择：搜索引擎反向索引

Yahoo/DDG 搜索可索引 WAF 后的 ec.chng.com.cn 页面。

已验证命中案例：
- "华能甘肃公司正宁2×1000兆瓦调峰煤电项目智慧电厂建设项目招标公告"
- "华能内蒙古东部能源有限公司5G智慧供热管家应用服务项目"
- "华能信息技术有限公司品牌管理平台建设项目设备招标公告"

### 第3选择：Bing 搜索（独立模式兜底）

质量较差但服务器可直接访问。

## 适配器架构

`scripts/adapter_huaneng.py`

```
crawl_huaneng(max_items=30)
  ├── 第1步：chng.toobiao.com 列表页抓取
  │   ├── _fetch_list_page() → requests
  │   ├── _parse_list_titles() → 正则提取标题+链接
  │   └── 关键词过滤（DIGITAL_KEYWORDS / EXCLUDE_KEYWORDS）
  ├── 第2步：纯文本解析兜底
  │   └── _extract_from_plaintext() → 正则匹配公告模式
  └── 第3步：搜索聚合兜底
      ├── Hermes模式: hermes_tools.web_search (Yahoo)
      └── 独立模式: _search_standalone() → cn.bing.com
```

## 关键词库

### 数字业务关键词（保留）
`数字化 智能化 智慧 软件 平台 系统 信息 数据 AI 人工智能 大模型 网络安全 安防 监控 物联网 传感器 数字孪生 BIM 数智 计算机 服务器 网络设备 云 5G`

### 硬件排除词（40+）
`螺栓 阀门 管件 焊接 保温 防腐 油漆 混凝土 钢筋 脚手架 电缆 开关柜 变压器 断路器 泵 压缩机 换热器 冷却塔 电梯 起重 物业 保洁 绿化 食堂 汽车 煤 燃油 劳务分包 土建 装修 船租赁 等`

## 双模式搜索注入

```python
# Hermes 模式 (crawl_pipeline.py 内)
try:
    import adapter_huaneng
    from hermes_tools import web_search
    adapter_huaneng._search_fn = web_search
except ImportError:
    pass  # 适配器自动回退到 _search_standalone()

# 独立模式 (systemd timer)
# 适配器检测到 _search_fn 为空 → 自动使用 _search_standalone() (Bing)
```

## 接入管线

`crawl_pipeline.py` 阶段11，在申能之后运行：

```python
hn_items = crawl_huaneng(max_items=20)
# → 适配器内已评分过滤 (≥55分)
# → insert_notice() 入库
```

## 后续扩展

dlzb.com 同一套模式可覆盖全部平台，只需替换 URL：
- 华电 → `https://www.dlzb.com/huadian/`
- 大唐 → `https://www.dlzb.com/datang/`
- 国电投 → `https://www.dlzb.com/guodianta/`
- 国网 → `https://www.dlzb.com/guowang/`
- 南网 → `https://www.dlzb.com/nanwang/`
