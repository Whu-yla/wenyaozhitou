#!/usr/bin/env python3
"""
文鳐智投 v7 — 100分制 · 数字门槛 · 70分硬底线
数智科技最大业务：智慧工地管控平台 + 智能安防
"""
import re
from typing import Optional

# ═══ 数字/智慧硬门槛 — 标题+正文至少命中1个才算数智相关 ═══
DIGITAL_GATE = [
    "智慧", "智能", "数字", "数智", "数字化", "智能化", "信息化",
    "BIM", "三维", "孪生", "AI", "人工智能", "大数据",
    "物联网", "IoT", "云平台", "SaaS", "软件", "APP",
    "管控平台", "管理平台", "监测系统", "监控系统", "巡检",
    "中台", "驾驶舱", "电子围栏", "智能安全帽", "人员定位",
    "国产化", "信创", "识别", "算法", "模型",
    # v8: 放宽硬门槛，允许"系统/平台/软件"类IT项目进入
    "系统开发", "信息系统", "监管系统", "管理系统",
    "平台建设", "软件系统", "数据管理", "数据平台",
    "业务系统", "综合管理", "应用系统",
    # v9: AI & 产品线
    "人工智能", "大模型", "机器学习", "深度学习",
    "玄武", "执法记录仪", "有限空间", "NLP", "LLM",
    "计算机视觉", "自然语言处理", "图像识别", "语音识别",
    # v10: 信息安全 & 等保
    "信息安全", "网络安全", "等保测评", "安全防护", "安全评估",
    "态势感知", "工控安全", "数据安全",
    # v11: IT信息化服务 — 87站batch_crawler通过率从1.5%提升
    "信息技术", "信息化服务", "信息化建设", "软件开发",
    "技术开发", "技术支撑", "技术支持", "技术服务",
    "数据服务", "数据分析", "数据治理", "数据仓库",
    "数据中心", "数据库", "网络设备", "网络系统",
    "服务器", "虚拟化", "容器", "微服务", "中间件",
    "应用开发", "接口开发", "实施服务", "集成服务",
    "容灾", "灾备", "备份恢复", "运维管理",
    "通信系统", "调度系统", "集控系统", "SCADA",
    "协同办公", "OA系统", "门户网站", "统一认证",
]

# 一级核心产品 — 数智科技主推，一个 +35分
CORE_KEYWORDS = [
    # 数智核心
    "数智", "数智科技", "数智化",
    # 智慧工地
    "智慧工地管控平台", "智慧工地平台", "智慧工地系统",
    "智慧工地管理", "智慧工地建设", "智慧建造",
    "工地管控", "工地数字化", "工地智慧化",
    # 智能安防
    "智能安防", "安防系统", "安防管理平台", "安防管控",
    "AI安防", "智慧安防", "安全管控系统", "安全管控平台",
    # 数智科技产品线
    "玄武SSK", "玄武", "SSK", "有限空间", "执法记录仪",
    # 人工智能
    "人工智能", "大模型", "深度学习", "机器学习",
    "计算机视觉", "自然语言处理", "NLP", "LLM",
    "图像识别", "语音识别", "智能识别",
    "AI平台", "AI中台", "AI大模型", "AI应用",
    # 三维/数字孪生
    "三维可视化", "3D可视化", "数字展厅",
    "BIM协同", "BIM管理平台", "BIM管控",
    "数字底座", "数字孪生", "智孪万维", "智电万通",
    # 管控平台
    "智慧决策", "智慧管理平台", "智能管理平台",
    "指挥中心", "驾驶舱", "管控中心",
    "视频智能分析", "AI监控", "AI视频",
    # 电力数字化
    "智慧电厂", "智慧电站", "电厂智能化",
    "输变电智能化", "输电线路在线监测",
    # 物联网
    "物联网感知", "IoT平台", "物联网平台",
    # 信息化平台
    "信息化管理平台", "数字化管理平台", "一体化管控平台",
    "信创改造", "国产化替代",
    "智慧工地", "数字工地", "智慧安防系统", "智能监控系统",
]

