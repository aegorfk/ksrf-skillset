"""Fail-closed contracts for an evidence-bound KSRF admissibility route.

The module validates research supplied by a human or another evidence workflow.
It does not infer legal facts, fetch sources, score merit, approve a complaint,
or perform filing.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any, Iterable, Mapping

from .storage import stable_id


SCHEMA_VERSION = "1.0.0"
MATRIX_SCHEMA = (
    "https://example.local/schemas/ksrf_filing/"
    "admissibility-matrix.v1.schema.json"
)
RECOMMENDATION_SCHEMA = (
    "https://example.local/schemas/ksrf_filing/"
    "ksrf-route-recommendation.v1.schema.json"
)
CANONICAL_GATE_IDS = (
    "competence_and_route",
    "applicant_and_subjective_interest",
    "case_status",
    "challenged_norm_version",
    "application_or_meaning",
    "causation_and_rights_harm",
    "exhaustion_and_preservation",
    "one_year_deadline",
    "continuing_legal_effect",
    "anti_appeal_boundary",
    "prior_ksrf_authority_delta",
    "permissible_remedy",
)
GATE_STATUSES = frozenset({"pass", "fail", "unknown", "not_applicable"})
CURABILITY_STATES = frozenset(
    {"curable", "incurable", "unknown", "not_applicable"}
)
RECORD_AVAILABILITY_STATES = frozenset(
    {
        "available",
        "controlled_retrieval",
        "unavailable_after_exhaustive_search",
        "not_applicable",
    }
)
OFFICIAL_SNAPSHOT_STATES = frozenset(
    {"verified_current", "missing", "stale", "unavailable_after_search"}
)
ROUTE_DECISIONS = frozenset(
    {
        "GO_TO_KSRF",
        "FIX_FIRST",
        "COURT_REQUEST_ROUTE",
        "NO_GO_KSRF",
        "ABSTAIN_PENDING_RECORD",
    }
)
_MATRIX_FIELDS = frozenset(
    {
        "$schema",
        "schema_version",
        "artifact_type",
        "matrix_id",
        "matter_id",
        "claim_id",
        "official_rule_snapshot",
        "gates",
        "route_context",
    }
)
_SNAPSHOT_FIELDS = frozenset({"status", "checked_at", "evidence_ids"})
_GATE_FIELDS = frozenset(
    {
        "gate_id",
        "status",
        "rationale",
        "applicability_reason",
        "evidence_ids",
        "official_rule_evidence_ids",
        "official_checked_at",
        "curability",
        "record_availability",
        "next_action",
        "disposition",
    }
)
_ROUTE_CONTEXT_FIELDS = frozenset(
    {
        "issue_assessment_status",
        "option_bindings",
        "preferred_option_id",
        "reserve_option_ids",
        "expected_client_benefit",
        "adverse_risks",
        "alternatives_and_deadlines",
        "next_actions_in_order",
        "reconsideration_conditions",
    }
)
_OPTION_BINDING_FIELDS = frozenset(
    {"option_id", "content_fingerprint", "readiness", "evidence_ids"}
)
_ISSUE_FINGERPRINT_RE = re.compile(
    r"^issue-candidate-content:sha256:[0-9a-f]{64}$"
)


class AdmissibilityContractError(ValueError):
    """The matrix cannot safely participate in route derivation."""


def _mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissibilityContractError(f"{label}: ожидается JSON-объект.")
    return dict(value)


def _exact_fields(value: Mapping[str, Any], expected: frozenset[str], *, label: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise AdmissibilityContractError(
            f"{label}: отсутствуют поля {', '.join(missing)}."
        )
    if extra:
        raise AdmissibilityContractError(
            f"{label}: неизвестные поля {', '.join(extra)}."
        )


def _text(value: Any, *, label: str, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise AdmissibilityContractError(f"{label}: требуется непустая строка.")
    return value.strip()


def _strings(
    value: Any,
    *,
    label: str,
    minimum: int = 0,
) -> list[str]:
    if not isinstance(value, list):
        raise AdmissibilityContractError(f"{label}: ожидается массив строк.")
    normalized = [_text(item, label=f"{label}[]") for item in value]
    strings = [str(item) for item in normalized]
    if len(strings) < minimum:
        raise AdmissibilityContractError(
            f"{label}: требуется не менее {minimum} значений."
        )
    if len(set(strings)) != len(strings):
        raise AdmissibilityContractError(f"{label}: значения не должны повторяться.")
    return strings


def _checked_at(value: Any, *, label: str) -> str:
    checked_at = _text(value, label=label)
    assert checked_at is not None
    try:
        parsed = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdmissibilityContractError(
            f"{label}: требуется дата и время RFC 3339."
        ) from exc
    if parsed.tzinfo is None:
        raise AdmissibilityContractError(
            f"{label}: требуется явный часовой пояс."
        )
    if parsed.astimezone(timezone.utc) > datetime.now(timezone.utc):
        raise AdmissibilityContractError(
            f"{label}: дата официальной проверки не может быть в будущем."
        )
    return checked_at


def _enum(value: Any, allowed: frozenset[str], *, label: str) -> str:
    normalized = _text(value, label=label)
    assert normalized is not None
    if normalized not in allowed:
        raise AdmissibilityContractError(
            f"{label}: недопустимое значение {normalized}."
        )
    return normalized


def _validate_snapshot(value: Any) -> dict[str, Any]:
    snapshot = _mapping(value, label="official_rule_snapshot")
    _exact_fields(snapshot, _SNAPSHOT_FIELDS, label="official_rule_snapshot")
    status = _enum(
        snapshot["status"],
        OFFICIAL_SNAPSHOT_STATES,
        label="official_rule_snapshot.status",
    )
    evidence_ids = _strings(
        snapshot["evidence_ids"],
        label="official_rule_snapshot.evidence_ids",
        minimum=1 if status == "verified_current" else 0,
    )
    return {
        "status": status,
        "checked_at": _checked_at(
            snapshot["checked_at"],
            label="official_rule_snapshot.checked_at",
        ),
        "evidence_ids": evidence_ids,
    }


def _validate_gate(
    value: Any,
    *,
    snapshot: Mapping[str, Any],
    index: int,
) -> dict[str, Any]:
    label = f"gates[{index}]"
    gate = _mapping(value, label=label)
    _exact_fields(gate, _GATE_FIELDS, label=label)
    gate_id = _text(gate["gate_id"], label=f"{label}.gate_id")
    assert gate_id is not None
    if gate_id not in CANONICAL_GATE_IDS:
        raise AdmissibilityContractError(
            f"{label}.gate_id: неизвестный порог {gate_id}."
        )
    status = _enum(gate["status"], GATE_STATUSES, label=f"{label}.status")
    rationale = _text(gate["rationale"], label=f"{label}.rationale")
    applicability_reason = _text(
        gate["applicability_reason"],
        label=f"{label}.applicability_reason",
    )
    evidence_ids = _strings(
        gate["evidence_ids"], label=f"{label}.evidence_ids", minimum=1
    )
    official_ids = _strings(
        gate["official_rule_evidence_ids"],
        label=f"{label}.official_rule_evidence_ids",
    )
    snapshot_ids = set(snapshot["evidence_ids"])
    if not set(official_ids).issubset(snapshot_ids):
        raise AdmissibilityContractError(
            f"{label}.official_rule_evidence_ids: ссылка отсутствует в official_rule_snapshot."
        )
    if snapshot["status"] == "verified_current" and not official_ids:
        raise AdmissibilityContractError(
            f"{label}.official_rule_evidence_ids: для текущего правила нужна официальная опора."
        )
    official_checked_at = _checked_at(
        gate["official_checked_at"],
        label=f"{label}.official_checked_at",
    )
    curability = _enum(
        gate["curability"], CURABILITY_STATES, label=f"{label}.curability"
    )
    record_availability = _enum(
        gate["record_availability"],
        RECORD_AVAILABILITY_STATES,
        label=f"{label}.record_availability",
    )
    next_action = _text(
        gate["next_action"], label=f"{label}.next_action", nullable=True
    )
    disposition = _text(
        gate["disposition"], label=f"{label}.disposition", nullable=True
    )

    if status == "pass":
        if curability != "not_applicable" or record_availability != "available":
            raise AdmissibilityContractError(
                f"{label}: pass требует curability=not_applicable и record_availability=available."
            )
    elif status == "fail":
        if curability not in {"curable", "incurable"} or next_action is None:
            raise AdmissibilityContractError(
                f"{label}: fail требует устранимость и конкретный следующий шаг."
            )
    elif status == "unknown":
        if curability not in {"curable", "unknown"} or next_action is None:
            raise AdmissibilityContractError(
                f"{label}: unknown требует честную устранимость и следующий шаг."
            )
        if record_availability == "not_applicable":
            raise AdmissibilityContractError(
                f"{label}: unknown не совместим с record_availability=not_applicable."
            )
    else:
        if (
            curability != "not_applicable"
            or record_availability != "not_applicable"
            or next_action is not None
            or not official_ids
        ):
            raise AdmissibilityContractError(
                f"{label}: not_applicable требует официальную опору, причину и пустой следующий шаг."
            )

    if gate_id == "competence_and_route":
        allowed = {
            "individual_complaint",
            "court_request",
            "ordinary_process",
            "none",
            "unknown",
        }
        if disposition not in allowed:
            raise AdmissibilityContractError(
                f"{label}.disposition: требуется доказанный вид текущего маршрута."
            )
        expected = {
            "individual_complaint": ("pass", "not_applicable"),
            "court_request": ("pass", "not_applicable"),
            "ordinary_process": ("fail", "curable"),
            "none": ("fail", "incurable"),
            "unknown": ("unknown", curability),
        }[disposition]
        if status != expected[0] or (
            disposition != "unknown" and curability != expected[1]
        ):
            raise AdmissibilityContractError(
                f"{label}: disposition маршрута не согласован со status/curability."
            )
    elif gate_id == "case_status":
        if disposition not in {"completed", "active", "unknown"}:
            raise AdmissibilityContractError(
                f"{label}.disposition: требуется completed, active или unknown."
            )
        if (disposition == "unknown") != (status == "unknown"):
            raise AdmissibilityContractError(
                f"{label}: disposition дела не согласован со status."
            )
        if disposition in {"completed", "active"} and status != "pass":
            raise AdmissibilityContractError(
                f"{label}: подтверждённый статус дела требует pass."
            )
    elif gate_id == "permissible_remedy":
        if disposition not in {"viable", "not_viable", "unknown"}:
            raise AdmissibilityContractError(
                f"{label}.disposition: требуется viable, not_viable или unknown."
            )
        consistent = (
            (disposition == "viable" and status == "pass")
            or (
                disposition == "not_viable"
                and status == "fail"
                and curability == "incurable"
            )
            or (disposition == "unknown" and status == "unknown")
        )
        if not consistent:
            raise AdmissibilityContractError(
                f"{label}: disposition способа защиты не согласован со status/curability."
            )
    elif disposition is not None:
        raise AdmissibilityContractError(
            f"{label}.disposition: для этого порога значение должно быть null."
        )

    return {
        "gate_id": gate_id,
        "status": status,
        "rationale": rationale,
        "applicability_reason": applicability_reason,
        "evidence_ids": evidence_ids,
        "official_rule_evidence_ids": official_ids,
        "official_checked_at": official_checked_at,
        "curability": curability,
        "record_availability": record_availability,
        "next_action": next_action,
        "disposition": disposition,
    }


def _validate_route_context(value: Any) -> dict[str, Any]:
    context = _mapping(value, label="route_context")
    _exact_fields(context, _ROUTE_CONTEXT_FIELDS, label="route_context")
    issue_status = _enum(
        context["issue_assessment_status"],
        frozenset({"complete", "incomplete", "not_started"}),
        label="route_context.issue_assessment_status",
    )
    raw_bindings = context["option_bindings"]
    if not isinstance(raw_bindings, list):
        raise AdmissibilityContractError(
            "route_context.option_bindings: ожидается массив."
        )
    bindings: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_bindings):
        label = f"route_context.option_bindings[{index}]"
        binding = _mapping(raw, label=label)
        _exact_fields(binding, _OPTION_BINDING_FIELDS, label=label)
        fingerprint = _text(
            binding["content_fingerprint"], label=f"{label}.content_fingerprint"
        )
        assert fingerprint is not None
        if _ISSUE_FINGERPRINT_RE.fullmatch(fingerprint) is None:
            raise AdmissibilityContractError(
                f"{label}.content_fingerprint: требуется штатный "
                "issue-candidate-content:sha256:<64 lowercase hex>."
            )
        bindings.append(
            {
                "option_id": _text(binding["option_id"], label=f"{label}.option_id"),
                "content_fingerprint": fingerprint,
                "readiness": _enum(
                    binding["readiness"],
                    frozenset({"viable", "conditional", "rejected"}),
                    label=f"{label}.readiness",
                ),
                "evidence_ids": _strings(
                    binding["evidence_ids"],
                    label=f"{label}.evidence_ids",
                    minimum=1,
                ),
            }
        )
    option_ids = [str(binding["option_id"]) for binding in bindings]
    if len(set(option_ids)) != len(option_ids):
        raise AdmissibilityContractError(
            "route_context.option_bindings: option_id не должны повторяться."
        )
    fingerprints = [str(binding["content_fingerprint"]) for binding in bindings]
    if len(set(fingerprints)) != len(fingerprints):
        raise AdmissibilityContractError(
            "route_context.option_bindings: fingerprints не должны повторяться."
        )
    preferred = _text(
        context["preferred_option_id"],
        label="route_context.preferred_option_id",
        nullable=True,
    )
    reserve = _strings(
        context["reserve_option_ids"], label="route_context.reserve_option_ids"
    )
    by_id = {str(binding["option_id"]): binding for binding in bindings}
    viable_ids = {
        option_id
        for option_id, binding in by_id.items()
        if binding["readiness"] == "viable"
    }
    selectable_ids = {
        option_id
        for option_id, binding in by_id.items()
        if binding["readiness"] in {"viable", "conditional"}
    }
    if preferred is not None and preferred not in viable_ids:
        raise AdmissibilityContractError(
            "route_context.preferred_option_id: требуется exact viable option binding."
        )
    if not set(reserve).issubset(selectable_ids) or preferred in reserve:
        raise AdmissibilityContractError(
            "route_context.reserve_option_ids: резерв должен ссылаться на отдельные bound options."
        )
    if issue_status != "complete" and (bindings or preferred is not None or reserve):
        raise AdmissibilityContractError(
            "route_context: незавершённое исследование не может объявлять option bindings."
        )
    return {
        "issue_assessment_status": issue_status,
        "option_bindings": bindings,
        "preferred_option_id": preferred,
        "reserve_option_ids": reserve,
        "expected_client_benefit": _text(
            context["expected_client_benefit"],
            label="route_context.expected_client_benefit",
        ),
        "adverse_risks": _strings(
            context["adverse_risks"],
            label="route_context.adverse_risks",
            minimum=1,
        ),
        "alternatives_and_deadlines": _strings(
            context["alternatives_and_deadlines"],
            label="route_context.alternatives_and_deadlines",
            minimum=1,
        ),
        "next_actions_in_order": _strings(
            context["next_actions_in_order"],
            label="route_context.next_actions_in_order",
            minimum=1,
        ),
        "reconsideration_conditions": _strings(
            context["reconsideration_conditions"],
            label="route_context.reconsideration_conditions",
            minimum=1,
        ),
    }


def validate_admissibility_matrix(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a canonical matrix or raise an exact fail-closed contract error."""

    matrix = _mapping(payload, label="AdmissibilityMatrix")
    _exact_fields(matrix, _MATRIX_FIELDS, label="AdmissibilityMatrix")
    if matrix["$schema"] != MATRIX_SCHEMA:
        raise AdmissibilityContractError("AdmissibilityMatrix.$schema: неизвестная схема.")
    if matrix["schema_version"] != SCHEMA_VERSION:
        raise AdmissibilityContractError(
            "AdmissibilityMatrix.schema_version: поддерживается только 1.0.0."
        )
    if matrix["artifact_type"] != "AdmissibilityMatrix":
        raise AdmissibilityContractError(
            "AdmissibilityMatrix.artifact_type: требуется AdmissibilityMatrix."
        )
    snapshot = _validate_snapshot(matrix["official_rule_snapshot"])
    raw_gates = matrix["gates"]
    if not isinstance(raw_gates, list):
        raise AdmissibilityContractError("gates: ожидается массив из двенадцати порогов.")
    gates = [
        _validate_gate(gate, snapshot=snapshot, index=index)
        for index, gate in enumerate(raw_gates)
    ]
    gate_ids = [gate["gate_id"] for gate in gates]
    duplicates = sorted({gate_id for gate_id in gate_ids if gate_ids.count(gate_id) > 1})
    missing = sorted(set(CANONICAL_GATE_IDS) - set(gate_ids))
    if duplicates or missing or len(gates) != len(CANONICAL_GATE_IDS):
        details: list[str] = []
        if duplicates:
            details.append(f"дублируется: {', '.join(duplicates)}")
        if missing:
            details.append(f"отсутствует: {', '.join(missing)}")
        raise AdmissibilityContractError(
            "gates: каждый из 12 порогов нужен ровно один раз; " + "; ".join(details)
        )
    by_id = {str(gate["gate_id"]): gate for gate in gates}
    if (
        by_id["competence_and_route"]["disposition"] == "court_request"
        and by_id["case_status"]["disposition"] != "active"
    ):
        raise AdmissibilityContractError(
            "gates: court_request требует evidence-bound case_status=active."
        )
    if (
        by_id["competence_and_route"]["disposition"] == "individual_complaint"
        and by_id["case_status"]["disposition"] != "completed"
    ):
        raise AdmissibilityContractError(
            "gates: individual_complaint требует evidence-bound case_status=completed."
        )
    normalized = {
        "$schema": MATRIX_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "AdmissibilityMatrix",
        "matrix_id": _text(matrix["matrix_id"], label="matrix_id"),
        "matter_id": _text(matrix["matter_id"], label="matter_id"),
        "claim_id": _text(matrix["claim_id"], label="claim_id"),
        "official_rule_snapshot": snapshot,
        "gates": [by_id[gate_id] for gate_id in CANONICAL_GATE_IDS],
        "route_context": _validate_route_context(matrix["route_context"]),
    }
    return json.loads(json.dumps(normalized, ensure_ascii=False))


