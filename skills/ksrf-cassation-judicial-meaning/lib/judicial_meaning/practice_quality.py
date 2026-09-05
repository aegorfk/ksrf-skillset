"""Dependency-free quality gates for case-relative practice analysis.

The functions in this module deliberately accept and return JSON-compatible
objects.  They do not read files, use a database, or make network requests, so
the CLI can persist their content-bound results without hiding side effects.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from .analysis import validate_coding_against_text, validate_coding_record
from .public_corpus import (
    OFFICIAL_EVIDENCE_SEED_ROLES,
    PUBLIC_SEED_ROLES,
    TREATMENT_TYPES,
    official_public_url_allowed,
    public_url_allowed,
    treatment_quality_proposition,
)


SCHEMA_VERSION = "1.0"

UNCERTAINTY_DIMENSIONS = (
    "comparable_reading_plurality",
    "fact_sensitivity",
    "court_distribution",
    "temporal_distribution",
    "chain_endorsement",
    "outcome_materiality",
    "higher_authority_treatment",
    "coverage_limits",
    "coding_reliability",
)

CHAIN_STAGES = (
    "first_instance",
    "appeal",
    "cassation",
    "supreme_court",
    "other",
)
EVIDENCE_ROLES = {"actor_primary_text", "later_court_report"}
CHAIN_TREATMENTS = {
    "originates",
    "expressly_adopts",
    "follows",
    "limits",
    "rejects",
    "does_not_reach",
    "leaves_result_without_endorsing",
    "unclear",
}
OUTCOME_MATERIALITY = {
    "necessary_to_outcome",
    "independent_sufficient_ground",
    "contextual",
    "unclear",
}
AUDITED_CODING_FIELDS = (
    "label",
    "speaker",
    "norm_edition_id",
    "reading_family",
    "relation",
    "reasoning_to_outcome",
    "alternative_grounds",
    "remedy",
)
NON_AUDITED_CODING_CONTENT_FIELDS = (
    "proposition",
    "quote",
    "quote_locator",
    "material_facts",
)
AUDIT_CODING_RECORD_FIELDS = frozenset(
    {
        "candidate_id",
        "chain_id",
        "document_id",
        "label",
        "speaker",
        "proposition",
        "quote",
        "quote_locator",
        "norm_edition_id",
        "reasoning_to_outcome",
        "reading_family",
        "relation",
        "remedy",
        "coder",
        "codebook_version",
        "material_facts",
        "alternative_grounds",
        "human_review",
        "quote_verified",
        "full_text_reviewed",
    }
)
NATIVE_AUDIT_SCREENING_FIELDS = frozenset(
    {
        "schema_version",
        "candidate_id",
        "plan_sha256",
        "chain_id",
        "document_id",
        "source_ids",
        "matches",
        "status",
    }
)
NATIVE_AUDIT_QUEUE_FIELDS = frozenset(
    {
        "schema_version",
        "candidate_id",
        "chain_id",
        "document_id",
        "source_ids",
        "source_text_sha256",
        "primary_coding_sha256",
        "codebook_version",
        "review_state",
    }
)
NATIVE_AUDIT_REVIEW_MATERIAL_FIELDS = frozenset(
    {
        "schema_version",
        "candidate_id",
        "chain_id",
        "document_id",
        "source_text_sha256",
        "packet_text_sha256",
        "text",
    }
)
NATIVE_AUDIT_CODEBOOK_VERSIONS = frozenset({"1.0"})
SUBSTANTIVE_LABELS = {"core_merits", "contextual"}
EXCLUSION_LABELS = {
    "party_only",
    "mentioned_only",
    "quoted_not_adopted",
    "false_positive",
    "unclear",
}
PREFILING_STATUSES = {
    "current_no_material_change",
    "bounded_current_with_disclosed_gaps",
    "refresh_incomplete",
    "material_change_requires_reanalysis",
}
LIVE_CORPUS_BINDING_FIELDS = frozenset(
    {
        "binding_version",
        "verified",
        "live_cache_stable",
        "live_corpus_evidence_digest",
        "live_refresh_plan_sha256",
        "live_treatment_set_sha256",
        "live_treatment_population_sha256",
        "live_treatment_ids",
        "issue_ids",
    }
)
CODING_AUDIT_PLAN_FIELDS = frozenset(
    {
        "schema_version",
        "plan_sha256",
        "screening_sha256",
        "primary_coding_sha256",
        "invalid_screening_record_ids",
        "invalid_primary_record_ids",
        "selection_method",
        "sample_size",
        "exclusion_sample_size",
        "sample_candidate_ids",
        "exclusion_sample_candidate_ids",
        "required_candidate_ids",
        "frozen",
        "audit_plan_sha256",
    }
)
CODING_AUDIT_DECISION_FIELDS = frozenset(
    {
        "candidate_id",
        "primary_coding_sha256",
        "secondary_coding",
        "secondary_coding_sha256",
    }
)
CODING_ADJUDICATION_FIELDS = frozenset(
    {
        "candidate_id",
        "primary_coding_sha256",
        "secondary_coding_sha256",
        "resolved_fields",
        "adjudicator",
        "reviewed_at",
        "human_review",
    }
)
CODING_RELIABILITY_FIELDS = frozenset(
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
CODING_REVIEW_RESOLUTION_FIELDS = frozenset(
    {
        "schema_version",
        "import_receipt_sha256",
        "candidate_id",
        "difference_fields",
        "primary_coding_sha256",
        "secondary_coding_sha256",
        "field_resolutions",
        "reviewer_pseudonym",
        "reviewed_at",
        "human_review",
        "full_text_reviewed",
        "quote_locators_reviewed",
        "final_coding_approved",
    }
)
CODING_REVIEW_FIELD_RESOLUTION_FIELDS = frozenset({"field", "choice"})
CODING_REVIEW_CUSTOM_FIELD_RESOLUTION_FIELDS = frozenset(
    {"field", "choice", "value"}
)
RESOLVED_REVIEW_DECISION_FIELDS = frozenset(
    {
        "schema_version",
        "import_receipt_sha256",
        "candidate_id",
        "difference_fields",
        "primary_coding_sha256",
        "secondary_coding_sha256",
        "field_choices",
        "resolution_sha256",
        "final_coding",
        "final_coding_sha256",
    }
)
CODING_AUDIT_REVIEW_IMPORT_RECEIPT_FIELDS = frozenset(
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
        "review_packet_sha256",
        "secondary_coding_file_sha256",
        "secondary_coding_sha256",
        "codebook_sha256",
        "coding_brief_file_sha256",
        "audit_decisions_file_sha256",
        "candidate_ids",
        "audited_fields",
        "non_audited_content_fields",
        "audited_field_agreement_candidate_ids",
        "audited_field_disagreement_candidate_ids",
        "non_audited_content_difference_candidate_ids",
        "audited_field_differences",
        "non_audited_content_differences",
        "non_audited_content_review_required",
        "adjudication_required",
        "expected_secondary_coder_label_sha256",
        "secondary_coder_label_precommit_verified",
        "returned_quote_literal_presence_verified",
        "quote_locator_verified",
        "secondary_coder_label_differs_from_each_sampled_primary_label",
        "single_secondary_coder_label",
        "bundle_internal_consistency_verified",
        "expected_manifest_digest_match_verified",
        "norm_edition_allowlist_membership_verified",
        "source_workspace_reverified",
        "reviewer_packet_use_attested",
        "norm_edition_temporal_applicability_verified",
        "reviewer_identity_authenticated",
        "human_review_authenticated",
        "independence_verified",
        "receipt_authenticated",
        "publication_safe",
        "legal_readiness",
        "receipt_sha256",
    }
)
CODING_AUDIT_FINALIZATION_RECEIPT_FIELDS = frozenset(
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
CODING_AUDIT_FINALIZATION_RECEIPT_SHA256_FIELDS = frozenset(
    {
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
        "receipt_sha256",
    }
)
REFRESH_PLAN_FIELDS = frozenset(
    {
        "plan_id",
        "as_of",
        "max_age_seconds",
        "evidence_digest",
        "treatment_ids",
        "treatment_population_sha256",
        "coverage_requirements",
        "entries",
        "coverage_gaps",
    }
)
REFRESH_ENTRY_FIELDS = frozenset(
    {"seed_id", "url", "role", "last_fetched_at", "reason"}
)
REFRESH_GAP_SCOPE_FIELDS = frozenset(
    {"court_id", "period_id", "enumerator_id", "source_role"}
)
RFC3339_DATETIME_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?"
    r"(?:[Zz]|[+-]\d{2}:\d{2})?"
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    """Return a stable SHA-256 over canonical UTF-8 JSON."""

    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _diagnostic_digest(value: Any) -> str:
    """Fingerprint malformed JSON values without promoting them to canonical data."""

    try:
        return canonical_digest(value)
    except UnicodeEncodeError:
        escaped = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("ascii")
        return hashlib.sha256(escaped).hexdigest()


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _unique_strings(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not _nonempty(value):
            continue
        cleaned = " ".join(str(value).split())
        if cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _valid_iso(value: Any) -> bool:
    return _aware_iso_datetime(value)


def _parse_iso_datetime(value: str) -> datetime:
    cleaned = value.strip()
    normalized = cleaned[:-1] + "+00:00" if cleaned[-1:] in {"Z", "z"} else cleaned
    return datetime.fromisoformat(normalized)


def _valid_iso_datetime(value: Any) -> bool:
    """Require the RFC 3339 calendar-date/full-time shape used by our schemas."""

    if not _nonempty(value):
        return False
    raw = str(value)
    cleaned = raw.strip()
    if cleaned != raw:
        return False
    if RFC3339_DATETIME_RE.fullmatch(cleaned) is None:
        return False
    try:
        _parse_iso_datetime(cleaned)
    except ValueError:
        return False
    return True


def _aware_iso_datetime(value: Any) -> bool:
    if not _valid_iso_datetime(value):
        return False
    parsed = _parse_iso_datetime(str(value))
    return parsed.utcoffset() is not None


def _canonical_reviewer(value: Any) -> str | None:
    if not _nonempty(value):
        return None
    raw = str(value)
    if any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in raw):
        return None
    normalized = unicodedata.normalize("NFKC", raw).casefold()
    return " ".join(normalized.split())


def _canonical_identifier(value: Any) -> str | None:
    if not _nonempty(value):
        return None
    raw = str(value)
    if any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in raw):
        return None
    return " ".join(raw.split())


def _is_canonical_identifier(value: Any) -> bool:
    canonical = _canonical_identifier(value)
    return canonical is not None and canonical == value


def _is_captured_full_text(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    permitted_layout_controls = {"\t", "\n", "\v", "\f", "\r"}
    return not any(
        unicodedata.category(character) in {"Cf", "Cs"}
        or (
            unicodedata.category(character) == "Cc"
            and character not in permitted_layout_controls
        )
        for character in value
    )


def _coding_provenance_valid(record: Mapping[str, Any]) -> bool:
    return (
        record.get("human_review") == "approved"
        and record.get("quote_verified") is True
        and record.get("full_text_reviewed") is True
    )


def _audit_coding_identity_valid(record: Mapping[str, Any]) -> bool:
    return all(
        _is_canonical_identifier(record.get(field))
        for field in (
            "candidate_id",
            "chain_id",
            "document_id",
            "norm_edition_id",
            "reading_family",
            "remedy",
            "codebook_version",
        )
    ) and _canonical_reviewer(record.get("coder")) is not None


def _coding_visible_text(value: Any) -> bool:
    """Mirror the authoritative coding text predicate without importing internals."""

    return (
        isinstance(value, str)
        and bool(value.strip())
        and not any(
            unicodedata.category(character) in {"Cf", "Cs"}
            or (
                unicodedata.category(character) == "Cc"
                and character not in {"\t", "\n", "\r"}
            )
            for character in value
        )
    )


def _coding_adjudication_field_value_valid(field: str, value: Any) -> bool:
    """Validate each audited value no more narrowly than completed coding does."""

    if field == "label":
        return isinstance(value, str) and value in SUBSTANTIVE_LABELS | EXCLUSION_LABELS
    if field in {"speaker", "reasoning_to_outcome"}:
        return _coding_visible_text(value)
    if field in {"norm_edition_id", "reading_family", "remedy"}:
        return _is_canonical_identifier(value)
    if field == "relation":
        return isinstance(value, str) and value in {
            "supports",
            "adverse",
            "neutral",
            "distinguishes",
            "supersedes",
        }
    if field == "alternative_grounds":
        permitted_fields = {
            "ground",
            "independently_sufficient",
            "quote",
            "quote_locator",
        }
        return isinstance(value, list) and all(
            isinstance(item, dict)
            and set(item).issubset(permitted_fields)
            and _coding_visible_text(item.get("ground"))
            and isinstance(item.get("independently_sufficient"), bool)
            and (
                item.get("quote") is None
                or _coding_visible_text(item.get("quote"))
            )
            and (
                item.get("quote_locator") is None
                or _coding_visible_text(item.get("quote_locator"))
            )
            for item in value
        )
    return False


def _coding_reliability_structure_valid(record: Mapping[str, Any]) -> bool:
    """Validate the closed v1.1 artifact without promoting it to complete."""

    try:
        if not isinstance(record, Mapping) or set(record) != CODING_RELIABILITY_FIELDS:
            return False
        evidence_sha256 = record.get("evidence_sha256")
        digest_payload = dict(record)
        digest_payload.pop("evidence_sha256", None)
        if (
            not _is_sha256(evidence_sha256)
            or canonical_digest(digest_payload) != evidence_sha256
            or record.get("schema_version") != SCHEMA_VERSION
        ):
            return False
        for field in (
            "audit_plan_frozen",
            "audit_plan_contract_valid",
            "audit_plan_digest_valid",
            "stale",
            "complete",
        ):
            if type(record.get(field)) is not bool:
                return False
        for field in (
            "audit_plan_input_sha256",
            "current_primary_coding_sha256",
            "audit_decisions_sha256",
            "adjudications_sha256",
        ):
            if not _is_sha256(record.get(field)):
                return False
        for field in ("audit_plan_sha256", "primary_coding_sha256"):
            value = record.get(field)
            if value is not None and not _is_sha256(value):
                return False

        def unique_identifiers(value: Any) -> bool:
            return (
                isinstance(value, list)
                and all(_is_canonical_identifier(item) for item in value)
                and len(value) == len(set(value))
            )

        required = record.get("required_candidate_ids")
        audited = record.get("audited_candidate_ids")
        if not unique_identifiers(required) or not unique_identifiers(audited):
            return False
        required_set = set(required)
        for field in (
            "missing_candidate_ids",
            "same_reviewer_candidate_ids",
            "invalid_binding_candidate_ids",
            "invalid_provenance_candidate_ids",
            "invalid_screening_record_ids",
            "invalid_primary_record_ids",
            "invalid_audit_record_ids",
            "invalid_adjudication_record_ids",
            "unresolved_candidate_ids",
        ):
            if not unique_identifiers(record.get(field)):
                return False

        disagreements = record.get("field_disagreements")
        if not isinstance(disagreements, list):
            return False
        disagreement_by_candidate: dict[str, Mapping[str, Any]] = {}
        for item in disagreements:
            if not isinstance(item, Mapping):
                return False
            candidate_id = item.get("candidate_id")
            fields = item.get("fields")
            adjudication_sha256 = item.get("adjudication_sha256")
            if (
                set(item)
                != {
                    "candidate_id",
                    "fields",
                    "primary_coding_sha256",
                    "secondary_coding_sha256",
                    "resolved",
                    "adjudication_sha256",
                }
                or not isinstance(candidate_id, str)
                or candidate_id not in required_set
                or candidate_id in disagreement_by_candidate
                or not _unique_nonempty_string_list(fields)
                or not set(fields).issubset(AUDITED_CODING_FIELDS)
                or not _is_sha256(item.get("primary_coding_sha256"))
                or not _is_sha256(item.get("secondary_coding_sha256"))
                or type(item.get("resolved")) is not bool
                or (
                    adjudication_sha256 is not None
                    and not _is_sha256(adjudication_sha256)
                )
            ):
                return False
            disagreement_by_candidate[candidate_id] = item

        empty_adjudications_sha256 = canonical_digest([])
        if (
            not disagreements
            and record.get("adjudications_sha256") != empty_adjudications_sha256
        ) or (
            disagreements
            and record.get("adjudications_sha256") == empty_adjudications_sha256
        ):
            return False

        false_exclusions = record.get("false_exclusion_diagnostics")
        if not isinstance(false_exclusions, list):
            return False
        seen_false_exclusions: set[str] = set()
        for item in false_exclusions:
            if not isinstance(item, Mapping):
                return False
            candidate_id = item.get("candidate_id")
            disagreement = (
                disagreement_by_candidate.get(candidate_id)
                if isinstance(candidate_id, str)
                else None
            )
            if (
                set(item)
                != {"candidate_id", "primary_label", "secondary_label", "resolved"}
                or not isinstance(candidate_id, str)
                or candidate_id not in required_set
                or candidate_id in seen_false_exclusions
                or item.get("primary_label") not in EXCLUSION_LABELS
                or item.get("secondary_label") not in SUBSTANTIVE_LABELS
                or type(item.get("resolved")) is not bool
                or disagreement is None
                or "label" not in disagreement.get("fields", [])
            ):
                return False
            seen_false_exclusions.add(candidate_id)

        if record.get("complete") is True:
            if (
                record.get("stale") is not False
                or record.get("audit_plan_frozen") is not True
                or record.get("audit_plan_contract_valid") is not True
                or record.get("audit_plan_digest_valid") is not True
                or not _is_sha256(record.get("audit_plan_sha256"))
                or not _is_sha256(record.get("primary_coding_sha256"))
                or record.get("primary_coding_sha256")
                != record.get("current_primary_coding_sha256")
                or not required
                or set(audited) != set(required)
            ):
                return False
            for field in (
                "missing_candidate_ids",
                "same_reviewer_candidate_ids",
                "invalid_binding_candidate_ids",
                "invalid_provenance_candidate_ids",
                "invalid_screening_record_ids",
                "invalid_primary_record_ids",
                "invalid_audit_record_ids",
                "invalid_adjudication_record_ids",
                "unresolved_candidate_ids",
            ):
                if record.get(field) != []:
                    return False
            if any(
                item.get("resolved") is not True
                or not _is_sha256(item.get("adjudication_sha256"))
                for item in disagreements
            ) or any(
                item.get("resolved") is not True for item in false_exclusions
            ):
                return False
        return True
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
        return False


def _coding_reliability_contract_valid(record: Mapping[str, Any]) -> bool:
    return (
        _coding_reliability_structure_valid(record)
        and record.get("complete") is True
    )


def _coding_audit_finalization_receipt_contract_valid(
    record: Mapping[str, Any],
) -> bool:
    if set(record) != CODING_AUDIT_FINALIZATION_RECEIPT_FIELDS:
        return False
    if (
        record.get("schema_version") != SCHEMA_VERSION
        or record.get("artifact_type")
        != "coding_audit_finalization_receipt"
        or record.get("producer")
        != "judicial_meaning.quality.coding_audit_finalize"
        or record.get("bundle_contract_version") not in {"1.1", "1.2"}
        or record.get("codebook_version") not in NATIVE_AUDIT_CODEBOOK_VERSIONS
        or not all(
            _is_sha256(record.get(field))
            for field in CODING_AUDIT_FINALIZATION_RECEIPT_SHA256_FIELDS
        )
        or record.get("source_bundle_manifest_sha256")
        != record.get("expected_source_bundle_manifest_sha256")
        or record.get("audit_import_receipt_sha256")
        != record.get("expected_audit_import_receipt_sha256")
    ):
        return False

    candidate_ids_value = record.get("candidate_ids")
    if (
        not isinstance(candidate_ids_value, list)
        or not candidate_ids_value
        or not _unique_nonempty_string_list(candidate_ids_value)
        or not all(
            _is_native_audit_candidate_id(value) for value in candidate_ids_value
        )
    ):
        return False
    candidate_ids = list(candidate_ids_value)
    candidate_id_set = set(candidate_ids)

    allowed_difference_fields = (
        *AUDITED_CODING_FIELDS,
        *NON_AUDITED_CODING_CONTENT_FIELDS,
    )
    allowed_difference_field_set = set(allowed_difference_fields)
    raw_pairs = record.get("required_difference_pairs")
    if not isinstance(raw_pairs, list):
        return False
    pair_set: set[tuple[str, str]] = set()
    for item in raw_pairs:
        if (
            not isinstance(item, Mapping)
            or set(item) != {"candidate_id", "field"}
            or item.get("candidate_id") not in candidate_id_set
            or item.get("field") not in allowed_difference_field_set
        ):
            return False
        pair = (str(item["candidate_id"]), str(item["field"]))
        if pair in pair_set:
            return False
        pair_set.add(pair)
    expected_pairs: list[dict[str, str]] = []
    expected_resolved_candidate_ids: list[str] = []
    expected_populations: list[dict[str, Any]] = []
    for candidate_id in candidate_ids:
        fields = [
            field
            for field in allowed_difference_fields
            if (candidate_id, field) in pair_set
        ]
        if not fields:
            continue
        expected_resolved_candidate_ids.append(candidate_id)
        expected_populations.append(
            {"candidate_id": candidate_id, "fields": fields}
        )
        expected_pairs.extend(
            {"candidate_id": candidate_id, "field": field}
            for field in fields
        )
    if raw_pairs != expected_pairs:
        return False
    if (
        record.get("resolved_candidate_ids") != expected_resolved_candidate_ids
        or record.get("resolved_field_populations") != expected_populations
    ):
        return False

    resolutions_present = record.get("resolutions_present")
    resolutions_file_sha256 = record.get("resolutions_file_sha256")
    if (
        not isinstance(resolutions_present, bool)
        or resolutions_present is not bool(expected_pairs)
        or (
            resolutions_present
            and not _is_sha256(resolutions_file_sha256)
        )
        or (not resolutions_present and resolutions_file_sha256 is not None)
        or record.get("resolutions_state_sha256")
        != canonical_digest(
            {
                "present": resolutions_present,
                "file_sha256": resolutions_file_sha256,
            }
        )
    ):
        return False

    required_true = (
        "difference_resolution_bijection_verified",
        "final_quote_literal_presence_verified",
        "final_quote_normalized_presence_verified",
        "reliability_complete",
    )
    required_false = (
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
    if (
        any(record.get(field) is not True for field in required_true)
        or any(record.get(field) is not False for field in required_false)
        or not isinstance(record.get("quote_locator_review_declared"), bool)
        or record.get("quote_locator_review_declared") is not bool(expected_pairs)
    ):
        return False
    try:
        canonical_digest(record)
    except (TypeError, ValueError, UnicodeEncodeError):
        return False
    return True


_NATIVE_RELIABILITY_DOCTOR_REASON_ORDER = (
    "coding_reliability_unreadable",
    "finalization_receipt_unreadable",
    "coding_reliability_json_invalid",
    "coding_reliability_canonical_bytes_invalid",
    "coding_reliability_contract_invalid",
    "finalization_receipt_json_invalid",
    "finalization_receipt_contract_invalid",
    "expected_finalization_receipt_sha256_invalid",
    "coding_reliability_missing",
    "finalization_receipt_missing",
    "expected_finalization_receipt_sha256_missing",
    "coding_reliability_incomplete",
    "finalization_receipt_self_digest_mismatch",
    "external_finalization_receipt_digest_mismatch",
    "coding_reliability_file_digest_mismatch",
    "audit_plan_digest_mismatch",
    "candidate_population_mismatch",
)
_NATIVE_RELIABILITY_DOCTOR_INPUT_REASON_CODES = frozenset(
    {
        "coding_reliability_unreadable",
        "finalization_receipt_unreadable",
        "coding_reliability_json_invalid",
        "coding_reliability_canonical_bytes_invalid",
        "finalization_receipt_json_invalid",
    }
)
_NATIVE_RELIABILITY_DOCTOR_REMEDIATION = (
    (
        "check_local_read_access",
        "Проверьте, что указанный локальный файл существует и доступен для "
        "чтения; команда не будет его изменять.",
    ),
    (
        "use_original_finalizer_files",
        "Используйте исходные файлы успешной финализации и не исправляйте их "
        "JSON вручную.",
    ),
    (
        "provide_exact_triple",
        "Передайте оба неизменённых файла финализации и отдельно сохранённый "
        "SHA-256 из её успешного стандартного вывода.",
    ),
    (
        "retain_external_digest",
        "Берите ожидаемый SHA-256 только из стандартного вывода успешно "
        "завершившейся финализации и не восстанавливайте его из квитанции.",
    ),
    (
        "recover_in_new_sibling",
        "Повторите финализацию из тех же неизменённых входов в новой соседней "
        "папке и побайтово сравните результат.",
    ),
)


def _evaluate_native_coding_reliability(
    coding_reliability: Any,
    finalization_receipt: Any,
    expected_receipt_sha256: Any,
    *,
    coding_reliability_file_sha256: str | None,
    current_plan_sha256: str | None = None,
) -> dict[str, Any]:
    """Evaluate the native relation without I/O or report-policy projection."""

    reliability = (
        coding_reliability if isinstance(coding_reliability, Mapping) else {}
    )
    receipt = (
        finalization_receipt
        if isinstance(finalization_receipt, Mapping)
        else {}
    )
    try:
        reliability_structure_valid = bool(
            isinstance(coding_reliability, Mapping)
            and _coding_reliability_structure_valid(coding_reliability)
        )
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
        reliability_structure_valid = False
    try:
        reliability_contract_valid = bool(
            isinstance(coding_reliability, Mapping)
            and _coding_reliability_contract_valid(coding_reliability)
        )
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
        reliability_contract_valid = False
    reliability_complete = (
        reliability.get("complete") if reliability_structure_valid else None
    )
    try:
        receipt_contract_valid = bool(
            isinstance(finalization_receipt, Mapping)
            and _coding_audit_finalization_receipt_contract_valid(
                finalization_receipt
            )
        )
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
        receipt_contract_valid = False

    receipt_sha256 = receipt.get("receipt_sha256")
    try:
        unsigned_receipt = {
            key: value
            for key, value in receipt.items()
            if key != "receipt_sha256"
        }
        calculated_receipt_sha256 = canonical_digest(unsigned_receipt)
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
        calculated_receipt_sha256 = None
    receipt_self_digest_valid = bool(
        _is_sha256(receipt_sha256)
        and calculated_receipt_sha256 == receipt_sha256
    )
    expected_receipt_sha256_valid = _is_sha256(expected_receipt_sha256)
    external_receipt_digest_valid = bool(
        expected_receipt_sha256_valid
        and receipt_self_digest_valid
        and expected_receipt_sha256 == receipt_sha256
    )
    reliability_file_digest_valid = bool(
        _is_sha256(coding_reliability_file_sha256)
        and receipt.get("coding_reliability_file_sha256")
        == coding_reliability_file_sha256
    )
    audit_plan_digest_valid = bool(
        _is_sha256(receipt.get("audit_plan_sha256"))
        and receipt.get("audit_plan_sha256")
        == reliability.get("audit_plan_sha256")
    )
    candidate_population_valid = bool(
        isinstance(receipt.get("candidate_ids"), list)
        and receipt.get("candidate_ids")
        == reliability.get("required_candidate_ids")
    )
    current_plan_valid = current_plan_sha256 is None or bool(
        _is_sha256(current_plan_sha256)
        and receipt.get("plan_sha256") == current_plan_sha256
    )
    return {
        "reliability_structure_valid": reliability_structure_valid,
        "reliability_contract_valid": reliability_contract_valid,
        "reliability_complete": reliability_complete,
        "receipt_contract_valid": receipt_contract_valid,
        "expected_receipt_sha256_valid": expected_receipt_sha256_valid,
        "receipt_self_digest_valid": receipt_self_digest_valid,
        "external_receipt_digest_valid": external_receipt_digest_valid,
        "reliability_file_digest_valid": reliability_file_digest_valid,
        "audit_plan_digest_valid": audit_plan_digest_valid,
        "candidate_population_valid": candidate_population_valid,
        "current_plan_valid": current_plan_valid,
    }


def _native_coding_reliability_origin(
    *,
    status: str,
    reason_codes: list[str],
    expected_receipt_sha256: str | None,
    reliability_contract_valid: bool,
    receipt_contract_valid: bool,
    receipt_self_digest_valid: bool,
    external_receipt_digest_valid: bool,
    reliability_file_digest_valid: bool,
    audit_plan_digest_valid: bool,
    candidate_population_valid: bool,
    usable_for_claim: bool,
) -> dict[str, Any]:
    return {
        "status": status,
        "reason_codes": reason_codes,
        "expected_receipt_sha256": expected_receipt_sha256,
        "reliability_contract_valid": reliability_contract_valid,
        "receipt_contract_valid": receipt_contract_valid,
        "receipt_self_digest_valid": receipt_self_digest_valid,
        "external_receipt_digest_valid": external_receipt_digest_valid,
        "reliability_file_digest_valid": reliability_file_digest_valid,
        "audit_plan_digest_valid": audit_plan_digest_valid,
        "candidate_population_valid": candidate_population_valid,
        "usable_for_claim": usable_for_claim,
    }


def build_native_reliability_doctor_report(
    coding_reliability: Mapping[str, Any] | None,
    finalization_receipt: Mapping[str, Any] | None,
    expected_receipt_sha256: str | None,
    *,
    coding_reliability_present: bool,
    coding_reliability_readable: bool | None,
    coding_reliability_canonical_bytes_valid: bool | None,
    coding_reliability_file_sha256: str | None,
    finalization_receipt_present: bool,
    finalization_receipt_readable: bool | None,
    input_reason_codes: Iterable[str] = (),
) -> dict[str, Any]:
    """Build a closed, value-free diagnosis of the Release 17 native relation."""

    state_error = (
        "Внутреннее состояние диагностики нативной надёжности некорректно."
    )
    try:
        supplied_reason_codes = tuple(input_reason_codes)
    except TypeError as error:
        raise ValueError(state_error) from error
    if (
        any(not isinstance(code, str) for code in supplied_reason_codes)
        or not set(supplied_reason_codes).issubset(
            _NATIVE_RELIABILITY_DOCTOR_INPUT_REASON_CODES
        )
    ):
        raise ValueError(state_error)
    supplied_reasons = set(supplied_reason_codes)

    if (
        type(coding_reliability_present) is not bool
        or type(finalization_receipt_present) is not bool
        or (
            coding_reliability_readable is not None
            and type(coding_reliability_readable) is not bool
        )
        or (
            coding_reliability_canonical_bytes_valid is not None
            and type(coding_reliability_canonical_bytes_valid) is not bool
        )
        or (
            finalization_receipt_readable is not None
            and type(finalization_receipt_readable) is not bool
        )
    ):
        raise ValueError(state_error)

    coding_unreadable = "coding_reliability_unreadable" in supplied_reasons
    coding_json_invalid = "coding_reliability_json_invalid" in supplied_reasons
    coding_canonical_invalid = (
        "coding_reliability_canonical_bytes_invalid" in supplied_reasons
    )
    receipt_unreadable = (
        "finalization_receipt_unreadable" in supplied_reasons
    )
    receipt_json_invalid = (
        "finalization_receipt_json_invalid" in supplied_reasons
    )

    if not coding_reliability_present:
        if (
            coding_reliability is not None
            or coding_reliability_readable is not None
            or coding_reliability_canonical_bytes_valid is not None
            or coding_reliability_file_sha256 is not None
            or coding_unreadable
            or coding_json_invalid
            or coding_canonical_invalid
        ):
            raise ValueError(state_error)
    else:
        if coding_reliability_readable is None:
            raise ValueError(state_error)
        if coding_reliability_readable is False:
            if (
                coding_reliability is not None
                or coding_reliability_canonical_bytes_valid is not None
                or coding_reliability_file_sha256 is not None
                or coding_json_invalid
                or coding_canonical_invalid
            ):
                raise ValueError(state_error)
            supplied_reasons.add("coding_reliability_unreadable")
        else:
            if not _is_sha256(coding_reliability_file_sha256):
                raise ValueError(state_error)
            if isinstance(coding_reliability, Mapping):
                if coding_reliability_canonical_bytes_valid is None:
                    raise ValueError(state_error)
                if coding_json_invalid or coding_unreadable:
                    raise ValueError(state_error)
                if coding_reliability_canonical_bytes_valid is False:
                    supplied_reasons.add(
                        "coding_reliability_canonical_bytes_invalid"
                    )
                elif coding_canonical_invalid:
                    raise ValueError(state_error)
            else:
                if coding_reliability_canonical_bytes_valid is True:
                    raise ValueError(state_error)
                if coding_canonical_invalid or coding_unreadable:
                    raise ValueError(state_error)
                supplied_reasons.add("coding_reliability_json_invalid")

    if not finalization_receipt_present:
        if (
            finalization_receipt is not None
            or finalization_receipt_readable is not None
            or receipt_unreadable
            or receipt_json_invalid
        ):
            raise ValueError(state_error)
    else:
        if finalization_receipt_readable is None:
            raise ValueError(state_error)
        if finalization_receipt_readable is False:
            if finalization_receipt is not None or receipt_json_invalid:
                raise ValueError(state_error)
            supplied_reasons.add("finalization_receipt_unreadable")
        elif isinstance(finalization_receipt, Mapping):
            if receipt_unreadable or receipt_json_invalid:
                raise ValueError(state_error)
        else:
            if receipt_unreadable:
                raise ValueError(state_error)
            supplied_reasons.add("finalization_receipt_json_invalid")

    evaluation = _evaluate_native_coding_reliability(
        coding_reliability,
        finalization_receipt,
        expected_receipt_sha256,
        coding_reliability_file_sha256=coding_reliability_file_sha256,
    )
    coding_contract_evaluable = bool(
        coding_reliability_present
        and coding_reliability_readable is True
        and coding_reliability_canonical_bytes_valid is True
        and isinstance(coding_reliability, Mapping)
        and "coding_reliability_json_invalid" not in supplied_reasons
    )
    coding_contract_valid: bool | None = (
        evaluation["reliability_structure_valid"]
        if coding_contract_evaluable
        else None
    )
    coding_complete: bool | None = (
        evaluation["reliability_complete"]
        if coding_contract_valid is True
        else None
    )
    receipt_contract_evaluable = bool(
        finalization_receipt_present
        and finalization_receipt_readable is True
        and isinstance(finalization_receipt, Mapping)
        and "finalization_receipt_json_invalid" not in supplied_reasons
    )
    receipt_contract_valid: bool | None = (
        evaluation["receipt_contract_valid"]
        if receipt_contract_evaluable
        else None
    )
    expected_present = expected_receipt_sha256 is not None
    expected_valid: bool | None = (
        evaluation["expected_receipt_sha256_valid"]
        if expected_present
        else None
    )
    receipt_self_digest_valid: bool | None = (
        evaluation["receipt_self_digest_valid"]
        if receipt_contract_valid is True
        else None
    )
    external_receipt_digest_valid: bool | None = (
        evaluation["external_receipt_digest_valid"]
        if receipt_self_digest_valid is True and expected_valid is True
        else None
    )
    reliability_file_digest_valid: bool | None = (
        evaluation["reliability_file_digest_valid"]
        if (
            coding_contract_valid is True
            and coding_reliability_canonical_bytes_valid is True
            and receipt_contract_valid is True
        )
        else None
    )
    audit_plan_digest_valid: bool | None = (
        evaluation["audit_plan_digest_valid"]
        if coding_contract_valid is True and receipt_contract_valid is True
        else None
    )
    candidate_population_valid: bool | None = (
        evaluation["candidate_population_valid"]
        if coding_contract_valid is True and receipt_contract_valid is True
        else None
    )

    checks = {
        "coding_reliability_present": coding_reliability_present,
        "coding_reliability_readable": coding_reliability_readable,
        "coding_reliability_contract_valid": coding_contract_valid,
        "coding_reliability_complete": coding_complete,
        "finalization_receipt_present": finalization_receipt_present,
        "finalization_receipt_readable": finalization_receipt_readable,
        "finalization_receipt_contract_valid": receipt_contract_valid,
        "expected_receipt_sha256_present": expected_present,
        "expected_receipt_sha256_valid": expected_valid,
        "receipt_self_digest_valid": receipt_self_digest_valid,
        "external_receipt_digest_valid": external_receipt_digest_valid,
        "coding_reliability_file_digest_valid": (
            reliability_file_digest_valid
        ),
        "audit_plan_digest_valid": audit_plan_digest_valid,
        "candidate_population_valid": candidate_population_valid,
    }

    reasons = set(supplied_reasons)
    if not coding_reliability_present:
        reasons.add("coding_reliability_missing")
    if not finalization_receipt_present:
        reasons.add("finalization_receipt_missing")
    if not expected_present:
        reasons.add("expected_finalization_receipt_sha256_missing")
    elif expected_valid is False:
        reasons.add("expected_finalization_receipt_sha256_invalid")
    if coding_contract_valid is False:
        reasons.add("coding_reliability_contract_invalid")
    if coding_complete is False:
        reasons.add("coding_reliability_incomplete")
    if receipt_contract_valid is False:
        reasons.add("finalization_receipt_contract_invalid")
    for value, reason in (
        (
            receipt_self_digest_valid,
            "finalization_receipt_self_digest_mismatch",
        ),
        (
            external_receipt_digest_valid,
            "external_finalization_receipt_digest_mismatch",
        ),
        (
            reliability_file_digest_valid,
            "coding_reliability_file_digest_mismatch",
        ),
        (audit_plan_digest_valid, "audit_plan_digest_mismatch"),
        (candidate_population_valid, "candidate_population_mismatch"),
    ):
        if value is False:
            reasons.add(reason)
    reason_codes = [
        reason
        for reason in _NATIVE_RELIABILITY_DOCTOR_REASON_ORDER
        if reason in reasons
    ]

    if reasons.intersection(_NATIVE_RELIABILITY_DOCTOR_REASON_ORDER[:2]):
        status = "unreadable"
    elif reasons.intersection(_NATIVE_RELIABILITY_DOCTOR_REASON_ORDER[2:8]):
        status = "invalid"
    elif reasons.intersection(_NATIVE_RELIABILITY_DOCTOR_REASON_ORDER[8:12]):
        status = "incomplete"
    elif reasons.intersection(_NATIVE_RELIABILITY_DOCTOR_REASON_ORDER[12:]):
        status = "mismatch"
    else:
        status = "valid"

    selected_remediation: set[str] = set()
    if reasons.intersection(
        {"coding_reliability_unreadable", "finalization_receipt_unreadable"}
    ):
        selected_remediation.add("check_local_read_access")
    if reasons.intersection(
        {
            "coding_reliability_json_invalid",
            "coding_reliability_canonical_bytes_invalid",
            "coding_reliability_contract_invalid",
            "finalization_receipt_json_invalid",
            "finalization_receipt_contract_invalid",
        }
    ):
        selected_remediation.add("use_original_finalizer_files")
    if reasons.intersection(
        {
            "coding_reliability_missing",
            "finalization_receipt_missing",
            "expected_finalization_receipt_sha256_missing",
            "coding_reliability_incomplete",
        }
    ):
        selected_remediation.add("provide_exact_triple")
    if reasons.intersection(
        {
            "expected_finalization_receipt_sha256_missing",
            "expected_finalization_receipt_sha256_invalid",
        }
    ):
        selected_remediation.update(
            {"retain_external_digest", "recover_in_new_sibling"}
        )
    if reasons.intersection(_NATIVE_RELIABILITY_DOCTOR_REASON_ORDER[12:]):
        selected_remediation.add("recover_in_new_sibling")
    remediation = [
        {"code": code, "message_ru": message}
        for code, message in _NATIVE_RELIABILITY_DOCTOR_REMEDIATION
        if code in selected_remediation
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "native_reliability_doctor_report",
        "status": status,
        "native_relation_valid": status == "valid",
        "reason_codes": reason_codes,
        "checks": checks,
        "remediation": remediation,
        "scope": {
            "technical_lineage_only": True,
            "consumer_revalidation_required": True,
            "reviewer_identity_authenticated": False,
            "legal_readiness": False,
            "filing_authorized": False,
        },
    }


_NATIVE_FINALIZATION_COMPARISON_CHECK_ORDER = (
    "common_parent_valid",
    "directories_distinct",
    "uncertain_directory_readable",
    "repeated_directory_readable",
    "uncertain_directory_private",
    "repeated_directory_private",
    "uncertain_inventory_exact",
    "repeated_inventory_exact",
    "expected_receipt_sha256_valid",
    "uncertain_artifact_contracts_valid",
    "repeated_artifact_contracts_valid",
    "uncertain_receipt_self_digest_valid",
    "repeated_receipt_self_digest_valid",
    "repeated_external_receipt_digest_valid",
    "uncertain_receipt_file_bindings_valid",
    "repeated_receipt_file_bindings_valid",
    "uncertain_internal_relation_valid",
    "repeated_native_relation_valid",
    "directory_file_bytes_equal",
    "final_recapture_valid",
)
_NATIVE_FINALIZATION_COMPARISON_REASON_ORDER = (
    "uncertain_finalization_unreadable",
    "repeated_finalization_unreadable",
    "comparison_input_changed",
    "comparison_topology_invalid",
    "uncertain_finalization_privacy_invalid",
    "repeated_finalization_privacy_invalid",
    "uncertain_finalization_inventory_invalid",
    "repeated_finalization_inventory_invalid",
    "expected_finalization_receipt_sha256_invalid",
    "uncertain_finalization_artifact_contract_invalid",
    "repeated_finalization_artifact_contract_invalid",
    "uncertain_finalization_receipt_self_digest_mismatch",
    "repeated_finalization_receipt_self_digest_mismatch",
    "external_finalization_receipt_digest_mismatch",
    "uncertain_finalization_file_binding_mismatch",
    "repeated_finalization_file_binding_mismatch",
    "uncertain_finalization_internal_relation_mismatch",
    "repeated_finalization_native_relation_mismatch",
    "finalization_directory_bytes_mismatch",
)
_NATIVE_FINALIZATION_COMPARISON_INPUT_REASON_BY_CHECK = {
    "uncertain_directory_readable": "uncertain_finalization_unreadable",
    "repeated_directory_readable": "repeated_finalization_unreadable",
    "final_recapture_valid": "comparison_input_changed",
}
_NATIVE_FINALIZATION_COMPARISON_REASON_BY_CHECK = {
    "common_parent_valid": "comparison_topology_invalid",
    "directories_distinct": "comparison_topology_invalid",
    **_NATIVE_FINALIZATION_COMPARISON_INPUT_REASON_BY_CHECK,
    "uncertain_directory_private": (
        "uncertain_finalization_privacy_invalid"
    ),
    "repeated_directory_private": "repeated_finalization_privacy_invalid",
    "uncertain_inventory_exact": (
        "uncertain_finalization_inventory_invalid"
    ),
    "repeated_inventory_exact": "repeated_finalization_inventory_invalid",
    "expected_receipt_sha256_valid": (
        "expected_finalization_receipt_sha256_invalid"
    ),
    "uncertain_artifact_contracts_valid": (
        "uncertain_finalization_artifact_contract_invalid"
    ),
    "repeated_artifact_contracts_valid": (
        "repeated_finalization_artifact_contract_invalid"
    ),
    "uncertain_receipt_self_digest_valid": (
        "uncertain_finalization_receipt_self_digest_mismatch"
    ),
    "repeated_receipt_self_digest_valid": (
        "repeated_finalization_receipt_self_digest_mismatch"
    ),
    "repeated_external_receipt_digest_valid": (
        "external_finalization_receipt_digest_mismatch"
    ),
    "uncertain_receipt_file_bindings_valid": (
        "uncertain_finalization_file_binding_mismatch"
    ),
    "repeated_receipt_file_bindings_valid": (
        "repeated_finalization_file_binding_mismatch"
    ),
    "uncertain_internal_relation_valid": (
        "uncertain_finalization_internal_relation_mismatch"
    ),
    "repeated_native_relation_valid": (
        "repeated_finalization_native_relation_mismatch"
    ),
    "directory_file_bytes_equal": "finalization_directory_bytes_mismatch",
}
_NATIVE_FINALIZATION_COMPARISON_PREREQUISITES = {
    "directories_distinct": (
        "common_parent_valid",
        "uncertain_directory_readable",
        "repeated_directory_readable",
    ),
    "uncertain_directory_private": (
        "common_parent_valid",
        "uncertain_directory_readable",
    ),
    "repeated_directory_private": (
        "common_parent_valid",
        "repeated_directory_readable",
    ),
    "uncertain_inventory_exact": ("uncertain_directory_private",),
    "repeated_inventory_exact": ("repeated_directory_private",),
    "uncertain_artifact_contracts_valid": (
        "uncertain_inventory_exact",
    ),
    "repeated_artifact_contracts_valid": ("repeated_inventory_exact",),
    "uncertain_receipt_self_digest_valid": (
        "uncertain_artifact_contracts_valid",
    ),
    "repeated_receipt_self_digest_valid": (
        "repeated_artifact_contracts_valid",
    ),
    "repeated_external_receipt_digest_valid": (
        "expected_receipt_sha256_valid",
        "repeated_receipt_self_digest_valid",
    ),
    "uncertain_receipt_file_bindings_valid": (
        "uncertain_artifact_contracts_valid",
    ),
    "repeated_receipt_file_bindings_valid": (
        "repeated_artifact_contracts_valid",
    ),
    "uncertain_internal_relation_valid": (
        "uncertain_artifact_contracts_valid",
        "uncertain_receipt_self_digest_valid",
        "uncertain_receipt_file_bindings_valid",
    ),
    "repeated_native_relation_valid": (
        "repeated_artifact_contracts_valid",
        "repeated_receipt_self_digest_valid",
        "repeated_external_receipt_digest_valid",
        "repeated_receipt_file_bindings_valid",
    ),
    "directory_file_bytes_equal": (
        "common_parent_valid",
        "directories_distinct",
        "uncertain_inventory_exact",
        "repeated_inventory_exact",
    ),
    "final_recapture_valid": (
        "common_parent_valid",
        "directories_distinct",
        "uncertain_inventory_exact",
        "repeated_inventory_exact",
    ),
}
_NATIVE_FINALIZATION_COMPARISON_REMEDIATION = (
    (
        "check_local_read_access",
        "Проверьте доступность двух указанных локальных папок, не изменяя их; "
        "команда не выполняет восстановление.",
    ),
    (
        "preserve_and_stop",
        "Остановите использование обеих папок и сохраните их неизменными; "
        "команда ничего не исправляет и не удаляет.",
    ),
    (
        "use_safe_complete_siblings",
        "Сравнивайте только две разные полные четырёхфайловые папки "
        "финализации у одного приватного родителя; небезопасное или неполное "
        "состояние передайте системному администратору.",
    ),
    (
        "retain_successful_repeat_digest",
        "Передайте строчный SHA-256 только из полного стандартного вывода "
        "успешно и нормально завершившегося повтора; не восстанавливайте его "
        "из квитанции.",
    ),
    (
        "administrator_quarantine",
        "При изменении inode, жёсткой ссылке, ACL, неучтённом или "
        "перемещённом объекте остановите автоматику и передайте состояние "
        "системному администратору для учёта всех ссылок и карантина.",
    ),
    (
        "repeat_after_mismatch",
        "Не используйте несовпавшие результаты; после проверки причины снова "
        "выполните финализацию из тех же неизменённых входов в новую "
        "отсутствующую соседнюю папку.",
    ),
)


def build_native_finalization_comparison_report(
    *,
    checks: Mapping[str, bool | None],
    input_reason_codes: Iterable[str] = (),
) -> dict[str, Any]:
    """Build the closed value-free Release 19 comparison report without I/O."""

    state_error = "Внутреннее состояние сравнения папок финализации некорректно."
    try:
        if not isinstance(checks, Mapping):
            raise ValueError(state_error)
        supplied_checks = dict(checks.items())
        if set(supplied_checks) != set(
            _NATIVE_FINALIZATION_COMPARISON_CHECK_ORDER
        ):
            raise ValueError(state_error)
        if any(
            value is not None and type(value) is not bool
            for value in supplied_checks.values()
        ):
            raise ValueError(state_error)
        normalized_checks = {
            key: supplied_checks[key]
            for key in _NATIVE_FINALIZATION_COMPARISON_CHECK_ORDER
        }

        if isinstance(
            input_reason_codes,
            (str, bytes, bytearray, Mapping),
        ):
            raise ValueError(state_error)
        supplied_reason_codes: list[str] = []
        for code in input_reason_codes:
            if len(supplied_reason_codes) == len(
                _NATIVE_FINALIZATION_COMPARISON_INPUT_REASON_BY_CHECK
            ):
                raise ValueError(state_error)
            if type(code) is not str or code in supplied_reason_codes:
                raise ValueError(state_error)
            supplied_reason_codes.append(code)
        input_reason_codes_by_check = {
            reason: check
            for check, reason in (
                _NATIVE_FINALIZATION_COMPARISON_INPUT_REASON_BY_CHECK.items()
            )
        }
        if not set(supplied_reason_codes).issubset(
            input_reason_codes_by_check
        ):
            raise ValueError(state_error)

        if (
            type(normalized_checks["uncertain_directory_readable"])
            is not bool
            or type(normalized_checks["repeated_directory_readable"])
            is not bool
            or type(normalized_checks["expected_receipt_sha256_valid"])
            is not bool
        ):
            raise ValueError(state_error)
        if (
            normalized_checks["common_parent_valid"] is None
            and normalized_checks["uncertain_directory_readable"] is True
            and normalized_checks["repeated_directory_readable"] is True
        ):
            raise ValueError(state_error)

        for check, prerequisites in (
            _NATIVE_FINALIZATION_COMPARISON_PREREQUISITES.items()
        ):
            prerequisites_valid = all(
                normalized_checks[prerequisite] is True
                for prerequisite in prerequisites
            )
            check_value = normalized_checks[check]
            if check == "final_recapture_valid":
                invalid_state = (
                    check_value is True and not prerequisites_valid
                ) or (check_value is None and prerequisites_valid)
            elif check == "directory_file_bytes_equal":
                invalid_state = (
                    not prerequisites_valid and check_value is not None
                ) or (
                    prerequisites_valid
                    and check_value is None
                    and normalized_checks["final_recapture_valid"] is not False
                )
            else:
                invalid_state = prerequisites_valid is (check_value is None)
            if invalid_state:
                raise ValueError(state_error)

        for code in supplied_reason_codes:
            if normalized_checks[input_reason_codes_by_check[code]] is not False:
                raise ValueError(state_error)
    except Exception:
        raise ValueError(state_error) from None

    reasons = set(supplied_reason_codes)
    for check, reason in _NATIVE_FINALIZATION_COMPARISON_REASON_BY_CHECK.items():
        if normalized_checks[check] is False:
            reasons.add(reason)
    reason_codes = [
        reason
        for reason in _NATIVE_FINALIZATION_COMPARISON_REASON_ORDER
        if reason in reasons
    ]

    if reasons.intersection(
        _NATIVE_FINALIZATION_COMPARISON_REASON_ORDER[:3]
    ):
        status = "unreadable"
    elif reasons.intersection(
        _NATIVE_FINALIZATION_COMPARISON_REASON_ORDER[3:11]
    ):
        status = "invalid"
    elif reasons:
        status = "mismatch"
    else:
        status = "match"

    selected_remediation: set[str] = set()
    if reasons.intersection(
        {
            "uncertain_finalization_unreadable",
            "repeated_finalization_unreadable",
        }
    ):
        selected_remediation.add("check_local_read_access")
    if "comparison_input_changed" in reasons:
        selected_remediation.update(
            {"preserve_and_stop", "administrator_quarantine"}
        )
    if reasons.intersection(
        {
            "comparison_topology_invalid",
            "uncertain_finalization_privacy_invalid",
            "repeated_finalization_privacy_invalid",
            "uncertain_finalization_inventory_invalid",
            "repeated_finalization_inventory_invalid",
            "uncertain_finalization_artifact_contract_invalid",
            "repeated_finalization_artifact_contract_invalid",
        }
    ):
        selected_remediation.update(
            {
                "preserve_and_stop",
                "use_safe_complete_siblings",
                "administrator_quarantine",
            }
        )
    if reasons.intersection(
        {
            "expected_finalization_receipt_sha256_invalid",
            "external_finalization_receipt_digest_mismatch",
        }
    ):
        selected_remediation.update(
            {"preserve_and_stop", "retain_successful_repeat_digest"}
        )
    administrator_only_reasons = {
        "comparison_input_changed",
        "comparison_topology_invalid",
        "uncertain_finalization_privacy_invalid",
        "repeated_finalization_privacy_invalid",
        "uncertain_finalization_inventory_invalid",
        "repeated_finalization_inventory_invalid",
        "uncertain_finalization_artifact_contract_invalid",
        "repeated_finalization_artifact_contract_invalid",
    }
    if reasons.intersection(
        {
            "uncertain_finalization_receipt_self_digest_mismatch",
            "repeated_finalization_receipt_self_digest_mismatch",
            "uncertain_finalization_file_binding_mismatch",
            "repeated_finalization_file_binding_mismatch",
            "uncertain_finalization_internal_relation_mismatch",
            "repeated_finalization_native_relation_mismatch",
            "finalization_directory_bytes_mismatch",
        }
    ) and not reasons.intersection(administrator_only_reasons):
        selected_remediation.update(
            {"preserve_and_stop", "repeat_after_mismatch"}
        )
    remediation = [
        {"code": code, "message_ru": message}
        for code, message in _NATIVE_FINALIZATION_COMPARISON_REMEDIATION
        if code in selected_remediation
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "native_finalization_comparison_report",
        "status": status,
        "recovery_comparison_valid": status == "match",
        "reason_codes": reason_codes,
        "checks": normalized_checks,
        "remediation": remediation,
        "scope": {
            "technical_recovery_comparison_only": True,
            "original_recovery_eligibility_verified": False,
            "repeat_normal_return_verified": False,
            "external_digest_provenance_authenticated": False,
            "original_durability_verified": False,
            "consumer_revalidation_required": True,
            "reviewer_identity_authenticated": False,
            "publication_safe": False,
            "legal_readiness": False,
            "filing_authorized": False,
        },
    }


def verify_native_coding_reliability(
    coding_reliability: Mapping[str, Any] | None,
    finalization_receipt: Mapping[str, Any] | None,
    expected_receipt_sha256: str | None,
    *,
    current_plan_sha256: str | None = None,
) -> dict[str, Any]:
    """Verify the externally anchored native coding-reliability relation."""

    receipt_supplied = finalization_receipt is not None
    expectation_supplied = expected_receipt_sha256 is not None
    if not receipt_supplied and not expectation_supplied:
        if coding_reliability is None:
            return _native_coding_reliability_origin(
                status="missing",
                reason_codes=["coding_reliability_missing"],
                expected_receipt_sha256=None,
                reliability_contract_valid=False,
                receipt_contract_valid=False,
                receipt_self_digest_valid=False,
                external_receipt_digest_valid=False,
                reliability_file_digest_valid=False,
                audit_plan_digest_valid=False,
                candidate_population_valid=False,
                usable_for_claim=False,
            )
        evaluation = _evaluate_native_coding_reliability(
            coding_reliability,
            None,
            None,
            coding_reliability_file_sha256=None,
            current_plan_sha256=current_plan_sha256,
        )
        reliability_contract_valid = evaluation[
            "reliability_contract_valid"
        ]
        reason_codes = ["native_finalization_binding_missing"]
        if not reliability_contract_valid:
            reason_codes.insert(0, "coding_reliability_contract_invalid")
        return _native_coding_reliability_origin(
            status="compatibility_only",
            reason_codes=reason_codes,
            expected_receipt_sha256=None,
            reliability_contract_valid=reliability_contract_valid,
            receipt_contract_valid=False,
            receipt_self_digest_valid=False,
            external_receipt_digest_valid=False,
            reliability_file_digest_valid=False,
            audit_plan_digest_valid=False,
            candidate_population_valid=False,
            usable_for_claim=False,
        )

    if (
        coding_reliability is None
        or not receipt_supplied
        or not expectation_supplied
    ):
        raise ValueError(
            "Нативная надёжность кодирования: передан неполный набор "
            "обязательных привязок. Передайте все три исходных значения: "
            "неизменённые файлы coding-reliability.json и "
            "coding-audit-finalization-receipt.json, а также отдельно "
            "сохранённый SHA-256 из успешного вывода coding-audit-finalize."
        )

    try:
        legacy_reliability_file_sha256 = hashlib.sha256(
            _canonical_bytes(coding_reliability) + b"\n"
        ).hexdigest()
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
        legacy_reliability_file_sha256 = None
    evaluation = _evaluate_native_coding_reliability(
        coding_reliability,
        finalization_receipt,
        expected_receipt_sha256,
        coding_reliability_file_sha256=legacy_reliability_file_sha256,
        current_plan_sha256=current_plan_sha256,
    )
    reliability_contract_valid = evaluation["reliability_contract_valid"]
    receipt_contract_valid = evaluation["receipt_contract_valid"]
    receipt_self_digest_valid = evaluation["receipt_self_digest_valid"]
    external_receipt_digest_valid = evaluation[
        "external_receipt_digest_valid"
    ]
    reliability_file_digest_valid = evaluation[
        "reliability_file_digest_valid"
    ]
    audit_plan_digest_valid = evaluation["audit_plan_digest_valid"]
    candidate_population_valid = evaluation["candidate_population_valid"]
    current_plan_valid = evaluation["current_plan_valid"]

    failures = [
        reason
        for valid, reason in (
            (reliability_contract_valid, "coding_reliability_contract_invalid"),
            (receipt_contract_valid, "finalization_receipt_contract_invalid"),
            (receipt_self_digest_valid, "finalization_receipt_self_digest_mismatch"),
            (
                external_receipt_digest_valid,
                "external_finalization_receipt_digest_mismatch",
            ),
            (
                reliability_file_digest_valid,
                "coding_reliability_file_digest_mismatch",
            ),
            (audit_plan_digest_valid, "audit_plan_digest_mismatch"),
            (candidate_population_valid, "candidate_population_mismatch"),
            (current_plan_valid, "current_plan_digest_mismatch"),
        )
        if not valid
    ]
    if failures:
        raise ValueError(
            "Нативная надёжность кодирования не подтверждена ("
            + ",".join(failures)
            + "). Передайте неизменённые файлы Release 16 и отдельно "
            "сохранённый SHA-256 из успешного вывода coding-audit-finalize; "
            "при сомнении повторите восстановление в новой соседней папке "
            "и побайтово сравните результат."
        )

    return _native_coding_reliability_origin(
        status="native_finalization_bound",
        reason_codes=[],
        expected_receipt_sha256=expected_receipt_sha256,
        reliability_contract_valid=True,
        receipt_contract_valid=True,
        receipt_self_digest_valid=True,
        external_receipt_digest_valid=True,
        reliability_file_digest_valid=True,
        audit_plan_digest_valid=True,
        candidate_population_valid=True,
        usable_for_claim=True,
    )


TREATMENT_SOURCE_FIELDS = (
    "source_chain_id",
    "source_court_id",
    "target_authority_id",
    "target_kind",
    "target_identity",
    "target_identity_confirmed",
    "treatment_type",
    "review_decision",
    "snapshot_id",
    "supersedes_treatment_id",
    "superseded_by_treatment_id",
    "speaker",
    "document_id",
    "document_sha256",
    "text_sha256",
    "source_role",
    "official_url",
    "quote",
    "quote_locator",
    "proposition",
    "decision_reason",
    "created_at",
)
TREATMENT_SET_FIELDS = frozenset(
    {
        "schema_version",
        "export_type",
        "corpus_evidence_digest",
        "treatment_population_sha256",
        "integrity_issue_ids",
        "treatment_ids",
        "items",
        "set_sha256",
    }
)
TREATMENT_RESOLVED_FIELDS = frozenset(
    {
        "treatment_id",
        "status",
        *TREATMENT_SOURCE_FIELDS,
        "source_binding_sha256",
        "reviewer",
        "reviewed_at",
        "human_review",
        "quote_verified",
        "full_text_reviewed",
    }
)
TREATMENT_CANDIDATE_FIELDS = frozenset(
    {
        "treatment_id",
        "status",
        "recorded_status",
        "quality_blockers",
        "source_chain_id",
        "target_authority_id",
        "supersedes_treatment_id",
        "superseded_by_treatment_id",
        "created_at",
    }
)


def _treatment_reference(treatment: Mapping[str, Any]) -> str:
    treatment_id = treatment.get("treatment_id")
    if _nonempty(treatment_id):
        return " ".join(str(treatment_id).split())
    return f"unidentified-{canonical_digest(dict(treatment))[:16]}"


def _malformed_treatment_reference(treatment: Any) -> str:
    return f"malformed-{canonical_digest(treatment)[:16]}"


def _treatment_has_reviewed_source(treatment: Mapping[str, Any]) -> bool:
    if set(treatment) != TREATMENT_RESOLVED_FIELDS:
        return False
    source_payload = {field: treatment.get(field) for field in TREATMENT_SOURCE_FIELDS}
    source_bound = (
        _nonempty(treatment.get("source_chain_id"))
        and _is_canonical_identifier(treatment.get("source_chain_id"))
        and _nonempty(treatment.get("source_court_id"))
        and _is_canonical_identifier(treatment.get("source_court_id"))
        and _nonempty(treatment.get("target_authority_id"))
        and _is_canonical_identifier(treatment.get("target_authority_id"))
        and _nonempty(treatment.get("target_kind"))
        and _is_canonical_identifier(treatment.get("target_kind"))
        and isinstance(treatment.get("target_identity"), Mapping)
        and bool(treatment.get("target_identity"))
        and isinstance(treatment.get("target_identity_confirmed"), bool)
        and treatment.get("treatment_type") in TREATMENT_TYPES
        and treatment.get("review_decision") in {"verified", "rejected"}
        and _nonempty(treatment.get("snapshot_id"))
        and (
            treatment.get("supersedes_treatment_id") is None
            or _is_canonical_identifier(treatment.get("supersedes_treatment_id"))
        )
        and (
            treatment.get("superseded_by_treatment_id") is None
            or _is_canonical_identifier(
                treatment.get("superseded_by_treatment_id")
            )
        )
        and treatment.get("snapshot_id")
        == f"snapshot-sha256:{treatment.get('document_sha256')}"
        and _nonempty(treatment.get("document_id"))
        and _is_canonical_identifier(treatment.get("document_id"))
        and _is_sha256(treatment.get("document_sha256"))
        and _is_sha256(treatment.get("text_sha256"))
        and treatment.get("source_role") in OFFICIAL_EVIDENCE_SEED_ROLES
        and official_public_url_allowed(treatment.get("official_url"))
        and _nonempty(treatment.get("proposition"))
        and _aware_iso_datetime(treatment.get("created_at"))
        and _is_sha256(treatment.get("source_binding_sha256"))
        and treatment.get("source_binding_sha256") == canonical_digest(source_payload)
    )
    common_review = (
        source_bound
        and _nonempty(treatment.get("treatment_id"))
        and _is_canonical_identifier(treatment.get("treatment_id"))
        and _is_canonical_identifier(treatment.get("reviewer"))
        and _aware_iso_datetime(treatment.get("reviewed_at"))
        and _parse_iso_datetime(str(treatment.get("reviewed_at")))
        >= _parse_iso_datetime(str(treatment.get("created_at")))
        and _parse_iso_datetime(str(treatment.get("reviewed_at")))
        <= datetime.now(timezone.utc)
        and treatment.get("human_review") == "approved"
        and treatment.get("full_text_reviewed") is True
    )
    if not common_review:
        return False
    status = treatment.get("status")
    review_decision = treatment.get("review_decision")
    if status in {"verified", "rejected"} and status != review_decision:
        return False
    if status == "superseded":
        if (
            not _is_canonical_identifier(
                treatment.get("superseded_by_treatment_id")
            )
            or treatment.get("superseded_by_treatment_id")
            == treatment.get("treatment_id")
        ):
            return False
    elif treatment.get("superseded_by_treatment_id") is not None:
        return False
    if review_decision == "verified":
        return (
            treatment.get("target_identity_confirmed") is True
            and treatment.get("speaker") == "court"
            and _nonempty(treatment.get("quote"))
            and _nonempty(treatment.get("quote_locator"))
            and treatment.get("quote_verified") is True
            and treatment.get("decision_reason") is None
            and treatment.get("proposition")
            == treatment_quality_proposition(
                status="verified",
                source_chain_id=str(treatment.get("source_chain_id")),
                treatment_type=str(treatment.get("treatment_type")),
                target_authority_id=str(treatment.get("target_authority_id")),
            )
        )
    return (
        review_decision == "rejected"
        and _nonempty(treatment.get("decision_reason"))
        and _is_canonical_identifier(treatment.get("decision_reason"))
        and treatment.get("proposition")
        == treatment_quality_proposition(
            status="rejected",
            source_chain_id=str(treatment.get("source_chain_id")),
            treatment_type=str(treatment.get("treatment_type")),
            target_authority_id=str(treatment.get("target_authority_id")),
            decision_reason=str(treatment.get("decision_reason")),
        )
        and (
            (
                treatment.get("quote") is None
                and treatment.get("quote_locator") is None
                and treatment.get("speaker") is None
                and treatment.get("quote_verified") is False
            )
            or (
                treatment.get("speaker") == "court"
                and _nonempty(treatment.get("quote"))
                and _nonempty(treatment.get("quote_locator"))
                and treatment.get("quote_verified") is True
            )
        )
    )


def _treatment_supersession_issue_ids(
    treatments: Sequence[Mapping[str, Any]],
) -> set[str]:
    """Return every record participating in an invalid supersession graph."""

    issues: set[str] = set()
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for treatment in treatments:
        reference = _treatment_reference(treatment)
        grouped.setdefault(reference, []).append(treatment)
    for reference, records in grouped.items():
        if len(records) != 1:
            issues.add(reference)
    records_by_id = {
        reference: records[0]
        for reference, records in grouped.items()
        if len(records) == 1
    }
    successors_by_prior: dict[str, list[str]] = {}
    for treatment_id, treatment in records_by_id.items():
        status = treatment.get("status")
        exact_fields = (
            set(treatment) == TREATMENT_CANDIDATE_FIELDS
            if status == "candidate"
            else set(treatment) == TREATMENT_RESOLVED_FIELDS
        )
        if (
            not exact_fields
            or not _is_canonical_identifier(treatment_id)
            or not _is_canonical_identifier(treatment.get("source_chain_id"))
            or not _is_canonical_identifier(treatment.get("target_authority_id"))
            or not _aware_iso_datetime(treatment.get("created_at"))
        ):
            issues.add(treatment_id)
        for field in ("supersedes_treatment_id", "superseded_by_treatment_id"):
            value = treatment.get(field)
            if value is not None and (
                not _is_canonical_identifier(value) or value == treatment_id
            ):
                issues.add(treatment_id)
        prior_id = treatment.get("supersedes_treatment_id")
        if _is_canonical_identifier(prior_id):
            successors_by_prior.setdefault(str(prior_id), []).append(treatment_id)

    for successor_ids in successors_by_prior.values():
        successor_ids.sort()
    for prior_id, successor_ids in successors_by_prior.items():
        if len(successor_ids) != 1:
            issues.add(prior_id)
            issues.update(successor_ids)
        prior = records_by_id.get(prior_id)
        if prior is None:
            issues.update(successor_ids)
            continue
        for successor_id in successor_ids:
            successor = records_by_id[successor_id]
            if (
                prior.get("status") != "superseded"
                or prior.get("superseded_by_treatment_id") != successor_id
                or successor.get("supersedes_treatment_id") != prior_id
                or prior.get("source_chain_id")
                != successor.get("source_chain_id")
                or prior.get("target_authority_id")
                != successor.get("target_authority_id")
                or set(prior) != TREATMENT_RESOLVED_FIELDS
                or not _aware_iso_datetime(prior.get("reviewed_at"))
                or not _aware_iso_datetime(successor.get("created_at"))
                or (
                    _aware_iso_datetime(prior.get("reviewed_at"))
                    and _aware_iso_datetime(successor.get("created_at"))
                    and _parse_iso_datetime(str(prior.get("reviewed_at")))
                    > _parse_iso_datetime(str(successor.get("created_at")))
                )
            ):
                issues.add(prior_id)
                issues.add(successor_id)

    for treatment_id, treatment in records_by_id.items():
        successor_ids = successors_by_prior.get(treatment_id, [])
        expected_successor = successor_ids[0] if len(successor_ids) == 1 else None
        if (
            treatment.get("superseded_by_treatment_id") != expected_successor
            or (treatment.get("status") == "superseded")
            != (expected_successor is not None)
        ):
            issues.add(treatment_id)
        seen: set[str] = set()
        current_id: str | None = treatment_id
        while current_id is not None:
            if current_id in seen:
                issues.update(seen)
                break
            seen.add(current_id)
            current = records_by_id.get(current_id)
            if current is None:
                break
            prior_id = current.get("supersedes_treatment_id")
            current_id = str(prior_id) if _is_canonical_identifier(prior_id) else None
    return issues


def _treatment_set_contract(
    value: Any,
    *,
    current_corpus_digest: str,
    expected_treatment_ids: Any,
    expected_treatment_population_sha256: Any,
) -> tuple[list[Any], bool, str | None, str | None, str | None]:
    if not isinstance(value, Mapping) or set(value) != TREATMENT_SET_FIELDS:
        return [], False, None, None, None
    items = value.get("items")
    treatment_ids = value.get("treatment_ids")
    corpus_evidence_digest = value.get("corpus_evidence_digest")
    treatment_population_sha256 = value.get("treatment_population_sha256")
    integrity_issue_ids = value.get("integrity_issue_ids")
    set_sha256 = value.get("set_sha256")
    unsigned = dict(value)
    unsigned.pop("set_sha256", None)
    valid = (
        value.get("schema_version") == SCHEMA_VERSION
        and value.get("export_type") == "public_corpus_treatment_quality_set"
        and corpus_evidence_digest
        == f"corpus-evidence-sha256:{current_corpus_digest}"
        and treatment_ids == expected_treatment_ids
        and _is_sha256(treatment_population_sha256)
        and treatment_population_sha256
        == expected_treatment_population_sha256
        and _unique_nonempty_string_list(integrity_issue_ids)
        and isinstance(items, list)
        and isinstance(treatment_ids, list)
        and treatment_ids == sorted(set(treatment_ids))
        and all(
            _is_canonical_identifier(identifier)
            for identifier in treatment_ids
        )
        and all(isinstance(item, Mapping) for item in items)
        and all(
            (
                set(item) == TREATMENT_CANDIDATE_FIELDS
                and item.get("status") == "candidate"
                and item.get("recorded_status")
                in {"candidate", "verified", "rejected"}
                and _unique_nonempty_string_list(item.get("quality_blockers"))
            )
            or (
                set(item) == TREATMENT_RESOLVED_FIELDS
                and item.get("status") in {"verified", "rejected", "superseded"}
            )
            for item in items
        )
        and [item.get("treatment_id") for item in items] == treatment_ids
        and _is_sha256(set_sha256)
        and set_sha256 == canonical_digest(unsigned)
        and not _treatment_supersession_issue_ids(items)
    )
    if valid:
        items_by_id = {
            str(item["treatment_id"]): item
            for item in items
            if isinstance(item, Mapping)
        }
        resolved_successors_by_prior: dict[str, list[str]] = {}
        for item in items_by_id.values():
            if set(item) != TREATMENT_RESOLVED_FIELDS:
                continue
            item_id = str(item["treatment_id"])
            prior_id = item.get("supersedes_treatment_id")
            successor_id = item.get("superseded_by_treatment_id")
            if item.get("status") == "superseded":
                if (
                    not _is_canonical_identifier(successor_id)
                    or successor_id == item_id
                    or successor_id not in items_by_id
                ):
                    valid = False
            elif successor_id is not None:
                valid = False
            if prior_id is not None:
                if (
                    not _is_canonical_identifier(prior_id)
                    or prior_id == item_id
                    or prior_id not in items_by_id
                ):
                    valid = False
                else:
                    resolved_successors_by_prior.setdefault(str(prior_id), []).append(
                        item_id
                    )
                    prior = items_by_id[str(prior_id)]
                    if (
                        set(prior) != TREATMENT_RESOLVED_FIELDS
                        or prior.get("status") != "superseded"
                        or prior.get("superseded_by_treatment_id") != item_id
                        or prior.get("source_chain_id") != item.get("source_chain_id")
                        or prior.get("target_authority_id")
                        != item.get("target_authority_id")
                    ):
                        valid = False
        if any(len(successors) != 1 for successors in resolved_successors_by_prior.values()):
            valid = False
    return (
        list(items) if isinstance(items, list) else [],
        bool(valid),
        set_sha256 if _is_sha256(set_sha256) else None,
        (
            corpus_evidence_digest
            if isinstance(corpus_evidence_digest, str)
            and re.fullmatch(
                r"corpus-evidence-sha256:[0-9a-f]{64}",
                corpus_evidence_digest,
            )
            else None
        ),
        (
            treatment_population_sha256
            if _is_sha256(treatment_population_sha256)
            else None
        ),
    )


def _classify_treatments(
    treatments: Any,
    *,
    final_reviewed_at: str | None = None,
) -> tuple[list[str], list[str], list[str], list[str], list[str], list[str]]:
    pending: set[str] = set()
    verified: set[str] = set()
    rejected: set[str] = set()
    superseded: set[str] = set()
    invalid_resolved: set[str] = set()
    chronology_issues: set[str] = set()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for treatment in treatments:
        if not isinstance(treatment, Mapping):
            reference = _malformed_treatment_reference(treatment)
            pending.add(reference)
            invalid_resolved.add(reference)
            continue
        reference = _treatment_reference(treatment)
        if not _nonempty(treatment.get("treatment_id")):
            pending.add(reference)
            invalid_resolved.add(reference)
            continue
        grouped.setdefault(reference, []).append(dict(treatment))

    graph_issue_ids = _treatment_supersession_issue_ids(
        [record for records in grouped.values() for record in records]
    )

    final_time = (
        _parse_iso_datetime(final_reviewed_at)
        if final_reviewed_at is not None
        else None
    )
    for reference, records in sorted(grouped.items()):
        candidate_chronology_issue = any(
            record.get("status") == "candidate"
            and record.get("recorded_status") in {"verified", "rejected"}
            and isinstance(record.get("quality_blockers"), list)
            and any(
                blocker
                in {
                    "review_chronology_invalid",
                    "reviewed_at_invalid",
                    "supersession_chronology_invalid",
                }
                for blocker in record["quality_blockers"]
            )
            for record in records
        )
        if reference in graph_issue_ids:
            pending.add(reference)
            invalid_resolved.add(reference)
            if candidate_chronology_issue:
                chronology_issues.add(reference)
            continue
        statuses = {record.get("status") for record in records}
        source_bindings = {record.get("source_binding_sha256") for record in records}
        if len(statuses) != 1 or len(source_bindings) != 1:
            pending.add(reference)
            invalid_resolved.add(reference)
            continue
        status = next(iter(statuses))
        if status not in {"verified", "rejected", "superseded"}:
            pending.add(reference)
            if any(
                record.get("recorded_status") in {"verified", "rejected"}
                for record in records
            ):
                invalid_resolved.add(reference)
            if candidate_chronology_issue:
                chronology_issues.add(reference)
            continue
        if not all(_treatment_has_reviewed_source(record) for record in records):
            pending.add(reference)
            invalid_resolved.add(reference)
            continue
        if final_time is not None:
            chronology_valid = True
            for record in records:
                treatment_time = _parse_iso_datetime(str(record["reviewed_at"]))
                timezone_mismatch = (treatment_time.utcoffset() is None) != (
                    final_time.utcoffset() is None
                )
                if timezone_mismatch or (
                    not timezone_mismatch and treatment_time > final_time
                ):
                    chronology_valid = False
                    break
            if not chronology_valid:
                pending.add(reference)
                invalid_resolved.add(reference)
                chronology_issues.add(reference)
                continue
        if status == "verified":
            verified.add(reference)
        elif status == "rejected":
            rejected.add(reference)
        else:
            superseded.add(reference)

    partitions = (pending, verified, rejected, superseded)
    if any(
        left & right
        for index, left in enumerate(partitions)
        for right in partitions[index + 1 :]
    ):
        raise AssertionError("treatment resolution partitions must be disjoint")
    return (
        sorted(pending),
        sorted(verified),
        sorted(rejected),
        sorted(superseded),
        sorted(invalid_resolved),
        sorted(chronology_issues),
    )


def _candidate_id(value: Mapping[str, Any]) -> str | None:
    candidate_id = value.get("candidate_id")
    canonical = _canonical_identifier(candidate_id)
    return canonical if canonical is not None and canonical == candidate_id else None


def _index_unique(
    values: Iterable[Any],
    *,
    record_kind: str,
) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    indexed: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    invalid_records: list[str] = []
    for row_number, value in enumerate(values, start=1):
        if not isinstance(value, Mapping):
            invalid_records.append(
                f"{record_kind}-record-{row_number}-{_diagnostic_digest(value)[:16]}"
            )
            continue
        identifier = _candidate_id(value)
        if identifier is None:
            invalid_records.append(
                f"{record_kind}-record-{row_number}-{_diagnostic_digest(dict(value))[:16]}"
            )
            continue
        if identifier in indexed:
            duplicates.append(identifier)
        else:
            indexed[identifier] = dict(value)
    return indexed, sorted(set(duplicates)), sorted(set(invalid_records))


def _invalid_coding_record_ids(
    records: Mapping[str, dict[str, Any]],
) -> list[str]:
    """Keep malformed codings inspectable while preventing false agreement."""

    return sorted(
        identifier
        for identifier, record in records.items()
        if set(record) != AUDIT_CODING_RECORD_FIELDS
        or validate_coding_record(record)
        or not _audit_coding_identity_valid(record)
    )


def _unique_nonempty_string_list(value: Any) -> bool:
    if not isinstance(value, list) or not all(_nonempty(item) for item in value):
        return False
    normalized = [" ".join(item.split()) for item in value]
    return value == normalized and len(normalized) == len(set(normalized))


def _unique_canonical_identifier_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(_is_canonical_identifier(item) for item in value)
        and len(value) == len(set(value))
    )


def _coding_audit_plan_contract_valid(plan: Mapping[str, Any]) -> bool:
    """Validate the closed frozen-plan contract without an optional dependency."""

    if set(plan) != CODING_AUDIT_PLAN_FIELDS:
        return False
    unsigned = {key: value for key, value in plan.items() if key != "audit_plan_sha256"}
    if (
        plan.get("schema_version") != SCHEMA_VERSION
        or not _is_sha256(plan.get("plan_sha256"))
        or not _is_sha256(plan.get("screening_sha256"))
        or not _is_sha256(plan.get("primary_coding_sha256"))
        or plan.get("selection_method") != "canonical_sha256_rank"
        or plan.get("frozen") is not True
        or not _is_sha256(plan.get("audit_plan_sha256"))
        or plan.get("audit_plan_sha256") != _diagnostic_digest(unsigned)
    ):
        return False
    for field in ("sample_size", "exclusion_sample_size"):
        value = plan.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return False
    for field in (
        "invalid_screening_record_ids",
        "invalid_primary_record_ids",
        "sample_candidate_ids",
        "exclusion_sample_candidate_ids",
        "required_candidate_ids",
    ):
        if not _unique_canonical_identifier_list(plan.get(field)):
            return False
    sample = plan["sample_candidate_ids"]
    exclusion = plan["exclusion_sample_candidate_ids"]
    required = plan["required_candidate_ids"]
    return (
        len(sample) <= plan["sample_size"]
        and len(exclusion) <= plan["exclusion_sample_size"]
        and set(required) == set(sample) | set(exclusion)
    )


def _coding_audit_record_contract_valid(
    record: Mapping[str, Any],
    identifier: str,
) -> bool:
    if set(record) != CODING_AUDIT_DECISION_FIELDS:
        return False
    secondary = record.get("secondary_coding")
    return (
        _canonical_identifier(record.get("candidate_id")) == identifier
        and record.get("candidate_id") == identifier
        and _is_sha256(record.get("primary_coding_sha256"))
        and isinstance(secondary, Mapping)
        and set(secondary) == AUDIT_CODING_RECORD_FIELDS
        and _audit_coding_identity_valid(secondary)
        and _is_sha256(record.get("secondary_coding_sha256"))
        and record.get("secondary_coding_sha256")
        == _diagnostic_digest(dict(secondary))
    )


def _coding_adjudication_contract_valid(
    record: Mapping[str, Any],
    identifier: str,
) -> bool:
    resolved_fields = record.get("resolved_fields")
    reviewed_at = record.get("reviewed_at")
    return (
        set(record) == CODING_ADJUDICATION_FIELDS
        and _canonical_identifier(record.get("candidate_id")) == identifier
        and record.get("candidate_id") == identifier
        and _is_sha256(record.get("primary_coding_sha256"))
        and _is_sha256(record.get("secondary_coding_sha256"))
        and isinstance(resolved_fields, Mapping)
        and bool(resolved_fields)
        and set(resolved_fields).issubset(AUDITED_CODING_FIELDS)
        and all(
            _coding_adjudication_field_value_valid(field, value)
            for field, value in resolved_fields.items()
        )
        and _canonical_reviewer(record.get("adjudicator")) is not None
        and _aware_iso_datetime(reviewed_at)
        and _parse_iso_datetime(str(reviewed_at)) <= datetime.now(timezone.utc)
        and record.get("human_review") == "approved"
    )


def _refresh_entry_contract_valid(
    entry: Any,
    *,
    as_of: datetime,
    max_age_seconds: int,
) -> bool:
    if not isinstance(entry, Mapping) or set(entry) != REFRESH_ENTRY_FIELDS:
        return False
    canonical_seed_id = _canonical_identifier(entry.get("seed_id"))
    if (
        canonical_seed_id is None
        or canonical_seed_id != entry.get("seed_id")
        or not (
            public_url_allowed(entry.get("url"))
            if entry.get("role") == "discovery_only"
            else official_public_url_allowed(entry.get("url"))
        )
        or entry.get("role") not in PUBLIC_SEED_ROLES
        or entry.get("reason")
        not in {
            "never_fetched",
            "stale",
            "invalid_fetched_at",
            "future_fetched_at",
        }
    ):
        return False
    last_fetched = entry.get("last_fetched_at")
    if entry.get("reason") == "never_fetched":
        return last_fetched is None
    if entry.get("reason") == "invalid_fetched_at":
        return _nonempty(last_fetched) and not _aware_iso_datetime(last_fetched)
    if not _aware_iso_datetime(last_fetched):
        return False
    last_time = _parse_iso_datetime(str(last_fetched))
    if entry.get("reason") == "future_fetched_at":
        return last_time > as_of
    return last_time <= as_of and (as_of - last_time).total_seconds() >= max_age_seconds


def _refresh_gap_contract_valid(gap: Any) -> bool:
    if not isinstance(gap, Mapping):
        return False
    allowed = REFRESH_GAP_SCOPE_FIELDS | {"reason", "action"}
    scope = set(gap) & REFRESH_GAP_SCOPE_FIELDS
    if not set(gap).issubset(allowed) or not scope:
        return False
    canonical_scope = {
        field: _canonical_identifier(gap.get(field)) for field in scope
    }
    return (
        all(
            normalized is not None and normalized == gap.get(field)
            for field, normalized in canonical_scope.items()
        )
        and (
            "source_role" not in scope
            or gap.get("source_role") in PUBLIC_SEED_ROLES
        )
        and gap.get("reason") == "coverage_gap_not_observed"
        and _nonempty(gap.get("action"))
    )


def _refresh_requirement_contract_valid(requirement: Any) -> bool:
    if not isinstance(requirement, Mapping):
        return False
    fields = set(requirement)
    if not fields or not fields.issubset(REFRESH_GAP_SCOPE_FIELDS):
        return False
    return all(
        _is_canonical_identifier(requirement.get(field))
        and (
            field != "source_role"
            or requirement.get(field) in PUBLIC_SEED_ROLES
        )
        for field in fields
    )


def _refresh_plan_contract_valid(
    plan: Mapping[str, Any],
    *,
    current_corpus_digest: str,
    checked_through: str,
) -> bool:
    if not isinstance(plan, Mapping) or set(plan) != REFRESH_PLAN_FIELDS:
        return False
    unsigned = {key: value for key, value in plan.items() if key != "plan_id"}
    expected_plan_id = f"refresh-plan-sha256:{canonical_digest(unsigned)}"
    max_age_seconds = plan.get("max_age_seconds")
    requirements = plan.get("coverage_requirements")
    treatment_ids = plan.get("treatment_ids")
    treatment_population_sha256 = plan.get("treatment_population_sha256")
    entries = plan.get("entries")
    gaps = plan.get("coverage_gaps")
    if (
        plan.get("plan_id") != expected_plan_id
        or not _aware_iso_datetime(plan.get("as_of"))
        or isinstance(max_age_seconds, bool)
        or not isinstance(max_age_seconds, int)
        or max_age_seconds < 0
        or plan.get("evidence_digest")
        != f"corpus-evidence-sha256:{current_corpus_digest}"
        or not isinstance(requirements, list)
        or not requirements
        or not isinstance(treatment_ids, list)
        or treatment_ids != sorted(set(treatment_ids))
        or not all(
            _is_canonical_identifier(identifier)
            for identifier in treatment_ids
        )
        or not _is_sha256(treatment_population_sha256)
        or not isinstance(entries, list)
        or not isinstance(gaps, list)
    ):
        return False
    as_of = _parse_iso_datetime(str(plan["as_of"]))
    if as_of > datetime.now(timezone.utc):
        return False
    if _aware_iso_datetime(checked_through):
        checked = _parse_iso_datetime(checked_through)
        if as_of != checked:
            return False
    if not all(
        _refresh_entry_contract_valid(
            entry,
            as_of=as_of,
            max_age_seconds=max_age_seconds,
        )
        for entry in entries
    ):
        return False
    if not all(_refresh_requirement_contract_valid(item) for item in requirements):
        return False
    if not all(_refresh_gap_contract_valid(gap) for gap in gaps):
        return False
    requirement_digests = {canonical_digest(item) for item in requirements}
    gap_scope_digests = {
        canonical_digest(
            {field: gap[field] for field in REFRESH_GAP_SCOPE_FIELDS if field in gap}
        )
        for gap in gaps
    }
    return (
        len(requirement_digests) == len(requirements)
        and gap_scope_digests.issubset(requirement_digests)
        and len({entry["seed_id"] for entry in entries}) == len(entries)
        and len({canonical_digest(gap) for gap in gaps}) == len(gaps)
    )


def _validate_stage_observation(observation: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    required_strings = (
        "observation_id",
        "chain_id",
        "source_stage",
        "position_actor_stage",
        "evidence_role",
        "document_id",
        "official_url",
        "speaker",
        "proposition",
        "quote",
        "quote_locator",
        "treatment_of_prior",
        "disposition",
        "outcome_materiality",
        "reviewer",
        "reviewed_at",
    )
    missing = [field for field in required_strings if not _nonempty(observation.get(field))]
    if missing:
        errors.append("missing:" + ",".join(sorted(missing)))
    if observation.get("source_stage") not in CHAIN_STAGES:
        errors.append("invalid_source_stage")
    if observation.get("position_actor_stage") not in CHAIN_STAGES:
        errors.append("invalid_position_actor_stage")
    evidence_role = observation.get("evidence_role")
    if evidence_role not in EVIDENCE_ROLES:
        errors.append("invalid_evidence_role")
    if (
        evidence_role == "actor_primary_text"
        and observation.get("source_stage") != observation.get("position_actor_stage")
    ):
        errors.append("primary_text_actor_stage_mismatch")
    if observation.get("treatment_of_prior") not in CHAIN_TREATMENTS:
        errors.append("invalid_treatment")
    if observation.get("outcome_materiality") not in OUTCOME_MATERIALITY:
        errors.append("invalid_outcome_materiality")
    if not _is_sha256(observation.get("document_sha256")):
        errors.append("invalid_document_sha256")
    if observation.get("quote_verified") is not True:
        errors.append("quote_not_verified")
    if observation.get("full_text_reviewed") is not True:
        errors.append("full_text_not_reviewed")
    if observation.get("human_review") != "approved":
        errors.append("human_review_not_approved")
    if not _valid_iso(observation.get("reviewed_at")):
        errors.append("invalid_reviewed_at")
    if not isinstance(observation.get("alternative_grounds"), list):
        errors.append("alternative_grounds_not_list")
    if (
        observation.get("treatment_of_prior") == "expressly_adopts"
        and not (
            evidence_role == "actor_primary_text"
            and observation.get("source_stage") in {"appeal", "cassation", "supreme_court"}
        )
    ):
        errors.append("express_adoption_requires_later_primary_text")
    return errors


def analyze_chain_stage_propagation(
    observations: Iterable[Any],
    *,
    required_chain_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Review how a meaning moves inside each judicial chain.

    A later court's report of a lower court is preserved as reported evidence.
    Leaving the result unchanged is never promoted to adoption without an
    express, primary-text statement by the later court.
    """

    raw_observations = [
        dict(item) if isinstance(item, Mapping) else item for item in observations
    ]
    material: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    valid_by_chain: dict[str, list[dict[str, Any]]] = {}
    invalid_chain_ids: set[str] = set()
    for row_number, raw_observation in enumerate(raw_observations, start=1):
        if not isinstance(raw_observation, Mapping):
            unresolved.append(
                {
                    "observation_id": (
                        f"malformed-observation-{row_number}-"
                        f"{canonical_digest(raw_observation)[:16]}"
                    ),
                    "chain_id": None,
                    "errors": ["observation_not_mapping"],
                }
            )
            continue
        observation = dict(raw_observation)
        material.append(observation)
        errors = _validate_stage_observation(observation)
        observation_id = observation.get("observation_id") or f"row-{row_number}"
        chain_id = observation.get("chain_id")
        if errors:
            if _nonempty(chain_id):
                invalid_chain_ids.add(str(chain_id).strip())
            unresolved.append(
                {
                    "observation_id": str(observation_id),
                    "chain_id": str(chain_id) if chain_id is not None else None,
                    "errors": errors,
                }
            )
            continue
        valid_by_chain.setdefault(str(chain_id).strip(), []).append(observation)

    required = sorted(set(_unique_strings(required_chain_ids)))
    for chain_id in required:
        if chain_id not in valid_by_chain:
            unresolved.append(
                {
                    "observation_id": None,
                    "chain_id": chain_id,
                    "errors": ["required_chain_not_reviewed"],
                }
            )
            invalid_chain_ids.add(chain_id)

    stage_order = {stage: index for index, stage in enumerate(CHAIN_STAGES)}
    trajectories: list[dict[str, Any]] = []
    for chain_id in sorted(valid_by_chain):
        chain_observations = sorted(
            valid_by_chain[chain_id],
            key=lambda item: (
                stage_order.get(str(item.get("source_stage")), len(stage_order)),
                str(item.get("observation_id")),
            ),
        )
        reported_only = [
            str(item["observation_id"])
            for item in chain_observations
            if item.get("evidence_role") == "later_court_report"
        ]
        primary_origin = [
            item
            for item in chain_observations
            if item.get("evidence_role") == "actor_primary_text"
            and item.get("treatment_of_prior") == "originates"
            and _nonempty(item.get("reading_family"))
        ]
        origin = min(
            primary_origin,
            key=lambda item: (
                stage_order.get(str(item.get("position_actor_stage")), len(stage_order)),
                str(item.get("observation_id")),
            ),
            default=None,
        )
        cassation_primary = [
            item
            for item in chain_observations
            if item.get("source_stage") == "cassation"
            and item.get("position_actor_stage") == "cassation"
            and item.get("evidence_role") == "actor_primary_text"
        ]
        cassation_treatments = {
            str(item.get("treatment_of_prior")) for item in cassation_primary
        }
        conflicting_treatments = len(cassation_treatments) > 1
        express_rows = [
            item
            for item in cassation_primary
            if item.get("treatment_of_prior") == "expressly_adopts"
        ]
        adoption_family_mismatch = bool(express_rows) and (
            origin is None
            or any(
                not _nonempty(item.get("reading_family"))
                or item.get("reading_family") != origin.get("reading_family")
                for item in express_rows
            )
        )
        if express_rows and not conflicting_treatments and not adoption_family_mismatch:
            cassation_treatment = "expressly_adopts"
            cassation_adoption = True
        elif conflicting_treatments or adoption_family_mismatch:
            cassation_treatment = "unclear"
            cassation_adoption = False
        elif cassation_primary:
            explicit_non_adoption = next(
                (
                    str(item.get("treatment_of_prior"))
                    for item in cassation_primary
                    if item.get("treatment_of_prior")
                    in {
                        "follows",
                        "limits",
                        "rejects",
                        "does_not_reach",
                        "leaves_result_without_endorsing",
                    }
                ),
                None,
            )
            if explicit_non_adoption is not None:
                cassation_treatment = explicit_non_adoption
            elif any(item.get("disposition") == "left_unchanged" for item in cassation_primary):
                cassation_treatment = "leaves_result_without_endorsing"
            else:
                cassation_treatment = "unclear"
            cassation_adoption = False
        else:
            cassation_treatment = "unclear"
            cassation_adoption = False

        alternative_ground = any(
            item.get("outcome_materiality") == "independent_sufficient_ground"
            or any(
                isinstance(ground, Mapping)
                and ground.get("independently_sufficient") is True
                for ground in item.get("alternative_grounds", [])
            )
            for item in chain_observations
        )
        unresolved_reasons: list[str] = []
        if origin is None:
            unresolved_reasons.append("primary_origin_not_observed")
        if not cassation_primary:
            unresolved_reasons.append("cassation_primary_text_not_observed")
        if conflicting_treatments:
            unresolved_reasons.append("conflicting_cassation_treatments")
        if adoption_family_mismatch:
            unresolved_reasons.append("cassation_reading_family_mismatch")
        if cassation_treatment == "unclear":
            unresolved_reasons.append("cassation_treatment_unclear")
        if chain_id in invalid_chain_ids:
            unresolved_reasons.append("invalid_stage_observation")

        if origin is None and reported_only:
            claim_limit = (
                "Позиция нижестоящего суда известна только из пересказа; первичный текст "
                "не проверен, поэтому происхождение судебного смысла не установлено."
            )
        elif cassation_treatment == "leaves_result_without_endorsing":
            claim_limit = (
                "Оставление результата без изменения не означает принятия кассацией "
                "мотивировки нижестоящего суда."
            )
        elif cassation_adoption:
            claim_limit = (
                "Наблюдается прямо выраженное принятие позиции в проверенном первичном тексте; "
                "это не доказывает полноту практики или неконституционность."
            )
        else:
            claim_limit = (
                "Обращение кассации с нижестоящей мотивировкой установлено лишь в раскрытых "
                "пределах и не должно усиливаться предположением."
            )

        observation_hashes = [canonical_digest(item) for item in chain_observations]
        trajectory_payload = {
            "schema_version": SCHEMA_VERSION,
            "chain_id": chain_id,
            "observation_ids": [str(item["observation_id"]) for item in chain_observations],
            "observation_sha256s": observation_hashes,
            "origin_stage": str(origin["position_actor_stage"]) if origin else None,
            "origin_reading_family": str(origin["reading_family"]) if origin else None,
            "reported_only_observation_ids": sorted(reported_only),
            "cassation_treatment": cassation_treatment,
            "cassation_express_adoption": cassation_adoption,
            "alternative_sufficient_ground_present": alternative_ground,
            "review_complete": not unresolved_reasons,
            "unresolved_reasons": sorted(set(unresolved_reasons)),
            "claim_limit": claim_limit,
        }
        trajectories.append(
            {
                **trajectory_payload,
                "trajectory_id": canonical_digest(trajectory_payload),
            }
        )
        if unresolved_reasons:
            unresolved.append(
                {
                    "observation_id": None,
                    "chain_id": chain_id,
                    "errors": sorted(set(unresolved_reasons)),
                }
            )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "observation_count": len(raw_observations),
        "observations_sha256": canonical_digest(raw_observations),
        "chain_count": len(trajectories),
        "required_chain_ids": required,
        "trajectories": trajectories,
        "unresolved": unresolved,
        "review_complete": not unresolved,
    }
    return {**payload, "evidence_sha256": canonical_digest(payload)}


