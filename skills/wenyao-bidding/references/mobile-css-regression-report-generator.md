# 手机端 CSS 回退根因：report_generator 重写 HTML 导致的样式丢失

## 问题（V1.35）

`report_generator.py` 的 `_html()` 生成**自己的 HTML 模板**（v5 基础版），结构与 polish 脚本累积注入的 V1.33+ 增强 CSS 不兼容。每次运行 → UI 筛选栏回退到 v5 基础版 → 用户质问「只是改功能？！怎么样式还会变？！！」

## 具体丢失的手机端样式

| 丢失项 | 表现 |
|:--|:--|
| 搜索框胶囊 | 🔍 图标不在框内、搜索按钮在框外独立一行 |
| 筛选栏水平滚动 | 胶囊换行堆叠成多行，东倒西歪 |
| 滑动动画提示 | 首次进入无滑动演示 |
| 右侧渐变淡出 | 无「还有更多可滑」视觉暗示 |

## 根因链

```
report_generator.py → _html() 写 index.html（v5模板）
  → 模板含基础 @media(max-width:768px) 规则（仅 stats/container/td）
  → 完全缺失 V1.33 手机端规则：
      · .search-box{display:flex} — 搜索输入+按钮一体化
      · .filter-row{flex-wrap:nowrap;overflow-x:auto} — 水平滚动
      · .filter-scroll-wrapper{overflow-x:auto} + ::after 渐变淡出
      · scrollHint 自动演示逻辑
  → polish_report.py 注入的 ENHANCE_CSS 被模板基础规则覆盖
```

## 最终解决方案

1. **`report_generator.py` 不再覆盖 `index.html`**：`generate()` 改为只生成 `data.json`
2. **HTML 样式由 `polish_report.py` 单独维护**
3. **测试/生产分离**：所有 UI 改动先在 `/bidding-test/` 验证

## 修复手机端搜索框胶囊

```css
/* 桌面端 */
.search-box {
  display: flex;
  align-items: center;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  overflow: hidden;
}
.search-box input {
  flex: 1;
  min-width: 0;
  padding: 9px 8px 9px 34px;
  border: none;
  background: transparent;
}
.search-box .search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
}
.search-btn {
  flex-shrink: 0;
  padding: 8px 16px;
  border: none;
  border-left: 1px solid var(--border);
  background: var(--accent);
  color: #fff;
  border-radius: 0 5px 5px 0;
}

/* 手机端 */
@media(max-width:768px) {
  .search-box { border-radius: 20px !important; height: 44px; }
  .search-btn { border-radius: 0 19px 19px 0 !important; padding: 9px 18px !important; }
}
```

## 修复筛选栏水平滚动

```css
@media(max-width:768px) {
  .filter-scroll-wrapper {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }
  .filter-scroll-wrapper::-webkit-scrollbar { display: none; }
  .filter-scroll-wrapper::after {
    content: '';
    position: absolute;
    right: 0; top: 0; bottom: 0;
    width: 40px;
    background: linear-gradient(to right, transparent, var(--bg));
    pointer-events: none;
  }
  .filter-row {
    flex-wrap: nowrap !important;
    gap: 6px !important;
  }
  .filter-row select, .filter-row input {
    flex-shrink: 0;
    height: 34px;
    border-radius: 17px;
  }
}
```

## 预防

- **⛔ 不要直接在生产环境改 CSS** — 先在测试环境改
- **promote.sh 推送前验证**：手机端搜索框胶囊 + 筛选栏水平滚动 + 滑动动画
