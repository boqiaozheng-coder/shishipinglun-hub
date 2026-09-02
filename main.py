#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""时评与事件中心 —— 软件统一入口。

用法：
  python3 main.py download                 # 下载文章（默认每栏目 5 篇，PDF+Word）
  python3 main.py download --format pdf --count 10
  python3 main.py desktop                   # 以独立桌面窗口打开软件
  python3 main.py events                    # 启动事件中心网页服务
  python3 main.py sync-events               # 同步国内外最新事件
  python3 main.py discuss --event ID --comment ID --text "回复内容"
  python3 main.py doctor                    # 检查依赖是否齐全
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DESKTOP_DIR = Path.home() / "Desktop" / "时评文章下载"


def _run_module(module: str, args: list[str]) -> int:
    return subprocess.call([sys.executable, "-m", module, *args], cwd=ROOT)


def cmd_download(extra: list[str]) -> int:
    if not extra:
        extra = ["--format", "both", "--count", "5", "--out", str(DESKTOP_DIR)]
    return _run_module("shishipinglun.downloader", extra)


def cmd_events(extra: list[str]) -> int:
    if not extra:
        extra = ["--port", "8765"]
    return _run_module("shishipinglun.events.server", extra)


def cmd_desktop(extra: list[str]) -> int:
    if not extra:
        extra = ["--port", "8765"]
    return _run_module("shishipinglun.desktop", extra)


def cmd_sync_events(extra: list[str]) -> int:
    if not extra:
        extra = ["--limit", "8"]
    return _run_module("shishipinglun.events.sync_events", extra)


def cmd_discuss(extra: list[str]) -> int:
    return _run_module("shishipinglun.events.record_discussion", extra)


def cmd_doctor() -> int:
    ok = True
    print("正在检查依赖…")
    for name in ("requests", "bs4", "docx", "pymupdf"):
        try:
            __import__(name)
            print(f"  ✓ {name}")
        except ImportError:
            ok = False
            print(f"  ✗ {name} 缺失")
    if not ok:
        print("缺少依赖，请执行：python3 -m pip install -r requirements.txt")
        return 1
    print("依赖齐全 ✓")
    return 0


def usage() -> int:
    print(__doc__)
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        return usage()
    verb = argv[0]
    extra = argv[1:]
    if verb == "download":
        return cmd_download(extra)
    if verb == "events":
        return cmd_events(extra)
    if verb == "desktop":
        return cmd_desktop(extra)
    if verb in ("sync-events", "sync"):
        return cmd_sync_events(extra)
    if verb == "discuss":
        return cmd_discuss(extra)
    if verb == "doctor":
        return cmd_doctor()
    print(f"未知命令：{verb}")
    return usage()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
