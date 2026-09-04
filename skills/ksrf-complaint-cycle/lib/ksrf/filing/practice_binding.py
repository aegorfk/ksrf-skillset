"""Host-attested evidence binding for ``practice_claim`` complaint sentences.

The complaint is a lookup request, never the authority.  A host adapter must
reopen current practice-analysis state and return a closed projection of the
native claim/result/wording/refresh records plus the selected IssueCandidate
and its two independent trusted approvals.  This module rechecks every
cross-record identity before emitting an immutable receipt.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from hashlib import sha256
import json
import re
from typing import Any, Mapping, Protocol, Sequence

from .issue_options import (
    issue_approval_requests,
    issue_candidate_content_fingerprint,
    issue_candidate_from_dict,
)
from .storage import canonical_json_bytes


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SENTENCE_ID_RE = re.compile(r"^sent-[0-9a-f]{16}$")
_TRUSTED_APPROVAL_ID_RE = re.compile(r"^trusted-approval:sha256:[0-9a-f]{64}$")
_RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
_PUBLIC_CLAIM_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
_PUBLIC_SOURCE_LOCATOR_RE = re.compile(r"^[A-Za-z0-9._#\[\]-]{1,160}$")

_CLAIM_BINDING_FIELDS = frozenset({"claim_id", "claim_sha256", "source_locator"})
_SELECTED_PROOF_FIELDS = frozenset(
    {
        "position_cards",
        "comparisons",
        "relations",
        "adverse",
        "bridge",
        "human_decision",
        "validation_report",
    }
)
_QUALITY_BINDING_FIELDS = frozenset(
    {"quality_type", "artifact_sha256", "artifact"}
)
_FINALIZATION_RECEIPT_BINDING_FIELDS = frozenset(
    {
        "quality_type",
        "artifact_sha256",
        "artifact",
        "expected_receipt_sha256",
    }
)
_ALLOWED_QUALITY_TYPES = frozenset(
    {
        "chain_stage_propagation",
        "uncertainty_profile",
        "coding_audit_plan",
        "coding_reliability",
        "coding_audit_finalization_receipt",
        "prefiling_refresh",
    }
)
_REQUIRED_QUALITY_TYPES = _ALLOWED_QUALITY_TYPES
_CODING_RELIABILITY_FIELDS = frozenset(
    {
        "schema_version",
        "audit_plan_input_sha256",
        "audit_plan_sha256",
        "audit_plan_frozen",
        "audit_plan_contract_valid",
        "audit_plan_digest_valid",
        "primary_coding_sha256",
        "current_primary_coding_sha256",
        "audit_decisions_sha256",
        "adjudications_sha256",
        "required_candidate_ids",
        "audited_candidate_ids",
        "missing_candidate_ids",
        "same_reviewer_candidate_ids",
        "invalid_binding_candidate_ids",
        "invalid_provenance_candidate_ids",
        "invalid_screening_record_ids",
        "invalid_primary_record_ids",
        "invalid_audit_record_ids",
        "invalid_adjudication_record_ids",
        "field_disagreements",
        "false_exclusion_diagnostics",
        "unresolved_candidate_ids",
        "stale",
        "complete",
        "evidence_sha256",
    }
)
_CODING_AUDIT_FINALIZATION_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "producer",
        "bundle_contract_version",
        "plan_sha256",
        "audit_plan_sha256",
        "codebook_version",
        "source_bundle_manifest_sha256",
        "expected_source_bundle_manifest_sha256",
        "source_bundle_manifest_file_sha256",
        "audit_plan_file_sha256",
        "primary_decisions_file_sha256",
        "review_packet_sha256",
        "codebook_sha256",
        "coding_brief_file_sha256",
        "audit_import_receipt_sha256",
        "expected_audit_import_receipt_sha256",
        "audit_import_receipt_file_sha256",
        "audit_decisions_file_sha256",
        "resolutions_present",
        "resolutions_file_sha256",
        "resolutions_state_sha256",
        "resolved_review_decisions_file_sha256",
        "adjudications_file_sha256",
        "coding_reliability_file_sha256",
        "candidate_ids",
        "required_difference_pairs",
        "resolved_candidate_ids",
        "resolved_field_populations",
        "final_coding_sha256",
        "difference_resolution_bijection_verified",
        "final_quote_literal_presence_verified",
        "final_quote_normalized_presence_verified",
        "quote_locator_review_declared",
        "quote_locator_verified",
        "reliability_complete",
        "source_workspace_reverified",
        "reviewer_identity_authenticated",
        "human_review_authenticated",
        "independence_verified",
        "receipt_authenticated",
        "norm_edition_temporal_applicability_verified",
        "publication_safe",
        "legal_readiness",
        "receipt_sha256",
    }
)
_CODING_RELIABILITY_ORIGIN_FIELDS = frozenset(
    {
        "status",
        "reason_codes",
        "expected_receipt_sha256",
        "reliability_contract_valid",
        "receipt_contract_valid",
        "receipt_self_digest_valid",
        "external_receipt_digest_valid",
        "reliability_file_digest_valid",
        "audit_plan_digest_valid",
        "candidate_population_valid",
        "usable_for_claim",
    }
)
_AUDITED_CODING_FIELDS = frozenset(
    {
        "label",
        "speaker",
        "norm_edition_id",
        "reading_family",
        "relation",
        "reasoning_to_outcome",
        "alternative_grounds",
        "remedy",
    }
)
_CODING_REVIEW_DIFFERENCE_FIELD_ORDER = (
    "label",
    "speaker",
    "norm_edition_id",
    "reading_family",
    "relation",
    "reasoning_to_outcome",
    "alternative_grounds",
    "remedy",
    "proposition",
    "quote",
    "quote_locator",
    "material_facts",
)
_CODING_REVIEW_DIFFERENCE_FIELDS = frozenset(
    _CODING_REVIEW_DIFFERENCE_FIELD_ORDER
)
_EXCLUSION_LABELS = frozenset(
    {
        "party_only",
        "mentioned_only",
        "quoted_not_adopted",
        "false_positive",
        "unclear",
    }
)
_SUBSTANTIVE_LABELS = frozenset({"core_merits", "contextual"})
_CLAIM_STATES = (
    "not_required",
    "required",
    "running",
    "blocked",
    "ready",
    "stale",
)
_BLOCKING_CLAIM_STATES = frozenset({"required", "running", "blocked", "stale"})

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
        "practice_claim_id",
        "issue_option_id",
        "evidence_ids",
        "maximum_supported_inference",
        "practice_binding_sha256",
    }
)
_MATTER_BINDING_FIELDS = frozenset(
    {
        "matter_id",
        "draft_id",
        "case_id",
        "workspace_revision_id",
        "input_bindings_sha256",
    }
)
_PRACTICE_STATE_FIELDS = frozenset(
    {
        "claim_id",
        "revision_id",
        "claim_sha256",
        "source_locator",
        "source_file_sha256",
        "input_bindings_sha256",
        "input_manifest_updated_at",
        "claim_created_at",
        "hypothesis_ids",
        "option_ids",
        "empirical_dimensions",
        "analysis_route",
        "state",
        "draft_blocked",
        "blocking_reasons",
        "next_actions",
        "request_id",
        "handoff_id",
        "maximum_permitted_claim",
        "plan_sha256",
        "evidence_sha256",
        "fingerprint_sha256",
        "wording_review_event_sha256",
        "wording_reviewed_at",
        "result_import_event_sha256",
        "expected_finalization_receipt_sha256",
        "result_imported_at",
        "result_source_sha256",
        "result_created_at",
        "attachment_event_sha256",
        "attachment_attached_at",
        "anchor_checked_at",
        "trust_anchor_sha256",
        "wording_review",
    }
)
_READY_BINDING_FIELDS = (
    "claim_id",
    "revision_id",
    "claim_sha256",
    "source_file_sha256",
    "input_bindings_sha256",
    "input_manifest_updated_at",
    "claim_created_at",
    "handoff_id",
    "plan_sha256",
    "evidence_sha256",
    "fingerprint_sha256",
    "maximum_permitted_claim",
    "wording_review_event_sha256",
    "wording_reviewed_at",
    "result_import_event_sha256",
    "expected_finalization_receipt_sha256",
    "result_imported_at",
    "result_source_sha256",
    "result_created_at",
    "attachment_event_sha256",
    "attachment_attached_at",
    "anchor_checked_at",
    "trust_anchor_sha256",
)
_READY_BINDING_FIELD_SET = frozenset(_READY_BINDING_FIELDS)
_WORDING_REVIEW_FIELDS = frozenset(
    {
        "schema_version",
        "record_type",
        "claim_id",
        "revision_id",
        "claim_sha256",
        "handoff_id",
        "request_id",
        "finding_ids",
        "maximum_permitted_claim",
        "plan_sha256",
        "evidence_sha256",
        "fingerprint_sha256",
        "human_decision_sha256",
        "validation_report_sha256",
        "normative_bridge_sha256",
        "decision",
        "reviewer",
        "reason",
        "wording_text",
        "wording_sha256",
        "wording_source_path",
        "wording_source_sha256",
        "reviewed_at",
        "ledger_id",
        "sequence",
        "previous_event_sha256",
        "event_sha256",
    }
)
_RESULT_FIELDS = frozenset(
    {
        "schema_version",
        "handoff_id",
        "created_at",
        "source_skill",
        "target_skill",
        "run_id",
        "plan_sha256",
        "evidence_sha256",
        "fingerprint_sha256",
        "payload_type",
        "payload",
        "limitations",
    }
)
_RESEARCH_REQUEST_FIELDS = frozenset(
    {
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
    }
)
_RESEARCH_REQUEST_PAYLOAD_FIELDS = frozenset(
    {
        "questions",
        "claim_bindings",
        "claim_set_sha256",
        "request_sha256",
        "claim_questions",
        "drafting_ready",
    }
)
_RESULT_PAYLOAD_FIELDS = frozenset(
    {
        "request_handoff_id",
        "request_sha256",
        "claim_set_sha256",
        "claim_bindings",
        "findings",
        "approval_binding",
        "artifact_manifest",
        "selected_position_set_sha256",
        "selected_proofs",
        "maximum_permitted_claim",
        "limitations",
        "quality_bindings",
        "drafting_ready",
        "supporting_position_card_ids",
        "adverse_position_card_ids",
    }
)
_FINDING_FIELDS = frozenset(
    {
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
)
_APPROVAL_BINDING_FIELDS = frozenset(
    {
        "human_decision_sha256",
        "validation_report_sha256",
        "normative_bridge_sha256",
        "reviewer",
        "approved_at",
    }
)
_REFRESH_FIELDS = frozenset({"required", "valid", "record", "ready_claim_set_sha256"})
_REFRESH_RECORD_FIELDS = frozenset(
    {
        "schema_version",
        "record_type",
        "as_of",
        "corpus_cutoff",
        "reviewer",
        "official_check_ref",
        "ready_claim_bindings",
        "ready_claim_set_sha256",
        "recorded_at",
        "ledger_id",
        "sequence",
        "previous_event_sha256",
        "event_sha256",
    }
)
_FILING_STATE_FIELDS = frozenset(
    {
        "schema_version",
        "case_id",
        "generated_at",
        "stage",
        "input_bindings",
        "counts_by_state",
        "claims",
        "stage_verdict",
        "blocked_claim_ids",
        "allowed_claim_ids",
        "unaffected_claim_ids",
        "global_integrity_errors",
        "prefiling_refresh",
    }
)
_FILING_VALIDATION_FIELDS = frozenset(
    {
        "schema_version",
        "valid",
        "stage",
        "errors",
        "blocked_claim_ids",
        "allowed_claim_ids",
        "unaffected_claim_ids",
        "global_integrity_errors",
        "state",
        "validated_at",
    }
)
_RESOLUTION_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "practice_binding_sha256",
        "matter_binding",
        "practice_state",
        "ready_binding",
        "research_request",
        "result",
        "findings",
        "wording_review",
        "filing_validation",
        "prefiling_refresh",
        "issue_candidate",
        "issue_candidate_fingerprint",
        "issue_approval_requests",
        "trusted_approval_ids",
        "authority_revision_id",
        "checked_at",
    }
)


class PracticeClaimEvidenceBindingAuthority(Protocol):
    """Host boundary for current practice state and complete draft registry."""

    def resolve_practice_claim_evidence_binding(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any] | None: ...

    def resolve_practice_claim_evidence_binding_index(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any] | None: ...


def _digest(value: Any) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def _stable_snapshot(value: Any) -> Any:
    """Detach one authority response from mutable or stateful mappings."""

    if isinstance(value, Mapping):
        keys = list(value.keys())
        return {key: _stable_snapshot(value[key]) for key in keys}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_stable_snapshot(item) for item in value]
    return deepcopy(value)


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _canonical_identifier(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = " ".join(value.split())
    return value if value and value == normalized and "\x00" not in value else ""


def _safe_digest(value: Any) -> str | None:
    try:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        return None
    return sha256(payload).hexdigest()


def _canonical_json_file_sha256(value: Any) -> str | None:
    """Hash the finalizer's canonical JSON file bytes, including exactly one LF."""

    try:
        payload = (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        return None
    return sha256(payload).hexdigest()


def _canonical_identifier_list(value: Any, *, allow_empty: bool) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(bool(_canonical_identifier(item)) for item in value)
        and len(value) == len(set(value))
    )


