"""Reusable, public-only cassation corpus primitives.

The module is intentionally self-contained: it uses SQLite and the Python
standard library, keeps raw responses content-addressed, and never accepts
private applicant material into the reusable store.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import sqlite3
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urldefrag, urlparse, urlunparse


PUBLIC_SEED_ROLES = {
    "official_enumerator_observation",
    "official_user_seed",
    "official_authority_seed",
    "discovery_only",
}
PRIVATE_SEED_ROLE = "applicant_private"
FUNNEL_STAGES = (
    "enumerated",
    "card",
    "document_link",
    "payload_validated",
    "full_text_extracted",
    "indexed",
    "screened",
    "coded",
    "approved_independent_chain",
)
FUNNEL_ALIASES = {
    "discovered": "enumerated",
    "fetched": "document_link",
    "coding_eligible": "screened",
}
FUNNEL_FAILURES = {
    "blocked",
    "retryable_error",
    "official_page_no_text",
    "unextractable",
    "ocr_pending",
    "human_verification_pending",
}
TREATMENT_TYPES = {
    "applies",
    "follows",
    "distinguishes",
    "limits",
    "rejects",
    "supersedes",
    "unclear",
    "does_not_reach",
}
OFFICIAL_HOST_SUFFIXES = (
    "sudrf.ru",
    "vsrf.ru",
    "arbitr.ru",
    "ksrf.ru",
    "pravo.gov.ru",
)


class PublicCorpusError(ValueError):
    """Base error for an invalid public-corpus operation."""


class PrivacyBoundaryError(PublicCorpusError):
    """Private matter data was offered to the reusable public corpus."""


class SeedRoleError(PublicCorpusError):
    """A seed role is unknown or incompatible with reusable storage."""


class RunPinConflict(PublicCorpusError):
    """An immutable run was recreated with a different snapshot set."""


class FunnelTransitionError(PublicCorpusError):
    """A full-text funnel transition skipped required evidence stages."""


class TreatmentReviewError(PublicCorpusError):
    """A treatment edge did not satisfy quote-level human review."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _identifier(prefix: str, value: Any) -> str:
    return f"{prefix}-sha256:{_sha256(_canonical_json(value).encode('utf-8'))}"


def _normalise_text(value: str) -> str:
    normalised = unicodedata.normalize("NFKC", value).casefold().replace("ё", "е")
    return re.sub(r"\s+", " ", normalised).strip()


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise PublicCorpusError(f"Invalid ISO timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _canonical_public_url(value: str) -> str:
    parsed = urlparse(urldefrag(value.strip())[0])
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
        raise PrivacyBoundaryError("Reusable corpus accepts only public HTTP(S) source URLs.")
    if parsed.username is not None or parsed.password is not None:
        raise PrivacyBoundaryError("Reusable public URLs must not contain credentials.")
    hostname = parsed.hostname
    if hostname is None:
        raise PrivacyBoundaryError("Reusable public URLs require a public hostname.")
    try:
        host = hostname.encode("idna").decode("ascii").casefold().rstrip(".")
        port = parsed.port
    except (UnicodeError, ValueError) as exc:
        raise PrivacyBoundaryError("Reusable public URL has an invalid hostname or port.") from exc
    if not host or host == "localhost" or host.endswith(".localhost"):
        raise PrivacyBoundaryError("Localhost URLs cannot enter the reusable public corpus.")
    if "%" in host or re.fullmatch(r"(?:0x[0-9a-f]+|[0-9.]+)", host):
        try:
            canonical_numeric_address = ipaddress.ip_address(host)
        except ValueError:
            raise PrivacyBoundaryError(
                "Ambiguous numeric host literals cannot enter the reusable corpus."
            ) from None
    else:
        canonical_numeric_address = None
    try:
        address = canonical_numeric_address or ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_reserved
        or not address.is_global
    ):
        raise PrivacyBoundaryError("Non-public IP literals cannot enter the reusable corpus.")
    secret_keys = {
        "token",
        "accesstoken",
        "refreshtoken",
        "securitytoken",
        "apikey",
        "key",
        "secret",
        "clientsecret",
        "password",
        "passwd",
        "pwd",
        "auth",
        "authorization",
        "authorizationcode",
        "credential",
        "credentials",
        "session",
        "sessionid",
        "signature",
        "sig",
        "xamzcredential",
        "xamzsignature",
        "xamzsecuritytoken",
    }
    secret_suffixes = (
        "token",
        "secret",
        "password",
        "passwd",
        "credential",
        "credentials",
        "signature",
        "apikey",
    )
    for raw_key, _ in parse_qsl(parsed.query, keep_blank_values=True):
        key = re.sub(r"[^a-z0-9]", "", raw_key.casefold())
        if key in secret_keys or any(key.endswith(suffix) for suffix in secret_suffixes):
            raise PrivacyBoundaryError(
                "Secret-bearing query parameters cannot enter reusable corpus provenance."
            )
    netloc_host = f"[{host}]" if address is not None and address.version == 6 else host
    netloc = f"{netloc_host}:{port}" if port is not None else netloc_host
    scheme = parsed.scheme.casefold()
    return urlunparse((scheme, netloc, parsed.path or "/", parsed.params, parsed.query, ""))


def _official_host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").casefold().rstrip(".")
    return any(host == suffix or host.endswith("." + suffix) for suffix in OFFICIAL_HOST_SUFFIXES)


