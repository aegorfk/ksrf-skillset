#!/usr/bin/env python3
"""Deterministic discovery helper for the ksrf-doctrine-research skill.

The tool plans redacted searches, queries explicitly enabled scholarly APIs,
normalizes and deduplicates metadata, and writes fail-closed coverage artifacts.
It does not establish current law, a doctrinal proposition, or a constitutional
defect.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


SKILL_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = SKILL_ROOT / "references" / "provider-registry.json"
TAXONOMY_PATH = SKILL_ROOT / "references" / "problem-taxonomy.json"
USER_AGENT = "ksrf-doctrine-research/0.1"
ALLOWED_MODES = {"exploratory_norm", "case_scoped", "hypothesis_verification"}
PII_PATTERNS = (
    re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
    re.compile(r"(?<!\d)(?:\+7|8)[\s()\-]*\d{3}[\s()\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)"),
    re.compile(r"(?<!\d)\d{3}-\d{3}-\d{3}[ -]\d{2}(?!\d)"),
    re.compile(r"(?<!\d)\d{2}\s?\d{2}\s?\d{6}(?!\d)"),
    re.compile(r"(?<!\w)\d{2}[A-ZА-Я]{2}\d{4}-\d{2}-\d{4}-\d{6}-\d{2}(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\d)\d{10}(?!\d)"),
    re.compile(r"(?<!\d)\d{12}(?!\d)"),
    re.compile(r"(?<!\d)(?:\d{13}|\d{15})(?!\d)"),
    re.compile(r"(?<!\d)\d{1,2}-\d{1,8}/\d{4}(?!\d)"),
    re.compile(r"\b(?:ФИО|адрес|дата\s+рождения|ИНН|ОГРН|СНИЛС|УИД|номер\s+дела)\s*[:№]", re.IGNORECASE),
    re.compile(r"\b[А-ЯЁ][а-яё]{2,}\s+[А-ЯЁ][а-яё]{2,}\s+[А-ЯЁ][а-яё]{2,}\b"),
)
TOPIC_STOP_PREFIXES = (
    "стат",
    "кодекс",
    "россий",
    "федерац",
    "прав",
    "проблем",
    "примен",
    "толкован",
    "поряд",
    "установ",
    "отсут",
    "друг",
    "связ",
    "вмест",
    "част",
)


class DoctrineResearchError(RuntimeError):
    """Controlled user-facing error."""


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def pretty_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json(path: Path, value: Any) -> None:
    atomic_write_bytes(path, pretty_bytes(value))


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    payload = b"".join(canonical_bytes(dict(row)) for row in rows)
    atomic_write_bytes(path, payload)


def stable_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(str(part).encode("utf-8"))
        digest.update(b"\0")
    return f"{prefix}{digest.hexdigest()[:16]}"


def unique_strings(values: Optional[Iterable[Any]]) -> List[str]:
    result: List[str] = []
    seen = set()
    if values is None:
        return result
    if isinstance(values, (str, bytes)):
        values = [values]
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_iso_date(value: Any) -> Optional[date]:
    text = normalize_space(value)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def has_meaningful_content(value: Any) -> bool:
    if isinstance(value, str):
        return bool(normalize_space(value))
    if isinstance(value, Mapping):
        return any(has_meaningful_content(part) for part in value.values())
    if isinstance(value, list):
        return any(has_meaningful_content(part) for part in value)
    return False


def has_meaningful_items(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    return any(has_meaningful_content(item) for item in value)


def validate_text_list(field: str, value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return [f"{field} must be a list"]
    return [
        f"{field}[{index}] must be a non-empty string"
        for index, item in enumerate(value)
        if not isinstance(item, str) or not normalize_space(item)
    ]


def validate_phrase_list(field: str, value: Any, mapping_keys: Sequence[str]) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return [f"{field} must be a list"]
    errors: List[str] = []
    allowed = set(mapping_keys)
    for index, item in enumerate(value):
        if isinstance(item, str):
            if not normalize_space(item):
                errors.append(f"{field}[{index}] must not be blank")
            continue
        if not isinstance(item, Mapping):
            errors.append(f"{field}[{index}] must be a string or an object")
            continue
        unknown = sorted(set(item) - allowed)
        if unknown:
            errors.append(f"{field}[{index}] contains unsupported keys: {', '.join(unknown)}")
        invalid_values = [
            key
            for key in mapping_keys
            if item.get(key) is not None and not isinstance(item.get(key), str)
        ]
        if invalid_values:
            errors.append(f"{field}[{index}] phrase values must be strings: {', '.join(invalid_values)}")
        if not any(isinstance(item.get(key), str) and normalize_space(item.get(key)) for key in mapping_keys):
            errors.append(f"{field}[{index}] must contain a non-empty public phrase")
    return errors


REFERENCE_KEYS = {
    "ref",
    "source_id",
    "document_id",
    "evidence_id",
    "path",
    "url",
    "locator",
    "page",
    "paragraph",
    "sha256",
}


def validate_reference_list(field: str, value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return [f"{field} must be a list"]
    errors: List[str] = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            if not normalize_space(item):
                errors.append(f"{field}[{index}] must not be blank")
            continue
        if not isinstance(item, Mapping):
            errors.append(f"{field}[{index}] must be a string or an object")
            continue
        unknown = sorted(set(item) - REFERENCE_KEYS)
        if unknown:
            errors.append(f"{field}[{index}] contains unsupported keys: {', '.join(unknown)}")
        if not has_meaningful_content(item):
            errors.append(f"{field}[{index}] must contain a non-empty reference")
    return errors


def normalize_title(value: Any) -> str:
    text = normalize_space(value).casefold().replace("ё", "е")
    return re.sub(r"[^0-9a-zа-я]+", " ", text).strip()


def lexical_stems(values: Iterable[Any]) -> set[str]:
    stems: set[str] = set()
    for value in values:
        for token in re.findall(r"[a-zа-яё]{5,}", normalize_space(value).casefold().replace("ё", "е")):
            if token.startswith(TOPIC_STOP_PREFIXES):
                continue
            stems.add(token[:7])
    return stems


def normalize_doi(value: Any) -> Optional[str]:
    text = normalize_space(value).casefold()
    if not text:
        return None
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text)
    text = re.sub(r"^doi:\s*", "", text)
    return text.rstrip(".,; ") or None


def strip_html(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_space(text)


def first_nonempty(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def validate_request(request: Mapping[str, Any], *, for_external_search: bool = False) -> List[str]:
    errors: List[str] = []
    if str(request.get("schema_version")) != "1.0":
        errors.append("schema_version must be 1.0")
    if not normalize_space(request.get("matter_id")):
        errors.append("matter_id is required")
    mode = request.get("mode")
    if mode not in ALLOWED_MODES:
        errors.append(f"mode must be one of {sorted(ALLOWED_MODES)}")
    as_of = parse_iso_date(request.get("as_of_date"))
    if as_of is None:
        errors.append("as_of_date must be a valid YYYY-MM-DD calendar date")
    norms = request.get("norms")
    if not isinstance(norms, list) or not norms:
        errors.append("norms must contain at least one public norm descriptor")
    else:
        for index, norm in enumerate(norms):
            if not isinstance(norm, Mapping):
                errors.append(f"norms[{index}] must be an object")
                continue
            if not isinstance(norm.get("citation"), str) or not normalize_space(norm.get("citation")):
                errors.append(f"norms[{index}].citation is required")
            variants = norm.get("citation_variants")
            if variants is not None:
                errors.extend(validate_text_list(f"norms[{index}].citation_variants", variants))
            title = norm.get("title")
            if title is not None and (not isinstance(title, str) or not normalize_space(title)):
                errors.append(f"norms[{index}].title must be a non-empty string when provided")
            excerpt = norm.get("public_text_excerpt")
            if excerpt is not None and not isinstance(excerpt, str):
                errors.append(f"norms[{index}].public_text_excerpt must be a string when provided")
    for field in (
        "disputed_elements",
        "mechanisms",
        "consequences",
        "adjacent_norms",
        "subject_terms",
        "material_types",
    ):
        errors.extend(validate_text_list(field, request.get(field)))
    errors.extend(
        validate_phrase_list(
            "judicial_meanings",
            request.get("judicial_meanings"),
            ("public_excerpt", "meaning", "phrase"),
        )
    )
    errors.extend(validate_reference_list("application_evidence_refs", request.get("application_evidence_refs")))
    errors.extend(validate_reference_list("fulltext_source_refs", request.get("fulltext_source_refs")))
    languages = request.get("languages")
    errors.extend(validate_text_list("languages", languages))
    if isinstance(languages, list):
        for index, language in enumerate(languages):
            if isinstance(language, str) and normalize_space(language) and not re.fullmatch(
                r"(?:[a-z]{2,3}(?:-[a-z0-9]{2,8})?|any)", language.casefold()
            ):
                errors.append(f"languages[{index}] must be a language tag or any")
    date_range = request.get("date_range", {})
    if not isinstance(date_range, Mapping):
        errors.append("date_range must be an object")
    else:
        start, end = date_range.get("from"), date_range.get("to")
        if start is not None and (not isinstance(start, int) or start < 1800):
            errors.append("date_range.from must be a plausible year")
        if end is not None and (not isinstance(end, int) or end < 1800):
            errors.append("date_range.to must be a plausible year")
        if isinstance(end, int) and as_of is not None and end > as_of.year:
            errors.append("date_range.to must not exceed as_of_date year")
        if isinstance(start, int) and isinstance(end, int) and start > end:
            errors.append("date_range.from must not exceed date_range.to")
    privacy = request.get("privacy", {})
    if not isinstance(privacy, Mapping):
        errors.append("privacy must be an object")
    elif for_external_search:
        if privacy.get("external_queries_redacted") is not True:
            errors.append("privacy.external_queries_redacted must be true before external search")
        if privacy.get("class") not in {"public_abstracted", "public_norm_profile"}:
            errors.append("privacy.class must be public_abstracted or public_norm_profile for external search")
    if mode == "case_scoped":
        if not has_meaningful_items(request.get("judicial_meanings")):
            errors.append("case_scoped mode requires at least one non-empty judicial_meaning")
        if not has_meaningful_items(request.get("mechanisms")):
            errors.append("case_scoped mode requires at least one non-empty mechanism")
        if not has_meaningful_items(request.get("consequences")):
            errors.append("case_scoped mode requires at least one non-empty consequence")
        if not has_meaningful_items(request.get("application_evidence_refs")):
            errors.append("case_scoped mode requires at least one non-empty application_evidence_ref")
        for index, norm in enumerate(norms or []):
            version_date = parse_iso_date(norm.get("version_date")) if isinstance(norm, Mapping) else None
            if version_date is None:
                errors.append(f"case_scoped mode requires norms[{index}].version_date as a valid YYYY-MM-DD date")
            elif as_of is not None and version_date > as_of:
                errors.append(f"norms[{index}].version_date must not exceed as_of_date")
    if mode == "hypothesis_verification":
        errors.extend(
            validate_phrase_list(
                "hypotheses_under_test",
                request.get("hypotheses_under_test"),
                ("hypothesis", "statement", "text", "claim"),
            )
        )
        if not has_meaningful_items(request.get("hypotheses_under_test")):
            errors.append("hypothesis_verification mode requires at least one non-empty hypotheses_under_test item")
        if not has_meaningful_items(request.get("fulltext_source_refs")):
            errors.append("hypothesis_verification mode requires at least one non-empty fulltext_source_refs item")
        if request.get("adverse_search_required") is not True:
            errors.append("hypothesis_verification mode requires adverse_search_required=true")
    return errors


def load_request(path: Path, *, for_external_search: bool = False) -> Dict[str, Any]:
    request = load_json(path)
    if not isinstance(request, dict):
        raise DoctrineResearchError("request must be a JSON object")
    errors = validate_request(request, for_external_search=for_external_search)
    if errors:
        raise DoctrineResearchError("invalid request: " + "; ".join(errors))
    return request


def extract_judicial_phrases(request: Mapping[str, Any]) -> List[str]:
    phrases: List[str] = []
    for item in request.get("judicial_meanings", []) or []:
        if isinstance(item, str):
            phrases.append(item)
        elif isinstance(item, Mapping):
            value = first_nonempty(item, ("public_excerpt", "meaning", "phrase"))
            if value:
                phrases.append(str(value))
    return unique_strings(phrases)


def extract_hypothesis_phrases(request: Mapping[str, Any]) -> List[str]:
    phrases: List[str] = []
    for item in request.get("hypotheses_under_test", []) or []:
        if isinstance(item, str):
            phrases.append(item)
        elif isinstance(item, Mapping):
            value = first_nonempty(item, ("hypothesis", "statement", "text", "claim"))
            if value:
                phrases.append(str(value))
    return unique_strings(phrases)


def norm_anchors(request: Mapping[str, Any]) -> List[Tuple[str, str]]:
    anchors: List[Tuple[str, str]] = []
    for index, norm in enumerate(request.get("norms", [])):
        citations = unique_strings([norm.get("citation"), *(norm.get("citation_variants", []) or [])])
        for position, citation in enumerate(citations):
            anchors.append((citation, f"norms[{index}].citation_variants[{position}]"))
        title = normalize_space(norm.get("title"))
        if title:
            anchors.append((title, f"norms[{index}].title"))
    return anchors


def build_problem_profile(request: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": "norm-problem-profile/1.0",
        "matter_id": request["matter_id"],
        "mode": request["mode"],
        "as_of_date": request["as_of_date"],
        "jurisdiction": request.get("jurisdiction", "RU"),
        "languages": unique_strings(request.get("languages", ["ru"])),
        "norms": request.get("norms", []),
        "judicial_phrases": extract_judicial_phrases(request),
        "disputed_elements": unique_strings(request.get("disputed_elements", [])),
        "mechanisms": unique_strings(request.get("mechanisms", [])),
        "consequences": unique_strings(request.get("consequences", [])),
        "adjacent_norms": unique_strings(request.get("adjacent_norms", [])),
        "subject_terms": unique_strings(request.get("subject_terms", [])),
        "constitutional_conclusion_preseeded": False,
        "case_scope_limit": "not_case_scoped" if request["mode"] == "exploratory_norm" else "application_evidence_external",
    }


def request_sha256(request: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(request)).hexdigest()


def ensure_workspace_identity(request: Mapping[str, Any], workspace: Path) -> None:
    snapshot = workspace / "request.snapshot.json"
    if not snapshot.exists():
        return
    existing = load_json(snapshot)
    if not isinstance(existing, Mapping) or request_sha256(existing) != request_sha256(request):
        raise DoctrineResearchError(
            "WORKSPACE_IDENTITY_MISMATCH: use a new workspace for a different request"
        )


def build_query_plan(request: Mapping[str, Any]) -> Dict[str, Any]:
    anchors = norm_anchors(request)
    if not anchors:
        raise DoctrineResearchError("no searchable norm anchors")
    primary_anchor = anchors[0][0]
    queries: List[Dict[str, Any]] = []
    seen = set()

    def add(lane: str, text: str, origin: str, polarity: str = "neutral") -> None:
        cleaned = normalize_space(text)
        key = (lane, cleaned.casefold(), origin, polarity)
        if not cleaned or key in seen:
            return
        seen.add(key)
        intent_id = stable_id("intent-", lane, origin, cleaned)
        queries.append(
            {
                "query_id": stable_id("query-", intent_id, cleaned),
                "query_intent_id": intent_id,
                "lane": lane,
                "text": cleaned,
                "origin": origin,
                "polarity": polarity,
                "status": "planned",
            }
        )

    for text, origin in anchors:
        lane = "norm_title" if origin.endswith(".title") else "exact_norm"
        add(lane, f'"{text}"', origin)

    for index, phrase in enumerate(extract_judicial_phrases(request)):
        add("decisive_phrase", f'"{phrase}" право', f"judicial_meanings[{index}]")
    for index, element in enumerate(unique_strings(request.get("disputed_elements", []))):
        add("element_meaning", f'"{primary_anchor}" "{element}"', f"disputed_elements[{index}]")
        add("problem_probe", f'"{primary_anchor}" "{element}" проблемы применения толкование', f"disputed_elements[{index}]")
        add("adverse", f'"{primary_anchor}" "{element}" обоснование допустимость альтернативное толкование', f"disputed_elements[{index}]", "adverse")
    for index, mechanism in enumerate(unique_strings(request.get("mechanisms", []))):
        add("mechanism_consequence", f'"{primary_anchor}" "{mechanism}"', f"mechanisms[{index}]")
    for index, consequence in enumerate(unique_strings(request.get("consequences", []))):
        add("mechanism_consequence", f'"{primary_anchor}" "{consequence}"', f"consequences[{index}]")
    for index, adjacent in enumerate(unique_strings(request.get("adjacent_norms", []))):
        add("system_link", f'"{primary_anchor}" "{adjacent}"', f"adjacent_norms[{index}]")
    for index, term in enumerate(unique_strings(request.get("subject_terms", []))):
        add("subject_problem", f'"{term}" право проблемы применения', f"subject_terms[{index}]")

    if request.get("mode") == "hypothesis_verification":
        add(
            "adverse",
            f'"{primary_anchor}" критика опровержение пределы альтернативное толкование',
            "generated:hypothesis-adverse",
            "adverse",
        )
        for index, hypothesis in enumerate(extract_hypothesis_phrases(request)):
            add(
                "adverse",
                f'"{primary_anchor}" "{hypothesis}" критика опровержение альтернативное толкование',
                f"hypotheses_under_test[{index}]",
                "adverse",
            )

    add("problem_probe", f'"{primary_anchor}" проблемы применения спорные вопросы', "generated:generic-problem-probe")
    add("procedure_evidence", f'"{primary_anchor}" процедура доказательства защита', "generated:procedure-evidence")
    add("remedy", f'"{primary_anchor}" способ защиты восстановление права', "generated:remedy")
    add("history_update", f'"{primary_anchor}" изменение редакции история правового регулирования', "generated:history-update")

    canonical_for_hash = [{key: row[key] for key in ("query_id", "query_intent_id", "lane", "text", "origin", "polarity")} for row in queries]
    return {
        "schema_version": "doctrine-query-plan/1.0",
        "matter_id": request["matter_id"],
        "as_of_date": request["as_of_date"],
        "query_count": len(queries),
        "queries": queries,
        "query_plan_hash": hashlib.sha256(canonical_bytes(canonical_for_hash)).hexdigest(),
        "legal_conclusions": [],
    }


def select_bounded_queries(query_plan: Mapping[str, Any], limit: int) -> List[Dict[str, Any]]:
    """Select a lane-balanced prefix instead of exhausting the first query family."""
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    lane_order: List[str] = []
    for query in query_plan.get("queries", []):
        lane = str(query.get("lane") or "unknown")
        if lane not in buckets:
            buckets[lane] = []
            lane_order.append(lane)
        buckets[lane].append(dict(query))
    selected: List[Dict[str, Any]] = []
    position = 0
    while len(selected) < limit:
        added = False
        for lane in lane_order:
            if position < len(buckets[lane]):
                selected.append(buckets[lane][position])
                added = True
                if len(selected) == limit:
                    break
        if not added:
            break
        position += 1
    return selected


def provider_routing(
    request: Mapping[str, Any],
    registry: Mapping[str, Any],
    selected_providers: Sequence[str],
) -> Dict[str, Any]:
    access_overrides = request.get("provider_access", {}) or {}
    decisions: List[Dict[str, Any]] = []
    providers = registry.get("providers", {})
    for provider_id in sorted(providers):
        capability = providers[provider_id]
        override = access_overrides.get(provider_id, {}) if isinstance(access_overrides, Mapping) else {}
        status = override.get("status", capability.get("default_status", "not_configured")) if isinstance(override, Mapping) else capability.get("default_status", "not_configured")
        if provider_id == "openalex" and status != "disabled":
            status = "ready_api" if normalize_space(os.getenv("OPENALEX_API_KEY")) else "auth_required"
        adapter = capability.get("adapter")
        selected = provider_id in selected_providers
        decisions.append(
            {
                "provider": provider_id,
                "label": capability.get("label", provider_id),
                "roles": capability.get("roles", []),
                "interface": capability.get("interface"),
                "adapter": adapter,
                "access_status": status,
                "selected_for_automated_run": selected,
                "automated_run_eligible": bool(selected and adapter and status in {"ready_api", "available", "enabled"}),
                "manual_task_required": capability.get("automation", "").startswith("manual"),
                "official_docs": capability.get("official_docs", []),
                "reason": (
                    "selected documented adapter"
                    if selected and adapter
                    else "manual or future provider route"
                    if capability.get("automation") != "supported"
                    else "not selected for this bounded run"
                ),
            }
        )
    unknown = sorted(set(selected_providers) - set(providers))
    if unknown:
        raise DoctrineResearchError(f"unknown providers: {', '.join(unknown)}")
    return {
        "schema_version": "provider-routing/1.0",
        "matter_id": request["matter_id"],
        "registry_last_verified_at": registry.get("last_verified_at"),
        "decisions": decisions,
    }


def redaction_violations(query_plan: Mapping[str, Any], request: Mapping[str, Any]) -> List[Dict[str, str]]:
    violations: List[Dict[str, str]] = []
    prohibited = unique_strings((request.get("privacy") or {}).get("prohibited_external_terms", []))
    for query in query_plan.get("queries", []):
        text = query.get("text", "")
        folded = text.casefold()
        for term in prohibited:
            if term.casefold() in folded:
                violations.append({"query_id": query["query_id"], "reason": "prohibited_external_term"})
        for pattern in PII_PATTERNS:
            if pattern.search(text):
                violations.append({"query_id": query["query_id"], "reason": "pii_like_pattern"})
    return violations


def generated_at(request: Mapping[str, Any]) -> str:
    return f"{request['as_of_date']}T00:00:00Z"


def prepare_workspace(
    request: Mapping[str, Any],
    workspace: Path,
    selected_providers: Sequence[str],
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    ensure_workspace_identity(request, workspace)
    registry = load_json(REGISTRY_PATH)
    taxonomy = load_json(TAXONOMY_PATH)
    profile = build_problem_profile(request)
    query_plan = build_query_plan(request)
    routing = provider_routing(request, registry, selected_providers)
    snapshot_hash = request_sha256(request)
    profile["request_sha256"] = snapshot_hash
    query_plan["request_sha256"] = snapshot_hash
    routing["request_sha256"] = snapshot_hash
    workspace.mkdir(parents=True, exist_ok=True)
    write_json(workspace / "request.snapshot.json", request)
    write_json(workspace / "norm-problem-profile.json", profile)
    write_json(workspace / "provider-capabilities.snapshot.json", registry)
    write_json(workspace / "provider-routing.json", routing)
    write_json(workspace / "query-plan.json", query_plan)
    return registry, taxonomy, query_plan, routing


def http_json(url: str, *, timeout: float, contact_email: Optional[str]) -> Tuple[Any, Dict[str, Any]]:
    user_agent = USER_AGENT if not contact_email else f"{USER_AGENT} (mailto:{contact_email})"
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": user_agent})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=verified_ssl_context()) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload, {
                "http_status": getattr(response, "status", 200),
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "url": public_request_url(url),
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(512).decode("utf-8", errors="replace")
        raise DoctrineResearchError(f"HTTP {exc.code}: {body}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise DoctrineResearchError(f"network or response error: {exc}") from exc


def verified_ssl_context() -> ssl.SSLContext:
    """Build a verifying TLS context, including the common macOS Python fallback."""
    defaults = ssl.get_default_verify_paths()
    candidates = unique_strings(
        [
            os.getenv("SSL_CERT_FILE"),
            defaults.cafile,
            "/etc/ssl/cert.pem",
            "/etc/pki/tls/certs/ca-bundle.crt",
        ]
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ssl.create_default_context(cafile=candidate)
    return ssl.create_default_context()


def public_request_url(url: str) -> str:
    """Return a reproducible request URL without credentials or contact data."""
    parsed = urllib.parse.urlsplit(url)
    safe_pairs = []
    for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        safe_pairs.append((key, "[redacted]" if key.casefold() in {"api_key", "mailto"} else value))
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(safe_pairs), parsed.fragment)
    )


def abstract_from_inverted(index: Any) -> str:
    if not isinstance(index, Mapping):
        return ""
    positions: List[Tuple[int, str]] = []
    for word, word_positions in index.items():
        if not isinstance(word_positions, list):
            continue
        for position in word_positions:
            if isinstance(position, int):
                positions.append((position, str(word)))
    return " ".join(word for _, word in sorted(positions))


def normalize_openalex(payload: Mapping[str, Any], query: Mapping[str, Any]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for item in payload.get("results", []) or []:
        if not isinstance(item, Mapping):
            continue
        primary = item.get("primary_location") or {}
        best_oa = item.get("best_oa_location") or {}
        source = primary.get("source") or {} if isinstance(primary, Mapping) else {}
        authors = []
        for authorship in item.get("authorships", []) or []:
            author = authorship.get("author", {}) if isinstance(authorship, Mapping) else {}
            name = normalize_space(author.get("display_name")) if isinstance(author, Mapping) else ""
            if name:
                authors.append(name)
        abstract = abstract_from_inverted(item.get("abstract_inverted_index"))
        landing = first_nonempty(best_oa if isinstance(best_oa, Mapping) else {}, ("landing_page_url",)) or first_nonempty(primary if isinstance(primary, Mapping) else {}, ("landing_page_url",)) or item.get("id")
        pdf_url = first_nonempty(best_oa if isinstance(best_oa, Mapping) else {}, ("pdf_url",))
        records.append(
            {
                "provider": "openalex",
                "provider_record_id": item.get("id"),
                "query_ids": [query["query_id"]],
                "query_intent_ids": [query["query_intent_id"]],
                "query_lanes": [query["lane"]],
                "query_polarities": [query["polarity"]],
                "title": normalize_space(first_nonempty(item, ("display_name", "title"))),
                "authors": unique_strings(authors),
                "year": item.get("publication_year"),
                "language": item.get("language"),
                "publication_type": item.get("type"),
                "venue": normalize_space(source.get("display_name")) if isinstance(source, Mapping) else "",
                "doi": normalize_doi(item.get("doi")),
                "edn": None,
                "isbn": [],
                "issn": unique_strings(source.get("issn", []) if isinstance(source, Mapping) else []),
                "abstract": abstract,
                "landing_url": landing,
                "fulltext_url": pdf_url,
                "cited_by_count": item.get("cited_by_count"),
                "verification_status": "abstract_checked" if abstract else "metadata_only",
                "access_status": "open_fulltext_candidate" if pdf_url else "metadata_or_landing",
                "license_status": "unknown_requires_item_check",
            }
        )
    return records


def crossref_year(item: Mapping[str, Any]) -> Optional[int]:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        value = item.get(key)
        if isinstance(value, Mapping):
            parts = value.get("date-parts")
            if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
                year = parts[0][0]
                if isinstance(year, int):
                    return year
    return None


def normalize_crossref(payload: Mapping[str, Any], query: Mapping[str, Any]) -> List[Dict[str, Any]]:
    message = payload.get("message", {})
    items = message.get("items", []) if isinstance(message, Mapping) else []
    records: List[Dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, Mapping):
            continue
        title_value = item.get("title", [])
        title = title_value[0] if isinstance(title_value, list) and title_value else title_value
        venue_value = item.get("container-title", [])
        venue = venue_value[0] if isinstance(venue_value, list) and venue_value else venue_value
        authors = []
        for author in item.get("author", []) or []:
            if not isinstance(author, Mapping):
                continue
            name = normalize_space(" ".join(part for part in (author.get("given"), author.get("family")) if part))
            if name:
                authors.append(name)
        links = item.get("link", []) or []
        fulltext_url = None
        for link in links:
            if isinstance(link, Mapping) and link.get("URL"):
                fulltext_url = link["URL"]
                break
        abstract = strip_html(item.get("abstract"))
        records.append(
            {
                "provider": "crossref",
                "provider_record_id": item.get("DOI") or item.get("URL"),
                "query_ids": [query["query_id"]],
                "query_intent_ids": [query["query_intent_id"]],
                "query_lanes": [query["lane"]],
                "query_polarities": [query["polarity"]],
                "title": normalize_space(title),
                "authors": unique_strings(authors),
                "year": crossref_year(item),
                "language": item.get("language"),
                "publication_type": item.get("type"),
                "venue": normalize_space(venue),
                "doi": normalize_doi(item.get("DOI")),
                "edn": None,
                "isbn": unique_strings(item.get("ISBN", []) or []),
                "issn": unique_strings(item.get("ISSN", []) or []),
                "abstract": abstract,
                "landing_url": item.get("URL"),
                "fulltext_url": fulltext_url,
                "cited_by_count": item.get("is-referenced-by-count"),
                "verification_status": "abstract_checked" if abstract else "metadata_only",
                "access_status": "fulltext_link_candidate" if fulltext_url else "metadata_or_landing",
                "license_status": "unknown_requires_item_check",
            }
        )
    return records


def provider_url(provider: str, query_text: str, request: Mapping[str, Any], max_results: int) -> str:
    contact = normalize_space(os.getenv("SCHOLARLY_API_EMAIL"))
    date_range = request.get("date_range", {}) or {}
    if provider == "openalex":
        filters = []
        languages = unique_strings(request.get("languages", []))
        if languages and "any" not in languages:
            filters.append("language:" + "|".join(languages))
        if isinstance(date_range.get("from"), int):
            filters.append(f"from_publication_date:{date_range['from']}-01-01")
        if isinstance(date_range.get("to"), int):
            filters.append(f"to_publication_date:{date_range['to']}-12-31")
        params: Dict[str, Any] = {"search": query_text, "per-page": max_results}
        if filters:
            params["filter"] = ",".join(filters)
        openalex_credential = normalize_space(os.getenv("OPENALEX_API_KEY"))
        if not openalex_credential:
            raise DoctrineResearchError("OpenAlex requires OPENALEX_API_KEY")
        params["api_key"] = openalex_credential
        return "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    if provider == "crossref":
        filters = []
        if isinstance(date_range.get("from"), int):
            filters.append(f"from-pub-date:{date_range['from']}-01-01")
        if isinstance(date_range.get("to"), int):
            filters.append(f"until-pub-date:{date_range['to']}-12-31")
        params = {"query.bibliographic": query_text, "rows": max_results}
        if filters:
            params["filter"] = ",".join(filters)
        if contact:
            params["mailto"] = contact
        return "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    raise DoctrineResearchError(f"provider adapter not implemented: {provider}")


def fixture_payload(fixture_root: Path, provider: str, query_id: str) -> Any:
    candidates = (
        fixture_root / provider / f"{query_id}.json",
        fixture_root / provider / "default.json",
    )
    for candidate in candidates:
        if candidate.exists():
            return load_json(candidate)
    raise DoctrineResearchError(f"OFFLINE_FIXTURE_MISS:{provider}:{query_id}")


def normalize_provider_payload(provider: str, payload: Mapping[str, Any], query: Mapping[str, Any]) -> List[Dict[str, Any]]:
    try:
        if not isinstance(payload, Mapping):
            raise DoctrineResearchError(f"invalid {provider} response: top-level JSON object required")
        if provider == "openalex":
            if not isinstance(payload.get("meta"), Mapping) or not isinstance(payload.get("results"), list):
                raise DoctrineResearchError("invalid OpenAlex response: meta object and results list are required")
            openalex_count = payload.get("meta", {}).get("count")
            if payload.get("error") or not isinstance(openalex_count, int) or openalex_count < 0:
                raise DoctrineResearchError("invalid OpenAlex response: non-negative meta.count and no error are required")
            return normalize_openalex(payload, query)
        if provider == "crossref":
            message = payload.get("message")
            if payload.get("status") != "ok":
                raise DoctrineResearchError("invalid Crossref response: status must be ok")
            if not isinstance(message, Mapping) or not isinstance(message.get("items"), list):
                raise DoctrineResearchError("invalid Crossref response: message.items list is required")
            total_results = message.get("total-results")
            if not isinstance(total_results, int) or total_results < 0:
                raise DoctrineResearchError("invalid Crossref response: non-negative message.total-results is required")
            return normalize_crossref(payload, query)
        raise DoctrineResearchError(f"provider adapter not implemented: {provider}")
    except DoctrineResearchError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise DoctrineResearchError(
            f"provider response normalization failed for {provider}: {type(exc).__name__}: {exc}"
        ) from exc


def candidate_key(record: Mapping[str, Any]) -> Tuple[str, bool]:
    doi = normalize_doi(record.get("doi"))
    if doi:
        return f"doi:{doi}", True
    edn = normalize_title(record.get("edn"))
    if edn:
        return f"edn:{edn}", True
    isbn = unique_strings(record.get("isbn", []) or [])
    if isbn:
        return f"isbn:{normalize_title(isbn[0])}", True
    title = normalize_title(record.get("title"))
    provider_id = normalize_space(record.get("provider_record_id"))
    return f"provider:{record.get('provider')}:{provider_id or stable_id('', title, record.get('year'))}", False


def merge_candidates(records: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for original in records:
        record = dict(original)
        key, confident = candidate_key(record)
        if key not in grouped:
            record["deduplication_key"] = key
            record["deduplication_confident"] = confident
            record["discovered_by"] = [record.get("provider")]
            record["provider_records"] = [record.get("provider_record_id")]
            record["provider_urls"] = unique_strings([record.get("landing_url"), record.get("fulltext_url")])
            grouped[key] = record
            continue
        target = grouped[key]
        target["discovered_by"] = sorted(set(target.get("discovered_by", [])) | {record.get("provider")})
        target["provider_records"] = unique_strings([*target.get("provider_records", []), record.get("provider_record_id")])
        target["provider_urls"] = unique_strings([*target.get("provider_urls", []), record.get("landing_url"), record.get("fulltext_url")])
        target["query_ids"] = sorted(set(target.get("query_ids", [])) | set(record.get("query_ids", [])))
        target["query_intent_ids"] = sorted(set(target.get("query_intent_ids", [])) | set(record.get("query_intent_ids", [])))
        target["query_lanes"] = sorted(set(target.get("query_lanes", [])) | set(record.get("query_lanes", [])))
        target["query_polarities"] = sorted(set(target.get("query_polarities", [])) | set(record.get("query_polarities", [])))
        target["authors"] = unique_strings([*target.get("authors", []), *record.get("authors", [])])
        target["isbn"] = unique_strings([*target.get("isbn", []), *record.get("isbn", [])])
        target["issn"] = unique_strings([*target.get("issn", []), *record.get("issn", [])])
        if len(normalize_space(record.get("abstract"))) > len(normalize_space(target.get("abstract"))):
            target["abstract"] = record.get("abstract")
            target["verification_status"] = record.get("verification_status")
        if not target.get("fulltext_url") and record.get("fulltext_url"):
            target["fulltext_url"] = record.get("fulltext_url")
            target["access_status"] = record.get("access_status")
        conflicts = target.setdefault("field_conflicts", [])
        for field in ("title", "year", "venue"):
            left, right = target.get(field), record.get(field)
            if left not in (None, "") and right not in (None, "") and normalize_space(left).casefold() != normalize_space(right).casefold():
                conflict = {"field": field, "values": unique_strings([left, right])}
                if conflict not in conflicts:
                    conflicts.append(conflict)
    merged: List[Dict[str, Any]] = []
    for key in sorted(grouped):
        record = grouped[key]
        record["source_family_id"] = stable_id("family-", key)
        record["source_id"] = stable_id("src-", key)
        merged.append(record)
    return merged


def classify_problem_labels(text: str, taxonomy: Mapping[str, Any]) -> Tuple[List[str], Dict[str, List[str]]]:
    folded = text.casefold().replace("ё", "е")
    labels: List[str] = []
    matches: Dict[str, List[str]] = {}
    for category in taxonomy.get("categories", []):
        category_id = category.get("id")
        terms = unique_strings([*category.get("markers_ru", []), *category.get("markers_en", [])])
        found = [term for term in terms if term.casefold().replace("ё", "е") in folded]
        if found:
            labels.append(category_id)
            matches[category_id] = found
    return labels, matches


def contains_any(text: str, values: Iterable[str]) -> int:
    folded = text.casefold().replace("ё", "е")
    return sum(1 for value in unique_strings(values) if value.casefold().replace("ё", "е") in folded)


def enrich_record(record: MutableMapping[str, Any], request: Mapping[str, Any], taxonomy: Mapping[str, Any]) -> None:
    title = normalize_space(record.get("title", ""))
    abstract = normalize_space(record.get("abstract", ""))
    text = normalize_space(" ".join([title, abstract]))
    labels, matches = classify_problem_labels(text, taxonomy)
    record["problem_labels"] = labels
    record["problem_marker_matches"] = matches
    citations = [text for text, origin in norm_anchors(request) if not origin.endswith(".title")]
    titles = [text for text, origin in norm_anchors(request) if origin.endswith(".title")]
    topic_values = [
        *titles,
        *unique_strings(request.get("disputed_elements", [])),
        *unique_strings(request.get("mechanisms", [])),
        *unique_strings(request.get("consequences", [])),
        *unique_strings(request.get("subject_terms", [])),
    ]
    topic_stems = lexical_stems(topic_values)
    title_topic_stems = sorted(topic_stems & lexical_stems([title]))
    abstract_topic_stems = sorted((topic_stems & lexical_stems([abstract])) - set(title_topic_stems))
    components = {
        "exact_norm_hits": contains_any(text, citations),
        "norm_title_hits": contains_any(text, titles),
        "disputed_element_hits": contains_any(text, request.get("disputed_elements", [])),
        "mechanism_hits": contains_any(text, request.get("mechanisms", [])),
        "consequence_hits": contains_any(text, request.get("consequences", [])),
        "subject_term_hits": contains_any(text, request.get("subject_terms", [])),
        "title_topic_stem_hits": len(title_topic_stems),
        "abstract_topic_stem_hits": len(abstract_topic_stems),
        "problem_label_count": len(labels),
        "has_abstract": int(bool(record.get("abstract"))),
        "has_fulltext_candidate": int(bool(record.get("fulltext_url"))),
    }
    score = (
        components["exact_norm_hits"] * 8
        + components["norm_title_hits"] * 6
        + components["disputed_element_hits"] * 3
        + components["mechanism_hits"] * 2
        + components["consequence_hits"] * 2
        + components["subject_term_hits"] * 2
        + components["title_topic_stem_hits"] * 4
        + min(components["abstract_topic_stem_hits"], 8)
        + (min(components["problem_label_count"], 4) if title_topic_stems or abstract_topic_stems else 0)
        + components["has_abstract"]
        + components["has_fulltext_candidate"]
    )
    if components["exact_norm_hits"] or len(title_topic_stems) >= 2 or (title_topic_stems and len(abstract_topic_stems) >= 2):
        relevance_status = "high_lexical_priority"
    elif title_topic_stems or len(abstract_topic_stems) >= 2:
        relevance_status = "medium_lexical_priority"
    else:
        relevance_status = "weak_candidate"
    record["relevance_status"] = relevance_status
    record["topic_stem_matches"] = {
        "title": title_topic_stems,
        "abstract_only": abstract_topic_stems,
    }
    record["reading_priority"] = {
        "score": score,
        "components": components,
        "meaning": "discovery reading order only; not legal authority or source quality",
    }
    record["evidence_role"] = "doctrine_candidate"
    record["promotion_status"] = "candidate_only"
    record["cannot_satisfy"] = [
        "official_source",
        "current_norm_version",
        "application_in_applicant_case",
        "stable_judicial_meaning",
        "constitutional_authority",
        "case_facts",
    ]


def problem_candidates(records: Sequence[Mapping[str, Any]], taxonomy: Mapping[str, Any]) -> Dict[str, Any]:
    categories = {item["id"]: item for item in taxonomy.get("categories", [])}
    clusters = []
    for category_id in sorted(categories):
        matching = [
            record
            for record in records
            if category_id in record.get("problem_labels", [])
            and record.get("relevance_status") in {"high_lexical_priority", "medium_lexical_priority"}
        ]
        if not matching:
            continue
        matching = sorted(matching, key=lambda row: (-row.get("reading_priority", {}).get("score", 0), row.get("source_id", "")))
        category = categories[category_id]
        clusters.append(
            {
                "problem_candidate_id": stable_id("problem-", category_id),
                "category": category_id,
                "label": category.get("label_ru"),
                "candidate_localizations": category.get("candidate_localizations", []),
                "source_ids": [row["source_id"] for row in matching[:20]],
                "status": "candidate_only",
                "warning": "Keyword-level discovery cluster; full-text propositions and defect localization are still required.",
            }
        )
    return {
        "schema_version": "doctrine-problem-candidates/1.0",
        "clusters": clusters,
        "constitutional_hypotheses": [],
    }


def build_coverage(
    request: Mapping[str, Any],
    routing: Mapping[str, Any],
    selected_providers: Sequence[str],
    query_count: int,
    logs: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    run_config_hash: str,
) -> Dict[str, Any]:
    provider_statuses = []
    for provider in selected_providers:
        provider_logs = [row for row in logs if row.get("provider") == provider]
        successes = [row for row in provider_logs if row.get("status") == "success"]
        failures = [row for row in provider_logs if row.get("status") != "success"]
        if successes and not failures:
            status = "complete_bounded"
        elif successes:
            status = "partial"
        elif any("OFFLINE_FIXTURE_MISS" in str(row.get("error")) for row in failures):
            status = "offline_fixture_miss"
        else:
            status = "provider_error"
        provider_statuses.append(
            {
                "provider": provider,
                "status": status,
                "successful_queries": len(successes),
                "failed_queries": len(failures),
            }
        )
    manual_gaps = [
        {
            "provider": row["provider"],
            "label": row["label"],
            "status": row["access_status"],
            "roles": row.get("roles", []),
            "blocks_absence_claim": True,
        }
        for row in routing.get("decisions", [])
        if row.get("manual_task_required")
        or row.get("access_status")
        in {
            "auth_required",
            "subscription_required",
            "optional_subscription",
            "license_review_required",
            "manual_optional",
            "candidate_not_enabled",
            "contact_email_required",
            "api_key_recommended",
            "available_if_running",
        }
    ]
    bounded_complete = bool(selected_providers) and all(row["status"] == "complete_bounded" for row in provider_statuses)
    return {
        "schema_version": "doctrine-coverage/1.0",
        "matter_id": request["matter_id"],
        "request_sha256": request_sha256(request),
        "run_config_hash": run_config_hash,
        "as_of_date": request["as_of_date"],
        "bounded_search_complete": bounded_complete,
        "coverage_complete": False,
        "absence_claim_permitted": False,
        "queries_attempted": query_count * len(selected_providers),
        "provider_statuses": provider_statuses,
        "unique_candidates": len(records),
        "high_lexical_priority_candidates": sum(1 for row in records if row.get("relevance_status") == "high_lexical_priority"),
        "medium_lexical_priority_candidates": sum(1 for row in records if row.get("relevance_status") == "medium_lexical_priority"),
        "weak_candidates": sum(1 for row in records if row.get("relevance_status") == "weak_candidate"),
        "metadata_only": sum(1 for row in records if row.get("verification_status") == "metadata_only"),
        "abstract_checked": sum(1 for row in records if row.get("verification_status") == "abstract_checked"),
        "fulltext_candidates": sum(1 for row in records if row.get("fulltext_url")),
        "page_verified": 0,
        "manual_and_access_gaps": manual_gaps,
        "adverse_fulltext_pass_complete": False,
        "citation_chaining_complete": False,
        "permitted_absence_wording": "No candidates were found in the explicitly completed bounded scope." if not records and bounded_complete else None,
    }


def acquisition_queue(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = []
    for record in records:
        if record.get("relevance_status") == "weak_candidate":
            continue
        if record.get("fulltext_url") and record.get("access_status") in {
            "open_fulltext_verified",
            "local_fulltext_verified",
        }:
            continue
        if record.get("reading_priority", {}).get("score", 0) <= 0:
            continue
        rows.append(
            {
                "request_id": stable_id("acq-", record["source_id"]),
                "source_id": record["source_id"],
                "title": record.get("title"),
                "authors": record.get("authors", []),
                "doi": record.get("doi"),
                "status": "access_review_required",
                "next_step": "Verify any candidate full-text link, then check local library, OA resolvers, catalogues, and publisher terms before purchase.",
                "payment_authorized": False,
            }
        )
    return {"schema_version": "doctrine-acquisition-queue/1.0", "requests": rows[:50]}


def run_plan(args: argparse.Namespace) -> int:
    request = load_request(Path(args.request))
    selected = [part for part in (args.providers or "").split(",") if part]
    prepare_workspace(request, Path(args.workspace), selected)
    print(json.dumps({"status": "planned", "workspace": str(Path(args.workspace).resolve())}, ensure_ascii=False))
    return 0


def run_search(args: argparse.Namespace) -> int:
    request = load_request(Path(args.request), for_external_search=True)
    selected = unique_strings(part.strip() for part in args.providers.split(","))
    if not selected:
        raise DoctrineResearchError("at least one provider is required")
    query_plan_preflight = build_query_plan(request)
    if request.get("mode") in {"case_scoped", "hypothesis_verification"}:
        approved_hash = normalize_space(getattr(args, "approved_query_plan_hash", ""))
        if approved_hash != query_plan_preflight["query_plan_hash"]:
            raise DoctrineResearchError(
                "manual query-plan review required: pass the exact --approved-query-plan-hash from the plan artifact"
            )
    registry_preflight = load_json(REGISTRY_PATH)
    routing_preflight = provider_routing(request, registry_preflight, selected)
    decisions = {row["provider"]: row for row in routing_preflight["decisions"]}
    for provider in selected:
        if not decisions[provider].get("adapter"):
            raise DoctrineResearchError(f"selected provider has no implemented adapter: {provider}")
        offline_auth_fixture = bool(
            args.offline_fixtures and decisions[provider].get("access_status") == "auth_required"
        )
        if not decisions[provider].get("automated_run_eligible") and not offline_auth_fixture:
            raise DoctrineResearchError(
                f"selected provider is not enabled for automated access: {provider} "
                f"({decisions[provider].get('access_status')})"
            )
    registry, taxonomy, query_plan, routing = prepare_workspace(request, Path(args.workspace), selected)
    violations = redaction_violations(query_plan, request)
    if violations:
        write_json(Path(args.workspace) / "qa-report.json", {"status": "blocked", "redaction_violations": violations})
        raise DoctrineResearchError("external query plan failed redaction checks")
    queries = select_bounded_queries(query_plan, args.max_queries)
    run_config_core = {
        "schema_version": "doctrine-search-run/1.0",
        "matter_id": request["matter_id"],
        "request_sha256": request_sha256(request),
        "query_plan_hash": query_plan["query_plan_hash"],
        "selected_providers": selected,
        "selected_query_ids": [query["query_id"] for query in queries],
        "max_queries": args.max_queries,
        "max_results_per_query": args.max_results,
        "approved_query_plan_hash": normalize_space(getattr(args, "approved_query_plan_hash", "")) or None,
    }
    run_config_hash = hashlib.sha256(canonical_bytes(run_config_core)).hexdigest()
    run_config = {**run_config_core, "run_config_hash": run_config_hash}
    write_json(Path(args.workspace) / "search-run-config.json", run_config)
    logs: List[Dict[str, Any]] = []
    normalized: List[Dict[str, Any]] = []
    fixture_root = Path(args.offline_fixtures) if args.offline_fixtures else None
    for provider in selected:
        for query in queries:
            log: Dict[str, Any] = {
                "provider": provider,
                "query_id": query["query_id"],
                "query_intent_id": query["query_intent_id"],
                "lane": query["lane"],
                "query_text": query["text"],
                "as_of_date": request["as_of_date"],
            }
            try:
                if fixture_root:
                    payload = fixture_payload(fixture_root, provider, query["query_id"])
                    meta = {"transport": "offline_fixture", "fixture_root": str(fixture_root.resolve())}
                else:
                    url = provider_url(provider, query["text"], request, args.max_results)
                    payload, meta = http_json(url, timeout=args.timeout, contact_email=normalize_space(os.getenv("SCHOLARLY_API_EMAIL")) or None)
                    meta["transport"] = "network"
                rows = normalize_provider_payload(provider, payload, query)
                normalized.extend(rows)
                log.update({"status": "success", "result_count": len(rows), **meta})
            except DoctrineResearchError as exc:
                log.update({"status": "error", "result_count": 0, "error": str(exc), "transport": "offline_fixture" if fixture_root else "network"})
            logs.append(log)
            if not fixture_root and getattr(args, "request_delay", 0) > 0:
                time.sleep(args.request_delay)

    records = merge_candidates(normalized)
    for record in records:
        enrich_record(record, request, taxonomy)
    records.sort(key=lambda row: (-row.get("reading_priority", {}).get("score", 0), row.get("source_id", "")))
    coverage = build_coverage(request, routing, selected, len(queries), logs, records, run_config_hash)
    write_jsonl(Path(args.workspace) / "search-log.jsonl", logs)
    write_jsonl(Path(args.workspace) / "source-ledger.jsonl", records)
    write_json(Path(args.workspace) / "problem-candidates.json", problem_candidates(records, taxonomy))
    write_json(Path(args.workspace) / "coverage-report.json", coverage)
    write_json(Path(args.workspace) / "acquisition-queue.json", acquisition_queue(records))
    qa = validate_workspace(Path(args.workspace))
    write_json(Path(args.workspace) / "qa-report.json", qa)
    if qa["status"] != "pass":
        run_status = "searched_with_qa_errors"
    elif not any(row.get("status") == "success" for row in logs):
        run_status = "searched_without_success"
    elif not coverage["bounded_search_complete"]:
        run_status = "searched_with_coverage_gaps"
    else:
        run_status = "searched"
    summary = {
        "status": run_status,
        "workspace": str(Path(args.workspace).resolve()),
        "unique_candidates": len(records),
        "bounded_search_complete": coverage["bounded_search_complete"],
        "coverage_complete": False,
        "qa_status": qa["status"],
    }
    print(json.dumps(summary, ensure_ascii=False))
    if qa["status"] != "pass":
        return 2
    if not any(row.get("status") == "success" for row in logs):
        return 3
    if not coverage["bounded_search_complete"]:
        return 4
    return 0


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DoctrineResearchError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise DoctrineResearchError(f"JSONL row must be an object at {path}:{line_number}")
            rows.append(value)
    return rows


def validate_workspace(workspace: Path) -> Dict[str, Any]:
    required = (
        "request.snapshot.json",
        "norm-problem-profile.json",
        "provider-capabilities.snapshot.json",
        "provider-routing.json",
        "query-plan.json",
    )
    errors = []
    warnings = []
    for filename in required:
        if not (workspace / filename).exists():
            errors.append(f"missing required artifact: {filename}")
    if errors:
        return {"schema_version": "doctrine-qa/1.0", "status": "fail", "errors": errors, "warnings": warnings}
    snapshot = load_json(workspace / "request.snapshot.json")
    if not isinstance(snapshot, Mapping):
        errors.append("request.snapshot.json must be an object")
        snapshot = {}
    snapshot_matter = snapshot.get("matter_id")
    snapshot_hash = request_sha256(snapshot)
    for filename in ("norm-problem-profile.json", "provider-routing.json", "query-plan.json"):
        artifact = load_json(workspace / filename)
        if artifact.get("matter_id") != snapshot_matter:
            errors.append(f"matter_id mismatch in {filename}")
        if artifact.get("request_sha256") != snapshot_hash:
            errors.append(f"request hash mismatch in {filename}")
    query_plan = load_json(workspace / "query-plan.json")
    query_ids = [row.get("query_id") for row in query_plan.get("queries", [])]
    if len(query_ids) != len(set(query_ids)):
        errors.append("duplicate query_id")
    if query_plan.get("legal_conclusions"):
        errors.append("query plan must not contain legal conclusions")
    source_path = workspace / "source-ledger.jsonl"
    sources: List[Dict[str, Any]] = []
    if source_path.exists():
        sources = read_jsonl(source_path)
        source_ids = [row.get("source_id") for row in sources]
        if len(source_ids) != len(set(source_ids)):
            errors.append("duplicate source_id")
        for row in sources:
            if row.get("promotion_status") != "candidate_only":
                errors.append(f"source promoted beyond candidate_only: {row.get('source_id')}")
            if row.get("verification_status") not in {"metadata_only", "abstract_checked"}:
                errors.append(f"network metadata has invalid verification status: {row.get('source_id')}")
    problem_path = workspace / "problem-candidates.json"
    if problem_path.exists():
        problems = load_json(problem_path)
        known = {row.get("source_id") for row in sources}
        for cluster in problems.get("clusters", []):
            unknown = set(cluster.get("source_ids", [])) - known
            if unknown:
                errors.append(f"problem cluster references unknown sources: {sorted(unknown)}")
            if cluster.get("status") != "candidate_only":
                errors.append("problem cluster promoted beyond candidate_only")
        if problems.get("constitutional_hypotheses"):
            errors.append("discovery script must not emit constitutional hypotheses")
    coverage_path = workspace / "coverage-report.json"
    if coverage_path.exists():
        coverage = load_json(coverage_path)
        if coverage.get("matter_id") != snapshot_matter:
            errors.append("matter_id mismatch in coverage-report.json")
        if coverage.get("request_sha256") != snapshot_hash:
            errors.append("request hash mismatch in coverage-report.json")
        if coverage.get("coverage_complete") is not False:
            errors.append("federated discovery coverage_complete must remain false")
        if coverage.get("absence_claim_permitted") is not False:
            errors.append("absence_claim_permitted must remain false")
        run_config_path = workspace / "search-run-config.json"
        if not run_config_path.exists():
            errors.append("coverage exists without search-run-config.json")
        else:
            run_config = load_json(run_config_path)
            if run_config.get("request_sha256") != snapshot_hash:
                errors.append("request hash mismatch in search-run-config.json")
            if run_config.get("run_config_hash") != coverage.get("run_config_hash"):
                errors.append("run config hash mismatch in coverage-report.json")
            routing = load_json(workspace / "provider-routing.json")
            routed = sorted(
                row.get("provider")
                for row in routing.get("decisions", [])
                if row.get("selected_for_automated_run")
            )
            configured = sorted(run_config.get("selected_providers", []))
            covered = sorted(row.get("provider") for row in coverage.get("provider_statuses", []))
            if routed != configured or covered != configured:
                errors.append("provider set mismatch across routing, run config, and coverage")
    else:
        warnings.append("search artifacts are not present; plan-only workspace")
    return {
        "schema_version": "doctrine-qa/1.0",
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
    }


def run_validate(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    report = validate_workspace(workspace)
    write_json(workspace / "qa-report.json", report)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 2


def run_rerank(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    request = load_request(Path(args.request))
    ensure_workspace_identity(request, workspace)
    source_path = workspace / "source-ledger.jsonl"
    if not source_path.is_file():
        raise DoctrineResearchError("source-ledger.jsonl is required for rerank")
    taxonomy = load_json(TAXONOMY_PATH)
    records = read_jsonl(source_path)
    for record in records:
        enrich_record(record, request, taxonomy)
    records.sort(key=lambda row: (-row.get("reading_priority", {}).get("score", 0), row.get("source_id", "")))
    write_jsonl(source_path, records)
    write_json(workspace / "problem-candidates.json", problem_candidates(records, taxonomy))
    write_json(workspace / "acquisition-queue.json", acquisition_queue(records))
    coverage_path = workspace / "coverage-report.json"
    if coverage_path.is_file():
        coverage = load_json(coverage_path)
        coverage.update(
            {
                "high_lexical_priority_candidates": sum(1 for row in records if row.get("relevance_status") == "high_lexical_priority"),
                "medium_lexical_priority_candidates": sum(1 for row in records if row.get("relevance_status") == "medium_lexical_priority"),
                "weak_candidates": sum(1 for row in records if row.get("relevance_status") == "weak_candidate"),
            }
        )
        write_json(coverage_path, coverage)
    report = validate_workspace(workspace)
    write_json(workspace / "qa-report.json", report)
    print(
        json.dumps(
            {
                "status": "reranked" if report["status"] == "pass" else "reranked_with_qa_errors",
                "workspace": str(workspace.resolve()),
                "unique_candidates": len(records),
                "high_lexical_priority_candidates": sum(1 for row in records if row.get("relevance_status") == "high_lexical_priority"),
                "qa_status": report["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "pass" else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan and run bounded legal-doctrine discovery.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Create deterministic query and provider-routing artifacts.")
    plan.add_argument("--request", required=True)
    plan.add_argument("--workspace", required=True)
    plan.add_argument("--providers", default="")
    plan.set_defaults(func=run_plan)

    search = subparsers.add_parser("search", help="Run selected documented API adapters.")
    search.add_argument("--request", required=True)
    search.add_argument("--workspace", required=True)
    search.add_argument("--providers", default="openalex,crossref")
    search.add_argument("--max-queries", type=int, default=12)
    search.add_argument("--max-results", type=int, default=10)
    search.add_argument("--timeout", type=float, default=20.0)
    search.add_argument("--request-delay", type=float, default=0.15)
    search.add_argument("--offline-fixtures")
    search.add_argument(
        "--approved-query-plan-hash",
        help="Required for case_scoped and hypothesis_verification after human review of query-plan.json.",
    )
    search.set_defaults(func=run_search)

    validate = subparsers.add_parser("validate", help="Validate a plan or completed bounded search workspace.")
    validate.add_argument("--workspace", required=True)
    validate.set_defaults(func=run_validate)

    rerank = subparsers.add_parser("rerank", help="Reapply the current legal-topic heuristic without network calls.")
    rerank.add_argument("--request", required=True)
    rerank.add_argument("--workspace", required=True)
    rerank.set_defaults(func=run_rerank)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "max_queries") and args.max_queries < 1:
        parser.error("--max-queries must be positive")
    if hasattr(args, "max_results") and not 1 <= args.max_results <= 100:
        parser.error("--max-results must be between 1 and 100")
    if hasattr(args, "request_delay") and args.request_delay < 0:
        parser.error("--request-delay must not be negative")
    try:
        return int(args.func(args))
    except DoctrineResearchError as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
