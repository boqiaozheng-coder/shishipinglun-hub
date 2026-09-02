#!/bin/zsh
# 生成 DMG 安装镜像（需先执行 scripts/build.sh）
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
VERSION="${1:-1.0.0}"
APP="$ROOT/dist/时评与事件中心.app"
STAGE="$ROOT/release/stage"
DMG="$ROOT/release/时评与事件中心-$VERSION.dmg"

if [[ ! -d "$APP" ]]; then
  echo "未找到 $APP，请先运行 scripts/build.sh" >&2
  exit 1
fi

rm -rf "$STAGE" "$DMG"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
cat > "$STAGE/安装说明.txt" <<'EOF'
时评与事件中心 v1.0.0

安装：
1. 把“时评与事件中心.app”拖入“应用程序”文件夹；
2. 双击运行。

首次打开若提示“无法验证开发者”，右键应用 → 打开 → 再点“打开”。

数据保存在：~/Library/Application Support/ShishipinglunCenter/
EOF

echo "== 创建 DMG =="
hdiutil create -volname "时评与事件中心" -srcfolder "$STAGE" \
  -ov -format UDZO "$DMG" >/dev/null

shasum -a 256 "$DMG" | tee "$DMG.sha256"
echo "DMG 已生成：$DMG"
