# 中广核电子商务平台 API 逆向记录

**日期：** 2026-06-24
**平台：** https://ecp.cgnpc.com.cn/
**类型：** 纯 JS-SPA（React/Vue）

## 关键 JS 文件

| 文件 | URL | 大小 | 作用 |
|:--|:--|:--|:--|
| site.js | `https://ecp.cgnpc.com.cn/site.js` | 176KB | 主逻辑，含 detail URL 构造 |
| render.3.0.min.js | `https://ecp.cgnpc.com.cn/js/render.3.0.min.js` | 116KB | 渲染引擎，含 API 定义 |
| env.network.js | `https://nep.gnpjvc.cgnpc.com.cn/env.network.js` | - | CDN 环境配置（DNS 不可解析） |

## API 端点发现

### 核心发现：apiPrefix 为空字符串

在 `render.3.0.min.js` 中发现：
```javascript
apiPrefix: ""  // 空字符串！
```

这意味着所有 API 直接挂在当前域名下，无需前缀。

### 已确认的 API 端点

| 端点 | 方法 | 用途 | 状态 |
|:--|:--|:--|:--|
| `/portalApi/content/queryPage` | POST | 分页查询公告列表 | ✅ 200 (需正确参数) |
| `/portalApi/content/detail` | POST | 获取公告详情 | 待验证 |
| `/portalApi/content/saveContent` | POST | 保存内容 | - |
| `/portalApi/connect/query?siteId=` | GET | 站点连接查询 | - |
| `/portalApi/virtualContentStoreData/get?Id=` | GET | 虚拟内容存储 | - |

### 详情页 URL 构造

从 `site.js` 中发现：
```javascript
vDataUrl = vDataUrl + '?dataId=' + vItem.ContentStoreId + '&detailId=' + vItem.Id;
```

浏览器可见的详情页 URL 格式：
```
https://ecp.cgnpc.com.cn/Details.html?dataId={ContentStoreId}&detailId={Id}
```

### queryPage 尝试记录

```
POST /portalApi/content/queryPage
Content-Type: application/json

{"pageNum": 1, "pageSize": 20}
→ 200 OK, 12B (空响应，缺少必要参数)

GET /portalApi/content/queryPage?pageNum=1&pageSize=10
→ 200 OK, {"Code":7,"Message":"Request method 'GET' not supported"}
```

**待解决：** queryPage 需要的完整请求体参数格式（疑似需要 `SiteId`、`classifyId` 或 `ContentStoreId`）。

## 备选方案

1. **Chromium 长超时渲染**：主页 279KB 包含【】格式的项目标题，可用 `virtual-time-budget=35000` 渲染详情页（慢但可行）
2. **浏览器交互**：用 Puppeteer/Playwright 在浏览器中等待 AJAX 完成后再提取 DOM
3. **直接调 API**：逆向 queryPage 的参数格式后批量请求
