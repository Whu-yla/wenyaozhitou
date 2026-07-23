# GitHub 部署 - 文鳐智投项目推送

> 首次推送: 2026-07-22 | 仓库: `git@github.com:Whu-yla/wenyaozhitou.git`
> 全量补推: 2026-07-23（70 个文件补推）

## SSH 密钥配置

### ⛔ Hermes HOME 重定向陷阱

Hermes profile 环境下 `HOME` 被重定向到 `/data/hermes/profiles/wenyaozhitou/home/`，
而 `~/.ssh/` 展开为该路径下不存在的 `.ssh` 目录。`ssh-keygen -f ~/.ssh/id_ed25519` 会报
`No such file or directory`。

**正确做法**：显式使用 `/root/.ssh/`：
```bash
mkdir -p /root/.ssh
ssh-keygen -t ed25519 -C "wenyaozhitou@hermes-agent" -f /root/.ssh/id_ed25519 -N ""
cat /root/.ssh/id_ed25519.pub  # 公钥添加到 GitHub Settings > SSH keys
```

验证连接：
```bash
ssh -T git@github.com -o StrictHostKeyChecking=no
# 预期: Hi Whu-yla! You've successfully authenticated...
```

## 敏感数据脱敏（推送前必做）

### 3 处必须脱敏的文件

| 文件 | 变量/字段 | 替换为 |
|:-----|:----------|:-------|
| `scripts/wecom_push.py` | `WEBHOOK` 变量（企微 webhook URL，含 key） | `...key=YOUR_WEBHOOK_KEY` |
| `scripts/nginx_guardian.py` | `WECOM_WEBHOOK` 变量（同上） | `...key=YOUR_WEBHOOK_KEY` |
| `config.yaml`（根目录） | `model.api_key` 字段（LLM API key） | `YOUR_API_KEY_HERE` |

⚠️ **config.yaml 脱敏（2026-07-23 致命遗漏）**：首次推送时遗漏了 config.yaml 中的
`api_key: ark-4052b17e-f92d-4770-afa0-1f4ecab69acb-c990c`，API key 直接暴露在 GitHub。
第二次推送才发现并替换为 `YOUR_API_KEY_HERE`。**推送前必须 `grep -rn 'key\|token\|secret\|password' config.yaml`**。

脱敏脚本：
```python
import os

# 1. 企微 webhook
old_wecom = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0256f02d-7368-4214-9c99-9c53ce449e92"
new_wecom = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_WEBHOOK_KEY"
for fp in ["scripts/wecom_push.py", "scripts/nginx_guardian.py"]:
    with open(fp, 'r') as f: content = f.read()
    if old_wecom in content:
        with open(fp, 'w') as f: f.write(content.replace(old_wecom, new_wecom))

# 2. config.yaml API key
with open('config.yaml', 'r') as f: content = f.read()
# 用正则匹配各种 api_key 格式
import re
content = re.sub(r'(api_key:\s*)\S+', r'\1YOUR_API_KEY_HERE', content)
with open('config.yaml', 'w') as f: f.write(content)
```

### 无需脱敏的文件

代码中部分 API 密钥从文件/配置动态读取，无硬编码：
- `ai_cover.py` / `memory_engine.py`: 从 `/tmp/qwen_key.txt` 读取
- `chat_engine.py`: 从 Hermes `config.yaml` 动态读取（运行时填充）

### 投标网站注册信息汇总表

`.gitignore` 排除 `cache/documents/*.xlsx`，包含用户名/密码/CA信息的 Excel 不会上传。

## .gitignore 要点

⛔ **用户明确要求「整个工程都推过去」**。`.gitignore` 只排除敏感文件和垃圾文件，
**不排除**项目数据文件。

### 正确的 .gitignore（2026-07-23 修订）

```
# 敏感文件
cache/documents/*.xlsx
cache/documents/*.xls
cache/documents/*.csv
/tmp/qwen_key.txt
*.key
*.pem
*.crt

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
venv/
.venv/

# 日志
*.log
api_server.log

# 备份
*.bak
*.orig

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
```

### ⛔ 被移除的排除规则（历史教训）

首次推送的 .gitignore 排除了以下文件，导致 70 个文件缺失：
- ~~`frontend/data_full.json`~~ — 全量数据，用户要求推送
- ~~`frontend/data_bid_p*.json`~~ — 分页数据，用户要求推送
- ~~`frontend/data_win_p*.json`~~ — 中标分页数据，用户要求推送
- ~~`frontend/report-*.html`~~ — 历史报告，用户要求推送
- ~~`frontend/2026-*/`~~ — 按日期归档目录

**规则：除非文件含真实密钥/密码，否则全部推送。体积大不是排除理由——用户要的是完整工程。**

## 推送前同步检查（必做）

### 为什么要检查

