#!/usr/bin/env python3
"""文鳐智投 对话引擎 v4 - 与 Hermes 共用同一 LLM 配置（GLM-5.2），真正多轮对话
v2: DeepSeek API（已废弃，欠费）
v3: 火山引擎 ARK coding endpoint（已废弃）
v4: 直接从 Hermes config.yaml 读取，与文鳐智投本体完全同款 API
"""
import json, sqlite3, os, re, requests, yaml
from datetime import datetime, timedelta
from pathlib import Path

DB = "/root/.hermes/profiles/wenyaozhitou/data/bidding.db"
MEMORY_DIR = "/root/.hermes/profiles/wenyaozhitou/memory"

# ═══════════════ 读取 LLM API 配置（与 Hermes 本体共用） ═══════════════
# 从 Hermes config.yaml 动态读取，改 provider 只需改 config.yaml + 重启 bookmark_server
LLM_API_KEY = None
LLM_BASE_URL = "https://www.szkj.site:18002/v1"
LLM_MODEL = "GLM-5.2"

_config_paths = [
    "/root/.hermes/profiles/wenyaozhitou/config.yaml",
    "/root/.hermes/config.yaml",
]
for _p in _config_paths:
    if os.path.exists(_p):
        try:
            with open(_p) as _f:
                _cfg = yaml.safe_load(_f)
            _model_cfg = _cfg.get("model", {})
            if _model_cfg.get("api_key"):
                LLM_API_KEY = _model_cfg["api_key"]
                if _model_cfg.get("base_url"):
                    LLM_BASE_URL = _model_cfg["base_url"]
                if _model_cfg.get("default"):
                    LLM_MODEL = _model_cfg["default"]
                break
        except Exception:
            pass

API_URL = f"{LLM_BASE_URL}/chat/completions"

# ═══════════════ 数据库查询工具 ═══════════════
def get_db_snapshot():
    """获取数据库概览，供AI参考"""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    # 全量统计
    total_b = conn.execute("SELECT COUNT(*) FROM bidding_notices WHERE relevance_score>0").fetchone()[0]
    total_w = conn.execute("SELECT COUNT(*) FROM winning_notices WHERE relevance_score>0").fetchone()[0]

    # 近30天统计
    recent_b = conn.execute(
        "SELECT COUNT(*) FROM bidding_notices WHERE relevance_score>0 AND date(publish_date)>=?", (month_ago,)
    ).fetchone()[0]
    recent_w = conn.execute(
        "SELECT COUNT(*) FROM winning_notices WHERE relevance_score>0 AND date(publish_date)>=?", (month_ago,)
    ).fetchone()[0]

    # 高相关TOP10（近30天招标）— 含URL
    top_bids = conn.execute("""
        SELECT id, title, source_site, category, budget_amount, publish_date, relevance_score, url
        FROM bidding_notices WHERE relevance_score>=7 AND date(publish_date)>=?
        ORDER BY relevance_score DESC LIMIT 10
    """, (month_ago,)).fetchall()

    # 高相关TOP10（近30天中标）— 含URL
    top_wins = conn.execute("""
        SELECT id, title, winner_company, winning_amount, source_site, publish_date, relevance_score, url
        FROM winning_notices WHERE relevance_score>=5 AND date(publish_date)>=?
        ORDER BY relevance_score DESC LIMIT 10
    """, (month_ago,)).fetchall()

    # 中标单位排行
    top_winners = conn.execute("""
        SELECT winner_company, COUNT(*) as cnt, SUM(CAST(COALESCE(NULLIF(REPLACE(REPLACE(winning_amount,'万元',''),',',''),''),'0') AS REAL)) as total_amt
        FROM winning_notices WHERE winner_company IS NOT NULL AND winner_company!='' AND relevance_score>0
        AND date(publish_date)>=? GROUP BY winner_company ORDER BY cnt DESC LIMIT 10
    """, (month_ago,)).fetchall()

    # 客户分类分布
    cats = conn.execute("""
        SELECT category, COUNT(*) as cnt FROM bidding_notices
        WHERE relevance_score>0 AND category IS NOT NULL AND date(publish_date)>=?
        GROUP BY category ORDER BY cnt DESC LIMIT 10
    """, (month_ago,)).fetchall()

    conn.close()

    snapshot = f"""📊 文鳐智投数据库概览（{datetime.now().strftime('%Y-%m-%d %H:%M')}）

【全量】招标{total_b}条 · 中标{total_w}条
【近30天】招标{recent_b}条 · 中标{recent_w}条

【近30天 高相关招标 TOP10】
"""
    for i, r in enumerate(top_bids):
        amt_val = r['budget_amount'] if r['budget_amount'] else ''
        amt = f" · 💰{amt_val}" if amt_val else ""
        url = r['url'] if r['url'] else ''
        snapshot += f"{i+1}. [{r['relevance_score']:.0f}分] {r['title'][:60]}{amt} | {r['source_site'] or '?'}\n   🔗 {url}\n"

    snapshot += "\n【近30天 中标 TOP10】\n"
    for i, r in enumerate(top_wins):
        amt_val = r['winning_amount'] if r['winning_amount'] else ''
        amt = f" · 💰{amt_val}" if amt_val else ""
        url = r['url'] if r['url'] else ''
        snapshot += f"{i+1}. [{r['relevance_score']:.0f}分] {r['title'][:60]} → {r['winner_company'] or '?'}{amt}\n   🔗 {url}\n"

    snapshot += "\n【近30天 中标单位排行】\n"
    for i, r in enumerate(top_winners):
        snapshot += f"{i+1}. {r['winner_company'][:25]} — {r['cnt']}次 · {r['total_amt']:.0f}万元\n"

    snapshot += "\n【近30天 客户分类】\n"
    for r in cats:
        snapshot += f"  {r['category']}: {r['cnt']}条\n"

    return snapshot


