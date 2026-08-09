#!/usr/bin/env python3
"""
文鳐智投 - GitHub Trending 每周自动同步守护进程
=================================================
环境无 systemd / cron 时的替代方案（常驻调度器）

触发规则：每周一 北京时间 03:00:00（Asia/Shanghai）
特性：
  · 首次启动时若检测到本周尚未成功跑过，则立即补跑（可通过 --no-catch-up 跳过）
  · 支持 start / stop / status / restart / run-now
  · PID 文件：/tmp/wenyao-github-trending-scheduler.pid
  · 日志文件：/tmp/wenyao-github-trending-scheduler.log
"""
import os
import sys
import time
import json
import signal
import logging
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # py<3.9
    ZoneInfo = None
    try:
        from backports.zoneinfo import ZoneInfo  # type: ignore
    except Exception:
        ZoneInfo = None

THIS_DIR = Path(__file__).resolve().parent
WORK_SCRIPT = THIS_DIR / "github_trending_sync.py"
PYTHON = sys.executable
PID_FILE = Path("/tmp/wenyao-github-trending-scheduler.pid")
LOG_FILE = Path("/tmp/wenyao-github-trending-scheduler.log")
STATE_FILE = Path("/tmp/wenyao-github-trending-state.json")
TZ_NAME = "Asia/Shanghai"
SCHED_DOW = 0  # Monday (0=Mon ... 6=Sun)
SCHED_HOUR = 3
SCHED_MIN = 0


# ========== timezone helpers ==========
def get_cn_now() -> datetime:
    if ZoneInfo:
        return datetime.now(ZoneInfo(TZ_NAME))
    # 降级：UTC + 8h
    return datetime.utcnow() + timedelta(hours=8)


def get_cn(t: datetime) -> datetime:
    """把一个带时区/naive时间统一成北京时间"""
    if ZoneInfo:
        if t.tzinfo is None:
            return t.replace(tzinfo=ZoneInfo(TZ_NAME))
        return t.astimezone(ZoneInfo(TZ_NAME))
    if t.tzinfo is None:
        return t
    return t.astimezone(type("FakeUTC", (), {"tzname": lambda self, d: "UTC"})()) + timedelta(hours=8)  # noqa


def next_run_dt() -> datetime:
    """计算下一个周一 03:00:00 北京时间"""
    now = get_cn_now()
    target_today = now.replace(hour=SCHED_HOUR, minute=SCHED_MIN, second=0, microsecond=0)
    days_ahead = (SCHED_DOW - now.weekday()) % 7
    candidate = target_today + timedelta(days=days_ahead)
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


# ========== state ==========
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        logging.warning("写入state失败: %s", e)


def iso_cn_week_marker(dt: datetime) -> str:
    """返回 YYYY-Www 作为“周几已经跑过”的标记"""
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


# ========== job ==========
def run_sync_once() -> tuple[int, str]:
    """执行一次同步脚本，返回 (退出码, 输出末尾500字节)"""
    logging.info("开始执行: %s %s", PYTHON, WORK_SCRIPT)
    t0 = time.time()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.run(
        [PYTHON, str(WORK_SCRIPT), "sync"],
        cwd=str(THIS_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=60 * 30,  # 最多 30 分钟
    )
    cost = time.time() - t0
    tail = (proc.stdout or "") + (proc.stderr or "")
    tail = tail[-800:] if len(tail) > 800 else tail
    logging.info("执行完成 rc=%s 耗时 %.1fs 末尾输出:\n%s", proc.returncode, cost, tail or "(无输出)")
    return proc.returncode, tail


# ========== scheduler ==========
def scheduler_loop(catch_up: bool) -> None:
    state = load_state()
    this_week = iso_cn_week_marker(get_cn_now())
    last_ok_week = state.get("last_success_week")

    if catch_up and last_ok_week != this_week:
        logging.info("[CatchUp] 本周(%s)尚无成功记录，立即补跑一次（last=%s）", this_week, last_ok_week)
        rc, _ = run_sync_once()
        if rc == 0:
            state["last_success_week"] = this_week
            state["last_success_at"] = get_cn_now().isoformat(timespec="seconds")
            save_state(state)
        else:
            logging.warning("[CatchUp] 补跑失败 rc=%s，将在稍后重试/等待下一次定时", rc)
    else:
        logging.info("本周(%s)已成功执行过(last=%s)或禁用补跑，跳过 CatchUp", this_week, last_ok_week)

    while True:
        nxt = next_run_dt()
        now = get_cn_now()
        sleep_sec = max(0.0, (nxt - now).total_seconds())
        logging.info("下次触发时间(北京时间): %s (距离现在 %.0f 秒 ≈ %.1f 小时)",
                     nxt.strftime("%Y-%m-%d %H:%M:%S %A"), sleep_sec, sleep_sec / 3600.0)
        # 分段 sleep，最长 60s，以便及时响应 SIGTERM 停止
        end_ts = time.time() + sleep_sec
        while True:
            remaining = end_ts - time.time()
            if remaining <= 0:
                break
            time.sleep(min(60.0, remaining))

        # 到点执行
        week_marker = iso_cn_week_marker(get_cn_now())
        rc, _ = run_sync_once()
        if rc == 0:
            state["last_success_week"] = week_marker
            state["last_success_at"] = get_cn_now().isoformat(timespec="seconds")
        state["last_attempt_week"] = week_marker
        state["last_attempt_at"] = get_cn_now().isoformat(timespec="seconds")
        state["last_rc"] = rc
        save_state(state)


# ========== PID management ==========
def read_pid() -> int | None:
    if PID_FILE.exists():
        try:
            p = int(PID_FILE.read_text().strip())
            return p
        except Exception:
            return None
    return None


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def clear_pid():
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception:
        pass


def setup_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(LOG_FILE, encoding="utf-8")]
    if sys.stdout.isatty():
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def cmd_start(catch_up: bool, foreground: bool) -> int:
    pid = read_pid()
    if pid and pid_alive(pid):
        print(f"[SKIP] 调度器已在运行，PID={pid}。日志: {LOG_FILE}")
        return 0
    if pid:
        print(f"[INFO] 清理残留PID文件({pid}已失效)")
        clear_pid()

    if not foreground:
        # 简单双 fork 后台化
        if os.fork() > 0:
            time.sleep(0.3)
            np = read_pid()
            print(f"[OK] 调度器已在后台启动，PID={np or '?'}。日志: {LOG_FILE}")
            return 0
        os.setsid()
        if os.fork() > 0:
            os._exit(0)
        # redirect stdio
        devnull = open(os.devnull, "r+b")
        os.dup2(devnull.fileno(), 0)

    setup_logging()
    PID_FILE.write_text(str(os.getpid()))

    def _graceful(signum, frame):
        logging.info("收到信号 %s，优雅退出", signum)
        clear_pid()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _graceful)
    signal.signal(signal.SIGINT, _graceful)

    logging.info("=" * 60)
    logging.info("调度器启动 PID=%s  catch_up=%s  TZ=%s  work_script=%s",
                 os.getpid(), catch_up, TZ_NAME, WORK_SCRIPT)
    try:
        scheduler_loop(catch_up=catch_up)
    finally:
        clear_pid()
    return 0