def _dimension(
    state: str,
    *,
    chain_ids: Iterable[Any] = (),
    evidence_refs: Iterable[Any] = (),
    unknowns: Iterable[Any] = (),
    claim_effect: str,
    review_complete: bool,
    assessed: bool | None = None,
    usable_for_claim: bool | None = None,
) -> dict[str, Any]:
    reviewed = bool(review_complete)
    return {
        "state": state,
        "chain_ids": sorted(set(_unique_strings(chain_ids))),
        "evidence_refs": sorted(set(_unique_strings(evidence_refs))),
        "unknowns": sorted(set(_unique_strings(unknowns))),
        "claim_effect": " ".join(claim_effect.split()),
        "assessed": reviewed if assessed is None else bool(assessed),
        "usable_for_claim": reviewed if usable_for_claim is None else bool(usable_for_claim),
        "review_complete": reviewed,
    }


def build_uncertainty_profile(
    *,
    fingerprint_sha256: str,
    position_cards: Iterable[Any],
    comparisons: Mapping[str, Mapping[str, Any]],
    applicant_relations: Mapping[str, Mapping[str, Any]],
    temporal_analysis: Mapping[str, Any] | None,
    trajectories: Iterable[Any],
    source_reconciliation: Mapping[str, Any] | None,
    coding_reliability: Mapping[str, Any] | None,
    higher_authority_treatments: Iterable[Any] | None,
    coding_audit_finalization_receipt: Mapping[str, Any] | None = None,
    expected_finalization_receipt_sha256: str | None = None,
) -> dict[str, Any]:
    """Build nine independent qualitative dimensions without an aggregate number."""

    raw_cards = [
        dict(item) if isinstance(item, Mapping) else item for item in position_cards
    ]
    raw_trajectories = [
        dict(item) if isinstance(item, Mapping) else item for item in trajectories
    ]
    cards: list[dict[str, Any]] = []
    malformed_position_card_refs: list[str] = []
    for row_number, item in enumerate(raw_cards, start=1):
        if not (
            isinstance(item, Mapping)
            and _nonempty(item.get("position_card_id"))
            and _nonempty(item.get("chain_id"))
        ):
            malformed_position_card_refs.append(
                f"position-card-{row_number}-{canonical_digest(item)[:16]}"
            )
            continue
        cards.append(dict(item))

    trajectory_list: list[dict[str, Any]] = []
    malformed_trajectory_refs: list[str] = []
    for row_number, item in enumerate(raw_trajectories, start=1):
        if not (
            isinstance(item, Mapping)
            and _nonempty(item.get("trajectory_id"))
            and _nonempty(item.get("chain_id"))
            and item.get("cassation_treatment") in CHAIN_TREATMENTS
            and isinstance(item.get("review_complete"), bool)
        ):
            malformed_trajectory_refs.append(
                f"trajectory-{row_number}-{canonical_digest(item)[:16]}"
            )
            continue
        trajectory_list.append(dict(item))
    authority_input = (
        None
        if higher_authority_treatments is None
        else [dict(item) if isinstance(item, Mapping) else item for item in higher_authority_treatments]
    )
    coding_reliability_origin = verify_native_coding_reliability(
        coding_reliability,
        coding_audit_finalization_receipt,
        expected_finalization_receipt_sha256,
    )
    current_cards: list[dict[str, Any]] = []
    for card in cards:
        card_id = str(card.get("position_card_id", ""))
        comparison = comparisons.get(card_id, {})
        relation = applicant_relations.get(card_id, {})
        if (
            card_id
            and comparison.get("status") == "matched"
            and comparison.get("fingerprint_sha256") == fingerprint_sha256
            and isinstance(comparison.get("review_provenance"), Mapping)
            and comparison["review_provenance"].get("status") == "approved"
            and relation.get("fingerprint_sha256") == fingerprint_sha256
            and relation.get("human_review") == "approved"
            and relation.get("stale") is not True
        ):
            current_cards.append(card)

    chain_ids = sorted(
        {str(card.get("chain_id")) for card in current_cards if _nonempty(card.get("chain_id"))}
    )
    card_refs = sorted(
        {
            str(card.get("position_card_id"))
            for card in current_cards
            if _nonempty(card.get("position_card_id"))
        }
    )
    family_by_chain = {
        str(card.get("chain_id")): str(card.get("reading_family"))
        for card in current_cards
        if _nonempty(card.get("chain_id")) and _nonempty(card.get("reading_family"))
    }
    families = sorted(set(family_by_chain.values()))
    if not current_cards:
        plurality = _dimension(
            "not_assessed",
            unknowns=["no_current_matched_position_cards"],
            claim_effect="Нельзя описывать конкуренцию чтений без текущих сопоставимых карточек.",
            review_complete=False,
        )
    elif len(families) >= 2:
        plurality = _dimension(
            "multiple_comparable_readings",
            chain_ids=chain_ids,
            evidence_refs=card_refs,
            claim_effect="Можно описать несколько наблюдаемых чтений только в раскрытом сопоставимом корпусе.",
            review_complete=True,
        )
    else:
        plurality = _dimension(
            "single_observed_reading",
            chain_ids=chain_ids,
            evidence_refs=card_refs,
            claim_effect="Одно наблюдаемое чтение не доказывает единообразие всей практики.",
            review_complete=True,
        )

    fact_groups_by_family: dict[str, set[str]] = {}
    missing_fact_groups: list[str] = []
    for card in current_cards:
        family = card.get("reading_family")
        group = card.get("material_facts_group")
        if _nonempty(family) and _nonempty(group):
            fact_groups_by_family.setdefault(str(family), set()).add(str(group))
        elif _nonempty(card.get("chain_id")):
            missing_fact_groups.append(str(card["chain_id"]))
    fact_families = sorted(fact_groups_by_family)
    fact_separated = len(fact_families) >= 2 and all(
        fact_groups_by_family[left].isdisjoint(fact_groups_by_family[right])
        for index, left in enumerate(fact_families)
        for right in fact_families[index + 1 :]
    )
    if not current_cards or missing_fact_groups:
        fact_state = "not_assessed"
        fact_complete = False
        fact_effect = "Нельзя отделить правовое расхождение от различий фактов без полной группировки."
    elif fact_separated:
        fact_state = "fact_separated_readings"
        fact_complete = True
        fact_effect = "Различие чтений может объясняться материальными фактами и не называется судебным расхождением."
    else:
        fact_state = "fact_sensitivity_not_observed"
        fact_complete = True
        fact_effect = "В проверенной группировке различие чтений не разделено материальными фактами."
    fact_dimension = _dimension(
        fact_state,
        chain_ids=chain_ids,
        evidence_refs=card_refs,
        unknowns=missing_fact_groups,
        claim_effect=fact_effect,
        review_complete=fact_complete,
    )

    families_by_court: dict[str, set[str]] = {}
    courts_by_family: dict[str, set[str]] = {}
    missing_courts: list[str] = []
    for card in current_cards:
        court = card.get("court_id")
        family = card.get("reading_family")
        if _nonempty(court) and _nonempty(family):
            families_by_court.setdefault(str(court), set()).add(str(family))
            courts_by_family.setdefault(str(family), set()).add(str(court))
        elif _nonempty(card.get("chain_id")):
            missing_courts.append(str(card["chain_id"]))
    court_families = sorted(courts_by_family)
    court_separated = len(court_families) >= 2 and all(
        courts_by_family[left].isdisjoint(courts_by_family[right])
        for index, left in enumerate(court_families)
        for right in court_families[index + 1 :]
    )
    if not current_cards or missing_courts:
        court_state = "not_assessed"
        court_complete = False
        court_effect = "Территориальное распределение нельзя оценить без идентичности судов."
    elif any(len(values) >= 2 for values in families_by_court.values()):
        court_state = "within_court_plurality"
        court_complete = True
        court_effect = "Несколько чтений наблюдаются внутри одного суда; вывод остаётся описательным."
    elif court_separated:
        court_state = "court_separated_families"
        court_complete = True
        court_effect = "Семьи чтения разделены по судам и не должны автоматически объясняться временем или фактами."
    elif len(families_by_court) >= 2:
        court_state = "cross_court_same_family"
        court_complete = True
        court_effect = "Одинаковая семья наблюдается в нескольких судах только в пределах раскрытого корпуса."
    else:
        court_state = "single_court_observation"
        court_complete = True
        court_effect = "Наблюдение одного суда нельзя распространять на другие кассационные суды."
    court_dimension = _dimension(
        court_state,
        chain_ids=chain_ids,
        evidence_refs=card_refs,
        unknowns=missing_courts,
        claim_effect=court_effect,
        review_complete=court_complete,
    )

    if temporal_analysis is None:
        temporal_dimension = _dimension(
            "not_assessed",
            unknowns=["temporal_analysis_missing"],
            claim_effect="Временное распределение не исследовано.",
            review_complete=False,
        )
    else:
        transitions = [
            item for item in temporal_analysis.get("transitions", []) if isinstance(item, Mapping)
        ]
        transition_refs = [
            f"transition-{index + 1}:{item.get('status', 'unknown')}"
            for index, item in enumerate(transitions)
        ]
        if temporal_analysis.get("temporal_analysis_complete") is not True:
            temporal_state = "insufficient_temporal_observation"
            temporal_effect = "Недостаток временных наблюдений исключает вывод о динамике или причинности."
            temporal_usable = False
        elif any(item.get("status") == "descriptive_distribution_changed" for item in transitions):
            temporal_state = "descriptive_distribution_changed"
            temporal_effect = "Изменилось только наблюдаемое распределение; причинный тренд не установлен."
            temporal_usable = True
        else:
            temporal_state = "no_descriptive_change_observed"
            temporal_effect = "Отсутствие наблюдаемого изменения не доказывает неизменность всей практики."
            temporal_usable = True
        temporal_dimension = _dimension(
            temporal_state,
            chain_ids=chain_ids,
            evidence_refs=transition_refs,
            claim_effect=temporal_effect,
            review_complete=temporal_usable,
            assessed=True,
            usable_for_claim=temporal_usable,
        )

    trajectory_refs = [
        str(item.get("trajectory_id"))
        for item in trajectory_list
        if _nonempty(item.get("trajectory_id"))
    ]
    trajectory_chains = [
        str(item.get("chain_id"))
        for item in trajectory_list
        if _nonempty(item.get("chain_id"))
    ]
    trajectory_states = {
        str(item.get("cassation_treatment"))
        for item in trajectory_list
        if _nonempty(item.get("cassation_treatment"))
    }
    unresolved_trajectory_chains = sorted(
        {
            str(item.get("chain_id"))
            for item in trajectory_list
            if item.get("review_complete") is not True
            and _nonempty(item.get("chain_id"))
        }
    )
    if not trajectory_list:
        chain_dimension = _dimension(
            "not_assessed",
            unknowns=["chain_trajectory_missing"],
            claim_effect="Нельзя приписывать кассации мотивы нижестоящих судов без анализа цепочки.",
            review_complete=False,
        )
    elif unresolved_trajectory_chains:
        chain_dimension = _dimension(
            "unresolved_chain_trajectory",
            chain_ids=trajectory_chains,
            evidence_refs=trajectory_refs,
            unknowns=unresolved_trajectory_chains,
            claim_effect="Неполные цепочки не позволяют использовать вывод о принятии или непринятии мотивировки.",
            review_complete=False,
            assessed=True,
            usable_for_claim=False,
        )
    elif len(trajectory_states) >= 2:
        chain_dimension = _dimension(
            "mixed_chain_treatment",
            chain_ids=trajectory_chains,
            evidence_refs=trajectory_refs,
            unknowns=[
                str(item.get("chain_id"))
                for item in trajectory_list
                if item.get("review_complete") is not True
            ],
            claim_effect="Кассационные суды по-разному обращаются с нижестоящей мотивировкой; каждую цепочку нужно описывать отдельно.",
            review_complete=True,
        )
    elif trajectory_states == {"expressly_adopts"}:
        chain_dimension = _dimension(
            "express_adoption_observed",
            chain_ids=trajectory_chains,
            evidence_refs=trajectory_refs,
            claim_effect="Прямое принятие установлено только по проверенным первичным текстам.",
            review_complete=True,
        )
    else:
        chain_dimension = _dimension(
            "non_endorsement_or_avoidance",
            chain_ids=trajectory_chains,
            evidence_refs=trajectory_refs,
            unknowns=[
                str(item.get("chain_id"))
                for item in trajectory_list
                if item.get("cassation_treatment") == "unclear"
            ],
            claim_effect="Сохранение результата или уклонение от вопроса не считается принятием мотивировки.",
            review_complete=True,
        )

    alternative_chains = sorted(
        {
            str(card.get("chain_id"))
            for card in current_cards
            if card.get("outcome_materiality") == "independent_sufficient_ground"
            or any(
                isinstance(ground, Mapping)
                and ground.get("independently_sufficient") is True
                for ground in card.get("alternative_grounds", [])
            )
        }
    )
    if not current_cards:
        outcome_dimension = _dimension(
            "not_assessed",
            unknowns=["outcome_materiality_missing"],
            claim_effect="Связь толкования с исходом не проверена.",
            review_complete=False,
        )
    elif alternative_chains:
        outcome_dimension = _dimension(
            "alternative_ground_exposure",
            chain_ids=alternative_chains,
            evidence_refs=card_refs,
            claim_effect="Самостоятельное основание ограничивает приписывание результата спорному толкованию.",
            review_complete=True,
        )
    elif all(card.get("outcome_materiality") == "necessary_to_outcome" for card in current_cards):
        outcome_dimension = _dimension(
            "necessary_to_outcome_observed",
            chain_ids=chain_ids,
            evidence_refs=card_refs,
            claim_effect="Исходозначимость наблюдается в проверенных карточках и не распространяется за их пределы.",
            review_complete=True,
        )
    else:
        outcome_dimension = _dimension(
            "mixed_outcome_materiality",
            chain_ids=chain_ids,
            evidence_refs=card_refs,
            claim_effect="Позиции имеют разную роль в исходе и не суммируются как равнозначные подтверждения.",
            review_complete=True,
        )

    if authority_input is None:
        authority_dimension = _dimension(
            "not_assessed",
            unknowns=["higher_authority_treatment_registry_missing"],
            claim_effect="Последующее обращение с авторитетными позициями не проверено.",
            review_complete=False,
        )
    else:
        (
            pending_treatments,
            verified_treatments,
            rejected_treatments,
            superseded_treatments,
            invalid_resolved_treatments,
            _,
        ) = (
            _classify_treatments(authority_input)
        )
        if pending_treatments:
            authority_state = "pending_higher_authority_treatment"
            authority_effect = "Неразрешённые связи с высшей позицией блокируют усиление вывода."
            authority_usable = False
        elif verified_treatments:
            authority_state = "verified_higher_authority_treatment"
            authority_effect = "Последующее обращение подтверждено только указанными цитатами и актами."
            authority_usable = True
        else:
            authority_state = "no_reviewed_treatment_observed"
            authority_effect = "Ноль проверенных связей не означает отсутствия последующей практики."
            authority_usable = True
        authority_dimension = _dimension(
            authority_state,
            evidence_refs=[
                *pending_treatments,
                *verified_treatments,
                *rejected_treatments,
                *superseded_treatments,
            ],
            unknowns=[*pending_treatments, *invalid_resolved_treatments],
            claim_effect=authority_effect,
            review_complete=authority_usable,
            assessed=True,
            usable_for_claim=authority_usable,
        )

    if source_reconciliation is None:
        coverage_dimension = _dimension(
            "not_assessed",
            unknowns=["source_reconciliation_missing"],
            claim_effect="Границы корпуса и открытые маршруты не проверены.",
            review_complete=False,
        )
    else:
        route_coverage = source_reconciliation.get("route_coverage", {})
        route_registry_present = isinstance(route_coverage, Mapping) and bool(
            route_coverage
        )
        routes_closed = route_registry_present and all(
            _nonempty(route_id)
            and
            isinstance(route, Mapping)
            and route.get("status") == "closed_declared_enumeration"
            for route_id, route in route_coverage.items()
        )
        closed = (
            source_reconciliation.get("overall_status") == "closed_declared_enumerations"
            and source_reconciliation.get("all_routes_closed") is True
            and routes_closed
        )
        route_refs = sorted(str(key) for key in route_coverage) if isinstance(route_coverage, Mapping) else []
        coverage_unknowns: list[str] = []
        if not route_registry_present:
            coverage_unknowns.append("declared_route_registry_empty")
        if source_reconciliation.get("all_routes_closed") is not True:
            coverage_unknowns.append("all_routes_closed_not_verified")
        if not routes_closed:
            coverage_unknowns.append("declared_enumeration_not_closed")
        coverage_dimension = _dimension(
            "closed_declared_scope" if closed else "open_disclosed_scope",
            chain_ids=chain_ids,
            evidence_refs=route_refs,
            unknowns=[] if closed else coverage_unknowns,
            claim_effect=(
                "Закрыт только заявленный scope перечислителей, а не вся судебная практика."
                if closed
                else "Открытые маршруты ограничивают вывод наблюдаемым раскрытым корпусом."
            ),
            review_complete=closed,
            assessed=True,
            usable_for_claim=closed,
        )

    if coding_reliability_origin["status"] == "missing":
        reliability_dimension = _dimension(
            "not_assessed",
            unknowns=coding_reliability_origin["reason_codes"],
            claim_effect="Надёжность кодирования не проверена независимой выборкой.",
            review_complete=False,
        )
    elif coding_reliability_origin["status"] == "compatibility_only":
        reliability_dimension = _dimension(
            "compatibility_only",
            evidence_refs=(
                [coding_reliability.get("audit_plan_sha256")]
                if coding_reliability_origin["reliability_contract_valid"]
                and isinstance(coding_reliability, Mapping)
                else []
            ),
            unknowns=coding_reliability_origin["reason_codes"],
            claim_effect=(
                "Отчёт надёжности доступен только для диагностики: без отдельно "
                "подтверждённой квитанции его нельзя использовать в выводе."
            ),
            review_complete=False,
            assessed=True,
            usable_for_claim=False,
        )
    else:
        assert isinstance(coding_reliability, Mapping)
        reliability_dimension = _dimension(
            "independent_audit_complete",
            evidence_refs=[coding_reliability.get("audit_plan_sha256")],
            unknowns=[],
            claim_effect="Независимая выборка проверена; это не превращает кодирование в безошибочное.",
            review_complete=True,
            assessed=True,
            usable_for_claim=True,
        )

    dimensions = {
        "comparable_reading_plurality": plurality,
        "fact_sensitivity": fact_dimension,
        "court_distribution": court_dimension,
        "temporal_distribution": temporal_dimension,
        "chain_endorsement": chain_dimension,
        "outcome_materiality": outcome_dimension,
        "higher_authority_treatment": authority_dimension,
        "coverage_limits": coverage_dimension,
        "coding_reliability": reliability_dimension,
    }

    def block_dimensions(dimension_names: Iterable[str], record_refs: Iterable[str]) -> None:
        refs = sorted(set(_unique_strings(record_refs)))
        if not refs:
            return
        for dimension_name in dimension_names:
            dimension = dimensions[dimension_name]
            dimension["unknowns"] = sorted(
                set(dimension.get("unknowns", [])) | set(refs)
            )
            dimension["assessed"] = True
            dimension["usable_for_claim"] = False
            dimension["review_complete"] = False

    block_dimensions(
        (
            "comparable_reading_plurality",
            "fact_sensitivity",
            "court_distribution",
            "outcome_materiality",
        ),
        malformed_position_card_refs,
    )
    block_dimensions(("chain_endorsement",), malformed_trajectory_refs)

    input_payload = {
        "position_cards": raw_cards,
        "comparisons": comparisons,
        "applicant_relations": applicant_relations,
        "temporal_analysis": temporal_analysis,
        "trajectories": raw_trajectories,
        "source_reconciliation": source_reconciliation,
        "coding_reliability": coding_reliability,
        "higher_authority_treatments": authority_input,
        "coding_audit_finalization_receipt": coding_audit_finalization_receipt,
    }
    input_sha256s = {
        key: canonical_digest(value) for key, value in sorted(input_payload.items())
    }
    input_sha256s["expected_finalization_receipt_sha256"] = (
        expected_finalization_receipt_sha256
        if expected_finalization_receipt_sha256 is not None
        else canonical_digest(None)
    )
    profile_assessed = all(item["assessed"] for item in dimensions.values())
    blocking_dimensions = sorted(
        name for name, item in dimensions.items() if not item["usable_for_claim"]
    )
    claim_use_ready = profile_assessed and not blocking_dimensions
    payload = {
        "schema_version": SCHEMA_VERSION,
        "fingerprint_sha256": fingerprint_sha256,
        "unit": "independent_case_chain",
        "dimensions": dimensions,
        "coding_reliability_origin": coding_reliability_origin,
        "profile_assessed": profile_assessed,
        "claim_use_ready": claim_use_ready,
        "blocking_dimensions": blocking_dimensions,
        "profile_complete": claim_use_ready,
        "numeric_aggregation": "prohibited",
        "constitutional_conclusion_permitted": False,
        "malformed_position_card_refs": sorted(
            set(malformed_position_card_refs)
        ),
        "malformed_trajectory_refs": sorted(set(malformed_trajectory_refs)),
        "input_sha256s": input_sha256s,
        "claim_limit": (
            "Профиль сохраняет независимые объяснения неопределённости; он не является "
            "числовым рейтингом и сам по себе не доказывает неконституционность."
        ),
    }
    return {**payload, "profile_id": canonical_digest(payload)}


