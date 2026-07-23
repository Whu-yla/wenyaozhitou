# 中文正文提取 — Regex 致命坑（2026-06-25 真实案例）

## 坑 1：字符排除集遗漏 `。`

### 症状
region 字段显示：`广州2.4资格审查方式：资格后审2.5招标分类：专项2.6标`
而不是：`广东`

### 根因
```python
REGION_PATTERNS = [
    re.compile(r'(?:招标项目|项目)所在地区[：:]\s*([^；;，,\n]+)'),
]
```
正文原文：`招标项目所在地区：广州。2.4资格审查方式：资格后审。2.5招标分类：专项`

regex 捕获组 `([^；;，,\n]+)` 从 `广州` 开始，遇到 `。` 不停止（`.` 不在排除集），一路吃到行尾第一个 `\n`。

### 修复
```python
REGION_PATTERNS = [
    re.compile(r'(?:招标项目|项目)所在地区[：:]\s*([^。；;，,\n]{1,20})'),
]
```
1. 排除集中加入 `。`（中文句号）
2. 加 `{1,20}` 长度截断，即使其他终止符全失效也只取前20字符

---

## 坑 2：`re.sub(r'\s+', ' ', text)` 压扁换行 → `[^\n]` 失效

### 症状
procurement_owner 字段显示：`南网数字运营软件科技（广东）有限公司联系人：王工地址：广东省深圳市电话：4008100100 转 2 采购代理机构：南方...`
而不是：`南网数字运营软件科技（广东）有限公司`

### 根因
```python
def _extract_region_owner(text):
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean)   # ← 把 \n 压成了空格！
    for pat in BIDDER_PATTERNS:
        m = pat.search(clean)
        ...
```
BIDDER_PATTERNS 用 `[^。；;，,\n]` 做排除，但 `\n` 已被压成空格，不再生效。于是 regex 跨越多行捕获到"联系人"后面的内容。

### 修复
```python
def _extract_region_owner(text):
    clean = re.sub(r'<[^>]+>', '', text)
    # 不要压换行！保留 \n 让 regex 的 [^\n] 能正确截断
    ...
```
删除 `re.sub(r'\s+', ' ', clean)`，保留原始换行符。

---

## 坑 3：标题前缀污染

### 症状
南网平台所有标题以 `采购公告 > 招标公告 > ` 或 `采购公告 > 公示公告 > ` 开头。
页面表格中标题列冗长、不可扫描。

### 修复
在 `score_item()` 中循环剥离：
```python
clean_title = re.sub(
    r'^(?:采购公告|招标公告|中标公告|成交公告|公示公告|非招标公告|零星采购公告)\s*>\s*', 
    '', title
)
while clean_title != title:
    title = clean_title
    clean_title = re.sub(r'^(?:采购公告|招标公告|...)\s*>\s*', '', title)
result['title'] = title[:200]
```
循环是因为有 `采购公告 > 招标公告 > 实际标题` 多层前缀。

---

## 坑 4：patch 工具的 Python 字符串转义

### 症状
```python
patch(path='file.py', old_string='...', new_string='...\\n...')
```
写入文件后变成字面量 `\\n` 而非换行符。

### 规避
涉及 `\n`、`\"` 等转义字符时，用 `write_file` 替换整个文件，不用 `patch` 做片段替换。
