#!/usr/bin/env python3
"""文鳐智投 书签+反馈 + 静态文件托管 — 端口8090
V2: 新增 /items (分页查询) + /stats (统计概览)
V3: 内嵌 /bidding/* 静态托管（替代 Flask Proxy），单端口提供所有服务"""
import json, os, sys, re, urllib.parse, sqlite3, mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path("/root/.hermes/profiles/wenyaozhitou")
DATA_DIR = Path("/var/www/html/bidding")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = BASE_DIR / "data" / "bidding.db"

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from chat_engine import PRESET_QUESTIONS, chat_with_llm
except ImportError:
    PRESET_QUESTIONS = []
    def chat_with_llm(*a): return "对话引擎暂不可用"

BOOKMARK_FILE = DATA_DIR / "data" / "bookmarks.json"
FEEDBACK_FILE = DATA_DIR / "data" / "feedback.json"
LOG_FILE = DATA_DIR / "data" / "api_server.log"

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{ts}] {msg}\n")
    except: pass

def read_json(path, default=None):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default if default is not None else []

def write_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def cors(h):
    h.send_header('Access-Control-Allow-Origin', '*')
    h.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    h.send_header('Access-Control-Allow-Headers', 'Content-Type')

# ═══════════ Item API helpers ═══════════

ALLOWED_SORTS = {'relevance_score','publish_date','title','budget_amount','fetch_date','id'}

_yesterday_ids_cache = None

def get_yesterday_ids():
    global _yesterday_ids_cache
    if _yesterday_ids_cache is not None:
        return _yesterday_ids_cache
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    archive_file = DATA_DIR / yesterday / 'data.json'
    ids = set()
    if archive_file.exists():
        with open(archive_file) as f:
            archive = json.load(f)
        for item in archive.get('bidding', []) + archive.get('winning', []):
            ids.add(item.get('id'))
    _yesterday_ids_cache = ids
    return ids

