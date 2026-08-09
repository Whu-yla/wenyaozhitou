#!/usr/bin/env python3
"""
文鳐智投 v1 技术匹配引擎
=============================
双向打通：招标需求 ↔ 开源技术

维度1：需求 → 技术（需求匹配推荐技术栈）
维度2：技术 → 需求（GitHub热门匹配能源场景）
"""
import re
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE_DIR = Path("/root/.hermes/profiles/wenyaozhitou")
DB = BASE_DIR / "data" / "bidding.db"
OUTPUT_DIR = Path("/var/www/html/bidding")

# ═══════════════════════════════════════════════════════════════════
# 【核心知识库】能源行业 ↔ 开源技术栈映射
# ═══════════════════════════════════════════════════════════════════

# 需求场景关键词 → 推荐技术栈（按匹配度从高到低）
SCENARIO_TECH_MAP = {
    # ── 智慧工地 / 施工安全 ──
    "智慧工地": {
        "scenario": "智慧工地/施工安全管理",
        "primary": [
            {"name": "Vue.js / React", "category": "前端框架", "github_stars": 206000, "why": "可视化大屏、管控平台标配"},
            {"name": "Spring Boot", "category": "后端框架", "github_stars": 73000, "why": "中台微服务，企业级首选"},
            {"name": "RT-DETR / YOLOv8", "category": "计算机视觉", "github_stars": 52000, "why": "安全帽/反光衣/违章识别"},
            {"name": "Mediapipe", "category": "手势/姿态识别", "github_stars": 25000, "why": "人员行为识别，未戴安全帽等"},
            {"name": "Leaflet / MapLibre", "category": "GIS地图", "github_stars": 42000, "why": "人员位置/设备位置地图展示"},
        ],
        "secondary": [
            {"name": "RabbitMQ / Kafka", "category": "消息队列", "github_stars": 27000, "why": "设备报警消息高吞吐分发"},
            {"name": "Apache IoTDB", "category": "时序数据库", "github_stars": 5200, "why": "传感器时序数据存储"},
            {"name": "InfluxDB", "category": "时序数据库", "github_stars": 27000, "why": "设备运行指标存储"},
        ]
    },
    "智能安防": {
        "scenario": "智能安防/视频监控",
        "primary": [
            {"name": "YOLOv10 / YOLOv8", "category": "目标检测", "github_stars": 52000, "why": "入侵检测、人员统计、安全帽识别"},
            {"name": "EasyCV / MMDetection", "category": "视觉工具箱", "github_stars": 12000, "why": "开箱即用的安防检测模型"},
            {"name": "Milvus", "category": "向量数据库", "github_stars": 29000, "why": "人脸检索/以图搜图"},
            {"name": "FFmpeg", "category": "视频处理", "github_stars": 43000, "why": "多路摄像头拉流转码"},
            {"name": "ZLMediakit / SRS", "category": "流媒体服务器", "github_stars": 10000, "why": "GB28181协议接入监控摄像头"},
        ],
        "secondary": [
            {"name": "GoCV", "category": "Go视觉库", "github_stars": 6500, "why": "高性能实时视频分析"},
            {"name": "Netty", "category": "网络框架", "github_stars": 33000, "why": "高并发摄像头连接管理"},
        ]
    },
    # ── 电力物联网/设备监控 ──
    "物联网": {
        "scenario": "电力物联网/设备在线监测",
        "primary": [
            {"name": "EMQX", "category": "MQTT Broker", "github_stars": 14000, "why": "百万级设备并发MQTT接入"},
            {"name": "NanoMQ", "category": "边缘MQTT", "github_stars": 1800, "why": "变电站边缘端MQTT网关"},
            {"name": "Apache IoTDB", "category": "工业时序库", "github_stars": 5200, "why": "电力IoT海量时序数据存储"},
            {"name": "ThingsBoard", "category": "IoT平台", "github_stars": 16000, "why": "设备管理+可视化+告警一体化"},
            {"name": "Grafana", "category": "可视化面板", "github_stars": 63000, "why": "设备指标实时监控大屏"},
        ],
        "secondary": [
            {"name": "Modbus库(各种语言)", "category": "工业协议", "github_stars": 2000, "why": "PLC/测控装置Modbus接入"},
            {"name": "Prometheus", "category": "监控系统", "github_stars": 52000, "why": "设备状态指标采集+告警"},
            {"name": "node-red", "category": "IoT流程编排", "github_stars": 19000, "why": "边缘端数据处理流程编排"},
        ]
    },
    "巡检": {
        "scenario": "智能巡检/无人机巡检",
        "primary": [
            {"name": "Sahi + YOLO", "category": "小目标检测", "github_stars": 12000, "why": "航拍图像缺陷/异物识别"},
            {"name": "OpenMMLab 系列", "category": "视觉算法套件", "github_stars": 45000, "why": "巡检识别算法快速搭建"},
            {"name": "SAM/YOLO-SAM", "category": "分割模型", "github_stars": 45000, "why": "绝缘子/线路缺陷分割"},
            {"name": "MMRotate", "category": "旋转目标检测", "github_stars": 2500, "why": "航拍多角度设备识别"},
            {"name": "COLMAP / OpenMVS", "category": "三维重建", "github_stars": 6500, "why": "无人机电力线三维建模"},
        ],
        "secondary": [
            {"name": "PaddleOCR", "category": "文字识别", "github_stars": 40000, "why": "巡检表计读数识别"},
            {"name": "WebODM", "category": "无人机地图", "github_stars": 3200, "why": "无人机正射影像/DSM生成"},
        ]
    },
    # ── 大数据/数据中台 ──
    "大数据": {
        "scenario": "电力数据中台/数据分析",
        "primary": [
            {"name": "Apache Doris", "category": "OLAP数据库", "github_stars": 12000, "why": "实时数仓，国产替代首选"},
            {"name": "Apache Flink", "category": "实时计算", "github_stars": 23000, "why": "实时流计算，异常检测场景"},
            {"name": "DuckDB", "category": "分析型数据库", "github_stars": 20000, "why": "嵌入式OLAP，小规模快速分析"},
            {"name": "Apache Spark", "category": "大数据引擎", "github_stars": 40000, "why": "电力海量数据批处理"},
            {"name": "Airbyte", "category": "数据集成", "github_stars": 14000, "why": "多源异构数据采集入湖"},
        ],
        "secondary": [
            {"name": "DolphinScheduler", "category": "任务调度", "github_stars": 12000, "why": "数据ETL调度编排（国产）"},
            {"name": "Apache Iceberg", "category": "数据湖表格式", "github_stars": 6000, "why": "电力数据湖底层格式"},
            {"name": "DataEase", "category": "BI可视化", "github_stars": 16000, "why": "国产BI大屏，快速做报表"},
        ]
    },
    # ── 数字孪生/BIM/三维 ──
    "孪生": {
        "scenario": "数字孪生/三维可视化",
        "primary": [
            {"name": "CesiumJS", "category": "三维地球", "github_stars": 12000, "why": "电厂/电网三维地理可视化"},
            {"name": "Three.js / R3F", "category": "Web3D框架", "github_stars": 101000, "why": "设备三维模型Web展示"},
            {"name": "Babylon.js", "category": "Web3D引擎", "github_stars": 23000, "why": "数字孪生场景3D渲染"},
            {"name": "Blender + Python API", "category": "三维建模", "github_stars": 18000, "why": "设备BIM模型处理"},
            {"name": "ifc.js / web-ifc", "category": "BIM解析", "github_stars": 1300, "why": "Web端IFC模型加载展示"},
        ],
        "secondary": [
            {"name": "Potree", "category": "点云渲染", "github_stars": 4000, "why": "LiDAR扫描点云Web展示"},
            {"name": "Pixi.js", "category": "2D渲染引擎", "github_stars": 43000, "why": "变电站接线图2D交互渲染"},
        ]
    },
    "BIM": {
        "scenario": "BIM协同/数字化交付",
        "primary": [
            {"name": "xBIM Toolkit", "category": "IFC处理", "github_stars": 1400, "why": ".NET平台BIM数据处理"},
            {"name": "IFCjs", "category": "Web IFC", "github_stars": 1300, "why": "前端BIM模型渲染"},
            {"name": "Speckle", "category": "BIM协同平台", "github_stars": 2200, "why": "多软件BIM数据互通"},
            {"name": "Neo4j", "category": "图数据库", "github_stars": 13000, "why": "BIM构件关系图谱存储"},
        ],
        "secondary": [
            {"name": "V-Ray API / Three.js", "category": "渲染输出", "github_stars": 101000, "why": "BIM可视化导出WebGL"},
        ]
    },
    # ── AI / 大模型 ──
    "大模型": {
        "scenario": "电力大模型/智能助手",
        "primary": [
            {"name": "LangChain / LangGraph", "category": "LLM框架", "github_stars": 92000, "why": "RAG检索增强问答/多智能体"},
            {"name": "Qwen2 / Qwen3", "category": "开源大模型", "github_stars": 38000, "why": "国产大模型，电力微调首选"},
            {"name": "DeepSeek-V3", "category": "推理大模型", "github_stars": 12000, "why": "高性能推理，代码/文档处理强"},
            {"name": "LlamaIndex", "category": "RAG框架", "github_stars": 36000, "why": "电力规程文档知识库构建"},
            {"name": "Ollama", "category": "本地LLM部署", "github_stars": 82000, "why": "离线私有化部署大模型"},
        ],
        "secondary": [
            {"name": "BGE / M3E", "category": "中文向量模型", "github_stars": 14000, "why": "电力文档检索向量编码"},
            {"name": "LiteLLM", "category": "LLM网关", "github_stars": 14000, "why": "多模型供应商统一调用"},
            {"name": "vLLM", "category": "LLM推理引擎", "github_stars": 31000, "why": "高吞吐大模型推理服务"},
        ]
    },
    "AI": {
        "scenario": "电力AI/智能识别",
        "primary": [
            {"name": "PaddleX / PaddleCls", "category": "Paddle生态", "github_stars": 11000, "why": "国产，电力工业视觉识别全流程"},
            {"name": "Scikit-learn", "category": "机器学习库", "github_stars": 59000, "why": "设备缺陷预测/负荷预测传统ML"},
            {"name": "XGBoost / LightGBM", "category": "梯度提升树", "github_stars": 25000, "why": "电力负荷/故障预测性能强"},
            {"name": "Optuna", "category": "超参数优化", "github_stars": 11000, "why": "AI模型自动调参"},
        ],
        "secondary": [
            {"name": "HuggingFace Transformers", "category": "NLP生态", "github_stars": 130000, "why": "电力文本/NLP任务模型库"},
            {"name": "Gradio / Streamlit", "category": "AI演示界面", "github_stars": 32000, "why": "AI Demo快速搭建演示"},
        ]
    },
    # ── 信息安全/等保 ──
    "信息安全": {
        "scenario": "电力信息安全/态势感知",
        "primary": [
            {"name": "Suricata", "category": "IDS/IPS", "github_stars": 16000, "why": "电力监控网络入侵检测"},
            {"name": "Wazuh", "category": "XDR安全平台", "github_stars": 11000, "why": "主机安全监控+威胁检测"},
            {"name": "Nuclei", "category": "漏洞扫描", "github_stars": 19000, "why": "电力系统漏洞快速检测"},
            {"name": "OpenVAS / Greenbone", "category": "漏洞管理", "github_stars": 5500, "why": "企业级漏洞扫描评估"},
            {"name": "Elastic Security / SIEM", "category": "安全分析", "github_stars": 68000, "why": "安全日志集中分析告警"},
        ],
        "secondary": [
            {"name": "Velocidex/velociraptor", "category": "主机取证", "github_stars": 4200, "why": "工控主机安全调查取证"},
            {"name": "Teleport", "category": "运维堡垒机", "github_stars": 17000, "why": "运维审计零信任堡垒机"},
        ]
    },
    "网络安全": {
        "scenario": "电力网络安全/态势感知",
        "primary": [
            {"name": "OPNSense / pfSense", "category": "开源防火墙", "github_stars": 3200, "why": "电力边界安全防护"},
            {"name": "WireGuard", "category": "VPN隧道", "github_stars": 120000, "why": "变电站异地安全加密互联"},
            {"name": "Minemeld / AbuseIPDB", "category": "威胁情报", "github_stars": 600, "why": "电力网络威胁情报共享"},
        ],
        "secondary": [
            {"name": "CyberChef", "category": "安全加密工具", "github_stars": 25000, "why": "加密解密分析工具集"},
        ]
    },
    # ── 中台 / 微服务 / 信创 ──
    "管控平台": {
        "scenario": "管控中心/驾驶舱/指挥中心",
        "primary": [
            {"name": "Vue3 + Vben/Vben5", "category": "中后台前端", "github_stars": 4500, "why": "企业级后台管理前端，组件齐全"},
            {"name": "RuoYi-Vue3 / RuoYi-Flowable", "category": "权限管理系统", "github_stars": 22000, "why": "开源权限+工作流引擎基础框架"},
            {"name": "JeecgBoot", "category": "低代码平台", "github_stars": 39000, "why": "电力业务系统快速构建，国产"},
            {"name": "NocoBase / AppSmith", "category": "内部工具平台", "github_stars": 11000, "why": "快速搭建管控内部工具"},
            {"name": "ECharts / D3.js", "category": "图表库", "github_stars": 61000, "why": "驾驶舱可视化大屏必备"},
        ],
        "secondary": [
            {"name": "Nginx / APISIX", "category": "网关", "github_stars": 14000, "why": "API网关统一入口，国产APISIX推荐"},
            {"name": "xxl-job", "category": "分布式调度", "github_stars": 26000, "why": "定时任务调度中心"},
        ]
    },
    "信创": {
        "scenario": "国产化/信创改造",
        "primary": [
            {"name": "openGauss", "category": "国产数据库", "github_stars": 2500, "why": "华为开源，政企信创首选数据库"},
            {"name": "OceanBase", "category": "国产分布式数据库", "github_stars": 8000, "why": "蚂蚁开源，分布式强一致金融级"},
            {"name": "TiDB", "category": "国产分布式SQL", "github_stars": 37000, "why": "MySQL兼容，水平扩展"},
            {"name": "openEuler", "category": "国产操作系统", "github_stars": 8000, "why": "华为开源服务器OS，信创OS首选"},
            {"name": "东方通 TongWeb 替代：Tomcat", "category": "应用服务器", "github_stars": 7100, "why": "国产中间件替代参考"},
        ],
        "secondary": [
            {"name": "Redis + Valkey", "category": "国产替代", "github_stars": 56000, "why": "Linux基金会分支，Redis商业版替代"},
            {"name": "PostgreSQL", "category": "开源数据库", "github_stars": 59000, "why": "国产达梦/人大金仓开发兼容参考"},
        ]
    },
    # ── 新能源 / 储能 / 调度 ──
    "风电": {
        "scenario": "新能源/风电/光伏/储能监控",
        "primary": [
            {"name": "LTB - Lightning Time Series", "category": "时序预测", "github_stars": 9000, "why": "风电/光伏发电功率预测"},
            {"name": "Darts", "category": "时序预测库", "github_stars": 8200, "why": "Python时序预测工具箱"},
            {"name": "Prophet / NeuralProphet", "category": "时序预测", "github_stars": 18000, "why": "负荷/发电快速预测模型"},
            {"name": "PULP / Pyomo", "category": "优化求解器", "github_stars": 9000, "why": "储能充放电策略优化调度"},
            {"name": "GridCal / PyPSA", "category": "电网仿真", "github_stars": 2200, "why": "电力系统潮流/安全约束仿真"},
        ],
        "secondary": [
            {"name": "OpenEI/Pecan Street 数据集", "category": "数据集", "github_stars": 0, "why": "电力/新能源公开数据集参考"},
        ]
    },
    "光伏": {
        "scenario": "光伏/储能电站智能化",
        "primary": [
            {"name": "SD-CNN / SolarNet", "category": "光伏缺陷识别", "github_stars": 800, "why": "光伏组件EL图像缺陷识别"},
            {"name": "PVlib", "category": "光伏发电模拟", "github_stars": 1100, "why": "光伏出力理论计算与预测"},
            {"name": "Grafana + InfluxDB", "category": "监控可视化", "github_stars": 63000, "why": "光伏组串级监控"},
        ],
        "secondary": [
            {"name": "Celery", "category": "任务队列", "github_stars": 24000, "why": "逆变器数据异步处理调度"},
        ]
    },
    # ── 信息系统/办公/OA ──
    "信息系统": {
        "scenario": "业务系统/协同办公/OA",
        "primary": [
            {"name": "RuoYi / RuoYi-Cloud", "category": "后台管理框架", "github_stars": 22000, "why": "最流行的权限系统基础框架"},
            {"name": "Mall / yudao-cloud", "category": "多租户微服务", "github_stars": 15000, "why": "企业级微服务架构参考"},
            {"name": "Odoo / Dify workflow", "category": "工作流", "github_stars": 35000, "why": "业务审批流程引擎"},
            {"name": "OnlyOffice", "category": "文档协作", "github_stars": 5200, "why": "在线文档编辑协作"},
            {"name": "Waline / Casdoor", "category": "统一认证", "github_stars": 15000, "why": "SSO单点登录，企业多系统统一认证"},
        ],
        "secondary": [
            {"name": "Keycloak", "category": "IAM身份管理", "github_stars": 23000, "why": "开源企业级统一身份认证"},
        ]
    },
}

