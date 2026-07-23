# execute_code File Corruption Pitfall

## Symptom
After using `hermes_tools.read_file()` + `hermes_tools.write_file()` inside `execute_code`, the target file gets corrupted with embedded line number prefixes.

Example: `app.js` line 1 becomes `1|// 文鳐智投 v7 ...` instead of `// 文鳐智投 v7 ...`

After multiple read/write cycles: `1|1|1|// 文鳐智投 v7 ...`

## Root Cause
`hermes_tools.read_file()` returns content with `LINE_NUM|` prefixes on each line (matching the main `read_file` tool output format). When you `write_file()` this content, the prefixes become literal text.

## Detection
```bash
grep -c '^[0-9]\+|' /path/to/file
# > 0 means clean. Non-zero means corrupted.
```

## Fix
```bash
python3 -c "
import re
with open('/path/to/file') as f:
    c = f.read()
for _ in range(10):
    c = re.sub(r'^\d+\|', '', c, flags=re.MULTILINE)
with open('/path/to/file', 'w') as f:
    f.write(c)
"
```

## Prevention
Use `terminal` with inline Python instead of execute_code for file edits:

```bash
# Right way:
cd /path && python3 << 'EOF'
with open('file.js') as f:
    content = f.read()
# ... modifications ...
with open('file.js', 'w') as f:
    f.write(content)
EOF

# Wrong way (corrupts files):
# Inside execute_code: read_file() → modify → write_file()
```

Alternatively, use the `patch` tool, which reads files directly without line number contamination.