def build_coding_audit_plan(
    screening_candidates: Iterable[Any],
    primary_decisions: Iterable[Any],
    *,
    plan_sha256: str,
    sample_size: int,
    exclusion_sample_size: int,
) -> dict[str, Any]:
    """Freeze a deterministic independent-coding and exclusion-audit sample."""

    if not _is_sha256(plan_sha256):
        raise ValueError(
            "Параметр --plan-sha256 должен содержать 64 "
            "строчные шестнадцатеричные цифры."
        )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in (sample_size, exclusion_sample_size)
    ):
        raise ValueError("sample sizes must be non-negative")
    screening_records = [
        dict(item) if isinstance(item, Mapping) else item
        for item in screening_candidates
    ]
    primary_records = [
        dict(item) if isinstance(item, Mapping) else item
        for item in primary_decisions
    ]
    sorted_screening_records = sorted(screening_records, key=canonical_digest)
    sorted_primary_records = sorted(primary_records, key=canonical_digest)
    (
        candidates,
        duplicate_candidates,
        invalid_screening_record_ids,
    ) = _index_unique(sorted_screening_records, record_kind="screening")
    primary, duplicate_primary, invalid_primary_record_ids = _index_unique(
        sorted_primary_records,
        record_kind="primary",
    )
    invalid_primary_record_ids = sorted(
        set(invalid_primary_record_ids)
        | set(_invalid_coding_record_ids(primary))
        | (set(candidates) - set(primary))
    )
    if duplicate_candidates:
        raise ValueError("duplicate screening candidates: " + ", ".join(duplicate_candidates))
    if duplicate_primary:
        raise ValueError("duplicate primary decisions: " + ", ".join(duplicate_primary))
    if not candidates:
        raise ValueError("screening candidate frame is empty")
    unknown_primary = sorted(set(primary) - set(candidates))
    if unknown_primary:
        raise ValueError("primary decisions outside screening frame: " + ", ".join(unknown_primary))

    def rank(identifier: str, lane: str) -> tuple[str, str]:
        return (
            canonical_digest(
                {"plan_sha256": plan_sha256, "lane": lane, "candidate_id": identifier}
            ),
            identifier,
        )

    candidate_ids = sorted(candidates)
    general = sorted(candidate_ids, key=lambda item: rank(item, "general"))[:sample_size]
    exclusion_ids = sorted(
        [
            identifier
            for identifier, decision in primary.items()
            if decision.get("label") in EXCLUSION_LABELS
        ],
        key=lambda item: rank(item, "exclusion"),
    )[:exclusion_sample_size]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "plan_sha256": plan_sha256,
        "screening_sha256": canonical_digest(sorted_screening_records),
        "primary_coding_sha256": canonical_digest(sorted_primary_records),
        "invalid_screening_record_ids": invalid_screening_record_ids,
        "invalid_primary_record_ids": invalid_primary_record_ids,
        "selection_method": "canonical_sha256_rank",
        "sample_size": sample_size,
        "exclusion_sample_size": exclusion_sample_size,
        "sample_candidate_ids": general,
        "exclusion_sample_candidate_ids": exclusion_ids,
        "required_candidate_ids": sorted(set(general) | set(exclusion_ids)),
        "frozen": True,
    }
    return {**payload, "audit_plan_sha256": canonical_digest(payload)}


