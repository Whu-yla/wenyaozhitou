#!/usr/bin/env python3
"""Nginx 端口守护 + 企微告警 + 自愈
每分钟运行，检测 80 端口健康：
  1. 80 被非 nginx 占用 → 杀进程 → 重启 nginx → 企微推送
  2. nginx 没跑 → 启动 nginx → 企微推送
  3. 网站 HTTP 200 正常 → 静默（不发告警）
"""

import subprocess, socket, os, json, time, urllib.request
from datetime import datetime

# ── 配置 ──
WECOM_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0256f02d-7368-4214-9c99-9c53ce449e92"
CHECK_URL = "https://yfzx.online/bidding/"
STATE_FILE = "/tmp/nginx_guardian_state.json"
COOLDOWN_MINUTES = 30  # 同一故障 30 分钟内不重复告警

HOSTNAME = socket.gethostname()

def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", 1

def send_wecom(markdown_content):
    """通过企业微信 Webhook 推送告警"""
    payload = json.dumps({
        "msgtype": "markdown",
        "markdown": {"content": markdown_content}
    }).encode("utf-8")
    try:
        req = urllib.request.Request(WECOM_WEBHOOK, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("errcode") == 0:
                print("📱 企微告警已推送")
                return True
            else:
                print(f"❌ 企微推送失败: {result}")
                return False
    except Exception as e:
        print(f"❌ 企微推送异常: {e}")
        return False

def check_cooldown(alert_key):
    """检查是否在冷却期内，避免重复告警"""
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    last = state.get(alert_key, 0)
    if time.time() - last < COOLDOWN_MINUTES * 60:
        return True
    state[alert_key] = time.time()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)
    return False

def who_owns_port_80():
    """返回占用 80 端口的进程信息 (pid, name) 或 None"""
    out, _, _ = run("ss -tlnp 'sport = :80' 2>/dev/null")
    for line in out.split("\n"):
        if ":80 " not in line:
            continue
        import re
        m = re.search(r'pid=(\d+)', line)
        if m:
            pid = int(m.group(1))
            pname, _, _ = run(f"cat /proc/{pid}/comm 2>/dev/null")
            return pid, pname.strip()
    return None

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    issues = []

    # ── 检查 1: 80 端口归属 ──
    owner = who_owns_port_80()
    nginx_running = False
    _, _, nginx_rc = run("systemctl is-active --quiet nginx")

    if owner:
        pid, pname = owner
        if pname == "nginx":
            nginx_running = True
        else:
            issues.append(f"> 🔴 80端口被 **{pname}** (PID={pid}) 占用")
            run(f"kill -9 {pid}")
            time.sleep(0.5)
    else:
        issues.append("> 🔴 80端口无人监听")

    # ── 检查 2: nginx 服务状态 ──
    if nginx_rc != 0 and not nginx_running:
        issues.append("> 🔴 nginx 服务未运行")

    # ── 自愈 ──
    if issues:
        run("systemctl start nginx")
        time.sleep(1)
        _, _, rc = run("systemctl is-active --quiet nginx")
        if rc == 0:
            issues.append("> ✅ 已自动重启 nginx")
        else:
            issues.append("> ❌ **nginx 重启失败！请立即处理！**")

    # ── 检查 3: HTTP 可达性 ──
    _, _, curl_rc = run(f"curl -sI --connect-timeout 5 {CHECK_URL} 2>/dev/null | head -1 | grep -q '200 OK'")
    if curl_rc != 0:
        issues.append(f"> ❌ [{CHECK_URL}]({CHECK_URL}) 返回非200")

    # ── 决定是否告警 ──
    if not issues:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        return

    alert_key = "|".join(sorted(issues))
    if check_cooldown(alert_key):
        print(f"[{now}] 故障已在冷却期，跳过告警")
        return

    md = f"""## 🚨 Nginx 端口异常告警
> 服务器: **{HOSTNAME}** (yfzx.online)
> 时间: {now}

**故障详情:**
{chr(10).join(issues)}

---
自动恢复已执行，请检查: [bidding看板]({CHECK_URL})
© 中南电力设计院数智科技 · 文鳐智投 2026"""

    send_wecom(md)
    print(f"[{now}] 告警: " + "; ".join(issues))

if __name__ == "__main__":
    main()