# 场景触发关键词 — 用于匹配公告标题/正文
SCENARIO_TRIGGERS = {
    "智慧工地": ["智慧工地", "工地管控", "智慧建造", "施工安全", "施工管理",
                  "智能安全帽", "人员定位", "电子围栏", "安全管控", "安全预警"],
    "智能安防": ["智能安防", "智慧安防", "视频监控", "AI安防", "安防系统", "安防平台",
                  "入侵检测", "行为分析", "视频分析", "视频智能"],
    "物联网": ["物联网", "IoT", "感知", "在线监测", "在线监控", "传感器", "智能感知",
                "数据采集", "采集终端", "边缘计算", "边缘网关"],
    "巡检": ["智能巡检", "自动巡检", "巡检机器人", "无人机巡检", "无人机巡查",
              "设备巡检", "线路巡检", "表计", "抄表", "读数识别"],
    "大数据": ["大数据", "数据中台", "数据治理", "数据仓库", "数据分析", "数据湖",
                "BI", "报表", "可视化大屏", "驾驶舱", "数据平台"],
    "孪生": ["数字孪生", "智孪", "三维", "3D", "可视化", "数字沙盘", "孪生平台",
              "三维建模", "实景三维"],
    "BIM": ["BIM", "数字化交付", "三维交付", "BIM协同", "建筑信息", "IFC"],
    "大模型": ["大模型", "LLM", "NLP", "人工智能", "AI应用", "AI大模型", "智能助手",
                "语义搜索", "RAG", "知识库", "大语言模型", "生成式AI"],
    "AI": ["AI", "人工智能", "机器学习", "深度学习", "识别", "图像识别", "语音识别",
            "算法", "模型", "智能分析", "缺陷识别", "人脸识别", "OCR"],
    "信息安全": ["信息安全", "等保", "安全防护", "态势感知", "安全评估", "安全咨询",
                  "渗透测试", "漏洞扫描", "数据安全"],
    "网络安全": ["网络安全", "防火墙", "工控安全", "安全运营", "SOC", "EDR", "XDR",
                  "零信任", "VPN", "网络隔离", "边界安全"],
    "管控平台": ["管控平台", "管理平台", "管控中心", "指挥中心", "驾驶舱", "决策平台",
                  "一体化平台", "综合管理平台", "智慧管理", "智能管理"],
    "信创": ["信创", "国产化", "国产化替代", "国产数据库", "国产操作系统",
              "鲲鹏", "海光", "飞腾", "麒麟", "统信UOS"],
    "风电": ["风电", "新能源", "风机", "风电项目", "风电场", "风力发电", "发电预测",
              "功率预测", "光伏", "储能"],
    "光伏": ["光伏", "光伏发电", "光伏电站", "光伏组件", "逆变器", "储能", "新能源"],
    "信息系统": ["信息系统", "业务系统", "管理系统", "OA系统", "办公系统", "协同办公",
                  "统一认证", "门户", "企业门户"],
}