# 二级强相关组件/服务 — 数智科技有能力做，一个 +18分
STRONG_KEYWORDS = [
    "管控平台", "管理平台", "监测系统", "监控系统",
    "管理系统", "监管系统", "业务系统", "应用系统",
    "系统开发", "平台建设", "软件开发", "系统集成",
    "信息化系统", "信息化平台", "数字化系统", "数字化平台",
    "智能化系统", "智能化平台", "智慧系统", "智慧平台",
    "智能识别", "AI识别", "人工智能", "图像识别",
    "缺陷自动识别", "违章识别", "行为识别",
    "智能巡检", "自动巡检", "无人机巡检",
    "综合管理", "集中管控", "一体化",
    "数据中台", "业务中台", "大数据",
    "云计算", "私有云",
    "数字化交付", "BIM交付", "三维交付",
    "数字化施工", "智慧施工",
    # v10: 信息安全 & 数字化服务
    "信息安全", "网络安全", "数字化", "智能化",
    "信号采集", "技术服务", "安全防护",
    # v11: IT信息化/运维/开发
    "信息技术", "信息化建设", "信息化服务",
    "信息化", "云平台", "云端",
    "信息技改", "数字研究", "经研院",
    "软件开发", "技术开发", "技术支撑", "技术支持",
    "数据服务", "数据分析", "数据治理",
    "数据中心", "网络设备", "网络系统",
    "服务器", "虚拟化", "数据库",
    "信息系统", "运维管理", "系统运维",
    "通信系统", "集控系统", "SCADA",
    "协同办公", "OA系统", "统一认证",
    "实施服务", "集成服务", "接口开发",
    "容灾", "灾备", "备份恢复",
]

# 三级：数智科技的客户/合作伙伴（谁在招标），一个 +12分
CUSTOMER_KEYWORDS = [
    "华电", "华能", "大唐", "国电投", "国家能源",
    "国家电力投资", "国电",
    "中广核", "中核", "三峡", "三峡新能源",
    "电建", "中电建", "能建", "中能建", "中国电建", "中国能建",
    "国网", "国家电网", "南方电网", "南网",
    "内蒙古电力", "蒙西", "蒙东",
    "广东能源", "浙江能源", "江苏能源", "湖北能源",
    "能源集团", "电力集团", "能源投资",
    "中石油", "中石化", "中海油", "中煤",
]

# 泛行业词 — 前两级有命中的情况下加分，一个 +5分（仅能源/工业领域）
GENERAL_KEYWORDS = [
    "风电", "光伏", "储能", "新能源",
    "电站", "电厂", "电网", "电力",
    "矿山", "园区", "楼宇",
]

# ── 排除词 ──
EXCLUDE_KEYWORDS = [
    "医疗", "医院", "卫生", "疾控", "药品", "药房", "中医",
    "教育", "学校", "小学", "中学", "大学", "学院", "教师", "学生",
    "教学", "教室", "课桌", "黑板", "教材", "培训",
    "食品", "餐饮", "食堂", "农贸", "养殖", "屠宰",
    "物业", "保洁", "保安", "绿化养护", "垃圾清运",
    "办公用品", "打印纸", "文具", "家具采购",
    "汽车维修", "车辆保养", "道路养护",
    "服装", "校服", "被服",
    "广告", "印刷", "宣传品", "展会",
    "法律顾问", "法律服务", "律师", "审计报告", "会计服务",
    "殡葬", "宗教",
    "储备林", "林业", "造林", "苗木", "绿化苗木", "农林",
]

# ── 施工/劳务排除 ──
CONSTRUCTION_EXCLUDE = [
    "专业分包", "劳务分包", "土建分包", "施工分包",
    "土建施工", "土建工程", "建筑工程施工",
    "混凝土", "脚手架", "钢筋", "砌筑", "抹灰",
    "装修工程", "装饰装修", "二次装修",
    "地基", "桩基", "基坑", "边坡",
    "架子工", "木工", "瓦工", "焊工", "钢筋工",
    "清包", "大清包", "劳务大清包",
    "车辆维修", "车辆租赁", "车辆定点",
    "体检", "员工体检", "健康体检",
]