def _coding_audit_plan_contract_valid(value: Any, *, plan_sha256: Any) -> bool:
    fields = frozenset(
        {
            "schema_version",
            "plan_sha256",
            "screening_sha256",
            "primary_coding_sha256",
            "selection_method",
            "sample_size",
            "exclusion_sample_size",
            "sample_candidate_ids",
            "exclusion_sample_candidate_ids",
            "required_candidate_ids",
            "invalid_screening_record_ids",
            "invalid_primary_record_ids",
            "frozen",
            "audit_plan_sha256",
        }
    )
    if not isinstance(value, Mapping) or frozenset(value) != fields:
        return False
    unsigned = {key: item for key, item in value.items() if key != "audit_plan_sha256"}
    sample = value.get("sample_candidate_ids")
    exclusion = value.get("exclusion_sample_candidate_ids")
    required = value.get("required_candidate_ids")
    sample_size = value.get("sample_size")
    exclusion_size = value.get("exclusion_sample_size")
    return (
        value.get("schema_version") == "1.0"
        and value.get("plan_sha256") == plan_sha256
        and isinstance(plan_sha256, str)
        and bool(_SHA256_RE.fullmatch(plan_sha256))
        and isinstance(value.get("screening_sha256"), str)
        and bool(_SHA256_RE.fullmatch(value["screening_sha256"]))
        and isinstance(value.get("primary_coding_sha256"), str)
        and bool(_SHA256_RE.fullmatch(value["primary_coding_sha256"]))
        and value.get("selection_method") == "canonical_sha256_rank"
        and isinstance(sample_size, int)
        and not isinstance(sample_size, bool)
        and sample_size >= 0
        and isinstance(exclusion_size, int)
        and not isinstance(exclusion_size, bool)
        and exclusion_size >= 0
        and _canonical_identifier_list(sample, allow_empty=True)
        and _canonical_identifier_list(exclusion, allow_empty=True)
        and _canonical_identifier_list(required, allow_empty=False)
        and len(sample) <= sample_size
        and len(exclusion) <= exclusion_size
        and set(required) == set(sample) | set(exclusion)
        and value.get("invalid_screening_record_ids") == []
        and value.get("invalid_primary_record_ids") == []
        and value.get("frozen") is True
        and value.get("audit_plan_sha256") == _safe_digest(unsigned)
    )


def _coding_reliability_contract_valid(value: Any) -> bool:
    if not isinstance(value, Mapping) or frozenset(value) != _CODING_RELIABILITY_FIELDS:
        return False
    unsigned = {key: item for key, item in value.items() if key != "evidence_sha256"}
    if value.get("evidence_sha256") != _safe_digest(unsigned):
        return False
    hash_fields = (
        "audit_plan_input_sha256",
        "audit_plan_sha256",
        "primary_coding_sha256",
        "current_primary_coding_sha256",
        "audit_decisions_sha256",
        "adjudications_sha256",
    )
    empty_fields = (
        "missing_candidate_ids",
        "same_reviewer_candidate_ids",
        "invalid_binding_candidate_ids",
        "invalid_provenance_candidate_ids",
        "invalid_screening_record_ids",
        "invalid_primary_record_ids",
        "invalid_audit_record_ids",
        "invalid_adjudication_record_ids",
        "unresolved_candidate_ids",
    )
    required = value.get("required_candidate_ids")
    audited = value.get("audited_candidate_ids")
    if not (
        value.get("schema_version") == "1.0"
        and all(
            isinstance(value.get(field), str)
            and bool(_SHA256_RE.fullmatch(value[field]))
            for field in hash_fields
        )
        and value.get("audit_plan_frozen") is True
        and value.get("audit_plan_contract_valid") is True
        and value.get("audit_plan_digest_valid") is True
        and value.get("primary_coding_sha256")
        == value.get("current_primary_coding_sha256")
        and _canonical_identifier_list(required, allow_empty=False)
        and _canonical_identifier_list(audited, allow_empty=False)
        and set(required) == set(audited)
        and all(value.get(field) == [] for field in empty_fields)
        and value.get("stale") is False
        and value.get("complete") is True
    ):
        return False
    required_ids = set(required)
    disagreements = value.get("field_disagreements")
    if not isinstance(disagreements, list):
        return False
    disagreement_by_candidate: dict[str, Mapping[str, Any]] = {}
    for item in disagreements:
        candidate_id = item.get("candidate_id") if isinstance(item, Mapping) else None
        fields = item.get("fields") if isinstance(item, Mapping) else None
        if not (
            isinstance(item, Mapping)
            and frozenset(item)
            == frozenset(
                {
                    "candidate_id",
                    "fields",
                    "primary_coding_sha256",
                    "secondary_coding_sha256",
                    "resolved",
                    "adjudication_sha256",
                }
            )
            and isinstance(candidate_id, str)
            and candidate_id in required_ids
            and str(candidate_id) not in disagreement_by_candidate
            and _canonical_identifier_list(fields, allow_empty=False)
            and set(fields).issubset(_AUDITED_CODING_FIELDS)
            and isinstance(item.get("primary_coding_sha256"), str)
            and bool(_SHA256_RE.fullmatch(item["primary_coding_sha256"]))
            and isinstance(item.get("secondary_coding_sha256"), str)
            and bool(_SHA256_RE.fullmatch(item["secondary_coding_sha256"]))
            and item.get("resolved") is True
            and isinstance(item.get("adjudication_sha256"), str)
            and bool(_SHA256_RE.fullmatch(item["adjudication_sha256"]))
        ):
            return False
        disagreement_by_candidate[str(candidate_id)] = item
    empty_adjudications_sha256 = _safe_digest([])
    if (
        (not disagreements and value.get("adjudications_sha256") != empty_adjudications_sha256)
        or (disagreements and value.get("adjudications_sha256") == empty_adjudications_sha256)
    ):
        return False
    false_exclusions = value.get("false_exclusion_diagnostics")
    if not isinstance(false_exclusions, list):
        return False
    seen_false_exclusions: set[str] = set()
    for item in false_exclusions:
        candidate_id = item.get("candidate_id") if isinstance(item, Mapping) else None
        disagreement = disagreement_by_candidate.get(str(candidate_id))
        if not (
            isinstance(item, Mapping)
            and frozenset(item)
            == frozenset(
                {"candidate_id", "primary_label", "secondary_label", "resolved"}
            )
            and isinstance(candidate_id, str)
            and candidate_id in required_ids
            and str(candidate_id) not in seen_false_exclusions
            and isinstance(item.get("primary_label"), str)
            and item.get("primary_label") in _EXCLUSION_LABELS
            and isinstance(item.get("secondary_label"), str)
            and item.get("secondary_label") in _SUBSTANTIVE_LABELS
            and item.get("resolved") is True
            and disagreement is not None
            and "label" in disagreement.get("fields", [])
        ):
            return False
        seen_false_exclusions.add(str(candidate_id))
    return True


def _finalization_receipt_contract_valid(value: Any) -> bool:
    if (
        not isinstance(value, Mapping)
        or frozenset(value) != _CODING_AUDIT_FINALIZATION_RECEIPT_FIELDS
    ):
        return False
    unsigned = {key: item for key, item in value.items() if key != "receipt_sha256"}
    if value.get("receipt_sha256") != _safe_digest(unsigned):
        return False
    hash_fields = (
        "plan_sha256",
        "audit_plan_sha256",
        "source_bundle_manifest_sha256",
        "expected_source_bundle_manifest_sha256",
        "source_bundle_manifest_file_sha256",
        "audit_plan_file_sha256",
        "primary_decisions_file_sha256",
        "review_packet_sha256",
        "codebook_sha256",
        "coding_brief_file_sha256",
        "audit_import_receipt_sha256",
        "expected_audit_import_receipt_sha256",
        "audit_import_receipt_file_sha256",
        "audit_decisions_file_sha256",
        "resolutions_state_sha256",
        "resolved_review_decisions_file_sha256",
        "adjudications_file_sha256",
        "coding_reliability_file_sha256",
        "final_coding_sha256",
    )
    candidate_ids = value.get("candidate_ids")
    if not (
        value.get("schema_version") == "1.0"
        and value.get("artifact_type") == "coding_audit_finalization_receipt"
        and value.get("producer")
        == "judicial_meaning.quality.coding_audit_finalize"
        and value.get("bundle_contract_version") in {"1.1", "1.2"}
        and value.get("codebook_version") == "1.0"
        and all(
            isinstance(value.get(field), str)
            and bool(_SHA256_RE.fullmatch(value[field]))
            for field in hash_fields
        )
        and value.get("source_bundle_manifest_sha256")
        == value.get("expected_source_bundle_manifest_sha256")
        and value.get("audit_import_receipt_sha256")
        == value.get("expected_audit_import_receipt_sha256")
        and _canonical_identifier_list(candidate_ids, allow_empty=False)
        and all(
            re.fullmatch(r"audit-candidate-sha256:[0-9a-f]{64}", item)
            for item in candidate_ids
        )
    ):
        return False
    pairs = value.get("required_difference_pairs")
    pair_values: list[tuple[str, str]] = []
    if not isinstance(pairs, list):
        return False
    for item in pairs:
        if not (
            isinstance(item, Mapping)
            and frozenset(item) == frozenset({"candidate_id", "field"})
            and item.get("candidate_id") in candidate_ids
            and isinstance(item.get("field"), str)
            and item.get("field") in _CODING_REVIEW_DIFFERENCE_FIELDS
        ):
            return False
        pair_values.append((str(item["candidate_id"]), str(item["field"])))
    pair_set = set(pair_values)
    expected_pairs = [
        {"candidate_id": candidate_id, "field": field}
        for candidate_id in candidate_ids
        for field in _CODING_REVIEW_DIFFERENCE_FIELD_ORDER
        if (candidate_id, field) in pair_set
    ]
    expected_resolved_ids = [
        candidate_id
        for candidate_id in candidate_ids
        if any(item["candidate_id"] == candidate_id for item in expected_pairs)
    ]
    expected_populations = [
        {
            "candidate_id": candidate_id,
            "fields": [
                item["field"]
                for item in expected_pairs
                if item["candidate_id"] == candidate_id
            ],
        }
        for candidate_id in expected_resolved_ids
    ]
    resolutions_present = value.get("resolutions_present")
    resolutions_file_sha256 = value.get("resolutions_file_sha256")
    true_fields = (
        "difference_resolution_bijection_verified",
        "final_quote_literal_presence_verified",
        "final_quote_normalized_presence_verified",
        "reliability_complete",
    )
    false_fields = (
        "quote_locator_verified",
        "source_workspace_reverified",
        "reviewer_identity_authenticated",
        "human_review_authenticated",
        "independence_verified",
        "receipt_authenticated",
        "norm_edition_temporal_applicability_verified",
        "publication_safe",
        "legal_readiness",
    )
    return (
        len(pair_values) == len(pair_set)
        and pairs == expected_pairs
        and value.get("resolved_candidate_ids") == expected_resolved_ids
        and value.get("resolved_field_populations") == expected_populations
        and isinstance(resolutions_present, bool)
        and resolutions_present is bool(expected_pairs)
        and (
            (resolutions_present and isinstance(resolutions_file_sha256, str)
             and bool(_SHA256_RE.fullmatch(resolutions_file_sha256)))
            or (not resolutions_present and resolutions_file_sha256 is None)
        )
        and value.get("resolutions_state_sha256")
        == _safe_digest(
            {"present": resolutions_present, "file_sha256": resolutions_file_sha256}
        )
        and value.get("quote_locator_review_declared") is bool(expected_pairs)
        and all(value.get(field) is True for field in true_fields)
        and all(value.get(field) is False for field in false_fields)
    )


