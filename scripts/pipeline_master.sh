#!/bin/bash
# 文鳐智投 全流程主控脚本 v2
# 由 systemd timer 直接调用，不经过 LLM，避免 API 断连
# v2: 使用 venv Python（含 bs4/lxml/requests 等依赖）
set -e
cd /root/.hermes/profiles/wenyaozhitou
LOG="/var/log/wenyao_pipeline.log"
PY="/usr/local/lib/hermes-agent/venv/bin/python3"

log() { echo "[$(date '+%m-%d %H:%M:%S')] $1" | tee -a "$LOG"; }

log "========== 文鳐智投 全流程启动 =========="

# 阶段1: 全平台采集（四连跑）
log "阶段1/6: 全平台采集"

log "  1a: crawl_pipeline.py（专属5平台）"
timeout 300 $PY scripts/crawl_pipeline.py 2>&1 | tee -a "$LOG" || log "  ⚠️ pipeline 超时或出错"

log "  1b: dedicated_adapters.py（三峡/国电投/中广核）"
timeout 300 $PY scripts/dedicated_adapters.py 2>&1 | tee -a "$LOG" || log "  ⚠️ dedicated 超时或出错"

log "  1c: batch_crawler.py（87站通用）"
timeout 600 $PY scripts/batch_crawler.py 2>&1 | tee -a "$LOG" || log "  ⚠️ batch_crawler 超时或出错"

log "  1d: chromium_crawler.py（JS增强）"
timeout 180 $PY scripts/chromium_crawler.py 2>&1 | tee -a "$LOG" || log "  ⚠️ chromium 超时或出错"

# 阶段2: 数据清洗
log "阶段2/6: 数据清洗"
$PY -c "
import sqlite3
conn = sqlite3.connect('data/bidding.db')
cur = conn.cursor()
cur.execute(\"DELETE FROM bidding_notices WHERE title LIKE '%终止公告%'\")
cur.execute(\"DELETE FROM bidding_notices WHERE title LIKE '招标网%' OR title LIKE '国能e招%'\")
conn.commit()
conn.close()
print('清洗完成')
" 2>&1 | tee -a "$LOG"

# 阶段3: 竞品追踪
log "阶段3/6: 竞品追踪"
$PY scripts/competitor_tracker.py 2>&1 | tee -a "$LOG" || log "  ⚠️ 竞品追踪出错"

# 阶段4: 生成报告
log "阶段4/6: 生成报告"
$PY scripts/report_generator.py 2>&1 | tee -a "$LOG"
chmod -R 755 /var/www/html/bidding/ 2>/dev/null
find /var/www/html/bidding -type f -exec chmod 644 {} \; 2>/dev/null
chmod -R 755 /var/www/html/bidding/img_gen 2>/dev/null  # 封面图目录必须nginx可读

# 阶段5: 企微推送
log "阶段5/6: 企微推送"
$PY scripts/wecom_push.py 2>&1 | tee -a "$LOG" || log "  ⚠️ 推送出错"

# 阶段6: DB维护
log "阶段6/6: 数据库维护"
$PY -c "
import sqlite3
conn = sqlite3.connect('data/bidding.db')
conn.execute('ANALYZE')
conn.execute(\"DELETE FROM crawl_log WHERE crawl_time < datetime('now','-90 days')\")
conn.commit()
conn.close()
print('DB维护完成')
" 2>&1 | tee -a "$LOG"

# 统计
BID=$($PY -c "import sqlite3;c=sqlite3.connect('data/bidding.db');print(c.execute('SELECT count(*) FROM bidding_notices WHERE relevance_score>0').fetchone()[0])")
WIN=$($PY -c "import sqlite3;c=sqlite3.connect('data/bidding.db');print(c.execute('SELECT count(*) FROM winning_notices WHERE relevance_score>0').fetchone()[0])")
log "========== 完成: 招标${BID} + 中标${WIN} = $((BID+WIN)) 条 =========="

# 日志轮转
tail -500 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
