#!/bin/zsh
# 构建 .app（在项目根目录执行：bash scripts/build.sh）
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "== 编译检查 =="
python3 -m compileall -q shishipinglun main.py packaging/launcher.py

echo "== PyInstaller 打包 =="
python3 -m PyInstaller --noconfirm --clean --windowed \
  --name ShishipinglunCenter \
  --icon "$ROOT/packaging/icon.icns" \
  --add-data 'shishipinglun:shishipinglun' \
  "$ROOT/packaging/launcher.py"

echo "== 重命名为中文名 =="
rm -rf "$ROOT/dist/时评与事件中心.app"
mv "$ROOT/dist/ShishipinglunCenter.app" "$ROOT/dist/时评与事件中心.app"

echo "构建完成：$ROOT/dist/时评与事件中心.app"
