#!/usr/bin/env python3
"""
工地安全检测 — 批量标注工具
批量读取图片 + JSON 检测结果，自动生成标注图
"""

import json
import os
import sys
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# 颜色配置
# ============================================================
GREEN  = "#22c55e"
RED    = "#ef4444"
DARK   = "#0f172a"

# ============================================================
# 字体查找
# ============================================================
def find_font(size=16):
    # Windows 常见中文字体路径
    windir = os.environ.get("WINDIR", "C:\\Windows")
    candidates = [
        # Windows
        os.path.join(windir, "Fonts", "msyh.ttc"),       # 微软雅黑
        os.path.join(windir, "Fonts", "msyhbd.ttc"),     # 微软雅黑粗体
        os.path.join(windir, "Fonts", "simsun.ttc"),     # 宋体
        os.path.join(windir, "Fonts", "SIMHEI.TTF"),     # 黑体
        os.path.join(windir, "Fonts", "SIMLI.TTF"),      # 隶书
        os.path.join(windir, "Fonts", "msyh.ttf"),       # 微软雅黑 .ttf
        # Linux / macOS
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/PingFang.ttc",             # macOS 苹方
        "/System/Library/Fonts/STHeiti Light.ttc",        # macOS 黑体
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

# ============================================================
# 核心标注函数
# ============================================================
def annotate_image(image_path: str, json_data: dict, output_path: str,
                   show_bbox=True, show_labels=True, show_header=True,
                   line_width=4, font_size=22, detection_type=""):
    """
    在图片上绘制检测框和风险标签
    """
    # 加载图片
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    font = find_font(font_size)
    font_bold = find_font(font_size + 2)

    img_w, img_h = img.size

    # 解析 JSON
    results = json_data
    if isinstance(results, dict):
        if "data" in results and "识别结果" in results["data"]:
            results = results["data"]["识别结果"]
        elif "识别结果" in results:
            results = results["识别结果"]
        else:
            print(f"  ⚠️ 未知的 JSON 结构，键: {list(results.keys())}")
            return False

    if not isinstance(results, list):
        print(f"  ⚠️ '识别结果' 不是数组")
        return False

    # 统计
    total_people = 0
    risk_people = 0
    risk_items_list = []

    # 先绘制安全框（底层），再绘制风险框（顶层）
    safe_draws = []
    risk_draws = []

    for item in results:
        if item.get("entity") != "人员":
            continue

        bbox = item.get("bbox")
        if not bbox or len(bbox) < 4:
            continue

        total_people += 1
        risks = item.get("risk_result", [])
        has_risk = any(r.get("is_risk") == "是" for r in risks)

        if has_risk:
            risk_people += 1
            risk_draws.append((bbox, risks))
            risk_items_list.extend(r for r in risks if r.get("is_risk") == "是")
        else:
            safe_draws.append(bbox)

    def _draw_bbox(x1, y1, x2, y2, color, lw, dash=False):
        if dash:
            for i in range(0, int((x2 - x1) * 1.5), int(lw * 4)):
                seg_start = x1 + i
                seg_end = min(seg_start + lw * 2, x2)
                if seg_start < x2:
                    draw.line([(seg_start, y1), (seg_end, y1)], fill=color, width=lw)
                    draw.line([(seg_start, y2), (seg_end, y2)], fill=color, width=lw)
            for i in range(0, int((y2 - y1) * 1.5), int(lw * 4)):
                seg_start = y1 + i
                seg_end = min(seg_start + lw * 2, y2)
                if seg_start < y2:
                    draw.line([(x1, seg_start), (x1, seg_end)], fill=color, width=lw)
                    draw.line([(x2, seg_start), (x2, seg_end)], fill=color, width=lw)
        else:
            draw.rectangle([x1, y1, x2, y2], outline=color, width=lw)

    all_labels = []

    def _label_distance(px, py, x1, y1, x2, y2, lw, lh):
        """计算标签中心到人物框最近边的距离"""
        cx, cy = px + lw // 2, py + lh // 2  # 标签中心
        bx, by = (x1 + x2) // 2, (y1 + y2) // 2  # 人物框中心
        # 尽量贴近框：只算垂直距离
        if cy < y1:
            return y1 - cy  # 标签在上方，到框顶边的距离
        elif cy > y2:
            return cy - y2  # 标签在下方，到框底边的距离
        else:
            return 0  # 标签在框内

    def _get_label_pos(x1, y1, x2, y2, lw, lh):
        HEADER_H = 52
        candidates = []
        # 1) 上方（最优先，贴近头）
        top_y = y1 - lh - 4
        if top_y >= HEADER_H:
            candidates.append(('above', top_y))
        # 2) 下方（次优先）
        bottom_y = y2 + 4
        if bottom_y + lh <= img_h:
            candidates.append(('below', bottom_y))
        # 3) 框内
        inner_y = max(HEADER_H, y1 + 4)
        if inner_y + lh <= y2 - 4:
            candidates.append(('inner', inner_y))
        # 4) 保底：下方（不超出底部），不跳到顶部信息栏里
        force_below = min(y2 + 20, img_h - lh - 4)
        if force_below >= HEADER_H:
            candidates.append(('below', force_below))
        # 5) 最后保底：紧贴 header 下方
        candidates.append(('below', HEADER_H + 2))

        best_pos = None
        best_overlap = False
        best_dist = float('inf')

        for pos_type, py in candidates:
            px = max(4, min(x1, img_w - lw - 4))
            if px < 4:
                px = 4

            overlap = False
            for (ex1, ey1, ex2, ey2) in all_labels:
                if not (px + lw < ex1 or px > ex2) and not (py + lh < ey1 or py > ey2):
                    overlap = True
                    break

            dist = _label_distance(px, py, x1, y1, x2, y2, lw, lh)

            if not overlap:
                # 非重叠位置：选距离最近的
                if not best_pos or dist < best_dist:
                    best_pos = (px, py)
                    best_dist = dist
                    best_overlap = False
            else:
                # 都重叠时，选距离最近的（至少比跳到顶部好）
                if best_overlap or (not best_pos and not best_overlap):
                    if dist < best_dist:
                        best_pos = (px, py)
                        best_dist = dist
                        best_overlap = True

        return best_pos or (max(4, min(x1, img_w - lw - 4)), HEADER_H)

    # ---- 安全框 ----
    for bbox in safe_draws:
        if not show_bbox:
            continue
        x1, y1, x2, y2 = bbox
        _draw_bbox(x1, y1, x2, y2, GREEN, line_width)

        if show_labels:
            lw, lh = 90, 30
            lx, ly = _get_label_pos(x1, y1, x2, y2, lw, lh)
            draw.rectangle([lx, ly, lx + lw, ly + lh], fill=GREEN)
            draw.text((lx + 6, ly + 3), "安全", fill="white", font=font)
            all_labels.append((lx, ly, lx + lw, ly + lh))

    # ---- 风险框 ----
    for bbox, risks in risk_draws:
        x1, y1, x2, y2 = bbox

        if show_bbox:
            _draw_bbox(x1, y1, x2, y2, RED, line_width + 1, dash=True)

        if show_labels:
            risk_lines = [
                f"[违规] {r.get('desc', '')}{r.get('sub_entity', '')} ({round(r.get('confidence', 0) * 100)}%)"
                for r in risks if r.get("is_risk") == "是"
            ]
            line_h, pad = 30, 8
            lw = min(340, img_w - 8)
            lh = len(risk_lines) * line_h + pad * 2
            lx, ly = _get_label_pos(x1, y1, x2, y2, lw, lh)

            draw.rectangle([lx, ly, lx + lw, ly + lh], fill=(239, 68, 68, 235))
            for i, line in enumerate(risk_lines):
                draw.text((lx + pad, ly + pad + line_h * i + 2),
                          line, fill="white", font=font_bold)

            all_labels.append((lx, ly, lx + lw, ly + lh))

            # 整改建议
            rectifications = [r.get("rectification", "") for r in risks
                              if r.get("is_risk") == "是" and r.get("rectification")]
            if rectifications and y2 + 28 < img_h:
                rect_text = rectifications[0][:28] + ("…" if len(rectifications[0]) > 28 else "")
                draw.rectangle([x1, y2 + 2, x1 + min(lbl_w, img_w - x1 - 4), y2 + 26],
                               fill=(239, 68, 68, 200))
                draw.text((x1 + 4, y2 + 5), "💡 " + rect_text, fill="white", font=font)

    # ---- 顶部信息栏 ----
    if show_header:
        h = 48
        draw.rectangle([0, 0, img_w, h], fill=(15, 23, 42, 225))
        title = "工地安全 AI 检测"
        title += f" | 共 {total_people} 人  ·  {risk_people} 人违规"
        draw.text((12, 12), title, fill="#f8fafc", font=font_bold)

    # 保存
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "PNG")
    return True


