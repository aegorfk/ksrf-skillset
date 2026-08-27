"""Dependency-free quality gates for case-relative practice analysis.

The functions in this module deliberately accept and return JSON-compatible
objects.  They do not read files, use a database, or make network requests, so
the CLI can persist their content-bound results without hiding side effects.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Iterable, Mapping


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
    if not _nonempty(value):
        return False
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _coding_provenance_valid(record: Mapping[str, Any]) -> bool:
    return (
        record.get("human_review") == "approved"
        and record.get("quote_verified") is True
        and record.get("full_text_reviewed") is True
    )


def _coding_reliability_contract_valid(record: Mapping[str, Any]) -> bool:
    evidence_sha256 = record.get("evidence_sha256")
    digest_payload = dict(record)
    digest_payload.pop("evidence_sha256", None)
    if not _is_sha256(evidence_sha256) or canonical_digest(digest_payload) != evidence_sha256:
        return False
    if (
        record.get("schema_version") != SCHEMA_VERSION
        or record.get("complete") is not True
        or record.get("stale") is not False
        or record.get("audit_plan_frozen") is not True
        or record.get("audit_plan_digest_valid") is not True
    ):
        return False
    for field in (
        "audit_plan_sha256",
        "primary_coding_sha256",
        "current_primary_coding_sha256",
    ):
        if not _is_sha256(record.get(field)):
            return False
    if record.get("primary_coding_sha256") != record.get(
        "current_primary_coding_sha256"
    ):
        return False
    required = record.get("required_candidate_ids")
    audited = record.get("audited_candidate_ids")
    if (
        not isinstance(required, list)
        or not required
        or len(required) != len(set(required))
        or not all(_nonempty(identifier) for identifier in required)
        or not isinstance(audited, list)
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
    disagreements = record.get("field_disagreements")
    false_exclusions = record.get("false_exclusion_diagnostics")
    if not isinstance(disagreements, list) or not all(
        isinstance(item, Mapping) and item.get("resolved") is True
        for item in disagreements
    ):
        return False
    if not isinstance(false_exclusions, list) or not all(
        isinstance(item, Mapping) and item.get("resolved") is True
        for item in false_exclusions
    ):
        return False
    return True


TREATMENT_SOURCE_FIELDS = (
    "document_id",
    "document_sha256",
    "official_url",
    "quote",
    "quote_locator",
    "proposition",
)


def _treatment_reference(treatment: Mapping[str, Any]) -> str:
    treatment_id = treatment.get("treatment_id")
    if _nonempty(treatment_id):
        return " ".join(str(treatment_id).split())
    return f"unidentified-{canonical_digest(dict(treatment))[:16]}"


def _malformed_treatment_reference(treatment: Any) -> str:
    return f"malformed-{canonical_digest(treatment)[:16]}"


def _treatment_has_reviewed_source(treatment: Mapping[str, Any]) -> bool:
    source_payload = {field: treatment.get(field) for field in TREATMENT_SOURCE_FIELDS}
    source_bound = (
        _nonempty(treatment.get("document_id"))
        and _is_sha256(treatment.get("document_sha256"))
        and _nonempty(treatment.get("official_url"))
        and re.match(r"^https?://", str(treatment.get("official_url"))) is not None
        and _nonempty(treatment.get("quote"))
        and _nonempty(treatment.get("quote_locator"))
        and _nonempty(treatment.get("proposition"))
        and _is_sha256(treatment.get("source_binding_sha256"))
        and treatment.get("source_binding_sha256") == canonical_digest(source_payload)
    )
    return (
        source_bound
        and _nonempty(treatment.get("treatment_id"))
        and _nonempty(treatment.get("reviewer"))
        and _valid_iso(treatment.get("reviewed_at"))
        and treatment.get("human_review") == "approved"
        and treatment.get("quote_verified") is True
        and treatment.get("full_text_reviewed") is True
    )


def _classify_treatments(
    treatments: Iterable[Any],
    *,
    final_reviewed_at: str | None = None,
) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    pending: set[str] = set()
    verified: set[str] = set()
    rejected: set[str] = set()
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

    final_time = (
        datetime.fromisoformat(final_reviewed_at.replace("Z", "+00:00"))
        if final_reviewed_at is not None
        else None
    )
    for reference, records in sorted(grouped.items()):
        statuses = {record.get("status") for record in records}
        source_bindings = {record.get("source_binding_sha256") for record in records}
        if len(statuses) != 1 or len(source_bindings) != 1:
            pending.add(reference)
            invalid_resolved.add(reference)
            continue
        status = next(iter(statuses))
        if status not in {"verified", "rejected"}:
            pending.add(reference)
            continue
        if not all(_treatment_has_reviewed_source(record) for record in records):
            pending.add(reference)
            invalid_resolved.add(reference)
            continue
        if final_time is not None:
            chronology_valid = True
            for record in records:
                treatment_time = datetime.fromisoformat(
                    str(record["reviewed_at"]).replace("Z", "+00:00")
                )
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
        else:
            rejected.add(reference)

    if pending & verified or pending & rejected or verified & rejected:
        raise AssertionError("treatment resolution partitions must be disjoint")
    return (
        sorted(pending),
        sorted(verified),
        sorted(rejected),
        sorted(invalid_resolved),
        sorted(chronology_issues),
    )


def _candidate_id(value: Mapping[str, Any]) -> str | None:
    candidate_id = value.get("candidate_id")
    if _nonempty(candidate_id):
        return " ".join(str(candidate_id).split())
    chain_id = value.get("chain_id")
    document_id = value.get("document_id")
    if _nonempty(chain_id) and _nonempty(document_id):
        return f"{str(chain_id).strip()}::{str(document_id).strip()}"
    return None


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
                f"{record_kind}-record-{row_number}-{canonical_digest(value)[:16]}"
            )
            continue
        identifier = _candidate_id(value)
        if identifier is None:
            invalid_records.append(
                f"{record_kind}-record-{row_number}-{canonical_digest(dict(value))[:16]}"
            )
            continue
        if identifier in indexed:
            duplicates.append(identifier)
        else:
            indexed[identifier] = dict(value)
    return indexed, sorted(set(duplicates)), sorted(set(invalid_records))


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
            evidence_refs=[*pending_treatments, *verified_treatments, *rejected_treatments],
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

    if coding_reliability is None:
        reliability_dimension = _dimension(
            "not_assessed",
            unknowns=["coding_reliability_missing"],
            claim_effect="Надёжность кодирования не проверена независимой выборкой.",
            review_complete=False,
        )
    else:
        unresolved_coding = coding_reliability.get("unresolved_candidate_ids", [])
        if not isinstance(unresolved_coding, list):
            unresolved_coding = ["invalid_reliability_contract"]
        reliability_usable = _coding_reliability_contract_valid(coding_reliability)
        if not reliability_usable and not unresolved_coding:
            unresolved_coding = ["invalid_or_unbound_reliability_contract"]
        reliability_dimension = _dimension(
            (
                "independent_audit_complete"
                if reliability_usable
                else "unresolved_coding_reliability"
            ),
            evidence_refs=[coding_reliability.get("audit_plan_sha256")],
            unknowns=unresolved_coding,
            claim_effect=(
                "Независимая выборка проверена; это не превращает кодирование в безошибочное."
                if reliability_usable
                else "Неразрешённые расхождения кодировщиков ограничивают или блокируют вывод."
            ),
            review_complete=reliability_usable,
            assessed=True,
            usable_for_claim=reliability_usable,
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
    }
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
        "input_sha256s": {
            key: canonical_digest(value) for key, value in sorted(input_payload.items())
        },
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

    if not _nonempty(plan_sha256):
        raise ValueError("plan_sha256 is required")
    if sample_size < 0 or exclusion_sample_size < 0:
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
    sorted_primary_records = sorted(primary_records, key=canonical_digest)
    sorted_audit_records = sorted(audit_records, key=canonical_digest)
    sorted_adjudication_records = sorted(adjudication_records, key=canonical_digest)
    primary, duplicate_primary, current_invalid_primary_ids = _index_unique(
        sorted_primary_records,
        record_kind="primary",
    )
    audits, duplicate_audits, invalid_audit_record_ids = _index_unique(
        sorted_audit_records,
        record_kind="audit",
    )
    (
        adjudication_map,
        duplicate_adjudications,
        invalid_adjudication_record_ids,
    ) = _index_unique(
        sorted_adjudication_records,
        record_kind="adjudication",
    )
    required = sorted(set(_unique_strings(audit_plan.get("required_candidate_ids", []))))
    current_primary_sha256 = canonical_digest(sorted_primary_records)
    plan_payload = {
        key: value for key, value in audit_plan.items() if key != "audit_plan_sha256"
    }
    plan_digest_valid = audit_plan.get("audit_plan_sha256") == canonical_digest(plan_payload)
    plan_frozen = audit_plan.get("frozen") is True

    def plan_invalid_ids(field: str) -> list[str]:
        value = audit_plan.get(field)
        if not isinstance(value, list) or not all(_nonempty(item) for item in value):
            return [f"audit-plan-{field}-invalid"]
        return sorted(set(_unique_strings(value)))

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

    if stale:
        unresolved.update(required)
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
        primary_sha256 = canonical_digest(primary_record)
        secondary = audit.get("secondary_coding")
        if not isinstance(secondary, Mapping):
            invalid_binding_ids.append(identifier)
            unresolved.add(identifier)
            continue
        secondary_record = dict(secondary)
        secondary_sha256 = canonical_digest(secondary_record)
        if (
            audit.get("primary_coding_sha256") != primary_sha256
            or audit.get("secondary_coding_sha256") != secondary_sha256
        ):
            invalid_binding_ids.append(identifier)
            unresolved.add(identifier)
            continue
        if not _coding_provenance_valid(primary_record) or not _coding_provenance_valid(
            secondary_record
        ):
            invalid_provenance_ids.append(identifier)
            unresolved.add(identifier)
        primary_coder = primary_record.get("coder")
        secondary_coder = secondary_record.get("coder")
        if not _nonempty(primary_coder) or not _nonempty(secondary_coder) or (
            str(primary_coder).strip() == str(secondary_coder).strip()
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
                resolved_fields = adjudication.get("resolved_fields")
                adjudicator = adjudication.get("adjudicator")
                adjudication_valid = (
                    adjudication.get("primary_coding_sha256") == primary_sha256
                    and adjudication.get("secondary_coding_sha256") == secondary_sha256
                    and isinstance(resolved_fields, Mapping)
                    and set(differing_fields).issubset(resolved_fields)
                    and _nonempty(adjudicator)
                    and str(adjudicator).strip()
                    not in {str(primary_coder).strip(), str(secondary_coder).strip()}
                    and adjudication.get("human_review") == "approved"
                    and _valid_iso(adjudication.get("reviewed_at"))
                )
                if adjudication_valid:
                    disagreement["resolved"] = True
                    disagreement["adjudication_sha256"] = canonical_digest(adjudication)
                else:
                    invalid_binding_ids.append(identifier)
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

    unresolved.update(duplicate_primary)
    unresolved.update(invalid_binding_ids)
    unresolved.update(invalid_provenance_ids)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "audit_plan_sha256": audit_plan.get("audit_plan_sha256"),
        "audit_plan_frozen": plan_frozen,
        "audit_plan_digest_valid": plan_digest_valid,
        "primary_coding_sha256": audit_plan.get("primary_coding_sha256"),
        "current_primary_coding_sha256": current_primary_sha256,
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
    return {**payload, "evidence_sha256": canonical_digest(payload)}


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
) -> dict[str, Any]:
    """Assess a bounded pre-filing refresh, including unresolved treatments."""

    for field, value in (
        ("baseline_corpus_digest", baseline_corpus_digest),
        ("current_corpus_digest", current_corpus_digest),
    ):
        if not _is_sha256(value):
            raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    if not _nonempty(reviewer):
        raise ValueError("reviewer is required")
    if not _valid_iso(reviewed_at):
        raise ValueError("reviewed_at must be an ISO timestamp")
    if not _valid_iso(checked_through) or not _valid_iso(filing_cutoff):
        raise ValueError("checked_through and filing_cutoff must be ISO timestamps")

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

    raw_gaps = refresh_plan.get("coverage_gaps", [])
    gaps: list[dict[str, Any]] = []
    malformed_coverage_gap_ids: list[str] = []
    if isinstance(raw_gaps, list):
        for index, item in enumerate(raw_gaps, start=1):
            if isinstance(item, Mapping) and _nonempty(item.get("reason")):
                gaps.append(dict(item))
            else:
                malformed_coverage_gap_ids.append(
                    f"coverage-gap-{index}-{canonical_digest(item)[:12]}"
                )
    else:
        malformed_coverage_gap_ids.append(
            f"coverage-gaps-container-{canonical_digest(raw_gaps)[:12]}"
        )
    treatment_list = [
        dict(item) if isinstance(item, Mapping) else item for item in treatments
    ]
    treatment_digest_records = sorted(treatment_list, key=canonical_digest)
    (
        pending_treatment_ids,
        verified_treatment_ids,
        rejected_treatment_ids,
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
    claims = sorted(set(_unique_strings(claim_ids)))
    reasons: list[str] = []
    material_change = baseline_corpus_digest != current_corpus_digest
    checked_time = datetime.fromisoformat(checked_through.replace("Z", "+00:00"))
    cutoff_time = datetime.fromisoformat(filing_cutoff.replace("Z", "+00:00"))
    reviewed_time = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    timezone_mismatch = (checked_time.utcoffset() is None) != (
        cutoff_time.utcoffset() is None
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
    elif malformed_refresh_entry_ids or malformed_coverage_gap_ids:
        status = "refresh_incomplete"
        if malformed_refresh_entry_ids:
            reasons.append("malformed_refresh_plan_entries")
        if malformed_coverage_gap_ids:
            reasons.append("malformed_coverage_gaps")
    elif stale_seed_ids:
        status = "refresh_incomplete"
        reasons.append("stale_or_unfetched_public_seeds")
    elif pending_treatment_ids:
        status = "refresh_incomplete"
        reasons.append("pending_treatment_review")
        if invalid_resolved_treatment_ids:
            reasons.append("resolved_treatment_lacks_content_bound_human_review")
        if treatment_chronology_issue_ids:
            reasons.append("treatment_review_chronology_invalid")
    elif timezone_mismatch:
        status = "refresh_incomplete"
        reasons.append("timestamp_timezone_mismatch")
    elif reviewed_timezone_mismatch:
        status = "refresh_incomplete"
        reasons.append("reviewed_at_timezone_mismatch")
    elif not reviewed_after_check:
        status = "refresh_incomplete"
        reasons.append("reviewed_at_before_checked_through")
    elif not timing_valid:
        status = "refresh_incomplete"
        reasons.append("checked_through_before_filing_cutoff")
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
    plan_payload = dict(refresh_plan)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "baseline_corpus_digest": baseline_corpus_digest,
        "current_corpus_digest": current_corpus_digest,
        "subject_evidence_sha256": subject_evidence_sha256,
        "refresh_plan_id": refresh_plan.get("plan_id"),
        "refresh_plan_sha256": canonical_digest(plan_payload),
        "checked_through": checked_through,
        "filing_cutoff": filing_cutoff,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "claim_ids": claims,
        "affected_claim_ids": affected_claim_ids,
        "treatments_sha256": canonical_digest(treatment_digest_records),
        "pending_treatment_ids": pending_treatment_ids,
        "verified_treatment_ids": verified_treatment_ids,
        "rejected_treatment_ids": rejected_treatment_ids,
        "treatment_chronology_issue_ids": treatment_chronology_issue_ids,
        "stale_seed_ids": stale_seed_ids,
        "malformed_refresh_entry_ids": malformed_refresh_entry_ids,
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
    "AUDITED_CODING_FIELDS",
    "CHAIN_STAGES",
    "CHAIN_TREATMENTS",
    "UNCERTAINTY_DIMENSIONS",
    "analyze_chain_stage_propagation",
    "assess_coding_reliability",
    "assess_prefiling_refresh",
    "build_coding_audit_plan",
    "build_uncertainty_profile",
    "canonical_digest",
]
