# Hermes + OpenCode + DeepSeek 集成

## 安装

```bash
npm config set registry https://registry.npmmirror.com
npm install -g opencode-ai@latest
```

## 配置 DeepSeek Provider

`~/.config/opencode/opencode.jsonc`:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "deepseek": {
      "provider": "openai-compatible",
      "baseURL": "https://api.deepseek.com/v1"
    }
  }
}
```

**关键**：API key 通过 `DEEPSEEK_API_KEY` 环境变量传入，**不在 config 里写** `apiKey` 字段。

## Python 包装器 `/usr/local/bin/opencode-ds`

因 Hermes 的 `write_file` 和 bash heredoc 会 redact `***`，bash 包装器不可用。使用 Python 包装器在运行时从 Hermes `.env` 读取 key：

```python
#!/usr/bin/env python3
"""OpenCode wrapper with DeepSeek API key auto-injected."""
import os, sys, subprocess

key = None
with open('/root/.hermes/profiles/wenyaozhitou/.env') as f:
    for line in f:
        if 'DEEPSEEK_API_KEY' in line:
            key = line.strip().split('=', 1)[1]
            break

os.environ["DEEPSEEK_API_KEY"] = key
os.environ["HOME"] = "/root"

args = ["opencode"] + sys.argv[1:]
sys.exit(subprocess.run(args).returncode)
```

## 使用

```bash
cd /var/www/html/bidding-test
opencode-ds run "Fix the pagination bug in app.js" --model deepseek/deepseek-chat
```

## Claude Code vs OpenCode

- **Claude Code**：仅支持 Anthropic API（含 Bedrock/Vertex/Foundry），**不能用** DeepSeek
- **OpenCode**：provider-agnostic，支持 `openai-compatible` 类型接入任何兼容 API

## 已知限制

- OpenCode 自动拒绝访问工作目录外的文件。解决：从项目目录运行，或复制所需文件到 cwd。
- Hermes `write_file` 会 redact `***` → bash 硬编码 key 的脚本不可用 → 用 Python 运行时读 `.env`
