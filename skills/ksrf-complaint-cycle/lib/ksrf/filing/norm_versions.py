from __future__ import annotations

import copy
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from .source_registry import load_norm_version_provider_registry
from .storage import stable_id, utc_now


_OFFICIAL_CLASSES = {"official_primary", "official_derivative"}
_TIMEPOINT_KINDS = {"material_event", "procedural_act", "judicial_act", "filing"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def _structural_blockers(passport: Mapping[str, Any]) -> tuple[list[str], list[Dict[str, Any]]]:
    blockers: list[str] = []
    mapping: list[Dict[str, Any]] = []
    required = ("norm_id", "canonical_citation", "issuing_authority", "official_publication_identity")
    for field in required:
        if not passport.get(field):
            blockers.append(f"missing_field:{field}")

    segments = list(passport.get("edition_segments") or [])
    if not segments:
        blockers.append("missing_edition_segments")
    segment_ids: set[str] = set()
    sorted_segments: list[Mapping[str, Any]] = []
    for segment in segments:
        edition_id = str(segment.get("edition_id") or "")
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
            sorted_segments.append(segment)
        except ValueError:
            blockers.append(f"invalid_edition_interval:{edition_id}")
        anchor = segment.get("official_anchor") or {}
        if anchor.get("authority_class") not in _OFFICIAL_CLASSES or not anchor.get("source_evidence_id"):
            blockers.append(f"unofficial_anchor:{edition_id}")
        if not _SHA256_RE.fullmatch(str(segment.get("official_text_sha256") or "")):
            blockers.append(f"invalid_official_text_hash:{edition_id}")
        if not str(segment.get("governing_reason") or "").strip():
            blockers.append(f"missing_governing_reason:{edition_id}")
        if not isinstance(segment.get("transitional_provisions"), list):
            blockers.append(f"missing_transitional_review:{edition_id}")

    sorted_segments.sort(key=lambda item: str(item.get("effective_from") or ""))
    for previous, current in zip(sorted_segments, sorted_segments[1:]):
        previous_end = previous.get("effective_to_exclusive")
        current_start = current.get("effective_from")
        if previous_end is None or (
            previous_end and current_start and _date(current_start, field="effective_from") < _date(previous_end, field="effective_to_exclusive")
        ):
            blockers.append(f"overlapping_editions:{previous.get('edition_id')}:{current.get('edition_id')}")

    timepoint_ids: set[str] = set()
    timepoints = list(passport.get("legal_timepoints") or [])
    if not timepoints:
        blockers.append("missing_legal_timepoints")
    for point in timepoints:
        timepoint_id = str(point.get("timepoint_id") or "")
        if not timepoint_id:
            blockers.append("missing_timepoint_id")
            continue
        if timepoint_id in timepoint_ids:
            blockers.append(f"duplicate_timepoint_id:{timepoint_id}")
        timepoint_ids.add(timepoint_id)
        if point.get("kind") not in _TIMEPOINT_KINDS:
            blockers.append(f"invalid_timepoint_kind:{timepoint_id}")
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

    if not isinstance(passport.get("amendment_acts"), list):
        blockers.append("missing_amendment_chain")
    else:
        for index, act in enumerate(passport.get("amendment_acts") or []):
            if not act.get("act_number") or not act.get("source_evidence_id"):
                blockers.append(f"unsubstantiated_amendment:{index}")

    for conflict in passport.get("unresolved_conflicts") or []:
        code = str(conflict.get("code") or "unspecified") if isinstance(conflict, Mapping) else "unspecified"
        blockers.append(f"unresolved_conflict:{code}")
    return sorted(set(blockers)), mapping


def assess_norm_version_passport(passport: Mapping[str, Any]) -> Dict[str, Any]:
    blockers, _mapping = _structural_blockers(passport)
    review = passport.get("human_review") or {}
    approved = (
        review.get("status") == "approved"
        and bool(review.get("reviewer"))
        and bool(review.get("reviewed_at"))
    )
    if blockers:
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


def _revision_id(passport: Mapping[str, Any]) -> str:
    return stable_id(
        "norm-passport-revision",
        {
            key: value
            for key, value in passport.items()
            if key not in {"gate", "passport_revision_id", "created_at", "updated_at"}
        },
    )


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
    passport["passport_id"] = stable_id(
        "norm-passport",
        {
            "norm_id": passport.get("norm_id"),
            "canonical_citation": passport.get("canonical_citation"),
            "official_publication_identity": passport.get("official_publication_identity"),
        },
    )
    blockers, mapping = _structural_blockers(passport)
    passport["timepoint_edition_map"] = mapping
    passport["gate"] = assess_norm_version_passport(passport)
    passport["passport_revision_id"] = _revision_id(passport)
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
    result["gate"] = assess_norm_version_passport(result)
    result["passport_revision_id"] = _revision_id(result)
    return result
