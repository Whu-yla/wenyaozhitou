# 日报+反馈闭环系统 V1.5

## 架构

```
用户收藏⭐(前端) → app.js syncBookmarksToServer() → API:8090 → bookmarks.json
                                                                    ↓
用户点赞/点踩(日报页) → fetch /bidding/api/feedback → API:8090 → feedback.json
                                              ↓
                                    HOT_MEMORY.md (点踩理由直写)
                                              ↓
                                    下次会话 AI 自动感知 → 迭代评分关键词
```

## 组件

### 1. API 微服务 (`bookmark_server.py`)
- 端口：8090，Nginx 反向代理 `/bidding/api/` → `127.0.0.1:8090/`
- 路由：
  - `GET /` → 返回书签列表 `{"bookmarks": [...], "count": N}`
  - `POST /` → 保存书签 `{"bookmarks": [...]}` 
  - `GET /feedback` → 返回反馈列表
  - `POST /feedback` → 提交反馈 `{"item_id": "x", "type": "like|dislike", "reason": "...", "report_date": "...", "section": "bidding|winning"}`
- 点踩时自动写入 `HOT_MEMORY.md` 供 AI 感知
- Nginx 守护脚本监控进程存活，挂了自动 `nohup` 重启

### 2. 日报生成器 (`daily_report.py`)
- 读取 DB 今日招标/中标数据（`date(fetch_date)=today`）
- 读取 `data/bookmarks.json` 标记收藏项目
- 逐条 AI 分析：
  - 招标：招标人/内容/金额/相关度/建议（重点关注→暂不考虑）
  - 中标：中标人/招标单位/金额/竞品分析/收藏提醒/非中南院预警/大标💰
- 生成 HTML：双 Tab 滑动切换、每项一张卡片、点赞/点踩按钮
- 输出：`/var/www/html/bidding/report-YYYY-MM-DD.html`

### 3. 前端交互（日报页内嵌 JS）
- `switchTab('bidding'|'winning')` — Tab 切换
- `submitLike(itemId, section)` — 点赞
- `openDislike(itemId, section)` — 打开点踩弹框
- `submitDislike()` — 提交点踩理由（必填验证）
- localStorage `daily_feedback` 防重复提交
- 已提交状态回显（👍已点赞 / 👎已反馈）

### 4. 主站书签同步 (app.js v8)
- `syncBookmarksToServer(stars)` — toggleStar 后 300ms 防抖 POST
- `loadBookmarksFromServer()` — 初始化时 GET 服务端书签，合并本地+服务端
- 合并策略：`[...new Set([...local, ...server])]`

## 定时任务

| 时间 | Job ID | 模式 | 脚本 |
|:--|:--|:--|:--|
| 20:00 | `04bf3bdc6aa6` | no_agent | `push_daily_report.sh` |

## 企微 Nginx 配置

```nginx
location /bidding/api/ {
    proxy_pass http://127.0.0.1:8090/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    add_header Access-Control-Allow-Origin "*" always;
}
```

## 排坑

| 问题 | 修复 |
|:--|:--|
| 书签 localStorage 服务端不可见 | API 微服务 + app.js 双向同步 |
| 点踩无理由提交 | 前端 `submitDislike()` 校验 `reason.trim()` 非空 |
| 同一项目重复反馈 | API 按 `item_id + ip` 去重，返回 409 |
| bookmark_server 挂了无人知 | nginx_guard.sh 扩展 pgrep 检测 + 自动重启 |
| 日报数据量大（50+条） | `daily_report.py` LIMIT 50，卡片按相关性降序 |
