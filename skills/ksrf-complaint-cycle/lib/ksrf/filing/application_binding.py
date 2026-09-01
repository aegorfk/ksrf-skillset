"""Host-attested evidence binding for application-finding sentences."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import re
from typing import Any, Mapping, Protocol, Sequence

from .application_evidence import (
    ApplicationEvidenceRecord,
    ChainAssessment,
    EvidenceSpan,
    ImplicitPremiseProof,
    application_record_content_fingerprint,
    assess_application_chain,
    classify_application,
)
from .norm_versions import norm_version_passport_content_fingerprint
from .relief_binding import (
    _application_gate_receipt_errors,
    _application_records,
    _norm_gate_receipt_errors,
    _norm_passport,
)
from .storage import canonical_json_bytes, stable_id


_SCHEMA_VERSION = "1.0.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SENTENCE_ID_RE = re.compile(r"^sent-[0-9a-f]{16}$")
_TRUSTED_APPROVAL_ID_RE = re.compile(
    r"^trusted-approval:sha256:[0-9a-f]{64}$"
)
_RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?"
    r"(?:Z|[+-]\d{2}:\d{2})$"
)
_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "matter_id",
        "draft_id",
        "sentence_id",
        "section_code",
        "sentence_text",
        "sentence_text_sha256",
        "claim_id",
        "norm_passport_id",
        "application_record_ids",
        "evidence_ids",
        "maximum_supported_inference",
        "application_binding_sha256",
    }
)
_SCOPE_FIELDS = frozenset(
    {
        "schema_version",
        "matter_id",
        "draft_id",
        "sentence_id",
        "section_code",
        "application_binding_sha256",
        "claim_id",
        "norm_passport_id",
        "norm_version_passport_revision_id",
        "norm_version_passport_content_fingerprint",
        "application_record_ids",
        "evidence_ids",
        "chain_fingerprint",
        "chain_revision_id",
        "chain_checked_at",
        "reviewed_statement",
        "reviewed_statement_sha256",
        "maximum_supported_inference",
        "scope_revision_id",
        "checked_at",
        "scope_content_fingerprint",
    }
)
_SCOPE_GATE_RECEIPT_FIELDS = frozenset(
    {
        "passed",
        "content_fingerprint",
        "approval_request",
        "trusted_approval_id",
    }
)
_APPLICATION_GATE_RECEIPT_FIELDS = frozenset(
    {
        "record_id",
        "passed",
        "content_fingerprint",
        "approval_request",
        "trusted_approval_id",
        "preservation_rule_evidence",
        "preservation_rule_gate_receipt",
    }
)
_NORM_GATE_RECEIPT_FIELDS = frozenset(
    {"passed", "content_fingerprint", "approval_request", "trusted_approval_id"}
)
_RESOLUTION_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "application_binding_sha256",
        "application_records",
        "chain_records",
        "chain_assessment",
        "norm_version_passport",
        "norm_version_gate_receipt",
        "application_gate_receipts",
        "scope_record",
        "scope_gate_receipt",
        "chain_revision_id",
        "chain_checked_at",
        "authority_revision_id",
        "checked_at",
    }
)
_INDEX_BINDING_FIELDS = frozenset(
    {
        "sentence_id",
        "section_code",
        "role",
        "claim_id",
        "norm_passport_id",
        "application_binding_sha256",
    }
)
_INDEX_RESOLUTION_FIELDS = frozenset(
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


class ApplicationFindingEvidenceBindingAuthority(Protocol):
    """Host boundary for current application evidence and draft-registry state."""

    def resolve_application_finding_evidence_binding(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any] | None: ...

    def resolve_application_finding_evidence_binding_index(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any] | None: ...


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _canonical_identifier(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = " ".join(value.split())
    return value if value and value == normalized else ""


def _exact_nonempty_text(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        return ""
    return value


def _is_rfc3339(value: Any) -> bool:
    canonical = _canonical_identifier(value)
    if not canonical or not _RFC3339_RE.fullmatch(canonical):
        return False
    candidate = canonical[:-1] + "+00:00" if canonical.endswith("Z") else canonical
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _exact_mapping_keys(
    value: Mapping[str, Any], expected: frozenset[str], *, label: str
) -> list[str]:
    if any(not isinstance(key, str) for key in value):
        return [f"{label}_mapping_key_invalid"]
    actual = set(value)
    errors = [f"{label}_field_missing:{key}" for key in sorted(expected - actual)]
    errors.extend(
        f"{label}_field_unexpected:{key}" for key in sorted(actual - expected)
    )
    return errors


def _exact_identifier_list(
    value: Any, *, label: str, allow_empty: bool = False
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
        if not identifier:
            errors.append(f"{label}_identifier_invalid:{ordinal}")
            continue
        if identifier in seen:
            errors.append(f"{label}_duplicate:{identifier}")
            continue
        seen.add(identifier)
        values.append(identifier)
    return values, errors


def build_application_finding_binding_request(
    *,
    matter_id: str,
    draft_id: str,
    sentence_id: str,
    section_code: str,
    sentence_text: str,
    claim_id: str,
    norm_passport_id: str,
    application_record_ids: Sequence[str],
    evidence_ids: Sequence[str],
    maximum_supported_inference: str,
) -> dict[str, Any]:
    """Build the exact-byte lookup for one application-finding sentence."""

    basis = {
        "schema_version": _SCHEMA_VERSION,
        "matter_id": matter_id,
        "draft_id": draft_id,
        "sentence_id": sentence_id,
        "section_code": section_code,
        "sentence_text": sentence_text,
        "sentence_text_sha256": sha256(sentence_text.encode("utf-8")).hexdigest(),
        "claim_id": claim_id,
        "norm_passport_id": norm_passport_id,
        "application_record_ids": sorted(application_record_ids),
        "evidence_ids": sorted(evidence_ids),
        "maximum_supported_inference": maximum_supported_inference,
    }
    return {
        **basis,
        "application_binding_sha256": sha256(
            canonical_json_bytes(basis)
        ).hexdigest(),
    }


def build_application_finding_binding_index_request(
    *, matter_id: str, draft_id: str
) -> dict[str, Any]:
    """Build the narrow lookup for the host-owned complete finding index."""

    return {
        "schema_version": _SCHEMA_VERSION,
        "matter_id": matter_id,
        "draft_id": draft_id,
    }


def _canonical_request(
    request: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    errors = _exact_mapping_keys(
        request, _REQUEST_FIELDS, label="application_binding_request"
    )
    if request.get("schema_version") != _SCHEMA_VERSION:
        errors.append("application_binding_request_schema_invalid")
    for field in (
        "matter_id",
        "draft_id",
        "section_code",
        "claim_id",
        "norm_passport_id",
    ):
        if not _canonical_identifier(request.get(field)):
            errors.append(f"application_binding_request_identifier_invalid:{field}")
    sentence_id = request.get("sentence_id")
    if not isinstance(sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(sentence_id):
        errors.append("application_binding_request_sentence_id_invalid")
    if not _exact_nonempty_text(request.get("sentence_text")):
        errors.append("application_binding_request_sentence_text_invalid")
    if not _exact_nonempty_text(request.get("maximum_supported_inference")):
        errors.append("application_binding_request_inference_invalid")
    record_ids, record_errors = _exact_identifier_list(
        request.get("application_record_ids"),
        label="application_binding_request_application_record_ids",
    )
    evidence_ids, evidence_errors = _exact_identifier_list(
        request.get("evidence_ids"),
        label="application_binding_request_evidence_ids",
    )
    errors.extend(record_errors)
    errors.extend(evidence_errors)
    if errors:
        return None, tuple(_unique(errors))
    rebuilt = build_application_finding_binding_request(
        matter_id=request["matter_id"],
        draft_id=request["draft_id"],
        sentence_id=request["sentence_id"],
        section_code=request["section_code"],
        sentence_text=request["sentence_text"],
        claim_id=request["claim_id"],
        norm_passport_id=request["norm_passport_id"],
        application_record_ids=record_ids,
        evidence_ids=evidence_ids,
        maximum_supported_inference=request["maximum_supported_inference"],
    )
    if dict(request) != rebuilt:
        return None, ("application_binding_request_fingerprint_mismatch",)
    return rebuilt, ()


def _chain_projection(chain: ChainAssessment) -> dict[str, Any]:
    return {
        "status": chain.status,
        "final_record_id": chain.final_record_id,
        "supporting_record_ids": list(chain.supporting_record_ids),
        "evidence_ids": list(chain.evidence_ids),
        "reason_codes": list(chain.reason_codes),
        "record_content_fingerprints": [
            {"record_id": record_id, "fingerprint": fingerprint}
            for record_id, fingerprint in chain.record_content_fingerprints
        ],
    }


def _chain_fingerprint(chain: ChainAssessment) -> str:
    return stable_id("application-finding-chain", _chain_projection(chain))


def _scope_basis(
    *,
    request: Mapping[str, Any],
    norm_version_passport: Mapping[str, Any],
    chain: ChainAssessment,
    chain_revision_id: str,
    chain_checked_at: str,
    scope_revision_id: str,
    checked_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "matter_id": request.get("matter_id"),
        "draft_id": request.get("draft_id"),
        "sentence_id": request.get("sentence_id"),
        "section_code": request.get("section_code"),
        "application_binding_sha256": request.get("application_binding_sha256"),
        "claim_id": request.get("claim_id"),
        "norm_passport_id": request.get("norm_passport_id"),
        "norm_version_passport_revision_id": norm_version_passport.get(
            "passport_revision_id"
        ),
        "norm_version_passport_content_fingerprint": (
            norm_version_passport_content_fingerprint(norm_version_passport)
        ),
        "application_record_ids": list(
            request.get("application_record_ids") or ()
        ),
        "evidence_ids": list(request.get("evidence_ids") or ()),
        "chain_fingerprint": _chain_fingerprint(chain),
        "chain_revision_id": chain_revision_id,
        "chain_checked_at": chain_checked_at,
        "reviewed_statement": request.get("sentence_text"),
        "reviewed_statement_sha256": request.get("sentence_text_sha256"),
        "maximum_supported_inference": request.get(
            "maximum_supported_inference"
        ),
        "scope_revision_id": scope_revision_id,
        "checked_at": checked_at,
    }


def application_finding_scope_content_fingerprint(
    scope: Mapping[str, Any],
) -> str:
    """Fingerprint every independently stored scope field except itself."""

    basis = {key: deepcopy(value) for key, value in scope.items() if key != "scope_content_fingerprint"}
    return stable_id("application-finding-scope", basis)


def build_application_finding_scope(
    *,
    request: Mapping[str, Any],
    norm_version_passport: Mapping[str, Any],
    chain: ChainAssessment,
    chain_revision_id: str,
    chain_checked_at: str,
    checked_at: str,
    scope_revision_id: str | None = None,
) -> dict[str, Any]:
    """Build the independently stored exact wording/inference scope record."""

    preliminary_revision = scope_revision_id or "pending"
    basis = _scope_basis(
        request=request,
        norm_version_passport=norm_version_passport,
        chain=chain,
        chain_revision_id=chain_revision_id,
        chain_checked_at=chain_checked_at,
        scope_revision_id=preliminary_revision,
        checked_at=checked_at,
    )
    if scope_revision_id is None:
        basis["scope_revision_id"] = stable_id(
            "application-finding-scope-revision",
            {key: value for key, value in basis.items() if key != "scope_revision_id"},
        )
    return {
        **basis,
        "scope_content_fingerprint": application_finding_scope_content_fingerprint(
            basis
        ),
    }


def build_application_finding_scope_approval_request(
    *, request: Mapping[str, Any], scope: Mapping[str, Any]
) -> dict[str, Any]:
    """Reconstruct the exact human review subject for one finding line."""

    bindings = {
        "matter_id": request.get("matter_id"),
        "draft_id": request.get("draft_id"),
        "sentence_id": request.get("sentence_id"),
        "section_code": request.get("section_code"),
        "application_binding_sha256": request.get("application_binding_sha256"),
        "claim_id": request.get("claim_id"),
        "norm_passport_id": request.get("norm_passport_id"),
        "norm_version_passport_revision_id": scope.get(
            "norm_version_passport_revision_id"
        ),
        "norm_version_passport_content_fingerprint": scope.get(
            "norm_version_passport_content_fingerprint"
        ),
        "application_record_ids": list(
            request.get("application_record_ids") or ()
        ),
        "evidence_ids": list(request.get("evidence_ids") or ()),
        "chain_fingerprint": scope.get("chain_fingerprint"),
        "chain_revision_id": scope.get("chain_revision_id"),
        "chain_checked_at": scope.get("chain_checked_at"),
        "reviewed_statement": scope.get("reviewed_statement"),
        "reviewed_statement_sha256": scope.get("reviewed_statement_sha256"),
        "maximum_supported_inference": scope.get(
            "maximum_supported_inference"
        ),
        "scope_revision_id": scope.get("scope_revision_id"),
        "scope_checked_at": scope.get("checked_at"),
        "scope_content_fingerprint": scope.get("scope_content_fingerprint"),
    }
    return {
        "purpose": "application_finding",
        "subject_type": "application_finding_sentence_scope",
        "subject_id": request.get("sentence_id"),
        "fingerprint": stable_id("application-finding-scope-review", bindings),
        "bindings": bindings,
    }


def _parsed_records(
    raw_records: Any, *, label: str, chain: bool
) -> tuple[list[ApplicationEvidenceRecord], list[str]]:
    records, errors = _application_records(raw_records)
    if errors:
        return records, [f"{label}:{error}" for error in errors]
    assert isinstance(raw_records, Sequence)
    raw_items = list(raw_records)
    for ordinal, (raw, record) in enumerate(zip(raw_items, records), start=1):
        if not isinstance(raw, Mapping) or dict(raw) != record.to_dict():
            errors.append(f"{label}_record_not_closed:{ordinal}")
    record_ids = [record.record_id for record in records]
    if len(record_ids) != len(set(record_ids)):
        errors.append(f"{label}_record_id_duplicate")
    if chain:
        stage_orders = [record.stage_order for record in records]
        if len(stage_orders) != len(set(stage_orders)):
            errors.append(f"{label}_stage_order_duplicate")
        if stage_orders != sorted(stage_orders):
            errors.append(f"{label}_stage_order_not_canonical")
    elif record_ids != sorted(record_ids):
        errors.append(f"{label}_record_order_not_canonical")
    return records, errors


def _span_matches_record(
    record: ApplicationEvidenceRecord, span: EvidenceSpan
) -> bool:
    return (
        span.claim_id == record.claim_id
        and span.norm_id == record.norm_id
        and span.act_id == record.act_id
        and span.stage == record.stage
    )


def _direct_span_is_positive(
    record: ApplicationEvidenceRecord, span: EvidenceSpan
) -> bool:
    if (
        not _span_matches_record(record, span)
        or not span.has_full_act_locator
        or span.inference_status == "contradicted"
    ):
        return False
    return (
        span.reasoning_role in {"express_norm_use", "operative_rule"}
        and span.speaker == "court"
    ) or (
        span.reasoning_role == "outcome_link"
        and span.speaker in {"court", "disposition"}
    )


def _implicit_span_is_positive(
    record: ApplicationEvidenceRecord,
    proof: ImplicitPremiseProof,
    span: EvidenceSpan,
) -> bool:
    if (
        proof.inference_status == "contradicted"
        or not _span_matches_record(record, span)
        or not span.has_full_act_locator
        or span.inference_status == "contradicted"
    ):
        return False
    if proof.premise == "issue_before_court":
        return span.reasoning_role == "issue_before_court"
    if proof.premise == "operative_norm_logic":
        return (
            span.reasoning_role in {"operative_rule", "application_reasoning"}
            and span.speaker == "court"
        )
    if proof.premise == "counterfactual_outcome_dependence":
        return (
            span.reasoning_role in {"outcome_link", "counterfactual_analysis"}
            and span.speaker in {"court", "disposition"}
        )
    if proof.premise == "no_independent_sufficient_ground":
        return (
            span.reasoning_role == "alternative_ground_analysis"
            and (
                span.speaker in {"court", "reviewer"}
                or span.inference_status == "human_confirmed"
            )
        )
    return False


def _implicit_proof_errors(record: ApplicationEvidenceRecord) -> list[str]:
    if record.norm_use_status != "reasoning_linked_implicit":
        return []
    errors: list[str] = []
    spans = {span.evidence_id: span for span in record.evidence}
    for proof in record.implicit_premises:
        if proof.inference_status == "contradicted":
            errors.append(
                "application_binding_implicit_premise_inference_invalid:"
                f"{proof.premise}"
            )
        for evidence_id in proof.evidence_ids:
            span = spans.get(evidence_id)
            if span is None:
                errors.append(
                    "application_binding_implicit_evidence_missing:"
                    f"{evidence_id}"
                )
                continue
            if span.inference_status == "contradicted":
                errors.append(
                    "application_binding_evidence_inference_invalid:"
                    f"{evidence_id}"
                )
            if not _span_matches_record(record, span):
                errors.append(
                    "application_binding_evidence_scope_mismatch:"
                    f"{evidence_id}"
                )
            if not span.has_full_act_locator:
                errors.append(
                    "application_binding_implicit_evidence_locator_invalid:"
                    f"{evidence_id}"
                )
            if not _implicit_span_is_positive(record, proof, span):
                errors.append(
                    "application_binding_implicit_evidence_role_invalid:"
                    f"{evidence_id}"
                )
    return _unique(errors)


def _chain_integrity_errors(
    records: Sequence[ApplicationEvidenceRecord],
    chain: ChainAssessment,
) -> list[str]:
    errors: list[str] = []
    all_record_ids = {record.record_id for record in records}
    prior_record_ids: set[str] = set()
    evidence_occurrences: dict[
        str, list[tuple[ApplicationEvidenceRecord, EvidenceSpan]]
    ] = {}
    for record in records:
        incorporated_ids = list(record.incorporated_record_ids)
        if len(incorporated_ids) != len(set(incorporated_ids)):
            errors.append(
                "application_binding_incorporated_record_duplicate:"
                f"{record.record_id}"
            )
        for incorporated_id in incorporated_ids:
            if not _canonical_identifier(incorporated_id):
                errors.append(
                    "application_binding_incorporated_record_id_invalid:"
                    f"{record.record_id}"
                )
            elif incorporated_id not in all_record_ids:
                errors.append(
                    "application_binding_incorporated_record_unknown:"
                    f"{incorporated_id}"
                )
            elif incorporated_id not in prior_record_ids:
                errors.append(
                    "application_binding_incorporated_record_not_earlier:"
                    f"{incorporated_id}"
                )
        for span in record.evidence:
            evidence_occurrences.setdefault(span.evidence_id, []).append(
                (record, span)
            )
            if not _span_matches_record(record, span):
                errors.append(
                    "application_binding_chain_evidence_scope_mismatch:"
                    f"{span.evidence_id}"
                )
        prior_record_ids.add(record.record_id)

    for evidence_id in chain.evidence_ids:
        occurrences = evidence_occurrences.get(evidence_id, ())
        if len(occurrences) != 1:
            errors.append(
                "application_binding_chain_evidence_occurrence_invalid:"
                f"{evidence_id}"
            )
            continue
        record, span = occurrences[0]
        if not _span_matches_record(record, span):
            errors.append(
                "application_binding_chain_evidence_scope_mismatch:"
                f"{evidence_id}"
            )
        if span.inference_status == "contradicted":
            errors.append(
                "application_binding_chain_evidence_inference_invalid:"
                f"{evidence_id}"
            )
        if not (
            span.has_full_act_locator
            and span.reasoning_role == "incorporation"
            and span.speaker in {"court", "disposition"}
        ):
            errors.append(
                "application_binding_chain_evidence_role_or_locator_invalid:"
                f"{evidence_id}"
            )
    return _unique(errors)


def _chain_positive_proof_ids(
    records: Sequence[ApplicationEvidenceRecord], chain: ChainAssessment
) -> set[str]:
    occurrences = {
        span.evidence_id: (record, span)
        for record in records
        for span in record.evidence
    }
    positive: set[str] = set()
    for evidence_id in chain.evidence_ids:
        occurrence = occurrences.get(evidence_id)
        if occurrence is None:
            continue
        record, span = occurrence
        if (
            _span_matches_record(record, span)
            and span.has_full_act_locator
            and span.inference_status != "contradicted"
            and span.reasoning_role == "incorporation"
            and span.speaker in {"court", "disposition"}
        ):
            positive.add(evidence_id)
    return positive

def _positive_proof_ids(record: ApplicationEvidenceRecord) -> set[str]:
    classification = classify_application(record)
    if classification.status not in {
        "explicitly_applied",
        "implicitly_applied_proven",
    }:
        return set()
    if classification.status == "explicitly_applied":
        return {
            span.evidence_id
            for span in record.evidence
            if _direct_span_is_positive(record, span)
        }

    spans = {span.evidence_id: span for span in record.evidence}
    proof_ids: set[str] = set()
    for proof in record.implicit_premises:
        for evidence_id in proof.evidence_ids:
            span = spans.get(evidence_id)
            if span is not None and _implicit_span_is_positive(
                record, proof, span
            ):
                proof_ids.add(evidence_id)
    return proof_ids


def build_application_finding_binding_resolution(
    *,
    request: Mapping[str, Any],
    application_records: Sequence[Mapping[str, Any]],
    chain_records: Sequence[Mapping[str, Any]],
    norm_version_passport: Mapping[str, Any],
    norm_version_gate_receipt: Mapping[str, Any],
    application_gate_receipts: Sequence[Mapping[str, Any]],
    trusted_scope_approval_id: str,
    chain_revision_id: str,
    chain_checked_at: str,
    authority_revision_id: str,
    checked_at: str,
    scope_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a canonical positive host resolution, mainly for adapters/tests."""

    parsed_chain, chain_errors = _parsed_records(
        chain_records, label="application_binding_chain", chain=True
    )
    if chain_errors:
        raise ValueError(", ".join(_unique(chain_errors)))
    chain = assess_application_chain(parsed_chain)
    scope = (
        deepcopy(dict(scope_record))
        if scope_record is not None
        else build_application_finding_scope(
            request=request,
            norm_version_passport=norm_version_passport,
            chain=chain,
            chain_revision_id=chain_revision_id,
            chain_checked_at=chain_checked_at,
            checked_at=checked_at,
        )
    )
    approval_request = build_application_finding_scope_approval_request(
        request=request, scope=scope
    )
    return {
        "schema_version": _SCHEMA_VERSION,
        "status": "verified",
        "application_binding_sha256": request.get(
            "application_binding_sha256"
        ),
        "application_records": sorted(
            (deepcopy(dict(item)) for item in application_records),
            key=lambda item: item["record_id"],
        ),
        "chain_records": [deepcopy(dict(item)) for item in chain_records],
        "chain_assessment": _chain_projection(chain),
        "norm_version_passport": deepcopy(dict(norm_version_passport)),
        "norm_version_gate_receipt": deepcopy(
            dict(norm_version_gate_receipt)
        ),
        "application_gate_receipts": sorted(
            (deepcopy(dict(item)) for item in application_gate_receipts),
            key=lambda item: item["record_id"],
        ),
        "scope_record": scope,
        "scope_gate_receipt": {
            "passed": True,
            "content_fingerprint": scope.get("scope_content_fingerprint"),
            "approval_request": approval_request,
            "trusted_approval_id": trusted_scope_approval_id,
        },
        "chain_revision_id": chain_revision_id,
        "chain_checked_at": chain_checked_at,
        "authority_revision_id": authority_revision_id,
        "checked_at": checked_at,
    }


