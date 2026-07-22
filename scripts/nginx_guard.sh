#!/bin/bash
# 文鳐智投 Nginx守护 + API服务守护 — cron watchdog（正常静默，异常才输出）
LOG=/var/log/nginx_guard.log
URL="https://www.yfzx.online/bidding/"
API_URL="https://www.yfzx.online/bidding/api/"
MAX_LOG_LINES=500

alert() {
    local msg="[$(date '+%m-%d %H:%M:%S')] $1"
    echo "$msg" | tee -a "$LOG"
}

# 1. nginx 进程检查
if ! pgrep -x nginx >/dev/null 2>&1; then
    alert "🆘 nginx 进程不存在！正在启动..."
    systemctl start nginx 2>&1 | tee -a "$LOG"
    sleep 2
    if pgrep -x nginx >/dev/null 2>&1; then
        alert "✅ nginx 启动成功"
    else
        alert "💀 nginx 启动失败！请立即检查！"
    fi
fi

# 2. nginx HTTP 健康检查
STATUS=$(curl -sI -o /dev/null -w "%{http_code}" --max-time 10 "$URL" 2>/dev/null)
if [ "$STATUS" != "200" ]; then
    alert "⚠️ ${URL} → HTTP ${STATUS}，尝试 reload..."
    systemctl reload nginx 2>/dev/null
    sleep 2
    STATUS2=$(curl -sI -o /dev/null -w "%{http_code}" --max-time 10 "$URL" 2>/dev/null)
    if [ "$STATUS2" = "200" ]; then
        alert "✅ reload 恢复 (${STATUS}→200)"
    else
        alert "🆘 reload 无效，执行 restart..."
        systemctl restart nginx 2>/dev/null
        sleep 3
        STATUS3=$(curl -sI -o /dev/null -w "%{http_code}" --max-time 10 "$URL" 2>/dev/null)
        alert "restart 后状态: HTTP ${STATUS3}"
    fi
fi

# 3. API 书签/反馈服务守护
if ! pgrep -f bookmark_server.py >/dev/null 2>&1; then
    alert "🆘 bookmark_server 挂了！重启中..."
    nohup /usr/local/lib/hermes-agent/venv/bin/python3 /root/.hermes/profiles/wenyaozhitou/scripts/bookmark_server.py >> /var/log/bookmark_server.log 2>&1 &
    sleep 2
    if pgrep -f bookmark_server.py >/dev/null 2>&1; then
        alert "✅ bookmark_server 恢复"
    else
        alert "💀 bookmark_server 重启失败！"
    fi
fi

# 4. API 端点健康检查
API_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$API_URL" 2>/dev/null)
if [ "$API_CODE" != "200" ]; then
    alert "⚠️ API端点 ${API_URL} → HTTP ${API_CODE}"
fi

# 日志轮转
if [ -f "$LOG" ]; then
    tail -"$MAX_LOG_LINES" "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
fi
