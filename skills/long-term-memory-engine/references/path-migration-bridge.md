# 记忆系统路径迁移桥接模式

## 背景

Hermes 系统提示词中注入了旧版绝对路径引用的 CLI 命令：
```bash
python3 /root/.hermes/memory_store/memory_engine.py store "..."
python3 /root/.hermes/memory_store/memory_engine.py search "..." --top 5
python3 /root/.hermes/memory_store/memory_maintainer.py
```

而实际部署已迁移到 profile 内：
- 新版引擎: `/root/.hermes/profiles/wenyaozhitou/scripts/memory_engine.py`
- 新版维护: `/root/.hermes/profiles/wenyaozhitou/scripts/memory_maintainer.py`
- 向量DB: `/root/.hermes/profiles/wenyaozhitou/data/memory.db`

## 解决方案：桥接脚本

在旧路径放置 thin wrapper，委托到新版实现：

```python
# /root/.hermes/memory_store/memory_engine.py (桥接器)
import sys, os
NEW_SCRIPT_DIR = "/root/.hermes/profiles/wenyaozhitou/scripts"
sys.path.insert(0, NEW_SCRIPT_DIR)
os.chdir("/root/.hermes/profiles/wenyaozhitou")

if __name__ == "__main__":
    import runpy
    runpy.run_path(os.path.join(NEW_SCRIPT_DIR, "memory_engine.py"), run_name="__main__")
```

```python
# /root/.hermes/memory_store/memory_maintainer.py (桥接器)
# 同样模式
```

## 关键原则

1. **不修改系统提示词**：提示词由 Hermes 框架注入，无法手动改
2. **旧路径必须可用**：`python3 /root/.hermes/memory_store/memory_engine.py search "..."` 必须能跑
3. **桥接脚本极简**：只做路径切换+委托，不包含业务逻辑
4. **版本统一**：旧路径始终指向同一份新版实现，不存在 fork

## 迁移后验证清单

| 检查项 | 命令 |
|:--|:--|
| 旧路径可达 | `python3 /root/.hermes/memory_store/memory_engine.py` 输出统计 |
| 旧路径可搜索 | `python3 /root/.hermes/memory_store/memory_engine.py search "投标" --top 2` |
| memory/ 目录完整 | `ls memory/hot/HOT_MEMORY.md memory/warm/WARM_MEMORY.md` |
| 每日日志存在 | `ls memory/$(date +%Y-%m-%d).md` |
| WARM_MEMORY 路径正确 | `grep 'memory_store' memory/warm/WARM_MEMORY.md` → 应为空 |
| systemd timer 正常 | `systemctl list-timers 'wenyao-*'` |

## 相关文件

- HOT_MEMORY.md: `memory/hot/HOT_MEMORY.md` — 当前任务/待办/环境
- WARM_MEMORY.md: `memory/warm/WARM_MEMORY.md` — 稳定配置/API参考/关键坑点
- 每日日志: `memory/YYYY-MM-DD.md` — 每日活动流水
- 向量DB: `data/memory.db` — SQLite + embedding 向量
