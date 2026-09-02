#!/usr/bin/env python3
"""Исполняемый per-claim gate анализа правоприменительной практики.

Модуль не импортирует соседние skills и использует только стандартную библиотеку
Python 3.10+. Все case-private артефакты записываются в выбранный matter workspace.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import functools
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from xml.etree import ElementTree


SCHEMA_VERSION = "1.0"
HANDOFF_VERSION = "2.0"
SOURCE_SKILL = "ksrf-complaint-cycle"
TARGET_SKILL = "ksrf-cassation-judicial-meaning"
CLAIM_STATES = (
    "not_required",
    "required",
    "running",
    "blocked",
    "ready",
    "stale",
)
STAGES = ("options", "drafting", "qa", "filing")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

ANALYSIS_DIR = "practice-analysis"
CONFIG_FILE = "config.json"
INPUT_MANIFEST_FILE = "input-manifest.json"
TRIGGER_SCAN_FILE = "trigger-scan.json"
CLAIM_LEDGER_FILE = "claim-ledger.jsonl"
CLAIM_INDEX_FILE = "claim-index.json"
TRIGGER_REVIEWS_FILE = "trigger-reviews.jsonl"
ATTACHMENTS_FILE = "run-attachments.jsonl"
RESULT_IMPORTS_FILE = "result-imports.jsonl"
WORDING_REVIEWS_FILE = "wording-reviews.jsonl"
REFRESHES_FILE = "refreshes.jsonl"
STATE_FILE = "state.json"
VALIDATION_FILE = "validation-report.json"
CLAIM_ALIASES_FILE = "claim-aliases.json"
MAX_DOCX_PART_BYTES = 8 * 1024 * 1024
MAX_DOCX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_REFRESH_AGE_DAYS = 7
REQUIRED_QUALITY_TYPES = frozenset(
    {
        "chain_stage_propagation",
        "uncertainty_profile",
        "coding_reliability",
        "prefiling_refresh",
    }
)
ALLOWED_QUALITY_TYPES = REQUIRED_QUALITY_TYPES | {"coding_audit_plan"}

TRIGGER_RULES: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "repeatability",
        "repeatability_language",
        re.compile(
            r"(?:устойчив\w*|последовательн\w*|единообразн\w*|сложил\w*\s+.{0,30}практик\w*|"
            r"суд\w*\s+(?:обычно|как\s+правило)|правоприменительн\w*\s+практик\w*)",
            re.IGNORECASE,
        ),
    ),
    (
        "split",
        "split_language",
        re.compile(
            r"(?:два\s+(?:судебн\w*\s+)?подход\w*|расхожден\w*|противоречив\w*|"
            r"неоднородн\w*|судебн\w*\s+хаос\w*|нет\s+единообраз\w*|"
            r"по[-\s]+разн\w*.{0,60}(?:толк\w*|примен\w*)|"
            r"суд\w*.{0,60}по[-\s]+разн\w*)",
            re.IGNORECASE,
        ),
    ),
    (
        "temporal",
        "temporal_language",
        re.compile(
            r"(?:динамик\w*|тенденц\w*|до\s+и\s+после|после\s+.{0,60}(?:измен\w*|стал\w*)|"
            r"с\s+20\d{2}\s+год\w*\s+.{0,40}(?:измен\w*|стал\w*))",
            re.IGNORECASE,
        ),
    ),
    (
        "cross_circuit",
        "cross_circuit_language",
        re.compile(
            r"(?:межокружн\w*|разн\w*\s+кассационн\w*\s+суд\w*|по\s+округ\w*)",
            re.IGNORECASE,
        ),
    ),
    (
        "systemic",
        "systemic_language",
        re.compile(
            r"(?:системн\w*|массов\w*|повсеместн\w*|закон\s+не\s+работает)",
            re.IGNORECASE,
        ),
    ),
    (
        "quantitative",
        "quantitative_language",
        re.compile(
            r"(?:\b\d+(?:[.,]\d+)?\s*%|\b\d+\s+(?:акт\w*|дел\w*|решен\w*))",
            re.IGNORECASE,
        ),
    ),
    (
        "judicial_meaning",
        "judicial_meaning_language",
        re.compile(
            r"(?:судебн\w*\s+смысл\w*|толк\w*.{0,50}суд\w*|"
            r"суд\w*.{0,50}толк\w*|кассационн\w*\s+суд\w*)",
            re.IGNORECASE,
        ),
    ),
    (
        "quantitative",
        "frequency_outcome_language",
        re.compile(
            r"(?:во\s+всех\s+(?:изученн\w*\s+)?дел\w*|в\s+большинств\w*\s+дел\w*|"
            r"чаще\s+(?:всего\s+)?(?:поддерж\w*|отказыва\w*|удовлетвор\w*)|"
            r"преимущественн\w*\s+(?:поддерж\w*|отказыва\w*|удовлетвор\w*))",
            re.IGNORECASE,
        ),
    ),
    (
        "cross_circuit",
        "named_cassation_court_language",
        re.compile(r"(?:\b(?:[1-9]|перв\w*|втор\w*|треть\w*|четверт\w*|пят\w*|шест\w*|седьм\w*|восьм\w*|девят\w*)\s+КСОЮ\b)", re.IGNORECASE),
    ),
    (
        "split",
        "differing_approaches_language",
        re.compile(r"(?:подход\w*\s+суд\w*.{0,40}различ\w*|различ\w*.{0,40}подход\w*\s+суд\w*)", re.IGNORECASE),
    ),
)

QUESTION_BY_DIMENSION = {
    "repeatability": "Повторяется ли один и тот же исходозначимый судебный смысл в сопоставимых независимых цепочках?",
    "split": "Какие конкурирующие прочтения наблюдаются в сопоставимых независимых цепочках и чем различаются их фактические основания?",
    "temporal": "Как распределяются проверенные reading families по заранее раскрытым временным стратам без причинного вывода из последовательности?",
    "cross_circuit": "Различаются ли проверенные reading families между раскрытыми кассационными судами при сопоставимых признаках?",
    "systemic": "Какой максимально ограниченный вывод допускает раскрытый проверенный корпус с учётом неблагоприятных позиций и пробелов охвата?",
    "quantitative": "Каков знаменатель независимых проверенных цепочек и какие ограничения препятствуют обобщению наблюдаемых количеств?",
    "judicial_meaning": "Какой исходозначимый смысл спорной норме придают кассационные суды в сопоставимых проверенных делах?",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_nonempty(value: Any, field: str) -> str:
    if not _nonempty(value):
        raise ValueError(f"Поле {field} должно быть непустой строкой.")
    return str(value).strip()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _require_sha256(value: Any, field: str) -> str:
    if not _is_sha256(value):
        raise ValueError(f"{field} должен быть SHA-256 в нижнем регистре.")
    return str(value)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _analysis_root(workspace: str | Path) -> Path:
    return Path(workspace).expanduser().resolve() / ANALYSIS_DIR


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def _atomic_write_json(path: Path, value: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    _atomic_write_bytes(path, payload)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Не найден обязательный файл: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Повреждён JSON {path}: строка {exc.lineno}, столбец {exc.colno}.") from exc
    except OSError as exc:
        raise ValueError(f"Не удалось прочитать {path}: {exc}") from exc


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    target = Path(path)
    if not target.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"Не удалось прочитать JSONL {target}: {exc}") from exc
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Повреждён JSONL {target}, строка {line_number}.") from exc
        if not isinstance(value, dict):
            raise ValueError(f"JSONL {target}, строка {line_number}, должен содержать объект.")
        records.append(value)
    return records


@contextmanager
def _interprocess_lock(path: Path, *, timeout: float = 10.0):
    """Cross-platform advisory lock for one ledger mutation.

    The chain/checkpoint detects accidental reorder/truncation. It is not an
    authenticity signature: deliberate forgery still requires an external key
    or immutable external checkpoint.
    """

    lock_path = path.with_name(f".{path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    deadline = time.monotonic() + timeout
    try:
        if os.name == "nt":  # pragma: no cover - exercised on Windows runners
            import msvcrt

            while True:
                try:
                    handle.seek(0)
                    if handle.tell() == 0:
                        handle.write(b"0")
                        handle.flush()
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"Не удалось получить lock для {path}.")
                    time.sleep(0.02)
        else:
            import fcntl

            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"Не удалось получить lock для {path}.")
                    time.sleep(0.02)
        yield
    finally:
        try:
            if os.name == "nt":  # pragma: no cover
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


_LOCAL_WORKSPACE_LOCKS: dict[str, threading.RLock] = {}
_LOCAL_WORKSPACE_LOCKS_GUARD = threading.Lock()
_WORKSPACE_OPERATION_STATE = threading.local()


def _local_workspace_lock(workspace_key: str) -> threading.RLock:
    with _LOCAL_WORKSPACE_LOCKS_GUARD:
        return _LOCAL_WORKSPACE_LOCKS.setdefault(workspace_key, threading.RLock())


@contextmanager
def _workspace_transaction(workspace: str | Path):
    """Reentrant in-process + interprocess transaction for one matter workspace."""

    root = _analysis_root(workspace)
    key = str(root.resolve())
    local_lock = _local_workspace_lock(key)
    with local_lock:
        depths = getattr(_WORKSPACE_OPERATION_STATE, "depths", None)
        if depths is None:
            depths = {}
            _WORKSPACE_OPERATION_STATE.depths = depths
        depth = int(depths.get(key, 0))
        depths[key] = depth + 1
        try:
            if depth:
                yield
            else:
                with _interprocess_lock(root / "workspace-transaction"):
                    yield
        finally:
            if depth:
                depths[key] = depth
            else:
                depths.pop(key, None)


def _invalidate_validation_report(workspace: str | Path) -> None:
    path = _analysis_root(workspace) / VALIDATION_FILE
    if not path.is_file():
        return
    try:
        report = _read_json(path)
    except ValueError:
        report = None
    if not isinstance(report, dict):
        return
    marker = "workspace_changed_since_validation"
    errors = report.get("errors", [])
    integrity = report.get("global_integrity_errors", [])
    report["valid"] = False
    report["errors"] = [*errors, marker] if isinstance(errors, list) and marker not in errors else errors
    report["global_integrity_errors"] = (
        [*integrity, marker]
        if isinstance(integrity, list) and marker not in integrity
        else integrity
    )
    _atomic_write_json(path, report)


def _workspace_operation(kind: str):
    if kind not in {"mutation", "derived", "validation"}:
        raise ValueError(f"Неизвестный workspace operation kind: {kind}.")

    def decorate(function):
        @functools.wraps(function)
        def wrapped(*args, **kwargs):
            workspace = args[0] if args else kwargs.get("workspace")
            if workspace is None:
                raise TypeError("workspace обязателен для workspace operation.")
            key = str(_analysis_root(workspace).resolve())
            validations = getattr(_WORKSPACE_OPERATION_STATE, "validations", None)
            if validations is None:
                validations = {}
                _WORKSPACE_OPERATION_STATE.validations = validations
            if kind == "mutation" and int(validations.get(key, 0)):
                raise RuntimeError("Нельзя изменять workspace во время публикации validation snapshot.")
            with _workspace_transaction(workspace):
                if kind == "validation":
                    validations[key] = int(validations.get(key, 0)) + 1
                try:
                    return function(*args, **kwargs)
                finally:
                    if kind == "mutation":
                        _invalidate_validation_report(workspace)
                    if kind == "validation":
                        remaining = int(validations.get(key, 1)) - 1
                        if remaining:
                            validations[key] = remaining
                        else:
                            validations.pop(key, None)

        return wrapped

    return decorate


def _ledger_checkpoint_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.head.json")


def _write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    payload = "".join(
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for item in records
    ).encode("utf-8")
    _atomic_write_bytes(path, payload)


def _append_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    """Locked atomic append for non-ledger compatibility paths."""

    if not records:
        return
    with _interprocess_lock(path):
        _write_jsonl(path, [*read_jsonl(path), *(dict(item) for item in records)])


def _sign_event(record: Mapping[str, Any]) -> dict[str, Any]:
    """Bind an append-only workflow event to its exact canonical contents."""
    unsigned = {key: value for key, value in record.items() if key != "event_sha256"}
    return {**unsigned, "event_sha256": _digest(unsigned)}


def _append_event(path: Path, record: Mapping[str, Any]) -> dict[str, Any]:
    with _interprocess_lock(path):
        existing = read_jsonl(path)
        errors = _ledger_integrity_errors(path, records=existing)
        if errors:
            raise ValueError("Нельзя продолжить повреждённый ledger: " + "; ".join(errors))
        checkpoint_path = _ledger_checkpoint_path(path)
        checkpoint = _read_json(checkpoint_path) if checkpoint_path.exists() else None
        ledger_id = (
            str(existing[0].get("ledger_id"))
            if existing
            else str(checkpoint.get("ledger_id"))
            if isinstance(checkpoint, Mapping) and _nonempty(checkpoint.get("ledger_id"))
            else str(uuid.uuid4())
        )
        previous = existing[-1].get("event_sha256") if existing else None
        chained = {
            **{key: value for key, value in record.items() if key not in {"ledger_id", "sequence", "previous_event_sha256", "event_sha256"}},
            "ledger_id": ledger_id,
            "sequence": len(existing) + 1,
            "previous_event_sha256": previous,
        }
        signed = _sign_event(chained)
        combined = [*existing, signed]
        _write_jsonl(path, combined)
        _atomic_write_json(
            checkpoint_path,
            {
                "schema_version": SCHEMA_VERSION,
                "ledger_id": ledger_id,
                "record_count": len(combined),
                "head_event_sha256": signed["event_sha256"],
            },
        )
        return signed


def _event_structure_error(record: Mapping[str, Any], ledger_name: str, line_number: int) -> str | None:
    common = {
        "schema_version",
        "record_type",
        "ledger_id",
        "sequence",
        "previous_event_sha256",
        "event_sha256",
    }
    fields_by_type = {
        "trigger_review": {
            "claim_id", "revision_id", "claim_sha256", "decision", "reviewer", "reason", "reviewed_at",
        },
        "run_attachment": {
            "request_id", "cassation_workspace", "sibling_cli", "status", "attached_at",
            "sibling_cli_sha256", "returncode", "stdout", "stderr", "error",
        },
        "result_import": {
            "request_id", "handoff_id", "result_schema_version", "status", "eligible_for_drafting",
            "claim_ids", "imported_at", "source_path", "source_sha256", "anchor_status",
            "anchor_handoff_id", "anchor_checked_at", "trusted_source_workspace", "sibling_cli",
            "sibling_cli_sha256", "attachment_event_sha256", "trust_anchor_sha256",
        },
        "wording_review": {
            "claim_id", "revision_id", "claim_sha256", "handoff_id", "request_id", "finding_ids",
            "maximum_permitted_claim", "plan_sha256", "evidence_sha256", "fingerprint_sha256",
            "human_decision_sha256", "validation_report_sha256", "normative_bridge_sha256",
            "decision", "reviewer", "reason", "wording_text", "wording_sha256",
            "wording_source_path", "wording_source_sha256", "reviewed_at",
        },
        "prefiling_refresh": {
            "as_of", "corpus_cutoff", "reviewer", "official_check_ref", "ready_claim_bindings",
            "ready_claim_set_sha256", "recorded_at",
        },
    }
    required_by_type = {
        "trigger_review": fields_by_type["trigger_review"],
        "run_attachment": {
            "request_id", "cassation_workspace", "sibling_cli", "status", "attached_at",
        },
        "result_import": {
            "request_id", "handoff_id", "result_schema_version", "status", "eligible_for_drafting",
            "claim_ids", "imported_at", "source_path", "source_sha256",
        },
        "wording_review": fields_by_type["wording_review"],
        "prefiling_refresh": fields_by_type["prefiling_refresh"],
    }
    record_type = record.get("record_type")
    allowed = fields_by_type.get(str(record_type))
    if allowed is None:
        return None
    required = required_by_type[str(record_type)]
    missing = sorted(field for field in required if field not in record or record.get(field) is None)
    if missing:
        return f"{ledger_name}, запись {line_number}: отсутствуют обязательные поля {missing}."
    unknown = sorted(set(record) - common - allowed)
    if unknown:
        return f"{ledger_name}, запись {line_number}: неизвестные поля {unknown}."
    if record_type == "prefiling_refresh":
        binding_fields = {
            "claim_id", "revision_id", "claim_sha256", "source_file_sha256",
            "input_bindings_sha256", "input_manifest_updated_at", "claim_created_at",
            "handoff_id", "plan_sha256",
            "evidence_sha256", "fingerprint_sha256", "maximum_permitted_claim",
            "wording_review_event_sha256", "wording_reviewed_at",
            "result_import_event_sha256", "result_imported_at", "result_source_sha256",
            "result_created_at", "attachment_event_sha256", "attachment_attached_at",
            "anchor_checked_at", "trust_anchor_sha256",
        }
        bindings = record.get("ready_claim_bindings")
        if not isinstance(bindings, list):
            return f"{ledger_name}, запись {line_number}: ready_claim_bindings должен быть массивом."
        for index, binding in enumerate(bindings, 1):
            if not isinstance(binding, Mapping) or set(binding) != binding_fields:
                return (
                    f"{ledger_name}, запись {line_number}: ready_claim_bindings[{index}] "
                    "не соответствует закрытому exact-material контракту."
                )
        if record.get("ready_claim_set_sha256") != _digest(bindings):
            return (
                f"{ledger_name}, запись {line_number}: ready_claim_set_sha256 "
                "не совпадает с exact-material bindings."
            )
    return None


def _event_record_error(
    record: Mapping[str, Any],
    *,
    ledger_name: str,
    line_number: int,
) -> str | None:
    structure = _event_structure_error(record, ledger_name, line_number)
    if structure:
        return structure
    supplied = record.get("event_sha256")
    expected = _digest({key: value for key, value in record.items() if key != "event_sha256"})
    if not _is_sha256(supplied) or supplied != expected:
        return (
            f"{ledger_name}, запись {line_number}: event_sha256 не совпадает с содержимым. "
            "Не используйте этот журнал для подготовки жалобы; восстановите его из доверенной копии."
        )
    return None


def _ledger_integrity_errors(
    path: Path,
    *,
    records: Sequence[Mapping[str, Any]] | None = None,
) -> list[str]:
    records = list(records) if records is not None else read_jsonl(path)
    errors: list[str] = []
    previous: str | None = None
    ledger_id: str | None = None
    for line_number, record in enumerate(records, 1):
        current_ledger = record.get("ledger_id")
        if not _nonempty(current_ledger):
            errors.append(f"{path.name}, запись {line_number}: отсутствует ledger_id.")
        elif ledger_id is None:
            ledger_id = str(current_ledger)
        elif current_ledger != ledger_id:
            errors.append(f"{path.name}, запись {line_number}: ledger_id изменился.")
        if record.get("sequence") != line_number:
            errors.append(f"{path.name}, запись {line_number}: нарушена sequence.")
        if record.get("previous_event_sha256") != previous:
            errors.append(f"{path.name}, запись {line_number}: нарушена hash-chain связь.")
        error = _event_record_error(record, ledger_name=path.name, line_number=line_number)
        if error:
            errors.append(error)
        previous = record.get("event_sha256") if _is_sha256(record.get("event_sha256")) else None
    checkpoint_path = _ledger_checkpoint_path(path)
    if records:
        if not checkpoint_path.exists():
            errors.append(f"{path.name}: отсутствует ledger head checkpoint.")
        else:
            try:
                checkpoint = _read_json(checkpoint_path)
            except ValueError as exc:
                errors.append(str(exc))
            else:
                if not isinstance(checkpoint, Mapping):
                    errors.append(f"{path.name}: checkpoint должен быть объектом.")
                elif (
                    checkpoint.get("ledger_id") != ledger_id
                    or checkpoint.get("record_count") != len(records)
                    or checkpoint.get("head_event_sha256") != previous
                ):
                    errors.append(f"{path.name}: checkpoint не совпадает с ledger head/count.")
    elif checkpoint_path.exists():
        errors.append(f"{path.name}: ledger усечён, но checkpoint сохранился.")
    return errors


def _event_integrity_errors(
    ledgers: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[str]:
    errors: list[str] = []
    for ledger_name, records in ledgers.items():
        for line_number, record in enumerate(records, 1):
            error = _event_record_error(
                record,
                ledger_name=ledger_name,
                line_number=line_number,
            )
            if error:
                errors.append(error)
    return errors


def _load_config(workspace: str | Path) -> dict[str, Any]:
    config = _read_json(_analysis_root(workspace) / CONFIG_FILE)
    if not isinstance(config, dict) or not _nonempty(config.get("case_id")):
        raise ValueError("config.json не содержит непустой case_id; повторите init в новом workspace.")
    return config


def _load_manifest(workspace: str | Path) -> dict[str, Any]:
    manifest = _read_json(_analysis_root(workspace) / INPUT_MANIFEST_FILE)
    if not isinstance(manifest, dict):
        raise ValueError("input-manifest.json должен содержать объект.")
    return manifest


def _document_identity(document: Mapping[str, Any], index: int) -> str:
    for key in ("document_id", "id", "relative_path", "path", "name"):
        if _nonempty(document.get(key)):
            return str(document[key]).strip()
    return f"document-{index + 1}"


def _case_dependencies(case_file: Mapping[str, Any], file_sha256: str) -> dict[str, str]:
    dependencies: dict[str, str] = {"__casefile__": file_sha256}
    documents = case_file.get("documents", [])
    if isinstance(documents, list):
        for index, document in enumerate(documents):
            if not isinstance(document, Mapping):
                continue
            identity = _document_identity(document, index)
            raw_sha = document.get("sha256")
            dependencies[identity] = str(raw_sha) if _is_sha256(raw_sha) else _digest(document)
    return dependencies


def _hypothesis_dependencies(argument_research: Mapping[str, Any] | None) -> dict[str, str]:
    if argument_research is None:
        return {}
    result: dict[str, str] = {}
    hypotheses = argument_research.get("hypotheses", [])
    if isinstance(hypotheses, list):
        for index, hypothesis in enumerate(hypotheses):
            if not isinstance(hypothesis, Mapping):
                continue
            hypothesis_id = hypothesis.get("hypothesis_id") or hypothesis.get("id")
            if _nonempty(hypothesis_id):
                result[str(hypothesis_id).strip()] = _digest(hypothesis)
            else:
                result[f"hypothesis-{index + 1}"] = _digest(hypothesis)
    return result


@_workspace_operation("mutation")
def init_workspace(
    workspace: str | Path,
    *,
    case_id: str,
    case_file: str | Path,
    argument_research: str | Path | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Initialize or refresh current input bindings without rewriting ledgers."""

    case_id = _require_nonempty(case_id, "case_id")
    root = _analysis_root(workspace)
    root.mkdir(parents=True, exist_ok=True)
    config_path = root / CONFIG_FILE
    if config_path.exists():
        existing = _read_json(config_path)
        if not isinstance(existing, dict) or existing.get("case_id") != case_id:
            raise ValueError(
                "Workspace уже связан с другим case_id; создайте отдельный matter workspace."
            )
        config = existing
    else:
        config = {
            "schema_version": SCHEMA_VERSION,
            "case_id": case_id,
            "created_at": now or _now(),
        }
        _atomic_write_json(config_path, config)

    case_path = Path(case_file).expanduser().resolve()
    case_payload = _read_json(case_path)
    if not isinstance(case_payload, dict):
        raise ValueError("CaseFile должен быть JSON-объектом.")
    case_sha = _file_sha256(case_path)

    argument_path: Path | None = None
    argument_payload: Mapping[str, Any] | None = None
    argument_sha: str | None = None
    if argument_research is not None:
        argument_path = Path(argument_research).expanduser().resolve()
        loaded_argument = _read_json(argument_path)
        if not isinstance(loaded_argument, dict):
            raise ValueError("ArgumentResearch должен быть JSON-объектом.")
        argument_payload = loaded_argument
        argument_sha = _file_sha256(argument_path)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "updated_at": now or _now(),
        "case_file": {
            "path": str(case_path),
            "sha256": case_sha,
        },
        "case_dependencies": _case_dependencies(case_payload, case_sha),
        "argument_research": (
            {"path": str(argument_path), "sha256": argument_sha}
            if argument_path is not None
            else None
        ),
        "hypothesis_dependencies": _hypothesis_dependencies(argument_payload),
    }
    manifest["input_bindings_sha256"] = _digest(
        {
            "case_dependencies": manifest["case_dependencies"],
            "hypothesis_dependencies": manifest["hypothesis_dependencies"],
        }
    )
    _atomic_write_json(root / INPUT_MANIFEST_FILE, manifest)
    return manifest


