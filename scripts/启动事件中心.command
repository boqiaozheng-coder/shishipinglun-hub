#!/bin/zsh
cd "$(dirname "$0")/.."
python3 -m shishipinglun.events.server --port 8765
