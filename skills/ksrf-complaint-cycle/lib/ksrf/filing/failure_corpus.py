from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Protocol, Sequence

from .storage import (
    AppendOnlyJsonlLedger,
    ContentAddressedStore,
    canonical_json_bytes,
    count_by,
    sha256_bytes,
    stable_id,
    utc_now,
)


_OFFICIAL_CLASSES = {"official_primary", "official_derivative"}
_REVIEW_DECISIONS = {"unreviewed", "approved", "corrected", "rejected", "blocked_for_source"}
_SUBMISSION_EVENT_TYPES = {
    "complaint",
    "secretariat_notice",
    "cure",
    "resubmission",
    "judicial_disposition",
}
_CONSENT_PURPOSES = {
    "same_matter",
    "cross_matter_retrieval",
    "evaluation",
    "model_training",
    "anonymized_publication",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)


class ProjectionSink(Protocol):
    def upsert_public(self, record: Mapping[str, Any]) -> str:
        ...

    def purge(self, projection_ids: Sequence[str]) -> None:
        ...


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace("ё", "е").split())


def _tokens(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        text = " ".join(str(item) for pair in value.items() for item in pair)
    elif isinstance(value, (list, tuple, set)):
        text = " ".join(str(item) for item in value)
    else:
        text = str(value or "")
    return {_normalize_text(item) for item in _TOKEN_RE.findall(text) if len(item) > 1}


def _latest_by_key(records: Iterable[Mapping[str, Any]], key: str) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for record in records:
        value = str(record.get(key) or "")
        if value:
            result[value] = dict(record)
    return result


class FailureCorpus:
    def __init__(self, root: Path, *, taxonomy_path: Optional[Path] = None) -> None:
        self.root = Path(root)
        self.public_objects = ContentAddressedStore(self.root, "failure-public")
        self.private_objects = ContentAddressedStore(self.root, "failure-private")
        self.shared_objects = ContentAddressedStore(self.root, "failure-shared")
        self.public_records = AppendOnlyJsonlLedger(self.root / "failure-public" / "petition-units.jsonl")
        self.public_reviews = AppendOnlyJsonlLedger(self.root / "failure-public" / "reviews.jsonl")
        self.access_failures = AppendOnlyJsonlLedger(self.root / "failure-public" / "access-failures.jsonl")
        self.private_records = AppendOnlyJsonlLedger(self.root / "failure-private" / "records.jsonl")
        self.consents = AppendOnlyJsonlLedger(self.root / "failure-private" / "consents.jsonl")
        self.consent_events = AppendOnlyJsonlLedger(self.root / "failure-private" / "consent-events.jsonl")
        self.submission_events = AppendOnlyJsonlLedger(self.root / "failure-private" / "submission-events.jsonl")
        self.redactions = AppendOnlyJsonlLedger(self.root / "failure-shared" / "redactions.jsonl")
        self.derivatives = AppendOnlyJsonlLedger(self.root / "failure-shared" / "derivatives.jsonl")
        self.tombstones = AppendOnlyJsonlLedger(self.root / "failure-shared" / "tombstones.jsonl")
        self.projection_events = AppendOnlyJsonlLedger(self.root / "failure-public" / "projection-events.jsonl")
        taxonomy_file = taxonomy_path or (_repository_root() / "configs" / "ksrf_refusal_taxonomy.v1.json")
        taxonomy = json.loads(Path(taxonomy_file).read_text(encoding="utf-8"))
        if not taxonomy.get("schema_version") or not isinstance(taxonomy.get("categories"), list):
            raise ValueError("invalid refusal taxonomy")
        self.taxonomy_version = str(taxonomy["schema_version"])
        self.taxonomy = {str(item["code"]): dict(item) for item in taxonomy["categories"]}

    def _validate_public_source(self, source: Mapping[str, Any]) -> None:
        if source.get("authority_class") not in _OFFICIAL_CLASSES:
            raise ValueError("public refusal requires official source authority")
        if source.get("filing_authority_state") != "verified_official":
            raise ValueError("public refusal requires verified official source identity")
        raw = source.get("raw_object") or {}
        if not source.get("evidence_id") or not _SHA256_RE.fullmatch(str(raw.get("sha256") or "")):
            raise ValueError("public refusal requires source evidence id and SHA-256")

    def _normalize_reasons(self, reasons: Any, *, petition_unit_id: str) -> list[Dict[str, Any]]:
        if not isinstance(reasons, list) or not reasons:
            raise ValueError("petition unit requires at least one refusal reason")
        normalized = []
        for index, raw in enumerate(reasons):
            reason = copy.deepcopy(dict(raw))
            code = str(reason.get("code") or "")
            if code not in self.taxonomy:
                raise ValueError(f"unknown refusal taxonomy code: {code}")
            if reason.get("role") not in {"primary", "ancillary"}:
                raise ValueError("refusal reason role must be primary or ancillary")
            if not reason.get("statement") or not reason.get("locator"):
                raise ValueError("refusal reason requires statement and locator")
            reason["taxonomy_version"] = self.taxonomy_version
            reason["extraction_status"] = "unreviewed"
            reason["reason_id"] = stable_id(
                "refusal-reason",
                {"petition_unit_id": petition_unit_id, "index": index, "reason": reason},
            )
            normalized.append(reason)
        return normalized

    def _current_public_records(self) -> list[Dict[str, Any]]:
        current = _latest_by_key(self.public_records, "petition_unit_id")
        return list(current.values())

    def ingest_public_refusal(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        source = payload.get("source_evidence") or {}
        self._validate_public_source(source)
        act_number = str(payload.get("act_number") or "").strip()
        act_date = str(payload.get("act_date") or "").strip()
        extractor_version = str(payload.get("extractor_version") or "").strip()
        extraction_method = str(payload.get("extraction_method") or "").strip()
        units = payload.get("petition_units")
        if not act_number or not act_date or not extractor_version or not extraction_method or not isinstance(units, list) or not units:
            raise ValueError("public refusal requires act identity, extractor provenance and petition_units[]")
        source_sha256 = str((source.get("raw_object") or {}).get("sha256"))
        inserted = 0
        duplicates = 0
        output = []
        existing_by_record = _latest_by_key(self.public_records, "record_id")
        current_by_unit = _latest_by_key(self.public_records, "petition_unit_id")

        for unit in units:
            unit = copy.deepcopy(dict(unit))
            locator = str(unit.get("unit_locator") or "").strip()
            signature = unit.get("challenged_norm_signature") or {}
            if not locator or not isinstance(signature.get("norm_ids"), list):
                raise ValueError("petition unit requires locator and challenged norm signature")
            petition_unit_id = stable_id(
                "ksrf-petition-unit",
                {
                    "source_evidence_id": source.get("evidence_id"),
                    "unit_locator": locator,
                    "norm_ids": sorted(str(item) for item in signature.get("norm_ids") or []),
                },
            )
            body = {
                "schema_version": "1.0.0",
                "petition_unit_id": petition_unit_id,
                "petition_claim_source": "ksrf_act_summary",
                "source_evidence_id": source.get("evidence_id"),
                "source_sha256": source_sha256,
                "official_url": source.get("origin_url"),
                "act_number": act_number,
                "act_date": act_date,
                "extractor_version": extractor_version,
                "extraction_method": extraction_method,
                "unit_locator": locator,
                "applicant_category": unit.get("applicant_category") or "unknown",
                "dispute_category": unit.get("dispute_category") or "unknown",
                "challenged_norm_signature": signature,
                "applicant_claim": unit.get("applicant_claim"),
                "ksrf_reframed_question": unit.get("ksrf_reframed_question"),
                "actually_answered_question": unit.get("actually_answered_question"),
                "disputed_meaning": unit.get("disputed_meaning"),
                "application_pattern": unit.get("application_pattern"),
                "constitutional_benchmarks": list(unit.get("constitutional_benchmarks") or []),
                "requested_remedy": unit.get("requested_remedy"),
                "procedural_disposition": unit.get("procedural_disposition"),
                "positive_remainder": unit.get("positive_remainder"),
                "repair_delta": unit.get("repair_delta"),
                "inference_confidence": unit.get("inference_confidence"),
                "review_status": "unreviewed",
                "ingested_at": utc_now(),
            }
            body["refusal_reasons"] = self._normalize_reasons(
                unit.get("refusal_reasons"), petition_unit_id=petition_unit_id
            )
            record_id = stable_id(
                "public-refusal-record",
                {"petition_unit_id": petition_unit_id, "source_sha256": source_sha256},
            )
            body["record_id"] = record_id
            previous = current_by_unit.get(petition_unit_id)
            body["supersedes_record_id"] = (
                previous.get("record_id") if previous and previous.get("record_id") != record_id else None
            )
            record_content = {key: value for key, value in body.items() if key != "ingested_at"}
            body["record_object"] = self.public_objects.put_bytes(canonical_json_bytes(record_content))
            if record_id in existing_by_record:
                duplicates += 1
                output.append(existing_by_record[record_id])
            else:
                self.public_records.append(body)
                existing_by_record[record_id] = body
                current_by_unit[petition_unit_id] = body
                inserted += 1
                output.append(body)
        return {
            "records": output,
            "inserted_count": inserted,
            "duplicate_count": duplicates,
        }

    def read_public_record(self, record_id: str) -> Dict[str, Any]:
        record = self.public_records.latest_by("record_id", record_id)
        if record is None:
            raise KeyError(f"unknown public refusal record: {record_id}")
        content = self.public_objects.read_bytes(record["record_object"])
        value = json.loads(content)
        if not isinstance(value, dict):
            raise ValueError("content-addressed public record is not an object")
        return value

    def review_public_record(
        self,
        record_id: str,
        *,
        decision: str,
        reviewer: str,
        corrections: Optional[Mapping[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        if decision not in _REVIEW_DECISIONS - {"unreviewed"}:
            raise ValueError(f"invalid review decision: {decision}")
        if not reviewer.strip():
            raise ValueError("named reviewer is required")
        source = self.public_records.latest_by("record_id", record_id)
        if source is None:
            raise KeyError(f"unknown public refusal record: {record_id}")
        body = {
            "schema_version": "1.0.0",
            "record_id": record_id,
            "decision": decision,
            "reviewer": reviewer,
            "reviewed_at": utc_now(),
            "reason": reason,
            "corrections": copy.deepcopy(dict(corrections or {})),
        }
        review = dict(body)
        review["review_id"] = stable_id("refusal-review", body)
        self.public_reviews.append(review)
        return review

    def _review_for(self, record_id: str) -> Optional[Dict[str, Any]]:
        return self.public_reviews.latest_by("record_id", record_id)

    def review_queue(self) -> Dict[str, Any]:
        items = []
        for record in self._current_public_records():
            review = self._review_for(str(record["record_id"]))
            status = str((review or {}).get("decision") or "unreviewed")
            items.append(
                {
                    "record_id": record["record_id"],
                    "petition_unit_id": record["petition_unit_id"],
                    "act_number": record["act_number"],
                    "status": status,
                }
            )
        return {"items": items, "status_counts": count_by(items, "status")}

    def _effective_public_record(self, record: Mapping[str, Any]) -> tuple[Dict[str, Any], str]:
        effective = copy.deepcopy(dict(record))
        review = self._review_for(str(record["record_id"]))
        status = str((review or {}).get("decision") or "unreviewed")
        if status == "corrected" and review:
            effective.update(copy.deepcopy(dict(review.get("corrections") or {})))
        effective["review_status"] = status
        return effective, status

    def search_adverse(self, query: Mapping[str, Any], *, limit: int = 20) -> Dict[str, Any]:
        query_norms = {str(item) for item in query.get("norm_ids") or []}
        query_tokens = _tokens(query)
        hits = []
        for raw_record in self._current_public_records():
            record, review_status = self._effective_public_record(raw_record)
            record_norms = {
                str(item)
                for item in (record.get("challenged_norm_signature") or {}).get("norm_ids") or []
            }
            norm_match = bool(query_norms and query_norms.intersection(record_norms))
            meaning_match = bool(query.get("disputed_meaning")) and _normalize_text(query.get("disputed_meaning")) == _normalize_text(record.get("disputed_meaning"))
            application_match = bool(query.get("application_pattern")) and _normalize_text(query.get("application_pattern")) == _normalize_text(record.get("application_pattern"))
            remedy_match = bool(query.get("requested_remedy")) and _normalize_text(query.get("requested_remedy")) == _normalize_text(record.get("requested_remedy"))
            query_benchmarks = {_normalize_text(item) for item in query.get("constitutional_benchmarks") or []}
            record_benchmarks = {_normalize_text(item) for item in record.get("constitutional_benchmarks") or []}
            benchmark_match = bool(query_benchmarks and query_benchmarks.intersection(record_benchmarks))
            record_tokens = _tokens(
                {
                    "meaning": record.get("disputed_meaning"),
                    "claim": record.get("applicant_claim"),
                    "reasons": [item.get("statement") for item in record.get("refusal_reasons") or []],
                    "remedy": record.get("requested_remedy"),
                }
            )
            lexical = len(query_tokens.intersection(record_tokens)) / max(1, len(query_tokens.union(record_tokens)))
            structural_count = sum((norm_match, meaning_match, application_match, remedy_match, benchmark_match))
            score = structural_count + lexical
            if score <= 0:
                continue
            material = norm_match and meaning_match and application_match and remedy_match
            differences = []
            if not norm_match:
                differences.append("challenged_norm_signature")
            if not meaning_match:
                differences.append("disputed_meaning")
            if not application_match:
                differences.append("application_pattern")
            if not remedy_match:
                differences.append("requested_remedy")
            if query_benchmarks and not benchmark_match:
                differences.append("constitutional_benchmarks")
            hits.append(
                {
                    "record_id": record["record_id"],
                    "petition_unit_id": record["petition_unit_id"],
                    "act_number": record["act_number"],
                    "official_url": record.get("official_url"),
                    "score": round(score, 6),
                    "lexical_score": round(lexical, 6),
                    "material_similarity": "material" if material else "non_material",
                    "differences": differences,
                    "refusal_reasons": record.get("refusal_reasons") or [],
                    "repair_delta": record.get("repair_delta"),
                    "review_status": review_status,
                    "eligible_for_adverse_gate": material and review_status in {"approved", "corrected"},
                    "required_response_task": (
                        "Объяснить отличие текущего дела от отказного аналога и устранить выявленный дефект."
                        if material
                        else "Не использовать как материально сходный аналог без устранения различий."
                    ),
                }
            )
        hits.sort(key=lambda item: (-float(item["score"]), str(item["act_number"]), str(item["record_id"])))
        hits = hits[: max(0, limit)]
        coverage = self.coverage_report()
        if any(item["eligible_for_adverse_gate"] for item in hits):
            conclusion = "verified analogues found"
        elif hits:
            conclusion = "candidate analogues require review"
        else:
            conclusion = "no verified analogue found in searched coverage"
        return {
            "hits": hits,
            "coverage_state": coverage["coverage_state"],
            "conclusion": conclusion,
            "limits": [
                "lexical_or_vector_similarity_is_discovery_only",
                "no_result_is_bounded_to_searched_coverage",
            ],
        }

    def record_access_failure(self, source_id: str, status: str, detail: str) -> Dict[str, Any]:
        if status not in {"unavailable", "interactive_required", "invalid_response", "conflict"}:
            raise ValueError("access failure status is not a failure state")
        body = {
            "schema_version": "1.0.0",
            "source_id": source_id,
            "status": status,
            "detail": detail,
            "observed_at": utc_now(),
        }
        record = dict(body)
        record["access_failure_id"] = stable_id("failure-corpus-access", body)
        self.access_failures.append(record)
        return record

    def record_submission_event(
        self,
        *,
        matter_id: str,
        event_type: str,
        event_at: str,
        evidence_id: str,
        parent_event_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if event_type not in _SUBMISSION_EVENT_TYPES:
            raise ValueError(f"invalid submission event type: {event_type}")
        if not matter_id or not event_at or not evidence_id:
            raise ValueError("submission event requires matter, time and evidence")
        body = {
            "schema_version": "1.0.0",
            "matter_id": matter_id,
            "event_type": event_type,
            "event_at": event_at,
            "evidence_id": evidence_id,
            "parent_event_id": parent_event_id,
            "recorded_at": utc_now(),
        }
        event = dict(body)
        event["event_id"] = stable_id("submission-event", body)
        if not self.submission_events.latest_by("event_id", event["event_id"]):
            self.submission_events.append(event)
        return event

    def submission_timeline(self, matter_id: str) -> Dict[str, Any]:
        events = [item for item in self.submission_events if item.get("matter_id") == matter_id]
        events.sort(key=lambda item: (str(item.get("event_at") or ""), str(item.get("recorded_at") or "")))
        judicial = [item for item in events if item.get("event_type") == "judicial_disposition"]
        return {
            "matter_id": matter_id,
            "events": events,
            "judicial_disposition_state": "known" if judicial else "unknown",
            "judicial_disposition_event_ids": [item["event_id"] for item in judicial],
        }

    def register_private_document(
        self,
        *,
        matter_id: str,
        document_role: str,
        content: bytes,
        consent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not matter_id or not document_role or not content:
            raise ValueError("private document requires matter, role and non-empty content")
        private_object = self.private_objects.put_bytes(content)
        if consent_id:
            consent = self._active_consent(consent_id)
            if consent.get("matter_id") != matter_id:
                raise ValueError("consent matter does not match private document")
            if document_role not in consent.get("document_roles", []):
                raise ValueError("document role is outside consent")
            if private_object["sha256"] not in consent.get("covered_sha256", []):
                raise ValueError("document hash is outside consent")
        body = {
            "schema_version": "1.0.0",
            "matter_id": matter_id,
            "document_role": document_role,
            "private_object": private_object,
            "consent_id": consent_id,
            "retrieval_scope": "matter_only",
            "cross_matter_eligible": False,
            "registered_at": utc_now(),
        }
        record = dict(body)
        record["private_record_id"] = stable_id(
            "private-failure-source",
            {"matter_id": matter_id, "document_role": document_role, "sha256": private_object["sha256"]},
        )
        existing = self.private_records.latest_by("private_record_id", record["private_record_id"])
        if existing:
            return existing
        self.private_records.append(record)
        return record

    def _private_record(self, private_record_id: str) -> Dict[str, Any]:
        record = self.private_records.latest_by("private_record_id", private_record_id)
        if record is None:
            raise KeyError(f"unknown private record: {private_record_id}")
        return record

    def read_private(self, private_record_id: str) -> bytes:
        record = self._private_record(private_record_id)
        return self.private_objects.read_bytes(record["private_object"])

    def _validate_consent(self, payload: Mapping[str, Any]) -> None:
        if not payload.get("consent_version") or not payload.get("matter_id") or not payload.get("evidence_ref"):
            raise ValueError("consent requires version, matter_id and evidence_ref")
        contributor = payload.get("contributor") or {}
        if not contributor.get("contributor_id") or contributor.get("authority_attested") is not True:
            raise ValueError("contributor authority attestation is required")
        if not isinstance(payload.get("document_roles"), list) or not payload.get("document_roles"):
            raise ValueError("document_roles are required")
        hashes = payload.get("covered_sha256")
        if not isinstance(hashes, list) or not hashes or not all(_SHA256_RE.fullmatch(str(item)) for item in hashes):
            raise ValueError("covered_sha256 must contain exact content hashes")
        uses = payload.get("permitted_uses")
        if not isinstance(uses, Mapping) or set(uses) != _CONSENT_PURPOSES:
            raise ValueError("permitted_uses must contain every granular purpose")
        if not all(isinstance(uses[key], bool) for key in _CONSENT_PURPOSES):
            raise ValueError("every permitted use must be boolean")
        if uses.get("same_matter") is not True:
            raise ValueError("same_matter consent must be explicit")
        if not payload.get("granted_at"):
            raise ValueError("granted_at is required")

    def record_consent(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        self._validate_consent(payload)
        body = copy.deepcopy(dict(payload))
        body["schema_version"] = "1.0.0"
        body["status"] = "active"
        body["recorded_at"] = utc_now()
        consent = dict(body)
        consent["consent_id"] = stable_id(
            "failure-corpus-consent",
            {
                "consent_version": body.get("consent_version"),
                "matter_id": body.get("matter_id"),
                "contributor": body.get("contributor"),
                "document_roles": body.get("document_roles"),
                "covered_sha256": body.get("covered_sha256"),
                "permitted_uses": body.get("permitted_uses"),
                "evidence_ref": body.get("evidence_ref"),
            },
        )
        existing = self.consents.latest_by("consent_id", consent["consent_id"])
        if existing:
            return existing
        self.consents.append(consent)
        self.consent_events.append(
            {
                "schema_version": "1.0.0",
                "consent_id": consent["consent_id"],
                "event_type": "granted",
                "event_at": consent["recorded_at"],
            }
        )
        return consent

    def _active_consent(self, consent_id: str) -> Dict[str, Any]:
        consent = self.consents.latest_by("consent_id", consent_id)
        if consent is None:
            raise KeyError(f"unknown consent: {consent_id}")
        event = self.consent_events.latest_by("consent_id", consent_id)
        if event and event.get("event_type") == "withdrawn":
            raise ValueError("consent is withdrawn")
        expires_at = consent.get("expires_at")
        if expires_at:
            expires = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if expires <= datetime.now(timezone.utc):
                raise ValueError("consent is expired")
        return consent

    def promote_redacted_derivative(
        self,
        *,
        private_record_id: str,
        consent_id: str,
        derived_content: bytes,
        unresolved_spans: Sequence[str],
        reviewer: str,
        approved: bool,
    ) -> Dict[str, Any]:
        private = self._private_record(private_record_id)
        consent = self._active_consent(consent_id)
        source_sha256 = str(private["private_object"]["sha256"])
        blockers = []
        if consent.get("matter_id") != private.get("matter_id"):
            blockers.append("consent_matter_mismatch")
        if private.get("document_role") not in consent.get("document_roles", []):
            blockers.append("document_role_outside_consent")
        if source_sha256 not in consent.get("covered_sha256", []):
            blockers.append("source_hash_outside_consent")
        if not (consent.get("permitted_uses") or {}).get("cross_matter_retrieval"):
            blockers.append("cross_matter_retrieval_not_permitted")
        if not derived_content:
            blockers.append("empty_derivative")
        if unresolved_spans:
            blockers.append("unresolved_redaction_spans")
        if not approved or not reviewer.strip():
            blockers.append("human_approval_missing")
        derived_sha256 = sha256_bytes(derived_content)
        redaction_body = {
            "schema_version": "1.0.0",
            "private_record_id": private_record_id,
            "consent_id": consent_id,
            "source_sha256": source_sha256,
            "derived_sha256": derived_sha256,
            "automated_check_status": "blocked" if unresolved_spans else "passed",
            "unresolved_spans": list(unresolved_spans),
            "reviewer": reviewer or None,
            "human_review_status": "approved" if approved and reviewer.strip() else "pending",
            "reviewed_at": utc_now() if approved and reviewer.strip() else None,
            "blockers": blockers,
        }
        redaction = dict(redaction_body)
        redaction["redaction_id"] = stable_id("failure-redaction", redaction_body)
        self.redactions.append(redaction)
        if blockers:
            return {"status": "blocked", **redaction}

        shared_object = self.shared_objects.put_bytes(derived_content)
        derivative_body = {
            "schema_version": "1.0.0",
            "consent_id": consent_id,
            "redaction_id": redaction["redaction_id"],
            "source_sha256": source_sha256,
            "derived_object": shared_object,
            "permitted_uses": copy.deepcopy(consent.get("permitted_uses")),
            "promoted_at": utc_now(),
            "projection_ids": [],
        }
        derivative = dict(derivative_body)
        derivative["derivative_id"] = stable_id(
            "failure-shared-derivative",
            {"consent_id": consent_id, "derived_sha256": derived_sha256},
        )
        derivative["projection_ids"] = [derivative["derivative_id"]]
        existing = self.derivatives.latest_by("derivative_id", derivative["derivative_id"])
        if not existing:
            self.derivatives.append(derivative)
        else:
            derivative = existing
        return {"status": "promoted", **derivative}

    def _tombstoned_derivative_ids(self) -> set[str]:
        result = set()
        for tombstone in self.tombstones:
            result.update(str(item) for item in tombstone.get("derivative_ids") or [])
        return result

    def search_shared_text(self, query: str) -> list[Dict[str, Any]]:
        tokens = _tokens(query)
        if not tokens:
            return []
        tombstoned = self._tombstoned_derivative_ids()
        hits = []
        for derivative in _latest_by_key(self.derivatives, "derivative_id").values():
            if derivative["derivative_id"] in tombstoned:
                continue
            text = self.shared_objects.read_bytes(derivative["derived_object"]).decode("utf-8", errors="replace")
            overlap = len(tokens.intersection(_tokens(text)))
            if overlap:
                hits.append(
                    {
                        "derivative_id": derivative["derivative_id"],
                        "derived_sha256": derivative["derived_object"]["sha256"],
                        "score": overlap,
                        "text": text,
                        "redaction_id": derivative["redaction_id"],
                    }
                )
        hits.sort(key=lambda item: (-int(item["score"]), str(item["derivative_id"])))
        return hits

    def withdraw_consent(
        self,
        consent_id: str,
        *,
        projection_purger: Optional[Callable[[list[str]], None]] = None,
    ) -> Dict[str, Any]:
        consent = self._active_consent(consent_id)
        withdrawn_at = utc_now()
        self.consent_events.append(
            {
                "schema_version": "1.0.0",
                "consent_id": consent_id,
                "event_type": "withdrawn",
                "event_at": withdrawn_at,
            }
        )
        active_tombstones = self._tombstoned_derivative_ids()
        affected = [
            item
            for item in _latest_by_key(self.derivatives, "derivative_id").values()
            if item.get("consent_id") == consent_id and item.get("derivative_id") not in active_tombstones
        ]
        derivative_ids = sorted(str(item["derivative_id"]) for item in affected)
        projection_ids = sorted(
            {str(projection_id) for item in affected for projection_id in item.get("projection_ids") or []}
        )
        purge_status = "not_applicable"
        if projection_ids and projection_purger:
            projection_purger(projection_ids)
            purge_status = "purged"
        elif projection_ids:
            purge_status = "purge_required_before_projection_rebuild"
        body = {
            "schema_version": "1.0.0",
            "consent_id": consent_id,
            "derivative_ids": derivative_ids,
            "projection_ids": projection_ids,
            "tombstoned_at": withdrawn_at,
            "purge_status": purge_status,
            "dependent_finding_status": "invalidated",
            "source_deletion_requires_separate_authorization": True,
        }
        tombstone = dict(body)
        tombstone["tombstone_id"] = stable_id("failure-projection-tombstone", body)
        tombstone["status"] = "tombstoned"
        self.tombstones.append(tombstone)
        return tombstone

    def project_approved_public(self, sink: ProjectionSink) -> Dict[str, Any]:
        projected = []
        for raw in self._current_public_records():
            record, status = self._effective_public_record(raw)
            if status not in {"approved", "corrected"}:
                continue
            projection_id = sink.upsert_public(record)
            event = {
                "schema_version": "1.0.0",
                "record_id": record["record_id"],
                "projection_id": projection_id,
                "projection_role": "discovery_only",
                "projected_at": utc_now(),
            }
            self.projection_events.append(event)
            projected.append(event)
        return {"projected": projected, "source_of_truth": "append_only_public_records"}

    def coverage_report(self) -> Dict[str, Any]:
        records = self._current_public_records()
        reviews = self.review_queue()["items"] if records else []
        reasons = [reason for record in records for reason in record.get("refusal_reasons") or []]
        norms = [
            {"norm_id": norm_id}
            for record in records
            for norm_id in (record.get("challenged_norm_signature") or {}).get("norm_ids") or []
        ]
        failures = self.access_failures.records()
        private_count = len(_latest_by_key(self.private_records, "private_record_id"))
        shared_count = len(
            set(_latest_by_key(self.derivatives, "derivative_id")) - self._tombstoned_derivative_ids()
        )
        if failures:
            coverage_state = "partial"
        elif records:
            coverage_state = "observed_not_complete"
        else:
            coverage_state = "unknown"
        return {
            "schema_version": "1.0.0",
            "public_petition_unit_count": len(records),
            "private_matter_local_count": private_count,
            "shared_anonymized_count": shared_count,
            "counts_by_source": count_by(records, "source_evidence_id"),
            "counts_by_date": count_by(records, "act_date"),
            "counts_by_taxonomy": count_by(reasons, "code"),
            "counts_by_norm": count_by(norms, "norm_id"),
            "counts_by_review_status": count_by(reviews, "status"),
            "access_failure_counts": count_by(failures, "status"),
            "coverage_state": coverage_state,
            "complete": False,
            "limits": [
                "corpus_size_is_not_completeness",
                "private_zero_coverage_is_reported_without_synthetic_substitution",
            ],
        }
