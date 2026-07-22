#!/usr/bin/env python3
"""文鳐智投 长记忆引擎 — 向量语义存储
HOT (<7天) → WARM (7-30天) → COLD (>30天)
嵌入模型: 通义千问 text-embedding-v3 (1024维)
"""
import os, json, time, sqlite3, logging, struct
import numpy as np
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# ═══════════════════ 配置 ═══════════════════
API_KEY_PATH = "/tmp/qwen_key.txt"
API_KEY = open(API_KEY_PATH).read().strip() if os.path.exists(API_KEY_PATH) else ""
EMBED_API = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
EMBED_MODEL = "text-embedding-v3"
EMBED_DIM = 1024

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "memory.db"
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "memory_logs"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_PATH.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH / f"memory_{datetime.now():%Y-%m-%d}.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("memory_engine")

# ═══════════════════ 向量编码/解码 ═══════════════════
def _vec_to_blob(vec: np.ndarray) -> bytes:
    """numpy数组 → BLOB"""
    return struct.pack(f'{len(vec)}f', *vec)

def _blob_to_vec(blob: bytes) -> np.ndarray:
    """BLOB → numpy数组"""
    return np.array(struct.unpack(f'{len(blob)//4}f', blob), dtype=np.float32)

# ═══════════════════ 嵌入 API ═══════════════════
_embed_cache: dict = {}

def get_embedding(text: str) -> np.ndarray:
    """获取文本向量（归一化，带缓存）"""
    if not API_KEY:
        raise RuntimeError("API KEY 未配置: /tmp/qwen_key.txt")
    key = text[:200]
    if key in _embed_cache:
        return _embed_cache[key]

    resp = requests.post(
        EMBED_API,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"model": EMBED_MODEL, "input": {"texts": [text]}},
        timeout=30
    )
    if resp.status_code != 200:
        raise RuntimeError(f"嵌入失败: {resp.status_code} {resp.text[:200]}")
    
    data = resp.json()
    vec = np.array(data["output"]["embeddings"][0]["embedding"], dtype=np.float32)
    # L2归一化
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    _embed_cache[key] = vec
    return vec

# ═══════════════════ 数据库 ═══════════════════
def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    return c

def init_db():
    """初始化数据库表"""
    with _conn() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            embedding BLOB NOT NULL,
            category TEXT DEFAULT 'general',
            tags TEXT DEFAULT '',
            importance REAL DEFAULT 1.0,
            tier TEXT DEFAULT 'HOT',
            source TEXT DEFAULT '',
            ref_id TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            accessed_at TEXT NOT NULL,
            access_count INTEGER DEFAULT 1,
            CONSTRAINT uq_ref UNIQUE(source, ref_id)
        )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_tier ON memories(tier)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_category ON memories(category)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at)")
        db.commit()
    log.info("数据库初始化完成")

# ═══════════════════ 核心操作 ═══════════════════
def add_memory(
    content: str,
    category: str = "general",
    tags: str = "",
    importance: float = 1.0,
    source: str = "",
    ref_id: str = "",
    force: bool = False
) -> int:
    """添加记忆。source+ref_id 唯一去重，force=True 强制覆盖。"""
    vec = get_embedding(content)
    now = datetime.now().isoformat()
    
    with _conn() as db:
        # 去重检查
        if source and ref_id:
            existing = db.execute(
                "SELECT id FROM memories WHERE source=? AND ref_id=?", (source, ref_id)
            ).fetchone()
            if existing:
                if force:
                    db.execute(
                        "UPDATE memories SET content=?, embedding=?, importance=?, accessed_at=? WHERE id=?",
                        (content, _vec_to_blob(vec), importance, now, existing["id"])
                    )
                    db.commit()
                    log.info(f"覆盖记忆 #{existing['id']}: {content[:60]}...")
                    return existing["id"]
                else:
                    log.info(f"记忆已存在 #{existing['id']} (source={source}, ref_id={ref_id})")
                    return existing["id"]
        
        # 语义去重：用原始余弦相似度（不加 importance 权重）
        results = search_memory(content, top_k=1, raw_cosine=True)
        if results:
            raw_cosine, dedup_id = results[0][0], results[0][1]
            if raw_cosine > 0.92 and not force:
                log.info(f"语义重复 (相似度={raw_cosine:.3f})，跳过 → 已存 #{dedup_id}")
                # 更新访问时间
                db.execute("UPDATE memories SET access_count=access_count+1, accessed_at=? WHERE id=?",
                           (now, dedup_id))
                db.commit()
                return dedup_id
        
        # 插入
        cursor = db.execute(
            """INSERT INTO memories (content, embedding, category, tags, importance, tier, source, ref_id, created_at, accessed_at)
            VALUES (?, ?, ?, ?, ?, 'HOT', ?, ?, ?, ?)""",
            (content, _vec_to_blob(vec), category, tags, importance, source, ref_id, now, now)
        )
        db.commit()
        mid = cursor.lastrowid
        log.info(f"新记忆 #{mid}: {content[:60]}... [{category}]")
        return mid

def search_memory(query: str, top_k: int = 5, category: str = "", min_similarity: float = 0.3, raw_cosine: bool = False) -> list:
    """语义搜索记忆。raw_cosine=True 时返回原始余弦相似度而非加权分"""
    if not query.strip():
        return []
    
    q_vec = get_embedding(query)
    
    with _conn() as db:
        where = "WHERE 1=1"
        params = []
        if category:
            where += " AND category=?"
            params.append(category)
        rows = db.execute(
            f"SELECT id, content, embedding, category, tags, importance, tier, created_at, access_count FROM memories {where}",
            params
        ).fetchall()
    
    results = []
    for row in rows:
        vec = _blob_to_vec(row["embedding"])
        cosine = float(np.dot(q_vec, vec))  # 向量已L2归一化
        if raw_cosine:
            if cosine >= min_similarity:
                results.append((cosine, row["id"], row["content"], row["category"], row["tags"], row["tier"], row["created_at"], row["access_count"]))
        else:
            score = cosine * row["importance"]
            if score >= min_similarity:
                results.append((score, row["id"], row["content"], row["category"], row["tags"], row["tier"], row["created_at"], row["access_count"]))
    
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top_k]

