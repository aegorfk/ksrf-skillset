"""Host-attested source binding for ``legal_holding`` complaint sentences.

The module deliberately treats a complaint sentence as a lookup request, not
as evidence authority.  A host adapter must return the immutable native
``SourceEvidence v1`` records, freshly recomputed filing-authority results, a
separate claim/scope registry projection, and an exact human-review receipt.
Every returned value is revalidated locally before a compact immutable receipt
is emitted.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import re
from typing import Any, Mapping, Protocol, Sequence

from .storage import canonical_json_bytes, stable_id


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SENTENCE_ID_RE = re.compile(r"^sent-[0-9a-f]{16}$")
_SOURCE_EVIDENCE_ID_RE = re.compile(r"^source-evidence:sha256:[0-9a-f]{64}$")
_SOURCE_VERIFICATION_ID_RE = re.compile(
    r"^source-verification:sha256:[0-9a-f]{64}$"
)
_SOURCE_IDENTITY_ID_RE = re.compile(r"^source-identity:sha256:[0-9a-f]{64}$")
_TRUSTED_APPROVAL_ID_RE = re.compile(r"^trusted-approval:sha256:[0-9a-f]{64}$")
_RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)

_SOURCE_EVIDENCE_REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "observation_id",
        "source_id",
        "issuer",
        "authority_class",
        "origin_url",
        "acquisition_transport",
        "retrieved_at",
        "content_type",
        "raw_object",
        "extracted_object",
        "identity_checks",
        "derived_identity_checks",
        "identity_fingerprint",
        "identity_verification_mode",
        "identity_verification_blockers",
        "verified_official_locator",
        "human_identity_reviewer",
        "approval_ids",
        "trusted_approval_id",
        "transform_chain",
        "filing_authority_state",
        "filing_ready",
        "validation_state",
        "supersedes_evidence_id",
        "evidence_id",
        "verification_revision_id",
    }
)
_SOURCE_EVIDENCE_ALLOWED_FIELDS = _SOURCE_EVIDENCE_REQUIRED_FIELDS | frozenset(
    {"discovery_transport", "redirect_chain"}
)
_CURRENT_AUTHORITY_FIELDS = frozenset(
    {"evidence_id", "filing_ready", "identity_verification_mode", "blockers"}
)
_CLAIM_SCOPE_FIELDS = frozenset(
    {
        "schema_version",
        "evidence_id",
        "source_id",
        "claim_id",
        "authority_role",
        "verified_official_locator",
        "pinpoint",
        "raw_sha256",
        "verification_revision_id",
        "current_evidence_id",
        "freshness_state",
        "scope_revision_id",
        "checked_at",
        "maximum_supported_inference",
    }
)
_SCOPE_GATE_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "passed",
        "sentence_id",
        "section_code",
        "holding_binding_sha256",
        "claim_id",
        "evidence_ids",
        "maximum_supported_inference",
        "source_ids",
        "source_evidence_content_fingerprints",
        "claim_scope_content_fingerprints",
        "authority_revision_id",
        "checked_at",
        "approval_request",
        "trusted_approval_id",
    }
)
_RESOLUTION_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "holding_binding_sha256",
        "source_evidence",
        "current_authority",
        "claim_scope",
        "scope_gate_receipt",
    }
)


class HoldingEvidenceBindingAuthority(Protocol):
    """Host boundary for current evidence, scope, and draft-registry state."""

    def resolve_holding_evidence_binding(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any] | None: ...

    def resolve_holding_evidence_binding_index(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any] | None: ...


def _canonical_identifier(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = " ".join(value.split())
    return value if value and value == normalized else ""


def _exact_nonempty_text(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        return ""
    return value


def _is_rfc3339_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not _RFC3339_RE.fullmatch(value):
        return False
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _unique(errors: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(errors))


def _exact_mapping_keys(
    value: Mapping[str, Any], expected: frozenset[str], *, label: str
) -> list[str]:
    if any(not isinstance(key, str) for key in value):
        return [f"{label}_mapping_key_invalid"]
    actual = set(value)
    errors: list[str] = []
    for key in sorted(expected - actual):
        errors.append(f"{label}_field_missing:{key}")
    for key in sorted(actual - expected):
        errors.append(f"{label}_field_unexpected:{key}")
    return errors


def _exact_identifier_list(
    value: Any,
    *,
    label: str,
    pattern: re.Pattern[str] | None = None,
    allow_empty: bool = False,
) -> tuple[list[str], list[str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return [], [f"{label}_invalid"]
    values: list[str] = []
    errors: list[str] = []
    seen: set[str] = set()
    if not value and not allow_empty:
        errors.append(f"{label}_empty")
    for ordinal, raw in enumerate(value, start=1):
        identifier = _canonical_identifier(raw)
        if not identifier or (pattern is not None and not pattern.fullmatch(identifier)):
            errors.append(f"{label}_identifier_invalid:{ordinal}")
            continue
        if identifier in seen:
            errors.append(f"{label}_duplicate:{identifier}")
            continue
        seen.add(identifier)
        values.append(identifier)
    return values, errors


def build_holding_binding_request(
    *,
    matter_id: str,
    draft_id: str,
    sentence_id: str,
    section_code: str,
    sentence_text: str,
    claim_id: str,
    evidence_ids: Sequence[str],
    maximum_supported_inference: str,
) -> dict[str, Any]:
    """Build the deterministic exact-byte request for one legal holding."""

    basis = {
        "schema_version": "1.0.0",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "sentence_id": sentence_id,
        "section_code": section_code,
        "sentence_text": sentence_text,
        "sentence_text_sha256": sha256(sentence_text.encode("utf-8")).hexdigest(),
        "claim_id": claim_id,
        "evidence_ids": sorted(evidence_ids),
        "maximum_supported_inference": maximum_supported_inference,
    }
    return {
        **basis,
        "holding_binding_sha256": sha256(canonical_json_bytes(basis)).hexdigest(),
    }


def build_holding_binding_index_request(
    *, matter_id: str, draft_id: str
) -> dict[str, Any]:
    """Build the narrow lookup for the host-owned complete holding index."""

    return {
        "schema_version": "1.0.0",
        "matter_id": matter_id,
        "draft_id": draft_id,
    }


def _canonical_holding_request(
    request: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    expected_fields = frozenset(
        {
            "schema_version",
            "matter_id",
            "draft_id",
            "sentence_id",
            "section_code",
            "sentence_text",
            "sentence_text_sha256",
            "claim_id",
            "evidence_ids",
            "maximum_supported_inference",
            "holding_binding_sha256",
        }
    )
    errors = _exact_mapping_keys(
        request, expected_fields, label="holding_binding_request"
    )
    if request.get("schema_version") != "1.0.0":
        errors.append("holding_binding_request_schema_invalid")
    for field in ("matter_id", "draft_id", "claim_id", "section_code"):
        if not _canonical_identifier(request.get(field)):
            errors.append(f"holding_binding_request_identifier_invalid:{field}")
    sentence_id = request.get("sentence_id")
    if not isinstance(sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(sentence_id):
        errors.append("holding_binding_request_sentence_id_invalid")
    if not _exact_nonempty_text(request.get("sentence_text")):
        errors.append("holding_binding_request_sentence_text_invalid")
    if not _exact_nonempty_text(request.get("maximum_supported_inference")):
        errors.append("holding_binding_request_inference_invalid")
    evidence_ids, evidence_errors = _exact_identifier_list(
        request.get("evidence_ids"),
        label="holding_binding_request_evidence_ids",
        pattern=_SOURCE_EVIDENCE_ID_RE,
    )
    errors.extend(evidence_errors)
    if errors:
        return None, tuple(_unique(errors))
    rebuilt = build_holding_binding_request(
        matter_id=request["matter_id"],
        draft_id=request["draft_id"],
        sentence_id=request["sentence_id"],
        section_code=request["section_code"],
        sentence_text=request["sentence_text"],
        claim_id=request["claim_id"],
        evidence_ids=evidence_ids,
        maximum_supported_inference=request["maximum_supported_inference"],
    )
    if dict(request) != rebuilt:
        return None, ("holding_binding_request_fingerprint_mismatch",)
    return rebuilt, ()


def _object_record_errors(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, Mapping):
        return [f"{label}_invalid"]
    errors = _exact_mapping_keys(
        value, frozenset({"sha256", "size", "object_path"}), label=label
    )
    sha_value = value.get("sha256")
    if not isinstance(sha_value, str) or not _SHA256_RE.fullmatch(sha_value):
        errors.append(f"{label}_sha256_invalid")
    size = value.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        errors.append(f"{label}_size_invalid")
    if not _exact_nonempty_text(value.get("object_path")):
        errors.append(f"{label}_object_path_invalid")
    return errors


def _mapping_list_errors(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return [f"{label}_invalid"]
    errors: list[str] = []
    for ordinal, item in enumerate(value, start=1):
        if not isinstance(item, Mapping) or any(
            not isinstance(key, str) for key in item
        ):
            errors.append(f"{label}_entry_invalid:{ordinal}")
    return errors


def _optional_string_errors(value: Any, *, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, str):
        return [f"{label}_invalid"]
    return []


def _source_evidence_errors(
    raw: Any, *, ordinal: int
) -> tuple[str, list[str]]:
    prefix = f"holding_source_evidence:{ordinal}"
    if not isinstance(raw, Mapping):
        return "", [f"{prefix}_invalid"]
    errors = _exact_mapping_keys(raw, _SOURCE_EVIDENCE_ALLOWED_FIELDS, label=prefix)
    # Optional native fields may be absent; only the schema-required subset is mandatory.
    errors = [
        error
        for error in errors
        if not (
            error.endswith("field_missing:discovery_transport")
            or error.endswith("field_missing:redirect_chain")
        )
    ]
    for field in sorted(_SOURCE_EVIDENCE_REQUIRED_FIELDS - set(raw)):
        marker = f"{prefix}_field_missing:{field}"
        if marker not in errors:
            errors.append(marker)

    evidence_id = raw.get("evidence_id")
    if not isinstance(evidence_id, str) or not _SOURCE_EVIDENCE_ID_RE.fullmatch(
        evidence_id
    ):
        errors.append(f"{prefix}_evidence_id_invalid")
        evidence_id = ""
    if raw.get("schema_version") != "1.0.0":
        errors.append(f"{prefix}_schema_invalid")
    for field in (
        "observation_id",
        "source_id",
        "origin_url",
        "acquisition_transport",
        "retrieved_at",
    ):
        if not _canonical_identifier(raw.get(field)):
            errors.append(f"{prefix}_{field}_invalid")
    if raw.get("authority_class") not in {
        "official_primary",
        "official_derivative",
        "discovery_only",
        "user_supplied_unverified",
    }:
        errors.append(f"{prefix}_authority_class_invalid")
    elif raw.get("authority_class") not in {
        "official_primary",
        "official_derivative",
    }:
        errors.append(f"{prefix}_authority_class_not_official")
    for field in (
        "issuer",
        "content_type",
        "human_identity_reviewer",
        "discovery_transport",
    ):
        if field in raw:
            errors.extend(
                _optional_string_errors(raw.get(field), label=f"{prefix}_{field}")
            )
    errors.extend(_object_record_errors(raw.get("raw_object"), label=f"{prefix}_raw"))
    extracted = raw.get("extracted_object")
    if extracted is not None:
        errors.extend(_object_record_errors(extracted, label=f"{prefix}_extracted"))
    errors.extend(_mapping_list_errors(raw.get("identity_checks"), label=f"{prefix}_identity_checks"))
    errors.extend(
        _mapping_list_errors(
            raw.get("derived_identity_checks"),
            label=f"{prefix}_derived_identity_checks",
        )
    )
    errors.extend(
        _mapping_list_errors(raw.get("transform_chain"), label=f"{prefix}_transform_chain")
    )
    identity_fingerprint = raw.get("identity_fingerprint")
    if not isinstance(identity_fingerprint, str) or not _SOURCE_IDENTITY_ID_RE.fullmatch(
        identity_fingerprint
    ):
        errors.append(f"{prefix}_identity_fingerprint_invalid")
    mode = raw.get("identity_verification_mode")
    if mode not in {"trusted_derived", "trusted_approval", "unverified"}:
        errors.append(f"{prefix}_identity_verification_mode_invalid")
    elif mode == "unverified":
        errors.append(f"{prefix}_identity_verification_mode_not_trusted")
    blockers, blocker_errors = _exact_identifier_list(
        raw.get("identity_verification_blockers"),
        label=f"{prefix}_identity_verification_blockers",
        allow_empty=True,
    )
    errors.extend(blocker_errors)
    if blockers and raw.get("filing_ready") is True:
        errors.append(f"{prefix}_identity_blockers_present")
    locator = raw.get("verified_official_locator")
    if not _canonical_identifier(locator):
        errors.append(f"{prefix}_verified_official_locator_invalid")
    approval_ids, approval_errors = _exact_identifier_list(
        raw.get("approval_ids"),
        label=f"{prefix}_approval_ids",
        pattern=_TRUSTED_APPROVAL_ID_RE,
        allow_empty=True,
    )
    errors.extend(approval_errors)
    trusted_approval_id = raw.get("trusted_approval_id")
    if trusted_approval_id is not None and (
        not isinstance(trusted_approval_id, str)
        or not _TRUSTED_APPROVAL_ID_RE.fullmatch(trusted_approval_id)
    ):
        errors.append(f"{prefix}_trusted_approval_id_invalid")
    if trusted_approval_id is not None and trusted_approval_id not in approval_ids:
        errors.append(f"{prefix}_trusted_approval_id_not_listed")
    if raw.get("filing_authority_state") != "verified_official":
        errors.append(f"{prefix}_filing_authority_state_invalid")
    if not isinstance(raw.get("filing_ready"), bool) or raw.get("filing_ready") is not True:
        errors.append(f"{prefix}_filing_ready_invalid")
    if raw.get("validation_state") != "verified":
        errors.append(f"{prefix}_validation_state_invalid")
    supersedes = raw.get("supersedes_evidence_id")
    if supersedes is not None and (
        not isinstance(supersedes, str)
        or not _SOURCE_EVIDENCE_ID_RE.fullmatch(supersedes)
    ):
        errors.append(f"{prefix}_supersedes_evidence_id_invalid")
    revision_id = raw.get("verification_revision_id")
    if not isinstance(revision_id, str) or not _SOURCE_VERIFICATION_ID_RE.fullmatch(
        revision_id
    ):
        errors.append(f"{prefix}_verification_revision_id_invalid")
    redirect_chain = raw.get("redirect_chain")
    if redirect_chain is not None:
        _, redirect_errors = _exact_identifier_list(
            redirect_chain,
            label=f"{prefix}_redirect_chain",
            allow_empty=True,
        )
        errors.extend(redirect_errors)
    try:
        canonical_json_bytes(dict(raw))
    except (TypeError, ValueError):
        errors.append(f"{prefix}_not_canonical_json")
    return evidence_id, _unique(errors)


def source_evidence_content_fingerprint(evidence: Mapping[str, Any]) -> str:
    """Fingerprint every native SourceEvidence field without adding claim data."""

    return stable_id("source-evidence-content", dict(evidence))


def holding_claim_scope_content_fingerprint(scope: Mapping[str, Any]) -> str:
    """Fingerprint one independently stored claim/scope registry record."""

    return stable_id("holding-claim-scope-content", dict(scope))


def build_holding_claim_scope(
    *,
    evidence: Mapping[str, Any],
    claim_id: str,
    pinpoint: str,
    maximum_supported_inference: str,
    checked_at: str,
    scope_revision_id: str | None = None,
    authority_role: str = "ksrf_legal_holding",
) -> dict[str, Any]:
    """Build a deterministic host claim/scope record for fixtures and adapters."""

    raw_object = evidence.get("raw_object")
    raw_sha256 = raw_object.get("sha256") if isinstance(raw_object, Mapping) else ""
    basis = {
        "schema_version": "1.0.0",
        "evidence_id": evidence.get("evidence_id"),
        "source_id": evidence.get("source_id"),
        "claim_id": claim_id,
        "authority_role": authority_role,
        "verified_official_locator": evidence.get("verified_official_locator"),
        "pinpoint": pinpoint,
        "raw_sha256": raw_sha256,
        "verification_revision_id": evidence.get("verification_revision_id"),
        "current_evidence_id": evidence.get("evidence_id"),
        "freshness_state": "current",
        "checked_at": checked_at,
        "maximum_supported_inference": maximum_supported_inference,
    }
    return {
        **basis,
        "scope_revision_id": scope_revision_id
        if scope_revision_id is not None
        else stable_id("holding-scope-revision", basis),
    }


def build_holding_scope_approval_request(
    *,
    request: Mapping[str, Any],
    source_evidence: Sequence[Mapping[str, Any]],
    claim_scope: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Reconstruct the complete review subject for one holding line."""

    source_by_id = {
        item["evidence_id"]: item
        for item in sorted(source_evidence, key=lambda entry: entry["evidence_id"])
    }
    scope_by_id = {
        item["evidence_id"]: item
        for item in sorted(claim_scope, key=lambda entry: entry["evidence_id"])
    }
    evidence_ids = list(request.get("evidence_ids") or ())
    bindings = {
        "matter_id": request.get("matter_id"),
        "draft_id": request.get("draft_id"),
        "sentence_id": request.get("sentence_id"),
        "section_code": request.get("section_code"),
        "holding_binding_sha256": request.get("holding_binding_sha256"),
        "claim_id": request.get("claim_id"),
        "evidence_ids": evidence_ids,
        "maximum_supported_inference": request.get("maximum_supported_inference"),
        "source_ids": {
            evidence_id: source_by_id[evidence_id].get("source_id")
            for evidence_id in evidence_ids
        },
        "source_evidence_content_fingerprints": {
            evidence_id: source_evidence_content_fingerprint(source_by_id[evidence_id])
            for evidence_id in evidence_ids
        },
        "claim_scope_content_fingerprints": {
            evidence_id: holding_claim_scope_content_fingerprint(scope_by_id[evidence_id])
            for evidence_id in evidence_ids
        },
    }
    return {
        "purpose": "legal_holding",
        "subject_type": "legal_holding_sentence_evidence",
        "subject_id": request.get("sentence_id"),
        "fingerprint": stable_id("holding-scope-review", bindings),
        "bindings": bindings,
    }


