"""Versioned, file-based handoffs between independently installed skills."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
REQUIRED_FIELDS = (
    "schema_version",
    "handoff_id",
    "created_at",
    "source_skill",
    "target_skill",
    "run_id",
    "plan_sha256",
    "evidence_sha256",
    "payload_type",
    "payload",
    "limitations",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def make_envelope(
    *,
    source_skill: str,
    target_skill: str,
    run_id: str,
    plan_sha256: str,
    evidence_sha256: str,
    payload_type: str,
    payload: dict[str, Any],
    limitations: list[str],
    created_at: str,
) -> dict[str, Any]:
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "source_skill": source_skill,
        "target_skill": target_skill,
        "run_id": run_id,
        "plan_sha256": plan_sha256,
        "evidence_sha256": evidence_sha256,
        "payload_type": payload_type,
        "payload": payload,
        "limitations": limitations,
    }
    envelope["handoff_id"] = hashlib.sha256(_canonical(envelope)).hexdigest()
    return envelope


def validate_envelope(envelope: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in envelope:
            errors.append(f"Отсутствует поле handoff: {field}")
    if errors:
        return errors
    if envelope["schema_version"] != SCHEMA_VERSION:
        errors.append(f"Несовместимая версия handoff: {envelope['schema_version']}")
    if not _is_sha256(envelope["plan_sha256"]):
        errors.append("plan_sha256 должен быть SHA-256")
    if not _is_sha256(envelope["evidence_sha256"]):
        errors.append("evidence_sha256 должен быть SHA-256")
    if not isinstance(envelope["payload"], dict):
        errors.append("payload должен быть объектом")
    if not isinstance(envelope["limitations"], list):
        errors.append("limitations должен быть списком")
    unsigned = {key: value for key, value in envelope.items() if key != "handoff_id"}
    expected = hashlib.sha256(_canonical(unsigned)).hexdigest()
    if envelope["handoff_id"] != expected:
        errors.append("handoff_id не соответствует содержимому envelope")
    return errors


def write_envelope(path: Path, envelope: dict[str, Any]) -> str:
    errors = validate_envelope(envelope)
    if errors:
        raise ValueError("; ".join(errors))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if path.exists():
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Повреждён JSONL handoff, строка {line_number}: {exc}") from exc
            if record.get("handoff_id") == envelope["handoff_id"]:
                if record != envelope:
                    raise ValueError("Повторный handoff_id имеет иное содержимое")
                return "already_present"
            existing.append(record)
    existing.append(envelope)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as stream:
        for record in existing:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    return "written"