def _native_quality_binding_errors(
    value: Any,
    *,
    expected_receipt_sha256: Any,
    plan_sha256: Any,
) -> list[str]:
    errors: list[str] = []
    if not (
        isinstance(expected_receipt_sha256, str)
        and _SHA256_RE.fullmatch(expected_receipt_sha256)
    ):
        errors.append("practice_native_reliability_anchor_missing")
    if not isinstance(value, list):
        return _unique([*errors, "practice_native_quality_bindings_invalid"])
    by_type: dict[str, Mapping[str, Any]] = {}
    for binding in value:
        if not isinstance(binding, Mapping):
            errors.append("practice_native_quality_binding_shape_invalid")
            continue
        quality_type = binding.get("quality_type")
        expected_fields = (
            _FINALIZATION_RECEIPT_BINDING_FIELDS
            if quality_type == "coding_audit_finalization_receipt"
            else _QUALITY_BINDING_FIELDS
        )
        if frozenset(binding) != expected_fields:
            errors.append("practice_native_quality_binding_shape_invalid")
            continue
        if (
            not isinstance(quality_type, str)
            or quality_type not in _REQUIRED_QUALITY_TYPES
            or quality_type in by_type
        ):
            errors.append("practice_native_quality_binding_population_invalid")
            continue
        artifact = binding.get("artifact")
        if (
            not isinstance(artifact, Mapping)
            or binding.get("artifact_sha256") != _safe_digest(artifact)
        ):
            errors.append("practice_native_quality_binding_digest_invalid")
            continue
        by_type[str(quality_type)] = binding
    if set(by_type) != set(_REQUIRED_QUALITY_TYPES) or len(value) != len(
        _REQUIRED_QUALITY_TYPES
    ):
        errors.append("practice_native_quality_binding_population_invalid")
    audit_plan_binding = by_type.get("coding_audit_plan")
    reliability_binding = by_type.get("coding_reliability")
    receipt_binding = by_type.get("coding_audit_finalization_receipt")
    profile_binding = by_type.get("uncertainty_profile")
    if not all(
        (audit_plan_binding, reliability_binding, receipt_binding, profile_binding)
    ):
        return _unique(errors)
    audit_plan = audit_plan_binding["artifact"]
    reliability = reliability_binding["artifact"]
    receipt = receipt_binding["artifact"]
    profile = profile_binding["artifact"]
    if not _coding_audit_plan_contract_valid(audit_plan, plan_sha256=plan_sha256):
        errors.append("practice_native_audit_plan_invalid")
    if not _coding_reliability_contract_valid(reliability):
        errors.append("practice_native_coding_reliability_invalid")
    if not _finalization_receipt_contract_valid(receipt):
        errors.append("practice_native_finalization_receipt_invalid")
    transported_expected = receipt_binding.get("expected_receipt_sha256")
    if transported_expected != expected_receipt_sha256:
        errors.append("practice_native_reliability_anchor_mismatch")
    if receipt.get("receipt_sha256") != transported_expected:
        errors.append("practice_native_finalization_receipt_digest_mismatch")
    if receipt.get("coding_reliability_file_sha256") != _canonical_json_file_sha256(
        reliability
    ):
        errors.append("practice_native_coding_reliability_file_digest_mismatch")
    if (
        reliability.get("audit_plan_input_sha256") != _safe_digest(audit_plan)
        or receipt.get("audit_plan_sha256")
        != reliability.get("audit_plan_sha256")
        or reliability.get("audit_plan_sha256")
        != audit_plan.get("audit_plan_sha256")
        or reliability.get("primary_coding_sha256")
        != audit_plan.get("primary_coding_sha256")
    ):
        errors.append("practice_native_audit_plan_binding_mismatch")
    if (
        receipt.get("candidate_ids")
        != reliability.get("required_candidate_ids")
        or reliability.get("required_candidate_ids")
        != audit_plan.get("required_candidate_ids")
    ):
        errors.append("practice_native_candidate_population_mismatch")
    if receipt.get("plan_sha256") != plan_sha256:
        errors.append("practice_native_current_plan_mismatch")
    origin = profile.get("coding_reliability_origin")
    input_sha256s = profile.get("input_sha256s")
    origin_valid = (
        isinstance(origin, Mapping)
        and frozenset(origin) == _CODING_RELIABILITY_ORIGIN_FIELDS
        and origin.get("status") == "native_finalization_bound"
        and origin.get("reason_codes") == []
        and origin.get("expected_receipt_sha256") == transported_expected
        and all(
            origin.get(field) is True
            for field in _CODING_RELIABILITY_ORIGIN_FIELDS
            - {"status", "reason_codes", "expected_receipt_sha256"}
        )
    )
    if not (
        origin_valid
        and isinstance(input_sha256s, Mapping)
        and input_sha256s.get("coding_reliability")
        == reliability_binding.get("artifact_sha256")
        and input_sha256s.get("coding_audit_finalization_receipt")
        == receipt_binding.get("artifact_sha256")
        and input_sha256s.get("expected_finalization_receipt_sha256")
        == transported_expected
    ):
        errors.append("practice_native_uncertainty_profile_origin_mismatch")
    return _unique(errors)


