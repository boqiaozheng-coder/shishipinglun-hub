"""事件中心本地数据库（JSON 文件存储，单用户使用）。"""

from __future__ import annotations

import copy
import datetime as dt
import json
import shutil
import sys
import threading
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
    ts = dt.datetime.now().strftime("%y%m%d%H%M%S")
    return f"{prefix}_{ts}_{abs(hash(prefix + ts + str(threading.get_ident()))) % 100000:05d}"


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
