"""事件同步：从国内外新闻源抓取最新事件标题写入事件中心数据库。

当前源：
  - 人民网·时政频道（国内）
  - 人民网·国际频道（国际，中文）
  - 纽约时报 World RSS（国际，英文）

用法：
  python3 update_events.py                 # 每个源取 8 条
  python3 update_events.py --limit 15      # 每个源取 15 条
  python3 update_events.py --sources people,nyt
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

try:
    from . import db
except ImportError:  # 直接以脚本方式运行 python3 sync_events.py 时
    import db

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)

FEEDS = {
    "people-domestic": {
        "area": "domestic",
        "source": "人民网·时政",
        "url": "http://politics.people.com.cn/GB/1024/index.html",
        "pattern": re.compile(r"/n1/20\d{2}/\d{4}/c1001-\d+\.html"),
    },
    "people-world": {
        "area": "international",
        "source": "人民网·国际",
        "url": "http://world.people.com.cn/",
        "pattern": re.compile(r"/n1/20\d{2}/\d{4}/c1002-\d+\.html"),
    },
    "nyt-world": {
        "area": "international",
        "source": "纽约时报·World",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "pattern": None,
    },
}


def _get(session: requests.Session, url: str, timeout: int = 25) -> requests.Response:
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp


def _url_date(href: str) -> str:
    m = re.search(r"/20(\d{2})/(\d{2})(\d{2})/", href) or re.search(
        r"/20(\d{2})(\d{2})(\d{2})/", href
    )
    if not m:
        return dt.date.today().isoformat()
    y = 2000 + int(m.group(1))
    try:
        return dt.date(y, int(m.group(2)), int(m.group(3))).isoformat()
    except ValueError:
        return dt.date.today().isoformat()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def fetch_people_list(session, feed, limit: int) -> list[dict]:
    resp = _get(session, feed["url"])
    if not resp.encoding or resp.encoding.lower() in ("iso-8859-1", "us-ascii"):
        resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    out: list[dict] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(feed["url"], a["href"])
        if not feed["pattern"].search(href):
            continue
        title = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip(" \u3000")
        if not title or len(title) < 5:
            continue
        if href in seen:
            continue
        seen.add(href)
        out.append(
            {
                "title": title,
                "area": feed["area"],
                "source": feed["source"],
                "url": href,
                "date": _url_date(href),
            }
        )

    # 人民网页面的 DOM 顺序并不总是时间顺序。例如国际频道可能先放置
    # 昨日的置顶稿件，再列出今天的最新稿件。必须先收集候选并按日期
    # 排序，再截取数量；否则 limit 较小时会把当天新闻全部漏掉。
    out.sort(key=lambda item: item["date"], reverse=True)
    return out[:limit]


def _xml_child(el: ET.Element, *names: str) -> ET.Element | None:
    for child in el:
        if _local_name(child.tag) in names:
            return child
    return None


def fetch_nyt_world(session, feed, limit: int) -> list[dict]:
    resp = _get(session, feed["url"])
    root = ET.fromstring(resp.text)
    out: list[dict] = []
    for entry in root.iter():
        if _local_name(entry.tag) not in ("item", "entry"):
            continue
        link_el = _xml_child(entry, "link")
        link = ""
        if link_el is not None:
            link = (link_el.get("href") or link_el.text or "").strip()
        if not link or "/video/" in link:
            continue
        title_el = _xml_child(entry, "title")
        title = re.sub(r"\s+", " ", title_el.text or "").strip()
        if not title:
            continue
        pub = _xml_child(entry, "pubDate", "published", "updated")
        date = dt.date.today().isoformat()
        if pub is not None and pub.text:
            m = re.search(r"(\d{1,2}) (\w{3}) (\d{4})", pub.text)
            if m:
                try:
                    date = dt.datetime.strptime(
                        f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %b %Y"
                    ).date().isoformat()
                except ValueError:
                    pass
        out.append(
            {
                "title": title,
                "area": feed["area"],
                "source": feed["source"],
                "url": link,
                "date": date,
            }
        )
        if len(out) >= limit:
            break
    return out


FETCHERS = {
    "people-domestic": fetch_people_list,
    "people-world": fetch_people_list,
    "nyt-world": fetch_nyt_world,
}


def sync_events(limit: int = 8, source_keys: list[str] | None = None) -> dict:
    """抓取新事件并入库存档，返回新增条数等摘要。"""
    source_keys = source_keys or list(FEEDS)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7"})
    data = db.load_db()
    existing = {e["url"] for e in data["events"] if e.get("url")}
    added: list[dict] = []
    errors: list[str] = []
    for key in source_keys:
        feed = FEEDS.get(key)
        if not feed:
            errors.append(f"未知源：{key}")
            continue
        try:
            rows = FETCHERS[key](session, feed, limit)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{feed['source']} 抓取失败：{exc}")
            continue
        for row in rows:
            if row["url"] in existing:
                continue
            event = {
                "id": db.new_id("ev"),
                "title": row["title"],
                "area": row["area"],
                "source": row["source"],
                "url": row["url"],
                "date": row["date"],
                "summary": "",
                "added_at": db.now_iso(),
            }
            data["events"].append(event)
            existing.add(row["url"])
            added.append(event)
    db.save_db(data)
    return {"added": added, "errors": errors, "total": len(data["events"])}


def main() -> int:
    ap = argparse.ArgumentParser(description="更新事件中心数据库")
    ap.add_argument("--limit", type=int, default=8, help="每个源最多收录条数")
    ap.add_argument(
        "--sources",
        default=",".join(FEEDS),
        help="数据源，逗号分隔：" + ", ".join(FEEDS),
    )
    args = ap.parse_args()
    keys = [k.strip() for k in args.sources.split(",") if k.strip()]
    result = sync_events(limit=args.limit, source_keys=keys)
    print(f"本次新增 {len(result['added'])} 条，事件库共 {result['total']} 条")
    for ev in result["added"]:
        print(f"  [{ev['area']}] {ev['date']} {ev['title'][:50]}（{ev['source']}）")
    for err in result["errors"]:
        print("  !", err, file=sys.stderr)
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
