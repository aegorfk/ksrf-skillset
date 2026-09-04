"""Typed, content-bound file handoffs with an atomic local inbox ledger."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence, TypeGuard


SCHEMA_VERSION = "2.0"
LEGACY_SCHEMA_VERSION = "1.0"
SUPPORTED_PAYLOAD_TYPES = frozenset(
    {
        "unproven_research_questions",
        "approved_bounded_findings",
        "authority_cards",
    }
)
LEGACY_PAYLOAD_TYPES = SUPPORTED_PAYLOAD_TYPES | {"selected_authorities"}
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
SELECTED_PROOF_KEYS = (
    "position_cards",
    "comparisons",
    "relations",
    "adverse",
    "bridge",
    "human_decision",
    "validation_report",
)
PROOF_MANIFEST_PATHS = {
    "position_cards": "selected-proofs/position-cards.json",
    "comparisons": "selected-proofs/comparisons.json",
    "relations": "selected-proofs/relations.json",
    "adverse": "case-adverse-review.json",
    "bridge": "normative-bridge.json",
    "human_decision": "human-decision.json",
    "validation_report": "validation-report.json",
}
REQUIRED_QUALITY_TYPES = frozenset(
    {
        "chain_stage_propagation",
        "uncertainty_profile",
        "coding_audit_plan",
        "coding_reliability",
        "coding_audit_finalization_receipt",
        "prefiling_refresh",
    }
)
UNCERTAINTY_DIMENSIONS = frozenset(
    {
        "comparable_reading_plurality",
        "fact_sensitivity",
        "court_distribution",
        "temporal_distribution",
        "chain_endorsement",
        "outcome_materiality",
        "higher_authority_treatment",
        "coverage_limits",
        "coding_reliability",
    }
)
_EXCLUSION_LABELS = frozenset(
    {"party_only", "mentioned_only", "quoted_not_adopted", "false_positive", "unclear"}
)
_SUBSTANTIVE_LABELS = frozenset({"core_merits", "contextual"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_HTTP_RE = re.compile(r"^https?://", re.IGNORECASE)
_RFC3339_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?"
    r"(?:[Zz]|[+-]\d{2}:\d{2})"
)
_REFRESH_PLAN_ID_RE = re.compile(r"^refresh-plan-sha256:[0-9a-f]{64}$")
_REFRESH_GAP_SCOPE_FIELDS = frozenset(
    {"court_id", "period_id", "enumerator_id", "source_role"}
)
_PUBLIC_SEED_ROLES = frozenset(
    {
        "official_enumerator_observation",
        "official_user_seed",
        "official_authority_seed",
        "discovery_only",
    }
)
_AUDITED_CODING_FIELD_ORDER = (
    "label",
    "speaker",
    "norm_edition_id",
    "reading_family",
    "relation",
    "reasoning_to_outcome",
    "alternative_grounds",
    "remedy",
)
_AUDITED_CODING_FIELDS = frozenset(_AUDITED_CODING_FIELD_ORDER)
_CODING_REVIEW_DIFFERENCE_FIELD_ORDER = _AUDITED_CODING_FIELD_ORDER + (
    "proposition",
    "quote",
    "quote_locator",
    "material_facts",
)
_CODING_REVIEW_DIFFERENCE_FIELDS = frozenset(
    _CODING_REVIEW_DIFFERENCE_FIELD_ORDER
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


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def artifact_sha256(value: Any) -> str:
    """Return the canonical JSON SHA-256 used by all portable proof bindings."""

    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _canonical_json_file_sha256(value: Any) -> str:
    """Hash canonical JSON bytes as written by the native finalizer."""

    return hashlib.sha256(_canonical_bytes(value) + b"\n").hexdigest()


def _is_sha256(value: Any) -> TypeGuard[str]:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _is_native_audit_candidate_id(value: Any) -> TypeGuard[str]:
    return (
        isinstance(value, str)
        and re.fullmatch(r"audit-candidate-sha256:[0-9a-f]{64}", value) is not None
    )


def _is_nonempty(value: Any) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value.strip())


def _is_canonical_identifier(value: Any) -> TypeGuard[str]:
    return (
        _is_nonempty(value)
        and value == " ".join(value.split())
        and not any(
            unicodedata.category(character) in {"Cc", "Cf", "Cs"}
            for character in value
        )
    )


def _parse_timestamp(value: Any) -> datetime | None:
    if (
        not _is_nonempty(value)
        or value != value.strip()
        or _RFC3339_RE.fullmatch(value) is None
    ):
        return None
    try:
        cleaned = value
        normalized = cleaned[:-1] + "+00:00" if cleaned[-1:] in {"Z", "z"} else cleaned
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.utcoffset() is not None else None


def _is_timestamp(value: Any) -> bool:
    return _parse_timestamp(value) is not None


def _refresh_gap_valid(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    allowed = _REFRESH_GAP_SCOPE_FIELDS | {"reason", "action"}
    scope = set(value) & _REFRESH_GAP_SCOPE_FIELDS
    return (
        set(value).issubset(allowed)
        and bool(scope)
        and all(_is_canonical_identifier(value.get(field)) for field in scope)
        and (
            "source_role" not in scope
            or value.get("source_role") in _PUBLIC_SEED_ROLES
        )
        and value.get("reason") == "coverage_gap_not_observed"
        and _is_nonempty(value.get("action"))
    )


def _coverage_requirement_valid(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    fields = set(value)
    return (
        bool(fields)
        and fields.issubset(_REFRESH_GAP_SCOPE_FIELDS)
        and all(_is_canonical_identifier(value.get(field)) for field in fields)
        and (
            "source_role" not in fields
            or value.get("source_role") in _PUBLIC_SEED_ROLES
        )
    )


def _digest(envelope: Mapping[str, Any]) -> str:
    unsigned = {key: value for key, value in envelope.items() if key != "handoff_id"}
    return artifact_sha256(unsigned)


def _string_list(value: Any, *, allow_empty: bool) -> TypeGuard[list[str]]:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(_is_nonempty(item) for item in value)
    )


def _unique_string_list(value: Any, *, allow_empty: bool) -> TypeGuard[list[str]]:
    return _string_list(value, allow_empty=allow_empty) and len(value) == len(set(value))


def _canonical_unique_string_list(
    value: Any, *, allow_empty: bool
) -> TypeGuard[list[str]]:
    return _unique_string_list(value, allow_empty=allow_empty) and all(
        _is_canonical_identifier(item) for item in value
    )


def _question_errors(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["unproven_research_questions требует непустой список questions."]
    return [
        f"questions[{index}] должен быть непустой строкой."
        for index, item in enumerate(value, 1)
        if not _is_nonempty(item)
    ]


def _normalized_questions(value: Sequence[Any]) -> list[Any]:
    return [" ".join(item.split()) if isinstance(item, str) else item for item in value]


def _claim_binding_errors(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["claim_bindings должен быть непустым списком привязок требований."]
    errors: list[str] = []
    seen: set[str] = set()
    allowed = {"claim_id", "claim_sha256", "source_locator"}
    for index, binding in enumerate(value, 1):
        if not isinstance(binding, Mapping):
            errors.append(f"claim_bindings[{index}] должен быть объектом.")
            continue
        unknown = sorted(set(binding) - allowed)
        if unknown:
            errors.append(
                f"claim_bindings[{index}] содержит неподдерживаемые поля: "
                + ", ".join(unknown)
                + "."
            )
        claim_id = binding.get("claim_id")
        if not _is_nonempty(claim_id):
            errors.append(f"claim_bindings[{index}].claim_id должен быть непустой строкой.")
        elif claim_id in seen:
            errors.append(f"claim_bindings содержит повторный claim_id: {claim_id}.")
        else:
            seen.add(claim_id)
        if not _is_sha256(binding.get("claim_sha256")):
            errors.append(f"claim_bindings[{index}].claim_sha256 должен быть SHA-256.")
        if not _is_nonempty(binding.get("source_locator")):
            errors.append(f"claim_bindings[{index}].source_locator должен быть непустым.")
    return errors


def _claim_question_errors(
    value: Any,
    *,
    questions: Sequence[Any],
    claim_bindings: Sequence[Mapping[str, Any]],
) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return ["claim_questions должен быть списком объектов."]
    errors: list[str] = []
    claim_ids = {str(item.get("claim_id")) for item in claim_bindings}
    question_values = {item for item in questions if isinstance(item, str)}
    seen: set[str] = set()
    required = {"claim_id", "question_id", "question", "disconfirmation_prompts"}
    for index, item in enumerate(value, 1):
        if not isinstance(item, Mapping):
            errors.append(f"claim_questions[{index}] должен быть объектом.")
            continue
        if set(item) != required:
            errors.append(
                f"claim_questions[{index}] должен содержать ровно: "
                + ", ".join(sorted(required))
                + "."
            )
            continue
        claim_id = item.get("claim_id")
        question = item.get("question")
        if claim_id not in claim_ids:
            errors.append(f"claim_questions[{index}].claim_id отсутствует в claim_bindings.")
        if question not in question_values:
            errors.append(f"claim_questions[{index}].question отсутствует в questions.")
        expected_id = artifact_sha256({"claim_id": claim_id, "question": question})
        if item.get("question_id") != expected_id:
            errors.append(f"claim_questions[{index}].question_id не соответствует содержимому.")
        elif expected_id in seen:
            errors.append(f"Повторный claim_questions.question_id: {expected_id}.")
        else:
            seen.add(expected_id)
        if not _string_list(item.get("disconfirmation_prompts"), allow_empty=True):
            errors.append(
                f"claim_questions[{index}].disconfirmation_prompts должен быть списком строк."
            )
    return errors


def normalize_claim_bindings(value: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Validate and canonically order claim-level source bindings."""

    errors = _claim_binding_errors(value)
    if errors:
        raise ValueError(" ".join(errors))
    normalized = [dict(binding) for binding in value]
    return sorted(
        normalized,
        key=lambda item: (
            str(item["claim_id"]),
            str(item["claim_sha256"]),
            str(item["source_locator"]),
        ),
    )


def claim_set_sha256(bindings: Sequence[Mapping[str, Any]]) -> str:
    return artifact_sha256(normalize_claim_bindings(bindings))


