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
from .trusted_approvals import TrustedApprovalLedger


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
_KSRF_ISSUER_IDENTITY = "constitutional court of the russian federation"
_DASH_TRANSLATION = str.maketrans({"–": "-", "—": "-", "−": "-", "‑": "-"})
_RUSSIAN_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


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


def _canonical_ksrf_issuer(value: Any) -> Optional[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return _KSRF_ISSUER_IDENTITY
    if normalized == _KSRF_ISSUER_IDENTITY:
        return normalized
    letters = re.sub(r"[^a-zа-я0-9]+", "", normalized)
    aliases = {
        "ксрф",
        "конституционныйсудрф",
        "конституционныйсудроссийскойфедерации",
    }
    return _KSRF_ISSUER_IDENTITY if letters in aliases else None


def _canonical_act_number(value: Any) -> Optional[tuple[str, str, int]]:
    normalized = _normalize_text(value).translate(_DASH_TRANSLATION).replace("ё", "е")
    compact = re.sub(r"\s+", "", normalized).replace("№", "")
    explicit_type: Optional[str] = None
    for prefix, act_type in (("определение", "determination"), ("постановление", "resolution")):
        if compact.startswith(prefix):
            explicit_type = act_type
            compact = compact[len(prefix) :]
            break
    match = re.fullmatch(r"(\d+)-([a-zа-я]+(?:-[a-zа-я]+)*)/(\d{4})", compact)
    if match is None:
        return None
    serial, raw_suffix, year_text = match.groups()
    suffix = raw_suffix.translate(str.maketrans({"o": "о", "p": "п"}))
    first_suffix = suffix.split("-", 1)[0]
    inferred_type = {"о": "determination", "п": "resolution"}.get(first_suffix)
    if inferred_type is None or (explicit_type is not None and explicit_type != inferred_type):
        return None
    year = int(year_text)
    return inferred_type, f"{int(serial)}-{suffix}/{year}", year


def _canonical_act_date(value: Any) -> Optional[str]:
    normalized = _normalize_text(value).translate(_DASH_TRANSLATION).replace(" г.", "").strip()
    for date_format in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(normalized, date_format).date().isoformat()
        except ValueError:
            pass
    words = re.fullmatch(r"(\d{1,2})\s+([а-я]+)\s+(\d{4})", normalized)
    if words is not None and words.group(2) in _RUSSIAN_MONTHS:
        try:
            return datetime(
                int(words.group(3)),
                _RUSSIAN_MONTHS[words.group(2)],
                int(words.group(1)),
            ).date().isoformat()
        except ValueError:
            return None
    return None


def _stable_act_identity(record: Mapping[str, Any]) -> tuple[str, bool]:
    """Return canonical act identity; ambiguous fields remain diagnostic-only."""

    issuer = _canonical_ksrf_issuer(record.get("issuer"))
    act_number = _canonical_act_number(record.get("act_number"))
    act_date = _canonical_act_date(record.get("act_date"))
    if issuer and act_number and act_date and act_number[2] == int(act_date[:4]):
        act_type, canonical_number, act_year = act_number
        return (
            stable_id(
                "ksrf-refusal-act",
                {
                    "issuer": issuer,
                    "act_type": act_type,
                    "act_number": canonical_number,
                    "act_year": act_year,
                    "act_date": act_date,
                },
            ),
            True,
        )
    source_version = str(record.get("source_evidence_id") or record.get("record_id") or "")
    if source_version:
        # This fallback supports diagnostics only. It must never increase the
        # distinct-act or verified-act counters used by the recurrence gate.
        return stable_id("unverified-refusal-act-version", source_version), False
    return "", False


class FailureCorpus:
    def __init__(
        self,
        root: Path,
        *,
        taxonomy_path: Optional[Path] = None,
        approval_ledger: TrustedApprovalLedger | None = None,
    ) -> None:
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
        self.approvals = approval_ledger or TrustedApprovalLedger(
            self.root / "trusted-approvals"
        )
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
        approval_id: str | None = None,
        approval_as_of: str | None = None,
        corrections: Optional[Mapping[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        del approval_as_of
        if decision not in _REVIEW_DECISIONS - {"unreviewed"}:
            raise ValueError(f"invalid review decision: {decision}")
        source = self.public_records.latest_by("record_id", record_id)
        if source is None:
            raise KeyError(f"unknown public refusal record: {record_id}")
        approval_request = self.public_review_approval_request(
            record_id,
            decision=decision,
            corrections=corrections,
        )
        trusted_approval = None
        if decision in {"approved", "corrected"}:
            if not str(approval_id or "").strip():
                raise ValueError("trusted approval_id is required for positive corpus review")
            validation = self.approvals.validate_approval(
                str(approval_id),
                **approval_request,
            )
            if validation.get("valid") is not True:
                raise ValueError(
                    "trusted corpus approval is invalid: "
                    + str(validation.get("reason_code") or "approval_invalid")
                )
            trusted_approval = validation["approval"]
        body = {
            "schema_version": "1.0.0",
            "record_id": record_id,
            "decision": decision,
            "reviewer": (
                trusted_approval.get("actor_display_name") if trusted_approval else None
            ),
            "reviewed_at": (
                trusted_approval.get("approved_at") if trusted_approval else utc_now()
            ),
            "approval_id": (
                trusted_approval.get("approval_id") if trusted_approval else None
            ),
            "approval_request": approval_request,
            "raw_reviewer_diagnostic": str(reviewer or "").strip() or None,
            "reason": reason,
            "corrections": copy.deepcopy(dict(corrections or {})),
        }
        review = dict(body)
        review["review_id"] = stable_id("refusal-review", body)
        self.public_reviews.append(review)
        return review

    def public_review_approval_request(
        self,
        record_id: str,
        *,
        decision: str,
        corrections: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        source = self.public_records.latest_by("record_id", record_id)
        if source is None:
            raise KeyError(f"unknown public refusal record: {record_id}")
        bindings = {
            "record_id": record_id,
            "record_sha256": str((source.get("record_object") or {}).get("sha256") or ""),
            "decision": str(decision),
            "corrections": copy.deepcopy(dict(corrections or {})),
        }
        return {
            "purpose": "issue",
            "subject_type": "public_refusal_review",
            "subject_id": record_id,
            "fingerprint": stable_id("public-refusal-review", bindings),
            "bindings": bindings,
        }

    def _review_for(self, record_id: str) -> Optional[Dict[str, Any]]:
        return self.public_reviews.latest_by("record_id", record_id)

    def review_queue(self) -> Dict[str, Any]:
        items = []
        for record in self._current_public_records():
            _, status = self._effective_public_record(record)
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
        if status in {"approved", "corrected"} and review:
            approval_request = review.get("approval_request") or {}
            validation = (
                self.approvals.validate_approval(
                    str(review.get("approval_id") or ""),
                    **approval_request,
                )
                if isinstance(approval_request, Mapping)
                and {
                    "purpose",
                    "subject_type",
                    "subject_id",
                    "fingerprint",
                    "bindings",
                }.issubset(approval_request)
                else {"valid": False, "reason_code": "trusted_approval_required"}
            )
            if validation.get("valid") is not True:
                status = "unreviewed"
                effective["trusted_review_reason_code"] = validation.get("reason_code")
        if status == "corrected" and review:
            effective.update(copy.deepcopy(dict(review.get("corrections") or {})))
        effective["review_status"] = status
        return effective, status

    def recurring_defects(
        self,
        query: Optional[Mapping[str, Any]] = None,
        *,
        min_distinct_acts: int = 2,
    ) -> Dict[str, Any]:
        """Detect repeated refusal-taxonomy defects without promoting unreviewed extraction.

        Repetition is counted across distinct official source acts, not petition units. A
        cluster becomes gate-eligible only when the threshold is independently met by
        records approved or corrected by a named reviewer.
        """

        if min_distinct_acts < 2:
            raise ValueError("recurring defect threshold must be at least two distinct acts")
        query_norms = {str(item) for item in (query or {}).get("norm_ids") or []}
        groups: Dict[tuple[str, str], Dict[str, Any]] = {}
        for raw_record in self._current_public_records():
            record, review_status = self._effective_public_record(raw_record)
            if review_status in {"rejected", "blocked_for_source"}:
                continue
            record_norms = {
                str(item)
                for item in (record.get("challenged_norm_signature") or {}).get("norm_ids") or []
            }
            if query_norms and not query_norms.intersection(record_norms):
                continue
            act_identity, stable_act_identity = _stable_act_identity(record)
            if not act_identity:
                continue
            for reason in record.get("refusal_reasons") or []:
                code = str(reason.get("code") or "")
                role = str(reason.get("role") or "")
                if not code or role not in {"primary", "ancillary"}:
                    continue
                group = groups.setdefault(
                    (code, role),
                    {
                        "act_ids": set(),
                        "fallback_observation_ids": set(),
                        "verified_act_ids": set(),
                        "act_numbers": set(),
                        "record_ids": set(),
                        "petition_unit_ids": set(),
                        "statements": set(),
                        "repair_deltas": set(),
                        "review_statuses": set(),
                    },
                )
                if stable_act_identity:
                    group["act_ids"].add(act_identity)
                else:
                    group["fallback_observation_ids"].add(act_identity)
                group["act_numbers"].add(str(record.get("act_number") or act_identity))
                group["record_ids"].add(str(record.get("record_id")))
                group["petition_unit_ids"].add(str(record.get("petition_unit_id")))
                group["statements"].add(str(reason.get("statement") or ""))
                group["review_statuses"].add(review_status)
                repair_delta = _normalize_text(record.get("repair_delta"))
                if repair_delta:
                    group["repair_deltas"].add(repair_delta)
                if stable_act_identity and review_status in {"approved", "corrected"}:
                    group["verified_act_ids"].add(act_identity)

        clusters: list[Dict[str, Any]] = []
        for (code, role), group in groups.items():
            distinct_act_count = len(group["act_ids"])
            if distinct_act_count < min_distinct_acts:
                continue
            verified_count = len(group["verified_act_ids"])
            eligible = verified_count >= min_distinct_acts
            evidence_state = (
                "verified_recurring_defect" if eligible else "candidate_requires_review"
            )
            clusters.append(
                {
                    "cluster_id": stable_id(
                        "recurring-refusal-defect",
                        {
                            "taxonomy_code": code,
                            "role": role,
                            "act_ids": sorted(group["act_ids"]),
                        },
                    ),
                    "taxonomy_code": code,
                    "role": role,
                    "distinct_act_count": distinct_act_count,
                    "verified_distinct_act_count": verified_count,
                    "unverified_identity_observation_count": len(group["fallback_observation_ids"]),
                    "petition_unit_count": len(group["petition_unit_ids"]),
                    "act_numbers": sorted(group["act_numbers"]),
                    "record_ids": sorted(group["record_ids"]),
                    "statements": sorted(item for item in group["statements"] if item),
                    "repair_deltas": sorted(group["repair_deltas"]),
                    "review_statuses": sorted(group["review_statuses"]),
                    "evidence_state": evidence_state,
                    "eligible_for_adverse_gate": eligible,
                    "required_response_task": (
                        f"Устранить повторяющийся дефект {code} и отдельно показать это в жалобе; "
                        "сверить предложенные исправления с каждым подтвержденным отказным актом."
                    ),
                }
            )
        clusters.sort(
            key=lambda item: (
                not bool(item["eligible_for_adverse_gate"]),
                -int(item["verified_distinct_act_count"]),
                -int(item["distinct_act_count"]),
                item["role"] != "primary",
                str(item["taxonomy_code"]),
            )
        )
        coverage = self.coverage_report()
        if any(item["eligible_for_adverse_gate"] for item in clusters):
            conclusion = "verified recurring defects found"
        elif clusters:
            conclusion = "candidate recurring defects require review"
        else:
            conclusion = "no recurring defect found in searched coverage"
        return {
            "clusters": clusters,
            "coverage_state": coverage["coverage_state"],
            "min_distinct_acts": min_distinct_acts,
            "conclusion": conclusion,
            "limits": [
                "recurrence_is_bounded_to_searched_coverage",
                "petition_units_from_one_act_do_not_establish_recurrence",
                "source_versions_and_fallback_identities_do_not_increase_act_counts",
                "unreviewed_clusters_are_discovery_only",
            ],
        }

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
        recurring = self.recurring_defects(query)
        return {
            "hits": hits,
            "recurring_defects": recurring["clusters"],
            "recurring_defects_conclusion": recurring["conclusion"],
            "coverage_state": coverage["coverage_state"],
            "conclusion": conclusion,
            "limits": [
                "lexical_or_vector_similarity_is_discovery_only",
                "no_result_is_bounded_to_searched_coverage",
                "unreviewed_recurring_defects_are_discovery_only",
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
        approval_id: str | None = None,
        approval_as_of: str | None = None,
    ) -> Dict[str, Any]:
        del approval_as_of
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
        derived_sha256 = sha256_bytes(derived_content)
        approval_request = self.redaction_approval_request(
            private_record_id=private_record_id,
            consent_id=consent_id,
            source_sha256=source_sha256,
            derived_sha256=derived_sha256,
            unresolved_spans=unresolved_spans,
        )
        trusted_approval = None
        if not str(approval_id or "").strip():
            blockers.append("trusted_redaction_approval_required")
        else:
            validation = self.approvals.validate_approval(
                str(approval_id),
                **approval_request,
            )
            if validation.get("valid") is True:
                trusted_approval = validation["approval"]
            else:
                blockers.append(
                    "trusted_redaction_"
                    + str(validation.get("reason_code") or "approval_invalid")
                )
        redaction_body = {
            "schema_version": "1.0.0",
            "private_record_id": private_record_id,
            "consent_id": consent_id,
            "source_sha256": source_sha256,
            "derived_sha256": derived_sha256,
            "automated_check_status": "blocked" if unresolved_spans else "passed",
            "unresolved_spans": list(unresolved_spans),
            "reviewer": (
                trusted_approval.get("actor_display_name") if trusted_approval else None
            ),
            "human_review_status": "approved" if trusted_approval else "pending",
            "reviewed_at": trusted_approval.get("approved_at") if trusted_approval else None,
            "approval_id": trusted_approval.get("approval_id") if trusted_approval else None,
            "approval_request": approval_request,
            "raw_reviewer_diagnostic": str(reviewer or "").strip() or None,
            "raw_approved_diagnostic": approved is True,
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
            "approval_id": trusted_approval["approval_id"],
            "approval_request": approval_request,
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

    def redaction_approval_request(
        self,
        *,
        private_record_id: str,
        consent_id: str,
        source_sha256: str,
        derived_sha256: str,
        unresolved_spans: Sequence[str],
    ) -> Dict[str, Any]:
        bindings = {
            "private_record_id": private_record_id,
            "consent_id": consent_id,
            "source_sha256": source_sha256,
            "derived_sha256": derived_sha256,
            "unresolved_spans": list(unresolved_spans),
        }
        return {
            "purpose": "issue",
            "subject_type": "private_redacted_derivative",
            "subject_id": private_record_id,
            "fingerprint": stable_id("private-redaction-review", bindings),
            "bindings": bindings,
        }

    def _tombstoned_derivative_ids(self) -> set[str]:
        result = set()
        for tombstone in self.tombstones:
            result.update(str(item) for item in tombstone.get("derivative_ids") or [])
        return result

    def _withdrawn_consent_ids(self) -> set[str]:
        latest = _latest_by_key(self.consent_events, "consent_id")
        return {
            consent_id
            for consent_id, event in latest.items()
            if event.get("event_type") == "withdrawn"
        }

    def search_shared_text(self, query: str) -> list[Dict[str, Any]]:
        tokens = _tokens(query)
        if not tokens:
            return []
        tombstoned = self._tombstoned_derivative_ids()
        withdrawn_consents = self._withdrawn_consent_ids()
        hits = []
        for derivative in _latest_by_key(self.derivatives, "derivative_id").values():
            if (
                derivative["derivative_id"] in tombstoned
                or derivative.get("consent_id") in withdrawn_consents
            ):
                continue
            if not self._shared_derivative_approval_valid(derivative):
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

    def _shared_derivative_approval_valid(
        self, derivative: Mapping[str, Any]
    ) -> bool:
        approval_request = derivative.get("approval_request") or {}
        if not isinstance(approval_request, Mapping) or not {
            "purpose",
            "subject_type",
            "subject_id",
            "fingerprint",
            "bindings",
        }.issubset(approval_request):
            return False
        validation = self.approvals.validate_approval(
            str(derivative.get("approval_id") or ""),
            **approval_request,
        )
        return validation.get("valid") is True

    def withdraw_consent(
        self,
        consent_id: str,
        *,
        projection_purger: Optional[Callable[[list[str]], None]] = None,
    ) -> Dict[str, Any]:
        consent = self.consents.latest_by("consent_id", consent_id)
        if consent is None:
            raise KeyError(f"unknown consent: {consent_id}")
        already_withdrawn = consent_id in self._withdrawn_consent_ids()
        if not already_withdrawn:
            self._active_consent(consent_id)
        prior_tombstones = [
            item for item in self.tombstones if item.get("consent_id") == consent_id
        ]
        if already_withdrawn and prior_tombstones and prior_tombstones[-1].get("purge_status") == "purged":
            return prior_tombstones[-1]
        withdrawn_at = utc_now()
        if not already_withdrawn:
            self.consent_events.append(
                {
                    "schema_version": "1.0.0",
                    "consent_id": consent_id,
                    "event_type": "withdrawn",
                    "event_at": withdrawn_at,
                }
            )
        affected = [
            item
            for item in _latest_by_key(self.derivatives, "derivative_id").values()
            if item.get("consent_id") == consent_id
        ]
        derivative_ids = sorted(str(item["derivative_id"]) for item in affected)
        projection_ids = sorted(
            {str(projection_id) for item in affected for projection_id in item.get("projection_ids") or []}
        )
        def append_tombstone(purge_status: str) -> Dict[str, Any]:
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

        if not projection_ids:
            return append_tombstone("not_applicable")

        pending = append_tombstone("purge_required_before_projection_rebuild")
        if projection_purger is None:
            return pending
        # Local retrieval is already denied by the withdrawal event and the
        # tombstone. If the external purge fails, the pending record remains and
        # this method can safely be retried with the same consent id.
        projection_purger(projection_ids)
        return append_tombstone("purged")

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
        latest_derivatives = _latest_by_key(self.derivatives, "derivative_id")
        tombstoned_derivatives = self._tombstoned_derivative_ids()
        withdrawn_consents = self._withdrawn_consent_ids()
        shared_count = sum(
            1
            for derivative_id, derivative in latest_derivatives.items()
            if derivative_id not in tombstoned_derivatives
            and derivative.get("consent_id") not in withdrawn_consents
            and self._shared_derivative_approval_valid(derivative)
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
