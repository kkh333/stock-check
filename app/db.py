from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Monitor:
    id: int
    url: str
    option_label: str
    email: str
    site: str
    meta: dict[str, Any]
    last_in_stock: bool | None
    last_summary: str | None
    last_checked_at: str | None
    last_error: str | None
    enabled: bool
    created_at: str


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS monitors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    option_label TEXT NOT NULL,
                    email TEXT NOT NULL,
                    site TEXT NOT NULL,
                    meta TEXT NOT NULL,
                    last_in_stock INTEGER,
                    last_summary TEXT,
                    last_checked_at TEXT,
                    last_error TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _row_to_monitor(self, row: sqlite3.Row) -> Monitor:
        return Monitor(
            id=row["id"],
            url=row["url"],
            option_label=row["option_label"],
            email=row["email"],
            site=row["site"],
            meta=json.loads(row["meta"]),
            last_in_stock=(
                None if row["last_in_stock"] is None else bool(row["last_in_stock"])
            ),
            last_summary=row["last_summary"],
            last_checked_at=row["last_checked_at"],
            last_error=row["last_error"],
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
        )

    def list_monitors(self) -> list[Monitor]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM monitors ORDER BY id DESC"
            ).fetchall()
        return [self._row_to_monitor(r) for r in rows]

    def get_monitor(self, monitor_id: int) -> Monitor | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM monitors WHERE id = ?", (monitor_id,)
            ).fetchone()
        return self._row_to_monitor(row) if row else None

    def add_monitor(
        self,
        *,
        url: str,
        option_label: str,
        email: str,
        site: str,
        meta: dict[str, Any],
    ) -> Monitor:
        now = _utc_now()
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO monitors (url, option_label, email, site, meta, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (url, option_label, email, site, json.dumps(meta, ensure_ascii=False), now),
            )
            mid = cur.lastrowid
        created = self.get_monitor(mid)
        assert created is not None
        return created

    def delete_monitor(self, monitor_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM monitors WHERE id = ?", (monitor_id,))
        return cur.rowcount > 0

    def set_enabled(self, monitor_id: int, enabled: bool) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE monitors SET enabled = ? WHERE id = ?",
                (1 if enabled else 0, monitor_id),
            )

    def update_check_result(
        self,
        monitor_id: int,
        *,
        in_stock: bool,
        summary: str,
        error: str | None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE monitors
                SET last_in_stock = ?, last_summary = ?, last_checked_at = ?, last_error = ?
                WHERE id = ?
                """,
                (
                    1 if in_stock else 0,
                    summary,
                    _utc_now(),
                    error,
                    monitor_id,
                ),
            )