CONSTRUCTION_VERBS = [
    "施工总承包", "PC总承包", "EPC总承包",
    "安装工程", "安装施工", "机电安装",
    "线路工程", "变电工程", "输变电工程",
]

PROVINCE_WEIGHTS = {
    "湖北": 1.0, "湖南": 0.9, "河南": 0.85,
    "江西": 0.8, "安徽": 0.8, "四川": 0.8, "重庆": 0.85,
    "贵州": 0.75, "云南": 0.7, "广东": 0.7, "广西": 0.7, "海南": 0.65,
    "浙江": 0.7, "江苏": 0.7, "上海": 0.65, "福建": 0.65,
    "山东": 0.7, "河北": 0.65, "山西": 0.7, "陕西": 0.75,
    "北京": 0.65, "天津": 0.65,
    "甘肃": 0.7, "宁夏": 0.65, "新疆": 0.6, "青海": 0.6,
    "内蒙古": 0.6, "西藏": 0.5,
    "辽宁": 0.6, "吉林": 0.6, "黑龙江": 0.55,
}
DEFAULT_WEIGHT = 0.5

PROVINCE_PATTERN = re.compile(
    r'(湖北|湖南|河南|江西|安徽|重庆|四川|贵州|陕西|甘肃|宁夏|新疆|青海|'
    r'广东|广西|云南|海南|江苏|浙江|上海|福建|山东|河北|山西|'
    r'北京|天津|内蒙古|西藏|辽宁|吉林|黑龙江)'
)

CUSTOMER_CATEGORIES = [
    ("🔴 五大发电", ["华能", "华电", "大唐", "国电投", "国家电力投资", "国家能源",
                    "华能集团", "华电集团", "大唐集团", "国电投集团", "国家能源集团"]),
    ("🟠 国网/南网", ["国网", "国家电网", "南方电网", "南网", "国网公司",
                     "南网公司", "国网新源", "南网能源"]),
    ("🟡 地方能源集团", ["能源集团", "电力集团", "能源投资", "能源开发",
                       "湖北能源", "广东能源", "浙江能源", "江苏能源",
                       "山东能源", "河南能源", "四川能源", "贵州能源",
                       "云南能源", "皖能", "晋能", "陕能", "甘能",
                       "深圳能源", "广州发展", "浙能", "粤电"]),
    ("🟢 政府/公共事业", ["政府采购", "公共资源", "住建局", "交通局", "水利局",
                        "环保局", "城管", "应急", "消防", "公安",
                        "商务厅", "教育厅", "卫健委", "市政", "开发区管委会",
                        "政府", "公共资源交易中心", "财政局"]),
    ("🔵 电力/央企/工业", ["中广核", "中核", "三峡", "三峡新能源",
                         "电建", "中电建", "能建", "中能建", "中国电建", "中国能建",
                         "中石油", "中石化", "中海油", "中煤",
                         "电网", "电厂", "变电站", "电力公司", "供电公司",
                         "送变电", "输变电", "配电"]),
    ("⚪ 其他", []),
]


def classify_customer(title: str) -> str:
    if not title:
        return "⚪ 其他"
    for cat_name, keywords in CUSTOMER_CATEGORIES:
        for kw in keywords:
            if kw in title:
                return cat_name
    return "⚪ 其他"


def extract_province(title: str) -> tuple:
    m = PROVINCE_PATTERN.search(title)
    if not m:
        return ("", "")
    return (m.group(1), m.group(1))


