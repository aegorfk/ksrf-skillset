"""Research-plan construction and immutable plan snapshots."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any


_REQUIRED_LANES = {
    "exact_norm",
    "synonyms",
    "mechanisms",
    "opposite_readings",
    "other_grounds",
    "later_authority",
}
_VALID_EDITION_STATUSES = {"verified"}
_VALID_UNITS = {"independent_case_chain"}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any, *, allow_empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(_nonempty_string(item) for item in value)
    )


def _valid_iso_date(value: Any, *, nullable: bool = False) -> bool:
    if value is None:
        return nullable
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _validate_temporal_plan(plan: dict[str, Any], population: Any) -> list[str]:
    """Validate optional, population-covering temporal strata and linked events."""

    errors: list[str] = []
    strata = plan.get("temporal_strata")
    events = plan.get("interpretive_events")
    if strata in (None, []):
        if events not in (None, []):
            errors.append("Интерпретационные события требуют временных страт.")
        return errors
    if not isinstance(strata, list) or len(strata) < 2:
        return ["Для временного сравнения нужны как минимум две страты."]

    parsed: list[tuple[date, date, str]] = []
    seen_ids: set[str] = set()
    strata_by_id: dict[str, tuple[date, date]] = {}
    for index, stratum in enumerate(strata, start=1):
        if not isinstance(stratum, dict):
            errors.append(f"Временная страта {index} должна быть объектом.")
            continue
        stratum_id = stratum.get("id")
        if not isinstance(stratum_id, str) or not stratum_id.strip() or stratum_id in seen_ids:
            errors.append(f"У временной страты {index} отсутствует уникальный id.")
            continue
        seen_ids.add(stratum_id)
        if not _nonempty_string(stratum.get("label")):
            errors.append(f"У временной страты {index} нет названия.")
        start_raw = stratum.get("date_from")
        end_raw = stratum.get("date_to")
        if (
            not isinstance(start_raw, str)
            or not isinstance(end_raw, str)
            or not _valid_iso_date(start_raw)
            or not _valid_iso_date(end_raw)
        ):
            errors.append(f"У временной страты {index} неверные даты ISO.")
            continue
        start = date.fromisoformat(start_raw)
        end = date.fromisoformat(end_raw)
        if start > end:
            errors.append(f"У временной страты {index} период задан в обратном порядке.")
            continue
        parsed.append((start, end, stratum_id))
        strata_by_id[stratum_id] = (start, end)

    if len(parsed) == len(strata):
        ordered = sorted(parsed)
        if isinstance(population, dict):
            population_start = population.get("date_from")
            population_end = population.get("date_to")
            if isinstance(population_start, str) and _valid_iso_date(population_start) and ordered[0][0] != date.fromisoformat(population_start):
                errors.append("Временные страты не начинаются вместе с исследуемой совокупностью.")
            if isinstance(population_end, str) and _valid_iso_date(population_end) and ordered[-1][1] != date.fromisoformat(population_end):
                errors.append("Временные страты не заканчиваются вместе с исследуемой совокупностью.")
        for previous, current in zip(ordered, ordered[1:]):
            if previous[1] + timedelta(days=1) != current[0]:
                errors.append("Временные страты должны идти подряд, без пробелов и пересечений.")
                break

    if events is None:
        events = []
    if not isinstance(events, list):
        return errors + ["Интерпретационные события должны быть списком."]

    seen_event_ids: set[str] = set()
    ordered_ids = [item[2] for item in sorted(parsed)]
    adjacent_pairs = set(zip(ordered_ids, ordered_ids[1:]))
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            errors.append(f"Интерпретационное событие {index} должно быть объектом.")
            continue
        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id.strip() or event_id in seen_event_ids:
            errors.append(f"У интерпретационного события {index} отсутствует уникальный id.")
        else:
            seen_event_ids.add(event_id)
        if not _nonempty_string(event.get("label")):
            errors.append(f"У интерпретационного события {index} нет названия.")
        source_url = event.get("official_source_url")
        if not isinstance(source_url, str) or not source_url.strip() or not source_url.startswith(("https://", "http://")):
            errors.append(f"У интерпретационного события {index} нет официальной ссылки.")
        before_id = event.get("before_stratum_id")
        after_id = event.get("after_stratum_id")
        if not isinstance(before_id, str) or not isinstance(after_id, str) or (before_id, after_id) not in adjacent_pairs:
            errors.append(f"Событие {index} должно связывать соседние временные страты.")
            continue
        effective_raw = event.get("effective_date")
        if not isinstance(effective_raw, str) or not _valid_iso_date(effective_raw):
            errors.append(f"У интерпретационного события {index} неверная дата.")
            continue
        effective = date.fromisoformat(effective_raw)
        before_dates = strata_by_id[before_id]
        after_dates = strata_by_id[after_id]
        if effective != after_dates[0] or before_dates[1] + timedelta(days=1) != effective:
            errors.append(f"Дата события {index} должна совпадать с началом следующей страты.")
    return errors


def make_research_question(assertion: str, norm_refs: list[str]) -> dict[str, Any]:
    """Convert a party's proposed assertion into a neutral hypothesis under test."""

    assertion = assertion.strip()
    refs = [ref.strip() for ref in norm_refs if _nonempty_string(ref)]
    seed = _canonical_json({"assertion": assertion, "norm_refs": refs})
    question_id = "rq-" + hashlib.sha256(seed).hexdigest()[:12]
    return {
        "id": question_id,
        "status": "hypothesis_under_test",
        "question": (
            "Подтверждается ли в заранее определённом корпусе следующее проверяемое предположение: "
            + assertion.rstrip(".?")
            + "?"
        ),
        "source_assertion": assertion,
        "norm_refs": refs,
        "supported": False,
    }


