# yfzx.online Nginx Config

Located at: `/etc/nginx/sites-enabled/wiki`

```nginx
server {
    listen 80;
    server_name www.yfzx.online yfzx.online;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name www.yfzx.online yfzx.online;

    ssl_certificate     /etc/nginx/ssl/wiki.pem;
    ssl_certificate_key /etc/nginx/ssl/wiki.key;

    location /bidding/ {
        alias /var/www/html/bidding/;
        index index.html;
        try_files $uri $uri/ =404;
        add_header Cache-Control "public, max-age=300";
        add_header X-Robots-Tag "noindex, nofollow";
    }

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        # ...
    }
}
```

## Bidding Site Directory Structure

```
/var/www/html/bidding/
├── index.html          # Main report
├── changelog.html      # Changelog page
├── app.js             # Frontend JS (versioned via ?v=N in script tag)
├── data.json          # Crawl data for report
├── data_full.json     # Full crawl data
├── img/
│   ├── logo.png       # Custom logo (82443 bytes, uploaded by user)
│   └── category_banners/  # AI-generated cover images (cached)
├── img_gen/
│   └── cache/         # TTS image cache
└── YYYY-MM-DD/        # Daily archives (report_generator auto-creates)
```

## Server Info

- IP: `8.137.179.128`
- Domain: `yfzx.online` (Alibaba DNS, needs A record @ 8.137.179.128)
- DNS resolver: `100.100.2.136`, `100.100.2.138` (Alibaba Cloud internal)
- nginx user: `www-data`
