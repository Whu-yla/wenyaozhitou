---
name: changelog-auto-update
description: 文鳐智投更新日志自动维护 — 每次重大系统变动必须自动追加到 changelog.html，不等用户提醒。
category: bidding
---

# 更新日志自动维护

## 铁律

⚠️ **每次完成重大系统变动后，必须主动更新 `/var/www/html/bidding/changelog.html`，不等用户提醒！**

## 触发条件

以下情况必须追加更新日志条目：

| 变动类型 | 示例 | 标签 |
|:--|:--|:--|
| 核心架构变更 | 采集管线升级、新平台接入、评分引擎改版 | `tag-core` 核心 |
| 新功能上线 | 新增面板/图表/筛选器/导出功能 | `tag-new` 新增 |
| Bug 修复 | 空白页/数据错误/推送失败修复 | `tag-fix` 修复 |
| 体验优化 | 布局/性能/加载速度改善 | `tag-imp` 优化 |
| Nginx/服务器变更 | 安全加固、性能调优、守护脚本 | `tag-core` 核心 |

## 更新格式

在 `changelog.html` 的 `<div class="timeline">` 最顶部插入新版本块：

```html
    <!-- VX.X -->
    <div class="version major">
      <div class="ver-header">
        <span class="ver-num">VX.X</span>
        <span class="ver-date">YYYY-MM-DD</span>
        <span class="ver-title">简短描述（≤20字）</span>
      </div>
      <div class="changes">
        <ul>
          <li><span class="tag tag-core">核心</span> 变更描述</li>
          <li><span class="tag tag-new">新增</span> 变更描述</li>
        </ul>
      </div>
    </div>
```

## 版本号规则

- 同一天多个变动：V1.2 → V1.3 → V1.4（小版本递增）
- 跨天：第二天从 VX.0 开始，或延续前一天递增
- 重大里程碑（如 v3 管线）：标记 `class="version major"`（橙色大圆点）
- 普通更新：标记 `class="version"`（蓝色小圆点）

## 可用标签

| CSS class | 含义 |
|:--|:--|
| `tag tag-core` | 核心 |
| `tag tag-new` | 新增 |
| `tag tag-fix` | 修复 |
| `tag tag-imp` | 优化 |
| `tag tag-ux` | UX |

## 操作流程

1. 完成系统变动
2. 用 `read_file` 读 `/var/www/html/bidding/changelog.html`
3. 在 `<!-- Vx.x -->` 最新条目上方插入新版本块
4. 用 `patch` 写入（⚠️ 不要用 write_file——会破坏整个文件）
5. `chmod 644` 确保 nginx 可读
6. 用 `curl -sI` 验证可访问

## ⚠️ 关键坑

1. **禁用缓存后立即生效**：Nginx 已设 `no-cache, no-store, must-revalidate`，更新后用户刷新即见，不需要等 5 分钟
2. **用 patch 不用 write_file**：patch 只改目标区域，write_file 需写完整文件（300+ 行容易出错）
3. **写了 ≠ 发布了**：用户明确反馈「你不是写，你要发布」。改完文件后必须 `curl -sI` + `grep` 双重验证线上可访问
4. **chmod 644 必做**：nginx worker 以 `www-data` 运行，文件必须是 644 否则 403
5. **验证最少验证**：`curl -sI | grep HTTP/` 确认 200 + `grep "Vx.x" /var/www/html/bidding/changelog.html` 确认插入
