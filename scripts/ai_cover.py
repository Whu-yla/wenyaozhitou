#!/usr/bin/env python3
"""文鳐智投 AI封面生成器 — 通义万相"""
import os, json, time, requests
from PIL import Image
from pathlib import Path

API_KEY_PATH = "/tmp/qwen_key.txt"
API_KEY = open(API_KEY_PATH).read().strip() if os.path.exists(API_KEY_PATH) else ""
IMG_DIR = Path("/var/www/html/bidding/img_gen")
IMG_DIR.mkdir(parents=True, exist_ok=True)
os.chmod(IMG_DIR, 0o755)  # nginx 要有 x 权限才能读子目录
CACHE_DIR = IMG_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
os.chmod(CACHE_DIR, 0o755)

IMG_API = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "X-DashScope-Async": "enable",
}

# 行业场景 → 视觉风格映射
STYLE_MAP = {
    "智慧工地": "现代智慧工地，塔吊和建筑，无人机监控，数字孪生界面，科技蓝绿配色",
    "智能安防": "智能安防监控中心，多屏幕显示，AI识别画面，深蓝科技风",
    "数字化": "数字化转型概念，数据流和网络连接，云计算图标，蓝紫渐变",
    "管控平台": "大型数据指挥中心，可视化大屏，数据面板，深色科技背景",
    "BIM": "三维BIM建筑模型，线框渲染，蓝色半透明，工程数字化",
    "电网": "智能电网，输电线路和变电站，数字化叠加，蓝橙配色",
    "新能源": "风电场和光伏电站，清洁能源，蓝天白云，绿色科技",
    "系统运维": "服务器机房，运维监控大屏，数据流动，蓝灰专业配色",
    "平台": "软件平台界面，数据可视化，仪表盘，现代扁平设计",
    "政务": "政府数字化服务大厅，电子政务，蓝白配色，庄重大气",
}


def make_prompt(title: str, category: str = "") -> str:
    """根据标题生成图像Prompt"""
    parts = []
    
    # 匹配行业场景
    for keyword, style in STYLE_MAP.items():
        if keyword in title:
            parts.append(style)
            if len(parts) >= 2:
                break
    
    if not parts:
        # 兜底
        parts.append("专业商务科技场景，数字化概念，数据可视化，简洁大气")
    
    parts.append("无文字无水印无logo")
    parts.append("3D渲染风格，电影级光影，4K画质")
    
    return "，".join(parts)


def generate_image(item_id: int, title: str, category: str = "") -> str:
    """为招标项生成AI封面图，返回本地URL路径。已有缓存则直接返回。"""
    
    cache_file = CACHE_DIR / f"{item_id}.png"
    if cache_file.exists():
        return f"https://www.yfzx.online/bidding/img_gen/cache/{item_id}.png"
    
    prompt = make_prompt(title, category)
    print(f"  🎨 [{item_id}] Prompt: {prompt[:80]}...")
    
    # 提交任务
    payload = {
        "model": "wanx2.0-t2i-turbo",
        "input": {"prompt": prompt},
        "parameters": {"size": "1024*1024", "n": 1}
    }
    
    try:
        resp = requests.post(IMG_API, json=payload, headers=HEADERS, timeout=30)
        result = resp.json()
    except Exception as e:
        print(f"  ❌ API调用失败: {e}")
        return ""
    
    task_id = result.get("output", {}).get("task_id", "")
    if not task_id:
        err = result.get("message") or result.get("code") or "unknown"
        print(f"  ❌ 任务创建失败: {err}")
        return ""
    
    # 轮询等待
    TASK_URL = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
    for i in range(30):  # 最多90秒
        time.sleep(3)
        try:
            r2 = requests.get(TASK_URL, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=10).json()
        except:
            continue
        status = r2.get("output", {}).get("task_status", "?")
        if status == "SUCCEEDED":
            results = r2["output"].get("results", [])
            if results:
                img_url = results[0].get("url", "")
                # 下载
                try:
                    img_resp = requests.get(img_url, timeout=30)
                    tmp_path = IMG_DIR / f"tmp_{item_id}.png"
                    tmp_path.write_bytes(img_resp.content)
                    
                    # 裁切成2:1
                    img = Image.open(tmp_path)
                    src_w, src_h = img.size
                    target_w, target_h = 800, 400
                    ratio = target_w / target_h
                    
                    if src_w / src_h > ratio:
                        new_w = int(src_h * ratio)
                        left = (src_w - new_w) // 2
                        img = img.crop((left, 0, left + new_w, src_h))
                    else:
                        new_h = int(src_w / ratio)
                        top = (src_h - new_h) // 2
                        img = img.crop((0, top, src_w, top + new_h))
                    
                    img = img.resize((target_w, target_h), Image.LANCZOS)
                    img.save(cache_file, "JPEG", quality=85, optimize=True)
                    tmp_path.unlink()
                    
                    file_url = f"https://www.yfzx.online/bidding/img_gen/cache/{item_id}.png"
                    print(f"  ✅ 生成完成 ({os.path.getsize(cache_file)} bytes)")
                    return file_url
                    
                except Exception as e:
                    print(f"  ❌ 下载/裁切失败: {e}")
                    return ""
            break
        elif status in ("FAILED", "CANCELED"):
            print(f"  ❌ 任务失败: {r2.get('output',{}).get('message','')}")
            return ""
    
    return ""


def prefetch_images(items: list) -> dict:
    """批量预生成图片，返回 {item_id: url} 映射"""
    urls = {}
    for item in items:
        item_id = item["id"]
        title = (item["title"] or "")[:100]
        category = item.get("category", "")
        url = generate_image(item_id, title, category)
        if url:
            urls[item_id] = url
    return urls


if __name__ == "__main__":
    # 测试
    url = generate_image(9999, "某智慧工地管控平台数字化建设招标项目", "🔵 电力/央企/工业")
    print(f"Result: {url}")
