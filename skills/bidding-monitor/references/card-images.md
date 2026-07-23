# ⚠️ 已废弃 — 企微图文卡片横幅图生成（Pillow方案）

> **此方案已被全AI封面替代。** 用户要求"不要用pillow了，都采用QWEN"。所有卡片封面现在由通义万相 `wanx2.0-t2i-turbo` 生成，缓存于 `img_gen/cache/`。
> 本文档保留供历史参考，新开发请参考 `references/ai-cover.md`。

## 用途

企微 `news` 消息类型的每张卡片需要一个 `picurl` 指向横幅图。按客户分类配色生成6张+1张品牌图。

## 生成脚本

```python
from PIL import Image, ImageDraw, ImageFont

CATEGORIES = {
    "🔴 五大发电":    {"color": (220, 38, 38),    "short": "wd",   "icon": "⚡"},
    "🟠 国网/南网":    {"color": (234, 88, 12),    "short": "gw",   "icon": "🔌"},
    "🟡 地方能源集团":  {"color": (217, 119, 6),   "short": "df",   "icon": "🏭"},
    "🟢 政府/公共事业":  {"color": (5, 150, 105),   "short": "zf",   "icon": "🏛"},
    "🔵 电力/央企/工业": {"color": (37, 99, 235),   "short": "yq",   "icon": "🏗"},
    "⚪ 其他":         {"color": (71, 85, 105),   "short": "other","icon": "📋"},
}

W, H = 1000, 500  # 2:1比例
# 输出到 /var/www/html/bidding/img/{short}.png
```

## 设计规范

- 尺寸：1000×500 px（2:1，企微推荐比例）
- 背景：深→亮渐变（顶部深色→底部主色）
- 网格纹理：40px间距细线
- 图标：左侧大号emoji（140px字体）
- 标题：右上中文名（60px加粗）+ 英文副标题（24px）
- 品牌：右下「中南电力设计院 · 数智科技 · 文鳐智投」（20px）
- 格式：PNG（透明支持但不用，RGB即可）

## 部署

- 目录：`/var/www/html/bidding/img/`
- Nginx自动serve，URL如 `https://www.yfzx.online/bidding/img/yq.png`
- `report_generator.py` 归档时自动 `copytree` img目录
- 新增分类时：①加字典项 ②重新生成 ③更新 `wecom_push.py` 的 `CAT_IMG`

## 依赖

- Pillow (`pip install pillow`)
- DejaVu 字体 (`/usr/share/fonts/truetype/dejavu/`)
