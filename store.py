"""SQLite store: sent_reports(rcept_no PK, sent_at)."""
from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

LOGGER = logging.getLogger(__name__)

_env_db_path = os.environ.get("DB_PATH")
DEFAULT_DB_PATH = (
    Path(_env_db_path) if _env_db_path else Path(__file__).with_name("sent.db")
)

_CREATE_SQL = (
    "CREATE TABLE IF NOT EXISTS sent_reports ("
    "  rcept_no TEXT PRIMARY KEY,"
    "  sent_at  TEXT NOT NULL"
    ")"
)


def init(db_path: Path = DEFAULT_DB_PATH) -> None:
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(_CREATE_SQL)
        conn.commit()


def is_sent(rcept_no: str, db_path: Path = DEFAULT_DB_PATH) -> bool:
    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute(
            "SELECT 1 FROM sent_reports WHERE rcept_no = ?", (rcept_no,)
        ).fetchone()
    return row is not None


def mark_sent(rcept_no: str, db_path: Path = DEFAULT_DB_PATH) -> None:
    mark_bulk([rcept_no], db_path)


def mark_bulk(rcept_nos: Iterable[str], db_path: Path = DEFAULT_DB_PATH) -> int:
    payload = [(r, datetime.now(timezone.utc).isoformat()) for r in rcept_nos]
    if not payload:
        return 0
    with closing(sqlite3.connect(db_path)) as conn:
        cur = conn.executemany(
            "INSERT OR IGNORE INTO sent_reports(rcept_no, sent_at) VALUES (?, ?)",
            payload,
        )
        conn.commit()
        return cur.rowcount


def is_empty(db_path: Path = DEFAULT_DB_PATH) -> bool:
    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute("SELECT 1 FROM sent_reports LIMIT 1").fetchone()
    return row is None


def count(db_path: Path = DEFAULT_DB_PATH) -> int:
    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute("SELECT COUNT(*) FROM sent_reports").fetchone()
    return int(row[0])


if __name__ == "__main__":
    import tempfile

    logging.basicConfig(level=logging.INFO)
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "t.db"
        init(path)
        assert is_empty(path), "fresh db should be empty"
        assert not is_sent("A1", path)
        mark_sent("A1", path)
        assert is_sent("A1", path)
        assert not is_empty(path)
        inserted = mark_bulk(["A1", "B2", "C3"], path)
        assert inserted == 2, f"expected 2 (A1 duplicate), got {inserted}"
        assert is_sent("B2", path) and is_sent("C3", path)
        assert count(path) == 3
        print("store.py self-test OK")
