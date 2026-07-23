# DeepSeek Provider Setup for OpenCode

## One-Time Setup

### 1. Install OpenCode
```bash
npm install -g opencode-ai@latest
```

### 2. Configure Provider
Create `/root/.config/opencode/opencode.jsonc`:
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

**Critical:** Use `"openai-compatible"` NOT `"openai"`. The `"openai"` provider type hardcodes to `api.openai.com` and ignores `baseURL`.

### 3. API Key Convention
The AI SDK uses `{PROVIDER}_API_KEY` env vars. Set `DEEPSEEK_API_KEY`:
```bash
export DEEPSEEK_API_KEY=sk-xxx...
```

The key lives in `/root/.hermes/profiles/wenyaozhitou/.env` as `DEEPSEEK_API_KEY=sk-...`.

### 4. Verify
```bash
opencode models | grep deepseek
# Should show: deepseek/deepseek-chat, deepseek/deepseek-reasoner, deepseek-v4-pro, etc.

opencode providers list
# Should show DEEPSEEK_API_KEY detected
```

### 5. Smoke Test
```bash
DEEPSEEK_API_KEY=sk-xxx HOME=/root \
  opencode run 'Say exactly: DEEPSEEK_OK' --model deepseek/deepseek-chat
```

## Available DeepSeek Models

| Model ID | Description |
|:---------|:------------|
| `deepseek/deepseek-chat` | General-purpose chat (V3) |
| `deepseek/deepseek-reasoner` | Reasoning model (R1) |
| `deepseek/deepseek-v4-flash` | Fast/cheap V4 variant |
| `deepseek/deepseek-v4-pro` | Premium V4 model |

## Wrapper Script

`/usr/local/bin/opencode-ds` — auto-injects DEEPSEEK_API_KEY from Hermes profile .env:

```python
#!/usr/bin/env python3
"""OpenCode wrapper with DeepSeek API key auto-injected."""
import os, sys, subprocess

with open('/root/.hermes/profiles/wenyaozhitou/.env') as f:
    for line in f:
        if 'DEEPSEEK_API_KEY' in line:
            os.environ['DEEPSEEK_API_KEY'] = line.strip().split('=', 1)[1]
            break

os.environ['HOME'] = '/root'
sys.exit(subprocess.run(['opencode'] + sys.argv[1:]).returncode)
```

Usage: `opencode-ds run "Fix the bug" --model deepseek/deepseek-chat`

## Troubleshooting

### "Model not found: deepseek/deepseek-chat"
- `opencode models` — verify the model is listed. If not, check config is valid JSON.
- The `opencode` command caches models. Run `opencode models` again to refresh.

### "Authorization Required" / "Authentication Fails"
1. Verify `DEEPSEEK_API_KEY` env var is set and correct
2. Check the key works: `curl -H "Authorization: Bearer $DEEPSEEK_API_...` https://api.deepseek.com/v1/models`
3. Make sure config uses `"openai-compatible"` not `"openai"`
4. Key should be in env var, NOT in config's `apiKey` field

### "Permission requested: external_directory"
OpenCode restricts file access to its working directory. Either:
- Run from the target directory: `cd /target && opencode-ds run "..."` 
- Use `--add-dir` flag (TUI mode only, not `run`)

### Timed out on `opencode/deepseek-v4-flash-free`
The free OpenCode-hosted models require internet access to OpenCode's servers. On restricted networks (China), these may be unreachable. Use your own DeepSeek API key instead.
