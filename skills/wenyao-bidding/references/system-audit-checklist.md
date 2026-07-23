# 文鳐智投 系统全链路自检清单

## 触发条件
每次以下操作后必须执行：
- 评分引擎（relevance_scorer.py）改动
- 爬虫/适配器调整
- Nginx 配置变更
- 前端组件添加或修改
- 数据库结构变更
- 文件权限/路径调整

## 7 项必检清单

### 1. 语法校验
```bash
# Python
find scripts/ -name '*.py' -exec python3 -m py_compile {} \;
# Shell
find scripts/ -name '*.sh' -exec bash -n {} \;
```

### 2. 数据库完整性
```sql
-- 重复标题
SELECT title, COUNT(*) FROM bidding_notices WHERE relevance_score>0 GROUP BY title HAVING COUNT(*)>1;
-- 同URL重复（unique_hash bug）
SELECT url, COUNT(*) FROM bidding_notices WHERE relevance_score>0 GROUP BY url HAVING COUNT(*)>1;
-- 空字段
SELECT COUNT(*) FROM bidding_notices WHERE relevance_score>0 AND (title IS NULL OR url IS NULL);
-- <50分残骸
SELECT COUNT(*) FROM bidding_notices WHERE relevance_score>0 AND relevance_score<50;
-- 评分分布
SELECT CASE WHEN relevance_score>=90 THEN '90-100' WHEN relevance_score>=70 THEN '70-89' WHEN relevance_score>=50 THEN '50-69' ELSE '<50' END as band, COUNT(*) FROM bidding_notices WHERE relevance_score>0 GROUP BY band;
```

### 3. 数据质量 — 地域/招标单位垃圾检测
```sql
-- 地域字段含正文垃圾（regex 排除集缺「。」）
SELECT COUNT(*) FROM bidding_notices WHERE length(region)>15 OR region LIKE '%资格%' OR region LIKE '%方式%' OR region LIKE '%招标%';
-- 招标单位字段含联系人/电话碎片
SELECT COUNT(*) FROM bidding_notices WHERE length(procurement_owner)>40 OR procurement_owner LIKE '%联系人%' OR procurement_owner LIKE '%电话%';
-- 标题含平台导航前缀
SELECT COUNT(*) FROM bidding_notices WHERE title LIKE '采购公告 >%' OR title LIKE '招标公告 >%' OR title LIKE '成交公告 >%';
```

### 4. 平台首页垃圾过滤
```sql
-- 误抓的首页/导航页/欢迎页
SELECT COUNT(*) FROM bidding_notices WHERE title LIKE '%欢迎来到%' OR title LIKE '%欢迎使用%' OR title LIKE '%设为首页%' OR title LIKE '%收藏此页%' OR title LIKE '%客服热线%' OR title LIKE '%产品与服务%' OR title LIKE '%平台首页%';
```

### 5. 前端引用完整性
```bash
# 监控页必须有 chat-widget（恰好2个：1CSS+1JS）
curl -s https://www.yfzx.online/bidding/ | grep -c "chat-widget"
# ⛔ 必须等于2！>2 说明 polish 非幂等导致重复注入，<2 说明组件丢失
```

### 6. 聊天组件重复注入检测
```bash
# polish_report.py 幂等性：检查 HTML 中 chat-widget 引用次数
n=$(curl -s https://www.yfzx.online/bidding/ | grep -c 'chat-widget.js')
if [ "$n" -ne 1 ]; then echo "DUP: chat-widget.js x$n"; fi
n=$(curl -s https://www.yfzx.online/bidding/ | grep -c 'chat-widget.css')
if [ "$n" -ne 1 ]; then echo "DUP: chat-widget.css x$n"; fi
```

### 7. 文件权限
```bash
# 目录必须有 x 执行位 (nginx 需要)
find /var/www/html/bidding -type d ! -perm 755
# 文件必须有 r 读权限
sudo -u www-data test -r /var/www/html/bidding/data/data_light.json
# 封面图可访问（企微推送依赖）
curl -sI https://www.yfzx.online/bidding/img_gen/covers/cover_1.png | grep -q '200 OK' || echo "COVER 404!"
# 操作手册可访问
curl -sI https://www.yfzx.online/bidding/manual.html | grep -q '200 OK' || echo "MANUAL 404!"
```

### 8. API 端点健康
```bash
for ep in / /api/bookmarks /api/chat /data/data_light.json /changelog.html; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://www.yfzx.online/bidding$ep")
  echo "$code $ep"
done
```

### 9. Nginx 语法 + systemd timer
```bash
nginx -t
systemctl list-timers 'wenyao-*' --no-pager
```

## 常见漏检 Bug 清单（历史教训）

| Bug | 症状 | 检查方式 |
|:--|:--|:--|
| 聊天组件消失 | 监控页无对话按钮 | grep chat-widget = 0 |
| 聊天组件重复 | 页面2个chat-trigger | grep -c chat-widget.js ≠ 1 |
| 地域字段垃圾 | "广州2.4资格审查…" | SQL length(region)>15 |
| 招标单位碎片 | "XX公司联系人：xxx电话…" | SQL length(owner)>40 |
| 标题前缀 | "采购公告 > 招标公告 > …" | SQL title LIKE '采购公告 >%' |
| 平台首页误抓 | "欢迎使用XX平台"入库 | SQL title LIKE '%欢迎来到%' |
| data_light.json 404 | 页面加载慢 | sudo -u www-data test -r |
| 列表页当招标 | 浙能"一体化平台"x9 | URL 含 category/list |
| unique_hash 不一致 | 同URL出现2条 | SQL GROUP BY url |
| bs4 依赖断裂 | pipeline 0新增 | 模拟 systemd 环境测试 import |
| 子目录权限遗落 | data/ 目录 404 | find -type d ! -perm 755 |
| changelog 顺序错 | V1.7在V1.6后 | grep -o "V1\.[0-9]" 验证降序 |