# ── 招标人/中标人/金额提取正则 ──
BIDDER_PATTERNS = [
    re.compile(r'采购人[：:]\s*(.{2,40}?)(?:[，。,.)）]|$)'),
    re.compile(r'招标人[：:]\s*(.{2,40}?)(?:[，。,.)）]|$)'),
    re.compile(r'采购单位[：:]\s*(.{2,40}?)(?:[，。,.)）]|$)'),
    re.compile(r'招标单位[：:]\s*(.{2,40}?)(?:[，。,.)）]|$)'),
    re.compile(r'业主[：:]\s*(.{2,40}?)(?:[，。,.)）]|$)'),
]
WINNER_PATTERNS = [
    re.compile(r'中标人[：:]\s*(.{2,40}?)(?:[，。,.)）]|$)'),
    re.compile(r'成交供应商[：:]\s*(.{2,40}?)(?:[，。,.)）]|$)'),
    re.compile(r'中标单位[：:]\s*(.{2,40}?)(?:[，。,.)）]|$)'),
    re.compile(r'供应商[：:]\s*(.{2,40}?)(?:[，。,.)）]|$)'),
]
AMOUNT_PATTERNS = [
    re.compile(r'中标金额[：:]\s*(.{2,30}?)(?:[，。,.)）]|$)'),
    re.compile(r'成交金额[：:]\s*(.{2,30}?)(?:[，。,.)）]|$)'),
    re.compile(r'合同金额[：:]\s*(.{2,30}?)(?:[，。,.)）]|$)'),
]


def extract_detail_fields(text: str) -> dict:
    """从公告正文提取招标人/中标人/金额"""
    if not text: return {}
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    result = {}
    for pat in BIDDER_PATTERNS:
        m = pat.search(text)
        if m and len(m.group(1).strip()) > 2 and not m.group(1).startswith('：'):
            result['procurement_owner'] = m.group(1).strip()[:40]
            break
    for pat in WINNER_PATTERNS:
        m = pat.search(text)
        if m and len(m.group(1).strip()) > 2 and not m.group(1).startswith('：'):
            result['winner_company'] = m.group(1).strip()[:40]
            break
    for pat in AMOUNT_PATTERNS:
        m = pat.search(text)
        if m:
            result['winning_amount'] = m.group(1).strip()
            break
    return result


def normalize_amount(raw: str) -> Optional[float]:
    if not raw: return None
    raw = raw.replace(',', '').replace('，', '').replace(' ', '')
    try:
        if '亿' in raw: return float(raw.replace('亿','').replace('元','')) * 1e8
        if '万' in raw: return float(raw.replace('万','').replace('元','')) * 1e4
        return float(raw.replace('元', ''))
    except: return None


