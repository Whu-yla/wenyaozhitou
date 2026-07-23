# Chat Engine LLM Provider 切换指南

## 当前状态 (v4 — 2026-07-20)

chat_engine.py v4 直接从 Hermes `config.yaml` 读取 LLM 配置，与文鳐智投本体完全同款。
当前 provider: custom (szkj.site:18002)，模型: GLM-5.2。

### 架构
- **后端** `chat_engine.py` v4 → 从 `config.yaml` 读取 `model.api_key / base_url / default`
- **前端** `chat-widget.js` v4 → 欢迎语显示「GLM-5.2 大模型」
- **HTTP 服务** `bookmark_server.py` (端口 8090) → Nginx 反代 `/bidding/api/chat` → `127.0.0.1:8090/chat`
- **变量名**: `LLM_API_KEY / LLM_BASE_URL / LLM_MODEL`（v3 的 `ARK_*` 已全部清除）

### config.yaml 当前值
```yaml
model:
  api_key: <key>
  base_url: https://www.szkj.site:18002/v1
  default: GLM-5.2
  provider: custom
```

### 换 Provider SOP（无需改代码）
1. 修改 `/root/.hermes/profiles/wenyaozhitou/config.yaml` 的 `model` 段
2. 重启 bookmark_server：`kill $(pgrep -f bookmark_server.py)` → 用 `terminal(background=true)` 启动 `/usr/local/lib/hermes-agent/venv/bin/python3 bookmark_server.py`
3. ⚠️ **同步更新前端文案**：`chat-widget.js` 中欢迎语的模型名称必须与实际一致
4. 验证：`curl -s -X POST http://localhost:8090/chat -H "Content-Type: application/json" -d '{"question":"你好","messages":[]}'`

### ⛔ 前后端文案同步铁律
切换 LLM provider 后，**必须同步更新前端 `chat-widget.js` 的欢迎语**。
历史教训：后端早已从 DeepSeek 切到 ARK 再切到 szkj.site，但前端欢迎语一直写着「DeepSeek 大模型」，
直到用户主动问才发现。用户看到的文案必须与实际后端一致。

### 诊断流程（问答不可用时）
1. **先查 bookmark_server 是否在运行**：`pgrep -f bookmark_server.py`
   - 不在运行 → 用 `terminal(background=true)` 启动（不要用 nohup，会被拒绝）
   - nginx_guardian.timer 每分钟检测，会通过 nginx_guard.sh 自动重启 bookmark_server（2026-07-20 已重新启用）
2. **测本地端点**：`curl -s http://127.0.0.1:8090/chat -X POST -H "Content-Type: application/json" -d '{"question":"你好","messages":[]}'`
3. **测 LLM API 直连**：
   ```python
   import requests, yaml
   cfg = yaml.safe_load(open("/root/.hermes/profiles/wenyaozhitou/config.yaml"))
   r = requests.post(cfg["model"]["base_url"]+"/chat/completions",
       headers={"Authorization":"Bearer "+cfg["model"]["api_key"]},
       json={"model":cfg["model"]["default"],"messages":[{"role":"user","content":"hi"}],"max_tokens":5})
   print(r.status_code, r.text[:200])
   ```
4. **测公网链路**：`curl -s -X POST https://www.yfzx.online/bidding/api/chat -H "Content-Type: application/json" -d '{"question":"你好","messages":[]}'`

### GLM 返回处理
GLM 模型可能把内容放在 `reasoning_content` 字段：
```python
content = data["choices"][0]["message"]["content"]
if not content and "reasoning_content" in data["choices"][0]["message"]:
    content = data["choices"][0]["message"]["reasoning_content"]
return content if content else "（模型未返回内容）"
```

### 性能注意
chat_engine 的 system prompt 包含完整数据库快照（TOP10 招标+中标+排行+分类），
GLM-5.2 处理带大 system prompt 的请求约需 10-20 秒。`requests.post` 的 timeout 设为 30 秒。
如果偶发超时，通常是网络波动，重试即可。

## 历史记录

### v4 (2026-07-20): 清除 ARK 残留 + 统一命名
- 变量名 `ARK_API_KEY/ARK_BASE_URL/ARK_MODEL` → `LLM_API_KEY/LLM_BASE_URL/LLM_MODEL`
- 默认回退值从 ARK coding endpoint 改为 szkj.site
- 注释/文档字符串全部更新，不再误导
- 前端 `chat-widget.js` 欢迎语从「DeepSeek 大模型」更正为「GLM-5.2 大模型」
- bookmark_server 未运行，手动重启恢复

### v3 (2026-07-18): DeepSeek → 火山引擎 ARK
- DeepSeek 账户欠费 → 切换到 ARK coding endpoint
- ARK 双 endpoint：`/api/v3` 返回 403（欠费），`/api/coding/v3` 正常
- 从 config.yaml 动态读取 ARK 配置

### v2: DeepSeek API（已废弃，欠费）

## 定时任务状态 (2026-07-20 更新)

### 2026-07-20: 全部定时任务已重新启用

用户要求重新启动所有服务。4 个 systemd timer 全部 active：

| Timer | 时间 | 说明 |
|:--|:--|:--|
| `wenyao-pipeline.timer` | 每天 08:00 | 全流程采集管线 |
| `wenyao-memory.timer` | 每天 09:00 | 长记忆维护（路径已修复） |
| `wenyao-selfheal.timer` | 每天 03:00 | 凌晨自检修复 |
| `nginx-guardian.timer` | 每分钟 | Nginx 端口守护 + bookmark_server 自愈 |

启用命令：`systemctl enable --now wenyao-memory.timer wenyao-selfheal.timer nginx-guardian.timer`

### 2026-07-18: 曾短暂关闭（已恢复）

用户曾要求关闭除早上管线外的所有定时任务，2026-07-20 全部恢复。

**注意**：bookmark_server.py 不是定时任务，是常驻 HTTP 服务，不能关。
nginx_guardian 会通过 nginx_guard.sh 检测并重启 bookmark_server。

### ⚠️ wenyao-memory.service 路径修复 (2026-07-20)

**症状**：wenyao-memory.service 一直 failed，日志报 `can't open file '/root/.hermes/memory_store/memory_maintainer.py': [Errno 2] No such file or directory`。

**根因**：systemd service 文件的 `ExecStart` 指向旧路径 `/root/.hermes/memory_store/memory_maintainer.py`（profile 迁移前的路径），实际脚本在 `/root/.hermes/profiles/wenyaozhitou/scripts/memory_maintainer.py`。

**修复**：`sed -i 's|/root/.hermes/memory_store/memory_maintainer.py|/root/.hermes/profiles/wenyaozhitou/scripts/memory_maintainer.py|' /etc/systemd/system/wenyao-memory.service` + `systemctl daemon-reload`

**教训**：profile 迁移后，所有 systemd service 文件的 `ExecStart` 路径必须同步更新。检查命令：`grep ExecStart /etc/systemd/system/wenyao-*.service`

### ⚠️ memory 服务依赖 /tmp/qwen_key.txt

wenyao-memory.service 通过 memory_engine.py 读取 `/tmp/qwen_key.txt`（通义千问 embedding API key）。
`/tmp` 重启后会被清理，导致 memory 服务失败。

**修复**：需要手动写入 key 到 `/tmp/qwen_key.txt`，或考虑将 key 迁移到 profile `.env` 或 config.yaml。