# ═══════════════════════════════════════════════════════════════════
# 【维度1】需求 → 技术 匹配引擎
# ═══════════════════════════════════════════════════════════════════

def detect_scenarios(title: str, content: str = "") -> dict:
    """检测公告命中的业务场景，返回 {场景: 命中次数}"""
    text = f"{title or ''} {content or ''}"
    hits = {}
    for scenario, keywords in SCENARIO_TRIGGERS.items():
        count = sum(text.count(kw) for kw in keywords)
        if count > 0:
            hits[scenario] = count
    return hits


def match_tech_for_notice(notice_id: int, title: str, content: str = "",
                          province: str = "", category: str = "") -> dict:
    """
    给一条招标公告匹配推荐的技术栈
    返回: {scenarios: [...], primary_tech: [...], secondary_tech: [...], confidence: 0-100}
    """
    scenarios = detect_scenarios(title, content)
    if not scenarios:
        # 没命中场景，按大类兜底
        text = f"{title}{content}"
        if any(t in text for t in ["平台", "系统", "软件"]):
            scenarios = {"管控平台": 1}

    if not scenarios:
        return {
            "notice_id": notice_id,
            "scenarios": [],
            "primary_tech": [],
            "secondary_tech": [],
            "confidence": 0,
            "recommend_reason": "暂未识别出明确技术场景",
        }

    # 按命中次数排序，取TOP2场景合并技术栈
    sorted_scenarios = sorted(scenarios.items(), key=lambda x: -x[1])
    top_scenarios = sorted_scenarios[:2]

    primary_tech, secondary_tech = [], []
    reason_parts = []
    for scenario, cnt in top_scenarios:
        info = SCENARIO_TECH_MAP.get(scenario, {})
        scenario_name = info.get("scenario", scenario)
        reason_parts.append(f"{scenario_name}(×{cnt})")
        for t in info.get("primary", []):
            if t["name"] not in {p["name"] for p in primary_tech}:
                primary_tech.append(t)
        for t in info.get("secondary", []):
            if t["name"] not in {p["name"] for p in secondary_tech} and \
               t["name"] not in {p["name"] for p in primary_tech}:
                secondary_tech.append(t)

    primary_tech.sort(key=lambda x: -x.get("github_stars", 0))
    secondary_tech.sort(key=lambda x: -x.get("github_stars", 0))

    # 置信度：命中数 × 10 + 关键词总次数 × 5，上限100
    total_hits = sum(scenarios.values())
    confidence = min(100, len(scenarios) * 15 + total_hits * 5)

    return {
        "notice_id": notice_id,
        "scenarios": list(scenarios.keys()),
        "scenario_detail": [{"scenario": SCENARIO_TECH_MAP.get(k, {}).get("scenario", k),
                             "hits": v, "key": k}
                            for k, v in sorted_scenarios],
        "primary_tech": primary_tech[:8],
        "secondary_tech": secondary_tech[:5],
        "confidence": confidence,
        "recommend_reason": "命中场景：" + "、".join(reason_parts),
    }


