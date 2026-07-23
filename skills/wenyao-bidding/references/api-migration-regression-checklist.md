# API 迁移 UI 回归防范手册 (V1.40)

## 核心教训

当为已有功能添加并行代码路径（如前端从 data.json 全量加载 → API 分页查询），**必须逐项对比旧路径的 UI 组件**，确保新路径不遗漏任何交互元素。

## 已知回归清单（API 模式 `renderTable()` 缺失项）

| # | 组件 | 旧路径 (`doFilter` legacy) | 新路径 (`renderTable` API) | 修复 |
|:--|:--|:--|:--|:--|
| 1 | 回到顶部按钮 | `init()` 创建 `#btnBackTop` | ❌ 未创建 | `init()` 补回创建 + scroll 监听 |
| 2 | 页码按钮 | `renderPg("pgNums", pg, tp)` | ❌ 未调用 | `renderTable()` 末尾补 `renderPg()` |
| 3 | 页码信息 | 通过 ID `pgInfo`/`pgInfoW` | ❌ 用 class `.pg-info` 找不到元素 | 改用 `getElementById('pgInfo')` |
| 4 | 收藏星 ⭐ | title-cell 内左侧 | ❌ 独立最后一列 | 移入 title-cell |
| 5 | Kebab ⋯ 菜单 | title-cell 内右侧（手机端） | ❌ 完全不渲染 | `window.innerWidth <= 768` 条件渲染 |
| 6 | 查看链接 | 第11列 "操作" → "查看" | ❌ 缺失 | 补回第11列 |
| 7 | 筛选折叠按钮 | 手机端 toggle `.filter-scroll-wrapper.expanded` | ❌ toggle `.filter-bar` display | 改回 toggle `.expanded` class |
| 8 | Star 过滤 | `starOnly` 在 `doFilter()` 中过滤 | ❌ `apiFilter()` 忽略 `starOnly` | API 返回后 client-side 过滤 |
| 9 | `renderTable` 数据源 | 用过滤后的 `allB/allW` | ❌ 用原始 `d.data` / `d.total` | 改用 `allB/allW` / `totalBidding/totalWinning` |

## Async 竞态模式

**症状**：快速切换 Tab 后页面卡死，`useApi` 被永久设为 `false`。

**根因**：`apiFilter()` 是 async，多次调用互相覆盖全局变量。某次调用抛异常 → `useApi = false` → 永久回退到旧路径。

**修复三件套**：
1. `sw()` 每次设 `useApi = true`（重置降级状态）
2. `_apiSeq` 计数器 + `if (seq !== _apiSeq) return;` 丢弃过期回调
3. catch 中 `useApi = false` 只是临时降级，下次 tab 切换自动恢复

```javascript
let _apiSeq = 0;
async function apiFilter() {
    const seq = ++_apiSeq;
    // ... fetch ...
    if (seq !== _apiSeq) return;  // stale, abort
    // ...
}
```

## 双路径分叉陷阱 (V1.40 新增)

API 路径和降级路径共享部分函数（`renderTable`, `sw`, `updateApiStats`），但这些函数内部可能对"当前处于哪条路径"有隐含假设。

| # | 陷阱 | 症状 | 根因 | 修复 |
|:--|:--|:--|:--|:--|
| 10 | 守卫误封 | 收藏 Tab 0条 → 切招标卡在"加载中" | `sw()` 中 `if(!allB.length&&!allW.length) return` — star 过滤后 allB=[] 触发守卫 | 移除守卫，信任 API re-fetch |
| 11 | 函数不存在 | `renderTable()` 报 ReferenceError | `emptyMsg()` 只在 `doFilter()` 内是局部变量，API 路径不可见 | 内联计算空态消息 |
| 12 | 函数名不一致 | `init()` 报 `loadBookmarks not defined` | 实际函数名 `loadBookmarksFromServer` | 统一函数名 |
| 13 | catch 锁死 | 一次 API 失败 → 永久降级 | `catch{useApi=false}` 不区分临时/永久错误 | `sw()` 中设 `useApi=true` |

详见 `references/api-dual-path-divergence-pitfalls.md`。

## 统计卡片跨 Tab 计数不一致

**症状**：点「高相关 26」→ 累计招标=21（正确），累计中标=13（错误，应为 5）。

**根因**：`apiFilter()` 只查当前 Tab 的 type。`totalBidding` 和 `totalWinning` 只有一个被更新。

**修复**：`activeStatFilter` 激活时，额外 fetch 另一 Tab 的 filtered total。

## 自检清单

每次新增并行代码路径后：
- [ ] 回到顶部按钮 ✅
- [ ] 页码按钮 + 信息 ✅
- [ ] 每页选择器 ✅
- [ ] 收藏星 + Kebab 菜单 ✅
- [ ] 操作列（查看链接）✅
- [ ] 筛选折叠按钮 ✅
- [ ] Star 过滤 ✅
- [ ] 统计卡片联动 ✅
- [ ] Async 竞态防护 ✅
- [ ] 快速 Tab 切换不卡死 ✅
- [ ] **双路径守卫条件**：`sw()` 不受 `allB/allW` 为空影响 ✅ (V1.40)
- [ ] **共享函数依赖**：`renderTable()` 引用的所有函数在两路径可访问 ✅ (V1.40)
- [ ] **全局函数名**：`grep` 确认所有调用点函数名一致 ✅ (V1.40)
