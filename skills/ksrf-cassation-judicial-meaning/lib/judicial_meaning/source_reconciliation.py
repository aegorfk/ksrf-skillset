"""Fail-closed reconciliation of versioned cassation source enumerators."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import date, datetime, timezone
from typing import Any, Iterable
from urllib.parse import urlparse


class SourceReconciliationError(ValueError):
    """Base error for invalid reconciliation input."""


class EnumeratorManifestError(SourceReconciliationError):
    """An enumerator did not declare a reproducible scope and closure rule."""


class PromotionGateError(SourceReconciliationError):
    """Discovery material lacks verified official identity evidence."""


_REQUIRED_MANIFEST_FIELDS = {
    "enumerator_id",
    "version",
    "source_role",
    "institutional_regime",
    "applicable_from",
    "applicable_to",
    "courts",
    "enumeration_unit",
    "closure_rule",
    "denominator_scope",
    "adapter_id",
    "configured",
}
_SUCCESS_STATUSES = {"success_empty", "success_nonempty"}
_SNAPSHOT_ID = re.compile(r"^snapshot-sha256:[0-9a-f]{64}$")
_TERMINAL_SNAPSHOT_SHA256 = re.compile(r"^(?:snapshot-sha256:)?[0-9a-f]{64}$")
_PROMOTION_ID = re.compile(r"^enumerator-promotion-sha256:[0-9a-f]{64}$")
_ENUMERATOR_VERIFICATION_GATES = (
    "registry_verified",
    "applicability_verified",
    "identity_verified",
    "terminal_states_verified",
    "fixtures_passed",
    "resume_passed",
    "live_smoke_passed",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(prefix: str, value: Any) -> str:
    payload = _canonical_json(value).encode("utf-8")
    return f"{prefix}-sha256:{hashlib.sha256(payload).hexdigest()}"


def _date(value: str | None, *, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise EnumeratorManifestError(f"{field} must be an ISO date or null") from exc


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _promotion_payload(
    manifest: dict[str, Any],
    *,
    verification: dict[str, Any],
    reviewer: str,
    reviewed_at: str,
) -> dict[str, Any]:
    base_manifest = deepcopy(manifest)
    base_manifest.pop("promotion", None)
    return {
        "candidate_enumerator_id": base_manifest["enumerator_id"],
        "candidate_version": base_manifest["version"],
        "manifest": base_manifest,
        "verification": deepcopy(verification),
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
    }


def _validate_promotion_certificate(manifest: dict[str, Any]) -> None:
    promotion = manifest.get("promotion")
    if promotion is None:
        return
    if not isinstance(promotion, dict):
        raise EnumeratorManifestError("promotion must be an object")
    if promotion.get("status") != "official_enumerator_verified":
        raise EnumeratorManifestError(
            "Configured enumerator promotion status must be official_enumerator_verified"
        )
    promotion_id = promotion.get("promotion_id")
    if not isinstance(promotion_id, str) or not _PROMOTION_ID.fullmatch(promotion_id):
        raise EnumeratorManifestError("Configured enumerator promotion_id is invalid")
    verification = promotion.get("verification")
    if not isinstance(verification, dict):
        raise EnumeratorManifestError("Configured enumerator promotion requires verification")
    failed = [
        gate for gate in _ENUMERATOR_VERIFICATION_GATES if verification.get(gate) is not True
    ]
    if failed:
        raise EnumeratorManifestError(
            "Configured enumerator promotion gates are incomplete: " + ", ".join(failed)
        )
    if verification.get("adapter_id") != manifest.get("adapter_id"):
        raise EnumeratorManifestError("Promotion adapter_id does not match manifest")
    if verification.get("closure_rule") != manifest.get("closure_rule"):
        raise EnumeratorManifestError("Promotion closure_rule does not match manifest")
    reviewer = promotion.get("reviewer")
    reviewed_at = promotion.get("reviewed_at")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise EnumeratorManifestError("Configured enumerator promotion requires reviewer")
    if not isinstance(reviewed_at, str):
        raise EnumeratorManifestError("Configured enumerator promotion requires reviewed_at")
    try:
        datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EnumeratorManifestError("Promotion reviewed_at must be an ISO timestamp") from exc
    expected = _digest(
        "enumerator-promotion",
        _promotion_payload(
            manifest,
            verification=verification,
            reviewer=reviewer.strip(),
            reviewed_at=reviewed_at,
        ),
    )
    if promotion_id != expected:
        raise EnumeratorManifestError("Configured enumerator promotion digest does not match")


def _has_verified_promotion(manifest: dict[str, Any]) -> bool:
    promotion = manifest.get("promotion")
    return (
        isinstance(promotion, dict)
        and promotion.get("status") == "official_enumerator_verified"
        and isinstance(promotion.get("promotion_id"), str)
        and bool(_PROMOTION_ID.fullmatch(promotion["promotion_id"]))
    )


def validate_enumerator_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate and copy one source-enumerator contract."""

    if not isinstance(manifest, dict):
        raise EnumeratorManifestError("Enumerator manifest must be an object.")
    missing = sorted(_REQUIRED_MANIFEST_FIELDS - set(manifest))
    if missing:
        raise EnumeratorManifestError("Enumerator manifest is missing: " + ", ".join(missing))
    clean = deepcopy(manifest)
    for field in (
        "enumerator_id",
        "version",
        "source_role",
        "institutional_regime",
        "enumeration_unit",
        "denominator_scope",
    ):
        if not isinstance(clean.get(field), str) or not clean[field].strip():
            raise EnumeratorManifestError(f"{field} must be a non-empty string")
        clean[field] = clean[field].strip()
    if clean["source_role"] not in {"official", "official_unconfigured"}:
        raise EnumeratorManifestError("Enumerator source_role must be official.")
    if not isinstance(clean.get("configured"), bool):
        raise EnumeratorManifestError("configured must be boolean")
    if not isinstance(clean.get("courts"), list) or any(
        not isinstance(court, str) or not court.strip() for court in clean["courts"]
    ):
        raise EnumeratorManifestError("courts must be a list of non-empty court identifiers")
    clean["courts"] = [court.strip() for court in clean["courts"]]
    applicable_from = _date(clean.get("applicable_from"), field="applicable_from")
    applicable_to = _date(clean.get("applicable_to"), field="applicable_to")
    if applicable_from is not None and applicable_to is not None and applicable_from > applicable_to:
        raise EnumeratorManifestError("applicable_from must not be after applicable_to")
    if clean["configured"]:
        if not isinstance(clean.get("adapter_id"), str) or not clean["adapter_id"].strip():
            raise EnumeratorManifestError("Configured enumerator requires adapter_id")
        if not isinstance(clean.get("closure_rule"), str) or not clean["closure_rule"].strip():
            raise EnumeratorManifestError("Configured enumerator requires closure_rule")
        if not clean["courts"]:
            raise EnumeratorManifestError("Configured enumerator requires at least one court")
        clean["adapter_id"] = clean["adapter_id"].strip()
        clean["closure_rule"] = clean["closure_rule"].strip()
        _validate_promotion_certificate(clean)
    else:
        if clean.get("adapter_id") is not None:
            raise EnumeratorManifestError("Unconfigured enumerator must not claim an adapter_id")
        if clean.get("closure_rule") not in {None, ""}:
            raise EnumeratorManifestError("Unconfigured enumerator must not claim a closure rule")
        if clean.get("promotion") is not None:
            raise EnumeratorManifestError("Unconfigured enumerator must not claim promotion")
        clean["closure_rule"] = None
    return clean