# ============================================================
# 批量处理
# ============================================================
def batch_process(image_dir: str, json_dir: str, output_dir: str,
                  json_suffix="_result", **kwargs):
    """
    批量处理文件夹中的图片

    匹配规则:
    - 图片文件: *.jpg, *.jpeg, *.png, *.webp
    - 对应的 JSON: 同名 + json_suffix 后缀，或直接同名.json
      例如: img_001.jpg → img_001_result.json 或 img_001.json
    """
    image_dir = Path(image_dir)
    json_dir = Path(json_dir) if json_dir else image_dir
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 支持的图片格式
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    images = sorted([
        f for f in image_dir.iterdir()
        if f.suffix.lower() in image_exts
    ])

    if not images:
        print(f"❌ 在 {image_dir} 中未找到图片文件")
        return

    print(f"\n{'='*60}")
    print(f"  工地安全检测 — 批量标注")
    print(f"{'='*60}")
    print(f"  图片目录: {image_dir}")
    print(f"  JSON目录: {json_dir}")
    print(f"  输出目录: {output_dir}")
    print(f"  共找到 {len(images)} 张图片\n")

    success = 0
    failed = 0
    skipped = 0

    for img_path in images:
        stem = img_path.stem  # 不含扩展名的文件名

        # 尝试多个 JSON 匹配模式
        json_candidates = [
            json_dir / f"{stem}{json_suffix}.json",
            json_dir / f"{stem}.json",
            json_dir / f"{stem}_result.json",
        ]
        # 去重
        seen = set()
        json_candidates_unique = []
        for jc in json_candidates:
            if str(jc) not in seen:
                seen.add(str(jc))
                json_candidates_unique.append(jc)

        json_path = None
        for jc in json_candidates_unique:
            if jc.exists():
                json_path = jc
                break

        if not json_path:
            print(f"  ⏭️  [{stem}] 跳过 (未找到匹配的 JSON)")
            skipped += 1
            continue

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ❌ [{stem}] JSON 解析失败: {e}")
            failed += 1
            continue

        # 从文件名提取识别类型
        dt = ""
        for p in stem.split("_"):
            if "检测" in p or "识别" in p:
                dt = p
                break

        out_path = output_dir / f"{stem}_annotated.png"
        ok = annotate_image(str(img_path), data, str(out_path), detection_type=dt)
        if ok:
            print(f"  ✅ [{stem}] → {out_path.name}")
            success += 1
        else:
            print(f"  ❌ [{stem}] 标注失败")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  处理完成:")
    print(f"  ✅ 成功: {success}")
    print(f"  ⏭️  跳过: {skipped}")
    print(f"  ❌ 失败: {failed}")
    print(f"{'='*60}\n")


