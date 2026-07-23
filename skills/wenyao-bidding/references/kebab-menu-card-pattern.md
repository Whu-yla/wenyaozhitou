# Kebab 菜单卡片模式 (V1.32)

## 设计决策

用户明确表示：
- 长按触发分享：「反人类」— 不可用
- `↗` 图标分享：「可读性太差了」— 不可用
- **最终方案：卡片右上角 `⋯` 按钮 + 弹出菜单**

对标产品：Linear.app、GitHub Mobile、Notion 的 `⋯` 菜单。

## HTML 结构

每张卡片（`tr.data-row`）的 `td.title-cell` 中包含：

```html
<span class="kebab-btn" onclick="event.stopPropagation();toggleKebab(event,${id},'${title}','${url}',${starred})">⋯</span>
```

- `event.stopPropagation()` — 不触发卡片的 `window.open()` 跳转
- `toggleKebab()` — 创建/管理菜单

## CSS

```css
/* 按钮 */
.kebab-btn{
  position:absolute; top:12px; right:12px;
  width:28px; height:28px; border-radius:50%;
  display:flex; align-items:center; justify-content:center;
  font-size:16px; color:#8e8e93; cursor:pointer; z-index:3;
  letter-spacing:-2px; font-weight:700;
}
.kebab-btn:active{background:rgba(0,0,0,.08)}

/* 菜单 */
.kebab-menu{
  position:fixed;
  background:#fff; border-radius:12px;
  box-shadow:0 4px 24px rgba(0,0,0,.15);
  z-index:9999; min-width:140px; overflow:hidden;
  animation:menuIn .15s ease;
}
body.dark .kebab-menu{background:#2c2c2e; box-shadow:0 4px 24px rgba(0,0,0,.5)}

/* 菜单项 */
.kebab-menu button{
  display:block; width:100%; padding:12px 16px;
  border:none; background:none; font-size:14px;
  color:#1d1d1f; text-align:left; cursor:pointer;
  border-bottom:1px solid rgba(0,0,0,.06); font-family:inherit;
}
.kebab-menu button:last-child{border-bottom:none}
.kebab-menu button:active{background:rgba(0,0,0,.06)}

/* Overlay */
.kebab-overlay{position:fixed; inset:0; z-index:9998; background:transparent}

@keyframes menuIn{from{opacity:0;transform:scale(.95)}to{opacity:1;transform:scale(1)}}
```

## NEW badge 和 kebab 冲突解决

两者都在 `td.title-cell` 内绝对定位，同处右上角会重叠。

**解决方案**：
```css
.new-badge{position:absolute; top:14px; left:14px; ...}  /* 左上角 */
.kebab-btn{position:absolute; top:12px; right:12px; ...}  /* 右上角 */
```

标题右侧留白 `padding-right:36px`（仅为 kebab 留空间，不再是 44px）。

## JS — toggleKebab()

```javascript
function toggleKebab(e, id, title, url, starred) {
    // 清除旧菜单
    document.querySelectorAll('.kebab-menu,.kebab-overlay').forEach(el => el.remove());
    
    // 创建 overlay（点外部关闭）
    const overlay = document.createElement('div');
    overlay.className = 'kebab-overlay';
    overlay.onclick = () => { overlay.remove(); document.querySelector('.kebab-menu')?.remove(); };
    
    // 创建菜单
    const menu = document.createElement('div');
    menu.className = 'kebab-menu';
    
    const items = [
        {label: '📤 分享', action: () => shareItem(id, title, url)},
        {label: '🔗 复制链接', action: () => { navigator.clipboard?.writeText(url).then(() => toast('链接已复制','success')); }},
        {label: '📋 复制标题', action: () => { navigator.clipboard?.writeText(title).then(() => toast('标题已复制','success')); }},
        {label: (starred?'☆':'⭐')+' '+(starred?'取消收藏':'收藏'), action: () => { toggleStar(id); }}
    ];
    
    items.forEach(item => {
        const btn = document.createElement('button');
        btn.textContent = item.label;
        btn.onclick = () => { item.action(); overlay.remove(); menu.remove(); };
        menu.appendChild(btn);
    });
    
    document.body.appendChild(overlay);
    document.body.appendChild(menu);
    
    // 定位到按钮下方
    const btnRect = e.target.getBoundingClientRect();
    menu.style.top = (btnRect.bottom + 4) + 'px';
    menu.style.right = (window.innerWidth - btnRect.right) + 'px';
}
```

## 菜单项设计

| 位置 | 内容 | 行为 |
|:--|:--|:--|
| 1 | 📤 分享 | `navigator.share()` 或复制链接 |
| 2 | 🔗 复制链接 | `navigator.clipboard.writeText(url)` |
| 3 | 📋 复制标题 | `navigator.clipboard.writeText(title)` |
| 4 | ⭐ 收藏 / ☆ 取消收藏 | `toggleStar(id)` — 实时联动 Toast + Badge |

## 验证清单

1. 卡片右上角有 `⋯` 按钮（非长按、非图标）
2. 点 `⋯` → 菜单弹出（scale 动画）
3. 点菜单外任意位置 → 菜单关闭
4. 📤 分享在手机端调起系统分享面板
5. 🔗/📋 复制后有 Toast 提示
6. ⭐ 收藏/取消收藏实时更新 Badge
7. 暗色模式下菜单可读
8. NEW badge 在左上角，kebab 在右上角，无重叠