def cmd_stop() -> int:
    pid = read_pid()
    if not pid or not pid_alive(pid):
        print("[OK] 调度器未在运行")
        clear_pid()
        return 0
    print(f"[STOP] 发送 SIGTERM 到 PID={pid} ...")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    for _ in range(20):
        if not pid_alive(pid):
            break
        time.sleep(0.25)
    if pid_alive(pid):
        print(f"[FORCE] 进程未退出，发送 SIGKILL 到 PID={pid}")
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
    clear_pid()
    print("[OK] 已停止")
    return 0


def cmd_status() -> int:
    pid = read_pid()
    alive = pid and pid_alive(pid)
    print(f"调度器状态 : {'RUNNING' if alive else 'STOPPED'}  PID={pid or '-'}")
    print(f"PID 文件   : {PID_FILE}")
    print(f"日志文件   : {LOG_FILE}")
    print(f"状态文件   : {STATE_FILE}")
    print(f"定时规则   : 每周一 北京时间 {SCHED_HOUR:02d}:{SCHED_MIN:02d}")
    print(f"下次触发(CN): {next_run_dt().strftime('%Y-%m-%d %H:%M:%S %A')}")
    st = load_state()
    if st:
        print(f"状态详情   : {json.dumps(st, ensure_ascii=False)}")
    if LOG_FILE.exists():
        size = LOG_FILE.stat().st_size
        print(f"--- 日志末尾(30行, 最近size={size}) ---")
        try:
            with LOG_FILE.open("r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                print("".join(lines[-30:]))
        except Exception as e:
            print(f"(读日志失败: {e})")
    return 0


def cmd_run_now() -> int:
    setup_logging()
    logging.info("[run-now] 手动触发执行...")
    rc, tail = run_sync_once()
    state = load_state()
    if rc == 0:
        state["last_success_week"] = iso_cn_week_marker(get_cn_now())
        state["last_success_at"] = get_cn_now().isoformat(timespec="seconds")
    state["last_attempt_week"] = iso_cn_week_marker(get_cn_now())
    state["last_attempt_at"] = get_cn_now().isoformat(timespec="seconds")
    state["last_rc"] = rc
    save_state(state)
    print(f"[DONE] 执行退出码={rc}")
    if tail:
        print("----- 输出末尾 -----")
        print(tail)
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description="文鳐智投 GitHub Trending 每周同步调度器")
    ap.add_argument("cmd", nargs="?", default="start",
                    choices=["start", "stop", "restart", "status", "run-now"],
                    help="命令: start(默认)|stop|restart|status|run-now")
    ap.add_argument("--no-catch-up", action="store_true", help="start 时若本周没跑过也不立即补跑")
    ap.add_argument("-f", "--foreground", action="store_true", help="start 时前台运行(不守护)")
    args = ap.parse_args()

    if args.cmd == "start":
        return cmd_start(catch_up=not args.no_catch_up, foreground=args.foreground)
    if args.cmd == "stop":
        return cmd_stop()
    if args.cmd == "restart":
        cmd_stop()
        time.sleep(0.5)
        return cmd_start(catch_up=not args.no_catch_up, foreground=args.foreground)
    if args.cmd == "status":
        return cmd_status()
    if args.cmd == "run-now":
        return cmd_run_now()
    return 2


if __name__ == "__main__":
    sys.exit(main())
