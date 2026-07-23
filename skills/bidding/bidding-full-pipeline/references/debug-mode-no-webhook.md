# 调试模式：运行管线但不推送企微

## 场景

用户要求「调试一下内容，不进行 webhook 推送」或「跑一下管线看看，别发群消息」。

## 双重保险机制

管线有**两层**推送拦截：

| 层 | 机制 | 文件 | 作用 |
|:--|:--|:--|:--|
| L1 | KILL_SWITCH | `wecom_push.py` 第10行 | 全局开关，True 时所有推送函数返回空 |
| L2 | PUSH_LOCK | `/tmp/wenyao_push.lock` | 日锁，同一天第二次调用自动跳过 |

> L2 只在「今天已经推送过」时有意义。调试当天**第一次跑**只需 L1。

## SOP（3步）

### 步骤1：开 KILL_SWITCH + 清锁

使用 patch 工具修改 `wecom_push.py`：

```
old: KILL_SWITCH = False  # ✅ 已开启
new: KILL_SWITCH = True   # 🔴 调试模式，禁止推送
```

同时清除推送日锁（防止当天已推送过的 lock 再拦截）：
```bash
rm -f /tmp/wenyao_push.lock
```

### 步骤2：跑管线

```bash
cd /root/.hermes/profiles/wenyaozhitou
bash scripts/pipeline_master.sh 2>&1 | tail -50
```

或后台运行（管线耗时 10-20 分钟）：
```bash
cd /root/.hermes/profiles/wenyaozhitou
nohup bash scripts/pipeline_master.sh > /tmp/debug_pipeline.log 2>&1 &
# 查看进度
tail -f /var/log/wenyao_pipeline.log
```

### 步骤3：恢复 KILL_SWITCH

用 patch 工具恢复：

```
old: KILL_SWITCH = True   # 🔴 调试模式，禁止推送
new: KILL_SWITCH = False  # ✅ 已开启
```

## ⚠️ 关键注意事项

- **KILL_SWITCH 必须恢复** — 否则第二天定时任务也会静默跳过推送
- 调试时也清 `/tmp/wenyao_push.lock` — 防止 lock 也拦截（双重保险）
- 管线阶段5日志应显示 `[KILL_SWITCH] XXX: 已拦截` 表示拦成功了
- 恢复后手动验证：`python3 scripts/wecom_push.py` 应正常发送

## 定时任务不受影响

systemd timer (`wenyao-pipeline.timer`) 每天 8:00 照常触发，KILL_SWITCH 只影响当前手动跑。恢复 KILL_SWITCH 后定时任务正常推送。
