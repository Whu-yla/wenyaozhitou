#!/usr/bin/env python3
"""文鳐智投 长记忆维护器 — 每日自动运行
1. 降级 HOT→WARM→COLD
2. 语义去重
3. 生成每日记忆摘要
4. 清理超冷数据
"""
import sys, os
from pathlib import Path
from datetime import datetime

# 确保能找到 memory_engine
sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_engine import init_db, maintain, deduplicate, search_memory, stats, log

def generate_digest():
    """生成每日记忆摘要"""
    now = datetime.now()
    st = stats()
    
    lines = [
        f"## 🧠 文鳐智投 记忆日报 — {now:%Y-%m-%d}",
        "",
        f"| 层级 | 数量 |",
        f"|:--|:--|",
        f"| 🔥 HOT (<7天) | {st['tiers']['HOT']} |",
        f"| 🌤 WARM (7-30天) | {st['tiers']['WARM']} |",
        f"| ❄️ COLD (>30天) | {st['tiers']['COLD']} |",
        f"| **总计** | **{st['total']}** |",
        "",
    ]
    
    if st['categories']:
        lines.append("### 📂 分类分布")
        for cat, cnt in sorted(st['categories'].items(), key=lambda x: -x[1]):
            lines.append(f"- {cat}: {cnt}条")
        lines.append("")
    
    # 近期高相关记忆
    lines.append("### 🔍 近期重要记忆 (近3天)")
    recent = search_memory("投标 数智科技 智慧工地 安防", top_k=5, min_similarity=0.3)
    for i, (score, mid, content, cat, tags, tier, created, ac) in enumerate(recent):
        lines.append(f"{i+1}. [{cat}] `{content[:60]}` (相似度={score:.2f}, {tier})")
    
    if not recent:
        lines.append("暂无")
    
    digest = "\n".join(lines)
    
    # 保存日报
    digest_dir = Path(__file__).resolve().parent.parent / "data" / "memory_logs"
    digest_file = digest_dir / f"digest_{now:%Y-%m-%d}.md"
    digest_file.write_text(digest, encoding="utf-8")
    log.info(f"日报已保存: {digest_file}")
    return digest

def main():
    init_db()
    log.info("═══ 记忆维护开始 ═══")
    
    # 1. 层级降级
    tier_stats = maintain()
    
    # 2. 语义去重
    removed = deduplicate(threshold=0.95)
    
    # 3. 生成日报
    digest = generate_digest()
    
    # 4. 最终统计
    final = stats()
    log.info(f"维护完成: 总计{final['total']}条 | HOT={final['tiers']['HOT']} WARM={final['tiers']['WARM']} COLD={final['tiers']['COLD']}")
    log.info("═══ 记忆维护结束 ═══")
    
    print(digest)
    return digest

if __name__ == "__main__":
    main()