项目文件分散在多个位置：
- 后端脚本：`/root/.hermes/profiles/wenyaozhitou/scripts/`
- 前端文件：`/var/www/html/bidding/`
- 配置文件：`/root/.hermes/profiles/wenyaozhitou/config.yaml`
- 记忆系统：`/root/.hermes/profiles/wenyaozhitou/memory/`

临时目录 `/tmp/wenyaozhitou/` 是组装仓库，容易遗漏同步。

### 检查脚本

```python
import os, hashlib

def md5(path):
    with open(path, 'rb') as f: return hashlib.md5(f.read()).hexdigest()

# 对比生产 vs git 仓库
sources = {
    "scripts": "/root/.hermes/profiles/wenyaozhitou/scripts/",
    "frontend": "/var/www/html/bidding/",
}
repo = "/tmp/wenyaozhitou"

for label, prod in sources.items():
    repo_dir = os.path.join(repo, label)
    for f in os.listdir(prod):
        if f in ('__pycache__',) or f.endswith('.bak'): continue
        prod_path = os.path.join(prod, f)
        if not os.path.isfile(prod_path): continue
        repo_path = os.path.join(repo_dir, f)
        if not os.path.exists(repo_path):
            print(f"❌ {label}/{f} (git仓库缺失)")
        elif md5(prod_path) != md5(repo_path):
            print(f"⚠️ {label}/{f} (内容不同)")

# 检查缺失目录
for subdir in ['frontend/data', 'frontend/img', 'frontend/img_gen']:
    p = os.path.join(repo, subdir)
    if not os.path.exists(p):
        print(f"❌ {subdir}/ 目录缺失")
```

## 项目目录结构（Git 仓库 - 2026-07-23 全量推送后）

```
wenyaozhitou/                    # 137 个文件
├── config.yaml                  # Hermes 配置（API key 已脱敏）
├── scripts/                     # 32 个后端脚本
├── frontend/                    # 前端全量
│   ├── index.html               # 主看板
│   ├── app.js                   # 前端交互
│   ├── changelog.html           # 更新日志
│   ├── chat-widget.js/css       # AI 对话组件
│   ├── data.json                # 招标数据（~1MB）
│   ├── data_full.json           # 全量数据（~3MB）
│   ├── data_bid_p1~p4.json      # 分页数据
│   ├── data_win_p1.json         # 中标分页
│   ├── report-2026-06-24~26.html# 历史报告
│   ├── data/                    # 运行时数据
│   │   ├── feedback.json
│   │   ├── data_light.json
│   │   ├── bookmarks.json
│   │   └── bidding.db
│   ├── img/                     # 静态图片（logo/banner/分类图标）
│   └── img_gen/                 # AI 封面图
│       ├── og-share.png
│       ├── cache/               # 28 张缓存图
│       └── covers/              # 8 张固定封面
├── config/                      # 8 个 Systemd service+timer
├── memory/                      # 三层记忆 (hot/warm/daily)
├── .gitignore
└── README.md
```

## 推送命令

### 首次推送

```bash
cd /tmp/wenyaozhitou  # 临时项目目录
git init
git config user.name "Whu-yla"
git config user.email "wenyaozhitou@hermes-agent"
git config --global url."git@github.com:".insteadOf "https://github.com/"
git remote add origin git@github.com:Whu-yla/wenyaozhitou.git
git branch -m main
git add -A
git commit -m "🎉 文鳐智投 V1.37 初始提交"
git push -u origin main --force  # --force 覆盖远程已有的 README 等初始化文件
```

### 后续增量推送

```bash
cd /tmp/wenyaozhitou
# 1. 运行同步检查脚本（见上方）
# 2. 同步最新文件到临时目录（注意脱敏）
# 3. 提交
git add -A
git commit -m "📦 全量同步：描述变更"
git push origin main
```

### 双向同步流程

用户在 TREA IDE 中修改代码 -> push 到 GitHub -> 通知文鳐智投 -> pull 同步到本地 -> 部署到生产环境。

```bash
# Pull 用户在 TREA 中的改动
cd /tmp/wenyaozhitou
git pull origin main
# 然后同步到生产环境路径
```

## 注意事项

- **临时目录策略**：项目在 `/tmp/wenyaozhitou/` 组装，不直接在运行环境 `git init`，避免误提交 venv/cache 等大目录
- **`--force` 仅首次**：后续推送不要用 `--force`，会覆盖远程的历史提交
- **data.json 体积监控**：当前 `data.json` (~1MB) 已上传。如后续体积增长超 1MB，参考数据策略铁律拆出 `data_light.json`，但两者都推送到仓库
- **⛔ 推送后验证**：`git ls-tree -r --name-only HEAD | wc -l` 确认文件总数；对比生产环境文件数确保无遗漏
