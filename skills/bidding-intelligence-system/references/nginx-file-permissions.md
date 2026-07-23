# Nginx File Permission Pitfall

## Symptom

New files under `/var/www/html/bidding/` return 404/403 despite existing on disk:

```
$ ls -la /var/www/html/bidding/img/logo.png
-rw-r--r-- 1 root root 16876 Jun 26 10:03 logo.png

$ curl -sI https://www.yfzx.online/bidding/img/logo.png
HTTP/1.1 404 Not Found
```

## Root Cause #1: Directory Missing Execute Bit

Nginx worker processes run as `www-data`, not root. To `stat()` a file, the worker needs:
1. **Execute permission (`x`)** on EVERY ancestor directory in the path
2. **Read permission (`r`)** on the file itself

When directories lack `x`:
```
drw-r--r-- 2 root root 4096 Jun 23 23:03 img/  ← no x → nginx can't enter!
```

## Root Cause #2 (MORE DANGEROUS): `chmod 644 *` Kills Directories

**This is the real recurring bug.** The habit of running `chmod 644 /var/www/html/bidding/*` after every edit is DESTRUCTIVE:

```bash
chmod 644 /var/www/html/bidding/*
# ↑ The * glob matches DIRECTORIES too!
# img/ was drwxr-xr-x → becomes drw-r--r-- (x stripped)
# img_gen/ was drwxr-xr-x → becomes drw-r--r-- (x stripped)
```

This pattern was used after every terminal edit in the conversation. Each time it ran, it silently broke all image directories until someone noticed the 404.

### ⛔ FORBIDDEN COMMAND
```bash
chmod 644 /var/www/html/bidding/*     # NEVER USE THIS
```

### ✅ CORRECT COMMAND
```bash
# Fix files only, never directories
find /var/www/html/bidding -maxdepth 1 -type f -exec chmod 644 {} \;
# Fix directories that need it
chmod 755 /var/www/html/bidding/img /var/www/html/bidding/img_gen
```

Or use the single-safe-command approach:
```bash
chmod -R a+rX /var/www/html/bidding/
# a+rX = add read to all, add execute ONLY where it already exists (directories keep x)
```

## Diagnosis

```bash
# Check nginx error log
tail -20 /var/log/nginx/error.log | grep "Permission denied"
# Output:
# stat() "/var/www/html/bidding/img/logo.png" failed (13: Permission denied)

# Check directory permissions
ls -ld /var/www/html/bidding/img/ /var/www/html/bidding/img_gen/
# If output shows drw-r--r-- (no x for others), the directory needs fixing
```

## Prevention in polish_report.py (v6+)

The polish script now handles permissions safely after rewriting index.html:

```python
if modified:
    INDEX.write_text(html, encoding="utf-8")
    # Safely fix file permissions WITHOUT touching directories
    for f in Path("/var/www/html/bidding").glob("*"):
        if f.is_file():
            f.chmod(0o644)
    for d in ["/var/www/html/bidding/img", "/var/www/html/bidding/img_gen"]:
        subprocess.run(["chmod", "755", d])
```

## Verification

```bash
curl -sI https://www.yfzx.online/bidding/img/logo.png | head -1
# Must return: HTTP/1.1 200 OK
```

## Timeline

| Date | File | Root Cause | Fix |
|:--|:--|:--|:--|
| 2026-06-24 | `img_gen/cover_*.png` | Directory lacked x | `chmod 755 img_gen` |
| 2026-06-26 AM | `img/logo.png` | Logo replaced, dir permission not set | `chmod 755 img` |
| 2026-06-26 PM | `img/logo.png` again | **`chmod 644 *` destroyed dir x-bit** | polish v6 built-in fix |
