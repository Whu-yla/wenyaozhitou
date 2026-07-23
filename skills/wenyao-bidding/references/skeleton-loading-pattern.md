# 骨架屏加载模式 (V1.27)

## 问题
页面加载时表格显示「显示 0 条」→ 数据到后突然填充 57 行，生硬闪现。

## 方案
在 `init()` 开始时立即注入骨架行，数据就绪后 `doFilter()` 覆盖。

### CSS
```css
.skel{
  display:inline-block;
  background:linear-gradient(90deg,var(--border) 25%,var(--surface) 50%,var(--border) 75%);
  background-size:200% 100%;
  animation:skelShimmer 1.5s infinite;
  border-radius:4px;
  vertical-align:middle
}
@keyframes skelShimmer{
  0%{background-position:200% 0}
  100%{background-position:-200% 0}
}
body.light .skel{
  background:linear-gradient(90deg,#e2e8f0 25%,#f8fafc 50%,#e2e8f0 75%);
  background-size:200% 100%
}
```

### JS
```javascript
function skeletonRows(n) {
    let html = '';
    for (let i = 0; i < Math.min(n, 10); i++) {
        html += `<tr class="skel-row">
            <td><span class="skel" style="width:16px;height:16px"></span></td>
            <td><span class="skel" style="width:20px;height:12px"></span></td>
            <td><span class="skel" style="width:50px;height:8px"></span></td>
            <td><span class="skel" style="width:${180+Math.random()*120|0}px;height:12px"></span></td>
            ...
        </tr>`;
    }
    return html;
}
// init() 中：
document.getElementById("tBidTb").innerHTML = skeletonRows(ps);
```

### 注意
- 骨架行数 ≤ min(n, 10)，不生成超过 10 行避免 DOM 过重
- 标题宽度用 `Math.random()` 产生自然长短变化
- 暗/亮主题各需独立的 shimmer 渐变颜色
