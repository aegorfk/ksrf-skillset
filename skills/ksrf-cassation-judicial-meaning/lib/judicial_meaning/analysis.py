"""Deterministic screening and fail-closed legal-research conclusion gates."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from typing import Any, Iterable


ALLOWED_CONCLUSIONS = frozenset(
    {
        "corroborated_observed_corpus",
        "material_split_candidate",
        "temporal_shift_candidate",
        "circuit_divergence_candidate",
        "fact_sensitive_divergence",
        "implementation_gap",
        "contradicted",
        "insufficient_coverage",
        "measurement_unreliable",
        "needs_human_resolution",
    }
)

_REQUIRED_CODING_FIELDS = {
    "chain_id",
    "document_id",
    "label",
    "speaker",
    "proposition",
    "quote",
    "quote_locator",
    "norm_edition_id",
    "reasoning_to_outcome",
    "reading_family",
    "relation",
    "remedy",
    "coder",
    "codebook_version",
    "human_review",
}
_VALID_LABELS = {
    "core_merits",
    "contextual",
    "party_only",
    "mentioned_only",
    "quoted_not_adopted",
    "false_positive",
    "unclear",
}
_VALID_RELATIONS = {"supports", "adverse", "neutral", "distinguishes", "supersedes"}
_RISKY_CLAIM_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:судебн\w+\s+)?хаос\b", re.IGNORECASE), "Слово «хаос» замените проверяемым описанием расхождения."),
    (
        re.compile(r"\bдоказыва\w*\s+неконституцион", re.IGNORECASE),
        "Корпус практики сам по себе не доказывает неконституционность нормы.",
    ),
    (re.compile(r"\bзакон\s+(?:в\s+целом\s+)?не\s+работает\b", re.IGNORECASE), "Утверждение «закон не работает» не является измеримым выводом корпуса."),
    (
        re.compile(r"\b(?:вся|все|любая|любые)\s+судебн\w*\s+практик", re.IGNORECASE),
        "Нельзя распространять результат наблюдаемого корпуса на всю судебную практику.",
    ),
    (
        re.compile(r"\bпрактик\w*\s+(?:абсолютно\s+)?единообраз", re.IGNORECASE),
        "Абсолютное единообразие нельзя утверждать без доказанного полного охвата.",
    ),
    (
        re.compile(r"\bустойчив\w+\s+(?:судебн\w+\s+)?практик", re.IGNORECASE),
        "Устойчивость практики требует отдельного одобренного правила измерения и закрытого охвата.",
    ),
    (
        re.compile(r"\b(?:тренд|динамик\w*)\b", re.IGNORECASE),
        "Тренд или динамику нельзя заявлять без раздельных временных страт, редакций и comparability review.",
    ),
)


def screen_text(text: str, query_lanes: dict[str, list[str]]) -> list[dict[str, Any]]:
    """Apply high-recall literal screening lanes supplied by the frozen plan."""

    if not isinstance(text, str) or not isinstance(query_lanes, dict):
        return []
    folded = text.casefold()
    matches: list[dict[str, Any]] = []
    for lane, queries in query_lanes.items():
        if not isinstance(lane, str) or not isinstance(queries, list):
            continue
        seen: set[str] = set()
        for raw_query in queries:
            if not isinstance(raw_query, str):
                continue
            query = " ".join(raw_query.split())
            folded_query = query.casefold()
            if not folded_query or folded_query in seen:
                continue
            seen.add(folded_query)
            start = folded.find(folded_query)
            if start >= 0:
                matches.append(
                    {
                        "lane": lane,
                        "query": query,
                        "start": start,
                        "end": start + len(folded_query),
                    }
                )
    return matches


def validate_coding_record(record: dict[str, Any]) -> list[str]:
    """Reject a legal proposition unless a human checked the court's full text."""

    if not isinstance(record, dict):
        return ["Карточка кодирования должна быть JSON-объектом."]
    errors: list[str] = []
    missing = sorted(field for field in _REQUIRED_CODING_FIELDS if not record.get(field))
    if missing:
        errors.append("Не заполнены обязательные поля: " + ", ".join(missing) + ".")
    if record.get("label") in {"core_merits", "contextual"} and record.get("speaker") != "court":
        errors.append("Правовую позицию нужно атрибутировать суду, а не стороне или пересказу.")
    if record.get("full_text_reviewed") is not True:
        errors.append("Полный текст акта не проверен.")
    if record.get("quote_verified") is not True:
        errors.append("Цитата не сверена с полным текстом.")
    if record.get("label") not in _VALID_LABELS:
        errors.append("Неизвестная метка роли акта в исследовании.")
    if record.get("relation") not in _VALID_RELATIONS:
        errors.append("Неизвестное отношение акта к проверяемому предположению.")
    if record.get("human_review") != "approved":
        errors.append("Кодирование не одобрено человеком.")
    if not isinstance(record.get("reasoning_to_outcome"), str) or not record.get("reasoning_to_outcome", "").strip():
        errors.append("Не объяснена связь толкования с исходом дела.")
    if not isinstance(record.get("material_facts"), list) or not record.get("material_facts"):
        errors.append("Не указаны материальные факты для проверки сопоставимости.")
    if not isinstance(record.get("alternative_grounds"), list):
        errors.append("Альтернативные основания должны быть явно перечислены, даже если список пуст.")
    return errors