def build_holding_binding_resolution(
    *,
    request: Mapping[str, Any],
    source_evidence: Sequence[Mapping[str, Any]],
    current_authority: Sequence[Mapping[str, Any]],
    claim_scope: Sequence[Mapping[str, Any]],
    trusted_approval_id: str,
    authority_revision_id: str,
    checked_at: str,
) -> dict[str, Any]:
    """Build one canonical positive host resolution (primarily for fixtures)."""

    sources = sorted((deepcopy(dict(item)) for item in source_evidence), key=lambda item: item["evidence_id"])
    authority_results = sorted(
        (deepcopy(dict(item)) for item in current_authority),
        key=lambda item: item["evidence_id"],
    )
    scopes = sorted((deepcopy(dict(item)) for item in claim_scope), key=lambda item: item["evidence_id"])
    approval_request = build_holding_scope_approval_request(
        request=request,
        source_evidence=sources,
        claim_scope=scopes,
    )
    approval_bindings = approval_request["bindings"]
    return {
        "schema_version": "1.0.0",
        "status": "verified",
        "holding_binding_sha256": request.get("holding_binding_sha256"),
        "source_evidence": sources,
        "current_authority": authority_results,
        "claim_scope": scopes,
        "scope_gate_receipt": {
            "schema_version": "1.0.0",
            "passed": True,
            "sentence_id": request.get("sentence_id"),
            "section_code": request.get("section_code"),
            "holding_binding_sha256": request.get("holding_binding_sha256"),
            "claim_id": request.get("claim_id"),
            "evidence_ids": list(request.get("evidence_ids") or ()),
            "maximum_supported_inference": request.get(
                "maximum_supported_inference"
            ),
            "source_ids": deepcopy(approval_bindings["source_ids"]),
            "source_evidence_content_fingerprints": deepcopy(
                approval_bindings["source_evidence_content_fingerprints"]
            ),
            "claim_scope_content_fingerprints": deepcopy(
                approval_bindings["claim_scope_content_fingerprints"]
            ),
            "authority_revision_id": authority_revision_id,
            "checked_at": checked_at,
            "approval_request": approval_request,
            "trusted_approval_id": trusted_approval_id,
        },
    }


