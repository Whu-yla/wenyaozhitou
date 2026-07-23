# Mobile Card Design V1.31 — Final Patterns

## Card Grid Layout (tr-level CSS Grid)

```css
tr.data-row{
  display:grid;
  grid-template-columns:1fr auto auto auto;  /* 4 columns */
  gap:3px 10px;
  padding:18px 16px;
  border-radius:14px;
  box-shadow:0 1px 3px rgba(0,0,0,.06),0 0 0 .5px rgba(0,0,0,.04);
  position:relative;  /* anchor for NEW badge */
}
```

**CRITICAL**: Use tr-level grid, NOT td-level grid. `td{display:grid}` causes label and value to share one cell.

## Row Placement

| Row | Columns | Content |
|:--|:--|:--|
| 1 | span 4 | Title (line-clamp:2) |
| 2 | col1: Customer badge, col2-4: Budget |
| 3 | span 4 | 招标单位 (with label) |
| 4 | col1: 地域 · col2: 日期 · col3: 相关度分 · col4: `›` |

```css
td.title-cell{grid-column:1/-1; grid-row:1}
td[data-label="客户"]{grid-column:1; grid-row:2}
td[data-label="预算"]{grid-column:2/span 3; grid-row:2}
td[data-label="招标单位"]{grid-column:1/-1; grid-row:3}
td[data-label="地域"]{grid-column:1; grid-row:4}
td[data-label="日期"]{grid-column:2; grid-row:4}
td[data-label="相关度"]{grid-column:3; grid-row:4}
tr.data-row::after{grid-column:4; grid-row:4}  /* › chevron */
```

## Hidden Fields (mobile)
- `td:first-child` (checkbox) — `display:none`
- `td[data-label="序号"]` — `display:none`
- `td[data-label="来源"]` — `display:none`
- `td[data-label="操作"]` — `display:none`
- `.hide-mobile` — `display:none!important`
- `.link-btn` — `display:none`

## Title
```css
td.title-cell{
  font-size:15px; font-weight:600; line-height:1.4;
  padding-right:44px;  /* room for NEW badge */
  overflow:hidden;
  display:-webkit-box;
  -webkit-line-clamp:2;
  -webkit-box-orient:vertical;
  border-bottom:1px solid rgba(0,0,0,.07);
}
td.title-cell a{font-size:inherit; line-height:inherit; color:inherit; text-decoration:none}
```

## NEW Badge
```css
.new-badge{
  position:absolute; top:14px; right:14px;
  font-size:10px; font-weight:700; padding:3px 8px;
  border-radius:5px; color:#fff; background:#ef4444; z-index:1;
}
```

## Star (bookmark)
```css
.star{font-size:18px; cursor:pointer; margin-right:4px; flex-shrink:0; z-index:2; position:relative}
.star.on{color:#f59e0b}  /* ★ gold when bookmarked */
```
Star has `event.stopPropagation()` to prevent card click navigation.

## Bottom Metadata Row
- 地域, 日期, 相关度: `font-size:12px; color:#8e8e93`
- Labels hidden (`::before{display:none}`) — self-evident fields
- Separator: `td[data-label="日期"]::before{content:'·';display:inline;margin:0 6px;color:#c7c7cc}`
- Score MUST include suffix: `${sc.toFixed(0)}分` in app.js template

## Card Click Behavior
```javascript
onclick="if(window.innerWidth<=768){window.open('${link}','_blank')}else{toggleDetail(${i.id})}"
```
Mobile: navigate to source. Desktop: expand detail.

## Back to Top Button
```javascript
// Injected in init()
const btn = document.createElement('button');
btn.id = 'btnBackTop';
btn.innerHTML = '↑';
btn.onclick = () => window.scrollTo({top:0,behavior:'smooth'});
// Scroll listener with rAF throttle:
window.addEventListener('scroll', () => {
  requestAnimationFrame(() => {
    btn.classList.toggle('show', window.scrollY > 300);
  });
}, {passive:true});
```
```css
#btnBackTop{position:fixed;bottom:80px;right:16px;width:40px;height:40px;
  border-radius:50%;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.12);
  opacity:0;transform:translateY(10px);pointer-events:none;transition:opacity .25s,transform .25s}
#btnBackTop.show{opacity:1;transform:translateY(0);pointer-events:auto}
```

## Toast Mobile Repositioning
```css
@media(max-width:768px){
  .toast{top:auto!important;bottom:100px!important;right:50%!important;transform:translateX(50%)!important}
}
```

## Empty State
```html
<tr class="empty-msg"><td colspan="N">提示文案</td></tr>
```
```css
tr.empty-msg{display:flex!important;justify-content:center;align-items:center;
  padding:48px 20px!important;background:#fff!important;
  border-radius:14px!important;color:#8e8e93!important;font-size:14px!important}
```

## Apple Design Constants
- Background: `#f5f5f7` (light) / `#0f172a` (dark)
- Card bg: `#fff` (light) / `#1c1c1e` (dark)
- Text: `#1d1d1f` (light) / `#f5f5f7` (dark)
- Muted: `#8e8e93` (light) / `#8e8e93` (dark)
- Input bg: `#f2f2f7` no border 10px radius
- Header: `rgba(255,255,255,.72)` + `backdrop-filter:blur(20px)`
- Chevron `›`: `#c7c7cc` (light) / `#545458` (dark)
- NO colored buttons. NO colored stat values. All `#1d1d1f`.

## Pitfall Checklist
1. `calc()` MUST have spaces: `calc(100vw - 16px)` not `calc(100vw-16px)`
2. JS inline styles override CSS media queries — clear them on mobile
3. Touch devices (ontouchstart) must disable drag
4. ALL input/textarea font-size ≥16px on mobile (iOS zoom)
5. ALL interactive elements ≥36px tap target
6. `td.title-cell a` uses `font-size:inherit` not hardcoded value
7. Every `<td>` must have `data-label` attribute (except title-cell)
8. Score values must include "分" suffix
