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
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, urldefrag, urlparse, urlunparse


PUBLIC_SEED_ROLES = {
    "official_enumerator_observation",
    "official_user_seed",
    "official_authority_seed",
    "discovery_only",
}
OFFICIAL_EVIDENCE_SEED_ROLES = {
    "official_enumerator_observation",
    "official_user_seed",
    "official_authority_seed",
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
RFC3339_AWARE_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?"
    r"(?:[Zz]|[+-]\d{2}:\d{2})"
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


def _consistent_read(method: Any) -> Any:
    """Run a multi-query producer against one SQLite read snapshot."""

    @wraps(method)
    def wrapped(self: "PublicCorpus", *args: Any, **kwargs: Any) -> Any:
        owns_transaction = not self.conn.in_transaction
        if owns_transaction:
            self.conn.execute("BEGIN")
        try:
            return method(self, *args, **kwargs)
        finally:
            if owns_transaction and self.conn.in_transaction:
                self.conn.rollback()

    return wrapped


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise PublicCorpusError(
            "Canonical JSON payload contains an unsupported or non-finite value."
        ) from exc


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _identifier(prefix: str, value: Any) -> str:
    return f"{prefix}-sha256:{_sha256(_canonical_json(value).encode('utf-8'))}"


def _normalise_text(value: str) -> str:
    normalised = unicodedata.normalize("NFKC", value).casefold().replace("ё", "е")
    return re.sub(r"\s+", " ", normalised).strip()


def treatment_quality_proposition(
    *,
    status: str,
    source_chain_id: str,
    treatment_type: str,
    target_authority_id: str,
    decision_reason: str | None = None,
) -> str:
    """Build the exact status-aware proposition used by quality exports."""

    if status == "verified":
        return (
            f"Судебный акт {source_chain_id} содержит проверенное отношение "
            f"{treatment_type} к акту {target_authority_id}."
        )
    if status == "rejected" and decision_reason is not None:
        return (
            f"Проверяющий отклонил предполагаемое отношение {treatment_type} "
            f"акта {source_chain_id} к акту {target_authority_id}: "
            f"{decision_reason}"
        )
    raise ValueError("Treatment quality proposition requires a resolved status.")


def _canonical_identifier(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    if any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in value):
        return None
    normalized = " ".join(value.split())
    return normalized if normalized == value else None


def _is_canonical_identifier(value: Any) -> bool:
    canonical = _canonical_identifier(value)
    return canonical is not None and canonical == value


def _parse_timestamp(value: str) -> datetime:
    try:
        normalized = value[:-1] + "+00:00" if value[-1:] in {"Z", "z"} else value
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError) as exc:
        raise PublicCorpusError(f"Invalid ISO timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _aware_rfc3339_datetime(value: Any) -> bool:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or RFC3339_AWARE_RE.fullmatch(value) is None
    ):
        return False
    try:
        return _parse_timestamp(value).utcoffset() is not None
    except PublicCorpusError:
        return False


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


def official_public_url_allowed(value: Any) -> bool:
    """Use the corpus privacy and official-host boundary for portable evidence."""

    if not isinstance(value, str):
        return False
    try:
        canonical = _canonical_public_url(value)
    except PublicCorpusError:
        return False
    return _official_host_allowed(canonical)


def public_url_allowed(value: Any) -> bool:
    """Apply the reusable-corpus privacy boundary without requiring an official host."""

    if not isinstance(value, str):
        return False
    try:
        _canonical_public_url(value)
    except PublicCorpusError:
        return False
    return True


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


def _database_file_fingerprint(path: Path) -> tuple[int, int, int, int, str]:
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return (
        stat.st_dev,
        stat.st_ino,
        stat.st_size,
        stat.st_mtime_ns,
        digest.hexdigest(),
    )


