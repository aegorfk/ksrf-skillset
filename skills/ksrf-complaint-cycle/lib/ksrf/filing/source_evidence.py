from __future__ import annotations

import hashlib
import stat
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Protocol, Sequence, Tuple
from urllib.parse import urlparse

from .adapters.base import AdapterRequest, AdapterResult, SourceAdapter
from .source_registry import RETRIEVAL_STATUSES, SourceRegistry
from .storage import AppendOnlyJsonlLedger, ContentAddressedStore, stable_id, utc_now
from .trusted_approvals import TrustedApprovalLedger


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


def source_identity_fingerprint(
    *,
    source_id: str,
    official_locator: str,
    content_sha256: str,
) -> str:
    return stable_id(
        "source-identity",
        {
            "source_id": str(source_id),
            "official_locator": str(official_locator),
            "content_sha256": str(content_sha256),
        },
    )


def _normalized_redirect_chain(request: AdapterRequest, result: AdapterResult) -> list[str]:
    values = [*result.redirect_chain]
    if not values:
        values = [request.locator, result.origin_url or request.locator]
    return list(dict.fromkeys(str(item) for item in values if str(item).strip()))


def _redirect_registry_conflict(
    registry: SourceRegistry,
    request: AdapterRequest,
    result: AdapterResult,
) -> Optional[str]:
    for locator in _normalized_redirect_chain(request, result):
        if urlparse(locator).scheme not in {"http", "https"}:
            continue
        resolved = registry.resolve_url(locator)
        if not resolved or resolved.get("source_id") != request.source_id:
            return locator
    return None


class SourceIdentityVerifier(Protocol):
    """Host-injected verifier that derives identity from the actual fetched bytes."""

    verifier_id: str

    def derive_identity_checks(
        self,
        *,
        source: Mapping[str, Any],
        request: AdapterRequest,
        result: AdapterResult,
        raw_bytes: bytes,
    ) -> Sequence[Mapping[str, Any]]: ...


def _core_identity_verification(
    *,
    registry: SourceRegistry,
    source: Mapping[str, Any],
    request: AdapterRequest,
    result: AdapterResult,
    checks: Sequence[Mapping[str, Any]],
    content_sha256: str,
) -> Dict[str, Any]:
    by_type: Dict[str, list[Mapping[str, Any]]] = {}
    for item in checks:
        check_type = str(item.get("check") or "").strip()
        if check_type and str(item.get("status") or "") == "passed":
            by_type.setdefault(check_type, []).append(item)
    blockers: list[str] = []

    issuer_domain = None
    for item in by_type.get("issuer_domain", []):
        official_locator = str(item.get("official_locator") or "").strip()
        official_host = (urlparse(official_locator).hostname or "").lower()
        declared_domain = str(item.get("domain") or "").strip().lower()
        resolved = registry.resolve_url(official_locator)
        if (
            str(item.get("issuer") or "").strip() == str(source.get("issuer") or "").strip()
            and declared_domain
            and declared_domain == official_host
            and resolved
            and resolved.get("source_id") == request.source_id
        ):
            issuer_domain = item
            break
    if issuer_domain is None:
        blockers.append("issuer_domain_check_missing")
    official_locator = str((issuer_domain or {}).get("official_locator") or "").strip()

    expected_identifiers = {str(item) for item in source.get("expected_identifiers") or []}
    document_identifier_types = {item for item in expected_identifiers if not item.endswith("_date")}
    identifier_valid = False
    for item in by_type.get("exact_document_identifier", []):
        identifier_type = str(item.get("identifier_type") or "").strip()
        expected_value = str(item.get("expected_value") or "").strip()
        observed_value = str(item.get("observed_value") or "").strip()
        scoped_value = request.bounded_scope.get(identifier_type)
        if scoped_value is None:
            scoped_value = request.bounded_scope.get("identifier")
        if (
            identifier_type in document_identifier_types
            and expected_value
            and expected_value == observed_value
            and scoped_value is not None
            and str(scoped_value).strip() == expected_value
        ):
            identifier_valid = True
            break
    if not identifier_valid:
        blockers.append("exact_document_identifier_check_missing")

    date_identifier_types = {item for item in expected_identifiers if item.endswith("_date")}
    if date_identifier_types:
        date_valid = False
        for item in by_type.get("document_date", []):
            identifier_type = str(item.get("identifier_type") or "").strip()
            expected_value = str(item.get("expected_value") or "").strip()
            observed_value = str(item.get("observed_value") or "").strip()
            scoped_value = request.bounded_scope.get(identifier_type)
            try:
                datetime.fromisoformat(observed_value)
            except ValueError:
                continue
            if (
                identifier_type in date_identifier_types
                and expected_value
                and expected_value == observed_value
                and scoped_value is not None
                and str(scoped_value).strip() == expected_value
            ):
                date_valid = True
                break
        if not date_valid:
            blockers.append("document_date_check_missing")

    binding_valid = False
    for item in by_type.get("content_locator_hash_binding", []):
        binding_locator = str(item.get("official_locator") or "").strip()
        if (
            official_locator
            and binding_locator == official_locator
            and str(item.get("content_sha256") or "").strip() == content_sha256
        ):
            if result.transport != "manual_import" and binding_locator != str(result.origin_url or request.locator):
                continue
            if result.transport == "manual_import":
                scoped_locator = str(request.bounded_scope.get("official_locator") or "").strip()
                if not scoped_locator or binding_locator != scoped_locator:
                    continue
            binding_valid = True
            break
    if not binding_valid:
        blockers.append("content_locator_hash_binding_missing")

    return {
        "verified": not blockers,
        "blockers": sorted(set(blockers)),
        "official_locator": official_locator or None,
    }


