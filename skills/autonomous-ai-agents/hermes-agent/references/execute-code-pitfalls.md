# execute_code Pitfalls

## The Line-Number Corruption Trap

`execute_code`'s `hermes_tools.read_file()` returns file content **with `LINE_NUM|` prefixes**
on every line. If you then `write_file()` that content back, those prefixes become
**embedded in the source file** — causing syntax errors on the next run.

### Symptoms
- Python: `SyntaxError: invalid syntax` at line 1 (`1|#!/usr/bin/env python3`)
- Multiple layers of nested numbers after repeated read→write cycles: `310|308|  code...`
- Silent JS failures when `function exportExcel()` becomes `387|function exportExcel()`

### Root Cause
```python
# execute_code's read_file returns:
"1|#!/usr/bin/env python3\n2|import os\n3|\n4|def main():\n"

# Writing that back embeds "1|", "2|", etc. as source text
write_file("script.py", content)  # CORRUPTS the file!
```

### Safe Alternatives

**1. Termial with inline Python (preferred)**
```bash
terminal(command="python3 -c \"...\"")
# Or heredoc:
terminal(command="python3 << 'EOF'\n...\nEOF")
```

**2. Write script first, then execute**
```python
write_file("/tmp/fix.py", clean_python_code)
terminal(command="python3 /tmp/fix.py")
```

**3. Use the `patch` tool directly**
```
patch(path="file.py", old_string="...", new_string="...")
```
The `patch` tool reads the file directly without line-number prefixes.

**4. Use `terminal` with `cat`/`sed`/`grep`**
```bash
grep -n 'pattern' file.py
sed -i 's/old/new/' file.py
```

### Recovery: Strip Embedded Line Numbers
```python
import re
with open('corrupted.py') as f:
    raw = f.read()
# Strip leading number| from every line, repeat to catch nesting
for _ in range(5):
    raw = re.sub(r'^\d+\|', '', raw, flags=re.MULTILINE)
with open('corrupted.py', 'w') as f:
    f.write(raw)
```

### When execute_code read_file IS safe
- Read-only analysis (never write back)
- Extracting data from the content (not re-writing)
- When you strip line numbers before writing:
  ```python
  content = read_file("file.py")["content"]
  clean = re.sub(r'^\d+\|', '', content, flags=re.MULTILINE)
  write_file("file.py", clean)
  ```

### Key Rule
> **Never pass `read_file` output directly to `write_file` inside `execute_code`.**
> Always route through `terminal` or the `patch` tool for file modifications.
