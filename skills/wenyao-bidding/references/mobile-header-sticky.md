# 移动端体验规范

## 聊天面板自动弹出 — 手机必须禁用

手机屏幕小，自动弹出聊天面板遮挡整个页面，体验极差。

```javascript
// chat-widget.js — 仅桌面端自动弹出
setTimeout(() => {
  if (window.innerWidth > 768 && !sessionStorage.getItem('chat_auto_opened')) {
    sessionStorage.setItem('chat_auto_opened', '1');
    window.openChat();
  }
}, 3000);
```

检测 `window.innerWidth > 768`，手机/小平板不弹。

## 头部 sticky 固定

滚动时头部必须保持在视口顶部——用户往下翻数据时仍需看到筛选条件和更新时间。

```css
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;  /* 高于表格内容，低于聊天面板(9999) */
}

/* 移动端增强：毛玻璃效果 */
@media(max-width:768px) {
  .app-header {
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
  }
}
```

⚠️ sticky 需要 `top:0` 明确声明，不能省略。z-index 设 100 即可（聊天面板在 9999 不受影响）。
