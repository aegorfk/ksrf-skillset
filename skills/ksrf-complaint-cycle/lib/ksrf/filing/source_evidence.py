from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from .adapters.base import AdapterRequest, AdapterResult, SourceAdapter
from .source_registry import RETRIEVAL_STATUSES, SourceRegistry
from .storage import AppendOnlyJsonlLedger, ContentAddressedStore, stable_id, utc_now


_TERMINAL_STATUSES = {
    "retrieved",
    "not_found",
    "interactive_required",
    "invalid_response",
    "conflict",
}
_SAFE_RESPONSE_HEADERS = {
    "content-length",
    "content-type",
    "etag",
    "last-modified",
    "location",
    "x-request-id",
}


def _safe_response_headers(headers: Mapping[str, Any]) -> Dict[str, str]:
    return {
        str(key).lower(): str(value)
        for key, value in headers.items()
        if str(key).lower() in _SAFE_RESPONSE_HEADERS
    }


def execute_bounded_retrieval(adapter: SourceAdapter, request: AdapterRequest) -> AdapterResult:
    last: Optional[AdapterResult] = None
    for attempt in range(1, request.max_attempts + 1):
        result = adapter.acquire(request).with_attempt_count(attempt)
        if result.status not in RETRIEVAL_STATUSES:
            return replace(
                result,
                status="invalid_response",
                error_code="unknown_adapter_status",
                error_detail=result.status,
                attempt_count=attempt,
            )
        if result.status == "not_found" and (
            not result.terminal_rule_verified or not request.bounded_scope
        ):
            return replace(
                result,
                status="invalid_response",
                error_code="unverified_negative_result",
                attempt_count=attempt,
            )
        last = result
        if result.status in _TERMINAL_STATUSES:
            return result
    return last or AdapterResult(
        status="invalid_response",
        transport="unknown",
        error_code="adapter_returned_no_result",
        attempt_count=0,
    )


def _identity_is_verified(identity_checks: Sequence[Mapping[str, Any]]) -> bool:
    return bool(identity_checks) and all(str(item.get("status") or "") == "passed" for item in identity_checks)