def score_item(item: dict) -> Optional[dict]:
    title = item.get("title", "") or ""
    content = item.get("content", "") or ""
    raw_text = item.get("raw_text", "") or ""
    text_for_check = title + " " + content + " " + raw_text[:500]

    # ═══ L1 页面类型判别 — 拒绝平台首页/导航/欢迎页 ═══
    L1_REJECT_SIGNALS = [
        # 强信号：3条命中即拒绝
        '欢迎来到', '欢迎您', '欢迎光临', 'V1.0欢迎您', 'V1.0 欢迎',
        '设为首页', '收藏此页', '平台首页', '网站首页',
        '电子采购平台首页', '平台操作流程', 'CA办理',
        '易招标-首页', '易招标', '产品与服务',
        '中国招标投标协会', '年会报道', '年会召开',
        '三十而立', '岁月答卷', '三峡小微',
        '您当前访问的是', '访问正式平台',
    ]
    l1_hits = [s for s in L1_REJECT_SIGNALS if s in text_for_check]
    # 3个以上L1信号 + 标题不含「招标/中标/采购/公告/公示/投标」→ 平台导航页
    notice_kw = ['招标', '中标', '采购', '公告', '公示', '投标', '项目']
    has_notice_kw = any(kw in title for kw in notice_kw)
    if len(l1_hits) >= 3 and not has_notice_kw:
        return None
    # 浙能/深圳能源 特殊模式：「V1.0 欢迎来到」+ 无公告词 → 直接拒绝
    # 增强：含门户导航文本（异议投诉/帮助中心/办理CA）→ 直接拒绝
    portal_nav = ['异议投诉', '帮助中心', '办理CA', '搜索 首 页', '设为首页']
    portal_nav_hits = [s for s in portal_nav if s in text_for_check]
    if ('V1.0' in title or '欢迎来到' in title) and (not has_notice_kw or len(portal_nav_hits) >= 2):
        return None

    # 0. 数字/智慧硬门槛
    if not any(kw in text_for_check for kw in DIGITAL_GATE):
        return None

    # 0.5. 非数字化业务排除 — 锅炉/煤矿/电厂本体改造/洗衣等一律拒掉
    NON_DIGITAL_EXCLUDE = [
        '锅炉', '省煤器', '空预器', '脱硫', '烟囱', '吸收塔', '除尘',
        '煤矿', '胶带机', '梭车', '粉煤灰', '罐车运输', '矸石',
        '再热器', '热网首站', '供热管网', '保温管道', '热电联产',
        '工装洗涤', '洗衣', '文体馆维修', '物业保洁', '食堂',
        'EPC总承包', '施工总承包', '土建', '桩基', '基坑',
    ]
    if any(kw in text_for_check for kw in NON_DIGITAL_EXCLUDE):
        # 如果同时包含数字化强关键词，允许通过（如"智慧工地 EPC总承包"）
        strong_save = ['数字化', '数智', '智慧工地', 'BIM', '数字孪生', '人工智能', 'AI平台', '软件平台']
        if not any(kw in text_for_check for kw in strong_save):
            return None

    # 1. 硬排除
    for kw in EXCLUDE_KEYWORDS:
        if kw in text_for_check:
            return None
    for kw in CONSTRUCTION_EXCLUDE:
        if kw in text_for_check:
            return None

    # 2. 施工动名词 + 监理排除
    has_digital = any(kw in text_for_check for kw in DIGITAL_GATE)
    is_construction = any(kw in title for kw in CONSTRUCTION_VERBS)
    if is_construction and not has_digital:
        return None
    if ("分包" in title or "监理" in title) and not has_digital:
        return None

    # ═══ 中标独立评分 — 只关心竞品 ═══
    is_winning = item.get('notice_type') == 'winning'
    is_competitor = False
    has_strong_digital = False
    if is_winning:
        winner = item.get('winner_company', '') or ''
        # 竞品短名（与 competitor_tracker.py 同步）
        COMPETITOR_NAMES = [
            '南网数字', '南方电网数字', '华工精卓', '南瑞', '国电南自',
            '远光软件', '朗坤智慧', '科远智慧', '金现代', '恒华科技',
            '国能信控', '四方继保', '积成电子', '东方电子', '东软',
            '中电普华', '中科曙光', '浪潮', '广联达', '德鑫莱',
        ]
        is_competitor = any(c in winner for c in COMPETITOR_NAMES)
        # 非竞品中标：必须有明确数字化关键词才保留
        STRONG_DIGITAL = ['数字化', '数智', '软件平台', 'APP', '管理平台',
                          '监控系统', '信息系统', '数据平台', '人工智能', 'BIM',
                          '大模型', 'LLM', '设备诊断', '鸿蒙', '智能楼宇', 'AI平台']
        has_strong_digital = any(kw in text_for_check for kw in STRONG_DIGITAL)
        if not is_competitor and not has_strong_digital:
            return None  # 非竞品且无数字化关键词→丢弃

    # 3. 评分 (100分制)
    raw_score = 0
    tags = []

    # 通过数字门槛即给基础分（代表IT/数字化项目的固有价值）
    base = 25
    # 非竞品中标降基础分，但有强数字化关键词的保留高分
    if is_winning and not is_competitor:
        base = 25 if has_strong_digital else 15
    raw_score += base
    tags.append("★digital_gate")

    # v2 精细化评分 — 小步长+上限+多样性奖励
    core_count = 0
    for kw in CORE_KEYWORDS:
        if kw in text_for_check and core_count < 3:
            raw_score += 12
            core_count += 1
            tags.append(f"★{kw}")

    strong_count = 0
    for kw in STRONG_KEYWORDS:
        if kw in text_for_check and strong_count < 5:
            raw_score += 6
            strong_count += 1
            tags.append(f"☆{kw}")

    for kw in CUSTOMER_KEYWORDS:
        if kw in text_for_check:
            raw_score += 5
            tags.append(f"@{kw}")

    weak_count = 0
    if raw_score > 0:
        for kw in GENERAL_KEYWORDS:
            if kw in text_for_check and weak_count < 8:
                raw_score += 3
                weak_count += 1
                tags.append(kw)

    # 多样性奖励：不同类型的匹配越多，分越高
    variety = (1 if core_count > 0 else 0) + (1 if strong_count > 0 else 0) + (1 if weak_count > 0 else 0)
    raw_score += variety * 4

    # 新鲜度奖励：近7天发布的项目加权
    from datetime import datetime, timedelta
    pub_date = item.get('publish_date', '')
    if pub_date and len(pub_date) >= 10:
        try:
            pd = datetime.strptime(pub_date[:10], '%Y-%m-%d')
            age = (datetime.now() - pd).days
            if age <= 1: raw_score += 5
            elif age <= 3: raw_score += 3
            elif age <= 7: raw_score += 1
        except: pass

    if raw_score == 0:
        return None

    province, _ = extract_province(title)
    # 全国统一权重，不再按省份打折
    geo = 1.0
    
    # ═══ v11: 日期新鲜度衰减 ═══
    # 旧公告随时间降权，避免两年前旧标排第一
    from datetime import datetime, timedelta
    pub_date = item.get('publish_date', '')
    if pub_date:
        try:
            pd = datetime.strptime(pub_date[:10], '%Y-%m-%d')
            age_days = (datetime.now() - pd).days
            if age_days > 730:       decay = 0.3   # >2年
            elif age_days > 365:      decay = 0.5   # 1-2年
            elif age_days > 180:      decay = 0.8   # 6-12月
            else:                     decay = 1.0
            geo *= decay
        except: pass
    
    final = min(round(raw_score * geo), 100)
    if final < 50:
        return None

    result = dict(item)
    # ── 标题清洗：去掉南网「采购公告 > xxx > 」前缀 ──
    clean_title = re.sub(r'^(?:采购公告|招标公告|中标公告|成交公告|公示公告|非招标公告|零星采购公告)\s*>\s*', '', title)
    while clean_title != title:
        title = clean_title
        clean_title = re.sub(r'^(?:采购公告|招标公告|中标公告|成交公告|公示公告|非招标公告|零星采购公告)\s*>\s*', '', title)
    result['title'] = title[:200]
    result["relevance_score"] = final
    result["province"] = province
    result["region"] = province
    result["matched_tags"] = tags[:12]
    result["category"] = classify_customer(title)
    
    # ═══ v11: 从内容提取地区+招标人 ═══
    content_text = item.get('content', '') or item.get('raw_text', '') or ''
    if content_text:
        extra_fields, region_field = _extract_region_owner(content_text)
        if extra_fields.get('procurement_owner'):
            result['procurement_owner'] = extra_fields['procurement_owner']
        if region_field.get('region'):
            result['region'] = region_field['region']
    
    return result


