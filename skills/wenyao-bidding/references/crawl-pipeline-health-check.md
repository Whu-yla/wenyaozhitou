# 采集管线健康检查 SOP (V1.36)

## 触发条件
- 用户问「数据怎么这么少」「是不是没抓到」
- 定时推送的数据看起来是旧的
- 怀疑爬虫没在跑

## 检查步骤

### 1. 确认 Cron 任务存在
```
cronjob(action='list')  → 应有「投标采集管线」任务
```
当前任务 ID: `ec61bb478859`，每天 9:00/18:00，no_agent=true

### 2. 确认采集日志在增长
```sql
SELECT COUNT(*) FROM crawl_log;
SELECT MAX(crawl_time) FROM crawl_log;
```

### 3. 确认数据新鲜度
```sql
SELECT MAX(fetch_date) FROM bidding_notices;
SELECT COUNT(*) FROM bidding_notices WHERE substr(fetch_date,1,10)=date('now');
```

### 4. 手动跑一次验证
```bash
cd /root/.hermes/profiles/wenyaozhitou
/usr/local/lib/hermes-agent/venv/bin/python3 scripts/crawl_pipeline.py
```

## 常见故障模式
| 症状 | 根因 | 修复 |
|:--|:--|:--|
| crawl_log 为空 | Cron 任务不存在 | `cronjob(action='create', ...)` |
| 南网适配器未加载 | 导入路径错误 (site_adapters→应为dedicated_adapters) | 修 crawl_pipeline.py |
| 国家能源 0 条 | Python 模块缓存旧 .pyc | 删 sys.modules 或重启进程 |
| 国电投 0 条 | 列表页 JS 动态渲染 | 需改 Chromium |
