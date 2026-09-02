"""轻量冒烟测试：不访问网络、不触碰真实用户数据。

运行：python3 -m tests.smoke_test
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


def test_db_roundtrip() -> None:
    from shishipinglun.events import db

    tmp = Path(tempfile.mkdtemp(prefix="sspl_test_"))
    db.DATA_DIR = tmp
    db.DB_PATH = tmp / "database.json"
    data = db.load_db()
    assert data == {"events": [], "comments": []}
    data["events"].append({"id": "ev_1", "title": "测试事件"})
    db.save_db(data)
    assert db.load_db()["events"][0]["title"] == "测试事件"
    print("✓ db 读写")


def test_imports() -> None:
    import shishipinglun.desktop  # noqa: F401
    import shishipinglun.downloader  # noqa: F401
    import shishipinglun.events.server  # noqa: F401
    import shishipinglun.events.sync_events  # noqa: F401

    print("✓ 模块导入")


def test_downloader_parser() -> None:
    from shishipinglun import downloader

    args = downloader.build_parser().parse_args(["--count", "3", "--format", "pdf"])
    assert args.count == 3 and args.format == "pdf"
    print("✓ 下载参数解析")


def test_static_files_exist() -> None:
    from shishipinglun.events import server

    assert (server.STATIC / "index.html").exists()
    assert (server.STATIC / "app.js").exists()
    print("✓ 前端静态文件")


def main() -> int:
    test_imports()
    test_downloader_parser()
    test_static_files_exist()
    test_db_roundtrip()
    print("全部通过 ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
