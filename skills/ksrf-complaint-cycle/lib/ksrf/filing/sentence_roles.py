"""Fail-closed sentence-role integrity for complaint filing releases.

The host owns the authoritative complete sentence registry.  Callers provide
only matter/draft identity to that boundary; current sentence bindings are
derived locally and compared with the detached host snapshot.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import re
from typing import Any, Mapping, Protocol, Sequence

from .storage import canonical_json_bytes


CANONICAL_SENTENCE_ROLES = frozenset(
    {
        "narrative",
        "fact",
        "court_reasoning",
        "norm_text",
        "legal_holding",
        "application_finding",
        "practice_claim",
        "adverse_authority",
        "requested_remedy",
    }
)

FILING_SIGNIFICANT_SENTENCE_ROLES = frozenset(
    CANONICAL_SENTENCE_ROLES - {"narrative"}
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SENTENCE_ID_RE = re.compile(r"^sent-[0-9a-f]{16}$")
_RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)

_BINDING_FIELDS = frozenset(
    {"ordinal", "sentence_id", "section_code", "text_sha256", "role"}
)
_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "matter_id",
        "draft_id",
        "bindings",
        "binding_index_sha256",
        "authority_revision_id",
        "checked_at",
    }
)
_RESOLUTION_FIELDS = _RECEIPT_FIELDS | {"status"}


class SentenceRoleIndexAuthority(Protocol):
    """Host boundary for a pre-existing complete draft sentence registry."""

    def resolve_sentence_role_index(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any] | None: ...


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _exact_identifier(value: Any) -> bool:
    if type(value) is not str or not value:
        return False
    return value == " ".join(value.split())


def _is_rfc3339(value: Any) -> bool:
    if type(value) is not str or not _RFC3339_RE.fullmatch(value):
        return False
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _exact_mapping_keys(
    value: Mapping[Any, Any], expected: frozenset[str], *, label: str
) -> list[str]:
    if any(type(key) is not str for key in value):
        return [f"{label}_mapping_key_invalid"]
    actual = set(value)
    errors: list[str] = []
    for key in sorted(expected - actual):
        errors.append(f"{label}_field_missing:{key}")
    for key in sorted(actual - expected):
        errors.append(f"{label}_field_unexpected:{key}")
    return errors


def _text_sha256(text: str) -> str:
    try:
        encoded = text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("sentence_role_index_text_invalid") from exc
    return sha256(encoded).hexdigest()


def sentence_role_binding(
    *, ordinal: int, sentence_id: str, section_code: str, text: str, role: str
) -> dict[str, Any]:
    """Bind one sentence to its exact UTF-8 text digest and canonical role."""

    errors: list[str] = []
    if type(ordinal) is not int or ordinal <= 0:
        errors.append("sentence_role_index_ordinal_invalid")
    if type(sentence_id) is not str or not _SENTENCE_ID_RE.fullmatch(sentence_id):
        errors.append("sentence_role_index_sentence_id_invalid")
    if type(section_code) is not str or not section_code:
        errors.append("sentence_role_index_section_code_invalid")
    if type(text) is not str or not text:
        errors.append("sentence_role_index_text_invalid")
    if type(role) is not str or role not in CANONICAL_SENTENCE_ROLES:
        errors.append(f"sentence_role_index_role_unknown:{sentence_id}:{role!r}")
    if errors:
        raise ValueError(", ".join(_unique(errors)))
    return {
        "ordinal": ordinal,
        "sentence_id": sentence_id,
        "section_code": section_code,
        "text_sha256": _text_sha256(text),
        "role": role,
    }


def build_sentence_role_index_request(
    *, matter_id: str, draft_id: str
) -> dict[str, str]:
    """Build the identity-only lookup passed to the host registry."""

    errors: list[str] = []
    if not _exact_identifier(matter_id):
        errors.append("sentence_role_index_matter_id_invalid")
    if not _exact_identifier(draft_id):
        errors.append("sentence_role_index_draft_id_invalid")
    if errors:
        raise ValueError(", ".join(errors))
    return {
        "schema_version": "1.0.0",
        "matter_id": matter_id,
        "draft_id": draft_id,
    }


def _canonical_bindings(
    value: Any,
    *,
    label: str,
    require_canonical_order: bool,
    require_json_types: bool = False,
) -> tuple[list[dict[str, Any]], list[str]]:
    if require_json_types and type(value) is not list:
        return [], [f"{label}_invalid"]
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return [], [f"{label}_invalid"]

    bindings: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_sentence_ids: set[str] = set()
    seen_ordinals: set[int] = set()
    for ordinal, raw in enumerate(value, start=1):
        if require_json_types and type(raw) is not dict:
            errors.append(f"{label}_entry_invalid:{ordinal}")
            continue
        if not isinstance(raw, Mapping):
            errors.append(f"{label}_entry_invalid:{ordinal}")
            continue

        entry_errors = _exact_mapping_keys(
            raw, _BINDING_FIELDS, label=f"{label}:{ordinal}"
        )
        binding_ordinal = raw.get("ordinal")
        sentence_id = raw.get("sentence_id")
        section_code = raw.get("section_code")
        text_digest = raw.get("text_sha256")
        role = raw.get("role")

        if type(binding_ordinal) is not int or binding_ordinal <= 0:
            entry_errors.append(f"{label}_ordinal_invalid:{ordinal}")
        elif binding_ordinal in seen_ordinals:
            entry_errors.append(f"{label}_ordinal_duplicate:{binding_ordinal}")
        else:
            seen_ordinals.add(binding_ordinal)
        if type(sentence_id) is not str or not _SENTENCE_ID_RE.fullmatch(sentence_id):
            entry_errors.append(f"{label}_sentence_id_invalid:{ordinal}")
        elif sentence_id in seen_sentence_ids:
            entry_errors.append(f"{label}_duplicate:{sentence_id}")
        else:
            seen_sentence_ids.add(sentence_id)
        if type(section_code) is not str or not section_code:
            entry_errors.append(f"{label}_section_code_invalid:{ordinal}")
        if type(text_digest) is not str or not _SHA256_RE.fullmatch(text_digest):
            entry_errors.append(f"{label}_text_sha256_invalid:{ordinal}")
        if type(role) is not str or role not in CANONICAL_SENTENCE_ROLES:
            entry_errors.append(
                f"sentence_role_index_role_unknown:{sentence_id}:{role!r}"
            )

        if entry_errors:
            errors.extend(entry_errors)
            continue
        assert type(binding_ordinal) is int
        assert type(sentence_id) is str
        assert type(section_code) is str
        assert type(text_digest) is str
        assert type(role) is str
        bindings.append(
            {
                "ordinal": binding_ordinal,
                "sentence_id": sentence_id,
                "section_code": section_code,
                "text_sha256": text_digest,
                "role": role,
            }
        )

    canonical = sorted(bindings, key=lambda item: item["ordinal"])
    if [item["ordinal"] for item in canonical] != list(
        range(1, len(canonical) + 1)
    ):
        errors.append(f"{label}_ordinals_not_contiguous")
    if require_canonical_order and bindings != canonical:
        errors.append(f"{label}_not_canonical")
    return canonical, _unique(errors)


def _index_basis(
    *, matter_id: str, draft_id: str, bindings: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": [dict(binding) for binding in bindings],
    }


def _index_sha256(
    *, matter_id: str, draft_id: str, bindings: Sequence[Mapping[str, Any]]
) -> str:
    return sha256(
        canonical_json_bytes(
            _index_basis(
                matter_id=matter_id,
                draft_id=draft_id,
                bindings=bindings,
            )
        )
    ).hexdigest()


def build_sentence_role_index_resolution(
    *,
    matter_id: str,
    draft_id: str,
    bindings: Sequence[Mapping[str, Any]],
    authority_revision_id: str,
    checked_at: str,
) -> dict[str, Any]:
    """Build a canonical authoritative complete role-index resolution."""

    canonical, errors = _canonical_bindings(
        bindings,
        label="sentence_role_index_bindings",
        require_canonical_order=False,
    )
    if not _exact_identifier(matter_id):
        errors.append("sentence_role_index_matter_id_invalid")
    if not _exact_identifier(draft_id):
        errors.append("sentence_role_index_draft_id_invalid")
    if not _exact_identifier(authority_revision_id):
        errors.append("sentence_role_index_authority_revision_id_invalid")
    if not _is_rfc3339(checked_at):
        errors.append("sentence_role_index_checked_at_invalid")
    if errors:
        raise ValueError(", ".join(_unique(errors)))

    return {
        "schema_version": "1.0.0",
        "status": "verified",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": deepcopy(canonical),
        "binding_index_sha256": _index_sha256(
            matter_id=matter_id,
            draft_id=draft_id,
            bindings=canonical,
        ),
        "authority_revision_id": authority_revision_id,
        "checked_at": checked_at,
    }


def _validate_receipt_snapshot(
    snapshot: Mapping[Any, Any],
    *,
    matter_id: str,
    draft_id: str,
    expected_bindings: Sequence[Mapping[str, Any]],
    include_status: bool,
) -> tuple[list[str], list[dict[str, str]], str]:
    expected_fields = _RESOLUTION_FIELDS if include_status else _RECEIPT_FIELDS
    container_label = (
        "sentence_role_index_resolution"
        if include_status
        else "sentence_role_index_receipt"
    )
    errors = _exact_mapping_keys(snapshot, expected_fields, label=container_label)

    if type(snapshot.get("schema_version")) is not str or snapshot.get(
        "schema_version"
    ) != "1.0.0":
        errors.append("sentence_role_index_schema_invalid")
    if include_status and (
        type(snapshot.get("status")) is not str
        or snapshot.get("status") != "verified"
    ):
        errors.append("sentence_role_index_not_verified")
    if type(snapshot.get("matter_id")) is not str or snapshot.get(
        "matter_id"
    ) != matter_id:
        errors.append("sentence_role_index_matter_id_mismatch")
    if type(snapshot.get("draft_id")) is not str or snapshot.get(
        "draft_id"
    ) != draft_id:
        errors.append("sentence_role_index_draft_id_mismatch")

    authoritative, binding_errors = _canonical_bindings(
        snapshot.get("bindings"),
        label="sentence_role_index_bindings",
        require_canonical_order=True,
        require_json_types=True,
    )
    errors.extend(binding_errors)

    expected, expected_errors = _canonical_bindings(
        expected_bindings,
        label="sentence_role_index_expected",
        require_canonical_order=False,
    )
    errors.extend(expected_errors)
    if authoritative != expected:
        errors.append("sentence_role_index_set_mismatch")

    computed_sha = _index_sha256(
        matter_id=matter_id,
        draft_id=draft_id,
        bindings=authoritative,
    )
    stored_sha = snapshot.get("binding_index_sha256")
    if type(stored_sha) is not str or not _SHA256_RE.fullmatch(stored_sha):
        errors.append("sentence_role_index_sha256_invalid")
    elif stored_sha != computed_sha:
        errors.append("sentence_role_index_sha256_mismatch")
    if not _exact_identifier(snapshot.get("authority_revision_id")):
        errors.append("sentence_role_index_authority_revision_id_invalid")
    if not _is_rfc3339(snapshot.get("checked_at")):
        errors.append("sentence_role_index_checked_at_invalid")
    return _unique(errors), authoritative, computed_sha


def validate_sentence_role_index_receipt(
    receipt: Any,
    *,
    matter_id: str,
    draft_id: str,
    expected_bindings: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    """Validate a persisted receipt without conferring current host authority."""

    errors: list[str] = []
    if not _exact_identifier(matter_id):
        errors.append("sentence_role_index_matter_id_invalid")
    if not _exact_identifier(draft_id):
        errors.append("sentence_role_index_draft_id_invalid")
    if errors:
        return tuple(errors)
    if not isinstance(receipt, Mapping):
        return ("sentence_role_index_receipt_missing",)
    try:
        snapshot = deepcopy(dict(receipt))
    except Exception:
        return ("sentence_role_index_receipt_snapshot_failed",)
    receipt_errors, _bindings, _digest = _validate_receipt_snapshot(
        snapshot,
        matter_id=matter_id,
        draft_id=draft_id,
        expected_bindings=expected_bindings,
        include_status=False,
    )
    return tuple(receipt_errors)


def resolve_sentence_role_index(
    *,
    matter_id: str,
    draft_id: str,
    expected_bindings: Sequence[Mapping[str, Any]],
    authority: SentenceRoleIndexAuthority | Any | None,
) -> tuple[tuple[str, ...], dict[str, Any] | None]:
    """Resolve and compare the host-owned complete sentence-role registry."""

    errors: list[str] = []
    if not _exact_identifier(matter_id):
        errors.append("sentence_role_index_matter_id_invalid")
    if not _exact_identifier(draft_id):
        errors.append("sentence_role_index_draft_id_invalid")
    expected, expected_errors = _canonical_bindings(
        expected_bindings,
        label="sentence_role_index_expected",
        require_canonical_order=False,
    )
    errors.extend(expected_errors)
    if errors:
        return tuple(_unique(errors)), None

    request = build_sentence_role_index_request(
        matter_id=matter_id,
        draft_id=draft_id,
    )
    resolver = getattr(authority, "resolve_sentence_role_index", None)
    if authority is None or not callable(resolver):
        return ("sentence_role_index_authority_required",), None

    adapter_request = deepcopy(request)
    try:
        raw_resolution = resolver(adapter_request)
    except Exception:
        return ("sentence_role_index_authority_error",), None
    if adapter_request != request:
        return ("sentence_role_index_request_mutated",), None
    if not isinstance(raw_resolution, Mapping):
        return ("sentence_role_index_resolution_missing",), None
    try:
        resolution = deepcopy(dict(raw_resolution))
    except Exception:
        return ("sentence_role_index_resolution_snapshot_failed",), None

    errors, authoritative, computed_sha = _validate_receipt_snapshot(
        resolution,
        matter_id=matter_id,
        draft_id=draft_id,
        expected_bindings=expected,
        include_status=True,
    )
    if errors:
        return tuple(errors), None

    return (), {
        "schema_version": "1.0.0",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": deepcopy(authoritative),
        "binding_index_sha256": computed_sha,
        "authority_revision_id": resolution["authority_revision_id"],
        "checked_at": resolution["checked_at"],
    }


__all__ = [
    "CANONICAL_SENTENCE_ROLES",
    "FILING_SIGNIFICANT_SENTENCE_ROLES",
    "SentenceRoleIndexAuthority",
    "build_sentence_role_index_request",
    "build_sentence_role_index_resolution",
    "resolve_sentence_role_index",
    "sentence_role_binding",
    "validate_sentence_role_index_receipt",
]