# ============================================================
# 单文件处理
# ============================================================
def single_process(image_path: str, json_path: str, output_path: str, **kwargs):
    print(f"\n{'='*60}")
    print(f"  单文件标注")
    print(f"{'='*60}")

    if not os.path.exists(image_path):
        print(f"❌ 图片不存在: {image_path}")
        return

    if not os.path.exists(json_path):
        print(f"❌ JSON 不存在: {json_path}")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ JSON 解析失败: {e}")
        return

    if not output_path:
        p = Path(image_path)
        output_path = str(p.parent / f"{p.stem}_annotated.png")

    ok = annotate_image(image_path, data, output_path, **kwargs)
    if ok:
        print(f"✅ 标注完成 → {output_path}")
    else:
        print(f"❌ 标注失败")


# ============================================================
# CLI 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="工地安全检测标注工具 — 批量/单文件标注图片"
    )
    parser.add_argument("image", nargs="?", help="图片路径（单文件模式）或图片目录（批量模式）")
    parser.add_argument("-j", "--json", help="JSON 文件路径（单文件模式）或 JSON 目录（批量模式，默认同图片目录）")
    parser.add_argument("-o", "--output", default="./output",
                        help="输出路径（单文件时为文件路径，批量时为目录，默认 ./output）")
    parser.add_argument("--json-suffix", default="_result",
                        help="JSON 文件名后缀（批量模式，如 _result 匹配 xxx_result.json，默认 _result）")
    parser.add_argument("--no-bbox", action="store_true", help="不显示检测框")
    parser.add_argument("--no-labels", action="store_true", help="不显示标签文字")
    parser.add_argument("--no-header", action="store_true", help="不显示顶部信息栏")
    parser.add_argument("--line-width", type=int, default=4, help="框线宽度（默认 4）")
    parser.add_argument("--font-size", type=int, default=22, help="字体大小（默认 22）")
    parser.add_argument("--batch", action="store_true", help="强制批量模式（当 image 是目录时自动批量）")

    args = parser.parse_args()

    kwargs = {
        "show_bbox": not args.no_bbox,
        "show_labels": not args.no_labels,
        "show_header": not args.no_header,
        "line_width": args.line_width,
        "font_size": args.font_size,
    }

    # 没有参数则显示帮助
    if not args.image:
        parser.print_help()
        print("\n\n📌 使用示例:")
        print("  # 单文件")
        print("  python safety_annotator.py photo.jpg -j result.json -o annotated.png")
        print()
        print("  # 批量处理文件夹")
        print("  python safety_annotator.py ./images -j ./jsons -o ./annotated")
        print("  python safety_annotator.py ./images --batch -o ./annotated")
        return

    # 判断模式
    is_dir = os.path.isdir(args.image)
    if is_dir or args.batch:
        batch_process(
            image_dir=args.image,
            json_dir=args.json or args.image,
            output_dir=args.output,
            json_suffix=args.json_suffix,
            **kwargs
        )
    else:
        single_process(
            image_path=args.image,
            json_path=args.json,
            output_path=args.output,
            **kwargs
        )


if __name__ == "__main__":
    main()
