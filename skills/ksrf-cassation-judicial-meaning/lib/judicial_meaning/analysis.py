"""Deterministic screening and fail-closed legal-research conclusion gates."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import date
from typing import Any, Iterable


ALLOWED_CONCLUSIONS = frozenset(
    {
        "corroborated_observed_corpus",
        "material_split_candidate",
        "temporal_shift_candidate",
        "emergent_reading_candidate",
        "mixed_post_event",
        "insufficient_temporal_evidence",
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
_ALTERNATIVE_GROUND_FIELDS = {
    "ground",
    "independently_sufficient",
    "quote",
    "quote_locator",
}
_CLOSED_ENUMERATION_COVERAGE = {
    "closed_declared_enumeration_observed",
    "closed_official_population_observed",
}
_ANALYSABLE_COVERAGE = _CLOSED_ENUMERATION_COVERAGE | {"bounded_sample_observed"}
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


def _is_visible_text(value: Any) -> bool:
    """Accept substantive text only when it has no invisible control payload."""

    return (
        isinstance(value, str)
        and bool(value.strip())
        and not any(
            unicodedata.category(character) in {"Cf", "Cs"}
            or (
                unicodedata.category(character) == "Cc"
                and character not in {"\t", "\n", "\r"}
            )
            for character in value
        )
    )


def _is_canonical_visible_identifier(value: Any) -> bool:
    """Require stable identity text rather than merely truthy Unicode."""

    return _is_visible_text(value) and value == " ".join(value.split())


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
    missing = sorted(
        field for field in _REQUIRED_CODING_FIELDS if not _is_visible_text(record.get(field))
    )
    if missing:
        errors.append("Не заполнены обязательные поля: " + ", ".join(missing) + ".")
    malformed_identifiers = sorted(
        field
        for field in (
            "chain_id",
            "document_id",
            "norm_edition_id",
            "reading_family",
            "remedy",
            "coder",
            "codebook_version",
        )
        if not _is_canonical_visible_identifier(record.get(field))
    )
    if malformed_identifiers:
        errors.append(
            "Идентификаторы должны быть видимыми и каноническими: "
            + ", ".join(malformed_identifiers)
            + "."
        )
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
    if not _is_visible_text(record.get("reasoning_to_outcome")):
        errors.append("Не объяснена связь толкования с исходом дела.")
    material_facts = record.get("material_facts")
    if (
        not isinstance(material_facts, list)
        or not material_facts
        or not all(_is_visible_text(item) for item in material_facts)
    ):
        errors.append("Не указаны материальные факты для проверки сопоставимости.")
    alternative_grounds = record.get("alternative_grounds")
    if not isinstance(alternative_grounds, list):
        errors.append("Альтернативные основания должны быть явно перечислены, даже если список пуст.")
    elif not all(
        isinstance(item, dict)
        and set(item).issubset(_ALTERNATIVE_GROUND_FIELDS)
        and _is_visible_text(item.get("ground"))
        and isinstance(item.get("independently_sufficient"), bool)
        and (item.get("quote") is None or _is_visible_text(item.get("quote")))
        and (
            item.get("quote_locator") is None
            or _is_visible_text(item.get("quote_locator"))
        )
        for item in alternative_grounds
    ):
        errors.append(
            "Каждое альтернативное основание должно содержать текст "
            "ground и логическое поле independently_sufficient."
        )
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
    temporal_strata: Iterable[dict[str, Any]] | None = None,
    interpretive_events: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Summarise approved independent case chains without overstating coverage."""

    chains, conflicts = _approved_unique_chains(records)

    def is_valid_date(value: Any) -> bool:
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return False
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
        return True

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
        if is_valid_date(record.get("decision_date"))
    )

    def matrix_cell(items: Iterable[dict[str, Any]]) -> dict[str, Any]:
        item_list = list(items)
        counts = Counter(record["reading_family"] for record in item_list)
        denominator = len(item_list)
        shares = {
            family: round(count / denominator, 6)
            for family, count in sorted(counts.items())
        } if denominator else {}
        return {
            "coded_chain_denominator": denominator,
            "counts": dict(sorted(counts.items())),
            "shares": shares,
        }

    by_year: dict[str, list[dict[str, Any]]] = {}
    for record in chains.values():
        decision_date = record.get("decision_date")
        if isinstance(decision_date, str) and is_valid_date(decision_date):
            by_year.setdefault(decision_date[:4], []).append(record)
    reading_family_by_year = {
        year: matrix_cell(items) for year, items in sorted(by_year.items())
    }

    strata = [item for item in (temporal_strata or []) if isinstance(item, dict)]
    events = [item for item in (interpretive_events or []) if isinstance(item, dict)]
    strata_by_id = {
        str(item.get("id")): item
        for item in strata
        if isinstance(item.get("id"), str) and item.get("id")
    }
    chains_by_stratum: dict[str, list[dict[str, Any]]] = {
        stratum_id: [] for stratum_id in strata_by_id
    }
    temporal_unassigned_chain_ids: list[str] = []
    for chain_id, record in chains.items():
        decision_date = record.get("decision_date")
        matches = []
        if isinstance(decision_date, str) and is_valid_date(decision_date):
            matches = [
                stratum_id
                for stratum_id, stratum in strata_by_id.items()
                if isinstance(stratum.get("date_from"), str)
                and isinstance(stratum.get("date_to"), str)
                and stratum["date_from"] <= decision_date <= stratum["date_to"]
            ]
        if strata and len(matches) != 1:
            temporal_unassigned_chain_ids.append(chain_id)
        elif len(matches) == 1:
            chains_by_stratum[matches[0]].append(record)

    reading_family_by_stratum = {
        stratum_id: matrix_cell(chains_by_stratum[stratum_id])
        for stratum_id in strata_by_id
    }
    event_findings: list[dict[str, Any]] = []
    for event in events:
        before_id = event.get("before_stratum_id")
        after_id = event.get("after_stratum_id")
        before_records = chains_by_stratum.get(str(before_id), [])
        after_records = chains_by_stratum.get(str(after_id), [])
        before_families = sorted({record["reading_family"] for record in before_records})
        after_families = sorted({record["reading_family"] for record in after_records})
        emergent_families = sorted(set(after_families) - set(before_families))
        persisting_families = sorted(set(after_families) & set(before_families))
        disappeared_families = sorted(set(before_families) - set(after_families))
        compared_records = before_records + after_records
        limitations = [
            "Знаменатель включает только одобренные полнотекстово закодированные независимые цепочки дел.",
            "Сравнение не означает полноту всех рассмотренных или опубликованных дел.",
        ]
        comparable = bool(compared_records) and all(
            record.get("comparability_approved") is True for record in compared_records
        )
        if (
            coverage_status not in _CLOSED_ENUMERATION_COVERAGE
            or temporal_unassigned_chain_ids
            or not before_records
            or not after_records
            or not comparable
        ):
            event_status = "insufficient_temporal_evidence"
        elif emergent_families and persisting_families:
            event_status = "mixed_post_event"
        elif emergent_families:
            event_status = "emergent_reading_candidate"
        elif disappeared_families:
            event_status = "contracted_post_event_observation"
        else:
            event_status = "no_observed_change"
        event_findings.append(
            {
                "event_id": event.get("id"),
                "before_stratum_id": before_id,
                "after_stratum_id": after_id,
                "before_chain_count": len(before_records),
                "after_chain_count": len(after_records),
                "before_families": before_families,
                "after_families": after_families,
                "emergent_families": emergent_families,
                "persisting_families": persisting_families,
                "disappeared_families": disappeared_families,
                "status": event_status,
                "limitations": limitations,
            }
        )

    temporal_analysis_complete = bool(strata) and not temporal_unassigned_chain_ids
    if events:
        temporal_analysis_complete = temporal_analysis_complete and all(
            finding["status"] != "insufficient_temporal_evidence"
            for finding in event_findings
        )
    elif strata:
        temporal_analysis_complete = (
            temporal_analysis_complete
            and coverage_status in _CLOSED_ENUMERATION_COVERAGE
            and all(chains_by_stratum.values())
            and all(record.get("comparability_approved") is True for record in chains.values())
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

    event_statuses = {finding["status"] for finding in event_findings}
    if conflicts:
        status = "measurement_unreliable"
    elif not chains:
        status = "insufficient_coverage"
    elif coverage_status not in _ANALYSABLE_COVERAGE:
        status = "insufficient_coverage"
    elif len(edition_counts) >= 2 and not all(
        record.get("comparability_approved") is True for record in chains.values()
    ):
        status = "needs_human_resolution"
    elif len(family_counts) >= 2 and separated_by("material_facts_group"):
        status = "fact_sensitive_divergence"
    elif len(family_counts) >= 2 and separated_by("court_code"):
        status = "circuit_divergence_candidate"
    elif "insufficient_temporal_evidence" in event_statuses:
        status = "insufficient_temporal_evidence"
    elif "mixed_post_event" in event_statuses:
        status = "mixed_post_event"
    elif "emergent_reading_candidate" in event_statuses:
        status = "emergent_reading_candidate"
    elif len(family_counts) >= 2:
        if temporal_separation():
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
        "reading_family_by_year": reading_family_by_year,
        "reading_family_by_stratum": reading_family_by_stratum,
        "interpretive_event_findings": event_findings,
        "temporal_unassigned_chain_ids": sorted(temporal_unassigned_chain_ids),
        "temporal_analysis_complete": temporal_analysis_complete,
        "denominator_scope": "approved_independent_coded_chains",
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
    if status in {
        None,
        "insufficient_coverage",
        "measurement_unreliable",
        "needs_human_resolution",
        "insufficient_temporal_evidence",
    }:
        return []
    temporal_event_ids = sorted(
        {
            str(finding["event_id"])
            for finding in analysis.get("interpretive_event_findings", [])
            if isinstance(finding, dict)
            and finding.get("status") in {"emergent_reading_candidate", "mixed_post_event"}
            and finding.get("event_id")
        }
    )
    if status in {"emergent_reading_candidate", "mixed_post_event"} and (
        analysis.get("temporal_analysis_complete") is not True or not temporal_event_ids
    ):
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
    if status == "emergent_reading_candidate":
        emergent_families = sorted(
            {
                str(family)
                for finding in analysis.get("interpretive_event_findings", [])
                if isinstance(finding, dict)
                for family in finding.get("emergent_families", [])
            }
        )
        observed_statement = (
            "В раскрытом и проверенном корпусе после указанного события впервые наблюдается "
            "семья чтения: "
            + ", ".join(emergent_families)
            + "; знаменатель ограничен одобренными независимыми цепочками дел."
        )
    elif status == "mixed_post_event":
        observed_statement = (
            "В раскрытом и проверенном корпусе после указанного события одновременно наблюдаются "
            "прежняя и новая семьи чтения; знаменатель ограничен одобренными независимыми цепочками дел."
        )
    else:
        observed_statement = (
            "В раскрытом и проверенном корпусе независимых цепочек дел выявлено "
            f"соотношение чтений со статусом {status}; вывод не выходит за раскрытый охват."
        )
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
            "interpretive_event_ids": temporal_event_ids,
            "observed_statement": observed_statement,
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
        "insufficient_temporal_evidence",
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
    if status in {"emergent_reading_candidate", "mixed_post_event"}:
        event_ids = candidate.get("interpretive_event_ids")
        if not isinstance(event_ids, list) or not event_ids:
            errors.append("Временной вывод не связан с проверенным интерпретационным событием.")
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
    if maximum_claim in {
        None,
        "",
        "insufficient_coverage",
        "measurement_unreliable",
        "needs_human_resolution",
        "insufficient_temporal_evidence",
    }:
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
