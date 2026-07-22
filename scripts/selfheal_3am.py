#!/usr/bin/env python3
"""
文鳐智投 凌晨3点自检脚本 v2
- 监控页面健康检查
- 读取所有用户反馈
- 按问题类型聚类分析根因
- 自动修复系统缺陷
- 写入修复日志
"""
import json, sqlite3, os, re, sys, requests
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

DB = "/root/.hermes/profiles/wenyaozhitou/data/bidding.db"
FEEDBACK_FILE = "/var/www/html/bidding/data/feedback.json"
LOG_FILE = "/var/log/wenyao_selfheal.log"
SCRIPTS_DIR = "/root/.hermes/profiles/wenyaozhitou/scripts"
BASE_URL = "https://yfzx.online"

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')
    print(line)

log("========== 凌晨自检 v2 启动 ==========")

# ═══ 0. 监控页面健康检查 ═══
log("📡 页面健康检查")
pages = {
    "主页": "/bidding/",
    "日报": "/bidding/report-" + datetime.now().strftime("%Y-%m-%d") + ".html",
    "更新日志": "/bidding/changelog.html",
}
alerts = []
for name, path in pages.items():
    try:
        r = requests.get(BASE_URL + path, timeout=10, allow_redirects=True)
        has_chat = 'chat-widget' in r.text
        size_kb = len(r.text) // 1024
        status = "✅" if r.status_code == 200 else "❌"
        chat_icon = "💬" if has_chat else "⚠️无对话框"
        log(f"  {status} {name}: HTTP{r.status_code} {size_kb}KB {chat_icon}")
        if r.status_code != 200:
            alerts.append(f"{name} 返回 {r.status_code}")
        if not has_chat:
            alerts.append(f"{name} 缺少对话框")
    except Exception as e:
        log(f"  ❌ {name}: {e}")
        alerts.append(f"{name} 不可达: {e}")

# API检查
apis = {
    "bookmarks": "/bidding/api/",
    "chat": "/bidding/api/chat",
    "data": "/bidding/api/data?limit=1",
}
for name, path in apis.items():
    try:
        r = requests.get(BASE_URL + path, timeout=10)
        ok = r.status_code == 200
        log(f"  {'✅' if ok else '❌'} API {name}: HTTP{r.status_code}")
        if not ok:
            alerts.append(f"API {name} 返回 {r.status_code}")
    except Exception as e:
        log(f"  ❌ API {name}: {e}")
        alerts.append(f"API {name} 不可达: {e}")

# 数据库检查
conn = sqlite3.connect(DB)
total = conn.execute("SELECT COUNT(*) FROM bidding_notices WHERE relevance_score>0").fetchone()[0]
total_w = conn.execute("SELECT COUNT(*) FROM winning_notices WHERE relevance_score>0").fetchone()[0]
log(f"  📊 DB: 招标{total} 中标{total_w}")
conn.close()

# Nginx检查
import subprocess
nginx = subprocess.run(["systemctl", "is-active", "nginx"], capture_output=True, text=True)
log(f"  {'✅' if 'active' in nginx.stdout else '❌'} Nginx: {nginx.stdout.strip()}")

if alerts:
    log(f"⚠️ 发现 {len(alerts)} 个问题:")
    for a in alerts:
        log(f"  - {a}")

# ═══ 1. 读取反馈 ═══
if not os.path.exists(FEEDBACK_FILE):
    log("无反馈文件，跳过")
    sys.exit(0)

with open(FEEDBACK_FILE) as f:
    feedback = json.load(f)

if not feedback:
    log("无反馈记录")
    sys.exit(0)

# 只处理24小时内的新反馈
cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
new_fb = [f for f in feedback if f.get('time', '') >= cutoff]
if not new_fb:
    log(f"共{len(feedback)}条反馈，24h内无新增")
    sys.exit(0)

log(f"共{len(feedback)}条反馈，24h内{len(new_fb)}条新增")

# 2. 聚类分析
conn = sqlite3.connect(DB)

# 关键词聚类
issue_patterns = Counter()
for fb in new_fb:
    reason = fb.get('reason', '')
    # 提取问题类型
    if '链接' in reason or '打不开' in reason:
        issue_patterns['link_dead'] += 1
    elif '限价' in reason or '预算' in reason or '金额' in reason or '万元' in reason:
        issue_patterns['budget_missing'] += 1
    elif '地点' in reason or '地区' in reason:
        issue_patterns['region_missing'] += 1
    elif '招标人' in reason or '采购人' in reason:
        issue_patterns['owner_missing'] += 1
    elif '中标' in reason and ('没有' in reason or '抓' in reason):
        issue_patterns['winner_missing'] += 1
    elif '截止' in reason or '过期' in reason or '资格预审' in reason:
        issue_patterns['expired_notice'] += 1
    else:
        issue_patterns['other'] += 1

log(f"问题分布: {dict(issue_patterns)}")

