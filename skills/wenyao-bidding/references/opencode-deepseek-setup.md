# OpenCode + DeepSeek 配置指南

## 背景

Claude Code 只能对接 Anthropic API，不能使用 DeepSeek。OpenCode 是 provider-agnostic 的替代方案，可以配置自定义 OpenAI-compatible 提供商。

## 安装

```bash
npm install -g opencode-ai@latest
```

## 配置步骤

### 1. 写入 config

文件：`~/.config/opencode/opencode.jsonc`

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

### 2. 环境变量

**关键**：AI SDK 对自定义 provider 使用 `{PROVIDER_NAME}_API_KEY` 命名约定。provider 名是 `deepseek`，所以环境变量是 `DEEPSEEK_API_KEY`。

```bash
export DEEPSEEK_API_KEY=sk-xxx
export HOME=/root  # 重要：Hermes 环境下的 HOME 可能不是 /root
```

### 3. 可用模型

配置成功后 `opencode models` 会列出：
- `deepseek/deepseek-chat`
- `deepseek/deepseek-reasoner`
- `deepseek/deepseek-v4-flash`
- `deepseek/deepseek-v4-pro`

### 4. 运行

```bash
cd /var/www/html/bidding-test
opencode run "Fix the bug in app.js" --model deepseek/deepseek-chat
```

## 关键坑

### 坑1：provider type 必须是 `openai-compatible` 不是 `openai`

- ❌ `"provider": "openai"` → `ProviderModelNotFoundError`
- ✅ `"provider": "openai-compatible"` → 正确识别

### 坑2：apiKey 不能写在 config 里

即使把 `apiKey` 写入 config JSON，AI SDK 也不会正确读取。必须通过环境变量 `DEEPSEEK_API_KEY` 传递。

- ❌ config 中有 `"apiKey": "sk-xxx"` → `Authorization Required`
- ✅ 环境变量 `DEEPSEEK_API_KEY=sk-xxx` → 正常工作

### 坑3：模型名称格式

- ❌ `--model deepseek-chat` → `Model not found: deepseek-chat/.`
- ❌ `--model openai/deepseek-chat` → OpenAI provider 不认
- ✅ `--model deepseek/deepseek-chat` → 正确

### 坑4：目录权限

OpenCode 只能访问当前工作目录。访问外部路径会触发 `external_directory` 权限拒绝。

- ✅ 在目标目录下运行 `cd /var/www/html/bidding-test && opencode run ...`
- ❌ 在 `/root` 下运行并尝试读 `/var/www/html/bidding-test/app.js`

### 坑5：Hermes 下的 HOME 变量

Hermes 环境中 `HOME` 指向 profile 目录而非真实 `/root`。OpenCode 需要真实 HOME：

```bash
export HOME=/root
```

## 便捷包装脚本

`/usr/local/bin/opencode-ds`（Python 包装器，自动注入 DEEPSEEK_API_KEY）：

```python
#!/usr/bin/env python3
import os, sys, subprocess

with open('/root/.hermes/profiles/wenyaozhitou/.env') as f:
    for line in f:
        if 'DEEPSEEK_API_KEY' in line:
            os.environ["DEEPSEEK_API_KEY"] = line.strip().split('=', 1)[1]
            break

os.environ["HOME"] = "/root"
args = ["opencode"] + sys.argv[1:]
sys.exit(subprocess.run(args).returncode)
```

使用：
```bash
cd /var/www/html/bidding-test && opencode-ds run "修复分页bug" --model deepseek/deepseek-chat
```

## 与 Hermes 原生工具的对比

| 维度 | Hermes 原生 (execute_code/patch) | OpenCode |
|:--|:--|:--|
| 小修改（1-2 行） | ⚡ 更快 | 🐢 杀鸡用牛刀 |
| 多步迭代（写→跑→修→再跑） | 需人工盯每步 | ✅ 自主循环 |
| 大型重构 | 需拆分为多轮对话 | ✅ 一次搞定 |
| 需要理解业务上下文 | ✅ 有系统记忆 | ⚠️ 需在 prompt 中注入上下文 |

**推荐策略**：日常小修用 Hermes 原生工具，大重构/新功能用 OpenCode。