def _overlaps(
    manifest: dict[str, Any], requested_from: date, requested_to: date
) -> bool:
    start = _date(manifest.get("applicable_from"), field="applicable_from") or date.min
    end = _date(manifest.get("applicable_to"), field="applicable_to") or date.max
    return start <= requested_to and end >= requested_from


def _normalise_route_coverage(
    manifest: dict[str, Any], raw: dict[str, Any] | None, *, applicable: bool
) -> dict[str, Any]:
    if not applicable:
        return {
            "status": "not_applicable",
            "total_segments": 0,
            "successful_segments": 0,
            "unresolved_segments": 0,
            "statuses": {},
            "denominator_scope": manifest["denominator_scope"],
        }
    if not manifest["configured"]:
        return {
            "status": "not_configured",
            "total_segments": 0,
            "successful_segments": 0,
            "unresolved_segments": 0,
            "statuses": {},
            "denominator_scope": manifest["denominator_scope"],
        }
    if raw is None:
        closure_blockers = ["coverage_not_supplied"]
        if not _has_verified_promotion(manifest):
            closure_blockers.append("enumerator_contract_not_promoted")
        return {
            "status": "observed_only",
            "total_segments": 0,
            "successful_segments": 0,
            "unresolved_segments": 0,
            "statuses": {},
            "denominator_scope": manifest["denominator_scope"],
            "reason": "coverage_not_supplied",
            "closure_blockers": closure_blockers,
        }
    try:
        total = int(raw.get("total_segments", 0))
        successful = int(raw.get("successful_segments", 0))
    except (TypeError, ValueError) as exc:
        raise SourceReconciliationError("Route coverage counts must be integers") from exc
    if total < 0 or successful < 0 or successful > total:
        raise SourceReconciliationError("Invalid route coverage counts")
    statuses = raw.get("statuses") or {}
    if not isinstance(statuses, dict) or any(
        not isinstance(key, str) or not isinstance(value, int) or value < 0
        for key, value in statuses.items()
    ):
        raise SourceReconciliationError("Route statuses must be non-negative integer counts")
    if sum(statuses.values()) != total:
        raise SourceReconciliationError("Route status counts must equal total_segments")
    successful_from_statuses = sum(int(statuses.get(state, 0)) for state in _SUCCESS_STATUSES)
    if successful_from_statuses != successful:
        raise SourceReconciliationError(
            "successful_segments must equal success_empty + success_nonempty"
        )
    closure_blockers: list[str] = []
    if total <= 0:
        closure_blockers.append("declared_denominator_empty")
    elif successful != total:
        closure_blockers.append("segments_not_terminal_success")
    if not _has_verified_promotion(manifest):
        closure_blockers.append("enumerator_contract_not_promoted")
    terminal_snapshot = raw.get("terminal_snapshot_sha256")
    if not isinstance(terminal_snapshot, str) or not _TERMINAL_SNAPSHOT_SHA256.fullmatch(
        terminal_snapshot
    ):
        closure_blockers.append("terminal_snapshot_sha256_missing_or_invalid")
    runtime_proofs = (
        ("terminal_rule_verified", "terminal_rule_not_verified"),
        ("pagination_complete", "pagination_not_complete"),
        ("resume_verified", "resume_not_verified"),
        ("live_smoke_verified", "live_smoke_not_verified"),
    )
    for field, blocker in runtime_proofs:
        if raw.get(field) is not True:
            closure_blockers.append(blocker)
    closed = total > 0 and successful == total and not closure_blockers
    return {
        "status": "closed_declared_enumeration" if closed else "observed_only",
        "total_segments": total,
        "successful_segments": successful,
        "unresolved_segments": total - successful,
        "statuses": dict(sorted(statuses.items())),
        "denominator_scope": manifest["denominator_scope"],
        "terminal_evidence": {
            "terminal_snapshot_sha256": terminal_snapshot,
            **{field: raw.get(field) is True for field, _ in runtime_proofs},
        },
        "closure_blockers": closure_blockers,
    }