# ═══════════════════════════════════════════════════════════════════
# 【维度2】GitHub热门 → 能源 匹配引擎
# ═══════════════════════════════════════════════════════════════════

# 能源行业典型应用场景池
ENERGY_SCENES = [
    {"scene": "电力巡检", "tags": ["识别", "检测", "缺陷", "无人机", "航拍", "目标检测", "分割", "OCR", "图像"]},
    {"scene": "智慧工地", "tags": ["视频", "识别", "安全帽", "行为", "人员定位", "追踪", "目标检测", "姿态"]},
    {"scene": "电力大模型助手", "tags": ["LLM", "大模型", "RAG", "知识库", "Agent", "NLP", "文档", "问答", "推理"]},
    {"scene": "新能源功率预测", "tags": ["时序", "预测", "时序预测", "Transformer", "forecast"]},
    {"scene": "电力物联接入", "tags": ["MQTT", "IoT", "物联网", "消息队列", "边缘", "工业协议", "Modbus"]},
    {"scene": "三维可视化/数字孪生", "tags": ["3D", "可视化", "Three", "地图", "GIS", "渲染", "WebGL", "孪生"]},
    {"scene": "数据中台/大数据", "tags": ["数据库", "数据仓库", "OLAP", "BI", "调度", "ETL", "Spark", "Flink", "数据湖"]},
    {"scene": "管理平台/中后台", "tags": ["前端", "后台", "管理系统", "Vue", "低代码", "工作流", "权限"]},
    {"scene": "电力网络安全", "tags": ["安全", "入侵检测", "漏洞", "VPN", "加密", "防火墙", "防护"]},
    {"scene": "储能调度优化", "tags": ["优化", "求解器", "运筹", "强化学习", "调度"]},
    {"scene": "变电站自动化", "tags": ["SCADA", "工控", "PLC", "协议", "通信", "控制"]},
    {"scene": "国产信创改造", "tags": ["国产", "数据库", "操作系统", "MySQL替代", "信创"]},
]