def score_items(items: list[dict]) -> list[dict]:
    return [r for item in items if (r := score_item(item)) is not None]


# ═══════════════════════════════════════════
# 详情提取 — 从公告正文提取招标人/中标人/金额
# ═══════════════════════════════════════════

BIDDER_PATTERNS = [
    re.compile(r'采购人[：:]\s*([^。；;，,\n]{1,60})'),
    re.compile(r'招标人[：:为是]\s*([^。；;，,\n]{1,60})'),
    re.compile(r'采购单位[：:]\s*([^。；;，,\n]{1,60})'),
    re.compile(r'业主[：:]\s*([^。；;，,\n]{1,60})'),
    re.compile(r'(?:采购人|招标人|采购单位|招标单位)[：:]\s*([^。；;，,\n]{1,60})'),
]

REGION_PATTERNS = [
    re.compile(r'(?:招标项目|项目)所在地区[：:]\s*([^。；;，,\n]{1,20})'),
    re.compile(r'(?:项目|建设)地点[：:]\s*([^。；;，,\n]{1,20})'),
    re.compile(r'交货地点[：:]\s*([^。；;，,\n]{1,20})'),
]

# Add region extraction + owner extraction to score_item
def _extract_region_owner(text):
    """从正文提取地区和招标人"""
    if not text: return {}, {}
    clean = re.sub(r'<[^>]+>', '', text)
    # 不要压换行！保留 \n 让 regex 的 [^\n] 能正确截断
    owner = None
    for pat in BIDDER_PATTERNS:
        m = pat.search(clean)
        if m and len(m.group(1).strip()) > 2:
            candidate = m.group(1).strip()
            if not candidate.startswith('：') and not candidate.startswith(':'):
                owner = candidate[:60]
                break
    region = None
    for pat in REGION_PATTERNS:
        m = pat.search(clean)
        if m and len(m.group(1).strip()) >= 2:
            candidate = m.group(1).strip()
            if not candidate.startswith('：') and not candidate.startswith(':'):
                region = candidate[:20]
                break
    return {'procurement_owner': owner}, {'region': region}

