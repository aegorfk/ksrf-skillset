"""Tamper-evident, host-attested approvals for filing-significant gates.

JSONL is storage, never authority. Filing-significant records are accepted only
when a host-injected verifier authenticates the actor assertion at creation and
verifies an attestation over the complete canonical record body at validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Protocol, TextIO

from .storage import AppendOnlyJsonlLedger, canonical_json_bytes, stable_id


class TrustedApprovalError(ValueError):
    pass


class HostApprovalVerifier(Protocol):
    """Application-owned trust boundary; never construct it from request data."""

    verifier_id: str

    def verify_actor_assertion(self, assertion: Any) -> Mapping[str, Any]: ...

    def attest_record(
        self,
        kind: str,
        canonical_body: bytes,
        verified_actor_claims: Mapping[str, Any],
    ) -> Any: ...

    def verify_record_attestation(
        self,
        kind: str,
        canonical_body: bytes,
        attestation: Any,
    ) -> bool: ...


_CONTEXT_ATTESTATION = object()
_TRUSTED_CHANNELS = {"interactive_tty", "authenticated_server"}
FILING_SIGNIFICANT_PURPOSES = frozenset({"source_identity", "application", "issue", "release"})
_MAX_AUTHENTICATION_AGE = timedelta(hours=12)
_REQUIRED_ACTOR_CLAIMS = (
    "actor_id",
    "actor_display_name",
    "session_id",
    "authenticated_at",
    "verification_method",
    "assertion_id",
)


def _system_clock() -> datetime:
    return datetime.now(timezone.utc)


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


def _canonical_timestamp(value: Any, *, label: str) -> str:
    parsed = _parse_timestamp(value)
    if parsed is None:
        raise TrustedApprovalError(f"{label} must be an ISO-8601 timestamp")
    return parsed.isoformat().replace("+00:00", "Z")


def _clock_timestamp(clock: Callable[[], datetime]) -> str:
    try:
        value = clock()
    except Exception as exc:  # pragma: no cover - defensive host boundary
        raise TrustedApprovalError("trusted clock failed") from exc
    if not isinstance(value, datetime):
        raise TrustedApprovalError("trusted clock must return datetime")
    if value.tzinfo is None:
        raise TrustedApprovalError("trusted clock must return timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _record_body(record: Mapping[str, Any], *, id_field: str) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in record.items()
        if key not in {id_field, "host_attestation"}
    }


@dataclass(frozen=True)
class TrustedActorContext:
    actor_id: str
    actor_display_name: str
    session_id: str
    channel: str
    authenticated_at: str
    verification_method: str
    assertion_id: str
    host_verifier_id: Optional[str]
    _verified_actor_claims: Mapping[str, Any] = field(repr=False, compare=False)
    _attestation: object = field(repr=False, compare=False)


def _interactive_context(
    *,
    actor_id: str,
    actor_display_name: str,
    session_id: str,
    authenticated_at: Any,
) -> TrustedActorContext:
    values = {
        "actor_id": str(actor_id).strip(),
        "actor_display_name": str(actor_display_name).strip(),
        "session_id": str(session_id).strip(),
        "authenticated_at": _canonical_timestamp(authenticated_at, label="authenticated_at"),
        "verification_method": "local_interactive_tty",
        "assertion_id": f"local-tty:{str(session_id).strip()}",
    }
    if not all(values.values()):
        raise TrustedApprovalError("trusted actor context is incomplete")
    return TrustedActorContext(
        **values,
        channel="interactive_tty",
        host_verifier_id=None,
        _verified_actor_claims=values,
        _attestation=_CONTEXT_ATTESTATION,
    )


def _authenticated_context(
    *,
    assertion: Any,
    host_verifier: HostApprovalVerifier,
) -> TrustedActorContext:
    verifier_id = str(getattr(host_verifier, "verifier_id", "") or "").strip()
    if not verifier_id:
        raise TrustedApprovalError("host verifier identity is required")
    try:
        verified = host_verifier.verify_actor_assertion(assertion)
    except TrustedApprovalError:
        raise
    except Exception as exc:
        raise TrustedApprovalError("host actor assertion verification failed") from exc
    if not isinstance(verified, Mapping):
        raise TrustedApprovalError("host verifier must return canonical actor claims")
    claims = {key: str(verified.get(key) or "").strip() for key in _REQUIRED_ACTOR_CLAIMS}
    if not all(claims.values()):
        raise TrustedApprovalError("host-verified actor claims are incomplete")
    claims["authenticated_at"] = _canonical_timestamp(
        claims["authenticated_at"], label="authenticated_at"
    )
    return TrustedActorContext(
        actor_id=claims["actor_id"],
        actor_display_name=claims["actor_display_name"],
        session_id=claims["session_id"],
        channel="authenticated_server",
        authenticated_at=claims["authenticated_at"],
        verification_method=claims["verification_method"],
        assertion_id=claims["assertion_id"],
        host_verifier_id=verifier_id,
        _verified_actor_claims=claims,
        _attestation=_CONTEXT_ATTESTATION,
    )


def interactive_tty_context(
    *,
    stream: TextIO,
    actor_id: str,
    actor_display_name: str,
    session_id: str,
    authenticated_at: Optional[str] = None,
) -> TrustedActorContext:
    if not hasattr(stream, "isatty") or not stream.isatty():
        raise TrustedApprovalError("approval creation requires an interactive TTY")
    return _interactive_context(
        actor_id=actor_id,
        actor_display_name=actor_display_name,
        session_id=session_id,
        authenticated_at=authenticated_at or _system_clock(),
    )


def _require_trusted_context(context: TrustedActorContext) -> None:
    if not isinstance(context, TrustedActorContext) or context._attestation is not _CONTEXT_ATTESTATION:
        raise TrustedApprovalError("approval requires a trusted actor context")


class TrustedApprovalLedger:
    def __init__(
        self,
        root: Path,
        *,
        host_verifier: Optional[HostApprovalVerifier] = None,
        clock: Callable[[], datetime] = _system_clock,
    ) -> None:
        self.root = Path(root)
        self.approvals = AppendOnlyJsonlLedger(self.root / "approvals.jsonl")
        self.revocations = AppendOnlyJsonlLedger(self.root / "revocations.jsonl")
        self.host_verifier = host_verifier
        self.clock = clock

    def authenticate_actor(self, assertion: Any) -> TrustedActorContext:
        if self.host_verifier is None:
            raise TrustedApprovalError("host verifier is not configured")
        return _authenticated_context(assertion=assertion, host_verifier=self.host_verifier)

    def _is_matching_host_context(self, context: TrustedActorContext) -> bool:
        return bool(
            self.host_verifier is not None
            and context.channel == "authenticated_server"
            and context.host_verifier_id
            == str(getattr(self.host_verifier, "verifier_id", "") or "").strip()
        )

    def _attest(
        self,
        *,
        kind: str,
        body: Mapping[str, Any],
        context: TrustedActorContext,
    ) -> Any:
        if self.host_verifier is None or not self._is_matching_host_context(context):
            raise TrustedApprovalError("filing-significant action requires a matching host verifier")
        try:
            attestation = self.host_verifier.attest_record(
                kind,
                canonical_json_bytes(body),
                context._verified_actor_claims,
            )
        except Exception as exc:
            raise TrustedApprovalError("host record attestation failed") from exc
        if attestation in (None, "", {}):
            raise TrustedApprovalError("host verifier returned an empty record attestation")
        return attestation

    def create_approval(
        self,
        *,
        purpose: str,
        subject_type: str,
        subject_id: str,
        fingerprint: str,
        bindings: Mapping[str, Any],
        context: TrustedActorContext,
        expires_at: str,
    ) -> dict[str, Any]:
        _require_trusted_context(context)
        required = {
            "purpose": str(purpose).strip(),
            "subject_type": str(subject_type).strip(),
            "subject_id": str(subject_id).strip(),
            "fingerprint": str(fingerprint).strip(),
        }
        if not all(required.values()) or not isinstance(bindings, Mapping) or not bindings:
            raise TrustedApprovalError("approval subject and bindings are required")
        filing_significant = required["purpose"] in FILING_SIGNIFICANT_PURPOSES
        if filing_significant and not self._is_matching_host_context(context):
            raise TrustedApprovalError(
                "filing-significant approval requires a matching host verifier"
            )
        approved = _clock_timestamp(self.clock)
        expires = _canonical_timestamp(expires_at, label="expires_at")
        authenticated_at = _parse_timestamp(context.authenticated_at)
        approved_timestamp = _parse_timestamp(approved)
        if (
            authenticated_at is None
            or approved_timestamp is None
            or approved_timestamp < authenticated_at
            or approved_timestamp - authenticated_at > _MAX_AUTHENTICATION_AGE
        ):
            raise TrustedApprovalError("actor authentication is not fresh for approval creation")
        if _parse_timestamp(expires) <= approved_timestamp:
            raise TrustedApprovalError("expires_at must be after approved_at")
        body = {
            "schema_version": "1.0.0",
            **required,
            "bindings": dict(bindings),
            "actor_id": context.actor_id,
            "actor_display_name": context.actor_display_name,
            "actor_provenance": {
                "channel": context.channel,
                "session_id": context.session_id,
                "authenticated_at": context.authenticated_at,
                "verification_method": context.verification_method,
                "assertion_id": context.assertion_id,
                "host_verifier_id": context.host_verifier_id,
            },
            "approved_at": approved,
            "expires_at": expires,
        }
        record = {
            **body,
            "host_attestation": (
                self._attest(kind="approval", body=body, context=context)
                if filing_significant
                else None
            ),
            "approval_id": stable_id("trusted-approval", body),
        }
        existing = [
            item for item in self.approvals if item.get("approval_id") == record["approval_id"]
        ]
        if existing:
            if all(item == record for item in existing):
                return existing[0]
            raise TrustedApprovalError("conflicting approval_id already exists")
        self.approvals.append(record)
        return record

    def revoke_approval(
        self,
        approval_id: str,
        *,
        context: TrustedActorContext,
        reason: str,
    ) -> dict[str, Any]:
        _require_trusted_context(context)
        matches = [item for item in self.approvals if item.get("approval_id") == approval_id]
        if not matches:
            raise TrustedApprovalError("approval does not exist")
        if any(item != matches[0] for item in matches[1:]):
            raise TrustedApprovalError("approval_id conflict prevents revocation")
        approval = matches[0]
        filing_significant = approval.get("purpose") in FILING_SIGNIFICANT_PURPOSES
        if filing_significant and not self._is_matching_host_context(context):
            raise TrustedApprovalError(
                "filing-significant revocation requires a matching host verifier"
            )
        reason_text = str(reason).strip()
        if not reason_text:
            raise TrustedApprovalError("revocation reason is required")
        body = {
            "schema_version": "1.0.0",
            "approval_id": str(approval_id),
            "actor_id": context.actor_id,
            "actor_provenance": {
                "channel": context.channel,
                "session_id": context.session_id,
                "authenticated_at": context.authenticated_at,
                "verification_method": context.verification_method,
                "assertion_id": context.assertion_id,
                "host_verifier_id": context.host_verifier_id,
            },
            "reason": reason_text,
            "revoked_at": _clock_timestamp(self.clock),
        }
        event = {
            **body,
            "host_attestation": (
                self._attest(kind="revocation", body=body, context=context)
                if filing_significant
                else None
            ),
            "revocation_id": stable_id("trusted-approval-revocation", body),
        }
        existing = [
            item
            for item in self.revocations
            if item.get("revocation_id") == event["revocation_id"]
        ]
        if existing:
            if all(item == event for item in existing):
                return existing[0]
            raise TrustedApprovalError("conflicting revocation_id already exists")
        self.revocations.append(event)
        return event

    def _verify_attestation(
        self,
        *,
        kind: str,
        body: Mapping[str, Any],
        attestation: Any,
    ) -> bool:
        if self.host_verifier is None:
            return False
        try:
            return self.host_verifier.verify_record_attestation(
                kind,
                canonical_json_bytes(body),
                attestation,
            ) is True
        except Exception:
            return False

    def validate_approval(
        self,
        approval_id: str,
        *,
        purpose: str,
        subject_type: str,
        subject_id: str,
        fingerprint: str,
        bindings: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self._validate_approval(
            approval_id,
            purpose=purpose,
            subject_type=subject_type,
            subject_id=subject_id,
            fingerprint=fingerprint,
            bindings=bindings,
            checked_at_text=_clock_timestamp(self.clock),
        )

    def audit_approval(
        self,
        approval_id: str,
        *,
        purpose: str,
        subject_type: str,
        subject_id: str,
        fingerprint: str,
        bindings: Mapping[str, Any],
        historical_as_of: str,
    ) -> dict[str, Any]:
        """Historical audit only; never use this result for a current filing gate."""

        result = self._validate_approval(
            approval_id,
            purpose=purpose,
            subject_type=subject_type,
            subject_id=subject_id,
            fingerprint=fingerprint,
            bindings=bindings,
            checked_at_text=_canonical_timestamp(historical_as_of, label="historical_as_of"),
        )
        return {
            **result,
            "audit_only": True,
            "authoritative_for_current_filing": False,
        }

    def _validate_approval(
        self,
        approval_id: str,
        *,
        purpose: str,
        subject_type: str,
        subject_id: str,
        fingerprint: str,
        bindings: Mapping[str, Any],
        checked_at_text: str,
    ) -> dict[str, Any]:
        records = [item for item in self.approvals if item.get("approval_id") == approval_id]
        if not records:
            return {"valid": False, "reason_code": "approval_not_found", "approval": None}
        if any(item != records[0] for item in records[1:]):
            return {"valid": False, "reason_code": "approval_id_conflict", "approval": None}
        record = records[0]
        body = _record_body(record, id_field="approval_id")
        if stable_id("trusted-approval", body) != approval_id:
            return {"valid": False, "reason_code": "approval_integrity_invalid", "approval": record}
        filing_significant = str(purpose) in FILING_SIGNIFICANT_PURPOSES
        provenance = record.get("actor_provenance") or {}
        if provenance.get("channel") not in _TRUSTED_CHANNELS:
            return {"valid": False, "reason_code": "approval_untrusted_channel", "approval": record}
        if filing_significant and self.host_verifier is None:
            return {
                "valid": False,
                "reason_code": "approval_host_verifier_unavailable",
                "approval": record,
            }
        if filing_significant and provenance.get("channel") != "authenticated_server":
            return {
                "valid": False,
                "reason_code": "approval_channel_insufficient_for_purpose",
                "approval": record,
            }
        expected_verifier_id = str(getattr(self.host_verifier, "verifier_id", "") or "").strip()
        if filing_significant and provenance.get("host_verifier_id") != expected_verifier_id:
            return {
                "valid": False,
                "reason_code": "approval_host_verifier_mismatch",
                "approval": record,
            }
        if filing_significant and not self._verify_attestation(
            kind="approval", body=body, attestation=record.get("host_attestation")
        ):
            return {
                "valid": False,
                "reason_code": "approval_host_attestation_invalid",
                "approval": record,
            }
        expected = {
            "purpose": str(purpose),
            "subject_type": str(subject_type),
            "subject_id": str(subject_id),
            "fingerprint": str(fingerprint),
            "bindings": dict(bindings),
        }
        if any(record.get(key) != value for key, value in expected.items()):
            return {"valid": False, "reason_code": "approval_binding_mismatch", "approval": record}
        actor_authenticated_at = _parse_timestamp(provenance.get("authenticated_at"))
        approved_at = _parse_timestamp(record.get("approved_at"))
        actor_provenance_complete = all(
            str(value or "").strip()
            for value in (
                record.get("actor_id"),
                record.get("actor_display_name"),
                provenance.get("session_id"),
                provenance.get("verification_method"),
                provenance.get("assertion_id"),
            )
        )
        if (
            not actor_provenance_complete
            or actor_authenticated_at is None
            or approved_at is None
            or approved_at < actor_authenticated_at
            or approved_at - actor_authenticated_at > _MAX_AUTHENTICATION_AGE
        ):
            return {
                "valid": False,
                "reason_code": "approval_actor_provenance_invalid",
                "approval": record,
            }
        checked_at = _parse_timestamp(checked_at_text)
        expires_at = _parse_timestamp(record.get("expires_at"))
        if checked_at is None or expires_at is None or checked_at < approved_at:
            return {"valid": False, "reason_code": "approval_not_yet_valid", "approval": record}
        if checked_at > expires_at:
            return {"valid": False, "reason_code": "approval_expired", "approval": record}

        revocations = [
            item for item in self.revocations if item.get("approval_id") == approval_id
        ]
        by_revocation_id: dict[str, list[Mapping[str, Any]]] = {}
        for event in revocations:
            by_revocation_id.setdefault(str(event.get("revocation_id") or ""), []).append(event)
        for revocation_id, events in by_revocation_id.items():
            if not revocation_id or any(item != events[0] for item in events[1:]):
                return {
                    "valid": False,
                    "reason_code": "approval_revocation_conflict",
                    "approval": record,
                }
            event = events[0]
            event_body = _record_body(event, id_field="revocation_id")
            if stable_id("trusted-approval-revocation", event_body) != revocation_id:
                return {
                    "valid": False,
                    "reason_code": "approval_revocation_integrity_invalid",
                    "approval": record,
                }
            if filing_significant and not self._verify_attestation(
                kind="revocation",
                body=event_body,
                attestation=event.get("host_attestation"),
            ):
                return {
                    "valid": False,
                    "reason_code": "approval_revocation_attestation_invalid",
                    "approval": record,
                }
            revoked_at = _parse_timestamp(event.get("revoked_at"))
            if revoked_at is None:
                return {
                    "valid": False,
                    "reason_code": "approval_revocation_integrity_invalid",
                    "approval": record,
                }
            if revoked_at <= checked_at:
                return {"valid": False, "reason_code": "approval_revoked", "approval": record}
        return {
            "valid": True,
            "reason_code": "approval_valid",
            "approval": record,
            "checked_at": checked_at_text,
        }