def _docx_paragraphs(path: Path) -> list[str]:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if any(info.file_size > MAX_DOCX_PART_BYTES for info in infos):
                raise ValueError(f"DOCX {path} превышает лимит размера одной части.")
            if sum(info.file_size for info in infos) > MAX_DOCX_TOTAL_BYTES:
                raise ValueError(f"DOCX {path} превышает общий лимит распаковки.")
            names = {info.filename for info in infos}
            if "word/document.xml" not in names:
                raise ValueError(f"DOCX {path} не содержит word/document.xml.")
            selected_names = ["word/document.xml"]
            selected_names.extend(
                sorted(
                    name
                    for name in names
                    if name in {"word/footnotes.xml", "word/endnotes.xml", "word/comments.xml"}
                    or re.fullmatch(r"word/(?:header|footer)\d+\.xml", name)
                )
            )
            xml_parts = [(name, archive.read(name)) for name in selected_names]
    except ValueError:
        raise
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise ValueError(
            f"Не удалось извлечь текст DOCX {path}; проверьте файл или передайте TXT/JSON."
        ) from exc
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs: list[str] = []
    for part_name, xml_bytes in xml_parts:
        try:
            root = ElementTree.fromstring(xml_bytes)
        except ElementTree.ParseError as exc:
            raise ValueError(f"Повреждён {part_name} в {path}.") from exc
        for paragraph in root.iter(f"{namespace}p"):
            text = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t"))
            normalized = _normalize_text(text)
            if normalized:
                paragraphs.append(normalized)
    return paragraphs