WINNER_PATTERNS = [
    re.compile(r'中标人[：:]\s*([^；;，,\n]+)'),
    re.compile(r'成交供应商[：:]\s*([^；;，,\n]+)'),
    re.compile(r'中标单位[：:]\s*([^；;，,\n]+)'),
    re.compile(r'供应商名称[：:]\s*([^；;，,\n]+)'),
]

AMOUNT_PATTERNS = [
    re.compile(r'(?:中标|成交|合同)金额[：:]\s*([0-9,.，]+万?亿?元?)'),
    re.compile(r'(?:预算|控制价)[：:]\s*([0-9,.，]+万?亿?元?)'),
]


def extract_detail_fields(text: str) -> dict:
    if not text:
        return {}
    text = re.sub(r'<[^>]+>', '', text)
    # 不要压换行！保留 \n 让 regex 的 [^\n] 能正确截断
    result = {}
    for pat in BIDDER_PATTERNS:
        m = pat.search(text)
        if m and len(m.group(1).strip()) > 2 and not m.group(1).startswith('：'):
            result['procurement_owner'] = m.group(1).strip()[:60]
            break
    for pat in WINNER_PATTERNS:
        m = pat.search(text)
        if m and len(m.group(1).strip()) > 2 and not m.group(1).startswith('：'):
            result['winner_company'] = m.group(1).strip()[:60]
            break
    for pat in AMOUNT_PATTERNS:
        m = pat.search(text)
        if m:
            result['winning_amount'] = m.group(1).strip()
            break
    return result


def normalize_amount(raw: str) -> Optional[float]:
    if not raw: return None
    raw = raw.replace(',', '').replace('，', '').replace(' ', '')
    try:
        if '亿' in raw: return float(raw.replace('亿','').replace('元','')) * 1e8
        if '万' in raw: return float(raw.replace('万','').replace('元','')) * 1e4
        return float(raw.replace('元', ''))
    except:
        return None


if __name__ == "__main__":
    tests = [
        "国电投湖北电力智慧工地管控平台采购招标公告",
        "华能集团智慧工地数字化管控平台建设项目",
        "某光伏电站100MW EPC总承包施工招标",
        "华电四川水电智能安防系统升级改造",
        "国家能源集团三维可视化数字展厅招标",
        "某小学教学楼建设项目",
        "大唐风电智慧工地物联网感知系统采购",
        "XX电厂施工总承包安装工程招标",
        "湖北能源集团数字化安全管控平台",
        "贵港市国家储备林基地建设项目工程监理服务",
    ]
    for t in tests:
        r = score_item({"title": t, "content": ""})
        print(f"[{'✅' if r else '❌'}] {r['relevance_score'] if r else '--'} | {t}")
