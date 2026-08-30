#!/usr/bin/env python3
"""Deterministic discovery helper for the ksrf-doctrine-research skill.

The tool plans redacted searches, queries explicitly enabled scholarly APIs,
normalizes and deduplicates metadata, and writes fail-closed coverage artifacts.
It does not establish current law, a doctrinal proposition, or a constitutional
defect.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import math
import os
import re
import ssl
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


SKILL_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = SKILL_ROOT / "references" / "provider-registry.json"
TAXONOMY_PATH = SKILL_ROOT / "references" / "problem-taxonomy.json"
USER_AGENT = "ksrf-doctrine-research/0.1"
ALLOWED_MODES = {"exploratory_norm", "case_scoped", "hypothesis_verification"}
PII_PATTERNS = (
    re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
    re.compile(r"(?<!\d)(?:\+7|8)[\s()\-]*\d{3}[\s()\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)"),
    re.compile(r"(?<!\d)\d{3}-\d{3}-\d{3}[ -]\d{2}(?!\d)"),
    re.compile(r"(?<!\d)\d{2}\s?\d{2}\s?\d{6}(?!\d)"),
    re.compile(r"(?<!\w)\d{2}[A-ZА-Я]{2}\d{4}-\d{2}-\d{4}-\d{6}-\d{2}(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\d)\d{10}(?!\d)"),
    re.compile(r"(?<!\d)\d{12}(?!\d)"),
    re.compile(r"(?<!\d)(?:\d{13}|\d{15})(?!\d)"),
    re.compile(r"(?<!\d)\d{1,2}-\d{1,8}/\d{4}(?!\d)"),
    re.compile(r"\b(?:ФИО|адрес|дата\s+рождения|ИНН|ОГРН|СНИЛС|УИД|номер\s+дела)\s*[:№]", re.IGNORECASE),
    re.compile(r"\b[А-ЯЁ][а-яё]{2,}\s+[А-ЯЁ][а-яё]{2,}\s+[А-ЯЁ][а-яё]{2,}\b"),
)
TOPIC_STOP_PREFIXES = (
    "стат",
    "кодекс",
    "россий",
    "федерац",
    "прав",
    "проблем",
    "примен",
    "толкован",
    "поряд",
    "установ",
    "отсут",
    "друг",
    "связ",
    "вмест",
    "част",
)


class DoctrineResearchError(RuntimeError):
    """Controlled user-facing error."""


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _assert_json_text_encodable(value: Any) -> None:
    if isinstance(value, str):
        value.encode("utf-8")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite JSON number")
    elif isinstance(value, Mapping):
        for key, nested in value.items():
            _assert_json_text_encodable(key)
            _assert_json_text_encodable(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_json_text_encodable(nested)


def _load_json_strict(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream, parse_constant=_reject_json_constant)
    _assert_json_text_encodable(value)
    return value


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def pretty_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json(path: Path, value: Any) -> None:
    atomic_write_bytes(path, pretty_bytes(value))


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    payload = b"".join(canonical_bytes(dict(row)) for row in rows)
    atomic_write_bytes(path, payload)


def stable_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(str(part).encode("utf-8"))
        digest.update(b"\0")
    return f"{prefix}{digest.hexdigest()[:16]}"


def unique_strings(values: Optional[Iterable[Any]]) -> List[str]:
    result: List[str] = []
    seen = set()
    if values is None:
        return result
    if isinstance(values, (str, bytes)):
        values = [values]
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_iso_date(value: Any) -> Optional[date]:
    text = normalize_space(value)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def has_meaningful_content(value: Any) -> bool:
    if isinstance(value, str):
        return bool(normalize_space(value))
    if isinstance(value, Mapping):
        return any(has_meaningful_content(part) for part in value.values())
    if isinstance(value, list):
        return any(has_meaningful_content(part) for part in value)
    return False


def has_meaningful_items(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    return any(has_meaningful_content(item) for item in value)


def validate_text_list(field: str, value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return [f"{field} must be a list"]
    return [
        f"{field}[{index}] must be a non-empty string"
        for index, item in enumerate(value)
        if not isinstance(item, str) or not normalize_space(item)
    ]


def validate_phrase_list(field: str, value: Any, mapping_keys: Sequence[str]) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return [f"{field} must be a list"]
    errors: List[str] = []
    allowed = set(mapping_keys)
    for index, item in enumerate(value):
        if isinstance(item, str):
            if not normalize_space(item):
                errors.append(f"{field}[{index}] must not be blank")
            continue
        if not isinstance(item, Mapping):
            errors.append(f"{field}[{index}] must be a string or an object")
            continue
        unknown = sorted(set(item) - allowed)
        if unknown:
            errors.append(f"{field}[{index}] contains unsupported keys: {', '.join(unknown)}")
        invalid_values = [
            key
            for key in mapping_keys
            if item.get(key) is not None and not isinstance(item.get(key), str)
        ]
        if invalid_values:
            errors.append(f"{field}[{index}] phrase values must be strings: {', '.join(invalid_values)}")
        if not any(isinstance(item.get(key), str) and normalize_space(item.get(key)) for key in mapping_keys):
            errors.append(f"{field}[{index}] must contain a non-empty public phrase")
    return errors


REFERENCE_KEYS = {
    "ref",
    "source_id",
    "document_id",
    "evidence_id",
    "path",
    "url",
    "locator",
    "page",
    "paragraph",
    "sha256",
    "size_bytes",
    "provenance",
    "trust_receipt",
}

ROUTE_CONTEXT_KEYS = {
    "schema_version",
    "portfolio_id",
    "portfolio_artifact",
    "issue_option_id",
    "trust_receipts",
}
PORTFOLIO_ARTIFACT_KEYS = {
    "artifact_id",
    "sha256",
    "size_bytes",
}
TRUST_RECEIPT_KEYS = {
    "schema_version",
    "receipt_id",
    "issuer_id",
    "key_id",
    "signature_algorithm",
    "issued_at",
    "expires_at",
    "signed_claims",
    "signed_claims_sha256",
    "signature_base64",
}
TRUST_CLAIMS_KEYS = {
    "receipt_role",
    "matter_id",
    "request_binding_sha256",
    "issue_option_id",
    "portfolio_id",
    "portfolio_sha256",
    "portfolio_size_bytes",
    "evidence_role",
    "artifact_id",
    "artifact_sha256",
    "artifact_size_bytes",
    "as_of_date",
    "corpus_generation_id",
    "corpus_manifest_sha256",
    "coverage_report_sha256",
    "query_plan_sha256",
    "hypotheses_sha256",
    "freshness_policy_id",
    "revocation_registry_generation",
}
LOWER_HEX_SHA256_RE = re.compile(r"[0-9a-f]{64}")


def validate_reference_list(field: str, value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return [f"{field} must be a list"]
    errors: List[str] = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            if not normalize_space(item):
                errors.append(f"{field}[{index}] must not be blank")
            continue
        if not isinstance(item, Mapping):
            errors.append(f"{field}[{index}] must be a string or an object")
            continue
        unknown = sorted(set(item) - REFERENCE_KEYS)
        if unknown:
            errors.append(f"{field}[{index}] contains unsupported keys: {', '.join(unknown)}")
        if not has_meaningful_content(item):
            errors.append(f"{field}[{index}] must contain a non-empty reference")
    return errors


def normalize_title(value: Any) -> str:
    text = normalize_space(value).casefold().replace("ё", "е")
    return re.sub(r"[^0-9a-zа-я]+", " ", text).strip()


def lexical_stems(values: Iterable[Any]) -> set[str]:
    stems: set[str] = set()
    for value in values:
        for token in re.findall(r"[a-zа-яё]{5,}", normalize_space(value).casefold().replace("ё", "е")):
            if token.startswith(TOPIC_STOP_PREFIXES):
                continue
            stems.add(token[:7])
    return stems


def normalize_doi(value: Any) -> Optional[str]:
    text = normalize_space(value).casefold()
    if not text:
        return None
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text)
    text = re.sub(r"^doi:\s*", "", text)
    return text.rstrip(".,; ") or None


def strip_html(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_space(text)


def first_nonempty(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and LOWER_HEX_SHA256_RE.fullmatch(value) is not None


def _exact_keys(value: Mapping[str, Any], expected: set[str], field: str) -> List[str]:
    actual = set(value)
    errors: List[str] = []
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        errors.append(f"{field} missing keys: {', '.join(missing)}")
    if unknown:
        errors.append(f"{field} contains unsupported keys: {', '.join(unknown)}")
    return errors


def request_binding_payload(request: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the request bytes a receipt may bind without a signature cycle."""

    payload = json.loads(json.dumps(request, ensure_ascii=False))
    context = payload.get("doctrine_route_context")
    if isinstance(context, dict):
        context.pop("trust_receipts", None)
    for field in ("application_evidence_refs", "fulltext_source_refs"):
        values = payload.get(field)
        if isinstance(values, list):
            for item in values:
                if isinstance(item, dict):
                    item.pop("trust_receipt", None)
    payload.pop("adverse_search_receipt", None)
    return payload


def request_binding_sha256(request: Mapping[str, Any]) -> str:
    return stable_hash(request_binding_payload(request))


def _rfc3339(value: Any) -> Optional[datetime]:
    text = normalize_space(value)
    if not text or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})",
        text,
    ):
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _trust_receipt_errors(
    field: str,
    receipt: Any,
    *,
    expected: Mapping[str, Any],
) -> Tuple[List[str], Optional[str]]:
    """Validate canonical bindings only; never authenticate the issuer locally."""

    if not isinstance(receipt, Mapping):
        return [f"{field} must be a doctrine-trust-receipt/1.0 object"], None
    errors = _exact_keys(receipt, TRUST_RECEIPT_KEYS, field)
    if receipt.get("schema_version") != "doctrine-trust-receipt/1.0":
        errors.append(f"{field}.schema_version must be doctrine-trust-receipt/1.0")
    for key in ("receipt_id", "issuer_id", "key_id"):
        if not normalize_space(receipt.get(key)):
            errors.append(f"{field}.{key} is required")
    if receipt.get("signature_algorithm") != "ed25519":
        errors.append(f"{field}.signature_algorithm must be ed25519")
    issued_at = _rfc3339(receipt.get("issued_at"))
    expires_at = _rfc3339(receipt.get("expires_at"))
    if issued_at is None:
        errors.append(f"{field}.issued_at must be RFC3339 with timezone")
    if expires_at is None:
        errors.append(f"{field}.expires_at must be RFC3339 with timezone")
    if issued_at is not None and expires_at is not None and expires_at <= issued_at:
        errors.append(f"{field}.expires_at must be after issued_at")
    signature = receipt.get("signature_base64")
    try:
        decoded_signature = base64.b64decode(signature, validate=True)
    except (TypeError, ValueError):
        decoded_signature = b""
    if len(decoded_signature) != 64:
        errors.append(f"{field}.signature_base64 must encode a 64-byte Ed25519 signature")

    claims = receipt.get("signed_claims")
    if not isinstance(claims, Mapping):
        errors.append(f"{field}.signed_claims must be an object")
        claims = {}
    else:
        errors.extend(_exact_keys(claims, TRUST_CLAIMS_KEYS, f"{field}.signed_claims"))
    claims_sha256 = receipt.get("signed_claims_sha256")
    if not _is_sha256(claims_sha256):
        errors.append(f"{field}.signed_claims_sha256 must be lowercase SHA-256")
    elif claims_sha256 != stable_hash(claims):
        errors.append(f"{field}.signed_claims_sha256 does not match canonical signed_claims bytes")

    for key, expected_value in expected.items():
        if claims.get(key) != expected_value:
            errors.append(f"{field}.signed_claims.{key} mismatch")
    for key in (
        "portfolio_sha256",
        "artifact_sha256",
        "corpus_manifest_sha256",
        "coverage_report_sha256",
        "query_plan_sha256",
        "hypotheses_sha256",
    ):
        value = claims.get(key)
        if value is not None and not _is_sha256(value):
            errors.append(f"{field}.signed_claims.{key} must be null or lowercase SHA-256")
    for key in ("portfolio_size_bytes", "artifact_size_bytes"):
        value = claims.get(key)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            errors.append(f"{field}.signed_claims.{key} must be null or a non-negative integer")
    for key in ("freshness_policy_id", "revocation_registry_generation"):
        if not normalize_space(claims.get(key)):
            errors.append(f"{field}.signed_claims.{key} is required")
    if parse_iso_date(claims.get("as_of_date")) is None:
        errors.append(f"{field}.signed_claims.as_of_date must be YYYY-MM-DD")

    role = claims.get("receipt_role")
    if role in {"application_evidence", "fulltext_evidence", "adverse_search"}:
        for key in ("corpus_generation_id",):
            if not normalize_space(claims.get(key)):
                errors.append(f"{field}.signed_claims.{key} is required for {role}")
        for key in ("corpus_manifest_sha256", "coverage_report_sha256", "query_plan_sha256"):
            if not _is_sha256(claims.get(key)):
                errors.append(f"{field}.signed_claims.{key} is required for {role}")

    return sorted(set(errors)), stable_hash(receipt)