def _plain_paragraphs(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Файл {path} не является UTF-8; передайте DOCX, UTF-8 TXT/MD или JSON.") from exc
    blocks = [_normalize_text(item) for item in re.split(r"\n\s*\n", text) if _normalize_text(item)]
    if len(blocks) <= 1:
        line_blocks = [_normalize_text(item) for item in text.splitlines() if _normalize_text(item)]
        if line_blocks:
            blocks = line_blocks
    return blocks


def _structured_claims(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path)
    if isinstance(payload, list):
        values = payload
    elif isinstance(payload, dict):
        candidate = payload.get("claims", payload.get("practice_claims"))
        if isinstance(candidate, list):
            values = candidate
        else:
            values = []
            for collection_name in ("hypotheses", "options"):
                collection = payload.get(collection_name, [])
                if isinstance(collection, list):
                    values.extend(collection)
    else:
        raise ValueError("Структурированный вход должен быть JSON-объектом или массивом.")
    claims: list[dict[str, Any]] = []
    for index, value in enumerate(values):
        if not isinstance(value, Mapping):
            raise ValueError(f"Элемент claims[{index}] должен быть объектом.")
        item = dict(value)
        text_value = next(
            (
                item.get(key)
                for key in (
                    "text",
                    "claim_text",
                    "thesis",
                    "challenged_norm_and_meaning",
                    "plain_language_problem",
                    "title",
                )
                if _nonempty(item.get(key))
            ),
            None,
        )
        if not _nonempty(text_value):
            raise ValueError(f"claims[{index}] не содержит непустой текст утверждения.")
        item["text"] = _normalize_text(str(text_value))
        item.setdefault("source_locator", f"{path.name}#claims[{index}]")
        claims.append(item)
    return claims


def _input_claims(path: Path) -> tuple[str, list[dict[str, Any]]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json", _structured_claims(path)
    if suffix == ".docx":
        paragraphs = _docx_paragraphs(path)
        format_name = "docx"
    elif suffix in {".txt", ".md"}:
        paragraphs = _plain_paragraphs(path)
        format_name = suffix.lstrip(".")
    else:
        raise ValueError("Поддерживаются JSON, UTF-8 TXT/MD и DOCX.")
    return format_name, [
        {
            "text": paragraph,
            "source_locator": f"{path.name}#paragraph-{index + 1}",
        }
        for index, paragraph in enumerate(paragraphs)
    ]


def _detect_triggers(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    normalized = _normalize_text(text)
    if normalized.endswith("?") and re.match(
        r"^(?:нужно|следует|требуется|необходимо|просим|заявитель\s+просит)\s+(?:ли\s+)?(?:проверить|установить|исследовать)",
        normalized,
        re.IGNORECASE,
    ):
        return [], []
    evidence: list[dict[str, Any]] = []
    dimensions: list[str] = []
    for dimension, rule_id, pattern in TRIGGER_RULES:
        for match in pattern.finditer(text):
            evidence.append(
                {
                    "rule_id": rule_id,
                    "dimension": dimension,
                    "match": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                }
            )
            if dimension not in dimensions:
                dimensions.append(dimension)
    return evidence, dimensions


def _string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(_nonempty(item) for item in value):
        raise ValueError(f"{field} должен быть массивом непустых строк.")
    return [str(item).strip() for item in value]


def _active_claims(workspace: str | Path) -> dict[str, dict[str, Any]]:
    records = read_jsonl(_analysis_root(workspace) / CLAIM_LEDGER_FILE)
    active: dict[str, dict[str, Any]] = {}
    for record in records:
        claim_id = record.get("claim_id")
        if _nonempty(claim_id):
            if record.get("record_type") == "claim_tombstone":
                active.pop(str(claim_id), None)
            elif record.get("record_type") == "claim_revision":
                active[str(claim_id)] = record
    return active


def _claim_material_from_record(record: Mapping[str, Any]) -> dict[str, Any]:
    source = record.get("source", {})
    bindings = record.get("bindings", {})
    material = {
        "claim_id": record.get("claim_id"),
        "claim_text": record.get("claim_text"),
        "source_locator": source.get("locator") if isinstance(source, Mapping) else None,
        "hypothesis_ids": record.get("hypothesis_ids", []),
        "option_ids": record.get("option_ids", []),
        "norm_refs": record.get("norm_refs", []),
        "empirical_dimensions": record.get("empirical_dimensions", []),
        "trigger_evidence": record.get("trigger_evidence", []),
        "practice_dependency_explicit": record.get("practice_dependency_explicit"),
        "analysis_route": record.get("analysis_route"),
        "case_dependency_ids": (
            bindings.get("case_dependency_ids", [])
            if isinstance(bindings, Mapping)
            else []
        ),
        "case_dependency_sha256": (
            bindings.get("case_dependency_sha256")
            if isinstance(bindings, Mapping)
            else None
        ),
        "hypothesis_sha256": (
            bindings.get("hypothesis_sha256")
            if isinstance(bindings, Mapping)
            else None
        ),
        "research_question": record.get("research_question"),
    }
    return material


def _claim_record_error(record: Mapping[str, Any], line_number: int) -> str | None:
    claim_id = record.get("claim_id")
    if record.get("record_type") == "claim_tombstone":
        allowed = {
            "schema_version", "record_type", "case_id", "claim_id", "source_path",
            "supersedes_revision_id", "created_at", "ledger_id", "sequence",
            "previous_event_sha256", "event_sha256",
        }
        if unknown := sorted(set(record) - allowed):
            return f"claim-ledger строка {line_number}: неизвестные поля {unknown}."
        if not _nonempty(claim_id) or not _nonempty(record.get("source_path")):
            return f"claim-ledger строка {line_number}: tombstone требует claim_id и source_path."
        return _event_record_error(record, ledger_name=CLAIM_LEDGER_FILE, line_number=line_number)
    if record.get("record_type") != "claim_revision" or not _nonempty(claim_id):
        return f"claim-ledger строка {line_number}: неверный record_type или claim_id."
    allowed = {
        "schema_version", "record_type", "case_id", "claim_id", "revision_id", "claim_sha256",
        "claim_text", "source", "hypothesis_ids", "option_ids", "norm_refs",
        "empirical_dimensions", "trigger_evidence", "practice_dependency_explicit",
        "analysis_route", "research_question", "bindings", "supersedes_revision_id", "created_at",
        "ledger_id", "sequence", "previous_event_sha256", "event_sha256",
    }
    if unknown := sorted(set(record) - allowed):
        return f"claim-ledger строка {line_number}: неизвестные поля {unknown}."
    expected_claim_sha = _digest(_claim_material_from_record(record))
    if record.get("claim_sha256") != expected_claim_sha:
        return f"claim-ledger строка {line_number}, claim {claim_id}: claim_sha256 не совпадает."
    source = record.get("source")
    source_file_sha = source.get("source_file_sha256") if isinstance(source, Mapping) else None
    expected_revision = _digest(
        {
            "claim_id": claim_id,
            "claim_sha256": expected_claim_sha,
            "source_file_sha256": source_file_sha,
        }
    )
    if record.get("revision_id") != expected_revision:
        return f"claim-ledger строка {line_number}, claim {claim_id}: revision_id не совпадает."
    if not isinstance(source, Mapping) or source.get("context_sha256") != _digest(record.get("claim_text")):
        return f"claim-ledger строка {line_number}, claim {claim_id}: source context_sha256 не совпадает."
    if not _is_sha256(source_file_sha):
        return f"claim-ledger строка {line_number}, claim {claim_id}: source_file_sha256 отсутствует или некорректен."
    return _event_record_error(record, ledger_name=CLAIM_LEDGER_FILE, line_number=line_number)


def _claim_ledger_integrity(records: Sequence[Mapping[str, Any]]) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    invalid_claim_ids: set[str] = set()
    previous_by_claim: dict[str, str] = {}
    for line_number, record in enumerate(records, 1):
        error = _claim_record_error(record, line_number)
        if error:
            errors.append(error)
            if _nonempty(record.get("claim_id")):
                invalid_claim_ids.add(str(record["claim_id"]))
        claim_id = record.get("claim_id")
        if not _nonempty(claim_id):
            continue
        claim_key = str(claim_id)
        expected_supersedes = previous_by_claim.get(claim_key)
        if record.get("supersedes_revision_id") != expected_supersedes:
            errors.append(
                f"claim-ledger строка {line_number}, claim {claim_key}: нарушена цепочка supersedes_revision_id."
            )
            invalid_claim_ids.add(claim_key)
        if record.get("record_type") == "claim_tombstone":
            previous_by_claim.pop(claim_key, None)
        elif _nonempty(record.get("revision_id")):
            previous_by_claim[claim_key] = str(record["revision_id"])
    return errors, invalid_claim_ids


def _case_projection(dependency_ids: Sequence[str], manifest: Mapping[str, Any]) -> str:
    available = manifest.get("case_dependencies", {})
    if not isinstance(available, Mapping):
        raise ValueError("input-manifest.json не содержит case_dependencies.")
    projection: dict[str, str] = {}
    for dependency_id in dependency_ids:
        value = available.get(dependency_id)
        if not _is_sha256(value):
            raise ValueError(
                f"Не найдена case dependency {dependency_id}; обновите CaseFile или исправьте claim."
            )
        projection[dependency_id] = str(value)
    return _digest(projection)


def _hypothesis_projection(hypothesis_ids: Sequence[str], manifest: Mapping[str, Any]) -> str:
    available = manifest.get("hypothesis_dependencies", {})
    if not isinstance(available, Mapping):
        available = {}
    projection = {
        hypothesis_id: available.get(hypothesis_id, "__unbound__")
        for hypothesis_id in hypothesis_ids
    }
    return _digest(projection)


def _write_claim_index(workspace: str | Path) -> dict[str, Any]:
    active = _active_claims(workspace)
    index = {
        "schema_version": SCHEMA_VERSION,
        "claims": {
            claim_id: {
                "revision_id": record.get("revision_id"),
                "claim_sha256": record.get("claim_sha256"),
                "source_locator": record.get("source", {}).get("locator"),
            }
            for claim_id, record in sorted(active.items())
        },
    }
    _atomic_write_json(_analysis_root(workspace) / CLAIM_INDEX_FILE, index)
    return index


@_workspace_operation("mutation")
def scan_input(
    workspace: str | Path,
    input_path: str | Path,
    *,
    now: str | None = None,
) -> dict[str, Any]:
    """Scan structured claims or text and append immutable claim revisions."""

    config = _load_config(workspace)
    manifest = _load_manifest(workspace)
    source = Path(input_path).expanduser().resolve()
    if not source.exists():
        raise ValueError(f"Не найден вход для scan: {source}")
    source_sha_before = _file_sha256(source)
    format_name, raw_claims = _input_claims(source)
    source_file_sha = _file_sha256(source)
    if source_file_sha != source_sha_before:
        raise ValueError("Входной файл изменился во время scan; повторите сканирование.")
    if not raw_claims:
        raise ValueError("Во входе не найдено ни одного непустого утверждения.")
    active_before = _active_claims(workspace)
    active_at_start = dict(active_before)
    revisions: list[dict[str, Any]] = []
    returned: list[dict[str, Any]] = []
    seen_claim_ids: set[str] = set()
    timestamp = now or _now()

    for index, item in enumerate(raw_claims):
        text = _normalize_text(str(item["text"]))
        source_locator = _require_nonempty(item.get("source_locator"), "source_locator")
        claim_id = item.get("claim_id")
        if not _nonempty(claim_id):
            claim_id = "claim-" + _digest(
                {"source": source.name, "locator": source_locator}
            )[:20]
        claim_id = str(claim_id).strip()
        seen_claim_ids.add(claim_id)
        hypothesis_ids = _string_list(item.get("hypothesis_ids"), "hypothesis_ids")
        option_ids = _string_list(item.get("option_ids"), "option_ids")
        norm_refs = _string_list(item.get("norm_refs"), "norm_refs")
        dependency_ids = _string_list(item.get("case_dependency_ids"), "case_dependency_ids")
        if not dependency_ids:
            dependency_ids = ["__casefile__"]
        case_projection_sha = _case_projection(dependency_ids, manifest)
        hypothesis_projection_sha = _hypothesis_projection(hypothesis_ids, manifest)
        trigger_evidence, dimensions = _detect_triggers(text)
        explicit_dependency = item.get("practice_dependency")
        if explicit_dependency not in (None, True, False):
            raise ValueError(f"claim {claim_id}: practice_dependency должен быть true/false/null.")
        if explicit_dependency is True and not dimensions:
            dimensions.append("judicial_meaning")
            trigger_evidence.append(
                {
                    "rule_id": "structured_practice_dependency",
                    "dimension": "judicial_meaning",
                    "match": "practice_dependency=true",
                    "start": None,
                    "end": None,
                }
            )
        route = item.get("analysis_route")
        if not _nonempty(route):
            route = "cassation_corpus" if dimensions else "single_case_meaning"
        if route not in {
            "single_case_meaning",
            "cassation_corpus",
            "higher_court_authority",
            "non_judicial_empirical",
        }:
            raise ValueError(f"claim {claim_id}: неизвестный analysis_route {route}.")

        claim_material = {
            "claim_id": claim_id,
            "claim_text": text,
            "source_locator": source_locator,
            "hypothesis_ids": hypothesis_ids,
            "option_ids": option_ids,
            "norm_refs": norm_refs,
            "empirical_dimensions": dimensions,
            "trigger_evidence": trigger_evidence,
            "practice_dependency_explicit": explicit_dependency,
            "analysis_route": route,
            "case_dependency_ids": dependency_ids,
            "case_dependency_sha256": case_projection_sha,
            "hypothesis_sha256": hypothesis_projection_sha,
            "research_question": (
                _normalize_text(str(item["research_question"]))
                if _nonempty(item.get("research_question"))
                else None
            ),
        }
        claim_sha = _digest(claim_material)
        revision_id = _digest(
            {
                "claim_id": claim_id,
                "claim_sha256": claim_sha,
                "source_file_sha256": source_file_sha,
            }
        )
        prior = active_before.get(claim_id)
        revision = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "claim_revision",
            "case_id": config["case_id"],
            "claim_id": claim_id,
            "revision_id": revision_id,
            "claim_sha256": claim_sha,
            "claim_text": text,
            "source": {
                "path": str(source),
                "format": format_name,
                "locator": source_locator,
                "context_sha256": _digest(text),
                "source_file_sha256": source_file_sha,
            },
            "hypothesis_ids": hypothesis_ids,
            "option_ids": option_ids,
            "norm_refs": norm_refs,
            "empirical_dimensions": dimensions,
            "trigger_evidence": trigger_evidence,
            "practice_dependency_explicit": explicit_dependency,
            "analysis_route": route,
            "research_question": claim_material["research_question"],
            "bindings": {
                "case_dependency_ids": dependency_ids,
                "case_dependency_sha256": case_projection_sha,
                "hypothesis_sha256": hypothesis_projection_sha,
            },
            "supersedes_revision_id": (
                prior.get("revision_id")
                if prior and prior.get("revision_id") != revision_id
                else None
            ),
            "created_at": timestamp,
        }
        if not prior or prior.get("revision_id") != revision_id:
            revisions.append(revision)
            active_before[claim_id] = revision
        else:
            revision = prior
        returned.append(revision)

    tombstones: list[dict[str, Any]] = []
    for removed_id, prior in sorted(active_at_start.items()):
        prior_source = prior.get("source", {})
        if (
            removed_id not in seen_claim_ids
            and isinstance(prior_source, Mapping)
            and prior_source.get("path") == str(source)
        ):
            tombstones.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "record_type": "claim_tombstone",
                    "case_id": config["case_id"],
                    "claim_id": removed_id,
                    "source_path": str(source),
                    "supersedes_revision_id": prior.get("revision_id"),
                    "created_at": timestamp,
                }
            )
    claim_ledger = _analysis_root(workspace) / CLAIM_LEDGER_FILE
    for record in [*revisions, *tombstones]:
        _append_event(claim_ledger, record)
    scan = {
        "schema_version": SCHEMA_VERSION,
        "case_id": config["case_id"],
        "scanned_at": timestamp,
        "format": format_name,
        "source": {
            "path": str(source),
            "sha256": source_file_sha,
            "format": format_name,
        },
        "claims": returned,
        "new_revision_count": len(revisions),
        "tombstone_count": len(tombstones),
    }
    _atomic_write_json(_analysis_root(workspace) / TRIGGER_SCAN_FILE, scan)
    _write_claim_index(workspace)
    return scan


def _latest_event(
    records: Iterable[Mapping[str, Any]],
    **matches: Any,
) -> dict[str, Any] | None:
    result: dict[str, Any] | None = None
    for record in records:
        if all(record.get(key) == value for key, value in matches.items()):
            result = dict(record)
    return result


@_workspace_operation("mutation")
def review_trigger(
    workspace: str | Path,
    *,
    claim_id: str,
    decision: str,
    reviewer: str,
    reason: str,
    now: str | None = None,
) -> dict[str, Any]:
    active = _active_claims(workspace)
    if claim_id not in active:
        raise ValueError(f"Не найден активный claim_id {claim_id}.")
    decision = decision.replace("-", "_")
    if decision not in {"required", "not_required"}:
        raise ValueError("decision должен быть required или not_required.")
    reviewer = _require_nonempty(reviewer, "reviewer")
    reason = _require_nonempty(reason, "причина review")
    claim = active[claim_id]
    record = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "trigger_review",
        "claim_id": claim_id,
        "revision_id": claim["revision_id"],
        "claim_sha256": claim["claim_sha256"],
        "decision": decision,
        "reviewer": reviewer,
        "reason": reason,
        "reviewed_at": now or _now(),
    }
    record = _append_event(_analysis_root(workspace) / TRIGGER_REVIEWS_FILE, record)
    return record


def _sorted_claim_bindings(bindings: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (dict(item) for item in bindings),
        key=lambda item: (
            str(item.get("claim_id", "")),
            str(item.get("claim_sha256", "")),
            str(item.get("source_locator", "")),
        ),
    )


def _public_claim_id(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9._-]{1,80}", value) and "@" not in value:
        return value
    return "claim-" + _digest({"private_claim_id": value})[:24]


def _public_source_locator(value: str) -> str:
    if (
        re.fullmatch(r"[A-Za-z0-9._#\[\]-]{1,160}", value)
        and "/" not in value
        and "\\" not in value
        and "@" not in value
    ):
        return value
    return "source-" + _digest({"private_source_locator": value})[:24]


def _neutral_question(claim: Mapping[str, Any]) -> str:
    dimensions = claim.get("empirical_dimensions", [])
    if not isinstance(dimensions, list) or not dimensions:
        dimensions = ["judicial_meaning"]
    questions = [QUESTION_BY_DIMENSION[item] for item in dimensions if item in QUESTION_BY_DIMENSION]
    norm_refs = claim.get("norm_refs", [])
    norm_suffix = ""
    if isinstance(norm_refs, list) and norm_refs:
        norm_suffix = " Нормативный фокус: " + ", ".join(str(item) for item in norm_refs) + "."
    base = " ".join(dict.fromkeys(questions))
    return base + norm_suffix


def _request_core(payload: Mapping[str, Any]) -> dict[str, Any]:
    bindings = payload.get("claim_bindings")
    questions = payload.get("questions")
    if not isinstance(bindings, list) or not all(isinstance(item, Mapping) for item in bindings):
        raise ValueError("Request требует claim_bindings[].")
    if not isinstance(questions, list) or not questions or not all(_nonempty(item) for item in questions):
        raise ValueError("Request требует непустой questions[].")
    for index, binding in enumerate(bindings):
        if set(binding) != {"claim_id", "claim_sha256", "source_locator"}:
            raise ValueError(f"Request claim_bindings[{index}] содержит неизвестные/пропущенные поля.")
        _require_nonempty(binding.get("claim_id"), f"claim_bindings[{index}].claim_id")
        _require_sha256(binding.get("claim_sha256"), f"claim_bindings[{index}].claim_sha256")
        _require_nonempty(binding.get("source_locator"), f"claim_bindings[{index}].source_locator")
    if len({str(item["claim_id"]) for item in bindings}) != len(bindings):
        raise ValueError("Request claim_bindings содержит повторный claim_id.")
    sorted_bindings = _sorted_claim_bindings(bindings)
    claim_set_sha = _digest(sorted_bindings)
    return {
        "questions": list(questions),
        "claim_bindings": sorted_bindings,
        "claim_set_sha256": claim_set_sha,
    }


def _envelope_digest(envelope: Mapping[str, Any]) -> str:
    return _digest({key: value for key, value in envelope.items() if key != "handoff_id"})


