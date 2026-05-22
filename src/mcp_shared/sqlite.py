from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


def connect_sqlite(
    db_path: str | Path,
    *,
    timeout: float = 5.0,
    foreign_keys: bool = False,
) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=timeout)
    conn.row_factory = sqlite3.Row
    if foreign_keys:
        conn.execute("PRAGMA foreign_keys=ON")
    return conn


def fetch_one(
    db_path: str | Path,
    query: str,
    params: tuple[Any, ...],
    *,
    timeout: float = 5.0,
    foreign_keys: bool = False,
) -> sqlite3.Row | None:
    with closing(connect_sqlite(db_path, timeout=timeout, foreign_keys=foreign_keys)) as conn:
        return conn.execute(query, params).fetchone()


def fetch_all(
    db_path: str | Path,
    query: str,
    params: tuple[Any, ...],
    *,
    timeout: float = 5.0,
    foreign_keys: bool = False,
) -> list[sqlite3.Row]:
    with closing(connect_sqlite(db_path, timeout=timeout, foreign_keys=foreign_keys)) as conn:
        return list(conn.execute(query, params).fetchall())
