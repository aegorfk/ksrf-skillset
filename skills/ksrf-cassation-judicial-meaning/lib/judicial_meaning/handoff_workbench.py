"""Typed, content-bound file handoffs with an atomic local inbox ledger."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "1.0"
SUPPORTED_PAYLOAD_TYPES = frozenset(
    {
        "unproven_research_questions",
        "approved_bounded_findings",
        "authority_cards",
        "selected_authorities",
    }
)
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
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _digest(envelope: Mapping[str, Any]) -> str:
    unsigned = {key: value for key, value in envelope.items() if key != "handoff_id"}
    return hashlib.sha256(_canonical_bytes(unsigned)).hexdigest()


def _string_list(value: Any, *, allow_empty: bool) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
    )


def _payload_errors(payload_type: str, payload: Mapping[str, Any]) -> list[str]:
    """Validate typed payload semantics independently of envelope integrity."""

    errors: list[str] = []
    if payload_type == "unproven_research_questions":
        if payload.get("drafting_ready") is True:
            errors.append("unproven_research_questions не может иметь drafting_ready=true.")
        if not _string_list(payload.get("questions"), allow_empty=False):
            errors.append("unproven_research_questions требует непустой список questions.")
        forbidden = sorted(
            key
            for key in (
                "findings",
                "maximum_permitted_claim",
                "supporting_position_card_ids",
                "adverse_position_card_ids",
                "complaint_wording",
            )
            if key in payload
        )
        if forbidden:
            errors.append(
                "Непроверенный payload не может содержать готовые выводы: "
                + ", ".join(forbidden)
                + "."
            )
    elif payload_type == "approved_bounded_findings":
        if payload.get("drafting_ready") is not True:
            errors.append("approved_bounded_findings требует drafting_ready=true.")
        maximum = payload.get("maximum_permitted_claim")
        if not isinstance(maximum, str) or not maximum.strip():
            errors.append("approved_bounded_findings требует maximum_permitted_claim.")
        findings = payload.get("findings")
        if not isinstance(findings, list) or not findings or not all(
            isinstance(item, Mapping) for item in findings
        ):
            errors.append("approved_bounded_findings требует непустой список findings.")
        if not _string_list(payload.get("supporting_position_card_ids"), allow_empty=False):
            errors.append("approved_bounded_findings требует supporting_position_card_ids.")
        if not _string_list(payload.get("adverse_position_card_ids"), allow_empty=True):
            errors.append("approved_bounded_findings требует явный список adverse_position_card_ids.")
    elif payload_type in {"authority_cards", "selected_authorities"}:
        cards = payload.get("authority_cards")
        if not isinstance(cards, list) or not cards or not all(
            isinstance(item, Mapping) for item in cards
        ):
            errors.append("authority_cards требует непустой список проверенных карточек.")
        if not isinstance(payload.get("reviewer"), str) or not payload["reviewer"].strip():
            errors.append("authority_cards требует reviewer.")
        if payload.get("review_state") != "approved":
            errors.append("authority_cards требует review_state=approved.")
        maximum = payload.get("maximum_permitted_claim")
        if not isinstance(maximum, str) or not maximum.strip():
            errors.append("authority_cards требует maximum_permitted_claim.")
    return errors


def create_handoff(
    *,
    source_skill: str,
    target_skill: str,
    run_id: str,
    plan_sha256: str,
    evidence_sha256: str,
    payload_type: str,
    payload: Mapping[str, Any],
    limitations: Sequence[str],
    created_at: str,
    fingerprint_sha256: str | None = None,
) -> dict[str, Any]:
    """Create one typed envelope whose identifier is its canonical digest."""

    for field_name, value in (
        ("source_skill", source_skill),
        ("target_skill", target_skill),
        ("run_id", run_id),
        ("created_at", created_at),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} должен быть непустой строкой.")
    if not _is_sha256(plan_sha256):
        raise ValueError("plan_sha256 должен быть SHA-256.")
    if not _is_sha256(evidence_sha256):
        raise ValueError("evidence_sha256 должен быть SHA-256.")
    if payload_type not in SUPPORTED_PAYLOAD_TYPES:
        raise ValueError(f"Неподдерживаемый payload_type: {payload_type}")
    if not isinstance(payload, Mapping):
        raise ValueError("payload должен быть объектом.")
    if not isinstance(limitations, Sequence) or isinstance(limitations, (str, bytes)):
        raise ValueError("limitations должен быть списком строк.")
    if not all(isinstance(item, str) for item in limitations):
        raise ValueError("limitations должен содержать только строки.")

    payload_copy = dict(payload)
    payload_errors = _payload_errors(payload_type, payload_copy)
    if payload_errors:
        raise ValueError(" ".join(payload_errors))
    if payload_type != "unproven_research_questions" and not any(
        isinstance(item, str) and item.strip() for item in limitations
    ):
        raise ValueError("Проверенный handoff требует явные limitations.")
    if payload_type != "unproven_research_questions" and not _is_sha256(
        fingerprint_sha256
    ):
        raise ValueError("Проверенный handoff требует fingerprint_sha256 дела заявителя.")

    envelope: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "source_skill": source_skill,
        "target_skill": target_skill,
        "run_id": run_id,
        "plan_sha256": plan_sha256,
        "evidence_sha256": evidence_sha256,
        "payload_type": payload_type,
        "payload": payload_copy,
        "limitations": list(limitations),
    }
    if fingerprint_sha256 is not None:
        if not _is_sha256(fingerprint_sha256):
            raise ValueError("fingerprint_sha256 должен быть SHA-256.")
        envelope["fingerprint_sha256"] = fingerprint_sha256
    envelope["handoff_id"] = _digest(envelope)
    return envelope


def _result(status: str, errors: list[str], envelope: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "valid": status == "valid",
        "status": status,
        "errors": errors,
        "handoff_id": envelope.get("handoff_id"),
        "digest_sha256": _digest(envelope) if all(key in envelope for key in REQUIRED_FIELDS if key != "handoff_id") else None,
    }


def check_handoff(
    envelope: Mapping[str, Any],
    *,
    expected_target: str | None = None,
    current_plan_sha256: str | None = None,
    current_evidence_sha256: str | None = None,
    current_fingerprint_sha256: str | None = None,
    current_maximum_permitted_claim: str | None = None,
) -> dict[str, Any]:
    """Validate type, digest, compatibility and optional current-workspace hashes."""

    if not isinstance(envelope, Mapping):
        return {
            "schema_version": SCHEMA_VERSION,
            "valid": False,
            "status": "invalid",
            "errors": ["Handoff должен быть объектом."],
            "handoff_id": None,
            "digest_sha256": None,
        }
    missing = [field for field in REQUIRED_FIELDS if field not in envelope]
    if missing:
        return _result("invalid", [f"Отсутствует поле: {field}" for field in missing], envelope)
    if envelope.get("schema_version") != SCHEMA_VERSION:
        return _result(
            "incompatible",
            [f"Несовместимая версия handoff: {envelope.get('schema_version')}"],
            envelope,
        )
    if not isinstance(envelope.get("payload"), Mapping):
        return _result("invalid", ["payload должен быть объектом."], envelope)
    limitations = envelope.get("limitations")
    if not isinstance(limitations, list) or not all(isinstance(item, str) for item in limitations):
        return _result("invalid", ["limitations должен быть списком строк."], envelope)
    hash_errors = []
    for key in ("plan_sha256", "evidence_sha256"):
        if not _is_sha256(envelope.get(key)):
            hash_errors.append(f"{key} должен быть SHA-256.")
    if hash_errors:
        return _result("invalid", hash_errors, envelope)

    expected_digest = _digest(envelope)
    if not _is_sha256(envelope.get("handoff_id")) or envelope.get("handoff_id") != expected_digest:
        return _result(
            "tampered",
            ["handoff_id не соответствует каноническому содержимому envelope."],
            envelope,
        )
    if envelope.get("payload_type") not in SUPPORTED_PAYLOAD_TYPES:
        return _result(
            "incompatible",
            [f"Неподдерживаемый payload_type: {envelope.get('payload_type')}"],
            envelope,
        )
    payload_type = str(envelope.get("payload_type"))
    payload_errors = _payload_errors(payload_type, envelope["payload"])
    if payload_type != "unproven_research_questions" and not any(
        isinstance(item, str) and item.strip() for item in limitations
    ):
        payload_errors.append("Проверенный handoff требует явные limitations.")
    if payload_type != "unproven_research_questions" and not _is_sha256(
        envelope.get("fingerprint_sha256")
    ):
        payload_errors.append(
            "Проверенный handoff требует fingerprint_sha256 дела заявителя."
        )
    if payload_errors:
        return _result("incompatible", payload_errors, envelope)
    if expected_target is not None and envelope.get("target_skill") != expected_target:
        return _result(
            "incompatible",
            [
                "Handoff предназначен для другого target skill: "
                f"{envelope.get('target_skill')} вместо {expected_target}."
            ],
            envelope,
        )

    stale_errors = []
    if current_plan_sha256 is not None and envelope.get("plan_sha256") != current_plan_sha256:
        stale_errors.append("plan_sha256 не совпадает с текущим исследовательским планом.")
    if current_evidence_sha256 is not None and envelope.get("evidence_sha256") != current_evidence_sha256:
        stale_errors.append("evidence_sha256 не совпадает с текущими доказательствами.")
    if (
        current_fingerprint_sha256 is not None
        and envelope.get("fingerprint_sha256") != current_fingerprint_sha256
    ):
        stale_errors.append(
            "fingerprint_sha256 не совпадает с текущим отпечатком дела заявителя."
        )
    if stale_errors:
        return _result("stale", stale_errors, envelope)
    if (
        current_maximum_permitted_claim is not None
        and payload_type != "unproven_research_questions"
        and envelope["payload"].get("maximum_permitted_claim")
        != current_maximum_permitted_claim
    ):
        return _result(
            "incompatible",
            [
                "maximum_permitted_claim handoff не совпадает с текущим пределом вывода."
            ],
            envelope,
        )
    return _result("valid", [], envelope)


def _read_ledger(ledger_path: Path) -> list[dict[str, Any]]:
    if not ledger_path.exists():
        return []
    records = []
    for line_number, line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Повреждён inbox ledger, строка {line_number}.") from exc
        if not isinstance(record, dict):
            raise ValueError(f"Inbox ledger, строка {line_number}, должен содержать объект.")
        records.append(record)
    return records


def _atomic_write_ledger(ledger_path: Path, records: list[dict[str, Any]]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for record in records
    )
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=ledger_path.parent,
            prefix=f".{ledger_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, ledger_path)
        temporary_name = None
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def import_handoff(
    envelope: Mapping[str, Any],
    ledger_path: str | Path,
    *,
    expected_target: str | None = None,
    current_plan_sha256: str | None = None,
    current_evidence_sha256: str | None = None,
    current_fingerprint_sha256: str | None = None,
    current_maximum_permitted_claim: str | None = None,
) -> dict[str, Any]:
    """Check and atomically add one envelope to an idempotent JSONL inbox ledger."""

    check = check_handoff(
        envelope,
        expected_target=expected_target,
        current_plan_sha256=current_plan_sha256,
        current_evidence_sha256=current_evidence_sha256,
        current_fingerprint_sha256=current_fingerprint_sha256,
        current_maximum_permitted_claim=current_maximum_permitted_claim,
    )
    if not check["valid"]:
        return {**check, "imported": False}

    target = Path(ledger_path)
    records = _read_ledger(target)
    handoff_id = str(envelope["handoff_id"])
    for record in records:
        if record.get("handoff_id") != handoff_id:
            continue
        if record.get("envelope") == dict(envelope) and record.get("envelope_sha256") == handoff_id:
            return {
                **check,
                "status": "idempotent_noop",
                "valid": True,
                "imported": False,
                "ledger_path": str(target),
            }
        return {
            **check,
            "status": "tampered_conflict",
            "valid": False,
            "errors": ["Существующий handoff_id связан с иным содержимым inbox ledger."],
            "imported": False,
            "ledger_path": str(target),
        }

    records.append(
        {
            "schema_version": SCHEMA_VERSION,
            "handoff_id": handoff_id,
            "envelope_sha256": handoff_id,
            "envelope": dict(envelope),
        }
    )
    _atomic_write_ledger(target, records)
    return {
        **check,
        "status": "imported",
        "valid": True,
        "imported": True,
        "ledger_path": str(target),
    }
