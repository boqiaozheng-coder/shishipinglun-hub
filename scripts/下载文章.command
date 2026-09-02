#!/bin/zsh
cd "$(dirname "$0")/.."
python3 -m shishipinglun.downloader --format both --count 5 --out "$HOME/Desktop/时评文章下载"
