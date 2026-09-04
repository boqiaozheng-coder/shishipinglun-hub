"""事件中心本地网页服务。

启动：python3 event_center/app.py
访问：http://127.0.0.1:8765

功能：
  - 事件库（国内/国际，可自动同步与手动添加）
  - 对事件写评论，标记想和 Codex 讨论
  - 查看 Codex 讨论回复（由 record_discussion.py 写入）
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    from . import db
except ImportError:  # 直接以脚本方式运行 python3 server.py 时
    import db

ROOT = Path(__file__).resolve().parent


def _static_dir() -> Path:
    """兼容开发模式与 PyInstaller 打包后的目录定位。"""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent / "_internal"))
        return base / "shishipinglun" / "events" / "static"
    return ROOT / "static"


STATIC = _static_dir()

_download_lock = threading.Lock()
DOWNLOAD_STATE = {
    "running": False,
    "code": None,
    "started_at": "",
    "finished_at": "",
    "message": "尚未运行过下载",
}


def _event_sort_key(event: dict) -> tuple[str, str]:
    """事件列表以新闻日期为主、入库时间为辅，避免补录旧闻排到最前。"""
    return (event.get("date", ""), event.get("added_at", ""))


def _download_worker(count: int) -> None:
    try:
        from shishipinglun import downloader

        out_dir = Path.home() / "Desktop" / "时评文章下载"
        args = downloader.build_parser().parse_args(
            ["--format", "both", "--count", str(count), "--out", str(out_dir)]
        )
        code = downloader.run(args)
        message = downloader.last_run_summary or (
            "下载完成" if code == 0 else "下载过程出现错误，请检查网络后重试"
        )
    except Exception as exc:  # noqa: BLE001
        code = 1
        message = f"下载失败：{exc}"
    with _download_lock:
        DOWNLOAD_STATE.update(
            {
                "running": False,
                "code": code,
                "finished_at": db.now_iso(),
                "message": message,
            }
        )


def start_download(count: int) -> tuple[bool, str]:
    with _download_lock:
        if DOWNLOAD_STATE["running"]:
            return False, "已有下载任务在运行，请稍候"
        DOWNLOAD_STATE.update(
            {
                "running": True,
                "code": None,
                "started_at": db.now_iso(),
                "finished_at": "",
                "message": "下载中…（每栏目 5 篇，PDF + Word，请稍候）",
            }
        )
    threading.Thread(target=_download_worker, args=(count,), daemon=True).start()
    return True, "已开始下载"


def _json(data, status: int = 200) -> bytes:
    return (
        json.dumps(data, ensure_ascii=False).encode("utf-8"),
        status,
        "application/json; charset=utf-8",
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "EventCenter/1.0"

    def log_message(self, fmt, *args):  # 精简控制台输出
        sys.stdout.write("  " + (fmt % args) + "\n")

    def _send(self, body: bytes, status: int = 200, ctype: str = "text/html; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    # ---------- GET ----------
    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            self._send((STATIC / "index.html").read_bytes())
            return
        if path == "/app.js":
            self._send((STATIC / "app.js").read_bytes(), ctype="text/javascript; charset=utf-8")
            return
        if path == "/style.css":
            self._send((STATIC / "style.css").read_bytes(), ctype="text/css; charset=utf-8")
            return
        if path == "/favicon.ico":
            self._send(b"", 404)
            return

        if path == "/api/events":
            data = db.load_db()
            events = data["events"]
            q = (query.get("q", [""])[0] or "").strip().lower()
            area = query.get("area", [""])[0]
            if area in ("domestic", "international"):
                events = [e for e in events if e.get("area") == area]
            if q:
                events = [
                    e
                    for e in events
                    if q in (e.get("title", "") + " " + e.get("source", "")).lower()
                ]
            events = sorted(events, key=_event_sort_key, reverse=True)
            body, status, ctype = _json({"events": events})
            self._send(body, status, ctype)
            return

        if path == "/api/event":
            eid = query.get("id", [""])[0]
            data = db.load_db()
            event = next((e for e in data["events"] if e["id"] == eid), None)
            if event is None:
                body, status, ctype = _json({"error": "事件不存在"}, 404)
                self._send(body, status, ctype)
                return
            comments = [
                c
                for c in data["comments"]
                if c.get("event_id") == eid
            ]
            comments = sorted(comments, key=lambda c: c.get("created_at", ""))
            body, status, ctype = _json({"event": event, "comments": comments})
            self._send(body, status, ctype)
            return

        if path == "/api/comments":
            data = db.load_db()
            comments = sorted(data["comments"], key=lambda c: c.get("created_at", ""), reverse=True)
            body, status, ctype = _json({"comments": comments})
            self._send(body, status, ctype)
            return

        if path == "/api/status":
            data = db.load_db()
            body, status, ctype = _json(
                {
                    "events": len(data["events"]),
                    "comments": len(data["comments"]),
                    "db_path": str(db.db_path()),
                }
            )
            self._send(body, status, ctype)
            return

        if path == "/api/download-status":
            with _download_lock:
                body, status, ctype = _json(dict(DOWNLOAD_STATE))
            self._send(body, status, ctype)
            return

        self._send(b"Not Found", 404)

    # ---------- POST ----------
    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        payload = self._read_body()

        if path == "/api/events":
            title = (payload.get("title") or "").strip()
            if not title:
                body, status, ctype = _json({"error": "标题不能为空"}, 400)
                self._send(body, status, ctype)
                return
            area = payload.get("area")
            if area not in ("domestic", "international"):
                area = "domestic"
            data = db.load_db()
            event = {
                "id": db.new_id("ev"),
                "title": title,
                "area": area,
                "source": (payload.get("source") or "手动添加").strip() or "手动添加",
                "url": (payload.get("url") or "").strip(),
                "date": (payload.get("date") or "").strip(),
                "summary": (payload.get("summary") or "").strip(),
                "added_at": db.now_iso(),
            }
            data["events"].append(event)
            db.save_db(data)
            body, status, ctype = _json({"event": event})
            self._send(body, status, ctype)
            return

        if path == "/api/comments":
            event_id = (payload.get("event_id") or "").strip()
            text = (payload.get("text") or "").strip()
            data = db.load_db()
            event = next((e for e in data["events"] if e["id"] == event_id), None)
            if event is None:
                body, status, ctype = _json({"error": "事件不存在"}, 404)
                self._send(body, status, ctype)
                return
            if not text:
                body, status, ctype = _json({"error": "评论不能为空"}, 400)
                self._send(body, status, ctype)
                return
            comment = {
                "id": db.new_id("cm"),
                "event_id": event_id,
                "text": text,
                "created_at": db.now_iso(),
                "want_discussion": False,
                "discussion": [],
            }
            data["comments"].append(comment)
            db.save_db(data)
            body, status, ctype = _json({"comment": comment})
            self._send(body, status, ctype)
            return

        if path == "/api/discuss":
            event_id = (payload.get("event_id") or "").strip()
            comment_id = (payload.get("comment_id") or "").strip()
            data = db.load_db()
            comment = next(
                (
                    c
                    for c in data["comments"]
                    if c["id"] == comment_id and c.get("event_id") == event_id
                ),
                None,
            )
            if comment is None:
                body, status, ctype = _json({"error": "评论不存在"}, 404)
                self._send(body, status, ctype)
                return
            comment["want_discussion"] = True
            db.save_db(data)
            body, status, ctype = _json({"ok": True})
            self._send(body, status, ctype)
            return

        if path == "/api/download":
            try:
                count = max(1, min(30, int(payload.get("count") or 5)))
            except (TypeError, ValueError):
                count = 5
            ok, message = start_download(count)
            body, status, ctype = _json(
                {"ok": ok, "message": message}, 200 if ok else 409
            )
            self._send(body, status, ctype)
            return

        if path == "/api/refresh":
            try:
                try:
                    from . import sync_events as update_events
                except ImportError:
                    import sync_events as update_events

                limit = int(payload.get("limit") or 8)
                result = update_events.sync_events(limit=limit)
                body, status, ctype = _json(
                    {
                        "added": [e["title"] for e in result["added"]],
                        "added_count": len(result["added"]),
                        "errors": result["errors"],
                        "total": result["total"],
                    }
                )
                self._send(body, status, ctype)
            except Exception as exc:  # noqa: BLE001
                body, status, ctype = _json({"error": f"同步失败：{exc}"}, 500)
                self._send(body, status, ctype)
            return

        body, status, ctype = _json({"error": "Not Found"}, 404)
        self._send(body, status, ctype)


def main() -> int:
    ap = argparse.ArgumentParser(description="事件中心本地服务")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()

    db.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("=" * 56)
    print("  事件中心已启动")
    print(f"  请用浏览器打开：http://{args.host}:{args.port}")
    print(f"  数据文件：{db.DB_PATH}")
    print("  按 Ctrl+C 停止服务")
    print("=" * 56)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