def match_github_to_energy(repo_name: str, description: str, language: str = "",
                           topics: list = None, tags: list = None) -> dict:
    """
    把一个GitHub热门Repo 匹配到能源行业适用场景
    """
    if tags is None:
        tags = []
    if topics is None:
        topics = []
    text = f"{repo_name} {description or ''} {language or ''} " + " ".join(topics or []) + " ".join(tags or [])
    text = text.lower()

    matches = []
    for es in ENERGY_SCENES:
        score = 0
        for t in es["tags"]:
            if t.lower() in text:
                score += 10 + len(t) // 3
        # 针对高相关词加权
        for strong_key in ["llm", "python", "yolo", "mqtt", "vue", "react", "postgres", "rust", "go", "kafka", "redis"]:
            if strong_key in text and strong_key in [t.lower() for t in es["tags"]]:
                score += 5
        if score > 0:
            matches.append({"scene": es["scene"], "score": score})

    matches.sort(key=lambda x: -x["score"])
    confidence = min(100, (matches[0]["score"] * 8 if matches else 0))

    # 生成推荐解释
    if matches:
        top = matches[0]
        why = f"关键词匹配到「{top['scene']}」典型需求"
        if len(matches) > 1:
            why += f"，同时适用于「{matches[1]['scene']}」等"
    else:
        why = "暂无明显能源行业适配场景"

    return {
        "repo_name": repo_name,
        "language": language,
        "matched_scenes": matches,
        "top_scene": matches[0]["scene"] if matches else "",
        "confidence": confidence,
        "why_it_matters": why,
    }