def reconcile_sources(
    *,
    manifests: Iterable[dict[str, Any]],
    observations: Iterable[dict[str, Any]],
    route_coverage: Iterable[dict[str, Any]],
    requested_from: str,
    requested_to: str,
) -> dict[str, Any]:
    """Reconcile confirmed independent chains without upgrading source coverage."""

    try:
        start = date.fromisoformat(requested_from)
        end = date.fromisoformat(requested_to)
    except (TypeError, ValueError) as exc:
        raise SourceReconciliationError("Requested period must use ISO dates") from exc
    if start > end:
        raise SourceReconciliationError("requested_from must not be after requested_to")

    manifest_list = sorted(
        (validate_enumerator_manifest(item) for item in manifests),
        key=lambda item: item["enumerator_id"],
    )
    manifest_by_id: dict[str, dict[str, Any]] = {}
    for item in manifest_list:
        identifier = item["enumerator_id"]
        if identifier in manifest_by_id:
            raise EnumeratorManifestError(f"Duplicate enumerator_id: {identifier}")
        manifest_by_id[identifier] = item

    coverage_input: dict[str, dict[str, Any]] = {}
    for item in route_coverage:
        if not isinstance(item, dict) or not isinstance(item.get("enumerator_id"), str):
            raise SourceReconciliationError("Each route coverage record requires enumerator_id")
        identifier = item["enumerator_id"]
        if identifier not in manifest_by_id:
            raise SourceReconciliationError(f"Coverage references unknown enumerator: {identifier}")
        if identifier in coverage_input:
            raise SourceReconciliationError(f"Duplicate route coverage: {identifier}")
        coverage_input[identifier] = item

    applicable_by_id = {
        identifier: _overlaps(item, start, end) for identifier, item in manifest_by_id.items()
    }
    route_results = {
        identifier: _normalise_route_coverage(
            item,
            coverage_input.get(identifier),
            applicable=applicable_by_id[identifier],
        )
        for identifier, item in sorted(manifest_by_id.items())
    }

    confirmed_found_by: dict[str, set[str]] = {}
    confirmed_documents: dict[str, set[str]] = {}
    unresolved: list[dict[str, Any]] = []
    normalised_observations: list[dict[str, Any]] = []
    for raw in observations:
        if not isinstance(raw, dict):
            raise SourceReconciliationError("Observation must be an object")
        identifier = raw.get("enumerator_id")
        chain_id = raw.get("chain_id")
        document_id = raw.get("document_id")
        identity_status = raw.get("identity_status")
        if identifier not in manifest_by_id:
            raise SourceReconciliationError(f"Observation references unknown enumerator: {identifier}")
        if not isinstance(chain_id, str) or not chain_id.strip():
            raise SourceReconciliationError("Observation requires chain_id")
        if not isinstance(document_id, str) or not document_id.strip():
            raise SourceReconciliationError("Observation requires document_id")
        record = {
            "enumerator_id": str(identifier),
            "chain_id": chain_id.strip(),
            "document_id": document_id.strip(),
            "identity_status": identity_status,
        }
        normalised_observations.append(record)
        if identity_status != "confirmed":
            unresolved.append(record)
            continue
        if not applicable_by_id[str(identifier)] or not manifest_by_id[str(identifier)]["configured"]:
            unresolved.append({**record, "identity_status": "outside_configured_scope"})
            continue
        confirmed_found_by.setdefault(record["chain_id"], set()).add(str(identifier))
        confirmed_documents.setdefault(record["chain_id"], set()).add(record["document_id"])

    found_by = {
        chain_id: sorted(enumerators)
        for chain_id, enumerators in sorted(confirmed_found_by.items())
    }
    intersection = sorted(
        chain_id for chain_id, enumerators in found_by.items() if len(enumerators) >= 2
    )
    comparable_enumerators = sorted(
        identifier
        for identifier, item in manifest_by_id.items()
        if item["configured"] and applicable_by_id[identifier]
    )
    gaps: list[dict[str, str]] = []
    for chain_id, observed_enumerators in found_by.items():
        for identifier in comparable_enumerators:
            if identifier in observed_enumerators:
                continue
            route_status = route_results[identifier]["status"]
            reason = (
                "not_observed_in_route"
                if route_status == "closed_declared_enumeration"
                else "route_coverage_open"
            )
            gaps.append(
                {"chain_id": chain_id, "missing_from": identifier, "reason": reason}
            )
    gaps.sort(key=lambda item: (item["chain_id"], item["missing_from"]))

    historical_gaps = [
        {
            "enumerator_id": identifier,
            "institutional_regime": item["institutional_regime"],
            "status": "not_configured",
            "applicable_from": item.get("applicable_from"),
            "applicable_to": item.get("applicable_to"),
        }
        for identifier, item in sorted(manifest_by_id.items())
        if applicable_by_id[identifier] and not item["configured"]
    ]
    applicable_configured = [
        identifier
        for identifier in comparable_enumerators
        if route_results[identifier]["status"] != "not_applicable"
    ]
    all_routes_closed = bool(applicable_configured) and all(
        route_results[identifier]["status"] == "closed_declared_enumeration"
        for identifier in applicable_configured
    ) and not historical_gaps
    overall_status = "closed_declared_enumerations" if all_routes_closed else "observed_only"
    digest_payload = {
        "manifests": manifest_list,
        "observations": sorted(
            normalised_observations,
            key=lambda item: (
                str(item["enumerator_id"]),
                str(item["chain_id"]),
                str(item["document_id"]),
            ),
        ),
        "route_coverage": route_results,
        "requested_from": requested_from,
        "requested_to": requested_to,
    }
    return {
        "schema_version": "1.0",
        "requested_from": requested_from,
        "requested_to": requested_to,
        "found_by": found_by,
        "intersection_chain_ids": intersection,
        "gaps": gaps,
        "unresolved_identity_observations": unresolved,
        "route_coverage": route_results,
        "historical_gaps": historical_gaps,
        "independent_chain_count": len(found_by),
        "all_routes_closed": all_routes_closed,
        "overall_status": overall_status,
        "denominator_limit": (
            "Closure applies only to each declared enumerator route; it is not all decided "
            "or all published cassation acts."
        ),
        "reconciliation_digest": _digest("reconciliation", digest_payload),
    }