class SourceEvidenceRepository:
    def __init__(self, root: Path, *, registry: Optional[SourceRegistry] = None) -> None:
        self.root = Path(root)
        self.registry = registry or SourceRegistry.load_default()
        self.objects = ContentAddressedStore(self.root, "source-evidence")
        self.observations = AppendOnlyJsonlLedger(self.root / "source-observations.jsonl")
        self.evidence = AppendOnlyJsonlLedger(self.root / "source-evidence.jsonl")
        self.refresh_events = AppendOnlyJsonlLedger(self.root / "source-refresh-events.jsonl")

    def _previous_for_origin(self, source_id: str, origin_url: str) -> Optional[Dict[str, Any]]:
        previous = None
        for record in self.evidence:
            if record.get("source_id") == source_id and record.get("origin_url") == origin_url:
                previous = record
        return previous

    def record_result(
        self,
        request: AdapterRequest,
        result: AdapterResult,
        *,
        identity_checks: Sequence[Mapping[str, Any]],
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        source = self.registry.get(request.source_id)
        observed_at = result.fetched_at or utc_now()
        origin_url = result.origin_url or request.locator
        observation_body = {
            "schema_version": "1.0.0",
            "source_registry_version": self.registry.schema_version,
            "source_id": request.source_id,
            "issuer": source.get("issuer"),
            "authority_class": source["authority_class"],
            "origin_url": origin_url,
            "requested_locator": request.locator,
            "bounded_scope": dict(request.bounded_scope),
            "result_status": result.status,
            "acquisition_transport": result.transport,
            "adapter_result_attempts": int(result.attempt_count),
            "terminal_rule_verified": bool(result.terminal_rule_verified),
            "http_status": result.http_status,
            "response_headers": _safe_response_headers(result.response_headers),
            "error_code": result.error_code,
            "error_detail": result.error_detail,
            "observed_at": observed_at,
        }
        observation = dict(observation_body)
        observation["observation_id"] = stable_id("source-observation", observation_body)
        self.observations.append(observation)

        if result.status != "retrieved":
            return observation, None
        if not isinstance(result.raw_bytes, bytes) or not result.raw_bytes:
            raise ValueError("retrieved adapter result requires non-empty raw_bytes")

        raw = self.objects.put_bytes(result.raw_bytes)
        extracted = self.objects.put_bytes(result.extracted_bytes) if result.extracted_bytes else None
        verified_identity = _identity_is_verified(identity_checks)
        official = source["authority_class"] in {"official_primary", "official_derivative"}
        filing_state = "verified_official" if official and verified_identity else (
            "identity_unverified" if official else "non_official"
        )
        previous = self._previous_for_origin(request.source_id, origin_url)
        evidence_body = {
            "schema_version": "1.0.0",
            "observation_id": observation["observation_id"],
            "source_id": request.source_id,
            "issuer": source.get("issuer"),
            "authority_class": source["authority_class"],
            "origin_url": origin_url,
            "acquisition_transport": result.transport,
            "retrieved_at": observed_at,
            "content_type": result.content_type,
            "raw_object": raw,
            "extracted_object": extracted,
            "identity_checks": [dict(item) for item in identity_checks],
            "transform_chain": [dict(item) for item in result.transform_chain],
            "filing_authority_state": filing_state,
            "filing_ready": filing_state == "verified_official",
            "validation_state": "verified" if verified_identity else "pending_identity_review",
            "supersedes_evidence_id": None,
        }
        if previous and (previous.get("raw_object") or {}).get("sha256") != raw["sha256"]:
            evidence_body["supersedes_evidence_id"] = previous.get("evidence_id")
        evidence_record = dict(evidence_body)
        evidence_record["evidence_id"] = stable_id(
            "source-evidence",
            {
                "source_id": request.source_id,
                "origin_url": origin_url,
                "raw_sha256": raw["sha256"],
                "extracted_sha256": (extracted or {}).get("sha256"),
            },
        )
        existing = self.evidence.latest_by("evidence_id", evidence_record["evidence_id"])
        if existing:
            return observation, existing
        self.evidence.append(evidence_record)
        return observation, evidence_record

    def read_raw(self, evidence: Mapping[str, Any]) -> bytes:
        raw = evidence.get("raw_object")
        if not isinstance(raw, Mapping):
            raise ValueError("evidence has no raw object")
        return self.objects.read_bytes(raw)

    def compare_refresh(
        self,
        previous: Mapping[str, Any],
        current: Mapping[str, Any],
        *,
        dependent_claim_ids: Iterable[str] = (),
    ) -> Dict[str, Any]:
        if previous.get("source_id") != current.get("source_id") or previous.get("origin_url") != current.get("origin_url"):
            raise ValueError("refresh comparison requires the same source and origin")
        previous_hash = str((previous.get("raw_object") or {}).get("sha256") or "")
        current_hash = str((current.get("raw_object") or {}).get("sha256") or "")
        state = "unchanged" if previous_hash == current_hash else "changed"
        invalidated = sorted(set(str(item) for item in dependent_claim_ids if item)) if state == "changed" else []
        body = {
            "schema_version": "1.0.0",
            "previous_evidence_id": previous.get("evidence_id"),
            "current_evidence_id": current.get("evidence_id"),
            "state": state,
            "invalidated_claim_ids": invalidated,
            "compared_at": utc_now(),
        }
        event = dict(body)
        event["refresh_event_id"] = stable_id("source-refresh", body)
        self.refresh_events.append(event)
        return event

    def coverage_report(self) -> Dict[str, Any]:
        observations = self.observations.records()
        statuses: Dict[str, int] = {}
        for item in observations:
            status = str(item.get("result_status") or "unknown")
            statuses[status] = statuses.get(status, 0) + 1
        partial = any(status in statuses for status in ("unavailable", "interactive_required", "invalid_response", "conflict"))
        absence_claim_permitted = bool(observations) and all(
            item.get("result_status") == "not_found" and item.get("terminal_rule_verified") is True
            for item in observations
        )
        return {
            "schema_version": "1.0.0",
            "observation_count": len(observations),
            "status_counts": dict(sorted(statuses.items())),
            "coverage_state": "partial" if partial else ("observed" if observations else "unknown"),
            "absence_claim_permitted": absence_claim_permitted,
        }
