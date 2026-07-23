# Patch 工具 literal `\n` 腐败陷阱

## 症状

使用 `patch` 工具的 `mode='replace'` 替换跨行内容时，`new_string` 中的换行符会被写成字面量 `\n` 字符串（两个字符：反斜杠+n），而非真正的换行符。

**结果**：Python/JS 文件被塞入字面量 `\n`，导致 `SyntaxError`。

## 触发条件

当 `old_string` 和 `new_string` 都包含多行内容，且 `new_string` 跨越多行时。

## 验证

```bash
node --check /var/www/html/bidding/app.js
```

如果有字面量 `\n`，会报 `SyntaxError: Invalid or unexpected token`。

## 修复方法

**不要再用 `patch` 工具跨行替换 JS/Python 文件。** 

改用 Python heredoc：
```bash
python3 << 'PYEOF'
with open('/path/to/file', 'r') as f:
    content = f.read()
old = "多行旧内容"
new = """多行新内容"""
content = content.replace(old, new)
with open('/path/to/file', 'w') as f:
    f.write(content)
PYEOF
```

**或用 `write_file` 重写整个文件块**：先 `read_file` 确认内容，再 `write_file` 写入修正版本。

## 历史案例

- 2026-06-28: `app.js` 新增 `filterToggleBtn` 事件处理器时，跨行 replace 导致 line 127 变成 `}\\n    // ── ...`。语法检查报错。Python heredoc 修复。