def _native_audit_candidate_id(
    *, plan_sha256: str, chain_id: str, document_id: str
) -> str:
    """Derive an audit identity without depending on source order or storage IDs."""

    identity = {
        "schema_version": SCHEMA_VERSION,
        "plan_sha256": plan_sha256,
        "chain_id": chain_id,
        "document_id": document_id,
    }
    return "audit-candidate-sha256:" + canonical_digest(identity)


def _is_native_audit_candidate_id(value: Any) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"audit-candidate-sha256:[0-9a-f]{64}", value) is not None
    )


def _native_audit_match_valid(value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value) != {
        "lane",
        "query",
        "start",
        "end",
    }:
        return False
    start = value.get("start")
    end = value.get("end")
    return (
        _is_canonical_identifier(value.get("lane"))
        and _is_canonical_identifier(value.get("query"))
        and isinstance(start, int)
        and not isinstance(start, bool)
        and isinstance(end, int)
        and not isinstance(end, bool)
        and 0 <= start < end
    )


def build_native_coding_audit_inputs(
    screening_candidates: Iterable[Any],
    primary_decisions: Iterable[Any],
    source_texts: Iterable[Any],
    *,
    plan_sha256: str,
    codebook_version: str,
    sample_size: int,
    exclusion_sample_size: int,
) -> dict[str, Any]:
    """Преобразовать проверенную рабочую папку в детерминированные входы аудита.

    Захват файлов и повторный отбор выполняет командная оболочка. Эта чистая
    функция замыкает идентификаторы, сверяет первичную разметку с переданным
    снимком текста и создаёт только явно незавершённые материалы проверки.
    """

    if not _is_sha256(plan_sha256):
        raise ValueError(
            "Контрольная сумма замороженного плана должна быть SHA-256 "
            "из строчных шестнадцатеричных символов."
        )
    if codebook_version not in NATIVE_AUDIT_CODEBOOK_VERSIONS:
        raise ValueError(
            "Версия справочника кодирования не поддерживается этой версией программы."
        )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in (sample_size, exclusion_sample_size)
    ):
        raise ValueError(
            "Размеры аудиторских выборок должны быть неотрицательными целыми числами."
        )
    if sample_size == 0 and exclusion_sample_size == 0:
        raise ValueError(
            "Хотя бы одна аудиторская выборка должна иметь ненулевой максимум."
        )

    sources_by_id: dict[int, dict[str, Any]] = {}
    for row_number, value in enumerate(source_texts, start=1):
        if not isinstance(value, Mapping) or set(value) != {
            "source_id",
            "chain_id",
            "document_id",
            "text_sha256",
            "text",
        }:
            raise ValueError(
                f"Снимок полного текста {row_number} имеет неверный закрытый формат."
            )
        source_id = value.get("source_id")
        chain_id = value.get("chain_id")
        document_id = value.get("document_id")
        text_sha256 = value.get("text_sha256")
        text = value.get("text")
        if (
            isinstance(source_id, bool)
            or not isinstance(source_id, int)
            or source_id < 1
        ):
            raise ValueError(f"У полного текста {row_number} неверный source_id.")
        if source_id in sources_by_id:
            raise ValueError(f"source_id {source_id} повторяется в реестре полных текстов.")
        if not _is_canonical_identifier(chain_id) or not _is_canonical_identifier(
            document_id
        ):
            raise ValueError(
                f"У полного текста source_id={source_id} неканонические идентификаторы."
            )
        if not _is_captured_full_text(text):
            raise ValueError(
                f"У source_id={source_id} отсутствует или небезопасен полный текст."
            )
        normalized_text = re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()
        expected_text_sha256 = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        if text_sha256 != expected_text_sha256:
            raise ValueError(
                f"У source_id={source_id} text_sha256 не совпадает с полным текстом."
            )
        if document_id != f"document-sha256:{expected_text_sha256}":
            raise ValueError(
                f"У source_id={source_id} document_id не связан с полным текстом."
            )
        sources_by_id[source_id] = dict(value)

    screening_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = {}
    seen_screening_source_ids: set[int] = set()
    ordinary_screening_fields = {
        "source_id",
        "document_id",
        "chain_id",
        "matches",
        "status",
    }
    for row_number, value in enumerate(screening_candidates, start=1):
        if not isinstance(value, Mapping) or set(value) != ordinary_screening_fields:
            raise ValueError(
                f"Строка рамки отбора {row_number} имеет неверный закрытый формат."
            )
        source_id = value.get("source_id")
        chain_id = value.get("chain_id")
        document_id = value.get("document_id")
        matches = value.get("matches")
        if (
            isinstance(source_id, bool)
            or not isinstance(source_id, int)
            or source_id < 1
            or source_id in seen_screening_source_ids
        ):
            raise ValueError(
                f"Строка рамки отбора {row_number} содержит неверный или повторный source_id."
            )
        seen_screening_source_ids.add(source_id)
        if not _is_canonical_identifier(chain_id) or not _is_canonical_identifier(
            document_id
        ):
            raise ValueError(
                f"Строка рамки отбора source_id={source_id} имеет "
                "неканонические идентификаторы."
            )
        if (
            value.get("status") != "candidate_needs_full_text_review"
            or not isinstance(matches, list)
            or not matches
            or not all(_native_audit_match_valid(match) for match in matches)
            or len({canonical_digest(match) for match in matches}) != len(matches)
        ):
            raise ValueError(
                f"Строка рамки отбора source_id={source_id} имеет неверные "
                "поля `matches` или `status`."
            )
        source = sources_by_id.get(source_id)
        if source is None or (
            source.get("chain_id"), source.get("document_id")
        ) != (chain_id, document_id):
            raise ValueError(
                f"Строка рамки отбора source_id={source_id} не связана "
                "с тем же полным текстом."
            )
        screening_by_pair.setdefault((chain_id, document_id), []).append(dict(value))

    if not screening_by_pair:
        raise ValueError("Замороженная рамка отбора пуста.")

    audit_screening: list[dict[str, Any]] = []
    text_by_pair: dict[tuple[str, str], str] = {}
    text_digest_by_pair: dict[tuple[str, str], str] = {}
    source_ids_by_pair: dict[tuple[str, str], list[int]] = {}
    for source_id, source in sources_by_id.items():
        pair = (source["chain_id"], source["document_id"])
        source_ids_by_pair.setdefault(pair, []).append(source_id)
    for (chain_id, document_id), records in sorted(screening_by_pair.items()):
        source_ids = sorted(record["source_id"] for record in records)
        if source_ids != sorted(source_ids_by_pair.get((chain_id, document_id), [])):
            raise ValueError(
                "Реестр полных текстов содержит неразрешённый источник той же "
                f"пары `chain_id` / `document_id`: {chain_id}/{document_id}."
            )
        texts = [sources_by_id[source_id]["text"] for source_id in source_ids]
        text_digests = {
            sources_by_id[source_id]["text_sha256"] for source_id in source_ids
        }
        packet_text_digests = {
            hashlib.sha256(text.encode("utf-8")).hexdigest() for text in texts
        }
        match_digests = {canonical_digest(record["matches"]) for record in records}
        if (
            len(text_digests) != 1
            or len(packet_text_digests) != 1
            or len(match_digests) != 1
        ):
            raise ValueError(
                "Несколько источников одной пары `chain_id` / `document_id` содержат "
                "разные точные тексты или совпадения рамки отбора: "
                f"{chain_id}/{document_id}."
            )
        candidate_id = _native_audit_candidate_id(
            plan_sha256=plan_sha256,
            chain_id=chain_id,
            document_id=document_id,
        )
        audit_record = {
            "schema_version": SCHEMA_VERSION,
            "candidate_id": candidate_id,
            "plan_sha256": plan_sha256,
            "chain_id": chain_id,
            "document_id": document_id,
            "source_ids": source_ids,
            "matches": records[0]["matches"],
            "status": "candidate_needs_full_text_review",
        }
        if set(audit_record) != NATIVE_AUDIT_SCREENING_FIELDS:
            raise AssertionError("неожиданный формат строки аудиторской рамки отбора")
        audit_screening.append(audit_record)
        text_by_pair[(chain_id, document_id)] = texts[0]
        text_digest_by_pair[(chain_id, document_id)] = next(iter(text_digests))

    primary_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for row_number, value in enumerate(primary_decisions, start=1):
        if not isinstance(value, Mapping):
            raise ValueError(
                f"Строка первичной разметки {row_number} должна быть объектом."
            )
        chain_id = value.get("chain_id")
        document_id = value.get("document_id")
        if not _is_canonical_identifier(chain_id) or not _is_canonical_identifier(
            document_id
        ):
            raise ValueError(
                f"Строка первичной разметки {row_number} имеет "
                "неканонические идентификаторы."
            )
        pair = (chain_id, document_id)
        if pair in primary_by_pair:
            raise ValueError(
                "Первичная разметка повторяет пару `chain_id` / `document_id`: "
                f"{chain_id}/{document_id}."
            )
        primary_by_pair[pair] = dict(value)

    missing_primary = sorted(set(screening_by_pair) - set(primary_by_pair))
    extra_primary = sorted(set(primary_by_pair) - set(screening_by_pair))
    if missing_primary or extra_primary:
        details: list[str] = []
        if missing_primary:
            details.append(
                "нет первичной разметки для "
                + ", ".join(f"{chain}/{document}" for chain, document in missing_primary)
            )
        if extra_primary:
            details.append(
                "лишняя первичная разметка для "
                + ", ".join(f"{chain}/{document}" for chain, document in extra_primary)
            )
        raise ValueError(
            "Первичная разметка не совпадает с рамкой отбора: " + "; ".join(details)
        )

    projected_primary: list[dict[str, Any]] = []
    primary_by_candidate: dict[str, dict[str, Any]] = {}
    for screening_record in audit_screening:
        candidate_id = screening_record["candidate_id"]
        pair = (screening_record["chain_id"], screening_record["document_id"])
        ordinary = primary_by_pair[pair]
        supplied_candidate_id = ordinary.get("candidate_id")
        if "candidate_id" in ordinary and supplied_candidate_id != candidate_id:
            raise ValueError(
                f"Первичная разметка {pair[0]}/{pair[1]} связана "
                "с чужим candidate_id."
            )
        projected = {
            field: ordinary.get(field) for field in AUDIT_CODING_RECORD_FIELDS
        }
        projected["candidate_id"] = candidate_id
        if projected.get("codebook_version") != codebook_version:
            raise ValueError(
                f"Первичная разметка {pair[0]}/{pair[1]} использует другую "
                "версию справочника кодирования."
            )
        errors = validate_coding_against_text(projected, text_by_pair[pair])
        if errors:
            raise ValueError(
                f"Первичная разметка {pair[0]}/{pair[1]} не прошла проверку: "
                + "; ".join(errors)
            )
        canonical_digest(projected)
        projected_primary.append(projected)
        primary_by_candidate[candidate_id] = projected

    audit_screening.sort(key=lambda record: record["candidate_id"])
    projected_primary.sort(key=lambda record: record["candidate_id"])
    audit_plan = build_coding_audit_plan(
        audit_screening,
        projected_primary,
        plan_sha256=plan_sha256,
        sample_size=sample_size,
        exclusion_sample_size=exclusion_sample_size,
    )
    if audit_plan["invalid_screening_record_ids"] or audit_plan[
        "invalid_primary_record_ids"
    ]:
        raise ValueError(
            "Производный план аудита содержит недопустимые входные записи."
        )
    required_candidate_ids = audit_plan["required_candidate_ids"]
    if not required_candidate_ids:
        raise ValueError(
            "Заданные максимумы не выбрали ни одного кандидата для аудита."
        )

    secondary_queue: list[dict[str, Any]] = []
    secondary_templates: list[dict[str, Any]] = []
    secondary_review_materials: list[dict[str, Any]] = []
    source_text_inventory: list[dict[str, Any]] = []
    for screening_record in audit_screening:
        candidate_id = screening_record["candidate_id"]
        pair = (screening_record["chain_id"], screening_record["document_id"])
        source_text_inventory.append(
            {
                "candidate_id": candidate_id,
                "source_ids": screening_record["source_ids"],
                "source_text_sha256": text_digest_by_pair[pair],
            }
        )
        if candidate_id not in required_candidate_ids:
            continue
        primary = primary_by_candidate[candidate_id]
        packet_text = text_by_pair[pair]
        review_material = {
            "schema_version": SCHEMA_VERSION,
            "candidate_id": candidate_id,
            "chain_id": pair[0],
            "document_id": pair[1],
            "source_text_sha256": text_digest_by_pair[pair],
            "packet_text_sha256": hashlib.sha256(
                packet_text.encode("utf-8")
            ).hexdigest(),
            "text": packet_text,
        }
        if set(review_material) != NATIVE_AUDIT_REVIEW_MATERIAL_FIELDS:
            raise AssertionError("неожиданный формат материала аудиторской проверки")
        secondary_review_materials.append(review_material)
        queue_record = {
            "schema_version": SCHEMA_VERSION,
            "candidate_id": candidate_id,
            "chain_id": pair[0],
            "document_id": pair[1],
            "source_ids": screening_record["source_ids"],
            "source_text_sha256": text_digest_by_pair[pair],
            "primary_coding_sha256": canonical_digest(primary),
            "codebook_version": codebook_version,
            "review_state": "independent_secondary_required",
        }
        if set(queue_record) != NATIVE_AUDIT_QUEUE_FIELDS:
            raise AssertionError("неожиданный формат очереди аудиторской проверки")
        secondary_queue.append(queue_record)
        template = {field: None for field in AUDIT_CODING_RECORD_FIELDS}
        template.update(
            {
                "candidate_id": candidate_id,
                "chain_id": pair[0],
                "document_id": pair[1],
                "codebook_version": codebook_version,
                "material_facts": [],
                "alternative_grounds": [],
                "human_review": "pending",
                "quote_verified": False,
                "full_text_reviewed": False,
            }
        )
        secondary_templates.append(template)

    return {
        "screening_candidates": audit_screening,
        "primary_decisions": projected_primary,
        "audit_plan": audit_plan,
        "secondary_review_queue": secondary_queue,
        "secondary_coding_templates": secondary_templates,
        "secondary_review_materials": secondary_review_materials,
        "codebook_version": codebook_version,
        "source_text_inventory_sha256": canonical_digest(source_text_inventory),
    }