def validate_plan(plan: dict[str, Any]) -> list[str]:
    """Validate that a plan can bound the population before collection begins."""

    if not isinstance(plan, dict):
        return ["План должен быть JSON-объектом."]

    errors: list[str] = []
    if plan.get("schema_version") != "1.0":
        errors.append("Нужна поддерживаемая версия схемы плана 1.0.")
    if not _nonempty_string(plan.get("title")):
        errors.append("Укажите название исследования.")

    questions = plan.get("research_questions")
    if not isinstance(questions, list) or not questions:
        errors.append("Добавьте хотя бы один нейтральный исследовательский вопрос.")
    else:
        for index, question in enumerate(questions, start=1):
            if not isinstance(question, dict):
                errors.append(f"Исследовательский вопрос {index} должен быть объектом.")
                continue
            if not _nonempty_string(question.get("id")):
                errors.append(f"У исследовательского вопроса {index} нет id.")
            if question.get("status") not in {"research_question", "hypothesis_under_test"}:
                errors.append(f"Исследовательский вопрос {index} преждевременно объявлен выводом.")
            if not _nonempty_string(question.get("question")):
                errors.append(f"Исследовательский вопрос {index} не сформулирован.")
            if not _string_list(question.get("norm_refs")):
                errors.append(f"Для исследовательского вопроса {index} не указаны нормы.")
            if question.get("supported") is True:
                errors.append(f"Исследовательский вопрос {index} нельзя считать подтверждённым до корпуса.")

    editions = plan.get("norm_editions")
    if not isinstance(editions, list) or not editions:
        errors.append("До сбора нужно зафиксировать применимые редакции норм.")
    else:
        seen_edition_ids: set[str] = set()
        for index, edition in enumerate(editions, start=1):
            if not isinstance(edition, dict):
                errors.append(f"Описание редакции нормы {index} должно быть объектом.")
                continue
            edition_id = edition.get("id")
            if not _nonempty_string(edition_id) or edition_id in seen_edition_ids:
                errors.append(f"У редакции нормы {index} отсутствует уникальный id.")
            elif isinstance(edition_id, str):
                seen_edition_ids.add(edition_id)
            if not _nonempty_string(edition.get("norm_ref")):
                errors.append(f"У редакции нормы {index} нет краткой ссылки на норму.")
            if edition.get("edition_status") not in _VALID_EDITION_STATUSES:
                errors.append(f"редакция нормы {index} не проверена по официальному источнику.")
            if not _nonempty_string(edition.get("official_source_url")):
                errors.append(f"Для редакции нормы {index} не указан официальный источник.")
            if not _valid_iso_date(edition.get("valid_from")):
                errors.append(f"У редакции нормы {index} неверная дата начала действия.")
            if not _valid_iso_date(edition.get("valid_to"), nullable=True):
                errors.append(f"У редакции нормы {index} неверная дата окончания действия.")
            if _valid_iso_date(edition.get("valid_from")) and _valid_iso_date(
                edition.get("valid_to"), nullable=True
            ):
                valid_to = edition.get("valid_to")
                if valid_to is not None and valid_to < edition.get("valid_from"):
                    errors.append(f"У редакции нормы {index} период задан в обратном порядке.")

    population = plan.get("population")
    if not isinstance(population, dict):
        errors.append("Не определена исследуемая совокупность актов.")
    else:
        if population.get("unit") not in _VALID_UNITS:
            errors.append("Единица учёта должна быть независимой цепочкой дела.")
        start = population.get("date_from")
        end = population.get("date_to")
        if (
            not isinstance(start, str)
            or not isinstance(end, str)
            or not _valid_iso_date(start)
            or not _valid_iso_date(end)
        ):
            errors.append("Период совокупности должен быть задан датами ISO.")
        elif start > end:
            errors.append("Начало периода совокупности позже его окончания.")
        if not _string_list(population.get("courts")):
            errors.append("Укажите охватываемые кассационные суды.")
        if not _string_list(population.get("regimes")):
            errors.append("Укажите режимы источников и судебной системы.")
        if not _nonempty_string(population.get("official_population_rule")):
            errors.append("Зафиксируйте правило официальной совокупности.")

    errors.extend(_validate_temporal_plan(plan, population))

    lanes = plan.get("query_lanes")
    if not isinstance(lanes, dict):
        errors.append("Не определены независимые поисковые дорожки.")
    else:
        missing_lanes = sorted(_REQUIRED_LANES - set(lanes))
        if missing_lanes:
            errors.append("Не хватает поисковых дорожек: " + ", ".join(missing_lanes) + ".")
        for lane, queries in lanes.items():
            if lane not in _REQUIRED_LANES:
                errors.append(f"Неизвестная поисковая дорожка: {lane}.")
            elif not _string_list(queries, allow_empty=True):
                errors.append(f"Поисковая дорожка {lane} должна быть списком строк.")
        if not any(lanes.get(lane) for lane in _REQUIRED_LANES):
            errors.append("Все поисковые дорожки пусты.")

    for field, message in (
        ("inclusion_rules", "Зафиксируйте правила включения актов."),
        ("exclusion_rules", "Зафиксируйте правила исключения актов."),
    ):
        if not _string_list(plan.get(field)):
            errors.append(message)
    for field, message in (
        ("materiality_rule", "Зафиксируйте критерий исходозначимости."),
        ("contradiction_rule", "Зафиксируйте обработку различающихся фактов."),
        ("coverage_expectation", "Зафиксируйте ожидаемый уровень охвата."),
        ("maximum_claim_if_incomplete", "Зафиксируйте предел вывода при неполном охвате."),
    ):
        if not _nonempty_string(plan.get(field)):
            errors.append(message)

    adverse = plan.get("adverse_review")
    if not isinstance(adverse, dict) or adverse.get("required") is not True:
        errors.append("Независимый поиск неблагоприятной практики обязателен.")
    else:
        if not _string_list(adverse.get("queries")):
            errors.append("Для неблагоприятной практики нужны отдельные запросы.")
        if not _nonempty_string(adverse.get("no_hit_wording")):
            errors.append("Нужно заранее задать осторожную формулировку отсутствия находок.")

    if not _nonempty_string(plan.get("approved_by")):
        errors.append("Перед заморозкой план должен одобрить человек.")

    # Subject-neutrality is structural: plan data may mention the user's actual
    # subject, while no built-in branch or mandatory category is imposed here.
    return errors