def execute_sql(query):
    """执行自定义SQL查询（安全限制）"""
    # 只允许SELECT
    q = query.strip().upper()
    if not q.startswith("SELECT"):
        return {"error": "仅支持SELECT查询"}
    # 禁用危险操作
    for bad in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "ATTACH"]:
        if bad in q:
            return {"error": f"不允许{bad}操作"}

    try:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query).fetchall()
        cols = [d[0] for d in conn.execute(f"SELECT * FROM ({query}) LIMIT 0").description]
        conn.close()
        results = []
        for r in rows[:30]:
            results.append({cols[i]: str(r[i]) if r[i] is not None else "" for i in range(len(cols))})
        return {"columns": cols, "rows": results, "count": len(results)}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════ 对话核心 ═══════════════
SYSTEM_PROMPT = """你是文鳐智投，中南电力设计院数智科技公司的AI投标助手。

## 你的身份
- 名字：文鳐智投
- 归属：程浩团队 / 量子纪元
- 公司背景：中南电力设计院数智科技公司（湖北武汉），专注数字化平台/AI/软件服务
- 核心业务：智慧工地、智慧电厂、数字孪生、BIM、AI平台、物联网、智能巡检、三维数字化设计
- 不是EPC施工公司，关注数字化/软件/平台类招标

## 你的能力
1. 回答招标/中标数据查询（你会收到数据库快照）
2. 分析投标趋势和竞品动向
3. 给出投标建议
4. 支持多轮对话和追问

## 回复规则（非常重要！）
- 简洁专业，用中文
- 数据要准确，引用数据库中的具体数字
- ⚠️ 【强制】当你提到任何具体的招标或中标项目时，必须附带可点击的链接！格式：[项目名称](完整URL)
- ⚠️ 【强制】列出多条项目时，每条都要有独立的链接！不要只列标题不给链接
- URL 在数据库快照中以「🔗」标记提供，请完整复制使用
- 链接是用户进入原始招标页面的唯一入口，缺失链接 = 用户体验极差
- 如果用户问的数据不在快照中，诚实告知"目前数据库中没有查到"
- 可以追问：位置、金额、时间范围等
- 保持友好，可以适当使用emoji

## 当前数据库快照
{DATA_SNAPSHOT}

用户现在要和你对话。请基于以上数据回答。"""


def chat_with_llm(messages, question):
    """调用 LLM API 进行对话（与 Hermes 本体同款 GLM-5.2）"""
    if not LLM_API_KEY:
        return "⚠️ API未配置，请联系管理员"

    snapshot = get_db_snapshot()
    sys_prompt = SYSTEM_PROMPT.replace("{DATA_SNAPSHOT}", snapshot)

    # 构建消息
    msgs = [{"role": "system", "content": sys_prompt}]
    # 加上最近5轮历史
    for m in messages[-10:]:
        msgs.append(m)
    msgs.append({"role": "user", "content": question})

    try:
        resp = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": msgs,
                "max_tokens": 1200,
                "temperature": 0.7,
            },
            timeout=30,
        )
        data = resp.json()
        if "choices" in data:
            content = data["choices"][0]["message"]["content"]
            # GLM-5.2 可能返回 reasoning_content，取 content 字段
            if not content and "reasoning_content" in data["choices"][0]["message"]:
                content = data["choices"][0]["message"]["reasoning_content"]
            return content if content else "（模型未返回内容）"
        else:
            return f"⚠️ API错误: {data.get('error',{}).get('message','未知错误')}"
    except Exception as e:
        return f"⚠️ 请求失败: {str(e)}"


# ═══════════════ 预设问题 ═══════════════
PRESET_QUESTIONS = [
    "最近一个月智慧工地有哪些招标？金额多少？",
    "最近一个月集控中心有哪些标挂网了？",
    "最近三个月华润电力招了哪些数字化项目？",
    "最近一周高相关的招标有哪些？",
    "最近一个月南方电网AI相关项目中标情况？",
    "最近一个月中标的单位都是哪些？金额最高的是谁？",
]


if __name__ == "__main__":
    # 测试
    print(get_db_snapshot()[:500])
    print(f"\nLLM API Key: {'已配置' if LLM_API_KEY else '未配置'}")
    print(f"LLM Model: {LLM_MODEL}")
    print(f"LLM URL: {API_URL}")
    print("\n--- 对话测试 ---")
    print(chat_with_llm([], "你好"))