def build_native_coding_review_import(
    audit_plan: Mapping[str, Any],
    primary_decisions: Iterable[Any],
    secondary_review_queue: Iterable[Any],
    secondary_review_materials: Iterable[Any],
    secondary_codings: Iterable[Any],
    *,
    codebook_version: str,
    norm_edition_ids: Iterable[str],
    expected_secondary_coder: str,
) -> dict[str, Any]:
    """Проверить возвращённую разметку и собрать решения для оценки надёжности.

    Функция намеренно не работает с файловой системой. Вызывающая сторона
    должна сначала проверить внутреннюю согласованность пакета и привязать его
    к отдельно сохранённому значению, а затем атомарно записать результат.
    Здесь замыкаются наборы записей, каждый ответ связывается с замороженной
    первичной разметкой и точным текстом, после чего заново проверяются цитаты.
    """

    if not isinstance(audit_plan, Mapping) or not _coding_audit_plan_contract_valid(
        audit_plan
    ):
        raise ValueError("Замороженный план аудита имеет неверный закрытый контракт.")
    if audit_plan.get("invalid_screening_record_ids") or audit_plan.get(
        "invalid_primary_record_ids"
    ):
        raise ValueError("План аудита содержит недопустимые входные записи.")
    required_candidate_ids = list(audit_plan["required_candidate_ids"])
    if (
        not required_candidate_ids
        or any(
            not _is_native_audit_candidate_id(candidate_id)
            for candidate_id in required_candidate_ids
        )
    ):
        raise ValueError(
            "План аудита не содержит канонический набор обязательных кандидатов."
        )

    if codebook_version not in NATIVE_AUDIT_CODEBOOK_VERSIONS:
        raise ValueError(
            "Версия справочника кодирования не поддерживается этой версией программы."
        )

    if isinstance(norm_edition_ids, (str, bytes)):
        raise ValueError("Список допустимых редакций норм имеет неверный формат.")
    allowed_norm_editions = list(norm_edition_ids)
    if (
        not allowed_norm_editions
        or not all(_is_canonical_identifier(value) for value in allowed_norm_editions)
        or len(allowed_norm_editions) != len(set(allowed_norm_editions))
    ):
        raise ValueError("Список допустимых редакций норм пуст или неканоничен.")
    allowed_norm_edition_set = set(allowed_norm_editions)

    expected_coder = _canonical_reviewer(expected_secondary_coder)
    if expected_coder is None:
        raise ValueError("Ожидаемая метка второго кодировщика неканонична.")

    def closed_index(
        values: Iterable[Any],
        *,
        record_kind: str,
        fields: frozenset[str],
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        if isinstance(values, (str, bytes, Mapping)):
            raise ValueError(f"Набор {record_kind} имеет неверный формат.")
        records: list[dict[str, Any]] = []
        indexed: dict[str, dict[str, Any]] = {}
        for row_number, value in enumerate(values, start=1):
            if not isinstance(value, Mapping) or set(value) != fields:
                raise ValueError(
                    f"Строка {record_kind} {row_number} имеет неверный закрытый формат."
                )
            record = dict(value)
            candidate_id = record.get("candidate_id")
            if not _is_native_audit_candidate_id(candidate_id):
                raise ValueError(
                    f"Строка {record_kind} {row_number} имеет неканонический candidate_id."
                )
            if candidate_id in indexed:
                raise ValueError(f"Набор {record_kind} повторяет candidate_id.")
            records.append(record)
            indexed[candidate_id] = record
        return records, indexed

    primary_records, primary_by_candidate = closed_index(
        primary_decisions,
        record_kind="первичной разметки",
        fields=AUDIT_CODING_RECORD_FIELDS,
    )
    for candidate_id, record in primary_by_candidate.items():
        errors = validate_coding_record(record)
        if errors or not _audit_coding_identity_valid(record):
            raise ValueError(
                "Первичная разметка не завершена или неканонична: "
                + "; ".join(errors or ["неверные идентификаторы"])
            )
        if record.get("codebook_version") != codebook_version:
            raise ValueError("Первичная разметка использует другую версию справочника.")
    try:
        primary_records_in_digest_order = sorted(primary_records, key=canonical_digest)
        primary_coding_sha256 = canonical_digest(primary_records_in_digest_order)
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ValueError("Первичная разметка не является каноническим JSON.") from exc
    if primary_coding_sha256 != audit_plan.get("primary_coding_sha256"):
        raise ValueError(
            "Первичная разметка не совпадает с контрольной суммой "
            "замороженного плана аудита."
        )

    _, queue_by_candidate = closed_index(
        secondary_review_queue,
        record_kind="очереди вторичной проверки",
        fields=NATIVE_AUDIT_QUEUE_FIELDS,
    )
    _, material_by_candidate = closed_index(
        secondary_review_materials,
        record_kind="материалов проверки",
        fields=NATIVE_AUDIT_REVIEW_MATERIAL_FIELDS,
    )
    secondary_records, secondary_by_candidate = closed_index(
        secondary_codings,
        record_kind="вторичной разметки",
        fields=AUDIT_CODING_RECORD_FIELDS,
    )

    expected_population = set(required_candidate_ids)
    for name, population in (
        ("первичной разметки", set(primary_by_candidate)),
        ("очереди вторичной проверки", set(queue_by_candidate)),
        ("материалов проверки", set(material_by_candidate)),
        ("вторичной разметки", set(secondary_by_candidate)),
    ):
        missing = expected_population - population
        extra = population - expected_population
        if name == "первичной разметки":
            extra = set()
        if missing or extra:
            raise ValueError(
                f"Набор {name} не совпадает с замороженной выборкой: "
                f"отсутствуют {len(missing)}, лишние {len(extra)}."
            )

    audit_decisions: list[dict[str, Any]] = []
    audited_agreement: list[str] = []
    audited_disagreement: list[str] = []
    non_audited_difference: list[str] = []
    audited_field_differences: list[dict[str, Any]] = []
    non_audited_content_differences: list[dict[str, Any]] = []
    adjudication_required_candidate_ids: list[str] = []

    for candidate_id in required_candidate_ids:
        primary = primary_by_candidate[candidate_id]
        queue = queue_by_candidate[candidate_id]
        material = material_by_candidate[candidate_id]
        secondary = secondary_by_candidate[candidate_id]
        chain_id = primary["chain_id"]
        document_id = primary["document_id"]

        if candidate_id != _native_audit_candidate_id(
            plan_sha256=audit_plan["plan_sha256"],
            chain_id=chain_id,
            document_id=document_id,
        ):
            raise ValueError(
                "candidate_id не связан с идентификаторами `plan_sha256`, "
                "`chain_id` и `document_id`."
            )
        if (
            queue.get("schema_version") != SCHEMA_VERSION
            or queue.get("review_state") != "independent_secondary_required"
            or queue.get("codebook_version") != codebook_version
            or any(
                queue.get(field) != expected
                for field, expected in (
                    ("candidate_id", candidate_id),
                    ("chain_id", chain_id),
                    ("document_id", document_id),
                )
            )
        ):
            raise ValueError("Очередь имеет неверные идентификаторы или статус.")
        source_ids = queue.get("source_ids")
        if (
            not isinstance(source_ids, list)
            or not source_ids
            or any(
                isinstance(source_id, bool)
                or not isinstance(source_id, int)
                or source_id < 1
                for source_id in source_ids
            )
            or source_ids != sorted(set(source_ids))
            or not _is_sha256(queue.get("source_text_sha256"))
        ):
            raise ValueError("Очередь содержит неверный реестр источников.")
        primary_sha256 = canonical_digest(primary)
        if queue.get("primary_coding_sha256") != primary_sha256:
            raise ValueError("Очередь не связана с первичной разметкой.")

        text = material.get("text")
        if (
            material.get("schema_version") != SCHEMA_VERSION
            or any(
                material.get(field) != expected
                for field, expected in (
                    ("candidate_id", candidate_id),
                    ("chain_id", chain_id),
                    ("document_id", document_id),
                    ("source_text_sha256", queue["source_text_sha256"]),
                )
            )
            or not _is_captured_full_text(text)
        ):
            raise ValueError("Материал имеет неверные идентификаторы или текст.")
        packet_text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        normalized_text = re.sub(
            r"\s+", " ", unicodedata.normalize("NFC", text)
        ).strip()
        source_text_sha256 = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        if (
            material.get("packet_text_sha256") != packet_text_sha256
            or material.get("source_text_sha256") != source_text_sha256
        ):
            raise ValueError("Хеш полного текста не совпадает.")

        primary_errors = validate_coding_against_text(primary, text)
        if primary_errors:
            raise ValueError(
                "Первичная разметка не прошла повторную проверку текста: "
                + "; ".join(primary_errors)
            )
        if primary.get("norm_edition_id") not in allowed_norm_edition_set:
            raise ValueError(
                "Первичная разметка ссылается на редакцию, "
                "не указанную в `CODING-BRIEF.json`."
            )

        if any(
            secondary.get(field) != expected
            for field, expected in (
                ("candidate_id", candidate_id),
                ("chain_id", chain_id),
                ("document_id", document_id),
                ("codebook_version", codebook_version),
            )
        ):
            raise ValueError(
                "Вторичная разметка имеет неверные идентификаторы или версию справочника."
            )
        if secondary.get("norm_edition_id") not in allowed_norm_edition_set:
            raise ValueError(
                "Вторичная разметка ссылается на редакцию, "
                "не указанную в `CODING-BRIEF.json`."
            )
        secondary_coder = _canonical_reviewer(secondary.get("coder"))
        primary_coder = _canonical_reviewer(primary.get("coder"))
        if secondary_coder != expected_coder:
            raise ValueError(
                "Поле coder вторичной разметки не совпадает с ожидаемой меткой "
                "второго кодирования."
            )
        if primary_coder is None or secondary_coder == primary_coder:
            raise ValueError(
                "Метка coder вторичной разметки совпадает с меткой "
                "первичного кодирования или первичная метка неканонична."
            )

        secondary_errors = validate_coding_against_text(secondary, text)
        if secondary_errors:
            raise ValueError(
                "Вторичная разметка не прошла проверку: "
                + "; ".join(secondary_errors)
            )
        quote = secondary.get("quote")
        if not isinstance(quote, str) or quote not in text:
            raise ValueError(
                "Основная цитата вторичной разметки не является буквальной подстрокой."
            )
        for ground_number, ground in enumerate(
            secondary.get("alternative_grounds", []), start=1
        ):
            ground_quote = ground.get("quote")
            if ground_quote is not None and ground_quote not in text:
                raise ValueError(
                    "Цитата альтернативного основания "
                    f"{ground_number} вторичной разметки "
                    "не является буквальной подстрокой."
                )

        secondary_sha256 = canonical_digest(secondary)
        decision = {
            "candidate_id": candidate_id,
            "primary_coding_sha256": primary_sha256,
            "secondary_coding": secondary,
            "secondary_coding_sha256": secondary_sha256,
        }
        if set(decision) != CODING_AUDIT_DECISION_FIELDS:
            raise AssertionError("неожиданный формат решения аудита разметки")
        audit_decisions.append(decision)

        differing_audited_fields = [
            field
            for field in AUDITED_CODING_FIELDS
            if primary.get(field) != secondary.get(field)
        ]
        differing_non_audited_fields = [
            field
            for field in NON_AUDITED_CODING_CONTENT_FIELDS
            if primary.get(field) != secondary.get(field)
        ]
        has_audited_difference = bool(differing_audited_fields)
        has_non_audited_difference = bool(differing_non_audited_fields)
        if has_audited_difference:
            audited_disagreement.append(candidate_id)
            audited_field_differences.append(
                {
                    "candidate_id": candidate_id,
                    "fields": differing_audited_fields,
                }
            )
        else:
            audited_agreement.append(candidate_id)
        if has_non_audited_difference:
            non_audited_difference.append(candidate_id)
            non_audited_content_differences.append(
                {
                    "candidate_id": candidate_id,
                    "fields": differing_non_audited_fields,
                }
            )
        if has_audited_difference:
            adjudication_required_candidate_ids.append(candidate_id)

    secondary_records_in_digest_order = sorted(
        secondary_records, key=canonical_digest
    )
    return {
        "audit_decisions": audit_decisions,
        "audit_decisions_sha256": canonical_digest(audit_decisions),
        "secondary_coding_sha256": canonical_digest(
            secondary_records_in_digest_order
        ),
        "candidate_ids": required_candidate_ids,
        "audited_fields": list(AUDITED_CODING_FIELDS),
        "non_audited_content_fields": list(NON_AUDITED_CODING_CONTENT_FIELDS),
        "audited_field_agreement_candidate_ids": audited_agreement,
        "audited_field_disagreement_candidate_ids": audited_disagreement,
        "audited_field_differences": audited_field_differences,
        "non_audited_content_difference_candidate_ids": non_audited_difference,
        "non_audited_content_differences": non_audited_content_differences,
        "non_audited_content_review_required": bool(non_audited_difference),
        "adjudication_required_candidate_ids": adjudication_required_candidate_ids,
        "adjudication_required": bool(adjudication_required_candidate_ids),
        "expected_secondary_coder_label": expected_coder,
    }


def build_native_coding_audit_finalization(
    audit_plan: Mapping[str, Any],
    primary_decisions: Iterable[Any],
    secondary_review_materials: Iterable[Any],
    audit_decisions: Iterable[Any],
    import_receipt: Mapping[str, Any],
    resolutions: Iterable[Any] | None = None,
    *,
    expected_import_receipt_sha256: str,
    norm_edition_ids: Iterable[str],
) -> dict[str, Any]:
    """Derive one final coding state from an exact native audit import.

    This is the side-effect-free half of native finalization.  The caller owns
    descriptor-held capture, byte-level receipt bindings, and atomic publication.
    Invalid contracts raise ``ValueError``.  A well-formed but unfinished review
    returns ``complete=False`` with candidate/field identifiers only.
    """

    if not isinstance(audit_plan, Mapping) or not _coding_audit_plan_contract_valid(
        audit_plan
    ):
        raise ValueError("Замороженный план аудита имеет неверный закрытый контракт.")
    if audit_plan.get("invalid_screening_record_ids") or audit_plan.get(
        "invalid_primary_record_ids"
    ):
        raise ValueError("План аудита содержит недопустимые входные записи.")
    required_candidate_ids = list(audit_plan["required_candidate_ids"])
    if not required_candidate_ids or any(
        not _is_native_audit_candidate_id(candidate_id)
        for candidate_id in required_candidate_ids
    ):
        raise ValueError(
            "План аудита не содержит канонический набор обязательных кандидатов."
        )

    if not _is_sha256(expected_import_receipt_sha256):
        raise ValueError(
            "Ожидаемая контрольная сумма квитанции импорта должна быть "
            "строчным SHA-256."
        )
    if not isinstance(import_receipt, Mapping) or set(import_receipt) != (
        CODING_AUDIT_REVIEW_IMPORT_RECEIPT_FIELDS
    ):
        raise ValueError("Квитанция импорта имеет неверный закрытый контракт.")
    receipt = dict(import_receipt)
    receipt_sha256 = receipt.get("receipt_sha256")
    unsigned_receipt = {
        key: value for key, value in receipt.items() if key != "receipt_sha256"
    }
    try:
        calculated_receipt_sha256 = canonical_digest(unsigned_receipt)
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ValueError("Квитанция импорта не является каноническим JSON.") from exc
    if (
        not _is_sha256(receipt_sha256)
        or receipt_sha256 != calculated_receipt_sha256
        or receipt_sha256 != expected_import_receipt_sha256
    ):
        raise ValueError(
            "Квитанция импорта не совпадает с отдельно сохранённой "
            "контрольной суммой."
        )

    if isinstance(norm_edition_ids, (str, bytes, Mapping)):
        raise ValueError("Список допустимых редакций норм имеет неверный формат.")
    try:
        allowed_norm_editions = list(norm_edition_ids)
    except TypeError as exc:
        raise ValueError("Список допустимых редакций норм имеет неверный формат.") from exc
    if (
        not allowed_norm_editions
        or not all(_is_canonical_identifier(value) for value in allowed_norm_editions)
        or len(allowed_norm_editions) != len(set(allowed_norm_editions))
    ):
        raise ValueError("Список допустимых редакций норм пуст или неканоничен.")
    allowed_norm_edition_set = set(allowed_norm_editions)

    def closed_index(
        values: Iterable[Any],
        *,
        record_kind: str,
        fields: frozenset[str],
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        if isinstance(values, (str, bytes, Mapping)):
            raise ValueError(f"Набор {record_kind} имеет неверный формат.")
        try:
            supplied_values = list(values)
        except TypeError as exc:
            raise ValueError(f"Набор {record_kind} имеет неверный формат.") from exc
        records: list[dict[str, Any]] = []
        indexed: dict[str, dict[str, Any]] = {}
        for row_number, value in enumerate(supplied_values, start=1):
            if not isinstance(value, Mapping) or set(value) != fields:
                raise ValueError(
                    f"Строка {record_kind} {row_number} имеет неверный закрытый формат."
                )
            record = dict(value)
            candidate_id = record.get("candidate_id")
            if not _is_native_audit_candidate_id(candidate_id):
                raise ValueError(
                    f"Строка {record_kind} {row_number} имеет "
                    "неканонический candidate_id."
                )
            if candidate_id in indexed:
                raise ValueError(f"Набор {record_kind} повторяет candidate_id.")
            try:
                canonical_digest(record)
            except (TypeError, ValueError, UnicodeEncodeError) as exc:
                raise ValueError(
                    f"Строка {record_kind} {row_number} не является "
                    "каноническим JSON."
                ) from exc
            records.append(record)
            indexed[candidate_id] = record
        return records, indexed

    primary_records, primary_by_candidate = closed_index(
        primary_decisions,
        record_kind="первичной разметки",
        fields=AUDIT_CODING_RECORD_FIELDS,
    )
    if not set(required_candidate_ids).issubset(primary_by_candidate):
        raise ValueError(
            "Первичная разметка не содержит всех кандидатов замороженной выборки."
        )
    for record in primary_records:
        try:
            errors = validate_coding_record(record)
        except (TypeError, ValueError) as exc:
            raise ValueError("Первичная разметка имеет неверные типы полей.") from exc
        if errors or not _audit_coding_identity_valid(record):
            raise ValueError(
                "Первичная разметка не завершена или неканонична: "
                + "; ".join(errors or ["неверные идентификаторы"])
            )
        if record.get("norm_edition_id") not in allowed_norm_edition_set:
            raise ValueError(
                "Первичная разметка ссылается на редакцию вне проверенного списка."
            )
    sorted_primary_records = sorted(primary_records, key=canonical_digest)
    if canonical_digest(sorted_primary_records) != audit_plan.get(
        "primary_coding_sha256"
    ):
        raise ValueError(
            "Первичная разметка не совпадает с замороженным планом аудита."
        )

    material_records, material_by_candidate = closed_index(
        secondary_review_materials,
        record_kind="материалов проверки",
        fields=NATIVE_AUDIT_REVIEW_MATERIAL_FIELDS,
    )
    audit_records, audit_by_candidate = closed_index(
        audit_decisions,
        record_kind="решений импорта",
        fields=CODING_AUDIT_DECISION_FIELDS,
    )
    expected_population = set(required_candidate_ids)
    if set(material_by_candidate) != expected_population:
        raise ValueError(
            "Материалы проверки не совпадают с замороженной выборкой."
        )
    if set(audit_by_candidate) != expected_population or [
        record["candidate_id"] for record in audit_records
    ] != required_candidate_ids:
        raise ValueError(
            "Решения импорта не совпадают с замороженной выборкой или её порядком."
        )

    codebook_version = receipt.get("codebook_version")
    if (
        not isinstance(codebook_version, str)
        or codebook_version not in NATIVE_AUDIT_CODEBOOK_VERSIONS
    ):
        raise ValueError(
            "Версия справочника кодирования в квитанции не поддерживается."
        )
    secondary_records: list[dict[str, Any]] = []
    audited_field_differences: list[dict[str, Any]] = []
    non_audited_content_differences: list[dict[str, Any]] = []
    audited_agreement_ids: list[str] = []
    audited_disagreement_ids: list[str] = []
    non_audited_difference_ids: list[str] = []
    secondary_coder_sha256: str | None = None

    for candidate_id in required_candidate_ids:
        primary = primary_by_candidate[candidate_id]
        material = material_by_candidate[candidate_id]
        audit = audit_by_candidate[candidate_id]
        if not _coding_audit_record_contract_valid(audit, candidate_id):
            raise ValueError("Решение импорта имеет неверный закрытый контракт.")
        secondary_value = audit.get("secondary_coding")
        if not isinstance(secondary_value, Mapping):
            raise ValueError("Решение импорта не содержит вторичную разметку.")
        secondary = dict(secondary_value)
        secondary_records.append(secondary)
        primary_sha256 = canonical_digest(primary)
        secondary_sha256 = canonical_digest(secondary)
        if (
            audit.get("primary_coding_sha256") != primary_sha256
            or audit.get("secondary_coding_sha256") != secondary_sha256
        ):
            raise ValueError("Решение импорта связано с другой разметкой.")
        if any(
            secondary.get(field) != primary.get(field)
            for field in ("candidate_id", "chain_id", "document_id", "codebook_version")
        ) or primary.get("codebook_version") != codebook_version:
            raise ValueError(
                "Первичная и вторичная разметки имеют разные обязательные привязки."
            )
        if candidate_id != _native_audit_candidate_id(
            plan_sha256=audit_plan["plan_sha256"],
            chain_id=primary["chain_id"],
            document_id=primary["document_id"],
        ):
            raise ValueError("candidate_id не связан с планом и документом.")
        if secondary.get("norm_edition_id") not in allowed_norm_edition_set:
            raise ValueError(
                "Вторичная разметка ссылается на редакцию вне проверенного списка."
            )
        try:
            secondary_errors = validate_coding_record(secondary)
        except (TypeError, ValueError) as exc:
            raise ValueError("Вторичная разметка имеет неверные типы полей.") from exc
        if secondary_errors or not _audit_coding_identity_valid(secondary):
            raise ValueError(
                "Вторичная разметка не завершена или неканонична: "
                + "; ".join(secondary_errors or ["неверные идентификаторы"])
            )
        primary_coder = _canonical_reviewer(primary.get("coder"))
        secondary_coder = _canonical_reviewer(secondary.get("coder"))
        if (
            primary_coder is None
            or secondary_coder is None
            or primary_coder == secondary_coder
        ):
            raise ValueError(
                "Метки первичного и вторичного кодировщиков не различаются."
            )
        current_secondary_coder_sha256 = hashlib.sha256(
            secondary_coder.encode("utf-8")
        ).hexdigest()
        if secondary_coder_sha256 is None:
            secondary_coder_sha256 = current_secondary_coder_sha256
        elif secondary_coder_sha256 != current_secondary_coder_sha256:
            raise ValueError("В импортированной выборке больше одного второго кодировщика.")

        text = material.get("text")
        if (
            material.get("schema_version") != SCHEMA_VERSION
            or material.get("candidate_id") != candidate_id
            or material.get("chain_id") != primary.get("chain_id")
            or material.get("document_id") != primary.get("document_id")
            or not _is_captured_full_text(text)
        ):
            raise ValueError("Материал проверки имеет неверные привязки или текст.")
        packet_text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        normalized_text = re.sub(
            r"\s+", " ", unicodedata.normalize("NFC", text)
        ).strip()
        source_text_sha256 = hashlib.sha256(
            normalized_text.encode("utf-8")
        ).hexdigest()
        if (
            material.get("packet_text_sha256") != packet_text_sha256
            or material.get("source_text_sha256") != source_text_sha256
        ):
            raise ValueError("Хеш текста материала проверки не совпадает.")
        for label, coding in (("Первичная", primary), ("Вторичная", secondary)):
            text_errors = validate_coding_against_text(coding, text)
            if text_errors:
                raise ValueError(
                    f"{label} разметка не прошла повторную проверку текста: "
                    + "; ".join(text_errors)
                )
            quote = coding.get("quote")
            if not isinstance(quote, str) or quote not in text:
                raise ValueError(
                    f"{label} основная цитата не является буквальной подстрокой."
                )
            for ground_number, ground in enumerate(
                coding.get("alternative_grounds", []), start=1
            ):
                ground_quote = ground.get("quote")
                if ground_quote is not None and ground_quote not in text:
                    raise ValueError(
                        f"{label} цитата альтернативного основания "
                        f"{ground_number} не является буквальной подстрокой."
                    )

        differing_audited_fields = [
            field
            for field in AUDITED_CODING_FIELDS
            if primary.get(field) != secondary.get(field)
        ]
        differing_non_audited_fields = [
            field
            for field in NON_AUDITED_CODING_CONTENT_FIELDS
            if primary.get(field) != secondary.get(field)
        ]
        if differing_audited_fields:
            audited_disagreement_ids.append(candidate_id)
            audited_field_differences.append(
                {"candidate_id": candidate_id, "fields": differing_audited_fields}
            )
        else:
            audited_agreement_ids.append(candidate_id)
        if differing_non_audited_fields:
            non_audited_difference_ids.append(candidate_id)
            non_audited_content_differences.append(
                {
                    "candidate_id": candidate_id,
                    "fields": differing_non_audited_fields,
                }
            )

    expected_true_receipt_fields = (
        "returned_quote_literal_presence_verified",
        "secondary_coder_label_differs_from_each_sampled_primary_label",
        "single_secondary_coder_label",
        "bundle_internal_consistency_verified",
        "expected_manifest_digest_match_verified",
        "norm_edition_allowlist_membership_verified",
    )
    expected_false_receipt_fields = (
        "secondary_coder_label_precommit_verified",
        "quote_locator_verified",
        "source_workspace_reverified",
        "reviewer_packet_use_attested",
        "norm_edition_temporal_applicability_verified",
        "reviewer_identity_authenticated",
        "human_review_authenticated",
        "independence_verified",
        "receipt_authenticated",
        "publication_safe",
        "legal_readiness",
    )
    receipt_hash_fields = (
        "source_bundle_manifest_sha256",
        "expected_source_bundle_manifest_sha256",
        "source_bundle_manifest_file_sha256",
        "review_packet_sha256",
        "secondary_coding_file_sha256",
        "secondary_coding_sha256",
        "codebook_sha256",
        "coding_brief_file_sha256",
        "audit_decisions_file_sha256",
        "expected_secondary_coder_label_sha256",
    )
    if (
        receipt.get("schema_version") != SCHEMA_VERSION
        or receipt.get("artifact_type") != "coding_audit_review_import_receipt"
        or receipt.get("producer")
        != "judicial_meaning.quality.coding_audit_review_import"
        or not isinstance(receipt.get("bundle_contract_version"), str)
        or receipt.get("bundle_contract_version") not in {"1.1", "1.2"}
        or receipt.get("plan_sha256") != audit_plan.get("plan_sha256")
        or receipt.get("audit_plan_sha256")
        != audit_plan.get("audit_plan_sha256")
        or receipt.get("candidate_ids") != required_candidate_ids
        or receipt.get("audited_fields") != list(AUDITED_CODING_FIELDS)
        or receipt.get("non_audited_content_fields")
        != list(NON_AUDITED_CODING_CONTENT_FIELDS)
        or receipt.get("audited_field_agreement_candidate_ids")
        != audited_agreement_ids
        or receipt.get("audited_field_disagreement_candidate_ids")
        != audited_disagreement_ids
        or receipt.get("non_audited_content_difference_candidate_ids")
        != non_audited_difference_ids
        or receipt.get("audited_field_differences") != audited_field_differences
        or receipt.get("non_audited_content_differences")
        != non_audited_content_differences
        or receipt.get("non_audited_content_review_required")
        is not bool(non_audited_difference_ids)
        or receipt.get("adjudication_required")
        is not bool(audited_disagreement_ids)
        or receipt.get("expected_secondary_coder_label_sha256")
        != secondary_coder_sha256
        or receipt.get("source_bundle_manifest_sha256")
        != receipt.get("expected_source_bundle_manifest_sha256")
        or any(receipt.get(field) is not True for field in expected_true_receipt_fields)
        or any(receipt.get(field) is not False for field in expected_false_receipt_fields)
        or any(not _is_sha256(receipt.get(field)) for field in receipt_hash_fields)
    ):
        raise ValueError(
            "Квитанция импорта не совпадает с планом, решениями или "
            "обязательными границами проверки."
        )
    secondary_records_in_digest_order = sorted(
        secondary_records, key=canonical_digest
    )
    if receipt.get("secondary_coding_sha256") != canonical_digest(
        secondary_records_in_digest_order
    ):
        raise ValueError(
            "Квитанция импорта не совпадает со вторичной разметкой."
        )

    audited_fields_by_candidate = {
        item["candidate_id"]: list(item["fields"])
        for item in audited_field_differences
    }
    non_audited_fields_by_candidate = {
        item["candidate_id"]: list(item["fields"])
        for item in non_audited_content_differences
    }
    difference_fields_by_candidate: dict[str, list[str]] = {}
    required_difference_pairs: list[dict[str, str]] = []
    for candidate_id in required_candidate_ids:
        fields = audited_fields_by_candidate.get(candidate_id, []) + (
            non_audited_fields_by_candidate.get(candidate_id, [])
        )
        if fields:
            difference_fields_by_candidate[candidate_id] = fields
            required_difference_pairs.extend(
                {"candidate_id": candidate_id, "field": field} for field in fields
            )

    def incomplete_result(
        *,
        missing_pairs: list[dict[str, str]],
        field_populations: list[dict[str, Any]],
        resolved_candidate_ids: list[str],
    ) -> dict[str, Any]:
        return {
            "complete": False,
            "incomplete_reason": "resolution_incomplete",
            "candidate_ids": required_candidate_ids,
            "required_difference_pairs": required_difference_pairs,
            "missing_difference_pairs": missing_pairs,
            "resolved_candidate_ids": resolved_candidate_ids,
            "resolved_field_populations": field_populations,
            "resolved_review_decisions": [],
            "resolved_review_decisions_sha256": None,
            "adjudications": [],
            "adjudications_sha256": None,
            "coding_reliability": None,
            "final_coding_sha256": None,
            "difference_resolution_bijection_verified": False,
            "final_quote_literal_presence_verified": False,
            "final_quote_normalized_presence_verified": False,
            "quote_locator_review_declared": False,
            "quote_locator_verified": False,
            "reliability_complete": False,
        }

    if not required_difference_pairs:
        if resolutions is not None:
            raise ValueError(
                "Файл решений нельзя передавать, когда обе карты различий пусты."
            )
        resolution_by_candidate: dict[str, dict[str, Any]] = {}
        resolved_field_populations: list[dict[str, Any]] = []
    else:
        if resolutions is None:
            return incomplete_result(
                missing_pairs=required_difference_pairs,
                field_populations=[],
                resolved_candidate_ids=[],
            )
        if isinstance(resolutions, (str, bytes, Mapping)):
            raise ValueError("Набор решений имеет неверный формат.")
        try:
            resolution_records = list(resolutions)
        except TypeError as exc:
            raise ValueError("Набор решений имеет неверный формат.") from exc
        resolution_by_candidate = {}
        covered_fields_by_candidate: dict[str, list[str]] = {}
        for row_number, value in enumerate(resolution_records, start=1):
            if not isinstance(value, Mapping) or set(value) != (
                CODING_REVIEW_RESOLUTION_FIELDS
            ):
                raise ValueError(
                    f"Строка решений {row_number} имеет неверный закрытый формат."
                )
            row = dict(value)
            try:
                canonical_digest(row)
            except (TypeError, ValueError, UnicodeEncodeError) as exc:
                raise ValueError(
                    f"Строка решений {row_number} не является каноническим JSON."
                ) from exc
            candidate_id = row.get("candidate_id")
            if not _is_native_audit_candidate_id(candidate_id):
                raise ValueError(
                    f"Строка решений {row_number} имеет неканонический candidate_id."
                )
            expected_fields = difference_fields_by_candidate.get(candidate_id)
            if expected_fields is None:
                raise ValueError(
                    f"Строка решений {row_number} относится к лишнему кандидату."
                )
            if candidate_id in resolution_by_candidate:
                raise ValueError("Набор решений повторяет candidate_id.")
            primary = primary_by_candidate[candidate_id]
            audit = audit_by_candidate[candidate_id]
            secondary = audit["secondary_coding"]
            reviewer = _canonical_reviewer(row.get("reviewer_pseudonym"))
            primary_coder = _canonical_reviewer(primary.get("coder"))
            secondary_coder = _canonical_reviewer(secondary.get("coder"))
            reviewed_at = row.get("reviewed_at")
            if (
                row.get("schema_version") != SCHEMA_VERSION
                or row.get("import_receipt_sha256") != receipt_sha256
                or row.get("difference_fields") != expected_fields
                or row.get("primary_coding_sha256")
                != audit.get("primary_coding_sha256")
                or row.get("secondary_coding_sha256")
                != audit.get("secondary_coding_sha256")
                or reviewer is None
                or not _is_canonical_identifier(row.get("reviewer_pseudonym"))
                or reviewer in {primary_coder, secondary_coder}
                or not _aware_iso_datetime(reviewed_at)
                or _parse_iso_datetime(str(reviewed_at)) > datetime.now(timezone.utc)
                or row.get("human_review") != "approved"
                or row.get("full_text_reviewed") is not True
                or row.get("quote_locators_reviewed") is not True
                or row.get("final_coding_approved") is not True
            ):
                raise ValueError(
                    f"Строка решений {row_number} имеет неверные привязки, "
                    "псевдоним, время или декларации."
                )
            field_resolutions = row.get("field_resolutions")
            if not isinstance(field_resolutions, list):
                raise ValueError(
                    f"Строка решений {row_number} имеет неверный список полей."
                )
            covered_fields: list[str] = []
            for field_number, field_resolution in enumerate(
                field_resolutions, start=1
            ):
                if not isinstance(field_resolution, Mapping):
                    raise ValueError(
                        f"Выбор поля {field_number} в строке {row_number} "
                        "должен быть объектом."
                    )
                variant = dict(field_resolution)
                choice = variant.get("choice")
                expected_variant_fields = (
                    CODING_REVIEW_CUSTOM_FIELD_RESOLUTION_FIELDS
                    if choice == "custom"
                    else CODING_REVIEW_FIELD_RESOLUTION_FIELDS
                )
                if (
                    not isinstance(choice, str)
                    or choice not in {"primary", "secondary", "custom"}
                    or set(variant) != expected_variant_fields
                ):
                    raise ValueError(
                        f"Выбор поля {field_number} в строке {row_number} "
                        "имеет неверный закрытый вариант."
                    )
                field = variant.get("field")
                if field not in expected_fields or field in covered_fields:
                    raise ValueError(
                        f"Выбор поля {field_number} в строке {row_number} "
                        "лишний или повторяется."
                    )
                if choice == "custom":
                    custom_probe = copy.deepcopy(primary)
                    custom_probe[field] = copy.deepcopy(variant["value"])
                    custom_probe["coder"] = row["reviewer_pseudonym"]
                    custom_probe["human_review"] = "approved"
                    custom_probe["full_text_reviewed"] = True
                    custom_probe["quote_verified"] = True
                    # Isolate the selected field from the only cross-field rule
                    # in the authoritative coding validator.  The complete
                    # composite is validated again after every choice is known.
                    if (
                        field == "label"
                        and isinstance(variant["value"], str)
                        and variant["value"] in SUBSTANTIVE_LABELS
                    ):
                        custom_probe["speaker"] = "court"
                    elif field == "speaker" and variant["value"] != "court":
                        custom_probe["label"] = "false_positive"
                    try:
                        custom_errors = validate_coding_record(custom_probe)
                    except (TypeError, ValueError) as exc:
                        raise ValueError(
                            f"Пользовательское значение поля {field} в строке "
                            f"{row_number} имеет неверный JSON-тип."
                        ) from exc
                    if (
                        custom_errors
                        or not _audit_coding_identity_valid(custom_probe)
                        or custom_probe.get("norm_edition_id")
                        not in allowed_norm_edition_set
                    ):
                        raise ValueError(
                            f"Пользовательское значение поля {field} в строке "
                            f"{row_number} не соответствует контракту разметки."
                        )
                    text = material_by_candidate[candidate_id]["text"]
                    if field == "quote" and (
                        not isinstance(variant["value"], str)
                        or variant["value"] not in text
                    ):
                        raise ValueError(
                            f"Пользовательская цитата в строке {row_number} "
                            "не является буквальной подстрокой."
                        )
                    if field == "alternative_grounds":
                        for ground in variant["value"]:
                            ground_quote = ground.get("quote")
                            if ground_quote is not None and ground_quote not in text:
                                raise ValueError(
                                    "Пользовательская цитата альтернативного "
                                    f"основания в строке {row_number} не является "
                                    "буквальной подстрокой."
                                )
                covered_fields.append(field)
            expected_covered_order = [
                field for field in expected_fields if field in covered_fields
            ]
            if covered_fields != expected_covered_order:
                raise ValueError(
                    f"Выборы полей в строке {row_number} нарушают порядок контракта."
                )
            resolution_by_candidate[candidate_id] = row
            covered_fields_by_candidate[candidate_id] = covered_fields

        resolved_field_populations = [
            {
                "candidate_id": candidate_id,
                "fields": covered_fields_by_candidate[candidate_id],
            }
            for candidate_id in required_candidate_ids
            if candidate_id in covered_fields_by_candidate
        ]
        missing_difference_pairs = [
            pair
            for pair in required_difference_pairs
            if pair["field"]
            not in covered_fields_by_candidate.get(pair["candidate_id"], [])
        ]
        resolved_candidate_ids = [
            candidate_id
            for candidate_id in required_candidate_ids
            if candidate_id in difference_fields_by_candidate
            and covered_fields_by_candidate.get(candidate_id)
            == difference_fields_by_candidate[candidate_id]
        ]
        if missing_difference_pairs:
            return incomplete_result(
                missing_pairs=missing_difference_pairs,
                field_populations=resolved_field_populations,
                resolved_candidate_ids=resolved_candidate_ids,
            )

    final_codings: list[dict[str, Any]] = []
    resolved_review_decisions: list[dict[str, Any]] = []
    adjudications: list[dict[str, Any]] = []
    for candidate_id in required_candidate_ids:
        primary = primary_by_candidate[candidate_id]
        audit = audit_by_candidate[candidate_id]
        secondary = audit["secondary_coding"]
        difference_fields = difference_fields_by_candidate.get(candidate_id, [])
        row = resolution_by_candidate.get(candidate_id)
        final_coding = copy.deepcopy(primary)
        field_choices: list[dict[str, str]] = []
        resolution_sha256: str | None = None
        if difference_fields:
            if row is None:
                raise AssertionError("полная карта решений потеряла обязательную строку")
            variants = {
                variant["field"]: variant for variant in row["field_resolutions"]
            }
            for field in difference_fields:
                variant = variants[field]
                choice = variant["choice"]
                if choice == "primary":
                    selected_value = primary[field]
                elif choice == "secondary":
                    selected_value = secondary[field]
                else:
                    selected_value = variant["value"]
                final_coding[field] = copy.deepcopy(selected_value)
                field_choices.append({"field": field, "choice": choice})
            final_coding["coder"] = row["reviewer_pseudonym"]
            final_coding["human_review"] = "approved"
            final_coding["full_text_reviewed"] = True
            final_coding["quote_verified"] = True
            resolution_sha256 = canonical_digest(row)

        if (
            set(final_coding) != AUDIT_CODING_RECORD_FIELDS
            or final_coding.get("candidate_id") != candidate_id
            or final_coding.get("chain_id") != primary.get("chain_id")
            or final_coding.get("document_id") != primary.get("document_id")
            or final_coding.get("codebook_version") != codebook_version
            or final_coding.get("norm_edition_id") not in allowed_norm_edition_set
        ):
            raise ValueError(
                f"Итоговая разметка кандидата {candidate_id} нарушает привязки."
            )
        try:
            final_errors = validate_coding_record(final_coding)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Итоговая разметка кандидата {candidate_id} имеет неверные типы полей."
            ) from exc
        if final_errors or not _audit_coding_identity_valid(final_coding):
            raise ValueError(
                f"Итоговая разметка кандидата {candidate_id} недопустима: "
                + "; ".join(final_errors or ["неверные идентификаторы"])
            )
        text = material_by_candidate[candidate_id]["text"]
        final_text_errors = validate_coding_against_text(final_coding, text)
        if final_text_errors:
            raise ValueError(
                f"Итоговая разметка кандидата {candidate_id} не прошла "
                "нормализованную проверку текста: "
                + "; ".join(final_text_errors)
            )
        quote = final_coding.get("quote")
        if not isinstance(quote, str) or quote not in text:
            raise ValueError(
                f"Итоговая основная цитата кандидата {candidate_id} "
                "не является буквальной подстрокой."
            )
        for ground_number, ground in enumerate(
            final_coding.get("alternative_grounds", []), start=1
        ):
            ground_quote = ground.get("quote")
            if ground_quote is not None and ground_quote not in text:
                raise ValueError(
                    "Итоговая цитата альтернативного основания "
                    f"{ground_number} кандидата {candidate_id} не является "
                    "буквальной подстрокой."
                )
        final_coding_sha256 = canonical_digest(final_coding)
        final_codings.append(final_coding)
        resolved_decision = {
            "schema_version": SCHEMA_VERSION,
            "import_receipt_sha256": receipt_sha256,
            "candidate_id": candidate_id,
            "difference_fields": difference_fields,
            "primary_coding_sha256": audit["primary_coding_sha256"],
            "secondary_coding_sha256": audit["secondary_coding_sha256"],
            "field_choices": field_choices,
            "resolution_sha256": resolution_sha256,
            "final_coding": final_coding,
            "final_coding_sha256": final_coding_sha256,
        }
        if set(resolved_decision) != RESOLVED_REVIEW_DECISION_FIELDS:
            raise AssertionError("неожиданный формат итогового решения проверки")
        resolved_review_decisions.append(resolved_decision)

        audited_difference_fields = audited_fields_by_candidate.get(candidate_id, [])
        if audited_difference_fields:
            if row is None:
                raise AssertionError("полная карта решений потеряла арбитражную строку")
            adjudication = {
                "candidate_id": candidate_id,
                "primary_coding_sha256": audit["primary_coding_sha256"],
                "secondary_coding_sha256": audit["secondary_coding_sha256"],
                "resolved_fields": {
                    field: copy.deepcopy(final_coding[field])
                    for field in audited_difference_fields
                },
                "adjudicator": row["reviewer_pseudonym"],
                "reviewed_at": row["reviewed_at"],
                "human_review": "approved",
            }
            if not _coding_adjudication_contract_valid(adjudication, candidate_id):
                raise ValueError(
                    f"Производный арбитраж кандидата {candidate_id} недопустим."
                )
            adjudications.append(adjudication)

    adjudications.sort(key=canonical_digest)
    coding_reliability = assess_coding_reliability(
        audit_plan,
        primary_records,
        audit_records,
        adjudications,
    )
    reliability_complete = coding_reliability.get("complete") is True
    resolved_candidate_ids = [
        candidate_id
        for candidate_id in required_candidate_ids
        if candidate_id in difference_fields_by_candidate
    ]
    resolved_field_populations = [
        {
            "candidate_id": candidate_id,
            "fields": difference_fields_by_candidate[candidate_id],
        }
        for candidate_id in resolved_candidate_ids
    ]
    return {
        "complete": reliability_complete,
        "incomplete_reason": None if reliability_complete else "reliability_unresolved",
        "candidate_ids": required_candidate_ids,
        "required_difference_pairs": required_difference_pairs,
        "missing_difference_pairs": [],
        "resolved_candidate_ids": resolved_candidate_ids,
        "resolved_field_populations": resolved_field_populations,
        "resolved_review_decisions": resolved_review_decisions,
        "resolved_review_decisions_sha256": canonical_digest(
            resolved_review_decisions
        ),
        "adjudications": adjudications,
        "adjudications_sha256": canonical_digest(adjudications),
        "coding_reliability": coding_reliability,
        "final_coding_sha256": canonical_digest(final_codings),
        "difference_resolution_bijection_verified": True,
        "final_quote_literal_presence_verified": True,
        "final_quote_normalized_presence_verified": True,
        "quote_locator_review_declared": bool(required_difference_pairs),
        "quote_locator_verified": False,
        "reliability_complete": reliability_complete,
    }


def assess_coding_reliability(
    audit_plan: Mapping[str, Any],
    primary_decisions: Iterable[Any],
    audit_decisions: Iterable[Any],
    adjudications: Iterable[Any] = (),
) -> dict[str, Any]:
    """Audit a frozen sample without reducing reliability to one coefficient."""

    primary_records = [
        dict(item) if isinstance(item, Mapping) else item
        for item in primary_decisions
    ]
    audit_records = [
        dict(item) if isinstance(item, Mapping) else item for item in audit_decisions
    ]
    adjudication_records = [
        dict(item) if isinstance(item, Mapping) else item for item in adjudications
    ]
    sorted_primary_records = sorted(primary_records, key=_diagnostic_digest)
    sorted_audit_records = sorted(audit_records, key=_diagnostic_digest)
    sorted_adjudication_records = sorted(
        adjudication_records, key=_diagnostic_digest
    )
    primary, duplicate_primary, current_invalid_primary_ids = _index_unique(
        sorted_primary_records,
        record_kind="primary",
    )
    current_invalid_primary_ids = sorted(
        set(current_invalid_primary_ids) | set(_invalid_coding_record_ids(primary))
    )
    audits, duplicate_audits, invalid_audit_record_ids = _index_unique(
        sorted_audit_records,
        record_kind="audit",
    )
    invalid_audit_record_ids = sorted(
        set(invalid_audit_record_ids)
        | {
            identifier
            for identifier, record in audits.items()
            if not _coding_audit_record_contract_valid(record, identifier)
        }
    )
    (
        adjudication_map,
        duplicate_adjudications,
        invalid_adjudication_record_ids,
    ) = _index_unique(
        sorted_adjudication_records,
        record_kind="adjudication",
    )
    invalid_adjudication_record_ids = sorted(
        set(invalid_adjudication_record_ids)
        | {
            identifier
            for identifier, record in adjudication_map.items()
            if not _coding_adjudication_contract_valid(record, identifier)
        }
    )
    required = sorted(
        {
            identifier
            for identifier in _unique_strings(
                audit_plan.get("required_candidate_ids", [])
            )
            if _is_canonical_identifier(identifier)
        }
    )
    invalid_audit_record_ids = sorted(
        set(invalid_audit_record_ids) | (set(audits) - set(required))
    )
    current_primary_sha256 = _diagnostic_digest(sorted_primary_records)
    audit_plan_input_sha256 = _diagnostic_digest(dict(audit_plan))
    audit_decisions_sha256 = _diagnostic_digest(sorted_audit_records)
    adjudications_sha256 = _diagnostic_digest(sorted_adjudication_records)
    plan_payload = {
        key: value for key, value in audit_plan.items() if key != "audit_plan_sha256"
    }
    plan_contract_valid = _coding_audit_plan_contract_valid(audit_plan)
    plan_digest_valid = (
        _is_sha256(audit_plan.get("audit_plan_sha256"))
        and audit_plan.get("audit_plan_sha256") == _diagnostic_digest(plan_payload)
    )
    plan_frozen = audit_plan.get("frozen") is True

    def plan_invalid_ids(field: str) -> list[str]:
        value = audit_plan.get(field)
        if not _unique_canonical_identifier_list(value):
            return [f"audit-plan-{field}-invalid"]
        return sorted(value)

    invalid_screening_record_ids = plan_invalid_ids(
        "invalid_screening_record_ids"
    )
    invalid_primary_record_ids = sorted(
        set(plan_invalid_ids("invalid_primary_record_ids"))
        | set(current_invalid_primary_ids)
    )
    stale = (
        audit_plan.get("primary_coding_sha256") != current_primary_sha256
        or not plan_digest_valid
        or not plan_contract_valid
        or not plan_frozen
        or bool(duplicate_primary)
    )
    missing: list[str] = []
    same_reviewer: list[str] = []
    unresolved: set[str] = set()
    field_disagreements: list[dict[str, Any]] = []
    false_exclusions: list[dict[str, Any]] = []
    audited: list[str] = []
    invalid_binding_ids: list[str] = []
    invalid_provenance_ids: list[str] = []
    used_adjudication_ids: set[str] = set()

    if stale:
        unresolved.update(required)
    if not plan_contract_valid:
        unresolved.add("audit-plan-contract-invalid")
    unresolved.update(duplicate_audits)
    unresolved.update(duplicate_adjudications)
    unresolved.update(invalid_screening_record_ids)
    unresolved.update(invalid_primary_record_ids)
    unresolved.update(invalid_audit_record_ids)
    unresolved.update(invalid_adjudication_record_ids)

    for identifier in required:
        primary_record = primary.get(identifier)
        audit = audits.get(identifier)
        if primary_record is None or audit is None:
            missing.append(identifier)
            unresolved.add(identifier)
            continue
        audited.append(identifier)
        primary_sha256 = _diagnostic_digest(primary_record)
        if identifier in invalid_audit_record_ids:
            unresolved.add(identifier)
            continue
        secondary = audit.get("secondary_coding")
        if not isinstance(secondary, Mapping):
            invalid_binding_ids.append(identifier)
            unresolved.add(identifier)
            continue
        secondary_record = dict(secondary)
        if (
            _candidate_id(secondary_record) != identifier
            or secondary_record.get("candidate_id") != identifier
        ):
            invalid_binding_ids.append(identifier)
            unresolved.add(identifier)
            continue
        secondary_sha256 = _diagnostic_digest(secondary_record)
        if (
            audit.get("primary_coding_sha256") != primary_sha256
            or audit.get("secondary_coding_sha256") != secondary_sha256
        ):
            invalid_binding_ids.append(identifier)
            unresolved.add(identifier)
            continue
        if validate_coding_record(secondary_record):
            invalid_audit_record_ids.append(identifier)
            unresolved.add(identifier)
            continue
        if (
            not _audit_coding_identity_valid(primary_record)
            or not _audit_coding_identity_valid(secondary_record)
            or any(
                primary_record.get(field) != secondary_record.get(field)
                for field in ("chain_id", "document_id", "codebook_version")
            )
        ):
            invalid_binding_ids.append(identifier)
            unresolved.add(identifier)
            continue
        if not _coding_provenance_valid(primary_record) or not _coding_provenance_valid(
            secondary_record
        ):
            invalid_provenance_ids.append(identifier)
            unresolved.add(identifier)
        primary_coder = _canonical_reviewer(primary_record.get("coder"))
        secondary_coder = _canonical_reviewer(secondary_record.get("coder"))
        if primary_coder is None or secondary_coder is None or (
            primary_coder == secondary_coder
        ):
            same_reviewer.append(identifier)
            unresolved.add(identifier)
        differing_fields = [
            field
            for field in AUDITED_CODING_FIELDS
            if primary_record.get(field) != secondary_record.get(field)
        ]
        if differing_fields:
            disagreement = {
                "candidate_id": identifier,
                "fields": differing_fields,
                "primary_coding_sha256": primary_sha256,
                "secondary_coding_sha256": secondary_sha256,
                "resolved": False,
                "adjudication_sha256": None,
            }
            adjudication = adjudication_map.get(identifier)
            if isinstance(adjudication, Mapping):
                used_adjudication_ids.add(identifier)
                resolved_fields = adjudication.get("resolved_fields")
                adjudicator = _canonical_reviewer(adjudication.get("adjudicator"))
                resolved_coding = dict(primary_record)
                if isinstance(resolved_fields, Mapping):
                    resolved_coding.update(resolved_fields)
                adjudication_valid = (
                    identifier not in invalid_adjudication_record_ids
                    and adjudication.get("primary_coding_sha256") == primary_sha256
                    and adjudication.get("secondary_coding_sha256") == secondary_sha256
                    and isinstance(resolved_fields, Mapping)
                    and set(resolved_fields) == set(differing_fields)
                    and adjudicator is not None
                    and adjudicator not in {primary_coder, secondary_coder}
                    and not validate_coding_record(resolved_coding)
                    and _audit_coding_identity_valid(resolved_coding)
                )
                if adjudication_valid:
                    disagreement["resolved"] = True
                    disagreement["adjudication_sha256"] = _diagnostic_digest(
                        adjudication
                    )
                else:
                    invalid_adjudication_record_ids.append(identifier)
            if not disagreement["resolved"]:
                unresolved.add(identifier)
            field_disagreements.append(disagreement)

        false_exclusion = (
            primary_record.get("label") in EXCLUSION_LABELS
            and secondary_record.get("label") in SUBSTANTIVE_LABELS
        )
        if false_exclusion:
            disagreement = next(
                (
                    item
                    for item in field_disagreements
                    if item["candidate_id"] == identifier
                ),
                None,
            )
            false_exclusions.append(
                {
                    "candidate_id": identifier,
                    "primary_label": primary_record.get("label"),
                    "secondary_label": secondary_record.get("label"),
                    "resolved": bool(disagreement and disagreement["resolved"]),
                }
            )

    invalid_adjudication_record_ids = sorted(
        set(invalid_adjudication_record_ids)
        | (set(adjudication_map) - used_adjudication_ids)
    )
    unresolved.update(duplicate_primary)
    unresolved.update(invalid_binding_ids)
    unresolved.update(invalid_provenance_ids)
    unresolved.update(invalid_audit_record_ids)
    unresolved.update(invalid_adjudication_record_ids)
    invalid_audit_record_ids = sorted(set(invalid_audit_record_ids))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "audit_plan_input_sha256": audit_plan_input_sha256,
        "audit_plan_sha256": (
            audit_plan.get("audit_plan_sha256")
            if _is_sha256(audit_plan.get("audit_plan_sha256"))
            else None
        ),
        "audit_plan_frozen": plan_frozen,
        "audit_plan_contract_valid": plan_contract_valid,
        "audit_plan_digest_valid": plan_digest_valid,
        "primary_coding_sha256": (
            audit_plan.get("primary_coding_sha256")
            if _is_sha256(audit_plan.get("primary_coding_sha256"))
            else None
        ),
        "current_primary_coding_sha256": current_primary_sha256,
        "audit_decisions_sha256": audit_decisions_sha256,
        "adjudications_sha256": adjudications_sha256,
        "required_candidate_ids": required,
        "audited_candidate_ids": sorted(set(audited)),
        "missing_candidate_ids": sorted(set(missing)),
        "same_reviewer_candidate_ids": sorted(set(same_reviewer)),
        "invalid_binding_candidate_ids": sorted(set(invalid_binding_ids)),
        "invalid_provenance_candidate_ids": sorted(set(invalid_provenance_ids)),
        "invalid_screening_record_ids": invalid_screening_record_ids,
        "invalid_primary_record_ids": invalid_primary_record_ids,
        "invalid_audit_record_ids": invalid_audit_record_ids,
        "invalid_adjudication_record_ids": invalid_adjudication_record_ids,
        "field_disagreements": field_disagreements,
        "false_exclusion_diagnostics": false_exclusions,
        "unresolved_candidate_ids": sorted(unresolved),
        "stale": stale,
        "complete": bool(required)
        and not stale
        and plan_contract_valid
        and not missing
        and not same_reviewer
        and not invalid_binding_ids
        and not invalid_provenance_ids
        and not invalid_screening_record_ids
        and not invalid_primary_record_ids
        and not invalid_audit_record_ids
        and not invalid_adjudication_record_ids
        and not unresolved,
    }
    return {**payload, "evidence_sha256": _diagnostic_digest(payload)}


