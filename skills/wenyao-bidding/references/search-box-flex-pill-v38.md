# 搜索框 Flex Pill 模式（V1.38）

## 问题

旧移动端搜索框用 `position:absolute` 定位按钮：
```css
.search-box{position:relative}
.search-box input{border-radius:22px;padding-right:72px}
.search-btn{position:absolute;right:2px;top:2px;height:40px;border-radius:0 20px 20px 0}
```

缺陷：`right:2px` 有 2px 间隙不贴合 + `height:40px` vs input `height:44px` 不匹配 + light 主题 border-color 需要单独处理。

## 修复（V1.38 最终方案）

**把 border 从 input 移到父容器 .search-box，按钮改为 flex 自然子元素：**

```css
/* 父容器持有 pill 外观 */
.search-box{
  display:flex; align-items:center; flex:1;
  position:relative;
  border-radius:22px;
  border:1px solid var(--border);
  background:var(--surface);
  overflow:hidden;  /* ← 关键：裁剪子元素保持 pill 形状 */
}
.search-box:focus-within{border-color:var(--accent)}

/* 输入框无独立边框 */
.search-box input{
  flex:1; height:44px; min-width:0;
  padding:0 8px 0 40px;  /* 左留 icon 空间 */
  border:none; background:transparent;
  font-size:16px; outline:none;
}

/* 按钮自然贴合右侧，无间隙 */
.search-btn{
  flex-shrink:0; height:44px;
  padding:0 18px; font-size:14px;
  border:none; background:var(--accent); color:#fff;
  cursor:pointer; white-space:nowrap;
}

/* light 主题只需改父容器 */
body.light .search-box{border-color:#cbd5e1}
body.light .search-box input{background:#fff;color:#1e293b}
```

## 优势

| 维度 | 旧 (absolute) | 新 (flex pill) |
|:--|:--|:--|
| 按钮贴合 | 2px 间隙 | 0 间隙 |
| 高度对齐 | 40px vs 44px 不齐 | 统一 44px |
| 主题适配 | 需分别设 input/btn | 仅设父容器 |
| focus 态 | 各管各 | `focus-within` 统一 |
| 间隙来源 | right:2px 魔法数字 | 无间隙，自然 flex |

## 同步规则

`index.html` 和 `polish_report.py` 两处必须同步修改，否则 pipeline 重生成后回退。