def query_items(params):
    """返回 (total, rows)"""
    data_type = params.get('type', ['bidding'])[0]
    page = max(1, int(params.get('page', ['1'])[0]))
    size = min(int(params.get('size', ['20'])[0]), 200)
    offset = (page - 1) * size
    keyword = params.get('q', [None])[0]
    min_score = float(params.get('min_score', ['1'])[0])  # 默认排除0分噪音
    sort_field = params.get('sort', ['relevance_score'])[0]
    sort_dir = params.get('sort_dir', ['desc'])[0].upper()
    date_from = params.get('date_from', [None])[0]
    date_to = params.get('date_to', [None])[0]
    category = params.get('category', [None])[0]
    province = params.get('province', [None])[0]
    budget_min = float(params.get('budget_min', ['0'])[0])
    is_new_today = params.get('is_new_today', ['0'])[0] == '1'  # 服务端过滤今日新增

    if sort_field not in ALLOWED_SORTS:
        sort_field = 'relevance_score'
    if sort_dir not in ('ASC', 'DESC'):
        sort_dir = 'DESC'

    table = 'bidding_notices' if data_type == 'bidding' else 'winning_notices'

    where = ['relevance_score >= ?']
    sql_params = [min_score]

    if keyword:
        where.append('(title LIKE ? OR procurement_owner LIKE ? OR content_summary LIKE ?)')
        kw = f'%{keyword}%'
        sql_params.extend([kw, kw, kw])
    if date_from:
        where.append('publish_date >= ?')
        sql_params.append(date_from)
    if date_to:
        where.append('publish_date <= ?')
        sql_params.append(date_to)
    if category:
        where.append('category = ?')
        sql_params.append(category)
    if province:
        where.append('province = ?')
        sql_params.append(province)
    if budget_min:
        where.append('CAST(budget_amount AS REAL) >= ?')
        sql_params.append(budget_min)

    where_clause = ' AND '.join(where)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    total = conn.execute(
        f'SELECT COUNT(*) FROM {table} WHERE {where_clause}', sql_params
    ).fetchone()[0]

    cols = ('id, title, url as source_url, source_site, notice_type, publish_date, '
            'relevance_score, budget_amount, region, procurement_owner, category, '
            'province, fetch_date, content_summary')

    if table == 'winning_notices':
        cols = cols.replace('notice_type', "'winning' as notice_type")
        cols = cols.replace('budget_amount', "'' as budget_amount")
        cols = cols.replace('procurement_owner', "'' as procurement_owner")
        cols = cols.replace('category', "'' as category")
        cols = cols.replace('province', "'' as province")

    rows = [dict(r) for r in conn.execute(
        f'SELECT {cols} FROM {table} WHERE {where_clause} '
        f'ORDER BY {sort_field} {sort_dir}, id DESC LIMIT ? OFFSET ?',
        sql_params + [size, offset]
    )]
    conn.close()

    yesterday_ids = get_yesterday_ids()
    for row in rows:
        row['is_new_today'] = 1 if row.get('id') not in yesterday_ids else 0

    # 服务端过滤今日新增 — 减少响应体积 92%（306KB→24KB）
    if is_new_today:
        rows = [r for r in rows if r['is_new_today']]
        total = sum(1 for r in rows)  # 总数也应反映过滤后的

    return total, rows

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200); cors(self); self.end_headers()

    def _resolve_api_path(self):
        """剥离 /bidding/api 前缀，返回内部逻辑使用的干净 path（带 query）。"""
        raw = self.path
        if raw.startswith('/bidding/api/'):
            return raw[len('/bidding/api'):]  # -> /items?... /stats?...
        if raw == '/bidding/api':
            return '/stats'
        return raw

    def do_GET(self):
        # 静态文件: /bidding/... / (redirect)
        path = self.path.split('?', 1)[0]
        if path == '/' or path == '':
            self.send_response(302)
            self.send_header('Location', '/bidding/index.html')
            self.end_headers()
            return
        if path.startswith('/bidding/') or path == '/bidding':
            ap = self._resolve_api_path()
            # 若剥离后仍然是 API 路由（表明原 path 就是 /bidding/api/...）
            if self.path.startswith('/bidding/api/') or self.path.startswith('/bidding/api?'):
                self.path = ap
            else:
                # 纯静态文件
                return self.handle_static()

        p = self.path
        if p.startswith('/items'):
            self.handle_items()
        elif p.startswith('/stats'):
            self.handle_stats()
        elif p.startswith('/feedback'):
            self.handle_get_feedback()
        elif p.startswith('/chat'):
            self.handle_get_chat()
        elif p.startswith('/data'):
            self.handle_get_data()
        elif p.startswith('/tech/summary'):
            self.handle_tech_summary()
        elif p.startswith('/tech/recommendations'):
            self.handle_tech_recommendations()
        elif p.startswith('/tech/github'):
            self.handle_github_energy()
        elif p.startswith('/tech/notice'):
            self.handle_tech_for_notice()
        else:
            self.handle_get_bookmarks()

    def do_POST(self):
        if self.path.startswith('/bidding/api/') or self.path == '/bidding/api':
            self.path = self._resolve_api_path()
        if self.path.startswith('/feedback'):
            self.handle_post_feedback()
        elif self.path.startswith('/chat'):
            self.handle_post_chat()
        else:
            self.handle_post_bookmarks()

    # ═══ 静态文件托管 ═══
    def handle_static(self):
        # 去掉 /bidding/ 前缀
        rel = self.path.split('?', 1)[0]
        if rel == '/bidding':
            rel = '/bidding/'
        if rel.startswith('/bidding/'):
            rel = rel[len('/bidding/'):]
        else:
            rel = rel.lstrip('/')
        rel = rel.lstrip('/')
        if rel == '' or rel.endswith('/'):
            rel += 'index.html'
        # 防 ../ 穿越
        candidate = (DATA_DIR / rel).resolve()
        try:
            candidate.relative_to(DATA_DIR.resolve())
        except Exception:
            self.send_error(403, "Forbidden")
            return
        if not candidate.exists() or not candidate.is_file():
            self.send_error(404, "Not Found")
            return
        ctype = (mimetypes.guess_type(str(candidate))[0] or 'application/octet-stream')
        try:
            data = candidate.read_bytes()
        except Exception:
            self.send_error(500, "Read Error")
            return
        self.send_response(200)
        self.send_header('Content-Type', ctype + '; charset=utf-8' if ctype.startswith(('text/','application/json','application/javascript')) else ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'public, max-age=60')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ═══ 分页查询 ═══
    def handle_items(self):
        try:
            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            total, rows = query_items(params)
            self._json(200, {
                'ok': True,
                'type': params.get('type', ['bidding'])[0],
                'total': total,
                'page': int(params.get('page', ['1'])[0]),
                'size': int(params.get('size', ['20'])[0]),
                'data': rows
            })
        except Exception as e:
            log(f"items错误: {e}")
            self._json(500, {'ok': False, 'error': str(e)})

    # ═══ 统计概览 ═══
    def handle_stats(self):
        try:
            conn = sqlite3.connect(str(DB_PATH))
            bid_total = conn.execute(
                'SELECT COUNT(*) FROM bidding_notices WHERE relevance_score >= 1'
            ).fetchone()[0]
            win_total = conn.execute(
                'SELECT COUNT(*) FROM winning_notices WHERE relevance_score >= 1'
            ).fetchone()[0]
            high_total = conn.execute(
                'SELECT COUNT(*) FROM bidding_notices WHERE relevance_score >= 70'
            ).fetchone()[0] + conn.execute(
                'SELECT COUNT(*) FROM winning_notices WHERE relevance_score >= 70'
            ).fetchone()[0]
            conn.close()

            yesterday_ids = get_yesterday_ids()
            conn = sqlite3.connect(str(DB_PATH))
            today_new = 0
            for table in ('bidding_notices', 'winning_notices'):
                ids = conn.execute(
                    f'SELECT id FROM {table} WHERE relevance_score >= 1'
                ).fetchall()
                today_new += sum(1 for (i,) in ids if i not in yesterday_ids)
            conn.close()

            self._json(200, {
                'ok': True,
                'bidding_total': bid_total,
                'winning_total': win_total,
                'today_total': today_new,
                'high_total': high_total,
                'updated': datetime.now().isoformat()
            })
        except Exception as e:
            log(f"stats错误: {e}")
            self._json(500, {'ok': False, 'error': str(e)})

    # ═══ 书签 ═══
    def handle_get_bookmarks(self):
        bookmarks = read_json(BOOKMARK_FILE, [])
        self._json(200, {"bookmarks": bookmarks, "count": len(bookmarks)})

    def handle_post_bookmarks(self):
        try:
            data = self._read_body()
            bookmarks = data.get('bookmarks', [])
            bookmarks = list(dict.fromkeys([str(b) for b in bookmarks if b]))
            write_json(BOOKMARK_FILE, bookmarks)
            log(f"书签: {len(bookmarks)}条")
            self._json(200, {"ok": True, "count": len(bookmarks)})
        except Exception as e:
            log(f"书签POST错误: {e}")
            self._json(400, {"ok": False, "error": str(e)})

    # ═══ 反馈 ═══
    def handle_get_feedback(self):
        feedback = read_json(FEEDBACK_FILE, [])
        self._json(200, {"feedback": feedback, "count": len(feedback)})

    def handle_post_feedback(self):
        try:
            data = self._read_body()
            item_id = str(data.get('item_id', 'general'))
            fb_type = data.get('type', '')
            reason = data.get('reason', '').strip()
            report_date = data.get('report_date', datetime.now().strftime('%Y-%m-%d'))
            section = data.get('section', 'bidding')
            if fb_type not in ('like', 'dislike', 'general'):
                self._json(400, {"ok": False, "error": "type 无效"})
                return
            if not reason:
                self._json(400, {"ok": False, "error": "请填写反馈内容"})
                return
            feedback = read_json(FEEDBACK_FILE, [])
            client_ip = self.client_address[0]
            if fb_type in ('like', 'dislike'):
                existing = [f for f in feedback
                           if f.get('item_id') == item_id and f.get('ip') == client_ip]
                if existing:
                    self._json(409, {"ok": False, "error": "您已对该项目提交过反馈"})
                    return
            entry = {"item_id": item_id, "type": fb_type, "reason": reason,
                     "report_date": report_date, "section": section,
                     "ip": client_ip, "time": datetime.now().isoformat()}
            feedback.append(entry)
            write_json(FEEDBACK_FILE, feedback)
            log(f"反馈: {fb_type} item={item_id} reason={reason[:50]}")
            if fb_type in ('dislike', 'general') and reason:
                self._write_hot_memory(item_id, reason, section)
            self._json(200, {"ok": True, "entry": entry})
        except Exception as e:
            log(f"反馈POST错误: {e}")
            self._json(500, {"ok": False, "error": str(e)})

    def _write_hot_memory(self, item_id, reason, section):
        hot_path = BASE_DIR / "memory" / "hot" / "HOT_MEMORY.md"
        hot_path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y-%m-%d %H:%M')
        note = (f"\n## 📝 用户反馈 [{ts}]\n- 项目ID: {item_id}\n"
                f"- 分类: {section}\n- 点踩理由: {reason}\n"
                f"- ⚠️ 请在下轮迭代中检查评分关键字/匹配逻辑\n")
        try:
            with open(hot_path, 'a') as f:
                f.write(note)
            log(f"已写入HOT记忆: {item_id}")
        except Exception as e:
            log(f"写入HOT记忆失败: {e}")

    # ═══ 技术匹配 API ═══
    def handle_tech_summary(self):
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            total_matched = conn.execute(
                "SELECT COUNT(*) FROM tech_matches WHERE confidence>0"
            ).fetchone()[0]
            scene_rows = conn.execute("""
                SELECT json_extract(scenarios_json, '$[0].scenario') as scene, COUNT(*) as cnt
                FROM tech_matches WHERE confidence>0
                GROUP BY scene ORDER BY cnt DESC LIMIT 15
            """).fetchall()
            gh_total = conn.execute("SELECT COUNT(*) FROM github_energy").fetchone()[0]
            top_scenes = conn.execute("""
                SELECT top_scene, COUNT(*) as cnt
                FROM github_energy WHERE top_scene != ''
                GROUP BY top_scene ORDER BY cnt DESC LIMIT 10
            """).fetchall()
            conn.close()
            self._json(200, {
                'ok': True,
                'match_summary': {
                    'total_matched': total_matched,
                    'by_scenario': [{'scene': r['scene'] or '未分类', 'count': r['cnt']} for r in scene_rows]
                },
                'github_summary': {
                    'total_repos': gh_total,
                    'by_scene': [{'scene': r['top_scene'], 'count': r['cnt']} for r in top_scenes]
                }
            })
        except Exception as e:
            log(f"tech_summary错误: {e}")
            self._json(500, {'ok': False, 'error': str(e)})

    def handle_tech_recommendations(self):
        try:
            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            page = max(1, int(params.get('page', ['1'])[0]))
            size = min(50, int(params.get('size', ['10'])[0]))
            offset = (page - 1) * size
            only_energy = params.get('only_energy', ['0'])[0] == '1'
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            sql_where = "WHERE t.confidence>=30"
            sql_params = []
            if only_energy:
                sql_where += " AND b.relevance_score>=60"
            total = conn.execute(f"""
                SELECT COUNT(*) FROM tech_matches t
                LEFT JOIN bidding_notices b ON t.notice_id=b.id AND t.notice_type='bidding'
                {sql_where}
            """, sql_params).fetchone()[0]
            rows = conn.execute(f"""
                SELECT t.*, b.url, b.procurement_owner, b.province,
                       b.relevance_score as bidding_score, b.publish_date, b.budget_amount
                FROM tech_matches t
                LEFT JOIN bidding_notices b ON t.notice_id=b.id AND t.notice_type='bidding'
                {sql_where}
                ORDER BY b.relevance_score DESC, t.confidence DESC
                LIMIT ? OFFSET ?
            """, sql_params + [size, offset]).fetchall()
            conn.close()
            data = []
            for r in rows:
                try:
                    scenarios = json.loads(r["scenarios_json"] or "[]")
                except Exception:
                    scenarios = []
                try:
                    primary_tech = json.loads(r["primary_tech_json"] or "[]")
                except Exception:
                    primary_tech = []
                try:
                    secondary_tech = json.loads(r["secondary_tech_json"] or "[]")
                except Exception:
                    secondary_tech = []
                data.append({
                    "notice_id": r["notice_id"],
                    "notice_type": r["notice_type"],
                    "title": r["title"],
                    "owner": r["procurement_owner"],
                    "province": r["province"],
                    "publish_date": r["publish_date"],
                    "budget": r["budget_amount"],
                    "bidding_score": r["bidding_score"],
                    "confidence": r["confidence"],
                    "reason": r["recommend_reason"],
                    "scenarios": scenarios,
                    "primary_tech": primary_tech,
                    "secondary_tech": secondary_tech,
                    "url": r["url"],
                })
            self._json(200, {
                'ok': True,
                'total': total,
                'page': page,
                'size': size,
                'data': data
            })
        except Exception as e:
            log(f"tech_rec错误: {e}")
            self._json(500, {'ok': False, 'error': str(e)})

    def handle_github_energy(self):
        try:
            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            scene = params.get('scene', [None])[0]
            size = min(50, int(params.get('size', ['30'])[0]))
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            where = ""
            sql_params = []
            if scene:
                where = "WHERE top_scene=?"
                sql_params.append(scene)
            rows = conn.execute(f"""
                SELECT * FROM github_energy
                {where} ORDER BY heat_score DESC, week_growth DESC, stars DESC
                LIMIT ?
            """, sql_params + [size]).fetchall()
            total = conn.execute(f"SELECT COUNT(*) FROM github_energy {where}").fetchone()[0]
            conn.close()
            data = []
            for r in rows:
                try:
                    topics = json.loads(r["topics_json"] or "[]")
                except Exception:
                    topics = []
                try:
                    matched_scenes = json.loads(r["matched_scenes_json"] or "[]")
                except Exception:
                    matched_scenes = []
                data.append({
                    "repo_name": r["repo_name"],
                    "description": r["description"],
                    "language": r["language"],
                    "stars": r["stars"],
                    "week_growth": r["week_growth"],
                    "topics": topics,
                    "matched_scenes": matched_scenes,
                    "top_scene": r["top_scene"],
                    "confidence": r["confidence"],
                    "why_it_matters": r["why_it_matters"],
                    "url": r["url"],
                    "heat_score": r["heat_score"] if "heat_score" in r.keys() else 0,
                    "fetch_date": r["fetch_date"] if "fetch_date" in r.keys() else None,
                })
            self._json(200, {
                'ok': True,
                'total': total,
                'scene': scene,
                'data': data
            })
        except Exception as e:
            log(f"github_energy错误: {e}")
            self._json(500, {'ok': False, 'error': str(e)})

    def handle_tech_for_notice(self):
        try:
            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            notice_id = int(params.get('id', ['0'])[0])
            ntype = params.get('type', ['bidding'])[0]
            table = 'bidding_notices' if ntype == 'bidding' else 'winning_notices'
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                f"SELECT id, title, content_summary, province, category FROM {table} WHERE id=?",
                (notice_id,)
            ).fetchone()
            conn.close()
            if not row:
                self._json(404, {'ok': False, 'error': '未找到该公告'})
                return
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from tech_matcher import match_tech_for_notice
            result = match_tech_for_notice(
                row["id"], row["title"], row["content_summary"] or "",
                row["province"] or "", row["category"] or ""
            )
            self._json(200, {'ok': True, 'data': result})
        except Exception as e:
            log(f"tech_notice错误: {e}")
            self._json(500, {'ok': False, 'error': str(e)})

    # ═══ 旧数据 API (保留兼容) ═══
    def handle_get_data(self):
        qs = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(qs)
        data_type = params.get('type', ['bidding'])[0]
        limit = min(int(params.get('limit', ['50'])[0]), 200)
        min_score = float(params.get('min_score', ['0'])[0])
        days = params.get('days', [None])[0]
        keyword = params.get('q', [None])[0]
        table = 'bidding_notices' if data_type == 'bidding' else 'winning_notices'
        cols = ('id, title, url, source_site, publish_date, relevance_score, '
                'budget_amount, region, procurement_owner, category')
        sql = f"SELECT {cols} FROM {table} WHERE relevance_score>=?"
        sql_params = [min_score]
        if days:
            sql += " AND date(publish_date)>=date('now',?)"
            sql_params.append(f'-{days} days')
        if keyword:
            sql += " AND title LIKE ?"
            sql_params.append(f'%{keyword}%')
        sql += " ORDER BY relevance_score DESC LIMIT ?"
        sql_params.append(limit)
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute(sql, sql_params)]
        conn.close()
        self._json(200, {"ok": True, "type": data_type, "total": len(rows), "data": rows})

    # ═══ 对话 ═══
    def handle_get_chat(self):
        self._json(200, {"presets": PRESET_QUESTIONS})

    def handle_post_chat(self):
        try:
            data = self._read_body()
            question = data.get('question', '').strip()
            messages = data.get('messages', [])
            if not question:
                self._json(400, {"ok": False, "error": "请输入问题"})
                return
            answer = chat_with_llm(messages, question)
            self._json(200, {"answer": answer})
            log(f"对话: {question[:40]} -> {len(answer)}字")
        except Exception as e:
            log(f"对话错误: {e}")
            self._json(500, {"ok": False, "error": str(e)})

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(length))

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'public, max-age=30')
        cors(self)
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, format, *args):
        pass

def run(port=8090):
    server = HTTPServer(('127.0.0.1', port), Handler)
    log(f"API服务启动 v2: 127.0.0.1:{port}")
    print(f"API服务 v2 已启动: 127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()

if __name__ == '__main__':
    run()
