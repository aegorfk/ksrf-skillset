"""Evidence-backed constitutional issue alternatives and fail-closed gates."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


GATE_STATES = frozenset({"passed", "failed", "unknown"})
PRACTICE_CLAIM_STATES = frozenset(
    {"proven", "candidate_pattern", "unknown", "not_asserted"}
)
FRESHNESS_STATES = frozenset({"current", "stale", "unknown", "not_applicable"})
HUMAN_DECISIONS = frozenset({"approved", "rejected", "pending", "not_required"})
AUTHORITY_CLASSES = frozenset(
    {
        "official_primary",
        "official_judicial",
        "verified_secondary",
        "discovery_only",
        "unknown",
    }
)
COUNTEREXAMPLE_REVIEW_STATES = frozenset(
    {"reviewed_none_found", "reviewed_found", "not_reviewed", "unknown"}
)
SELECTION_STATES = frozenset(
    {"pending", "principal", "reserve", "experimental", "rejected"}
)


def _require_member(value: str, allowed: frozenset[str], label: str) -> None:
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValueError(f"{label} must be one of: {choices}; got {value!r}")


@dataclass(frozen=True)
class IssueGate:
    state: str
    rationale: str
    evidence_ids: tuple[str, ...] = ()
    reviewer: str | None = None
    reviewed_at: str | None = None
    requires_human_review: bool = False

    def __post_init__(self) -> None:
        _require_member(self.state, GATE_STATES, "issue gate state")

    @property
    def has_required_human_review(self) -> bool:
        return not self.requires_human_review or bool(
            self.reviewer and self.reviewer.strip()
        ) and bool(self.reviewed_at and self.reviewed_at.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "rationale": self.rationale,
            "evidence_ids": list(self.evidence_ids),
            "reviewer": self.reviewer,
            "reviewed_at": self.reviewed_at,
            "requires_human_review": self.requires_human_review,
        }


@dataclass(frozen=True)
class PracticeClaimGate:
    claim_id: str
    statement: str
    state: str
    evidence_ids: tuple[str, ...]
    authority_scope: str
    authority_class: str
    freshness_status: str
    counterexample_ids: tuple[str, ...]
    counterexample_review_status: str
    human_decision: str
    reviewer: str | None = None
    reviewed_at: str | None = None

    def __post_init__(self) -> None:
        _require_member(self.state, PRACTICE_CLAIM_STATES, "practice claim state")
        _require_member(
            self.freshness_status, FRESHNESS_STATES, "practice claim freshness"
        )
        _require_member(
            self.authority_class, AUTHORITY_CLASSES, "practice claim authority class"
        )
        _require_member(
            self.counterexample_review_status,
            COUNTEREXAMPLE_REVIEW_STATES,
            "practice claim counterexample review",
        )
        _require_member(
            self.human_decision, HUMAN_DECISIONS, "practice claim human decision"
        )

    @property
    def is_proven(self) -> bool:
        if self.state == "not_asserted":
            return True
        return (
            self.state == "proven"
            and bool(self.evidence_ids)
            and bool(self.authority_scope.strip())
            and self.authority_class in {"official_primary", "official_judicial"}
            and self.freshness_status == "current"
            and self.counterexample_review_status
            in {"reviewed_none_found", "reviewed_found"}
            and self.human_decision == "approved"
            and bool(self.reviewer and self.reviewer.strip())
            and bool(self.reviewed_at and self.reviewed_at.strip())
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "statement": self.statement,
            "state": self.state,
            "evidence_ids": list(self.evidence_ids),
            "authority_scope": self.authority_scope,
            "authority_class": self.authority_class,
            "freshness_status": self.freshness_status,
            "counterexample_ids": list(self.counterexample_ids),
            "counterexample_review_status": self.counterexample_review_status,
            "human_decision": self.human_decision,
            "reviewer": self.reviewer,
            "reviewed_at": self.reviewed_at,
        }


@dataclass(frozen=True)
class HumanIssueSelection:
    state: str = "pending"
    reviewer: str | None = None
    reviewed_at: str | None = None
    note: str = ""

    def __post_init__(self) -> None:
        _require_member(self.state, SELECTION_STATES, "human issue selection state")

    @property
    def is_release_selection(self) -> bool:
        return (
            self.state in {"principal", "reserve"}
            and bool(self.reviewer and self.reviewer.strip())
            and bool(self.reviewed_at and self.reviewed_at.strip())
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "reviewer": self.reviewer,
            "reviewed_at": self.reviewed_at,
            "note": self.note,
        }


@dataclass(frozen=True)
class IssueSeed:
    seed_id: str
    claim_id: str
    norm_id: str
    norm_version_id: str
    theory_code: str
    normative_meaning: str
    application_evidence_ids: tuple[str, ...]
    application_gate_passed: bool
    constitutional_benchmarks: tuple[str, ...]
    rights_impairment: str
    anti_fourth_instance_boundary: str
    ksrf_authority_ids: tuple[str, ...]
    adverse_authority_ids: tuple[str, ...]
    adverse_authority_summary: str
    adverse_authority_delta: str
    requested_remedy: str
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    source_gaps: tuple[str, ...]
    model_rank: int
    anti_fourth_instance_gate: IssueGate
    practice_claims: tuple[PracticeClaimGate, ...]
    adverse_authority_gate: IssueGate
    remedy_gate: IssueGate
    human_selection: HumanIssueSelection

    def __post_init__(self) -> None:
        if self.model_rank < 1:
            raise ValueError("model_rank must be at least 1")


@dataclass(frozen=True)
class IssueCandidate:
    schema_version: str
    issue_id: str
    seed_id: str
    claim_id: str
    norm_id: str
    norm_version_id: str
    theory_code: str
    normative_meaning: str
    application_evidence_ids: tuple[str, ...]
    application_gate_passed: bool
    constitutional_benchmarks: tuple[str, ...]
    rights_impairment: str
    anti_fourth_instance_boundary: str
    ksrf_authority_ids: tuple[str, ...]
    adverse_authority_ids: tuple[str, ...]
    adverse_authority_summary: str
    adverse_authority_delta: str
    requested_remedy: str
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    source_gaps: tuple[str, ...]
    model_rank: int
    anti_fourth_instance_gate: IssueGate
    practice_claims: tuple[PracticeClaimGate, ...]
    adverse_authority_gate: IssueGate
    remedy_gate: IssueGate
    human_selection: HumanIssueSelection

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "issue_id": self.issue_id,
            "seed_id": self.seed_id,
            "claim_id": self.claim_id,
            "object_of_review": {
                "norm_id": self.norm_id,
                "norm_version_id": self.norm_version_id,
            },
            "theory_code": self.theory_code,
            "normative_meaning": self.normative_meaning,
            "application_proof": {
                "evidence_ids": list(self.application_evidence_ids),
                "gate_passed": self.application_gate_passed,
            },
            "constitutional_benchmarks": list(self.constitutional_benchmarks),
            "rights_impairment": self.rights_impairment,
            "anti_fourth_instance_boundary": self.anti_fourth_instance_boundary,
            "ksrf_authority_ids": list(self.ksrf_authority_ids),
            "adverse_authority": {
                "authority_ids": list(self.adverse_authority_ids),
                "summary": self.adverse_authority_summary,
                "delta": self.adverse_authority_delta,
            },
            "requested_remedy": self.requested_remedy,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "source_gaps": list(self.source_gaps),
            "model_rank": self.model_rank,
            "gates": {
                "anti_fourth_instance": self.anti_fourth_instance_gate.to_dict(),
                "practice_claims": [claim.to_dict() for claim in self.practice_claims],
                "adverse_authority": self.adverse_authority_gate.to_dict(),
                "remedy": self.remedy_gate.to_dict(),
            },
            "human_selection": self.human_selection.to_dict(),
        }


@dataclass(frozen=True)
class OmittedIssue:
    seed_id: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class IssueGenerationResult:
    candidates: tuple[IssueCandidate, ...]
    omitted: tuple[OmittedIssue, ...]
    generation_note: str
    generic_default_used: bool = False


@dataclass(frozen=True)
class IssueGateDecision:
    passed: bool
    blockers: tuple[str, ...]
    evidence_map: Mapping[str, tuple[str, ...]]


def _missing_core_fields(seed: IssueSeed) -> tuple[str, ...]:
    missing: list[str] = []
    scalar_fields = (
        ("seed_id", seed.seed_id),
        ("claim_id", seed.claim_id),
        ("norm_id", seed.norm_id),
        ("norm_version", seed.norm_version_id),
        ("theory_code", seed.theory_code),
        ("normative_meaning", seed.normative_meaning),
        ("rights_impairment", seed.rights_impairment),
        ("anti_fourth_instance_boundary", seed.anti_fourth_instance_boundary),
        ("adverse_authority_summary", seed.adverse_authority_summary),
        ("adverse_authority_delta", seed.adverse_authority_delta),
        ("requested_remedy", seed.requested_remedy),
    )
    for label, value in scalar_fields:
        if not value.strip():
            missing.append(f"missing_{label}")
    list_fields = (
        ("application_evidence", seed.application_evidence_ids),
        ("constitutional_benchmark", seed.constitutional_benchmarks),
        ("ksrf_authority", seed.ksrf_authority_ids),
    )
    for label, value in list_fields:
        if not value:
            missing.append(f"missing_{label}")
    return tuple(missing)


def _formulation_key(seed: IssueSeed) -> tuple[str, ...]:
    return (
        seed.claim_id.strip(),
        seed.norm_id.strip(),
        seed.norm_version_id.strip(),
        seed.theory_code.strip(),
        seed.normative_meaning.strip(),
        seed.requested_remedy.strip(),
    )


def _issue_id(seed: IssueSeed) -> str:
    material = "\x1f".join(_formulation_key(seed)).encode("utf-8")
    return f"constitutional-issue-{hashlib.sha256(material).hexdigest()[:16]}"


def _candidate_from_seed(seed: IssueSeed) -> IssueCandidate:
    return IssueCandidate(
        schema_version="1.0.0",
        issue_id=_issue_id(seed),
        seed_id=seed.seed_id,
        claim_id=seed.claim_id,
        norm_id=seed.norm_id,
        norm_version_id=seed.norm_version_id,
        theory_code=seed.theory_code,
        normative_meaning=seed.normative_meaning,
        application_evidence_ids=seed.application_evidence_ids,
        application_gate_passed=seed.application_gate_passed,
        constitutional_benchmarks=seed.constitutional_benchmarks,
        rights_impairment=seed.rights_impairment,
        anti_fourth_instance_boundary=seed.anti_fourth_instance_boundary,
        ksrf_authority_ids=seed.ksrf_authority_ids,
        adverse_authority_ids=seed.adverse_authority_ids,
        adverse_authority_summary=seed.adverse_authority_summary,
        adverse_authority_delta=seed.adverse_authority_delta,
        requested_remedy=seed.requested_remedy,
        strengths=seed.strengths,
        weaknesses=seed.weaknesses,
        source_gaps=seed.source_gaps,
        model_rank=seed.model_rank,
        anti_fourth_instance_gate=seed.anti_fourth_instance_gate,
        practice_claims=seed.practice_claims,
        adverse_authority_gate=seed.adverse_authority_gate,
        remedy_gate=seed.remedy_gate,
        human_selection=seed.human_selection,
    )


def generate_issue_candidates(
    seeds: Sequence[IssueSeed], *, max_candidates: int = 4
) -> IssueGenerationResult:
    """Generate zero to four distinct supported options, never a generic default."""

    if not 1 <= max_candidates <= 4:
        raise ValueError("max_candidates must be between 1 and 4")
    candidates: list[IssueCandidate] = []
    omitted: list[OmittedIssue] = []
    seen: set[tuple[str, ...]] = set()
    for seed in sorted(seeds, key=lambda item: (item.model_rank, item.seed_id)):
        missing = _missing_core_fields(seed)
        if missing:
            omitted.append(OmittedIssue(seed_id=seed.seed_id, reason_codes=missing))
            continue
        key = _formulation_key(seed)
        if key in seen:
            omitted.append(
                OmittedIssue(
                    seed_id=seed.seed_id,
                    reason_codes=("duplicate_formulation",),
                )
            )
            continue
        seen.add(key)
        if len(candidates) >= max_candidates:
            omitted.append(
                OmittedIssue(
                    seed_id=seed.seed_id,
                    reason_codes=("candidate_limit_reached",),
                )
            )
            continue
        candidates.append(_candidate_from_seed(seed))

    if not candidates:
        note = (
            "Конституционно-правовые формулировки не сформированы: "
            "в представленных данных нет полного доказательного каркаса."
        )
    elif len(candidates) == 1:
        note = (
            "Сформирован один доказанный вариант; дополнительные формулировки "
            "не созданы без самостоятельного нормативного смысла, доказательств "
            "и способа защиты, доступного КС РФ."
        )
    else:
        note = (
            f"Сформировано {len(candidates)} самостоятельных вариантов; "
            "ранжирование модели носит рекомендательный характер."
        )
    return IssueGenerationResult(
        candidates=tuple(candidates),
        omitted=tuple(omitted),
        generation_note=note,
        generic_default_used=False,
    )


def evaluate_issue_gates(candidate: IssueCandidate) -> IssueGateDecision:
    """Evaluate every candidate independently; unknown never passes."""

    blockers: list[str] = []
    if not candidate.application_gate_passed:
        blockers.append("application_proof_gate_not_passed")

    anti = candidate.anti_fourth_instance_gate
    if anti.state == "failed":
        blockers.append("anti_fourth_instance_failed")
    elif anti.state != "passed" or not anti.rationale.strip():
        blockers.append("anti_fourth_instance_not_proven")

    for claim in candidate.practice_claims:
        if not claim.is_proven:
            blockers.append(f"practice_claim:{claim.claim_id}:not_proven")

    adverse = candidate.adverse_authority_gate
    if adverse.state != "passed" or not adverse.rationale.strip():
        blockers.append("adverse_authority_unresolved")
    elif not adverse.has_required_human_review:
        blockers.append("adverse_authority_human_resolution_required")

    remedy = candidate.remedy_gate
    if remedy.state != "passed" or not remedy.rationale.strip():
        blockers.append("remedy_not_within_ksrf_competence")
    elif not remedy.has_required_human_review:
        blockers.append("remedy_human_approval_required")

    if not candidate.human_selection.is_release_selection:
        blockers.append("human_issue_selection_required")

    blockers = list(dict.fromkeys(blockers))
    practice_evidence = tuple(
        evidence_id
        for claim in candidate.practice_claims
        for evidence_id in claim.evidence_ids
    )
    return IssueGateDecision(
        passed=not blockers,
        blockers=tuple(blockers),
        evidence_map={
            "application": candidate.application_evidence_ids,
            "anti_fourth_instance": anti.evidence_ids,
            "practice_claims": practice_evidence,
            "adverse_authority": adverse.evidence_ids,
            "remedy": remedy.evidence_ids,
        },
    )


__all__ = [
    "HumanIssueSelection",
    "IssueCandidate",
    "IssueGate",
    "IssueGateDecision",
    "IssueGenerationResult",
    "IssueSeed",
    "OmittedIssue",
    "PracticeClaimGate",
    "evaluate_issue_gates",
    "generate_issue_candidates",
]
