#!/bin/bash
# 文鳐智投 测试→生产 一键发布
# 用法: bash scripts/promote.sh [--dry-run]
set -e

TEST="/var/www/html/bidding-test"
PROD="/var/www/html/bidding"
DRY=false
[ "$1" = "--dry-run" ] && DRY=true

FILES_TO_SYNC=(
    "index.html"
    "app.js"
    "chat-widget.js"
    "chat-widget.css"
    "changelog.html"
    "manual.html"
    "img/logo.png"
    "img/favicon-32x32.png"
    "img/favicon.ico"
    "img/apple-touch-icon.png"
    "img_gen/og-share.png"
)

echo "============================================"
echo "  文鳐智投  测试 → 生产  发布"
echo "============================================"
echo ""

# 检查测试环境数据一致性
PROD_DATA=$(md5sum "$PROD/data.json" 2>/dev/null | cut -d' ' -f1)
TEST_DATA=$(md5sum "$TEST/data.json" 2>/dev/null | cut -d' ' -f1)
if [ "$PROD_DATA" != "$TEST_DATA" ]; then
    echo "⚠️  data.json 不一致（测试共用生产软链接，此警告可忽略）"
fi

echo "即将推送以下文件："
for f in "${FILES_TO_SYNC[@]}"; do
    if [ -f "$TEST/$f" ]; then
        echo "  ✓ $f"
    else
        echo "  ✗ $f (不存在，跳过)"
    fi
done
echo ""

if $DRY; then
    echo "🔍 DRY RUN — 仅检查，不实际复制"
    exit 0
fi

# 确认
read -p "确认发布到生产环境？[y/N] " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消"
    exit 0
fi

# 备份生产环境
BACKUP_DIR="/var/www/html/bidding.bak.$(date +%Y%m%d_%H%M)"
mkdir -p "$BACKUP_DIR"
echo "📦 备份到 $BACKUP_DIR"
for f in "${FILES_TO_SYNC[@]}"; do
    if [ -f "$PROD/$f" ]; then
        mkdir -p "$(dirname "$BACKUP_DIR/$f")"
        cp "$PROD/$f" "$BACKUP_DIR/$f"
    fi
done

# 推送
echo ""
echo "🚀 开始推送..."
for f in "${FILES_TO_SYNC[@]}"; do
    if [ -f "$TEST/$f" ]; then
        mkdir -p "$(dirname "$PROD/$f")"
        cp "$TEST/$f" "$PROD/$f"
        echo "  ✅ $f"
    fi
done

# 去掉测试标记
/usr/local/lib/hermes-agent/venv/bin/python3 -c "
html = open('$PROD/index.html').read()
html = html.replace('<title>🧪 测试环境 · 文鳐智投</title>', '<title>文鳐智投 · 数智科技投标监控</title>')
html = html.replace('<h1>文鳐智投 <span style=\"background:#f59e0b;color:#000;font-size:10px;padding:2px 8px;border-radius:4px;vertical-align:middle\">测试</span></h1>', '<h1>文鳐智投</h1>')
open('$PROD/index.html','w').write(html)
print('  ✅ 已移除测试标记')
"

# 修复权限
chmod -R 755 "$PROD"
find "$PROD" -type f -exec chmod 644 {} \; 2>/dev/null

echo ""
echo "============================================"
echo "  ✅ 发布完成！"
echo "  生产: https://www.yfzx.online/bidding/"
echo "  备份: $BACKUP_DIR"
echo "============================================"
