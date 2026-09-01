"""Host-attested evidence binding for requested-remedy complaint sentences."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re
from hashlib import sha256
from typing import Any, Mapping, Protocol, Sequence

from .application_evidence import (
    PRESERVATION_RULE_STATUSES,
    ApplicationEvidenceRecord,
    application_review_approval_request,
    application_record_content_fingerprint,
    application_record_from_dict,
    assess_application_chain,
    preservation_rule_content_fingerprint,
    preservation_rule_review_approval_request,
)
from .issue_options import (
    IssueCandidate,
    issue_approval_requests,
    issue_candidate_content_fingerprint,
    issue_candidate_from_dict,
)
from .norm_versions import (
    norm_version_passport_content_fingerprint,
    norm_version_review_approval_request,
)
from .storage import canonical_json_bytes, stable_id


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SENTENCE_ID_RE = re.compile(r"^sent-[0-9a-f]{16}$")
_RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class ReliefEvidenceBindingAuthority(Protocol):
    """Host boundary that resolves current, gate-attested upstream artifacts."""

    def resolve_relief_evidence_binding(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any] | None: ...

    def resolve_relief_evidence_binding_index(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any] | None: ...


def _clean(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = " ".join(value.split())
    return value if value and value == normalized else ""


def _is_rfc3339_datetime(value: Any) -> bool:
    canonical = _clean(value)
    if not canonical or not _RFC3339_RE.fullmatch(canonical):
        return False
    candidate = canonical[:-1] + "+00:00" if canonical.endswith("Z") else canonical
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _raw_identifier_errors(
    raw: Mapping[str, Any],
    fields: Sequence[str],
    *,
    label: str,
) -> list[str]:
    return [
        f"{label}_raw_identifier_invalid:{field}"
        for field in fields
        if (
            not isinstance(raw.get(field), str)
            or not raw.get(field)
            or raw.get(field) != _clean(raw.get(field))
        )
    ]


def _raw_identifier_sequence_errors(
    value: Any,
    *,
    label: str,
    allow_empty: bool = True,
) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return [f"{label}_raw_identifier_list_invalid"]
    errors: list[str] = []
    if not value and not allow_empty:
        errors.append(f"{label}_raw_identifier_list_empty")
    seen: set[str] = set()
    for ordinal, raw in enumerate(value, start=1):
        if not isinstance(raw, str) or not raw or raw != _clean(raw):
            errors.append(f"{label}_raw_identifier_invalid:{ordinal}")
            continue
        if raw in seen:
            errors.append(f"{label}_raw_identifier_duplicate:{raw}")
        seen.add(raw)
    return errors


def _nested_identifier_errors(value: Any, *, label: str) -> list[str]:
    """Reject identifier coercion anywhere inside a host artifact graph."""

    errors: list[str] = []
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            if not isinstance(raw_key, str):
                errors.append(f"{label}_raw_mapping_key_invalid")
                continue
            path = f"{label}:{raw_key}"
            if raw_key.endswith("_id"):
                if (
                    not isinstance(nested, str)
                    or not nested
                    or nested != _clean(nested)
                ):
                    errors.append(f"{path}_raw_identifier_invalid")
            elif raw_key.endswith("_ids"):
                errors.extend(
                    _raw_identifier_sequence_errors(nested, label=path)
                )
            if isinstance(nested, Mapping) or (
                isinstance(nested, Sequence)
                and not isinstance(nested, (str, bytes))
            ):
                errors.extend(_nested_identifier_errors(nested, label=path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for ordinal, nested in enumerate(value, start=1):
            if isinstance(nested, Mapping) or (
                isinstance(nested, Sequence)
                and not isinstance(nested, (str, bytes))
            ):
                errors.extend(
                    _nested_identifier_errors(
                        nested,
                        label=f"{label}:{ordinal}",
                    )
                )
    return errors


def _binding_index_basis(
    *,
    matter_id: str,
    draft_id: str,
    bindings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": [dict(item) for item in bindings],
    }


def _binding_index_sha256(
    *,
    matter_id: str,
    draft_id: str,
    bindings: Sequence[Mapping[str, Any]],
) -> str:
    return sha256(
        canonical_json_bytes(
            _binding_index_basis(
                matter_id=matter_id,
                draft_id=draft_id,
                bindings=bindings,
            )
        )
    ).hexdigest()


def build_relief_binding_request(
    *,
    matter_id: str,
    draft_id: str,
    sentence_id: str,
    sentence_text: str,
    claim_id: str,
    issue_option_id: str,
    norm_passport_id: str,
    application_record_ids: Sequence[str],
    evidence_ids: Sequence[str],
) -> dict[str, Any]:
    """Return the deterministic lookup and approval basis for one remedy line."""

    basis = {
        "schema_version": "1.0.0",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "sentence_id": sentence_id,
        "sentence_text": sentence_text,
        "sentence_text_sha256": sha256(sentence_text.encode("utf-8")).hexdigest(),
        "claim_id": claim_id,
        "issue_option_id": issue_option_id,
        "norm_passport_id": norm_passport_id,
        "application_record_ids": sorted(application_record_ids),
        "evidence_ids": sorted(evidence_ids),
    }
    return {
        **basis,
        "relief_binding_sha256": sha256(canonical_json_bytes(basis)).hexdigest(),
    }


def build_relief_binding_index_request(
    *,
    matter_id: str,
    draft_id: str,
) -> dict[str, Any]:
    """Return the narrow host lookup for the authoritative remedy-line set."""

    return {
        "schema_version": "1.0.0",
        "matter_id": matter_id,
        "draft_id": draft_id,
    }


def _canonical_binding_request(
    request: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    scalar_fields = (
        "matter_id",
        "draft_id",
        "sentence_id",
        "sentence_text",
        "claim_id",
        "issue_option_id",
        "norm_passport_id",
    )
    errors = _raw_identifier_errors(
        request,
        scalar_fields,
        label="relief_binding_request",
    )
    errors.extend(
        _raw_identifier_sequence_errors(
            request.get("application_record_ids"),
            label="relief_binding_request:application_record_ids",
            allow_empty=False,
        )
    )
    errors.extend(
        _raw_identifier_sequence_errors(
            request.get("evidence_ids"),
            label="relief_binding_request:evidence_ids",
            allow_empty=False,
        )
    )
    if request.get("schema_version") != "1.0.0":
        errors.append("relief_binding_request_schema_invalid")
    if errors:
        return None, tuple(errors)
    rebuilt = build_relief_binding_request(
        matter_id=request["matter_id"],
        draft_id=request["draft_id"],
        sentence_id=request["sentence_id"],
        sentence_text=request["sentence_text"],
        claim_id=request["claim_id"],
        issue_option_id=request["issue_option_id"],
        norm_passport_id=request["norm_passport_id"],
        application_record_ids=request["application_record_ids"],
        evidence_ids=request["evidence_ids"],
    )
    if dict(request) != rebuilt:
        return None, ("relief_binding_request_sha_mismatch",)
    return rebuilt, ()


def _basic_gate_receipt_errors(
    receipt: Any,
    expected_fingerprint: str,
    *,
    label: str,
) -> list[str]:
    if not isinstance(receipt, Mapping):
        return [f"{label}_gate_receipt_missing"]
    errors: list[str] = []
    if receipt.get("passed") is not True:
        errors.append(f"{label}_gate_not_passed")
    if _clean(receipt.get("content_fingerprint")) != expected_fingerprint:
        errors.append(f"{label}_content_fingerprint_stale")
    return errors


def _exact_approval_request_errors(
    receipt: Mapping[str, Any],
    expected_request: Mapping[str, Any],
    *,
    label: str,
) -> list[str]:
    raw_request = receipt.get("approval_request")
    if not isinstance(raw_request, Mapping) or dict(raw_request) != dict(
        expected_request
    ):
        return [f"{label}_approval_request_mismatch"]
    return []


def _issue_gate_receipt_errors(
    receipt: Any,
    issue: IssueCandidate,
) -> list[str]:
    fingerprint = issue_candidate_content_fingerprint(issue)
    errors = _basic_gate_receipt_errors(
        receipt, fingerprint, label="issue"
    )
    if not isinstance(receipt, Mapping):
        return errors
    expected_requests = issue_approval_requests(issue)
    raw_requests = receipt.get("approval_requests")
    if not isinstance(raw_requests, Mapping) or dict(raw_requests) != expected_requests:
        errors.append("issue_approval_requests_mismatch")
    approval_ids = receipt.get("trusted_approval_ids")
    if not isinstance(approval_ids, Mapping):
        errors.append("issue_trusted_approval_ids_missing")
        return errors
    if not all(isinstance(key, str) and key == _clean(key) for key in approval_ids):
        errors.append("issue_trusted_approval_key_invalid")
    if set(approval_ids) != set(expected_requests):
        errors.append("issue_trusted_approval_set_mismatch")
    for key in sorted(expected_requests):
        if not _clean(approval_ids.get(key)):
            errors.append(f"issue_trusted_approval_missing:{key}")
    return errors


def _norm_gate_receipt_errors(
    receipt: Any,
    passport: Mapping[str, Any],
) -> list[str]:
    fingerprint = norm_version_passport_content_fingerprint(passport)
    errors = _basic_gate_receipt_errors(
        receipt, fingerprint, label="norm_version"
    )
    if not isinstance(receipt, Mapping):
        return errors
    errors.extend(
        _exact_approval_request_errors(
            receipt,
            norm_version_review_approval_request(passport),
            label="norm_version",
        )
    )
    if not _clean(receipt.get("trusted_approval_id")):
        errors.append("norm_version_trusted_approval_id_missing")
    return errors


def _preservation_rule_errors(
    raw_rule: Any,
    record: ApplicationEvidenceRecord,
) -> list[str]:
    if not isinstance(raw_rule, Mapping):
        return [f"preservation_rule_missing:{record.record_id}"]
    errors: list[str] = []
    expected_bindings = {
        "application_record_id": record.record_id,
        "claim_id": record.claim_id,
        "norm_id": record.norm_id,
        "norm_version_id": record.norm_version_id,
        "record_preservation_exhaustion": record.preservation_exhaustion,
    }
    if raw_rule.get("schema_version") != "1.0.0":
        errors.append(f"preservation_rule_schema_invalid:{record.record_id}")
    if any(raw_rule.get(key) != value for key, value in expected_bindings.items()):
        errors.append(f"preservation_rule_record_binding_mismatch:{record.record_id}")
    if _clean(raw_rule.get("rule_status")) not in PRESERVATION_RULE_STATUSES:
        errors.append(f"preservation_rule_status_invalid:{record.record_id}")
    raw_evidence_ids = raw_rule.get("evidence_ids")
    raw_evidence_errors = _raw_identifier_sequence_errors(
        raw_evidence_ids,
        label=f"preservation_rule:{record.record_id}:evidence_ids",
        allow_empty=False,
    )
    if raw_evidence_errors:
        errors.append(f"preservation_rule_evidence_missing:{record.record_id}")
        errors.extend(raw_evidence_errors)
    fingerprint = preservation_rule_content_fingerprint(raw_rule)
    if raw_rule.get("content_fingerprint") != fingerprint:
        errors.append(
            f"preservation_rule_content_fingerprint_mismatch:{record.record_id}"
        )
    expected_rule_id = stable_id(
        "preservation-rule",
        {
            "application_record_id": record.record_id,
            "content_fingerprint": fingerprint,
        },
    )
    if raw_rule.get("rule_id") != expected_rule_id:
        errors.append(f"preservation_rule_id_mismatch:{record.record_id}")
    return errors


def _application_gate_receipt_errors(
    receipt: Any,
    record: ApplicationEvidenceRecord,
    records: Sequence[ApplicationEvidenceRecord],
    passport: Mapping[str, Any],
    norm_receipt: Any,
) -> list[str]:
    label = f"application:{record.record_id}"
    fingerprint = application_record_content_fingerprint(record)
    errors = _basic_gate_receipt_errors(receipt, fingerprint, label=label)
    if not isinstance(receipt, Mapping):
        return errors
    application_approval_id = _clean(receipt.get("trusted_approval_id"))
    if not application_approval_id:
        errors.append(f"{label}_trusted_approval_id_missing")

    chain = assess_application_chain(records)
    if chain.status not in {"survived", "incorporated", "concurrent"}:
        errors.append(f"{label}_chain_not_release_supported")
    if record.record_id not in chain.supporting_record_ids:
        errors.append(f"{label}_record_not_supported_by_chain")

    raw_rule = receipt.get("preservation_rule_evidence")
    errors.extend(_preservation_rule_errors(raw_rule, record))
    rule = raw_rule if isinstance(raw_rule, Mapping) else None
    raw_rule_receipt = receipt.get("preservation_rule_gate_receipt")
    rule_approval_id = ""
    if rule is not None:
        rule_fingerprint = preservation_rule_content_fingerprint(rule)
        errors.extend(
            _basic_gate_receipt_errors(
                raw_rule_receipt,
                rule_fingerprint,
                label=f"preservation:{record.record_id}",
            )
        )
        if isinstance(raw_rule_receipt, Mapping):
            errors.extend(
                _exact_approval_request_errors(
                    raw_rule_receipt,
                    preservation_rule_review_approval_request(rule),
                    label=f"preservation:{record.record_id}",
                )
            )
            rule_approval_id = _clean(
                raw_rule_receipt.get("trusted_approval_id")
            )
            if not rule_approval_id:
                errors.append(
                    f"preservation:{record.record_id}_trusted_approval_id_missing"
                )

    norm_approval_id = (
        _clean(norm_receipt.get("trusted_approval_id"))
        if isinstance(norm_receipt, Mapping)
        else ""
    )
    expected_request = application_review_approval_request(
        record,
        chain,
        norm_version_status="verified",
        version_evidence_ids=(),
        preservation_rule_status=(
            _clean(rule.get("rule_status")) if rule is not None else ""
        ),
        norm_version_passport=passport,
        norm_version_approval_id=norm_approval_id,
        preservation_rule_evidence=rule,
        preservation_rule_approval_id=rule_approval_id,
    )
    errors.extend(
        _exact_approval_request_errors(
            receipt, expected_request, label=label
        )
    )
    return errors


def _issue_option(
    raw_issue: Any,
) -> tuple[IssueCandidate | None, list[str]]:
    if not isinstance(raw_issue, Mapping):
        return None, ["issue_option_resolution_missing"]
    errors = _raw_identifier_errors(
        raw_issue,
        ("issue_id", "seed_id", "claim_id"),
        label="issue_option",
    )
    if raw_issue.get("schema_version") != "1.0.0":
        errors.append("issue_option_schema_version_invalid")
    if (
        not isinstance(raw_issue.get("model_rank"), int)
        or isinstance(raw_issue.get("model_rank"), bool)
        or raw_issue.get("model_rank", 0) < 1
    ):
        errors.append("issue_option_model_rank_raw_integer_invalid")
    errors.extend(_nested_identifier_errors(raw_issue, label="issue_option"))
    errors.extend(
        _raw_identifier_sequence_errors(
            raw_issue.get("ksrf_authority_ids", ()),
            label="issue_option:ksrf_authority_ids",
        )
    )
    object_of_review = raw_issue.get("object_of_review")
    if not isinstance(object_of_review, Mapping):
        errors.append("issue_option_object_of_review_invalid")
    else:
        errors.extend(
            _raw_identifier_errors(
                object_of_review,
                ("norm_id", "norm_version_id"),
                label="issue_option:object_of_review",
            )
        )
    adverse_authority = raw_issue.get("adverse_authority")
    if not isinstance(adverse_authority, Mapping):
        errors.append("issue_option_adverse_authority_invalid")
    else:
        errors.extend(
            _raw_identifier_sequence_errors(
                adverse_authority.get("authority_ids", ()),
                label="issue_option:adverse_authority:authority_ids",
            )
        )
    gates = raw_issue.get("gates")
    if not isinstance(gates, Mapping):
        errors.append("issue_option_gates_invalid")
    else:
        for gate_name in ("anti_fourth_instance", "adverse_authority", "remedy"):
            raw_gate = gates.get(gate_name)
            if not isinstance(raw_gate, Mapping):
                errors.append(f"issue_option_gate_invalid:{gate_name}")
                continue
            errors.extend(
                _raw_identifier_sequence_errors(
                    raw_gate.get("evidence_ids", ()),
                    label=f"issue_option:gate:{gate_name}:evidence_ids",
                )
            )
            if not isinstance(raw_gate.get("requires_human_review"), bool):
                errors.append(
                    "issue_option_gate:"
                    f"{gate_name}:requires_human_review_raw_boolean_invalid"
                )
        raw_practice_claims = gates.get("practice_claims", ())
        if not isinstance(raw_practice_claims, Sequence) or isinstance(
            raw_practice_claims, (str, bytes)
        ):
            errors.append("issue_option_practice_claims_invalid")
        else:
            for ordinal, raw_claim in enumerate(raw_practice_claims, start=1):
                if not isinstance(raw_claim, Mapping):
                    errors.append(f"issue_option_practice_claim_invalid:{ordinal}")
                    continue
                errors.extend(
                    _raw_identifier_errors(
                        raw_claim,
                        ("claim_id",),
                        label=f"issue_option:practice_claim:{ordinal}",
                    )
                )
                for field in ("evidence_ids", "counterexample_ids"):
                    errors.extend(
                        _raw_identifier_sequence_errors(
                            raw_claim.get(field, ()),
                            label=(
                                f"issue_option:practice_claim:{ordinal}:{field}"
                            ),
                        )
                    )
    application_proof = raw_issue.get("application_proof")
    if not isinstance(application_proof, Mapping):
        errors.append("issue_option_application_proof_invalid")
    else:
        errors.extend(
            _raw_identifier_sequence_errors(
                application_proof.get("evidence_ids"),
                label="issue_option:application_proof:evidence_ids",
                allow_empty=False,
            )
        )
        if not isinstance(application_proof.get("gate_passed"), bool):
            errors.append(
                "issue_option_application_proof_gate_passed_raw_boolean_invalid"
            )
    raw_remedy = raw_issue.get("requested_remedy")
    if not isinstance(raw_remedy, str) or raw_remedy != _clean(raw_remedy):
        errors.append("issue_option_requested_remedy_raw_string_invalid")
    if errors:
        return None, errors
    try:
        return issue_candidate_from_dict(raw_issue), []
    except (KeyError, TypeError, ValueError) as exc:
        return None, [f"issue_option_resolution_invalid:{exc}"]


def _norm_passport(
    raw_passport: Any,
) -> tuple[Mapping[str, Any] | None, list[str]]:
    if not isinstance(raw_passport, Mapping):
        return None, ["norm_version_passport_resolution_missing"]
    errors = _raw_identifier_errors(
        raw_passport,
        ("passport_id", "passport_revision_id", "norm_id"),
        label="norm_version_passport",
    )
    if raw_passport.get("schema_version") != "1.0.0":
        errors.append("norm_version_passport_schema_version_invalid")
    errors.extend(
        _nested_identifier_errors(
            raw_passport,
            label="norm_version_passport",
        )
    )
    raw_segments = raw_passport.get("edition_segments")
    if not isinstance(raw_segments, Sequence) or isinstance(
        raw_segments, (str, bytes)
    ):
        errors.append("norm_version_passport_edition_segments_invalid")
    else:
        for ordinal, segment in enumerate(raw_segments, start=1):
            if not isinstance(segment, Mapping):
                errors.append(
                    f"norm_version_passport_edition_segment_invalid:{ordinal}"
                )
                continue
            errors.extend(
                _raw_identifier_errors(
                    segment,
                    ("edition_id",),
                    label=f"norm_version_passport:edition_segment:{ordinal}",
                )
            )
    return (None, errors) if errors else (raw_passport, [])


def _application_records(
    raw_records: Any,
) -> tuple[list[ApplicationEvidenceRecord], list[str]]:
    if not isinstance(raw_records, Sequence) or isinstance(raw_records, (str, bytes)):
        return [], ["application_records_resolution_invalid"]
    records: list[ApplicationEvidenceRecord] = []
    errors: list[str] = []
    for ordinal, raw in enumerate(raw_records, start=1):
        if not isinstance(raw, Mapping):
            errors.append(f"application_record_resolution_invalid:{ordinal}")
            continue
        raw_errors = _raw_identifier_errors(
            raw,
            (
                "record_id",
                "claim_id",
                "norm_id",
                "norm_version_id",
                "normative_meaning_id",
                "act_id",
                "stage",
            ),
            label=f"application_record:{ordinal}",
        )
        if raw.get("schema_version") != "1.0.0":
            raw_errors.append(
                f"application_record_schema_version_invalid:{ordinal}"
            )
        if (
            not isinstance(raw.get("stage_order"), int)
            or isinstance(raw.get("stage_order"), bool)
            or raw.get("stage_order", 0) < 1
        ):
            raw_errors.append(
                f"application_record_stage_order_raw_integer_invalid:{ordinal}"
            )
        raw_errors.extend(
            _nested_identifier_errors(
                raw,
                label=f"application_record:{ordinal}",
            )
        )
        raw_errors.extend(
            _raw_identifier_sequence_errors(
                raw.get("incorporated_record_ids", ()),
                label=f"application_record:{ordinal}:incorporated_record_ids",
            )
        )
        raw_evidence = raw.get("evidence")
        if not isinstance(raw_evidence, Sequence) or isinstance(
            raw_evidence, (str, bytes)
        ):
            raw_errors.append(f"application_record:{ordinal}_evidence_invalid")
        else:
            for evidence_ordinal, evidence in enumerate(raw_evidence, start=1):
                if not isinstance(evidence, Mapping):
                    raw_errors.append(
                        f"application_record:{ordinal}_evidence_invalid:"
                        f"{evidence_ordinal}"
                    )
                    continue
                raw_errors.extend(
                    _raw_identifier_errors(
                        evidence,
                        (
                            "evidence_id",
                            "claim_id",
                            "norm_id",
                            "act_id",
                            "stage",
                            "source_kind",
                            "speaker",
                            "reasoning_role",
                            "inference_status",
                        ),
                        label=(
                            f"application_record:{ordinal}:evidence:"
                            f"{evidence_ordinal}"
                        ),
                    )
                )
                locator = evidence.get("locator")
                if not isinstance(locator, Mapping):
                    raw_errors.append(
                        f"application_record:{ordinal}:evidence:"
                        f"{evidence_ordinal}_locator_invalid"
                    )
                else:
                    raw_errors.extend(
                        _raw_identifier_errors(
                            locator,
                            ("kind", "value"),
                            label=(
                                f"application_record:{ordinal}:evidence:"
                                f"{evidence_ordinal}:locator"
                            ),
                        )
                    )
        raw_premises = raw.get("implicit_premises", ())
        if not isinstance(raw_premises, Sequence) or isinstance(
            raw_premises, (str, bytes)
        ):
            raw_errors.append(
                f"application_record:{ordinal}_implicit_premises_invalid"
            )
        else:
            for premise_ordinal, premise in enumerate(raw_premises, start=1):
                if not isinstance(premise, Mapping):
                    raw_errors.append(
                        f"application_record:{ordinal}_implicit_premise_invalid:"
                        f"{premise_ordinal}"
                    )
                    continue
                raw_errors.extend(
                    _raw_identifier_sequence_errors(
                        premise.get("evidence_ids", ()),
                        label=(
                            f"application_record:{ordinal}:implicit_premise:"
                            f"{premise_ordinal}:evidence_ids"
                        ),
                    )
                )
        raw_non_application = raw.get("affirmative_non_application")
        if raw_non_application is not None:
            if not isinstance(raw_non_application, Mapping):
                raw_errors.append(
                    f"application_record:{ordinal}_affirmative_non_application_invalid"
                )
            else:
                raw_errors.extend(
                    _raw_identifier_sequence_errors(
                        raw_non_application.get("evidence_ids", ()),
                        label=(
                            f"application_record:{ordinal}:"
                            "affirmative_non_application:evidence_ids"
                        ),
                    )
                )
        if raw_errors:
            errors.extend(raw_errors)
            continue
        try:
            records.append(application_record_from_dict(raw))
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"application_record_resolution_invalid:{ordinal}:{exc}")
    return records, errors


def _claim_evidence(
    raw_entries: Any,
    *,
    expected_claim_id: str,
    expected_norm_id: str,
    expected_norm_version_id: str,
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    if raw_entries is None:
        return {}, []
    if not isinstance(raw_entries, Sequence) or isinstance(raw_entries, (str, bytes)):
        return {}, ["claim_evidence_resolution_invalid"]
    entries: dict[str, Mapping[str, Any]] = {}
    errors: list[str] = []
    for ordinal, raw in enumerate(raw_entries, start=1):
        if not isinstance(raw, Mapping):
            errors.append(f"claim_evidence_resolution_invalid:{ordinal}")
            continue
        raw_errors = _raw_identifier_errors(
            raw,
            ("evidence_id", "claim_id", "norm_id", "norm_version_id"),
            label=f"claim_evidence:{ordinal}",
        )
        if raw_errors:
            errors.extend(raw_errors)
            continue
        evidence_id = _clean(raw.get("evidence_id"))
        if not evidence_id:
            errors.append(f"claim_evidence_id_missing:{ordinal}")
            continue
        if evidence_id in entries:
            errors.append(f"claim_evidence_duplicate:{evidence_id}")
            continue
        entries[evidence_id] = raw
        if _clean(raw.get("claim_id")) != expected_claim_id:
            errors.append(f"claim_evidence_cross_claim:{evidence_id}")
        if _clean(raw.get("norm_id")) != expected_norm_id:
            errors.append(f"claim_evidence_norm_mismatch:{evidence_id}")
        if _clean(raw.get("norm_version_id")) != expected_norm_version_id:
            errors.append(f"claim_evidence_edition_mismatch:{evidence_id}")
        if raw.get("status") != "current":
            errors.append(f"claim_evidence_not_current:{evidence_id}")
        if not _SHA256_RE.fullmatch(_clean(raw.get("content_sha256"))):
            errors.append(f"claim_evidence_content_sha256_invalid:{evidence_id}")
        for key in ("verification_revision_id", "verifier_id"):
            if not _clean(raw.get(key)):
                errors.append(f"claim_evidence_{key}_missing:{evidence_id}")
        if not _is_rfc3339_datetime(raw.get("checked_at")):
            errors.append(f"claim_evidence_checked_at_invalid:{evidence_id}")
        locator = raw.get("locator")
        if not isinstance(locator, Mapping) or _raw_identifier_errors(
            locator,
            ("kind", "value"),
            label=f"claim_evidence:{ordinal}:locator",
        ):
            errors.append(f"claim_evidence_locator_missing:{evidence_id}")
    return entries, errors


def _resolution_errors_and_receipt(
    request: Mapping[str, Any],
    resolution: Mapping[str, Any],
) -> tuple[list[str], dict[str, Any] | None]:
    errors: list[str] = []
    expected_binding_sha = _clean(request.get("relief_binding_sha256"))
    if resolution.get("status") != "verified":
        errors.append("relief_binding_resolution_not_verified")
    if _clean(resolution.get("relief_binding_sha256")) != expected_binding_sha:
        errors.append("relief_binding_sha256_mismatch")

    issue, issue_errors = _issue_option(resolution.get("issue_option"))
    errors.extend(issue_errors)

    passport, passport_errors = _norm_passport(
        resolution.get("norm_version_passport")
    )
    errors.extend(passport_errors)

    records, record_errors = _application_records(resolution.get("application_records"))
    errors.extend(record_errors)
    record_ids = [record.record_id for record in records]
    if len(record_ids) != len(set(record_ids)):
        errors.append("resolved_application_record_ids_duplicate")
    expected_record_ids = list(request.get("application_record_ids") or ())
    if sorted(record_ids) != expected_record_ids:
        errors.append("application_record_set_mismatch")

    claim_id = _clean(request.get("claim_id"))
    issue_id = _clean(request.get("issue_option_id"))
    passport_id = _clean(request.get("norm_passport_id"))
    sentence_text = _clean(request.get("sentence_text"))
    norm_id = issue.norm_id if issue is not None else ""
    norm_version_id = issue.norm_version_id if issue is not None else ""

    if issue is not None:
        if issue.issue_id != issue_id:
            errors.append("issue_option_id_mismatch")
        if issue.claim_id != claim_id:
            errors.append("issue_option_cross_claim")
        if issue.human_selection.state not in {"principal", "reserve"}:
            errors.append("issue_option_not_selected")
        if not issue.application_gate_passed:
            errors.append("issue_application_gate_not_passed")
        if issue.requested_remedy != sentence_text:
            errors.append("requested_remedy_text_mismatch")

    if passport is not None:
        if passport.get("passport_id") != passport_id:
            errors.append("norm_passport_id_mismatch")
        if issue is not None and passport.get("norm_id") != issue.norm_id:
            errors.append("norm_passport_norm_mismatch")
        edition_ids = {
            item.get("edition_id")
            for item in passport.get("edition_segments") or ()
            if isinstance(item, Mapping)
        }
        if issue is not None and issue.norm_version_id not in edition_ids:
            errors.append("norm_passport_edition_mismatch")

    evidence_spans: dict[str, list[Any]] = {}
    for record in records:
        if record.claim_id != claim_id:
            errors.append(f"application_record_cross_claim:{record.record_id}")
        if issue is not None and record.norm_id != issue.norm_id:
            errors.append(f"application_record_norm_mismatch:{record.record_id}")
        if issue is not None and record.norm_version_id != issue.norm_version_id:
            errors.append(f"application_record_edition_mismatch:{record.record_id}")
        for span in record.evidence:
            evidence_spans.setdefault(span.evidence_id, []).append(span)
            if span.claim_id != claim_id:
                errors.append(f"application_evidence_cross_claim:{span.evidence_id}")
            if issue is not None and span.norm_id != issue.norm_id:
                errors.append(f"application_evidence_norm_mismatch:{span.evidence_id}")
            if not span.has_full_act_locator:
                errors.append(f"application_evidence_locator_missing:{span.evidence_id}")

    if issue is not None:
        if not issue.application_evidence_ids:
            errors.append("issue_application_evidence_ids_missing")
        for evidence_id in issue.application_evidence_ids:
            if len(evidence_spans.get(evidence_id, ())) != 1:
                errors.append(f"issue_application_evidence_not_exact:{evidence_id}")

    claim_entries, claim_errors = _claim_evidence(
        resolution.get("claim_evidence"),
        expected_claim_id=claim_id,
        expected_norm_id=norm_id,
        expected_norm_version_id=norm_version_id,
    )
    errors.extend(claim_errors)
    for evidence_id in request.get("evidence_ids") or ():
        span_count = len(evidence_spans.get(evidence_id, ()))
        claim_count = 1 if evidence_id in claim_entries else 0
        if span_count + claim_count == 0:
            errors.append(f"sentence_evidence_unknown:{evidence_id}")
        elif span_count + claim_count > 1:
            errors.append(f"sentence_evidence_ambiguous:{evidence_id}")

    issue_fingerprint = (
        issue_candidate_content_fingerprint(issue) if issue is not None else ""
    )
    passport_fingerprint = (
        norm_version_passport_content_fingerprint(passport) if passport is not None else ""
    )
    if issue is not None:
        errors.extend(
            _issue_gate_receipt_errors(
                resolution.get("issue_gate_receipt"), issue
            )
        )
    if passport is not None:
        errors.extend(
            _norm_gate_receipt_errors(
                resolution.get("norm_version_gate_receipt"), passport
            )
        )

    raw_application_receipts = resolution.get("application_gate_receipts")
    receipt_by_record: dict[str, Mapping[str, Any]] = {}
    if not isinstance(raw_application_receipts, Sequence) or isinstance(
        raw_application_receipts, (str, bytes)
    ):
        errors.append("application_gate_receipts_invalid")
    else:
        for raw in raw_application_receipts:
            if not isinstance(raw, Mapping):
                errors.append("application_gate_receipt_invalid")
                continue
            record_id = _clean(raw.get("record_id"))
            if not record_id:
                errors.append("application_gate_receipt_record_id_missing")
            elif record_id in receipt_by_record:
                errors.append(f"application_gate_receipt_duplicate:{record_id}")
            else:
                receipt_by_record[record_id] = raw
    if sorted(receipt_by_record) != sorted(record_ids):
        errors.append("application_gate_receipt_set_mismatch")

    application_fingerprints: dict[str, str] = {}
    for record in records:
        fingerprint = application_record_content_fingerprint(record)
        application_fingerprints[record.record_id] = fingerprint
        if passport is not None:
            errors.extend(
                _application_gate_receipt_errors(
                    receipt_by_record.get(record.record_id),
                    record,
                    records,
                    passport,
                    resolution.get("norm_version_gate_receipt"),
                )
            )

    if errors:
        return list(dict.fromkeys(errors)), None

    issue_approvals = dict(
        resolution["issue_gate_receipt"].get("trusted_approval_ids") or {}
    )
    application_approvals = {
        record_id: _clean(receipt_by_record[record_id].get("trusted_approval_id"))
        for record_id in sorted(receipt_by_record)
    }
    issue_requests = issue_approval_requests(issue) if issue is not None else {}
    norm_request = (
        norm_version_review_approval_request(passport)
        if passport is not None
        else {}
    )
    application_request_fingerprints = {
        record_id: _clean(
            (receipt_by_record[record_id].get("approval_request") or {}).get(
                "fingerprint"
            )
        )
        for record_id in sorted(receipt_by_record)
    }
    preservation_request_fingerprints = {
        record_id: _clean(
            (
                receipt_by_record[record_id].get(
                    "preservation_rule_gate_receipt"
                )
                or {}
            ).get("approval_request", {}).get("fingerprint")
        )
        for record_id in sorted(receipt_by_record)
    }
    requested_evidence_ids = set(request.get("evidence_ids") or ())
    used_claim_entries = {
        evidence_id: entry
        for evidence_id, entry in claim_entries.items()
        if evidence_id in requested_evidence_ids
    }
    source_revisions = {
        evidence_id: _clean(entry.get("verification_revision_id"))
        for evidence_id, entry in sorted(used_claim_entries.items())
    }
    source_receipts: dict[str, dict[str, Any]] = {}
    for evidence_id, entry in sorted(used_claim_entries.items()):
        projection = {
            "evidence_id": evidence_id,
            "claim_id": entry["claim_id"],
            "norm_id": entry["norm_id"],
            "norm_version_id": entry["norm_version_id"],
            "status": entry["status"],
            "content_sha256": entry["content_sha256"],
            "verification_revision_id": entry["verification_revision_id"],
            "verifier_id": entry["verifier_id"],
            "checked_at": entry["checked_at"],
            "locator": {
                "kind": entry["locator"]["kind"],
                "value": entry["locator"]["value"],
            },
        }
        source_receipts[evidence_id] = {
            **projection,
            "content_fingerprint": sha256(
                canonical_json_bytes(projection)
            ).hexdigest(),
        }
    return [], {
        "schema_version": "1.1.0",
        "sentence_id": request["sentence_id"],
        "relief_binding_sha256": expected_binding_sha,
        "claim_id": claim_id,
        "issue_option_id": issue_id,
        "issue_content_fingerprint": issue_fingerprint,
        "norm_passport_id": passport_id,
        "norm_passport_content_fingerprint": passport_fingerprint,
        "application_record_content_fingerprints": dict(
            sorted(application_fingerprints.items())
        ),
        "evidence_ids": list(request.get("evidence_ids") or ()),
        "source_evidence_revision_ids": source_revisions,
        "source_evidence_receipts": source_receipts,
        "trusted_approval_ids": {
            "issue": issue_approvals,
            "norm_version": _clean(
                resolution["norm_version_gate_receipt"].get("trusted_approval_id")
            ),
            "application": application_approvals,
        },
        "approval_request_fingerprints": {
            "issue": {
                key: _clean(value.get("fingerprint"))
                for key, value in sorted(issue_requests.items())
            },
            "norm_version": _clean(norm_request.get("fingerprint")),
            "application": application_request_fingerprints,
            "preservation": preservation_request_fingerprints,
        },
    }


def resolve_relief_evidence_binding(
    request: Mapping[str, Any],
    authority: ReliefEvidenceBindingAuthority | Any | None,
) -> tuple[tuple[str, ...], dict[str, Any] | None]:
    """Resolve and locally revalidate one exact remedy binding."""

    canonical_request, request_errors = _canonical_binding_request(request)
    if canonical_request is None:
        return request_errors, None
    if authority is None or not callable(
        getattr(authority, "resolve_relief_evidence_binding", None)
    ):
        return ("relief_binding_authority_required",), None
    adapter_request = deepcopy(canonical_request)
    try:
        resolution = authority.resolve_relief_evidence_binding(adapter_request)
    except Exception as exc:  # host adapter failures are blockers, never passes
        return (f"relief_binding_authority_error:{exc}",), None
    if adapter_request != canonical_request:
        return ("relief_binding_request_mutated",), None
    if not isinstance(resolution, Mapping):
        return ("relief_binding_resolution_missing",), None
    errors, receipt = _resolution_errors_and_receipt(canonical_request, resolution)
    return tuple(errors), receipt


def _canonical_index_bindings(
    value: Any,
    *,
    label: str,
) -> tuple[list[dict[str, str]], list[str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return [], [f"{label}_invalid"]
    bindings: list[dict[str, str]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for ordinal, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping) or set(raw) != {
            "sentence_id",
            "section_code",
            "role",
            "relief_binding_sha256",
        }:
            errors.append(f"{label}_entry_invalid:{ordinal}")
            continue
        sentence_id = raw.get("sentence_id")
        binding_sha = raw.get("relief_binding_sha256")
        if not isinstance(sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(
            sentence_id
        ):
            errors.append(f"{label}_sentence_id_invalid:{ordinal}")
            continue
        if not isinstance(binding_sha, str) or not _SHA256_RE.fullmatch(binding_sha):
            errors.append(f"{label}_sha256_invalid:{sentence_id}")
            continue
        if raw.get("section_code") != "requested_remedy":
            errors.append(f"{label}_section_invalid:{sentence_id}")
            continue
        if raw.get("role") != "requested_remedy":
            errors.append(f"{label}_role_invalid:{sentence_id}")
            continue
        if sentence_id in seen:
            errors.append(f"{label}_duplicate:{sentence_id}")
            continue
        seen.add(sentence_id)
        bindings.append(
            {
                "sentence_id": sentence_id,
                "section_code": "requested_remedy",
                "role": "requested_remedy",
                "relief_binding_sha256": binding_sha,
            }
        )
    canonical = sorted(bindings, key=lambda item: item["sentence_id"])
    if bindings != canonical:
        errors.append(f"{label}_not_canonical")
    return canonical, errors


def build_relief_binding_index_resolution(
    *,
    matter_id: str,
    draft_id: str,
    bindings: Sequence[Mapping[str, Any]],
    authority_revision_id: str,
    checked_at: str,
) -> dict[str, Any]:
    """Build one canonical host response for an authoritative draft registry."""

    canonical, errors = _canonical_index_bindings(
        bindings,
        label="relief_binding_index_bindings",
    )
    if errors:
        raise ValueError(", ".join(errors))
    for label, value in (
        ("matter_id", matter_id),
        ("draft_id", draft_id),
        ("authority_revision_id", authority_revision_id),
    ):
        if value != _clean(value):
            raise ValueError(f"{label} must be a canonical nonempty string")
    if not _is_rfc3339_datetime(checked_at):
        raise ValueError("checked_at must be an RFC 3339 date-time")
    return {
        "schema_version": "1.0.0",
        "status": "verified",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": canonical,
        "binding_index_sha256": _binding_index_sha256(
            matter_id=matter_id,
            draft_id=draft_id,
            bindings=canonical,
        ),
        "authority_revision_id": authority_revision_id,
        "checked_at": checked_at,
    }


def resolve_relief_evidence_binding_index(
    *,
    matter_id: str,
    draft_id: str,
    binding_requests: Sequence[Mapping[str, Any]],
    authority: ReliefEvidenceBindingAuthority | Any | None,
) -> tuple[tuple[str, ...], dict[str, Any] | None]:
    """Resolve the host-authoritative complete remedy-line set for one draft."""

    lookup = build_relief_binding_index_request(
        matter_id=matter_id,
        draft_id=draft_id,
    )
    if not matter_id or matter_id != _clean(matter_id):
        return ("relief_binding_index_matter_id_invalid",), None
    if not draft_id or draft_id != _clean(draft_id):
        return ("relief_binding_index_draft_id_invalid",), None

    expected_bindings: list[dict[str, str]] = []
    request_errors: list[str] = []
    for request in binding_requests:
        canonical, binding_request_errors = _canonical_binding_request(request)
        request_errors.extend(binding_request_errors)
        if canonical is not None:
            expected_bindings.append(
                {
                    "sentence_id": canonical["sentence_id"],
                    "section_code": "requested_remedy",
                    "role": "requested_remedy",
                    "relief_binding_sha256": canonical["relief_binding_sha256"],
                }
            )
    expected_bindings.sort(key=lambda item: item["sentence_id"])
    if len(expected_bindings) != len(
        {item["sentence_id"] for item in expected_bindings}
    ):
        request_errors.append("relief_binding_index_request_duplicate")
    if not expected_bindings:
        request_errors.append("relief_binding_index_request_empty")
    if request_errors:
        return tuple(dict.fromkeys(request_errors)), None

    resolver = getattr(authority, "resolve_relief_evidence_binding_index", None)
    if authority is None or not callable(resolver):
        return ("relief_binding_index_authority_required",), None
    adapter_lookup = deepcopy(lookup)
    try:
        resolution = resolver(adapter_lookup)
    except Exception as exc:  # host adapter failures are blockers, never passes
        return (f"relief_binding_index_authority_error:{exc}",), None
    if adapter_lookup != lookup:
        return ("relief_binding_index_request_mutated",), None
    if not isinstance(resolution, Mapping):
        return ("relief_binding_index_resolution_missing",), None

    errors: list[str] = []
    if resolution.get("schema_version") != "1.0.0":
        errors.append("relief_binding_index_schema_invalid")
    if resolution.get("status") != "verified":
        errors.append("relief_binding_index_not_verified")
    if resolution.get("matter_id") != matter_id:
        errors.append("relief_binding_index_matter_id_mismatch")
    if resolution.get("draft_id") != draft_id:
        errors.append("relief_binding_index_draft_id_mismatch")
    authoritative_bindings, binding_errors = _canonical_index_bindings(
        resolution.get("bindings"),
        label="relief_binding_index_bindings",
    )
    errors.extend(binding_errors)
    if authoritative_bindings != expected_bindings:
        errors.append("relief_binding_index_set_mismatch")
    computed_sha = _binding_index_sha256(
        matter_id=matter_id,
        draft_id=draft_id,
        bindings=authoritative_bindings,
    )
    if resolution.get("binding_index_sha256") != computed_sha:
        errors.append("relief_binding_index_sha256_mismatch")
    authority_revision_id = _clean(resolution.get("authority_revision_id"))
    checked_at = _clean(resolution.get("checked_at"))
    if not authority_revision_id:
        errors.append("relief_binding_index_authority_revision_id_missing")
    if not _is_rfc3339_datetime(resolution.get("checked_at")):
        errors.append("relief_binding_index_checked_at_invalid")
    if errors:
        return tuple(dict.fromkeys(errors)), None
    return (), {
        "schema_version": "1.0.0",
        "matter_id": matter_id,
        "draft_id": draft_id,
        "bindings": authoritative_bindings,
        "binding_index_sha256": computed_sha,
        "authority_revision_id": authority_revision_id,
        "checked_at": checked_at,
    }


__all__ = [
    "ReliefEvidenceBindingAuthority",
    "build_relief_binding_index_resolution",
    "build_relief_binding_index_request",
    "build_relief_binding_request",
    "resolve_relief_evidence_binding",
    "resolve_relief_evidence_binding_index",
]
