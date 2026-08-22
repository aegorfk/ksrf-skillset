"""Local, resumable evidence store for judicial-meaning research runs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import unicodedata
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse


_RETRYABLE_STATES = {
    "retryable_error",
    "blocked",
    "http_error",
    "invalid_structure",
    "ambiguous_empty",
}
_SUCCESS_STATES = {"success_empty", "success_nonempty"}
_TERMINAL_INCOMPLETE_STATES = {"terminal_error", "pagination_unresolved", "unavailable"}
_SOURCE_SUCCESS_STATES = {"full_text", "card_indexed"}
_SOURCE_RETRYABLE_STATES = {"retryable_error", "blocked"}
_SOURCE_TERMINAL_STATES = {"official_page_no_text", "card_only", "missing", "terminal_error"}
_EXPORTABLE_TABLES = {"runs", "listing_tasks", "source_tasks", "sources", "snapshots", "events"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()


class RunStore:
    """SQLite-backed run state with content-addressed raw snapshots.

    A run can be stopped at any point.  Successful listing segments stay
    successful, while failed and abandoned claims remain separately visible
    and can be retried without relabelling them as empty results.
    """

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / "objects" / "sha256").mkdir(parents=True, exist_ok=True)
        (self.workspace / "exports").mkdir(parents=True, exist_ok=True)
        self.db_path = self.workspace / "corpus.sqlite3"
        self.conn = sqlite3.connect(self.db_path, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = FULL")
        self._create_schema()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                plan_sha256 TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'planned'
            );

            CREATE TABLE IF NOT EXISTS listing_tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                court_code TEXT NOT NULL,
                listing_date TEXT NOT NULL,
                segment_key TEXT NOT NULL,
                page_url TEXT,
                parent_task_id INTEGER REFERENCES listing_tasks(task_id),
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at TEXT,
                claimed_at TEXT,
                finished_at TEXT,
                http_status INTEGER,
                row_count INTEGER,
                error_code TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(run_id, segment_key)
            );

            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                canonical_url TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                object_path TEXT NOT NULL,
                byte_length INTEGER NOT NULL,
                http_status INTEGER,
                content_type TEXT,
                UNIQUE(snapshot_id, run_id)
            );

            CREATE TABLE IF NOT EXISTS source_tasks (
                source_task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                court_code TEXT NOT NULL,
                kind TEXT NOT NULL CHECK(kind IN ('card', 'doc')),
                canonical_url TEXT NOT NULL,
                source_key TEXT NOT NULL,
                chain_key TEXT,
                discovered_from_task_id INTEGER REFERENCES listing_tasks(task_id),
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at TEXT,
                claimed_at TEXT,
                finished_at TEXT,
                http_status INTEGER,
                error_code TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(run_id, source_key)
            );

            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                snapshot_id INTEGER REFERENCES snapshots(snapshot_id),
                court_code TEXT NOT NULL,
                kind TEXT NOT NULL,
                canonical_url TEXT NOT NULL,
                case_uid TEXT,
                document_id TEXT NOT NULL,
                chain_id TEXT NOT NULL,
                raw_sha256 TEXT NOT NULL,
                text_sha256 TEXT,
                text TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT REFERENCES runs(run_id) ON DELETE CASCADE,
                task_id INTEGER REFERENCES listing_tasks(task_id) ON DELETE CASCADE,
                event_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_listing_claim
                ON listing_tasks(run_id, status, next_attempt_at, listing_date, court_code);
            CREATE INDEX IF NOT EXISTS idx_sources_document
                ON sources(run_id, document_id);
            CREATE INDEX IF NOT EXISTS idx_sources_chain
                ON sources(run_id, chain_id);
            CREATE INDEX IF NOT EXISTS idx_events_run
                ON events(run_id, event_id);
            CREATE INDEX IF NOT EXISTS idx_source_task_claim
                ON source_tasks(run_id, status, next_attempt_at, source_task_id);
            """
        )
        source_task_columns = {
            str(row[1]) for row in self.conn.execute("PRAGMA table_info(source_tasks)").fetchall()
        }
        if "chain_key" not in source_task_columns:
            self.conn.execute("ALTER TABLE source_tasks ADD COLUMN chain_key TEXT")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "RunStore":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def _event(
        self,
        *,
        run_id: str | None,
        task_id: int | None,
        event_type: str,
        reason_code: str,
        payload: dict[str, Any] | None = None,
        event_at: str | None = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO events(run_id, task_id, event_at, event_type, reason_code, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                task_id,
                event_at or _utc_now(),
                event_type,
                reason_code,
                _canonical_json(payload or {}),
            ),
        )

    def create_run(self, plan: dict[str, Any]) -> str:
        plan_json = _canonical_json(plan)
        plan_sha256 = str(plan.get("plan_sha256") or _sha256(plan_json.encode("utf-8")))
        run_id = uuid.uuid4().hex
        created_at = _utc_now()
        with self.conn:
            self.conn.execute(
                "INSERT INTO runs(run_id, created_at, plan_json, plan_sha256) VALUES (?, ?, ?, ?)",
                (run_id, created_at, plan_json, plan_sha256),
            )
            self._event(
                run_id=run_id,
                task_id=None,
                event_type="run",
                reason_code="run_created",
                payload={"plan_sha256": plan_sha256},
                event_at=created_at,
            )
        return run_id

    def latest_run_id(self) -> str | None:
        row = self.conn.execute(
            "SELECT run_id FROM runs ORDER BY created_at DESC, run_id DESC LIMIT 1"
        ).fetchone()
        return str(row["run_id"]) if row is not None else None

    def put_object(self, raw: bytes) -> Path:
        """Store bytes once and return their path relative to the workspace."""

        digest = _sha256(raw)
        relative = Path("objects") / "sha256" / digest[:2] / digest
        target = self.workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            # A matching digest is the identity.  Check size to catch an
            # interrupted or externally corrupted object instead of masking it.
            if target.stat().st_size != len(raw):
                raise RuntimeError(f"content-addressed object is corrupt: {relative}")
        return relative

    def seed_calendar(
        self,
        run_id: str,
        court_codes: Iterable[str],
        start_date: str,
        end_date: str,
    ) -> int:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        if end < start:
            raise ValueError("end_date must be on or after start_date")
        courts = sorted({str(code).strip() for code in court_codes if str(code).strip()})
        if not courts:
            raise ValueError("at least one court code is required")
        created_at = _utc_now()
        inserted = 0
        with self.conn:
            day = start
            while day <= end:
                day_text = day.isoformat()
                for court_code in courts:
                    cursor = self.conn.execute(
                        """
                        INSERT OR IGNORE INTO listing_tasks(
                            run_id, court_code, listing_date, segment_key, created_at
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (run_id, court_code, day_text, f"{court_code}:{day_text}:root", created_at),
                    )
                    if cursor.rowcount:
                        inserted += 1
                        self._event(
                            run_id=run_id,
                            task_id=cursor.lastrowid,
                            event_type="listing",
                            reason_code="listing_seeded",
                            payload={"court_code": court_code, "listing_date": day_text},
                            event_at=created_at,
                        )
                day += timedelta(days=1)
        return inserted

    def claim_next_listing(self, run_id: str, now: str | None = None) -> dict[str, Any] | None:
        claimed_at = now or _utc_now()
        placeholders = ",".join("?" for _ in _RETRYABLE_STATES)
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            row = self.conn.execute(
                f"""
                SELECT * FROM listing_tasks
                WHERE run_id = ? AND (
                    status = 'pending'
                    OR (status IN ({placeholders}) AND next_attempt_at IS NOT NULL
                        AND next_attempt_at <= ?)
                )
                ORDER BY CASE WHEN status = 'pending' THEN 0 ELSE 1 END,
                         listing_date, court_code, task_id
                LIMIT 1
                """,
                (run_id, *sorted(_RETRYABLE_STATES), claimed_at),
            ).fetchone()
            if row is None:
                self.conn.commit()
                return None
            task_id = int(row["task_id"])
            attempts = int(row["attempts"]) + 1
            self.conn.execute(
                """
                UPDATE listing_tasks
                SET status='fetching', attempts=?, claimed_at=?, finished_at=NULL,
                    error_code=NULL, error_message=NULL
                WHERE task_id=?
                """,
                (attempts, claimed_at, task_id),
            )
            self._event(
                run_id=run_id,
                task_id=task_id,
                event_type="listing",
                reason_code="listing_claimed",
                payload={"attempt": attempts},
                event_at=claimed_at,
            )
            claimed = self.conn.execute(
                "SELECT * FROM listing_tasks WHERE task_id=?", (task_id,)
            ).fetchone()
            self.conn.commit()
            return dict(claimed) if claimed is not None else None
        except Exception:
            self.conn.rollback()
            raise

    def get_listing(self, task_id: int) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM listing_tasks WHERE task_id=?", (task_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown listing task: {task_id}")
        return dict(row)

    def finish_listing(
        self,
        task_id: int,
        status: str,
        http_status: int | None,
        *,
        row_count: int | None = None,
    ) -> None:
        if status not in _SUCCESS_STATES:
            raise ValueError(f"not a successful terminal listing status: {status}")
        finished_at = _utc_now()
        with self.conn:
            current = self.conn.execute(
                "SELECT run_id FROM listing_tasks WHERE task_id=?", (task_id,)
            ).fetchone()
            if current is None:
                raise KeyError(f"unknown listing task: {task_id}")
            self.conn.execute(
                """
                UPDATE listing_tasks
                SET status=?, http_status=?, row_count=?, finished_at=?, next_attempt_at=NULL,
                    error_code=NULL, error_message=NULL
                WHERE task_id=?
                """,
                (status, http_status, row_count, finished_at, task_id),
            )
            self._event(
                run_id=current["run_id"],
                task_id=task_id,
                event_type="listing",
                reason_code=status,
                payload={"http_status": http_status, "row_count": row_count},
                event_at=finished_at,
            )

    def fail_listing(self, task_id: int, status: str, reason: str) -> None:
        if status not in _RETRYABLE_STATES:
            raise ValueError(f"not a retryable listing status: {status}")
        failed_at = _utc_now()
        with self.conn:
            current = self.conn.execute(
                "SELECT run_id, attempts FROM listing_tasks WHERE task_id=?", (task_id,)
            ).fetchone()
            if current is None:
                raise KeyError(f"unknown listing task: {task_id}")
            delay_seconds = min(3600, 60 * (2 ** max(0, int(current["attempts"]) - 1)))
            next_attempt_at = (
                _parse_time(failed_at) + timedelta(seconds=delay_seconds)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            self.conn.execute(
                """
                UPDATE listing_tasks
                SET status=?, error_code=?, error_message=?, finished_at=?, next_attempt_at=?
                WHERE task_id=?
                """,
                (status, status, reason, failed_at, next_attempt_at, task_id),
            )
            self._event(
                run_id=current["run_id"],
                task_id=task_id,
                event_type="listing",
                reason_code=status,
                payload={"reason": reason, "next_attempt_at": next_attempt_at},
                event_at=failed_at,
            )

    def terminate_listing(self, task_id: int, status: str, reason: str) -> None:
        if status not in _TERMINAL_INCOMPLETE_STATES:
            raise ValueError(f"not an incomplete terminal listing status: {status}")
        finished_at = _utc_now()
        with self.conn:
            current = self.conn.execute(
                "SELECT run_id FROM listing_tasks WHERE task_id=?", (task_id,)
            ).fetchone()
            if current is None:
                raise KeyError(f"unknown listing task: {task_id}")
            self.conn.execute(
                """
                UPDATE listing_tasks
                SET status=?, error_code=?, error_message=?, finished_at=?, next_attempt_at=NULL
                WHERE task_id=?
                """,
                (status, status, reason, finished_at, task_id),
            )
            self._event(
                run_id=current["run_id"],
                task_id=task_id,
                event_type="listing",
                reason_code=status,
                payload={"reason": reason},
                event_at=finished_at,
            )

    def recover_stale_claims(self, older_than: str) -> int:
        """Return abandoned fetching claims to pending and leave audit events."""

        recovered_at = _utc_now()
        with self.conn:
            rows = self.conn.execute(
                """
                SELECT task_id, run_id, claimed_at FROM listing_tasks
                WHERE status='fetching' AND claimed_at IS NOT NULL AND claimed_at < ?
                ORDER BY task_id
                """,
                (older_than,),
            ).fetchall()
            for row in rows:
                self.conn.execute(
                    """
                    UPDATE listing_tasks
                    SET status='pending', claimed_at=NULL, next_attempt_at=NULL,
                        error_code='stale_claim_recovered',
                        error_message='Fetching claim was abandoned and made resumable'
                    WHERE task_id=?
                    """,
                    (row["task_id"],),
                )
                self._event(
                    run_id=row["run_id"],
                    task_id=row["task_id"],
                    event_type="recovery",
                    reason_code="stale_claim_recovered",
                    payload={"previous_claimed_at": row["claimed_at"], "cutoff": older_than},
                    event_at=recovered_at,
                )
        return len(rows)

    def discover_source_task(
        self,
        run_id: str,
        *,
        court_code: str,
        kind: str,
        canonical_url: str,
        source_key: str,
        chain_key: str | None = None,
        discovered_from_task_id: int | None = None,
    ) -> bool:
        if kind not in {"card", "doc"}:
            raise ValueError("source task kind must be card or doc")
        created_at = _utc_now()
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO source_tasks(
                    run_id, court_code, kind, canonical_url, source_key, chain_key,
                    discovered_from_task_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, source_key) DO UPDATE SET
                    chain_key=COALESCE(source_tasks.chain_key, excluded.chain_key)
                """,
                (
                    run_id,
                    court_code,
                    kind,
                    canonical_url,
                    source_key,
                    chain_key,
                    discovered_from_task_id,
                    created_at,
                ),
            )
            if cursor.rowcount:
                self._event(
                    run_id=run_id,
                    task_id=discovered_from_task_id,
                    event_type="source_task",
                    reason_code="source_discovered",
                    payload={"source_task_id": cursor.lastrowid, "kind": kind, "url": canonical_url},
                    event_at=created_at,
                )
                return True
        return False

    def claim_next_source(self, run_id: str, now: str | None = None) -> dict[str, Any] | None:
        claimed_at = now or _utc_now()
        placeholders = ",".join("?" for _ in _SOURCE_RETRYABLE_STATES)
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            row = self.conn.execute(
                f"""
                SELECT * FROM source_tasks
                WHERE run_id=? AND (
                    status='pending'
                    OR (status IN ({placeholders}) AND next_attempt_at IS NOT NULL
                        AND next_attempt_at <= ?)
                )
                ORDER BY CASE WHEN status='pending' THEN 0 ELSE 1 END, source_task_id
                LIMIT 1
                """,
                (run_id, *sorted(_SOURCE_RETRYABLE_STATES), claimed_at),
            ).fetchone()
            if row is None:
                self.conn.commit()
                return None
            attempts = int(row["attempts"]) + 1
            self.conn.execute(
                """
                UPDATE source_tasks
                SET status='fetching', attempts=?, claimed_at=?, finished_at=NULL,
                    error_code=NULL, error_message=NULL
                WHERE source_task_id=?
                """,
                (attempts, claimed_at, row["source_task_id"]),
            )
            claimed = self.conn.execute(
                "SELECT * FROM source_tasks WHERE source_task_id=?", (row["source_task_id"],)
            ).fetchone()
            self.conn.commit()
            return dict(claimed) if claimed is not None else None
        except Exception:
            self.conn.rollback()
            raise

    def finish_source_task(
        self,
        source_task_id: int,
        status: str,
        http_status: int | None,
        *,
        error_message: str | None = None,
    ) -> None:
        allowed = _SOURCE_SUCCESS_STATES | _SOURCE_TERMINAL_STATES
        if status not in allowed:
            raise ValueError(f"invalid terminal source task status: {status}")
        finished_at = _utc_now()
        with self.conn:
            current = self.conn.execute(
                "SELECT run_id, discovered_from_task_id FROM source_tasks WHERE source_task_id=?",
                (source_task_id,),
            ).fetchone()
            if current is None:
                raise KeyError(f"unknown source task: {source_task_id}")
            self.conn.execute(
                """
                UPDATE source_tasks
                SET status=?, http_status=?, finished_at=?, next_attempt_at=NULL,
                    error_code=?, error_message=?
                WHERE source_task_id=?
                """,
                (
                    status,
                    http_status,
                    finished_at,
                    None if status in _SOURCE_SUCCESS_STATES else status,
                    error_message,
                    source_task_id,
                ),
            )
            self._event(
                run_id=current["run_id"],
                task_id=current["discovered_from_task_id"],
                event_type="source_task",
                reason_code=status,
                payload={"source_task_id": source_task_id, "http_status": http_status},
                event_at=finished_at,
            )

    def fail_source_task(self, source_task_id: int, status: str, reason: str) -> None:
        if status not in _SOURCE_RETRYABLE_STATES:
            raise ValueError(f"invalid retryable source task status: {status}")
        failed_at = _utc_now()
        with self.conn:
            current = self.conn.execute(
                "SELECT run_id, attempts, discovered_from_task_id FROM source_tasks WHERE source_task_id=?",
                (source_task_id,),
            ).fetchone()
            if current is None:
                raise KeyError(f"unknown source task: {source_task_id}")
            delay_seconds = min(3600, 60 * (2 ** max(0, int(current["attempts"]) - 1)))
            next_attempt_at = (
                _parse_time(failed_at) + timedelta(seconds=delay_seconds)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            self.conn.execute(
                """
                UPDATE source_tasks
                SET status=?, error_code=?, error_message=?, finished_at=?, next_attempt_at=?
                WHERE source_task_id=?
                """,
                (status, status, reason, failed_at, next_attempt_at, source_task_id),
            )
            self._event(
                run_id=current["run_id"],
                task_id=current["discovered_from_task_id"],
                event_type="source_task",
                reason_code=status,
                payload={"source_task_id": source_task_id, "reason": reason},
                event_at=failed_at,
            )

    def recover_stale_source_claims(self, older_than: str) -> int:
        recovered_at = _utc_now()
        with self.conn:
            rows = self.conn.execute(
                """
                SELECT source_task_id, run_id, discovered_from_task_id, claimed_at
                FROM source_tasks
                WHERE status='fetching' AND claimed_at IS NOT NULL AND claimed_at < ?
                ORDER BY source_task_id
                """,
                (older_than,),
            ).fetchall()
            for row in rows:
                self.conn.execute(
                    """
                    UPDATE source_tasks
                    SET status='pending', claimed_at=NULL, next_attempt_at=NULL,
                        error_code='stale_claim_recovered', error_message='Source claim recovered'
                    WHERE source_task_id=?
                    """,
                    (row["source_task_id"],),
                )
                self._event(
                    run_id=row["run_id"],
                    task_id=row["discovered_from_task_id"],
                    event_type="recovery",
                    reason_code="stale_source_claim_recovered",
                    payload={"source_task_id": row["source_task_id"], "cutoff": older_than},
                    event_at=recovered_at,
                )
        return len(rows)

    def source_task_report(self, run_id: str) -> dict[str, Any]:
        rows = self.conn.execute(
            "SELECT status, COUNT(*) AS count FROM source_tasks WHERE run_id=? GROUP BY status",
            (run_id,),
        ).fetchall()
        counts = {str(row["status"]): int(row["count"]) for row in rows}
        all_states = _SOURCE_SUCCESS_STATES | _SOURCE_RETRYABLE_STATES | _SOURCE_TERMINAL_STATES | {"pending", "fetching"}
        for status in sorted(all_states):
            counts.setdefault(status, 0)
        total = sum(counts.values())
        successful = sum(counts[state] for state in _SOURCE_SUCCESS_STATES)
        return {
            **counts,
            "total": total,
            "successful": successful,
            "unresolved": total - successful,
        }

    def coverage_report(self, run_id: str) -> dict[str, Any]:
        rows = self.conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM listing_tasks WHERE run_id=? GROUP BY status ORDER BY status
            """,
            (run_id,),
        ).fetchall()
        counts = {str(row["status"]): int(row["count"]) for row in rows}
        for status in sorted(
            _SUCCESS_STATES | _RETRYABLE_STATES | _TERMINAL_INCOMPLETE_STATES | {"pending", "fetching"}
        ):
            counts.setdefault(status, 0)
        total = sum(counts.values())
        successful = sum(counts[status] for status in _SUCCESS_STATES)
        closed = total > 0 and successful == total
        return {
            **counts,
            "total_segments": total,
            "successful_segments": successful,
            "unresolved_segments": total - successful,
            "closed_official_population_observed": closed,
            "population_status": (
                "closed_official_population_observed" if closed else "observed_corpus_only"
            ),
        }

    def _derive_chain_id(
        self,
        *,
        court_code: str,
        case_uid: str | None,
        canonical_url: str,
        document_id: str,
        chain_key: str | None,
    ) -> str:
        identity = _normalise_text(chain_key or case_uid or "").casefold()
        if not identity:
            query = parse_qs(urlparse(canonical_url).query)
            url_uid = (query.get("case_uid") or [""])[0]
            if url_uid:
                identity = _normalise_text(url_uid).casefold()
            else:
                case_id = (query.get("case_id") or [""])[0]
                delo_id = (query.get("delo_id") or [""])[0]
                if case_id:
                    identity = f"case_id={case_id};delo_id={delo_id}"
        if not identity:
            # With no chain evidence, content identity is a conservative lower
            # bound: mirrored copies of the same act cannot inflate the count.
            identity = f"document={document_id}"
        payload = f"{court_code.strip().casefold()}\n{identity}".encode("utf-8")
        return f"chain-sha256:{_sha256(payload)}"

    def add_source(
        self,
        run_id: str,
        *,
        court_code: str,
        kind: str,
        canonical_url: str,
        raw: bytes,
        text: str = "",
        case_uid: str | None = None,
        chain_key: str | None = None,
        http_status: int | None = None,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        object_path = self.put_object(raw)
        raw_sha256 = _sha256(raw)
        normalised_text = _normalise_text(text)
        identity_bytes = normalised_text.encode("utf-8") if normalised_text else raw
        document_id = f"document-sha256:{_sha256(identity_bytes)}"
        text_sha256 = _sha256(normalised_text.encode("utf-8")) if normalised_text else None
        chain_id = self._derive_chain_id(
            court_code=court_code,
            case_uid=case_uid,
            canonical_url=canonical_url,
            document_id=document_id,
            chain_key=chain_key,
        )
        created_at = _utc_now()
        with self.conn:
            snapshot = self.conn.execute(
                """
                INSERT INTO snapshots(
                    run_id, canonical_url, captured_at, sha256, object_path, byte_length,
                    http_status, content_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    canonical_url,
                    created_at,
                    raw_sha256,
                    str(object_path),
                    len(raw),
                    http_status,
                    content_type,
                ),
            )
            source = self.conn.execute(
                """
                INSERT INTO sources(
                    run_id, snapshot_id, court_code, kind, canonical_url, case_uid,
                    document_id, chain_id, raw_sha256, text_sha256, text,
                    metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    snapshot.lastrowid,
                    court_code,
                    kind,
                    canonical_url,
                    case_uid,
                    document_id,
                    chain_id,
                    raw_sha256,
                    text_sha256,
                    text,
                    _canonical_json(metadata or {}),
                    created_at,
                ),
            )
            source_id = int(source.lastrowid)
            self._event(
                run_id=run_id,
                task_id=None,
                event_type="source",
                reason_code="source_captured",
                payload={
                    "source_id": source_id,
                    "document_id": document_id,
                    "chain_id": chain_id,
                    "canonical_url": canonical_url,
                },
                event_at=created_at,
            )
        return {
            "source_id": source_id,
            "snapshot_id": int(snapshot.lastrowid),
            "document_id": document_id,
            "chain_id": chain_id,
            "raw_sha256": raw_sha256,
            "object_path": str(object_path),
        }

    def independence_counts(self, run_id: str) -> dict[str, int]:
        row = self.conn.execute(
            """
            SELECT COUNT(*) AS sources,
                   COUNT(DISTINCT document_id) AS documents,
                   COUNT(DISTINCT chain_id) AS case_chains
            FROM sources WHERE run_id=? AND kind IN ('card', 'doc')
            """,
            (run_id,),
        ).fetchone()
        return {
            "sources": int(row["sources"]),
            "documents": int(row["documents"]),
            "case_chains": int(row["case_chains"]),
        }

    def export_jsonl(self, table: str) -> Path:
        """Export an audit table with stable columns, order and JSON encoding."""

        if table not in _EXPORTABLE_TABLES:
            raise ValueError(f"unsupported export table: {table}")
        schema = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        primary = [str(row["name"]) for row in schema if int(row["pk"])]
        columns = [str(row["name"]) for row in schema]
        order = primary or columns
        rows = self.conn.execute(
            f"SELECT * FROM {table} ORDER BY " + ", ".join(order)
        ).fetchall()
        output = self.workspace / "exports" / f"{table}.jsonl"
        payload = "".join(
            _canonical_json({column: row[column] for column in columns}) + "\n" for row in rows
        )
        output.write_text(payload, encoding="utf-8", newline="\n")
        return output

    def export_case_chains(self, run_id: str) -> Path:
        """Export deterministic candidate case-chain groupings for human review.

        An official case UID is strong linkage evidence.  URL/content fallbacks
        remain explicit candidates and must not silently become human-approved
        independent chains.
        """

        rows = self.conn.execute(
            """
            SELECT source_id, court_code, kind, canonical_url, case_uid,
                   document_id, chain_id
            FROM sources
            WHERE run_id=? AND kind IN ('card', 'doc')
            ORDER BY chain_id, source_id
            """,
            (run_id,),
        ).fetchall()
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            chain_id = str(row["chain_id"])
            record = grouped.setdefault(
                chain_id,
                {
                    "schema_version": "1.0",
                    "run_id": run_id,
                    "chain_id": chain_id,
                    "source_ids": [],
                    "document_ids": [],
                    "court_codes": [],
                    "kinds": [],
                    "canonical_urls": [],
                    "case_uids": [],
                    "link_status": "needs_merge_split_review",
                    "review_status": "pending",
                },
            )
            record["source_ids"].append(int(row["source_id"]))
            record["document_ids"].append(str(row["document_id"]))
            record["court_codes"].append(str(row["court_code"]))
            record["kinds"].append(str(row["kind"]))
            record["canonical_urls"].append(str(row["canonical_url"]))
            if row["case_uid"]:
                record["case_uids"].append(str(row["case_uid"]))

        for record in grouped.values():
            for field in (
                "source_ids",
                "document_ids",
                "court_codes",
                "kinds",
                "canonical_urls",
                "case_uids",
            ):
                record[field] = sorted(set(record[field]))
            if len(record["case_uids"]) == 1:
                record["link_status"] = "official_case_uid_candidate"

        output = self.workspace / "exports" / "case-chains.jsonl"
        payload = "".join(
            _canonical_json(grouped[chain_id]) + "\n" for chain_id in sorted(grouped)
        )
        output.write_text(payload, encoding="utf-8", newline="\n")
        return output
