# 文件操作安全规则

## 问题根因

Hermes 的 `read_file` 工具 (以及 `hermes_tools.read_file`) 在输出内容时自动为每行添加 `LINE_NUM|` 前缀。
当 agent 将该内容通过 `write_file` 写回时, 行号前缀会永久嵌入文件, 导致:
- Python 文件第一行变成 `1|#!/usr/bin/env python3` -> SyntaxError
- JS 文件出现 `310|308|` 双重行号污染
- 所有 grep/sed 匹配失败

## 禁止操作

```python
# ❌ 危险 — read_file 输出含行号, 写回污染文件
from hermes_tools import read_file, write_file
r = read_file("/path/to/file", limit=500)
write_file("/path/to/file", r["content"])
```

## 正确操作

### 读取+修改+写回: 用 terminal + python3

```bash
python3 -c "
c = open('file.py').read()
c = c.replace('old', 'new')
open('file.py', 'w').write(c)
"
```

### 简单替换: 用 patch 工具

```python
patch(path="file.py", old_string="exact text", new_string="replacement")
```

### 修复已污染文件

```bash
python3 -c "
import re
c = open('file.py').read()
for _ in range(5):
    c = re.sub(r'^\d+\|', '', c, flags=re.MULTILINE)
open('file.py', 'w').write(c)
"
```

## 污染检测

```bash
# 检查文件是否被污染 (第一行以数字|开头)
head -1 file.py | grep -q '^[0-9]\+|' && echo "POLLUTED"
```