class PublicCorpus:
    """A local immutable public corpus with optional SQLite FTS5 search."""

    _read_only_database_path: Path | None
    _read_only_database_fingerprint: tuple[int, int, int, int, str] | None

    def __init__(self, root: Path, *, force_fallback_search: bool = False) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.objects = self.root / "objects" / "sha256"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.root / "public-corpus.sqlite3")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._read_only_database_path = None
        self._read_only_database_fingerprint = None
        self._create_schema()
        self.search_backend = self._configure_search(force_fallback_search)

    @classmethod
    def open_read_only(cls, root: Path) -> "PublicCorpus":
        """Open an existing cache without creating or migrating anything."""

        requested_root = Path(root).expanduser()
        try:
            resolved_root = requested_root.resolve(strict=True)
        except OSError as exc:
            raise PublicCorpusError(
                "Корневая папка публичного корпуса не существует."
            ) from exc
        if not resolved_root.is_dir():
            raise PublicCorpusError(
                "Корневая папка публичного корпуса должна быть каталогом."
            )
        database_path = resolved_root / "public-corpus.sqlite3"
        if (
            not database_path.exists()
            or not database_path.is_file()
            or database_path.is_symlink()
        ):
            raise PublicCorpusError(
                "В корневой папке нет обычного файла public-corpus.sqlite3."
            )
        try:
            with database_path.open("rb") as stream:
                header = stream.read(20)
            initial_database_fingerprint = _database_file_fingerprint(database_path)
        except OSError as exc:
            raise PublicCorpusError(
                "Не удалось прочитать заголовок public-corpus.sqlite3."
            ) from exc
        auxiliary_paths = tuple(
            Path(str(database_path) + suffix)
            for suffix in ("-wal", "-shm", "-journal")
        )
        if (
            len(header) < 20
            or header[:16] != b"SQLite format 3\x00"
        ):
            raise PublicCorpusError("public-corpus.sqlite3 не является базой SQLite 3.")
        if b"\x02" in header[18:20] or any(
            path.exists() for path in auxiliary_paths
        ):
            raise PublicCorpusError(
                "Проверка качества не открывает WAL/журналируемый корпус: "
                "завершите запись и переведите отдельную проверяемую копию SQLite "
                "в режим DELETE."
            )

        instance = cls.__new__(cls)
        instance.root = resolved_root
        instance.objects = resolved_root / "objects" / "sha256"
        try:
            instance.conn = sqlite3.connect(
                f"{database_path.as_uri()}?mode=ro",
                uri=True,
            )
            instance.conn.row_factory = sqlite3.Row
            instance.conn.execute("PRAGMA query_only=ON")
            instance.conn.execute("PRAGMA foreign_keys=ON")
            required_tables = {
                "seeds",
                "snapshots",
                "observations",
                "indexed_texts",
                "funnel_state",
                "treatments",
                "treatment_review_history",
            }
            actual_tables = {
                str(row["name"])
                for row in instance.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            missing_tables = sorted(required_tables - actual_tables)
            if missing_tables:
                raise PublicCorpusError(
                    "Публичный корпус не содержит обязательные таблицы: "
                    + ", ".join(missing_tables)
                )
        except (OSError, sqlite3.Error):
            if hasattr(instance, "conn"):
                instance.conn.close()
            raise PublicCorpusError(
                "Не удалось открыть публичный корпус только для чтения."
            )
        except Exception:
            if hasattr(instance, "conn"):
                instance.conn.close()
            raise
        instance.search_backend = "read_only"
        instance._read_only_database_path = database_path
        instance._read_only_database_fingerprint = initial_database_fingerprint
        if instance._read_only_store_issue_ids():
            instance.conn.close()
            raise PublicCorpusError(
                "Публичный корпус изменился во время открытия только для чтения."
            )
        return instance

    def _read_only_store_issue_ids(self) -> list[str]:
        database_path = getattr(self, "_read_only_database_path", None)
        expected_fingerprint = getattr(
            self, "_read_only_database_fingerprint", None
        )
        if not isinstance(database_path, Path) or expected_fingerprint is None:
            return []
        issues: list[str] = []
        if database_path.is_symlink():
            issues.append("live_cache_database_symlinked")
        if any(
            Path(str(database_path) + suffix).exists()
            for suffix in ("-wal", "-shm", "-journal")
        ):
            issues.append("live_cache_journal_present")
        try:
            with database_path.open("rb") as stream:
                header = stream.read(20)
            if (
                len(header) < 20
                or header[:16] != b"SQLite format 3\x00"
                or b"\x02" in header[18:20]
            ):
                issues.append("live_cache_database_header_invalid")
            current_fingerprint = _database_file_fingerprint(database_path)
        except OSError:
            issues.append("live_cache_database_unreadable")
        else:
            if current_fingerprint != expected_fingerprint:
                issues.append("live_cache_database_changed")
        return sorted(set(issues))

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
        branched_supersession = self.conn.execute(
            """
            SELECT 1
            FROM treatments
            WHERE supersedes_treatment_id IS NOT NULL
            GROUP BY supersedes_treatment_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        ).fetchone()
        if branched_supersession is None:
            self.conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_treatments_one_replacement
                    ON treatments(supersedes_treatment_id)
                    WHERE supersedes_treatment_id IS NOT NULL
                """
            )
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
        if not _aware_rfc3339_datetime(fetched_at):
            raise PublicCorpusError(
                "fetched_at должен содержать полные дату, время с секундами "
                "и часовой пояс RFC 3339."
            )
        if _parse_timestamp(fetched_at) > datetime.now(timezone.utc):
            raise PublicCorpusError("fetched_at не может находиться в будущем.")
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

    def _snapshot_integrity(self, snapshot_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            """
            SELECT snapshot_id, raw_sha256, object_path, byte_length
            FROM snapshots WHERE snapshot_id=?
            """,
            (snapshot_id,),
        ).fetchone()
        if row is None:
            return {
                "valid": False,
                "stored_sha256": None,
                "observed_sha256": None,
                "stored_byte_length": None,
                "observed_byte_length": None,
                "path_valid": False,
                "readable": False,
            }
        stored_sha256 = str(row["raw_sha256"])
        stored_length = int(row["byte_length"])
        object_path = Path(str(row["object_path"]))
        expected_path = self.objects / stored_sha256[:2] / f"{stored_sha256}.bin"
        try:
            canonical_objects_root = self.objects.resolve(strict=True)
            canonical_object_path = object_path.resolve(strict=True)
            canonical_expected_path = expected_path.resolve(strict=True)
        except OSError:
            canonical_objects_root = None
            canonical_object_path = None
            canonical_expected_path = None
        contained_in_objects = False
        if canonical_objects_root is not None and canonical_object_path is not None:
            try:
                canonical_object_path.relative_to(canonical_objects_root)
            except ValueError:
                pass
            else:
                contained_in_objects = True
        expected_components_are_plain = not self.root.is_symlink()
        try:
            expected_relative = expected_path.relative_to(self.root)
        except ValueError:
            expected_components_are_plain = False
        else:
            component = self.root
            for part in expected_relative.parts:
                component = component / part
                if component.is_symlink():
                    expected_components_are_plain = False
                    break
        path_valid = (
            canonical_object_path is not None
            and canonical_object_path == canonical_expected_path
            and contained_in_objects
            and expected_components_are_plain
            and object_path.is_file()
            and not object_path.is_symlink()
        )
        observed_sha256: str | None = None
        observed_length: int | None = None
        readable = False
        if path_valid:
            try:
                raw = object_path.read_bytes()
            except OSError:
                pass
            else:
                readable = True
                observed_sha256 = _sha256(raw)
                observed_length = len(raw)
        valid = (
            path_valid
            and readable
            and re.fullmatch(r"[0-9a-f]{64}", stored_sha256) is not None
            and snapshot_id == f"snapshot-sha256:{stored_sha256}"
            and observed_sha256 == stored_sha256
            and observed_length == stored_length
        )
        return {
            "valid": valid,
            "stored_sha256": stored_sha256,
            "observed_sha256": observed_sha256,
            "stored_byte_length": stored_length,
            "observed_byte_length": observed_length,
            "path_valid": path_valid,
            "readable": readable,
        }

    def _indexed_text_integrity(self, snapshot_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            """
            SELECT text_hash, original_text, normalized_text
            FROM indexed_texts WHERE snapshot_id=?
            """,
            (snapshot_id,),
        ).fetchone()
        if row is None:
            return {
                "valid": False,
                "stored_text_sha256": None,
                "observed_text_sha256": None,
                "normalized_text_matches": False,
            }
        original_text = row["original_text"]
        normalized_text = row["normalized_text"]
        if not isinstance(original_text, str) or not isinstance(normalized_text, str):
            return {
                "valid": False,
                "stored_text_sha256": row["text_hash"],
                "observed_text_sha256": None,
                "normalized_text_matches": False,
            }
        observed_normalized = _normalise_text(original_text)
        observed_hash = _sha256(observed_normalized.encode("utf-8"))
        stored_hash = str(row["text_hash"])
        normalized_matches = normalized_text == observed_normalized
        return {
            "valid": stored_hash == observed_hash and normalized_matches,
            "stored_text_sha256": stored_hash,
            "observed_text_sha256": observed_hash,
            "normalized_text_matches": normalized_matches,
        }

    def _cache_integrity_issue_ids(self) -> list[str]:
        """Return deterministic issues that make a live quality read unsafe."""

        issues: set[str] = set(self._read_only_store_issue_ids())
        for row in self.conn.execute("PRAGMA foreign_key_check").fetchall():
            table_name = str(row[0])
            row_id = str(row[1])
            parent_name = str(row[2])
            foreign_key_id = str(row[3])
            issues.add(
                "foreign_key_violation:"
                f"{table_name}:{row_id}:{parent_name}:{foreign_key_id}"
            )
        for row in self.conn.execute(
            "SELECT snapshot_id FROM snapshots ORDER BY snapshot_id"
        ).fetchall():
            snapshot_id = str(row["snapshot_id"])
            if not self._snapshot_integrity(snapshot_id)["valid"]:
                issues.add(f"snapshot_object_integrity_invalid:{snapshot_id}")
        for row in self.conn.execute(
            "SELECT snapshot_id FROM indexed_texts ORDER BY snapshot_id"
        ).fetchall():
            snapshot_id = str(row["snapshot_id"])
            if not self._indexed_text_integrity(snapshot_id)["valid"]:
                issues.add(f"indexed_text_integrity_invalid:{snapshot_id}")
        return sorted(issues)

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

    @_consistent_read
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
        observed_snapshot_roles = {
            (
                str(observation["snapshot_id"]),
                str(validated_seeds[str(observation["seed_id"])]["role"]),
            )
            for observation in validated_observations
        }

        def validate_funnel_source_binding(
            item: Mapping[str, Any], *, label: str
        ) -> None:
            role = item.get("source_role")
            snapshot_id = item.get("snapshot_id")
            if role is not None and role not in PUBLIC_SEED_ROLES:
                raise PublicCorpusError(
                    f"Portable funnel {label} has an unknown source role."
                )
            if (
                role is not None
                and snapshot_id is not None
                and (str(snapshot_id), str(role)) not in observed_snapshot_roles
            ):
                raise PublicCorpusError(
                    f"Portable funnel {label} source role is not bound to its observation."
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
            validate_funnel_source_binding(state, label="state")
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
            validate_funnel_source_binding(event, label="event")
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
            created_at = treatment.get("created_at")
            reviewed_at = treatment.get("reviewed_at")
            if (
                not _aware_rfc3339_datetime(created_at)
                or _parse_timestamp(str(created_at)) > datetime.now(timezone.utc)
            ):
                raise PublicCorpusError(
                    "Portable treatment created_at must be an aware RFC 3339 time not in the future."
                )
            if reviewed_at is not None and (
                not _aware_rfc3339_datetime(reviewed_at)
                or _parse_timestamp(str(reviewed_at)) > datetime.now(timezone.utc)
                or _parse_timestamp(str(reviewed_at))
                < _parse_timestamp(str(created_at))
            ):
                raise PublicCorpusError(
                    "Portable treatment review chronology is invalid."
                )
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
                if not _aware_rfc3339_datetime(history_item.get("event_at")):
                    raise PublicCorpusError(
                        "Portable treatment history requires aware RFC 3339 event times."
                    )
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
            if (
                history[0].get("reviewer") is not None
                or history[0].get("event_at") != treatment.get("created_at")
            ):
                raise PublicCorpusError(
                    "Portable treatment candidate history conflicts with creation metadata."
                )
            if treatment.get("status") in {"verified", "rejected"}:
                decision_history = history[-1]
                decision_payload = decision_history.get("payload", {})
                if (
                    decision_history.get("reviewer") != treatment.get("reviewer")
                    or decision_history.get("event_at") != treatment.get("reviewed_at")
                    or set(decision_payload)
                    != {
                        "quote",
                        "locator",
                        "speaker",
                        "confirmed_target_authority_id",
                        "target_identity_confirmed",
                        "decision_reason",
                    }
                    or decision_payload.get("quote") != treatment.get("quote")
                    or decision_payload.get("locator") != treatment.get("locator")
                    or decision_payload.get("speaker") != treatment.get("speaker")
                ):
                    raise PublicCorpusError(
                        "Portable treatment decision conflicts with immutable review history."
                    )
                decision_reason = decision_payload.get("decision_reason")
                if treatment.get("status") == "verified" and decision_reason is not None:
                    raise PublicCorpusError(
                        "Portable verified treatment must not contain a rejection reason."
                    )
                if treatment.get("status") == "rejected" and not _is_canonical_identifier(
                    decision_reason
                ):
                    raise PublicCorpusError(
                        "Portable rejected treatment requires a canonical decision reason."
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
            if _parse_timestamp(str(prior.get("reviewed_at"))) > _parse_timestamp(
                str(treatment.get("created_at"))
            ):
                raise PublicCorpusError(
                    "Portable treatment supersession predates the completed prior review."
                )

        successor_counts: dict[str, int] = {}
        for treatment in validated_treatments.values():
            prior_id = treatment.get("supersedes_treatment_id")
            if prior_id is not None:
                successor_counts[str(prior_id)] = (
                    successor_counts.get(str(prior_id), 0) + 1
                )
        if any(count != 1 for count in successor_counts.values()):
            raise PublicCorpusError(
                "Portable treatment supersession must be a single-successor chain."
            )

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
            _is_canonical_identifier(value)
            for value in (document_id, chain_candidate_id, query_lane)
        ):
            raise PublicCorpusError(
                "Search provenance requires canonical document_id, "
                "chain_candidate_id, and query_lane."
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
        if source_role is not None and source_role not in PUBLIC_SEED_ROLES:
            raise FunnelTransitionError(f"Unknown funnel source role: {source_role}")
        current = self.conn.execute(
            "SELECT status, snapshot_id, source_role FROM funnel_state WHERE chain_id=?",
            (chain_id,),
        ).fetchone()
        current_status = str(current["status"]) if current is not None else None
        effective_snapshot_id = snapshot_id or (
            str(current["snapshot_id"])
            if current is not None and current["snapshot_id"] is not None
            else None
        )
        effective_source_role = source_role or (
            str(current["source_role"])
            if current is not None and current["source_role"] is not None
            else None
        )
        if effective_source_role is not None and effective_snapshot_id is not None:
            bound_observation = (
                self.conn.execute(
                    """
                    SELECT seed.canonical_url
                    FROM observations o
                    JOIN seeds seed ON seed.seed_id=o.seed_id
                    WHERE o.snapshot_id=? AND seed.role=?
                    ORDER BY seed.canonical_url LIMIT 1
                    """,
                    (effective_snapshot_id, effective_source_role),
                ).fetchone()
            )
            if bound_observation is None or (
                effective_source_role in OFFICIAL_EVIDENCE_SEED_ROLES
                and not official_public_url_allowed(bound_observation["canonical_url"])
            ):
                raise FunnelTransitionError(
                    "Funnel source_role must match an observation for the effective snapshot."
                )
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

    @_consistent_read
    def plan_refresh(
        self,
        *,
        as_of: str,
        max_age_seconds: int,
        coverage_requirements: Iterable[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if (
            isinstance(max_age_seconds, bool)
            or not isinstance(max_age_seconds, int)
            or max_age_seconds < 0
        ):
            raise PublicCorpusError("max_age_seconds must be non-negative")
        if not _aware_rfc3339_datetime(as_of):
            raise PublicCorpusError(
                "--as-of должен содержать полные дату, время с секундами "
                "и часовой пояс RFC 3339."
            )
        as_of_time = _parse_timestamp(as_of)
        if as_of_time > datetime.now(timezone.utc):
            raise PublicCorpusError("--as-of не может находиться в будущем.")
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
            elif not _aware_rfc3339_datetime(str(last_value)):
                reason = "invalid_fetched_at"
            else:
                last_time = _parse_timestamp(str(last_value))
                if last_time > as_of_time:
                    reason = "future_fetched_at"
                else:
                    age = (as_of_time - last_time).total_seconds()
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
        normalized_requirements: list[dict[str, str]] = []
        coverage_gaps: list[dict[str, Any]] = []
        allowed_dimensions = ("court_id", "period_id", "enumerator_id", "source_role")
        seen_requirements: set[str] = set()
        for raw_requirement in coverage_requirements or []:
            if not isinstance(raw_requirement, dict):
                raise PublicCorpusError("Coverage requirement must be an object.")
            if not raw_requirement or not set(raw_requirement).issubset(allowed_dimensions):
                raise PublicCorpusError(
                    "Coverage requirement contains an unsupported dimension."
                )
            if not all(
                isinstance(raw_requirement.get(key), str)
                and bool(raw_requirement[key].strip())
                for key in raw_requirement
            ):
                raise PublicCorpusError(
                    "Coverage requirement values must be non-empty strings."
                )
            requirement = {
                key: str(raw_requirement[key])
                for key in allowed_dimensions
                if key in raw_requirement
            }
            if any(
                value != " ".join(value.split())
                or any(
                    unicodedata.category(character) in {"Cc", "Cf", "Cs"}
                    for character in value
                )
                for value in requirement.values()
            ):
                raise PublicCorpusError(
                    "Coverage requirement identifiers must use canonical whitespace."
                )
            if (
                "source_role" in requirement
                and requirement["source_role"] not in PUBLIC_SEED_ROLES
            ):
                raise PublicCorpusError("Coverage requirement source_role is unsupported.")
            requirement_digest = _sha256(
                _canonical_json(requirement).encode("utf-8")
            )
            if requirement_digest in seen_requirements:
                continue
            seen_requirements.add(requirement_digest)
            normalized_requirements.append(requirement)
            clauses = [f"f.{key}=?" for key in requirement]
            values = [requirement[key] for key in requirement]
            scope_rows = self.conn.execute(
                """
                SELECT f.chain_id, f.status, f.snapshot_id, f.source_role
                FROM funnel_state f
                WHERE """
                + " AND ".join(clauses)
                + " ORDER BY f.chain_id",
                values,
            ).fetchall()

            def chain_is_observed(row: sqlite3.Row) -> bool:
                snapshot_id = row["snapshot_id"]
                status = str(row["status"])
                source_role = row["source_role"]
                if (
                    not isinstance(snapshot_id, str)
                    or status
                    not in {
                        "full_text_extracted",
                        "indexed",
                        "screened",
                        "coded",
                        "approved_independent_chain",
                    }
                    or source_role not in OFFICIAL_EVIDENCE_SEED_ROLES
                    or not self._snapshot_integrity(snapshot_id)["valid"]
                    or (
                        status != "full_text_extracted"
                        and not self._indexed_text_integrity(snapshot_id)["valid"]
                    )
                ):
                    return False
                observation_rows = self.conn.execute(
                    """
                    SELECT seed.canonical_url, seed.role
                    FROM observations o
                    JOIN seeds seed ON seed.seed_id=o.seed_id
                    WHERE o.snapshot_id=? AND seed.role=?
                    ORDER BY seed.canonical_url
                    """,
                    (snapshot_id, source_role),
                ).fetchall()
                return any(
                    observation["role"] in OFFICIAL_EVIDENCE_SEED_ROLES
                    and official_public_url_allowed(observation["canonical_url"])
                    for observation in observation_rows
                )

            observed = bool(scope_rows) and all(
                chain_is_observed(row) for row in scope_rows
            )
            if not observed:
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
        normalized_requirements.sort(
            key=lambda item: tuple(str(item.get(key, "")) for key in allowed_dimensions)
        )
        payload = {
            "as_of": as_of,
            "max_age_seconds": max_age_seconds,
            "evidence_digest": self.evidence_digest(),
            "treatment_ids": self.treatment_ids(),
            "treatment_population_sha256": self.treatment_population_sha256(),
            "coverage_requirements": normalized_requirements,
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
        for label, value in (
            ("source_chain_id", source_chain_id),
            ("source_court_id", source_court_id),
            ("target_authority_id", target_authority_id),
            ("target_kind", target_kind),
        ):
            if not _is_canonical_identifier(value):
                raise TreatmentReviewError(
                    f"{label} must be a non-empty canonical identifier."
                )
        if treatment_type not in TREATMENT_TYPES:
            raise TreatmentReviewError(f"Unsupported treatment type: {treatment_type}")
        if not self._snapshot_exists(snapshot_id):
            raise TreatmentReviewError(f"Unknown treatment snapshot: {snapshot_id}")
        if not isinstance(target_identity, dict) or not target_identity:
            raise TreatmentReviewError("target_identity must be a non-empty object.")
        try:
            canonical_target_identity = _canonical_json(target_identity)
        except PublicCorpusError as exc:
            raise TreatmentReviewError(
                "target_identity must contain finite JSON-compatible values."
            ) from exc
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
            existing_replacement = self.conn.execute(
                "SELECT treatment_id FROM treatments WHERE supersedes_treatment_id=?",
                (supersedes_treatment_id,),
            ).fetchone()
            if existing_replacement is not None:
                raise TreatmentReviewError(
                    "A completed treatment already has a replacement candidate."
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
            self.conn.execute("BEGIN IMMEDIATE")
            if supersedes_treatment_id is not None:
                concurrent_replacement = self.conn.execute(
                    "SELECT treatment_id FROM treatments WHERE supersedes_treatment_id=?",
                    (supersedes_treatment_id,),
                ).fetchone()
                if concurrent_replacement is not None:
                    raise TreatmentReviewError(
                        "A completed treatment already has a replacement candidate."
                    )
            inserted = self.conn.execute(
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
                    canonical_target_identity,
                    treatment_type,
                    snapshot_id,
                    supersedes_treatment_id,
                    created_at,
                ),
            )
            if inserted.rowcount == 1:
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
        current = self.conn.execute(
            "SELECT status FROM treatments WHERE treatment_id=?", (treatment_id,)
        ).fetchone()
        if current is None:
            raise TreatmentReviewError(
                "Another replacement candidate already won the supersession race."
            )
        return {
            "treatment_id": treatment_id,
            "status": str(current["status"]),
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
        decision_reason: str | None = None,
        reviewed_at: str | None = None,
    ) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM treatments WHERE treatment_id=?", (treatment_id,)
        ).fetchone()
        if row is None:
            raise TreatmentReviewError(f"Unknown treatment candidate: {treatment_id}")
        try:
            stored_target_identity = json.loads(str(row["target_identity_json"]))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise TreatmentReviewError(
                "Treatment review requires a valid structured target identity."
            ) from exc
        if not isinstance(stored_target_identity, dict) or not stored_target_identity:
            raise TreatmentReviewError(
                "Treatment review requires a non-empty structured target identity."
            )
        if decision not in {"verified", "rejected"}:
            raise TreatmentReviewError("Treatment decision must be verified or rejected.")
        if not _is_canonical_identifier(reviewer):
            raise TreatmentReviewError("Treatment review requires a reviewer.")
        if not self._snapshot_integrity(str(row["snapshot_id"]))["valid"]:
            raise TreatmentReviewError(
                "Treatment review requires intact content-addressed snapshot bytes."
            )
        if not self._indexed_text_integrity(str(row["snapshot_id"]))["valid"]:
            raise TreatmentReviewError(
                "Treatment review requires intact indexed full text and text hash."
            )
        if decision == "verified":
            if decision_reason is not None:
                raise TreatmentReviewError(
                    "Verified treatment must not include a rejection reason."
                )
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
            indexed = self.conn.execute(
                """
                SELECT i.original_text, i.chain_candidate_id,
                       i.document_id, i.text_hash, s.raw_sha256,
                       (
                         SELECT seed.canonical_url
                         FROM observations o
                         JOIN seeds seed ON seed.seed_id=o.seed_id
                         WHERE o.snapshot_id=i.snapshot_id
                           AND seed.role IN (
                             'official_enumerator_observation',
                             'official_user_seed',
                             'official_authority_seed'
                           )
                         ORDER BY CASE seed.role
                           WHEN 'official_enumerator_observation' THEN 0
                           WHEN 'official_authority_seed' THEN 1
                           WHEN 'official_user_seed' THEN 2
                           ELSE 9 END,
                           seed.canonical_url
                         LIMIT 1
                       ) AS official_url,
                       (
                         SELECT seed.role
                         FROM observations o
                         JOIN seeds seed ON seed.seed_id=o.seed_id
                         WHERE o.snapshot_id=i.snapshot_id
                           AND seed.role IN (
                             'official_enumerator_observation',
                             'official_user_seed',
                             'official_authority_seed'
                           )
                         ORDER BY CASE seed.role
                           WHEN 'official_enumerator_observation' THEN 0
                           WHEN 'official_authority_seed' THEN 1
                           WHEN 'official_user_seed' THEN 2
                           ELSE 9 END,
                           seed.canonical_url
                         LIMIT 1
                       ) AS source_role
                FROM indexed_texts i
                JOIN snapshots s ON s.snapshot_id=i.snapshot_id
                WHERE i.snapshot_id=?
                """,
                (row["snapshot_id"],),
            ).fetchone()
            if (
                indexed is None
                or indexed["chain_candidate_id"] != row["source_chain_id"]
                or not _is_canonical_identifier(indexed["document_id"])
                or indexed["source_role"] not in OFFICIAL_EVIDENCE_SEED_ROLES
                or not official_public_url_allowed(indexed["official_url"])
                or _normalise_text(str(quote))
                not in _normalise_text(str(indexed["original_text"]))
            ):
                raise TreatmentReviewError(
                    "Verified treatment requires a matching quote in indexed "
                    "official full text bound to the same source chain."
                )
        else:
            if not _is_canonical_identifier(decision_reason):
                raise TreatmentReviewError(
                    "Rejected treatment requires a non-empty canonical decision reason."
                )
            if quote is None and (locator is not None or speaker is not None):
                raise TreatmentReviewError(
                    "Rejected treatment without a quote must not include a locator or speaker."
                )
            if (
                target_identity_confirmed is True
                and confirmed_target_authority_id != row["target_authority_id"]
            ) or (
                target_identity_confirmed is False
                and confirmed_target_authority_id is not None
            ):
                raise TreatmentReviewError(
                    "Rejected treatment target confirmation must be internally consistent."
                )
            indexed = self.conn.execute(
                """
                SELECT i.original_text, i.chain_candidate_id,
                       i.document_id, i.text_hash, s.raw_sha256,
                       (
                         SELECT seed.canonical_url
                         FROM observations o
                         JOIN seeds seed ON seed.seed_id=o.seed_id
                         WHERE o.snapshot_id=i.snapshot_id
                           AND seed.role IN (
                             'official_enumerator_observation',
                             'official_user_seed',
                             'official_authority_seed'
                           )
                         ORDER BY CASE seed.role
                           WHEN 'official_enumerator_observation' THEN 0
                           WHEN 'official_authority_seed' THEN 1
                           WHEN 'official_user_seed' THEN 2
                           ELSE 9 END,
                           seed.canonical_url
                         LIMIT 1
                       ) AS official_url,
                       (
                         SELECT seed.role
                         FROM observations o
                         JOIN seeds seed ON seed.seed_id=o.seed_id
                         WHERE o.snapshot_id=i.snapshot_id
                           AND seed.role IN (
                             'official_enumerator_observation',
                             'official_user_seed',
                             'official_authority_seed'
                           )
                         ORDER BY CASE seed.role
                           WHEN 'official_enumerator_observation' THEN 0
                           WHEN 'official_authority_seed' THEN 1
                           WHEN 'official_user_seed' THEN 2
                           ELSE 9 END,
                           seed.canonical_url
                         LIMIT 1
                       ) AS source_role
                FROM indexed_texts i
                JOIN snapshots s ON s.snapshot_id=i.snapshot_id
                WHERE i.snapshot_id=?
                """,
                (row["snapshot_id"],),
            ).fetchone()
            if (
                indexed is None
                or indexed["chain_candidate_id"] != row["source_chain_id"]
                or not _is_canonical_identifier(indexed["document_id"])
                or indexed["source_role"] not in OFFICIAL_EVIDENCE_SEED_ROLES
                or not official_public_url_allowed(indexed["official_url"])
            ):
                raise TreatmentReviewError(
                    "Rejected treatment requires indexed official full text "
                    "bound to the same source chain."
                )
            if quote is not None and (
                not quote.strip()
                or not _is_canonical_identifier(locator)
                or speaker != "court"
                or _normalise_text(quote)
                not in _normalise_text(str(indexed["original_text"]))
            ):
                raise TreatmentReviewError(
                    "A quoted rejection reason requires a matching court quote and locator."
                )
        existing_status = str(row["status"])
        if existing_status != "candidate":
            raise TreatmentReviewError("Treatment review is immutable after the first decision.")
        decided_at = reviewed_at if reviewed_at is not None else _utc_now()
        if not _aware_rfc3339_datetime(decided_at):
            raise TreatmentReviewError(
                "reviewed_at должен содержать полные дату, время с секундами "
                "и часовой пояс RFC 3339."
            )
        if _parse_timestamp(decided_at) > datetime.now(timezone.utc):
            raise TreatmentReviewError("reviewed_at не может находиться в будущем.")
        created_at = str(row["created_at"])
        if (
            not _aware_rfc3339_datetime(created_at)
            or _parse_timestamp(decided_at) < _parse_timestamp(created_at)
        ):
            raise TreatmentReviewError(
                "reviewed_at не может предшествовать созданию treatment candidate."
            )
        with self.conn:
            updated = self.conn.execute(
                """
                UPDATE treatments SET status=?, reviewer=?, quote=?, locator=?, speaker=?, reviewed_at=?
                WHERE treatment_id=? AND status='candidate'
                """,
                (decision, reviewer.strip(), quote, locator, speaker, decided_at, treatment_id),
            )
            if updated.rowcount != 1:
                raise TreatmentReviewError(
                    "Treatment review is immutable after the first decision."
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
                    "decision_reason": decision_reason,
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
            "decision_reason": decision_reason,
        }

    @_consistent_read
    def treatment_quality_export(self) -> dict[str, Any]:
        """Export the complete treatment population for the pre-filing gate.

        Resolved database rows are promoted only when their official snapshot,
        indexed full text, quote, target confirmation, and immutable review
        history agree.  Every other row remains visibly candidate-only.
        """

        rows = self.conn.execute(
            """
            SELECT t.*, s.raw_sha256, i.text_hash, i.original_text,
                   i.document_id, i.chain_candidate_id,
                   (
                     SELECT seed.canonical_url
                     FROM observations o
                     JOIN seeds seed ON seed.seed_id=o.seed_id
                     WHERE o.snapshot_id=t.snapshot_id
                       AND seed.role IN (
                         'official_enumerator_observation',
                         'official_user_seed',
                         'official_authority_seed'
                       )
                     ORDER BY CASE seed.role
                       WHEN 'official_enumerator_observation' THEN 0
                       WHEN 'official_authority_seed' THEN 1
                       WHEN 'official_user_seed' THEN 2
                       ELSE 9 END,
                       seed.canonical_url
                     LIMIT 1
                   ) AS official_url,
                   (
                     SELECT seed.role
                     FROM observations o
                     JOIN seeds seed ON seed.seed_id=o.seed_id
                     WHERE o.snapshot_id=t.snapshot_id
                       AND seed.role IN (
                         'official_enumerator_observation',
                         'official_user_seed',
                         'official_authority_seed'
                       )
                     ORDER BY CASE seed.role
                       WHEN 'official_enumerator_observation' THEN 0
                       WHEN 'official_authority_seed' THEN 1
                       WHEN 'official_user_seed' THEN 2
                       ELSE 9 END,
                       seed.canonical_url
                     LIMIT 1
                   ) AS source_role
            FROM treatments t
            LEFT JOIN snapshots s ON s.snapshot_id=t.snapshot_id
            LEFT JOIN indexed_texts i ON i.snapshot_id=t.snapshot_id
            ORDER BY t.treatment_id
            """
        ).fetchall()
        rows_by_id = {str(row["treatment_id"]): row for row in rows}
        successors_by_prior: dict[str, list[str]] = {}
        for row in rows:
            prior_id = row["supersedes_treatment_id"]
            if isinstance(prior_id, str):
                successors_by_prior.setdefault(prior_id, []).append(
                    str(row["treatment_id"])
                )
        for successor_ids in successors_by_prior.values():
            successor_ids.sort()

        supersession_blockers: dict[str, set[str]] = {
            treatment_id: set() for treatment_id in rows_by_id
        }
        for prior_id, successor_ids in successors_by_prior.items():
            if len(successor_ids) > 1:
                supersession_blockers.setdefault(prior_id, set()).add(
                    "supersession_branch_invalid"
                )
                for successor_id in successor_ids:
                    supersession_blockers[successor_id].add(
                        "supersession_branch_invalid"
                    )
            prior_row = rows_by_id.get(prior_id)
            for successor_id in successor_ids:
                successor_row = rows_by_id[successor_id]
                if prior_row is None or not _is_canonical_identifier(prior_id):
                    supersession_blockers[successor_id].add(
                        "supersedes_treatment_missing"
                    )
                    continue
                if str(prior_row["status"]) not in {"verified", "rejected"}:
                    supersession_blockers[successor_id].add(
                        "superseded_prior_unresolved"
                    )
                    supersession_blockers[prior_id].add(
                        "superseded_while_unresolved"
                    )
                if (
                    prior_row["source_chain_id"] != successor_row["source_chain_id"]
                    or prior_row["target_authority_id"]
                    != successor_row["target_authority_id"]
                ):
                    supersession_blockers[successor_id].add(
                        "supersession_identity_mismatch"
                    )
                    supersession_blockers[prior_id].add(
                        "supersession_identity_mismatch"
                    )
                prior_reviewed_at = prior_row["reviewed_at"]
                successor_created_at = successor_row["created_at"]
                if (
                    not _aware_rfc3339_datetime(prior_reviewed_at)
                    or not _aware_rfc3339_datetime(successor_created_at)
                    or _parse_timestamp(str(prior_reviewed_at))
                    > _parse_timestamp(str(successor_created_at))
                ):
                    supersession_blockers[successor_id].add(
                        "supersession_chronology_invalid"
                    )
                    supersession_blockers[prior_id].add(
                        "supersession_chronology_invalid"
                    )

        def supersession_cycle(start_id: str) -> bool:
            seen: set[str] = set()
            current_id: str | None = start_id
            while current_id is not None:
                if current_id in seen:
                    return True
                seen.add(current_id)
                current_row = rows_by_id.get(current_id)
                if current_row is None:
                    return False
                prior_id = current_row["supersedes_treatment_id"]
                current_id = str(prior_id) if isinstance(prior_id, str) else None
            return False

        for treatment_id in rows_by_id:
            if supersession_cycle(treatment_id):
                supersession_blockers[treatment_id].add(
                    "supersession_cycle_invalid"
                )

        records: list[dict[str, Any]] = []
        for row in rows:
            treatment_id = str(row["treatment_id"])
            status = str(row["status"])
            blockers: list[str] = sorted(supersession_blockers[treatment_id])
            prior_treatment_id = row["supersedes_treatment_id"]
            successor_ids = successors_by_prior.get(treatment_id, [])
            identity: Any = None
            try:
                identity = json.loads(str(row["target_identity_json"]))
            except (TypeError, ValueError, json.JSONDecodeError):
                blockers.append("target_identity_invalid")
            history_rows = self.conn.execute(
                """
                SELECT history_id, event_type, reviewer, payload_json, event_at
                FROM treatment_review_history
                WHERE treatment_id=?
                ORDER BY rowid
                """,
                (treatment_id,),
            ).fetchall()
            history = history_rows[1] if len(history_rows) == 2 else None
            candidate_history = history_rows[0] if len(history_rows) == 2 else None
            history_payload: Any = None
            candidate_history_payload: Any = None
            if history is not None:
                try:
                    history_payload = json.loads(str(history["payload_json"]))
                except (TypeError, ValueError, json.JSONDecodeError):
                    history_payload = None
            if candidate_history is not None:
                try:
                    candidate_history_payload = json.loads(
                        str(candidate_history["payload_json"])
                    )
                except (TypeError, ValueError, json.JSONDecodeError):
                    candidate_history_payload = None

            canonical_fields = (
                "treatment_id",
                "source_chain_id",
                "source_court_id",
                "target_authority_id",
                "target_kind",
                "snapshot_id",
                "reviewer",
                "document_id",
            )
            for field in canonical_fields:
                if not _is_canonical_identifier(row[field]):
                    blockers.append(f"{field}_invalid")
            if status not in {"verified", "rejected"}:
                blockers.append("review_pending")
            if row["treatment_type"] not in TREATMENT_TYPES:
                blockers.append("treatment_type_invalid")
            if not isinstance(identity, dict) or not identity:
                blockers.append("target_identity_invalid")
            expected_candidate_history = {
                "source_chain_id": row["source_chain_id"],
                "source_court_id": row["source_court_id"],
                "target_authority_id": row["target_authority_id"],
                "target_kind": row["target_kind"],
                "target_identity": identity,
                "treatment_type": row["treatment_type"],
                "snapshot_id": row["snapshot_id"],
                "supersedes_treatment_id": row["supersedes_treatment_id"],
            }
            if status in {"verified", "rejected"} and (
                len(history_rows) != 2
                or candidate_history is None
                or candidate_history["event_type"] != "candidate_created"
                or candidate_history["reviewer"] is not None
                or candidate_history["event_at"] != row["created_at"]
                or candidate_history_payload != expected_candidate_history
                or candidate_history["history_id"]
                != _identifier(
                    "treatment-history",
                    {
                        "treatment_id": treatment_id,
                        "event_type": "candidate_created",
                        "reviewer": None,
                        "payload": expected_candidate_history,
                        "event_at": row["created_at"],
                    },
                )
                or history is None
                or history["event_type"] != status
            ):
                blockers.append("review_history_cardinality_invalid")
            reviewed_at = row["reviewed_at"]
            created_at = row["created_at"]
            if (
                not _aware_rfc3339_datetime(reviewed_at)
                or _parse_timestamp(str(reviewed_at)) > datetime.now(timezone.utc)
            ):
                blockers.append("reviewed_at_invalid")
            if (
                not _aware_rfc3339_datetime(created_at)
                or (
                    _aware_rfc3339_datetime(reviewed_at)
                    and _parse_timestamp(str(reviewed_at))
                    < _parse_timestamp(str(created_at))
                )
            ):
                blockers.append("review_chronology_invalid")
            raw_sha256 = row["raw_sha256"]
            if raw_sha256 is None:
                blockers.append("snapshot_missing")
            if (
                not isinstance(raw_sha256, str)
                or re.fullmatch(r"[0-9a-f]{64}", raw_sha256) is None
                or row["snapshot_id"] != f"snapshot-sha256:{raw_sha256}"
            ):
                blockers.append("snapshot_binding_invalid")
            if not self._snapshot_integrity(str(row["snapshot_id"]))["valid"]:
                blockers.append("snapshot_object_integrity_invalid")
            text_sha256 = row["text_hash"]
            if not isinstance(text_sha256, str) or re.fullmatch(
                r"[0-9a-f]{64}", text_sha256
            ) is None:
                blockers.append("indexed_text_missing")
            if not self._indexed_text_integrity(str(row["snapshot_id"]))["valid"]:
                blockers.append("indexed_text_integrity_invalid")
            if row["chain_candidate_id"] != row["source_chain_id"]:
                blockers.append("source_chain_binding_invalid")
            official_url = row["official_url"]
            source_role = row["source_role"]
            if source_role not in OFFICIAL_EVIDENCE_SEED_ROLES:
                blockers.append("official_source_role_missing")
            if not official_public_url_allowed(official_url):
                blockers.append("official_url_missing")
            quote = row["quote"]
            original_text = row["original_text"]
            quote_matches = (
                isinstance(quote, str)
                and bool(quote.strip())
                and isinstance(original_text, str)
                and _normalise_text(quote) in _normalise_text(original_text)
            )
            if status == "verified":
                if not quote_matches:
                    blockers.append("quote_not_found_in_indexed_text")
                if not _is_canonical_identifier(row["locator"]):
                    blockers.append("quote_locator_invalid")
                if row["speaker"] != "court":
                    blockers.append("speaker_not_court")
            elif quote is not None and (
                not quote_matches
                or not _is_canonical_identifier(row["locator"])
                or row["speaker"] != "court"
            ):
                blockers.append("optional_rejection_quote_invalid")
            decision_reason = (
                history_payload.get("decision_reason")
                if isinstance(history_payload, dict)
                else None
            )
            if status == "rejected" and not _is_canonical_identifier(
                decision_reason
            ):
                blockers.append("decision_reason_invalid")
            if status == "verified" and decision_reason is not None:
                blockers.append("verified_decision_reason_invalid")
            if (
                history is None
                or history["event_type"] != status
                or history["reviewer"] != row["reviewer"]
                or history["event_at"] != reviewed_at
                or not isinstance(history_payload, dict)
                or (
                    isinstance(history_payload, dict)
                    and history["history_id"]
                    != _identifier(
                        "treatment-history",
                        {
                            "treatment_id": treatment_id,
                            "event_type": status,
                            "reviewer": row["reviewer"],
                            "payload": history_payload,
                            "event_at": reviewed_at,
                        },
                    )
                )
                or set(history_payload)
                != {
                    "quote",
                    "locator",
                    "speaker",
                    "confirmed_target_authority_id",
                    "target_identity_confirmed",
                    "decision_reason",
                }
                or (
                    isinstance(history_payload, dict)
                    and (
                        history_payload.get("quote") != quote
                        or history_payload.get("locator") != row["locator"]
                        or history_payload.get("speaker") != row["speaker"]
                        or history_payload.get("decision_reason")
                        != decision_reason
                    )
                )
                or (
                    status == "verified"
                    and history_payload.get("confirmed_target_authority_id")
                    != row["target_authority_id"]
                )
                or not isinstance(
                    history_payload.get("target_identity_confirmed"), bool
                )
                or (
                    status == "verified"
                    and history_payload.get("target_identity_confirmed") is not True
                )
                or (
                    status == "rejected"
                    and history_payload.get("target_identity_confirmed") is True
                    and history_payload.get("confirmed_target_authority_id")
                    != row["target_authority_id"]
                )
                or (
                    status == "rejected"
                    and history_payload.get("target_identity_confirmed") is False
                    and history_payload.get("confirmed_target_authority_id") is not None
                )
            ):
                blockers.append("review_history_binding_invalid")

            if blockers:
                records.append(
                    {
                        "treatment_id": treatment_id,
                        "status": "candidate",
                        "recorded_status": status,
                        "quality_blockers": sorted(set(blockers)),
                        "source_chain_id": row["source_chain_id"],
                        "target_authority_id": row["target_authority_id"],
                        "supersedes_treatment_id": prior_treatment_id,
                        "superseded_by_treatment_id": (
                            successor_ids[0] if len(successor_ids) == 1 else None
                        ),
                        "created_at": row["created_at"],
                    }
                )
                continue

            proposition = treatment_quality_proposition(
                status=status,
                source_chain_id=str(row["source_chain_id"]),
                treatment_type=str(row["treatment_type"]),
                target_authority_id=str(row["target_authority_id"]),
                decision_reason=(
                    str(decision_reason) if status == "rejected" else None
                ),
            )
            source = {
                "source_chain_id": row["source_chain_id"],
                "source_court_id": row["source_court_id"],
                "target_authority_id": row["target_authority_id"],
                "target_kind": row["target_kind"],
                "target_identity": identity,
                "target_identity_confirmed": history_payload[
                    "target_identity_confirmed"
                ],
                "treatment_type": row["treatment_type"],
                "review_decision": status,
                "snapshot_id": row["snapshot_id"],
                "supersedes_treatment_id": prior_treatment_id,
                "superseded_by_treatment_id": (
                    successor_ids[0] if len(successor_ids) == 1 else None
                ),
                "speaker": row["speaker"],
                "document_id": row["document_id"],
                "document_sha256": raw_sha256,
                "text_sha256": text_sha256,
                "source_role": source_role,
                "official_url": official_url,
                "quote": quote,
                "quote_locator": row["locator"],
                "proposition": proposition,
                "decision_reason": (
                    decision_reason if status == "rejected" else None
                ),
                "created_at": created_at,
            }
            effective_status = "superseded" if len(successor_ids) == 1 else status
            records.append(
                {
                    "treatment_id": treatment_id,
                    "status": effective_status,
                    **source,
                    "source_binding_sha256": _sha256(
                        _canonical_json(source).encode("utf-8")
                    ),
                    "reviewer": row["reviewer"],
                    "reviewed_at": reviewed_at,
                    "human_review": "approved",
                    "quote_verified": quote_matches,
                    "full_text_reviewed": True,
                }
            )

        treatment_ids = [str(row["treatment_id"]) for row in rows]
        payload = {
            "schema_version": "1.0",
            "export_type": "public_corpus_treatment_quality_set",
            "corpus_evidence_digest": self.evidence_digest(),
            "treatment_population_sha256": self.treatment_population_sha256(),
            "integrity_issue_ids": self._cache_integrity_issue_ids(),
            "treatment_ids": treatment_ids,
            "items": records,
        }
        return {
            **payload,
            "set_sha256": _sha256(_canonical_json(payload).encode("utf-8")),
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

    @_consistent_read
    def list_treatments(self, *, verified_only: bool = False) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            f"""
            SELECT treatment_id, source_chain_id, source_court_id,
                   target_authority_id, target_kind, target_identity_json,
                   treatment_type, snapshot_id, supersedes_treatment_id, status,
                   reviewer, quote, locator, speaker, created_at, reviewed_at
            FROM treatments ORDER BY treatment_id
            """
        ).fetchall()
        quality_by_id = {
            str(item["treatment_id"]): item
            for item in self.treatment_quality_export()["items"]
        }
        records: list[dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            raw_identity = record.pop("target_identity_json", None)
            raw_status = str(record.pop("status"))
            quality = quality_by_id[str(record["treatment_id"])]
            record["review_decision"] = (
                raw_status if raw_status in {"verified", "rejected"} else None
            )
            record["status"] = quality["status"]
            record["superseded_by_treatment_id"] = quality.get(
                "superseded_by_treatment_id"
            )
            record["quality_blockers"] = quality.get("quality_blockers", [])
            try:
                record["target_identity"] = (
                    json.loads(str(raw_identity)) if raw_identity is not None else None
                )
            except (TypeError, ValueError, json.JSONDecodeError):
                record["target_identity"] = None
            if verified_only and record["status"] != "verified":
                continue
            records.append(record)
        return records

    def treatment_ids(self) -> list[str]:
        return [
            str(row["treatment_id"])
            for row in self.conn.execute(
                "SELECT treatment_id FROM treatments ORDER BY treatment_id"
            ).fetchall()
        ]

    def _treatment_population_records(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        treatments = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT treatment_id, source_chain_id, source_court_id,
                       target_authority_id, target_kind, target_identity_json,
                       snapshot_id, treatment_type, supersedes_treatment_id,
                       status, reviewer, quote, locator, speaker, created_at, reviewed_at
                FROM treatments ORDER BY treatment_id
                """
            ).fetchall()
        ]
        history = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT history_id, treatment_id, event_type, reviewer,
                       payload_json, event_at
                FROM treatment_review_history
                ORDER BY treatment_id, rowid
                """
            ).fetchall()
        ]
        return treatments, history

    def treatment_population_sha256(self) -> str:
        treatments, history = self._treatment_population_records()
        return _sha256(
            _canonical_json(
                {"treatments": treatments, "treatment_history": history}
            ).encode("utf-8")
        )

    def evidence_digest(self) -> str:
        seeds = [
            dict(row)
            for row in self.conn.execute(
                "SELECT seed_id, canonical_url, role FROM seeds ORDER BY seed_id"
            ).fetchall()
        ]
        snapshot_rows = self.conn.execute(
            "SELECT snapshot_id, raw_sha256, byte_length FROM snapshots ORDER BY snapshot_id"
        ).fetchall()
        snapshots = []
        for row in snapshot_rows:
            integrity = self._snapshot_integrity(str(row["snapshot_id"]))
            snapshots.append(
                {
                    **dict(row),
                    "observed_raw_sha256": integrity["observed_sha256"],
                    "observed_byte_length": integrity["observed_byte_length"],
                    "object_path_valid": integrity["path_valid"],
                    "object_readable": integrity["readable"],
                    "object_integrity_valid": integrity["valid"],
                }
            )
        indexed_rows = self.conn.execute(
            """
            SELECT snapshot_id, text_hash, document_id,
                   chain_candidate_id, query_lane
            FROM indexed_texts ORDER BY snapshot_id
            """
        ).fetchall()
        indexed = []
        for row in indexed_rows:
            integrity = self._indexed_text_integrity(str(row["snapshot_id"]))
            indexed.append(
                {
                    **dict(row),
                    "observed_text_sha256": integrity["observed_text_sha256"],
                    "normalized_text_matches": integrity[
                        "normalized_text_matches"
                    ],
                    "text_integrity_valid": integrity["valid"],
                }
            )
        observation_bindings = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT DISTINCT seed_id, snapshot_id
                FROM observations
                ORDER BY seed_id, snapshot_id
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
        treatments, treatment_history = self._treatment_population_records()
        return _identifier(
            "corpus-evidence",
            {
                "seeds": seeds,
                "snapshots": snapshots,
                "observation_bindings": observation_bindings,
                "indexed": indexed,
                "funnel_states": funnel_states,
                "treatments": treatments,
                "treatment_history": treatment_history,
            },
        )

    def verify_prefiling_inputs(
        self,
        *,
        refresh_plan: Mapping[str, Any],
        treatment_set: Mapping[str, Any],
        current_corpus_digest: str,
    ) -> dict[str, Any]:
        """Bind caller-supplied quality inputs to this existing cache snapshot."""

        if self.conn.in_transaction:
            raise PublicCorpusError(
                "Prefiling verification requires ownership of its read transaction."
            )
        read_only_issues_before = self._read_only_store_issue_ids()
        result = self._verify_prefiling_inputs_snapshot(
            refresh_plan=refresh_plan,
            treatment_set=treatment_set,
            current_corpus_digest=current_corpus_digest,
            read_only_issues_before=read_only_issues_before,
        )
        # The snapshot decorator has rolled back the SQLite read transaction before
        # this second observation of the externally mutable database file.
        read_only_issues_after = self._read_only_store_issue_ids()
        issue_ids = list(result["issue_ids"])
        issue_ids.extend(read_only_issues_after)
        if read_only_issues_before != read_only_issues_after:
            issue_ids.append("live_cache_static_store_changed_during_read")
        normalized_issues = sorted(set(issue_ids))
        result["issue_ids"] = normalized_issues
        result["verified"] = not normalized_issues
        result["live_cache_stable"] = bool(result["live_cache_stable"]) and not (
            read_only_issues_before or read_only_issues_after
        )
        return result

    @_consistent_read
    def _verify_prefiling_inputs_snapshot(
        self,
        *,
        refresh_plan: Mapping[str, Any],
        treatment_set: Mapping[str, Any],
        current_corpus_digest: str,
        read_only_issues_before: list[str],
    ) -> dict[str, Any]:
        """Regenerate quality inputs inside one consistent SQLite snapshot."""

        issue_ids: list[str] = []
        issue_ids.extend(read_only_issues_before)
        digest_before = self.evidence_digest()
        live_plan: dict[str, Any] | None = None
        try:
            live_plan = self.plan_refresh(
                as_of=refresh_plan.get("as_of"),
                max_age_seconds=refresh_plan.get("max_age_seconds"),
                coverage_requirements=refresh_plan.get("coverage_requirements"),
            )
        except (PublicCorpusError, TypeError, ValueError):
            issue_ids.append("refresh_plan_regeneration_failed")

        live_treatment_set = self.treatment_quality_export()
        digest_after = self.evidence_digest()
        live_integrity_issues = self._cache_integrity_issue_ids()
        if live_integrity_issues:
            issue_ids.append("live_cache_integrity_invalid")
            issue_ids.extend(
                f"live_cache:{identifier}" for identifier in live_integrity_issues
            )
        cache_stable = digest_before == digest_after
        if not cache_stable:
            issue_ids.append("live_cache_changed_during_read")

        expected_current_digest = f"corpus-evidence-sha256:{current_corpus_digest}"
        if digest_after != expected_current_digest:
            issue_ids.append("current_corpus_digest_mismatch")

        live_plan_sha256: str | None = None
        if live_plan is not None:
            live_plan_sha256 = _sha256(
                _canonical_json(live_plan).encode("utf-8")
            )
            if _canonical_json(dict(refresh_plan)) != _canonical_json(live_plan):
                issue_ids.append("refresh_plan_mismatch")
            if live_plan.get("evidence_digest") != digest_after:
                issue_ids.append("live_refresh_plan_digest_mismatch")

        live_treatment_set_sha256 = live_treatment_set.get("set_sha256")
        if _canonical_json(dict(treatment_set)) != _canonical_json(live_treatment_set):
            issue_ids.append("treatment_set_mismatch")
        if live_treatment_set.get("corpus_evidence_digest") != digest_after:
            issue_ids.append("live_treatment_set_digest_mismatch")

        live_treatment_ids = self.treatment_ids()
        live_treatment_population_sha256 = self.treatment_population_sha256()
        if live_treatment_set.get("treatment_ids") != live_treatment_ids:
            issue_ids.append("live_treatment_ids_mismatch")
        if (
            live_treatment_set.get("treatment_population_sha256")
            != live_treatment_population_sha256
        ):
            issue_ids.append("live_treatment_population_mismatch")

        normalized_issues = sorted(set(issue_ids))
        cache_stable = cache_stable and not read_only_issues_before
        return {
            "binding_version": "1.0",
            "verified": not normalized_issues,
            "live_cache_stable": cache_stable,
            "live_corpus_evidence_digest": digest_after,
            "live_refresh_plan_sha256": live_plan_sha256,
            "live_treatment_set_sha256": (
                str(live_treatment_set_sha256)
                if isinstance(live_treatment_set_sha256, str)
                else None
            ),
            "live_treatment_population_sha256": live_treatment_population_sha256,
            "live_treatment_ids": live_treatment_ids,
            "issue_ids": normalized_issues,
        }