def bind_request_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a research request and add its claim-set and request digests."""

    if not isinstance(payload, Mapping):
        raise ValueError("Payload запроса должен быть объектом.")
    questions = payload.get("questions")
    if not isinstance(questions, list):
        raise ValueError("unproven_research_questions требует непустой список questions.")
    question_errors = _question_errors(questions)
    if question_errors:
        raise ValueError(" ".join(question_errors))
    bindings = normalize_claim_bindings(payload.get("claim_bindings", []))
    normalized_questions = _normalized_questions(questions)
    expected_claim_set = artifact_sha256(bindings)
    supplied_claim_set = payload.get("claim_set_sha256")
    if supplied_claim_set is not None and supplied_claim_set != expected_claim_set:
        raise ValueError("claim_set_sha256 не соответствует claim_bindings.")
    request_material = {
        "questions": normalized_questions,
        "claim_bindings": bindings,
        "claim_set_sha256": expected_claim_set,
    }
    expected_request = artifact_sha256(request_material)
    supplied_request = payload.get("request_sha256")
    if supplied_request is not None and supplied_request != expected_request:
        raise ValueError("request_sha256 не соответствует вопросам и claim_bindings.")
    result = dict(payload)
    result["drafting_ready"] = False
    result["questions"] = normalized_questions
    result["claim_bindings"] = bindings
    result["claim_set_sha256"] = expected_claim_set
    result["request_sha256"] = expected_request
    claim_questions = payload.get("claim_questions")
    claim_question_errors = _claim_question_errors(
        claim_questions,
        questions=normalized_questions,
        claim_bindings=bindings,
    )
    if claim_question_errors:
        raise ValueError(" ".join(claim_question_errors))
    if claim_questions is not None:
        result["claim_questions"] = [dict(item) for item in claim_questions]
    return result


def build_selected_position_set_sha256(selected_proofs: Mapping[str, Any]) -> str:
    """Bind the exact selected cards, comparisons and applicant relations."""

    return artifact_sha256(
        {
            "position_cards": selected_proofs.get("position_cards"),
            "comparisons": selected_proofs.get("comparisons"),
            "relations": selected_proofs.get("relations"),
        }
    )


def build_artifact_manifest(selected_proofs: Mapping[str, Any]) -> dict[str, Any]:
    """Build a portable virtual-file manifest for the seven selected proofs."""

    files = []
    for key, path in PROOF_MANIFEST_PATHS.items():
        present = key in selected_proofs
        content = selected_proofs.get(key)
        content_bytes = _canonical_bytes(content) if present else b""
        files.append(
            {
                "path": path,
                "present": present,
                "bytes": len(content_bytes),
                "sha256": hashlib.sha256(content_bytes).hexdigest() if present else None,
            }
        )
    files.sort(key=lambda item: item["path"])
    return {"files": files, "manifest_sha256": artifact_sha256(files)}


def build_trusted_source_receipt(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Build the external source-workspace receipt; it is deliberately not portable proof."""

    payload = envelope.get("payload")
    if not isinstance(payload, Mapping):
        raise ValueError("Trusted receipt требует payload reviewed handoff.")
    quality = payload.get("quality_bindings", [])
    return {
        "schema_version": "1.0",
        "handoff_id": envelope.get("handoff_id"),
        "payload_sha256": artifact_sha256(payload),
        "request_handoff_id": payload.get("request_handoff_id"),
        "plan_sha256": envelope.get("plan_sha256"),
        "evidence_sha256": envelope.get("evidence_sha256"),
        "fingerprint_sha256": envelope.get("fingerprint_sha256"),
        "selected_position_set_sha256": payload.get("selected_position_set_sha256"),
        "maximum_permitted_claim": payload.get("maximum_permitted_claim"),
        "quality_artifact_sha256s": sorted(
            str(item.get("artifact_sha256"))
            for item in quality
            if isinstance(item, Mapping) and _is_sha256(item.get("artifact_sha256"))
        ),
        "quality_binding_sha256s": sorted(
            artifact_sha256(item)
            for item in quality
            if isinstance(item, Mapping)
        ),
    }


