import http.client
import mimetypes
import json
import os
from codecs import encode
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ====== 配置区（你只需要改这里）======

# 图片文件夹（你的图片都放在这里）
IMAGE_DIR = r"D:\lvjun\文档文件\alarmData (2)\大模型识别源文件0702\大模型识别图片"

# 标注图输出文件夹
OUTPUT_DIR = r"D:\lvjun\文档文件\alarmData (2)\大模型识别源文件0702\标注结果"

# 大模型接口地址
API_HOST = "www.wybz.top"
API_PORT = 9001
API_PATH = "/AiServer/ai/vl/safe_risk_flow_2603"

# 你的 Token（把下面引号里的内容换成你的 Token）
TOKEN = "Bearer 在这里填你的Token"

# ====== 以下代码不用改 ======


# ---------- 字体查找（兼容 Windows）----------
def find_font(size=22):
    windir = os.environ.get("WINDIR", "C:\\Windows")
    candidates = [
        os.path.join(windir, "Fonts", "msyh.ttc"),
        os.path.join(windir, "Fonts", "msyhbd.ttc"),
        os.path.join(windir, "Fonts", "simsun.ttc"),
        os.path.join(windir, "Fonts", "SIMHEI.TTF"),
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# ---------- 发送图片给大模型 ----------
def analyze_one_image(image_path):
    filename = os.path.basename(image_path)
    boundary = 'wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'
    dataList = []

    dataList.append(encode('--' + boundary))
    dataList.append(encode(f'Content-Disposition: form-data; name=upload_file; filename="{filename}"'))

    fileType = mimetypes.guess_type(image_path)[0] or 'application/octet-stream'
    dataList.append(encode(f'Content-Type: {fileType}'))
    dataList.append(encode(''))

    with open(image_path, 'rb') as f:
        dataList.append(f.read())

    dataList.append(encode('--' + boundary + '--'))
    dataList.append(encode(''))

    body = b'\r\n'.join(dataList)

    headers = {
        'authorization': TOKEN,
        'Content-Type': f'multipart/form-data; boundary={boundary}',
    }

    try:
        conn = http.client.HTTPSConnection(API_HOST, API_PORT, timeout=60)
        conn.request("POST", API_PATH, body, headers)
        res = conn.getresponse()
        data = res.read()
        return json.loads(data.decode("utf-8"))
    except Exception as e:
        return {"code": -1, "msg": f"请求失败: {str(e)}"}
    finally:
        conn.close()


# ---------- 在图片上画标注 ----------
def annotate_image(img, json_data, detection_type=""):
    draw = ImageDraw.Draw(img)
    font = find_font(22)
    font_bold = find_font(24)

    img_w, img_h = img.size

    # 解析 JSON
    results = json_data
    if isinstance(results, dict):
        if "data" in results and "识别结果" in results["data"]:
            results = results["data"]["识别结果"]
        elif "识别结果" in results:
            results = results["识别结果"]
        else:
            return False

    if not isinstance(results, list):
        return False

    total_people = 0
    risk_people = 0
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
        else:
            safe_draws.append(bbox)

    all_labels = []  # 收集所有标签位置，用于检测重叠

    def _label_dist(px, py, x1, y1, x2, y2, lw, lh):
        """标签中心到人物框最近边的距离"""
        cx, cy = px + lw // 2, py + lh // 2
        if cy < y1:
            return y1 - cy
        elif cy > y2:
            return cy - y2
        return 0

    def get_label_pos(x1, y1, x2, y2, lbl_w, lbl_h):
        """自适应计算标签位置：上→下→内，选最近的非重叠位置"""
        HEADER_H = 52  # 顶部信息栏高度+边距

        # 候选位置：上方、下方、内部（从近到远排）
        candidates = []

        # 位置1: 框上方（紧贴人头）
        top_y = y1 - lbl_h - 4
        if top_y >= HEADER_H:
            candidates.append(("top", top_y))

        # 位置2: 框下方
        bottom_y = y2 + 4
        if bottom_y + lbl_h <= img_h:
            candidates.append(("bottom", bottom_y))

        # 位置3: 框内部（靠近上边缘）
        inner_y = max(HEADER_H, y1 + 4)
        if inner_y + lbl_h <= y2 - 4:
            candidates.append(("inner", inner_y))

        # 保底：下方（不超出底部），不跳到顶部信息栏里
        force_below = min(y2 + 20, img_h - lbl_h - 4)
        if force_below >= HEADER_H:
            candidates.append(("bottom", force_below))

        # 最后保底：紧贴 header 下方
        candidates.append(("bottom", HEADER_H + 2))

        best = None
        best_overlap = False
        best_dist = 99999

        for pos_name, pos_y in candidates:
            px = max(4, min(x1, img_w - lbl_w - 4))
            if px < 4:
                px = 4

            # 检查是否和其他标签重叠
            overlapping = False
            for (ex1, ey1, ex2, ey2) in all_labels:
                h_overlap = not (px + lbl_w < ex1 or px > ex2)
                v_overlap = not (pos_y + lbl_h < ey1 or pos_y > ey2)
                if h_overlap and v_overlap:
                    overlapping = True
                    break

            dist = _label_dist(px, pos_y, x1, y1, x2, y2, lbl_w, lbl_h)

            if not overlapping:
                if not best or dist < best_dist:
                    best = (px, pos_y)
                    best_dist = dist
                    best_overlap = False
            else:
                if best_overlap or (not best and not best_overlap):
                    if dist < best_dist:
                        best = (px, pos_y)
                        best_dist = dist
                        best_overlap = True

        return best or (max(4, min(x1, img_w - lbl_w - 4)), HEADER_H)

    # 绿色安全框
    for bbox in safe_draws:
        x1, y1, x2, y2 = bbox
        draw.rectangle([x1, y1, x2, y2], outline="#22c55e", width=4)
        lbl_w, lbl_h = 90, 30
        lx, ly = get_label_pos(x1, y1, x2, y2, lbl_w, lbl_h)
        draw.rectangle([lx, ly, lx + lbl_w, ly + lbl_h], fill="#22c55e")
        draw.text((lx + 6, ly + 3), "安全", fill="white", font=font)
        all_labels.append((lx, ly, lx + lbl_w, ly + lbl_h))

    # 红色风险框（虚线）
    for bbox, risks in risk_draws:
        x1, y1, x2, y2 = bbox
        for i in range(0, int((x2 - x1) * 1.5), 20):
            seg_end = min(x1 + i + 8, x2)
            if x1 + i < x2:
                draw.line([(x1 + i, y1), (seg_end, y1)], fill="#ef4444", width=5)
                draw.line([(x1 + i, y2), (seg_end, y2)], fill="#ef4444", width=5)
        for i in range(0, int((y2 - y1) * 1.5), 20):
            seg_end = min(y1 + i + 8, y2)
            if y1 + i < y2:
                draw.line([(x1, y1 + i), (x1, seg_end)], fill="#ef4444", width=5)
                draw.line([(x2, y1 + i), (x2, seg_end)], fill="#ef4444", width=5)

        # 风险标签
        risk_lines = [
            f"[违规] {r.get('desc', '')}{r.get('sub_entity', '')} ({round(r.get('confidence', 0) * 100)}%)"
            for r in risks if r.get("is_risk") == "是"
        ]
        line_h, pad = 30, 8
        lbl_w = min(340, img_w - 8)
        lbl_h = len(risk_lines) * line_h + pad * 2
        lx, ly = get_label_pos(x1, y1, x2, y2, lbl_w, lbl_h)

        draw.rectangle([lx, ly, lx + lbl_w, ly + lbl_h], fill=(239, 68, 68, 235))
        for i, line in enumerate(risk_lines):
            draw.text((lx + pad, ly + pad + line_h * i + 2), line, fill="white", font=font_bold)

        # 记录此标签位置
        all_labels.append((lx, ly, lx + lbl_w, ly + lbl_h))

    # 顶部信息栏
    h = 48
    draw.rectangle([0, 0, img_w, h], fill=(15, 23, 42, 225))
    title = f"工地安全 AI 检测"
    title += f" | 共 {total_people} 人  ·  {risk_people} 人违规"
    draw.text((12, 12), title, fill="#f8fafc", font=font_bold)

    return True


# ---------- 主流程 ----------
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    images = sorted([f for f in Path(IMAGE_DIR).iterdir() if f.suffix.lower() in image_exts])

    if not images:
        print(f"❌ 在 {IMAGE_DIR} 中没找到图片文件")
        return

    print(f"📁 图片文件夹: {IMAGE_DIR}")
    print(f"📁 输出文件夹: {OUTPUT_DIR}")
    print(f"📸 共找到 {len(images)} 张图片\n")

    success = 0
    failed = 0
    total = len(images)

    for i, img_path in enumerate(images, 1):
        filename = img_path.name
        output_path = Path(OUTPUT_DIR) / f"{img_path.stem}_annotated.png"

        print(f"[{i}/{total}] 🔍 {filename} ... ", end="", flush=True)

        # 第一步：发给大模型识别
        try:
            result = analyze_one_image(str(img_path))
        except Exception as e:
            print(f"❌ analyze_one_image 异常: {e}")
            failed += 1
            continue

        if result.get("code") != 200:
            print(f"❌ 识别失败 (code={result.get('code')})")
            failed += 1
            continue

        # 第二步：加载原图
        try:
            img = Image.open(str(img_path)).convert("RGB")
        except Exception as e:
            print(f"❌ 图片加载失败: {e}")
            failed += 1
            continue

        # 从文件名提取识别类型（如 "未戴安全帽检测"）
        detection_type = ""
        parts = filename.replace(".jpg", "").replace(".jpeg", "").replace(".png", "").split("_")
        for p in parts:
            if "检测" in p or "识别" in p:
                detection_type = p
                break

        # 第三步：画标注
        try:
            ok = annotate_image(img, result, detection_type)
        except Exception as e:
            print(f"❌ 标注异常: {e}")
            failed += 1
            continue
        if not ok:
            print(f"❌ 标注失败 (JSON 格式异常)")
            failed += 1
            continue

        # 第四步：保存标注图
        img.save(str(output_path), "PNG")
        print(f"✅ → {output_path.name}")
        success += 1

    print(f"\n📊 汇总：共 {total} 张，成功 {success} 张，失败 {failed} 张")
    print(f"📁 标注图已保存到: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
