# 文鳐智投 PM 产品交互审计清单

> V1.34 审计日期：2026-06-26 | 审计人视角：字节跳动产品经理

## 审计方法论

1. **实际使用页面**（不看代码，看渲染结果）
2. **⛔ 桌面+手机双端验证**：每次改动后必须检查两个视口。`@media(max-width:768px)` 的 CSS 可能被误改，HTML 结构可能被重构破坏手机端布局。
3. **逐项记录交互缺陷**（不是"感觉不好"，是"点击X后Y没发生"）
4. **优先级分 P1/P2/P3**（P1=用户死胡同，P2=认知负荷，P3=体验打磨）
5. **每项给出可落地方案**（不写"建议优化"，写具体CSS/JS怎么做）
6. **实现后逐项验证**（console检查 + 可视化截图）
7. **用户否决后立即回滚并记录到此文档**——不做"更好的设计"，做"用户要的设计"

## ⛔ 用户已否决的设计模式

| 功能 | 否决理由 | 记录日期 |
|:--|:--|:--|
| 「更多筛选」折叠 | 用户偏好所有筛选控件始终可见 | 2026-06-26 |
| 手机端「紧凑/舒适」密度切换 | 手机端卡片视图不需要密度切换 | 2026-06-26 |

## 桌面端 vs 手机端隔离原则

**铁律：修改桌面端布局时，必须同步检查手机端 `@media(max-width:768px)` 内的 CSS 是否被破坏。**

常见陷阱：
1. `chmod 644 *` 会抹掉目录的 `x` 权限 → nginx 403 → 但仅影响图片/资源，HTML仍在 → 不容易立即发现
2. 把元素从 `.filter-row` 移到 `.filter-bar` 直级（桌面端对齐修复）→ 手机端 `.filter-bar` 是 `display:block` → 这些元素变成竖列堆叠
3. 全局 CSS 规则（如 `body.dense`）在手机端仍生效，即使功能在手机端无意义
4. Polish 脚本的 ENHANCE_CSS 守卫条件用了已被回滚的功能名 → 每次 polish 都重复注入

**自查清单（每次改完 CSS/HTML 后）：**
- [ ] 手机端 `.filter-bar` 是否仍是 `display:block`？导出/重置按钮是否被隐藏？
- [ ] 手机端卡片视图（`tr.data-row{display:grid}`）是否正常？
- [ ] 手机端 `filter-scroll-wrapper` 是否 `overflow:hidden`（不是 `visible`）？
- [ ] 手机端无意义的桌面功能（密度切换 `≡`）是否已隐藏？
- [ ] 对 `@media(max-width:768px)` 内的 CSS 改动是否幂等（不会每跑一次 polish 重复注入）？

## V1.33 第一轮审计 — 实现并保留

| # | 发现 | 优先级 | 修复 | 验证方式 |
|:--|:--|:--|:--|:--|
| 1 | 搜索无结果→空白表 | P1 | smartEmptyMsg + 清除筛选按钮 | 搜索不存在关键词→看到提示+按钮 |
| 2 | 筛选后URL不变→无法分享 | P1 | history.replaceState + URLSearchParams | 筛选后URL含?q=参数 |
| 3 | 中文输入法下Enter触发搜索 | P1 | compositionstart/end + composing标志 | 拼音输入时按Enter不触发 |
| 4 | 12个筛选控件挤一行 | ~~P2~~ | 「更多筛选」折叠 → **用户否决，已回滚** | — |
| 5 | 统计卡片无对比维度 | P2 | 已有trend indicators | renderTrendIndicators已有 |
| 6 | 表格10列→需横向滚动 | P2 | 紧凑/舒适密度toggle(≡) — 仅桌面端 | 紧凑模式行高32px |
| 7 | 评分彩色条缺图例 | P3 | 表头ⓘ→弹出三色说明 | 点击ⓘ看到tooltip |
| 8 | 缺键盘快捷键 | P3 | / Esc Ctrl+Enter Ctrl+←→ Ctrl+S | 按键测试 |
| 9 | 长标题hover无预览 | P3 | 600ms延迟弹出全文气泡 | hover长标题→看到全文 |

## V1.33 第二轮审计 — 同会话补充修复

| # | 发现 | 优先级 | 修复 |
|:--|:--|:--|:--|
| 10 | 操作手册头部Logo用favicon凑数 | P2 | 改为`/bidding/img/logo.png` |
| 11 | 操作手册内容过时，未覆盖V1.33新功能 | P2 | 新增4.8~4.11四节 |
| 12 | 页面title太简略 | P3 | 三页统一为「文鳐智投 · 页面名 — 数智科技投标监控」|

## V1.34 追加修复 — 移动端回归问题

| # | 发现 | 根因 | 修复 |
|:--|:--|:--|:--|
| 13 | 手机端筛选栏下面多出「\|」「每页」「导出」「重置」等元素堆叠 | 桌面端对齐修复把导出/重置移到了`.filter-bar`直级子元素→手机端`display:block`下变成竖列 | 手机端CSS隐藏这些元素，仅保留导出按钮 |
| 14 | 手机端点了紧凑按钮后卡片挤成一坨 | `body.dense`全局规则压缩了卡片padding/font-size | 手机端隐藏≡按钮 + 移除dense模式的mobile覆盖 |
| 15 | 手机端整个布局挤成一团 | **ENHANCE_CSS重复注入**——守卫条件用了已被回滚的`more-filters-toggle`，每次polish都重复注入整套CSS→5个重复`@media`块 | 守卫改为`hover-preview-tip`（永久保留的CSS标识）|
| 16 | Logo反复404 | **`chmod 644 /var/www/html/bidding/*` 破坏目录执行权限**→`img/`目录变成`drw-r--r--`→nginx无法进入读文件 | polish v6内置：只chmod文件不改目录，目录强制755 |

## 三页一致性原则

**每次功能变更后必须检查三个页面**：
- `index.html` — 监控看板（由report_generator+polish自动维护）
- `changelog.html` — 更新日志（手动维护）
- `manual.html` — 操作手册（手动维护）

检查清单：
- [ ] Header Logo 是否一致（都是 `/bidding/img/logo.png`）
- [ ] Favicon/OG 标签是否一致
- [ ] `<title>` 格式是否为「文鳐智投 · 页面名 — 数智科技投标监控」
- [ ] 新功能是否已写入操作手册
- [ ] 版本号是否已更新
- [ ] **Nginx 返回200**：`curl -sI https://www.yfzx.online/bidding/img/logo.png`