def validate_coding_against_text(record: dict[str, Any], full_text: str) -> list[str]:
    """Verify that the reviewed quote is actually present in the stored full text."""

    errors = validate_coding_record(record)
    if not isinstance(full_text, str) or not full_text.strip():
        errors.append("Сохранённый полный текст документа отсутствует.")
        return errors
    quote = record.get("quote")
    if isinstance(quote, str):
        normalised_quote = " ".join(quote.casefold().split())
        normalised_text = " ".join(full_text.casefold().split())
        if normalised_quote and normalised_quote not in normalised_text:
            errors.append("Проверенная цитата не найдена в сохранённом полном тексте документа.")
    return errors


def _approved_unique_chains(records: Iterable[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    chains: dict[str, dict[str, Any]] = {}
    conflicts: list[str] = []
    for record in records:
        if not isinstance(record, dict) or record.get("human_review") != "approved":
            continue
        chain_id = record.get("chain_id")
        family = record.get("reading_family")
        if not isinstance(chain_id, str) or not chain_id.strip() or not isinstance(family, str) or not family.strip():
            continue
        normalised = {
            "chain_id": chain_id.strip(),
            "reading_family": family.strip(),
            "relation": record.get("relation"),
            "decision_date": record.get("decision_date"),
            "court_code": record.get("court_code"),
            "norm_edition_id": record.get("norm_edition_id"),
            "material_facts_group": record.get("material_facts_group"),
            "comparability_approved": record.get("comparability_approved") is True,
        }
        previous = chains.get(normalised["chain_id"])
        if previous is None:
            chains[normalised["chain_id"]] = normalised
        elif previous != normalised:
            conflicts.append(normalised["chain_id"])
    return chains, sorted(set(conflicts))


def analyze_reviewed_chains(
    records: Iterable[dict[str, Any]],
    *,
    coverage_status: str,
) -> dict[str, Any]:
    """Summarise approved independent case chains without overstating coverage."""

    chains, conflicts = _approved_unique_chains(records)
    family_counts = Counter(record["reading_family"] for record in chains.values())
    relation_counts = Counter(str(record.get("relation")) for record in chains.values())
    edition_counts = Counter(
        str(record["norm_edition_id"])
        for record in chains.values()
        if record.get("norm_edition_id")
    )
    court_counts = Counter(
        str(record["court_code"])
        for record in chains.values()
        if record.get("court_code")
    )
    year_counts = Counter(
        str(record["decision_date"])[:4]
        for record in chains.values()
        if isinstance(record.get("decision_date"), str)
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(record["decision_date"]))
    )

    def separated_by(field: str) -> bool:
        by_family: dict[str, set[str]] = {}
        for record in chains.values():
            value = record.get(field)
            if not isinstance(value, str) or not value.strip():
                return False
            by_family.setdefault(record["reading_family"], set()).add(value.strip())
        families = list(by_family)
        return len(families) >= 2 and all(
            by_family[left].isdisjoint(by_family[right])
            for index, left in enumerate(families)
            for right in families[index + 1 :]
        )

    def temporal_separation() -> bool:
        ranges: list[tuple[str, str]] = []
        by_family: dict[str, list[str]] = {}
        for record in chains.values():
            value = record.get("decision_date")
            if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                return False
            by_family.setdefault(record["reading_family"], []).append(value)
        if len(by_family) < 2:
            return False
        for values in by_family.values():
            ranges.append((min(values), max(values)))
        ranges.sort()
        return all(ranges[index][1] < ranges[index + 1][0] for index in range(len(ranges) - 1))

    if conflicts:
        status = "measurement_unreliable"
    elif not chains:
        status = "insufficient_coverage"
    elif coverage_status not in {"closed_official_population_observed", "bounded_sample_observed"}:
        status = "insufficient_coverage"
    elif len(edition_counts) >= 2 and not all(
        record.get("comparability_approved") is True for record in chains.values()
    ):
        status = "needs_human_resolution"
    elif len(family_counts) >= 2:
        if separated_by("material_facts_group"):
            status = "fact_sensitive_divergence"
        elif separated_by("court_code"):
            status = "circuit_divergence_candidate"
        elif temporal_separation():
            status = "temporal_shift_candidate"
        else:
            status = "material_split_candidate"
    elif relation_counts.get("adverse", 0) and not relation_counts.get("supports", 0):
        status = "contradicted"
    else:
        status = "corroborated_observed_corpus"

    return {
        "schema_version": "1.0",
        "status": status,
        "independent_chain_count": len(chains),
        "reading_family_counts": dict(sorted(family_counts.items())),
        "relation_counts": dict(sorted(relation_counts.items())),
        "norm_edition_counts": dict(sorted(edition_counts.items())),
        "court_counts": dict(sorted(court_counts.items())),
        "year_counts": dict(sorted(year_counts.items())),
        "conflicting_chain_ids": conflicts,
        "coverage_status": coverage_status,
        "bounded": True,
    }


def build_thesis_candidates(
    plan: dict[str, Any],
    applicant_chain: dict[str, Any],
    coding_records: Iterable[dict[str, Any]],
    analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build bounded post-corpus candidates, never a drafting-ready assertion."""

    status = analysis.get("status")
    if status in {None, "insufficient_coverage", "measurement_unreliable", "needs_human_resolution"}:
        return []
    approved = [
        record
        for record in coding_records
        if isinstance(record, dict)
        and record.get("human_review") == "approved"
        and isinstance(record.get("chain_id"), str)
    ]
    if not approved:
        return []
    supportive = sorted(
        {record["chain_id"] for record in approved if record.get("relation") == "supports"}
    )
    adverse = sorted(
        {record["chain_id"] for record in approved if record.get("relation") == "adverse"}
    )
    edition_ids = sorted(
        {
            str(record["norm_edition_id"])
            for record in approved
            if record.get("norm_edition_id")
        }
    )
    applicant_meanings = [
        proposition.get("meaning")
        for proposition in applicant_chain.get("propositions", [])
        if isinstance(proposition, dict)
        and proposition.get("speaker") == "court"
        and isinstance(proposition.get("meaning"), str)
        and proposition.get("meaning", "").strip()
    ]
    applicant_meaning = applicant_meanings[0] if len(applicant_meanings) == 1 else None
    candidates: list[dict[str, Any]] = []
    for question in plan.get("research_questions", []):
        if not isinstance(question, dict):
            continue
        base = {
            "schema_version": "1.0",
            "status": status,
            "research_question_id": question.get("id"),
            "norm_refs": question.get("norm_refs", []),
            "norm_edition_ids": edition_ids,
            "applicant_case_meaning": applicant_meaning,
            "supportive_chain_ids": supportive,
            "adverse_chain_ids": adverse,
            "coverage_status": analysis.get("coverage_status"),
            "observed_statement": (
                "В раскрытом и проверенном корпусе независимых цепочек дел выявлено "
                f"соотношение чтений со статусом {status}; вывод не выходит за раскрытый охват."
            ),
            "limitations": [
                "Практика используется как доказательство придаваемого норме смысла, а не как самостоятельный предмет проверки КС РФ.",
                "Частота и расхождение сами по себе не доказывают неконституционность.",
            ],
            "normative_defect_bridge": None,
            "human_review": "pending",
            "drafting_ready": False,
            "plan_sha256": plan.get("plan_sha256"),
        }
        base["candidate_id"] = "thesis-" + hashlib.sha256(
            json.dumps(base, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16]
        candidates.append(base)
    return candidates


def validate_thesis_candidate(candidate: dict[str, Any]) -> list[str]:
    """Validate the legal bridge that only a human may approve after corpus review."""

    if not isinstance(candidate, dict):
        return ["Кандидат тезиса должен быть JSON-объектом."]
    errors: list[str] = []
    status = candidate.get("status")
    if status not in ALLOWED_CONCLUSIONS or status in {
        "insufficient_coverage",
        "measurement_unreliable",
        "needs_human_resolution",
    }:
        errors.append("Статус исследования не допускает одобрение тезиса по существу.")
    for field, message in (
        ("norm_refs", "Не указана точная оспариваемая норма."),
        ("norm_edition_ids", "Не указана применимая редакция нормы."),
        ("limitations", "Не раскрыты ограничения корпуса."),
    ):
        value = candidate.get(field)
        if not isinstance(value, list) or not value:
            errors.append(message)
    if not isinstance(candidate.get("applicant_case_meaning"), str) or not candidate.get(
        "applicant_case_meaning", ""
    ).strip():
        errors.append("Не установлен исходозначимый смысл нормы в деле заявителя.")
    supportive = candidate.get("supportive_chain_ids")
    adverse = candidate.get("adverse_chain_ids")
    if not isinstance(supportive, list) or not isinstance(adverse, list) or not (supportive or adverse):
        errors.append("Кандидат не связан ни с одной проверенной независимой цепочкой дела.")
    if not isinstance(candidate.get("coverage_status"), str) or not candidate.get(
        "coverage_status", ""
    ).strip():
        errors.append("Не указан статус охвата корпуса.")
    if not isinstance(candidate.get("normative_defect_bridge"), str) or not candidate.get(
        "normative_defect_bridge", ""
    ).strip():
        errors.append("Не объяснён мост от судебного смысла к предполагаемому нормативному дефекту.")
    if candidate.get("human_review") != "approved":
        errors.append("Кандидат тезиса не одобрен человеком.")
    return errors


def validate_thesis_readiness(state: dict[str, Any], proposed_thesis: str) -> list[str]:
    """Block a practice-dependent thesis until collection and review gates pass."""

    if not isinstance(state, dict):
        return ["Состояние исследования отсутствует."]
    errors: list[str] = []
    gates = (
        ("plan_frozen", "Исследовательский план не заморожен до сбора."),
        ("collection_complete", "Сбор заявленной совокупности не завершён."),
        ("coding_complete", "Кодирование полного текста актов не завершено."),
        ("adverse_review_complete", "Отдельный поиск неблагоприятной практики не завершён."),
        ("coverage_review_complete", "Охват и недоступные сегменты не проверены."),
        ("human_approved", "Итоговый вывод не одобрен человеком."),
        ("candidate_approved", "Кандидат тезиса не прошёл отдельную проверку нормативного моста."),
    )
    for key, message in gates:
        if state.get(key) is not True:
            errors.append(message)

    maximum_claim = state.get("maximum_permitted_claim")
    if maximum_claim in {None, "", "insufficient_coverage", "measurement_unreliable", "needs_human_resolution"}:
        errors.append("Текущий уровень охвата не допускает тезис по существу практики.")
    elif maximum_claim not in ALLOWED_CONCLUSIONS and maximum_claim != "corroborated_observed_corpus":
        errors.append("Неизвестен допустимый предел итогового утверждения.")

    if not isinstance(proposed_thesis, str) or not proposed_thesis.strip():
        errors.append("Проект тезиса отсутствует.")
        return errors
    for pattern, message in _RISKY_CLAIM_PATTERNS:
        if pattern.search(proposed_thesis):
            errors.append(message)
    return errors
