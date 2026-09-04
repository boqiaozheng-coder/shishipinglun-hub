"""事件中心本地数据库（JSON 文件存储，单用户使用）。"""

from __future__ import annotations

import copy
import datetime as dt
import json
import shutil
import sys
import threading
import uuid
from pathlib import Path

_EMPTY = {"events": [], "comments": []}
_lock = threading.Lock()


def _user_data_dir() -> Path:
    """软件的用户数据放到系统标准位置，打包成 .app 后也可写。"""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ShishipinglunCenter"
    return Path.home() / ".shishipinglun-hub"


DATA_DIR = _user_data_dir()
DB_PATH = DATA_DIR / "database.json"
LEGACY_DB = Path(__file__).resolve().parent / "data" / "database.json"


def _migrate_legacy_data() -> None:
    """首次运行时，把仓库内置/历史数据库复制到用户数据目录。"""
    if DB_PATH.exists() or not LEGACY_DB.exists():
        return
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LEGACY_DB, DB_PATH)
    except OSError:
        pass


_migrate_legacy_data()


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def repair_duplicate_ids(data: dict) -> int:
    """修复历史数据中缺失或重复的记录 ID，返回修复数量。

    旧版 ID 只精确到秒，同一批同步的事件会得到完全相同的 ID，导致
    点击任意卡片都打开该批第一条。保留每组的首个 ID，其余记录换成
    UUID；已有评论仍继续关联首个记录，避免猜测其原始归属。
    """
    repaired = 0
    for collection, prefix in (("events", "ev"), ("comments", "cm")):
        seen: set[str] = set()
        for record in data.get(collection, []):
            record_id = record.get("id")
            if not isinstance(record_id, str) or not record_id or record_id in seen:
                record_id = new_id(prefix)
                while record_id in seen:
                    record_id = new_id(prefix)
                record["id"] = record_id
                repaired += 1
            seen.add(record_id)
    return repaired


def load_db() -> dict:
    with _lock:
        if not DB_PATH.exists():
            return copy.deepcopy(_EMPTY)
        try:
            data = json.loads(DB_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        data.setdefault("events", [])
        data.setdefault("comments", [])
        return data


def save_db(db: dict) -> None:
    with _lock:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = DB_PATH.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(DB_PATH)


def db_path() -> Path:
    return DB_PATH
