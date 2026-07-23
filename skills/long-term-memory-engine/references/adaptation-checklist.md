# 新 Profile 适配自查清单

> 完整流程参见 SKILL.md § 新 Profile 适配流程。本文件是逐项打勾的快速检查单。

## 适配目标
- Profile 名: ___________
- Profile 路径: `/root/.hermes/profiles/___________/`

## 检查项

### 引擎配置
- [ ] `config.json` 中 `profile` 和 `profile_dir` 已改
- [ ] `memory_maintainer.py` 中 `PROFILE_DIR` 已改
- [ ] `memory_maintainer.py` 中标题字符串已改
- [ ] `memory_maintainer.py` 中 import 行确认只有 `MemoryEngine`（无 `load_memories`/`save_memories`）

### API 字段对照
| maintainer 中使用 | engine 实际返回 | 检查 |
|:---|:---|:--:|
| `result["status"]` | `{"status": "created"/"updated"}` | ☐ |
| `stats["total_entries"]` | `{"total_entries": N}` | ☐ |
| `result["removed"]` | `{"removed": N, "ids": [...]}` | ☐ |

### 文件创建
- [ ] `mkdir -p memory/hot memory/warm`
- [ ] `memory/hot/HOT_MEMORY.md` — 含当前任务/待办/临时上下文/活跃会话
- [ ] `memory/warm/WARM_MEMORY.md` — 含核心身份/技术栈/关键路径/排坑记录
- [ ] `memory/YYYY-MM-DD.md` — 今日日志

### SOUL.md
- [ ] 更新身份描述
- [ ] 加入启动加载序列（7步）

### 测试
- [ ] `python3 memory_engine.py store "测试"` → 返回 `{"status": "created"}`
- [ ] `python3 memory_engine.py search "测试"` → 命中
- [ ] `python3 memory_engine.py stats` → `{"total_entries": >=1}`
- [ ] `python3 memory_maintainer.py` → 无报错

### 定时任务
- [ ] cronjob 已创建，每日 9:00
- [ ] job_id: ___________

### 排坑速查
- ❌ 不要用 LiteLLM `openai/` 前缀 → 直调 Dashscope REST
- ❌ 不要引用 `load_memories`/`save_memories`（不存在）
- ❌ 不要用 `result["action"]`（用 `result["status"]`）
- ❌ 不要用 `stats["total"]`（用 `stats["total_entries"]`）
- ❌ 不要用 `result["deleted"]`/`["kept"]`（用 `result["removed"]`）
