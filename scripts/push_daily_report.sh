#!/bin/bash
# 文鳐智投 日报生成+推送 — 每晚20:00执行
set -e
cd /root/.hermes/profiles/wenyaozhitou
PY="/usr/local/lib/hermes-agent/venv/bin/python3"
TODAY=$(date +%Y-%m-%d)

echo "[$(date)] 生成日报..."
$PY scripts/daily_report.py

if [ -f "/var/www/html/bidding/report-${TODAY}.html" ]; then
    echo "日报已生成: /var/www/html/bidding/report-${TODAY}.html"
    chmod 644 "/var/www/html/bidding/report-${TODAY}.html"
else
    echo "❌ 日报生成失败"
    exit 1
fi