@_workspace_operation("mutation")
def create_request(
    workspace: str | Path,
    *,
    claim_ids: Sequence[str] | None = None,
    output: str | Path | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    state = derive_state(workspace, stage="options")
    state_by_id = {item["claim_id"]: item for item in state["claims"]}
    active = _active_claims(workspace)
    selected_ids = list(claim_ids or [])
    if not selected_ids:
        selected_ids = [
            claim_id
            for claim_id, item in state_by_id.items()
            if item["state"] in {"required", "blocked", "stale"}
        ]
    selected: list[dict[str, Any]] = []
    for claim_id in selected_ids:
        claim = active.get(claim_id)
        if claim is None:
            raise ValueError(f"Не найден активный claim_id {claim_id}.")
        if state_by_id[claim_id]["state"] == "not_required":
            raise ValueError(f"Claim {claim_id} отмечен not_required и не должен входить в corpus request.")
        selected.append(claim)
    if not selected:
        raise ValueError("Нет practice-dependent claims для нейтрального запроса.")

    bindings = _sorted_claim_bindings(
        [
            {
                "claim_id": _public_claim_id(str(claim["claim_id"])),
                "claim_sha256": claim["claim_sha256"],
                "source_locator": _public_source_locator(str(claim["source"]["locator"])),
            }
            for claim in selected
        ]
    )
    questions = [_neutral_question(claim) for claim in selected]
    alias_records = {
        _public_claim_id(str(claim["claim_id"])): {
            "private_claim_id": claim["claim_id"],
            "private_source_locator": claim["source"]["locator"],
        }
        for claim in selected
    }
    aliases_path = _analysis_root(workspace) / CLAIM_ALIASES_FILE
    existing_aliases = _read_json(aliases_path) if aliases_path.exists() else {}
    if not isinstance(existing_aliases, dict):
        raise ValueError("claim-aliases.json должен быть объектом.")
    existing_aliases.update(alias_records)
    _atomic_write_json(aliases_path, existing_aliases)
    core = {
        "questions": questions,
        "claim_bindings": bindings,
        "claim_set_sha256": _digest(bindings),
    }
    request_sha = _digest(core)
    payload = {
        **core,
        "request_sha256": request_sha,
        "claim_questions": [
            {
                "claim_id": _public_claim_id(str(claim["claim_id"])),
                "question_id": _digest(
                    {"claim_id": claim["claim_id"], "question": question}
                ),
                "question": question,
                "disconfirmation_prompts": [
                    "Найти противоположное или более узкое прочтение.",
                    "Проверить самостоятельные альтернативные основания исхода.",
                    "Проверить позднейшее регулирование и позиции высшей инстанции.",
                ],
            }
            for claim, question in zip(selected, questions)
        ],
        "drafting_ready": False,
    }
    evidence_scope = {
        claim["claim_id"]: claim["bindings"]["case_dependency_sha256"]
        for claim in selected
    }
    timestamp = now or _now()
    envelope: dict[str, Any] = {
        "schema_version": HANDOFF_VERSION,
        "created_at": timestamp,
        "source_skill": SOURCE_SKILL,
        "target_skill": TARGET_SKILL,
        "run_id": f"practice-request-{request_sha[:16]}",
        "plan_sha256": request_sha,
        "evidence_sha256": _digest(evidence_scope),
        "payload_type": "unproven_research_questions",
        "payload": payload,
        "limitations": [
            "Передаются только недоказанные вопросы; payload не является выводом для жалобы.",
            "Акты заявителя и их полный текст остаются в case-private workspace.",
        ],
    }
    envelope["handoff_id"] = _envelope_digest(envelope)
    canonical_destination = (
        _analysis_root(workspace) / "requests" / f"{envelope['handoff_id']}.json"
    )
    exported = Path(output).expanduser().resolve() if output is not None else None
    if exported is not None and exported.exists():
        existing_export = _read_json(exported)
        if existing_export != envelope:
            raise ValueError(f"Export path уже содержит другое содержимое: {exported}")
    if canonical_destination.exists():
        existing = _read_json(canonical_destination)
        if existing != envelope:
            raise ValueError(
                f"Request path уже содержит другое содержимое: {canonical_destination}"
            )
    else:
        _atomic_write_json(canonical_destination, envelope)
    if exported is not None:
        if not exported.exists() and exported != canonical_destination:
            _atomic_write_json(exported, envelope)
    return envelope


def _request_by_id(workspace: str | Path, request_id: str) -> tuple[Path, dict[str, Any]]:
    _require_sha256(request_id, "request_id")
    path = _analysis_root(workspace) / "requests" / f"{request_id}.json"
    request = _read_json(path)
    if not isinstance(request, dict):
        raise ValueError(f"Request {request_id} должен быть JSON-объектом.")
    if request.get("handoff_id") != _envelope_digest(request):
        raise ValueError(f"Request {request_id}: handoff_id не соответствует содержимому.")
    if request.get("handoff_id") != request_id:
        raise ValueError(f"Request {request_id}: имя/ID не совпадает с handoff_id.")
    if (
        request.get("schema_version") != HANDOFF_VERSION
        or request.get("source_skill") != SOURCE_SKILL
        or request.get("target_skill") != TARGET_SKILL
        or request.get("payload_type") != "unproven_research_questions"
    ):
        raise ValueError(f"Request {request_id}: неверный envelope contract.")
    exact_envelope_fields = {
        "schema_version", "handoff_id", "created_at", "source_skill", "target_skill",
        "run_id", "plan_sha256", "evidence_sha256", "payload_type", "payload", "limitations",
    }
    if set(request) != exact_envelope_fields:
        raise ValueError(f"Request {request_id}: envelope содержит неизвестные/пропущенные поля.")
    payload = request.get("payload")
    if not isinstance(payload, Mapping):
        raise ValueError(f"Request {request_id} не содержит payload.")
    core = _request_core(payload)
    if payload.get("claim_set_sha256") != core["claim_set_sha256"]:
        raise ValueError(f"Request {request_id}: claim_set_sha256 не совпадает.")
    if payload.get("request_sha256") != _digest(core):
        raise ValueError(f"Request {request_id}: request_sha256 не совпадает.")
    return path, request


@_workspace_operation("mutation")
def attach_run(
    workspace: str | Path,
    *,
    request_id: str,
    cassation_workspace: str | Path,
    skills_root: str | Path | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    request_path, _ = _request_by_id(workspace, request_id)
    if skills_root is None:
        skill_root = Path(__file__).resolve().parents[2]
    else:
        skill_root = Path(skills_root).expanduser().resolve()
    sibling_cli = (
        skill_root
        / "ksrf-cassation-judicial-meaning"
        / "scripts"
        / "judicial_meaning.py"
    )
    cassation_root = Path(cassation_workspace).expanduser().resolve()
    timestamp = now or _now()
    base_record = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "run_attachment",
        "request_id": request_id,
        "cassation_workspace": str(cassation_root),
        "sibling_cli": str(sibling_cli),
        "attached_at": timestamp,
    }
    if not sibling_cli.is_file():
        record = {
            **base_record,
            "status": "blocked",
            "error": (
                "Не найден установленный ksrf-cassation-judicial-meaning: "
                f"ожидался CLI {sibling_cli}. Установите полный KSRF skillset или укажите --skills-root."
            ),
        }
        record = _append_event(_analysis_root(workspace) / ATTACHMENTS_FILE, record)
        return record

    cassation_root.mkdir(parents=True, exist_ok=True)
    ledger = cassation_root / "handoff-inbox.jsonl"
    command = [
        sys.executable,
        str(sibling_cli),
        "handoff",
        "import",
        "--input",
        str(request_path),
        "--ledger",
        str(ledger),
        "--expected-target",
        TARGET_SKILL,
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        record = {
            **base_record,
            "status": "blocked",
            "sibling_cli_sha256": _file_sha256(sibling_cli),
            "error": f"Не удалось импортировать request в кассационный скилл: {exc}",
        }
        record = _append_event(_analysis_root(workspace) / ATTACHMENTS_FILE, record)
        return record

    if completed.returncode == 0:
        status = "attached"
        error = None
    else:
        status = "blocked"
        detail = _normalize_text(completed.stderr or completed.stdout or "без диагностического вывода")
        error = f"Кассационный CLI отклонил request (код {completed.returncode}): {detail[:2000]}"
    record = {
        **base_record,
        "status": status,
        "sibling_cli_sha256": _file_sha256(sibling_cli),
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
        "error": error,
    }
    record = _append_event(_analysis_root(workspace) / ATTACHMENTS_FILE, record)
    return record


def _validate_envelope_identity(envelope: Mapping[str, Any]) -> None:
    if envelope.get("handoff_id") != _envelope_digest(envelope):
        raise ValueError("handoff_id не соответствует каноническому содержимому result envelope.")
    if envelope.get("source_skill") != TARGET_SKILL:
        raise ValueError("Result имеет неверный source_skill; ожидался кассационный скилл.")
    if envelope.get("target_skill") != SOURCE_SKILL:
        raise ValueError("Result предназначен для другого target_skill.")
    if envelope.get("payload_type") not in {"approved_bounded_findings", "authority_cards"}:
        raise ValueError("Result требует payload_type approved_bounded_findings или authority_cards.")
    for field in ("plan_sha256", "evidence_sha256"):
        _require_sha256(envelope.get(field), field)
    if envelope.get("schema_version") == HANDOFF_VERSION:
        _require_sha256(envelope.get("fingerprint_sha256"), "fingerprint_sha256")
        exact_fields = {
            "schema_version", "handoff_id", "created_at", "source_skill", "target_skill",
            "run_id", "plan_sha256", "evidence_sha256", "fingerprint_sha256",
            "payload_type", "payload", "limitations",
        }
        if set(envelope) != exact_fields:
            raise ValueError("v2 result envelope содержит неизвестные/пропущенные поля.")


def _proof_file_manifest(selected: Mapping[str, Any]) -> list[dict[str, Any]]:
    virtual = {
        "selected-proofs/position-cards.json": selected["position_cards"],
        "selected-proofs/comparisons.json": selected["comparisons"],
        "selected-proofs/relations.json": selected["relations"],
        "case-adverse-review.json": selected["adverse"],
        "normative-bridge.json": selected["bridge"],
        "human-decision.json": selected["human_decision"],
        "validation-report.json": selected["validation_report"],
    }
    return sorted(
        [
            {
                "path": path,
                "present": True,
                "bytes": len(_canonical_bytes(content)),
                "sha256": _digest(content),
            }
            for path, content in virtual.items()
        ],
        key=lambda item: item["path"],
    )


def _position_id(value: Mapping[str, Any]) -> str | None:
    for key in ("position_card_id", "id"):
        if _nonempty(value.get(key)):
            return str(value[key])
    return None


def _validate_selected_proofs(
    payload: Mapping[str, Any],
    *,
    permitted_claim_ids: set[str],
    plan_sha256: str,
) -> None:
    selected = payload.get("selected_proofs")
    if not isinstance(selected, Mapping):
        raise ValueError("v2 result требует selected_proofs.")
    required_types = {
        "position_cards": list,
        "comparisons": list,
        "relations": list,
        "adverse": Mapping,
        "bridge": Mapping,
        "human_decision": Mapping,
        "validation_report": Mapping,
    }
    if set(selected) != set(required_types):
        raise ValueError("selected_proofs должен содержать ровно canonical proof-поля.")
    for field, expected_type in required_types.items():
        if field not in selected or not isinstance(selected[field], expected_type):
            raise ValueError(f"selected_proofs.{field} имеет неверный тип или отсутствует.")
    for field in ("position_cards", "comparisons", "relations"):
        if not selected[field] or not all(isinstance(item, Mapping) for item in selected[field]):
            raise ValueError(f"selected_proofs.{field} должен быть непустым массивом объектов.")

    selected_set = {
        "position_cards": selected["position_cards"],
        "comparisons": selected["comparisons"],
        "relations": selected["relations"],
    }
    if payload.get("selected_position_set_sha256") != _digest(selected_set):
        raise ValueError("selected_position_set_sha256 не совпадает с selected proofs.")

    expected_files = _proof_file_manifest(selected)
    manifest = payload.get("artifact_manifest")
    if not isinstance(manifest, Mapping):
        raise ValueError("v2 result требует artifact_manifest.")
    files = manifest.get("files")
    if files != expected_files:
        raise ValueError("artifact_manifest.files не соответствует content-bound selected proofs.")
    if manifest.get("manifest_sha256") != _digest(expected_files):
        raise ValueError("artifact_manifest.manifest_sha256 не совпадает.")

    approval = payload.get("approval_binding")
    if not isinstance(approval, Mapping):
        raise ValueError("v2 result требует approval_binding.")
    expected_approval = {
        "human_decision_sha256": _digest(selected["human_decision"]),
        "validation_report_sha256": _digest(selected["validation_report"]),
        "normative_bridge_sha256": _digest(selected["bridge"]),
    }
    for field, expected in expected_approval.items():
        if approval.get(field) != expected:
            raise ValueError(f"approval_binding.{field} не совпадает с selected proof.")
    _require_nonempty(approval.get("reviewer"), "approval_binding.reviewer")
    _require_nonempty(approval.get("approved_at"), "approval_binding.approved_at")
    if selected["validation_report"].get("valid") is not True:
        raise ValueError("selected validation_report не подтверждает valid=true.")
    if (
        selected["validation_report"].get("schema_version") != HANDOFF_VERSION
        or selected["validation_report"].get("gate") != "drafting_ready"
    ):
        raise ValueError("selected validation_report имеет неверные version/gate.")
    if selected["adverse"].get("complete") is not True:
        raise ValueError("selected adverse review не подтверждает complete=true.")
    human_status = (
        selected["human_decision"].get("decision")
        or selected["human_decision"].get("status")
        or selected["human_decision"].get("review_state")
    )
    if human_status not in {"approved", "evidence_reviewed"}:
        raise ValueError("selected human_decision не подтверждает approved review.")
    human_reviewer = _require_nonempty(
        selected["human_decision"].get("reviewer"),
        "selected_proofs.human_decision.reviewer",
    )
    if human_reviewer != approval.get("reviewer"):
        raise ValueError("approval reviewer не совпадает с human_decision reviewer.")

    position_ids = {
        position_id
        for item in selected["position_cards"]
        if (position_id := _position_id(item)) is not None
    }
    rejected_position_ids = [
        _position_id(item)
        for item in selected["position_cards"]
        if item.get("human_review") != "approved" and item.get("review_state") != "approved"
    ]
    if rejected_position_ids:
        raise ValueError(f"position cards не имеют approved review: {rejected_position_ids}")
    supporting = payload.get("supporting_position_card_ids")
    adverse_ids = payload.get("adverse_position_card_ids")
    if not isinstance(supporting, list) or not supporting or not all(_nonempty(item) for item in supporting):
        raise ValueError("v2 result требует supporting_position_card_ids.")
    if not isinstance(adverse_ids, list) or not all(_nonempty(item) for item in adverse_ids):
        raise ValueError("v2 result требует явный adverse_position_card_ids[].")
    unknown_positions = set(str(item) for item in [*supporting, *adverse_ids]) - position_ids
    if unknown_positions:
        raise ValueError(f"Proof set не содержит position cards: {sorted(unknown_positions)}")
    comparison_ids = {
        str(item.get("position_card_id"))
        for item in selected["comparisons"]
        if (item.get("status") == "matched" or item.get("overall") == "matched")
        and (
            item.get("review_state") == "approved"
            or item.get("human_review") == "approved"
            or (
                isinstance(item.get("review_provenance"), Mapping)
                and item["review_provenance"].get("status") == "approved"
            )
        )
    }
    relation_by_position = {
        str(item.get("position_card_id")): item.get("relation")
        for item in selected["relations"]
        if item.get("stale") is not True
        and (
            item.get("human_review") == "approved"
            or item.get("review_state") == "approved"
        )
    }
    for position_id in supporting:
        if position_id not in comparison_ids or relation_by_position.get(position_id) != "supports":
            raise ValueError(f"Supporting position {position_id} не имеет approved matched/supports proof.")
    for position_id in adverse_ids:
        if position_id not in comparison_ids or relation_by_position.get(position_id) != "adverse":
            raise ValueError(f"Adverse position {position_id} не имеет approved matched/adverse proof.")

    maximum = _require_nonempty(payload.get("maximum_permitted_claim"), "maximum_permitted_claim")
    bridge = selected["bridge"]
    if bridge.get("maximum_permitted_claim") != maximum:
        raise ValueError("maximum_permitted_claim не совпадает с normative bridge.")
    if bridge.get("supporting_position_card_ids") != supporting:
        raise ValueError("supporting_position_card_ids не совпадает с normative bridge.")
    if bridge.get("adverse_position_card_ids") != adverse_ids:
        raise ValueError("adverse_position_card_ids не совпадает с normative bridge.")
    findings = payload.get("findings")
    if not isinstance(findings, list) or not findings or not all(isinstance(item, Mapping) for item in findings):
        raise ValueError("v2 result требует непустой findings[].")
    exact_finding_fields = {
        "finding_id",
        "candidate_id",
        "candidate_sha256",
        "candidate",
        "claim_ids",
        "claim_wording",
        "supporting_position_card_ids",
        "adverse_position_card_ids",
        "maximum_permitted_claim",
    }
    covered_claim_ids: set[str] = set()
    seen_finding_ids: set[str] = set()
    decision_candidate_ids = selected["human_decision"].get("candidate_ids")
    if not isinstance(decision_candidate_ids, list) or not all(
        _nonempty(item) for item in decision_candidate_ids
    ):
        raise ValueError("selected human_decision требует candidate_ids[].")
    normative_bridge_sha256 = _digest(bridge)
    for index, finding in enumerate(findings):
        if set(finding) != exact_finding_fields:
            raise ValueError(
                f"findings[{index}] должен содержать ровно canonical artifact-derived поля."
            )
        candidate = finding.get("candidate")
        if not isinstance(candidate, Mapping):
            raise ValueError(f"findings[{index}] не содержит artifact-derived candidate.")
        candidate_id = _require_nonempty(candidate.get("candidate_id"), f"findings[{index}].candidate.candidate_id")
        if finding.get("candidate_id") != candidate_id:
            raise ValueError(f"findings[{index}].candidate_id не совпадает с candidate.")
        if candidate_id not in decision_candidate_ids:
            raise ValueError(f"findings[{index}].candidate_id отсутствует в human_decision.")
        if candidate.get("plan_sha256") != plan_sha256:
            raise ValueError(f"findings[{index}].candidate относится к иному plan_sha256.")
        if candidate.get("human_review") != "approved" or candidate.get("drafting_ready") is not True:
            raise ValueError(f"findings[{index}].candidate не одобрен для drafting.")
        candidate_sha256 = _digest(candidate)
        if finding.get("candidate_sha256") != candidate_sha256:
            raise ValueError(f"findings[{index}].candidate_sha256 не совпадает.")
        finding_claim_ids = finding.get("claim_ids")
        if (
            not isinstance(finding_claim_ids, list)
            or not finding_claim_ids
            or not all(_nonempty(item) for item in finding_claim_ids)
            or finding_claim_ids != sorted(set(finding_claim_ids))
        ):
            raise ValueError(f"findings[{index}].claim_ids требует непустой канонический порядок.")
        unknown_claim_ids = set(finding_claim_ids) - permitted_claim_ids
        if unknown_claim_ids:
            raise ValueError(
                f"findings[{index}] ссылается на неизвестные claim_id: {sorted(unknown_claim_ids)}"
            )
        covered_claim_ids.update(finding_claim_ids)
        expected_finding = {
            "finding_id": _digest(
                {
                    "candidate_sha256": candidate_sha256,
                    "claim_ids": finding_claim_ids,
                    "normative_bridge_sha256": normative_bridge_sha256,
                }
            ),
            "candidate_id": candidate_id,
            "candidate_sha256": candidate_sha256,
            "candidate": dict(candidate),
            "claim_ids": finding_claim_ids,
            "claim_wording": bridge.get("claim_wording"),
            "supporting_position_card_ids": list(bridge.get("supporting_position_card_ids", [])),
            "adverse_position_card_ids": list(bridge.get("adverse_position_card_ids", [])),
            "maximum_permitted_claim": bridge.get("maximum_permitted_claim"),
        }
        if dict(finding) != expected_finding:
            raise ValueError(
                f"findings[{index}] не выведен из candidate и normative bridge; finding_id или поля не совпадают."
            )
        finding_id = str(finding["finding_id"])
        if finding_id in seen_finding_ids:
            raise ValueError(f"Повторный finding_id: {finding_id}.")
        seen_finding_ids.add(finding_id)
    if covered_claim_ids != permitted_claim_ids:
        raise ValueError("findings[] не покрывает точный набор claim_bindings.")
    limitations = payload.get("limitations")
    if not isinstance(limitations, list) or not limitations or not all(_nonempty(item) for item in limitations):
        raise ValueError("v2 result требует непустые payload.limitations[].")


def _validate_v2_result(
    envelope: Mapping[str, Any],
    request: Mapping[str, Any],
    active: Mapping[str, Mapping[str, Any]],
    *,
    claim_id_filter: str | None = None,
) -> list[str]:
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping):
        raise ValueError("v2 result требует payload-объект.")
    exact_payload_fields = {
        "drafting_ready", "maximum_permitted_claim", "findings", "supporting_position_card_ids",
        "adverse_position_card_ids", "request_handoff_id", "request_sha256", "claim_set_sha256",
        "claim_bindings", "approval_binding", "artifact_manifest", "selected_position_set_sha256",
        "selected_proofs", "limitations", "quality_bindings",
    }
    if set(payload) != exact_payload_fields:
        raise ValueError("v2 result payload должен содержать ровно canonical поля.")
    quality_bindings = payload.get("quality_bindings")
    if not isinstance(quality_bindings, list) or not quality_bindings:
        raise ValueError("v2 result требует непустой quality_bindings[].")
    seen_quality_types: set[str] = set()
    for index, binding in enumerate(quality_bindings):
        if not isinstance(binding, Mapping) or set(binding) != {
            "quality_type", "artifact_sha256", "artifact",
        }:
            raise ValueError(
                f"quality_bindings[{index}] должен содержать ровно quality_type, artifact_sha256 и artifact."
            )
        quality_type = _require_nonempty(
            binding.get("quality_type"), f"quality_bindings[{index}].quality_type"
        )
        if quality_type not in ALLOWED_QUALITY_TYPES:
            raise ValueError(f"quality_bindings[{index}].quality_type не поддерживается.")
        if quality_type in seen_quality_types:
            raise ValueError(f"Повторный quality binding типа {quality_type}.")
        seen_quality_types.add(quality_type)
        artifact = binding.get("artifact")
        if not isinstance(artifact, Mapping):
            raise ValueError(f"quality_bindings[{index}].artifact должен быть объектом.")
        if binding.get("artifact_sha256") != _digest(artifact):
            raise ValueError(
                f"quality_bindings[{index}].artifact_sha256 не соответствует artifact."
            )
    if missing_quality := sorted(REQUIRED_QUALITY_TYPES - seen_quality_types):
        raise ValueError(
            "quality_bindings не содержит обязательные типы: " + ", ".join(missing_quality) + "."
        )
    request_payload = request.get("payload")
    if not isinstance(request_payload, Mapping):
        raise ValueError("Связанный request не содержит payload.")
    if payload.get("request_handoff_id") != request.get("handoff_id"):
        raise ValueError("request_handoff_id result не совпадает со связанным request.")
    if payload.get("request_sha256") != request_payload.get("request_sha256"):
        raise ValueError("request_sha256 result не совпадает со связанным request.")
    if payload.get("claim_set_sha256") != request_payload.get("claim_set_sha256"):
        raise ValueError("claim_set_sha256 result не совпадает со связанным request.")
    result_bindings = payload.get("claim_bindings")
    request_bindings = request_payload.get("claim_bindings")
    if not isinstance(result_bindings, list) or not all(isinstance(item, Mapping) for item in result_bindings):
        raise ValueError("v2 result требует claim_bindings[].")
    if _sorted_claim_bindings(result_bindings) != _sorted_claim_bindings(request_bindings or []):
        request_by_id = {
            str(item.get("claim_id")): item
            for item in (request_bindings or [])
            if isinstance(item, Mapping)
        }
        for item in result_bindings:
            claim_id = str(item.get("claim_id"))
            expected = request_by_id.get(claim_id, {})
            if item.get("claim_sha256") != expected.get("claim_sha256"):
                raise ValueError(f"claim_sha256 result не совпадает для claim {claim_id}.")
        raise ValueError("claim_bindings result не совпадает со связанным request.")
    claim_ids: list[str] = []
    active_by_public_id = {
        _public_claim_id(str(private_id)): (str(private_id), claim)
        for private_id, claim in active.items()
    }
    for binding in result_bindings:
        public_claim_id = _require_nonempty(binding.get("claim_id"), "claim_bindings.claim_id")
        if claim_id_filter is not None and public_claim_id != _public_claim_id(claim_id_filter):
            claim_ids.append(public_claim_id)
            continue
        resolved = active_by_public_id.get(public_claim_id)
        if resolved is None:
            raise ValueError(f"Claim {public_claim_id} больше не активен.")
        claim_id, claim = resolved
        if binding.get("claim_sha256") != claim.get("claim_sha256"):
            raise ValueError(f"claim_sha256 result устарел для claim {claim_id}.")
        if binding.get("source_locator") != _public_source_locator(
            str(claim.get("source", {}).get("locator"))
        ):
            raise ValueError(f"source_locator result устарел для claim {claim_id}.")
        claim_ids.append(public_claim_id)
    _validate_selected_proofs(
        payload,
        permitted_claim_ids=set(claim_ids),
        plan_sha256=str(envelope.get("plan_sha256")),
    )
    return claim_ids


def _latest_attachment_for_request(
    workspace: str | Path,
    request_id: str,
) -> dict[str, Any] | None:
    path = _analysis_root(workspace) / ATTACHMENTS_FILE
    errors = _ledger_integrity_errors(path)
    if errors:
        raise ValueError("Attachment ledger повреждён: " + "; ".join(errors))
    return _latest_event(read_jsonl(path), request_id=request_id)


def _anchor_check(
    *,
    result_path: Path,
    source_workspace: Path,
    sibling_cli: Path,
    expected_handoff_id: str,
) -> dict[str, Any]:
    if not source_workspace.is_dir():
        return {
            "valid": False,
            "status": "source_workspace_missing",
            "handoff_id": expected_handoff_id,
            "audit_readable": True,
        }
    if not sibling_cli.is_file():
        return {
            "valid": False,
            "status": "sibling_cli_missing",
            "handoff_id": expected_handoff_id,
            "audit_readable": True,
        }
    command = [
        sys.executable,
        str(sibling_cli),
        "handoff",
        "check",
        "--input",
        str(result_path),
        "--source-workspace",
        str(source_workspace),
        "--expected-target",
        SOURCE_SKILL,
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "valid": False,
            "status": "anchor_check_failed",
            "handoff_id": expected_handoff_id,
            "audit_readable": True,
            "error": str(exc),
        }
    try:
        checked = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        checked = {}
    valid = (
        completed.returncode == 0
        and isinstance(checked, Mapping)
        and checked.get("valid") is True
        and checked.get("status") == "valid"
        and checked.get("handoff_id") == expected_handoff_id
    )
    return {
        "valid": valid,
        "status": "valid" if valid else str(checked.get("status") or "anchor_check_rejected"),
        "handoff_id": checked.get("handoff_id") if isinstance(checked, Mapping) else None,
        "audit_readable": bool(checked.get("audit_readable")) if isinstance(checked, Mapping) else False,
        "returncode": completed.returncode,
        "error": None if valid else _normalize_text(completed.stderr or completed.stdout)[:2000],
    }


def _trust_anchor_material(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "anchor_status": event.get("anchor_status"),
        "anchor_handoff_id": event.get("anchor_handoff_id"),
        "anchor_checked_at": event.get("anchor_checked_at"),
        "trusted_source_workspace": event.get("trusted_source_workspace"),
        "sibling_cli": event.get("sibling_cli"),
        "sibling_cli_sha256": event.get("sibling_cli_sha256"),
        "attachment_event_sha256": event.get("attachment_event_sha256"),
    }


@_workspace_operation("mutation")
def import_result(
    workspace: str | Path,
    input_path: str | Path,
    *,
    request_id: str,
    trusted_source_workspace: str | Path | None = None,
    skills_root: str | Path | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Validate first; only then atomically persist a result and import event."""

    _, request = _request_by_id(workspace, request_id)
    source = Path(input_path).expanduser().resolve()
    timestamp = now or _now()
    envelope = _read_json(source)
    if not isinstance(envelope, dict):
        raise ValueError("Result envelope должен быть JSON-объектом.")
    _validate_envelope_identity(envelope)
    schema_version = envelope.get("schema_version")
    if schema_version not in {"1.0", HANDOFF_VERSION}:
        raise ValueError(f"Несовместимая версия result envelope: {schema_version}")

    active = _active_claims(workspace)
    anchor: dict[str, Any] | None = None
    attachment: dict[str, Any] | None = None
    if schema_version == HANDOFF_VERSION:
        claim_ids = _validate_v2_result(envelope, request, active)
        attachment = _latest_attachment_for_request(workspace, request_id)
        if attachment is not None and attachment.get("status") == "attached":
            attached_ok = True
            attached_workspace = (
                Path(str(attachment.get("cassation_workspace"))).expanduser().resolve()
                if _nonempty(attachment.get("cassation_workspace"))
                else None
            )
        else:
            attached_ok = False
            attached_workspace = None
        requested_workspace = (
            Path(trusted_source_workspace).expanduser().resolve()
            if trusted_source_workspace is not None
            else attached_workspace
        )
        if attached_workspace is not None and requested_workspace != attached_workspace:
            raise ValueError("trusted_source_workspace не совпадает с attached cassation workspace.")
        if skills_root is not None:
            sibling_cli = (
                Path(skills_root).expanduser().resolve()
                / TARGET_SKILL
                / "scripts"
                / "judicial_meaning.py"
            )
        elif attachment is not None and attached_ok and _nonempty(attachment.get("sibling_cli")):
            sibling_cli = Path(str(attachment["sibling_cli"])).expanduser().resolve()
        else:
            sibling_cli = Path(__file__).resolve().parents[2] / TARGET_SKILL / "scripts" / "judicial_meaning.py"
        if not attached_ok or requested_workspace is None:
            anchor = {
                "valid": False,
                "status": "audit_only_unanchored",
                "handoff_id": envelope["handoff_id"],
                "audit_readable": True,
            }
        else:
            anchor = _anchor_check(
                result_path=source,
                source_workspace=requested_workspace,
                sibling_cli=sibling_cli,
                expected_handoff_id=str(envelope["handoff_id"]),
            )
        eligible = anchor.get("valid") is True and anchor.get("status") == "valid"
        status = "imported" if eligible else "audit_only_unanchored"
    else:
        payload = envelope.get("payload")
        linked_request = payload.get("request_handoff_id") if isinstance(payload, Mapping) else None
        if linked_request not in {None, request_id}:
            raise ValueError("Legacy result ссылается на другой request_handoff_id.")
        request_bindings = request.get("payload", {}).get("claim_bindings", [])
        claim_ids = [
            str(item.get("claim_id"))
            for item in request_bindings
            if isinstance(item, Mapping) and _nonempty(item.get("claim_id"))
        ]
        status = "legacy_audit_only"
        eligible = False

    event: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "result_import",
        "request_id": request_id,
        "handoff_id": envelope["handoff_id"],
        "result_schema_version": schema_version,
        "status": status,
        "eligible_for_drafting": eligible,
        "claim_ids": claim_ids,
        "imported_at": timestamp,
        "source_path": str(source),
        "source_sha256": _file_sha256(source),
    }
    if anchor is not None:
        event.update(
            {
                "anchor_status": anchor.get("status"),
                "anchor_handoff_id": anchor.get("handoff_id"),
                "anchor_checked_at": timestamp,
                "trusted_source_workspace": (
                    str(Path(str(attachment["cassation_workspace"])).expanduser().resolve())
                    if attachment and _nonempty(attachment.get("cassation_workspace"))
                    else None
                ),
                "sibling_cli": (
                    str(Path(str(attachment["sibling_cli"])).expanduser().resolve())
                    if attachment and _nonempty(attachment.get("sibling_cli"))
                    else None
                ),
                "sibling_cli_sha256": attachment.get("sibling_cli_sha256") if attachment else None,
                "attachment_event_sha256": attachment.get("event_sha256") if attachment else None,
            }
        )
        event["trust_anchor_sha256"] = _digest(_trust_anchor_material(event))
    destination = _analysis_root(workspace) / "results" / f"{envelope['handoff_id']}.json"
    imports_path = _analysis_root(workspace) / RESULT_IMPORTS_FILE
    with _interprocess_lock(imports_path.with_name("result-import.transaction")):
        if destination.exists():
            existing = _read_json(destination)
            if existing != envelope:
                raise ValueError("Существующий handoff_id связан с иным содержимым result store.")
            existing_event = _latest_event(read_jsonl(imports_path), handoff_id=envelope["handoff_id"])
            if existing_event:
                return {
                    **existing_event,
                    "status": "idempotent_noop",
                    "imported": False,
                    "eligible_for_drafting": existing_event.get("eligible_for_drafting") is True,
                }
        else:
            _atomic_write_json(destination, envelope)
        try:
            event = _append_event(imports_path, event)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    return {**event, "imported": True}


@_workspace_operation("mutation")
def review_wording(
    workspace: str | Path,
    *,
    claim_id: str,
    handoff_id: str,
    decision: str,
    reviewer: str,
    reason: str,
    finding_ids: Sequence[str],
    wording_text: str,
    wording_source: str | Path,
    now: str | None = None,
) -> dict[str, Any]:
    active = _active_claims(workspace)
    claim = active.get(claim_id)
    if claim is None:
        raise ValueError(f"Не найден активный claim_id {claim_id}.")
    decision = decision.replace("-", "_")
    if decision not in {"within_limit", "too_strong", "unclear"}:
        raise ValueError("decision должен быть within_limit, too_strong или unclear.")
    reviewer = _require_nonempty(reviewer, "reviewer")
    reason = _require_nonempty(reason, "причина wording review")
    if not finding_ids or not all(_nonempty(item) for item in finding_ids):
        raise ValueError("Wording review требует хотя бы один finding_id.")
    wording_text = _normalize_text(_require_nonempty(wording_text, "wording_text"))
    if wording_text != claim.get("claim_text"):
        raise ValueError("wording_text не совпадает с текущей ревизией claim; сначала выполните scan.")
    wording_path = Path(wording_source).expanduser().resolve()
    if not wording_path.is_file():
        raise ValueError(f"Не найден wording source: {wording_path}")
    _, source_claims = _input_claims(wording_path)
    if wording_text not in {_normalize_text(str(item["text"])) for item in source_claims}:
        raise ValueError("wording_text не найден как самостоятельный фрагмент wording source.")
    result_path = _analysis_root(workspace) / "results" / f"{handoff_id}.json"
    result = _read_json(result_path)
    if not isinstance(result, Mapping) or result.get("schema_version") != HANDOFF_VERSION:
        raise ValueError("Wording review допускается только для проверенного v2 result.")
    import_event = _latest_event(
        read_jsonl(_analysis_root(workspace) / RESULT_IMPORTS_FILE),
        handoff_id=handoff_id,
    )
    if not import_event or import_event.get("eligible_for_drafting") is not True:
        raise ValueError("Result не импортирован как v2 drafting-eligible proof.")
    payload = result.get("payload", {})
    bindings = payload.get("claim_bindings", []) if isinstance(payload, Mapping) else []
    binding = next(
        (
            item
            for item in bindings
            if isinstance(item, Mapping) and item.get("claim_id") == claim_id
        ),
        None,
    )
    if not isinstance(binding, Mapping) or binding.get("claim_sha256") != claim.get("claim_sha256"):
        raise ValueError("Result не связан с текущей ревизией claim.")
    known_findings = {
        str(item.get("finding_id"))
        for item in payload.get("findings", [])
        if isinstance(item, Mapping) and _nonempty(item.get("finding_id"))
    }
    unknown = set(str(item) for item in finding_ids) - known_findings
    if unknown:
        raise ValueError(f"Неизвестные finding_id для result: {sorted(unknown)}")
    public_claim_id = _public_claim_id(claim_id)
    applicable_findings = {
        str(item.get("finding_id"))
        for item in payload.get("findings", [])
        if isinstance(item, Mapping)
        and public_claim_id in item.get("claim_ids", [])
        and _nonempty(item.get("finding_id"))
    }
    wrong_claim = set(str(item) for item in finding_ids) - applicable_findings
    if wrong_claim:
        raise ValueError(f"finding_id не относится к текущему claim: {sorted(wrong_claim)}")
    approval = payload.get("approval_binding", {})
    record = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "wording_review",
        "claim_id": claim_id,
        "revision_id": claim["revision_id"],
        "claim_sha256": claim["claim_sha256"],
        "handoff_id": handoff_id,
        "request_id": import_event["request_id"],
        "finding_ids": list(finding_ids),
        "maximum_permitted_claim": payload.get("maximum_permitted_claim"),
        "plan_sha256": result.get("plan_sha256"),
        "evidence_sha256": result.get("evidence_sha256"),
        "fingerprint_sha256": result.get("fingerprint_sha256"),
        "human_decision_sha256": approval.get("human_decision_sha256"),
        "validation_report_sha256": approval.get("validation_report_sha256"),
        "normative_bridge_sha256": approval.get("normative_bridge_sha256"),
        "decision": decision,
        "reviewer": reviewer,
        "reason": reason,
        "wording_text": wording_text,
        "wording_sha256": _digest(wording_text),
        "wording_source_path": str(wording_path),
        "wording_source_sha256": _file_sha256(wording_path),
        "reviewed_at": now or _now(),
    }
    record = _append_event(_analysis_root(workspace) / WORDING_REVIEWS_FILE, record)
    return record


def _request_files(workspace: str | Path) -> list[dict[str, Any]]:
    directory = _analysis_root(workspace) / "requests"
    if not directory.exists():
        return []
    requests: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        value = _read_json(path)
        if isinstance(value, dict):
            requests.append(value)
    return requests


def _current_dependency_status(
    claim: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    bindings = claim.get("bindings", {})
    if not isinstance(bindings, Mapping):
        return True, ["claim_bindings_missing"]
    reasons: list[str] = []
    dependency_ids = bindings.get("case_dependency_ids", [])
    try:
        current_case_sha = _case_projection(dependency_ids, manifest)
    except ValueError:
        current_case_sha = None
    if current_case_sha != bindings.get("case_dependency_sha256"):
        reasons.append("case_dependency_changed")
    current_hypothesis_sha = _hypothesis_projection(claim.get("hypothesis_ids", []), manifest)
    if current_hypothesis_sha != bindings.get("hypothesis_sha256"):
        reasons.append("hypothesis_dependency_changed")
    return bool(reasons), reasons


def _current_source_status(claim: Mapping[str, Any]) -> tuple[bool, list[str]]:
    source = claim.get("source")
    if not isinstance(source, Mapping):
        return True, ["source_file_binding_missing", "rescan_required"]
    stored_sha = source.get("source_file_sha256")
    if not _is_sha256(stored_sha):
        return True, ["source_file_binding_missing", "rescan_required"]
    source_path = source.get("path")
    if not _nonempty(source_path):
        return True, ["source_file_binding_missing", "rescan_required"]
    try:
        current_path = Path(str(source_path)).expanduser().resolve()
    except (OSError, RuntimeError):
        return True, ["source_file_missing", "rescan_required"]
    if not current_path.is_file():
        return True, ["source_file_missing", "rescan_required"]
    try:
        current_sha = _file_sha256(current_path)
    except OSError:
        return True, ["source_file_unreadable", "rescan_required"]
    if current_sha != stored_sha:
        return True, ["source_file_changed", "rescan_required"]
    return False, []


def _request_binding(request: Mapping[str, Any], claim_id: str) -> Mapping[str, Any] | None:
    payload = request.get("payload", {})
    bindings = payload.get("claim_bindings", []) if isinstance(payload, Mapping) else []
    return next(
        (
            item
            for item in bindings
            if isinstance(item, Mapping) and item.get("claim_id") == _public_claim_id(claim_id)
        ),
        None,
    )


def _result_path(workspace: str | Path, handoff_id: str) -> Path:
    _require_sha256(handoff_id, "handoff_id")
    return _analysis_root(workspace) / "results" / f"{handoff_id}.json"


def _next_actions(state: str, reasons: Sequence[str]) -> list[str]:
    if state == "not_required":
        return []
    if state == "required":
        return ["Создайте нейтральный corpus request командой request create."]
    if state == "running":
        return ["Завершите кассационный workbench и импортируйте проверенный v2 result."]
    if state == "stale":
        return ["Пересоберите request для текущей ревизии claim и повторите зависимые review."]
    if state == "ready":
        return []
    if "wording_review_required" in reasons:
        return ["Проверьте финальную формулировку командой wording review."]
    if "sibling_skill_unavailable" in reasons:
        return ["Установите полный KSRF skillset или укажите корректный --skills-root."]
    return ["Устраните указанный proof/coverage blocker и импортируйте новый v2 result."]


def _ready_binding(claim_state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": claim_state["claim_id"],
        "revision_id": claim_state.get("revision_id"),
        "claim_sha256": claim_state["claim_sha256"],
        "source_file_sha256": claim_state.get("source_file_sha256"),
        "input_bindings_sha256": claim_state.get("input_bindings_sha256"),
        "input_manifest_updated_at": claim_state.get("input_manifest_updated_at"),
        "claim_created_at": claim_state.get("claim_created_at"),
        "handoff_id": claim_state.get("handoff_id"),
        "plan_sha256": claim_state.get("plan_sha256"),
        "evidence_sha256": claim_state.get("evidence_sha256"),
        "fingerprint_sha256": claim_state.get("fingerprint_sha256"),
        "maximum_permitted_claim": claim_state.get("maximum_permitted_claim"),
        "wording_review_event_sha256": claim_state.get("wording_review_event_sha256"),
        "wording_reviewed_at": claim_state.get("wording_reviewed_at"),
        "result_import_event_sha256": claim_state.get("result_import_event_sha256"),
        "result_imported_at": claim_state.get("result_imported_at"),
        "result_source_sha256": claim_state.get("result_source_sha256"),
        "result_created_at": claim_state.get("result_created_at"),
        "attachment_event_sha256": claim_state.get("attachment_event_sha256"),
        "attachment_attached_at": claim_state.get("attachment_attached_at"),
        "anchor_checked_at": claim_state.get("anchor_checked_at"),
        "trust_anchor_sha256": claim_state.get("trust_anchor_sha256"),
    }


def _latest_refresh(workspace: str | Path) -> dict[str, Any] | None:
    records = read_jsonl(_analysis_root(workspace) / REFRESHES_FILE)
    return dict(records[-1]) if records else None


def _parse_material_timestamp(value: Any, field: str) -> datetime:
    if not _nonempty(value):
        raise ValueError(f"{field} отсутствует в exact material binding.")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} содержит некорректный timestamp.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} должен содержать timezone.")
    return parsed.astimezone(timezone.utc)


@_workspace_operation("derived")
def derive_state(
    workspace: str | Path,
    *,
    stage: str = "drafting",
    now: str | None = None,
) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError(f"Неизвестная стадия {stage}; допустимы {', '.join(STAGES)}.")
    config = _load_config(workspace)
    manifest = _load_manifest(workspace)
    ledger_records = read_jsonl(_analysis_root(workspace) / CLAIM_LEDGER_FILE)
    integrity_errors, invalid_claim_ids = _claim_ledger_integrity(ledger_records)
    integrity_errors.extend(
        _ledger_integrity_errors(
            _analysis_root(workspace) / CLAIM_LEDGER_FILE,
            records=ledger_records,
        )
    )
    active = _active_claims(workspace)
    trigger_reviews = read_jsonl(_analysis_root(workspace) / TRIGGER_REVIEWS_FILE)
    attachments = read_jsonl(_analysis_root(workspace) / ATTACHMENTS_FILE)
    result_imports = read_jsonl(_analysis_root(workspace) / RESULT_IMPORTS_FILE)
    wording_reviews = read_jsonl(_analysis_root(workspace) / WORDING_REVIEWS_FILE)
    refreshes = read_jsonl(_analysis_root(workspace) / REFRESHES_FILE)
    event_records = {
        TRIGGER_REVIEWS_FILE: trigger_reviews,
        ATTACHMENTS_FILE: attachments,
        RESULT_IMPORTS_FILE: result_imports,
        WORDING_REVIEWS_FILE: wording_reviews,
        REFRESHES_FILE: refreshes,
    }
    event_errors_by_ledger = {
        name: _ledger_integrity_errors(_analysis_root(workspace) / name, records=records)
        for name, records in event_records.items()
    }
    event_errors = [error for errors in event_errors_by_ledger.values() for error in errors]
    integrity_errors.extend(event_errors)
    invalid_event_claim_ids: set[str] = set()
    for name in (TRIGGER_REVIEWS_FILE, WORDING_REVIEWS_FILE):
        if event_errors_by_ledger[name]:
            invalid_event_claim_ids.update(
                str(record["claim_id"])
                for record in event_records[name]
                if _nonempty(record.get("claim_id"))
            )
    for name in (ATTACHMENTS_FILE, RESULT_IMPORTS_FILE):
        if event_errors_by_ledger[name]:
            affected_requests = {
                str(record["request_id"])
                for record in event_records[name]
                if _nonempty(record.get("request_id"))
            }
            for request in _request_files(workspace):
                if request.get("handoff_id") not in affected_requests:
                    continue
                payload = request.get("payload", {})
                for binding in payload.get("claim_bindings", []) if isinstance(payload, Mapping) else []:
                    if isinstance(binding, Mapping) and _nonempty(binding.get("claim_id")):
                        for private_id in active:
                            if _public_claim_id(private_id) == binding.get("claim_id"):
                                invalid_event_claim_ids.add(private_id)
    requests = _request_files(workspace)

    claims_state: list[dict[str, Any]] = []
    for claim_id, claim in sorted(active.items()):
        review = _latest_event(
            trigger_reviews,
            claim_id=claim_id,
            revision_id=claim.get("revision_id"),
        )
        triggers = claim.get("trigger_evidence", [])
        explicit = claim.get("practice_dependency_explicit")
        required = bool(triggers) or explicit is True
        if review and review.get("decision") == "required":
            required = True
        if review and review.get("decision") == "not_required":
            required = False
        elif not required:
            required = any(
                record.get("claim_id") == claim_id
                and record.get("revision_id") != claim.get("revision_id")
                and (
                    bool(record.get("trigger_evidence"))
                    or record.get("practice_dependency_explicit") is True
                )
                for record in ledger_records
            )

        reasons: list[str] = []
        selected_request: Mapping[str, Any] | None = None
        selected_attachment: Mapping[str, Any] | None = None
        selected_import: Mapping[str, Any] | None = None
        selected_result: Mapping[str, Any] | None = None
        selected_wording: Mapping[str, Any] | None = None
        continue_to_wording = False
        state = "blocked"
        source_stale, source_reasons = _current_source_status(claim)
        if claim_id in invalid_event_claim_ids:
            state = "blocked"
            reasons.append("ledger_integrity_failed")
        elif claim_id in invalid_claim_ids:
            state = "blocked"
            reasons.append("ledger_integrity_failed")
        elif source_stale:
            state = "stale"
            reasons.extend(source_reasons)
        elif not required:
            state = "not_required"
        else:
            dependency_stale, dependency_reasons = _current_dependency_status(claim, manifest)
            historical_requests = [
                request for request in requests if _request_binding(request, claim_id) is not None
            ]
            exact_requests = [
                request
                for request in historical_requests
                if (binding := _request_binding(request, claim_id)) is not None
                and binding.get("claim_sha256") == claim.get("claim_sha256")
                and binding.get("source_locator")
                == _public_source_locator(str(claim.get("source", {}).get("locator")))
            ]
            if dependency_stale:
                state = "stale"
                reasons.extend(dependency_reasons)
            elif not exact_requests:
                state = "stale" if historical_requests else "required"
                if historical_requests:
                    reasons.append("claim_revision_changed")
            else:
                selected_request = exact_requests[-1]
                request_id = str(selected_request.get("handoff_id"))
                selected_attachment = _latest_event(attachments, request_id=request_id)
                matching_imports = [
                    item for item in result_imports if item.get("request_id") == request_id
                ]
                selected_import = matching_imports[-1] if matching_imports else None
                if selected_attachment and selected_attachment.get("status") == "blocked":
                    state = "blocked"
                    reasons.append("sibling_skill_unavailable" if "Не найден установленный" in str(selected_attachment.get("error")) else "run_attach_failed")
                elif selected_import is None:
                    state = "running" if selected_attachment and selected_attachment.get("status") == "attached" else "required"
                elif selected_import.get("eligible_for_drafting") is not True:
                    state = "blocked"
                    reasons.append(
                        "unanchored_result_audit_only"
                        if selected_import.get("status") == "audit_only_unanchored"
                        else "legacy_result_audit_only"
                    )
                elif (
                    selected_attachment is None
                    or selected_import.get("attachment_event_sha256")
                    != selected_attachment.get("event_sha256")
                ):
                    state = "stale"
                    reasons.append("attachment_changed_since_result")
                else:
                    stored_result_path = _result_path(
                        workspace,
                        str(selected_import.get("handoff_id")),
                    )
                    if not stored_result_path.is_file():
                        state = "blocked"
                        reasons.append("result_missing")
                    else:
                        loaded_result = _read_json(stored_result_path)
                        selected_result = loaded_result if isinstance(loaded_result, Mapping) else None
                    try:
                        if selected_result is None:
                            raise ValueError("Stored result должен быть JSON-объектом.")
                        if selected_result.get("handoff_id") != selected_import.get("handoff_id"):
                            raise ValueError("Stored result не совпадает с импортированным handoff_id.")
                        _validate_envelope_identity(selected_result)
                        _validate_v2_result(
                            selected_result,
                            selected_request,
                            active,
                            claim_id_filter=claim_id,
                        )
                    except (AttributeError, ValueError):
                        if "result_missing" not in reasons:
                            state = "blocked"
                            reasons.append("result_integrity_failed")
                    else:
                        if selected_import.get("trust_anchor_sha256") != _digest(
                            _trust_anchor_material(selected_import)
                        ):
                            state = "stale"
                            reasons.append("trust_anchor_binding_changed")
                            continue_to_wording = False
                        trusted_workspace = selected_import.get("trusted_source_workspace")
                        sibling_cli = selected_import.get("sibling_cli")
                        anchor_cli_path = (
                            Path(str(sibling_cli)).expanduser().resolve()
                            if _nonempty(sibling_cli)
                            else None
                        )
                        cli_binding_valid = (
                            anchor_cli_path is not None
                            and anchor_cli_path.is_file()
                            and _file_sha256(anchor_cli_path) == selected_import.get("sibling_cli_sha256")
                        )
                        anchor = (
                            _anchor_check(
                                result_path=stored_result_path,
                                source_workspace=Path(str(trusted_workspace)).expanduser().resolve(),
                                sibling_cli=anchor_cli_path,
                                expected_handoff_id=str(selected_import.get("handoff_id")),
                            )
                            if _nonempty(trusted_workspace) and cli_binding_valid and anchor_cli_path is not None
                            else {"valid": False, "status": "anchor_missing"}
                        )
                        if "trust_anchor_binding_changed" in reasons:
                            continue_to_wording = False
                        elif anchor.get("valid") is not True:
                            state = "stale"
                            reasons.append("trusted_source_changed")
                            continue_to_wording = False
                        else:
                            continue_to_wording = True
                    if selected_result is not None and continue_to_wording:
                        matching_wording = [
                            item
                            for item in wording_reviews
                            if item.get("claim_id") == claim_id
                            and item.get("claim_sha256") == claim.get("claim_sha256")
                            and item.get("handoff_id") == selected_import.get("handoff_id")
                        ]
                        selected_wording = matching_wording[-1] if matching_wording else None
                        if selected_wording is None:
                            state = "blocked"
                            reasons.append("wording_review_required")
                        else:
                            result_payload = selected_result.get("payload", {})
                            approval = (
                                result_payload.get("approval_binding", {})
                                if isinstance(result_payload, Mapping)
                                else {}
                            )
                            review_binding_matches = all(
                                (
                                    selected_wording.get("plan_sha256") == selected_result.get("plan_sha256"),
                                    selected_wording.get("evidence_sha256") == selected_result.get("evidence_sha256"),
                                    selected_wording.get("fingerprint_sha256") == selected_result.get("fingerprint_sha256"),
                                    selected_wording.get("maximum_permitted_claim") == result_payload.get("maximum_permitted_claim"),
                                    selected_wording.get("human_decision_sha256") == approval.get("human_decision_sha256"),
                                    selected_wording.get("validation_report_sha256") == approval.get("validation_report_sha256"),
                                    selected_wording.get("normative_bridge_sha256") == approval.get("normative_bridge_sha256"),
                                )
                            )
                            wording_source_path = selected_wording.get("wording_source_path")
                            wording_source_current = (
                                Path(str(wording_source_path)).expanduser().resolve()
                                if _nonempty(wording_source_path)
                                else None
                            )
                            wording_source_matches = (
                                wording_source_current is not None
                                and wording_source_current.is_file()
                                and _file_sha256(wording_source_current)
                                == selected_wording.get("wording_source_sha256")
                                and selected_wording.get("wording_sha256") == _digest(claim.get("claim_text"))
                            )
                            if not wording_source_matches:
                                state = "stale"
                                reasons.append("wording_source_changed")
                            elif not review_binding_matches:
                                state = "stale"
                                reasons.append("wording_review_binding_changed")
                            elif selected_wording.get("decision") == "within_limit":
                                state = "ready"
                            else:
                                state = "blocked"
                                reasons.append(str(selected_wording.get("decision")))

        claim_state = {
            "claim_id": claim_id,
            "revision_id": claim.get("revision_id"),
            "claim_sha256": claim.get("claim_sha256"),
            "source_locator": claim.get("source", {}).get("locator"),
            "source_file_sha256": claim.get("source", {}).get("source_file_sha256"),
            "input_bindings_sha256": manifest.get("input_bindings_sha256"),
            "input_manifest_updated_at": manifest.get("updated_at"),
            "claim_created_at": claim.get("created_at"),
            "hypothesis_ids": claim.get("hypothesis_ids", []),
            "option_ids": claim.get("option_ids", []),
            "empirical_dimensions": claim.get("empirical_dimensions", []),
            "analysis_route": claim.get("analysis_route"),
            "state": state,
            "draft_blocked": state in {"required", "running", "blocked", "stale"},
            "blocking_reasons": reasons,
            "next_actions": _next_actions(state, reasons),
            "request_id": selected_request.get("handoff_id") if selected_request else None,
            "handoff_id": selected_import.get("handoff_id") if selected_import else None,
            "maximum_permitted_claim": (
                selected_result.get("payload", {}).get("maximum_permitted_claim")
                if isinstance(selected_result, Mapping)
                and isinstance(selected_result.get("payload"), Mapping)
                else None
            ),
            "plan_sha256": selected_result.get("plan_sha256") if isinstance(selected_result, Mapping) else None,
            "evidence_sha256": selected_result.get("evidence_sha256") if isinstance(selected_result, Mapping) else None,
            "fingerprint_sha256": selected_result.get("fingerprint_sha256") if isinstance(selected_result, Mapping) else None,
            "wording_review_event_sha256": selected_wording.get("event_sha256") if selected_wording else None,
            "wording_reviewed_at": selected_wording.get("reviewed_at") if selected_wording else None,
            "result_import_event_sha256": selected_import.get("event_sha256") if selected_import else None,
            "result_imported_at": selected_import.get("imported_at") if selected_import else None,
            "result_source_sha256": selected_import.get("source_sha256") if selected_import else None,
            "result_created_at": selected_result.get("created_at") if isinstance(selected_result, Mapping) else None,
            "attachment_event_sha256": selected_attachment.get("event_sha256") if selected_attachment else None,
            "attachment_attached_at": selected_attachment.get("attached_at") if selected_attachment else None,
            "anchor_checked_at": selected_import.get("anchor_checked_at") if selected_import else None,
            "trust_anchor_sha256": selected_import.get("trust_anchor_sha256") if selected_import else None,
            "wording_review": dict(selected_wording) if selected_wording else None,
        }
        claims_state.append(claim_state)

    blocked_claim_ids = [item["claim_id"] for item in claims_state if item["draft_blocked"]]
    allowed_claim_ids = [item["claim_id"] for item in claims_state if not item["draft_blocked"]]
    unaffected_claim_ids = [item["claim_id"] for item in claims_state if item["state"] == "not_required"]
    ready_bindings = sorted(
        [_ready_binding(item) for item in claims_state if item["state"] == "ready"],
        key=lambda item: item["claim_id"],
    )
    refresh = dict(refreshes[-1]) if refreshes else None
    refresh_required = stage == "filing" and bool(ready_bindings)
    reference_time = datetime.fromisoformat((now or _now()).replace("Z", "+00:00"))
    refresh_date_valid = False
    if refresh is not None and _nonempty(refresh.get("as_of")) and _nonempty(refresh.get("corpus_cutoff")):
        try:
            refresh_as_of = datetime.strptime(str(refresh["as_of"]), "%Y-%m-%d").date()
            refresh_cutoff = datetime.strptime(str(refresh["corpus_cutoff"]), "%Y-%m-%d").date()
            refresh_date_valid = (
                0 <= (reference_time.date() - refresh_as_of).days <= MAX_REFRESH_AGE_DAYS
                and refresh_cutoff <= refresh_as_of
            )
        except ValueError:
            refresh_date_valid = False
    refresh_valid = (
        not refresh_required
        or (
            refresh is not None
            and refresh.get("ready_claim_set_sha256") == _digest(ready_bindings)
            and refresh_date_valid
        )
    )
    if blocked_claim_ids or not refresh_valid or integrity_errors:
        stage_verdict = "partial" if allowed_claim_ids and blocked_claim_ids else "blocked"
    else:
        stage_verdict = "ready"
    counts = Counter(item["state"] for item in claims_state)
    state_payload = {
        "schema_version": SCHEMA_VERSION,
        "case_id": config["case_id"],
        "generated_at": now or _now(),
        "stage": stage,
        "input_bindings": {
            "case_file_sha256": manifest.get("case_file", {}).get("sha256"),
            "argument_research_sha256": (
                manifest.get("argument_research", {}).get("sha256")
                if isinstance(manifest.get("argument_research"), Mapping)
                else None
            ),
            "input_bindings_sha256": manifest.get("input_bindings_sha256"),
        },
        "counts_by_state": {state: counts.get(state, 0) for state in CLAIM_STATES},
        "claims": claims_state,
        "stage_verdict": stage_verdict,
        "blocked_claim_ids": blocked_claim_ids,
        "allowed_claim_ids": allowed_claim_ids,
        "unaffected_claim_ids": unaffected_claim_ids,
        "global_integrity_errors": integrity_errors,
        "prefiling_refresh": {
            "required": refresh_required,
            "valid": refresh_valid,
            "record": refresh,
            "ready_claim_set_sha256": _digest(ready_bindings) if ready_bindings else None,
        },
    }
    _write_claim_index(workspace)
    _atomic_write_json(_analysis_root(workspace) / STATE_FILE, state_payload)
    return state_payload


@_workspace_operation("mutation")
def record_refresh(
    workspace: str | Path,
    *,
    as_of: str,
    reviewer: str,
    official_check_ref: str,
    corpus_cutoff: str | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    reviewer = _require_nonempty(reviewer, "reviewer")
    official_check_ref = _require_nonempty(official_check_ref, "official_check_ref")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of):
        raise ValueError("as_of должен иметь формат YYYY-MM-DD.")
    try:
        as_of_date = datetime.strptime(as_of, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("as_of содержит несуществующую календарную дату.") from exc
    corpus_cutoff = corpus_cutoff or as_of
    try:
        cutoff_date = datetime.strptime(corpus_cutoff, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("corpus_cutoff должен иметь формат YYYY-MM-DD.") from exc
    checked_at = datetime.fromisoformat((now or _now()).replace("Z", "+00:00"))
    if (checked_at.date() - as_of_date).days > MAX_REFRESH_AGE_DAYS or as_of_date > checked_at.date():
        raise ValueError("Prefiling refresh недостаточно свеж или датирован будущим.")
    if cutoff_date > as_of_date:
        raise ValueError("corpus_cutoff не может быть позже as_of.")
    drafting = validate_workspace(workspace, stage="drafting", now=now)
    if not drafting.get("valid"):
        raise ValueError("Prefiling refresh невозможен: сначала устраните drafting blockers.")
    state = drafting["state"]
    latest_ready_review_dates = []
    for item in state["claims"]:
        review = item.get("wording_review")
        if item.get("state") == "ready" and isinstance(review, Mapping) and _nonempty(review.get("reviewed_at")):
            latest_ready_review_dates.append(
                datetime.fromisoformat(str(review["reviewed_at"]).replace("Z", "+00:00")).date()
            )
    if latest_ready_review_dates and as_of_date < max(latest_ready_review_dates):
        raise ValueError("Prefiling refresh предшествует последнему wording/result review.")
    ready_bindings = sorted(
        [_ready_binding(item) for item in state["claims"] if item["state"] == "ready"],
        key=lambda item: item["claim_id"],
    )
    material_timestamp_fields = (
        "claim_created_at",
        "input_manifest_updated_at",
        "wording_reviewed_at",
        "result_imported_at",
        "result_created_at",
        "attachment_attached_at",
        "anchor_checked_at",
    )
    checked_at_utc = checked_at.astimezone(timezone.utc)
    for binding in ready_bindings:
        for field in material_timestamp_fields:
            if _parse_material_timestamp(binding.get(field), field) > checked_at_utc:
                raise ValueError(
                    f"Prefiling refresh предшествует material event {field} "
                    f"для claim {binding.get('claim_id')}."
                )
    record = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "prefiling_refresh",
        "as_of": as_of,
        "corpus_cutoff": corpus_cutoff,
        "reviewer": reviewer,
        "official_check_ref": official_check_ref,
        "ready_claim_bindings": ready_bindings,
        "ready_claim_set_sha256": _digest(ready_bindings),
        "recorded_at": now or _now(),
    }
    record = _append_event(_analysis_root(workspace) / REFRESHES_FILE, record)
    return record


def lint_workspace(workspace: str | Path) -> dict[str, Any]:
    root = _analysis_root(workspace)
    errors: list[str] = []
    for name in (CONFIG_FILE, INPUT_MANIFEST_FILE):
        try:
            value = _read_json(root / name)
            if not isinstance(value, dict):
                errors.append(f"{name} должен содержать объект.")
        except ValueError as exc:
            errors.append(str(exc))
    for name in (
        CLAIM_LEDGER_FILE,
        TRIGGER_REVIEWS_FILE,
        ATTACHMENTS_FILE,
        RESULT_IMPORTS_FILE,
        WORDING_REVIEWS_FILE,
        REFRESHES_FILE,
    ):
        try:
            read_jsonl(root / name)
        except ValueError as exc:
            errors.append(str(exc))
    try:
        claim_records = read_jsonl(root / CLAIM_LEDGER_FILE)
        claim_errors, _ = _claim_ledger_integrity(claim_records)
        errors.extend(claim_errors)
        errors.extend(_ledger_integrity_errors(root / CLAIM_LEDGER_FILE, records=claim_records))
    except ValueError:
        pass
    event_ledgers: dict[str, list[dict[str, Any]]] = {}
    for name in (
        TRIGGER_REVIEWS_FILE,
        ATTACHMENTS_FILE,
        RESULT_IMPORTS_FILE,
        WORDING_REVIEWS_FILE,
        REFRESHES_FILE,
    ):
        try:
            event_ledgers[name] = read_jsonl(root / name)
        except ValueError:
            continue
    for name, records in event_ledgers.items():
        errors.extend(_ledger_integrity_errors(root / name, records=records))
    requests_dir = root / "requests"
    if requests_dir.exists():
        for path in sorted(requests_dir.glob("*.json")):
            try:
                value = _read_json(path)
                if not isinstance(value, dict) or value.get("handoff_id") != _envelope_digest(value):
                    errors.append(f"Request {path.name}: handoff_id не совпадает.")
                elif path.stem != value.get("handoff_id"):
                    errors.append(f"Request {path.name}: имя файла не совпадает с handoff_id.")
                elif value.get("payload") and value["payload"].get("request_sha256") != _digest(_request_core(value["payload"])):
                    errors.append(f"Request {path.name}: request_sha256 не совпадает.")
            except (ValueError, AttributeError) as exc:
                errors.append(str(exc))
    results_dir = root / "results"
    if results_dir.exists():
        for path in sorted(results_dir.glob("*.json")):
            try:
                value = _read_json(path)
                if not isinstance(value, dict) or value.get("handoff_id") != _envelope_digest(value):
                    errors.append(f"Result {path.name}: handoff_id не совпадает.")
                elif path.stem != value.get("handoff_id"):
                    errors.append(f"Result {path.name}: имя файла не совпадает с handoff_id.")
            except ValueError as exc:
                errors.append(str(exc))
    return {
        "schema_version": SCHEMA_VERSION,
        "valid": not errors,
        "errors": errors,
        "workspace": str(Path(workspace).expanduser().resolve()),
    }


def _snapshot_file(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    entry: dict[str, Any] = {"path": str(resolved)}
    try:
        before = resolved.stat()
        if not resolved.is_file():
            return {**entry, "present": False, "kind": "not_file"}
        digest = _file_sha256(resolved)
        after = resolved.stat()
    except OSError as exc:
        return {**entry, "present": False, "error": type(exc).__name__}
    entry.update(
        {
            "present": True,
            "bytes": after.st_size,
            "mtime_ns": after.st_mtime_ns,
            "sha256": digest,
            "stable_read": (
                before.st_size == after.st_size
                and before.st_mtime_ns == after.st_mtime_ns
                and before.st_ino == after.st_ino
            ),
        }
    )
    return entry


def _workspace_snapshot_digest(workspace: str | Path) -> str:
    """Optimistic validation snapshot over all drafting-authoritative material.

    The digest is re-read immediately before publication.  Generated state/report
    files and lock files are excluded because validation itself updates them.
    """

    root = _analysis_root(workspace).resolve()
    excluded_names = {STATE_FILE, VALIDATION_FILE, CLAIM_INDEX_FILE}
    paths: set[Path] = set()
    if root.exists():
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.name in excluded_names or path.name.endswith(".lock") or ".tmp-" in path.name:
                continue
            paths.add(path.resolve())

    claim_records: list[dict[str, Any]] = []
    try:
        claim_records = read_jsonl(root / CLAIM_LEDGER_FILE)
    except ValueError:
        pass
    for claim in claim_records:
        source = claim.get("source")
        if isinstance(source, Mapping) and _nonempty(source.get("path")):
            paths.add(Path(str(source["path"])).expanduser().resolve())

    result_imports: list[dict[str, Any]] = []
    try:
        result_imports = read_jsonl(root / RESULT_IMPORTS_FILE)
    except ValueError:
        pass
    trusted_fixed = (
        "position-cards.jsonl",
        "comparability-matrix.jsonl",
        "applicant-relations.jsonl",
        "case-adverse-review.json",
        "normative-bridge.json",
        "human-decision.json",
        "validation-report.json",
    )
    for event in result_imports:
        if _nonempty(event.get("sibling_cli")):
            paths.add(Path(str(event["sibling_cli"])).expanduser().resolve())
        if not _nonempty(event.get("trusted_source_workspace")):
            continue
        trusted = Path(str(event["trusted_source_workspace"])).expanduser().resolve()
        for name in trusted_fixed:
            paths.add((trusted / name).resolve())
        for directory in (
            trusted / "handoffs" / "trusted-requests",
            trusted / "handoffs" / "trusted-quality",
            trusted / "handoffs" / "trusted-results",
        ):
            if directory.is_dir():
                paths.update(path.resolve() for path in directory.glob("*.json") if path.is_file())

    return _digest([_snapshot_file(path) for path in sorted(paths, key=str)])


@_workspace_operation("validation")
def validate_workspace(
    workspace: str | Path,
    *,
    stage: str,
    now: str | None = None,
) -> dict[str, Any]:
    snapshot_before = _workspace_snapshot_digest(workspace)
    lint = lint_workspace(workspace)
    if not lint["valid"]:
        try:
            degraded_state = derive_state(workspace, stage=stage, now=now)
        except (ValueError, OSError, AttributeError):
            degraded_state = None
        report = {
            "schema_version": SCHEMA_VERSION,
            "valid": False,
            "stage": stage,
            "errors": lint["errors"],
            "blocked_claim_ids": degraded_state.get("blocked_claim_ids", []) if degraded_state else [],
            "allowed_claim_ids": degraded_state.get("allowed_claim_ids", []) if degraded_state else [],
            "unaffected_claim_ids": degraded_state.get("unaffected_claim_ids", []) if degraded_state else [],
            "global_integrity_errors": lint["errors"],
            "state": degraded_state,
            "validated_at": now or _now(),
        }
        if _workspace_snapshot_digest(workspace) != snapshot_before:
            report["errors"] = [*report["errors"], "workspace_changed_during_validation"]
            report["global_integrity_errors"] = [
                *report["global_integrity_errors"],
                "workspace_changed_during_validation",
            ]
        _atomic_write_json(_analysis_root(workspace) / VALIDATION_FILE, report)
        return report
    state = derive_state(workspace, stage=stage, now=now)
    errors = [
        f"blocking_empirical_overclaim:{item['claim_id']}:{item['state']}"
        for item in state["claims"]
        if item["draft_blocked"]
    ]
    if stage == "filing" and state["prefiling_refresh"]["required"] and not state["prefiling_refresh"]["valid"]:
        errors.append("prefiling_refresh_required")
    report = {
        "schema_version": SCHEMA_VERSION,
        "valid": not errors and state["stage_verdict"] == "ready",
        "stage": stage,
        "errors": errors,
        "blocked_claim_ids": state["blocked_claim_ids"],
        "allowed_claim_ids": state["allowed_claim_ids"],
        "unaffected_claim_ids": state["unaffected_claim_ids"],
        "global_integrity_errors": state["global_integrity_errors"],
        "state": state,
        "validated_at": now or _now(),
    }
    if _workspace_snapshot_digest(workspace) != snapshot_before:
        report["valid"] = False
        report["errors"].append("workspace_changed_during_validation")
        report["global_integrity_errors"] = [
            *report["global_integrity_errors"],
            "workspace_changed_during_validation",
        ]
    _atomic_write_json(_analysis_root(workspace) / VALIDATION_FILE, report)
    return report


@_workspace_operation("validation")
def current_filing_claim_projection(
    workspace: str | Path,
    *,
    claim_id: str,
    issue_option_id: str,
    now: str | None = None,
) -> dict[str, Any]:
    """Return a closed current projection for one filing-ready practice claim.

    The caller supplies only the already host-selected workspace, private
    practice claim identifier, and selected issue option. Matter/draft routing
    remains a host-registry responsibility; this function never accepts a
    caller-selected workspace path inside a filing request.
    """

    claim_id = _require_nonempty(claim_id, "claim_id")
    issue_option_id = _require_nonempty(issue_option_id, "issue_option_id")
    snapshot_before_validation = _workspace_snapshot_digest(workspace)
    report = validate_workspace(workspace, stage="filing", now=now)
    snapshot_after_validation = _workspace_snapshot_digest(workspace)
    if snapshot_after_validation != snapshot_before_validation:
        raise ValueError("Practice workspace изменился во время filing validation.")
    state = report.get("state")
    if not isinstance(state, Mapping) or report.get("stage") != "filing":
        raise ValueError("Current practice projection требует filing-stage state.")
    if (
        report.get("global_integrity_errors") != []
        or state.get("global_integrity_errors") != []
    ):
        raise ValueError("Current practice projection заблокирован global integrity errors.")

    claims = state.get("claims")
    if not isinstance(claims, list):
        raise ValueError("Current practice projection не содержит claims[].")
    matches = [
        item
        for item in claims
        if isinstance(item, Mapping) and item.get("claim_id") == claim_id
    ]
    if len(matches) != 1:
        raise ValueError(f"Practice claim {claim_id} отсутствует или неоднозначен.")
    claim_state = dict(matches[0])
    option_ids = claim_state.get("option_ids")
    if (
        not isinstance(option_ids, list)
        or not all(isinstance(item, str) and item for item in option_ids)
        or option_ids.count(issue_option_id) != 1
    ):
        raise ValueError("Practice claim не связан с exact issue_option_id.")
    allowed_claim_ids = state.get("allowed_claim_ids")
    if not isinstance(allowed_claim_ids, list) or not all(
        isinstance(item, str) and item for item in allowed_claim_ids
    ):
        raise ValueError("Current practice projection не содержит valid allowed_claim_ids.")
    if (
        claim_state.get("state") != "ready"
        or claim_state.get("draft_blocked") is not False
        or claim_state.get("blocking_reasons") != []
        or claim_id not in allowed_claim_ids
    ):
        raise ValueError(f"Practice claim {claim_id} не готов к filing.")

    refresh_projection = state.get("prefiling_refresh")
    if not isinstance(refresh_projection, Mapping):
        raise ValueError("Current practice projection не содержит prefiling_refresh.")
    if (
        refresh_projection.get("required") is not True
        or refresh_projection.get("valid") is not True
    ):
        raise ValueError("Practice claim требует действующий prefiling refresh.")
    refresh = refresh_projection.get("record")
    if not isinstance(refresh, Mapping):
        raise ValueError("Prefiling refresh record отсутствует.")
    ready_bindings = refresh.get("ready_claim_bindings")
    if not isinstance(ready_bindings, list):
        raise ValueError("Prefiling refresh не содержит ready_claim_bindings[].")
    target_ready = [
        item
        for item in ready_bindings
        if isinstance(item, Mapping) and item.get("claim_id") == claim_id
    ]
    if len(target_ready) != 1:
        raise ValueError("Prefiling refresh не связывает exact practice claim.")
    expected_ready = _ready_binding(claim_state)
    if dict(target_ready[0]) != expected_ready:
        raise ValueError("Prefiling refresh ready binding устарел.")
    if refresh.get("ready_claim_set_sha256") != _digest(
        sorted(
            [dict(item) for item in ready_bindings if isinstance(item, Mapping)],
            key=lambda item: str(item.get("claim_id")),
        )
    ):
        raise ValueError("Prefiling refresh ready-claim set fingerprint не совпадает.")

    wording = claim_state.get("wording_review")
    if not isinstance(wording, Mapping) or wording.get("decision") != "within_limit":
        raise ValueError("Practice claim не имеет текущего within-limit wording review.")
    finding_ids = wording.get("finding_ids")
    if (
        not isinstance(finding_ids, list)
        or not finding_ids
        or not all(isinstance(item, str) and item for item in finding_ids)
        or finding_ids != sorted(set(finding_ids))
    ):
        raise ValueError("Wording review finding_ids должны быть canonical unique list.")

    handoff_id = claim_state.get("handoff_id")
    if not _nonempty(handoff_id):
        raise ValueError("Practice claim не связан с current result handoff.")
    request_id = claim_state.get("request_id")
    if not _nonempty(request_id):
        raise ValueError("Practice claim не связан с current research request.")
    _, research_request = _request_by_id(workspace, str(request_id))
    result_path = _result_path(workspace, str(handoff_id))
    if not result_path.is_file():
        raise ValueError("Current practice result отсутствует.")
    result = _read_json(result_path)
    if not isinstance(result, Mapping):
        raise ValueError("Current practice result должен быть JSON-объектом.")
    payload = result.get("payload")
    if not isinstance(payload, Mapping):
        raise ValueError("Current practice result не содержит payload.")
    all_findings = payload.get("findings")
    if not isinstance(all_findings, list):
        raise ValueError("Current practice result не содержит findings[].")
    requested = set(finding_ids)
    selected_findings = [
        dict(item)
        for item in all_findings
        if isinstance(item, Mapping) and item.get("finding_id") in requested
    ]
    if (
        len(selected_findings) != len(requested)
        or {str(item.get("finding_id")) for item in selected_findings} != requested
    ):
        raise ValueError("Current practice result не содержит exact finding set.")
    public_claim_id = _public_claim_id(claim_id)
    maximum = claim_state.get("maximum_permitted_claim")
    wording_text = _normalize_text(
        _require_nonempty(wording.get("wording_text"), "wording_text")
    )
    if (
        wording.get("claim_id") != claim_id
        or wording.get("claim_sha256") != claim_state.get("claim_sha256")
        or wording.get("handoff_id") != handoff_id
        or wording.get("wording_text") != wording_text
        or wording.get("maximum_permitted_claim") != maximum
        or payload.get("maximum_permitted_claim") != maximum
    ):
        raise ValueError("Current wording/result binding не совпадает с ready claim.")
    for finding in selected_findings:
        claim_ids = finding.get("claim_ids")
        candidate = finding.get("candidate")
        if (
            not isinstance(claim_ids, list)
            or not all(isinstance(item, str) and item for item in claim_ids)
            or public_claim_id not in claim_ids
            or finding.get("maximum_permitted_claim") != maximum
            or finding.get("claim_wording") != wording_text
            or not isinstance(candidate, Mapping)
            or candidate.get("claim_wording") != wording_text
        ):
            raise ValueError(
                "Finding не относится к exact practice claim, wording или ceiling."
            )

    projection = {
        "schema_version": SCHEMA_VERSION,
        "case_id": state.get("case_id"),
        "issue_option_id": issue_option_id,
        "workspace_binding": {
            "input_bindings": dict(state.get("input_bindings", {})),
            "workspace_snapshot_sha256": snapshot_after_validation,
        },
        "claim_state": claim_state,
        "ready_binding": expected_ready,
        "research_request": dict(research_request),
        "result": dict(result),
        "wording_review": dict(wording),
        "findings": sorted(selected_findings, key=lambda item: str(item["finding_id"])),
        "filing_validation": dict(report),
        "prefiling_refresh": dict(refresh_projection),
    }
    if _workspace_snapshot_digest(workspace) != snapshot_after_validation:
        raise ValueError("Practice workspace изменился во время current projection.")
    return projection


def _print_json(value: Any, *, stream: Any = None) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), file=stream or sys.stdout)


class _RussianArgumentParser(argparse.ArgumentParser):
    """Показывать русскую справку, не меняя usage и ошибки выполнения."""

    _HELP_METAVARS = {
        "command": "КОМАНДА",
        "claim_command": "КОМАНДА",
        "request_command": "КОМАНДА",
        "run_command": "КОМАНДА",
        "result_command": "КОМАНДА",
        "wording_command": "КОМАНДА",
        "refresh_command": "КОМАНДА",
        "workspace": "ПАПКА",
        "case_id": "ИДЕНТИФИКАТОР",
        "case_file": "ФАЙЛ",
        "argument_research": "ФАЙЛ",
        "input": "ФАЙЛ",
        "claim_id": "ИДЕНТИФИКАТОР",
        "reviewer": "ПРОВЕРЯЮЩИЙ",
        "reason": "ОБОСНОВАНИЕ",
        "output": "ФАЙЛ",
        "request_id": "ИДЕНТИФИКАТОР",
        "cassation_workspace": "ПАПКА",
        "skills_root": "ПАПКА",
        "trusted_source_workspace": "ПАПКА",
        "handoff_id": "ИДЕНТИФИКАТОР",
        "finding_id": "ИДЕНТИФИКАТОР",
        "wording_text": "ТЕКСТ",
        "wording_source": "ФАЙЛ_ИСТОЧНИКА",
        "as_of": "ДАТА_ГГГГ-ММ-ДД",
        "official_check_ref": "ССЫЛКА",
        "corpus_cutoff": "ДАТА",
        "stage": "ЭТАП",
    }

    def format_help(self) -> str:
        positional_heading = (
            "команды:"
            if any(
                isinstance(action, argparse._SubParsersAction)
                for action in self._actions
            )
            else "позиционные аргументы:"
        )
        localized = [
            (action, action.metavar)
            for action in self._actions
            if action.dest in self._HELP_METAVARS
        ]
        for action, _metavar in localized:
            action.metavar = self._HELP_METAVARS[action.dest]
        try:
            rendered = super().format_help()
        finally:
            for action, metavar in localized:
                action.metavar = metavar
        return (
            rendered
            .replace("usage:", "Использование:", 1)
            .replace("positional arguments:", positional_heading, 1)
            .replace("optional arguments:", "параметры:", 1)
            .replace("options:", "параметры:", 1)
            .replace(
                "show this help message and exit",
                "показать эту справку и выйти",
            )
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = _RussianArgumentParser(
        description=(
            "Проверить необходимость анализа правоприменительной практики "
            "по каждому утверждению жалобы в КС РФ."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init_description = (
        "Связать рабочую папку дела с исходным файлом дела формата CaseFile."
    )
    init = sub.add_parser(
        "init",
        help=init_description,
        description=init_description,
    )
    init.add_argument("--workspace", required=True)
    init.add_argument("--case-id", required=True)
    init.add_argument("--case-file", required=True)
    init.add_argument("--argument-research")

    scan_description = "Найти утверждения, требующие проверки судебной практикой."
    scan = sub.add_parser(
        "scan",
        help=scan_description,
        description=scan_description,
    )
    scan.add_argument("--workspace", required=True)
    scan.add_argument("--input", required=True)

    claim_description = "Проверить вручную, требуется ли анализ судебной практики."
    claim = sub.add_parser(
        "claim",
        help=claim_description,
        description=claim_description,
    )
    claim_sub = claim.add_subparsers(dest="claim_command", required=True)
    claim_review_description = (
        "Записать ручное решение о необходимости анализа судебной практики."
    )
    claim_review = claim_sub.add_parser(
        "review",
        help=claim_review_description,
        description=claim_review_description,
    )
    claim_review.add_argument("--workspace", required=True)
    claim_review.add_argument("--claim-id", required=True)
    claim_review.add_argument(
        "--decision",
        choices=("required", "not-required", "not_required"),
        required=True,
        help=(
            "Решение проверяющего: required — анализ практики нужен; "
            "not-required или not_required — анализ не нужен."
        ),
    )
    claim_review.add_argument("--reviewer", required=True)
    claim_review.add_argument("--reason", required=True)

    request_description = "Подготовить нейтральный запрос для исследования практики."
    request = sub.add_parser(
        "request",
        help=request_description,
        description=request_description,
    )
    request_sub = request.add_subparsers(dest="request_command", required=True)
    request_create_description = (
        "Создать нейтральный запрос для выбранных утверждений."
    )
    request_create = request_sub.add_parser(
        "create",
        help=request_create_description,
        description=request_create_description,
    )
    request_create.add_argument("--workspace", required=True)
    request_create.add_argument("--claim-id", action="append")
    request_create.add_argument("--output")

    run_description = (
        "Связать запрос с рабочей папкой исследования кассационной практики."
    )
    run = sub.add_parser(
        "run",
        help=run_description,
        description=run_description,
    )
    run_sub = run.add_subparsers(dest="run_command", required=True)
    run_attach_description = (
        "Связать запрос с результатами исследования кассационной практики."
    )
    run_attach = run_sub.add_parser(
        "attach",
        help=run_attach_description,
        description=run_attach_description,
    )
    run_attach.add_argument("--workspace", required=True)
    run_attach.add_argument("--request-id", required=True)
    run_attach.add_argument("--cassation-workspace", required=True)
    run_attach.add_argument("--skills-root")

    result_description = "Импортировать проверенный результат исследования."
    result = sub.add_parser(
        "result",
        help=result_description,
        description=result_description,
    )
    result_sub = result.add_subparsers(dest="result_command", required=True)
    result_import_description = (
        "Импортировать проверенный результат и проверить его привязки."
    )
    result_import = result_sub.add_parser(
        "import",
        help=result_import_description,
        description=result_import_description,
    )
    result_import.add_argument("--workspace", required=True)
    result_import.add_argument("--input", required=True)
    result_import.add_argument("--request-id", required=True)
    result_import.add_argument("--trusted-source-workspace")
    result_import.add_argument("--skills-root")

    wording_description = "Проверить обоснованность итоговой формулировки."
    wording = sub.add_parser(
        "wording",
        help=wording_description,
        description=wording_description,
    )
    wording_sub = wording.add_subparsers(dest="wording_command", required=True)
    wording_review_description = (
        "Проверить, не выходит ли итоговая формулировка за пределы доказанного."
    )
    wording_review = wording_sub.add_parser(
        "review",
        help=wording_review_description,
        description=wording_review_description,
    )
    wording_review.add_argument("--workspace", required=True)
    wording_review.add_argument("--claim-id", required=True)
    wording_review.add_argument("--handoff-id", required=True)
    wording_review.add_argument(
        "--decision",
        choices=(
            "within-limit",
            "within_limit",
            "too-strong",
            "too_strong",
            "unclear",
        ),
        required=True,
        help=(
            "Решение проверяющего: within-limit или within_limit — формулировка "
            "в пределах доказанного; too-strong или too_strong — вывод слишком "
            "сильный; unclear — вывод неясен."
        ),
    )
    wording_review.add_argument("--reviewer", required=True)
    wording_review.add_argument("--reason", required=True)
    wording_review.add_argument("--finding-id", action="append", required=True)
    wording_review.add_argument("--wording-text", required=True)
    wording_review.add_argument("--wording-source", required=True)

    refresh_description = (
        "Зафиксировать проверку актуальности практики перед подачей жалобы."
    )
    refresh = sub.add_parser(
        "refresh",
        help=refresh_description,
        description=refresh_description,
    )
    refresh_sub = refresh.add_subparsers(dest="refresh_command", required=True)
    refresh_record_description = (
        "Записать проверку актуальности официальной практики перед подачей."
    )
    refresh_record = refresh_sub.add_parser(
        "record",
        help=refresh_record_description,
        description=refresh_record_description,
    )
    refresh_record.add_argument("--workspace", required=True)
    refresh_record.add_argument(
        "--as-of",
        required=True,
        help="Дата проверки в формате ГГГГ-ММ-ДД.",
    )
    refresh_record.add_argument("--reviewer", required=True)
    refresh_record.add_argument("--official-check-ref", required=True)
    refresh_record.add_argument(
        "--corpus-cutoff",
        help="Дата, по которую проверен корпус; по умолчанию берётся --as-of.",
    )

    terminal_descriptions = {
        "status": "Показать текущее состояние анализа по каждому утверждению.",
        "validate": "Проверить полноту и согласованность рабочей папки анализа.",
    }
    for name, description in terminal_descriptions.items():
        command = sub.add_parser(name, help=description, description=description)
        command.add_argument("--workspace", required=True)
        command.add_argument(
            "--stage",
            choices=STAGES,
            default="drafting",
            help=(
                "Этап проверки: options, drafting, qa или filing "
                "(по умолчанию: drafting)."
            ),
        )
    lint_description = "Проверить структуру и взаимные ссылки файлов анализа."
    lint = sub.add_parser(
        "lint",
        help=lint_description,
        description=lint_description,
    )
    lint.add_argument("--workspace", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "init":
            value = init_workspace(
                args.workspace,
                case_id=args.case_id,
                case_file=args.case_file,
                argument_research=args.argument_research,
            )
            code = 0
        elif args.command == "scan":
            value = scan_input(args.workspace, args.input)
            code = 0
        elif args.command == "claim":
            value = review_trigger(
                args.workspace,
                claim_id=args.claim_id,
                decision=args.decision,
                reviewer=args.reviewer,
                reason=args.reason,
            )
            code = 0
        elif args.command == "request":
            value = create_request(
                args.workspace,
                claim_ids=args.claim_id,
                output=args.output,
            )
            code = 0
        elif args.command == "run":
            value = attach_run(
                args.workspace,
                request_id=args.request_id,
                cassation_workspace=args.cassation_workspace,
                skills_root=args.skills_root,
            )
            code = 0 if value.get("status") == "attached" else 2
        elif args.command == "result":
            value = import_result(
                args.workspace,
                args.input,
                request_id=args.request_id,
                trusted_source_workspace=args.trusted_source_workspace,
                skills_root=args.skills_root,
            )
            code = 0
        elif args.command == "wording":
            value = review_wording(
                args.workspace,
                claim_id=args.claim_id,
                handoff_id=args.handoff_id,
                decision=args.decision,
                reviewer=args.reviewer,
                reason=args.reason,
                finding_ids=args.finding_id,
                wording_text=args.wording_text,
                wording_source=args.wording_source,
            )
            code = 0
        elif args.command == "refresh":
            value = record_refresh(
                args.workspace,
                as_of=args.as_of,
                reviewer=args.reviewer,
                official_check_ref=args.official_check_ref,
                corpus_cutoff=args.corpus_cutoff,
            )
            code = 0
        elif args.command == "status":
            value = derive_state(args.workspace, stage=args.stage)
            code = 0
        elif args.command == "validate":
            value = validate_workspace(args.workspace, stage=args.stage)
            code = 0 if value.get("valid") else 2
        elif args.command == "lint":
            value = lint_workspace(args.workspace)
            code = 0 if value.get("valid") else 2
        else:  # pragma: no cover - argparse prevents this branch
            raise ValueError(f"Неизвестная команда: {args.command}")
        _print_json(value)
        return code
    except (ValueError, OSError) as exc:
        _print_json(
            {
                "schema_version": SCHEMA_VERSION,
                "valid": False,
                "error": str(exc),
                "next_action": "Исправьте указанный вход или binding и повторите команду.",
            },
            stream=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