def _host_derived_identity_checks(
    verifier: Optional[SourceIdentityVerifier],
    *,
    source: Mapping[str, Any],
    request: AdapterRequest,
    result: AdapterResult,
    raw_bytes: bytes,
    content_sha256: str,
) -> tuple[list[Mapping[str, Any]], Optional[str]]:
    if verifier is None:
        return [], ("host_identity_verifier_required" if result.derived_identity_checks else None)
    verifier_id = str(getattr(verifier, "verifier_id", "") or "").strip()
    if not verifier_id:
        return [], "host_identity_verifier_invalid"
    try:
        checks = verifier.derive_identity_checks(
            source=source,
            request=request,
            result=result,
            raw_bytes=raw_bytes,
        )
    except Exception:
        return [], "host_identity_verification_failed"
    if not isinstance(checks, Sequence) or isinstance(checks, (str, bytes)):
        return [], "host_identity_verification_failed"
    trusted: list[Mapping[str, Any]] = []
    for item in checks:
        if not isinstance(item, Mapping):
            return [], "host_identity_verification_failed"
        if not str(item.get("evidence_locator") or "").strip() or not str(
            item.get("evidence_excerpt") or ""
        ).strip():
            return [], "host_identity_verification_failed"
        trusted.append(
            {
                **dict(item),
                "verifier_id": verifier_id,
                "derived_from_content_sha256": content_sha256,
            }
        )
    return trusted, None


def _identity_verification(
    *,
    registry: SourceRegistry,
    source: Mapping[str, Any],
    request: AdapterRequest,
    result: AdapterResult,
    identity_checks: Sequence[Mapping[str, Any]],
    identity_verifier: Optional[SourceIdentityVerifier],
    approval_ledger: TrustedApprovalLedger,
    approval_ids: Sequence[str],
    content_sha256: str,
) -> Dict[str, Any]:
    caller_core = _core_identity_verification(
        registry=registry,
        source=source,
        request=request,
        result=result,
        checks=identity_checks,
        content_sha256=content_sha256,
    )
    trusted_checks, host_verifier_blocker = _host_derived_identity_checks(
        identity_verifier,
        source=source,
        request=request,
        result=result,
        raw_bytes=result.raw_bytes or b"",
        content_sha256=content_sha256,
    )
    derived_core = _core_identity_verification(
        registry=registry,
        source=source,
        request=request,
        result=result,
        checks=trusted_checks,
        content_sha256=content_sha256,
    )
    preferred_core = derived_core if derived_core["verified"] else caller_core
    official_locator = str(preferred_core.get("official_locator") or "")

    fingerprint = source_identity_fingerprint(
        source_id=request.source_id,
        official_locator=official_locator,
        content_sha256=content_sha256,
    )
    intermediary_or_manual = (
        result.transport == "manual_import"
        or bool(result.discovery_transport)
        or result.transport not in {"direct_http"}
    )
    approval_bindings = {
        "source_id": request.source_id,
        "official_locator": official_locator,
        "content_sha256": content_sha256,
    }
    valid_approval = None
    approval_failures: list[str] = []
    for approval_id in sorted({str(item).strip() for item in approval_ids if str(item).strip()}):
        validation = approval_ledger.validate_approval(
            approval_id,
            purpose="source_identity",
            subject_type="official_source_content",
            subject_id=request.source_id,
            fingerprint=fingerprint,
            bindings=approval_bindings,
        )
        if validation["valid"] is True:
            valid_approval = validation["approval"]
            break
        approval_failures.append(str(validation.get("reason_code") or "approval_invalid"))

    blockers: list[str] = []
    mode = "unverified"
    if intermediary_or_manual:
        blockers.extend(preferred_core["blockers"])
        if valid_approval is None:
            blockers.append("trusted_fingerprint_approval_required")
        elif preferred_core["verified"]:
            mode = "trusted_approval"
    elif derived_core["verified"]:
        mode = "trusted_derived"
    elif caller_core["verified"] and valid_approval is not None:
        mode = "trusted_approval"
    else:
        blockers.extend(caller_core["blockers"])
        blockers.append("trusted_derived_identity_or_human_approval_required")
    if host_verifier_blocker:
        blockers.append(host_verifier_blocker)
    if valid_approval is None:
        blockers.extend(f"trusted_{reason}" for reason in approval_failures)
    return {
        "verified": not blockers,
        "blockers": sorted(set(blockers)),
        "official_locator": official_locator or None,
        "identity_fingerprint": fingerprint,
        "human_reviewer": (
            str(valid_approval.get("actor_display_name")) if valid_approval else None
        ),
        "trusted_approval_id": (
            str(valid_approval.get("approval_id")) if valid_approval else None
        ),
        "mode": mode,
        "trusted_derived_checks": [dict(item) for item in trusted_checks],
    }


