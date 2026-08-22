"""Research-plan construction and immutable plan snapshots."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import date
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
        if not _valid_iso_date(start) or not _valid_iso_date(end):
            errors.append("Период совокупности должен быть задан датами ISO.")
        elif start > end:
            errors.append("Начало периода совокупности позже его окончания.")
        if not _string_list(population.get("courts")):
            errors.append("Укажите охватываемые кассационные суды.")
        if not _string_list(population.get("regimes")):
            errors.append("Укажите режимы источников и судебной системы.")
        if not _nonempty_string(population.get("official_population_rule")):
            errors.append("Зафиксируйте правило официальной совокупности.")

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
    for lane in sorted(frozen["query_lanes"]):
        for index, query in enumerate(frozen["query_lanes"][lane], start=1):
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