def _parse_source_evidence(
    value: Any, *, requested_ids: Sequence[str]
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return {}, ["holding_source_evidence_resolution_invalid"]
    records: dict[str, Mapping[str, Any]] = {}
    errors: list[str] = []
    for ordinal, raw in enumerate(value, start=1):
        evidence_id, record_errors = _source_evidence_errors(raw, ordinal=ordinal)
        errors.extend(record_errors)
        if not evidence_id:
            continue
        if evidence_id in records:
            errors.append(f"holding_source_evidence_duplicate:{evidence_id}")
            continue
        if isinstance(raw, Mapping):
            records[evidence_id] = raw
    if sorted(records) != list(requested_ids):
        errors.append("holding_source_evidence_set_mismatch")
    return records, _unique(errors)


def _parse_current_authority(
    value: Any,
    *,
    requested_ids: Sequence[str],
    sources: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return {}, ["holding_current_authority_resolution_invalid"]
    records: dict[str, Mapping[str, Any]] = {}
    errors: list[str] = []
    for ordinal, raw in enumerate(value, start=1):
        label = f"holding_current_authority:{ordinal}"
        if not isinstance(raw, Mapping):
            errors.append(f"{label}_invalid")
            continue
        errors.extend(_exact_mapping_keys(raw, _CURRENT_AUTHORITY_FIELDS, label=label))
        evidence_id = raw.get("evidence_id")
        if not isinstance(evidence_id, str) or not _SOURCE_EVIDENCE_ID_RE.fullmatch(evidence_id):
            errors.append(f"{label}_evidence_id_invalid")
            continue
        if evidence_id in records:
            errors.append(f"holding_current_authority_duplicate:{evidence_id}")
            continue
        records[evidence_id] = raw
        if not isinstance(raw.get("filing_ready"), bool) or raw.get("filing_ready") is not True:
            errors.append(f"holding_current_authority_not_ready:{evidence_id}")
        if raw.get("blockers") != []:
            errors.append(f"holding_current_authority_blockers_present:{evidence_id}")
        source = sources.get(evidence_id)
        if source is not None and raw.get("identity_verification_mode") != source.get(
            "identity_verification_mode"
        ):
            errors.append(f"holding_current_authority_mode_mismatch:{evidence_id}")
    if sorted(records) != list(requested_ids):
        errors.append("holding_current_authority_set_mismatch")
    return records, _unique(errors)


def _parse_claim_scope(
    value: Any,
    *,
    request: Mapping[str, Any],
    sources: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return {}, ["holding_claim_scope_resolution_invalid"]
    records: dict[str, Mapping[str, Any]] = {}
    errors: list[str] = []
    requested_ids = list(request.get("evidence_ids") or ())
    for ordinal, raw in enumerate(value, start=1):
        label = f"holding_claim_scope:{ordinal}"
        if not isinstance(raw, Mapping):
            errors.append(f"{label}_invalid")
            continue
        errors.extend(_exact_mapping_keys(raw, _CLAIM_SCOPE_FIELDS, label=label))
        evidence_id = raw.get("evidence_id")
        if not isinstance(evidence_id, str) or not _SOURCE_EVIDENCE_ID_RE.fullmatch(evidence_id):
            errors.append(f"{label}_evidence_id_invalid")
            continue
        if evidence_id in records:
            errors.append(f"holding_claim_scope_duplicate:{evidence_id}")
            continue
        records[evidence_id] = raw
        if raw.get("schema_version") != "1.0.0":
            errors.append(f"holding_claim_scope_schema_invalid:{evidence_id}")
        for field in ("source_id", "claim_id"):
            if not _canonical_identifier(raw.get(field)):
                errors.append(f"holding_claim_scope_{field}_invalid:{evidence_id}")
        if raw.get("authority_role") != "ksrf_legal_holding":
            errors.append(f"holding_claim_scope_authority_role_invalid:{evidence_id}")
        if not _canonical_identifier(raw.get("verified_official_locator")):
            errors.append(f"holding_claim_scope_locator_invalid:{evidence_id}")
        if not _exact_nonempty_text(raw.get("pinpoint")):
            errors.append(f"holding_claim_scope_pinpoint_invalid:{evidence_id}")
        raw_sha = raw.get("raw_sha256")
        if not isinstance(raw_sha, str) or not _SHA256_RE.fullmatch(raw_sha):
            errors.append(f"holding_claim_scope_raw_sha256_invalid:{evidence_id}")
        revision = raw.get("verification_revision_id")
        if not isinstance(revision, str) or not _SOURCE_VERIFICATION_ID_RE.fullmatch(revision):
            errors.append(f"holding_claim_scope_verification_revision_invalid:{evidence_id}")
        current_id = raw.get("current_evidence_id")
        if not isinstance(current_id, str) or not _SOURCE_EVIDENCE_ID_RE.fullmatch(current_id):
            errors.append(f"holding_claim_scope_current_evidence_id_invalid:{evidence_id}")
        if raw.get("freshness_state") != "current":
            errors.append(f"holding_claim_scope_not_current:{evidence_id}")
        scope_revision = raw.get("scope_revision_id")
        if not _canonical_identifier(scope_revision):
            errors.append(f"holding_claim_scope_revision_invalid:{evidence_id}")
        if not _is_rfc3339_datetime(raw.get("checked_at")):
            errors.append(f"holding_claim_scope_checked_at_invalid:{evidence_id}")
        if not _exact_nonempty_text(raw.get("maximum_supported_inference")):
            errors.append(f"holding_claim_scope_inference_invalid:{evidence_id}")

        source = sources.get(evidence_id)
        if source is None:
            continue
        raw_object = source.get("raw_object")
        source_raw_sha = raw_object.get("sha256") if isinstance(raw_object, Mapping) else None
        expected = {
            "evidence_id": evidence_id,
            "source_id": source.get("source_id"),
            "claim_id": request.get("claim_id"),
            "authority_role": "ksrf_legal_holding",
            "verified_official_locator": source.get("verified_official_locator"),
            "raw_sha256": source_raw_sha,
            "verification_revision_id": source.get("verification_revision_id"),
            "current_evidence_id": evidence_id,
            "freshness_state": "current",
            "maximum_supported_inference": request.get("maximum_supported_inference"),
        }
        for field, expected_value in expected.items():
            if raw.get(field) != expected_value:
                errors.append(f"holding_claim_scope_binding_mismatch:{evidence_id}:{field}")
        try:
            canonical_json_bytes(dict(raw))
        except (TypeError, ValueError):
            errors.append(f"holding_claim_scope_not_canonical_json:{evidence_id}")
    if sorted(records) != requested_ids:
        errors.append("holding_claim_scope_set_mismatch")
    return records, _unique(errors)


def _resolution_errors_and_receipt(
    request: Mapping[str, Any], resolution: Mapping[str, Any]
) -> tuple[list[str], dict[str, Any] | None]:
    errors = _exact_mapping_keys(resolution, _RESOLUTION_FIELDS, label="holding_binding_resolution")
    if resolution.get("schema_version") != "1.0.0":
        errors.append("holding_binding_resolution_schema_invalid")
    if resolution.get("status") != "verified":
        errors.append("holding_binding_resolution_not_verified")
    if resolution.get("holding_binding_sha256") != request.get("holding_binding_sha256"):
        errors.append("holding_binding_sha256_mismatch")

    requested_ids = list(request.get("evidence_ids") or ())
    sources, source_errors = _parse_source_evidence(
        resolution.get("source_evidence"), requested_ids=requested_ids
    )
    errors.extend(source_errors)
    current, current_errors = _parse_current_authority(
        resolution.get("current_authority"), requested_ids=requested_ids, sources=sources
    )
    errors.extend(current_errors)
    scopes, scope_errors = _parse_claim_scope(
        resolution.get("claim_scope"), request=request, sources=sources
    )
    errors.extend(scope_errors)

    gate = resolution.get("scope_gate_receipt")
    expected_approval_request: dict[str, Any] | None = None
    if not isinstance(gate, Mapping):
        errors.append("holding_scope_gate_receipt_missing")
    else:
        errors.extend(
            _exact_mapping_keys(gate, _SCOPE_GATE_RECEIPT_FIELDS, label="holding_scope_gate_receipt")
        )
        if gate.get("schema_version") != "1.0.0":
            errors.append("holding_scope_gate_receipt_schema_invalid")
        if not isinstance(gate.get("passed"), bool) or gate.get("passed") is not True:
            errors.append("holding_scope_gate_not_passed")
        trusted_id = gate.get("trusted_approval_id")
        if not isinstance(trusted_id, str) or not _TRUSTED_APPROVAL_ID_RE.fullmatch(trusted_id):
            errors.append("holding_scope_trusted_approval_id_invalid")
        if not _canonical_identifier(gate.get("authority_revision_id")):
            errors.append("holding_scope_authority_revision_id_invalid")
        if not _is_rfc3339_datetime(gate.get("checked_at")):
            errors.append("holding_scope_checked_at_invalid")
        if (
            not source_errors
            and not scope_errors
            and sorted(sources) == requested_ids
            and sorted(scopes) == requested_ids
        ):
            try:
                expected_approval_request = build_holding_scope_approval_request(
                    request=request,
                    source_evidence=[
                        sources[evidence_id] for evidence_id in requested_ids
                    ],
                    claim_scope=[scopes[evidence_id] for evidence_id in requested_ids],
                )
            except (KeyError, TypeError, ValueError):
                errors.append("holding_scope_approval_request_rebuild_failed")
                expected_approval_request = None
        if expected_approval_request is not None:
            raw_approval_request = gate.get("approval_request")
            if not isinstance(raw_approval_request, Mapping) or dict(raw_approval_request) != expected_approval_request:
                errors.append("holding_scope_approval_request_mismatch")
            expected_gate_bindings = {
                "sentence_id": request.get("sentence_id"),
                "section_code": request.get("section_code"),
                "holding_binding_sha256": request.get("holding_binding_sha256"),
                "claim_id": request.get("claim_id"),
                "evidence_ids": requested_ids,
                "maximum_supported_inference": request.get(
                    "maximum_supported_inference"
                ),
                "source_ids": expected_approval_request["bindings"]["source_ids"],
                "source_evidence_content_fingerprints": expected_approval_request[
                    "bindings"
                ]["source_evidence_content_fingerprints"],
                "claim_scope_content_fingerprints": expected_approval_request[
                    "bindings"
                ]["claim_scope_content_fingerprints"],
            }
            for field, expected_value in expected_gate_bindings.items():
                if gate.get(field) != expected_value:
                    errors.append(f"holding_scope_gate_binding_mismatch:{field}")

    errors = _unique(errors)
    if errors or expected_approval_request is None or not isinstance(gate, Mapping):
        return errors, None

    source_receipts: dict[str, dict[str, Any]] = {}
    scope_receipts: dict[str, dict[str, Any]] = {}
    authority_receipts: dict[str, dict[str, Any]] = {}
    for evidence_id in requested_ids:
        source = sources[evidence_id]
        raw_object = source["raw_object"]
        source_receipts[evidence_id] = {
            "evidence_id": evidence_id,
            "source_id": source["source_id"],
            "origin_url": source["origin_url"],
            "authority_class": source["authority_class"],
            "raw_sha256": raw_object["sha256"],
            "verified_official_locator": source["verified_official_locator"],
            "verification_revision_id": source["verification_revision_id"],
            "identity_fingerprint": source["identity_fingerprint"],
            "source_evidence_content_fingerprint": source_evidence_content_fingerprint(source),
        }
        scope_receipts[evidence_id] = {
            **deepcopy(dict(scopes[evidence_id])),
            "claim_scope_content_fingerprint": holding_claim_scope_content_fingerprint(
                scopes[evidence_id]
            ),
        }
        authority_receipts[evidence_id] = deepcopy(dict(current[evidence_id]))
    return [], {
        "schema_version": "1.0.0",
        "sentence_id": request["sentence_id"],
        "section_code": request["section_code"],
        "holding_binding_sha256": request["holding_binding_sha256"],
        "claim_id": request["claim_id"],
        "evidence_ids": requested_ids,
        "maximum_supported_inference": request["maximum_supported_inference"],
        "source_evidence_receipts": source_receipts,
        "current_authority_results": authority_receipts,
        "claim_scope_receipts": scope_receipts,
        "scope_gate_receipt": deepcopy(dict(gate)),
    }


def resolve_holding_evidence_binding(
    request: Mapping[str, Any],
    authority: HoldingEvidenceBindingAuthority | Any | None,
) -> tuple[tuple[str, ...], dict[str, Any] | None]:
    """Resolve and locally revalidate one exact legal-holding binding."""

    canonical_request, request_errors = _canonical_holding_request(request)
    if canonical_request is None:
        return request_errors, None
    resolver = getattr(authority, "resolve_holding_evidence_binding", None)
    if authority is None or not callable(resolver):
        return ("holding_binding_authority_required",), None
    adapter_request = deepcopy(canonical_request)
    try:
        resolution = resolver(adapter_request)
    except Exception:
        return ("holding_binding_authority_error",), None
    if adapter_request != canonical_request:
        return ("holding_binding_request_mutated",), None
    if not isinstance(resolution, Mapping):
        return ("holding_binding_resolution_missing",), None
    errors, receipt = _resolution_errors_and_receipt(canonical_request, resolution)
    return tuple(errors), receipt


def _binding_index_basis(
    *, matter_id: str, draft_id: str, bindings: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": [dict(item) for item in bindings],
    }


def _binding_index_sha256(
    *, matter_id: str, draft_id: str, bindings: Sequence[Mapping[str, Any]]
) -> str:
    return sha256(
        canonical_json_bytes(
            _binding_index_basis(
                matter_id=matter_id, draft_id=draft_id, bindings=bindings
            )
        )
    ).hexdigest()


def _canonical_index_bindings(
    value: Any,
    *,
    label: str,
    require_canonical_order: bool,
) -> tuple[list[dict[str, str]], list[str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return [], [f"{label}_invalid"]
    expected_fields = frozenset(
        {"sentence_id", "section_code", "role", "holding_binding_sha256"}
    )
    bindings: list[dict[str, str]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for ordinal, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping):
            errors.append(f"{label}_entry_invalid:{ordinal}")
            continue
        entry_errors = _exact_mapping_keys(
            raw, expected_fields, label=f"{label}:{ordinal}"
        )
        sentence_id = raw.get("sentence_id")
        section_code = raw.get("section_code")
        binding_sha = raw.get("holding_binding_sha256")
        if not isinstance(sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(sentence_id):
            entry_errors.append(f"{label}_sentence_id_invalid:{ordinal}")
        if not _canonical_identifier(section_code):
            entry_errors.append(f"{label}_section_code_invalid:{ordinal}")
        if raw.get("role") != "legal_holding":
            entry_errors.append(f"{label}_role_invalid:{ordinal}")
        if not isinstance(binding_sha, str) or not _SHA256_RE.fullmatch(binding_sha):
            entry_errors.append(f"{label}_sha256_invalid:{ordinal}")
        if isinstance(sentence_id, str) and sentence_id in seen:
            entry_errors.append(f"{label}_duplicate:{sentence_id}")
        if entry_errors:
            errors.extend(entry_errors)
            continue
        assert isinstance(sentence_id, str)
        assert isinstance(section_code, str)
        assert isinstance(binding_sha, str)
        seen.add(sentence_id)
        bindings.append(
            {
                "sentence_id": sentence_id,
                "section_code": section_code,
                "role": "legal_holding",
                "holding_binding_sha256": binding_sha,
            }
        )
    canonical = sorted(bindings, key=lambda item: item["sentence_id"])
    if require_canonical_order and bindings != canonical:
        errors.append(f"{label}_not_canonical")
    return canonical, _unique(errors)


def build_holding_binding_index_resolution(
    *,
    matter_id: str,
    draft_id: str,
    bindings: Sequence[Mapping[str, Any]],
    authority_revision_id: str,
    checked_at: str,
) -> dict[str, Any]:
    """Build a canonical authoritative complete index, including an empty set."""

    canonical, errors = _canonical_index_bindings(
        bindings,
        label="holding_binding_index_bindings",
        require_canonical_order=False,
    )
    for label, value in (
        ("matter_id", matter_id),
        ("draft_id", draft_id),
        ("authority_revision_id", authority_revision_id),
    ):
        if not _canonical_identifier(value):
            errors.append(f"holding_binding_index_{label}_invalid")
    if not _is_rfc3339_datetime(checked_at):
        errors.append("holding_binding_index_checked_at_invalid")
    if errors:
        raise ValueError(", ".join(_unique(errors)))
    return {
        "schema_version": "1.0.0",
        "status": "verified",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": canonical,
        "binding_index_sha256": _binding_index_sha256(
            matter_id=matter_id, draft_id=draft_id, bindings=canonical
        ),
        "authority_revision_id": authority_revision_id,
        "checked_at": checked_at,
    }


def resolve_holding_evidence_binding_index(
    *,
    matter_id: str,
    draft_id: str,
    expected_bindings: Sequence[Mapping[str, Any]],
    authority: HoldingEvidenceBindingAuthority | Any | None,
) -> tuple[tuple[str, ...], dict[str, Any] | None]:
    """Revalidate the host-owned complete legal-holding set for one draft."""

    errors: list[str] = []
    if not _canonical_identifier(matter_id):
        errors.append("holding_binding_index_matter_id_invalid")
    if not _canonical_identifier(draft_id):
        errors.append("holding_binding_index_draft_id_invalid")
    expected, expected_errors = _canonical_index_bindings(
        expected_bindings,
        label="holding_binding_index_expected",
        require_canonical_order=False,
    )
    errors.extend(expected_errors)
    if errors:
        return tuple(_unique(errors)), None

    lookup = build_holding_binding_index_request(matter_id=matter_id, draft_id=draft_id)
    resolver = getattr(authority, "resolve_holding_evidence_binding_index", None)
    if authority is None or not callable(resolver):
        return ("holding_binding_index_authority_required",), None
    adapter_lookup = deepcopy(lookup)
    try:
        resolution = resolver(adapter_lookup)
    except Exception:
        return ("holding_binding_index_authority_error",), None
    if adapter_lookup != lookup:
        return ("holding_binding_index_request_mutated",), None
    if not isinstance(resolution, Mapping):
        return ("holding_binding_index_resolution_missing",), None

    resolution_fields = frozenset(
        {
            "schema_version",
            "status",
            "matter_id",
            "draft_id",
            "bindings",
            "binding_index_sha256",
            "authority_revision_id",
            "checked_at",
        }
    )
    errors = _exact_mapping_keys(
        resolution, resolution_fields, label="holding_binding_index_resolution"
    )
    if resolution.get("schema_version") != "1.0.0":
        errors.append("holding_binding_index_schema_invalid")
    if resolution.get("status") != "verified":
        errors.append("holding_binding_index_not_verified")
    if resolution.get("matter_id") != matter_id:
        errors.append("holding_binding_index_matter_id_mismatch")
    if resolution.get("draft_id") != draft_id:
        errors.append("holding_binding_index_draft_id_mismatch")
    authoritative, binding_errors = _canonical_index_bindings(
        resolution.get("bindings"),
        label="holding_binding_index_bindings",
        require_canonical_order=True,
    )
    errors.extend(binding_errors)
    if authoritative != expected:
        errors.append("holding_binding_index_set_mismatch")
    computed_sha = _binding_index_sha256(
        matter_id=matter_id, draft_id=draft_id, bindings=authoritative
    )
    if resolution.get("binding_index_sha256") != computed_sha:
        errors.append("holding_binding_index_sha256_mismatch")
    if not _canonical_identifier(resolution.get("authority_revision_id")):
        errors.append("holding_binding_index_authority_revision_id_invalid")
    if not _is_rfc3339_datetime(resolution.get("checked_at")):
        errors.append("holding_binding_index_checked_at_invalid")
    errors = _unique(errors)
    if errors:
        return tuple(errors), None
    return (), {
        "schema_version": "1.0.0",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": authoritative,
        "binding_index_sha256": computed_sha,
        "authority_revision_id": resolution["authority_revision_id"],
        "checked_at": resolution["checked_at"],
    }


__all__ = [
    "HoldingEvidenceBindingAuthority",
    "build_holding_binding_index_request",
    "build_holding_binding_index_resolution",
    "build_holding_binding_request",
    "build_holding_binding_resolution",
    "build_holding_claim_scope",
    "build_holding_scope_approval_request",
    "holding_claim_scope_content_fingerprint",
    "resolve_holding_evidence_binding",
    "resolve_holding_evidence_binding_index",
    "source_evidence_content_fingerprint",
]