# ═══════════════════════════════════════════════════════════════════
# 数据库集成
# ═══════════════════════════════════════════════════════════════

def ensure_db():
    conn = sqlite3.connect(str(DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tech_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notice_id INTEGER NOT NULL,
            notice_type TEXT DEFAULT 'bidding',
            title TEXT,
            scenarios_json TEXT,
            primary_tech_json TEXT,
            secondary_tech_json TEXT,
            confidence REAL,
            recommend_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(notice_id, notice_type)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS github_energy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_name TEXT UNIQUE,
            description TEXT,
            language TEXT,
            stars INTEGER DEFAULT 0,
            week_growth INTEGER DEFAULT 0,
            topics_json TEXT,
            matched_scenes_json TEXT,
            top_scene TEXT,
            confidence REAL,
            why_it_matters TEXT,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def run_match_for_db(limit: int = 50, only_new: bool = True):
    """对DB中招标/中标公告批量跑技术匹配"""
    conn = ensure_db()
    conn.row_factory = sqlite3.Row
    stats = {"processed": 0, "matched": 0, "failed": 0}

    for ntype, table in [("bidding", "bidding_notices"), ("winning", "winning_notices")]:
        # 选未匹配过的高相关公告优先
        where_new = ""
        if only_new:
            where_new = f""" AND n.id NOT IN (
                SELECT notice_id FROM tech_matches WHERE notice_type='{ntype}'
            )"""
        rows = conn.execute(f"""
            SELECT n.id, n.title, n.content_summary, n.province, n.category, n.relevance_score
            FROM {table} n
            WHERE n.relevance_score >= 40 {where_new}
            ORDER BY n.relevance_score DESC, n.id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        for r in rows:
            stats["processed"] += 1
            try:
                result = match_tech_for_notice(
                    r["id"], r["title"], r["content_summary"] or "",
                    r["province"] or "", r["category"] or ""
                )
                if result["confidence"] > 0:
                    stats["matched"] += 1
                conn.execute("""
                    INSERT OR REPLACE INTO tech_matches
                    (notice_id, notice_type, title, scenarios_json,
                     primary_tech_json, secondary_tech_json,
                     confidence, recommend_reason)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (
                    r["id"], ntype, r["title"][:300],
                    json.dumps(result["scenario_detail"], ensure_ascii=False),
                    json.dumps(result["primary_tech"], ensure_ascii=False),
                    json.dumps(result["secondary_tech"], ensure_ascii=False),
                    result["confidence"],
                    result["recommend_reason"]
                ))
            except Exception as e:
                stats["failed"] += 1
                print(f"  ❌ {ntype}#{r['id']}: {e}")

    conn.commit()
    print(f"✅ 技术匹配完成: 处理{stats['processed']} 匹配成功{stats['matched']} 失败{stats['failed']}")
    conn.close()
    return stats


def add_demo_github_data():
    """植入一批演示用的GitHub热门Repo（模拟每周拉取）"""
    conn = ensure_db()
    conn.row_factory = sqlite3.Row

    demo_repos = [
        # AI / 大模型
        {"repo_name": "QwenLM/Qwen3", "description": "通义千问开源大模型，中文能力强",
         "language": "Python", "stars": 38000, "week_growth": 350,
         "topics": ["llm", "nlp", "大模型", "ai"], "tags": ["LLM", "推理"]},
        {"repo_name": "ollama/ollama", "description": "本地私有部署大模型，一键运行",
         "language": "Go", "stars": 82000, "week_growth": 1500,
         "topics": ["llm", "self-hosted", "ai"], "tags": ["LLM", "知识库"]},
        {"repo_name": "langchain-ai/langchain", "description": "大模型应用开发框架，RAG/Agent首选",
         "language": "Python", "stars": 92000, "week_growth": 600,
         "topics": ["llm", "rag", "agent"], "tags": ["LLM", "RAG", "Agent", "知识库", "问答"]},
        # CV / 视觉识别
        {"repo_name": "ultralytics/ultralytics", "description": "YOLOv8/v9/v10 目标检测",
         "language": "Python", "stars": 52000, "week_growth": 800,
         "topics": ["yolo", "目标检测", "识别", "computer-vision"],
         "tags": ["识别", "检测", "缺陷", "目标检测", "图像"]},
        {"repo_name": "open-mmlab/mmdetection", "description": "商汤开源检测工具箱，工业场景强",
         "language": "Python", "stars": 30000, "week_growth": 280,
         "topics": ["检测", "工业视觉"],
         "tags": ["检测", "识别", "缺陷", "目标检测"]},
        {"repo_name": "PaddlePaddle/PaddleOCR", "description": "国产开源OCR，中文表计读数识别",
         "language": "Python", "stars": 40000, "week_growth": 500,
         "topics": ["ocr", "识别"], "tags": ["OCR", "图像"]},
        # IoT / 消息
        {"repo_name": "emqx/emqx", "description": "百万级MQTT Broker，电力物联首选",
         "language": "Erlang", "stars": 14000, "week_growth": 80,
         "topics": ["mqtt", "iot", "物联网"], "tags": ["MQTT", "IoT", "物联网", "消息队列"]},
        {"repo_name": "apache/iotdb", "description": "国产工业时序数据库，电力IoT专用",
         "language": "Java", "stars": 5200, "week_growth": 30,
         "topics": ["iot", "时序数据库"], "tags": ["物联网", "时序", "工业协议"]},
        {"repo_name": "thingsboard/thingsboard", "description": "开源IoT平台，设备接入+可视化",
         "language": "Java", "stars": 16000, "week_growth": 120,
         "topics": ["iot", "物联网平台"], "tags": ["IoT", "物联网"]},
        # 大数据
        {"repo_name": "apache/doris", "description": "国产OLAP实时数仓，大数据分析首选",
         "language": "Java", "stars": 12000, "week_growth": 90,
         "topics": ["database", "olap", "数据仓库"],
         "tags": ["数据库", "数据仓库", "OLAP", "BI"]},
        {"repo_name": "grafana/grafana", "description": "业界领先的可视化监控大屏",
         "language": "TypeScript", "stars": 63000, "week_growth": 700,
         "topics": ["可视化", "监控", "bi"],
         "tags": ["可视化", "BI"]},
        {"repo_name": "dataease/dataease", "description": "国产BI开源软件，大屏制作简单",
         "language": "Java", "stars": 16000, "week_growth": 150,
         "topics": ["bi", "可视化"], "tags": ["BI", "可视化", "大屏"]},
        # 三维/孪生
        {"repo_name": "mrdoob/three.js", "description": "Web3D渲染框架，数字孪生可视化",
         "language": "JavaScript", "stars": 101000, "week_growth": 900,
         "topics": ["webgl", "3d", "可视化"],
         "tags": ["3D", "可视化", "WebGL", "渲染", "孪生"]},
        {"repo_name": "CesiumGS/cesium", "description": "三维地球GIS，电厂地理可视化",
         "language": "JavaScript", "stars": 12000, "week_growth": 60,
         "topics": ["gis", "3d", "地球"], "tags": ["GIS", "3D", "地图", "孪生"]},
        # 时序预测
        {"repo_name": "unit8co/darts", "description": "Python时序预测库，新能源功率预测",
         "language": "Python", "stars": 8200, "week_growth": 120,
         "topics": ["time-series", "forecast", "预测"],
         "tags": ["时序", "预测", "时序预测", "forecast"]},
        # 中后台
        {"repo_name": "yangzongzhuan/RuoYi-Vue3", "description": "RuoYi-Vue3 权限管理系统",
         "language": "Java", "stars": 22000, "week_growth": 300,
         "topics": ["管理系统", "权限"],
         "tags": ["权限", "后台", "管理系统", "低代码", "Vue"]},
        {"repo_name": "jeecgboot/JeecgBoot", "description": "国产低代码平台，业务系统快速搭建",
         "language": "Java", "stars": 39000, "week_growth": 400,
         "topics": ["低代码", "低代码开发", "后台"],
         "tags": ["低代码", "工作流", "后台", "管理系统"]},
        # 安全
        {"repo_name": "OISF/suricata", "description": "开源入侵检测IDS/IPS，电力网络安全",
         "language": "C", "stars": 16000, "week_growth": 50,
         "topics": ["ids", "安全", "网络安全"],
         "tags": ["安全", "入侵检测", "防护"]},
        # 信创
        {"repo_name": "opengauss-mirror/openGauss-server", "description": "华为开源国产数据库",
         "language": "C++", "stars": 2500, "week_growth": 20,
         "topics": ["国产", "database"],
         "tags": ["国产", "数据库", "信创"]},
        {"repo_name": "oceanbase/oceanbase", "description": "蚂蚁开源分布式国产数据库",
         "language": "C++", "stars": 8000, "week_growth": 50,
         "topics": ["database", "分布式数据库", "国产"],
         "tags": ["国产", "数据库", "信创"]},
        # 前端大屏
        {"repo_name": "apache/echarts", "description": "百度开源图表库，大屏可视化标配",
         "language": "TypeScript", "stars": 61000, "week_growth": 600,
         "topics": ["可视化", "图表"],
         "tags": ["可视化", "3D", "大屏"]},
        {"repo_name": "vuejs/core", "description": "Vue3 前端框架，中后台首选",
         "language": "TypeScript", "stars": 46000, "week_growth": 800,
         "topics": ["vue", "前端框架"],
         "tags": ["前端", "Vue", "低代码", "后台", "管理系统"]},
        # 流媒体/视频
        {"repo_name": "ZLMediaKit/ZLMediaKit", "description": "国产流媒体服务器，GB28181监控接入",
         "language": "C++", "stars": 10000, "week_growth": 80,
         "topics": ["流媒体", "gb28181", "视频"],
         "tags": ["视频", "识别"]},
        # 智能巡检
        {"repo_name": "obss/sahi", "description": "航拍小目标检测，无人机电力巡检",
         "language": "Python", "stars": 12000, "week_growth": 200,
         "topics": ["目标检测", "航拍"],
         "tags": ["无人机", "航拍", "缺陷", "检测", "目标检测"]},
    ]

    inserted = 0
    for rp in demo_repos:
        result = match_github_to_energy(
            rp["repo_name"], rp["description"], rp["language"],
            rp["topics"], rp["tags"]
        )
        try:
            conn.execute("""
                INSERT OR REPLACE INTO github_energy
                (repo_name, description, language, stars, week_growth,
                 topics_json, matched_scenes_json, top_scene,
                 confidence, why_it_matters, url, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?, CURRENT_TIMESTAMP)
            """, (
                rp["repo_name"], rp["description"][:500], rp["language"],
                rp["stars"], rp["week_growth"],
                json.dumps(rp["topics"], ensure_ascii=False),
                json.dumps(result["matched_scenes"], ensure_ascii=False),
                result["top_scene"],
                result["confidence"],
                result["why_it_matters"],
                f"https://github.com/{rp['repo_name']}"
            ))
            inserted += 1
        except Exception as e:
            print(f"  ⚠️ {rp['repo_name']}: {e}")

    conn.commit()
    print(f"✅ 植入{inserted}条GitHub热门Repo能源化数据")
    conn.close()
    return inserted


# ═══════════════════════════════════════════════════════════════════
# 汇总导出（给前端）
# ═══════════════════════════════════════════════════════════════

def export_for_frontend():
    """生成前端用的 JSON 数据"""
    conn = ensure_db()
    conn.row_factory = sqlite3.Row
    out = {}

    # --- 1. 技术匹配总览 ---
    tm_cnt = conn.execute("SELECT COUNT(*) FROM tech_matches WHERE confidence>0").fetchone()[0]
    sc_rows = conn.execute("""
        SELECT json_extract(scenarios_json, '$[0].scenario') as scene, COUNT(*) as cnt
        FROM tech_matches
        WHERE confidence>0
        GROUP BY scene
        ORDER BY cnt DESC
        LIMIT 15
    """).fetchall()
    out["match_summary"] = {
        "total_matched": tm_cnt,
        "by_scenario": [{"scene": r["scene"] or "未分类", "count": r["cnt"]} for r in sc_rows]
    }

    # --- 2. 高相关招标的技术推荐（TOP 20）---
    recs = conn.execute("""
        SELECT t.*, b.url, b.procurement_owner, b.province, b.relevance_score as bidding_score,
               b.publish_date, b.budget_amount
        FROM tech_matches t
        LEFT JOIN bidding_notices b ON t.notice_id=b.id AND t.notice_type='bidding'
        WHERE t.confidence>=30
        ORDER BY b.relevance_score DESC, t.confidence DESC
        LIMIT 20
    """).fetchall()
    out["top_recommendations"] = [
        {
            "notice_id": r["notice_id"],
            "title": r["title"],
            "owner": r["procurement_owner"],
            "province": r["province"],
            "publish_date": r["publish_date"],
            "budget": r["budget_amount"],
            "bidding_score": r["bidding_score"],
            "confidence": r["confidence"],
            "reason": r["recommend_reason"],
            "scenarios": json.loads(r["scenarios_json"] or "[]"),
            "primary_tech": json.loads(r["primary_tech_json"] or "[]"),
            "secondary_tech": json.loads(r["secondary_tech_json"] or "[]"),
            "url": r["url"],
        }
        for r in recs
    ]

    # --- 3. GitHub热门能源化榜单 ---
    ge = conn.execute("""
        SELECT * FROM github_energy
        ORDER BY confidence DESC, stars DESC, week_growth DESC
        LIMIT 30
    """).fetchall()
    out["github_trending_energy"] = [
        {
            "repo_name": r["repo_name"],
            "description": r["description"],
            "language": r["language"],
            "stars": r["stars"],
            "week_growth": r["week_growth"],
            "topics": json.loads(r["topics_json"] or "[]"),
            "matched_scenes": json.loads(r["matched_scenes_json"] or "[]"),
            "top_scene": r["top_scene"],
            "confidence": r["confidence"],
            "why_it_matters": r["why_it_matters"],
            "url": r["url"],
        }
        for r in ge
    ]

    # 按能源场景聚合
    by_scene = {}
    for g in out["github_trending_energy"]:
        if g["top_scene"]:
            by_scene.setdefault(g["top_scene"], []).append(g)
    out["github_by_scene"] = {k: v[:5] for k, v in by_scene.items()}

    conn.close()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "tech_match.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"✅ 已导出: {output_path}  ({len(out['top_recommendations'])}项推荐 + {len(out['github_trending_energy'])}个GitHub Repo)")
    return output_path


# ═══════════════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "match":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            only_new = "--all" not in " ".join(sys.argv)
            run_match_for_db(limit=limit, only_new=only_new)
        elif cmd == "github":
            add_demo_github_data()
        elif cmd == "export":
            export_for_frontend()
        elif cmd == "all":
            run_match_for_db(limit=100, only_new=True)
            add_demo_github_data()
            export_for_frontend()
        else:
            print("Usage: tech_matcher.py [match|github|export|all]")
    else:
        print("自动执行全部流程...")
        run_match_for_db(limit=100, only_new=True)
        add_demo_github_data()
        export_for_frontend()