def build_approved_finding(
    candidate: Mapping[str, Any],
    claim_ids: Sequence[str],
    bridge: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive one bounded finding from an approved candidate and normative bridge."""

    if not isinstance(candidate, Mapping) or not _is_nonempty(candidate.get("candidate_id")):
        raise ValueError("Одобренный кандидат должен содержать candidate_id.")
    normalized_claim_ids = sorted(set(claim_ids))
    if not _string_list(normalized_claim_ids, allow_empty=False):
        raise ValueError("Finding требует хотя бы один claim_id.")
    if not isinstance(bridge, Mapping):
        raise ValueError("Finding требует нормативный мост.")
    candidate_copy = dict(candidate)
    candidate_sha = artifact_sha256(candidate_copy)
    bridge_sha = artifact_sha256(bridge)
    material = {
        "candidate_sha256": candidate_sha,
        "claim_ids": normalized_claim_ids,
        "normative_bridge_sha256": bridge_sha,
    }
    return {
        "finding_id": artifact_sha256(material),
        "candidate_id": candidate_copy["candidate_id"],
        "candidate_sha256": candidate_sha,
        "candidate": candidate_copy,
        "claim_ids": normalized_claim_ids,
        "claim_wording": bridge.get("claim_wording"),
        "supporting_position_card_ids": list(
            bridge.get("supporting_position_card_ids", [])
        ),
        "adverse_position_card_ids": list(bridge.get("adverse_position_card_ids", [])),
        "maximum_permitted_claim": bridge.get("maximum_permitted_claim"),
    }


def _request_payload_errors(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("drafting_ready") is not False:
        errors.append("unproven_research_questions требует drafting_ready=false.")
    errors.extend(_question_errors(payload.get("questions")))
    errors.extend(_claim_binding_errors(payload.get("claim_bindings")))
    if isinstance(payload.get("questions"), list) and isinstance(
        payload.get("claim_bindings"), list
    ):
        errors.extend(
            _claim_question_errors(
                payload.get("claim_questions"),
                questions=payload["questions"],
                claim_bindings=[
                    item for item in payload["claim_bindings"] if isinstance(item, Mapping)
                ],
            )
        )
    if not errors:
        bindings = normalize_claim_bindings(payload["claim_bindings"])
        if payload.get("claim_bindings") != bindings:
            errors.append("claim_bindings должен иметь канонический порядок.")
        expected_claim_set = artifact_sha256(bindings)
        if payload.get("claim_set_sha256") != expected_claim_set:
            errors.append("claim_set_sha256 не соответствует claim_bindings.")
        request_material = {
            "questions": _normalized_questions(payload["questions"]),
            "claim_bindings": bindings,
            "claim_set_sha256": expected_claim_set,
        }
        if payload.get("request_sha256") != artifact_sha256(request_material):
            errors.append("request_sha256 не соответствует вопросам и claim_bindings.")
    forbidden = sorted(
        key
        for key in (
            "findings",
            "maximum_permitted_claim",
            "supporting_position_card_ids",
            "adverse_position_card_ids",
            "approval_binding",
            "selected_proofs",
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
    allowed = {
        "drafting_ready",
        "questions",
        "claim_bindings",
        "claim_set_sha256",
        "request_sha256",
        "claim_questions",
    }
    unknown = sorted(set(payload) - allowed)
    if unknown:
        errors.append("Неподдерживаемые поля request payload: " + ", ".join(unknown) + ".")
    return errors


def _selected_proof_errors(
    payload: Mapping[str, Any],
    *,
    plan_sha256: str,
    evidence_sha256: str,
    fingerprint_sha256: str | None,
) -> list[str]:
    errors: list[str] = []
    selected = payload.get("selected_proofs")
    if not isinstance(selected, Mapping):
        return ["selected_proofs должен быть объектом с переносимыми доказательствами."]
    missing = [key for key in SELECTED_PROOF_KEYS if key not in selected]
    if missing:
        errors.append("selected_proofs не содержит: " + ", ".join(missing) + ".")
        return errors
    unknown = sorted(set(selected) - set(SELECTED_PROOF_KEYS))
    if unknown:
        errors.append("selected_proofs содержит неподдерживаемые поля: " + ", ".join(unknown) + ".")
    for key in ("position_cards", "comparisons", "relations"):
        if not isinstance(selected.get(key), list):
            errors.append(f"selected_proofs.{key} должен быть списком.")
    for key in ("adverse", "bridge", "human_decision", "validation_report"):
        if not isinstance(selected.get(key), Mapping):
            errors.append(f"selected_proofs.{key} должен быть объектом.")
    if errors:
        return errors

    cards = selected["position_cards"]
    comparisons = selected["comparisons"]
    relations = selected["relations"]
    if not cards:
        errors.append("selected_proofs.position_cards не может быть пустым.")
    cards_by_id: dict[str, Mapping[str, Any]] = {}
    for index, card in enumerate(cards, 1):
        if not isinstance(card, Mapping):
            errors.append(f"position_cards[{index}] должен быть объектом.")
            continue
        card_id = card.get("position_card_id")
        if not _is_nonempty(card_id):
            errors.append(f"position_cards[{index}] не содержит position_card_id.")
            continue
        if card_id in cards_by_id:
            errors.append(f"Повторный position_card_id: {card_id}.")
            continue
        cards_by_id[str(card_id)] = card
        for key in ("document_id", "proposition", "quote", "quote_locator"):
            if not _is_nonempty(card.get(key)):
                errors.append(f"Карточка {card_id} не содержит {key}.")
        if not _is_nonempty(card.get("official_url")) or not _HTTP_RE.match(
            str(card.get("official_url", ""))
        ):
            errors.append(f"Карточка {card_id} не содержит официальный URL.")
        if not _is_sha256(card.get("document_sha256")):
            errors.append(f"Карточка {card_id} не содержит document_sha256.")
        if card.get("speaker") != "court":
            errors.append(f"Карточка {card_id}: speaker должен быть court.")
        if card.get("quote_verified") is not True or card.get("full_text_reviewed") is not True:
            errors.append(f"Карточка {card_id}: цитата и полный текст не проверены.")
        if card.get("human_review") != "approved":
            errors.append(f"Карточка {card_id}: отсутствует human_review=approved.")
        if card.get("outcome_materiality") not in {
            "necessary_to_outcome",
            "independent_sufficient_ground",
        }:
            errors.append(f"Карточка {card_id}: вывод не связан с исходом дела.")

    comparisons_by_id: dict[str, Mapping[str, Any]] = {}
    for index, comparison in enumerate(comparisons, 1):
        if not isinstance(comparison, Mapping):
            errors.append(f"comparisons[{index}] должен быть объектом.")
            continue
        card_id = comparison.get("position_card_id")
        if not _is_nonempty(card_id) or card_id not in cards_by_id:
            errors.append(f"comparisons[{index}] ссылается на неизвестную карточку.")
            continue
        if card_id in comparisons_by_id:
            errors.append(f"Повторное сравнение для карточки {card_id}.")
            continue
        comparisons_by_id[str(card_id)] = comparison
        if comparison.get("status") != "matched":
            errors.append(f"Сравнение {card_id} не подтверждает сопоставимость.")
        if comparison.get("fingerprint_sha256") != fingerprint_sha256:
            errors.append(f"Сравнение {card_id} связано с иным fingerprint_sha256.")
        if comparison.get("position_card_sha256") != artifact_sha256(cards_by_id[str(card_id)]):
            errors.append(f"Сравнение {card_id} не связано с содержимым карточки.")
        provenance = comparison.get("review_provenance")
        if not isinstance(provenance, Mapping) or provenance.get("status") != "approved":
            errors.append(f"Сравнение {card_id} не одобрено человеком.")

    relations_by_id: dict[str, Mapping[str, Any]] = {}
    for index, relation in enumerate(relations, 1):
        if not isinstance(relation, Mapping):
            errors.append(f"relations[{index}] должен быть объектом.")
            continue
        card_id = relation.get("position_card_id")
        if not _is_nonempty(card_id) or card_id not in cards_by_id:
            errors.append(f"relations[{index}] ссылается на неизвестную карточку.")
            continue
        if card_id in relations_by_id:
            errors.append(f"Повторная applicant-relative связь для карточки {card_id}.")
            continue
        relations_by_id[str(card_id)] = relation
        comparison = comparisons_by_id.get(str(card_id))
        if relation.get("relation") not in {"supports", "adverse"}:
            errors.append(f"Связь {card_id} не является supports/adverse.")
        if relation.get("stale") is not False or relation.get("human_review") != "approved":
            errors.append(f"Связь {card_id} устарела или не одобрена.")
        if relation.get("fingerprint_sha256") != fingerprint_sha256:
            errors.append(f"Связь {card_id} относится к иному fingerprint_sha256.")
        if relation.get("position_card_sha256") != artifact_sha256(cards_by_id[str(card_id)]):
            errors.append(f"Связь {card_id} не связана с содержимым карточки.")
        if comparison is None:
            errors.append(f"Связь {card_id} не имеет сравнения.")
        else:
            if relation.get("comparison_id") != comparison.get("comparison_id"):
                errors.append(f"Связь {card_id} ссылается на иное сравнение.")
            if relation.get("comparison_sha256") != artifact_sha256(comparison):
                errors.append(f"Связь {card_id} не связана с содержимым сравнения.")
    if set(cards_by_id) != set(comparisons_by_id):
        errors.append("Не для каждой выбранной карточки есть ровно одно сравнение.")
    if set(cards_by_id) != set(relations_by_id):
        errors.append("Не для каждой выбранной карточки есть ровно одна applicant-relative связь.")

    bridge = selected["bridge"]
    supporting = bridge.get("supporting_position_card_ids")
    adverse_ids = bridge.get("adverse_position_card_ids")
    if not _unique_string_list(supporting, allow_empty=False):
        errors.append(
            "Нормативный мост требует уникальные supporting_position_card_ids без повторов."
        )
        supporting = []
    if not _unique_string_list(adverse_ids, allow_empty=True):
        errors.append(
            "Нормативный мост требует уникальные adverse_position_card_ids без повторов."
        )
        adverse_ids = []
    if set(supporting) & set(adverse_ids):
        errors.append("Supporting и adverse карточки не могут пересекаться.")
    if set(supporting) | set(adverse_ids) != set(cards_by_id):
        errors.append("Нормативный мост не охватывает точный набор выбранных карточек.")
    for card_id in supporting:
        if relations_by_id.get(card_id, {}).get("relation") != "supports":
            errors.append(f"Supporting карточка {card_id} не имеет relation=supports.")
    for card_id in adverse_ids:
        if relations_by_id.get(card_id, {}).get("relation") != "adverse":
            errors.append(f"Adverse карточка {card_id} не имеет relation=adverse.")
    if bridge.get("human_review") != "approved" or not _is_nonempty(bridge.get("reviewer")):
        errors.append("Нормативный мост не одобрен человеком.")
    if bridge.get("fingerprint_sha256") != fingerprint_sha256:
        errors.append("Нормативный мост связан с иным fingerprint_sha256.")
    if not _is_nonempty(bridge.get("claim_wording")):
        errors.append("Нормативный мост не содержит claim_wording.")
    if not _is_nonempty(bridge.get("maximum_permitted_claim")):
        errors.append("Нормативный мост не содержит maximum_permitted_claim.")

    adverse = selected["adverse"]
    if adverse.get("completed") is not True or adverse.get("missing_buckets") not in ([], ()):
        errors.append("Adverse review должен быть полностью завершён.")
    bucket_map = adverse.get("buckets")
    reviewed_adverse_ids: set[str] = set()
    if isinstance(bucket_map, Mapping):
        for ids in bucket_map.values():
            if isinstance(ids, list):
                reviewed_adverse_ids.update(item for item in ids if isinstance(item, str))
    if not set(adverse_ids).issubset(reviewed_adverse_ids):
        errors.append("Не все adverse карточки подтверждены adverse review.")

    decision = selected["human_decision"]
    if decision.get("decision") != "approved":
        errors.append("human_decision не содержит decision=approved.")
    if decision.get("plan_sha256") != plan_sha256:
        errors.append("human_decision относится к иному plan_sha256.")
    if decision.get("evidence_sha256") != evidence_sha256:
        errors.append("human_decision относится к иному evidence_sha256.")
    if not _is_nonempty(decision.get("reviewer")) or not _is_timestamp(decision.get("decided_at")):
        errors.append("human_decision требует reviewer и decided_at.")

    validation = selected["validation_report"]
    if validation.get("valid") is not True:
        errors.append("validation_report должен содержать valid=true.")
    if validation.get("plan_sha256") != plan_sha256:
        errors.append("validation_report относится к иному plan_sha256.")
    if validation.get("evidence_sha256") != evidence_sha256:
        errors.append("validation_report относится к иному evidence_sha256.")
    if validation.get("fingerprint_sha256") != fingerprint_sha256:
        errors.append("validation_report относится к иному fingerprint_sha256.")

    if payload.get("selected_position_set_sha256") != build_selected_position_set_sha256(selected):
        errors.append("selected_position_set_sha256 не соответствует выбранным карточкам.")
    expected_manifest = build_artifact_manifest(selected)
    if payload.get("artifact_manifest") != expected_manifest:
        errors.append("artifact_manifest не соответствует переносимым доказательствам.")

    approval = payload.get("approval_binding")
    if not isinstance(approval, Mapping):
        errors.append("approval_binding должен быть объектом.")
    else:
        approval_keys = {
            "human_decision_sha256",
            "validation_report_sha256",
            "normative_bridge_sha256",
            "reviewer",
            "approved_at",
        }
        if set(approval) != approval_keys:
            errors.append(
                "approval_binding должен содержать ровно: "
                + ", ".join(sorted(approval_keys))
                + "."
            )
        expected_digests = {
            "human_decision_sha256": artifact_sha256(decision),
            "validation_report_sha256": artifact_sha256(validation),
            "normative_bridge_sha256": artifact_sha256(bridge),
        }
        for key, expected in expected_digests.items():
            if approval.get(key) != expected:
                errors.append(f"approval_binding.{key} не соответствует доказательству.")
        if approval.get("reviewer") != decision.get("reviewer"):
            errors.append("approval_binding.reviewer не совпадает с human_decision.")
        if approval.get("approved_at") != decision.get("decided_at"):
            errors.append("approval_binding.approved_at не совпадает с human_decision.")
    return errors


def _approved_common_errors(
    payload: Mapping[str, Any],
    *,
    plan_sha256: str,
    evidence_sha256: str,
    fingerprint_sha256: str | None,
    limitations: Sequence[str],
) -> list[str]:
    errors: list[str] = []
    if payload.get("drafting_ready") is not True:
        errors.append("Проверенный handoff требует drafting_ready=true.")
    for key in ("request_handoff_id", "request_sha256", "claim_set_sha256"):
        if not _is_sha256(payload.get(key)):
            errors.append(f"Проверенный handoff требует {key} SHA-256.")
    errors.extend(_claim_binding_errors(payload.get("claim_bindings")))
    if not errors or not any("claim_bindings" in item for item in errors):
        try:
            bindings = normalize_claim_bindings(payload.get("claim_bindings", []))
        except ValueError:
            bindings = []
        if bindings and payload.get("claim_bindings") != bindings:
            errors.append("claim_bindings должен иметь канонический порядок.")
        if bindings and payload.get("claim_set_sha256") != artifact_sha256(bindings):
            errors.append("claim_set_sha256 не соответствует claim_bindings.")
    maximum = payload.get("maximum_permitted_claim")
    if not _is_nonempty(maximum):
        errors.append("Проверенный handoff требует maximum_permitted_claim.")
    payload_limitations = payload.get("limitations")
    if not _string_list(payload_limitations, allow_empty=False):
        errors.append("Проверенный handoff требует непустой payload.limitations.")
    elif list(payload_limitations) != list(limitations):
        errors.append("payload.limitations не совпадает с limitations envelope.")
    errors.extend(
        _selected_proof_errors(
            payload,
            plan_sha256=plan_sha256,
            evidence_sha256=evidence_sha256,
            fingerprint_sha256=fingerprint_sha256,
        )
    )
    selected = payload.get("selected_proofs")
    bridge = selected.get("bridge", {}) if isinstance(selected, Mapping) else {}
    if maximum != bridge.get("maximum_permitted_claim"):
        errors.append("maximum_permitted_claim не совпадает с нормативным мостом.")
    if payload.get("supporting_position_card_ids") != bridge.get(
        "supporting_position_card_ids"
    ):
        errors.append("supporting_position_card_ids не совпадает с нормативным мостом.")
    if payload.get("adverse_position_card_ids") != bridge.get("adverse_position_card_ids"):
        errors.append("adverse_position_card_ids не совпадает с нормативным мостом.")
    return errors


def _approved_finding_errors(
    payload: Mapping[str, Any],
    *,
    plan_sha256: str,
) -> list[str]:
    errors: list[str] = []
    findings = payload.get("findings")
    if not isinstance(findings, list) or not findings:
        return ["approved_bounded_findings требует непустой список findings."]
    selected = payload.get("selected_proofs")
    bridge_value = selected.get("bridge") if isinstance(selected, Mapping) else None
    bridge: Mapping[str, Any] = bridge_value if isinstance(bridge_value, Mapping) else {}
    decision_value = (
        selected.get("human_decision") if isinstance(selected, Mapping) else None
    )
    decision: Mapping[str, Any] = (
        decision_value if isinstance(decision_value, Mapping) else {}
    )
    permitted_claim_ids = {
        str(item.get("claim_id"))
        for item in payload.get("claim_bindings", [])
        if isinstance(item, Mapping) and _is_nonempty(item.get("claim_id"))
    }
    covered_claim_ids: set[str] = set()
    seen_finding_ids: set[str] = set()
    candidate_ids_value = decision.get("candidate_ids")
    candidate_ids = candidate_ids_value if isinstance(candidate_ids_value, list) else []
    for index, finding in enumerate(findings, 1):
        if not isinstance(finding, Mapping):
            errors.append(f"findings[{index}] должен быть объектом.")
            continue
        candidate = finding.get("candidate")
        if not isinstance(candidate, Mapping):
            errors.append(f"findings[{index}] не содержит artifact-derived candidate.")
            continue
        claim_ids = finding.get("claim_ids")
        if not _string_list(claim_ids, allow_empty=False):
            errors.append(f"findings[{index}] требует claim_ids.")
            continue
        if list(claim_ids) != sorted(set(claim_ids)):
            errors.append(f"findings[{index}].claim_ids должен иметь канонический порядок.")
        unknown_claims = sorted(set(claim_ids) - permitted_claim_ids)
        if unknown_claims:
            errors.append(
                f"findings[{index}] ссылается на неизвестные claim_id: "
                + ", ".join(unknown_claims)
                + "."
            )
        covered_claim_ids.update(claim_ids)
        candidate_id = candidate.get("candidate_id")
        if finding.get("candidate_id") != candidate_id:
            errors.append(f"findings[{index}].candidate_id не совпадает с candidate.")
        if candidate_id not in candidate_ids:
            errors.append(f"Кандидат {candidate_id} отсутствует в human_decision.")
        if candidate.get("plan_sha256") != plan_sha256:
            errors.append(f"Кандидат {candidate_id} относится к иному плану.")
        if candidate.get("human_review") != "approved" or candidate.get("drafting_ready") is not True:
            errors.append(f"Кандидат {candidate_id} не одобрен для drafting.")
        candidate_sha = artifact_sha256(candidate)
        if finding.get("candidate_sha256") != candidate_sha:
            errors.append(f"findings[{index}].candidate_sha256 не соответствует candidate.")
        expected = build_approved_finding(candidate, claim_ids, bridge)
        if dict(finding) != expected:
            errors.append(f"findings[{index}] не выведен из candidate и normative bridge.")
        finding_id = finding.get("finding_id")
        if finding_id in seen_finding_ids:
            errors.append(f"Повторный finding_id: {finding_id}.")
        elif isinstance(finding_id, str):
            seen_finding_ids.add(finding_id)
    if covered_claim_ids != permitted_claim_ids:
        errors.append("Approved findings не покрывают точный набор claim_bindings.")
    return errors


def _authority_card_errors(payload: Mapping[str, Any]) -> list[str]:
    selected_value = payload.get("selected_proofs")
    selected: Mapping[str, Any] = (
        selected_value if isinstance(selected_value, Mapping) else {}
    )
    cards = selected.get("position_cards")
    if payload.get("authority_cards") != cards or not isinstance(cards, list) or not cards:
        return ["authority_cards должен точно совпадать с выбранными position_cards."]
    if payload.get("review_state") != "approved":
        return ["authority_cards требует review_state=approved."]
    decision_value = selected.get("human_decision")
    decision = decision_value if isinstance(decision_value, Mapping) else {}
    if payload.get("reviewer") != decision.get("reviewer"):
        return ["authority_cards.reviewer не совпадает с human_decision."]
    return []


def _coding_audit_finalization_receipt_errors(
    artifact: Mapping[str, Any],
) -> list[str]:
    label = "quality coding_audit_finalization_receipt"
    if set(artifact) != _CODING_AUDIT_FINALIZATION_RECEIPT_FIELDS:
        return [f"{label}: нарушен закрытый контракт полей."]

    errors: list[str] = []
    unsigned = {
        key: value for key, value in artifact.items() if key != "receipt_sha256"
    }
    try:
        calculated_receipt_sha256 = artifact_sha256(unsigned)
    except (TypeError, ValueError, UnicodeEncodeError):
        calculated_receipt_sha256 = None
    if (
        not _is_sha256(artifact.get("receipt_sha256"))
        or artifact.get("receipt_sha256") != calculated_receipt_sha256
    ):
        errors.append(f"{label}: receipt_sha256 не соответствует artifact.")

    sha_fields = {
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
    }
    candidate_ids = artifact.get("candidate_ids")
    resolved_candidate_ids = artifact.get("resolved_candidate_ids")
    required_pairs = artifact.get("required_difference_pairs")
    resolved_populations = artifact.get("resolved_field_populations")

    required_pair_values: list[tuple[str, str]] = []
    required_pairs_valid = isinstance(required_pairs, list)
    if required_pairs_valid:
        for item in required_pairs:
            if (
                not isinstance(item, Mapping)
                or set(item) != {"candidate_id", "field"}
                or not _is_canonical_identifier(item.get("candidate_id"))
                or item.get("field") not in _CODING_REVIEW_DIFFERENCE_FIELDS
            ):
                required_pairs_valid = False
                break
            required_pair_values.append(
                (str(item["candidate_id"]), str(item["field"]))
            )
    required_pairs_valid = (
        required_pairs_valid
        and len(required_pair_values) == len(set(required_pair_values))
    )
    expected_pairs = (
        [
            {"candidate_id": candidate_id, "field": field}
            for candidate_id in candidate_ids
            for field in _CODING_REVIEW_DIFFERENCE_FIELD_ORDER
            if (candidate_id, field) in set(required_pair_values)
        ]
        if _canonical_unique_string_list(candidate_ids, allow_empty=False)
        else []
    )
    required_pairs_valid = required_pairs_valid and required_pairs == expected_pairs
    expected_resolved_candidate_ids = [
        candidate_id
        for candidate_id in candidate_ids
        if any(pair["candidate_id"] == candidate_id for pair in expected_pairs)
    ] if _canonical_unique_string_list(candidate_ids, allow_empty=False) else []
    expected_populations = [
        {
            "candidate_id": candidate_id,
            "fields": [
                pair["field"]
                for pair in expected_pairs
                if pair["candidate_id"] == candidate_id
            ],
        }
        for candidate_id in expected_resolved_candidate_ids
    ]

    expected_true = {
        "difference_resolution_bijection_verified",
        "final_quote_literal_presence_verified",
        "final_quote_normalized_presence_verified",
        "reliability_complete",
    }
    expected_false = {
        "quote_locator_verified",
        "source_workspace_reverified",
        "reviewer_identity_authenticated",
        "human_review_authenticated",
        "independence_verified",
        "receipt_authenticated",
        "norm_edition_temporal_applicability_verified",
        "publication_safe",
        "legal_readiness",
    }
    resolutions_present = artifact.get("resolutions_present")
    resolutions_file_sha256 = artifact.get("resolutions_file_sha256")
    receipt_contract_valid = (
        artifact.get("schema_version") == "1.0"
        and artifact.get("artifact_type")
        == "coding_audit_finalization_receipt"
        and artifact.get("producer")
        == "judicial_meaning.quality.coding_audit_finalize"
        and artifact.get("bundle_contract_version") in {"1.1", "1.2"}
        and artifact.get("codebook_version") == "1.0"
        and all(_is_sha256(artifact.get(field)) for field in sha_fields)
        and artifact.get("source_bundle_manifest_sha256")
        == artifact.get("expected_source_bundle_manifest_sha256")
        and artifact.get("audit_import_receipt_sha256")
        == artifact.get("expected_audit_import_receipt_sha256")
        and type(resolutions_present) is bool
        and (
            (resolutions_present is False and resolutions_file_sha256 is None)
            or (resolutions_present is True and _is_sha256(resolutions_file_sha256))
        )
        and _canonical_unique_string_list(candidate_ids, allow_empty=False)
        and all(_is_native_audit_candidate_id(value) for value in candidate_ids)
        and required_pairs_valid
        and set(candidate_id for candidate_id, _ in required_pair_values).issubset(
            set(candidate_ids)
        )
        and resolved_candidate_ids == expected_resolved_candidate_ids
        and resolved_populations == expected_populations
        and resolutions_present is bool(expected_pairs)
        and artifact.get("resolutions_state_sha256")
        == artifact_sha256(
            {
                "present": resolutions_present,
                "file_sha256": resolutions_file_sha256,
            }
        )
        and all(artifact.get(field) is True for field in expected_true)
        and all(artifact.get(field) is False for field in expected_false)
        and type(artifact.get("quote_locator_review_declared")) is bool
        and artifact.get("quote_locator_review_declared") is bool(expected_pairs)
    )
    if not receipt_contract_valid:
        errors.append(f"{label}: квитанция не подтверждает закрытую финализацию.")
    return errors


def _quality_artifact_errors(
    quality_type: str,
    artifact: Mapping[str, Any],
    *,
    plan_sha256: str,
    evidence_sha256: str,
    fingerprint_sha256: str | None,
    claim_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    if artifact.get("schema_version") != "1.0":
        errors.append(f"quality {quality_type}: schema_version должен быть 1.0.")
    if quality_type == "chain_stage_propagation":
        required = {
            "schema_version", "observation_count", "observations_sha256", "chain_count",
            "required_chain_ids", "trajectories", "unresolved",
            "review_complete", "evidence_sha256",
        }
        if set(artifact) != required:
            errors.append("quality chain_stage_propagation: нарушен закрытый контракт полей.")
        payload = {key: value for key, value in artifact.items() if key != "evidence_sha256"}
        if artifact.get("evidence_sha256") != artifact_sha256(payload):
            errors.append("quality chain_stage_propagation: evidence_sha256 не соответствует artifact.")
        trajectories = artifact.get("trajectories")
        trajectory_fields = {
            "schema_version", "chain_id", "observation_ids", "observation_sha256s",
            "origin_stage", "origin_reading_family", "reported_only_observation_ids",
            "cassation_treatment", "cassation_express_adoption",
            "alternative_sufficient_ground_present", "review_complete",
            "unresolved_reasons", "claim_limit", "trajectory_id",
        }
        trajectory_invalid = not isinstance(trajectories, list) or not trajectories
        if isinstance(trajectories, list) and trajectories:
            for trajectory in trajectories:
                if not isinstance(trajectory, Mapping) or set(trajectory) != trajectory_fields:
                    trajectory_invalid = True
                    break
                trajectory_payload = {
                    key: value for key, value in trajectory.items() if key != "trajectory_id"
                }
                if (
                    trajectory.get("trajectory_id") != artifact_sha256(trajectory_payload)
                    or trajectory.get("review_complete") is not True
                    or trajectory.get("unresolved_reasons") not in ([], ())
                    or not _unique_string_list(trajectory.get("observation_ids"), allow_empty=False)
                    or not _unique_string_list(
                        trajectory.get("observation_sha256s"), allow_empty=False
                    )
                    or not all(_is_sha256(item) for item in trajectory["observation_sha256s"])
                ):
                    trajectory_invalid = True
                    break
        if trajectory_invalid:
            errors.append("quality chain_stage_propagation: trajectory неполон или не content-bound.")
        if (
            artifact.get("review_complete") is not True
            or not _is_sha256(artifact.get("observations_sha256"))
            or artifact.get("unresolved") not in ([], ())
            or not _unique_string_list(artifact.get("required_chain_ids"), allow_empty=False)
            or trajectory_invalid
        ):
            errors.append("quality chain_stage_propagation: межинстанционная проверка не завершена.")
    elif quality_type == "uncertainty_profile":
        required = {
            "schema_version", "fingerprint_sha256", "unit", "dimensions",
            "profile_assessed", "claim_use_ready", "blocking_dimensions",
            "profile_complete", "numeric_aggregation",
            "constitutional_conclusion_permitted", "malformed_position_card_refs",
            "malformed_trajectory_refs", "coding_reliability_origin",
            "input_sha256s",
            "claim_limit", "profile_id",
        }
        if set(artifact) != required:
            errors.append("quality uncertainty_profile: нарушен закрытый контракт полей.")
        payload = {key: value for key, value in artifact.items() if key != "profile_id"}
        if artifact.get("profile_id") != artifact_sha256(payload):
            errors.append("quality uncertainty_profile: profile_id не соответствует artifact.")
        dimensions = artifact.get("dimensions")
        dimension_fields = {
            "state", "chain_ids", "evidence_refs", "unknowns", "claim_effect",
            "assessed", "usable_for_claim", "review_complete",
        }
        if not isinstance(dimensions, Mapping) or set(dimensions) != UNCERTAINTY_DIMENSIONS:
            errors.append("quality uncertainty_profile: требуется девять отдельных измерений.")
        elif any(
            not isinstance(item, Mapping)
            or set(item) != dimension_fields
            or item.get("assessed") is not True
            or item.get("usable_for_claim") is not True
            or item.get("review_complete") is not True
            for item in dimensions.values()
        ):
            errors.append("quality uncertainty_profile: есть неоценённое или блокирующее измерение.")
        input_hashes = artifact.get("input_sha256s")
        input_hash_fields = {
            "applicant_relations", "coding_audit_finalization_receipt",
            "coding_reliability", "comparisons",
            "expected_finalization_receipt_sha256",
            "higher_authority_treatments", "position_cards", "source_reconciliation",
            "temporal_analysis", "trajectories",
        }
        reliability_origin = artifact.get("coding_reliability_origin")
        reliability_origin_valid = (
            isinstance(reliability_origin, Mapping)
            and set(reliability_origin) == _CODING_RELIABILITY_ORIGIN_FIELDS
            and reliability_origin.get("status") == "native_finalization_bound"
            and reliability_origin.get("reason_codes") in ([], ())
            and _is_sha256(reliability_origin.get("expected_receipt_sha256"))
            and all(
                reliability_origin.get(field) is True
                for field in (
                    "reliability_contract_valid",
                    "receipt_contract_valid",
                    "receipt_self_digest_valid",
                    "external_receipt_digest_valid",
                    "reliability_file_digest_valid",
                    "audit_plan_digest_valid",
                    "candidate_population_valid",
                    "usable_for_claim",
                )
            )
        )
        if (
            artifact.get("fingerprint_sha256") != fingerprint_sha256
            or artifact.get("unit") != "independent_case_chain"
            or artifact.get("profile_assessed") is not True
            or artifact.get("claim_use_ready") is not True
            or artifact.get("profile_complete") is not True
            or artifact.get("blocking_dimensions") not in ([], ())
            or artifact.get("numeric_aggregation") != "prohibited"
            or artifact.get("constitutional_conclusion_permitted") is not False
            or artifact.get("malformed_position_card_refs") not in ([], ())
            or artifact.get("malformed_trajectory_refs") not in ([], ())
            or not isinstance(input_hashes, Mapping)
            or set(input_hashes) != input_hash_fields
            or not all(_is_sha256(value) for value in input_hashes.values())
            or not reliability_origin_valid
            or input_hashes.get("expected_finalization_receipt_sha256")
            != reliability_origin.get("expected_receipt_sha256")
            or not _is_nonempty(artifact.get("claim_limit"))
        ):
            errors.append("quality uncertainty_profile: профиль не готов или связан с иным делом.")
    elif quality_type == "coding_audit_plan":
        required = {
            "schema_version", "plan_sha256", "screening_sha256",
            "primary_coding_sha256", "selection_method", "sample_size",
            "exclusion_sample_size", "sample_candidate_ids",
            "exclusion_sample_candidate_ids", "required_candidate_ids",
            "invalid_screening_record_ids", "invalid_primary_record_ids",
            "frozen", "audit_plan_sha256",
        }
        if set(artifact) != required:
            errors.append("quality coding_audit_plan: нарушен закрытый контракт полей.")
        payload = {key: value for key, value in artifact.items() if key != "audit_plan_sha256"}
        if artifact.get("audit_plan_sha256") != artifact_sha256(payload):
            errors.append("quality coding_audit_plan: audit_plan_sha256 не соответствует artifact.")
        sample_size = artifact.get("sample_size")
        exclusion_sample_size = artifact.get("exclusion_sample_size")
        sample_ids = artifact.get("sample_candidate_ids")
        exclusion_ids = artifact.get("exclusion_sample_candidate_ids")
        required_candidate_ids = artifact.get("required_candidate_ids")
        plan_lists_valid = all(
            _canonical_unique_string_list(artifact.get(field), allow_empty=True)
            for field in (
                "invalid_screening_record_ids", "invalid_primary_record_ids",
                "sample_candidate_ids", "exclusion_sample_candidate_ids",
                "required_candidate_ids",
            )
        )
        if (
            artifact.get("schema_version") != "1.0"
            or artifact.get("plan_sha256") != plan_sha256
            or not _is_sha256(artifact.get("plan_sha256"))
            or artifact.get("frozen") is not True
            or artifact.get("selection_method") != "canonical_sha256_rank"
            or not _is_sha256(artifact.get("screening_sha256"))
            or not _is_sha256(artifact.get("primary_coding_sha256"))
            or isinstance(sample_size, bool)
            or not isinstance(sample_size, int)
            or sample_size < 0
            or isinstance(exclusion_sample_size, bool)
            or not isinstance(exclusion_sample_size, int)
            or exclusion_sample_size < 0
            or not plan_lists_valid
            or len(sample_ids) > sample_size
            or len(exclusion_ids) > exclusion_sample_size
            or set(required_candidate_ids) != set(sample_ids) | set(exclusion_ids)
            or artifact.get("invalid_screening_record_ids") not in ([], ())
            or artifact.get("invalid_primary_record_ids") not in ([], ())
            or not required_candidate_ids
        ):
            errors.append("quality coding_audit_plan: план не заморожен или связан с иным планом.")
    elif quality_type == "coding_reliability":
        required = {
            "schema_version", "audit_plan_input_sha256", "audit_plan_sha256",
            "audit_plan_frozen",
            "audit_plan_contract_valid", "audit_plan_digest_valid",
            "primary_coding_sha256",
            "current_primary_coding_sha256", "required_candidate_ids",
            "audit_decisions_sha256", "adjudications_sha256",
            "audited_candidate_ids", "missing_candidate_ids",
            "same_reviewer_candidate_ids", "invalid_binding_candidate_ids",
            "invalid_provenance_candidate_ids", "invalid_screening_record_ids",
            "invalid_primary_record_ids", "invalid_audit_record_ids",
            "invalid_adjudication_record_ids", "field_disagreements",
            "false_exclusion_diagnostics", "unresolved_candidate_ids",
            "stale", "complete", "evidence_sha256",
        }
        if set(artifact) != required:
            errors.append("quality coding_reliability: нарушен закрытый контракт полей.")
        payload = {key: value for key, value in artifact.items() if key != "evidence_sha256"}
        if artifact.get("evidence_sha256") != artifact_sha256(payload):
            errors.append("quality coding_reliability: evidence_sha256 не соответствует artifact.")
        required_ids = artifact.get("required_candidate_ids")
        audited_ids = artifact.get("audited_candidate_ids")
        required_ids_valid = _canonical_unique_string_list(
            required_ids, allow_empty=False
        )
        audited_ids_valid = _canonical_unique_string_list(
            audited_ids, allow_empty=False
        )
        required_id_set = set(required_ids) if required_ids_valid else set()
        field_disagreements = artifact.get("field_disagreements")
        disagreements_valid = isinstance(field_disagreements, list) and all(
            isinstance(item, Mapping)
            and set(item)
            == {
                "candidate_id", "fields", "primary_coding_sha256",
                "secondary_coding_sha256", "resolved", "adjudication_sha256",
            }
            and _is_canonical_identifier(item.get("candidate_id"))
            and _unique_string_list(item.get("fields"), allow_empty=False)
            and set(item.get("fields", [])).issubset(_AUDITED_CODING_FIELDS)
            and _is_sha256(item.get("primary_coding_sha256"))
            and _is_sha256(item.get("secondary_coding_sha256"))
            and item.get("resolved") is True
            and _is_sha256(item.get("adjudication_sha256"))
            for item in field_disagreements
        )
        disagreement_by_candidate = (
            {str(item["candidate_id"]): item for item in field_disagreements}
            if disagreements_valid
            else {}
        )
        empty_adjudications_sha256 = artifact_sha256([])
        adjudication_digest_shape_valid = (
            not field_disagreements
            and artifact.get("adjudications_sha256")
            == empty_adjudications_sha256
        ) or (
            bool(field_disagreements)
            and artifact.get("adjudications_sha256")
            != empty_adjudications_sha256
        )
        disagreements_valid = (
            disagreements_valid
            and len(disagreement_by_candidate) == len(field_disagreements)
            and set(disagreement_by_candidate).issubset(required_id_set)
        )
        false_exclusions = artifact.get("false_exclusion_diagnostics")
        false_exclusions_valid = isinstance(false_exclusions, list) and all(
            isinstance(item, Mapping)
            and set(item)
            == {
                "candidate_id", "primary_label", "secondary_label", "resolved",
            }
            and _is_canonical_identifier(item.get("candidate_id"))
            and item.get("primary_label") in _EXCLUSION_LABELS
            and item.get("secondary_label") in _SUBSTANTIVE_LABELS
            and item.get("resolved") is True
            and str(item.get("candidate_id")) in required_id_set
            and str(item.get("candidate_id")) in disagreement_by_candidate
            and "label"
            in disagreement_by_candidate[str(item.get("candidate_id"))].get("fields", [])
            for item in false_exclusions
        )
        false_exclusion_ids = (
            [str(item["candidate_id"]) for item in false_exclusions]
            if false_exclusions_valid
            else []
        )
        false_exclusions_valid = (
            false_exclusions_valid
            and len(false_exclusion_ids) == len(set(false_exclusion_ids))
        )
        if (
            not _is_sha256(artifact.get("audit_plan_input_sha256"))
            or not _is_sha256(artifact.get("audit_plan_sha256"))
            or artifact.get("audit_plan_frozen") is not True
            or artifact.get("audit_plan_contract_valid") is not True
            or artifact.get("audit_plan_digest_valid") is not True
            or not _is_sha256(artifact.get("primary_coding_sha256"))
            or not _is_sha256(artifact.get("current_primary_coding_sha256"))
            or not _is_sha256(artifact.get("audit_decisions_sha256"))
            or not _is_sha256(artifact.get("adjudications_sha256"))
            or not adjudication_digest_shape_valid
            or artifact.get("primary_coding_sha256")
            != artifact.get("current_primary_coding_sha256")
            or artifact.get("complete") is not True
            or artifact.get("stale") is not False
            or artifact.get("unresolved_candidate_ids") not in ([], ())
            or artifact.get("missing_candidate_ids") not in ([], ())
            or artifact.get("same_reviewer_candidate_ids") not in ([], ())
            or artifact.get("invalid_binding_candidate_ids") not in ([], ())
            or artifact.get("invalid_provenance_candidate_ids") not in ([], ())
            or artifact.get("invalid_screening_record_ids") not in ([], ())
            or artifact.get("invalid_primary_record_ids") not in ([], ())
            or artifact.get("invalid_audit_record_ids") not in ([], ())
            or artifact.get("invalid_adjudication_record_ids") not in ([], ())
            or not required_ids_valid
            or not audited_ids_valid
            or set(required_ids) != set(audited_ids)
            or not disagreements_valid
            or not false_exclusions_valid
        ):
            errors.append("quality coding_reliability: независимая проверка не завершена.")
    elif quality_type == "coding_audit_finalization_receipt":
        errors.extend(_coding_audit_finalization_receipt_errors(artifact))
    elif quality_type == "prefiling_refresh":
        required = {
            "schema_version", "baseline_corpus_digest", "current_corpus_digest",
            "subject_evidence_sha256", "refresh_plan_id", "refresh_plan_sha256",
            "refresh_plan_contract_valid", "refresh_plan_as_of",
            "refresh_plan_max_age_seconds", "refresh_plan_evidence_digest",
            "refresh_plan_treatment_ids",
            "refresh_plan_treatment_population_sha256",
            "refresh_plan_coverage_requirements",
            "refresh_plan_coverage_requirements_sha256",
            "checked_through", "filing_cutoff", "reviewer", "reviewed_at",
            "claim_ids", "affected_claim_ids", "live_binding_version",
            "live_corpus_binding_contract_valid",
            "live_corpus_binding_verified", "live_cache_stable",
            "live_corpus_evidence_digest", "live_refresh_plan_sha256",
            "live_treatment_set_sha256",
            "live_treatment_population_sha256", "live_treatment_ids",
            "live_binding_issue_ids", "treatment_set_contract_valid",
            "treatment_set_sha256", "treatment_set_corpus_evidence_digest",
            "treatment_set_population_sha256",
            "treatments_sha256",
            "pending_treatment_ids", "verified_treatment_ids", "rejected_treatment_ids",
            "superseded_treatment_ids",
            "treatment_chronology_issue_ids", "stale_seed_ids",
            "malformed_refresh_entry_ids", "malformed_coverage_requirement_ids",
            "malformed_coverage_gap_ids",
            "coverage_gaps", "reasons", "status", "complete", "refresh_id",
        }
        if set(artifact) != required:
            errors.append("quality prefiling_refresh: нарушен закрытый контракт полей.")
        payload = {key: value for key, value in artifact.items() if key != "refresh_id"}
        if artifact.get("refresh_id") != artifact_sha256(payload):
            errors.append("quality prefiling_refresh: refresh_id не соответствует artifact.")
        refresh_claim_ids = artifact.get("claim_ids")
        refresh_treatment_ids = artifact.get("refresh_plan_treatment_ids")
        treatment_list_values = [
            artifact.get("pending_treatment_ids"),
            artifact.get("verified_treatment_ids"),
            artifact.get("rejected_treatment_ids"),
            artifact.get("superseded_treatment_ids"),
        ]
        treatment_lists_valid = all(
            _unique_string_list(value, allow_empty=True)
            for value in treatment_list_values
        )
        treatment_sets: list[set[str]] = []
        if treatment_lists_valid:
            for value in treatment_list_values:
                if isinstance(value, list):
                    treatment_sets.append(
                        {item for item in value if isinstance(item, str)}
                    )
        treatments_disjoint = len(treatment_sets) == 4 and not any(
            left & right
            for index, left in enumerate(treatment_sets)
            for right in treatment_sets[index + 1 :]
        )
        refresh_plan_as_of = _parse_timestamp(artifact.get("refresh_plan_as_of"))
        checked_through = _parse_timestamp(artifact.get("checked_through"))
        filing_cutoff = _parse_timestamp(artifact.get("filing_cutoff"))
        reviewed_at = _parse_timestamp(artifact.get("reviewed_at"))
        evaluation_time = datetime.now(timezone.utc)
        max_age_seconds = artifact.get("refresh_plan_max_age_seconds")
        status = artifact.get("status")
        coverage_gaps = artifact.get("coverage_gaps")
        coverage_requirements = artifact.get("refresh_plan_coverage_requirements")
        requirements_valid = (
            isinstance(coverage_requirements, list)
            and bool(coverage_requirements)
            and all(
                _coverage_requirement_valid(item)
                for item in coverage_requirements
            )
            and len({artifact_sha256(item) for item in coverage_requirements})
            == len(coverage_requirements)
            and artifact.get("refresh_plan_coverage_requirements_sha256")
            == artifact_sha256(coverage_requirements)
        )
        requirement_digests = (
            {artifact_sha256(item) for item in coverage_requirements}
            if requirements_valid
            else set()
        )
        gap_scope_digests = (
            {
                artifact_sha256(
                    {
                        field: item[field]
                        for field in _REFRESH_GAP_SCOPE_FIELDS
                        if field in item
                    }
                )
                for item in coverage_gaps
                if isinstance(item, Mapping)
            }
            if isinstance(coverage_gaps, list)
            else set()
        )
        reasons = artifact.get("reasons")
        status_shape_valid = (
            status == "current_no_material_change"
            and coverage_gaps in ([], ())
            and reasons in ([], ())
        ) or (
            status == "bounded_current_with_disclosed_gaps"
            and isinstance(coverage_gaps, list)
            and bool(coverage_gaps)
            and all(_refresh_gap_valid(item) for item in coverage_gaps)
            and len({artifact_sha256(item) for item in coverage_gaps})
            == len(coverage_gaps)
            and reasons == ["unchanged_disclosed_coverage_gaps"]
        )
        if (
            not _is_sha256(artifact.get("baseline_corpus_digest"))
            or not _is_sha256(artifact.get("current_corpus_digest"))
            or artifact.get("baseline_corpus_digest")
            != artifact.get("current_corpus_digest")
            or artifact.get("subject_evidence_sha256") != evidence_sha256
            or not _is_sha256(artifact.get("refresh_plan_sha256"))
            or not isinstance(artifact.get("refresh_plan_id"), str)
            or _REFRESH_PLAN_ID_RE.fullmatch(artifact.get("refresh_plan_id")) is None
            or artifact.get("refresh_plan_contract_valid") is not True
            or refresh_plan_as_of is None
            or isinstance(max_age_seconds, bool)
            or not isinstance(max_age_seconds, int)
            or max_age_seconds < 0
            or artifact.get("refresh_plan_evidence_digest")
            != f"corpus-evidence-sha256:{artifact.get('current_corpus_digest')}"
            or artifact.get("live_binding_version") != "1.0"
            or artifact.get("live_corpus_binding_contract_valid") is not True
            or artifact.get("live_corpus_binding_verified") is not True
            or artifact.get("live_cache_stable") is not True
            or artifact.get("live_corpus_evidence_digest")
            != f"corpus-evidence-sha256:{artifact.get('current_corpus_digest')}"
            or artifact.get("live_refresh_plan_sha256")
            != artifact.get("refresh_plan_sha256")
            or artifact.get("live_treatment_set_sha256")
            != artifact.get("treatment_set_sha256")
            or artifact.get("live_treatment_population_sha256")
            != artifact.get("refresh_plan_treatment_population_sha256")
            or artifact.get("live_treatment_ids") != refresh_treatment_ids
            or artifact.get("live_binding_issue_ids") not in ([], ())
            or not _canonical_unique_string_list(
                refresh_treatment_ids, allow_empty=True
            )
            or refresh_treatment_ids != sorted(refresh_treatment_ids)
            or not _is_sha256(
                artifact.get("refresh_plan_treatment_population_sha256")
            )
            or not requirements_valid
            or not gap_scope_digests.issubset(requirement_digests)
            or artifact.get("treatment_set_contract_valid") is not True
            or not _is_sha256(artifact.get("treatment_set_sha256"))
            or artifact.get("treatment_set_corpus_evidence_digest")
            != f"corpus-evidence-sha256:{artifact.get('current_corpus_digest')}"
            or artifact.get("treatment_set_population_sha256")
            != artifact.get("refresh_plan_treatment_population_sha256")
            or set(refresh_treatment_ids)
            != set().union(*treatment_sets)
            or not _is_sha256(artifact.get("treatments_sha256"))
            or artifact.get("complete") is not True
            or not status_shape_valid
            or artifact.get("affected_claim_ids") not in ([], ())
            or artifact.get("pending_treatment_ids") not in ([], ())
            or artifact.get("treatment_chronology_issue_ids") not in ([], ())
            or artifact.get("stale_seed_ids") not in ([], ())
            or artifact.get("malformed_refresh_entry_ids") not in ([], ())
            or artifact.get("malformed_coverage_requirement_ids") not in ([], ())
            or artifact.get("malformed_coverage_gap_ids") not in ([], ())
            or not treatments_disjoint
            or not _canonical_unique_string_list(
                refresh_claim_ids, allow_empty=False
            )
            or set(refresh_claim_ids) != claim_ids
            or not _is_canonical_identifier(artifact.get("reviewer"))
            or reviewed_at is None
            or checked_through is None
            or filing_cutoff is None
            or checked_through > evaluation_time
            or reviewed_at > evaluation_time
            or refresh_plan_as_of != checked_through
            or reviewed_at < checked_through
            or checked_through < filing_cutoff
        ):
            errors.append("quality prefiling_refresh: refresh не текущий или не охватывает claims.")
    return errors


def _quality_binding_errors(
    value: Any,
    *,
    plan_sha256: str,
    evidence_sha256: str,
    fingerprint_sha256: str | None,
    claim_bindings: Any,
) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["quality_bindings должен быть непустым списком content-bound артефактов."]
    errors: list[str] = []
    allowed_types = set(REQUIRED_QUALITY_TYPES)
    seen_types: set[str] = set()
    artifacts_by_type: dict[str, Mapping[str, Any]] = {}
    claim_ids = {
        str(item.get("claim_id"))
        for item in claim_bindings
        if isinstance(item, Mapping) and _is_nonempty(item.get("claim_id"))
    } if isinstance(claim_bindings, list) else set()
    for index, binding in enumerate(value, 1):
        if not isinstance(binding, Mapping):
            errors.append(f"quality_bindings[{index}] должен быть объектом.")
            continue
        quality_type = binding.get("quality_type")
        expected_binding_fields = {"quality_type", "artifact_sha256", "artifact"}
        if quality_type == "coding_audit_finalization_receipt":
            expected_binding_fields.add("expected_receipt_sha256")
        if set(binding) != expected_binding_fields:
            expected_description = (
                "quality_type, artifact_sha256, artifact и "
                "expected_receipt_sha256"
                if quality_type == "coding_audit_finalization_receipt"
                else "quality_type, artifact_sha256 и artifact"
            )
            errors.append(
                f"quality_bindings[{index}] должен содержать ровно "
                f"{expected_description}."
            )
            continue
        artifact = binding.get("artifact")
        if quality_type not in allowed_types:
            errors.append(f"quality_bindings[{index}].quality_type не поддерживается.")
        if not isinstance(artifact, Mapping):
            errors.append(f"quality_bindings[{index}].artifact должен быть объектом.")
            continue
        digest = artifact_sha256(artifact)
        if binding.get("artifact_sha256") != digest:
            errors.append(f"quality_bindings[{index}].artifact_sha256 не соответствует artifact.")
        if (
            quality_type == "coding_audit_finalization_receipt"
            and not _is_sha256(binding.get("expected_receipt_sha256"))
        ):
            errors.append(
                f"quality_bindings[{index}].expected_receipt_sha256 должен быть SHA-256."
            )
        if isinstance(quality_type, str) and quality_type in seen_types:
            errors.append(f"Повторный quality binding типа {quality_type}.")
        elif isinstance(quality_type, str):
            seen_types.add(quality_type)
            artifacts_by_type[quality_type] = artifact
        errors.extend(
            _quality_artifact_errors(
                str(quality_type),
                artifact,
                plan_sha256=plan_sha256,
                evidence_sha256=evidence_sha256,
                fingerprint_sha256=fingerprint_sha256,
                claim_ids=claim_ids,
            )
        )
    missing_types = sorted(REQUIRED_QUALITY_TYPES - seen_types)
    if missing_types:
        errors.append("quality_bindings не содержит обязательные типы: " + ", ".join(missing_types) + ".")
    audit_plan = artifacts_by_type.get("coding_audit_plan")
    reliability = artifacts_by_type.get("coding_reliability")
    finalization_receipt = artifacts_by_type.get(
        "coding_audit_finalization_receipt"
    )
    if audit_plan is not None and reliability is not None:
        if (
            reliability.get("audit_plan_input_sha256") != artifact_sha256(audit_plan)
            or reliability.get("audit_plan_sha256")
            != audit_plan.get("audit_plan_sha256")
            or reliability.get("primary_coding_sha256")
            != audit_plan.get("primary_coding_sha256")
            or reliability.get("required_candidate_ids")
            != audit_plan.get("required_candidate_ids")
        ):
            errors.append(
                "quality coding_reliability не связан с переданным coding_audit_plan."
            )
    receipt_binding = next(
        (
            binding
            for binding in value
            if isinstance(binding, Mapping)
            and binding.get("quality_type")
            == "coding_audit_finalization_receipt"
            and set(binding)
            == {
                "quality_type",
                "artifact_sha256",
                "artifact",
                "expected_receipt_sha256",
            }
        ),
        None,
    )
    if (
        audit_plan is not None
        and reliability is not None
        and finalization_receipt is not None
        and receipt_binding is not None
    ):
        expected_receipt_sha256 = receipt_binding.get("expected_receipt_sha256")
        native_relation_valid = (
            _is_sha256(expected_receipt_sha256)
            and finalization_receipt.get("receipt_sha256")
            == expected_receipt_sha256
            and finalization_receipt.get("coding_reliability_file_sha256")
            == _canonical_json_file_sha256(reliability)
            and finalization_receipt.get("audit_plan_sha256")
            == reliability.get("audit_plan_sha256")
            == audit_plan.get("audit_plan_sha256")
            and finalization_receipt.get("candidate_ids")
            == reliability.get("required_candidate_ids")
            == audit_plan.get("required_candidate_ids")
            and finalization_receipt.get("plan_sha256") == plan_sha256
        )
        if not native_relation_valid:
            errors.append(
                "quality coding_audit_finalization_receipt не связан с внешним "
                "подтверждением, reliability, планом или кандидатами."
            )
    profile = artifacts_by_type.get("uncertainty_profile")
    propagation = artifacts_by_type.get("chain_stage_propagation")
    if profile is not None and reliability is not None:
        input_hashes = profile.get("input_sha256s")
        if (
            not isinstance(input_hashes, Mapping)
            or input_hashes.get("coding_reliability")
            != artifact_sha256(reliability)
        ):
            errors.append(
                "quality uncertainty_profile не связан с coding_reliability."
            )
    if (
        profile is not None
        and finalization_receipt is not None
        and receipt_binding is not None
    ):
        input_hashes = profile.get("input_sha256s")
        origin = profile.get("coding_reliability_origin")
        expected_receipt_sha256 = receipt_binding.get("expected_receipt_sha256")
        if (
            not isinstance(input_hashes, Mapping)
            or not isinstance(origin, Mapping)
            or input_hashes.get("coding_audit_finalization_receipt")
            != artifact_sha256(finalization_receipt)
            or input_hashes.get("expected_finalization_receipt_sha256")
            != expected_receipt_sha256
            or origin.get("expected_receipt_sha256")
            != expected_receipt_sha256
        ):
            errors.append(
                "quality uncertainty_profile не связан с native-квитанцией и "
                "внешним подтверждением."
            )
    if profile is not None and propagation is not None:
        input_hashes = profile.get("input_sha256s")
        trajectories = propagation.get("trajectories")
        if (
            not isinstance(input_hashes, Mapping)
            or not isinstance(trajectories, list)
            or input_hashes.get("trajectories") != artifact_sha256(trajectories)
        ):
            errors.append(
                "quality uncertainty_profile не связан с chain_stage_propagation."
            )
    return errors


def _payload_errors(
    payload_type: str,
    payload: Mapping[str, Any],
    *,
    plan_sha256: str,
    evidence_sha256: str,
    fingerprint_sha256: str | None,
    limitations: Sequence[str],
) -> list[str]:
    """Validate typed payload semantics independently of envelope integrity."""

    if payload_type == "unproven_research_questions":
        return _request_payload_errors(payload)
    errors = _approved_common_errors(
        payload,
        plan_sha256=plan_sha256,
        evidence_sha256=evidence_sha256,
        fingerprint_sha256=fingerprint_sha256,
        limitations=limitations,
    )
    errors.extend(
        _quality_binding_errors(
            payload.get("quality_bindings"),
            plan_sha256=plan_sha256,
            evidence_sha256=evidence_sha256,
            fingerprint_sha256=fingerprint_sha256,
            claim_bindings=payload.get("claim_bindings"),
        )
    )
    if payload_type == "approved_bounded_findings":
        errors.extend(_approved_finding_errors(payload, plan_sha256=plan_sha256))
        allowed = {
            "drafting_ready",
            "request_handoff_id",
            "request_sha256",
            "claim_set_sha256",
            "claim_bindings",
            "findings",
            "supporting_position_card_ids",
            "adverse_position_card_ids",
            "approval_binding",
            "artifact_manifest",
            "selected_position_set_sha256",
            "selected_proofs",
            "maximum_permitted_claim",
            "limitations",
            "quality_bindings",
        }
    elif payload_type == "authority_cards":
        errors.extend(_authority_card_errors(payload))
        allowed = {
            "drafting_ready",
            "request_handoff_id",
            "request_sha256",
            "claim_set_sha256",
            "claim_bindings",
            "authority_cards",
            "reviewer",
            "review_state",
            "supporting_position_card_ids",
            "adverse_position_card_ids",
            "approval_binding",
            "artifact_manifest",
            "selected_position_set_sha256",
            "selected_proofs",
            "maximum_permitted_claim",
            "limitations",
            "quality_bindings",
        }
    else:
        allowed = set()
    unknown = sorted(set(payload) - allowed)
    if unknown:
        errors.append("Неподдерживаемые поля reviewed payload: " + ", ".join(unknown) + ".")
    return errors


def _read_json_object(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"{path.name} должен содержать JSON-объект.")
    return value


def _read_jsonl_objects(path: Path) -> list[Mapping[str, Any]]:
    records: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, Mapping):
            raise ValueError(f"{path.name}, строка {line_number}, должен содержать объект.")
        records.append(value)
    return records


def _trusted_record_map(
    records: Sequence[Mapping[str, Any]],
    *,
    id_field: str,
    label: str,
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    result: dict[str, Mapping[str, Any]] = {}
    errors: list[str] = []
    for record in records:
        identifier = record.get(id_field)
        if not _is_nonempty(identifier):
            errors.append(f"trusted {label}: запись без {id_field}.")
            continue
        key = str(identifier)
        if key in result:
            errors.append(f"trusted {label}: повторный {id_field} {key}.")
            continue
        result[key] = record
    return result, errors


def _trusted_source_errors(
    envelope: Mapping[str, Any],
    workspace_value: str | Path,
) -> list[str]:
    """Compare a reviewed envelope with independently supplied source-workspace bytes."""

    workspace = Path(workspace_value).expanduser().resolve()
    errors: list[str] = []
    if not workspace.is_dir():
        return [f"trusted source workspace недоступен: {workspace}."]
    payload = envelope["payload"]
    receipt_path = (
        workspace
        / "handoffs"
        / "trusted-results"
        / f"{envelope.get('handoff_id')}.json"
    )
    try:
        receipt = _read_json_object(receipt_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"trusted result receipt не найден или повреждён: {exc}.")
    else:
        expected_receipt = {
            "schema_version": "1.0",
            "handoff_id": envelope.get("handoff_id"),
            "payload_sha256": artifact_sha256(payload),
            "request_handoff_id": payload.get("request_handoff_id"),
            "plan_sha256": envelope.get("plan_sha256"),
            "evidence_sha256": envelope.get("evidence_sha256"),
            "fingerprint_sha256": envelope.get("fingerprint_sha256"),
            "selected_position_set_sha256": payload.get("selected_position_set_sha256"),
            "maximum_permitted_claim": payload.get("maximum_permitted_claim"),
            "quality_artifact_sha256s": sorted(
                str(item.get("artifact_sha256"))
                for item in payload.get("quality_bindings", [])
                if isinstance(item, Mapping) and _is_sha256(item.get("artifact_sha256"))
            ),
            "quality_binding_sha256s": sorted(
                artifact_sha256(item)
                for item in payload.get("quality_bindings", [])
                if isinstance(item, Mapping)
            ),
        }
        if set(receipt) != set(expected_receipt):
            errors.append("trusted result receipt: нарушен закрытый контракт полей.")
        else:
            for key, expected in expected_receipt.items():
                if receipt.get(key) != expected:
                    errors.append(
                        f"trusted result receipt: {key} не совпадает с reviewed result."
                    )
    request_id = payload.get("request_handoff_id")
    request_path = workspace / "handoffs" / "trusted-requests" / f"{request_id}.json"
    try:
        trusted_request = _read_json_object(request_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"trusted request не найден или повреждён: {exc}.")
    else:
        request_check = check_handoff(
            trusted_request,
            expected_target="ksrf-cassation-judicial-meaning",
        )
        if not request_check.get("valid"):
            errors.append("trusted request не прошёл проверку v2.")
        request_payload = trusted_request.get("payload", {})
        if trusted_request.get("handoff_id") != request_id:
            errors.append("trusted request_handoff_id не совпадает с reviewed result.")
        for key in ("request_sha256", "claim_set_sha256", "claim_bindings"):
            if isinstance(request_payload, Mapping) and payload.get(key) != request_payload.get(key):
                errors.append(f"trusted request: {key} не совпадает с reviewed result.")

    selected = payload.get("selected_proofs")
    if not isinstance(selected, Mapping):
        return errors + ["trusted selected_proofs отсутствует."]
    selected_specs = (
        ("position_cards", "position-cards.jsonl", "position_card_id"),
        ("comparisons", "comparability-matrix.jsonl", "position_card_id"),
        ("relations", "applicant-relations.jsonl", "position_card_id"),
    )
    for selected_key, filename, id_field in selected_specs:
        try:
            source_records = _read_jsonl_objects(workspace / filename)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"trusted {filename} не найден или повреждён: {exc}.")
            continue
        source_by_id, record_errors = _trusted_record_map(
            source_records,
            id_field=id_field,
            label=filename,
        )
        errors.extend(record_errors)
        portable_records = selected.get(selected_key)
        portable_by_id, portable_errors = _trusted_record_map(
            portable_records if isinstance(portable_records, list) else [],
            id_field=id_field,
            label=f"portable {selected_key}",
        )
        errors.extend(portable_errors)
        for identifier, portable in portable_by_id.items():
            if source_by_id.get(identifier) != portable:
                errors.append(
                    f"trusted {filename}: содержимое {identifier} не совпадает с source workspace."
                )

    for selected_key, filename in (
        ("adverse", "case-adverse-review.json"),
        ("bridge", "normative-bridge.json"),
        ("human_decision", "human-decision.json"),
        ("validation_report", "validation-report.json"),
    ):
        try:
            source_value = _read_json_object(workspace / filename)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"trusted {filename} не найден или повреждён: {exc}.")
            continue
        if source_value != selected.get(selected_key):
            errors.append(f"trusted {filename} не совпадает с portable proof.")

    quality_bindings = payload.get("quality_bindings")
    if isinstance(quality_bindings, list):
        for binding in quality_bindings:
            if not isinstance(binding, Mapping):
                continue
            quality_type = binding.get("quality_type")
            digest = binding.get("artifact_sha256")
            quality_path = (
                workspace
                / "handoffs"
                / "trusted-quality"
                / f"{quality_type}-{digest}.json"
            )
            try:
                source_quality = _read_json_object(quality_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"trusted quality {quality_type} не найден или повреждён: {exc}.")
                continue
            if source_quality != binding.get("artifact"):
                errors.append(f"trusted quality {quality_type} не совпадает с portable artifact.")
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
    """Create one v2 envelope whose identifier is its canonical digest."""

    for field_name, value in (
        ("source_skill", source_skill),
        ("target_skill", target_skill),
        ("run_id", run_id),
    ):
        if not _is_nonempty(value):
            raise ValueError(f"{field_name} должен быть непустой строкой.")
    if not _is_timestamp(created_at):
        raise ValueError("created_at должен быть ISO 8601 timestamp с часовым поясом.")
    if not _is_sha256(plan_sha256):
        raise ValueError("plan_sha256 должен быть SHA-256.")
    if not _is_sha256(evidence_sha256):
        raise ValueError("evidence_sha256 должен быть SHA-256.")
    if payload_type not in SUPPORTED_PAYLOAD_TYPES:
        if payload_type == "selected_authorities":
            raise ValueError("selected_authorities относится к legacy v1 и доступен только для аудита.")
        raise ValueError(f"Неподдерживаемый payload_type: {payload_type}")
    if not isinstance(payload, Mapping):
        raise ValueError("payload должен быть объектом.")
    if not isinstance(limitations, Sequence) or isinstance(limitations, (str, bytes)):
        raise ValueError("limitations должен быть списком строк.")
    if not all(isinstance(item, str) for item in limitations):
        raise ValueError("limitations должен содержать только строки.")
    if fingerprint_sha256 is not None and not _is_sha256(fingerprint_sha256):
        raise ValueError("fingerprint_sha256 должен быть SHA-256.")
    if payload_type != "unproven_research_questions" and not _is_sha256(
        fingerprint_sha256
    ):
        raise ValueError("Проверенный handoff требует fingerprint_sha256 дела заявителя.")

    payload_copy = json.loads(json.dumps(payload, ensure_ascii=False))
    payload_errors = _payload_errors(
        payload_type,
        payload_copy,
        plan_sha256=plan_sha256,
        evidence_sha256=evidence_sha256,
        fingerprint_sha256=fingerprint_sha256,
        limitations=limitations,
    )
    if payload_errors:
        raise ValueError(" ".join(payload_errors))
    if payload_type != "unproven_research_questions" and not any(
        _is_nonempty(item) for item in limitations
    ):
        raise ValueError("Проверенный handoff требует явные limitations.")

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
        envelope["fingerprint_sha256"] = fingerprint_sha256
    envelope["handoff_id"] = _digest(envelope)
    return envelope


def _result(
    status: str,
    errors: list[str],
    envelope: Mapping[str, Any],
    *,
    audit_readable: bool = True,
) -> dict[str, Any]:
    can_digest = all(key in envelope for key in REQUIRED_FIELDS if key != "handoff_id")
    return {
        "schema_version": SCHEMA_VERSION,
        "envelope_schema_version": envelope.get("schema_version"),
        "valid": status == "valid",
        "audit_readable": audit_readable,
        "status": status,
        "errors": errors,
        "handoff_id": envelope.get("handoff_id"),
        "digest_sha256": _digest(envelope) if can_digest else None,
    }


def check_handoff(
    envelope: Mapping[str, Any],
    *,
    expected_target: str | None = None,
    current_plan_sha256: str | None = None,
    current_evidence_sha256: str | None = None,
    current_fingerprint_sha256: str | None = None,
    current_maximum_permitted_claim: str | None = None,
    trusted_source_workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Validate integrity; reviewed drafting validity additionally requires an external anchor."""

    if not isinstance(envelope, Mapping):
        return {
            "schema_version": SCHEMA_VERSION,
            "envelope_schema_version": None,
            "valid": False,
            "audit_readable": False,
            "status": "invalid",
            "errors": ["Handoff должен быть объектом."],
            "handoff_id": None,
            "digest_sha256": None,
        }
    missing = [field for field in REQUIRED_FIELDS if field not in envelope]
    if missing:
        return _result(
            "invalid",
            [f"Отсутствует поле: {field}" for field in missing],
            envelope,
            audit_readable=False,
        )
    for key in ("plan_sha256", "evidence_sha256"):
        if not _is_sha256(envelope.get(key)):
            return _result("invalid", [f"{key} должен быть SHA-256."], envelope)
    if not _is_sha256(envelope.get("handoff_id")) or envelope.get("handoff_id") != _digest(
        envelope
    ):
        return _result(
            "tampered",
            ["handoff_id не соответствует каноническому содержимому envelope."],
            envelope,
            audit_readable=False,
        )
    version = envelope.get("schema_version")
    if version == LEGACY_SCHEMA_VERSION:
        legacy_type = envelope.get("payload_type")
        extra = [] if legacy_type in LEGACY_PAYLOAD_TYPES else [f"Неизвестный legacy payload_type: {legacy_type}."]
        return _result(
            "legacy_audit_only",
            [
                "Handoff v1 доступен только для аудита и не может использоваться для drafting/import."
            ]
            + extra,
            envelope,
            audit_readable=True,
        )
    if version != SCHEMA_VERSION:
        return _result(
            "incompatible",
            [f"Несовместимая версия handoff: {version}"],
            envelope,
        )
    allowed_envelope_fields = set(REQUIRED_FIELDS) | {"fingerprint_sha256"}
    unknown_envelope_fields = sorted(set(envelope) - allowed_envelope_fields)
    if unknown_envelope_fields:
        return _result(
            "incompatible",
            [
                "Неподдерживаемые поля handoff envelope: "
                + ", ".join(unknown_envelope_fields)
                + "."
            ],
            envelope,
        )
    if not _is_timestamp(envelope.get("created_at")):
        return _result("invalid", ["created_at должен быть ISO 8601 timestamp."], envelope)
    for key in ("source_skill", "target_skill", "run_id"):
        if not _is_nonempty(envelope.get(key)):
            return _result("invalid", [f"{key} должен быть непустой строкой."], envelope)
    if not isinstance(envelope.get("payload"), Mapping):
        return _result("invalid", ["payload должен быть объектом."], envelope)
    limitations = envelope.get("limitations")
    if not isinstance(limitations, list) or not all(isinstance(item, str) for item in limitations):
        return _result("invalid", ["limitations должен быть списком строк."], envelope)
    payload_type = envelope.get("payload_type")
    if payload_type not in SUPPORTED_PAYLOAD_TYPES:
        return _result(
            "incompatible",
            [f"Неподдерживаемый payload_type: {payload_type}"],
            envelope,
        )
    if payload_type != "unproven_research_questions" and not _is_sha256(
        envelope.get("fingerprint_sha256")
    ):
        return _result(
            "incompatible",
            ["Проверенный handoff требует fingerprint_sha256 дела заявителя."],
            envelope,
        )
    payload_errors = _payload_errors(
        str(payload_type),
        envelope["payload"],
        plan_sha256=str(envelope["plan_sha256"]),
        evidence_sha256=str(envelope["evidence_sha256"]),
        fingerprint_sha256=envelope.get("fingerprint_sha256"),
        limitations=limitations,
    )
    if payload_type != "unproven_research_questions" and not any(
        _is_nonempty(item) for item in limitations
    ):
        payload_errors.append("Проверенный handoff требует явные limitations.")
    if payload_errors:
        return _result("incompatible", payload_errors, envelope)
    if payload_type != "unproven_research_questions" and not _is_nonempty(
        expected_target
    ):
        return _result(
            "incompatible",
            [
                "Проверенный receiver handoff требует явный непустой expected_target "
                "до проверки trusted source."
            ],
            envelope,
        )
    if expected_target is not None and envelope.get("target_skill") != expected_target:
        return _result(
            "incompatible",
            [
                "Handoff предназначен для другого target skill: "
                f"{envelope.get('target_skill')} вместо {expected_target}."
            ],
            envelope,
        )

    if payload_type != "unproven_research_questions":
        if trusted_source_workspace is None:
            return _result(
                "audit_only_unanchored",
                [
                    "Portable SHA-256 подтверждает целостность, но не происхождение; "
                    "для drafting/import требуется внешний trusted source workspace."
                ],
                envelope,
                audit_readable=True,
            )
        trusted_errors = _trusted_source_errors(
            envelope,
            trusted_source_workspace,
        )
        if trusted_errors:
            return _result(
                "trusted_source_mismatch",
                trusted_errors,
                envelope,
                audit_readable=True,
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
            ["maximum_permitted_claim handoff не совпадает с текущим пределом вывода."],
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


@contextmanager
def _ledger_lock(ledger_path: Path, *, timeout_seconds: float = 10.0):
    """Serialize cross-process read/modify/replace using an atomic stdlib lockfile."""

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger_path.parent / f".{ledger_path.name}.lock"
    deadline = time.monotonic() + timeout_seconds
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError:
            try:
                stale = time.time() - lock_path.stat().st_mtime > 300
            except FileNotFoundError:
                continue
            if stale:
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Не удалось получить lock inbox ledger: {lock_path}")
            time.sleep(0.01)
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
        os.fsync(descriptor)
        yield
    finally:
        os.close(descriptor)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _append_checked_handoff(
    envelope: Mapping[str, Any],
    target: Path,
    check: Mapping[str, Any],
) -> dict[str, Any]:
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


def import_handoff(
    envelope: Mapping[str, Any],
    ledger_path: str | Path,
    *,
    expected_target: str | None = None,
    current_plan_sha256: str | None = None,
    current_evidence_sha256: str | None = None,
    current_fingerprint_sha256: str | None = None,
    current_maximum_permitted_claim: str | None = None,
    trusted_source_workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Check and atomically add one v2 envelope to an idempotent inbox ledger."""

    check = check_handoff(
        envelope,
        expected_target=expected_target,
        current_plan_sha256=current_plan_sha256,
        current_evidence_sha256=current_evidence_sha256,
        current_fingerprint_sha256=current_fingerprint_sha256,
        current_maximum_permitted_claim=current_maximum_permitted_claim,
        trusted_source_workspace=trusted_source_workspace,
    )
    if not check["valid"]:
        return {**check, "imported": False}

    target = Path(ledger_path)
    with _ledger_lock(target):
        return _append_checked_handoff(envelope, target, check)
