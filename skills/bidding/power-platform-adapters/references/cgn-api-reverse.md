# 中广核平台 API 逆向笔记

## 平台信息
- 域名: `ecp.cgnpc.com.cn`
- 类型: 纯 JS-SPA (Vue/React)
- Chromium dump-dom: 主页可渲染（279KB），**详情页内容为空**

## API 发现

### 核心接口
```
POST /portalApi/content/queryPage
```
- 来源：`js/render.3.0.min.js` 中 `portal.env.apiPrefix + '/portalApi/content/queryPage'`
- **apiPrefix 为空字符串**（在 render JS 中 `apiPrefix: ""`）
- 需要正确的 POST body 参数

### 详情 URL 模式
```
/Details.html?dataId={ContentStoreId}&detailId={Id}
```
- `dataId` 映射到 `ContentStoreId`
- `detailId` 映射到公告 `Id`

### 其他发现的端点
```
POST /portalApi/content/detail
POST /portalApi/connect/query?siteId={appId}
POST /portalApi/favorites/getFavoritesList
GET  /portalApi/top
GET  /portalApi/select
```

## 提取方案

### 方案 A：主页文本提取（当前可用）
Chromium 渲染主页 → 正则提取项目标题 → 评分入库
- 优点：无需详情页，速度快
- 缺点：只能拿标题，无法获取正文/金额/日期

### 方案 B：API 直攻（推荐，未完成）
需要逆向正确的 POST 参数格式。
已知关键参数：`pageSize`（默认15）、`SiteId`、`ContentStoreId`

### 方案 C：浏览器实时交互（最可靠但最慢）
Node.js Puppeteer/Playwright 自动化浏览器操作。

## 2026-06-24 成果
- 方案 A 成功：主页文本提取 2 条数字化/安防项目入库
- API 端点已确认存活（返回 200，但参数格式待逆向）
