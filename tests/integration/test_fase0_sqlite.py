"""EPIC-2 SQLite industrialization tests (integration layer)."""

from __future__ import annotations

import threading
import time
from pathlib import Path


class TestSQLiteIndustrial:
    """EPIC-2: WAL, busy_timeout, foreign_keys and lookup indexes."""

    def _repo(self, tmp_path: Path):
        from soar_lab.infrastructure.persistence.sqlite_alert_repository import (
            SqliteAlertRepository,
        )

        return SqliteAlertRepository(db_path=str(tmp_path / "t.db"))

    def test_wal_and_busy_timeout_enabled(self, tmp_path: Path) -> None:

        repo = self._repo(tmp_path)
        with repo._connect() as conn:
            assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
            assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
            assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    def test_lookup_indexes_created(self, tmp_path: Path) -> None:
        import sqlite3

        repo = self._repo(tmp_path)
        with sqlite3.connect(repo.db_path) as conn:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                ).fetchall()
            }
        assert {
            "idx_alert_timestamp",
            "idx_alert_status",
            "idx_alert_severity",
        } <= names

    def test_concurrent_writer_waits_on_lock(self, tmp_path: Path) -> None:
        """busy_timeout: a second writer waits instead of failing fast."""
        import sqlite3

        repo = self._repo(tmp_path)
        holder = sqlite3.connect(repo.db_path)
        holder.execute("BEGIN IMMEDIATE")
        holder.execute("INSERT INTO alerts (alert_id, alert_type, severity) VALUES ('h','t','1')")

        outcome = []

        def writer() -> None:
            try:
                repo.store_alert({"alert_id": "w", "alert_type": "t", "severity": "2"})
                outcome.append("ok")
            except sqlite3.OperationalError as exc:
                outcome.append(str(exc))

        t = threading.Thread(target=writer)
        t.start()
        time.sleep(0.2)
        holder.commit()
        holder.close()
        t.join(timeout=8)
        assert outcome == ["ok"]
