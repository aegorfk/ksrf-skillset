"""Evidence-backed constitutional issue alternatives and fail-closed gates."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .storage import stable_id
from .trusted_approvals import TrustedApprovalLedger


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
        # Caller-supplied reviewer fields are diagnostic only. Required review
        # is resolved by evaluate_issue_gates against TrustedApprovalLedger.
        return not self.requires_human_review

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
        # A positive practice claim is never proven by raw human_decision fields.
        return False

    @property
    def is_substantively_proven(self) -> bool:
        return (
            self.state == "proven"
            and bool(self.evidence_ids)
            and bool(self.authority_scope.strip())
            and self.authority_class in {"official_primary", "official_judicial"}
            and self.freshness_status == "current"
            and self.counterexample_review_status
            in {"reviewed_none_found", "reviewed_found"}
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
        # Selection state is only advisory until a trusted approval validates.
        return False

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
    trusted_approval_ids: Mapping[str, str] = field(default_factory=dict)


def issue_candidate_from_dict(payload: Mapping[str, Any]) -> IssueCandidate:
    """Deserialize a candidate without treating embedded human fields as authority."""

    def strings(value: Any) -> tuple[str, ...]:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            return ()
        return tuple(str(item).strip() for item in value if str(item).strip())

    def mapping(value: Any) -> Mapping[str, Any]:
        return value if isinstance(value, Mapping) else {}

    def gate(value: Any) -> IssueGate:
        raw = mapping(value)
        return IssueGate(
            state=str(raw.get("state") or "unknown"),
            rationale=str(raw.get("rationale") or ""),
            evidence_ids=strings(raw.get("evidence_ids")),
            reviewer=(str(raw.get("reviewer")).strip() if raw.get("reviewer") else None),
            reviewed_at=(
                str(raw.get("reviewed_at")).strip() if raw.get("reviewed_at") else None
            ),
            requires_human_review=raw.get("requires_human_review") is True,
        )

    object_of_review = mapping(payload.get("object_of_review"))
    application_proof = mapping(payload.get("application_proof"))
    adverse = mapping(payload.get("adverse_authority"))
    gates = mapping(payload.get("gates"))
    selection = mapping(payload.get("human_selection"))
    practice_claims = tuple(
        PracticeClaimGate(
            claim_id=str(raw.get("claim_id") or ""),
            statement=str(raw.get("statement") or ""),
            state=str(raw.get("state") or "unknown"),
            evidence_ids=strings(raw.get("evidence_ids")),
            authority_scope=str(raw.get("authority_scope") or ""),
            authority_class=str(raw.get("authority_class") or "unknown"),
            freshness_status=str(raw.get("freshness_status") or "unknown"),
            counterexample_ids=strings(raw.get("counterexample_ids")),
            counterexample_review_status=str(
                raw.get("counterexample_review_status") or "unknown"
            ),
            human_decision=str(raw.get("human_decision") or "pending"),
            reviewer=(str(raw.get("reviewer")).strip() if raw.get("reviewer") else None),
            reviewed_at=(
                str(raw.get("reviewed_at")).strip() if raw.get("reviewed_at") else None
            ),
        )
        for value in gates.get("practice_claims") or ()
        if (raw := mapping(value))
    )
    return IssueCandidate(
        schema_version=str(payload.get("schema_version") or "1.0.0"),
        issue_id=str(payload.get("issue_id") or ""),
        seed_id=str(payload.get("seed_id") or ""),
        claim_id=str(payload.get("claim_id") or ""),
        norm_id=str(object_of_review.get("norm_id") or ""),
        norm_version_id=str(object_of_review.get("norm_version_id") or ""),
        theory_code=str(payload.get("theory_code") or ""),
        normative_meaning=str(payload.get("normative_meaning") or ""),
        application_evidence_ids=strings(application_proof.get("evidence_ids")),
        application_gate_passed=application_proof.get("gate_passed") is True,
        constitutional_benchmarks=strings(payload.get("constitutional_benchmarks")),
        rights_impairment=str(payload.get("rights_impairment") or ""),
        anti_fourth_instance_boundary=str(
            payload.get("anti_fourth_instance_boundary") or ""
        ),
        ksrf_authority_ids=strings(payload.get("ksrf_authority_ids")),
        adverse_authority_ids=strings(adverse.get("authority_ids")),
        adverse_authority_summary=str(adverse.get("summary") or ""),
        adverse_authority_delta=str(adverse.get("delta") or ""),
        requested_remedy=str(payload.get("requested_remedy") or ""),
        strengths=strings(payload.get("strengths")),
        weaknesses=strings(payload.get("weaknesses")),
        source_gaps=strings(payload.get("source_gaps")),
        model_rank=int(payload.get("model_rank") or 1),
        anti_fourth_instance_gate=gate(gates.get("anti_fourth_instance")),
        practice_claims=practice_claims,
        adverse_authority_gate=gate(gates.get("adverse_authority")),
        remedy_gate=gate(gates.get("remedy")),
        human_selection=HumanIssueSelection(
            state=str(selection.get("state") or "pending"),
            reviewer=(
                str(selection.get("reviewer")).strip()
                if selection.get("reviewer")
                else None
            ),
            reviewed_at=(
                str(selection.get("reviewed_at")).strip()
                if selection.get("reviewed_at")
                else None
            ),
            note=str(selection.get("note") or ""),
        ),
    )


def issue_candidate_review_payload(candidate: IssueCandidate) -> dict[str, Any]:
    """Canonical substantive candidate content, excluding raw review diagnostics."""

    def gate_payload(gate: IssueGate) -> dict[str, Any]:
        return {
            "state": gate.state,
            "rationale": gate.rationale,
            "evidence_ids": list(gate.evidence_ids),
            "requires_human_review": gate.requires_human_review,
        }

    return {
        "schema_version": candidate.schema_version,
        "issue_id": candidate.issue_id,
        "seed_id": candidate.seed_id,
        "claim_id": candidate.claim_id,
        "norm_id": candidate.norm_id,
        "norm_version_id": candidate.norm_version_id,
        "theory_code": candidate.theory_code,
        "normative_meaning": candidate.normative_meaning,
        "application_evidence_ids": list(candidate.application_evidence_ids),
        "application_gate_passed": candidate.application_gate_passed,
        "constitutional_benchmarks": list(candidate.constitutional_benchmarks),
        "rights_impairment": candidate.rights_impairment,
        "anti_fourth_instance_boundary": candidate.anti_fourth_instance_boundary,
        "ksrf_authority_ids": list(candidate.ksrf_authority_ids),
        "adverse_authority_ids": list(candidate.adverse_authority_ids),
        "adverse_authority_summary": candidate.adverse_authority_summary,
        "adverse_authority_delta": candidate.adverse_authority_delta,
        "requested_remedy": candidate.requested_remedy,
        "strengths": list(candidate.strengths),
        "weaknesses": list(candidate.weaknesses),
        "source_gaps": list(candidate.source_gaps),
        "model_rank": candidate.model_rank,
        "anti_fourth_instance_gate": gate_payload(
            candidate.anti_fourth_instance_gate
        ),
        "practice_claims": [
            {
                "claim_id": claim.claim_id,
                "statement": claim.statement,
                "state": claim.state,
                "evidence_ids": list(claim.evidence_ids),
                "authority_scope": claim.authority_scope,
                "authority_class": claim.authority_class,
                "freshness_status": claim.freshness_status,
                "counterexample_ids": list(claim.counterexample_ids),
                "counterexample_review_status": claim.counterexample_review_status,
            }
            for claim in candidate.practice_claims
        ],
        "adverse_authority_gate": gate_payload(candidate.adverse_authority_gate),
        "remedy_gate": gate_payload(candidate.remedy_gate),
        "selection_state": candidate.human_selection.state,
    }


def issue_candidate_content_fingerprint(candidate: IssueCandidate) -> str:
    return stable_id("issue-candidate-content", issue_candidate_review_payload(candidate))


def issue_approval_requests(candidate: IssueCandidate) -> dict[str, dict[str, Any]]:
    """Return exact approval subjects for every filing-significant issue decision."""

    requests: dict[str, dict[str, Any]] = {}
    candidate_content_fingerprint = issue_candidate_content_fingerprint(candidate)

    def gate_request(key: str, gate: IssueGate) -> None:
        bindings = {
            "issue_id": candidate.issue_id,
            "gate": key,
            "state": gate.state,
            "rationale": gate.rationale,
            "evidence_ids": list(gate.evidence_ids),
            "candidate_content_fingerprint": candidate_content_fingerprint,
        }
        requests[key] = {
            "purpose": "issue",
            "subject_type": "constitutional_issue_gate",
            "subject_id": f"{candidate.issue_id}:{key}",
            "fingerprint": stable_id("issue-gate-review", bindings),
            "bindings": bindings,
        }

    if candidate.anti_fourth_instance_gate.requires_human_review:
        gate_request("anti_fourth_instance", candidate.anti_fourth_instance_gate)
    gate_request("adverse_authority", candidate.adverse_authority_gate)
    gate_request("remedy", candidate.remedy_gate)
    for claim in candidate.practice_claims:
        if claim.state == "not_asserted":
            continue
        key = f"practice:{claim.claim_id}"
        bindings = {
            "issue_id": candidate.issue_id,
            "claim_id": claim.claim_id,
            "statement": claim.statement,
            "state": claim.state,
            "evidence_ids": list(claim.evidence_ids),
            "authority_scope": claim.authority_scope,
            "authority_class": claim.authority_class,
            "freshness_status": claim.freshness_status,
            "counterexample_ids": list(claim.counterexample_ids),
            "counterexample_review_status": claim.counterexample_review_status,
            "candidate_content_fingerprint": candidate_content_fingerprint,
        }
        requests[key] = {
            "purpose": "issue",
            "subject_type": "practice_claim",
            "subject_id": claim.claim_id,
            "fingerprint": stable_id("practice-claim-review", bindings),
            "bindings": bindings,
        }
    selection_bindings = {
        "issue_id": candidate.issue_id,
        "selection_state": candidate.human_selection.state,
        "norm_id": candidate.norm_id,
        "norm_version_id": candidate.norm_version_id,
        "theory_code": candidate.theory_code,
        "normative_meaning": candidate.normative_meaning,
        "requested_remedy": candidate.requested_remedy,
        "candidate_content_fingerprint": candidate_content_fingerprint,
    }
    requests["selection"] = {
        "purpose": "issue",
        "subject_type": "constitutional_issue_selection",
        "subject_id": candidate.issue_id,
        "fingerprint": stable_id("issue-selection", selection_bindings),
        "bindings": selection_bindings,
    }
    return requests


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


def evaluate_issue_gates(
    candidate: IssueCandidate,
    *,
    approval_ledger: TrustedApprovalLedger | None = None,
    approval_ids: Mapping[str, str] | None = None,
    approval_as_of: str | None = None,
) -> IssueGateDecision:
    """Evaluate every candidate independently; unknown never passes."""

    del approval_as_of
    blockers: list[str] = []
    supplied_approval_ids = dict(approval_ids or {})
    approval_requests = issue_approval_requests(candidate)
    trusted_approval_ids: dict[str, str] = {}

    def trusted(key: str) -> bool:
        approval_id = str(supplied_approval_ids.get(key) or "").strip()
        request = approval_requests[key]
        if approval_ledger is None or not approval_id:
            blockers.append(f"trusted_issue_approval_required:{key}")
            return False
        validation = approval_ledger.validate_approval(
            approval_id,
            **request,
        )
        if validation.get("valid") is not True:
            blockers.append(
                f"trusted_issue_approval_invalid:{key}:{validation.get('reason_code')}"
            )
            return False
        trusted_approval_ids[key] = approval_id
        return True
    if not candidate.application_gate_passed:
        blockers.append("application_proof_gate_not_passed")

    anti = candidate.anti_fourth_instance_gate
    if anti.state == "failed":
        blockers.append("anti_fourth_instance_failed")
    elif anti.state != "passed" or not anti.rationale.strip():
        blockers.append("anti_fourth_instance_not_proven")
    elif anti.requires_human_review and not trusted("anti_fourth_instance"):
        blockers.append("anti_fourth_instance_human_review_required")

    for claim in candidate.practice_claims:
        if claim.state == "not_asserted":
            continue
        if not claim.is_substantively_proven or not trusted(f"practice:{claim.claim_id}"):
            blockers.append(f"practice_claim:{claim.claim_id}:not_proven")

    adverse = candidate.adverse_authority_gate
    if adverse.state != "passed" or not adverse.rationale.strip():
        blockers.append("adverse_authority_unresolved")
    elif not trusted("adverse_authority"):
        blockers.append("adverse_authority_human_resolution_required")

    remedy = candidate.remedy_gate
    if remedy.state != "passed" or not remedy.rationale.strip():
        blockers.append("remedy_not_within_ksrf_competence")
    elif not trusted("remedy"):
        blockers.append("remedy_human_approval_required")

    if candidate.human_selection.state not in {"principal", "reserve"} or not trusted("selection"):
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
        trusted_approval_ids=trusted_approval_ids,
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
    "issue_candidate_content_fingerprint",
    "issue_candidate_from_dict",
    "issue_candidate_review_payload",
    "issue_approval_requests",
]
