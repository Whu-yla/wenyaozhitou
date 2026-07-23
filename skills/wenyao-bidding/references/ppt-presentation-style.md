# PPT / 演示文稿制作规范

用户要求：材料必须**大气、撑满屏幕**，不要"一点点很小"。

## 设计原则

- 字号用 `clamp()` 自适应分辨率：标题 `clamp(48px,8vw,96px)`，正文 `clamp(16px,2vw,24px)`
- 全屏沉浸布局：`height:100vh; overflow:hidden;`
- 深色背景基调：`background:#0b1120; color:#e2e8f0`
- Slide 切换动画：`opacity + transform:scale(.96)` + `cubic-bezier(.4,0,.2,1)` 过渡
- 数字数据用 `linear-gradient` 渐变色大字：`font-weight:900; font-size:clamp(40px,8vw,96px)`
- 卡片用半透明玻璃态：`background:rgba(30,41,59,.9); border:2px solid #334155; border-radius:clamp(12px,2vw,24px)`

## 交互

- 键盘 ← → 翻页，F 全屏，Esc 退出全屏
- 触摸滑动翻页
- 底部导航栏 + 页码指示器

## 内容原则

- 故事线必须跟随 `changelog.html` 版本时间线（V0.1→V1.41），不自编
- 署名必须用「中南电力设计院数智科技」，禁止「量子纪元/程浩团队」
- 每页一个主题，用 Grid 卡片或 Timeline 组织
- 版本里程碑用大号版本号 + 简短描述 + 标签分类

## 技术栈

- 纯 HTML/CSS/JS，零外部依赖
- 部署到 `/var/www/html/bidding/`，Nginx 直接服务
- 参考实现：`wenyao-story.html`（14 页开发全纪实）
- 培训通知参考：`training-notice.html`