def _route_context_binding(
    request: Mapping[str, Any],
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    value = request.get("doctrine_route_context")
    if value is None:
        return None, []
    if not isinstance(value, Mapping):
        return None, ["doctrine_route_context must be an object"]

    errors = _exact_keys(value, ROUTE_CONTEXT_KEYS, "doctrine_route_context")
    portfolio_id = normalize_space(value.get("portfolio_id"))
    issue_option_id = normalize_space(value.get("issue_option_id"))
    if value.get("schema_version") != "doctrine-route-context/1.1":
        errors.append("doctrine_route_context.schema_version must be doctrine-route-context/1.1")
    if not portfolio_id:
        errors.append("doctrine_route_context.portfolio_id is required")
    if not issue_option_id:
        errors.append("doctrine_route_context.issue_option_id is required")

    artifact = value.get("portfolio_artifact")
    if not isinstance(artifact, Mapping):
        errors.append("doctrine_route_context.portfolio_artifact must be an object")
        artifact = {}
    else:
        errors.extend(
            _exact_keys(artifact, PORTFOLIO_ARTIFACT_KEYS, "doctrine_route_context.portfolio_artifact")
        )
    portfolio_artifact_id = normalize_space(artifact.get("artifact_id"))
    portfolio_sha256 = artifact.get("sha256")
    portfolio_size_bytes = artifact.get("size_bytes")
    if not portfolio_artifact_id:
        errors.append("doctrine_route_context.portfolio_artifact.artifact_id is required")
    if not _is_sha256(portfolio_sha256):
        errors.append("doctrine_route_context.portfolio_artifact.sha256 must be lowercase SHA-256")
    if (
        not isinstance(portfolio_size_bytes, int)
        or isinstance(portfolio_size_bytes, bool)
        or portfolio_size_bytes < 0
    ):
        errors.append("doctrine_route_context.portfolio_artifact.size_bytes must be a non-negative integer")

    receipts = value.get("trust_receipts")
    receipt_hashes: List[str] = []
    selection_count = 0
    if not isinstance(receipts, list) or not receipts:
        errors.append("doctrine_route_context.trust_receipts must contain a lane-selection receipt")
    else:
        expected = {
            "receipt_role": "lane_selection",
            "matter_id": normalize_space(request.get("matter_id")),
            "request_binding_sha256": request_binding_sha256(request),
            "issue_option_id": issue_option_id,
            "portfolio_id": portfolio_id,
            "portfolio_sha256": portfolio_sha256,
            "portfolio_size_bytes": portfolio_size_bytes,
            "evidence_role": "selected_doctrine_lane",
            "artifact_id": portfolio_artifact_id,
            "artifact_sha256": portfolio_sha256,
            "artifact_size_bytes": portfolio_size_bytes,
            "as_of_date": request.get("as_of_date"),
            "hypotheses_sha256": stable_hash(request.get("hypotheses_under_test") or []),
        }
        for index, receipt in enumerate(receipts):
            receipt_errors, receipt_hash = _trust_receipt_errors(
                f"doctrine_route_context.trust_receipts[{index}]",
                receipt,
                expected=expected,
            )
            errors.extend(receipt_errors)
            if isinstance(receipt, Mapping) and isinstance(receipt.get("signed_claims"), Mapping):
                if receipt["signed_claims"].get("receipt_role") == "lane_selection":
                    selection_count += 1
            if receipt_hash:
                receipt_hashes.append(receipt_hash)
    if selection_count != 1:
        errors.append("doctrine_route_context.trust_receipts must contain exactly one lane_selection receipt")

    binding: Dict[str, Any] = {
        "portfolio_id": portfolio_id or None,
        "portfolio_artifact_id": portfolio_artifact_id or None,
        "portfolio_sha256": portfolio_sha256 if _is_sha256(portfolio_sha256) else None,
        "portfolio_size_bytes": (
            portfolio_size_bytes
            if isinstance(portfolio_size_bytes, int)
            and not isinstance(portfolio_size_bytes, bool)
            and portfolio_size_bytes >= 0
            else None
        ),
        "issue_option_id": issue_option_id or None,
        "receipt_canonical_sha256s": sorted(receipt_hashes),
    }
    return binding, sorted(set(errors))


def _trusted_reference_errors(
    request: Mapping[str, Any],
    binding: Optional[Mapping[str, Any]],
    field: str,
    value: Any,
    *,
    identity_key: str,
    provenance: str,
    receipt_role: str,
) -> Tuple[List[str], List[str]]:
    if not isinstance(value, list) or not value:
        return [f"{field} must contain at least one trust-receipted reference object"], []
    expected_keys = {identity_key, "sha256", "size_bytes", "provenance", "trust_receipt"}
    errors: List[str] = []
    receipt_hashes: List[str] = []
    for index, item in enumerate(value):
        label = f"{field}[{index}]"
        if not isinstance(item, Mapping):
            errors.append(f"{label} must be a trust-receipted reference object")
            continue
        errors.extend(_exact_keys(item, expected_keys, label))
        artifact_id = normalize_space(item.get(identity_key))
        if not artifact_id:
            errors.append(f"{label}.{identity_key} is required")
        artifact_sha256 = item.get("sha256")
        if not _is_sha256(artifact_sha256):
            errors.append(f"{label}.sha256 must be lowercase SHA-256")
        artifact_size = item.get("size_bytes")
        if not isinstance(artifact_size, int) or isinstance(artifact_size, bool) or artifact_size < 0:
            errors.append(f"{label}.size_bytes must be a non-negative integer")
        if item.get("provenance") != provenance:
            errors.append(f"{label}.provenance must be {provenance}")
        expected = {
            "receipt_role": receipt_role,
            "matter_id": normalize_space(request.get("matter_id")),
            "request_binding_sha256": request_binding_sha256(request),
            "issue_option_id": binding.get("issue_option_id") if binding else None,
            "portfolio_id": binding.get("portfolio_id") if binding else None,
            "portfolio_sha256": binding.get("portfolio_sha256") if binding else None,
            "portfolio_size_bytes": binding.get("portfolio_size_bytes") if binding else None,
            "evidence_role": provenance,
            "artifact_id": artifact_id,
            "artifact_sha256": artifact_sha256,
            "artifact_size_bytes": artifact_size,
            "as_of_date": request.get("as_of_date"),
            "hypotheses_sha256": stable_hash(request.get("hypotheses_under_test") or []),
        }
        receipt_errors, receipt_hash = _trust_receipt_errors(
            f"{label}.trust_receipt",
            item.get("trust_receipt"),
            expected=expected,
        )
        errors.extend(receipt_errors)
        if receipt_hash:
            receipt_hashes.append(receipt_hash)
    return sorted(set(errors)), sorted(receipt_hashes)


def _adverse_receipt_errors(
    request: Mapping[str, Any],
    binding: Optional[Mapping[str, Any]],
) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    if request.get("adverse_search_required") is not True:
        errors.append("adverse_search_required must be true")
    if request.get("adverse_search_status") != "pass":
        errors.append("adverse_search_status must be pass")
    expected = {
        "receipt_role": "adverse_search",
        "matter_id": normalize_space(request.get("matter_id")),
        "request_binding_sha256": request_binding_sha256(request),
        "issue_option_id": binding.get("issue_option_id") if binding else None,
        "portfolio_id": binding.get("portfolio_id") if binding else None,
        "portfolio_sha256": binding.get("portfolio_sha256") if binding else None,
        "portfolio_size_bytes": binding.get("portfolio_size_bytes") if binding else None,
        "evidence_role": "adverse_search",
        "artifact_id": None,
        "artifact_sha256": None,
        "artifact_size_bytes": None,
        "as_of_date": request.get("as_of_date"),
        "hypotheses_sha256": stable_hash(request.get("hypotheses_under_test") or []),
    }
    receipt_errors, receipt_hash = _trust_receipt_errors(
        "adverse_search_receipt",
        request.get("adverse_search_receipt"),
        expected=expected,
    )
    errors.extend(receipt_errors)
    return sorted(set(errors)), [receipt_hash] if receipt_hash else []


def _finish_route_decision(core: Mapping[str, Any]) -> Dict[str, Any]:
    decision = dict(core)
    decision["route_decision_hash"] = stable_hash(core)
    return decision


def select_research_route(request: Mapping[str, Any]) -> Dict[str, Any]:
    """Derive a typed route; request-carried receipts never authenticate themselves."""

    request_hash = stable_hash(request)
    binding, context_errors = _route_context_binding(request)
    if "doctrine_lane_selected" in request:
        context_errors.append(
            "bare doctrine_lane_selected is unsupported; use doctrine_route_context"
        )
    hypotheses = request.get("hypotheses_under_test")
    hypothesis_set_hash = stable_hash(hypotheses if hypotheses is not None else [])
    base = {
        "schema_version": "doctrine-route/1.1",
        "request_sha256": request_hash,
        "request_binding_sha256": request_binding_sha256(request),
        "matter_id": normalize_space(request.get("matter_id")) or None,
        "issue_option_id": binding.get("issue_option_id") if binding else None,
        "portfolio_id": binding.get("portfolio_id") if binding else None,
        "portfolio_sha256": binding.get("portfolio_sha256") if binding else None,
        "portfolio_size_bytes": binding.get("portfolio_size_bytes") if binding else None,
        "receipt_canonical_sha256s": (
            binding.get("receipt_canonical_sha256s", []) if binding else []
        ),
        "hypothesis_set_sha256": hypothesis_set_hash,
        "declared_mode": request.get("mode"),
        "promotion_eligible": False,
    }

    if binding is None:
        status = "blocked" if context_errors else "not_routed"
        blockers = ["route_context_invalid"] if context_errors else []
        return _finish_route_decision(
            {
                **base,
                "routed": False,
                "mode": None,
                "status": status,
                "blockers": blockers,
                "scope_limits": [],
                "validation_errors": sorted(set(context_errors)),
                "trust_verification": {
                    "schema_version": "doctrine-verifier-boundary/1.0",
                    "status": "not_required" if not context_errors else "unavailable",
                    "protected_verifier_configured": False,
                    "receipt_canonical_sha256s": [],
                },
                "maximum_permitted_claim": "standalone_exploratory_discovery_only",
            }
        )

    hypothesis_declared = (
        "hypotheses_under_test" in request
        and hypotheses is not None
        and hypotheses != []
    )
    scope_limits: List[str] = []
    strict_errors: List[str] = []
    receipt_hashes = list(binding.get("receipt_canonical_sha256s", []))

    if hypothesis_declared:
        mode = "hypothesis_verification"
        fulltext_errors, fulltext_receipt_hashes = _trusted_reference_errors(
            request,
            binding,
            "fulltext_source_refs",
            request.get("fulltext_source_refs"),
            identity_key="source_id",
            provenance="lawful_fulltext_artifact",
            receipt_role="fulltext_evidence",
        )
        adverse_errors, adverse_receipt_hashes = _adverse_receipt_errors(request, binding)
        strict_errors.extend(fulltext_errors)
        strict_errors.extend(adverse_errors)
        receipt_hashes.extend(fulltext_receipt_hashes)
        receipt_hashes.extend(adverse_receipt_hashes)
    else:
        for field in ("judicial_meanings", "mechanisms", "consequences"):
            if not has_meaningful_items(request.get(field)):
                scope_limits.append(f"{field}_missing")

        application_value = request.get("application_evidence_refs")
        if not has_meaningful_items(application_value):
            scope_limits.append("application_evidence_refs_missing")
        else:
            application_errors, application_receipt_hashes = _trusted_reference_errors(
                request,
                binding,
                "application_evidence_refs",
                application_value,
                identity_key="evidence_id",
                provenance="official_application_record",
                receipt_role="application_evidence",
            )
            receipt_hashes.extend(application_receipt_hashes)
            if application_errors:
                scope_limits.append(
                    "application_evidence_refs_invalid_or_unverified"
                )

        norms = request.get("norms")
        norm_versions_complete = (
            isinstance(norms, list)
            and bool(norms)
            and all(
                isinstance(norm, Mapping)
                and parse_iso_date(norm.get("version_date")) is not None
                for norm in norms
            )
        )
        if not norm_versions_complete:
            scope_limits.append("norm_version_dates_missing")
        mode = "exploratory_norm" if scope_limits else "case_scoped"

    validation_request = dict(request)
    validation_request["mode"] = mode
    validation_errors = list(context_errors)
    validation_errors.extend(validate_request(validation_request))
    validation_errors.extend(strict_errors)
    validation_errors = sorted(set(validation_errors))

    blockers: List[str] = []
    if context_errors:
        blockers.append("route_context_invalid")
    if validation_errors:
        blockers.append("request_schema_invalid")
    if mode == "hypothesis_verification":
        if any(error.startswith("fulltext_source_refs") for error in strict_errors):
            blockers.append("fulltext_source_refs_invalid_or_unverified")
        if any(
            error.startswith("adverse_search_") for error in strict_errors
        ):
            blockers.append("adverse_search_not_passed_or_unbound")
    # This skill has no protected key store, revocation registry, byte resolver,
    # or host-attested verifier. Request-carried JSON therefore cannot close a
    # conditional gate, even when every declared hash and signature field has
    # the expected shape.
    blockers.append("protected_receipt_verifier_unavailable")

    return _finish_route_decision(
        {
            **base,
            "routed": True,
            "mode": mode,
            "status": "blocked" if blockers else "ready",
            "blockers": blockers,
            "scope_limits": sorted(set(scope_limits)),
            "validation_errors": validation_errors,
            "receipt_canonical_sha256s": sorted(set(receipt_hashes)),
            "trust_verification": {
                "schema_version": "doctrine-verifier-boundary/1.0",
                "status": "unavailable",
                "protected_verifier_configured": False,
                "receipt_canonical_sha256s": sorted(set(receipt_hashes)),
                "required_attestation_schema": "doctrine-verifier-attestation/1.0",
                "reason": "no protected verifier/trust root exists inside this skill boundary",
            },
            "maximum_permitted_claim": "candidate_only_untrusted_declarations",
        }
    )


def require_bound_research_route(request: Mapping[str, Any]) -> Dict[str, Any]:
    decision = select_research_route(request)
    if not decision.get("routed"):
        if decision.get("status") == "not_routed" and request.get("mode") == "exploratory_norm":
            errors = validate_request(request)
            if errors:
                raise DoctrineResearchError("invalid standalone request: " + "; ".join(errors))
            return decision
        raise DoctrineResearchError("doctrine route is not selected by a valid conditional context")
    if decision.get("status") != "ready":
        if "protected_receipt_verifier_unavailable" in decision.get("blockers", []):
            raise DoctrineResearchError(
                "doctrine route is blocked: protected receipt verifier unavailable; "
                "request-carried receipts are untrusted declarations"
            )
        details = "; ".join(decision.get("validation_errors") or decision.get("blockers") or [])
        raise DoctrineResearchError(f"doctrine route is blocked: {details}")
    if request.get("mode") != decision.get("mode"):
        raise DoctrineResearchError(
            "declared mode does not match derived doctrine route: "
            f"{request.get('mode')} != {decision.get('mode')}"
        )
    return decision


def validate_request(request: Mapping[str, Any], *, for_external_search: bool = False) -> List[str]:
    errors: List[str] = []
    route_binding, route_context_errors = _route_context_binding(request)
    errors.extend(route_context_errors)
    if "doctrine_lane_selected" in request:
        errors.append("bare doctrine_lane_selected is unsupported; use doctrine_route_context")
    if str(request.get("schema_version")) != "1.0":
        errors.append("schema_version must be 1.0")
    if not normalize_space(request.get("matter_id")):
        errors.append("matter_id is required")
    mode = request.get("mode")
    if not isinstance(mode, str) or mode not in ALLOWED_MODES:
        errors.append(f"mode must be one of {sorted(ALLOWED_MODES)}")
    hypotheses_value = request.get("hypotheses_under_test")
    if (
        "hypotheses_under_test" in request
        and hypotheses_value is not None
        and hypotheses_value != []
        and mode != "hypothesis_verification"
    ):
        errors.append(
            "non-empty hypotheses_under_test requires mode hypothesis_verification"
        )
    as_of = parse_iso_date(request.get("as_of_date"))
    if as_of is None:
        errors.append("as_of_date must be a valid YYYY-MM-DD calendar date")
    norms = request.get("norms")
    if not isinstance(norms, list) or not norms:
        errors.append("norms must contain at least one public norm descriptor")
    else:
        for index, norm in enumerate(norms):
            if not isinstance(norm, Mapping):
                errors.append(f"norms[{index}] must be an object")
                continue
            if not isinstance(norm.get("citation"), str) or not normalize_space(norm.get("citation")):
                errors.append(f"norms[{index}].citation is required")
            variants = norm.get("citation_variants")
            if variants is not None:
                errors.extend(validate_text_list(f"norms[{index}].citation_variants", variants))
            title = norm.get("title")
            if title is not None and (not isinstance(title, str) or not normalize_space(title)):
                errors.append(f"norms[{index}].title must be a non-empty string when provided")
            excerpt = norm.get("public_text_excerpt")
            if excerpt is not None and not isinstance(excerpt, str):
                errors.append(f"norms[{index}].public_text_excerpt must be a string when provided")
    for field in (
        "disputed_elements",
        "mechanisms",
        "consequences",
        "adjacent_norms",
        "subject_terms",
        "material_types",
    ):
        errors.extend(validate_text_list(field, request.get(field)))
    errors.extend(
        validate_phrase_list(
            "judicial_meanings",
            request.get("judicial_meanings"),
            ("public_excerpt", "meaning", "phrase"),
        )
    )
    errors.extend(validate_reference_list("application_evidence_refs", request.get("application_evidence_refs")))
    errors.extend(validate_reference_list("fulltext_source_refs", request.get("fulltext_source_refs")))
    languages = request.get("languages")
    errors.extend(validate_text_list("languages", languages))
    if isinstance(languages, list):
        for index, language in enumerate(languages):
            if isinstance(language, str) and normalize_space(language) and not re.fullmatch(
                r"(?:[a-z]{2,3}(?:-[a-z0-9]{2,8})?|any)", language.casefold()
            ):
                errors.append(f"languages[{index}] must be a language tag or any")
    date_range = request.get("date_range", {})
    if not isinstance(date_range, Mapping):
        errors.append("date_range must be an object")
    else:
        start, end = date_range.get("from"), date_range.get("to")
        if start is not None and (not isinstance(start, int) or start < 1800):
            errors.append("date_range.from must be a plausible year")
        if end is not None and (not isinstance(end, int) or end < 1800):
            errors.append("date_range.to must be a plausible year")
        if isinstance(end, int) and as_of is not None and end > as_of.year:
            errors.append("date_range.to must not exceed as_of_date year")
        if isinstance(start, int) and isinstance(end, int) and start > end:
            errors.append("date_range.from must not exceed date_range.to")
    privacy = request.get("privacy", {})
    if not isinstance(privacy, Mapping):
        errors.append("privacy must be an object")
    elif for_external_search:
        if privacy.get("external_queries_redacted") is not True:
            errors.append("privacy.external_queries_redacted must be true before external search")
        if privacy.get("class") not in {"public_abstracted", "public_norm_profile"}:
            errors.append("privacy.class must be public_abstracted or public_norm_profile for external search")
    if mode == "case_scoped":
        if not has_meaningful_items(request.get("judicial_meanings")):
            errors.append("case_scoped mode requires at least one non-empty judicial_meaning")
        if not has_meaningful_items(request.get("mechanisms")):
            errors.append("case_scoped mode requires at least one non-empty mechanism")
        if not has_meaningful_items(request.get("consequences")):
            errors.append("case_scoped mode requires at least one non-empty consequence")
        reference_errors, _ = _trusted_reference_errors(
                request,
                route_binding,
                "application_evidence_refs",
                request.get("application_evidence_refs"),
                identity_key="evidence_id",
                provenance="official_application_record",
                receipt_role="application_evidence",
            )
        errors.extend(reference_errors)
        for index, norm in enumerate(norms or []):
            version_date = parse_iso_date(norm.get("version_date")) if isinstance(norm, Mapping) else None
            if version_date is None:
                errors.append(f"case_scoped mode requires norms[{index}].version_date as a valid YYYY-MM-DD date")
            elif as_of is not None and version_date > as_of:
                errors.append(f"norms[{index}].version_date must not exceed as_of_date")
    if mode == "hypothesis_verification":
        errors.extend(
            validate_phrase_list(
                "hypotheses_under_test",
                request.get("hypotheses_under_test"),
                ("hypothesis", "statement", "text", "claim"),
            )
        )
        if not has_meaningful_items(request.get("hypotheses_under_test")):
            errors.append("hypothesis_verification mode requires at least one non-empty hypotheses_under_test item")
        reference_errors, _ = _trusted_reference_errors(
                request,
                route_binding,
                "fulltext_source_refs",
                request.get("fulltext_source_refs"),
                identity_key="source_id",
                provenance="lawful_fulltext_artifact",
                receipt_role="fulltext_evidence",
            )
        errors.extend(reference_errors)
        adverse_errors, _ = _adverse_receipt_errors(request, route_binding)
        errors.extend(adverse_errors)
    return errors


def load_request(path: Path, *, for_external_search: bool = False) -> Dict[str, Any]:
    request = _load_json_for_command(path)
    if not isinstance(request, dict):
        raise DoctrineResearchError("request must be a JSON object")
    errors = validate_request(request, for_external_search=for_external_search)
    if errors:
        raise DoctrineResearchError("invalid request: " + "; ".join(errors))
    require_bound_research_route(request)
    return request


def extract_judicial_phrases(request: Mapping[str, Any]) -> List[str]:
    phrases: List[str] = []
    for item in request.get("judicial_meanings", []) or []:
        if isinstance(item, str):
            phrases.append(item)
        elif isinstance(item, Mapping):
            value = first_nonempty(item, ("public_excerpt", "meaning", "phrase"))
            if value:
                phrases.append(str(value))
    return unique_strings(phrases)


def extract_hypothesis_phrases(request: Mapping[str, Any]) -> List[str]:
    phrases: List[str] = []
    for item in request.get("hypotheses_under_test", []) or []:
        if isinstance(item, str):
            phrases.append(item)
        elif isinstance(item, Mapping):
            value = first_nonempty(item, ("hypothesis", "statement", "text", "claim"))
            if value:
                phrases.append(str(value))
    return unique_strings(phrases)


def norm_anchors(request: Mapping[str, Any]) -> List[Tuple[str, str]]:
    anchors: List[Tuple[str, str]] = []
    for index, norm in enumerate(request.get("norms", [])):
        citations = unique_strings([norm.get("citation"), *(norm.get("citation_variants", []) or [])])
        for position, citation in enumerate(citations):
            anchors.append((citation, f"norms[{index}].citation_variants[{position}]"))
        title = normalize_space(norm.get("title"))
        if title:
            anchors.append((title, f"norms[{index}].title"))
    return anchors


def build_problem_profile(request: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": "norm-problem-profile/1.0",
        "matter_id": request["matter_id"],
        "mode": request["mode"],
        "as_of_date": request["as_of_date"],
        "jurisdiction": request.get("jurisdiction", "RU"),
        "languages": unique_strings(request.get("languages", ["ru"])),
        "norms": request.get("norms", []),
        "judicial_phrases": extract_judicial_phrases(request),
        "disputed_elements": unique_strings(request.get("disputed_elements", [])),
        "mechanisms": unique_strings(request.get("mechanisms", [])),
        "consequences": unique_strings(request.get("consequences", [])),
        "adjacent_norms": unique_strings(request.get("adjacent_norms", [])),
        "subject_terms": unique_strings(request.get("subject_terms", [])),
        "constitutional_conclusion_preseeded": False,
        "case_scope_limit": "not_case_scoped" if request["mode"] == "exploratory_norm" else "application_evidence_external",
    }


def request_sha256(request: Mapping[str, Any]) -> str:
    return stable_hash(request)


def ensure_workspace_identity(request: Mapping[str, Any], workspace: Path) -> None:
    snapshot = workspace / "request.snapshot.json"
    if not snapshot.exists():
        return
    try:
        existing = _load_json_for_command(snapshot)
        same_identity = isinstance(existing, Mapping) and request_sha256(existing) == request_sha256(request)
    except (TypeError, UnicodeError, ValueError, RecursionError):
        same_identity = False
    if not same_identity:
        raise DoctrineResearchError(
            "WORKSPACE_IDENTITY_MISMATCH: use a new workspace for a different request"
        )


def build_query_plan(request: Mapping[str, Any]) -> Dict[str, Any]:
    route_decision = require_bound_research_route(request)
    anchors = norm_anchors(request)
    if not anchors:
        raise DoctrineResearchError("no searchable norm anchors")
    primary_anchor = anchors[0][0]
    queries: List[Dict[str, Any]] = []
    seen = set()

    def add(lane: str, text: str, origin: str, polarity: str = "neutral") -> None:
        cleaned = normalize_space(text)
        key = (lane, cleaned.casefold(), origin, polarity)
        if not cleaned or key in seen:
            return
        seen.add(key)
        intent_id = stable_id("intent-", lane, origin, cleaned)
        queries.append(
            {
                "query_id": stable_id("query-", intent_id, cleaned),
                "query_intent_id": intent_id,
                "lane": lane,
                "text": cleaned,
                "origin": origin,
                "polarity": polarity,
                "status": "planned",
            }
        )

    for text, origin in anchors:
        lane = "norm_title" if origin.endswith(".title") else "exact_norm"
        add(lane, f'"{text}"', origin)

    for index, phrase in enumerate(extract_judicial_phrases(request)):
        add("decisive_phrase", f'"{phrase}" право', f"judicial_meanings[{index}]")
    for index, element in enumerate(unique_strings(request.get("disputed_elements", []))):
        add("element_meaning", f'"{primary_anchor}" "{element}"', f"disputed_elements[{index}]")
        add("problem_probe", f'"{primary_anchor}" "{element}" проблемы применения толкование', f"disputed_elements[{index}]")
        add("adverse", f'"{primary_anchor}" "{element}" обоснование допустимость альтернативное толкование', f"disputed_elements[{index}]", "adverse")
    for index, mechanism in enumerate(unique_strings(request.get("mechanisms", []))):
        add("mechanism_consequence", f'"{primary_anchor}" "{mechanism}"', f"mechanisms[{index}]")
    for index, consequence in enumerate(unique_strings(request.get("consequences", []))):
        add("mechanism_consequence", f'"{primary_anchor}" "{consequence}"', f"consequences[{index}]")
    for index, adjacent in enumerate(unique_strings(request.get("adjacent_norms", []))):
        add("system_link", f'"{primary_anchor}" "{adjacent}"', f"adjacent_norms[{index}]")
    for index, term in enumerate(unique_strings(request.get("subject_terms", []))):
        add("subject_problem", f'"{term}" право проблемы применения', f"subject_terms[{index}]")

    if request.get("mode") == "hypothesis_verification":
        add(
            "adverse",
            f'"{primary_anchor}" критика опровержение пределы альтернативное толкование',
            "generated:hypothesis-adverse",
            "adverse",
        )
        for index, hypothesis in enumerate(extract_hypothesis_phrases(request)):
            add(
                "adverse",
                f'"{primary_anchor}" "{hypothesis}" критика опровержение альтернативное толкование',
                f"hypotheses_under_test[{index}]",
                "adverse",
            )

    add("problem_probe", f'"{primary_anchor}" проблемы применения спорные вопросы', "generated:generic-problem-probe")
    add("procedure_evidence", f'"{primary_anchor}" процедура доказательства защита', "generated:procedure-evidence")
    add("remedy", f'"{primary_anchor}" способ защиты восстановление права', "generated:remedy")
    add("history_update", f'"{primary_anchor}" изменение редакции история правового регулирования', "generated:history-update")

    canonical_queries = [{key: row[key] for key in ("query_id", "query_intent_id", "lane", "text", "origin", "polarity")} for row in queries]
    canonical_for_hash = {
        "route_decision_hash": route_decision["route_decision_hash"],
        "queries": canonical_queries,
    }
    return {
        "schema_version": "doctrine-query-plan/1.0",
        "matter_id": request["matter_id"],
        "as_of_date": request["as_of_date"],
        "query_count": len(queries),
        "queries": queries,
        "route_decision_hash": route_decision["route_decision_hash"],
        "query_plan_hash": stable_hash(canonical_for_hash),
        "legal_conclusions": [],
        "promotion_eligible": False,
        "maximum_permitted_claim": route_decision["maximum_permitted_claim"],
    }


def select_bounded_queries(query_plan: Mapping[str, Any], limit: int) -> List[Dict[str, Any]]:
    """Select a lane-balanced prefix instead of exhausting the first query family."""
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    lane_order: List[str] = []
    for query in query_plan.get("queries", []):
        lane = str(query.get("lane") or "unknown")
        if lane not in buckets:
            buckets[lane] = []
            lane_order.append(lane)
        buckets[lane].append(dict(query))
    selected: List[Dict[str, Any]] = []
    position = 0
    while len(selected) < limit:
        added = False
        for lane in lane_order:
            if position < len(buckets[lane]):
                selected.append(buckets[lane][position])
                added = True
                if len(selected) == limit:
                    break
        if not added:
            break
        position += 1
    return selected


def provider_routing(
    request: Mapping[str, Any],
    registry: Mapping[str, Any],
    selected_providers: Sequence[str],
) -> Dict[str, Any]:
    access_overrides = request.get("provider_access", {}) or {}
    decisions: List[Dict[str, Any]] = []
    providers = registry.get("providers", {})
    for provider_id in sorted(providers):
        capability = providers[provider_id]
        override = access_overrides.get(provider_id, {}) if isinstance(access_overrides, Mapping) else {}
        status = override.get("status", capability.get("default_status", "not_configured")) if isinstance(override, Mapping) else capability.get("default_status", "not_configured")
        if provider_id == "openalex" and status != "disabled":
            status = "ready_api" if normalize_space(os.getenv("OPENALEX_API_KEY")) else "auth_required"
        adapter = capability.get("adapter")
        selected = provider_id in selected_providers
        decisions.append(
            {
                "provider": provider_id,
                "label": capability.get("label", provider_id),
                "roles": capability.get("roles", []),
                "interface": capability.get("interface"),
                "adapter": adapter,
                "access_status": status,
                "selected_for_automated_run": selected,
                "automated_run_eligible": bool(selected and adapter and status in {"ready_api", "available", "enabled"}),
                "manual_task_required": capability.get("automation", "").startswith("manual"),
                "official_docs": capability.get("official_docs", []),
                "reason": (
                    "selected documented adapter"
                    if selected and adapter
                    else "manual or future provider route"
                    if capability.get("automation") != "supported"
                    else "not selected for this bounded run"
                ),
            }
        )
    unknown = sorted(set(selected_providers) - set(providers))
    if unknown:
        raise DoctrineResearchError(f"unknown providers: {', '.join(unknown)}")
    return {
        "schema_version": "provider-routing/1.0",
        "matter_id": request["matter_id"],
        "registry_last_verified_at": registry.get("last_verified_at"),
        "decisions": decisions,
    }


def privacy_inspection_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(character for character in normalized if unicodedata.category(character) != "Cf")


def redaction_violations(query_plan: Mapping[str, Any], request: Mapping[str, Any]) -> List[Dict[str, str]]:
    violations: List[Dict[str, str]] = []
    prohibited = [
        privacy_inspection_text(term).casefold()
        for term in unique_strings((request.get("privacy") or {}).get("prohibited_external_terms", []))
    ]
    for query in query_plan.get("queries", []):
        text = query.get("text", "")
        if any(unicodedata.category(character) == "Cf" for character in text):
            violations.append({"query_id": query["query_id"], "reason": "unicode_format_control"})
        inspection_text = privacy_inspection_text(text)
        folded = inspection_text.casefold()
        for term in prohibited:
            if term and term in folded:
                violations.append({"query_id": query["query_id"], "reason": "prohibited_external_term"})
        for pattern in PII_PATTERNS:
            if pattern.search(inspection_text):
                violations.append({"query_id": query["query_id"], "reason": "pii_like_pattern"})
    return violations


def generated_at(request: Mapping[str, Any]) -> str:
    return f"{request['as_of_date']}T00:00:00Z"


def prepare_workspace(
    request: Mapping[str, Any],
    workspace: Path,
    selected_providers: Sequence[str],
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    route_decision = require_bound_research_route(request)
    ensure_workspace_identity(request, workspace)
    registry = load_json(REGISTRY_PATH)
    taxonomy = load_json(TAXONOMY_PATH)
    profile = build_problem_profile(request)
    query_plan = build_query_plan(request)
    routing = provider_routing(request, registry, selected_providers)
    snapshot_hash = request_sha256(request)
    profile["request_sha256"] = snapshot_hash
    profile["route_decision_hash"] = route_decision["route_decision_hash"]
    query_plan["request_sha256"] = snapshot_hash
    routing["request_sha256"] = snapshot_hash
    routing["route_decision_hash"] = route_decision["route_decision_hash"]
    workspace.mkdir(parents=True, exist_ok=True)
    write_json(workspace / "request.snapshot.json", request)
    write_json(workspace / "route-decision.json", route_decision)
    write_json(workspace / "norm-problem-profile.json", profile)
    write_json(workspace / "provider-capabilities.snapshot.json", registry)
    write_json(workspace / "provider-routing.json", routing)
    write_json(workspace / "query-plan.json", query_plan)
    return registry, taxonomy, query_plan, routing


def http_json(url: str, *, timeout: float, contact_email: Optional[str]) -> Tuple[Any, Dict[str, Any]]:
    user_agent = USER_AGENT if not contact_email else f"{USER_AGENT} (mailto:{contact_email})"
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": user_agent})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=verified_ssl_context()) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload, {
                "http_status": getattr(response, "status", 200),
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "url": public_request_url(url),
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(512).decode("utf-8", errors="replace")
        raise DoctrineResearchError(f"HTTP {exc.code}: {body}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise DoctrineResearchError(f"network or response error: {exc}") from exc


def verified_ssl_context() -> ssl.SSLContext:
    """Build a verifying TLS context, including the common macOS Python fallback."""
    defaults = ssl.get_default_verify_paths()
    candidates = unique_strings(
        [
            os.getenv("SSL_CERT_FILE"),
            defaults.cafile,
            "/etc/ssl/cert.pem",
            "/etc/pki/tls/certs/ca-bundle.crt",
        ]
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ssl.create_default_context(cafile=candidate)
    return ssl.create_default_context()


def public_request_url(url: str) -> str:
    """Return a reproducible request URL without credentials or contact data."""
    parsed = urllib.parse.urlsplit(url)
    safe_pairs = []
    for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        safe_pairs.append((key, "[redacted]" if key.casefold() in {"api_key", "mailto"} else value))
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(safe_pairs), parsed.fragment)
    )


def abstract_from_inverted(index: Any) -> str:
    if not isinstance(index, Mapping):
        return ""
    positions: List[Tuple[int, str]] = []
    for word, word_positions in index.items():
        if not isinstance(word_positions, list):
            continue
        for position in word_positions:
            if isinstance(position, int):
                positions.append((position, str(word)))
    return " ".join(word for _, word in sorted(positions))


def normalize_openalex(payload: Mapping[str, Any], query: Mapping[str, Any]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for item in payload.get("results", []) or []:
        if not isinstance(item, Mapping):
            continue
        primary = item.get("primary_location") or {}
        best_oa = item.get("best_oa_location") or {}
        source = primary.get("source") or {} if isinstance(primary, Mapping) else {}
        authors = []
        for authorship in item.get("authorships", []) or []:
            author = authorship.get("author", {}) if isinstance(authorship, Mapping) else {}
            name = normalize_space(author.get("display_name")) if isinstance(author, Mapping) else ""
            if name:
                authors.append(name)
        abstract = abstract_from_inverted(item.get("abstract_inverted_index"))
        landing = first_nonempty(best_oa if isinstance(best_oa, Mapping) else {}, ("landing_page_url",)) or first_nonempty(primary if isinstance(primary, Mapping) else {}, ("landing_page_url",)) or item.get("id")
        pdf_url = first_nonempty(best_oa if isinstance(best_oa, Mapping) else {}, ("pdf_url",))
        records.append(
            {
                "provider": "openalex",
                "provider_record_id": item.get("id"),
                "query_ids": [query["query_id"]],
                "query_intent_ids": [query["query_intent_id"]],
                "query_lanes": [query["lane"]],
                "query_polarities": [query["polarity"]],
                "title": normalize_space(first_nonempty(item, ("display_name", "title"))),
                "authors": unique_strings(authors),
                "year": item.get("publication_year"),
                "language": item.get("language"),
                "publication_type": item.get("type"),
                "venue": normalize_space(source.get("display_name")) if isinstance(source, Mapping) else "",
                "doi": normalize_doi(item.get("doi")),
                "edn": None,
                "isbn": [],
                "issn": unique_strings(source.get("issn", []) if isinstance(source, Mapping) else []),
                "abstract": abstract,
                "landing_url": landing,
                "fulltext_url": pdf_url,
                "cited_by_count": item.get("cited_by_count"),
                "verification_status": "abstract_checked" if abstract else "metadata_only",
                "access_status": "open_fulltext_candidate" if pdf_url else "metadata_or_landing",
                "license_status": "unknown_requires_item_check",
            }
        )
    return records


def crossref_year(item: Mapping[str, Any]) -> Optional[int]:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        value = item.get(key)
        if isinstance(value, Mapping):
            parts = value.get("date-parts")
            if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
                year = parts[0][0]
                if isinstance(year, int):
                    return year
    return None


def normalize_crossref(payload: Mapping[str, Any], query: Mapping[str, Any]) -> List[Dict[str, Any]]:
    message = payload.get("message", {})
    items = message.get("items", []) if isinstance(message, Mapping) else []
    records: List[Dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, Mapping):
            continue
        title_value = item.get("title", [])
        title = title_value[0] if isinstance(title_value, list) and title_value else title_value
        venue_value = item.get("container-title", [])
        venue = venue_value[0] if isinstance(venue_value, list) and venue_value else venue_value
        authors = []
        for author in item.get("author", []) or []:
            if not isinstance(author, Mapping):
                continue
            name = normalize_space(" ".join(part for part in (author.get("given"), author.get("family")) if part))
            if name:
                authors.append(name)
        links = item.get("link", []) or []
        fulltext_url = None
        for link in links:
            if isinstance(link, Mapping) and link.get("URL"):
                fulltext_url = link["URL"]
                break
        abstract = strip_html(item.get("abstract"))
        records.append(
            {
                "provider": "crossref",
                "provider_record_id": item.get("DOI") or item.get("URL"),
                "query_ids": [query["query_id"]],
                "query_intent_ids": [query["query_intent_id"]],
                "query_lanes": [query["lane"]],
                "query_polarities": [query["polarity"]],
                "title": normalize_space(title),
                "authors": unique_strings(authors),
                "year": crossref_year(item),
                "language": item.get("language"),
                "publication_type": item.get("type"),
                "venue": normalize_space(venue),
                "doi": normalize_doi(item.get("DOI")),
                "edn": None,
                "isbn": unique_strings(item.get("ISBN", []) or []),
                "issn": unique_strings(item.get("ISSN", []) or []),
                "abstract": abstract,
                "landing_url": item.get("URL"),
                "fulltext_url": fulltext_url,
                "cited_by_count": item.get("is-referenced-by-count"),
                "verification_status": "abstract_checked" if abstract else "metadata_only",
                "access_status": "fulltext_link_candidate" if fulltext_url else "metadata_or_landing",
                "license_status": "unknown_requires_item_check",
            }
        )
    return records


def provider_url(provider: str, query_text: str, request: Mapping[str, Any], max_results: int) -> str:
    contact = normalize_space(os.getenv("SCHOLARLY_API_EMAIL"))
    date_range = request.get("date_range", {}) or {}
    if provider == "openalex":
        filters = []
        languages = unique_strings(request.get("languages", []))
        if languages and "any" not in languages:
            filters.append("language:" + "|".join(languages))
        if isinstance(date_range.get("from"), int):
            filters.append(f"from_publication_date:{date_range['from']}-01-01")
        if isinstance(date_range.get("to"), int):
            filters.append(f"to_publication_date:{date_range['to']}-12-31")
        params: Dict[str, Any] = {"search": query_text, "per-page": max_results}
        if filters:
            params["filter"] = ",".join(filters)
        openalex_credential = normalize_space(os.getenv("OPENALEX_API_KEY"))
        if not openalex_credential:
            raise DoctrineResearchError("OpenAlex requires OPENALEX_API_KEY")
        params["api_key"] = openalex_credential
        return "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    if provider == "crossref":
        filters = []
        if isinstance(date_range.get("from"), int):
            filters.append(f"from-pub-date:{date_range['from']}-01-01")
        if isinstance(date_range.get("to"), int):
            filters.append(f"until-pub-date:{date_range['to']}-12-31")
        params = {"query.bibliographic": query_text, "rows": max_results}
        if filters:
            params["filter"] = ",".join(filters)
        if contact:
            params["mailto"] = contact
        return "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    raise DoctrineResearchError(f"provider adapter not implemented: {provider}")


def fixture_payload(fixture_root: Path, provider: str, query_id: str) -> Any:
    candidates = (
        fixture_root / provider / f"{query_id}.json",
        fixture_root / provider / "default.json",
    )
    for candidate in candidates:
        if candidate.exists():
            try:
                return _load_json_strict(candidate)
            except (OSError, UnicodeError, ValueError, RecursionError) as exc:
                raise DoctrineResearchError(
                    f"OFFLINE_FIXTURE_INVALID:{provider}:{candidate.name}"
                ) from exc
    raise DoctrineResearchError(f"OFFLINE_FIXTURE_MISS:{provider}:{query_id}")


def normalize_provider_payload(provider: str, payload: Mapping[str, Any], query: Mapping[str, Any]) -> List[Dict[str, Any]]:
    try:
        if not isinstance(payload, Mapping):
            raise DoctrineResearchError(f"invalid {provider} response: top-level JSON object required")
        if provider == "openalex":
            if not isinstance(payload.get("meta"), Mapping) or not isinstance(payload.get("results"), list):
                raise DoctrineResearchError("invalid OpenAlex response: meta object and results list are required")
            openalex_count = payload.get("meta", {}).get("count")
            if payload.get("error") or not isinstance(openalex_count, int) or openalex_count < 0:
                raise DoctrineResearchError("invalid OpenAlex response: non-negative meta.count and no error are required")
            return normalize_openalex(payload, query)
        if provider == "crossref":
            message = payload.get("message")
            if payload.get("status") != "ok":
                raise DoctrineResearchError("invalid Crossref response: status must be ok")
            if not isinstance(message, Mapping) or not isinstance(message.get("items"), list):
                raise DoctrineResearchError("invalid Crossref response: message.items list is required")
            total_results = message.get("total-results")
            if not isinstance(total_results, int) or total_results < 0:
                raise DoctrineResearchError("invalid Crossref response: non-negative message.total-results is required")
            return normalize_crossref(payload, query)
        raise DoctrineResearchError(f"provider adapter not implemented: {provider}")
    except DoctrineResearchError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise DoctrineResearchError(
            f"provider response normalization failed for {provider}: {type(exc).__name__}: {exc}"
        ) from exc


def candidate_key(record: Mapping[str, Any]) -> Tuple[str, bool]:
    doi = normalize_doi(record.get("doi"))
    if doi:
        return f"doi:{doi}", True
    edn = normalize_title(record.get("edn"))
    if edn:
        return f"edn:{edn}", True
    isbn = unique_strings(record.get("isbn", []) or [])
    if isbn:
        return f"isbn:{normalize_title(isbn[0])}", True
    title = normalize_title(record.get("title"))
    provider_id = normalize_space(record.get("provider_record_id"))
    return f"provider:{record.get('provider')}:{provider_id or stable_id('', title, record.get('year'))}", False


def merge_candidates(records: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for original in records:
        record = dict(original)
        key, confident = candidate_key(record)
        if key not in grouped:
            record["deduplication_key"] = key
            record["deduplication_confident"] = confident
            record["discovered_by"] = [record.get("provider")]
            record["provider_records"] = [record.get("provider_record_id")]
            record["provider_urls"] = unique_strings([record.get("landing_url"), record.get("fulltext_url")])
            grouped[key] = record
            continue
        target = grouped[key]
        target["discovered_by"] = sorted(set(target.get("discovered_by", [])) | {record.get("provider")})
        target["provider_records"] = unique_strings([*target.get("provider_records", []), record.get("provider_record_id")])
        target["provider_urls"] = unique_strings([*target.get("provider_urls", []), record.get("landing_url"), record.get("fulltext_url")])
        target["query_ids"] = sorted(set(target.get("query_ids", [])) | set(record.get("query_ids", [])))
        target["query_intent_ids"] = sorted(set(target.get("query_intent_ids", [])) | set(record.get("query_intent_ids", [])))
        target["query_lanes"] = sorted(set(target.get("query_lanes", [])) | set(record.get("query_lanes", [])))
        target["query_polarities"] = sorted(set(target.get("query_polarities", [])) | set(record.get("query_polarities", [])))
        target["authors"] = unique_strings([*target.get("authors", []), *record.get("authors", [])])
        target["isbn"] = unique_strings([*target.get("isbn", []), *record.get("isbn", [])])
        target["issn"] = unique_strings([*target.get("issn", []), *record.get("issn", [])])
        if len(normalize_space(record.get("abstract"))) > len(normalize_space(target.get("abstract"))):
            target["abstract"] = record.get("abstract")
            target["verification_status"] = record.get("verification_status")
        if not target.get("fulltext_url") and record.get("fulltext_url"):
            target["fulltext_url"] = record.get("fulltext_url")
            target["access_status"] = record.get("access_status")
        conflicts = target.setdefault("field_conflicts", [])
        for field in ("title", "year", "venue"):
            left, right = target.get(field), record.get(field)
            if left not in (None, "") and right not in (None, "") and normalize_space(left).casefold() != normalize_space(right).casefold():
                conflict = {"field": field, "values": unique_strings([left, right])}
                if conflict not in conflicts:
                    conflicts.append(conflict)
    merged: List[Dict[str, Any]] = []
    for key in sorted(grouped):
        record = grouped[key]
        record["source_family_id"] = stable_id("family-", key)
        record["source_id"] = stable_id("src-", key)
        merged.append(record)
    return merged


def classify_problem_labels(text: str, taxonomy: Mapping[str, Any]) -> Tuple[List[str], Dict[str, List[str]]]:
    folded = text.casefold().replace("ё", "е")
    labels: List[str] = []
    matches: Dict[str, List[str]] = {}
    for category in taxonomy.get("categories", []):
        category_id = category.get("id")
        terms = unique_strings([*category.get("markers_ru", []), *category.get("markers_en", [])])
        found = [term for term in terms if term.casefold().replace("ё", "е") in folded]
        if found:
            labels.append(category_id)
            matches[category_id] = found
    return labels, matches


def contains_any(text: str, values: Iterable[str]) -> int:
    folded = text.casefold().replace("ё", "е")
    return sum(1 for value in unique_strings(values) if value.casefold().replace("ё", "е") in folded)


def enrich_record(record: MutableMapping[str, Any], request: Mapping[str, Any], taxonomy: Mapping[str, Any]) -> None:
    title = normalize_space(record.get("title", ""))
    abstract = normalize_space(record.get("abstract", ""))
    text = normalize_space(" ".join([title, abstract]))
    labels, matches = classify_problem_labels(text, taxonomy)
    record["problem_labels"] = labels
    record["problem_marker_matches"] = matches
    citations = [text for text, origin in norm_anchors(request) if not origin.endswith(".title")]
    titles = [text for text, origin in norm_anchors(request) if origin.endswith(".title")]
    topic_values = [
        *titles,
        *unique_strings(request.get("disputed_elements", [])),
        *unique_strings(request.get("mechanisms", [])),
        *unique_strings(request.get("consequences", [])),
        *unique_strings(request.get("subject_terms", [])),
    ]
    topic_stems = lexical_stems(topic_values)
    title_topic_stems = sorted(topic_stems & lexical_stems([title]))
    abstract_topic_stems = sorted((topic_stems & lexical_stems([abstract])) - set(title_topic_stems))
    components = {
        "exact_norm_hits": contains_any(text, citations),
        "norm_title_hits": contains_any(text, titles),
        "disputed_element_hits": contains_any(text, request.get("disputed_elements", [])),
        "mechanism_hits": contains_any(text, request.get("mechanisms", [])),
        "consequence_hits": contains_any(text, request.get("consequences", [])),
        "subject_term_hits": contains_any(text, request.get("subject_terms", [])),
        "title_topic_stem_hits": len(title_topic_stems),
        "abstract_topic_stem_hits": len(abstract_topic_stems),
        "problem_label_count": len(labels),
        "has_abstract": int(bool(record.get("abstract"))),
        "has_fulltext_candidate": int(bool(record.get("fulltext_url"))),
    }
    score = (
        components["exact_norm_hits"] * 8
        + components["norm_title_hits"] * 6
        + components["disputed_element_hits"] * 3
        + components["mechanism_hits"] * 2
        + components["consequence_hits"] * 2
        + components["subject_term_hits"] * 2
        + components["title_topic_stem_hits"] * 4
        + min(components["abstract_topic_stem_hits"], 8)
        + (min(components["problem_label_count"], 4) if title_topic_stems or abstract_topic_stems else 0)
        + components["has_abstract"]
        + components["has_fulltext_candidate"]
    )
    if components["exact_norm_hits"] or len(title_topic_stems) >= 2 or (title_topic_stems and len(abstract_topic_stems) >= 2):
        relevance_status = "high_lexical_priority"
    elif title_topic_stems or len(abstract_topic_stems) >= 2:
        relevance_status = "medium_lexical_priority"
    else:
        relevance_status = "weak_candidate"
    record["relevance_status"] = relevance_status
    record["topic_stem_matches"] = {
        "title": title_topic_stems,
        "abstract_only": abstract_topic_stems,
    }
    record["reading_priority"] = {
        "score": score,
        "components": components,
        "meaning": "discovery reading order only; not legal authority or source quality",
    }
    record["evidence_role"] = "doctrine_candidate"
    record["promotion_status"] = "candidate_only"
    record["cannot_satisfy"] = [
        "official_source",
        "current_norm_version",
        "application_in_applicant_case",
        "stable_judicial_meaning",
        "constitutional_authority",
        "case_facts",
    ]


def problem_candidates(records: Sequence[Mapping[str, Any]], taxonomy: Mapping[str, Any]) -> Dict[str, Any]:
    categories = {item["id"]: item for item in taxonomy.get("categories", [])}
    clusters = []
    for category_id in sorted(categories):
        matching = [
            record
            for record in records
            if category_id in record.get("problem_labels", [])
            and record.get("relevance_status") in {"high_lexical_priority", "medium_lexical_priority"}
        ]
        if not matching:
            continue
        matching = sorted(matching, key=lambda row: (-row.get("reading_priority", {}).get("score", 0), row.get("source_id", "")))
        category = categories[category_id]
        clusters.append(
            {
                "problem_candidate_id": stable_id("problem-", category_id),
                "category": category_id,
                "label": category.get("label_ru"),
                "candidate_localizations": category.get("candidate_localizations", []),
                "source_ids": [row["source_id"] for row in matching[:20]],
                "status": "candidate_only",
                "warning": "Keyword-level discovery cluster; full-text propositions and defect localization are still required.",
            }
        )
    return {
        "schema_version": "doctrine-problem-candidates/1.0",
        "clusters": clusters,
        "constitutional_hypotheses": [],
    }


def build_coverage(
    request: Mapping[str, Any],
    routing: Mapping[str, Any],
    selected_providers: Sequence[str],
    query_count: int,
    logs: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    run_config_hash: str,
) -> Dict[str, Any]:
    provider_statuses = []
    for provider in selected_providers:
        provider_logs = [row for row in logs if row.get("provider") == provider]
        successes = [row for row in provider_logs if row.get("status") == "success"]
        failures = [row for row in provider_logs if row.get("status") != "success"]
        if successes and not failures:
            status = "complete_bounded"
        elif successes:
            status = "partial"
        elif any("OFFLINE_FIXTURE_MISS" in str(row.get("error")) for row in failures):
            status = "offline_fixture_miss"
        else:
            status = "provider_error"
        provider_statuses.append(
            {
                "provider": provider,
                "status": status,
                "successful_queries": len(successes),
                "failed_queries": len(failures),
            }
        )
    manual_gaps = [
        {
            "provider": row["provider"],
            "label": row["label"],
            "status": row["access_status"],
            "roles": row.get("roles", []),
            "blocks_absence_claim": True,
        }
        for row in routing.get("decisions", [])
        if row.get("manual_task_required")
        or row.get("access_status")
        in {
            "auth_required",
            "subscription_required",
            "optional_subscription",
            "license_review_required",
            "manual_optional",
            "candidate_not_enabled",
            "contact_email_required",
            "api_key_recommended",
            "available_if_running",
        }
    ]
    bounded_complete = bool(selected_providers) and all(row["status"] == "complete_bounded" for row in provider_statuses)
    return {
        "schema_version": "doctrine-coverage/1.0",
        "matter_id": request["matter_id"],
        "request_sha256": request_sha256(request),
        "run_config_hash": run_config_hash,
        "as_of_date": request["as_of_date"],
        "bounded_search_complete": bounded_complete,
        "coverage_complete": False,
        "absence_claim_permitted": False,
        "queries_attempted": query_count * len(selected_providers),
        "provider_statuses": provider_statuses,
        "unique_candidates": len(records),
        "high_lexical_priority_candidates": sum(1 for row in records if row.get("relevance_status") == "high_lexical_priority"),
        "medium_lexical_priority_candidates": sum(1 for row in records if row.get("relevance_status") == "medium_lexical_priority"),
        "weak_candidates": sum(1 for row in records if row.get("relevance_status") == "weak_candidate"),
        "metadata_only": sum(1 for row in records if row.get("verification_status") == "metadata_only"),
        "abstract_checked": sum(1 for row in records if row.get("verification_status") == "abstract_checked"),
        "fulltext_candidates": sum(1 for row in records if row.get("fulltext_url")),
        "page_verified": 0,
        "manual_and_access_gaps": manual_gaps,
        "adverse_fulltext_pass_complete": False,
        "citation_chaining_complete": False,
        "permitted_absence_wording": "No candidates were found in the explicitly completed bounded scope." if not records and bounded_complete else None,
    }


def acquisition_queue(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = []
    for record in records:
        if record.get("relevance_status") == "weak_candidate":
            continue
        if record.get("fulltext_url") and record.get("access_status") in {
            "open_fulltext_verified",
            "local_fulltext_verified",
        }:
            continue
        if record.get("reading_priority", {}).get("score", 0) <= 0:
            continue
        rows.append(
            {
                "request_id": stable_id("acq-", record["source_id"]),
                "source_id": record["source_id"],
                "title": record.get("title"),
                "authors": record.get("authors", []),
                "doi": record.get("doi"),
                "status": "access_review_required",
                "next_step": "Verify any candidate full-text link, then check local library, OA resolvers, catalogues, and publisher terms before purchase.",
                "payment_authorized": False,
            }
        )
    return {"schema_version": "doctrine-acquisition-queue/1.0", "requests": rows[:50]}


def run_route(args: argparse.Namespace) -> int:
    request = _load_json_for_command(Path(args.request))
    if not isinstance(request, Mapping):
        raise DoctrineResearchError("route request must be a JSON object")
    decision = select_research_route(request)
    print(json.dumps(decision, ensure_ascii=False, sort_keys=True))
    return 2 if decision.get("status") == "blocked" else 0


def run_plan(args: argparse.Namespace) -> int:
    request = load_request(Path(args.request))
    selected = [part for part in (args.providers or "").split(",") if part]
    prepare_workspace(request, Path(args.workspace), selected)
    print(json.dumps({"status": "planned", "workspace": str(Path(args.workspace).resolve())}, ensure_ascii=False))
    return 0


def load_bound_plan(
    request: Mapping[str, Any], workspace: Path
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    for filename in ("request.snapshot.json", "route-decision.json", "query-plan.json"):
        if not (workspace / filename).is_file():
            raise DoctrineResearchError(
                f"search requires a prior bound plan artifact: {filename}"
            )
    snapshot = _load_json_for_command(workspace / "request.snapshot.json")
    if snapshot != request:
        raise DoctrineResearchError("planned request snapshot does not match search request")

    expected_route = require_bound_research_route(request)
    observed_route = _load_json_for_command(workspace / "route-decision.json")
    if observed_route != expected_route:
        raise DoctrineResearchError("route decision artifact/hash mismatch")

    expected_plan = build_query_plan(request)
    expected_plan["request_sha256"] = request_sha256(request)
    observed_plan = _load_json_for_command(workspace / "query-plan.json")
    if observed_plan != expected_plan:
        raise DoctrineResearchError("query plan artifact/hash mismatch")
    return observed_route, observed_plan


def run_search(args: argparse.Namespace) -> int:
    request = load_request(Path(args.request), for_external_search=True)
    workspace = Path(args.workspace)
    selected = unique_strings(part.strip() for part in args.providers.split(","))
    if not selected:
        raise DoctrineResearchError("at least one provider is required")
    try:
        route_decision, query_plan_preflight = load_bound_plan(request, workspace)
    except DoctrineResearchError as exc:
        _write_preflight_failure(workspace, exc)
        raise
    if request.get("mode") in {"case_scoped", "hypothesis_verification"}:
        approved_hash = normalize_space(getattr(args, "approved_query_plan_hash", ""))
        if approved_hash != query_plan_preflight["query_plan_hash"]:
            raise DoctrineResearchError(
                "manual query-plan review required: pass the exact --approved-query-plan-hash from the plan artifact"
            )
    registry_preflight = load_json(REGISTRY_PATH)
    routing_preflight = provider_routing(request, registry_preflight, selected)
    decisions = {row["provider"]: row for row in routing_preflight["decisions"]}
    for provider in selected:
        if not decisions[provider].get("adapter"):
            raise DoctrineResearchError(f"selected provider has no implemented adapter: {provider}")
        offline_auth_fixture = bool(
            args.offline_fixtures and decisions[provider].get("access_status") == "auth_required"
        )
        if not decisions[provider].get("automated_run_eligible") and not offline_auth_fixture:
            raise DoctrineResearchError(
                f"selected provider is not enabled for automated access: {provider} "
                f"({decisions[provider].get('access_status')})"
            )
    registry = load_json(REGISTRY_PATH)
    taxonomy = load_json(TAXONOMY_PATH)
    query_plan = query_plan_preflight
    routing = provider_routing(request, registry, selected)
    routing["request_sha256"] = request_sha256(request)
    routing["route_decision_hash"] = route_decision["route_decision_hash"]
    write_json(workspace / "provider-capabilities.snapshot.json", registry)
    write_json(workspace / "provider-routing.json", routing)
    violations = redaction_violations(query_plan, request)
    if violations:
        write_json(Path(args.workspace) / "qa-report.json", {"status": "blocked", "redaction_violations": violations})
        raise DoctrineResearchError("external query plan failed redaction checks")
    queries = select_bounded_queries(query_plan, args.max_queries)
    run_config_core = {
        "schema_version": "doctrine-search-run/1.0",
        "matter_id": request["matter_id"],
        "request_sha256": request_sha256(request),
        "query_plan_hash": query_plan["query_plan_hash"],
        "route_decision_hash": route_decision["route_decision_hash"],
        "selected_providers": selected,
        "selected_query_ids": [query["query_id"] for query in queries],
        "max_queries": args.max_queries,
        "max_results_per_query": args.max_results,
        "approved_query_plan_hash": normalize_space(getattr(args, "approved_query_plan_hash", "")) or None,
    }
    run_config_hash = hashlib.sha256(canonical_bytes(run_config_core)).hexdigest()
    run_config = {**run_config_core, "run_config_hash": run_config_hash}
    write_json(Path(args.workspace) / "search-run-config.json", run_config)
    logs: List[Dict[str, Any]] = []
    normalized: List[Dict[str, Any]] = []
    fixture_root = Path(args.offline_fixtures) if args.offline_fixtures else None
    for provider in selected:
        for query in queries:
            log: Dict[str, Any] = {
                "provider": provider,
                "query_id": query["query_id"],
                "query_intent_id": query["query_intent_id"],
                "lane": query["lane"],
                "query_text": query["text"],
                "as_of_date": request["as_of_date"],
            }
            try:
                if fixture_root:
                    payload = fixture_payload(fixture_root, provider, query["query_id"])
                    meta = {"transport": "offline_fixture", "fixture_root": str(fixture_root.resolve())}
                else:
                    url = provider_url(provider, query["text"], request, args.max_results)
                    payload, meta = http_json(url, timeout=args.timeout, contact_email=normalize_space(os.getenv("SCHOLARLY_API_EMAIL")) or None)
                    meta["transport"] = "network"
                rows = normalize_provider_payload(provider, payload, query)
                normalized.extend(rows)
                log.update({"status": "success", "result_count": len(rows), **meta})
            except DoctrineResearchError as exc:
                log.update({"status": "error", "result_count": 0, "error": str(exc), "transport": "offline_fixture" if fixture_root else "network"})
            logs.append(log)
            if not fixture_root and getattr(args, "request_delay", 0) > 0:
                time.sleep(args.request_delay)

    records = merge_candidates(normalized)
    for record in records:
        enrich_record(record, request, taxonomy)
    records.sort(key=lambda row: (-row.get("reading_priority", {}).get("score", 0), row.get("source_id", "")))
    coverage = build_coverage(request, routing, selected, len(queries), logs, records, run_config_hash)
    write_jsonl(Path(args.workspace) / "search-log.jsonl", logs)
    write_jsonl(Path(args.workspace) / "source-ledger.jsonl", records)
    write_json(Path(args.workspace) / "problem-candidates.json", problem_candidates(records, taxonomy))
    write_json(Path(args.workspace) / "coverage-report.json", coverage)
    write_json(Path(args.workspace) / "acquisition-queue.json", acquisition_queue(records))
    qa = validate_workspace(Path(args.workspace))
    write_json(Path(args.workspace) / "qa-report.json", qa)
    if qa["status"] != "pass":
        run_status = "searched_with_qa_errors"
    elif not any(row.get("status") == "success" for row in logs):
        run_status = "searched_without_success"
    elif not coverage["bounded_search_complete"]:
        run_status = "searched_with_coverage_gaps"
    else:
        run_status = "searched"
    summary = {
        "status": run_status,
        "workspace": str(Path(args.workspace).resolve()),
        "unique_candidates": len(records),
        "bounded_search_complete": coverage["bounded_search_complete"],
        "coverage_complete": False,
        "qa_status": qa["status"],
    }
    print(json.dumps(summary, ensure_ascii=False))
    if qa["status"] != "pass":
        return 2
    if not any(row.get("status") == "success" for row in logs):
        return 3
    if not coverage["bounded_search_complete"]:
        return 4
    return 0


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line, parse_constant=_reject_json_constant)
            except (json.JSONDecodeError, ValueError, UnicodeError, RecursionError) as exc:
                raise DoctrineResearchError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
            try:
                _assert_json_text_encodable(value)
            except (ValueError, UnicodeError, RecursionError) as exc:
                raise DoctrineResearchError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise DoctrineResearchError(f"JSONL row must be an object at {path}:{line_number}")
            rows.append(value)
    return rows


_INVALID_VALIDATION_ARTIFACT = object()


def _load_json_for_validation(path: Path, errors: List[str]) -> Any:
    """Load an artifact without allowing malformed bytes to escape validation."""
    try:
        return _load_json_strict(path)
    except (OSError, UnicodeError, ValueError, RecursionError):
        errors.append(f"invalid JSON artifact: {path.name}")
        return _INVALID_VALIDATION_ARTIFACT


def _read_jsonl_for_validation(path: Path, errors: List[str]) -> List[Dict[str, Any]]:
    """Read an artifact ledger and turn parser failures into QA errors."""
    try:
        return read_jsonl(path)
    except (DoctrineResearchError, OSError, UnicodeError, ValueError, RecursionError):
        errors.append(f"invalid JSONL artifact: {path.name}")
        return []


def _load_json_for_command(path: Path) -> Any:
    """Convert workspace parse failures into the CLI's controlled blocked state."""
    try:
        return _load_json_strict(path)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise DoctrineResearchError(f"invalid JSON artifact: {path.name}") from exc


def _read_jsonl_for_command(path: Path) -> List[Dict[str, Any]]:
    """Convert workspace JSONL failures into the CLI's controlled blocked state."""
    try:
        return read_jsonl(path)
    except (DoctrineResearchError, OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise DoctrineResearchError(f"invalid JSONL artifact: {path.name}") from exc


def _safe_text(value: Any) -> str:
    """Keep untrusted diagnostic values encodable without exposing raw control bytes."""
    return str(value).encode("utf-8", "backslashreplace").decode("utf-8")


def _write_preflight_failure(workspace: Path, error: DoctrineResearchError) -> None:
    """Invalidate a previously passing QA report when a command is blocked early."""
    write_json(
        workspace / "qa-report.json",
        {
            "schema_version": "doctrine-qa/1.0",
            "status": "fail",
            "errors": [_safe_text(error)],
            "warnings": [],
        },
    )


def validate_workspace(workspace: Path) -> Dict[str, Any]:
    required = (
        "request.snapshot.json",
        "route-decision.json",
        "norm-problem-profile.json",
        "provider-capabilities.snapshot.json",
        "provider-routing.json",
        "query-plan.json",
    )
    errors = []
    warnings = []
    for filename in required:
        if not (workspace / filename).exists():
            errors.append(f"missing required artifact: {filename}")
    if errors:
        return {"schema_version": "doctrine-qa/1.0", "status": "fail", "errors": errors, "warnings": warnings}
    snapshot = _load_json_for_validation(workspace / "request.snapshot.json", errors)
    if snapshot is _INVALID_VALIDATION_ARTIFACT:
        snapshot = {}
    elif not isinstance(snapshot, Mapping):
        errors.append("request.snapshot.json must be an object")
        snapshot = {}
    snapshot_matter = snapshot.get("matter_id")
    try:
        snapshot_hash = request_sha256(snapshot)
    except (UnicodeError, ValueError, RecursionError):
        errors.append("request.snapshot.json contains unsupported JSON values")
        snapshot_hash = ""
    capabilities = _load_json_for_validation(
        workspace / "provider-capabilities.snapshot.json", errors
    )
    if capabilities is not _INVALID_VALIDATION_ARTIFACT and not isinstance(capabilities, Mapping):
        errors.append("provider-capabilities.snapshot.json must be an object")
    observed_route = _load_json_for_validation(workspace / "route-decision.json", errors)
    if observed_route is _INVALID_VALIDATION_ARTIFACT:
        observed_route = None
    try:
        expected_route = require_bound_research_route(snapshot)
    except (DoctrineResearchError, TypeError, UnicodeError, ValueError, RecursionError) as exc:
        errors.append(f"invalid bound route: {exc}")
        expected_route = {}
    if observed_route != expected_route:
        errors.append("route decision artifact/hash mismatch")
    route_hash = expected_route.get("route_decision_hash")
    bound_artifacts: Dict[str, Mapping[str, Any]] = {}
    for filename in ("norm-problem-profile.json", "provider-routing.json", "query-plan.json"):
        artifact = _load_json_for_validation(workspace / filename, errors)
        if artifact is _INVALID_VALIDATION_ARTIFACT:
            continue
        if not isinstance(artifact, Mapping):
            errors.append(f"{filename} must be an object")
            continue
        bound_artifacts[filename] = artifact
        if artifact.get("matter_id") != snapshot_matter:
            errors.append(f"matter_id mismatch in {filename}")
        if artifact.get("request_sha256") != snapshot_hash:
            errors.append(f"request hash mismatch in {filename}")
        if artifact.get("route_decision_hash") != route_hash:
            errors.append(f"route decision hash mismatch in {filename}")
    query_plan = bound_artifacts.get("query-plan.json", {})
    try:
        expected_query_plan = build_query_plan(snapshot)
        expected_query_plan["request_sha256"] = snapshot_hash
    except (DoctrineResearchError, TypeError, UnicodeError, ValueError, RecursionError) as exc:
        errors.append(f"query plan cannot be rebuilt from request snapshot: {exc}")
        expected_query_plan = {}
    if expected_query_plan and query_plan != expected_query_plan:
        errors.append("query plan artifact/hash mismatch")
    query_rows = query_plan.get("queries", [])
    if not isinstance(query_rows, list) or not all(isinstance(row, Mapping) for row in query_rows):
        errors.append("query plan queries must be a list of objects")
        query_rows = []
    query_ids = [row.get("query_id") for row in query_rows]
    if not all(isinstance(query_id, str) and query_id for query_id in query_ids):
        errors.append("query_id must be a non-empty string")
    elif len(query_ids) != len(set(query_ids)):
        errors.append("duplicate query_id")
    if query_plan.get("legal_conclusions"):
        errors.append("query plan must not contain legal conclusions")
    routing_artifact = bound_artifacts.get("provider-routing.json", {})
    routing_decisions = routing_artifact.get("decisions", [])
    if not isinstance(routing_decisions, list) or not all(
        isinstance(row, Mapping) for row in routing_decisions
    ):
        errors.append("provider-routing.json decisions must be a list of objects")
        routing_decisions = []
    source_path = workspace / "source-ledger.jsonl"
    sources: List[Dict[str, Any]] = []
    if source_path.exists():
        sources = _read_jsonl_for_validation(source_path, errors)
        source_ids = []
        for row in sources:
            source_id = row.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                errors.append("source_id must be a non-empty string")
                continue
            source_ids.append(source_id)
        if len(source_ids) != len(set(source_ids)):
            errors.append("duplicate source_id")
        for row in sources:
            if row.get("promotion_status") != "candidate_only":
                errors.append(f"source promoted beyond candidate_only: {row.get('source_id')}")
            if row.get("verification_status") not in {"metadata_only", "abstract_checked"}:
                errors.append(f"network metadata has invalid verification status: {row.get('source_id')}")
    problem_path = workspace / "problem-candidates.json"
    if problem_path.exists():
        problems = _load_json_for_validation(problem_path, errors)
        if problems is _INVALID_VALIDATION_ARTIFACT:
            problems = {}
        elif not isinstance(problems, Mapping):
            errors.append("problem-candidates.json must be an object")
            problems = {}
        known = {row.get("source_id") for row in sources if isinstance(row.get("source_id"), str)}
        clusters = problems.get("clusters", [])
        if not isinstance(clusters, list) or not all(isinstance(cluster, Mapping) for cluster in clusters):
            errors.append("problem-candidates.json clusters must be a list of objects")
            clusters = []
        for cluster in clusters:
            source_ids = cluster.get("source_ids", [])
            if not isinstance(source_ids, list) or not all(
                isinstance(source_id, str) and source_id for source_id in source_ids
            ):
                errors.append("problem cluster source_ids must be a list of strings")
                continue
            unknown = set(source_ids) - known
            if unknown:
                errors.append(f"problem cluster references unknown sources: {sorted(unknown)}")
            if cluster.get("status") != "candidate_only":
                errors.append("problem cluster promoted beyond candidate_only")
        if problems.get("constitutional_hypotheses"):
            errors.append("discovery script must not emit constitutional hypotheses")
    search_marker_names = (
        "search-run-config.json",
        "search-log.jsonl",
        "coverage-report.json",
    )
    required_search_artifacts = search_marker_names + (
        "source-ledger.jsonl",
        "problem-candidates.json",
        "acquisition-queue.json",
    )
    present_search_markers = {
        filename for filename in search_marker_names if (workspace / filename).exists()
    }
    if present_search_markers:
        missing = sorted(
            filename for filename in required_search_artifacts if not (workspace / filename).exists()
        )
    else:
        missing = []
    if missing:
        errors.append(f"incomplete search artifact set; missing: {', '.join(missing)}")
    search_log_path = workspace / "search-log.jsonl"
    if search_log_path.exists():
        _read_jsonl_for_validation(search_log_path, errors)
    acquisition_path = workspace / "acquisition-queue.json"
    if acquisition_path.exists():
        acquisition = _load_json_for_validation(acquisition_path, errors)
        if acquisition is not _INVALID_VALIDATION_ARTIFACT and not isinstance(acquisition, Mapping):
            errors.append("acquisition-queue.json must be an object")
    coverage_path = workspace / "coverage-report.json"
    if coverage_path.exists():
        coverage = _load_json_for_validation(coverage_path, errors)
        if coverage is _INVALID_VALIDATION_ARTIFACT:
            coverage = None
        elif not isinstance(coverage, Mapping):
            errors.append("coverage-report.json must be an object")
            coverage = None
        if isinstance(coverage, Mapping):
            if coverage.get("matter_id") != snapshot_matter:
                errors.append("matter_id mismatch in coverage-report.json")
            if coverage.get("request_sha256") != snapshot_hash:
                errors.append("request hash mismatch in coverage-report.json")
            if coverage.get("coverage_complete") is not False:
                errors.append("federated discovery coverage_complete must remain false")
            if coverage.get("absence_claim_permitted") is not False:
                errors.append("absence_claim_permitted must remain false")
            run_config_path = workspace / "search-run-config.json"
            if not run_config_path.exists():
                errors.append("coverage exists without search-run-config.json")
            else:
                run_config = _load_json_for_validation(run_config_path, errors)
                if run_config is _INVALID_VALIDATION_ARTIFACT:
                    run_config = None
                elif not isinstance(run_config, Mapping):
                    errors.append("search-run-config.json must be an object")
                    run_config = None
                if isinstance(run_config, Mapping):
                    if run_config.get("request_sha256") != snapshot_hash:
                        errors.append("request hash mismatch in search-run-config.json")
                    if run_config.get("route_decision_hash") != route_hash:
                        errors.append("route decision hash mismatch in search-run-config.json")
                    if run_config.get("run_config_hash") != coverage.get("run_config_hash"):
                        errors.append("run config hash mismatch in coverage-report.json")
                    routed = []
                    for row in routing_decisions:
                        if not row.get("selected_for_automated_run"):
                            continue
                        provider = row.get("provider")
                        if not isinstance(provider, str) or not provider:
                            errors.append("provider-routing.json provider must be a non-empty string")
                            continue
                        routed.append(provider)
                    configured_values = run_config.get("selected_providers", [])
                    if not isinstance(configured_values, list) or not all(
                        isinstance(provider, str) and provider for provider in configured_values
                    ):
                        errors.append("search-run-config.json selected_providers must be a list of strings")
                        configured = []
                    else:
                        configured = sorted(configured_values)
                    status_values = coverage.get("provider_statuses", [])
                    if not isinstance(status_values, list) or not all(
                        isinstance(row, Mapping) for row in status_values
                    ):
                        errors.append("coverage-report.json provider_statuses must be a list of objects")
                        covered = []
                    else:
                        covered = []
                        for row in status_values:
                            provider = row.get("provider")
                            if not isinstance(provider, str) or not provider:
                                errors.append("coverage-report.json provider must be a non-empty string")
                                continue
                            covered.append(provider)
                    if sorted(routed) != configured or sorted(covered) != configured:
                        errors.append("provider set mismatch across routing, run config, and coverage")
    elif not present_search_markers:
        warnings.append("search artifacts are not present; plan-only workspace")
    return {
        "schema_version": "doctrine-qa/1.0",
        "status": "pass" if not errors else "fail",
        "errors": [_safe_text(error) for error in errors],
        "warnings": [_safe_text(warning) for warning in warnings],
    }


def run_validate(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    report = validate_workspace(workspace)
    write_json(workspace / "qa-report.json", report)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 2


def run_rerank(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    request = load_request(Path(args.request))
    try:
        ensure_workspace_identity(request, workspace)
        source_path = workspace / "source-ledger.jsonl"
        if not source_path.is_file():
            raise DoctrineResearchError("source-ledger.jsonl is required for rerank")
        coverage_path = workspace / "coverage-report.json"
        coverage = None
        if coverage_path.is_file():
            coverage = _load_json_for_command(coverage_path)
            if not isinstance(coverage, MutableMapping):
                raise DoctrineResearchError("coverage-report.json must be an object")
        taxonomy = load_json(TAXONOMY_PATH)
        records = _read_jsonl_for_command(source_path)
        if any(
            not isinstance(record.get("source_id"), str) or not record.get("source_id")
            for record in records
        ):
            raise DoctrineResearchError("source-ledger.jsonl source_id must be a non-empty string")
    except DoctrineResearchError as exc:
        _write_preflight_failure(workspace, exc)
        raise
    for record in records:
        enrich_record(record, request, taxonomy)
    records.sort(key=lambda row: (-row.get("reading_priority", {}).get("score", 0), row.get("source_id", "")))
    write_jsonl(source_path, records)
    write_json(workspace / "problem-candidates.json", problem_candidates(records, taxonomy))
    write_json(workspace / "acquisition-queue.json", acquisition_queue(records))
    if coverage is not None:
        coverage.update(
            {
                "high_lexical_priority_candidates": sum(1 for row in records if row.get("relevance_status") == "high_lexical_priority"),
                "medium_lexical_priority_candidates": sum(1 for row in records if row.get("relevance_status") == "medium_lexical_priority"),
                "weak_candidates": sum(1 for row in records if row.get("relevance_status") == "weak_candidate"),
            }
        )
        write_json(coverage_path, coverage)
    report = validate_workspace(workspace)
    write_json(workspace / "qa-report.json", report)
    print(
        json.dumps(
            {
                "status": "reranked" if report["status"] == "pass" else "reranked_with_qa_errors",
                "workspace": str(workspace.resolve()),
                "unique_candidates": len(records),
                "high_lexical_priority_candidates": sum(1 for row in records if row.get("relevance_status") == "high_lexical_priority"),
                "qa_status": report["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "pass" else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan and run bounded legal-doctrine discovery.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    route = subparsers.add_parser(
        "route",
        help="Select the safest doctrine-research mode before planning or search.",
    )
    route.add_argument("--request", required=True)
    route.set_defaults(func=run_route)

    plan = subparsers.add_parser("plan", help="Create deterministic query and provider-routing artifacts.")
    plan.add_argument("--request", required=True)
    plan.add_argument("--workspace", required=True)
    plan.add_argument("--providers", default="")
    plan.set_defaults(func=run_plan)

    search = subparsers.add_parser("search", help="Run selected documented API adapters.")
    search.add_argument("--request", required=True)
    search.add_argument("--workspace", required=True)
    search.add_argument("--providers", default="openalex,crossref")
    search.add_argument("--max-queries", type=int, default=12)
    search.add_argument("--max-results", type=int, default=10)
    search.add_argument("--timeout", type=float, default=20.0)
    search.add_argument("--request-delay", type=float, default=0.15)
    search.add_argument("--offline-fixtures")
    search.add_argument(
        "--approved-query-plan-hash",
        help="Required for case_scoped and hypothesis_verification after human review of query-plan.json.",
    )
    search.set_defaults(func=run_search)

    validate = subparsers.add_parser("validate", help="Validate a plan or completed bounded search workspace.")
    validate.add_argument("--workspace", required=True)
    validate.set_defaults(func=run_validate)

    rerank = subparsers.add_parser("rerank", help="Reapply the current legal-topic heuristic without network calls.")
    rerank.add_argument("--request", required=True)
    rerank.add_argument("--workspace", required=True)
    rerank.set_defaults(func=run_rerank)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "max_queries") and args.max_queries < 1:
        parser.error("--max-queries must be positive")
    if hasattr(args, "max_results") and not 1 <= args.max_results <= 100:
        parser.error("--max-results must be between 1 and 100")
    if hasattr(args, "request_delay") and args.request_delay < 0:
        parser.error("--request-delay must not be negative")
    try:
        return int(args.func(args))
    except DoctrineResearchError as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
