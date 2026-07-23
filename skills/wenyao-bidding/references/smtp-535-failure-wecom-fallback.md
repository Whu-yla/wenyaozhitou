# SMTP 腾讯企业邮 535 认证失败 → 企微 Webhook 替代

## 事件
2026-06-26 部署 Nginx 守护告警，先尝试 SMTP → 企微 Webhook。

## SMTP 失败详情

| 参数 | 值 |
|:--|:--|
| 邮箱 | yla5995@csepdi.com (腾讯企业邮) |
| MX | mxbiz1.qq.com |
| SMTP 服务器 | smtp.exmail.qq.com |
| 尝试端口 | 465 (SSL) / 587 (STARTTLS) |
| 尝试用户 | yla5995 / yla5995@csepdi.com |
| 密码 | 客户端专用密码 (刚生成) |
| 结果 | **全部 535 `authentication failed, system busy`** |

## 可能原因
1. 密码刚生成需等待激活（几分钟到几小时）
2. 企业管理员禁用了 SMTP 服务
3. 阿里云 ECS IP 不在企业邮白名单
4. 需要先在 webmail 登录一次激活账号

## 解决方案：企微 Webhook

```python
import json, urllib.request
payload = json.dumps({
    "msgtype": "markdown",
    "markdown": {"content": "## 标题\n> 内容"}
}).encode()
req = urllib.request.Request(WEBHOOK_URL, data=payload,
    headers={"Content-Type": "application/json"})
urllib.request.urlopen(req, timeout=10)
```

**优势**：
- 零依赖（仅 stdlib `json` + `urllib.request`）
- 无认证凭据泄露风险
- 消息秒级直达用户手机
- 支持 Markdown 格式化

## 企微 Markdown 格式规范

```json
{
    "msgtype": "markdown",
    "markdown": {
        "content": "## 标题\n> 引用\n**加粗**\n[链接](url)"
    }
}
```
