# DOM元素ID不匹配导致 init() 静默崩溃

**日期**：2026-06-26  
**版本**：V1.35  
**严重级别**：🔥 致命 — 全页白屏

## 症状
- 页面 title 正确、CSS 正常、表头可见
- **表格显示 "招标 0" / "中标 0"（永远空表）**
- `curl` 检查 data.json 200 OK、数据完整（60条招标+8条中标）
- **控制台报错**：`TypeError: Cannot set properties of null (setting 'textContent')` at app.js:107
- 仅浏览器渲染可发现，curl 全链路检查全部通过

## 根因
```javascript
// app.js line 107
document.getElementById('lastUpdate').textContent = '数据更新: ' + dt;
```

`#lastUpdate` 元素在 index.html 中**不存在**（HTML 模板仍为静态文本「系统运行中」）。

**因果链**：`getElementById → null → .textContent = → TypeError → init() 中断 → doFilter() 永不执行 → 全页空表`

## 根本原因
**app.js 与 index.html 版本不匹配**。app.js V1.28 引入了「数据更新时间」功能，依赖 `#lastUpdate` 元素，但 index.html 模板从未更新（仍为「系统运行中」静态文本）。所有数据加载正常，纯粹是 DOM 元素缺失导致渲染管线中断。

## 修复（四层防护）

### 1. index.html（修复根源）
```html
<!-- 之前 -->
<span class="dot"></span> 系统运行中

<!-- 之后 -->
<span class="dot"></span> <span id="lastUpdate">数据更新: —</span>
```

### 2. app.js（防御层）
```javascript
// 之前 — 无保护
document.getElementById('lastUpdate').textContent = '数据更新: ' + dt;

// 之后 — null 安全
const el = document.getElementById('lastUpdate');
if (el) el.textContent = '数据更新: ' + dt;
```

### 3. report_generator.py（模板源）
同步更新模板中的 header 元素。

### 4. polish_report.py（双阶段注入）
```python
# Stage 1: 检测旧模板「系统运行中」→ 替换为 lastUpdate span
if '系统运行中' in html and 'id="lastUpdate"' not in html:
    html = html.replace(
        '<span class="dot"></span> 系统运行中',
        '<span class="dot"></span> <span id="lastUpdate">数据更新: —</span>')

# Stage 2: 在 lastUpdate 存在时注入密度按钮
if 'densityBtn' not in html and 'id="lastUpdate"' in html:
    html = html.replace(
        '<span class="dot"></span> <span id="lastUpdate">',
        '<span class="dot"></span> <span id="lastUpdate">\n    <button ...densityBtn...>')
```

## 预防铁律
1. **任何 JS 新增 DOM 引用必须同时在 HTML 模板添加对应元素**
2. **所有 `document.getElementById()` 调用加 null 检查** — 不要让一个缺失元素崩溃整个应用
3. **polish_report.py 的注入逻辑必须检测旧模板格式** — 不仅是目标格式（"系统运行中" vs "id=lastUpdate"）
4. **版本不匹配检测**：app.js 初始化时可输出缺失元素清单，而非静默崩溃
