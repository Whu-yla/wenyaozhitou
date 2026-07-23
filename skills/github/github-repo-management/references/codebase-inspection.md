# Codebase Inspection with pygount

Analyze repositories for lines of code, language breakdown, file counts, and code-vs-comment ratios using `pygount`.

## When to Use

- User asks for LOC (lines of code) count
- User wants a language breakdown of a repo
- User asks about codebase size or composition

## Prerequisites

```bash
pip install --break-system-packages pygount 2>/dev/null || pip install pygount
```

## Basic Summary

```bash
cd /path/to/repo
pygount --format=summary \
  --folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,.eggs,*.egg-info" \
  .
```

**IMPORTANT:** Always use `--folders-to-skip` to exclude dependency/build directories.

## Common Exclusions

- Python: `--folders-to-skip=".git,venv,.venv,__pycache__,.cache,dist,build,.tox,.eggs,.mypy_cache"`
- JavaScript: `--folders-to-skip=".git,node_modules,dist,build,.next,.cache,.turbo,coverage"`
- General: `--folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,vendor,third_party"`

## Filter by Language

```bash
pygount --suffix=py --format=summary .
pygount --suffix=py,yaml,yml --format=summary .
```

## Output Formats

```bash
pygount --format=summary .            # Summary table (default)
pygount --format=json .               # JSON for programmatic use
```

## Interpreting Results

- **Language** — detected programming language
- **Files** — number of files
- **Code** — lines of actual code
- **Comment** — lines that are comments/docs
- **%** — percentage of total

Special pseudo-languages: `__empty__` (empty files), `__binary__` (binary files), `__generated__` (auto-generated), `__duplicate__` (identical content), `__unknown__` (unrecognized).

## Pitfalls

1. **Always exclude .git, node_modules, venv** — without `--folders-to-skip`, pygount may hang on large dependency trees.
2. **Markdown shows 0 code lines** — pygount classifies all Markdown as comments.
3. **Large monorepos** — use `--suffix` to target specific languages.
