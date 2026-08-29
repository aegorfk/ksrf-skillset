"""Claim-level proof of judicial application of a challenged norm.

The module deliberately keeps norm use, outcome causation, and procedural
preservation as separate axes.  It does not import the wider filing contracts:
these local dataclasses are the bounded contract for OpenSpec tasks 5.1--5.6
and can be consolidated after the neighbouring package contracts stabilise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from .norm_versions import (
    assess_norm_version_passport,
    norm_version_passport_content_fingerprint,
    official_evidence_references,
    verify_official_evidence_reference,
)
from .storage import stable_id
from .trusted_approvals import TrustedApprovalLedger


NORM_USE_STATUSES = frozenset(
    {
        "direct_reasoned_use",
        "reasoning_linked_implicit",
        "mentioned_only",
        "party_only",
        "quoted_authority_only",
        "reasoned_rejection",
        "unclear",
    }
)
NORM_USE_STATUS_ALIASES = {
    "reasoned_direct_use": "direct_reasoned_use",
    "reasoning_linked_implicit_use": "reasoning_linked_implicit",
    "mention_only": "mentioned_only",
}
OUTCOME_CAUSATION_STATUSES = frozenset(
    {
        "determinative",
        "contributory",
        "independent_sufficient_ground",
        "unclear",
    }
)
PRESERVATION_EXHAUSTION_STATUSES = frozenset(
    {
        "raised_and_reviewed",
        "raised_but_not_addressed",
        "not_raised",
        "record_missing",
        "unclear",
    }
)
APPLICATION_STATUSES = frozenset(
    {
        "explicitly_applied",
        "implicitly_applied_proven",
        "application_unclear",
        "not_applied",
    }
)
CHAIN_STATUSES = frozenset(
    {"survived", "superseded", "concurrent", "incorporated", "unclear"}
)
RELATIONS_TO_PRIOR = frozenset(
    {
        "initial",
        "independent_reapplication",
        "express_incorporation",
        "affirmance_only",
        "superseding_ground",
        "concurrent_ground",
        "unclear",
    }
)
EVIDENCE_SPEAKERS = frozenset(
    {"court", "party", "disposition", "metadata", "quoted_authority", "model", "reviewer"}
)
EVIDENCE_SOURCE_KINDS = frozenset(
    {"full_act", "case_metadata", "party_document", "official_publication", "other"}
)
INFERENCE_STATUSES = frozenset(
    {"observed", "inferred", "human_confirmed", "contradicted"}
)
HUMAN_REVIEW_STATES = frozenset(
    {"pending", "approved", "rejected", "needs_changes"}
)
AFFIRMATIVE_NON_APPLICATION_REASONS = frozenset(
    {"express_non_use", "complete_independent_ground", "operative_mismatch"}
)
IMPLICIT_PREMISES = (
    "issue_before_court",
    "operative_norm_logic",
    "counterfactual_outcome_dependence",
    "no_independent_sufficient_ground",
)


def _require_member(value: str, allowed: frozenset[str], label: str) -> None:
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValueError(f"{label} must be one of: {choices}; got {value!r}")


@dataclass(frozen=True)
class FullActLocator:
    """Stable location inside the complete judicial act."""

    kind: str
    value: str

    @property
    def is_complete(self) -> bool:
        return bool(self.kind.strip() and self.value.strip())

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "value": self.value}


@dataclass(frozen=True)
class EvidenceSpan:
    """One claim-level span without collapsing its author or evidentiary role."""

    evidence_id: str
    claim_id: str
    norm_id: str
    act_id: str
    stage: str
    source_kind: str
    locator: FullActLocator | None
    quote: str
    speaker: str
    reasoning_role: str
    inference_status: str

    def __post_init__(self) -> None:
        _require_member(self.source_kind, EVIDENCE_SOURCE_KINDS, "source_kind")
        _require_member(self.speaker, EVIDENCE_SPEAKERS, "speaker")
        _require_member(self.inference_status, INFERENCE_STATUSES, "inference_status")
        if not self.evidence_id.strip():
            raise ValueError("evidence_id must not be empty")
        if not self.reasoning_role.strip():
            raise ValueError("reasoning_role must not be empty")

    @property
    def has_full_act_locator(self) -> bool:
        return (
            self.source_kind == "full_act"
            and self.locator is not None
            and self.locator.is_complete
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "claim_id": self.claim_id,
            "norm_id": self.norm_id,
            "act_id": self.act_id,
            "stage": self.stage,
            "source_kind": self.source_kind,
            "locator": self.locator.to_dict() if self.locator else None,
            "quote": self.quote,
            "speaker": self.speaker,
            "reasoning_role": self.reasoning_role,
            "inference_status": self.inference_status,
        }


@dataclass(frozen=True)
class ImplicitPremiseProof:
    premise: str
    conclusion: str
    evidence_ids: tuple[str, ...]
    inference_status: str

    def __post_init__(self) -> None:
        if self.premise not in IMPLICIT_PREMISES:
            raise ValueError(f"unknown implicit premise: {self.premise}")
        _require_member(self.inference_status, INFERENCE_STATUSES, "inference_status")

    def to_dict(self) -> dict[str, Any]:
        return {
            "premise": self.premise,
            "conclusion": self.conclusion,
            "evidence_ids": list(self.evidence_ids),
            "inference_status": self.inference_status,
        }


@dataclass(frozen=True)
class AffirmativeNonApplication:
    reason: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_member(
            self.reason,
            AFFIRMATIVE_NON_APPLICATION_REASONS,
            "affirmative_non_application.reason",
        )

    def to_dict(self) -> dict[str, Any]:
        return {"reason": self.reason, "evidence_ids": list(self.evidence_ids)}


@dataclass(frozen=True)
class HumanReview:
    state: str = "pending"
    reviewer: str | None = None
    reviewed_at: str | None = None
    note: str = ""

    def __post_init__(self) -> None:
        _require_member(self.state, HUMAN_REVIEW_STATES, "human_review.state")

    @property
    def is_named_approval(self) -> bool:
        return (
            self.state == "approved"
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
class ApplicationEvidenceRecord:
    schema_version: str
    record_id: str
    claim_id: str
    norm_id: str
    norm_version_id: str
    normative_meaning_id: str
    act_id: str
    stage: str
    stage_order: int
    norm_use_status: str
    outcome_causation: str
    preservation_exhaustion: str
    relation_to_prior: str
    incorporated_record_ids: tuple[str, ...] = ()
    evidence: tuple[EvidenceSpan, ...] = ()
    implicit_premises: tuple[ImplicitPremiseProof, ...] = ()
    affirmative_non_application: AffirmativeNonApplication | None = None
    human_review: HumanReview = field(default_factory=HumanReview)
    decision_rationale: str = ""

    def __post_init__(self) -> None:
        canonical_norm_use = NORM_USE_STATUS_ALIASES.get(
            self.norm_use_status, self.norm_use_status
        )
        object.__setattr__(self, "norm_use_status", canonical_norm_use)
        _require_member(self.norm_use_status, NORM_USE_STATUSES, "norm_use_status")
        _require_member(
            self.outcome_causation, OUTCOME_CAUSATION_STATUSES, "outcome_causation"
        )
        _require_member(
            self.preservation_exhaustion,
            PRESERVATION_EXHAUSTION_STATUSES,
            "preservation_exhaustion",
        )
        _require_member(self.relation_to_prior, RELATIONS_TO_PRIOR, "relation_to_prior")
        if self.stage_order < 1:
            raise ValueError("stage_order must be at least 1")
        for label, value in (
            ("schema_version", self.schema_version),
            ("record_id", self.record_id),
            ("claim_id", self.claim_id),
            ("norm_id", self.norm_id),
            ("norm_version_id", self.norm_version_id),
            ("normative_meaning_id", self.normative_meaning_id),
            ("act_id", self.act_id),
            ("stage", self.stage),
        ):
            if not value.strip():
                raise ValueError(f"{label} must not be empty")
        evidence_ids = [span.evidence_id for span in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence_id values must be unique inside an application record")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "claim_id": self.claim_id,
            "norm_id": self.norm_id,
            "norm_version_id": self.norm_version_id,
            "normative_meaning_id": self.normative_meaning_id,
            "act_id": self.act_id,
            "stage": self.stage,
            "stage_order": self.stage_order,
            "norm_use_status": self.norm_use_status,
            "outcome_causation": self.outcome_causation,
            "preservation_exhaustion": self.preservation_exhaustion,
            "relation_to_prior": self.relation_to_prior,
            "incorporated_record_ids": list(self.incorporated_record_ids),
            "evidence": [span.to_dict() for span in self.evidence],
            "implicit_premises": [proof.to_dict() for proof in self.implicit_premises],
            "affirmative_non_application": (
                self.affirmative_non_application.to_dict()
                if self.affirmative_non_application
                else None
            ),
            "human_review": self.human_review.to_dict(),
            "decision_rationale": self.decision_rationale,
        }


def application_record_review_payload(
    record: ApplicationEvidenceRecord,
) -> dict[str, Any]:
    """Canonical reviewable content, excluding caller-supplied review diagnostics."""

    payload = record.to_dict()
    payload.pop("human_review", None)
    return payload


def application_record_content_fingerprint(
    record: ApplicationEvidenceRecord,
) -> str:
    return stable_id(
        "application-evidence-content",
        application_record_review_payload(record),
    )


@dataclass(frozen=True)
class ApplicationClassification:
    status: str
    compatibility_aliases: tuple[str, ...] = ()
    missing_premises: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_member(self.status, APPLICATION_STATUSES, "application status")


@dataclass(frozen=True)
class ChainAssessment:
    status: str
    final_record_id: str | None
    supporting_record_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    record_content_fingerprints: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _require_member(self.status, CHAIN_STATUSES, "chain status")


@dataclass(frozen=True)
class AdmissibilityDecision:
    passed: bool
    blockers: tuple[str, ...]
    application_status: str
    evidence_map: Mapping[str, tuple[str, ...]]
    trusted_approval_id: str | None = None
    trusted_reviewer: str | None = None


PRESERVATION_RULE_STATUSES = frozenset(
    {"verified_required", "verified_not_required"}
)
_PRESERVATION_RULE_FIELDS = {
    "schema_version",
    "application_record_id",
    "claim_id",
    "norm_id",
    "norm_version_id",
    "rule_status",
    "rule_citation",
    "rule_statement",
    "evidence_ids",
    "record_preservation_exhaustion",
    "content_fingerprint",
    "rule_id",
}
EvidenceReferenceVerifier = Callable[
    [Mapping[str, Any]], bool | Mapping[str, Any]
]


def preservation_rule_review_payload(
    rule: Mapping[str, Any],
) -> dict[str, Any]:
    """Canonical preservation/exhaustion rule content without self-identifiers."""

    return {
        key: value
        for key, value in rule.items()
        if key not in {"rule_id", "content_fingerprint"}
    }


def preservation_rule_content_fingerprint(rule: Mapping[str, Any]) -> str:
    return stable_id(
        "preservation-rule-content",
        preservation_rule_review_payload(rule),
    )


def build_preservation_rule_evidence(
    record: ApplicationEvidenceRecord,
    *,
    rule_status: str,
    rule_citation: str,
    rule_statement: str,
    evidence_ids: Sequence[str],
) -> dict[str, Any]:
    """Build a content-addressed current-law prerequisite for the application gate."""

    if not isinstance(evidence_ids, Sequence) or isinstance(evidence_ids, (str, bytes)):
        raise ValueError("evidence_ids must be a sequence")
    evidence = sorted(
        {str(item).strip() for item in evidence_ids if str(item).strip()}
    )
    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "application_record_id": record.record_id,
        "claim_id": record.claim_id,
        "norm_id": record.norm_id,
        "norm_version_id": record.norm_version_id,
        "rule_status": str(rule_status),
        "rule_citation": str(rule_citation).strip(),
        "rule_statement": str(rule_statement).strip(),
        "evidence_ids": evidence,
        "record_preservation_exhaustion": record.preservation_exhaustion,
    }
    payload["content_fingerprint"] = preservation_rule_content_fingerprint(payload)
    payload["rule_id"] = stable_id(
        "preservation-rule",
        {
            "application_record_id": record.record_id,
            "content_fingerprint": payload["content_fingerprint"],
        },
    )
    return payload


def preservation_rule_review_approval_request(
    rule: Mapping[str, Any],
) -> dict[str, Any]:
    bindings = {
        "rule_id": str(rule.get("rule_id") or ""),
        "content_fingerprint": preservation_rule_content_fingerprint(rule),
        "rule": preservation_rule_review_payload(rule),
    }
    return {
        "purpose": "application",
        "subject_type": "preservation_exhaustion_rule",
        "subject_id": bindings["rule_id"],
        "fingerprint": stable_id("preservation-rule-review", bindings),
        "bindings": bindings,
    }


def _preservation_rule_assessment(
    record: ApplicationEvidenceRecord,
    rule: Mapping[str, Any] | None,
    *,
    evidence_verifier: EvidenceReferenceVerifier | Any | None,
    approval_ledger: TrustedApprovalLedger | None,
    approval_id: str | None,
) -> tuple[list[str], tuple[str, ...], str | None]:
    if not isinstance(rule, Mapping):
        return ["preservation_rule_evidence_required"], (), None

    blockers: list[str] = []
    for field in sorted(set(rule) - _PRESERVATION_RULE_FIELDS):
        blockers.append(f"unexpected_preservation_rule_field:{field}")
    expected_bindings = {
        "application_record_id": record.record_id,
        "claim_id": record.claim_id,
        "norm_id": record.norm_id,
        "norm_version_id": record.norm_version_id,
        "record_preservation_exhaustion": record.preservation_exhaustion,
    }
    if rule.get("schema_version") != "1.0.0":
        blockers.append("preservation_rule_schema_invalid")
    if any(rule.get(key) != value for key, value in expected_bindings.items()):
        blockers.append("preservation_rule_record_binding_mismatch")
    rule_status = str(rule.get("rule_status") or "")
    if rule_status not in PRESERVATION_RULE_STATUSES:
        blockers.append("preservation_rule_status_invalid")
    if not str(rule.get("rule_citation") or "").strip():
        blockers.append("preservation_rule_citation_missing")
    if not str(rule.get("rule_statement") or "").strip():
        blockers.append("preservation_rule_statement_missing")
    raw_evidence_ids = rule.get("evidence_ids")
    if not isinstance(raw_evidence_ids, Sequence) or isinstance(
        raw_evidence_ids, (str, bytes)
    ):
        evidence_ids: tuple[str, ...] = ()
    else:
        evidence_ids = tuple(
            sorted({str(item).strip() for item in raw_evidence_ids if str(item).strip()})
        )
        if list(raw_evidence_ids) != list(evidence_ids):
            blockers.append("preservation_rule_evidence_ids_noncanonical")
    if not evidence_ids:
        blockers.append("preservation_rule_official_evidence_missing")
    if rule.get("content_fingerprint") != preservation_rule_content_fingerprint(rule):
        blockers.append("preservation_rule_content_fingerprint_mismatch")
    expected_rule_id = stable_id(
        "preservation-rule",
        {
            "application_record_id": record.record_id,
            "content_fingerprint": preservation_rule_content_fingerprint(rule),
        },
    )
    if rule.get("rule_id") != expected_rule_id:
        blockers.append("preservation_rule_id_mismatch")

    if evidence_ids and evidence_verifier is None:
        blockers.append("preservation_rule_evidence_verifier_required")
    elif evidence_verifier is not None:
        for evidence_id in evidence_ids:
            reference = {
                "role": "preservation_exhaustion_rule",
                "evidence_id": evidence_id,
                "authority_class": "official_primary",
            }
            if not verify_official_evidence_reference(evidence_verifier, reference):
                blockers.append(f"preservation_evidence_not_verified:{evidence_id}")

    approval_validation: Mapping[str, Any] = {
        "valid": False,
        "reason_code": "approval_required",
    }
    if approval_ledger is not None and str(approval_id or "").strip():
        approval_validation = approval_ledger.validate_approval(
            str(approval_id),
            **preservation_rule_review_approval_request(rule),
        )
    if approval_validation.get("valid") is not True:
        if approval_ledger is None or not str(approval_id or "").strip():
            blockers.append("trusted_preservation_rule_approval_required")
        else:
            blockers.append(
                "trusted_preservation_rule_"
                f"{approval_validation.get('reason_code') or 'approval_invalid'}"
            )
    return list(dict.fromkeys(blockers)), evidence_ids, rule_status or None


def application_review_approval_request(
    record: ApplicationEvidenceRecord,
    chain: ChainAssessment,
    *,
    norm_version_status: str,
    version_evidence_ids: Sequence[str],
    preservation_rule_status: str,
    norm_version_passport: Mapping[str, Any] | None = None,
    norm_version_approval_id: str | None = None,
    preservation_rule_evidence: Mapping[str, Any] | None = None,
    preservation_rule_approval_id: str | None = None,
) -> dict[str, Any]:
    """Build exact immutable bindings for a positive application gate."""

    del norm_version_status, version_evidence_ids, preservation_rule_status
    classification = classify_application(record)
    record_content_fingerprint = application_record_content_fingerprint(record)
    norm_binding = None
    if isinstance(norm_version_passport, Mapping):
        norm_binding = {
            "passport_id": str(norm_version_passport.get("passport_id") or ""),
            "passport_revision_id": str(
                norm_version_passport.get("passport_revision_id") or ""
            ),
            "content_fingerprint": norm_version_passport_content_fingerprint(
                norm_version_passport
            ),
            "official_evidence_references": official_evidence_references(
                norm_version_passport
            ),
            "trusted_approval_id": str(norm_version_approval_id or ""),
        }
    preservation_binding = None
    if isinstance(preservation_rule_evidence, Mapping):
        preservation_binding = {
            "rule_id": str(preservation_rule_evidence.get("rule_id") or ""),
            "content_fingerprint": preservation_rule_content_fingerprint(
                preservation_rule_evidence
            ),
            "trusted_approval_id": str(preservation_rule_approval_id or ""),
        }
    bindings = {
        "record_id": record.record_id,
        "claim_id": record.claim_id,
        "norm_id": record.norm_id,
        "norm_version_id": record.norm_version_id,
        "act_id": record.act_id,
        "application_status": classification.status,
        "application_evidence_ids": list(classification.evidence_ids),
        "record_content_fingerprint": record_content_fingerprint,
        "chain_assessment": {
            "status": chain.status,
            "final_record_id": chain.final_record_id,
            "supporting_record_ids": list(chain.supporting_record_ids),
            "evidence_ids": list(chain.evidence_ids),
            "reason_codes": list(chain.reason_codes),
            "record_content_fingerprints": [
                {"record_id": record_id, "fingerprint": fingerprint}
                for record_id, fingerprint in chain.record_content_fingerprints
            ],
        },
        "norm_version_prerequisite": norm_binding,
        "preservation_rule_prerequisite": preservation_binding,
    }
    return {
        "purpose": "application",
        "subject_type": "application_admissibility",
        "subject_id": record.record_id,
        "fingerprint": stable_id("application-review", bindings),
        "bindings": bindings,
    }


def application_record_from_dict(payload: Mapping[str, Any]) -> ApplicationEvidenceRecord:
    """Deserialize the versioned JSON record into the local immutable contract."""

    evidence = []
    for raw in payload.get("evidence", ()):
        locator_raw = raw.get("locator")
        locator = (
            FullActLocator(kind=str(locator_raw["kind"]), value=str(locator_raw["value"]))
            if isinstance(locator_raw, Mapping)
            else None
        )
        evidence.append(
            EvidenceSpan(
                evidence_id=str(raw["evidence_id"]),
                claim_id=str(raw["claim_id"]),
                norm_id=str(raw["norm_id"]),
                act_id=str(raw["act_id"]),
                stage=str(raw["stage"]),
                source_kind=str(raw["source_kind"]),
                locator=locator,
                quote=str(raw.get("quote", "")),
                speaker=str(raw["speaker"]),
                reasoning_role=str(raw["reasoning_role"]),
                inference_status=str(raw["inference_status"]),
            )
        )
    premises = tuple(
        ImplicitPremiseProof(
            premise=str(raw["premise"]),
            conclusion=str(raw.get("conclusion", "")),
            evidence_ids=tuple(str(item) for item in raw.get("evidence_ids", ())),
            inference_status=str(raw["inference_status"]),
        )
        for raw in payload.get("implicit_premises", ())
    )
    non_application_raw = payload.get("affirmative_non_application")
    non_application = (
        AffirmativeNonApplication(
            reason=str(non_application_raw["reason"]),
            evidence_ids=tuple(
                str(item) for item in non_application_raw.get("evidence_ids", ())
            ),
        )
        if isinstance(non_application_raw, Mapping)
        else None
    )
    review_raw = payload.get("human_review") or {}
    review = HumanReview(
        state=str(review_raw.get("state", "pending")),
        reviewer=review_raw.get("reviewer"),
        reviewed_at=review_raw.get("reviewed_at"),
        note=str(review_raw.get("note", "")),
    )
    return ApplicationEvidenceRecord(
        schema_version=str(payload["schema_version"]),
        record_id=str(payload["record_id"]),
        claim_id=str(payload["claim_id"]),
        norm_id=str(payload["norm_id"]),
        norm_version_id=str(payload["norm_version_id"]),
        normative_meaning_id=str(payload["normative_meaning_id"]),
        act_id=str(payload["act_id"]),
        stage=str(payload["stage"]),
        stage_order=int(payload["stage_order"]),
        norm_use_status=str(payload["norm_use_status"]),
        outcome_causation=str(payload["outcome_causation"]),
        preservation_exhaustion=str(payload["preservation_exhaustion"]),
        relation_to_prior=str(payload.get("relation_to_prior", "unclear")),
        incorporated_record_ids=tuple(
            str(item) for item in payload.get("incorporated_record_ids", ())
        ),
        evidence=tuple(evidence),
        implicit_premises=premises,
        affirmative_non_application=non_application,
        human_review=review,
        decision_rationale=str(payload.get("decision_rationale", "")),
    )


def normalize_application_status(status: str) -> str:
    """Map the only supported legacy label without broad fuzzy fallback."""

    if status == "directly_applied":
        return "explicitly_applied"
    if status not in APPLICATION_STATUSES:
        raise ValueError(f"unknown application status: {status}")
    return status


def _evidence_by_id(record: ApplicationEvidenceRecord) -> dict[str, EvidenceSpan]:
    return {span.evidence_id: span for span in record.evidence}


def _claim_level_mismatches(record: ApplicationEvidenceRecord) -> tuple[str, ...]:
    mismatches: list[str] = []
    for span in record.evidence:
        if (
            span.claim_id != record.claim_id
            or span.norm_id != record.norm_id
            or span.act_id != record.act_id
            or span.stage != record.stage
        ):
            mismatches.append(span.evidence_id)
    return tuple(mismatches)


def _usable_full_act_spans(
    record: ApplicationEvidenceRecord, evidence_ids: Sequence[str]
) -> tuple[EvidenceSpan, ...]:
    evidence = _evidence_by_id(record)
    spans: list[EvidenceSpan] = []
    for evidence_id in evidence_ids:
        span = evidence.get(evidence_id)
        if span is None or not span.has_full_act_locator:
            return ()
        if span.inference_status == "contradicted":
            return ()
        spans.append(span)
    return tuple(spans)


def _role_is_proven(
    record: ApplicationEvidenceRecord,
    role: str,
    *,
    speakers: frozenset[str] = frozenset({"court"}),
) -> bool:
    return any(
        span.reasoning_role == role
        and span.speaker in speakers
        and span.has_full_act_locator
        and span.inference_status != "contradicted"
        for span in record.evidence
    )


def _direct_application_is_proven(record: ApplicationEvidenceRecord) -> bool:
    return (
        _role_is_proven(record, "express_norm_use")
        and _role_is_proven(record, "operative_rule")
        and _role_is_proven(
            record, "outcome_link", speakers=frozenset({"court", "disposition"})
        )
    )


def _affirmative_non_application_is_proven(
    record: ApplicationEvidenceRecord,
) -> bool:
    assertion = record.affirmative_non_application
    if assertion is None or not assertion.evidence_ids:
        return False
    spans = _usable_full_act_spans(record, assertion.evidence_ids)
    if not spans:
        return False
    roles_by_reason = {
        "express_non_use": {"express_non_use", "reasoned_rejection"},
        "complete_independent_ground": {
            "independent_ground",
            "alternative_ground_analysis",
        },
        "operative_mismatch": {"operative_mismatch"},
    }
    return any(
        span.reasoning_role in roles_by_reason[assertion.reason]
        for span in spans
    )


def _implicit_missing_premises(record: ApplicationEvidenceRecord) -> tuple[str, ...]:
    proofs = {proof.premise: proof for proof in record.implicit_premises}
    missing: list[str] = []
    for premise in IMPLICIT_PREMISES:
        proof = proofs.get(premise)
        if proof is None or not proof.conclusion.strip() or not proof.evidence_ids:
            missing.append(premise)
            continue
        spans = _usable_full_act_spans(record, proof.evidence_ids)
        if not spans:
            missing.append(f"{premise}:full_act_locator_required")
            continue
        if premise == "issue_before_court" and not any(
            span.reasoning_role == "issue_before_court" for span in spans
        ):
            missing.append(f"{premise}:issue_evidence_required")
        elif premise == "operative_norm_logic" and not any(
            span.speaker == "court"
            and span.reasoning_role in {"operative_rule", "application_reasoning"}
            for span in spans
        ):
            missing.append(f"{premise}:court_reasoning_required")
        elif premise == "counterfactual_outcome_dependence" and not any(
            span.speaker in {"court", "disposition"}
            and span.reasoning_role in {"outcome_link", "counterfactual_analysis"}
            for span in spans
        ):
            missing.append(f"{premise}:causal_evidence_required")
        elif premise == "no_independent_sufficient_ground" and not any(
            span.reasoning_role == "alternative_ground_analysis"
            and (
                span.speaker in {"court", "reviewer"}
                or span.inference_status == "human_confirmed"
            )
            for span in spans
        ):
            missing.append(f"{premise}:alternative_ground_analysis_required")
    if record.outcome_causation != "determinative":
        missing.append("counterfactual_outcome_dependence:causation_not_determinative")
    return tuple(dict.fromkeys(missing))


def classify_application(record: ApplicationEvidenceRecord) -> ApplicationClassification:
    """Derive the compatibility status without merging the three source axes."""

    mismatches = _claim_level_mismatches(record)
    if mismatches:
        return ApplicationClassification(
            status="application_unclear",
            reason_codes=("claim_level_evidence_mismatch",),
            evidence_ids=mismatches,
        )

    if record.norm_use_status == "direct_reasoned_use":
        if _direct_application_is_proven(record):
            reasons = ["court_reasoned_direct_use"]
            if record.outcome_causation == "independent_sufficient_ground":
                reasons.append("independent_ground_preserved_on_causation_axis")
            if not record.human_review.is_named_approval:
                reasons.append("human_review_pending")
            return ApplicationClassification(
                status="explicitly_applied",
                compatibility_aliases=("directly_applied",),
                reason_codes=tuple(reasons),
                evidence_ids=tuple(span.evidence_id for span in record.evidence),
            )
        return ApplicationClassification(
            status="application_unclear",
            reason_codes=("direct_application_evidence_incomplete",),
        )

    if _affirmative_non_application_is_proven(record):
        assert record.affirmative_non_application is not None
        return ApplicationClassification(
            status="not_applied",
            reason_codes=(record.affirmative_non_application.reason,),
            evidence_ids=record.affirmative_non_application.evidence_ids,
        )

    if record.norm_use_status == "reasoned_rejection" and _role_is_proven(
        record, "express_non_use"
    ):
        return ApplicationClassification(
            status="not_applied",
            reason_codes=("express_non_use",),
            evidence_ids=tuple(
                span.evidence_id
                for span in record.evidence
                if span.reasoning_role == "express_non_use"
            ),
        )

    if record.outcome_causation == "independent_sufficient_ground" and _role_is_proven(
        record,
        "independent_ground",
        speakers=frozenset({"court", "disposition"}),
    ):
        return ApplicationClassification(
            status="not_applied",
            reason_codes=("complete_independent_ground",),
            evidence_ids=tuple(
                span.evidence_id
                for span in record.evidence
                if span.reasoning_role == "independent_ground"
            ),
        )

    if record.norm_use_status == "reasoning_linked_implicit":
        missing = _implicit_missing_premises(record)
        if not missing:
            reasons = ["conjunctive_implicit_proof_complete"]
            if not record.human_review.is_named_approval:
                reasons.append("human_review_pending")
            return ApplicationClassification(
                status="implicitly_applied_proven",
                reason_codes=tuple(reasons),
                evidence_ids=tuple(
                    evidence_id
                    for proof in record.implicit_premises
                    for evidence_id in proof.evidence_ids
                ),
            )
        return ApplicationClassification(
            status="application_unclear",
            missing_premises=missing,
            reason_codes=("implicit_application_not_proven",),
        )

    if record.norm_use_status == "party_only":
        return ApplicationClassification(
            status="application_unclear",
            reason_codes=("court_reasoning_not_proven",),
            evidence_ids=tuple(span.evidence_id for span in record.evidence),
        )
    if record.norm_use_status == "quoted_authority_only":
        return ApplicationClassification(
            status="application_unclear",
            reason_codes=("quoted_authority_is_not_court_application",),
        )
    if record.norm_use_status == "mentioned_only":
        return ApplicationClassification(
            status="application_unclear",
            reason_codes=("mention_is_discovery_only",),
        )
    return ApplicationClassification(
        status="application_unclear",
        reason_codes=("silence_is_not_non_application",),
    )


def _same_chain_scope(records: Sequence[ApplicationEvidenceRecord]) -> bool:
    first = records[0]
    return all(
        record.claim_id == first.claim_id
        and record.norm_id == first.norm_id
        and record.norm_version_id == first.norm_version_id
        for record in records
    )


def assess_application_chain(
    records: Sequence[ApplicationEvidenceRecord],
) -> ChainAssessment:
    """Assess the final-stage survival without inheriting a lower finding by silence."""

    if not records:
        return ChainAssessment(
            status="unclear",
            final_record_id=None,
            reason_codes=("no_stage_records",),
        )
    ordered = tuple(sorted(records, key=lambda item: item.stage_order))
    record_content_fingerprints = tuple(
        (record.record_id, application_record_content_fingerprint(record))
        for record in ordered
    )

    def assessment(**values: Any) -> ChainAssessment:
        return ChainAssessment(
            **values,
            record_content_fingerprints=record_content_fingerprints,
        )

    final = ordered[-1]
    record_ids = tuple(record.record_id for record in ordered)
    if len(record_ids) != len(set(record_ids)):
        return assessment(
            status="unclear",
            final_record_id=final.record_id,
            reason_codes=("duplicate_chain_record_id",),
        )
    if not _same_chain_scope(ordered):
        return assessment(
            status="unclear",
            final_record_id=final.record_id,
            reason_codes=("chain_scope_mismatch",),
        )
    classifications = {record.record_id: classify_application(record) for record in ordered}
    positive = {
        record_id
        for record_id, result in classifications.items()
        if result.status in {"explicitly_applied", "implicitly_applied_proven"}
    }
    earlier_positive = tuple(
        record.record_id for record in ordered[:-1] if record.record_id in positive
    )
    final_result = classifications[final.record_id]

    if len(ordered) == 1:
        if final.record_id in positive and final.outcome_causation != "independent_sufficient_ground":
            return assessment(
                status="survived",
                final_record_id=final.record_id,
                supporting_record_ids=(final.record_id,),
                reason_codes=("application_proven_in_final_act",),
            )
        return assessment(
            status="unclear",
            final_record_id=final.record_id,
            supporting_record_ids=tuple(positive),
            reason_codes=("final_application_does_not_survive",),
        )

    if final.relation_to_prior == "express_incorporation":
        incorporation_evidence = tuple(
            span.evidence_id
            for span in final.evidence
            if span.reasoning_role == "incorporation"
            and span.speaker == "court"
            and span.has_full_act_locator
        )
        incorporated = tuple(
            record_id
            for record_id in final.incorporated_record_ids
            if record_id in earlier_positive
        )
        if incorporation_evidence and incorporated:
            return assessment(
                status="incorporated",
                final_record_id=final.record_id,
                supporting_record_ids=incorporated + (final.record_id,),
                evidence_ids=incorporation_evidence,
                reason_codes=("express_incorporation_proven",),
            )
        return assessment(
            status="unclear",
            final_record_id=final.record_id,
            supporting_record_ids=earlier_positive,
            reason_codes=("incorporation_locator_or_source_missing",),
        )

    if final.relation_to_prior == "affirmance_only" and final.record_id not in positive:
        return assessment(
            status="unclear",
            final_record_id=final.record_id,
            supporting_record_ids=earlier_positive,
            reason_codes=("affirmance_without_incorporation",),
        )

    independent_ground_evidence = tuple(
        span.evidence_id
        for span in final.evidence
        if span.reasoning_role == "independent_ground"
        and span.has_full_act_locator
        and span.speaker in {"court", "disposition"}
    )
    if earlier_positive and (
        final.relation_to_prior == "superseding_ground"
        or (
            final_result.status == "not_applied"
            and final.outcome_causation == "independent_sufficient_ground"
        )
    ):
        if final.outcome_causation == "independent_sufficient_ground" and independent_ground_evidence:
            return assessment(
                status="superseded",
                final_record_id=final.record_id,
                supporting_record_ids=earlier_positive + (final.record_id,),
                evidence_ids=independent_ground_evidence,
                reason_codes=("later_independent_ground_supersedes",),
            )
        return assessment(
            status="unclear",
            final_record_id=final.record_id,
            supporting_record_ids=earlier_positive,
            reason_codes=("superseding_ground_not_proven",),
        )

    if final.relation_to_prior == "concurrent_ground":
        if (
            earlier_positive
            and final.record_id in positive
            and final.outcome_causation in {"determinative", "contributory"}
        ):
            return assessment(
                status="concurrent",
                final_record_id=final.record_id,
                supporting_record_ids=earlier_positive + (final.record_id,),
                reason_codes=("concurrent_operation_proven",),
            )
        return assessment(
            status="unclear",
            final_record_id=final.record_id,
            supporting_record_ids=earlier_positive,
            reason_codes=("concurrent_operation_not_proven",),
        )

    if final.record_id in positive:
        first_meaning = ordered[0].normative_meaning_id
        if final.normative_meaning_id != first_meaning and earlier_positive:
            return assessment(
                status="superseded",
                final_record_id=final.record_id,
                supporting_record_ids=earlier_positive + (final.record_id,),
                reason_codes=("normative_meaning_replaced",),
            )
        return assessment(
            status="survived",
            final_record_id=final.record_id,
            supporting_record_ids=(final.record_id,),
            reason_codes=("application_independently_proven_in_final_act",),
        )

    return assessment(
        status="unclear",
        final_record_id=final.record_id,
        supporting_record_ids=earlier_positive,
        reason_codes=("final_stage_application_unclear",),
    )


def evaluate_application_admissibility(
    record: ApplicationEvidenceRecord,
    chain: ChainAssessment,
    *,
    norm_version_status: str,
    version_evidence_ids: Sequence[str],
    preservation_rule_status: str,
    discovery_score: float | None = None,
    approval_ledger: TrustedApprovalLedger | None = None,
    approval_id: str | None = None,
    approval_as_of: str | None = None,
    norm_version_passport: Mapping[str, Any] | None = None,
    norm_version_official_evidence_verifier: EvidenceReferenceVerifier | Any | None = None,
    norm_version_approval_id: str | None = None,
    preservation_rule_evidence: Mapping[str, Any] | None = None,
    preservation_rule_evidence_verifier: EvidenceReferenceVerifier | Any | None = None,
    preservation_rule_approval_id: str | None = None,
) -> AdmissibilityDecision:
    """Fail-closed applied-norm gate; candidate scores are intentionally ignored."""

    del discovery_score, approval_as_of
    classification = classify_application(record)
    blockers: list[str] = []
    if classification.status not in {
        "explicitly_applied",
        "implicitly_applied_proven",
    }:
        blockers.append("judicial_norm_use_not_proven")
    version_evidence: tuple[str, ...] = ()
    if not isinstance(norm_version_passport, Mapping):
        blockers.append("norm_version_passport_required")
        blockers.append("norm_version_not_verified")
    else:
        passport_gate = assess_norm_version_passport(
            norm_version_passport,
            official_evidence_verifier=norm_version_official_evidence_verifier,
            approval_ledger=approval_ledger,
            approval_id=norm_version_approval_id,
        )
        version_evidence = tuple(
            sorted(
                {
                    str(item.get("evidence_id") or "")
                    for item in official_evidence_references(norm_version_passport)
                    if str(item.get("evidence_id") or "")
                }
            )
        )
        edition_ids = {
            str(item.get("edition_id") or "")
            for item in norm_version_passport.get("edition_segments") or ()
            if isinstance(item, Mapping)
        }
        if (
            norm_version_passport.get("norm_id") != record.norm_id
            or record.norm_version_id not in edition_ids
        ):
            blockers.append("norm_version_record_binding_mismatch")
        if passport_gate.get("filing_ready") is not True:
            blockers.append("norm_version_not_verified")
            blockers.extend(
                f"norm_version:{item}"
                for item in passport_gate.get("blockers") or ()
            )
    if record.outcome_causation not in {"determinative", "contributory"}:
        blockers.append("causal_harm_not_proven")

    preservation_blockers, preservation_evidence, verified_rule_status = (
        _preservation_rule_assessment(
            record,
            preservation_rule_evidence,
            evidence_verifier=preservation_rule_evidence_verifier,
            approval_ledger=approval_ledger,
            approval_id=preservation_rule_approval_id,
        )
    )
    blockers.extend(preservation_blockers)
    if verified_rule_status == "verified_required":
        if record.preservation_exhaustion != "raised_and_reviewed":
            blockers.append("preservation_or_exhaustion_not_satisfied")
    elif verified_rule_status != "verified_not_required":
        blockers.append("preservation_rule_not_verified")
    if chain.status not in {"survived", "incorporated", "concurrent"}:
        blockers.append("application_does_not_survive_final_chain")
    elif record.record_id not in chain.supporting_record_ids:
        blockers.append("record_not_supported_by_chain")
    else:
        chain_fingerprints = dict(chain.record_content_fingerprints)
        required_chain_record_ids = {
            str(chain.final_record_id or ""),
            *chain.supporting_record_ids,
        } - {""}
        if not required_chain_record_ids or not required_chain_record_ids.issubset(
            chain_fingerprints
        ):
            blockers.append("chain_content_fingerprints_missing")
        elif chain_fingerprints.get(record.record_id) != (
            application_record_content_fingerprint(record)
        ):
            blockers.append("record_content_fingerprint_mismatch")
    approval_request = application_review_approval_request(
        record,
        chain,
        norm_version_status=norm_version_status,
        version_evidence_ids=version_evidence_ids,
        preservation_rule_status=preservation_rule_status,
        norm_version_passport=norm_version_passport,
        norm_version_approval_id=norm_version_approval_id,
        preservation_rule_evidence=preservation_rule_evidence,
        preservation_rule_approval_id=preservation_rule_approval_id,
    )
    approval_validation: Mapping[str, Any] = {
        "valid": False,
        "reason_code": "trusted_approval_required",
        "approval": None,
    }
    if approval_ledger is not None and str(approval_id or "").strip():
        approval_validation = approval_ledger.validate_approval(
            str(approval_id),
            **approval_request,
        )
    if approval_validation.get("valid") is not True:
        blockers.append("human_application_review_required")
        reason_code = str(approval_validation.get("reason_code") or "approval_invalid")
        blockers.append(f"trusted_application_{reason_code}")
    blockers = list(dict.fromkeys(blockers))
    trusted_approval = approval_validation.get("approval") or {}
    return AdmissibilityDecision(
        passed=not blockers,
        blockers=tuple(blockers),
        application_status=classification.status,
        evidence_map={
            "application": classification.evidence_ids,
            "version": version_evidence,
            "preservation": preservation_evidence,
            "chain": chain.evidence_ids,
        },
        trusted_approval_id=(
            str(trusted_approval.get("approval_id")) if trusted_approval else None
        ),
        trusted_reviewer=(
            str(trusted_approval.get("actor_display_name")) if trusted_approval else None
        ),
    )


__all__ = [
    "AffirmativeNonApplication",
    "AdmissibilityDecision",
    "ApplicationClassification",
    "ApplicationEvidenceRecord",
    "ChainAssessment",
    "EvidenceSpan",
    "FullActLocator",
    "HumanReview",
    "ImplicitPremiseProof",
    "application_record_content_fingerprint",
    "application_record_from_dict",
    "application_record_review_payload",
    "application_review_approval_request",
    "assess_application_chain",
    "build_preservation_rule_evidence",
    "classify_application",
    "evaluate_application_admissibility",
    "normalize_application_status",
    "preservation_rule_content_fingerprint",
    "preservation_rule_review_approval_request",
    "preservation_rule_review_payload",
]
