from __future__ import annotations

import copy
import re
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from .source_registry import load_norm_version_provider_registry
from .storage import stable_id, utc_now
from .trusted_approvals import TrustedApprovalLedger


_OFFICIAL_CLASSES = {"official_primary", "official_derivative"}
_TIMEPOINT_KINDS = {"material_event", "procedural_act", "judicial_act", "filing"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PASSPORT_FIELDS = {
    "schema_version",
    "norm_id",
    "canonical_citation",
    "issuing_authority",
    "official_publication_identity",
    "amendment_acts",
    "legal_timepoints",
    "edition_segments",
    "provider_assertions",
    "unresolved_conflicts",
    "human_review",
    "created_at",
    "updated_at",
    "passport_id",
    "timepoint_edition_map",
    "gate",
    "passport_revision_id",
}
_EDITION_FIELDS = {
    "edition_id",
    "effective_from",
    "effective_to_exclusive",
    "controlling_text",
    "official_text_sha256",
    "official_anchor",
    "governing_reason",
    "transitional_provisions",
}
_TIMEPOINT_FIELDS = {"timepoint_id", "kind", "date", "reason", "source_evidence_id"}
OfficialEvidenceVerifier = Callable[[Mapping[str, Any]], bool | Mapping[str, Any]]


def _date(value: Any, *, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO date") from exc


def _segment_contains(segment: Mapping[str, Any], point: date) -> bool:
    start = _date(segment.get("effective_from"), field="effective_from")
    end_raw = segment.get("effective_to_exclusive")
    end = _date(end_raw, field="effective_to_exclusive") if end_raw else None
    return start <= point and (end is None or point < end)


def edition_for_date(passport: Mapping[str, Any], value: Any) -> Optional[Dict[str, Any]]:
    point = _date(value, field="date")
    matches = [dict(item) for item in passport.get("edition_segments") or [] if _segment_contains(item, point)]
    return matches[0] if len(matches) == 1 else None


def _mapping_items(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _structural_blockers(passport: Mapping[str, Any]) -> tuple[list[str], list[Dict[str, Any]]]:
    blockers: list[str] = []
    mapping: list[Dict[str, Any]] = []
    for field in sorted(set(passport) - _PASSPORT_FIELDS):
        blockers.append(f"unexpected_field:{field}")
    if passport.get("schema_version") != "1.0.0":
        blockers.append("invalid_schema_version")
    required = ("norm_id", "canonical_citation", "issuing_authority", "official_publication_identity")
    for field in required:
        if not passport.get(field):
            blockers.append(f"missing_field:{field}")
    publication = passport.get("official_publication_identity")
    if not isinstance(publication, Mapping) or not str(
        publication.get("source_evidence_id") or ""
    ).strip():
        blockers.append("unsubstantiated_official_publication")
    if not str(passport.get("created_at") or "").strip():
        blockers.append("missing_field:created_at")
    if not isinstance(passport.get("human_review"), Mapping):
        blockers.append("invalid_human_review_diagnostic")
    if not isinstance(passport.get("provider_assertions"), list):
        blockers.append("invalid_provider_assertions")
    if not isinstance(passport.get("unresolved_conflicts"), list):
        blockers.append("invalid_unresolved_conflicts")

    raw_segments = passport.get("edition_segments")
    segments = _mapping_items(raw_segments)
    if raw_segments is not None and (
        not isinstance(raw_segments, Sequence)
        or isinstance(raw_segments, (str, bytes))
        or len(segments) != len(raw_segments)
    ):
        blockers.append("invalid_edition_segments")
    if not segments:
        blockers.append("missing_edition_segments")
    segment_ids: set[str] = set()
    sorted_segments: list[Mapping[str, Any]] = []
    for segment in segments:
        edition_id = str(segment.get("edition_id") or "")
        for field in sorted(set(segment) - _EDITION_FIELDS):
            blockers.append(f"unexpected_edition_field:{edition_id or 'unknown'}:{field}")
        if not edition_id:
            blockers.append("missing_edition_id")
            continue
        if edition_id in segment_ids:
            blockers.append(f"duplicate_edition_id:{edition_id}")
        segment_ids.add(edition_id)
        try:
            start = _date(segment.get("effective_from"), field=f"{edition_id}.effective_from")
            end_raw = segment.get("effective_to_exclusive")
            end = _date(end_raw, field=f"{edition_id}.effective_to_exclusive") if end_raw else None
            if end is not None and end <= start:
                blockers.append(f"invalid_edition_interval:{edition_id}")
            else:
                sorted_segments.append(segment)
        except ValueError:
            blockers.append(f"invalid_edition_interval:{edition_id}")
        anchor = segment.get("official_anchor") or {}
        if not isinstance(anchor, Mapping) or (
            anchor.get("authority_class") not in _OFFICIAL_CLASSES
            or not anchor.get("source_evidence_id")
        ):
            blockers.append(f"unofficial_anchor:{edition_id}")
        if not _SHA256_RE.fullmatch(str(segment.get("official_text_sha256") or "")):
            blockers.append(f"invalid_official_text_hash:{edition_id}")
        if not str(segment.get("controlling_text") or "").strip():
            blockers.append(f"missing_controlling_text:{edition_id}")
        if not str(segment.get("governing_reason") or "").strip():
            blockers.append(f"missing_governing_reason:{edition_id}")
        if not isinstance(segment.get("transitional_provisions"), list):
            blockers.append(f"missing_transitional_review:{edition_id}")
        else:
            for index, provision in enumerate(segment.get("transitional_provisions") or []):
                if not isinstance(provision, Mapping) or not str(
                    provision.get("source_evidence_id") or ""
                ).strip():
                    blockers.append(
                        f"unsubstantiated_transitional_provision:{edition_id}:{index}"
                    )

    sorted_segments.sort(key=lambda item: str(item.get("effective_from") or ""))
    for previous, current in zip(sorted_segments, sorted_segments[1:]):
        previous_end = previous.get("effective_to_exclusive")
        current_start = current.get("effective_from")
        if previous_end is None or (
            previous_end and current_start and _date(current_start, field="effective_from") < _date(previous_end, field="effective_to_exclusive")
        ):
            blockers.append(f"overlapping_editions:{previous.get('edition_id')}:{current.get('edition_id')}")

    timepoint_ids: set[str] = set()
    timepoint_kinds: set[str] = set()
    raw_timepoints = passport.get("legal_timepoints")
    timepoints = _mapping_items(raw_timepoints)
    if raw_timepoints is not None and (
        not isinstance(raw_timepoints, Sequence)
        or isinstance(raw_timepoints, (str, bytes))
        or len(timepoints) != len(raw_timepoints)
    ):
        blockers.append("invalid_legal_timepoints")
    if not timepoints:
        blockers.append("missing_legal_timepoints")
    for point in timepoints:
        timepoint_id = str(point.get("timepoint_id") or "")
        for field in sorted(set(point) - _TIMEPOINT_FIELDS):
            blockers.append(
                f"unexpected_timepoint_field:{timepoint_id or 'unknown'}:{field}"
            )
        if not timepoint_id:
            blockers.append("missing_timepoint_id")
            continue
        if timepoint_id in timepoint_ids:
            blockers.append(f"duplicate_timepoint_id:{timepoint_id}")
        timepoint_ids.add(timepoint_id)
        if point.get("kind") not in _TIMEPOINT_KINDS:
            blockers.append(f"invalid_timepoint_kind:{timepoint_id}")
        else:
            timepoint_kinds.add(str(point.get("kind")))
        if not point.get("reason") or not point.get("source_evidence_id"):
            blockers.append(f"unsubstantiated_timepoint:{timepoint_id}")
        try:
            point_date = _date(point.get("date"), field=f"{timepoint_id}.date")
        except ValueError:
            blockers.append(f"invalid_timepoint_date:{timepoint_id}")
            continue
        matches = [item for item in sorted_segments if _segment_contains(item, point_date)]
        if len(matches) == 1:
            mapping.append(
                {
                    "timepoint_id": timepoint_id,
                    "date": point.get("date"),
                    "kind": point.get("kind"),
                    "edition_id": matches[0].get("edition_id"),
                }
            )
        elif not matches:
            blockers.append(f"uncovered_timepoint:{timepoint_id}")
        else:
            blockers.append(f"ambiguous_timepoint:{timepoint_id}")
    if "filing" not in timepoint_kinds:
        blockers.append("missing_filing_timepoint")

    if not isinstance(passport.get("amendment_acts"), list):
        blockers.append("missing_amendment_chain")
    else:
        for index, act in enumerate(passport.get("amendment_acts") or []):
            if not isinstance(act, Mapping) or not act.get("act_number") or not act.get("source_evidence_id"):
                blockers.append(f"unsubstantiated_amendment:{index}")

    raw_conflicts = passport.get("unresolved_conflicts")
    conflicts = raw_conflicts if isinstance(raw_conflicts, list) else []
    for conflict in conflicts:
        code = str(conflict.get("code") or "unspecified") if isinstance(conflict, Mapping) else "unspecified"
        blockers.append(f"unresolved_conflict:{code}")
    return sorted(set(blockers)), mapping


def _passport_identity(passport: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "norm_id": passport.get("norm_id"),
        "canonical_citation": passport.get("canonical_citation"),
        "official_publication_identity": passport.get("official_publication_identity"),
    }


def _expected_passport_id(passport: Mapping[str, Any]) -> str:
    return stable_id("norm-passport", _passport_identity(passport))


def norm_version_passport_review_payload(passport: Mapping[str, Any]) -> Dict[str, Any]:
    """Canonical substantive passport content; raw review projections are excluded."""

    return {
        key: copy.deepcopy(value)
        for key, value in passport.items()
        if key
        not in {
            "created_at",
            "updated_at",
            "human_review",
            "gate",
            "passport_id",
            "passport_revision_id",
        }
    }


def norm_version_passport_content_fingerprint(passport: Mapping[str, Any]) -> str:
    return stable_id(
        "norm-passport-content",
        norm_version_passport_review_payload(passport),
    )


def _revision_id(passport: Mapping[str, Any]) -> str:
    return stable_id(
        "norm-passport-revision",
        {
            "passport_id": _expected_passport_id(passport),
            "content_fingerprint": norm_version_passport_content_fingerprint(passport),
        },
    )


def official_evidence_references(passport: Mapping[str, Any]) -> list[Dict[str, Any]]:
    """Return the exact official-source references that a host verifier must resolve."""

    references: list[Dict[str, Any]] = []

    def add(
        role: str,
        evidence_id: Any,
        *,
        expected_content_sha256: Any = None,
        authority_class: Any = None,
    ) -> None:
        identifier = str(evidence_id or "").strip()
        if not identifier:
            return
        reference: Dict[str, Any] = {"role": role, "evidence_id": identifier}
        expected_hash = str(expected_content_sha256 or "").strip()
        if expected_hash:
            reference["expected_content_sha256"] = expected_hash
        if authority_class:
            reference["authority_class"] = str(authority_class)
        references.append(reference)

    publication = passport.get("official_publication_identity")
    if isinstance(publication, Mapping):
        add(
            "official_publication",
            publication.get("source_evidence_id"),
            expected_content_sha256=(
                publication.get("content_sha256")
                or publication.get("official_text_sha256")
            ),
            authority_class="official_primary",
        )
    for index, act in enumerate(_mapping_items(passport.get("amendment_acts"))):
        add(
            f"amendment_act:{index}",
            act.get("source_evidence_id"),
            expected_content_sha256=(act.get("content_sha256") or act.get("official_text_sha256")),
            authority_class=str(act.get("authority_class") or "official_primary"),
        )
    for segment in _mapping_items(passport.get("edition_segments")):
        edition_id = str(segment.get("edition_id") or "unknown")
        anchor = segment.get("official_anchor")
        if isinstance(anchor, Mapping):
            add(
                f"edition:{edition_id}",
                anchor.get("source_evidence_id"),
                expected_content_sha256=segment.get("official_text_sha256"),
                authority_class=anchor.get("authority_class"),
            )
        for index, provision in enumerate(
            _mapping_items(segment.get("transitional_provisions"))
        ):
            add(
                f"transitional_provision:{edition_id}:{index}",
                provision.get("source_evidence_id"),
                expected_content_sha256=(
                    provision.get("content_sha256")
                    or provision.get("official_text_sha256")
                ),
                authority_class=str(
                    provision.get("authority_class") or "official_primary"
                ),
            )
    return sorted(
        references,
        key=lambda item: (
            str(item.get("evidence_id") or ""),
            str(item.get("role") or ""),
            str(item.get("expected_content_sha256") or ""),
        ),
    )


def _repository_verification(
    repository: Any,
    reference: Mapping[str, Any],
) -> bool | Mapping[str, Any]:
    method = getattr(repository, "verify_official_evidence_reference", None)
    if callable(method):
        return method(reference)
    evidence_ledger = getattr(repository, "evidence", None)
    records_method = getattr(evidence_ledger, "records", None)
    authority_method = getattr(repository, "current_filing_authority", None)
    if not callable(records_method) or not callable(authority_method):
        return False
    evidence_id = str(reference.get("evidence_id") or "")
    matches = [
        item
        for item in records_method()
        if str(item.get("evidence_id") or "") == evidence_id
    ]
    if len(matches) != 1:
        return False
    record = matches[0]
    authority = authority_method(record)
    content_hashes = {
        str(record.get("content_sha256") or ""),
        str(record.get("official_text_sha256") or ""),
        str((record.get("raw_object") or {}).get("sha256") or ""),
        str((record.get("extracted_object") or {}).get("sha256") or ""),
    } - {""}
    expected_hash = str(reference.get("expected_content_sha256") or "")
    return {
        "verified": authority.get("filing_ready") is True
        and (not expected_hash or expected_hash in content_hashes),
        "evidence_id": evidence_id,
        "content_sha256": expected_hash if expected_hash in content_hashes else None,
    }


def _reference_verified(
    verifier: OfficialEvidenceVerifier | Any,
    reference: Mapping[str, Any],
) -> bool:
    try:
        result = (
            verifier(reference)
            if callable(verifier)
            else _repository_verification(verifier, reference)
        )
    except Exception:
        return False
    if result is True:
        return True
    if not isinstance(result, Mapping):
        return False
    if result.get("verified") is not True and result.get("filing_ready") is not True:
        return False
    returned_id = str(result.get("evidence_id") or "")
    if returned_id != str(reference.get("evidence_id") or ""):
        return False
    expected_hash = str(reference.get("expected_content_sha256") or "")
    if expected_hash:
        returned_hash = str(
            result.get("content_sha256")
            or result.get("official_text_sha256")
            or result.get("sha256")
            or ""
        )
        if returned_hash != expected_hash:
            return False
    return True


def verify_official_evidence_reference(
    verifier: OfficialEvidenceVerifier | Any,
    reference: Mapping[str, Any],
) -> bool:
    """Use a host-supplied callback or repository to resolve one exact reference."""

    return _reference_verified(verifier, reference)


def _integrity_blockers(
    passport: Mapping[str, Any],
    expected_mapping: Sequence[Mapping[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if passport.get("passport_id") != _expected_passport_id(passport):
        blockers.append("passport_id_mismatch")
    if passport.get("timepoint_edition_map") != list(expected_mapping):
        blockers.append("timepoint_edition_map_mismatch")
    if passport.get("passport_revision_id") != _revision_id(passport):
        blockers.append("passport_revision_id_mismatch")
    return blockers


def norm_version_review_approval_request(
    passport: Mapping[str, Any],
) -> Dict[str, Any]:
    """Build the exact filing-significant review binding for one passport revision."""

    bindings = {
        "passport_id": str(passport.get("passport_id") or ""),
        "passport_revision_id": str(passport.get("passport_revision_id") or ""),
        "content_fingerprint": norm_version_passport_content_fingerprint(passport),
        "official_evidence_references": official_evidence_references(passport),
    }
    return {
        "purpose": "application",
        "subject_type": "norm_version_passport",
        "subject_id": bindings["passport_id"],
        "fingerprint": stable_id("norm-version-review", bindings),
        "bindings": bindings,
    }


def assess_norm_version_passport(
    passport: Mapping[str, Any],
    *,
    official_evidence_verifier: OfficialEvidenceVerifier | Any | None = None,
    approval_ledger: TrustedApprovalLedger | None = None,
    approval_id: str | None = None,
) -> Dict[str, Any]:
    structural_blockers, expected_mapping = _structural_blockers(passport)
    integrity_blockers = _integrity_blockers(passport, expected_mapping)
    evidence_blockers: list[str] = []
    references = official_evidence_references(passport)
    if not references:
        evidence_blockers.append("official_evidence_references_missing")
    elif official_evidence_verifier is None:
        evidence_blockers.append("official_evidence_verifier_required")
    else:
        for reference in references:
            if not _reference_verified(official_evidence_verifier, reference):
                evidence_blockers.append(
                    "official_evidence_not_verified:"
                    f"{reference['evidence_id']}:{reference['role']}"
                )

    approval_validation: Mapping[str, Any] = {
        "valid": False,
        "reason_code": "approval_required",
        "approval": None,
    }
    if approval_ledger is not None and str(approval_id or "").strip():
        approval_validation = approval_ledger.validate_approval(
            str(approval_id),
            **norm_version_review_approval_request(passport),
        )
    approval_blockers: list[str] = []
    if approval_validation.get("valid") is not True:
        if approval_ledger is None or not str(approval_id or "").strip():
            approval_blockers.append("trusted_norm_version_approval_required")
        else:
            approval_blockers.append(
                "trusted_norm_version_"
                f"{approval_validation.get('reason_code') or 'approval_invalid'}"
            )

    hard_blockers = structural_blockers + integrity_blockers + evidence_blockers
    blockers = sorted(set(hard_blockers + approval_blockers))
    approved = approval_validation.get("valid") is True
    if hard_blockers:
        status = "blocked"
    elif approved:
        status = "passed"
    else:
        status = "ready_for_human_review"
    return {
        "status": status,
        "blockers": blockers,
        "human_review_required": True,
        "human_review_status": "approved" if approved else "pending",
        "filing_ready": status == "passed",
    }


def build_norm_version_passport(payload: Mapping[str, Any]) -> Dict[str, Any]:
    passport = copy.deepcopy(dict(payload))
    passport["schema_version"] = str(passport.get("schema_version") or "1.0.0")
    passport.setdefault("amendment_acts", [])
    passport.setdefault("legal_timepoints", [])
    passport.setdefault("edition_segments", [])
    passport.setdefault("provider_assertions", [])
    passport.setdefault("unresolved_conflicts", [])
    passport.setdefault("human_review", {"status": "pending"})
    passport.setdefault("created_at", utc_now())
    passport["passport_id"] = _expected_passport_id(passport)
    blockers, mapping = _structural_blockers(passport)
    passport["timepoint_edition_map"] = mapping
    passport["passport_revision_id"] = _revision_id(passport)
    passport["gate"] = assess_norm_version_passport(passport)
    return passport


def reconcile_provider_assertions(
    passport: Mapping[str, Any],
    assertions: Sequence[Mapping[str, Any]],
    *,
    provider_registry_path: Optional[Path] = None,
) -> Dict[str, Any]:
    result = copy.deepcopy(dict(passport))
    provider_registry = load_norm_version_provider_registry(provider_registry_path)
    allowed = {str(item["provider_id"]) for item in provider_registry["providers"]}
    segments = {str(item.get("edition_id")): item for item in result.get("edition_segments") or []}
    reconciled = list(result.get("provider_assertions") or [])
    conflicts = list(result.get("unresolved_conflicts") or [])

    for raw_assertion in assertions:
        assertion = copy.deepcopy(dict(raw_assertion))
        provider_id = str(assertion.get("provider_id") or "")
        if provider_id not in allowed:
            raise ValueError(f"unknown norm-version provider: {provider_id}")
        edition_id = str(assertion.get("edition_id") or "")
        official = segments.get(edition_id)
        assertion["authority_class"] = "discovery_only"
        assertion["official_anchor_required"] = True
        if official is None:
            assertion["reconciliation_status"] = "official_edition_missing"
            conflicts.append(
                {
                    "code": "provider_edition_without_official_match",
                    "provider_id": provider_id,
                    "edition_id": edition_id,
                    "provider_value": assertion,
                    "official_value": None,
                }
            )
        else:
            official_hash = str(official.get("official_text_sha256") or "")
            provider_hash = str(assertion.get("text_sha256") or "")
            intervals_match = (
                assertion.get("effective_from") == official.get("effective_from")
                and assertion.get("effective_to_exclusive") == official.get("effective_to_exclusive")
            )
            if provider_hash == official_hash and intervals_match:
                assertion["reconciliation_status"] = "matched_official"
            else:
                assertion["reconciliation_status"] = "conflict"
                conflicts.append(
                    {
                        "code": "provider_official_mismatch",
                        "provider_id": provider_id,
                        "edition_id": edition_id,
                        "official_value": official_hash,
                        "provider_value": provider_hash,
                        "official_interval": {
                            "effective_from": official.get("effective_from"),
                            "effective_to_exclusive": official.get("effective_to_exclusive"),
                        },
                        "provider_interval": {
                            "effective_from": assertion.get("effective_from"),
                            "effective_to_exclusive": assertion.get("effective_to_exclusive"),
                        },
                    }
                )
        assertion["assertion_id"] = stable_id("norm-provider-assertion", assertion)
        reconciled.append(assertion)

    result["provider_assertions"] = reconciled
    result["unresolved_conflicts"] = conflicts
    result["updated_at"] = utc_now()
    _blockers, mapping = _structural_blockers(result)
    result["timepoint_edition_map"] = mapping
    result["passport_revision_id"] = _revision_id(result)
    result["gate"] = assess_norm_version_passport(result)
    return result
