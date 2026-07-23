#!/bin/bash
# promote.sh — 测试环境 → 生产环境 一键发布
# 文鳐智投 V1.0 稳定版部署工具
set -euo pipefail

TEST_DIR="/var/www/html/bidding-test"
PROD_DIR="/var/www/html/bidding"
STABLE_DIR="/var/www/html/bidding/v1.0-stable"
CHANGELOG="$PROD_DIR/changelog.html"
NOW=$(date '+%Y-%m-%d %H:%M')

FILES=(
    "index.html"
    "app.js"
    "chat-widget.css"
    "chat-widget.js"
    "changelog.html"
    "manual.html"
)

echo "=========================================="
echo " 文鳐智投 — 测试 → 生产 发布工具"
echo "=========================================="
echo ""
echo "将同步以下文件："
echo ""

for f in "${FILES[@]}"; do
    if [ -f "$TEST_DIR/$f" ]; then
        ts=$(stat -c %Y "$TEST_DIR/$f" 2>/dev/null)
        ps=$(stat -c %Y "$PROD_DIR/$f" 2>/dev/null)
        echo "  $f  (测试: $(date -d @$ts '+%H:%M') | 生产: $(date -d @$ps '+%H:%M'))"
    fi
done

echo ""
echo "⚠️  此操作将覆盖生产环境文件！"
read -p "确认发布? (输入 yes 继续): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "已取消"
    exit 0
fi

echo ""
echo ">>> 备份当前生产到 V1.0 快照..."
for f in "${FILES[@]}"; do
    if [ -f "$PROD_DIR/$f" ]; then
        cp "$PROD_DIR/$f" "$STABLE_DIR/"
    fi
done
echo "$NOW — 发布前自动备份" >> "$STABLE_DIR/VERSION.txt"
echo "✅ 备份完成"

echo ""
echo ">>> 同步文件..."
for f in "${FILES[@]}"; do
    if [ -f "$TEST_DIR/$f" ]; then
        cp "$TEST_DIR/$f" "$PROD_DIR/"
        echo "  ✅ $f"
    else
        echo "  ⏭️  $f (测试环境无此文件，跳过)"
    fi
done

echo ""
echo ">>> 设置权限..."
# 文件 644
chmod 644 "$PROD_DIR"/*.html "$PROD_DIR"/*.js "$PROD_DIR"/*.css "$PROD_DIR"/*.json "$PROD_DIR"/*.ico "$PROD_DIR"/*.png 2>/dev/null || true
# 目录 755
find "$PROD_DIR/img" "$PROD_DIR/img_gen" "$PROD_DIR/data" -type d -exec chmod 755 {} \; 2>/dev/null || true

echo "✅ 权限完成"

echo ""
echo ">>> 验证..."
for f in "${FILES[@]}"; do
    if [ -f "$PROD_DIR/$f" ]; then
        code=$(curl -sI -o /dev/null -w "%{http_code}" "https://www.yfzx.online/bidding/$f")
        if [ "$code" = "200" ]; then
            echo "  ✅ $f → HTTP $code"
        else
            echo "  ⚠️  $f → HTTP $code"
        fi
    fi
done

echo ""
echo "=========================================="
echo " ✅ 发布完成！"
echo " 生产: https://www.yfzx.online/bidding/"
echo " 测试: https://www.yfzx.online/bidding-test/"
echo "=========================================="