def _write_portable_file(path: Path, payload: bytes) -> None:
    """Write a package member once; never overwrite different evidence."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise PublicCorpusError(f"Portable package member already differs: {path.name}")
        return
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class PublicCorpus:
    """A local immutable public corpus with optional SQLite FTS5 search."""

    def __init__(self, root: Path, *, force_fallback_search: bool = False) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.objects = self.root / "objects" / "sha256"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.root / "public-corpus.sqlite3")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_schema()
        self.search_backend = self._configure_search(force_fallback_search)

    def __enter__(self) -> "PublicCorpus":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS seeds (
                seed_id TEXT PRIMARY KEY,
                canonical_url TEXT NOT NULL,
                role TEXT NOT NULL,
                public INTEGER NOT NULL CHECK(public = 1),
                created_at TEXT NOT NULL,
                UNIQUE(canonical_url, role)
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id TEXT PRIMARY KEY,
                raw_sha256 TEXT NOT NULL UNIQUE,
                object_path TEXT NOT NULL,
                byte_length INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS observations (
                observation_id TEXT PRIMARY KEY,
                seed_id TEXT NOT NULL REFERENCES seeds(seed_id),
                snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
                fetched_at TEXT NOT NULL,
                content_type TEXT,
                parser_manifest_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_observations_seed_time
                ON observations(seed_id, fetched_at);
            CREATE TABLE IF NOT EXISTS indexed_texts (
                snapshot_id TEXT PRIMARY KEY REFERENCES snapshots(snapshot_id),
                text_hash TEXT NOT NULL,
                original_text TEXT NOT NULL,
                normalized_text TEXT NOT NULL,
                document_id TEXT,
                chain_candidate_id TEXT,
                query_lane TEXT,
                indexed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                pin_digest TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS run_pins (
                run_id TEXT NOT NULL REFERENCES runs(run_id),
                snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
                ordinal INTEGER NOT NULL,
                PRIMARY KEY(run_id, snapshot_id),
                UNIQUE(run_id, ordinal)
            );
            CREATE TABLE IF NOT EXISTS funnel_state (
                chain_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                snapshot_id TEXT REFERENCES snapshots(snapshot_id),
                reason TEXT,
                source_role TEXT,
                court_id TEXT,
                period_id TEXT,
                enumerator_id TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS funnel_events (
                event_id TEXT PRIMARY KEY,
                chain_id TEXT NOT NULL,
                status TEXT NOT NULL,
                snapshot_id TEXT,
                reason TEXT,
                source_role TEXT,
                court_id TEXT,
                period_id TEXT,
                enumerator_id TEXT,
                event_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS treatments (
                treatment_id TEXT PRIMARY KEY,
                source_chain_id TEXT NOT NULL,
                source_court_id TEXT,
                target_authority_id TEXT NOT NULL,
                target_kind TEXT,
                target_identity_json TEXT,
                treatment_type TEXT NOT NULL,
                snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
                supersedes_treatment_id TEXT REFERENCES treatments(treatment_id),
                status TEXT NOT NULL,
                reviewer TEXT,
                quote TEXT,
                locator TEXT,
                speaker TEXT,
                created_at TEXT NOT NULL,
                reviewed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS treatment_review_history (
                history_id TEXT PRIMARY KEY,
                treatment_id TEXT NOT NULL REFERENCES treatments(treatment_id),
                event_type TEXT NOT NULL,
                reviewer TEXT,
                payload_json TEXT NOT NULL,
                event_at TEXT NOT NULL
            );
            """
        )
        self._ensure_column("indexed_texts", "document_id", "TEXT")
        self._ensure_column("indexed_texts", "chain_candidate_id", "TEXT")
        self._ensure_column("indexed_texts", "query_lane", "TEXT")
        for table in ("funnel_state", "funnel_events"):
            for column in ("source_role", "court_id", "period_id", "enumerator_id"):
                self._ensure_column(table, column, "TEXT")
        self._ensure_column("treatments", "source_court_id", "TEXT")
        self._ensure_column("treatments", "target_kind", "TEXT")
        self._ensure_column("treatments", "target_identity_json", "TEXT")
        self._ensure_column("treatments", "supersedes_treatment_id", "TEXT")
        self.conn.commit()

    def _ensure_column(self, table: str, column: str, declaration: str) -> None:
        columns = {
            str(row["name"])
            for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")

    def _configure_search(self, force_fallback: bool) -> str:
        if force_fallback:
            return "fallback"
        try:
            self.conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS indexed_texts_fts "
                "USING fts5(snapshot_id UNINDEXED, normalized_text)"
            )
            self.conn.execute(
                """
                INSERT INTO indexed_texts_fts(snapshot_id, normalized_text)
                SELECT i.snapshot_id, i.normalized_text
                FROM indexed_texts i
                WHERE NOT EXISTS (
                    SELECT 1 FROM indexed_texts_fts f WHERE f.snapshot_id=i.snapshot_id
                )
                """
            )
            self.conn.commit()
            return "fts5"
        except sqlite3.OperationalError:
            return "fallback"

    def register_seed(self, *, url: str, role: str, public: bool) -> dict[str, Any]:
        if role == PRIVATE_SEED_ROLE or public is not True:
            raise PrivacyBoundaryError(
                "Private applicant material must stay in the matter workspace, not the reusable corpus."
            )
        if role not in PUBLIC_SEED_ROLES:
            raise SeedRoleError(f"Unsupported public seed role: {role}")
        canonical_url = _canonical_public_url(url)
        if role != "discovery_only" and not _official_host_allowed(canonical_url):
            raise SeedRoleError(
                "Official public-corpus roles require a recognized official host; "
                "use discovery_only until the source route is reviewed."
            )
        seed_id = _identifier("seed", {"url": canonical_url, "role": role})
        created_at = _utc_now()
        with self.conn:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO seeds(seed_id, canonical_url, role, public, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (seed_id, canonical_url, role, created_at),
            )
        return {
            "seed_id": seed_id,
            "url": canonical_url,
            "role": role,
            "public": True,
        }

    def list_seeds(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT seed_id, canonical_url, role, public, created_at FROM seeds ORDER BY seed_id"
        ).fetchall()
        return [
            {
                "seed_id": str(row["seed_id"]),
                "url": str(row["canonical_url"]),
                "role": str(row["role"]),
                "public": bool(row["public"]),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    def _snapshot_exists(self, snapshot_id: str) -> bool:
        return self.conn.execute(
            "SELECT 1 FROM snapshots WHERE snapshot_id=?", (snapshot_id,)
        ).fetchone() is not None

    def store_snapshot(
        self,
        *,
        seed_id: str,
        raw: bytes,
        content_type: str | None,
        fetched_at: str,
        parser_manifest: dict[str, Any],
    ) -> dict[str, Any]:
        seed = self.conn.execute(
            "SELECT seed_id, role FROM seeds WHERE seed_id=?", (seed_id,)
        ).fetchone()
        if seed is None:
            raise PublicCorpusError(f"Unknown public seed: {seed_id}")
        if str(seed["role"]) == "discovery_only":
            raise PrivacyBoundaryError(
                "discovery_only stores URL metadata only; mirror bytes and text cannot enter shared evidence objects."
            )
        if not isinstance(raw, bytes):
            raise PublicCorpusError("Raw snapshot payload must be bytes.")
        if not isinstance(parser_manifest, dict) or not parser_manifest:
            raise PublicCorpusError("Snapshot observation requires a non-empty parser manifest.")
        _parse_timestamp(fetched_at)
        raw_hash = _sha256(raw)
        snapshot_id = f"snapshot-sha256:{raw_hash}"
        object_path = self.objects / raw_hash[:2] / f"{raw_hash}.bin"
        object_path.parent.mkdir(parents=True, exist_ok=True)
        if object_path.exists():
            if object_path.read_bytes() != raw:
                raise PublicCorpusError("Content-addressed object collision detected.")
        else:
            temporary = object_path.with_name(f".{object_path.name}.{uuid.uuid4().hex}.tmp")
            with temporary.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, object_path)
        observation_id = _identifier(
            "observation",
            {
                "seed_id": seed_id,
                "snapshot_id": snapshot_id,
                "fetched_at": fetched_at,
                "content_type": content_type,
                "parser_manifest": parser_manifest,
            },
        )
        created_at = _utc_now()
        with self.conn:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO snapshots(
                    snapshot_id, raw_sha256, object_path, byte_length, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (snapshot_id, raw_hash, str(object_path), len(raw), created_at),
            )
            self.conn.execute(
                """
                INSERT OR IGNORE INTO observations(
                    observation_id, seed_id, snapshot_id, fetched_at, content_type,
                    parser_manifest_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    seed_id,
                    snapshot_id,
                    fetched_at,
                    content_type,
                    _canonical_json(parser_manifest),
                ),
            )
        return {
            "seed_id": seed_id,
            "snapshot_id": snapshot_id,
            "observation_id": observation_id,
            "raw_sha256": raw_hash,
            "object_path": str(object_path),
        }

    def snapshot_bytes(self, snapshot_id: str) -> bytes:
        row = self.conn.execute(
            "SELECT object_path FROM snapshots WHERE snapshot_id=?", (snapshot_id,)
        ).fetchone()
        if row is None:
            raise PublicCorpusError(f"Unknown snapshot: {snapshot_id}")
        return Path(str(row["object_path"])).read_bytes()

    def create_run(self, run_id: str, snapshot_ids: Iterable[str]) -> dict[str, Any]:
        clean_run_id = run_id.strip()
        if not clean_run_id:
            raise PublicCorpusError("run_id is required")
        pins = sorted(set(snapshot_ids))
        if not pins:
            raise PublicCorpusError("A reusable-corpus run requires at least one snapshot pin.")
        missing = [snapshot_id for snapshot_id in pins if not self._snapshot_exists(snapshot_id)]
        if missing:
            raise PublicCorpusError("Unknown snapshot pins: " + ", ".join(missing))
        pin_digest = _identifier("evidence", pins)
        existing = self.conn.execute(
            "SELECT pin_digest FROM runs WHERE run_id=?", (clean_run_id,)
        ).fetchone()
        if existing is not None:
            if str(existing["pin_digest"]) != pin_digest:
                raise RunPinConflict("Run pins are immutable and differ from the existing run.")
            return {
                "run_id": clean_run_id,
                "pin_digest": pin_digest,
                "snapshot_ids": self.run_snapshots(clean_run_id),
            }
        with self.conn:
            self.conn.execute(
                "INSERT INTO runs(run_id, pin_digest, created_at) VALUES (?, ?, ?)",
                (clean_run_id, pin_digest, _utc_now()),
            )
            for ordinal, snapshot_id in enumerate(pins):
                self.conn.execute(
                    "INSERT INTO run_pins(run_id, snapshot_id, ordinal) VALUES (?, ?, ?)",
                    (clean_run_id, snapshot_id, ordinal),
                )
        return {"run_id": clean_run_id, "pin_digest": pin_digest, "snapshot_ids": pins}

    def run_snapshots(self, run_id: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT snapshot_id FROM run_pins WHERE run_id=? ORDER BY ordinal", (run_id,)
        ).fetchall()
        if not rows and self.conn.execute(
            "SELECT 1 FROM runs WHERE run_id=?", (run_id,)
        ).fetchone() is None:
            raise PublicCorpusError(f"Unknown run: {run_id}")
        return [str(row["snapshot_id"]) for row in rows]

    def export_run(self, run_id: str, destination: str | Path) -> dict[str, Any]:
        """Export one immutable public run as a deterministic directory package."""

        pinned_snapshot_ids = self.run_snapshots(run_id)
        run = self.conn.execute(
            "SELECT run_id, pin_digest, created_at FROM runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if run is None:
            raise PublicCorpusError(f"Unknown public run: {run_id}")

        # A run pins its primary raw evidence.  The exchange additionally carries
        # public snapshots that are necessary to reproduce the complete funnel and
        # treatment history of the pinned chains.  They never become run pins.
        package_snapshot_ids = set(pinned_snapshot_ids)
        related_chain_ids: set[str] = set()
        while True:
            previous = (set(package_snapshot_ids), set(related_chain_ids))
            if package_snapshot_ids:
                placeholders = ",".join("?" for _ in package_snapshot_ids)
                for row in self.conn.execute(
                    f"""
                    SELECT chain_candidate_id FROM indexed_texts
                    WHERE snapshot_id IN ({placeholders})
                      AND chain_candidate_id IS NOT NULL
                    """,
                    sorted(package_snapshot_ids),
                ):
                    related_chain_ids.add(str(row["chain_candidate_id"]))
                for table in ("funnel_state", "funnel_events"):
                    for row in self.conn.execute(
                        f"SELECT chain_id FROM {table} WHERE snapshot_id IN ({placeholders})",
                        sorted(package_snapshot_ids),
                    ):
                        related_chain_ids.add(str(row["chain_id"]))
                for row in self.conn.execute(
                    f"SELECT source_chain_id FROM treatments WHERE snapshot_id IN ({placeholders})",
                    sorted(package_snapshot_ids),
                ):
                    related_chain_ids.add(str(row["source_chain_id"]))
            if related_chain_ids:
                placeholders = ",".join("?" for _ in related_chain_ids)
                for table in ("funnel_state", "funnel_events"):
                    for row in self.conn.execute(
                        f"""
                        SELECT snapshot_id FROM {table}
                        WHERE chain_id IN ({placeholders}) AND snapshot_id IS NOT NULL
                        """,
                        sorted(related_chain_ids),
                    ):
                        package_snapshot_ids.add(str(row["snapshot_id"]))
                for row in self.conn.execute(
                    f"""
                    SELECT snapshot_id FROM treatments
                    WHERE source_chain_id IN ({placeholders})
                    """,
                    sorted(related_chain_ids),
                ):
                    package_snapshot_ids.add(str(row["snapshot_id"]))
            if previous == (package_snapshot_ids, related_chain_ids):
                break

        snapshot_ids = sorted(package_snapshot_ids)
        placeholders = ",".join("?" for _ in snapshot_ids)
        package_root = Path(destination)
        snapshots: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        seeds: list[dict[str, Any]] = []
        indexed_texts: list[dict[str, Any]] = []
        if snapshot_ids:
            snapshot_rows = self.conn.execute(
                f"""
                SELECT snapshot_id, raw_sha256, byte_length
                FROM snapshots WHERE snapshot_id IN ({placeholders})
                ORDER BY snapshot_id
                """,
                snapshot_ids,
            ).fetchall()
            for row in snapshot_rows:
                object_name = f"{row['raw_sha256']}.bin"
                _write_portable_file(
                    package_root / "objects" / object_name,
                    self.snapshot_bytes(row["snapshot_id"]),
                )
                snapshots.append(
                    {
                        "snapshot_id": row["snapshot_id"],
                        "raw_sha256": row["raw_sha256"],
                        "byte_length": row["byte_length"],
                        "object_path": f"objects/{object_name}",
                    }
                )
            observation_rows = self.conn.execute(
                f"""
                SELECT observation_id, seed_id, snapshot_id, fetched_at,
                       content_type, parser_manifest_json
                FROM observations WHERE snapshot_id IN ({placeholders})
                ORDER BY observation_id
                """,
                snapshot_ids,
            ).fetchall()
            observations = [
                {
                    "observation_id": row["observation_id"],
                    "seed_id": row["seed_id"],
                    "snapshot_id": row["snapshot_id"],
                    "fetched_at": row["fetched_at"],
                    "content_type": row["content_type"],
                    "parser_manifest": json.loads(row["parser_manifest_json"]),
                }
                for row in observation_rows
            ]
            seed_ids = sorted({row["seed_id"] for row in observation_rows})
            if seed_ids:
                seed_placeholders = ",".join("?" for _ in seed_ids)
                seeds = [
                    {
                        "seed_id": row["seed_id"],
                        "url": row["canonical_url"],
                        "role": row["role"],
                        "public": bool(row["public"]),
                    }
                    for row in self.conn.execute(
                        f"""
                        SELECT seed_id, canonical_url, role, public
                        FROM seeds WHERE seed_id IN ({seed_placeholders})
                        ORDER BY seed_id
                        """,
                        seed_ids,
                    ).fetchall()
                ]
            indexed_texts = [
                {
                    "snapshot_id": row["snapshot_id"],
                    "text_hash": row["text_hash"],
                    "text": row["original_text"],
                    "document_id": row["document_id"],
                    "chain_candidate_id": row["chain_candidate_id"],
                    "query_lane": row["query_lane"],
                }
                for row in self.conn.execute(
                    f"""
                    SELECT snapshot_id, text_hash, original_text, document_id,
                           chain_candidate_id, query_lane
                    FROM indexed_texts WHERE snapshot_id IN ({placeholders})
                    ORDER BY snapshot_id
                    """,
                    snapshot_ids,
                ).fetchall()
            ]

        funnel_states: list[dict[str, Any]] = []
        funnel_events: list[dict[str, Any]] = []
        if related_chain_ids:
            chain_placeholders = ",".join("?" for _ in related_chain_ids)
            funnel_states = [
                dict(row)
                for row in self.conn.execute(
                    f"""
                    SELECT chain_id, status, snapshot_id, reason, source_role,
                           court_id, period_id, enumerator_id, updated_at
                    FROM funnel_state WHERE chain_id IN ({chain_placeholders})
                    ORDER BY chain_id
                    """,
                    sorted(related_chain_ids),
                ).fetchall()
            ]
            event_rows = self.conn.execute(
                f"""
                SELECT event_id, chain_id, status, snapshot_id, reason, source_role,
                       court_id, period_id, enumerator_id, event_at, rowid AS storage_ordinal
                FROM funnel_events WHERE chain_id IN ({chain_placeholders})
                ORDER BY chain_id, storage_ordinal
                """,
                sorted(related_chain_ids),
            ).fetchall()
            chain_ordinals: dict[str, int] = {}
            for row in event_rows:
                chain_id = str(row["chain_id"])
                ordinal = chain_ordinals.get(chain_id, 0)
                chain_ordinals[chain_id] = ordinal + 1
                funnel_events.append(
                    {
                        key: row[key]
                        for key in (
                            "event_id",
                            "chain_id",
                            "status",
                            "snapshot_id",
                            "reason",
                            "source_role",
                            "court_id",
                            "period_id",
                            "enumerator_id",
                            "event_at",
                        )
                    }
                    | {"ordinal": ordinal}
                )

        treatment_rows: list[sqlite3.Row] = []
        if snapshot_ids or related_chain_ids:
            clauses: list[str] = []
            values: list[str] = []
            if snapshot_ids:
                clauses.append(
                    "snapshot_id IN (" + ",".join("?" for _ in snapshot_ids) + ")"
                )
                values.extend(snapshot_ids)
            if related_chain_ids:
                clauses.append(
                    "source_chain_id IN ("
                    + ",".join("?" for _ in related_chain_ids)
                    + ")"
                )
                values.extend(sorted(related_chain_ids))
            treatment_rows = self.conn.execute(
                "SELECT * FROM treatments WHERE " + " OR ".join(clauses), values
            ).fetchall()
        treatments_by_id = {str(row["treatment_id"]): row for row in treatment_rows}
        unresolved_prior_ids = {
            str(row["supersedes_treatment_id"])
            for row in treatment_rows
            if row["supersedes_treatment_id"] is not None
            and str(row["supersedes_treatment_id"]) not in treatments_by_id
        }
        while unresolved_prior_ids:
            prior_placeholders = ",".join("?" for _ in unresolved_prior_ids)
            prior_rows = self.conn.execute(
                f"SELECT * FROM treatments WHERE treatment_id IN ({prior_placeholders})",
                sorted(unresolved_prior_ids),
            ).fetchall()
            if len(prior_rows) != len(unresolved_prior_ids):
                raise PublicCorpusError("Treatment supersession history is incomplete.")
            unresolved_prior_ids = set()
            for row in prior_rows:
                treatment_id = str(row["treatment_id"])
                treatments_by_id[treatment_id] = row
                prior_id = row["supersedes_treatment_id"]
                if prior_id is not None and str(prior_id) not in treatments_by_id:
                    unresolved_prior_ids.add(str(prior_id))

        treatments: list[dict[str, Any]] = []
        for treatment_id in sorted(treatments_by_id):
            row = treatments_by_id[treatment_id]
            history_rows = self.conn.execute(
                """
                SELECT history_id, event_type, reviewer, payload_json, event_at
                FROM treatment_review_history WHERE treatment_id=? ORDER BY rowid
                """,
                (treatment_id,),
            ).fetchall()
            history = [
                {
                    "history_id": history_row["history_id"],
                    "event_type": history_row["event_type"],
                    "reviewer": history_row["reviewer"],
                    "payload": json.loads(str(history_row["payload_json"])),
                    "event_at": history_row["event_at"],
                    "ordinal": ordinal,
                }
                for ordinal, history_row in enumerate(history_rows)
            ]
            treatments.append(
                {
                    "treatment_id": treatment_id,
                    "source_chain_id": row["source_chain_id"],
                    "source_court_id": row["source_court_id"],
                    "target_authority_id": row["target_authority_id"],
                    "target_kind": row["target_kind"],
                    "target_identity": (
                        json.loads(str(row["target_identity_json"]))
                        if row["target_identity_json"] is not None
                        else None
                    ),
                    "treatment_type": row["treatment_type"],
                    "snapshot_id": row["snapshot_id"],
                    "supersedes_treatment_id": row["supersedes_treatment_id"],
                    "status": row["status"],
                    "reviewer": row["reviewer"],
                    "quote": row["quote"],
                    "locator": row["locator"],
                    "speaker": row["speaker"],
                    "created_at": row["created_at"],
                    "reviewed_at": row["reviewed_at"],
                    "review_history": history,
                }
            )

        run_pin = {
            "run_id": str(run["run_id"]),
            "pin_digest": str(run["pin_digest"]),
            "snapshot_ids": pinned_snapshot_ids,
            "created_at": str(run["created_at"]),
        }
        limitations = [
            "Пакет содержит только публичные снимки и связанные проверяемые производные записи.",
            "Наличие записи в пакете не доказывает полноту опубликованной судебной практики.",
        ]
        evidence_payload = {
            "seeds": seeds,
            "snapshots": snapshots,
            "observations": observations,
            "indexed_texts": indexed_texts,
            "run_pins": [run_pin],
            "funnel": {"states": funnel_states, "events": funnel_events},
            "treatments": treatments,
            "limitations": limitations,
        }
        corpus_evidence_digest = _identifier("portable-evidence", evidence_payload)
        export_id = _identifier(
            "public-corpus-export",
            {
                "run_pins": [run_pin],
                "corpus_evidence_digest": corpus_evidence_digest,
            },
        )
        package = {
            "schema_version": "1.0",
            "export_id": export_id,
            "exported_at": str(run["created_at"]),
            "corpus_evidence_digest": corpus_evidence_digest,
            "public_only": True,
            # `run` remains as a compatibility alias for earlier 1.0 importers.
            "run": run_pin,
            **evidence_payload,
        }
        package["manifest_sha256"] = _sha256(_canonical_json(package).encode("utf-8"))
        _write_portable_file(
            package_root / "manifest.json",
            (_canonical_json(package) + "\n").encode("utf-8"),
        )
        return package

    def import_run(self, source: str | Path) -> dict[str, Any]:
        """Validate a public package completely, then idempotently import it."""

        package_root = Path(source)
        try:
            package = json.loads((package_root / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PublicCorpusError("Portable public-corpus manifest is unreadable.") from exc
        if not isinstance(package, dict) or package.get("schema_version") != "1.0":
            raise PublicCorpusError("Unsupported public-corpus package schema.")
        if package.get("public_only") is not True:
            raise PrivacyBoundaryError("Portable package is not declared public-only.")
        declared_digest = package.get("manifest_sha256")
        unsigned = {key: value for key, value in package.items() if key != "manifest_sha256"}
        if declared_digest != _sha256(_canonical_json(unsigned).encode("utf-8")):
            raise PublicCorpusError("Portable package manifest digest does not match.")
        rich_package = "export_id" in package
        run = package.get("run")
        seeds = package.get("seeds")
        snapshots = package.get("snapshots")
        observations = package.get("observations")
        indexed_texts = package.get("indexed_texts", [])
        run_pins = package.get("run_pins", [run] if isinstance(run, dict) else [])
        funnel = package.get("funnel", {"states": [], "events": []})
        treatments = package.get("treatments", [])
        limitations = package.get("limitations", [])
        if not isinstance(run, dict) or not all(
            isinstance(value, list)
            for value in (
                seeds,
                snapshots,
                observations,
                indexed_texts,
                run_pins,
                treatments,
                limitations,
            )
        ):
            raise PublicCorpusError("Portable package has invalid collections.")
        if not isinstance(funnel, dict) or not isinstance(funnel.get("states"), list) or not isinstance(
            funnel.get("events"), list
        ):
            raise PublicCorpusError("Portable package has invalid funnel collections.")
        if rich_package:
            required = {
                "schema_version",
                "export_id",
                "exported_at",
                "corpus_evidence_digest",
                "public_only",
                "run",
                "seeds",
                "snapshots",
                "observations",
                "indexed_texts",
                "run_pins",
                "funnel",
                "treatments",
                "limitations",
                "manifest_sha256",
            }
            if set(package) != required:
                missing = sorted(required - set(package))
                extra = sorted(set(package) - required)
                raise PublicCorpusError(
                    f"Portable package fields do not match schema; missing={missing}, extra={extra}."
                )
            if len(run_pins) != 1 or run_pins[0] != run:
                raise PublicCorpusError("Portable run compatibility alias does not match run_pins.")
            _parse_timestamp(str(package.get("exported_at", "")))
            if package.get("exported_at") != run.get("created_at"):
                raise PublicCorpusError("Portable export time must equal immutable run creation time.")
            if not limitations or any(not isinstance(item, str) or not item.strip() for item in limitations):
                raise PublicCorpusError("Portable package limitations must be non-empty strings.")

        validated_seeds: dict[str, dict[str, Any]] = {}
        for seed in seeds:
            if not isinstance(seed, dict) or seed.get("public") is not True:
                raise PrivacyBoundaryError("Portable package contains a non-public seed.")
            role = seed.get("role")
            if role not in PUBLIC_SEED_ROLES:
                raise SeedRoleError(f"Unsupported public seed role: {role}")
            canonical_url = _canonical_public_url(str(seed.get("url", "")))
            if role != "discovery_only" and not _official_host_allowed(canonical_url):
                raise SeedRoleError(
                    "Portable official seed does not use a recognized official host."
                )
            expected_seed_id = _identifier("seed", {"url": canonical_url, "role": role})
            if seed.get("seed_id") != expected_seed_id:
                raise PublicCorpusError("Portable seed identity does not match its URL and role.")
            if expected_seed_id in validated_seeds:
                raise PublicCorpusError("Portable seed identities must be unique.")
            validated_seeds[expected_seed_id] = {
                "url": canonical_url,
                "role": role,
                "public": True,
            }

        raw_by_snapshot: dict[str, bytes] = {}
        for snapshot in snapshots:
            if not isinstance(snapshot, dict):
                raise PublicCorpusError("Portable snapshot entry must be an object.")
            raw_hash = snapshot.get("raw_sha256")
            object_path = snapshot.get("object_path")
            if not isinstance(raw_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", raw_hash):
                raise PublicCorpusError("Portable snapshot has invalid SHA-256.")
            if object_path != f"objects/{raw_hash}.bin":
                raise PublicCorpusError("Portable snapshot object path is not content-addressed.")
            try:
                raw = (package_root / object_path).read_bytes()
            except OSError as exc:
                raise PublicCorpusError("Portable snapshot object is unreadable.") from exc
            expected_snapshot_id = f"snapshot-sha256:{raw_hash}"
            if _sha256(raw) != raw_hash or snapshot.get("snapshot_id") != expected_snapshot_id:
                raise PublicCorpusError("Portable snapshot bytes or identity were tampered with.")
            if snapshot.get("byte_length") != len(raw):
                raise PublicCorpusError("Portable snapshot byte length does not match.")
            if expected_snapshot_id in raw_by_snapshot:
                raise PublicCorpusError("Portable snapshot identities must be unique.")
            raw_by_snapshot[expected_snapshot_id] = raw

        validated_observations: list[dict[str, Any]] = []
        observation_ids: set[str] = set()
        observed_snapshot_ids: set[str] = set()
        for observation in observations:
            if not isinstance(observation, dict):
                raise PublicCorpusError("Portable observation entry must be an object.")
            if observation.get("seed_id") not in validated_seeds:
                raise PublicCorpusError("Portable observation references an unknown seed.")
            if observation.get("snapshot_id") not in raw_by_snapshot:
                raise PublicCorpusError("Portable observation references an unknown snapshot.")
            if not isinstance(observation.get("parser_manifest"), dict) or not observation.get(
                "parser_manifest"
            ):
                raise PublicCorpusError("Portable observation lacks parser manifest.")
            if validated_seeds[str(observation["seed_id"])]["role"] == "discovery_only":
                raise PrivacyBoundaryError(
                    "discovery_only metadata cannot carry snapshots in a portable package."
                )
            _parse_timestamp(str(observation.get("fetched_at", "")))
            expected_observation_id = _identifier(
                "observation",
                {
                    "seed_id": observation.get("seed_id"),
                    "snapshot_id": observation.get("snapshot_id"),
                    "fetched_at": observation.get("fetched_at"),
                    "content_type": observation.get("content_type"),
                    "parser_manifest": observation.get("parser_manifest"),
                },
            )
            if observation.get("observation_id") != expected_observation_id:
                raise PublicCorpusError("Portable observation identity does not match its payload.")
            if expected_observation_id in observation_ids:
                raise PublicCorpusError("Portable observation identities must be unique.")
            observation_ids.add(expected_observation_id)
            observed_snapshot_ids.add(str(observation["snapshot_id"]))
            validated_observations.append(observation)
        if observed_snapshot_ids != set(raw_by_snapshot):
            raise PublicCorpusError(
                "Every portable snapshot requires at least one public source observation."
            )
        expected_pins = run.get("snapshot_ids")
        if (
            not isinstance(expected_pins, list)
            or not expected_pins
            or expected_pins != sorted(set(expected_pins))
            or any(item not in raw_by_snapshot for item in expected_pins)
        ):
            raise PublicCorpusError("Portable run pins reference unknown snapshots.")
        if run.get("pin_digest") != _identifier("evidence", sorted(set(expected_pins))):
            raise PublicCorpusError("Portable run pin digest does not match.")
        if not isinstance(run.get("run_id"), str) or not str(run.get("run_id")).strip():
            raise PublicCorpusError("Portable run_id is required.")
        if rich_package:
            _parse_timestamp(str(run.get("created_at", "")))

        validated_indexed: list[dict[str, Any]] = []
        indexed_snapshot_ids: set[str] = set()
        for indexed in indexed_texts:
            if not isinstance(indexed, dict) or indexed.get("snapshot_id") not in raw_by_snapshot:
                raise PublicCorpusError("Portable search text references an unknown snapshot.")
            text = indexed.get("text")
            if not isinstance(text, str) or indexed.get("text_hash") != _sha256(
                _normalise_text(text).encode("utf-8")
            ):
                raise PublicCorpusError("Portable search text digest does not match.")
            if indexed["snapshot_id"] in indexed_snapshot_ids:
                raise PublicCorpusError("Portable indexed snapshots must be unique.")
            indexed_snapshot_ids.add(str(indexed["snapshot_id"]))
            if rich_package and not all(
                isinstance(indexed.get(key), str) and str(indexed[key]).strip()
                for key in ("document_id", "chain_candidate_id", "query_lane")
            ):
                raise PublicCorpusError(
                    "Portable search provenance requires document_id, chain_candidate_id, and query_lane."
                )
            validated_indexed.append(indexed)

        validated_states: list[dict[str, Any]] = []
        state_chain_ids: set[str] = set()
        allowed_funnel_statuses = set(FUNNEL_STAGES) | FUNNEL_FAILURES
        for state in funnel["states"]:
            if not isinstance(state, dict) or set(state) != {
                "chain_id",
                "status",
                "snapshot_id",
                "reason",
                "source_role",
                "court_id",
                "period_id",
                "enumerator_id",
                "updated_at",
            }:
                raise PublicCorpusError("Portable funnel state does not match its schema.")
            chain_id = state.get("chain_id")
            if not isinstance(chain_id, str) or not chain_id.strip() or chain_id in state_chain_ids:
                raise PublicCorpusError("Portable funnel state chain IDs must be non-empty and unique.")
            if state.get("status") not in allowed_funnel_statuses:
                raise PublicCorpusError("Portable funnel state has an unknown status.")
            if state.get("snapshot_id") is not None and state.get("snapshot_id") not in raw_by_snapshot:
                raise PublicCorpusError("Portable funnel state references an unknown snapshot.")
            _parse_timestamp(str(state.get("updated_at", "")))
            state_chain_ids.add(chain_id)
            validated_states.append(state)

        validated_events: list[dict[str, Any]] = []
        event_ids: set[str] = set()
        chain_ordinals: dict[str, list[int]] = {}
        for event in funnel["events"]:
            if not isinstance(event, dict) or set(event) != {
                "event_id",
                "chain_id",
                "status",
                "snapshot_id",
                "reason",
                "source_role",
                "court_id",
                "period_id",
                "enumerator_id",
                "event_at",
                "ordinal",
            }:
                raise PublicCorpusError("Portable funnel event does not match its schema.")
            if event.get("status") not in allowed_funnel_statuses:
                raise PublicCorpusError("Portable funnel event has an unknown status.")
            if event.get("snapshot_id") is not None and event.get("snapshot_id") not in raw_by_snapshot:
                raise PublicCorpusError("Portable funnel event references an unknown snapshot.")
            if not isinstance(event.get("chain_id"), str) or not str(event["chain_id"]).strip():
                raise PublicCorpusError("Portable funnel event requires a chain ID.")
            if not isinstance(event.get("ordinal"), int) or event["ordinal"] < 0:
                raise PublicCorpusError("Portable funnel event ordinal is invalid.")
            _parse_timestamp(str(event.get("event_at", "")))
            expected_event_id = _identifier(
                "funnel-event",
                {
                    key: event.get(key)
                    for key in (
                        "chain_id",
                        "status",
                        "snapshot_id",
                        "reason",
                        "source_role",
                        "court_id",
                        "period_id",
                        "enumerator_id",
                        "event_at",
                    )
                },
            )
            if event.get("event_id") != expected_event_id or expected_event_id in event_ids:
                raise PublicCorpusError("Portable funnel event identity is invalid or duplicated.")
            event_ids.add(expected_event_id)
            chain_ordinals.setdefault(str(event["chain_id"]), []).append(int(event["ordinal"]))
            validated_events.append(event)
        for chain_id, ordinals in chain_ordinals.items():
            if sorted(ordinals) != list(range(len(ordinals))) or chain_id not in state_chain_ids:
                raise PublicCorpusError(
                    "Portable funnel history must be contiguous and have a current state."
                )
        events_by_chain: dict[str, list[dict[str, Any]]] = {}
        for event in validated_events:
            events_by_chain.setdefault(str(event["chain_id"]), []).append(event)
        states_by_chain = {str(state["chain_id"]): state for state in validated_states}
        if set(events_by_chain) != set(states_by_chain):
            raise PublicCorpusError(
                "Portable funnel requires complete event history for every current state."
            )
        for chain_id, events in events_by_chain.items():
            current_status: str | None = None
            for event in sorted(events, key=lambda item: int(item["ordinal"])):
                status = str(event["status"])
                if current_status is None:
                    allowed = status == "enumerated"
                elif status == current_status or status in FUNNEL_FAILURES:
                    allowed = True
                elif current_status in FUNNEL_FAILURES:
                    allowed = status in {"card", "document_link", "payload_validated"}
                else:
                    allowed = (
                        current_status in FUNNEL_STAGES
                        and status in FUNNEL_STAGES
                        and FUNNEL_STAGES.index(status)
                        == FUNNEL_STAGES.index(current_status) + 1
                    )
                if not allowed:
                    raise PublicCorpusError(
                        f"Portable funnel history skips a required stage for {chain_id}."
                    )
                current_status = status
            if states_by_chain[chain_id]["status"] != current_status:
                raise PublicCorpusError(
                    "Portable funnel current state conflicts with its final event."
                )

        validated_treatments: dict[str, dict[str, Any]] = {}
        validated_histories: list[dict[str, Any]] = []
        for treatment in treatments:
            required_treatment_fields = {
                "treatment_id",
                "source_chain_id",
                "source_court_id",
                "target_authority_id",
                "target_kind",
                "target_identity",
                "treatment_type",
                "snapshot_id",
                "supersedes_treatment_id",
                "status",
                "reviewer",
                "quote",
                "locator",
                "speaker",
                "created_at",
                "reviewed_at",
                "review_history",
            }
            if not isinstance(treatment, dict) or set(treatment) != required_treatment_fields:
                raise PublicCorpusError("Portable treatment does not match its schema.")
            if treatment.get("treatment_type") not in TREATMENT_TYPES:
                raise PublicCorpusError("Portable treatment has an unknown type.")
            if treatment.get("status") not in {"candidate", "verified", "rejected"}:
                raise PublicCorpusError("Portable treatment has an unknown review status.")
            if treatment.get("snapshot_id") not in raw_by_snapshot:
                raise PublicCorpusError("Portable treatment references an unknown snapshot.")
            if treatment.get("target_identity") is not None and (
                not isinstance(treatment.get("target_identity"), dict)
                or not treatment.get("target_identity")
            ):
                raise PublicCorpusError("Portable treatment target identity is invalid.")
            for key in ("source_chain_id", "target_authority_id"):
                if not isinstance(treatment.get(key), str) or not str(treatment[key]).strip():
                    raise PublicCorpusError("Portable treatment source and target are required.")
            expected_treatment_id = _identifier(
                "treatment",
                {
                    "source_chain_id": treatment.get("source_chain_id"),
                    "source_court_id": treatment.get("source_court_id"),
                    "target_authority_id": treatment.get("target_authority_id"),
                    "target_kind": treatment.get("target_kind"),
                    "target_identity": treatment.get("target_identity"),
                    "treatment_type": treatment.get("treatment_type"),
                    "snapshot_id": treatment.get("snapshot_id"),
                    "supersedes_treatment_id": treatment.get("supersedes_treatment_id"),
                },
            )
            if treatment.get("treatment_id") != expected_treatment_id:
                raise PublicCorpusError("Portable treatment identity does not match its payload.")
            if expected_treatment_id in validated_treatments:
                raise PublicCorpusError("Portable treatment identities must be unique.")
            _parse_timestamp(str(treatment.get("created_at", "")))
            if treatment.get("reviewed_at") is not None:
                _parse_timestamp(str(treatment["reviewed_at"]))
            if treatment.get("status") in {"verified", "rejected"} and not all(
                treatment.get(key) is not None and str(treatment[key]).strip()
                for key in ("reviewer", "reviewed_at")
            ):
                raise PublicCorpusError("Portable completed treatment lacks review metadata.")
            if treatment.get("status") == "candidate" and any(
                treatment.get(key) is not None
                for key in ("reviewer", "quote", "locator", "speaker", "reviewed_at")
            ):
                raise PublicCorpusError("Portable candidate treatment contains a mutable decision.")
            if treatment.get("status") == "verified" and not all(
                treatment.get(key) is not None and str(treatment[key]).strip()
                for key in (
                    "source_court_id",
                    "target_kind",
                    "target_identity",
                    "reviewer",
                    "quote",
                    "locator",
                    "reviewed_at",
                )
            ):
                raise PublicCorpusError("Portable verified treatment lacks reviewed evidence.")
            if treatment.get("status") == "verified" and treatment.get("speaker") != "court":
                raise PublicCorpusError("Portable verified treatment must identify the court speaker.")
            history = treatment.get("review_history")
            if not isinstance(history, list) or not history:
                raise PublicCorpusError("Portable treatment requires immutable review history.")
            history_types: list[str] = []
            for ordinal, history_item in enumerate(history):
                if not isinstance(history_item, dict) or set(history_item) != {
                    "history_id",
                    "event_type",
                    "reviewer",
                    "payload",
                    "event_at",
                    "ordinal",
                }:
                    raise PublicCorpusError("Portable treatment history does not match its schema.")
                if history_item.get("ordinal") != ordinal:
                    raise PublicCorpusError("Portable treatment history ordinals must be contiguous.")
                if history_item.get("event_type") not in {"candidate_created", "verified", "rejected"}:
                    raise PublicCorpusError("Portable treatment history has an unknown event type.")
                if not isinstance(history_item.get("payload"), dict):
                    raise PublicCorpusError("Portable treatment history payload must be an object.")
                _parse_timestamp(str(history_item.get("event_at", "")))
                expected_history_id = _identifier(
                    "treatment-history",
                    {
                        "treatment_id": expected_treatment_id,
                        "event_type": history_item.get("event_type"),
                        "reviewer": history_item.get("reviewer"),
                        "payload": history_item.get("payload"),
                        "event_at": history_item.get("event_at"),
                    },
                )
                if history_item.get("history_id") != expected_history_id:
                    raise PublicCorpusError("Portable treatment history identity does not match.")
                history_types.append(str(history_item["event_type"]))
                validated_histories.append(
                    {**history_item, "treatment_id": expected_treatment_id}
                )
            expected_history_types = ["candidate_created"]
            if treatment.get("status") in {"verified", "rejected"}:
                expected_history_types.append(str(treatment["status"]))
            if history_types != expected_history_types:
                raise PublicCorpusError("Portable treatment history conflicts with current status.")
            expected_candidate_payload = {
                "source_chain_id": treatment.get("source_chain_id"),
                "source_court_id": treatment.get("source_court_id"),
                "target_authority_id": treatment.get("target_authority_id"),
                "target_kind": treatment.get("target_kind"),
                "target_identity": treatment.get("target_identity"),
                "treatment_type": treatment.get("treatment_type"),
                "snapshot_id": treatment.get("snapshot_id"),
                "supersedes_treatment_id": treatment.get("supersedes_treatment_id"),
            }
            if history[0].get("payload") != expected_candidate_payload:
                raise PublicCorpusError(
                    "Portable treatment candidate history conflicts with its identity."
                )
            if treatment.get("status") in {"verified", "rejected"}:
                decision_history = history[-1]
                if (
                    decision_history.get("reviewer") != treatment.get("reviewer")
                    or decision_history.get("event_at") != treatment.get("reviewed_at")
                    or decision_history.get("payload", {}).get("quote")
                    != treatment.get("quote")
                    or decision_history.get("payload", {}).get("locator")
                    != treatment.get("locator")
                    or decision_history.get("payload", {}).get("speaker")
                    != treatment.get("speaker")
                ):
                    raise PublicCorpusError(
                        "Portable treatment decision conflicts with immutable review history."
                    )
                if treatment.get("status") == "verified" and (
                    decision_history.get("payload", {}).get(
                        "confirmed_target_authority_id"
                    )
                    != treatment.get("target_authority_id")
                    or decision_history.get("payload", {}).get(
                        "target_identity_confirmed"
                    )
                    is not True
                ):
                    raise PublicCorpusError(
                        "Portable verified treatment lacks exact target confirmation."
                    )
            validated_treatments[expected_treatment_id] = treatment

        for treatment in validated_treatments.values():
            prior_id = treatment.get("supersedes_treatment_id")
            if prior_id is None:
                continue
            prior = validated_treatments.get(str(prior_id))
            if prior is None or prior.get("status") not in {"verified", "rejected"}:
                raise PublicCorpusError("Portable treatment supersession target is unavailable.")
            if (
                prior.get("source_chain_id") != treatment.get("source_chain_id")
                or prior.get("target_authority_id") != treatment.get("target_authority_id")
            ):
                raise PublicCorpusError("Portable treatment supersession changes source or target.")

        if rich_package:
            evidence_payload = {
                "seeds": seeds,
                "snapshots": snapshots,
                "observations": observations,
                "indexed_texts": indexed_texts,
                "run_pins": run_pins,
                "funnel": funnel,
                "treatments": treatments,
                "limitations": limitations,
            }
            expected_evidence_digest = _identifier("portable-evidence", evidence_payload)
            if package.get("corpus_evidence_digest") != expected_evidence_digest:
                raise PublicCorpusError("Portable corpus evidence digest does not match.")
            expected_export_id = _identifier(
                "public-corpus-export",
                {
                    "run_pins": run_pins,
                    "corpus_evidence_digest": expected_evidence_digest,
                },
            )
            if package.get("export_id") != expected_export_id:
                raise PublicCorpusError("Portable export identity does not match its evidence.")

        for seed_id, seed in sorted(validated_seeds.items()):
            registered = self.register_seed(**seed)
            if registered["seed_id"] != seed_id:
                raise PublicCorpusError("Imported seed identity changed unexpectedly.")
        for observation in validated_observations:
            stored = self.store_snapshot(
                seed_id=observation["seed_id"],
                raw=raw_by_snapshot[observation["snapshot_id"]],
                content_type=observation.get("content_type"),
                fetched_at=observation["fetched_at"],
                parser_manifest=observation["parser_manifest"],
            )
            if stored["observation_id"] != observation.get("observation_id"):
                raise PublicCorpusError("Imported observation identity changed unexpectedly.")
        for indexed in validated_indexed:
            self.index_text(
                indexed["snapshot_id"],
                indexed["text"],
                document_id=indexed.get("document_id"),
                chain_candidate_id=indexed.get("chain_candidate_id"),
                query_lane=indexed.get("query_lane"),
            )

        with self.conn:
            for event in sorted(
                validated_events,
                key=lambda item: (str(item["chain_id"]), int(item["ordinal"])),
            ):
                values = tuple(
                    event.get(key)
                    for key in (
                        "event_id",
                        "chain_id",
                        "status",
                        "snapshot_id",
                        "reason",
                        "source_role",
                        "court_id",
                        "period_id",
                        "enumerator_id",
                        "event_at",
                    )
                )
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO funnel_events(
                        event_id, chain_id, status, snapshot_id, reason, source_role,
                        court_id, period_id, enumerator_id, event_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            for state in validated_states:
                values = tuple(
                    state.get(key)
                    for key in (
                        "chain_id",
                        "status",
                        "snapshot_id",
                        "reason",
                        "source_role",
                        "court_id",
                        "period_id",
                        "enumerator_id",
                        "updated_at",
                    )
                )
                existing = self.conn.execute(
                    "SELECT * FROM funnel_state WHERE chain_id=?", (state["chain_id"],)
                ).fetchone()
                if existing is None:
                    self.conn.execute(
                        """
                        INSERT INTO funnel_state(
                            chain_id, status, snapshot_id, reason, source_role, court_id,
                            period_id, enumerator_id, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        values,
                    )
                elif tuple(existing[key] for key in (
                    "chain_id", "status", "snapshot_id", "reason", "source_role",
                    "court_id", "period_id", "enumerator_id", "updated_at",
                )) != values:
                    raise PublicCorpusError("Imported funnel state conflicts with local evidence.")

            pending_treatments = dict(validated_treatments)
            while pending_treatments:
                progressed = False
                for treatment_id, treatment in list(pending_treatments.items()):
                    prior_id = treatment.get("supersedes_treatment_id")
                    if prior_id is not None and self.conn.execute(
                        "SELECT 1 FROM treatments WHERE treatment_id=?", (prior_id,)
                    ).fetchone() is None:
                        continue
                    target_identity_json = (
                        _canonical_json(treatment["target_identity"])
                        if treatment.get("target_identity") is not None
                        else None
                    )
                    values = (
                        treatment_id,
                        treatment["source_chain_id"],
                        treatment.get("source_court_id"),
                        treatment["target_authority_id"],
                        treatment.get("target_kind"),
                        target_identity_json,
                        treatment["treatment_type"],
                        treatment["snapshot_id"],
                        prior_id,
                        treatment["status"],
                        treatment.get("reviewer"),
                        treatment.get("quote"),
                        treatment.get("locator"),
                        treatment.get("speaker"),
                        treatment["created_at"],
                        treatment.get("reviewed_at"),
                    )
                    existing = self.conn.execute(
                        "SELECT * FROM treatments WHERE treatment_id=?", (treatment_id,)
                    ).fetchone()
                    comparison_keys = (
                        "treatment_id", "source_chain_id", "source_court_id",
                        "target_authority_id", "target_kind", "target_identity_json",
                        "treatment_type", "snapshot_id", "supersedes_treatment_id",
                        "status", "reviewer", "quote", "locator", "speaker",
                        "created_at", "reviewed_at",
                    )
                    if existing is None:
                        self.conn.execute(
                            """
                            INSERT INTO treatments(
                                treatment_id, source_chain_id, source_court_id,
                                target_authority_id, target_kind, target_identity_json,
                                treatment_type, snapshot_id, supersedes_treatment_id,
                                status, reviewer, quote, locator, speaker, created_at, reviewed_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            values,
                        )
                    elif tuple(existing[key] for key in comparison_keys) != values:
                        raise PublicCorpusError("Imported treatment conflicts with local evidence.")
                    del pending_treatments[treatment_id]
                    progressed = True
                if not progressed:
                    raise PublicCorpusError("Portable treatment supersession graph is cyclic.")

            for history in sorted(
                validated_histories,
                key=lambda item: (str(item["treatment_id"]), int(item["ordinal"])),
            ):
                values = (
                    history["history_id"],
                    history["treatment_id"],
                    history["event_type"],
                    history.get("reviewer"),
                    _canonical_json(history["payload"]),
                    history["event_at"],
                )
                existing = self.conn.execute(
                    "SELECT * FROM treatment_review_history WHERE history_id=?",
                    (history["history_id"],),
                ).fetchone()
                comparison_keys = (
                    "history_id", "treatment_id", "event_type", "reviewer",
                    "payload_json", "event_at",
                )
                if existing is None:
                    self.conn.execute(
                        """
                        INSERT INTO treatment_review_history(
                            history_id, treatment_id, event_type, reviewer, payload_json, event_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        values,
                    )
                elif tuple(existing[key] for key in comparison_keys) != values:
                    raise PublicCorpusError(
                        "Imported treatment review history conflicts with local evidence."
                    )

        if rich_package:
            existing_run = self.conn.execute(
                "SELECT pin_digest, created_at FROM runs WHERE run_id=?", (run["run_id"],)
            ).fetchone()
            if existing_run is not None and (
                str(existing_run["pin_digest"]) != str(run["pin_digest"])
                or str(existing_run["created_at"]) != str(run["created_at"])
            ):
                raise RunPinConflict("Imported run conflicts with existing immutable run metadata.")
            if existing_run is not None and self.run_snapshots(str(run["run_id"])) != list(
                expected_pins
            ):
                raise RunPinConflict("Imported run conflicts with existing immutable pin order.")
            if existing_run is None:
                with self.conn:
                    self.conn.execute(
                        "INSERT INTO runs(run_id, pin_digest, created_at) VALUES (?, ?, ?)",
                        (run["run_id"], run["pin_digest"], run["created_at"]),
                    )
                    for ordinal, snapshot_id in enumerate(expected_pins):
                        self.conn.execute(
                            "INSERT INTO run_pins(run_id, snapshot_id, ordinal) VALUES (?, ?, ?)",
                            (run["run_id"], snapshot_id, ordinal),
                        )
            created = {
                "run_id": str(run["run_id"]),
                "pin_digest": str(run["pin_digest"]),
                "snapshot_ids": list(expected_pins),
            }
        else:
            created = self.create_run(str(run.get("run_id", "")), expected_pins)
        return {
            "schema_version": "1.0",
            "status": "imported",
            "run_id": created["run_id"],
            "snapshot_count": len(expected_pins),
            "manifest_sha256": declared_digest,
        }

    def index_text(
        self,
        snapshot_id: str,
        text: str,
        *,
        document_id: str | None = None,
        chain_candidate_id: str | None = None,
        query_lane: str | None = None,
    ) -> dict[str, Any]:
        if not self._snapshot_exists(snapshot_id):
            raise PublicCorpusError(f"Unknown snapshot: {snapshot_id}")
        normalized = _normalise_text(text)
        if not normalized:
            raise PublicCorpusError("Cannot index empty normalized text.")
        document_id = document_id or _identifier("document", {"snapshot_id": snapshot_id})
        chain_candidate_id = chain_candidate_id or _identifier(
            "chain-candidate", {"snapshot_id": snapshot_id}
        )
        query_lane = query_lane or "manual_public_import"
        if not all(
            isinstance(value, str) and value.strip()
            for value in (document_id, chain_candidate_id, query_lane)
        ):
            raise PublicCorpusError(
                "Search provenance requires document_id, chain_candidate_id, and query_lane."
            )
        text_hash = _sha256(normalized.encode("utf-8"))
        existing = self.conn.execute(
            """
            SELECT text_hash, document_id, chain_candidate_id, query_lane
            FROM indexed_texts WHERE snapshot_id=?
            """,
            (snapshot_id,),
        ).fetchone()
        if existing is not None:
            existing_identity = (
                str(existing["text_hash"]),
                str(existing["document_id"]),
                str(existing["chain_candidate_id"]),
                str(existing["query_lane"]),
            )
            proposed_identity = (
                text_hash,
                document_id,
                chain_candidate_id,
                query_lane,
            )
            if existing_identity != proposed_identity:
                raise PublicCorpusError(
                    "Indexed text and provenance are immutable for a snapshot; create a versioned extraction record."
                )
        if existing is None:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO indexed_texts(
                        snapshot_id, text_hash, original_text, normalized_text,
                        document_id, chain_candidate_id, query_lane, indexed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        text_hash,
                        text,
                        normalized,
                        document_id,
                        chain_candidate_id,
                        query_lane,
                        _utc_now(),
                    ),
                )
                if self.search_backend == "fts5":
                    self.conn.execute(
                        "INSERT INTO indexed_texts_fts(snapshot_id, normalized_text) VALUES (?, ?)",
                        (snapshot_id, normalized),
                    )
        return {
            "snapshot_id": snapshot_id,
            "text_hash": text_hash,
            "document_id": document_id,
            "chain_candidate_id": chain_candidate_id,
            "query_lane": query_lane,
        }

    def search(self, query: str, *, limit: int = 100) -> list[dict[str, Any]]:
        normalized_query = _normalise_text(query)
        if not normalized_query or limit <= 0:
            return []
        if self.search_backend == "fts5":
            tokens = [token for token in normalized_query.split(" ") if token]
            match_query = " AND ".join('"' + token.replace('"', '""') + '"' for token in tokens)
            candidate_rows = self.conn.execute(
                """
                SELECT i.snapshot_id, i.normalized_text, i.document_id,
                       i.chain_candidate_id, i.query_lane
                FROM indexed_texts_fts f
                JOIN indexed_texts i ON i.snapshot_id=f.snapshot_id
                WHERE indexed_texts_fts MATCH ?
                ORDER BY i.snapshot_id LIMIT ?
                """,
                (match_query, limit),
            ).fetchall()
        else:
            candidate_rows = self.conn.execute(
                """
                SELECT snapshot_id, normalized_text, document_id,
                       chain_candidate_id, query_lane FROM indexed_texts
                WHERE instr(normalized_text, ?) > 0
                ORDER BY snapshot_id LIMIT ?
                """,
                (normalized_query, limit),
            ).fetchall()
        hits: list[dict[str, Any]] = []
        first_token = normalized_query.split(" ")[0]
        for row in candidate_rows:
            text = str(row["normalized_text"])
            start = text.find(normalized_query)
            matched_text = normalized_query
            if start < 0:
                start = text.find(first_token)
                matched_text = first_token
            source = self.conn.execute(
                """
                SELECT s.canonical_url, s.role
                FROM observations o JOIN seeds s ON s.seed_id=o.seed_id
                WHERE o.snapshot_id=?
                ORDER BY CASE s.role
                    WHEN 'official_enumerator_observation' THEN 0
                    WHEN 'official_authority_seed' THEN 1
                    WHEN 'official_user_seed' THEN 2
                    ELSE 9 END,
                    s.seed_id
                LIMIT 1
                """,
                (row["snapshot_id"],),
            ).fetchone()
            hits.append(
                {
                    "snapshot_id": str(row["snapshot_id"]),
                    "document_id": str(row["document_id"]),
                    "chain_candidate_id": str(row["chain_candidate_id"]),
                    "query_lane": str(row["query_lane"]),
                    "source_url": str(source["canonical_url"]) if source else None,
                    "source_role": str(source["role"]) if source else None,
                    "start": start,
                    "end": start + len(matched_text) if start >= 0 else -1,
                    "matched_text": matched_text,
                    "backend": self.search_backend,
                    "evidence_role": "discovery_needs_full_text_legal_coding",
                }
            )
        return hits

    def record_funnel(
        self,
        chain_id: str,
        status: str,
        *,
        snapshot_id: str | None = None,
        reason: str | None = None,
        source_role: str | None = None,
        court_id: str | None = None,
        period_id: str | None = None,
        enumerator_id: str | None = None,
    ) -> dict[str, Any]:
        status = FUNNEL_ALIASES.get(status, status)
        if status not in set(FUNNEL_STAGES) | FUNNEL_FAILURES:
            raise FunnelTransitionError(f"Unknown funnel status: {status}")
        if snapshot_id is not None and not self._snapshot_exists(snapshot_id):
            raise FunnelTransitionError(f"Unknown funnel snapshot: {snapshot_id}")
        current = self.conn.execute(
            "SELECT status FROM funnel_state WHERE chain_id=?", (chain_id,)
        ).fetchone()
        current_status = str(current["status"]) if current is not None else None
        if current_status is None:
            allowed = status == "enumerated"
        elif status == current_status:
            allowed = True
        elif status in FUNNEL_FAILURES:
            allowed = True
        elif current_status in FUNNEL_FAILURES:
            allowed = status in {"card", "document_link", "payload_validated"}
        else:
            allowed = (
                current_status in FUNNEL_STAGES
                and status in FUNNEL_STAGES
                and FUNNEL_STAGES.index(status) == FUNNEL_STAGES.index(current_status) + 1
            )
        if not allowed:
            raise FunnelTransitionError(
                f"Invalid funnel transition for {chain_id}: {current_status!r} -> {status!r}"
            )
        event_at = _utc_now()
        event_id = _identifier(
            "funnel-event",
            {
                "chain_id": chain_id,
                "status": status,
                "snapshot_id": snapshot_id,
                "reason": reason,
                "source_role": source_role,
                "court_id": court_id,
                "period_id": period_id,
                "enumerator_id": enumerator_id,
                "event_at": event_at,
            },
        )
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO funnel_state(
                    chain_id, status, snapshot_id, reason, source_role, court_id,
                    period_id, enumerator_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chain_id) DO UPDATE SET
                    status=excluded.status,
                    snapshot_id=COALESCE(excluded.snapshot_id, funnel_state.snapshot_id),
                    reason=excluded.reason,
                    source_role=COALESCE(excluded.source_role, funnel_state.source_role),
                    court_id=COALESCE(excluded.court_id, funnel_state.court_id),
                    period_id=COALESCE(excluded.period_id, funnel_state.period_id),
                    enumerator_id=COALESCE(excluded.enumerator_id, funnel_state.enumerator_id),
                    updated_at=excluded.updated_at
                """,
                (
                    chain_id,
                    status,
                    snapshot_id,
                    reason,
                    source_role,
                    court_id,
                    period_id,
                    enumerator_id,
                    event_at,
                ),
            )
            self.conn.execute(
                """
                INSERT OR IGNORE INTO funnel_events(
                    event_id, chain_id, status, snapshot_id, reason, source_role,
                    court_id, period_id, enumerator_id, event_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    chain_id,
                    status,
                    snapshot_id,
                    reason,
                    source_role,
                    court_id,
                    period_id,
                    enumerator_id,
                    event_at,
                ),
            )
        return {
            "chain_id": chain_id,
            "status": status,
            "snapshot_id": snapshot_id,
            "reason": reason,
            "source_role": source_role,
            "court_id": court_id,
            "period_id": period_id,
            "enumerator_id": enumerator_id,
        }

    def funnel_report(self) -> dict[str, Any]:
        counts = {status: 0 for status in (*FUNNEL_STAGES, *sorted(FUNNEL_FAILURES))}
        for row in self.conn.execute(
            "SELECT status, COUNT(*) AS count FROM funnel_state GROUP BY status"
        ):
            counts[str(row["status"])] = int(row["count"])
        strata: dict[str, dict[str, dict[str, int]]] = {}
        for dimension in ("source_role", "court_id", "period_id", "enumerator_id"):
            dimension_counts: dict[str, dict[str, int]] = {}
            for row in self.conn.execute(
                f"""
                SELECT {dimension} AS value, status, COUNT(*) AS count
                FROM funnel_state WHERE {dimension} IS NOT NULL
                GROUP BY {dimension}, status ORDER BY {dimension}, status
                """
            ):
                value = str(row["value"])
                dimension_counts.setdefault(
                    value,
                    {status: 0 for status in (*FUNNEL_STAGES, *sorted(FUNNEL_FAILURES))},
                )[str(row["status"])] = int(row["count"])
            strata[dimension] = dimension_counts
        counts["strata"] = strata
        return counts

    def plan_refresh(
        self,
        *,
        as_of: str,
        max_age_seconds: int,
        coverage_requirements: Iterable[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if max_age_seconds < 0:
            raise PublicCorpusError("max_age_seconds must be non-negative")
        as_of_time = _parse_timestamp(as_of)
        rows = self.conn.execute(
            """
            SELECT s.seed_id, s.canonical_url, s.role, MAX(o.fetched_at) AS last_fetched_at
            FROM seeds s LEFT JOIN observations o ON o.seed_id=s.seed_id
            GROUP BY s.seed_id, s.canonical_url, s.role ORDER BY s.seed_id
            """
        ).fetchall()
        entries: list[dict[str, Any]] = []
        for row in rows:
            last_value = row["last_fetched_at"]
            if last_value is None:
                reason = "never_fetched"
            else:
                age = (as_of_time - _parse_timestamp(str(last_value))).total_seconds()
                reason = "stale" if age >= max_age_seconds else ""
            if reason:
                entries.append(
                    {
                        "seed_id": str(row["seed_id"]),
                        "url": str(row["canonical_url"]),
                        "role": str(row["role"]),
                        "last_fetched_at": str(last_value) if last_value is not None else None,
                        "reason": reason,
                    }
                )
        coverage_gaps: list[dict[str, Any]] = []
        allowed_dimensions = ("court_id", "period_id", "enumerator_id", "source_role")
        for raw_requirement in coverage_requirements or []:
            if not isinstance(raw_requirement, dict):
                raise PublicCorpusError("Coverage requirement must be an object.")
            requirement = {
                key: raw_requirement.get(key)
                for key in allowed_dimensions
                if isinstance(raw_requirement.get(key), str)
                and raw_requirement.get(key).strip()
            }
            if not requirement:
                raise PublicCorpusError(
                    "Coverage requirement needs court, period, enumerator, or source role."
                )
            clauses = [f"{key}=?" for key in requirement]
            values = [requirement[key] for key in requirement]
            observed = self.conn.execute(
                "SELECT COUNT(*) AS count FROM funnel_state WHERE "
                + " AND ".join(clauses)
                + " AND snapshot_id IS NOT NULL",
                values,
            ).fetchone()
            if observed is None or int(observed["count"]) == 0:
                coverage_gaps.append(
                    {
                        **requirement,
                        "reason": "coverage_gap_not_observed",
                        "action": "Передать ограниченный сегмент штатному коллектору; не считать нулём практики.",
                    }
                )
        coverage_gaps.sort(
            key=lambda item: tuple(str(item.get(key, "")) for key in allowed_dimensions)
        )
        payload = {
            "as_of": as_of,
            "max_age_seconds": max_age_seconds,
            "evidence_digest": self.evidence_digest(),
            "entries": entries,
            "coverage_gaps": coverage_gaps,
        }
        return {"plan_id": _identifier("refresh-plan", payload), **payload}

    def propose_treatment(
        self,
        *,
        source_chain_id: str,
        source_court_id: str | None = None,
        target_authority_id: str,
        target_kind: str | None = None,
        target_identity: dict[str, Any] | None = None,
        treatment_type: str,
        snapshot_id: str,
        supersedes_treatment_id: str | None = None,
    ) -> dict[str, Any]:
        if treatment_type not in TREATMENT_TYPES:
            raise TreatmentReviewError(f"Unsupported treatment type: {treatment_type}")
        if not self._snapshot_exists(snapshot_id):
            raise TreatmentReviewError(f"Unknown treatment snapshot: {snapshot_id}")
        if target_identity is not None and (
            not isinstance(target_identity, dict) or not target_identity
        ):
            raise TreatmentReviewError("target_identity must be a non-empty object when supplied.")
        if supersedes_treatment_id is not None:
            prior = self.conn.execute(
                "SELECT source_chain_id, target_authority_id, status FROM treatments WHERE treatment_id=?",
                (supersedes_treatment_id,),
            ).fetchone()
            if prior is None or str(prior["status"]) not in {"verified", "rejected"}:
                raise TreatmentReviewError(
                    "A replacement treatment must reference a completed prior review."
                )
            if (
                str(prior["source_chain_id"]) != source_chain_id
                or str(prior["target_authority_id"]) != target_authority_id
            ):
                raise TreatmentReviewError(
                    "A replacement treatment must preserve source and target identity."
                )
        treatment_id = _identifier(
            "treatment",
            {
                "source_chain_id": source_chain_id,
                "source_court_id": source_court_id,
                "target_authority_id": target_authority_id,
                "target_kind": target_kind,
                "target_identity": target_identity,
                "treatment_type": treatment_type,
                "snapshot_id": snapshot_id,
                "supersedes_treatment_id": supersedes_treatment_id,
            },
        )
        created_at = _utc_now()
        with self.conn:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO treatments(
                    treatment_id, source_chain_id, source_court_id,
                    target_authority_id, target_kind, target_identity_json,
                    treatment_type, snapshot_id, supersedes_treatment_id,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate', ?)
                """,
                (
                    treatment_id,
                    source_chain_id,
                    source_court_id,
                    target_authority_id,
                    target_kind,
                    _canonical_json(target_identity) if target_identity is not None else None,
                    treatment_type,
                    snapshot_id,
                    supersedes_treatment_id,
                    created_at,
                ),
            )
            self._append_treatment_history(
                treatment_id,
                event_type="candidate_created",
                reviewer=None,
                payload={
                    "source_chain_id": source_chain_id,
                    "source_court_id": source_court_id,
                    "target_authority_id": target_authority_id,
                    "target_kind": target_kind,
                    "target_identity": target_identity,
                    "treatment_type": treatment_type,
                    "snapshot_id": snapshot_id,
                    "supersedes_treatment_id": supersedes_treatment_id,
                },
                event_at=created_at,
            )
        return {
            "treatment_id": treatment_id,
            "status": "candidate",
            "supersedes_treatment_id": supersedes_treatment_id,
        }

    def _append_treatment_history(
        self,
        treatment_id: str,
        *,
        event_type: str,
        reviewer: str | None,
        payload: dict[str, Any],
        event_at: str,
    ) -> None:
        history_id = _identifier(
            "treatment-history",
            {
                "treatment_id": treatment_id,
                "event_type": event_type,
                "reviewer": reviewer,
                "payload": payload,
                "event_at": event_at,
            },
        )
        self.conn.execute(
            """
            INSERT OR IGNORE INTO treatment_review_history(
                history_id, treatment_id, event_type, reviewer, payload_json, event_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                history_id,
                treatment_id,
                event_type,
                reviewer,
                _canonical_json(payload),
                event_at,
            ),
        )

    def review_treatment(
        self,
        treatment_id: str,
        *,
        decision: str,
        reviewer: str,
        quote: str | None = None,
        locator: str | None = None,
        speaker: str | None = None,
        confirmed_target_authority_id: str | None = None,
        target_identity_confirmed: bool = False,
        reviewed_at: str | None = None,
    ) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM treatments WHERE treatment_id=?", (treatment_id,)
        ).fetchone()
        if row is None:
            raise TreatmentReviewError(f"Unknown treatment candidate: {treatment_id}")
        if decision not in {"verified", "rejected"}:
            raise TreatmentReviewError("Treatment decision must be verified or rejected.")
        if not reviewer.strip():
            raise TreatmentReviewError("Treatment review requires a reviewer.")
        if decision == "verified":
            if not all(
                value is not None and str(value).strip()
                for value in (
                    quote,
                    locator,
                    row["source_court_id"],
                    row["target_kind"],
                    row["target_identity_json"],
                )
            ) or speaker != "court":
                raise TreatmentReviewError(
                    "Verified treatment requires source court, court speaker, quote, locator, and structured target identity."
                )
            if (
                confirmed_target_authority_id != row["target_authority_id"]
                or target_identity_confirmed is not True
            ):
                raise TreatmentReviewError(
                    "Verified treatment requires reviewed confirmation of the exact target identity."
                )
        existing_status = str(row["status"])
        if existing_status != "candidate":
            raise TreatmentReviewError("Treatment review is immutable after the first decision.")
        decided_at = reviewed_at or _utc_now()
        _parse_timestamp(decided_at)
        with self.conn:
            self.conn.execute(
                """
                UPDATE treatments SET status=?, reviewer=?, quote=?, locator=?, speaker=?, reviewed_at=?
                WHERE treatment_id=?
                """,
                (decision, reviewer.strip(), quote, locator, speaker, decided_at, treatment_id),
            )
            self._append_treatment_history(
                treatment_id,
                event_type=decision,
                reviewer=reviewer.strip(),
                payload={
                    "quote": quote,
                    "locator": locator,
                    "speaker": speaker,
                    "confirmed_target_authority_id": confirmed_target_authority_id,
                    "target_identity_confirmed": target_identity_confirmed,
                },
                event_at=decided_at,
            )
        return {
            "treatment_id": treatment_id,
            "status": decision,
            "reviewer": reviewer.strip(),
            "quote": quote,
            "locator": locator,
            "speaker": speaker,
            "reviewed_at": decided_at,
        }

    def treatment_history(self, treatment_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT history_id, event_type, reviewer, payload_json, event_at
            FROM treatment_review_history WHERE treatment_id=?
            ORDER BY rowid
            """,
            (treatment_id,),
        ).fetchall()
        return [
            {
                "history_id": str(row["history_id"]),
                "treatment_id": treatment_id,
                "event_type": str(row["event_type"]),
                "reviewer": row["reviewer"],
                "payload": json.loads(str(row["payload_json"])),
                "event_at": str(row["event_at"]),
            }
            for row in rows
        ]

    def list_treatments(self, *, verified_only: bool = False) -> list[dict[str, Any]]:
        where = "WHERE status='verified'" if verified_only else ""
        rows = self.conn.execute(
            f"""
            SELECT treatment_id, source_chain_id, source_court_id,
                   target_authority_id, target_kind, target_identity_json,
                   treatment_type, snapshot_id, supersedes_treatment_id, status,
                   reviewer, quote, locator, speaker, reviewed_at
            FROM treatments {where} ORDER BY treatment_id
            """
        ).fetchall()
        records: list[dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            raw_identity = record.pop("target_identity_json", None)
            record["target_identity"] = (
                json.loads(str(raw_identity)) if raw_identity is not None else None
            )
            records.append(record)
        return records

    def evidence_digest(self) -> str:
        seeds = [
            dict(row)
            for row in self.conn.execute(
                "SELECT seed_id, canonical_url, role FROM seeds ORDER BY seed_id"
            ).fetchall()
        ]
        snapshots = [
            dict(row)
            for row in self.conn.execute(
                "SELECT snapshot_id, raw_sha256, byte_length FROM snapshots ORDER BY snapshot_id"
            ).fetchall()
        ]
        indexed = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT snapshot_id, text_hash, document_id,
                       chain_candidate_id, query_lane
                FROM indexed_texts ORDER BY snapshot_id
                """
            ).fetchall()
        ]
        funnel_states = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT chain_id, status, snapshot_id, reason, source_role,
                       court_id, period_id, enumerator_id
                FROM funnel_state ORDER BY chain_id
                """
            ).fetchall()
        ]
        verified_treatments = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT treatment_id, source_chain_id, source_court_id,
                       target_authority_id, target_kind, target_identity_json,
                       snapshot_id, treatment_type, supersedes_treatment_id,
                       reviewer, quote, locator, speaker, created_at, reviewed_at
                FROM treatments WHERE status='verified' ORDER BY treatment_id
                """
            ).fetchall()
        ]
        treatment_history = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT h.history_id, h.treatment_id, h.event_type, h.reviewer,
                       h.payload_json, h.event_at
                FROM treatment_review_history h
                JOIN treatments t ON t.treatment_id=h.treatment_id
                WHERE t.status='verified'
                ORDER BY h.treatment_id, h.rowid
                """
            ).fetchall()
        ]
        return _identifier(
            "corpus-evidence",
            {
                "seeds": seeds,
                "snapshots": snapshots,
                "indexed": indexed,
                "funnel_states": funnel_states,
                "verified_treatments": verified_treatments,
                "treatment_history": treatment_history,
            },
        )
