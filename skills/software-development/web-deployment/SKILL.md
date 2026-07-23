---
name: web-deployment
description: Deploy and troubleshoot static web apps on Nginx — permissions, file corruption, cache busting, DNS.
triggers:
  - "deploy the site"
  - "nginx 403"
  - "page not loading"
  - "static files not serving"
  - "permission denied nginx"
  - "file corrupted after write"
  - "更新日志"
  - "发布"
  - "部署"
  - "changelog"
  - "无法访问"
---

# Web Deployment — Nginx Static Serving

## 1. Permission Fix (most common 403 cause)

After creating or updating any file served by Nginx:

```bash
chmod 755 /var/www/html/SITE_DIR
chmod 644 /var/www/html/SITE_DIR/*.html /var/www/html/SITE_DIR/*.js /var/www/html/SITE_DIR/*.json
chmod 755 /var/www/html/SITE_DIR/img/
chmod 644 /var/www/html/SITE_DIR/img/*
```

Pitfall: Files created by root default to 600 — Nginx (www-data) cannot read them → 403.

## 2. Cache Busting

Always version the JS/CSS URL in HTML templates to defeat browser cache:

```html
<script src="app.js?v=NEXT_VERSION"></script>
```

Bump the version every time `app.js` changes. Update BOTH the template source file AND the deployed HTML. Old browsers hold stale JS → bugs that appear "not fixed."

## 3. File Corruption from `execute_code` read_file

**CRITICAL PITFALL:** `hermes_tools.read_file()` in `execute_code` returns content with `LINE_NUM|` prefixes on every line. Writing that content back to disk embeds the prefixes, corrupting the file.

**DO NOT do this:**
```python
from hermes_tools import read_file, write_file
r = read_file("foo.py")
js = r["content"]       # ← contains "1|#!/usr/bin/env python3" etc.
write_file("foo.py", js) # ← corrupted!
```

**INSTEAD use terminal directly:**
```bash
python3 << 'PYEOF'
with open('file.py') as f:
    content = f.read()
# ... modify ...
with open('file.py', 'w') as f:
    f.write(content)
PYEOF
```

**If already corrupted**, strip embedded prefixes:
```bash
python3 -c "
import re
c = open('file.py').read()
for _ in range(10):
    c = re.sub(r'^\d+\|', '', c, flags=re.MULTILINE)
open('file.py','w').write(c)
"
```

## 4. Nginx `alias` + `try_files` Gotcha

With `alias`, `try_files $uri` resolves relative to the default root, not the alias path. Prefer this pattern:

```nginx
location /SITE/ {
    alias /var/www/html/SITE/;
    index index.html;
    try_files $uri $uri/ =404;
}
```

## 5. Domain DNS Check

If a domain resolves locally but not from the server or externally:
```bash
# Check what the server's resolver sees
resolvectl query DOMAIN
# Test directly by IP
curl -sk -H "Host: DOMAIN" https://127.0.0.1/PATH
```
Common: domain registered but no A record pointing to server IP → add at registrar.

## 6. "Page Not Accessible" Diagnostic Workflow

When a user reports a page is down or not accessible, follow this diagnostic sequence BEFORE making config changes:

```bash
# 1. Quick health check — does Nginx respond at all?
curl -sI https://example.com/ 2>&1 | head -3

# 2. Check if Nginx was RECENTLY RESTARTED (most common cause of transient outages)
systemctl status nginx --no-pager | grep -E "Active:|since"
# If "Active: active (running) since <TIME>" is minutes/hours ago, it was restarted!
# Transient outage during restart window is the likely cause.

# 3. Check system journal for the restart reason
journalctl -u nginx --since "1 hour ago" --no-pager | grep -iE "stopping|deactivated|starting|error"

# 4. Check for health-guard timer
systemctl is-active nginx-healthguard.timer 2>/dev/null || echo "NO HEALTH GUARD — Nginx crash will cause silent outage!"

# 5. Page-level verification
curl -s -o /dev/null -w "HTTP %{http_code} %{size_download}B %{time_total}s" https://example.com/page
```

**Key insight**: A transient outage during Nginx restart (even 1-2 seconds) is the root cause when the user says "it was down earlier but works now." Don't just dismiss it — the fact that it restarted at all needs investigation.

## 7. Health Guard Deployment

Deploy a systemd timer to auto-restart Nginx if it dies:

```bash
# /etc/systemd/system/nginx-healthguard.service
[Unit]
Description=nginx health guard — restart if dead
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'systemctl is-active --quiet nginx || { echo "$(date): nginx dead, restarting" >> /var/log/nginx-healthguard.log; systemctl restart nginx; }'

# /etc/systemd/system/nginx-healthguard.timer
[Unit]
Description=nginx health guard timer
[Timer]
OnCalendar=*-*-* *:*:00/120
[Install]
WantedBy=timers.target
```

Verify: `systemctl enable --now nginx-healthguard.timer && systemctl list-timers nginx-healthguard`

## 8. Browser Hard-Refresh After Deploy

After deploying fixes, the user may still see old errors due to browser caching of the 403/404 response. Instruct them to:
- `Ctrl+Shift+R` (force refresh)
- Or open in incognito/private mode
- Check `tail -f /var/log/nginx/access.log` to verify their IP made a fresh request
