# 投标技术规范书深度分析工作流

## 触发条件
- 用户上传 .doc/.docx 格式的技术规范书/招标文件
- 用户要求分析某个特定项目的投标机会
- 用户问"有没有类似项目的中标情况"

## 工作流步骤

### 1. 文档提取

```bash
# .doc 文件 (Composite Document File V2) — 用 catdoc
catdoc "/path/to/file.doc" 2>/dev/null | head -300   # 先看前300行概览
catdoc "/path/to/file.doc" 2>/dev/null | wc -l        # 总行数
catdoc "/path/to/file.doc" 2>/dev/null | sed -n 'N,Mp' # 翻页读取

# .docx 文件 — 用 python-docx 或 libreoffice 转换
# 优先 catdoc，比 libreoffice --headless 快 10 倍以上
```

**文件元信息获取**：
```bash
file /path/to/file.doc   # 查看格式/编码/作者/页数
```

### 2. 竞争分析数据库查询

数据库路径：`/root/.hermes/profiles/wenyaozhitou/data/bidding.db`

关键查询模式：

```sql
-- 同类中标项目
SELECT * FROM winning_notices 
WHERE (title LIKE '%三维%' OR title LIKE '%BIM%' OR title LIKE '%数字孪生%')
  AND relevance_score >= 30
ORDER BY publish_date DESC;

-- 同一招标方的历史中标
SELECT * FROM winning_notices 
WHERE procurement_owner LIKE '%深圳能源%'
ORDER BY publish_date DESC;

-- 同类招标项目（用于判断竞争态势）
SELECT * FROM bidding_notices 
WHERE (title LIKE '%管理系统%' OR title LIKE '%数字化%')
  AND relevance_score >= 55
ORDER BY publish_date DESC;
```

⚠️ **查询注意事项**：
- 使用 `procurement_owner` LIKE 匹配时用简称（如"深能"而非全称"深圳能源环保"）
- 招标方信息可能存储在 `procurement_owner` 或 `content_summary` 中
- 中标方信息在 `winner_company` 字段
- `winning_amount` 可能是文本格式（如"人民币壹仟贰佰贰拾贰万元整"）需注意

### 3. 报告结构模板

投标机会分析报告应包含以下章节：

| 章节 | 内容 |
|:--|:--|
| 项目速览 | 招标方、项目类型、规模、核心指标卡片 |
| 项目总览 | 基本信息表 + 范围全景（系统开发/现场服务分开） |
| 核心技术指标 | 性能/BIM/安全三大维度 |
| 进度与交付 | 里程碑时间线 + 知识产权交付要求 |
| 团队资质要求 | 关键角色硬门槛（证书/经验） |
| 竞争格局 | 数据库同类中标 + 竞品画像表 |
| 数智科技匹配度 | 能力对标表 + SWOT四象限 |
| 风险与应对 | 风险等级表 + 具体应对策略 |
| 投标策略建议 | 差异化亮点 + 报价参考 |
| 前置行动清单 | P0/P1/P2优先级 + 时限 |

### 4. 匹配度评分标准

| 匹配度 | 条件 |
|:--|:--|
| ⭐⭐⭐⭐⭐ | 数智科技已有成熟产品直接覆盖 |
| ⭐⭐⭐⭐ | 核心能力覆盖，需少量适配 |
| ⭐⭐⭐ | 能力可扩展覆盖，需一定投入 |
| ⭐⭐ | 可做但缺少行业经验 |
| ⭐ | 不是核心能力方向 |

### 5. 风险等级定义

| 等级 | 标签 | 含义 |
|:--|:--|:--|
| 致命 | 🔴 | 可能导致直接出局（如地域门槛、资质硬伤） |
| 高 | 🔴 | 需要重大投入才能满足（如人员证书缺失） |
| 中 | 🟡 | 可通过策略应对（如竞争关系、技术壁垒） |
| 低 | 🟢 | 行业惯例，接受即可 |

### 6. 部署

```bash
# 报告生成后部署到测试环境
cp report.html /var/www/html/bidding-test/xxx-report.html
chmod 644 /var/www/html/bidding-test/xxx-report.html
```

⚠️ 遵循**生产环境锁定铁律**：先部署测试环境，不直接动 `/var/www/html/bidding/`。
