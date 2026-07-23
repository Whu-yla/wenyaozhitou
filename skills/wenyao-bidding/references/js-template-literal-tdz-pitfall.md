# JS 模板字符串 TDZ 陷阱 (V1.36)

## 症状
中标 Tab 完全无数据，且统计卡片显示 0，但 data.json 正常加载。

## 根因
```javascript
// ❌ 错误：starred 在第454行先被使用，但在第456行才声明
const menuHtml = `...toggleKebab(event,${i.id},...,${starred})...`;  // line 454
const newDot = isNew(i) ? 'NEW' : '';                                // line 455
const starred = getStars().includes(String(i.id));                   // line 456

// ReferenceError: Cannot access 'starred' before initialization
```

`const` 变量在模板字符串 `${}` 中先引用后声明 → ReferenceError → `doFilter()` 中断 → 页面静默显示 0 条。

## 修复
```javascript
// ✅ 正确：声明在前，使用在后
const starred = getStars().includes(String(i.id));                   // 先声明
const menuHtml = `...toggleKebab(event,${i.id},...,${starred})...`;  // 再使用
const newDot = isNew(i) ? 'NEW' : '';
```

## 排查方法
浏览器 Console 手动调用 `init()` → 看报错行号 → 检查该行模板字符串中的变量是否已声明。
