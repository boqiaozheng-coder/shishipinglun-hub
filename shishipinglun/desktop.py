#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立桌面窗口入口。

把事件中心网页装进一个原生 macOS 窗口：
  - 后台启动本地 HTTP 服务（默认 127.0.0.1:8765）
  - pywebview 打开无边框浏览器窗口，关闭窗口即退出

用法：
  python3 -m shishipinglun.desktop
  python3 main.py desktop
"""

from __future__ import annotations

import argparse
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path


def _load_events_server():
    """把 events 目录加入 sys.path 后加载 server 模块（兼容 -m 与直接运行）。"""
    events_dir = Path(__file__).resolve().parent / "events"
    if str(events_dir) not in sys.path:
        sys.path.insert(0, str(events_dir))
    import server  # noqa: PLC0415

    return server


def main() -> int:
    ap = argparse.ArgumentParser(description="时评与事件中心 - 桌面窗口")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--width", type=int, default=1220)
    ap.add_argument("--height", type=int, default=820)
    args = ap.parse_args()

    try:
        import webview  # noqa: PLC0415
    except ImportError:
        print(
            "缺少 pywebview，请先执行：python3 -m pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 2

    try:
        from shishipinglun.events import server as events_server
    except ImportError:
        events_server = _load_events_server()
    Handler = events_server.Handler

    repaired = events_server.prepare_database()
    if repaired:
        print(f"已修复 {repaired} 条重复或缺失的记录 ID", flush=True)

    # 端口被占用时自动顺延，避免“窗口开了但内容不对”的困惑
    httpd = None
    for port in range(args.port, args.port + 10):
        try:
            httpd = ThreadingHTTPServer((args.host, port), Handler)
            break
        except OSError:
            continue
    if httpd is None:
        print(f"无法绑定端口 {args.port}~{args.port + 9}", file=sys.stderr)
        return 1

    url = f"http://{args.host}:{httpd.server_address[1]}"
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    print(f"本地服务已启动：{url}（关闭窗口后自动停止）", flush=True)

    window = webview.create_window(
        "时评与事件中心",
        url,
        width=args.width,
        height=args.height,
        min_size=(940, 640),
        confirm_close=False,
    )
    try:
        webview.start()
    finally:
        httpd.shutdown()
        httpd.server_close()
    print("桌面窗口已关闭，服务已停止。", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
