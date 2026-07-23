# ⛔ AI封面生成 — 已废弃 (2026-06-24)

**AI 封面方案已全面废弃。** 现用 8 张本地固化封面图。

## 废弃原因

1. **权限问题频发**：`img_gen/` 目录 umask 导致 754 → nginx 403/404
2. **中文字体不可用**：服务器无 CJK 字体 → 所有中文变方块
3. **API 断连**：DeepSeek/通义万相 API 不稳定，`Broken pipe` 频发
4. **用户明确要求**：「你就直接搞一个1~8的那个图片」「固定下来，固化下来，以后不要再改了」

## 当前方案：固定封面

- 8 张纯数字封面：`/var/www/html/bidding/img_gen/covers/cover_1~8.png`
- 深色科技感底 + 彩色斜线 + 大数字（800×400）
- 推送时按卡片顺序循环：第N张卡片 → cover_N.png
- `wecom_push.py` 不再导入 `ai_cover`，纯本地路径

## 权限（仍须注意）

即使不用 AI 生成，`img_gen/` 目录仍需 **755**：
- `pipeline_master.sh` 阶段4 有 `chmod -R 755 /var/www/html/bidding/img_gen`
- 生成脚本 `gen_covers.py` 创建目录后显式 `os.chmod(0o755)`

## 历史参考（AI方案，已废弃）

<details>
<summary>通义万相 API 方案（仅供参考，不再使用）</summary>

- 模型：`wanx2.0-t2i-turbo`
- 端点：`https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis`
- 模式：异步（`X-DashScope-Async: enable`）
- 裁切：1024×1024 → 800×400
- 缓存：`/var/www/html/bidding/img_gen/cache/{item_id}.png`

</details>