# 3. 自动修复
fixes_applied = []

# ── 链接失效检测 ──
if issue_patterns.get('link_dead', 0) > 0:
    log("🔧 诊断链接失效...")
    # 找被投诉的项目
    complaint_ids = [fb['item_id'] for fb in new_fb if '链接' in fb.get('reason', '') or '打不开' in fb.get('reason', '')]
    for iid in complaint_ids:
        for table in ['bidding_notices', 'winning_notices']:
            row = conn.execute(f"SELECT id, url, publish_date, relevance_score FROM {table} WHERE id=?", (iid,)).fetchone()
            if row:
                url = row[1]
                pub_date = row[2]
                # 尝试检查
                try:
                    import requests
                    r = requests.head(url, timeout=10, allow_redirects=True, headers={'User-Agent': 'Mozilla/5.0'})
                    if r.status_code >= 400:
                        log(f"  Item {iid}: 链接返回{r.status_code}，降权处理")
                        conn.execute(f"UPDATE {table} SET relevance_score=relevance_score*0.3 WHERE id=?", (iid,))
                        fixes_applied.append(f"链接失效降权: item {iid} ({r.status_code})")
                    else:
                        log(f"  Item {iid}: 链接正常({r.status_code})，可能需登录或JS渲染")
                        # 超6个月旧链接降权
                        if pub_date and pub_date < (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d'):
                            conn.execute(f"UPDATE {table} SET relevance_score=relevance_score*0.5 WHERE id=?", (iid,))
                            fixes_applied.append(f"旧链接降权: item {iid}")
                except Exception as e:
                    log(f"  Item {iid}: 链接检查失败 {e}")
                    conn.execute(f"UPDATE {table} SET relevance_score=relevance_score*0.3 WHERE id=?", (iid,))
                    fixes_applied.append(f"链接不可达降权: item {iid}")
                break

# ── 预算缺失回顾 ──
if issue_patterns.get('budget_missing', 0) > 0:
    log("🔧 回顾预算提取...")
    # 检查预算提取函数所有已存数据
    missing = conn.execute(
        "SELECT COUNT(*) FROM bidding_notices WHERE (budget_amount IS NULL OR budget_amount='') AND relevance_score>=60"
    ).fetchone()[0]
    log(f"  仍有{missing}条高相关项目缺失预算")
    # 尝试用增强版正则回填最近的项目
    sys.path.insert(0, SCRIPTS_DIR)
    from crawl_pipeline import extract_budget_from_content
    # 取最近30天缺预算的高相关项目
    rows = conn.execute(
        "SELECT id, raw_html, content_summary FROM bidding_notices WHERE (budget_amount IS NULL OR budget_amount='') AND relevance_score>=60 AND date(publish_date)>=? LIMIT 20",
        ((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),)
    ).fetchall()
    filled = 0
    for row in rows:
        text = (row[1] or '') + (row[2] or '')
        if text:
            budget = extract_budget_from_content(text)
            if budget:
                conn.execute("UPDATE bidding_notices SET budget_amount=? WHERE id=?", (budget, row[0]))
                filled += 1
    if filled:
        log(f"  回填{missing}条中的{filled}条预算")
        fixes_applied.append(f"回填{missing}条预算")

# ── 过期公告清理 ──
if issue_patterns.get('expired_notice', 0) > 0 or issue_patterns.get('link_dead', 0) > 0:
    log("🔧 检查过期公告...")
    # 降权所有超过1年的高评分公告
    year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    old_high = conn.execute(
        "SELECT COUNT(*) FROM bidding_notices WHERE relevance_score>=70 AND publish_date<? AND publish_date!=''",
        (year_ago,)
    ).fetchone()[0]
    if old_high > 0:
        conn.execute(
            "UPDATE bidding_notices SET relevance_score=relevance_score*0.5 WHERE relevance_score>=70 AND publish_date<? AND publish_date!=''",
            (year_ago,)
        )
        log(f"  降权{old_high}条超1年旧公告")
        fixes_applied.append(f"降权{old_high}条超1年旧公告")

conn.commit()
conn.close()

# 4. 写入HOT记忆供下次会话感知
hot_path = Path("/root/.hermes/profiles/wenyaozhitou/memory/hot/HOT_MEMORY.md")
hot_path.parent.mkdir(parents=True, exist_ok=True)
hot_note = f"\n## 🔧 凌晨自检 [{datetime.now().strftime('%Y-%m-%d %H:%M')}]\n"
hot_note += f"- 24h新反馈: {len(new_fb)}条\n"
hot_note += f"- 问题分布: {dict(issue_patterns)}\n"
for fix in fixes_applied:
    hot_note += f"- ✅ {fix}\n"
if not fixes_applied:
    hot_note += "- 无需自动修复\n"

with open(hot_path, 'a') as f:
    f.write(hot_note)

log(f"修复: {len(fixes_applied)}条")
log("========== 自检完成 ==========")