def _resolution_errors_and_receipt(
    request: Mapping[str, Any], resolution: Mapping[str, Any]
) -> tuple[list[str], dict[str, Any] | None]:
    errors = _exact_mapping_keys(
        resolution, _RESOLUTION_FIELDS, label="application_binding_resolution"
    )
    if resolution.get("schema_version") != _SCHEMA_VERSION:
        errors.append("application_binding_resolution_schema_invalid")
    if resolution.get("status") != "verified":
        errors.append("application_binding_resolution_not_verified")
    if resolution.get("application_binding_sha256") != request.get(
        "application_binding_sha256"
    ):
        errors.append("application_binding_sha256_mismatch")
    authority_revision_id = _canonical_identifier(
        resolution.get("authority_revision_id")
    )
    if not authority_revision_id:
        errors.append("application_binding_authority_revision_id_invalid")
    if not _is_rfc3339(resolution.get("checked_at")):
        errors.append("application_binding_checked_at_invalid")
    chain_revision_id = _canonical_identifier(
        resolution.get("chain_revision_id")
    )
    if not chain_revision_id:
        errors.append("application_binding_chain_revision_id_invalid")
    chain_checked_at = resolution.get("chain_checked_at")
    if not _is_rfc3339(chain_checked_at):
        errors.append("application_binding_chain_checked_at_invalid")

    selected, selected_errors = _parsed_records(
        resolution.get("application_records"),
        label="application_binding_selected_records",
        chain=False,
    )
    chain_records, chain_errors = _parsed_records(
        resolution.get("chain_records"),
        label="application_binding_chain_records",
        chain=True,
    )
    errors.extend(selected_errors)
    errors.extend(chain_errors)
    requested_record_ids = list(request.get("application_record_ids") or ())
    selected_by_id = {record.record_id: record for record in selected}
    chain_by_id = {record.record_id: record for record in chain_records}
    if sorted(selected_by_id) != requested_record_ids:
        errors.append("application_binding_selected_record_set_mismatch")
    for record_id, selected_record in selected_by_id.items():
        chain_record = chain_by_id.get(record_id)
        if (
            chain_record is None
            or chain_record.to_dict() != selected_record.to_dict()
        ):
            errors.append(
                f"application_binding_selected_record_not_in_chain:{record_id}"
            )

    chain = assess_application_chain(chain_records)
    errors.extend(_chain_integrity_errors(chain_records, chain))
    chain_projection = _chain_projection(chain)
    if resolution.get("chain_assessment") != chain_projection:
        errors.append("application_binding_chain_assessment_mismatch")
    if chain.status not in {"survived", "incorporated", "concurrent"}:
        errors.append("application_binding_chain_not_release_supported")
    for record in selected:
        classification = classify_application(record)
        errors.extend(_implicit_proof_errors(record))
        if classification.status not in {
            "explicitly_applied",
            "implicitly_applied_proven",
        }:
            errors.append(
                f"application_binding_selected_record_not_positive:{record.record_id}"
            )
        if record.outcome_causation not in {"determinative", "contributory"}:
            errors.append(
                f"application_binding_selected_record_causation_invalid:{record.record_id}"
            )
        if record.record_id not in chain.supporting_record_ids:
            errors.append(
                f"application_binding_selected_record_not_supported:{record.record_id}"
            )

    passport, passport_errors = _norm_passport(
        resolution.get("norm_version_passport")
    )
    errors.extend(passport_errors)
    if passport is not None:
        if passport.get("passport_id") != request.get("norm_passport_id"):
            errors.append("application_binding_norm_passport_id_mismatch")
        selected_norm_ids = {record.norm_id for record in selected}
        chain_norm_ids = {record.norm_id for record in chain_records}
        if selected_norm_ids | chain_norm_ids != {passport.get("norm_id")}:
            errors.append("application_binding_norm_id_mismatch")
        edition_ids = {
            segment.get("edition_id")
            for segment in passport.get("edition_segments", ())
            if isinstance(segment, Mapping)
        }
        for record in chain_records:
            if record.norm_version_id not in edition_ids:
                errors.append(
                    f"application_binding_record_edition_mismatch:{record.record_id}"
                )

    norm_receipt = resolution.get("norm_version_gate_receipt")
    if not isinstance(norm_receipt, Mapping):
        errors.append("application_binding_norm_gate_receipt_missing")
    else:
        errors.extend(
            _exact_mapping_keys(
                norm_receipt,
                _NORM_GATE_RECEIPT_FIELDS,
                label="application_binding_norm_gate_receipt",
            )
        )
        if passport is not None:
            errors.extend(_norm_gate_receipt_errors(norm_receipt, passport))

    raw_application_receipts = resolution.get("application_gate_receipts")
    receipt_by_record: dict[str, Mapping[str, Any]] = {}
    if not isinstance(raw_application_receipts, Sequence) or isinstance(
        raw_application_receipts, (str, bytes)
    ):
        errors.append("application_binding_application_gate_receipts_invalid")
    else:
        raw_receipt_ids: list[str] = []
        for ordinal, raw in enumerate(raw_application_receipts, start=1):
            if not isinstance(raw, Mapping):
                errors.append(
                    f"application_binding_application_gate_receipt_invalid:{ordinal}"
                )
                continue
            errors.extend(
                _exact_mapping_keys(
                    raw,
                    _APPLICATION_GATE_RECEIPT_FIELDS,
                    label=(
                        "application_binding_application_gate_receipt:"
                        f"{ordinal}"
                    ),
                )
            )
            record_id = _canonical_identifier(raw.get("record_id"))
            if not record_id:
                errors.append(
                    "application_binding_application_gate_receipt_record_id_invalid:"
                    f"{ordinal}"
                )
                continue
            raw_receipt_ids.append(record_id)
            if record_id in receipt_by_record:
                errors.append(
                    f"application_binding_application_gate_receipt_duplicate:{record_id}"
                )
            receipt_by_record[record_id] = raw
        if raw_receipt_ids != sorted(raw_receipt_ids):
            errors.append(
                "application_binding_application_gate_receipts_not_canonical"
            )
    if sorted(receipt_by_record) != requested_record_ids:
        errors.append("application_binding_application_gate_receipt_set_mismatch")
    if passport is not None and isinstance(norm_receipt, Mapping):
        for record in selected:
            errors.extend(
                _application_gate_receipt_errors(
                    receipt_by_record.get(record.record_id),
                    record,
                    chain_records,
                    passport,
                    norm_receipt,
                )
            )

    evidence_occurrences: dict[
        str, list[tuple[ApplicationEvidenceRecord, EvidenceSpan]]
    ] = {}
    for record in chain_records:
        for span in record.evidence:
            evidence_occurrences.setdefault(span.evidence_id, []).append(
                (record, span)
            )
    positive_ids = _chain_positive_proof_ids(chain_records, chain)
    for record in selected:
        positive_ids.update(_positive_proof_ids(record))
    requested_evidence_ids = set(request.get("evidence_ids") or ())
    if requested_evidence_ids != positive_ids:
        errors.append("application_binding_positive_evidence_set_mismatch")
    for evidence_id in request.get("evidence_ids") or ():
        occurrences = evidence_occurrences.get(evidence_id, [])
        if len(occurrences) != 1:
            errors.append(
                f"application_binding_evidence_occurrence_invalid:{evidence_id}"
            )
            continue
        record, span = occurrences[0]
        if evidence_id not in positive_ids:
            errors.append(
                f"application_binding_evidence_not_positive:{evidence_id}"
            )
        if not span.has_full_act_locator:
            errors.append(
                f"application_binding_evidence_locator_invalid:{evidence_id}"
            )
        if span.inference_status == "contradicted":
            errors.append(
                f"application_binding_evidence_inference_invalid:{evidence_id}"
            )
        if not _span_matches_record(record, span):
            errors.append(
                f"application_binding_evidence_scope_mismatch:{evidence_id}"
            )
        if span.claim_id != request.get("claim_id"):
            errors.append(
                f"application_binding_evidence_claim_mismatch:{evidence_id}"
            )
        if passport is not None and span.norm_id != passport.get("norm_id"):
            errors.append(
                f"application_binding_evidence_norm_mismatch:{evidence_id}"
            )

    scope = resolution.get("scope_record")
    expected_scope: dict[str, Any] | None = None
    if not isinstance(scope, Mapping):
        errors.append("application_binding_scope_record_missing")
    elif passport is not None:
        errors.extend(
            _exact_mapping_keys(
                scope, _SCOPE_FIELDS, label="application_binding_scope_record"
            )
        )
        scope_revision_id = _canonical_identifier(scope.get("scope_revision_id"))
        scope_checked_at = scope.get("checked_at")
        if not scope_revision_id:
            errors.append("application_binding_scope_revision_id_invalid")
        if not _is_rfc3339(scope_checked_at):
            errors.append("application_binding_scope_checked_at_invalid")
        if (
            scope_revision_id
            and isinstance(scope_checked_at, str)
            and _is_rfc3339(scope_checked_at)
            and chain_revision_id
            and isinstance(chain_checked_at, str)
            and _is_rfc3339(chain_checked_at)
        ):
            expected_scope = build_application_finding_scope(
                request=request,
                norm_version_passport=passport,
                chain=chain,
                chain_revision_id=chain_revision_id,
                chain_checked_at=chain_checked_at,
                checked_at=scope_checked_at,
                scope_revision_id=scope_revision_id,
            )
            if dict(scope) != expected_scope:
                errors.append("application_binding_scope_record_mismatch")

    scope_gate = resolution.get("scope_gate_receipt")
    if not isinstance(scope_gate, Mapping):
        errors.append("application_binding_scope_gate_receipt_missing")
    else:
        errors.extend(
            _exact_mapping_keys(
                scope_gate,
                _SCOPE_GATE_RECEIPT_FIELDS,
                label="application_binding_scope_gate_receipt",
            )
        )
        if scope_gate.get("passed") is not True:
            errors.append("application_binding_scope_gate_not_passed")
        trusted_id = scope_gate.get("trusted_approval_id")
        if not isinstance(trusted_id, str) or not _TRUSTED_APPROVAL_ID_RE.fullmatch(
            trusted_id
        ):
            errors.append("application_binding_scope_trusted_approval_id_invalid")
        if expected_scope is not None:
            if scope_gate.get("content_fingerprint") != expected_scope.get(
                "scope_content_fingerprint"
            ):
                errors.append(
                    "application_binding_scope_content_fingerprint_stale"
                )
            expected_approval_request = (
                build_application_finding_scope_approval_request(
                    request=request, scope=expected_scope
                )
            )
            raw_approval_request = scope_gate.get("approval_request")
            if (
                not isinstance(raw_approval_request, Mapping)
                or dict(raw_approval_request) != expected_approval_request
            ):
                errors.append(
                    "application_binding_scope_approval_request_mismatch"
                )

    errors = _unique(errors)
    if (
        errors
        or passport is None
        or expected_scope is None
        or not isinstance(norm_receipt, Mapping)
        or not isinstance(scope_gate, Mapping)
    ):
        return errors, None
    return [], {
        "schema_version": _SCHEMA_VERSION,
        "sentence_id": request["sentence_id"],
        "section_code": request["section_code"],
        "application_binding_sha256": request["application_binding_sha256"],
        "claim_id": request["claim_id"],
        "norm_passport_id": request["norm_passport_id"],
        "application_record_ids": requested_record_ids,
        "evidence_ids": list(request["evidence_ids"]),
        "maximum_supported_inference": request[
            "maximum_supported_inference"
        ],
        "chain_inventory_receipt": {
            "chain_assessment": chain_projection,
            "chain_fingerprint": _chain_fingerprint(chain),
            "chain_revision_id": chain_revision_id,
            "checked_at": chain_checked_at,
            "record_content_fingerprints": {
                record.record_id: application_record_content_fingerprint(record)
                for record in chain_records
            },
        },
        "norm_version_gate_receipt": deepcopy(dict(norm_receipt)),
        "application_gate_receipts": {
            record_id: deepcopy(dict(receipt_by_record[record_id]))
            for record_id in requested_record_ids
        },
        "scope_receipt": {
            "scope_record": deepcopy(expected_scope),
            "scope_gate_receipt": deepcopy(dict(scope_gate)),
        },
        "authority_revision_id": authority_revision_id,
        "checked_at": resolution["checked_at"],
    }