def promote_discovery(
    candidate: dict[str, Any],
    *,
    official_snapshot_id: str | None,
    official_url: str | None,
    official_source_role: str | None,
    identity_status: str,
    reviewer: str,
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    """Create an immutable verified-promotion record from discovery metadata."""

    if not isinstance(candidate, dict) or candidate.get("source_role") != "discovery_only":
        raise PromotionGateError("Only discovery_only candidates use the promotion gate.")
    candidate_id = candidate.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        raise PromotionGateError("Promotion candidate requires candidate_id.")
    if not isinstance(official_snapshot_id, str) or not _SNAPSHOT_ID.fullmatch(
        official_snapshot_id
    ):
        raise PromotionGateError("Promotion requires a content-addressed official snapshot.")
    if official_source_role != "official":
        raise PromotionGateError("Promotion requires an independently verified official source role.")
    if not isinstance(official_url, str):
        raise PromotionGateError("Promotion requires an official URL.")
    parsed_url = urlparse(official_url)
    if parsed_url.scheme.casefold() != "https" or not parsed_url.netloc:
        raise PromotionGateError("Official promotion URL must be an absolute HTTPS URL.")
    if identity_status != "confirmed":
        raise PromotionGateError("Promotion requires confirmed source-to-case identity.")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise PromotionGateError("Promotion requires an identified reviewer.")
    decided_at = reviewed_at or _utc_now()
    try:
        datetime.fromisoformat(decided_at.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise PromotionGateError("reviewed_at must be an ISO timestamp") from exc
    payload = {
        "candidate_id": candidate_id.strip(),
        "discovery_url": candidate.get("url"),
        "official_snapshot_id": official_snapshot_id,
        "official_url": official_url,
        "official_source_role": "official",
        "identity_status": "confirmed",
        "reviewer": reviewer.strip(),
        "reviewed_at": decided_at,
    }
    return {
        **payload,
        "promotion_id": _digest("promotion", payload),
        "source_role": "official",
        "status": "official_verified",
    }


def promote_enumerator(
    candidate_manifest: dict[str, Any],
    *,
    verification: dict[str, Any],
    reviewer: str,
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    """Promote a route only after every reproducibility and fail-closed gate passes."""

    candidate = validate_enumerator_manifest(candidate_manifest)
    if candidate["configured"] is not False:
        raise PromotionGateError("Enumerator promotion requires an unconfigured candidate manifest.")
    if not isinstance(verification, dict):
        raise PromotionGateError("Enumerator promotion requires a verification record.")
    failed = [
        gate for gate in _ENUMERATOR_VERIFICATION_GATES if verification.get(gate) is not True
    ]
    if failed:
        raise PromotionGateError(
            "Enumerator promotion gates are incomplete: " + ", ".join(failed)
        )
    adapter_id = verification.get("adapter_id")
    closure_rule = verification.get("closure_rule")
    if not isinstance(adapter_id, str) or not adapter_id.strip():
        raise PromotionGateError("Enumerator promotion requires a verified adapter_id.")
    if not isinstance(closure_rule, str) or not closure_rule.strip():
        raise PromotionGateError("Enumerator promotion requires a verified closure_rule.")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise PromotionGateError("Enumerator promotion requires an identified reviewer.")
    decided_at = reviewed_at or _utc_now()
    try:
        datetime.fromisoformat(decided_at.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise PromotionGateError("reviewed_at must be an ISO timestamp") from exc

    promoted_manifest = deepcopy(candidate)
    promoted_manifest.update(
        {
            "source_role": "official",
            "configured": True,
            "adapter_id": adapter_id.strip(),
            "closure_rule": closure_rule.strip(),
        }
    )
    verification_record = {
        "adapter_id": adapter_id.strip(),
        "closure_rule": closure_rule.strip(),
        **{gate: True for gate in _ENUMERATOR_VERIFICATION_GATES},
    }
    promoted_manifest = validate_enumerator_manifest(promoted_manifest)
    payload = _promotion_payload(
        promoted_manifest,
        verification=verification_record,
        reviewer=reviewer.strip(),
        reviewed_at=decided_at,
    )
    promotion_id = _digest("enumerator-promotion", payload)
    promoted_manifest["promotion"] = {
        "promotion_id": promotion_id,
        "status": "official_enumerator_verified",
        "verification": verification_record,
        "reviewer": reviewer.strip(),
        "reviewed_at": decided_at,
    }
    promoted_manifest = validate_enumerator_manifest(promoted_manifest)
    return {
        **payload,
        "manifest": promoted_manifest,
        "promotion_id": promotion_id,
        "status": "official_enumerator_verified",
    }