def assess_prefiling_refresh(
    *,
    baseline_corpus_digest: str,
    current_corpus_digest: str,
    subject_evidence_sha256: str,
    refresh_plan: Mapping[str, Any],
    treatments: Iterable[Any],
    checked_through: str,
    filing_cutoff: str,
    reviewer: str,
    reviewed_at: str,
    claim_ids: Iterable[str] = (),
    live_corpus_binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assess a bounded pre-filing refresh, including unresolved treatments."""

    for field, value in (
        ("baseline_corpus_digest", baseline_corpus_digest),
        ("current_corpus_digest", current_corpus_digest),
    ):
        if not _is_sha256(value):
            raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    if not _is_sha256(subject_evidence_sha256):
        raise ValueError(
            "Параметр --subject-evidence-sha256 должен содержать 64 "
            "строчные шестнадцатеричные цифры."
        )
    if not _is_canonical_identifier(reviewer):
        raise ValueError(
            "reviewer должен быть видимым каноническим идентификатором проверяющего"
        )
    if not all(
        _valid_iso_datetime(value)
        for value in (checked_through, filing_cutoff, reviewed_at)
    ):
        raise ValueError(
            "Параметры --checked-through, --filing-cutoff и --reviewed-at "
            "должны содержать дату и время в формате ISO 8601."
        )

    refresh_plan_contract_valid = _refresh_plan_contract_valid(
        refresh_plan,
        current_corpus_digest=current_corpus_digest,
        checked_through=checked_through,
    )

    raw_entries = refresh_plan.get("entries", [])
    entries: list[Mapping[str, Any]] = []
    malformed_refresh_entry_ids: list[str] = []
    if isinstance(raw_entries, list):
        for index, item in enumerate(raw_entries, start=1):
            if isinstance(item, Mapping) and any(
                _nonempty(item.get(field)) for field in ("seed_id", "url", "reason")
            ):
                entries.append(item)
            else:
                malformed_refresh_entry_ids.append(
                    f"refresh-entry-{index}-{canonical_digest(item)[:12]}"
                )
    else:
        malformed_refresh_entry_ids.append(
            f"refresh-entries-container-{canonical_digest(raw_entries)[:12]}"
        )

    raw_requirements = refresh_plan.get("coverage_requirements")
    coverage_requirements: list[dict[str, Any]] = []
    malformed_coverage_requirement_ids: list[str] = []
    if isinstance(raw_requirements, list):
        for index, item in enumerate(raw_requirements, start=1):
            if _refresh_requirement_contract_valid(item):
                coverage_requirements.append(dict(item))
            else:
                malformed_coverage_requirement_ids.append(
                    f"coverage-requirement-{index}-{canonical_digest(item)[:12]}"
                )
    else:
        malformed_coverage_requirement_ids.append(
            "coverage-requirements-container-"
            + canonical_digest(raw_requirements)[:12]
        )

    raw_gaps = refresh_plan.get("coverage_gaps", [])
    gaps: list[dict[str, Any]] = []
    malformed_coverage_gap_ids: list[str] = []
    if isinstance(raw_gaps, list):
        for index, item in enumerate(raw_gaps, start=1):
            if _refresh_gap_contract_valid(item):
                gaps.append(dict(item))
            else:
                malformed_coverage_gap_ids.append(
                    f"coverage-gap-{index}-{canonical_digest(item)[:12]}"
                )
    else:
        malformed_coverage_gap_ids.append(
            f"coverage-gaps-container-{canonical_digest(raw_gaps)[:12]}"
        )
    (
        raw_treatment_items,
        treatment_set_contract_valid,
        treatment_set_sha256,
        treatment_set_corpus_evidence_digest,
        treatment_set_population_sha256,
    ) = _treatment_set_contract(
        treatments,
        current_corpus_digest=current_corpus_digest,
        expected_treatment_ids=refresh_plan.get("treatment_ids"),
        expected_treatment_population_sha256=refresh_plan.get(
            "treatment_population_sha256"
        ),
    )
    treatment_list = [
        dict(item) if isinstance(item, Mapping) else item
        for item in raw_treatment_items
    ]
    treatment_set_integrity_issue_ids = (
        list(treatments.get("integrity_issue_ids", []))
        if isinstance(treatments, Mapping)
        and isinstance(treatments.get("integrity_issue_ids"), list)
        else []
    )
    treatment_digest_records = sorted(treatment_list, key=canonical_digest)
    (
        pending_treatment_ids,
        verified_treatment_ids,
        rejected_treatment_ids,
        superseded_treatment_ids,
        invalid_resolved_treatment_ids,
        treatment_chronology_issue_ids,
    ) = _classify_treatments(
        treatment_list,
        final_reviewed_at=reviewed_at,
    )
    stale_seed_ids = sorted(
        {
            str(item.get("seed_id") or item.get("url") or item.get("reason"))
            for item in entries
            if item.get("seed_id") or item.get("url") or item.get("reason")
        }
    )
    raw_claim_ids = list(claim_ids)
    if (
        any(
            not _is_canonical_identifier(claim_id)
            for claim_id in raw_claim_ids
        )
        or len(set(raw_claim_ids)) != len(raw_claim_ids)
    ):
        raise ValueError(
            "Каждый параметр --claim-id должен содержать уникальный непустой "
            "канонический идентификатор."
        )
    claims = sorted(raw_claim_ids)
    plan_payload = dict(refresh_plan)
    raw_plan_as_of = refresh_plan.get("as_of")
    raw_plan_max_age = refresh_plan.get("max_age_seconds")
    raw_plan_evidence = refresh_plan.get("evidence_digest")
    raw_plan_treatment_ids = refresh_plan.get("treatment_ids")
    raw_plan_treatment_population_sha256 = refresh_plan.get(
        "treatment_population_sha256"
    )

    binding = (
        dict(live_corpus_binding)
        if isinstance(live_corpus_binding, Mapping)
        else {}
    )
    live_treatment_ids = binding.get("live_treatment_ids")
    live_binding_issue_ids = binding.get("issue_ids")
    live_corpus_binding_contract_valid = (
        set(binding) == LIVE_CORPUS_BINDING_FIELDS
        and binding.get("binding_version") == "1.0"
        and isinstance(binding.get("verified"), bool)
        and isinstance(binding.get("live_cache_stable"), bool)
        and isinstance(binding.get("live_corpus_evidence_digest"), str)
        and re.fullmatch(
            r"corpus-evidence-sha256:[0-9a-f]{64}",
            binding["live_corpus_evidence_digest"],
        )
        is not None
        and (
            binding.get("live_refresh_plan_sha256") is None
            or _is_sha256(binding.get("live_refresh_plan_sha256"))
        )
        and (
            binding.get("live_treatment_set_sha256") is None
            or _is_sha256(binding.get("live_treatment_set_sha256"))
        )
        and _is_sha256(binding.get("live_treatment_population_sha256"))
        and _unique_nonempty_string_list(live_treatment_ids)
        and live_treatment_ids == sorted(live_treatment_ids)
        and _unique_nonempty_string_list(live_binding_issue_ids)
    )
    live_corpus_binding_verified = bool(
        live_corpus_binding_contract_valid
        and binding.get("verified") is True
        and binding.get("live_cache_stable") is True
        and binding.get("issue_ids") == []
        and binding.get("live_corpus_evidence_digest")
        == f"corpus-evidence-sha256:{current_corpus_digest}"
        and binding.get("live_refresh_plan_sha256")
        == canonical_digest(dict(refresh_plan))
        and binding.get("live_treatment_set_sha256") == treatment_set_sha256
        and binding.get("live_treatment_population_sha256")
        == raw_plan_treatment_population_sha256
        and binding.get("live_treatment_population_sha256")
        == treatment_set_population_sha256
        and live_treatment_ids == raw_plan_treatment_ids
    )
    if live_corpus_binding_contract_valid:
        normalized_live_binding_issues = list(live_binding_issue_ids)
        if not live_corpus_binding_verified and not normalized_live_binding_issues:
            normalized_live_binding_issues = ["live_corpus_binding_claim_invalid"]
    elif live_corpus_binding is None:
        normalized_live_binding_issues = ["live_corpus_binding_missing"]
    else:
        normalized_live_binding_issues = ["live_corpus_binding_contract_invalid"]

    reasons: list[str] = []
    material_change = baseline_corpus_digest != current_corpus_digest
    checked_time = _parse_iso_datetime(checked_through)
    cutoff_time = _parse_iso_datetime(filing_cutoff)
    reviewed_time = _parse_iso_datetime(reviewed_at)
    evaluation_time = datetime.now(timezone.utc)
    timestamps_in_future = any(
        value.utcoffset() is not None and value > evaluation_time
        for value in (checked_time, reviewed_time)
    )
    timezone_mismatch = (checked_time.utcoffset() is None) != (
        cutoff_time.utcoffset() is None
    )
    timezone_missing = any(
        value.utcoffset() is None for value in (checked_time, cutoff_time, reviewed_time)
    )
    timing_valid = not timezone_mismatch and checked_time >= cutoff_time
    reviewed_timezone_mismatch = (reviewed_time.utcoffset() is None) != (
        checked_time.utcoffset() is None
    )
    reviewed_after_check = (
        not reviewed_timezone_mismatch and reviewed_time >= checked_time
    )

    if material_change:
        status = "material_change_requires_reanalysis"
        reasons.append("public_corpus_digest_changed")
    elif not refresh_plan_contract_valid:
        status = "refresh_incomplete"
        reasons.append("refresh_plan_contract_invalid")
        if timestamps_in_future:
            reasons.append("timestamp_in_future")
        if malformed_refresh_entry_ids:
            reasons.append("malformed_refresh_plan_entries")
        if malformed_coverage_gap_ids:
            reasons.append("malformed_coverage_gaps")
        if malformed_coverage_requirement_ids:
            reasons.append("malformed_coverage_requirements")
    elif (
        malformed_refresh_entry_ids
        or malformed_coverage_requirement_ids
        or malformed_coverage_gap_ids
    ):
        status = "refresh_incomplete"
        if malformed_refresh_entry_ids:
            reasons.append("malformed_refresh_plan_entries")
        if malformed_coverage_requirement_ids:
            reasons.append("malformed_coverage_requirements")
        if malformed_coverage_gap_ids:
            reasons.append("malformed_coverage_gaps")
    elif stale_seed_ids:
        status = "refresh_incomplete"
        reasons.append("stale_or_unfetched_public_seeds")
    elif not treatment_set_contract_valid:
        status = "refresh_incomplete"
        reasons.append("treatment_set_contract_invalid")
    elif treatment_set_integrity_issue_ids:
        status = "refresh_incomplete"
        reasons.append("live_cache_integrity_invalid")
    elif pending_treatment_ids:
        status = "refresh_incomplete"
        reasons.append("pending_treatment_review")
        if invalid_resolved_treatment_ids:
            reasons.append("resolved_treatment_lacks_content_bound_human_review")
        if treatment_chronology_issue_ids:
            reasons.append("treatment_review_chronology_invalid")
    elif timestamps_in_future:
        status = "refresh_incomplete"
        reasons.append("timestamp_in_future")
    elif timezone_mismatch:
        status = "refresh_incomplete"
        reasons.append("timestamp_timezone_mismatch")
    elif reviewed_timezone_mismatch:
        status = "refresh_incomplete"
        reasons.append("reviewed_at_timezone_mismatch")
    elif timezone_missing:
        status = "refresh_incomplete"
        reasons.append("timestamp_timezone_missing")
    elif not reviewed_after_check:
        status = "refresh_incomplete"
        reasons.append("reviewed_at_before_checked_through")
    elif not timing_valid:
        status = "refresh_incomplete"
        reasons.append("checked_through_before_filing_cutoff")
    elif not claims:
        status = "refresh_incomplete"
        reasons.append("claim_scope_missing")
    elif not live_corpus_binding_verified:
        status = "refresh_incomplete"
        if live_corpus_binding is None:
            reasons.append("live_corpus_binding_missing")
        elif not live_corpus_binding_contract_valid:
            reasons.append("live_corpus_binding_contract_invalid")
        else:
            reasons.append("live_corpus_binding_mismatch")
    elif gaps:
        status = "bounded_current_with_disclosed_gaps"
        reasons.append("unchanged_disclosed_coverage_gaps")
    else:
        status = "current_no_material_change"

    complete = status in {
        "current_no_material_change",
        "bounded_current_with_disclosed_gaps",
    }
    affected_claim_ids = [] if complete else claims
    payload = {
        "schema_version": SCHEMA_VERSION,
        "baseline_corpus_digest": baseline_corpus_digest,
        "current_corpus_digest": current_corpus_digest,
        "subject_evidence_sha256": subject_evidence_sha256,
        "refresh_plan_id": (
            refresh_plan.get("plan_id")
            if _nonempty(refresh_plan.get("plan_id"))
            else None
        ),
        "refresh_plan_sha256": canonical_digest(plan_payload),
        "refresh_plan_contract_valid": refresh_plan_contract_valid,
        "refresh_plan_as_of": (
            raw_plan_as_of if _aware_iso_datetime(raw_plan_as_of) else None
        ),
        "refresh_plan_max_age_seconds": (
            raw_plan_max_age
            if isinstance(raw_plan_max_age, int)
            and not isinstance(raw_plan_max_age, bool)
            and raw_plan_max_age >= 0
            else None
        ),
        "refresh_plan_evidence_digest": (
            raw_plan_evidence
            if isinstance(raw_plan_evidence, str)
            and re.fullmatch(
                r"corpus-evidence-sha256:[0-9a-f]{64}", raw_plan_evidence
            )
            else None
        ),
        "refresh_plan_treatment_ids": (
            list(raw_plan_treatment_ids)
            if isinstance(raw_plan_treatment_ids, list)
            and raw_plan_treatment_ids == sorted(set(raw_plan_treatment_ids))
            and all(
                _is_canonical_identifier(identifier)
                for identifier in raw_plan_treatment_ids
            )
            else []
        ),
        "refresh_plan_treatment_population_sha256": (
            raw_plan_treatment_population_sha256
            if _is_sha256(raw_plan_treatment_population_sha256)
            else None
        ),
        "refresh_plan_coverage_requirements": coverage_requirements,
        "refresh_plan_coverage_requirements_sha256": (
            canonical_digest(coverage_requirements)
            if coverage_requirements
            and not malformed_coverage_requirement_ids
            else None
        ),
        "checked_through": checked_through,
        "filing_cutoff": filing_cutoff,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "claim_ids": claims,
        "affected_claim_ids": affected_claim_ids,
        "live_binding_version": binding.get("binding_version"),
        "live_corpus_binding_contract_valid": live_corpus_binding_contract_valid,
        "live_corpus_binding_verified": live_corpus_binding_verified,
        "live_cache_stable": (
            binding.get("live_cache_stable")
            if isinstance(binding.get("live_cache_stable"), bool)
            else False
        ),
        "live_corpus_evidence_digest": (
            binding.get("live_corpus_evidence_digest")
            if isinstance(binding.get("live_corpus_evidence_digest"), str)
            else None
        ),
        "live_refresh_plan_sha256": (
            binding.get("live_refresh_plan_sha256")
            if _is_sha256(binding.get("live_refresh_plan_sha256"))
            else None
        ),
        "live_treatment_set_sha256": (
            binding.get("live_treatment_set_sha256")
            if _is_sha256(binding.get("live_treatment_set_sha256"))
            else None
        ),
        "live_treatment_population_sha256": (
            binding.get("live_treatment_population_sha256")
            if _is_sha256(binding.get("live_treatment_population_sha256"))
            else None
        ),
        "live_treatment_ids": (
            list(live_treatment_ids)
            if _unique_nonempty_string_list(live_treatment_ids)
            else []
        ),
        "live_binding_issue_ids": normalized_live_binding_issues,
        "treatment_set_contract_valid": treatment_set_contract_valid,
        "treatment_set_sha256": treatment_set_sha256,
        "treatment_set_corpus_evidence_digest": treatment_set_corpus_evidence_digest,
        "treatment_set_population_sha256": treatment_set_population_sha256,
        "treatments_sha256": canonical_digest(treatment_digest_records),
        "pending_treatment_ids": pending_treatment_ids,
        "verified_treatment_ids": verified_treatment_ids,
        "rejected_treatment_ids": rejected_treatment_ids,
        "superseded_treatment_ids": superseded_treatment_ids,
        "treatment_chronology_issue_ids": treatment_chronology_issue_ids,
        "stale_seed_ids": stale_seed_ids,
        "malformed_refresh_entry_ids": malformed_refresh_entry_ids,
        "malformed_coverage_requirement_ids": malformed_coverage_requirement_ids,
        "malformed_coverage_gap_ids": malformed_coverage_gap_ids,
        "coverage_gaps": gaps,
        "reasons": reasons,
        "status": status,
        "complete": complete,
    }
    if status not in PREFILING_STATUSES:
        raise AssertionError("unexpected prefiling status")
    return {**payload, "refresh_id": canonical_digest(payload)}


__all__ = [
    "AUDIT_CODING_RECORD_FIELDS",
    "AUDITED_CODING_FIELDS",
    "CODING_AUDIT_REVIEW_IMPORT_RECEIPT_FIELDS",
    "CODING_REVIEW_CUSTOM_FIELD_RESOLUTION_FIELDS",
    "CODING_REVIEW_FIELD_RESOLUTION_FIELDS",
    "CODING_REVIEW_RESOLUTION_FIELDS",
    "NON_AUDITED_CODING_CONTENT_FIELDS",
    "RESOLVED_REVIEW_DECISION_FIELDS",
    "CHAIN_STAGES",
    "CHAIN_TREATMENTS",
    "UNCERTAINTY_DIMENSIONS",
    "analyze_chain_stage_propagation",
    "assess_coding_reliability",
    "assess_prefiling_refresh",
    "build_coding_audit_plan",
    "build_native_coding_audit_finalization",
    "build_native_coding_audit_inputs",
    "build_native_coding_review_import",
    "build_native_finalization_comparison_report",
    "build_native_reliability_doctor_report",
    "build_uncertainty_profile",
    "canonical_digest",
    "verify_native_coding_reliability",
]
