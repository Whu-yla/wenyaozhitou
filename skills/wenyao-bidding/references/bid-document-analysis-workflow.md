# 投标技术规范书分析工作流

## 触发条件

用户发送 `.doc`/`.docx`/`.pdf` 格式的招标技术规范书或项目需求文档时，执行此工作流。

## 四步分析流程

### 阶段 1 — 文档提取

| 文档格式 | 工具 | 命令 |
|:--|:--|:--|
| `.doc` (旧Word) | `catdoc` | `catdoc "file.doc" 2>/dev/null` |
| `.docx` | `python-docx` | `python3 -c "from docx import Document; ..."` |
| `.pdf` | `pdftotext` 或 web_extract | `pdftotext -layout "file.pdf" -` |

**Pitfall**：不要假设 `.doc` 能用 `python-docx` 打开——旧格式是 OLE Compound Document，必须用 `catdoc` 或 `antiword` 或 LibreOffice 转换。

**大文档分段读取**：>3000 行时用 `sed -n 'OFFSET,LIMITp'` 分段提取。

### 阶段 2 — 数据库相似项目查询

**DB 路径**：`/root/.hermes/profiles/wenyaozhitou/data/bidding.db`

⚠️ **Pitfall**：`/var/www/html/bidding/data/bidding.db` 是空文件（0字节），不要用这个路径。正确路径必须通过代码检查确认：`grep -r "DB_PATH\|bidding.db" scripts/bidding_engine.py`。

**Python 查询模式**（避免 bash 转义问题）：
```python
# ✅ 用 write_file 写独立 .py 文件，再用 terminal 执行
# ❌ 不要用 terminal + python3 heredoc —— f-string 花括号会被 bash 解析

import sqlite3
conn = sqlite3.connect('/root/.hermes/profiles/wenyaozhitou/data/bidding.db')
conn.row_factory = sqlite3.Row  # 按列名访问
c = conn.cursor()

# 按业主名搜中标
c.execute("""SELECT ... FROM winning_notices WHERE procurement_owner LIKE '%xxx%'""")

# 按技术关键词搜相似项目
c.execute("""SELECT ... FROM bidding_notices WHERE title LIKE '%关键词%' AND relevance_score >= 50""")
```

**查询维度优先级**：
1. 中标表 → 同一业主的中标记录（看供应商偏好）
2. 中标表 → 同行业同类技术的中标记录（看竞争对手）
3. 招标表 → 同技术方向高分招标（看市场规模）

### 阶段 3 — 公开信息搜索

```
web_search "项目关键词 中标 业主名 年份"
web_search "技术方向 中标 2025 2026"
```

⚠️ web_search 受网络环境影响，失败时不要重试超过 1 次，改为基于数据库结果输出。

### 阶段 4 — 结构化分析报告

输出模板：
```
## 📋 项目速览
| 维度 | 内容 |
（项目名称、业主、行业、核心需求）

## 🎯 核心匹配度分析
| 数智科技能力 | 项目需求 | 匹配度 |
（逐项对标）

## 📐 项目规模判断
（功能模块数、技术门槛、业绩门槛、地域要求）

## ⚠️ 关键风险点
（地域、业绩、IP归属、行业know-how）

## 🔍 同类项目中标情况
（DB查询结果 + 竞争格局）
```

## 关键 Pitfalls

- **Python in bash escaping**：`terminal("python3 -c '...'")` 中的花括号 `{r['field']}` 会被 bash 解析为命令替换。解决方案：用 `write_file` + 独立 `.py` 文件。
- **DB 路径误导**：不要直接假设 `/var/www/html/bidding/data/bidding.db` 存在。先用 `find` 或代码 grep 确认实际路径。
- **.doc vs .docx**：`.doc` 文件 `python-docx` 打不开（`PackageNotFoundError`），需要 `catdoc`/`antiword`/LibreOffice。
