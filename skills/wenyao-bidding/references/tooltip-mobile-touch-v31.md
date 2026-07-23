# Tooltip 手机端触屏适配 — V1.31

## 问题

`?` 图标 tooltip 在桌面端 hover 正常，但手机端点无反应（`title` 属性在触屏设备上不触发）。

## 修复

### 1. 点击触发 + 点击空白消失
```javascript
function showTooltip(e) {
    e.stopPropagation();
    // 清除旧 tooltip
    document.querySelectorAll('.custom-tooltip').forEach(el => el.remove());
    
    const tip = document.createElement('div');
    tip.className = 'custom-tooltip';
    tip.textContent = '...';
    
    // 边界保护：居中但不出屏
    const rect = e.target.getBoundingClientRect();
    const tipW = 260;
    let left = rect.left + rect.width/2 - tipW/2;
    if (left < 12) left = 12;
    if (left + tipW > window.innerWidth - 12) left = window.innerWidth - tipW - 12;
    
    tip.style.cssText = `position:fixed;left:${left}px;top:${rect.bottom + 8}px;width:${tipW}px;...`;
    document.body.appendChild(tip);
    
    // 延迟绑定全局 dismiss，避免立即触发
    setTimeout(() => {
        document.addEventListener('click', dismiss);
        document.addEventListener('touchstart', dismiss);
    }, 50);
}
```

### 2. HTML 中阻止冒泡
```html
<span class="tooltip-trigger" 
      onclick="event.stopPropagation();showTooltip(event)" 
      title="...">?</span>
```

### 3. 边界保护公式
```
left = max(12, min(rect.left + rect.width/2 - tipW/2, innerWidth - tipW - 12))
```

## 关键点
- `event.stopPropagation()` — 防触父级 statClick
- dismiss 用 `addEventListener` 而非 onclick — 支持触屏
- `setTimeout 50ms` — 防当前点击立即触发 dismiss
- 边界 12px 留边 — 视觉呼吸