def official_rule_evidence_ids(matrix: Mapping[str, Any]) -> tuple[str, ...]:
    """Return every official evidence ID declared by a valid matrix."""

    normalized = validate_admissibility_matrix(matrix)
    identifiers = set(normalized["official_rule_snapshot"]["evidence_ids"])
    for gate in normalized["gates"]:
        identifiers.update(gate["official_rule_evidence_ids"])
    return tuple(sorted(identifiers))


def derive_route_recommendation(
    matrix: Mapping[str, Any],
    *,
    current_official_evidence_ids: Iterable[str],
    current_issue_binding_blockers: Iterable[str] = (),
) -> dict[str, Any]:
    """Derive one planning route from already assessed gates, never legal truth."""

    normalized = validate_admissibility_matrix(matrix)
    gates = normalized["gates"]
    gates_by_id = {str(gate["gate_id"]): gate for gate in gates}
    context = normalized["route_context"]
    snapshot = normalized["official_rule_snapshot"]
    matrix_revision_id = stable_id("admissibility-matrix-revision", normalized)
    current_ids = {
        str(value).strip()
        for value in current_official_evidence_ids
        if str(value).strip()
    }
    required_official_ids = set(official_rule_evidence_ids(normalized))
    missing_official_ids = required_official_ids - current_ids
    issue_binding_blockers = sorted(
        {
            str(value).strip()
            for value in current_issue_binding_blockers
            if str(value).strip()
        }
    )
    blocker_codes: list[str] = []
    decisive_gate_ids: set[str] = set()

    incurable = [
        gate
        for gate in gates
        if gate["status"] == "fail" and gate["curability"] == "incurable"
    ]
    unavailable = [
        gate
        for gate in gates
        if gate["status"] == "unknown"
        and gate["record_availability"]
        == "unavailable_after_exhaustive_search"
    ]
    curable_failures = [
        gate
        for gate in gates
        if gate["status"] == "fail" and gate["curability"] == "curable"
    ]
    controlled_unknowns = [
        gate
        for gate in gates
        if gate["status"] == "unknown"
        and gate["curability"] == "curable"
        and gate["record_availability"]
        in {"available", "controlled_retrieval"}
    ]
    controlled = curable_failures + controlled_unknowns
    residual_unknown = [
        gate
        for gate in gates
        if gate["status"] == "unknown"
        and gate not in unavailable
        and gate not in controlled
    ]
    for code, affected in (
        ("incurable_admissibility_failure", incurable),
        ("critical_record_unavailable", unavailable),
        ("controlled_gap_requires_action", controlled),
        ("unresolved_admissibility_unknown", residual_unknown),
    ):
        if affected:
            blocker_codes.append(code)
            decisive_gate_ids.update(str(gate["gate_id"]) for gate in affected)

    unresolved_authority = (
        snapshot["status"] != "verified_current"
        or bool(missing_official_ids)
    )
    unresolved_issue_binding = bool(issue_binding_blockers)
    if unresolved_authority or unresolved_issue_binding:
        if unresolved_authority:
            blocker_codes.append("official_authority_unverified")
            blocker_codes.extend(
                f"official_authority_unverified:{evidence_id}"
                for evidence_id in sorted(missing_official_ids)
            )
            if snapshot["status"] != "verified_current":
                blocker_codes.append(f"official_snapshot_{snapshot['status']}")
                decisive_gate_ids.update(str(gate["gate_id"]) for gate in gates)
            else:
                affected_by_missing_authority = [
                    gate
                    for gate in gates
                    if set(gate["official_rule_evidence_ids"])
                    & missing_official_ids
                ]
                if affected_by_missing_authority:
                    decisive_gate_ids.update(
                        str(gate["gate_id"])
                        for gate in affected_by_missing_authority
                    )
                else:
                    # A snapshot-level source is part of the common authority
                    # basis even when no individual row repeats its identifier.
                    decisive_gate_ids.update(str(gate["gate_id"]) for gate in gates)
        if unresolved_issue_binding:
            blocker_codes.append("issue_binding_unverified")
            blocker_codes.extend(issue_binding_blockers)
        decision = "ABSTAIN_PENDING_RECORD"
    else:
        if unavailable:
            decision = "ABSTAIN_PENDING_RECORD"
        elif residual_unknown:
            decision = "ABSTAIN_PENDING_RECORD"
        elif controlled_unknowns:
            decision = "FIX_FIRST"
        elif incurable:
            decision = "NO_GO_KSRF"
        elif curable_failures:
            decision = "FIX_FIRST"
        elif (
            gates_by_id["case_status"]["disposition"] == "active"
            and gates_by_id["competence_and_route"]["disposition"]
            == "court_request"
        ):
            decisive_gate_ids.update(
                {"competence_and_route", "case_status"}
            )
            decision = "COURT_REQUEST_ROUTE"
        elif context["issue_assessment_status"] != "complete":
            blocker_codes.append("issue_research_incomplete")
            decision = "FIX_FIRST"
        elif any(
            binding["readiness"] == "viable"
            for binding in context["option_bindings"]
        ) and context["preferred_option_id"] is not None:
            # GO is justified by the complete hard-gate chain, not by one
            # isolated positive signal.  Preserve that full evidence trace in
            # the recommendation so a human reviewer can audit the result.
            decisive_gate_ids.update(str(gate["gate_id"]) for gate in gates)
            decision = "GO_TO_KSRF"
        elif context["issue_assessment_status"] == "complete":
            has_viable_option = any(
                binding["readiness"] == "viable"
                for binding in context["option_bindings"]
            )
            blocker_codes.append(
                "preferred_viable_option_missing"
                if has_viable_option
                else "no_currently_viable_bound_issue"
            )
            decision = "FIX_FIRST"
        else:
            blocker_codes.append("route_uncertainty_remains")
            decision = "ABSTAIN_PENDING_RECORD"

    if decision in {"NO_GO_KSRF", "ABSTAIN_PENDING_RECORD"}:
        preferred_option_id = None
        reserve_option_ids: list[str] = []
    else:
        preferred_option_id = context["preferred_option_id"]
        reserve_option_ids = list(context["reserve_option_ids"])
    decisive_gate_evidence = [
        {
            "gate_id": str(gate["gate_id"]),
            "evidence_ids": sorted(
                set(str(item) for item in gate.get("evidence_ids") or ())
                | set(
                    str(item)
                    for item in gate.get("official_rule_evidence_ids") or ()
                )
            ),
        }
        for gate in gates
        if str(gate["gate_id"]) in decisive_gate_ids
    ]
    ordered_decisive_gates: list[Mapping[str, Any]] = []
    seen_decisive_gate_ids: set[str] = set()
    for gate in (
        unavailable
        + residual_unknown
        + controlled_unknowns
        + incurable
        + curable_failures
        + list(gates)
    ):
        gate_id = str(gate["gate_id"])
        if gate_id in decisive_gate_ids and gate_id not in seen_decisive_gate_ids:
            ordered_decisive_gates.append(gate)
            seen_decisive_gate_ids.add(gate_id)
    gate_next_actions = [
        str(gate["next_action"])
        for gate in ordered_decisive_gates
        if gate.get("next_action") is not None
    ]
    next_actions_in_order = list(
        dict.fromkeys(
            gate_next_actions + list(context["next_actions_in_order"])
        )
    )
    recommendation_body = {
        "matrix_id": normalized["matrix_id"],
        "matrix_revision_id": matrix_revision_id,
        "matter_id": normalized["matter_id"],
        "claim_id": normalized["claim_id"],
        "decision_rule_version": "ksrf-route-precedence.v1",
        "decision": decision,
        "decisive_gate_evidence": decisive_gate_evidence,
        "blocker_codes": sorted(set(blocker_codes)),
        "official_authority_evidence_ids": sorted(current_ids & required_official_ids),
        "option_bindings": list(context["option_bindings"]),
        "preferred_option_id": preferred_option_id,
        "reserve_option_ids": reserve_option_ids,
        "expected_client_benefit": context["expected_client_benefit"],
        "adverse_risks": list(context["adverse_risks"]),
        "alternatives_and_deadlines": list(context["alternatives_and_deadlines"]),
        "next_actions_in_order": next_actions_in_order,
        "reconsideration_conditions": list(context["reconsideration_conditions"]),
        "human_decision": "pending",
        "human_legal_review_required": True,
        "legal_assessment_automated": False,
        "filing_authority": False,
        "filing_performed": False,
    }
    recommendation = {
        "$schema": RECOMMENDATION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "KSRFRouteRecommendation",
        "recommendation_id": stable_id(
            "ksrf-route-recommendation", recommendation_body
        ),
        **recommendation_body,
    }
    if recommendation["decision"] not in ROUTE_DECISIONS:
        raise AssertionError("Internal route decision is outside the public contract.")
    return recommendation


__all__ = [
    "AdmissibilityContractError",
    "CANONICAL_GATE_IDS",
    "CURABILITY_STATES",
    "GATE_STATUSES",
    "MATRIX_SCHEMA",
    "OFFICIAL_SNAPSHOT_STATES",
    "RECOMMENDATION_SCHEMA",
    "RECORD_AVAILABILITY_STATES",
    "ROUTE_DECISIONS",
    "derive_route_recommendation",
    "official_rule_evidence_ids",
    "validate_admissibility_matrix",
]