def _exact_text(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        return ""
    return value


def _is_rfc3339(value: Any) -> bool:
    if not isinstance(value, str) or not _RFC3339_RE.fullmatch(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _parse_rfc3339(value: Any) -> datetime | None:
    if not _is_rfc3339(value):
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _validate_ledger_event(value: Mapping[str, Any], *, label: str) -> list[str]:
    """Validate the self-contained link carried by one projected ledger event."""

    errors: list[str] = []
    if not _canonical_identifier(value.get("ledger_id")):
        errors.append(f"{label}_ledger_id_invalid")
    sequence = value.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        errors.append(f"{label}_sequence_invalid")
    previous = value.get("previous_event_sha256")
    if sequence == 1:
        if previous is not None:
            errors.append(f"{label}_previous_event_sha256_invalid")
    elif isinstance(sequence, int) and sequence > 1:
        if not isinstance(previous, str) or not _SHA256_RE.fullmatch(previous):
            errors.append(f"{label}_previous_event_sha256_invalid")
    event_sha = value.get("event_sha256")
    if not isinstance(event_sha, str) or not _SHA256_RE.fullmatch(event_sha):
        errors.append(f"{label}_event_sha256_invalid")
    else:
        unsigned = {key: deepcopy(item) for key, item in value.items() if key != "event_sha256"}
        if event_sha != _digest(unsigned):
            errors.append(f"{label}_event_sha256_mismatch")
    return _unique(errors)


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
        (
            {
                "path": path,
                "present": True,
                "bytes": len(canonical_json_bytes(content)),
                "sha256": _digest(content),
            }
            for path, content in virtual.items()
        ),
        key=lambda item: item["path"],
    )


def _position_id(value: Mapping[str, Any]) -> str:
    for field in ("position_card_id", "id"):
        identifier = _canonical_identifier(value.get(field))
        if identifier:
            return identifier
    return ""


def _exact_mapping_keys(value: Mapping[str, Any], expected: frozenset[str], *, label: str) -> list[str]:
    errors: list[str] = []
    raw_keys = list(value.keys())
    if any(not isinstance(key, str) for key in raw_keys):
        errors.append(f"{label}_field_name_invalid")
    actual = frozenset(key for key in raw_keys if isinstance(key, str))
    if missing := sorted(expected - actual):
        errors.extend(f"{label}_field_missing:{field}" for field in missing)
    if extra := sorted(actual - expected):
        errors.extend(f"{label}_field_unexpected:{field}" for field in extra)
    return errors


def _identifier_list(
    value: Any,
    *,
    label: str,
    allow_empty: bool = True,
    require_list: bool = False,
) -> tuple[list[str], list[str]]:
    if require_list:
        valid_container = isinstance(value, list)
    else:
        valid_container = isinstance(value, Sequence) and not isinstance(
            value, (str, bytes)
        )
    if not valid_container:
        return [], [f"{label}_invalid"]
    result: list[str] = []
    errors: list[str] = []
    for ordinal, item in enumerate(value, start=1):
        if not _canonical_identifier(item):
            errors.append(f"{label}_item_invalid:{ordinal}")
        else:
            assert isinstance(item, str)
            result.append(item)
    if not allow_empty and not result:
        errors.append(f"{label}_empty")
    if len(result) != len(set(result)):
        errors.append(f"{label}_duplicate")
    return result, errors


def _sha_list(value: Any, *, label: str, allow_empty: bool = False) -> tuple[list[str], list[str]]:
    items, errors = _identifier_list(value, label=label, allow_empty=allow_empty)
    for ordinal, item in enumerate(items, start=1):
        if not _SHA256_RE.fullmatch(item):
            errors.append(f"{label}_sha256_invalid:{ordinal}")
    return items, _unique(errors)


def _public_claim_id(value: str) -> str:
    if _PUBLIC_CLAIM_ID_RE.fullmatch(value) and "@" not in value:
        return value
    return "claim-" + _digest({"private_claim_id": value})[:24]


def _public_source_locator(value: str) -> str:
    if (
        _PUBLIC_SOURCE_LOCATOR_RE.fullmatch(value)
        and "/" not in value
        and "\\" not in value
        and "@" not in value
    ):
        return value
    return "source-" + _digest({"private_source_locator": value})[:24]


def build_practice_claim_binding_request(
    *,
    matter_id: Any,
    draft_id: Any,
    sentence_id: Any,
    section_code: Any,
    sentence_text: Any,
    claim_id: Any,
    practice_claim_id: Any,
    issue_option_id: Any,
    evidence_ids: Any,
    maximum_supported_inference: Any,
) -> dict[str, Any]:
    """Build a strict exact-byte request for one empirical practice sentence."""

    errors: list[str] = []
    for label, value in (
        ("matter_id", matter_id),
        ("draft_id", draft_id),
        ("section_code", section_code),
        ("claim_id", claim_id),
        ("practice_claim_id", practice_claim_id),
        ("issue_option_id", issue_option_id),
    ):
        if not _canonical_identifier(value):
            errors.append(f"practice_binding_{label}_invalid")
    if not isinstance(sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(sentence_id):
        errors.append("practice_binding_sentence_id_invalid")
    if not _exact_text(sentence_text):
        errors.append("practice_binding_sentence_text_invalid")
    if not _exact_text(maximum_supported_inference):
        errors.append("practice_binding_maximum_supported_inference_invalid")
    findings, finding_errors = _sha_list(
        evidence_ids, label="practice_binding_evidence_ids", allow_empty=False
    )
    errors.extend(finding_errors)
    if claim_id == practice_claim_id:
        errors.append("practice_binding_claim_identity_ambiguous")
    if errors:
        raise ValueError(", ".join(_unique(errors)))
    basis = {
        "schema_version": "1.0.0",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "sentence_id": sentence_id,
        "section_code": section_code,
        "sentence_text": sentence_text,
        "sentence_text_sha256": sha256(sentence_text.encode("utf-8")).hexdigest(),
        "claim_id": claim_id,
        "practice_claim_id": practice_claim_id,
        "issue_option_id": issue_option_id,
        "evidence_ids": sorted(findings),
        "maximum_supported_inference": maximum_supported_inference,
    }
    return {**basis, "practice_binding_sha256": _digest(basis)}


def _canonical_request(value: Any) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    if not isinstance(value, Mapping):
        return None, ("practice_binding_request_invalid",)
    errors = _exact_mapping_keys(value, _REQUEST_FIELDS, label="practice_binding_request")
    try:
        rebuilt = build_practice_claim_binding_request(
            matter_id=value.get("matter_id"),
            draft_id=value.get("draft_id"),
            sentence_id=value.get("sentence_id"),
            section_code=value.get("section_code"),
            sentence_text=value.get("sentence_text"),
            claim_id=value.get("claim_id"),
            practice_claim_id=value.get("practice_claim_id"),
            issue_option_id=value.get("issue_option_id"),
            evidence_ids=value.get("evidence_ids"),
            maximum_supported_inference=value.get("maximum_supported_inference"),
        )
    except ValueError as exc:
        errors.extend(str(exc).split(", "))
        rebuilt = None
    if rebuilt is not None and dict(value) != rebuilt:
        errors.append("practice_binding_request_not_canonical")
    errors = _unique(errors)
    return (rebuilt if not errors else None), tuple(errors)


def _ready_binding_from_state(state: Mapping[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(state.get(field)) for field in _READY_BINDING_FIELDS}


def _validate_practice_state(
    value: Any, *, request: Mapping[str, Any], label: str = "practice_state"
) -> tuple[Mapping[str, Any] | None, list[str]]:
    if not isinstance(value, Mapping):
        return None, [f"{label}_missing"]
    errors = _exact_mapping_keys(value, _PRACTICE_STATE_FIELDS, label=label)
    if value.get("claim_id") != request.get("practice_claim_id"):
        errors.append(f"{label}_claim_id_mismatch")
    if value.get("state") != "ready" or value.get("draft_blocked") is not False:
        errors.append("practice_state_not_ready" if label == "practice_state" else f"{label}_not_ready")
    if value.get("blocking_reasons") != []:
        errors.append(f"{label}_blocking_reasons_present")
    if value.get("next_actions") != []:
        errors.append(f"{label}_next_actions_present")
    if not _exact_text(value.get("source_locator")):
        errors.append(f"{label}_source_locator_invalid")
    if not isinstance(value.get("request_id"), str) or not _SHA256_RE.fullmatch(
        value.get("request_id", "")
    ):
        errors.append(f"{label}_request_id_invalid")
    option_ids, option_errors = _identifier_list(
        value.get("option_ids"),
        label=f"{label}_option_ids",
        allow_empty=False,
        require_list=True,
    )
    errors.extend(option_errors)
    if option_ids != sorted(option_ids):
        errors.append(f"{label}_option_ids_not_canonical")
    if request.get("issue_option_id") not in option_ids:
        errors.append(f"{label}_issue_option_missing")
    for field in ("hypothesis_ids", "empirical_dimensions"):
        identifiers, identifier_errors = _identifier_list(
            value.get(field),
            label=f"{label}_{field}",
            require_list=True,
        )
        errors.extend(identifier_errors)
        if identifiers != sorted(identifiers):
            errors.append(f"{label}_{field}_not_canonical")
    if not _canonical_identifier(value.get("analysis_route")):
        errors.append(f"{label}_analysis_route_invalid")
    for field in (
        "revision_id",
        "claim_sha256",
        "source_file_sha256",
        "input_bindings_sha256",
        "handoff_id",
        "plan_sha256",
        "evidence_sha256",
        "fingerprint_sha256",
        "wording_review_event_sha256",
        "result_import_event_sha256",
        "expected_finalization_receipt_sha256",
        "result_source_sha256",
        "attachment_event_sha256",
        "trust_anchor_sha256",
    ):
        if not isinstance(value.get(field), str) or not _SHA256_RE.fullmatch(value[field]):
            errors.append(f"{label}_{field}_invalid")
    for field in (
        "input_manifest_updated_at",
        "claim_created_at",
        "wording_reviewed_at",
        "result_imported_at",
        "result_created_at",
        "attachment_attached_at",
        "anchor_checked_at",
    ):
        if not _is_rfc3339(value.get(field)):
            errors.append(f"{label}_{field}_invalid")
    if value.get("maximum_permitted_claim") != request.get("maximum_supported_inference"):
        errors.append(f"{label}_maximum_permitted_claim_mismatch")
    if not _exact_text(value.get("maximum_permitted_claim")):
        errors.append(f"{label}_maximum_permitted_claim_invalid")
    return value, _unique(errors)


def _validate_wording_review(value: Any, *, request: Mapping[str, Any], state: Mapping[str, Any]) -> list[str]:
    if not isinstance(value, Mapping):
        return ["practice_wording_review_missing"]
    errors = _exact_mapping_keys(value, _WORDING_REVIEW_FIELDS, label="practice_wording_review")
    expected = {
        "schema_version": "1.0",
        "record_type": "wording_review",
        "claim_id": request.get("practice_claim_id"),
        "revision_id": state.get("revision_id"),
        "claim_sha256": state.get("claim_sha256"),
        "handoff_id": state.get("handoff_id"),
        "request_id": state.get("request_id"),
        "maximum_permitted_claim": request.get("maximum_supported_inference"),
        "plan_sha256": state.get("plan_sha256"),
        "evidence_sha256": state.get("evidence_sha256"),
        "fingerprint_sha256": state.get("fingerprint_sha256"),
        "decision": "within_limit",
        "wording_text": request.get("sentence_text"),
        "wording_sha256": _digest(request.get("sentence_text")),
        "wording_source_sha256": state.get("source_file_sha256"),
        "event_sha256": state.get("wording_review_event_sha256"),
        "reviewed_at": state.get("wording_reviewed_at"),
    }
    for field, expected_value in expected.items():
        if value.get(field) != expected_value:
            errors.append(f"practice_wording_review_binding_mismatch:{field}")
    findings, finding_errors = _sha_list(
        value.get("finding_ids"), label="practice_wording_review_finding_ids", allow_empty=False
    )
    errors.extend(finding_errors)
    if sorted(findings) != list(request.get("evidence_ids") or ()):
        errors.append("practice_wording_review_finding_set_mismatch")
    for field in (
        "human_decision_sha256",
        "validation_report_sha256",
        "normative_bridge_sha256",
        "wording_source_sha256",
        "event_sha256",
    ):
        if not isinstance(value.get(field), str) or not _SHA256_RE.fullmatch(value[field]):
            errors.append(f"practice_wording_review_{field}_invalid")
    if not _is_rfc3339(value.get("reviewed_at")):
        errors.append("practice_wording_review_reviewed_at_invalid")
    if not _canonical_identifier(value.get("reviewer")):
        errors.append("practice_wording_review_reviewer_invalid")
    if not _exact_text(value.get("reason")):
        errors.append("practice_wording_review_reason_invalid")
    if not _exact_text(value.get("wording_source_path")):
        errors.append("practice_wording_review_source_path_invalid")
    errors.extend(
        _validate_ledger_event(value, label="practice_wording_review")
    )
    return _unique(errors)


def _canonical_result_claim_bindings(
    value: Any,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(value, list):
        return [], ["practice_result_claim_bindings_invalid"]
    bindings: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for ordinal, raw in enumerate(value, start=1):
        label = f"practice_result_claim_binding:{ordinal}"
        if not isinstance(raw, Mapping):
            errors.append(f"{label}_invalid")
            continue
        errors.extend(_exact_mapping_keys(raw, _CLAIM_BINDING_FIELDS, label=label))
        claim_id = _canonical_identifier(raw.get("claim_id"))
        if not claim_id:
            errors.append(f"{label}_claim_id_invalid")
            continue
        if claim_id in seen:
            errors.append(f"practice_result_claim_binding_duplicate:{claim_id}")
            continue
        seen.add(claim_id)
        if not isinstance(raw.get("claim_sha256"), str) or not _SHA256_RE.fullmatch(
            raw.get("claim_sha256", "")
        ):
            errors.append(f"{label}_claim_sha256_invalid")
        if not _exact_text(raw.get("source_locator")):
            errors.append(f"{label}_source_locator_invalid")
        bindings.append(deepcopy(dict(raw)))
    canonical = sorted(bindings, key=lambda item: item["claim_id"])
    if bindings != canonical:
        errors.append("practice_result_claim_bindings_not_canonical")
    if not canonical:
        errors.append("practice_result_claim_bindings_empty")
    return canonical, _unique(errors)


def _validate_research_request(
    value: Any,
    *,
    state: Mapping[str, Any],
    result_payload: Mapping[str, Any],
) -> list[str]:
    """Validate the exact native request to which the v2 result was answered."""

    if not isinstance(value, Mapping):
        return ["practice_research_request_missing"]
    errors = _exact_mapping_keys(
        value, _RESEARCH_REQUEST_FIELDS, label="practice_research_request"
    )
    for field, expected in (
        ("schema_version", "2.0"),
        ("source_skill", "ksrf-complaint-cycle"),
        ("target_skill", "ksrf-cassation-judicial-meaning"),
        ("payload_type", "unproven_research_questions"),
    ):
        if value.get(field) != expected:
            errors.append(f"practice_research_request_identity_mismatch:{field}")
    if not _is_rfc3339(value.get("created_at")):
        errors.append("practice_research_request_created_at_invalid")
    for field in ("run_id",):
        if not _canonical_identifier(value.get(field)):
            errors.append(f"practice_research_request_{field}_invalid")
    for field in ("plan_sha256", "evidence_sha256", "handoff_id"):
        if not isinstance(value.get(field), str) or not _SHA256_RE.fullmatch(
            value.get(field, "")
        ):
            errors.append(f"practice_research_request_{field}_invalid")
    unsigned = {
        key: deepcopy(item) for key, item in value.items() if key != "handoff_id"
    }
    if value.get("handoff_id") != _digest(unsigned):
        errors.append("practice_research_request_handoff_id_mismatch")
    if value.get("handoff_id") != state.get("request_id"):
        errors.append("practice_research_request_state_id_mismatch")

    payload = value.get("payload")
    if not isinstance(payload, Mapping):
        return _unique([*errors, "practice_research_request_payload_missing"])
    errors.extend(
        _exact_mapping_keys(
            payload,
            _RESEARCH_REQUEST_PAYLOAD_FIELDS,
            label="practice_research_request_payload",
        )
    )
    if payload.get("drafting_ready") is not False:
        errors.append("practice_research_request_not_neutral")
    questions = payload.get("questions")
    if (
        not isinstance(questions, list)
        or not questions
        or any(not _exact_text(item) for item in questions)
    ):
        errors.append("practice_research_request_questions_invalid")
        questions = []
    bindings, binding_errors = _canonical_result_claim_bindings(
        payload.get("claim_bindings")
    )
    errors.extend(
        error.replace("practice_result_", "practice_research_request_", 1)
        for error in binding_errors
    )
    claim_set_sha256 = _digest(bindings)
    if payload.get("claim_set_sha256") != claim_set_sha256:
        errors.append("practice_research_request_claim_set_sha256_mismatch")
    core = {
        "questions": questions,
        "claim_bindings": bindings,
        "claim_set_sha256": claim_set_sha256,
    }
    request_sha256 = _digest(core)
    if payload.get("request_sha256") != request_sha256:
        errors.append("practice_research_request_sha256_mismatch")
    if value.get("plan_sha256") != request_sha256:
        errors.append("practice_research_request_plan_sha256_mismatch")
    if result_payload.get("request_handoff_id") != value.get("handoff_id"):
        errors.append("practice_result_request_handoff_id_request_mismatch")
    if result_payload.get("request_sha256") != request_sha256:
        errors.append("practice_result_request_sha256_mismatch")
    if result_payload.get("claim_set_sha256") != claim_set_sha256:
        errors.append("practice_result_request_claim_set_sha256_mismatch")
    if result_payload.get("claim_bindings") != bindings:
        errors.append("practice_result_request_claim_bindings_mismatch")

    claim_questions = payload.get("claim_questions")
    if not isinstance(claim_questions, list) or len(claim_questions) != len(bindings):
        errors.append("practice_research_request_claim_questions_invalid")
    else:
        projected_ids: list[str] = []
        seen_question_ids: set[str] = set()
        question_values = set(questions)
        expected_fields = frozenset(
            {"claim_id", "question_id", "question", "disconfirmation_prompts"}
        )
        for ordinal, claim_question in enumerate(claim_questions, start=1):
            if not isinstance(claim_question, Mapping):
                errors.append(
                    f"practice_research_request_claim_question_invalid:{ordinal}"
                )
                continue
            errors.extend(
                _exact_mapping_keys(
                    claim_question,
                    expected_fields,
                    label=f"practice_research_request_claim_question:{ordinal}",
                )
            )
            claim_id = _canonical_identifier(claim_question.get("claim_id"))
            if claim_id:
                projected_ids.append(claim_id)
            question = claim_question.get("question")
            if question not in question_values:
                errors.append(
                    f"practice_research_request_claim_question_not_in_questions:{ordinal}"
                )
            expected_question_id = _digest(
                {"claim_id": claim_question.get("claim_id"), "question": question}
            )
            if claim_question.get("question_id") != expected_question_id:
                errors.append(
                    f"practice_research_request_claim_question_id_mismatch:{ordinal}"
                )
            elif expected_question_id in seen_question_ids:
                errors.append(
                    f"practice_research_request_claim_question_id_duplicate:{ordinal}"
                )
            else:
                seen_question_ids.add(expected_question_id)
            if not _exact_text(question):
                errors.append(
                    f"practice_research_request_claim_question_text_invalid:{ordinal}"
                )
            prompts = claim_question.get("disconfirmation_prompts")
            if (
                not isinstance(prompts, list)
                or not prompts
                or any(not _exact_text(item) for item in prompts)
            ):
                errors.append(
                    f"practice_research_request_disconfirmation_prompts_invalid:{ordinal}"
                )
        binding_ids = [str(item.get("claim_id")) for item in bindings]
        if len(projected_ids) != len(set(projected_ids)) or set(projected_ids) != set(
            binding_ids
        ):
            errors.append("practice_research_request_claim_question_set_mismatch")
    limitations = value.get("limitations")
    if (
        not isinstance(limitations, list)
        or not limitations
        or any(not _exact_text(item) for item in limitations)
    ):
        errors.append("practice_research_request_limitations_invalid")
    return _unique(errors)


def _validate_result_proof_bundle(
    *,
    payload: Mapping[str, Any],
    result: Mapping[str, Any],
    bindings: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Recheck native v2 proof closure instead of trusting copied digests."""

    errors: list[str] = []
    selected = payload.get("selected_proofs")
    if not isinstance(selected, Mapping):
        return ["practice_result_selected_proofs_missing"]
    errors.extend(
        _exact_mapping_keys(
            selected, _SELECTED_PROOF_FIELDS, label="practice_result_selected_proofs"
        )
    )
    for field in ("position_cards", "comparisons", "relations"):
        items = selected.get(field)
        if (
            not isinstance(items, list)
            or not items
            or any(not isinstance(item, Mapping) for item in items)
        ):
            errors.append(f"practice_result_selected_proofs_{field}_invalid")
    for field in ("adverse", "bridge", "human_decision", "validation_report"):
        if not isinstance(selected.get(field), Mapping):
            errors.append(f"practice_result_selected_proofs_{field}_invalid")
    if errors:
        return _unique(errors)

    position_cards = selected["position_cards"]
    comparisons = selected["comparisons"]
    relations = selected["relations"]
    adverse = selected["adverse"]
    bridge = selected["bridge"]
    human_decision = selected["human_decision"]
    validation_report = selected["validation_report"]
    selected_set = {
        "position_cards": position_cards,
        "comparisons": comparisons,
        "relations": relations,
    }
    if payload.get("selected_position_set_sha256") != _digest(selected_set):
        errors.append("practice_result_selected_position_set_sha256_mismatch")

    manifest = payload.get("artifact_manifest")
    expected_files = _proof_file_manifest(selected)
    if not isinstance(manifest, Mapping):
        errors.append("practice_result_artifact_manifest_missing")
    else:
        manifest_fields = frozenset({"files", "manifest_sha256"})
        errors.extend(
            _exact_mapping_keys(
                manifest, manifest_fields, label="practice_result_artifact_manifest"
            )
        )
        if manifest.get("files") != expected_files:
            errors.append("practice_result_artifact_manifest_files_mismatch")
        if manifest.get("manifest_sha256") != _digest(expected_files):
            errors.append("practice_result_artifact_manifest_sha256_mismatch")

    approval = payload.get("approval_binding")
    if not isinstance(approval, Mapping):
        approval = {}
        errors.append("practice_result_approval_binding_missing")
    expected_approval = {
        "human_decision_sha256": _digest(human_decision),
        "validation_report_sha256": _digest(validation_report),
        "normative_bridge_sha256": _digest(bridge),
    }
    for field, expected in expected_approval.items():
        if approval.get(field) != expected:
            errors.append(f"practice_result_selected_proof_mismatch:{field}")

    if (
        validation_report.get("schema_version") != "2.0"
        or validation_report.get("gate") != "drafting_ready"
        or validation_report.get("valid") is not True
    ):
        errors.append("practice_result_validation_report_not_drafting_ready")
    if adverse.get("complete") is not True:
        errors.append("practice_result_adverse_review_incomplete")
    human_status = (
        human_decision.get("decision")
        or human_decision.get("status")
        or human_decision.get("review_state")
    )
    if human_status not in {"approved", "evidence_reviewed"}:
        errors.append("practice_result_human_decision_not_approved")
    if human_decision.get("reviewer") != approval.get("reviewer"):
        errors.append("practice_result_human_decision_reviewer_mismatch")
    decision_candidate_ids, decision_errors = _identifier_list(
        human_decision.get("candidate_ids"),
        label="practice_result_human_decision_candidate_ids",
        allow_empty=False,
        require_list=True,
    )
    errors.extend(decision_errors)

    position_ids: set[str] = set()
    for ordinal, card in enumerate(position_cards, start=1):
        position_id = _position_id(card)
        if not position_id:
            errors.append(f"practice_result_position_card_id_invalid:{ordinal}")
        elif position_id in position_ids:
            errors.append(f"practice_result_position_card_duplicate:{position_id}")
        else:
            position_ids.add(position_id)
        if card.get("human_review") != "approved" and card.get("review_state") != "approved":
            errors.append(f"practice_result_position_card_not_approved:{ordinal}")

    supporting, supporting_errors = _identifier_list(
        payload.get("supporting_position_card_ids"),
        label="practice_result_supporting_position_card_ids",
        allow_empty=False,
        require_list=True,
    )
    adverse_ids, adverse_errors = _identifier_list(
        payload.get("adverse_position_card_ids"),
        label="practice_result_adverse_position_card_ids",
        require_list=True,
    )
    errors.extend(supporting_errors)
    errors.extend(adverse_errors)
    if supporting != sorted(supporting):
        errors.append("practice_result_supporting_position_card_ids_not_canonical")
    if adverse_ids != sorted(adverse_ids):
        errors.append("practice_result_adverse_position_card_ids_not_canonical")
    for position_id in sorted(set([*supporting, *adverse_ids]) - position_ids):
        errors.append(f"practice_result_position_card_unknown:{position_id}")

    comparison_ids = {
        str(item.get("position_card_id"))
        for item in comparisons
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
        for item in relations
        if item.get("stale") is not True
        and (
            item.get("human_review") == "approved"
            or item.get("review_state") == "approved"
        )
    }
    for position_id in supporting:
        if position_id not in comparison_ids or relation_by_position.get(position_id) != "supports":
            errors.append(f"practice_result_supporting_proof_invalid:{position_id}")
    for position_id in adverse_ids:
        if position_id not in comparison_ids or relation_by_position.get(position_id) != "adverse":
            errors.append(f"practice_result_adverse_proof_invalid:{position_id}")

    maximum = payload.get("maximum_permitted_claim")
    if bridge.get("maximum_permitted_claim") != maximum:
        errors.append("practice_result_bridge_maximum_mismatch")
    if bridge.get("supporting_position_card_ids") != supporting:
        errors.append("practice_result_bridge_supporting_set_mismatch")
    if bridge.get("adverse_position_card_ids") != adverse_ids:
        errors.append("practice_result_bridge_adverse_set_mismatch")

    bound_claim_ids = {str(item.get("claim_id")) for item in bindings}
    findings = payload.get("findings")
    if not isinstance(findings, list) or not findings:
        errors.append("practice_result_findings_invalid")
        findings = []
    covered_claim_ids: set[str] = set()
    seen_findings: set[str] = set()
    normative_bridge_sha256 = _digest(bridge)
    for ordinal, finding in enumerate(findings, start=1):
        if not isinstance(finding, Mapping):
            errors.append(f"practice_result_finding_invalid:{ordinal}")
            continue
        candidate = finding.get("candidate")
        if not isinstance(candidate, Mapping):
            errors.append(f"practice_result_finding_candidate_missing:{ordinal}")
            continue
        candidate_id = _canonical_identifier(candidate.get("candidate_id"))
        if not candidate_id or candidate_id != finding.get("candidate_id"):
            errors.append(f"practice_result_finding_candidate_id_mismatch:{ordinal}")
        if candidate_id not in decision_candidate_ids:
            errors.append(f"practice_result_finding_candidate_not_human_selected:{ordinal}")
        if candidate.get("plan_sha256") != result.get("plan_sha256"):
            errors.append(f"practice_result_finding_plan_mismatch:{ordinal}")
        if candidate.get("human_review") != "approved":
            errors.append(f"practice_result_finding_candidate_not_approved:{ordinal}")
        if candidate.get("drafting_ready") is not True:
            errors.append(f"practice_result_finding_candidate_not_drafting_ready:{ordinal}")
        candidate_sha = _digest(candidate)
        claim_ids, claim_errors = _identifier_list(
            finding.get("claim_ids"),
            label=f"practice_result_finding_claim_ids:{ordinal}",
            allow_empty=False,
            require_list=True,
        )
        errors.extend(claim_errors)
        if claim_ids != sorted(claim_ids):
            errors.append(f"practice_result_finding_claim_ids_not_canonical:{ordinal}")
        for claim_id in sorted(set(claim_ids) - bound_claim_ids):
            errors.append(f"practice_result_finding_unbound_claim:{claim_id}")
        covered_claim_ids.update(claim_ids)
        expected = {
            "finding_id": _digest(
                {
                    "candidate_sha256": candidate_sha,
                    "claim_ids": claim_ids,
                    "normative_bridge_sha256": normative_bridge_sha256,
                }
            ),
            "candidate_id": candidate_id,
            "candidate_sha256": candidate_sha,
            "candidate": dict(candidate),
            "claim_ids": claim_ids,
            "claim_wording": bridge.get("claim_wording"),
            "supporting_position_card_ids": list(
                bridge.get("supporting_position_card_ids", [])
            ),
            "adverse_position_card_ids": list(
                bridge.get("adverse_position_card_ids", [])
            ),
            "maximum_permitted_claim": bridge.get("maximum_permitted_claim"),
        }
        if dict(finding) != expected:
            errors.append(f"practice_result_finding_not_artifact_derived:{ordinal}")
        finding_id = finding.get("finding_id")
        if isinstance(finding_id, str):
            if finding_id in seen_findings:
                errors.append(f"practice_result_finding_duplicate:{finding_id}")
            seen_findings.add(finding_id)
    if covered_claim_ids != bound_claim_ids:
        errors.append("practice_result_finding_claim_coverage_mismatch")

    limitations = payload.get("limitations")
    if (
        not isinstance(limitations, list)
        or not limitations
        or any(not _exact_text(item) for item in limitations)
    ):
        errors.append("practice_result_limitations_invalid")
    if result.get("limitations") != limitations:
        errors.append("practice_result_limitations_mismatch")

    quality = payload.get("quality_bindings")
    if not isinstance(quality, list) or not quality:
        errors.append("practice_result_quality_bindings_invalid")
        quality = []
    seen_quality: set[str] = set()
    for ordinal, binding in enumerate(quality, start=1):
        if not isinstance(binding, Mapping):
            errors.append(f"practice_result_quality_binding_invalid:{ordinal}")
            continue
        quality_type_value = binding.get("quality_type")
        expected_binding_fields = (
            _FINALIZATION_RECEIPT_BINDING_FIELDS
            if quality_type_value == "coding_audit_finalization_receipt"
            else _QUALITY_BINDING_FIELDS
        )
        errors.extend(
            _exact_mapping_keys(
                binding,
                expected_binding_fields,
                label=f"practice_result_quality_binding:{ordinal}",
            )
        )
        quality_type = _canonical_identifier(quality_type_value)
        if quality_type not in _ALLOWED_QUALITY_TYPES:
            errors.append(f"practice_result_quality_type_invalid:{ordinal}")
        elif quality_type in seen_quality:
            errors.append(f"practice_result_quality_type_duplicate:{quality_type}")
        else:
            seen_quality.add(quality_type)
        artifact = binding.get("artifact")
        if not isinstance(artifact, Mapping):
            errors.append(f"practice_result_quality_artifact_invalid:{ordinal}")
        elif binding.get("artifact_sha256") != _digest(artifact):
            errors.append(f"practice_result_quality_artifact_sha256_mismatch:{ordinal}")
    for quality_type in sorted(_REQUIRED_QUALITY_TYPES - seen_quality):
        errors.append(f"practice_result_quality_type_missing:{quality_type}")
    return _unique(errors)


def _validate_result(
    value: Any,
    *,
    request: Mapping[str, Any],
    state: Mapping[str, Any],
    research_request: Any,
    wording: Mapping[str, Any],
    projected_findings: Any,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(value, Mapping):
        return [], ["practice_result_missing"]
    errors = _exact_mapping_keys(value, _RESULT_FIELDS, label="practice_result")
    for field, expected in (
        ("schema_version", "2.0"),
        ("source_skill", "ksrf-cassation-judicial-meaning"),
        ("target_skill", "ksrf-complaint-cycle"),
        ("payload_type", "approved_bounded_findings"),
        ("handoff_id", state.get("handoff_id")),
        ("plan_sha256", state.get("plan_sha256")),
        ("evidence_sha256", state.get("evidence_sha256")),
        ("fingerprint_sha256", state.get("fingerprint_sha256")),
    ):
        if value.get(field) != expected:
            errors.append(f"practice_result_binding_mismatch:{field}")
    unsigned = {key: deepcopy(item) for key, item in value.items() if key != "handoff_id"}
    if value.get("handoff_id") != _digest(unsigned):
        errors.append("practice_result_handoff_id_invalid")
    if not _is_rfc3339(value.get("created_at")):
        errors.append("practice_result_created_at_invalid")
    if value.get("created_at") != state.get("result_created_at"):
        errors.append("practice_result_created_at_state_mismatch")
    payload = value.get("payload")
    if not isinstance(payload, Mapping):
        return [], _unique([*errors, "practice_result_payload_missing"])
    errors.extend(_exact_mapping_keys(payload, _RESULT_PAYLOAD_FIELDS, label="practice_result_payload"))
    errors.extend(
        _validate_research_request(
            research_request,
            state=state,
            result_payload=payload,
        )
    )
    if payload.get("drafting_ready") is not True:
        errors.append("practice_result_not_drafting_ready")
    if payload.get("request_handoff_id") != state.get("request_id"):
        errors.append("practice_result_request_handoff_id_mismatch")
    if not isinstance(payload.get("request_sha256"), str) or not _SHA256_RE.fullmatch(
        payload.get("request_sha256", "")
    ):
        errors.append("practice_result_request_sha256_invalid")
    if payload.get("maximum_permitted_claim") != request.get("maximum_supported_inference"):
        errors.append("practice_result_maximum_permitted_claim_mismatch")
    approval = payload.get("approval_binding")
    if not isinstance(approval, Mapping):
        errors.append("practice_result_approval_binding_missing")
        approval = {}
    else:
        errors.extend(_exact_mapping_keys(approval, _APPROVAL_BINDING_FIELDS, label="practice_result_approval_binding"))
    for field in ("human_decision_sha256", "validation_report_sha256", "normative_bridge_sha256"):
        if approval.get(field) != wording.get(field):
            errors.append(f"practice_result_wording_approval_mismatch:{field}")
    if not _exact_text(approval.get("reviewer")):
        errors.append("practice_result_approval_reviewer_invalid")
    if not _is_rfc3339(approval.get("approved_at")):
        errors.append("practice_result_approval_approved_at_invalid")

    approved_at = _parse_rfc3339(approval.get("approved_at"))
    request_created_at = (
        _parse_rfc3339(research_request.get("created_at"))
        if isinstance(research_request, Mapping)
        else None
    )
    attachment_attached_at = _parse_rfc3339(state.get("attachment_attached_at"))
    result_created_at = _parse_rfc3339(value.get("created_at"))
    result_imported_at = _parse_rfc3339(state.get("result_imported_at"))
    wording_reviewed_at = _parse_rfc3339(state.get("wording_reviewed_at"))
    if (
        request_created_at is not None
        and (
            (
                attachment_attached_at is not None
                and request_created_at > attachment_attached_at
            )
            or (
                result_created_at is not None
                and request_created_at > result_created_at
            )
        )
    ):
        errors.append("practice_result_request_timestamp_order_invalid")
    if (
        attachment_attached_at is not None
        and approved_at is not None
        and result_created_at is not None
        and result_imported_at is not None
        and wording_reviewed_at is not None
        and not (
            attachment_attached_at
            <= approved_at
            <= result_created_at
            <= result_imported_at
            <= wording_reviewed_at
        )
    ):
        errors.append("practice_result_approval_timestamp_order_invalid")

    for field in (
        "supporting_position_card_ids",
        "adverse_position_card_ids",
    ):
        position_ids, position_errors = _identifier_list(
            payload.get(field),
            label=f"practice_result_{field}",
            require_list=True,
        )
        errors.extend(position_errors)
        if position_ids != sorted(position_ids):
            errors.append(f"practice_result_{field}_not_canonical")

    public_claim_id = _public_claim_id(str(request.get("practice_claim_id")))
    bindings, binding_errors = _canonical_result_claim_bindings(
        payload.get("claim_bindings")
    )
    errors.extend(binding_errors)
    if payload.get("claim_set_sha256") != _digest(bindings):
        errors.append("practice_result_claim_set_sha256_mismatch")
    matching_bindings = [
        item for item in bindings if isinstance(item, Mapping) and item.get("claim_id") == public_claim_id
    ]
    if len(matching_bindings) != 1:
        errors.append("practice_result_claim_binding_not_exact")
    else:
        binding = matching_bindings[0]
        if frozenset(binding.keys()) != frozenset({"claim_id", "claim_sha256", "source_locator"}):
            errors.append("practice_result_claim_binding_fields_invalid")
        if binding.get("claim_sha256") != state.get("claim_sha256"):
            errors.append("practice_result_claim_sha256_mismatch")
        if binding.get("source_locator") != _public_source_locator(
            str(state.get("source_locator"))
        ):
            errors.append("practice_result_source_locator_mismatch")

    raw_findings = payload.get("findings")
    if not isinstance(raw_findings, list):
        errors.append("practice_result_findings_invalid")
        raw_findings = []
    by_id: dict[str, Mapping[str, Any]] = {}
    claim_ids_by_finding: dict[str, list[str]] = {}
    for ordinal, raw in enumerate(raw_findings, start=1):
        if not isinstance(raw, Mapping):
            errors.append(f"practice_result_finding_invalid:{ordinal}")
            continue
        errors.extend(_exact_mapping_keys(raw, _FINDING_FIELDS, label=f"practice_result_finding:{ordinal}"))
        finding_id = raw.get("finding_id")
        if not isinstance(finding_id, str) or not _SHA256_RE.fullmatch(finding_id):
            errors.append(f"practice_result_finding_id_invalid:{ordinal}")
            continue
        if finding_id in by_id:
            errors.append(f"practice_result_finding_duplicate:{finding_id}")
            continue
        claim_ids, claim_errors = _identifier_list(
            raw.get("claim_ids"),
            label=f"practice_result_finding_claim_ids:{finding_id}",
            allow_empty=False,
            require_list=True,
        )
        errors.extend(claim_errors)
        if claim_ids != sorted(claim_ids):
            errors.append(
                f"practice_result_finding_claim_ids_not_canonical:{finding_id}"
            )
        for field in (
            "supporting_position_card_ids",
            "adverse_position_card_ids",
        ):
            position_ids, position_errors = _identifier_list(
                raw.get(field),
                label=f"practice_result_finding_{field}:{ordinal}",
                require_list=True,
            )
            errors.extend(position_errors)
            if position_ids != sorted(position_ids):
                errors.append(
                    f"practice_result_finding_{field}_not_canonical:{ordinal}"
                )
        by_id[finding_id] = raw
        claim_ids_by_finding[finding_id] = claim_ids

    requested_ids = list(request.get("evidence_ids") or ())
    target_native_finding_ids = {
        finding_id
        for finding_id, claim_ids in claim_ids_by_finding.items()
        if public_claim_id in claim_ids
    }
    if target_native_finding_ids != set(requested_ids):
        errors.append("practice_result_finding_set_mismatch")
    selected: list[dict[str, Any]] = []
    for finding_id in requested_ids:
        raw = by_id.get(finding_id)
        if raw is None:
            errors.append(f"practice_result_finding_missing:{finding_id}")
            continue
        claim_ids = claim_ids_by_finding.get(finding_id, [])
        if public_claim_id not in claim_ids:
            errors.append(f"practice_result_finding_foreign_claim:{finding_id}")
        candidate = raw.get("candidate")
        if not isinstance(candidate, Mapping):
            errors.append(f"practice_result_finding_candidate_missing:{finding_id}")
            continue
        candidate_sha = _digest(candidate)
        if raw.get("candidate_sha256") != candidate_sha:
            errors.append(f"practice_result_finding_candidate_sha256_mismatch:{finding_id}")
        if raw.get("candidate_id") != candidate.get("candidate_id"):
            errors.append(f"practice_result_finding_candidate_id_mismatch:{finding_id}")
        if candidate.get("plan_sha256") != value.get("plan_sha256"):
            errors.append(f"practice_result_finding_plan_mismatch:{finding_id}")
        if candidate.get("human_review") != "approved":
            errors.append(
                f"practice_result_finding_candidate_not_approved:{finding_id}"
            )
        if candidate.get("drafting_ready") is not True:
            errors.append(
                f"practice_result_finding_candidate_not_drafting_ready:{finding_id}"
            )
        if raw.get("claim_wording") != request.get("sentence_text"):
            errors.append(
                f"practice_result_finding_claim_wording_mismatch:{finding_id}"
            )
        if candidate.get("claim_wording") != request.get("sentence_text"):
            errors.append(
                f"practice_result_finding_candidate_wording_mismatch:{finding_id}"
            )
        for ceiling in (
            raw.get("maximum_permitted_claim"),
            candidate.get("maximum_permitted_claim"),
            payload.get("maximum_permitted_claim"),
        ):
            if ceiling != request.get("maximum_supported_inference"):
                errors.append(f"practice_result_finding_maximum_mismatch:{finding_id}")
                break
        expected_finding_id = _digest(
            {
                "candidate_sha256": candidate_sha,
                "claim_ids": claim_ids,
                "normative_bridge_sha256": approval.get("normative_bridge_sha256"),
            }
        )
        if finding_id != expected_finding_id:
            errors.append(f"practice_result_finding_sha256_mismatch:{finding_id}")
        selected.append(deepcopy(dict(raw)))
    selected = sorted(selected, key=lambda item: item["finding_id"])
    if not isinstance(projected_findings, Sequence) or isinstance(projected_findings, (str, bytes)):
        errors.append("practice_resolution_findings_invalid")
    else:
        projected: list[dict[str, Any]] = []
        for ordinal, item in enumerate(projected_findings, start=1):
            if not isinstance(item, Mapping):
                errors.append(f"practice_resolution_finding_invalid:{ordinal}")
                continue
            projected.append(deepcopy(dict(item)))
        if projected != selected:
            errors.append("practice_resolution_finding_set_mismatch")
    errors.extend(
        _validate_result_proof_bundle(
            payload=payload,
            result=value,
            bindings=bindings,
        )
    )
    errors.extend(
        _native_quality_binding_errors(
            payload.get("quality_bindings"),
            expected_receipt_sha256=state.get(
                "expected_finalization_receipt_sha256"
            ),
            plan_sha256=value.get("plan_sha256"),
        )
    )
    return selected, _unique(errors)


def _validate_issue(
    value: Any,
    *,
    request: Mapping[str, Any],
    supplied_fingerprint: Any,
    supplied_requests: Any,
    trusted_ids: Any,
) -> tuple[str | None, list[str]]:
    if not isinstance(value, Mapping):
        return None, ["practice_issue_candidate_missing"]
    errors: list[str] = []
    try:
        candidate = issue_candidate_from_dict(value)
    except (TypeError, ValueError, KeyError) as exc:
        return None, [f"practice_issue_candidate_invalid:{type(exc).__name__}"]
    if candidate.to_dict() != dict(value):
        errors.append("practice_issue_candidate_not_exact")
    fingerprint = issue_candidate_content_fingerprint(candidate)
    if supplied_fingerprint != fingerprint:
        errors.append("practice_issue_candidate_fingerprint_mismatch")
    if candidate.claim_id != request.get("claim_id"):
        errors.append("practice_issue_constitutional_claim_mismatch")
    if candidate.issue_id != request.get("issue_option_id"):
        errors.append("practice_issue_option_mismatch")
    claims = [claim for claim in candidate.practice_claims if claim.claim_id == request.get("practice_claim_id")]
    if len(claims) != 1:
        errors.append("practice_issue_claim_gate_not_exact")
    else:
        claim = claims[0]
        if not claim.is_substantively_proven:
            errors.append("practice_issue_claim_not_substantively_proven")
        if claim.statement != request.get("sentence_text"):
            errors.append("practice_issue_claim_statement_mismatch")
        if list(claim.evidence_ids) != list(request.get("evidence_ids") or ()):
            errors.append("practice_issue_claim_finding_set_mismatch")
    if candidate.human_selection.state not in {"principal", "reserve"}:
        errors.append("practice_issue_selection_not_release_selected")
    practice_key = f"practice:{request.get('practice_claim_id')}"
    expected_all = issue_approval_requests(candidate)
    expected_requests = {practice_key: expected_all.get(practice_key), "selection": expected_all.get("selection")}
    if not isinstance(supplied_requests, Mapping) or dict(supplied_requests) != expected_requests:
        errors.append("practice_issue_approval_requests_mismatch")
    expected_keys = {practice_key, "selection"}
    if not isinstance(trusted_ids, Mapping) or set(trusted_ids.keys()) != expected_keys:
        errors.append("practice_issue_trusted_approval_ids_mismatch")
    else:
        valid_ids: list[str] = []
        for key in sorted(expected_keys):
            if not isinstance(trusted_ids.get(key), str) or not _TRUSTED_APPROVAL_ID_RE.fullmatch(trusted_ids[key]):
                errors.append(f"practice_issue_trusted_approval_id_invalid:{key}")
            else:
                valid_ids.append(trusted_ids[key])
        if len(valid_ids) == len(expected_keys) and len(set(valid_ids)) != len(valid_ids):
            errors.append("practice_issue_trusted_approval_ids_not_distinct")
    return fingerprint, _unique(errors)


def _canonical_ready_bindings(value: Any, *, label: str) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return [], [f"{label}_invalid"]
    result: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for ordinal, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping):
            errors.append(f"{label}_entry_invalid:{ordinal}")
            continue
        errors.extend(_exact_mapping_keys(raw, _READY_BINDING_FIELD_SET, label=f"{label}:{ordinal}"))
        claim_id = _canonical_identifier(raw.get("claim_id"))
        if not claim_id:
            errors.append(f"{label}_claim_id_invalid:{ordinal}")
            continue
        if claim_id in seen:
            errors.append(f"{label}_duplicate:{claim_id}")
            continue
        seen.add(claim_id)
        result.append(deepcopy(dict(raw)))
    canonical = sorted(result, key=lambda item: item["claim_id"])
    if result != canonical:
        errors.append(f"{label}_not_canonical")
    return canonical, _unique(errors)


def _validate_refresh(value: Any, *, expected_ready: Sequence[Mapping[str, Any]]) -> list[str]:
    if not isinstance(value, Mapping):
        return ["practice_prefiling_refresh_missing"]
    errors = _exact_mapping_keys(value, _REFRESH_FIELDS, label="practice_prefiling_refresh")
    if value.get("required") is not True or value.get("valid") is not True:
        errors.append("practice_prefiling_refresh_not_valid")
    record = value.get("record")
    if not isinstance(record, Mapping):
        return _unique([*errors, "practice_prefiling_refresh_record_missing"])
    errors.extend(_exact_mapping_keys(record, _REFRESH_RECORD_FIELDS, label="practice_prefiling_refresh_record"))
    if record.get("schema_version") != "1.0" or record.get("record_type") != "prefiling_refresh":
        errors.append("practice_prefiling_refresh_record_identity_invalid")
    if not _canonical_identifier(record.get("reviewer")):
        errors.append("practice_prefiling_refresh_reviewer_invalid")
    if not _exact_text(record.get("official_check_ref")):
        errors.append("practice_prefiling_refresh_official_check_ref_invalid")
    ready, ready_errors = _canonical_ready_bindings(
        record.get("ready_claim_bindings"), label="practice_prefiling_refresh_ready_bindings"
    )
    errors.extend(ready_errors)
    expected = [deepcopy(dict(item)) for item in expected_ready]
    if ready != expected:
        errors.append("practice_prefiling_refresh_ready_set_mismatch")
    ready_sha = _digest(ready)
    if record.get("ready_claim_set_sha256") != ready_sha:
        errors.append("practice_prefiling_refresh_record_sha256_mismatch")
    if value.get("ready_claim_set_sha256") != ready_sha:
        errors.append("practice_prefiling_refresh_sha256_mismatch")
    try:
        as_of = date.fromisoformat(str(record.get("as_of")))
        cutoff = date.fromisoformat(str(record.get("corpus_cutoff")))
        if cutoff > as_of:
            errors.append("practice_prefiling_refresh_cutoff_invalid")
    except ValueError:
        errors.append("practice_prefiling_refresh_date_invalid")
    if not _is_rfc3339(record.get("recorded_at")):
        errors.append("practice_prefiling_refresh_recorded_at_invalid")
    errors.extend(
        _validate_ledger_event(record, label="practice_prefiling_refresh")
    )
    return _unique(errors)


def _validate_filing(
    value: Any,
    *,
    request: Mapping[str, Any],
    practice_state: Mapping[str, Any],
    refresh: Mapping[str, Any],
    matter_binding: Mapping[str, Any],
) -> list[str]:
    if not isinstance(value, Mapping):
        return ["practice_filing_validation_missing"]
    errors = _exact_mapping_keys(
        value, _FILING_VALIDATION_FIELDS, label="practice_filing_validation"
    )
    if value.get("schema_version") != "1.0" or value.get("stage") != "filing":
        errors.append("practice_filing_validation_stage_invalid")
    validation_valid = value.get("valid")
    if type(validation_valid) is not bool:
        errors.append("practice_filing_validation_valid_invalid")
    if value.get("global_integrity_errors") != []:
        errors.append("practice_filing_global_integrity_errors")
    validation_ids: dict[str, list[str]] = {}
    for field in ("blocked_claim_ids", "allowed_claim_ids", "unaffected_claim_ids"):
        identifiers, identifier_errors = _identifier_list(
            value.get(field),
            label=f"practice_filing_{field}",
            require_list=True,
        )
        errors.extend(identifier_errors)
        validation_ids[field] = identifiers
    if not _is_rfc3339(value.get("validated_at")):
        errors.append("practice_filing_validated_at_invalid")
    state = value.get("state")
    if not isinstance(state, Mapping):
        return _unique([*errors, "practice_filing_state_missing"])
    errors.extend(
        _exact_mapping_keys(state, _FILING_STATE_FIELDS, label="practice_filing_state")
    )
    if state.get("schema_version") != "1.0" or state.get("stage") != "filing":
        errors.append("practice_filing_state_stage_invalid")
    if not _is_rfc3339(state.get("generated_at")):
        errors.append("practice_filing_state_generated_at_invalid")
    if state.get("case_id") != matter_binding.get("case_id"):
        errors.append("practice_filing_case_id_mismatch")
    if state.get("global_integrity_errors") != []:
        errors.append("practice_filing_state_global_integrity_errors")
    report_errors = value.get("errors")
    if not isinstance(report_errors, list) or any(
        not _exact_text(item) for item in report_errors
    ):
        errors.append("practice_filing_errors_invalid")
    if state.get("prefiling_refresh") != refresh:
        errors.append("practice_filing_refresh_projection_mismatch")
    input_bindings = state.get("input_bindings")
    if (
        not isinstance(input_bindings, Mapping)
        or frozenset(input_bindings.keys())
        != frozenset(
            {
                "case_file_sha256",
                "argument_research_sha256",
                "input_bindings_sha256",
            }
        )
        or input_bindings.get("input_bindings_sha256")
        != matter_binding.get("input_bindings_sha256")
    ):
        errors.append("practice_filing_input_bindings_mismatch")
    elif (
        not isinstance(input_bindings.get("case_file_sha256"), str)
        or not _SHA256_RE.fullmatch(input_bindings.get("case_file_sha256", ""))
    ):
        errors.append("practice_filing_case_file_sha256_invalid")
    else:
        argument_research_sha256 = input_bindings.get(
            "argument_research_sha256"
        )
        if argument_research_sha256 is not None and (
            not isinstance(argument_research_sha256, str)
            or not _SHA256_RE.fullmatch(argument_research_sha256)
        ):
            errors.append("practice_filing_argument_research_sha256_invalid")
    claims = state.get("claims")
    if not isinstance(claims, list):
        return _unique([*errors, "practice_filing_claims_invalid"])

    matching: list[Mapping[str, Any]] = []
    expected_ready: list[dict[str, Any]] = []
    claim_ids: list[str] = []
    blocked_claim_ids: list[str] = []
    allowed_claim_ids: list[str] = []
    unaffected_claim_ids: list[str] = []
    counts = {claim_state: 0 for claim_state in _CLAIM_STATES}
    for ordinal, raw in enumerate(claims, start=1):
        if not isinstance(raw, Mapping):
            errors.append(f"practice_filing_claim_invalid:{ordinal}")
            continue
        errors.extend(
            _exact_mapping_keys(
                raw, _PRACTICE_STATE_FIELDS, label=f"practice_filing_claim:{ordinal}"
            )
        )
        claim_id = _canonical_identifier(raw.get("claim_id"))
        if not claim_id:
            errors.append(f"practice_filing_claim_id_invalid:{ordinal}")
            continue
        if claim_id in claim_ids:
            errors.append(f"practice_filing_claim_duplicate:{claim_id}")
        claim_ids.append(claim_id)
        claim_state = raw.get("state")
        if claim_state not in _CLAIM_STATES:
            errors.append(f"practice_filing_claim_state_invalid:{claim_id}")
            continue
        counts[str(claim_state)] += 1
        expected_blocked = claim_state in _BLOCKING_CLAIM_STATES
        if raw.get("draft_blocked") is not expected_blocked:
            errors.append(f"practice_filing_claim_draft_blocked_mismatch:{claim_id}")
        if expected_blocked:
            blocked_claim_ids.append(claim_id)
        else:
            allowed_claim_ids.append(claim_id)
        if claim_state == "not_required":
            unaffected_claim_ids.append(claim_id)
        if claim_id == request.get("practice_claim_id"):
            matching.append(raw)
        if claim_state == "ready":
            raw_options = raw.get("option_ids")
            sibling_issue_option = (
                raw_options[0]
                if isinstance(raw_options, list) and raw_options
                else None
            )
            raw_wording = raw.get("wording_review")
            sibling_request = {
                "practice_claim_id": claim_id,
                "issue_option_id": sibling_issue_option,
                "maximum_supported_inference": raw.get(
                    "maximum_permitted_claim"
                ),
                "sentence_text": (
                    raw_wording.get("wording_text")
                    if isinstance(raw_wording, Mapping)
                    else None
                ),
                "evidence_ids": (
                    raw_wording.get("finding_ids")
                    if isinstance(raw_wording, Mapping)
                    else None
                ),
            }
            _, ready_state_errors = _validate_practice_state(
                raw,
                request=sibling_request,
                label=f"practice_filing_ready_claim:{claim_id}",
            )
            errors.extend(ready_state_errors)
            if isinstance(raw_wording, Mapping):
                errors.extend(
                    _validate_wording_review(
                        raw_wording,
                        request=sibling_request,
                        state=raw,
                    )
                )
            else:
                errors.append(
                    f"practice_filing_ready_claim_wording_missing:{claim_id}"
                )
            expected_ready.append(_ready_binding_from_state(raw))

    if len(matching) != 1 or dict(matching[0]) != dict(practice_state):
        errors.append("practice_filing_target_state_mismatch")

    derived_ids = {
        "blocked_claim_ids": blocked_claim_ids,
        "allowed_claim_ids": allowed_claim_ids,
        "unaffected_claim_ids": unaffected_claim_ids,
    }
    for field, derived in derived_ids.items():
        state_value = state.get(field)
        if state_value != derived:
            errors.append(f"practice_filing_state_{field}_derivation_mismatch")
        if validation_ids[field] != derived:
            errors.append(f"practice_filing_{field}_derivation_mismatch")

    target_id = str(request.get("practice_claim_id"))
    if target_id not in allowed_claim_ids:
        errors.extend(
            ["practice_filing_target_not_allowed", "practice_filing_state_target_not_allowed"]
        )
    if target_id in blocked_claim_ids:
        errors.extend(
            ["practice_filing_target_blocked", "practice_filing_state_target_blocked"]
        )

    counts_by_state = state.get("counts_by_state")
    if not isinstance(counts_by_state, Mapping) or dict(counts_by_state) != counts:
        errors.append("practice_filing_counts_by_state_mismatch")

    expected_ready = sorted(expected_ready, key=lambda item: item["claim_id"])
    errors.extend(_validate_refresh(refresh, expected_ready=expected_ready))

    refresh_valid = refresh.get("valid") is True
    if blocked_claim_ids or not refresh_valid:
        expected_verdict = (
            "partial" if allowed_claim_ids and blocked_claim_ids else "blocked"
        )
    else:
        expected_verdict = "ready"
    stage_verdict = state.get("stage_verdict")
    if stage_verdict != expected_verdict:
        errors.append("practice_filing_state_verdict_derivation_mismatch")
    if stage_verdict == "blocked":
        errors.append("practice_filing_state_verdict_blocked")
    elif stage_verdict not in {"ready", "partial"}:
        errors.append("practice_filing_state_verdict_invalid")

    expected_report_errors = [
        f"blocking_empirical_overclaim:{raw.get('claim_id')}:{raw.get('state')}"
        for raw in claims
        if isinstance(raw, Mapping) and raw.get("draft_blocked") is True
    ]
    if refresh.get("required") is True and not refresh_valid:
        expected_report_errors.append("prefiling_refresh_required")
    if isinstance(report_errors, list) and report_errors != expected_report_errors:
        errors.append("practice_filing_errors_derivation_mismatch")
        if expected_verdict == "partial":
            errors.append("practice_filing_partial_errors_mismatch")

    expected_valid = not expected_report_errors and expected_verdict == "ready"
    if validation_valid is not expected_valid:
        if expected_verdict == "ready":
            errors.append("practice_filing_validation_not_valid")
        else:
            errors.append("practice_filing_validation_validity_mismatch")
    return _unique(errors)


def _validate_temporal_snapshot(
    *,
    resolution: Mapping[str, Any],
    practice_state: Mapping[str, Any],
    refresh: Mapping[str, Any],
) -> list[str]:
    filing = resolution.get("filing_validation")
    refresh_record = refresh.get("record")
    if not isinstance(filing, Mapping) or not isinstance(refresh_record, Mapping):
        return []
    filing_state = filing.get("state")
    if not isinstance(filing_state, Mapping):
        return []

    material_fields = (
        "input_manifest_updated_at",
        "claim_created_at",
        "wording_reviewed_at",
        "result_imported_at",
        "result_created_at",
        "attachment_attached_at",
        "anchor_checked_at",
    )
    claims = filing_state.get("claims")
    ready_states = (
        [item for item in claims if isinstance(item, Mapping) and item.get("state") == "ready"]
        if isinstance(claims, list)
        else []
    )
    if not ready_states:
        ready_states = [practice_state]
    native_times = [
        _parse_rfc3339(ready_state.get(field))
        for ready_state in ready_states
        for field in material_fields
    ]
    research_request = resolution.get("research_request")
    if isinstance(research_request, Mapping):
        native_times.append(_parse_rfc3339(research_request.get("created_at")))
    refresh_time = _parse_rfc3339(refresh_record.get("recorded_at"))
    filing_generated = _parse_rfc3339(filing_state.get("generated_at"))
    validated_time = _parse_rfc3339(filing.get("validated_at"))
    checked_time = _parse_rfc3339(resolution.get("checked_at"))
    if (
        any(value is None for value in native_times)
        or refresh_time is None
        or filing_generated is None
        or validated_time is None
        or checked_time is None
    ):
        return []
    exact_native_times = [value for value in native_times if value is not None]
    if not (
        refresh_time >= max(exact_native_times)
        and filing_generated >= refresh_time
        and validated_time >= filing_generated
        and checked_time >= validated_time
    ):
        return ["practice_binding_timestamp_order_invalid"]
    try:
        as_of = date.fromisoformat(str(refresh_record.get("as_of")))
    except ValueError:
        return []
    if refresh_time.date() != as_of or checked_time.date() != as_of:
        return ["practice_prefiling_refresh_snapshot_mismatch"]
    return []


def build_practice_claim_binding_resolution(
    *,
    request: Mapping[str, Any],
    matter_binding: Mapping[str, Any],
    practice_state: Mapping[str, Any],
    ready_binding: Mapping[str, Any],
    research_request: Mapping[str, Any],
    result: Mapping[str, Any],
    findings: Sequence[Mapping[str, Any]],
    wording_review: Mapping[str, Any],
    filing_validation: Mapping[str, Any],
    prefiling_refresh: Mapping[str, Any],
    issue_candidate: Mapping[str, Any],
    issue_approval_requests: Mapping[str, Mapping[str, Any]],
    trusted_approval_ids: Mapping[str, str],
    authority_revision_id: str,
    checked_at: str,
) -> dict[str, Any]:
    """Build one canonical positive host resolution (primarily for adapters/tests)."""

    candidate = issue_candidate_from_dict(issue_candidate)
    return {
        "schema_version": "1.0.0",
        "status": "verified",
        "practice_binding_sha256": request.get("practice_binding_sha256"),
        "matter_binding": deepcopy(dict(matter_binding)),
        "practice_state": deepcopy(dict(practice_state)),
        "ready_binding": deepcopy(dict(ready_binding)),
        "research_request": deepcopy(dict(research_request)),
        "result": deepcopy(dict(result)),
        "findings": sorted(
            (deepcopy(dict(item)) for item in findings), key=lambda item: item["finding_id"]
        ),
        "wording_review": deepcopy(dict(wording_review)),
        "filing_validation": deepcopy(dict(filing_validation)),
        "prefiling_refresh": deepcopy(dict(prefiling_refresh)),
        "issue_candidate": deepcopy(dict(issue_candidate)),
        "issue_candidate_fingerprint": issue_candidate_content_fingerprint(candidate),
        "issue_approval_requests": deepcopy(dict(issue_approval_requests)),
        "trusted_approval_ids": deepcopy(dict(trusted_approval_ids)),
        "authority_revision_id": authority_revision_id,
        "checked_at": checked_at,
    }


def _resolution_errors_and_receipt(
    request: Mapping[str, Any], resolution: Mapping[str, Any]
) -> tuple[list[str], dict[str, Any] | None]:
    errors = _exact_mapping_keys(resolution, _RESOLUTION_FIELDS, label="practice_binding_resolution")
    if resolution.get("schema_version") != "1.0.0" or resolution.get("status") != "verified":
        errors.append("practice_binding_resolution_not_verified")
    if resolution.get("practice_binding_sha256") != request.get("practice_binding_sha256"):
        errors.append("practice_binding_sha256_mismatch")
    if not _canonical_identifier(resolution.get("authority_revision_id")):
        errors.append("practice_binding_authority_revision_id_invalid")
    if not _is_rfc3339(resolution.get("checked_at")):
        errors.append("practice_binding_checked_at_invalid")

    matter = resolution.get("matter_binding")
    if not isinstance(matter, Mapping):
        matter = {}
        errors.append("practice_matter_binding_missing")
    else:
        errors.extend(_exact_mapping_keys(matter, _MATTER_BINDING_FIELDS, label="practice_matter_binding"))
    for field in ("matter_id", "draft_id"):
        if matter.get(field) != request.get(field):
            errors.append(f"practice_matter_binding_{field}_mismatch")
    for field in ("case_id", "workspace_revision_id"):
        if not _canonical_identifier(matter.get(field)):
            errors.append(f"practice_matter_binding_{field}_invalid")
    if not isinstance(matter.get("input_bindings_sha256"), str) or not _SHA256_RE.fullmatch(matter.get("input_bindings_sha256", "")):
        errors.append("practice_matter_binding_input_bindings_sha256_invalid")

    state, state_errors = _validate_practice_state(resolution.get("practice_state"), request=request)
    errors.extend(state_errors)
    if state is None:
        return _unique(errors), None
    if state.get("input_bindings_sha256") != matter.get("input_bindings_sha256"):
        errors.append("practice_state_input_bindings_mismatch")
    ready = resolution.get("ready_binding")
    expected_ready = _ready_binding_from_state(state)
    if not isinstance(ready, Mapping) or frozenset(ready.keys()) != _READY_BINDING_FIELD_SET:
        errors.append("practice_ready_binding_invalid")
    elif dict(ready) != expected_ready:
        errors.append("practice_ready_binding_mismatch")

    wording = resolution.get("wording_review")
    errors.extend(_validate_wording_review(wording, request=request, state=state))
    if isinstance(wording, Mapping) and state.get("wording_review") != wording:
        errors.append("practice_state_wording_review_mismatch")
    selected_findings, result_errors = _validate_result(
        resolution.get("result"),
        request=request,
        state=state,
        research_request=resolution.get("research_request"),
        wording=wording if isinstance(wording, Mapping) else {},
        projected_findings=resolution.get("findings"),
    )
    errors.extend(result_errors)
    refresh = resolution.get("prefiling_refresh")
    if isinstance(refresh, Mapping):
        errors.extend(
            _validate_filing(
                resolution.get("filing_validation"),
                request=request,
                practice_state=state,
                refresh=refresh,
                matter_binding=matter,
            )
        )
        errors.extend(
            _validate_temporal_snapshot(
                resolution=resolution,
                practice_state=state,
                refresh=refresh,
            )
        )
    else:
        errors.append("practice_prefiling_refresh_missing")
    issue_fingerprint, issue_errors = _validate_issue(
        resolution.get("issue_candidate"),
        request=request,
        supplied_fingerprint=resolution.get("issue_candidate_fingerprint"),
        supplied_requests=resolution.get("issue_approval_requests"),
        trusted_ids=resolution.get("trusted_approval_ids"),
    )
    errors.extend(issue_errors)
    errors = _unique(errors)
    if errors or issue_fingerprint is None or not isinstance(wording, Mapping) or not isinstance(refresh, Mapping):
        return errors, None

    result = resolution["result"]
    filing = resolution["filing_validation"]
    refresh_record = refresh["record"]
    return [], {
        "schema_version": "1.0.0",
        "sentence_id": request["sentence_id"],
        "section_code": request["section_code"],
        "practice_binding_sha256": request["practice_binding_sha256"],
        "claim_id": request["claim_id"],
        "practice_claim_id": request["practice_claim_id"],
        "issue_option_id": request["issue_option_id"],
        "evidence_ids": list(request["evidence_ids"]),
        "maximum_supported_inference": request["maximum_supported_inference"],
        "matter_binding": deepcopy(dict(matter)),
        "practice_state_sha256": _digest(state),
        "ready_binding": deepcopy(expected_ready),
        "result_handoff_id": result["handoff_id"],
        "result_sha256": _digest(result),
        "finding_receipts": selected_findings,
        "wording_review_event_sha256": wording["event_sha256"],
        "wording_review_sha256": _digest(wording),
        "filing_validation_sha256": _digest(filing),
        "prefiling_refresh_receipt": {
            "event_sha256": refresh_record["event_sha256"],
            "ready_claim_set_sha256": refresh["ready_claim_set_sha256"],
            "as_of": refresh_record["as_of"],
            "corpus_cutoff": refresh_record["corpus_cutoff"],
            "recorded_at": refresh_record["recorded_at"],
        },
        "issue_candidate_fingerprint": issue_fingerprint,
        "issue_approval_requests": deepcopy(dict(resolution["issue_approval_requests"])),
        "trusted_approval_ids": deepcopy(dict(resolution["trusted_approval_ids"])),
        "authority_revision_id": resolution["authority_revision_id"],
        "checked_at": resolution["checked_at"],
    }


def resolve_practice_claim_evidence_binding(
    request: Mapping[str, Any],
    authority: PracticeClaimEvidenceBindingAuthority | Any | None,
) -> tuple[tuple[str, ...], dict[str, Any] | None]:
    """Resolve and locally revalidate one exact practice-claim binding."""

    try:
        canonical, request_errors = _canonical_request(request)
    except Exception:
        return ("practice_binding_request_validation_error",), None
    if canonical is None:
        return request_errors, None
    try:
        if authority is None:
            return ("practice_binding_authority_required",), None
        resolver = getattr(authority, "resolve_practice_claim_evidence_binding", None)
        if not callable(resolver):
            return ("practice_binding_authority_required",), None
        adapter_request = deepcopy(canonical)
        resolution = resolver(adapter_request)
        request_mutated = adapter_request != canonical
    except Exception:
        return ("practice_binding_authority_error",), None
    if request_mutated:
        return ("practice_binding_request_mutated",), None
    if not isinstance(resolution, Mapping):
        return ("practice_binding_resolution_missing",), None
    try:
        resolution_snapshot = _stable_snapshot(resolution)
    except Exception:
        return ("practice_binding_resolution_snapshot_error",), None
    if not isinstance(resolution_snapshot, Mapping):
        return ("practice_binding_resolution_snapshot_error",), None
    try:
        errors, receipt = _resolution_errors_and_receipt(
            canonical, resolution_snapshot
        )
    except Exception:
        return ("practice_binding_resolution_validation_error",), None
    return tuple(errors), receipt


def _binding_index_basis(
    *, matter_id: str, draft_id: str, bindings: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": [deepcopy(dict(item)) for item in bindings],
    }


def _canonical_index_bindings(
    value: Any, *, label: str, require_canonical_order: bool
) -> tuple[list[dict[str, str]], list[str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return [], [f"{label}_invalid"]
    fields = frozenset(
        {
            "sentence_id",
            "section_code",
            "role",
            "claim_id",
            "practice_claim_id",
            "issue_option_id",
            "practice_binding_sha256",
        }
    )
    bindings: list[dict[str, str]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for ordinal, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping):
            errors.append(f"{label}_entry_invalid:{ordinal}")
            continue
        try:
            raw = _stable_snapshot(raw)
        except Exception:
            errors.append(f"{label}_entry_snapshot_error:{ordinal}")
            continue
        if not isinstance(raw, Mapping):
            errors.append(f"{label}_entry_snapshot_error:{ordinal}")
            continue
        entry_errors = _exact_mapping_keys(raw, fields, label=f"{label}:{ordinal}")
        sentence_id = raw.get("sentence_id")
        if not isinstance(sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(sentence_id):
            entry_errors.append(f"{label}_sentence_id_invalid:{ordinal}")
        for field in ("section_code", "claim_id", "practice_claim_id", "issue_option_id"):
            if not _canonical_identifier(raw.get(field)):
                entry_errors.append(f"{label}_{field}_invalid:{ordinal}")
        if raw.get("role") != "practice_claim":
            entry_errors.append(f"{label}_role_invalid:{ordinal}")
        binding_sha = raw.get("practice_binding_sha256")
        if not isinstance(binding_sha, str) or not _SHA256_RE.fullmatch(binding_sha):
            entry_errors.append(f"{label}_sha256_invalid:{ordinal}")
        if isinstance(sentence_id, str) and sentence_id in seen:
            entry_errors.append(f"{label}_duplicate:{sentence_id}")
        if entry_errors:
            errors.extend(entry_errors)
            continue
        assert isinstance(sentence_id, str)
        seen.add(sentence_id)
        bindings.append({field: raw[field] for field in fields})
    canonical = sorted(bindings, key=lambda item: item["sentence_id"])
    if require_canonical_order and bindings != canonical:
        errors.append(f"{label}_not_canonical")
    return canonical, _unique(errors)


def build_practice_claim_binding_index_resolution(
    *,
    matter_id: str,
    draft_id: str,
    bindings: Sequence[Mapping[str, Any]],
    authority_revision_id: str,
    checked_at: str,
) -> dict[str, Any]:
    """Build a host-authoritative complete index, including an empty set."""

    canonical, errors = _canonical_index_bindings(
        bindings, label="practice_binding_index_bindings", require_canonical_order=False
    )
    for label, value in (
        ("matter_id", matter_id),
        ("draft_id", draft_id),
        ("authority_revision_id", authority_revision_id),
    ):
        if not _canonical_identifier(value):
            errors.append(f"practice_binding_index_{label}_invalid")
    if not _is_rfc3339(checked_at):
        errors.append("practice_binding_index_checked_at_invalid")
    if errors:
        raise ValueError(", ".join(_unique(errors)))
    basis = _binding_index_basis(matter_id=matter_id, draft_id=draft_id, bindings=canonical)
    return {
        "schema_version": "1.0.0",
        "status": "verified",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": canonical,
        "binding_index_sha256": _digest(basis),
        "authority_revision_id": authority_revision_id,
        "checked_at": checked_at,
    }


def _index_errors_and_receipt(
    *,
    matter_id: str,
    draft_id: str,
    expected: Sequence[Mapping[str, Any]],
    resolution: Mapping[str, Any],
) -> tuple[list[str], dict[str, Any] | None]:
    fields = frozenset(
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
        resolution, fields, label="practice_binding_index_resolution"
    )
    if resolution.get("schema_version") != "1.0.0" or resolution.get("status") != "verified":
        errors.append("practice_binding_index_not_verified")
    if resolution.get("matter_id") != matter_id:
        errors.append("practice_binding_index_matter_id_mismatch")
    if resolution.get("draft_id") != draft_id:
        errors.append("practice_binding_index_draft_id_mismatch")
    authoritative, binding_errors = _canonical_index_bindings(
        resolution.get("bindings"),
        label="practice_binding_index_bindings",
        require_canonical_order=True,
    )
    errors.extend(binding_errors)
    if authoritative != list(expected):
        errors.append("practice_binding_index_set_mismatch")
    basis = _binding_index_basis(
        matter_id=matter_id, draft_id=draft_id, bindings=authoritative
    )
    computed_sha = _digest(basis)
    if resolution.get("binding_index_sha256") != computed_sha:
        errors.append("practice_binding_index_sha256_mismatch")
    if not _canonical_identifier(resolution.get("authority_revision_id")):
        errors.append("practice_binding_index_authority_revision_id_invalid")
    if not _is_rfc3339(resolution.get("checked_at")):
        errors.append("practice_binding_index_checked_at_invalid")
    errors = _unique(errors)
    if errors:
        return errors, None
    return [], {
        "schema_version": "1.0.0",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": authoritative,
        "binding_index_sha256": computed_sha,
        "authority_revision_id": resolution["authority_revision_id"],
        "checked_at": resolution["checked_at"],
    }


def resolve_practice_claim_evidence_binding_index(
    *,
    matter_id: str,
    draft_id: str,
    expected_bindings: Sequence[Mapping[str, Any]],
    authority: PracticeClaimEvidenceBindingAuthority | Any | None,
) -> tuple[tuple[str, ...], dict[str, Any] | None]:
    """Revalidate the host-owned complete practice-line set for one draft."""

    errors: list[str] = []
    try:
        if not _canonical_identifier(matter_id):
            errors.append("practice_binding_index_matter_id_invalid")
        if not _canonical_identifier(draft_id):
            errors.append("practice_binding_index_draft_id_invalid")
    except Exception:
        return ("practice_binding_index_input_validation_error",), None
    try:
        expected_snapshot = _stable_snapshot(expected_bindings)
        expected, expected_errors = _canonical_index_bindings(
            expected_snapshot,
            label="practice_binding_index_expected",
            require_canonical_order=False,
        )
    except Exception:
        return ("practice_binding_index_expected_snapshot_error",), None
    errors.extend(expected_errors)
    if errors:
        return tuple(_unique(errors)), None
    lookup = {"schema_version": "1.0.0", "matter_id": matter_id, "draft_id": draft_id}
    try:
        if authority is None:
            return ("practice_binding_index_authority_required",), None
        resolver = getattr(
            authority, "resolve_practice_claim_evidence_binding_index", None
        )
        if not callable(resolver):
            return ("practice_binding_index_authority_required",), None
        adapter_lookup = deepcopy(lookup)
        resolution = resolver(adapter_lookup)
        request_mutated = adapter_lookup != lookup
    except Exception:
        return ("practice_binding_index_authority_error",), None
    if request_mutated:
        return ("practice_binding_index_request_mutated",), None
    if not isinstance(resolution, Mapping):
        return ("practice_binding_index_resolution_missing",), None
    try:
        resolution_snapshot = _stable_snapshot(resolution)
    except Exception:
        return ("practice_binding_index_resolution_snapshot_error",), None
    if not isinstance(resolution_snapshot, Mapping):
        return ("practice_binding_index_resolution_snapshot_error",), None
    try:
        index_errors, receipt = _index_errors_and_receipt(
            matter_id=matter_id,
            draft_id=draft_id,
            expected=expected,
            resolution=resolution_snapshot,
        )
    except Exception:
        return ("practice_binding_index_resolution_validation_error",), None
    return tuple(index_errors), receipt


__all__ = [
    "PracticeClaimEvidenceBindingAuthority",
    "build_practice_claim_binding_request",
    "build_practice_claim_binding_resolution",
    "build_practice_claim_binding_index_resolution",
    "resolve_practice_claim_evidence_binding",
    "resolve_practice_claim_evidence_binding_index",
]