def get_recent(n: int = 20, category: str = "") -> list:
    """获取最近记忆"""
    with _conn() as db:
        where = "WHERE tier != 'COLD'"
        params = []
        if category:
            where += " AND category=?"
            params.append(category)
        rows = db.execute(
            f"SELECT * FROM memories {where} ORDER BY created_at DESC LIMIT ?",
            [*params, n]
        ).fetchall()
    return [dict(r) for r in rows]

def update_importance(mem_id: int, delta: float):
    """调整记忆重要性"""
    with _conn() as db:
        db.execute("UPDATE memories SET importance=MAX(0.1, MIN(5.0, importance+?)) WHERE id=?", (delta, mem_id))
        db.commit()

# ═══════════════════ 维护操作 ═══════════════════
def maintain():
    """每日维护：降级旧记忆、清理冷数据、输出统计"""
    now = datetime.now()
    seven_days = (now - timedelta(days=7)).isoformat()
    thirty_days = (now - timedelta(days=30)).isoformat()
    
    with _conn() as db:
        # WARM: 7-30天
        db.execute(
            "UPDATE memories SET tier='WARM' WHERE tier='HOT' AND created_at < ?",
            (seven_days,)
        )
        warm_count = db.total_changes
        
        # COLD: >30天
        db.execute(
            "UPDATE memories SET tier='COLD' WHERE tier='WARM' AND created_at < ?",
            (thirty_days,)
        )
        cold_count = db.total_changes
        
        # 统计
        stats = {}
        for tier in ['HOT', 'WARM', 'COLD']:
            cnt = db.execute("SELECT COUNT(*) FROM memories WHERE tier=?", (tier,)).fetchone()[0]
            stats[tier] = cnt
        
        db.commit()
    
    log.info(f"维护完成: HOT→WARM {warm_count}条, WARM→COLD {cold_count}条")
    log.info(f"当前分布: HOT={stats['HOT']} WARM={stats['WARM']} COLD={stats['COLD']}")
    return stats

def deduplicate(threshold: float = 0.95):
    """去重：删除语义高度相似的旧记忆"""
    with _conn() as db:
        rows = db.execute("SELECT id, content, embedding, created_at, access_count FROM memories WHERE tier IN ('HOT','WARM')").fetchall()
    
    removed = 0
    kept = set()
    for i, r1 in enumerate(rows):
        if r1["id"] in kept:
            continue
        v1 = _blob_to_vec(r1["embedding"])
        for r2 in rows[i+1:]:
            if r2["id"] in kept:
                continue
            v2 = _blob_to_vec(r2["embedding"])
            cosine = np.dot(v1, v2)  # 向量已L2归一化
            if cosine >= threshold:
                # 保留访问次数多的
                if r1["access_count"] >= r2["access_count"]:
                    to_remove = r2["id"]
                else:
                    to_remove = r1["id"]
                    kept.add(r2["id"])
                with _conn() as db:
                    db.execute("DELETE FROM memories WHERE id=?", (to_remove,))
                    db.commit()
                removed += 1
                log.info(f"去重删除 #{to_remove} (相似度={cosine:.3f})")
                break
        kept.add(r1["id"])
    
    log.info(f"去重完成: 删除 {removed} 条重复记忆")
    return removed

def stats() -> dict:
    """返回数据库统计"""
    with _conn() as db:
        total = db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        tiers = {}
        for tier in ['HOT', 'WARM', 'COLD']:
            tiers[tier] = db.execute("SELECT COUNT(*) FROM memories WHERE tier=?", (tier,)).fetchone()[0]
        cats = {}
        for row in db.execute("SELECT category, COUNT(*) as cnt FROM memories GROUP BY category ORDER BY cnt DESC").fetchall():
            cats[row["category"]] = row["cnt"]
    return {"total": total, "tiers": tiers, "categories": cats}

# ═══════════════════ CLI ═══════════════════
if __name__ == "__main__":
    import sys
    init_db()
    
    if len(sys.argv) < 2:
        st = stats()
        print(f"🧠 文鳐智投长记忆")
        print(f"   总计: {st['total']} 条")
        print(f"   分布: HOT={st['tiers']['HOT']} WARM={st['tiers']['WARM']} COLD={st['tiers']['COLD']}")
        if st['categories']:
            print(f"   分类: {st['categories']}")
        sys.exit(0)
    
    cmd = sys.argv[1]
    if cmd == "add" and len(sys.argv) >= 4:
        mid = add_memory(sys.argv[2], sys.argv[3])
        print(f"✅ #{mid}")
    elif cmd == "search" and len(sys.argv) >= 3:
        results = search_memory(sys.argv[2], top_k=5)
        for i, (score, mid, content, cat, _, _, _, _) in enumerate(results):
            print(f"{i+1}. [{cat}] (相似度={score:.3f}) #{mid} {content[:80]}")
        if not results:
            print("🔍 无结果")
    elif cmd == "maintain":
        maintain()
    elif cmd == "dedup":
        deduplicate()
    elif cmd == "init":
        print("✅ 数据库已就绪")
    else:
        print("用法: python memory_engine.py [add <内容> <分类>|search <查询>|maintain|dedup]")