def _string_list(value: Any, *, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{label} must be a sequence")
    return sorted({str(item).strip() for item in value if str(item).strip()})


def _parse_timestamp(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class SourceEvidenceRepository:
    def __init__(
        self,
        root: Path,
        *,
        registry: Optional[SourceRegistry] = None,
        approval_ledger: Optional[TrustedApprovalLedger] = None,
        identity_verifier: Optional[SourceIdentityVerifier] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self.root = Path(root)
        self.registry = registry or SourceRegistry.load_default()
        self.objects = ContentAddressedStore(self.root, "source-evidence")
        self.observations = AppendOnlyJsonlLedger(self.root / "source-observations.jsonl")
        self.evidence = AppendOnlyJsonlLedger(self.root / "source-evidence.jsonl")
        self.refresh_events = AppendOnlyJsonlLedger(self.root / "source-refresh-events.jsonl")
        self.approvals = approval_ledger or TrustedApprovalLedger(self.root / "trusted-approvals")
        self.identity_verifier = identity_verifier
        self.clock = clock or (
            approval_ledger.clock
            if approval_ledger is not None
            else lambda: datetime.now(timezone.utc)
        )

    def _read_current_raw_object(
        self,
        evidence: Mapping[str, Any],
        blockers: list[str],
    ) -> tuple[Optional[bytes], str]:
        raw = evidence.get("raw_object")
        if not isinstance(raw, Mapping):
            blockers.append("raw_object_record_invalid")
            return None, ""

        declared_sha256 = str(raw.get("sha256") or "").strip().lower()
        path_value = str(raw.get("object_path") or "").strip()
        declared_size = raw.get("size")
        if len(declared_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in declared_sha256
        ):
            blockers.append("raw_object_record_invalid")
            return None, declared_sha256
        if (
            not isinstance(declared_size, int)
            or isinstance(declared_size, bool)
            or declared_size < 0
        ):
            blockers.append("raw_object_size_mismatch")

        expected_relative = (
            Path("source-evidence")
            / "objects"
            / "sha256"
            / declared_sha256[:2]
            / declared_sha256
        )
        supplied_relative = Path(path_value)
        if supplied_relative.is_absolute() or supplied_relative != expected_relative:
            blockers.append("raw_object_path_invalid")
            return None, declared_sha256

        object_path = self.objects.root / supplied_relative
        try:
            metadata = object_path.lstat()
        except FileNotFoundError:
            blockers.append("raw_object_missing")
            return None, declared_sha256
        except OSError:
            blockers.append("raw_object_unreadable")
            return None, declared_sha256
        if not stat.S_ISREG(metadata.st_mode):
            blockers.append("raw_object_not_regular_file")
            return None, declared_sha256
        try:
            resolved_path = object_path.resolve(strict=True)
            resolved_path.relative_to(self.objects.root)
        except (FileNotFoundError, OSError, ValueError):
            blockers.append("raw_object_path_invalid")
            return None, declared_sha256
        if resolved_path != object_path:
            blockers.append("raw_object_not_regular_file")
            return None, declared_sha256
        try:
            content = object_path.read_bytes()
        except OSError:
            blockers.append("raw_object_unreadable")
            return None, declared_sha256

        observed_sha256 = hashlib.sha256(content).hexdigest()
        if observed_sha256 != declared_sha256:
            blockers.append("raw_object_sha256_mismatch")
        if not isinstance(declared_size, int) or isinstance(declared_size, bool) or len(
            content
        ) != declared_size:
            blockers.append("raw_object_size_mismatch")
        return content, observed_sha256

    def _current_observation(
        self,
        evidence: Mapping[str, Any],
        blockers: list[str],
    ) -> Optional[Dict[str, Any]]:
        observation_id = str(evidence.get("observation_id") or "")
        observation = self.observations.latest_by("observation_id", observation_id)
        if not observation:
            blockers.append("source_observation_missing")
            return None
        observation_body = {
            key: observation.get(key)
            for key in (
                "schema_version",
                "source_registry_version",
                "source_id",
                "issuer",
                "authority_class",
                "origin_url",
                "requested_locator",
                "bounded_scope",
                "result_status",
                "acquisition_transport",
                "discovery_transport",
                "redirect_chain",
                "adapter_result_attempts",
                "terminal_rule_verified",
                "http_status",
                "response_headers",
                "error_code",
                "error_detail",
                "observed_at",
            )
        }
        if stable_id("source-observation", observation_body) != observation_id:
            blockers.append("source_observation_id_mismatch")
        if (
            observation.get("result_status") != "retrieved"
            or observation.get("source_id") != evidence.get("source_id")
            or observation.get("origin_url") != evidence.get("origin_url")
            or observation.get("acquisition_transport")
            != evidence.get("acquisition_transport")
            or observation.get("discovery_transport") != evidence.get("discovery_transport")
            or observation.get("redirect_chain") != evidence.get("redirect_chain")
            or observation.get("observed_at") != evidence.get("retrieved_at")
        ):
            blockers.append("source_observation_binding_mismatch")
        return observation

    def current_filing_authority(self, evidence: Mapping[str, Any]) -> Dict[str, Any]:
        """Recompute content and current authority instead of trusting stored flags."""

        evidence_id = str(evidence.get("evidence_id") or "")
        blockers: list[str] = []
        if (
            evidence.get("filing_ready") is not True
            or evidence.get("filing_authority_state") != "verified_official"
            or evidence.get("validation_state") != "verified"
        ):
            blockers.append("evidence_not_verified_official")

        raw_bytes, observed_sha256 = self._read_current_raw_object(evidence, blockers)
        raw_record = evidence.get("raw_object")
        declared_sha256 = str(
            (raw_record.get("sha256") if isinstance(raw_record, Mapping) else None) or ""
        )
        content_sha256 = observed_sha256 or declared_sha256
        extracted_record = evidence.get("extracted_object")
        if extracted_record is None:
            extracted_sha256 = None
        elif isinstance(extracted_record, Mapping) and str(
            extracted_record.get("sha256") or ""
        ):
            extracted_sha256 = str(extracted_record.get("sha256"))
        else:
            extracted_sha256 = None
            blockers.append("extracted_object_record_invalid")

        source_id = str(evidence.get("source_id") or "")
        origin_url = str(evidence.get("origin_url") or "")
        expected_evidence_id = stable_id(
            "source-evidence",
            {
                "source_id": source_id,
                "origin_url": origin_url,
                "raw_sha256": content_sha256,
                "extracted_sha256": extracted_sha256,
            },
        )
        if evidence_id != expected_evidence_id:
            blockers.append("evidence_id_mismatch")
        expected_revision_id = stable_id(
            "source-verification",
            {
                "evidence_id": evidence_id,
                "identity_checks": evidence.get("identity_checks"),
                "derived_identity_checks": evidence.get("derived_identity_checks"),
                "approval_ids": evidence.get("approval_ids"),
                "trusted_approval_id": evidence.get("trusted_approval_id"),
                "validation_state": evidence.get("validation_state"),
            },
        )
        if str(evidence.get("verification_revision_id") or "") != expected_revision_id:
            blockers.append("verification_revision_id_mismatch")

        source: Optional[Dict[str, Any]] = None
        try:
            source = self.registry.get(source_id)
        except KeyError:
            blockers.append("current_source_registry_missing")
        if source is not None:
            if source.get("authority_class") not in {
                "official_primary",
                "official_derivative",
            }:
                blockers.append("current_source_not_official")
            if (
                evidence.get("issuer") != source.get("issuer")
                or evidence.get("authority_class") != source.get("authority_class")
            ):
                blockers.append("source_registry_binding_mismatch")

        locator = str(evidence.get("verified_official_locator") or "")
        resolved_locator = self.registry.resolve_url(locator) if locator else None
        if not resolved_locator or resolved_locator.get("source_id") != source_id:
            blockers.append("official_locator_registry_mismatch")
        reconstructed = source_identity_fingerprint(
            source_id=source_id,
            official_locator=locator,
            content_sha256=content_sha256,
        )
        if reconstructed != str(evidence.get("identity_fingerprint") or ""):
            blockers.append("source_identity_fingerprint_mismatch")

        mode = str(evidence.get("identity_verification_mode") or "")
        if mode == "trusted_approval":
            approval_id = str(evidence.get("trusted_approval_id") or "")
            if not approval_id:
                blockers.append("approval_not_found")
            else:
                validation = self.approvals.validate_approval(
                    approval_id,
                    purpose="source_identity",
                    subject_type="official_source_content",
                    subject_id=source_id,
                    fingerprint=reconstructed,
                    bindings={
                        "source_id": source_id,
                        "official_locator": locator,
                        "content_sha256": content_sha256,
                    },
                )
                if validation.get("valid") is not True:
                    blockers.append(str(validation.get("reason_code") or "approval_invalid"))
        elif mode == "trusted_derived":
            if (
                evidence.get("acquisition_transport") != "direct_http"
                or evidence.get("discovery_transport")
            ):
                blockers.append("trusted_derived_direct_transport_required")
            observation = self._current_observation(evidence, blockers)
            if self.identity_verifier is None:
                blockers.append("host_identity_verifier_required")
            elif raw_bytes is None or source is None or observation is None:
                blockers.append("trusted_derived_revalidation_unavailable")
            else:
                try:
                    request = AdapterRequest(
                        source_id=source_id,
                        locator=str(observation.get("requested_locator") or ""),
                        bounded_scope=dict(observation.get("bounded_scope") or {}),
                    )
                    result = AdapterResult(
                        status="retrieved",
                        transport=str(evidence.get("acquisition_transport") or ""),
                        origin_url=origin_url,
                        raw_bytes=raw_bytes,
                        content_type=evidence.get("content_type"),
                        terminal_rule_verified=bool(
                            observation.get("terminal_rule_verified")
                        ),
                        transform_chain=tuple(evidence.get("transform_chain") or ()),
                        fetched_at=str(evidence.get("retrieved_at") or "") or None,
                        attempt_count=int(observation.get("adapter_result_attempts") or 1),
                        discovery_transport=evidence.get("discovery_transport"),
                        redirect_chain=tuple(evidence.get("redirect_chain") or ()),
                        derived_identity_checks=tuple(
                            evidence.get("derived_identity_checks") or ()
                        ),
                    )
                except (TypeError, ValueError):
                    blockers.append("source_observation_invalid")
                else:
                    current_checks, verifier_blocker = _host_derived_identity_checks(
                        self.identity_verifier,
                        source=source,
                        request=request,
                        result=result,
                        raw_bytes=raw_bytes,
                        content_sha256=content_sha256,
                    )
                    if verifier_blocker:
                        blockers.append(verifier_blocker)
                    current_core = _core_identity_verification(
                        registry=self.registry,
                        source=source,
                        request=request,
                        result=result,
                        checks=current_checks,
                        content_sha256=content_sha256,
                    )
                    if current_core.get("verified") is not True:
                        blockers.extend(current_core.get("blockers") or [])
                    if str(current_core.get("official_locator") or "") != locator:
                        blockers.append("trusted_derived_locator_mismatch")
        else:
            blockers.append("current_identity_authority_missing")
        return {
            "evidence_id": evidence_id,
            "filing_ready": not blockers,
            "identity_verification_mode": mode or None,
            "blockers": sorted(set(blockers)),
        }

    def current_verified_official_evidence(self) -> list[Dict[str, Any]]:
        return [
            record
            for record in self.evidence.records()
            if self.current_filing_authority(record)["filing_ready"] is True
        ]

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
        approval_ids: Sequence[str] = (),
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        source = self.registry.get(request.source_id)
        registry_conflict = _redirect_registry_conflict(self.registry, request, result)
        if result.status == "retrieved" and registry_conflict:
            result = replace(
                result,
                status="conflict",
                raw_bytes=None,
                extracted_bytes=None,
                error_code="final_origin_registry_mismatch",
                error_detail=f"Unregistered redirect/final origin: {registry_conflict}",
            )
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
            "discovery_transport": result.discovery_transport,
            "redirect_chain": _normalized_redirect_chain(request, result),
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
        verification = _identity_verification(
            registry=self.registry,
            source=source,
            request=request,
            result=result,
            identity_checks=identity_checks,
            identity_verifier=self.identity_verifier,
            approval_ledger=self.approvals,
            approval_ids=approval_ids,
            content_sha256=raw["sha256"],
        )
        verified_identity = verification["verified"] is True
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
            "discovery_transport": result.discovery_transport,
            "redirect_chain": _normalized_redirect_chain(request, result),
            "retrieved_at": observed_at,
            "content_type": result.content_type,
            "raw_object": raw,
            "extracted_object": extracted,
            "identity_checks": [dict(item) for item in identity_checks],
            "derived_identity_checks": verification["trusted_derived_checks"],
            "identity_fingerprint": verification["identity_fingerprint"],
            "identity_verification_mode": verification["mode"],
            "identity_verification_blockers": verification["blockers"],
            "verified_official_locator": verification["official_locator"],
            "human_identity_reviewer": verification["human_reviewer"],
            "approval_ids": sorted({str(item).strip() for item in approval_ids if str(item).strip()}),
            "trusted_approval_id": verification["trusted_approval_id"],
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
        evidence_record["verification_revision_id"] = stable_id(
            "source-verification",
            {
                "evidence_id": evidence_record["evidence_id"],
                "identity_checks": evidence_record["identity_checks"],
                "derived_identity_checks": evidence_record["derived_identity_checks"],
                "approval_ids": evidence_record["approval_ids"],
                "trusted_approval_id": evidence_record["trusted_approval_id"],
                "validation_state": evidence_record["validation_state"],
            },
        )
        existing = self.evidence.latest_by(
            "verification_revision_id",
            evidence_record["verification_revision_id"],
        )
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

    def claim_source_coverage_report(
        self,
        claims: Sequence[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluate filing support for each supplied proposition without inference.

        The caller supplies explicit claim-to-evidence links.  The report never
        treats discovery results, an unverified official URL, or model inference
        as official support.
        """

        evidence_by_id = {
            str(record.get("evidence_id")): record
            for record in self.evidence.records()
            if record.get("evidence_id")
        }
        report_claims: list[Dict[str, Any]] = []
        seen_claim_ids: set[str] = set()
        for raw_claim in claims:
            if not isinstance(raw_claim, Mapping):
                raise ValueError("each claim must be an object")
            claim_id = str(raw_claim.get("claim_id") or "").strip()
            if not claim_id or claim_id in seen_claim_ids:
                raise ValueError(f"missing or duplicate claim_id: {claim_id!r}")
            seen_claim_ids.add(claim_id)
            evidence_ids = _string_list(raw_claim.get("evidence_ids"), label="evidence_ids")
            sentence_ids = _string_list(raw_claim.get("sentence_ids"), label="sentence_ids")
            required_support = str(raw_claim.get("required_support") or "official").strip()
            if required_support not in {"official", "recorded"}:
                raise ValueError(f"unsupported required_support: {required_support!r}")
            declared_support = str(raw_claim.get("declared_support") or "").strip()
            if declared_support and declared_support not in {
                "official",
                "party_supplied",
                "inferred",
                "pending",
            }:
                raise ValueError(f"unsupported declared_support: {declared_support!r}")
            scope_review_status = str(raw_claim.get("scope_review_status") or "unknown").strip()
            if scope_review_status not in {"passed", "overclaimed", "unknown"}:
                raise ValueError(f"unsupported scope_review_status: {scope_review_status!r}")

            linked = [evidence_by_id[item] for item in evidence_ids if item in evidence_by_id]
            missing_ids = sorted(set(evidence_ids) - set(evidence_by_id))
            authority_by_id = {
                str(item["evidence_id"]): self.current_filing_authority(item)
                for item in linked
            }
            official_ids = sorted(
                str(item["evidence_id"])
                for item in linked
                if authority_by_id[str(item["evidence_id"])]["filing_ready"] is True
            )
            party_ids = sorted(
                str(item["evidence_id"])
                for item in linked
                if item.get("authority_class") == "user_supplied_unverified"
            )
            discovery_ids = sorted(
                str(item["evidence_id"])
                for item in linked
                if item.get("authority_class") == "discovery_only"
                or item.get("filing_authority_state") == "identity_unverified"
                or (
                    item.get("filing_authority_state") == "verified_official"
                    and authority_by_id[str(item["evidence_id"])]["filing_ready"] is False
                )
            )
            if declared_support in {"inferred", "pending"}:
                support_class = declared_support
            elif official_ids:
                support_class = "official"
            elif party_ids:
                support_class = "party_supplied"
            else:
                support_class = "pending"

            blockers: list[str] = []
            if required_support == "official":
                for evidence_id in evidence_ids:
                    blockers.extend(
                        (authority_by_id.get(evidence_id) or {}).get("blockers") or []
                    )
            if not evidence_ids or missing_ids:
                blockers.append("source_evidence_missing")
            if discovery_ids:
                blockers.append("discovery_or_identity_unverified_source")
            if required_support == "official" and not official_ids:
                blockers.append("official_support_required")
            elif required_support == "recorded" and not linked:
                blockers.append("recorded_support_required")
            if declared_support == "inferred":
                blockers.append("inference_not_evidence")
            elif declared_support == "pending":
                blockers.append("support_pending")
            if scope_review_status == "overclaimed":
                blockers.append("claim_scope_overclaimed")
            elif scope_review_status == "unknown":
                blockers.append("claim_scope_review_unknown")

            report_claims.append(
                {
                    "claim_id": claim_id,
                    "dependent_sentence_ids": sentence_ids,
                    "required_support": required_support,
                    "support_class": support_class,
                    "scope_review_status": scope_review_status,
                    "linked_evidence_ids": sorted(str(item["evidence_id"]) for item in linked),
                    "verified_official_evidence_ids": official_ids,
                    "party_supplied_evidence_ids": party_ids,
                    "discovery_or_unverified_evidence_ids": discovery_ids,
                    "missing_evidence_ids": missing_ids,
                    "support_gate_passed": not blockers,
                    "blockers": sorted(set(blockers)),
                }
            )

        filing_ready = bool(report_claims) and all(item["support_gate_passed"] for item in report_claims)
        return {
            "schema_version": "1.0.0",
            "claim_count": len(report_claims),
            "supported_claim_count": sum(bool(item["support_gate_passed"]) for item in report_claims),
            "coverage_state": "complete" if filing_ready else ("partial" if report_claims else "unknown"),
            "filing_ready": filing_ready,
            "claims": report_claims,
        }

    def pre_filing_freshness_report(
        self,
        claims: Sequence[Mapping[str, Any]],
        *,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Revalidate freshness gates for claim dependencies at filing time.

        An unchanged refresh extends the effective check time through the
        append-only refresh event.  A changed refresh invalidates only the
        claims explicitly recorded as depending on that source.
        """

        coverage = self.claim_source_coverage_report(claims)
        evidence_records = self.evidence.records()
        evidence_by_id = {
            str(record.get("evidence_id")): record
            for record in evidence_records
            if record.get("evidence_id")
        }
        latest_by_origin: Dict[tuple[str, str], Mapping[str, Any]] = {}
        for record in evidence_records:
            latest_by_origin[(str(record.get("source_id")), str(record.get("origin_url")))] = record
        refresh_events = self.refresh_events.records()
        authoritative_for_current_filing = as_of is None
        if as_of is None:
            trusted_now = self.clock()
            if not isinstance(trusted_now, datetime) or trusted_now.tzinfo is None:
                raise ValueError("trusted clock must return a timezone-aware datetime")
            report_time_text = trusted_now.astimezone(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            )
        else:
            report_time_text = as_of
        report_time = _parse_timestamp(report_time_text)
        if report_time is None:
            raise ValueError("as_of must be an ISO-8601 timestamp")

        coverage_by_id = {item["claim_id"]: item for item in coverage["claims"]}
        report_claims: list[Dict[str, Any]] = []
        invalidated_claim_ids: list[str] = []
        invalidated_sentence_ids: list[str] = []
        for raw_claim in claims:
            claim_id = str(raw_claim.get("claim_id") or "").strip()
            coverage_claim = coverage_by_id[claim_id]
            evidence_ids = coverage_claim["linked_evidence_ids"]
            reviewed_at = _parse_timestamp(raw_claim.get("reviewed_at"))
            evidence_freshness: list[Dict[str, Any]] = []
            blockers = list(coverage_claim["blockers"])
            if not authoritative_for_current_filing:
                blockers.append("historical_as_of_non_authoritative")
            effective_checks: list[datetime] = []
            source_changed = False

            for event in refresh_events:
                if claim_id not in (event.get("invalidated_claim_ids") or []):
                    continue
                changed_at = _parse_timestamp(event.get("compared_at"))
                if reviewed_at is None or changed_at is None or changed_at >= reviewed_at:
                    source_changed = True
            if source_changed:
                blockers.append("source_changed_since_claim_review")

            for evidence_id in evidence_ids:
                evidence = evidence_by_id[evidence_id]
                source = self.registry.get(str(evidence.get("source_id")))
                freshness = source.get("freshness") or {}
                max_age_days = freshness.get("max_age_days")
                checked_at = _parse_timestamp(evidence.get("retrieved_at"))
                for event in refresh_events:
                    if event.get("state") != "unchanged":
                        continue
                    if event.get("current_evidence_id") != evidence_id:
                        continue
                    event_time = _parse_timestamp(event.get("compared_at"))
                    if event_time and (checked_at is None or event_time > checked_at):
                        checked_at = event_time
                latest = latest_by_origin.get(
                    (str(evidence.get("source_id")), str(evidence.get("origin_url")))
                )
                state = "unknown"
                if latest and latest.get("evidence_id") != evidence_id:
                    state = "superseded"
                    blockers.append("source_evidence_superseded")
                elif checked_at is None or not isinstance(max_age_days, int):
                    blockers.append("source_freshness_unknown")
                else:
                    age_seconds = (report_time - checked_at).total_seconds()
                    state = "current" if age_seconds <= max_age_days * 86400 else "stale"
                    if state == "stale":
                        blockers.append("source_freshness_stale")
                    effective_checks.append(checked_at)
                evidence_freshness.append(
                    {
                        "evidence_id": evidence_id,
                        "source_id": evidence.get("source_id"),
                        "freshness_mode": freshness.get("mode"),
                        "max_age_days": max_age_days,
                        "effective_checked_at": checked_at.isoformat().replace("+00:00", "Z") if checked_at else None,
                        "state": state,
                    }
                )

            unique_blockers = sorted(set(blockers))
            if source_changed:
                claim_state = "invalidated"
                invalidated_claim_ids.append(claim_id)
                invalidated_sentence_ids.extend(coverage_claim["dependent_sentence_ids"])
            elif any(item["state"] == "superseded" for item in evidence_freshness):
                claim_state = "stale"
            elif any(item["state"] == "stale" for item in evidence_freshness):
                claim_state = "stale"
            elif unique_blockers or not evidence_freshness:
                claim_state = "unknown"
            else:
                claim_state = "current"
            effective_checked_at = min(effective_checks) if effective_checks else None
            report_claims.append(
                {
                    "claim_id": claim_id,
                    "dependent_sentence_ids": coverage_claim["dependent_sentence_ids"],
                    "freshness_state": claim_state,
                    "effective_checked_at": (
                        effective_checked_at.isoformat().replace("+00:00", "Z")
                        if effective_checked_at
                        else None
                    ),
                    "evidence": evidence_freshness,
                    "blockers": unique_blockers,
                }
            )

        states = {item["freshness_state"] for item in report_claims}
        if "invalidated" in states:
            freshness_state = "invalidated"
        elif "stale" in states:
            freshness_state = "stale"
        elif "unknown" in states or not states:
            freshness_state = "unknown"
        else:
            freshness_state = "current"
        pre_filing_ready = (
            authoritative_for_current_filing
            and coverage["filing_ready"]
            and freshness_state == "current"
        )
        return {
            "schema_version": "1.0.0",
            "checked_at": report_time.isoformat().replace("+00:00", "Z"),
            "report_mode": (
                "current_filing_validation"
                if authoritative_for_current_filing
                else "historical_audit"
            ),
            "authoritative_for_current_filing": authoritative_for_current_filing,
            "freshness_state": freshness_state,
            "pre_filing_ready": pre_filing_ready,
            "claim_coverage": coverage,
            "invalidated_claim_ids": sorted(set(invalidated_claim_ids)),
            "invalidated_sentence_ids": sorted(set(invalidated_sentence_ids)),
            "claims": report_claims,
        }

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
        current_authority = [
            self.current_filing_authority(item) for item in self.evidence.records()
        ]
        return {
            "schema_version": "1.0.0",
            "observation_count": len(observations),
            "status_counts": dict(sorted(statuses.items())),
            "coverage_state": "partial" if partial else ("observed" if observations else "unknown"),
            "absence_claim_permitted": absence_claim_permitted,
            "verified_official_evidence_ids": sorted(
                item["evidence_id"]
                for item in current_authority
                if item["filing_ready"] is True
            ),
            "current_authority_blockers": {
                item["evidence_id"]: item["blockers"]
                for item in current_authority
                if item["blockers"]
            },
        }
