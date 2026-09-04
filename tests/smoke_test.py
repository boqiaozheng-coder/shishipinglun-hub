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


def test_ids_are_unique_and_legacy_duplicates_are_repaired() -> None:
    from shishipinglun.events import db

    generated = {db.new_id("ev") for _ in range(1000)}
    assert len(generated) == 1000

    data = {
        "events": [{"id": "legacy", "title": "第一条"}, {"id": "legacy", "title": "第二条"}],
        "comments": [{"id": "", "event_id": "legacy", "text": "评论"}],
    }
    assert db.repair_duplicate_ids(data) == 2
    assert data["events"][0]["id"] == "legacy"
    assert len({row["id"] for row in data["events"]}) == 2
    assert data["comments"][0]["id"].startswith("cm_")
    print("✓ 唯一 ID 与历史重复 ID 修复")


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


def test_people_feed_sorts_before_limiting() -> None:
    from shishipinglun.events import sync_events

    class Response:
        encoding = "utf-8"
        apparent_encoding = "utf-8"
        text = """
            <a href="/n1/2026/0903/c1002-1.html">昨日置顶新闻</a>
            <a href="/n1/2026/0902/c1002-2.html">更早新闻内容</a>
            <a href="/n1/2026/0904/c1002-3.html">今日最新新闻</a>
        """

        def raise_for_status(self) -> None:
            return None

    class Session:
        def get(self, url: str, timeout: int):
            return Response()

    feed = {
        "area": "international",
        "source": "测试源",
        "url": "http://example.com/",
        "pattern": sync_events.re.compile(r"/n1/20\d{2}/\d{4}/c1002-\d+\.html"),
    }
    rows = sync_events.fetch_people_list(Session(), feed, limit=2)
    assert [row["date"] for row in rows] == ["2026-09-04", "2026-09-03"]
    assert rows[0]["title"] == "今日最新新闻"
    print("✓ 人民网新闻先按日期排序再截取")


def test_event_list_sorts_by_news_date() -> None:
    from shishipinglun.events import server

    events = [
        {"title": "昨日补录", "date": "2026-09-03", "added_at": "2026-09-04T13:00:00+08:00"},
        {"title": "今日事件", "date": "2026-09-04", "added_at": "2026-09-04T12:00:00+08:00"},
        {"title": "今日稍后入库", "date": "2026-09-04", "added_at": "2026-09-04T12:30:00+08:00"},
    ]
    rows = sorted(events, key=server._event_sort_key, reverse=True)
    assert [row["title"] for row in rows] == ["今日稍后入库", "今日事件", "昨日补录"]
    print("✓ 事件列表按新闻日期排序")


def main() -> int:
    test_imports()
    test_downloader_parser()
    test_static_files_exist()
    test_people_feed_sorts_before_limiting()
    test_event_list_sorts_by_news_date()
    test_db_roundtrip()
    test_ids_are_unique_and_legacy_duplicates_are_repaired()
    print("全部通过 ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
