# Cron no_agent 模式 — DeepSeek Broken Pipe 教训

## 问题

2026-06-24 9:00 定时任务全部 `error`。errors.log：

```
[Errno 32] Broken pipe
Stream stale for 180s — no chunks received
API call failed after 3 retries
```

## 根因

Cron job 使用 **LLM Agent 模式**（`no_agent=false`，默认）。Agent 需要维持与 DeepSeek API 的流式连接。当 Agent 调用 `terminal()` 跑长命令（如 crawl_pipeline.py 耗时 5-10 分钟），API 流超过 180s 无 chunk → 判定 stale → kill 连接 → retry 3 次全 fail → RuntimeError。

## 修复

将长流程 cron job 改为 `no_agent=true`，用 bash 主控脚本直跑全部阶段：

```bash
# pipeline_master.sh 结构
timeout 300 python3 scripts/crawl_pipeline.py || log "⚠️"
timeout 300 python3 scripts/dedicated_adapters.py || log "⚠️"
timeout 600 python3 scripts/batch_crawler.py || log "⚠️"
timeout 180 python3 scripts/chromium_crawler.py || log "⚠️"
# ... 清洗→竞品→报告→推送→维护
```

Cron 配置：`no_agent=true`, `script="pipeline_master.sh"`, `skills=[]`

## 判定表

| 场景 | 模式 |
|:--|:--|
| 短任务 < 2min | LLM Agent |
| 长流程 > 5min | **no_agent** |
| 纯采集/报告 | **no_agent** |
| 需判断/决策 | LLM Agent |