def resolve_application_finding_evidence_binding(
    request: Mapping[str, Any],
    authority: ApplicationFindingEvidenceBindingAuthority | Any | None,
) -> tuple[tuple[str, ...], dict[str, Any] | None]:
    """Resolve and locally revalidate one exact application finding."""

    canonical_request, request_errors = _canonical_request(request)
    if canonical_request is None:
        return request_errors, None
    resolver = getattr(
        authority, "resolve_application_finding_evidence_binding", None
    )
    if authority is None or not callable(resolver):
        return ("application_binding_authority_required",), None
    adapter_request = deepcopy(canonical_request)
    try:
        resolution = resolver(adapter_request)
    except Exception:
        return ("application_binding_authority_error",), None
    if adapter_request != canonical_request:
        return ("application_binding_request_mutated",), None
    if not isinstance(resolution, Mapping):
        return ("application_binding_resolution_missing",), None
    errors, receipt = _resolution_errors_and_receipt(
        canonical_request, resolution
    )
    return tuple(errors), receipt


def _canonical_index_bindings(
    value: Any, *, label: str, require_canonical_order: bool
) -> tuple[list[dict[str, str]], list[str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return [], [f"{label}_invalid"]
    bindings: list[dict[str, str]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for ordinal, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping):
            errors.append(f"{label}_entry_invalid:{ordinal}")
            continue
        entry_errors = _exact_mapping_keys(
            raw, _INDEX_BINDING_FIELDS, label=f"{label}:{ordinal}"
        )
        sentence_id = raw.get("sentence_id")
        section_code = raw.get("section_code")
        claim_id = raw.get("claim_id")
        norm_passport_id = raw.get("norm_passport_id")
        if not isinstance(sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(
            sentence_id
        ):
            entry_errors.append(f"{label}_sentence_id_invalid:{ordinal}")
        for field, value in (
            ("section_code", section_code),
            ("claim_id", claim_id),
            ("norm_passport_id", norm_passport_id),
        ):
            if not _canonical_identifier(value):
                entry_errors.append(f"{label}_{field}_invalid:{ordinal}")
        if raw.get("role") != "application_finding":
            entry_errors.append(f"{label}_role_invalid:{ordinal}")
        binding_sha = raw.get("application_binding_sha256")
        if not isinstance(binding_sha, str) or not _SHA256_RE.fullmatch(
            binding_sha
        ):
            entry_errors.append(f"{label}_sha256_invalid:{ordinal}")
        if isinstance(sentence_id, str) and sentence_id in seen:
            entry_errors.append(f"{label}_duplicate:{sentence_id}")
        if entry_errors:
            errors.extend(entry_errors)
            continue
        assert isinstance(sentence_id, str)
        assert isinstance(section_code, str)
        assert isinstance(claim_id, str)
        assert isinstance(norm_passport_id, str)
        assert isinstance(binding_sha, str)
        seen.add(sentence_id)
        bindings.append(
            {
                "sentence_id": sentence_id,
                "section_code": section_code,
                "role": "application_finding",
                "claim_id": claim_id,
                "norm_passport_id": norm_passport_id,
                "application_binding_sha256": binding_sha,
            }
        )
    canonical = sorted(bindings, key=lambda item: item["sentence_id"])
    if require_canonical_order and bindings != canonical:
        errors.append(f"{label}_not_canonical")
    return canonical, _unique(errors)


def _index_sha256(
    *, matter_id: str, draft_id: str, bindings: Sequence[Mapping[str, Any]]
) -> str:
    basis = {
        "schema_version": _SCHEMA_VERSION,
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": [dict(item) for item in bindings],
    }
    return sha256(canonical_json_bytes(basis)).hexdigest()


def build_application_finding_binding_index_resolution(
    *,
    matter_id: str,
    draft_id: str,
    bindings: Sequence[Mapping[str, Any]],
    authority_revision_id: str,
    checked_at: str,
) -> dict[str, Any]:
    """Build the complete authoritative index, including an empty set."""

    canonical, errors = _canonical_index_bindings(
        bindings,
        label="application_binding_index_bindings",
        require_canonical_order=False,
    )
    for label, value in (
        ("matter_id", matter_id),
        ("draft_id", draft_id),
        ("authority_revision_id", authority_revision_id),
    ):
        if not _canonical_identifier(value):
            errors.append(f"application_binding_index_{label}_invalid")
    if not _is_rfc3339(checked_at):
        errors.append("application_binding_index_checked_at_invalid")
    if errors:
        raise ValueError(", ".join(_unique(errors)))
    return {
        "schema_version": _SCHEMA_VERSION,
        "status": "verified",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": canonical,
        "binding_index_sha256": _index_sha256(
            matter_id=matter_id, draft_id=draft_id, bindings=canonical
        ),
        "authority_revision_id": authority_revision_id,
        "checked_at": checked_at,
    }


def resolve_application_finding_evidence_binding_index(
    *,
    matter_id: str,
    draft_id: str,
    expected_bindings: Sequence[Mapping[str, Any]],
    authority: ApplicationFindingEvidenceBindingAuthority | Any | None,
) -> tuple[tuple[str, ...], dict[str, Any] | None]:
    """Revalidate the host-owned complete application-finding set."""

    errors: list[str] = []
    if not _canonical_identifier(matter_id):
        errors.append("application_binding_index_matter_id_invalid")
    if not _canonical_identifier(draft_id):
        errors.append("application_binding_index_draft_id_invalid")
    expected, binding_errors = _canonical_index_bindings(
        expected_bindings,
        label="application_binding_index_expected",
        require_canonical_order=False,
    )
    errors.extend(binding_errors)
    if errors:
        return tuple(_unique(errors)), None
    lookup = build_application_finding_binding_index_request(
        matter_id=matter_id, draft_id=draft_id
    )
    resolver = getattr(
        authority, "resolve_application_finding_evidence_binding_index", None
    )
    if authority is None or not callable(resolver):
        return ("application_binding_index_authority_required",), None
    adapter_lookup = deepcopy(lookup)
    try:
        resolution = resolver(adapter_lookup)
    except Exception:
        return ("application_binding_index_authority_error",), None
    if adapter_lookup != lookup:
        return ("application_binding_index_request_mutated",), None
    if not isinstance(resolution, Mapping):
        return ("application_binding_index_resolution_missing",), None
    errors = _exact_mapping_keys(
        resolution,
        _INDEX_RESOLUTION_FIELDS,
        label="application_binding_index_resolution",
    )
    if resolution.get("schema_version") != _SCHEMA_VERSION:
        errors.append("application_binding_index_schema_invalid")
    if resolution.get("status") != "verified":
        errors.append("application_binding_index_not_verified")
    if resolution.get("matter_id") != matter_id:
        errors.append("application_binding_index_matter_id_mismatch")
    if resolution.get("draft_id") != draft_id:
        errors.append("application_binding_index_draft_id_mismatch")
    authoritative, authoritative_errors = _canonical_index_bindings(
        resolution.get("bindings"),
        label="application_binding_index_bindings",
        require_canonical_order=True,
    )
    errors.extend(authoritative_errors)
    if authoritative != expected:
        errors.append("application_binding_index_set_mismatch")
    computed_sha = _index_sha256(
        matter_id=matter_id, draft_id=draft_id, bindings=authoritative
    )
    if resolution.get("binding_index_sha256") != computed_sha:
        errors.append("application_binding_index_sha256_mismatch")
    if not _canonical_identifier(resolution.get("authority_revision_id")):
        errors.append("application_binding_index_authority_revision_id_invalid")
    if not _is_rfc3339(resolution.get("checked_at")):
        errors.append("application_binding_index_checked_at_invalid")
    errors = _unique(errors)
    if errors:
        return tuple(errors), None
    return (), {
        "schema_version": _SCHEMA_VERSION,
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": authoritative,
        "binding_index_sha256": computed_sha,
        "authority_revision_id": resolution["authority_revision_id"],
        "checked_at": resolution["checked_at"],
    }


__all__ = [
    "ApplicationFindingEvidenceBindingAuthority",
    "application_finding_scope_content_fingerprint",
    "build_application_finding_binding_request",
    "build_application_finding_binding_index_request",
    "build_application_finding_scope",
    "build_application_finding_scope_approval_request",
    "build_application_finding_binding_resolution",
    "resolve_application_finding_evidence_binding",
    "build_application_finding_binding_index_resolution",
    "resolve_application_finding_evidence_binding_index",
]