def freeze_plan(plan: dict[str, Any], workspace: str | Path) -> dict[str, Any]:
    """Validate, hash, and persist a plan before any corpus collection."""

    errors = validate_plan(plan)
    if errors:
        raise ValueError("План нельзя заморозить:\n- " + "\n- ".join(errors))

    frozen = copy.deepcopy(plan)
    frozen.pop("frozen", None)
    frozen.pop("plan_sha256", None)
    digest = hashlib.sha256(_canonical_json(frozen)).hexdigest()
    frozen["frozen"] = True
    frozen["plan_sha256"] = digest

    plans_dir = Path(workspace) / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    existing_versions = []
    for existing in plans_dir.glob("plan-v*.json"):
        match = re.fullmatch(r"plan-v(\d+)\.json", existing.name)
        if match:
            existing_versions.append(int(match.group(1)))
    version = max(existing_versions, default=0) + 1
    destination = plans_dir / f"plan-v{version}.json"
    temporary = plans_dir / f".{destination.name}.tmp"
    temporary.write_text(
        json.dumps(frozen, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)

    workspace_path = Path(workspace)
    questions_path = workspace_path / "research-questions.jsonl"
    question_payload = "".join(
        json.dumps(
            {**question, "plan_sha256": digest},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
        for question in sorted(frozen["research_questions"], key=lambda item: item["id"])
    )
    questions_path.write_text(question_payload, encoding="utf-8", newline="\n")

    query_records: list[dict[str, Any]] = []
    accepted = frozen.get("accepted_query_suggestions", [])
    accepted_pairs: set[tuple[str, str]] = set()
    if isinstance(accepted, list):
        for decision in accepted:
            if not isinstance(decision, dict):
                continue
            suggestion = decision.get("suggestion")
            if not isinstance(suggestion, dict):
                continue
            query = suggestion.get("query")
            lane = suggestion.get("lane")
            if not isinstance(query, str) or not isinstance(lane, str):
                continue
            plan_lane = {
                "exact_norm": "exact_norm",
                "court_language": "synonyms",
                "legal_mechanism": "mechanisms",
                "controlled_synonym": "synonyms",
                "opposite_reading": "opposite_readings",
                "narrower_reading": "opposite_readings",
                "alternative_ground": "other_grounds",
                "later_legislation": "later_authority",
                "higher_authority": "later_authority",
                "case_feature": "synonyms",
            }.get(lane)
            if plan_lane is None:
                continue
            accepted_pairs.add((plan_lane, query))
            query_records.append(
                {
                    "query_id": suggestion.get("query_id"),
                    "lane": plan_lane,
                    "source_lane": lane,
                    "query": query,
                    "adverse": lane
                    in {
                        "opposite_reading",
                        "narrower_reading",
                        "alternative_ground",
                        "later_legislation",
                        "higher_authority",
                    },
                    "plan_relationship": "accepted_pre_freeze",
                    "provenance": suggestion.get("provenance"),
                    "reviewer": decision.get("reviewer"),
                    "confirmed_at": decision.get("confirmed_at"),
                    "plan_sha256": digest,
                }
            )
    for lane in sorted(frozen["query_lanes"]):
        for index, query in enumerate(frozen["query_lanes"][lane], start=1):
            if (lane, query) in accepted_pairs:
                continue
            query_records.append(
                {
                    "query_id": f"{lane}-{index}",
                    "lane": lane,
                    "query": query,
                    "adverse": False,
                    "plan_sha256": digest,
                }
            )
    for index, query in enumerate(frozen["adverse_review"]["queries"], start=1):
        query_records.append(
            {
                "query_id": f"adverse-{index}",
                "lane": "adverse",
                "query": query,
                "adverse": True,
                "plan_sha256": digest,
            }
        )
    queries_path = workspace_path / "queries.jsonl"
    queries_path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for record in query_records
        ),
        encoding="utf-8",
        newline="\n",
    )
    return frozen
