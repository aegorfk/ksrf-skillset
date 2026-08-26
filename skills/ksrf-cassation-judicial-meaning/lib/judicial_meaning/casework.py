"""Pure, case-relative primitives for reviewing cassation positions.

The workbench is deliberately independent of the collector and persistence layer.
It turns reviewed inputs into deterministic, provenance-carrying artifacts and
fails closed when facts, materiality, comparability, or the normative bridge are
not established.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from typing import Any, Iterable, Mapping


ADVERSE_BUCKETS = (
    "opposite_reading",
    "narrower_reading",
    "alternative_ground",
    "later_authority",
)

_FEATURE_STATUSES = {"verified", "unknown", "disputed"}
_QUERY_LANES = (
    "exact_norm",
    "court_language",
    "legal_mechanism",
    "controlled_synonym",
    "opposite_reading",
    "narrower_reading",
    "alternative_ground",
    "later_legislation",
    "higher_authority",
)
_QUERY_LANE_ALIASES = {
    "exact_norm": "exact_norm",
    "exact_norms": "exact_norm",
    "court_language": "court_language",
    "legal_mechanism": "legal_mechanism",
    "legal_mechanisms": "legal_mechanism",
    "controlled_synonym": "controlled_synonym",
    "controlled_synonyms": "controlled_synonym",
    "opposite_reading": "opposite_reading",
    "opposite_readings": "opposite_reading",
    "narrower_reading": "narrower_reading",
    "narrower_readings": "narrower_reading",
    "alternative_ground": "alternative_ground",
    "alternative_grounds": "alternative_ground",
    "later_legislation": "later_legislation",
    "higher_authority": "higher_authority",
    "higher_authorities": "higher_authority",
}
_QUERY_REASON_CODES = {
    "exact_norm": "exact_norm_reference",
    "court_language": "court_language_search",
    "legal_mechanism": "legal_mechanism_search",
    "controlled_synonym": "controlled_synonym_search",
    "opposite_reading": "opposite_reading_adverse_search",
    "narrower_reading": "narrower_reading_adverse_search",
    "alternative_ground": "same_outcome_alternative_ground_search",
    "later_legislation": "later_legislation_search",
    "higher_authority": "higher_authority_search",
    "case_feature": "verified_case_feature_term",
}
_SOURCE_FIELDS = (
    "source_type",
    "document_id",
    "decision_id",
    "speaker",
    "quote",
    "quote_locator",
)
_OUTCOME_MATERIALITY = {
    "necessary_to_outcome",
    "independent_sufficient_ground",
    "contextual",
    "unclear",
}
_POSITION_REQUIRED_FIELDS = (
    "position_card_id",
    "chain_id",
    "document_id",
    "court_id",
    "decision_date",
    "official_url",
    "document_sha256",
    "speaker",
    "proposition",
    "quote",
    "quote_locator",
    "norm_edition_id",
    "material_facts",
    "comparison_features",
    "reasoning_to_outcome",
    "outcome_materiality",
    "alternative_grounds",
    "reading_family",
    "outcome",
    "remedy",
    "coder",
    "human_review",
)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _unique_strings(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not _nonempty(value):
            continue
        cleaned = " ".join(value.split())
        folded = cleaned.casefold()
        if folded not in seen:
            result.append(cleaned)
            seen.add(folded)
    return result


def _normalise_source(source: Any) -> dict[str, str] | None:
    """Preserve only explicit source facts; never fill missing attribution fields."""

    if not isinstance(source, Mapping):
        return None
    result: dict[str, str] = {}
    for field in _SOURCE_FIELDS:
        value = source.get(field)
        if _nonempty(value):
            result[field] = " ".join(value.split())
    source_type = result.get("source_type")
    if source_type is not None and source_type not in {"document", "user_decision"}:
        raise ValueError("source_type должен быть document или user_decision.")
    return result or None


def _normalise_value(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, list):
        return [_normalise_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _normalise_value(item) for key, item in value.items()}
    return value


def _source_supports_verified_feature(source: Mapping[str, Any] | None) -> bool:
    if not isinstance(source, Mapping):
        return False
    if source.get("source_type") == "user_decision":
        return _nonempty(source.get("decision_id"))
    return _nonempty(source.get("document_id")) and _nonempty(
        source.get("quote_locator")
    )


def _normalise_features(features: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalised: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(features, start=1):
        if not isinstance(raw, Mapping):
            raise ValueError(f"Признак {index} должен быть объектом.")
        feature_id = raw.get("feature_id")
        if not _nonempty(feature_id) or feature_id in seen_ids:
            raise ValueError(f"У признака {index} отсутствует уникальный feature_id.")
        feature_id = feature_id.strip()
        seen_ids.add(feature_id)
        status = raw.get("status")
        if status not in _FEATURE_STATUSES:
            raise ValueError(f"У признака {feature_id} неизвестный статус.")
        source_payload = _normalise_source(raw.get("source"))
        if status == "verified":
            value = raw.get("value")
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(
                    f"Проверенный признак {feature_id} требует непустого значения."
                )
            if not _source_supports_verified_feature(source_payload):
                raise ValueError(
                    f"Проверенный признак {feature_id} требует document_id и quote_locator "
                    "либо явное решение пользователя с decision_id."
                )
        query_terms = raw.get("query_terms", [])
        if not isinstance(query_terms, list):
            raise ValueError(f"query_terms признака {feature_id} должен быть списком.")
        normalised.append(
            {
                "feature_id": feature_id,
                "value": _normalise_value(raw.get("value")),
                "status": status,
                "confirmation_state": status,
                "material": raw.get("material") is True,
                "source": source_payload,
                "query_terms": _unique_strings(query_terms),
            }
        )
    return sorted(normalised, key=lambda item: item["feature_id"])


def _default_query(lane: str, issue: str, norm_ref: str) -> str:
    """Build discovery prompts only from stated issue/norm, without new case facts."""

    stem = f"{norm_ref} {issue}"
    suffixes = {
        "court_language": "формулировка суда",
        "legal_mechanism": "правовой механизм",
        "controlled_synonym": "синоним правовой категории",
        "opposite_reading": "противоположное толкование",
        "narrower_reading": "узкое толкование",
        "alternative_ground": "тот же результат иное основание",
        "later_legislation": "последующая редакция изменение законодательства",
        "higher_authority": "позиция Конституционного Суда Верховного Суда",
    }
    return f"{stem} {suffixes[lane]}"


def _normalise_query_axes(
    query_axes: Mapping[str, Iterable[Any]] | None,
) -> dict[str, list[Any]]:
    if query_axes is None:
        return {}
    if not isinstance(query_axes, Mapping):
        raise ValueError("query_axes должен быть объектом с именованными направлениями.")
    result: dict[str, list[Any]] = {}
    for raw_lane, raw_entries in query_axes.items():
        lane = _QUERY_LANE_ALIASES.get(raw_lane)
        if lane is None:
            raise ValueError(f"Неизвестное направление query_axes: {raw_lane}.")
        if isinstance(raw_entries, (str, Mapping)):
            entries = [raw_entries]
        elif isinstance(raw_entries, Iterable):
            entries = list(raw_entries)
        else:
            raise ValueError(f"query_axes.{raw_lane} должен быть списком.")
        result.setdefault(lane, []).extend(entries)
    return result


def _query_suggestion(
    *,
    lane: str,
    query: str,
    fingerprint_sha256: str,
    revision: int,
    derived_from: Iterable[str],
    source_feature_ids: Iterable[str],
    norm_refs: Iterable[str],
    source_records: Iterable[Mapping[str, Any]] = (),
    reason_code: str | None = None,
) -> dict[str, Any]:
    provenance = {
        "fingerprint_sha256": fingerprint_sha256,
        "fingerprint_revision": revision,
        "derived_from": _unique_strings(derived_from),
        "source_feature_ids": _unique_strings(source_feature_ids),
        "norm_refs": _unique_strings(norm_refs),
        "source_records": [dict(item) for item in source_records],
    }
    payload = {
        "lane": lane,
        "query": " ".join(query.split()),
        "reason_code": reason_code or _QUERY_REASON_CODES[lane],
        "confirmation_state": "suggested_unconfirmed",
        "plan_relationship": "pre_freeze_candidate",
        "provenance": provenance,
    }
    return {"query_id": "query-" + _digest(payload)[:16], **payload}


def prepare_casework(
    *,
    issue: str,
    norm_refs: Iterable[str],
    features: Iterable[Mapping[str, Any]],
    previous_fingerprint: Mapping[str, Any] | None = None,
    query_axes: Mapping[str, Iterable[Any]] | None = None,
    allowed_document_ids: Iterable[str] | None = None,
    document_text_by_id: Mapping[str, str] | None = None,
    required_feature_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Prepare a deterministic fingerprint and provenance-linked query seeds."""

    if not _nonempty(issue):
        raise ValueError("Юридический вопрос не указан.")
    cleaned_norm_refs = _unique_strings(norm_refs)
    if not cleaned_norm_refs:
        raise ValueError("Не указана точная спорная норма.")
    normalised_features = _normalise_features(features)
    if not normalised_features:
        raise ValueError("Fingerprint должен содержать хотя бы один признак.")
    if allowed_document_ids is not None:
        allowed = {
            item.strip()
            for item in allowed_document_ids
            if isinstance(item, str) and item.strip()
        }
        text_by_id = dict(document_text_by_id or {})
        for feature in normalised_features:
            if feature["status"] != "verified":
                continue
            source = feature.get("source")
            if not isinstance(source, Mapping) or source.get("source_type") == "user_decision":
                continue
            document_id = source.get("document_id")
            if document_id not in allowed:
                raise ValueError(
                    f"Источник признака {feature['feature_id']} не найден среди "
                    "инвентаризированных актов заявителя."
                )
            document_text = text_by_id.get(str(document_id), "")
            if not _nonempty(document_text):
                raise ValueError(
                    f"Для акта {document_id} нет извлечённого текста; проверенный "
                    f"признак {feature['feature_id']} пока недопустим."
                )
            quote = source.get("quote")
            if _nonempty(quote) and " ".join(quote.split()).casefold() not in " ".join(
                document_text.split()
            ).casefold():
                raise ValueError(
                    f"Цитата источника признака {feature['feature_id']} не найдена "
                    "в инвентаризированном тексте акта."
                )

    payload = {
        "schema_version": "1.0",
        "issue": " ".join(issue.split()),
        "norm_refs": cleaned_norm_refs,
        "features": normalised_features,
    }
    fingerprint_sha256 = _digest(payload)
    previous_sha = (
        previous_fingerprint.get("fingerprint_sha256")
        if isinstance(previous_fingerprint, Mapping)
        else None
    )
    previous_revision = (
        previous_fingerprint.get("revision", 0)
        if isinstance(previous_fingerprint, Mapping)
        else 0
    )
    if previous_sha == fingerprint_sha256 and isinstance(previous_revision, int):
        revision = max(previous_revision, 1)
    else:
        revision = max(previous_revision, 0) + 1 if isinstance(previous_revision, int) else 1
    fingerprint = {
        **payload,
        "revision": revision,
        "fingerprint_sha256": fingerprint_sha256,
    }
    for feature in fingerprint["features"]:
        feature["revision"] = revision
    fingerprint_changed = bool(previous_sha) and previous_sha != fingerprint_sha256
    missing_tasks = [
        {
            "task_id": "missing-" + _digest(
                {
                    "fingerprint_sha256": fingerprint_sha256,
                    "feature_id": feature["feature_id"],
                }
            )[:16],
            "task_type": "feature_confirmation",
            "feature_id": feature["feature_id"],
            "lane": None,
            "status": feature["status"],
            "reason_code": "feature_not_verified",
            "action": "Установить значение по материалам дела заявителя и добавить точный локатор.",
            "blocks_comparability": feature["material"] is True,
            "source": feature["source"],
        }
        for feature in normalised_features
        if feature["status"] != "verified"
    ]
    existing_feature_ids = {feature["feature_id"] for feature in normalised_features}
    for required_feature_id in sorted(
        {
            item.strip()
            for item in required_feature_ids
            if isinstance(item, str) and item.strip()
        }
        - existing_feature_ids
    ):
        missing_tasks.append(
            {
                "task_id": "missing-" + _digest(
                    {
                        "fingerprint_sha256": fingerprint_sha256,
                        "feature_id": required_feature_id,
                    }
                )[:16],
                "task_type": "required_case_field",
                "feature_id": required_feature_id,
                "lane": None,
                "status": "unknown",
                "reason_code": "required_case_field_absent",
                "action": "Установить обязательное поле по акту заявителя и подтвердить точным источником.",
                "blocks_comparability": True,
                "source": None,
            }
        )

    suggestions: list[dict[str, Any]] = []
    for norm_ref in cleaned_norm_refs:
        suggestions.append(
            _query_suggestion(
                lane="exact_norm",
                query=norm_ref,
                fingerprint_sha256=fingerprint_sha256,
                revision=revision,
                derived_from=[f"norm_ref:{norm_ref}"],
                source_feature_ids=[],
                norm_refs=[norm_ref],
            )
        )

    normalised_axes = _normalise_query_axes(query_axes)
    for lane in _QUERY_LANES:
        usable_entries = 1 if lane == "exact_norm" else 0
        for index, entry in enumerate(normalised_axes.get(lane, []), start=1):
            if isinstance(entry, str):
                query = " ".join(entry.split())
                status = "suggested"
                source = None
                reason_code = None
            elif isinstance(entry, Mapping):
                query = entry.get("query", entry.get("value"))
                status = entry.get("status", "suggested")
                source = _normalise_source(entry.get("source"))
                reason_code = entry.get("reason_code")
            else:
                query = None
                status = "unknown"
                source = None
                reason_code = None
            if status in {"unknown", "disputed"} or not _nonempty(query):
                task_seed = {
                    "fingerprint_sha256": fingerprint_sha256,
                    "lane": lane,
                    "entry_index": index,
                    "status": status,
                }
                missing_tasks.append(
                    {
                        "task_id": "missing-" + _digest(task_seed)[:16],
                        "task_type": "query_axis_confirmation",
                        "feature_id": None,
                        "lane": lane,
                        "status": status if status in _FEATURE_STATUSES else "unknown",
                        "reason_code": "query_axis_not_confirmed",
                        "action": "Уточнить формулировку направления поиска и подтвердить её источник до заморозки плана.",
                        "blocks_comparability": False,
                        "source": source,
                    }
                )
                continue
            if status not in {"suggested", "verified"}:
                raise ValueError(
                    f"Неизвестный статус query_axes.{lane}: {status}."
                )
            usable_entries += 1
            suggestions.append(
                _query_suggestion(
                    lane=lane,
                    query=query,
                    fingerprint_sha256=fingerprint_sha256,
                    revision=revision,
                    derived_from=[f"query_axis:{lane}:{index}"],
                    source_feature_ids=[],
                    norm_refs=cleaned_norm_refs,
                    source_records=[source] if source is not None else [],
                    reason_code=(
                        reason_code.strip() if _nonempty(reason_code) else None
                    ),
                )
            )
        if usable_entries == 0:
            norm_ref = cleaned_norm_refs[0]
            suggestions.append(
                _query_suggestion(
                    lane=lane,
                    query=_default_query(lane, payload["issue"], norm_ref),
                    fingerprint_sha256=fingerprint_sha256,
                    revision=revision,
                    derived_from=["issue", f"norm_ref:{norm_ref}", f"lane:{lane}"],
                    source_feature_ids=[],
                    norm_refs=[norm_ref],
                )
            )

    for feature in normalised_features:
        if feature["status"] != "verified":
            continue
        for query_term in feature["query_terms"]:
            suggestions.append(
                _query_suggestion(
                    lane="case_feature",
                    query=query_term,
                    fingerprint_sha256=fingerprint_sha256,
                    revision=revision,
                    derived_from=[f"feature:{feature['feature_id']}"],
                    source_feature_ids=[feature["feature_id"]],
                    norm_refs=cleaned_norm_refs,
                    source_records=(
                        [feature["source"]] if feature["source"] is not None else []
                    ),
                )
            )
    return {
        "schema_version": "1.0",
        "fingerprint": fingerprint,
        "query_suggestions": suggestions,
        "missing_tasks": missing_tasks,
        "dependency_state": {
            "applicant_relative_evidence_stale": fingerprint_changed,
            "superseded_fingerprint_sha256": previous_sha if fingerprint_changed else None,
            "current_fingerprint_sha256": fingerprint_sha256,
        },
    }


def validate_position_card(card: Mapping[str, Any]) -> list[str]:
    """Validate attribution, full-text support, and reasoning materiality."""

    if not isinstance(card, Mapping):
        return ["Карточка позиции должна быть объектом."]
    errors: list[str] = []
    missing = [
        field
        for field in _POSITION_REQUIRED_FIELDS
        if field not in card
        or card.get(field) is None
        or (field != "alternative_grounds" and not card.get(field))
    ]
    if missing:
        errors.append("Не заполнены обязательные поля: " + ", ".join(missing) + ".")
    if card.get("quote_verified") is not True:
        errors.append("Цитата не сверена с полным текстом акта.")
    if card.get("full_text_reviewed") is not True:
        errors.append("Полный текст акта не проверен.")
    if not isinstance(card.get("official_url"), str) or not card["official_url"].startswith(
        ("https://", "http://")
    ):
        errors.append("Не указана публичная официальная ссылка на акт.")
    if not isinstance(card.get("document_sha256"), str) or re.fullmatch(
        r"[0-9a-f]{64}", card["document_sha256"]
    ) is None:
        errors.append("document_sha256 должен быть SHA-256 полного текста.")
    try:
        date.fromisoformat(str(card.get("decision_date")))
    except ValueError:
        errors.append("decision_date должна быть датой ISO.")
    material_facts = card.get("material_facts")
    if not isinstance(material_facts, list) or not material_facts or not all(
        _nonempty(item) for item in material_facts
    ):
        errors.append("Нужно перечислить проверенные материальные факты позиции.")
    comparison_features = card.get("comparison_features")
    if not isinstance(comparison_features, list) or not comparison_features:
        errors.append("Нужны структурированные признаки сопоставимости позиции.")
    else:
        try:
            indexed_features = _features_by_id(
                comparison_features, "сопоставляемого дела"
            )
        except ValueError as exc:
            errors.append(str(exc))
        else:
            for feature_id, feature in indexed_features.items():
                if feature.get("status") != "verified" or feature.get("value") is None:
                    errors.append(
                        f"Признак сопоставимости {feature_id} не подтверждён."
                    )
                    continue
                source = feature.get("source")
                if not isinstance(source, Mapping) or source.get(
                    "document_id"
                ) != card.get("document_id") or not _nonempty(
                    source.get("quote_locator") if isinstance(source, Mapping) else None
                ):
                    errors.append(
                        f"Признак сопоставимости {feature_id} не связан локатором "
                        "с полным текстом карточки."
                    )
    materiality = card.get("outcome_materiality")
    if materiality not in _OUTCOME_MATERIALITY:
        errors.append("Неизвестна роль позиции в исходе дела.")
    if materiality == "necessary_to_outcome" and card.get("speaker") != "court":
        errors.append("Необходимый для исхода мотив должен быть принят судом.")
    alternative_grounds = card.get("alternative_grounds")
    if not isinstance(alternative_grounds, list):
        errors.append("Самостоятельные альтернативные основания должны быть списком.")
    else:
        independently_sufficient = any(
            isinstance(ground, Mapping) and ground.get("independently_sufficient") is True
            for ground in alternative_grounds
        )
        if materiality == "necessary_to_outcome" and independently_sufficient:
            errors.append(
                "Позиция не может быть необходимой для исхода при наличии самостоятельного достаточного основания."
            )
        if materiality == "independent_sufficient_ground" and not independently_sufficient:
            errors.append(
                "Для independent_sufficient_ground нужно указать самостоятельное достаточное основание."
            )
    if not _nonempty(card.get("reasoning_to_outcome")):
        errors.append("Не объяснена связь позиции с исходом дела.")
    if card.get("human_review") != "approved":
        errors.append("Карточка позиции не одобрена человеком.")
    return errors


def _features_by_id(features: Iterable[Mapping[str, Any]], role: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(features, start=1):
        if not isinstance(raw, Mapping) or not _nonempty(raw.get("feature_id")):
            raise ValueError(f"Признак {role} {index} не имеет feature_id.")
        feature_id = raw["feature_id"].strip()
        if feature_id in indexed:
            raise ValueError(f"Повторяющийся feature_id {feature_id} в признаках {role}.")
        indexed[feature_id] = dict(raw)
    return indexed


def compare_case_features(
    applicant_features: Iterable[Mapping[str, Any]],
    candidate_features: Iterable[Mapping[str, Any]],
    *,
    reviewer: str | None = None,
    reviewed_at: str | None = None,
    fingerprint_sha256: str | None = None,
) -> dict[str, Any]:
    """Compare material features and explain every match, difference, or unknown."""

    applicant = _features_by_id(applicant_features, "заявителя")
    candidate = _features_by_id(candidate_features, "сопоставляемого дела")
    material_ids = sorted(
        feature_id
        for feature_id, feature in applicant.items()
        if feature.get("material") is True
    )
    comparisons: list[dict[str, Any]] = []
    matched_ids: list[str] = []
    different_ids: list[str] = []
    unknown_ids: list[str] = []
    for feature_id in material_ids:
        left = applicant[feature_id]
        right = candidate.get(feature_id)
        if (
            left.get("status") != "verified"
            or left.get("value") is None
            or right is None
            or right.get("status") != "verified"
            or right.get("value") is None
        ):
            comparison_status = "unknown"
            unknown_ids.append(feature_id)
        elif _canonical_json(left.get("value")) == _canonical_json(right.get("value")):
            comparison_status = "matched"
            matched_ids.append(feature_id)
        else:
            comparison_status = "different"
            different_ids.append(feature_id)
        comparisons.append(
            {
                "feature_id": feature_id,
                "applicant_value": left.get("value"),
                "candidate_value": right.get("value") if right else None,
                "status": comparison_status,
            }
        )
    if not material_ids:
        overall = "uncertain"
        limitation = "В fingerprint не отмечены материальные признаки."
    elif different_ids:
        overall = "distinguishable"
        limitation = None
    elif unknown_ids:
        overall = "uncertain"
        limitation = "Не все материальные признаки установлены по обоим делам."
    else:
        overall = "matched"
        limitation = None
    reviewer_present = _nonempty(reviewer)
    reviewed_at_present = _nonempty(reviewed_at)
    if reviewer_present != reviewed_at_present:
        raise ValueError("Для review provenance одновременно нужны reviewer и reviewed_at.")
    review_provenance = {
        "status": "approved" if reviewer_present and reviewed_at_present else "pending_human_review",
        "reviewer": reviewer.strip() if reviewer_present else None,
        "reviewed_at": reviewed_at.strip() if reviewed_at_present else None,
    }
    return {
        "status": overall,
        "comparisons": comparisons,
        "matched_feature_ids": matched_ids,
        "different_feature_ids": different_ids,
        "unknown_feature_ids": unknown_ids,
        "limitation": limitation,
        "fingerprint_sha256": fingerprint_sha256,
        "review_provenance": review_provenance,
    }


def classify_applicant_relation(
    position_card: Mapping[str, Any],
    comparison: Mapping[str, Any],
    applicant_position: Mapping[str, Any],
    *,
    current_fingerprint_sha256: str | None = None,
) -> dict[str, Any]:
    """Classify a generic reading only after case-relative comparability."""

    comparison_fingerprint = comparison.get("fingerprint_sha256")
    if not _nonempty(current_fingerprint_sha256) or not _nonempty(
        comparison_fingerprint
    ):
        return {
            "relation": "unresolved",
            "stale": True,
            "reason": "Сопоставление не связано с текущим fingerprint дела заявителя.",
        }
    if (
        current_fingerprint_sha256 != comparison_fingerprint
    ):
        return {
            "relation": "unresolved",
            "stale": True,
            "reason": "Fingerprint дела заявителя изменён; сопоставимость и отношение позиции нужно проверить заново.",
        }
    review_provenance = comparison.get("review_provenance")
    if not isinstance(review_provenance, Mapping) or review_provenance.get(
        "status"
    ) != "approved":
        return {
            "relation": "unresolved",
            "stale": False,
            "reason": "Матрица сопоставимости не одобрена человеком.",
        }
    if applicant_position.get("human_review") != "approved":
        return {
            "relation": "unresolved",
            "stale": False,
            "reason": "Классификация поддерживающих и неблагоприятных чтений заявителя не одобрена человеком.",
        }
    if (
        position_card.get("human_review") != "approved"
        or position_card.get("speaker") != "court"
        or position_card.get("quote_verified") is not True
        or position_card.get("full_text_reviewed") is not True
    ):
        return {
            "relation": "unresolved",
            "stale": False,
            "reason": "Позиция не подтверждена как проверенное высказывание суда по полному тексту.",
        }
    comparison_status = comparison.get("status")
    if comparison_status == "distinguishable":
        different = sorted(str(item) for item in comparison.get("different_feature_ids", []))
        return {
            "relation": "distinguishes",
            "stale": False,
            "reason": "Дело различается по материальным признакам: " + ", ".join(different) + ".",
        }
    if comparison_status != "matched":
        unknown = sorted(str(item) for item in comparison.get("unknown_feature_ids", []))
        suffix = ": " + ", ".join(unknown) if unknown else ""
        return {
            "relation": "unresolved",
            "stale": False,
            "reason": "Сопоставимость дел не установлена" + suffix + ".",
        }
    materiality = position_card.get("outcome_materiality")
    if materiality != "necessary_to_outcome":
        return {
            "relation": "neutral",
            "stale": False,
            "reason": (
                "Позиция сопоставима, но её роль в исходе — "
                f"{materiality}; она сохранена как граница и не считается прямой "
                "поддержкой или неблагоприятным чтением."
            ),
        }
    reading_family = position_card.get("reading_family")
    if not _nonempty(reading_family):
        return {"relation": "unresolved", "stale": False, "reason": "Reading family позиции не установлена."}
    supportive = set(_unique_strings(applicant_position.get("supportive_reading_families", [])))
    adverse = set(_unique_strings(applicant_position.get("adverse_reading_families", [])))
    if reading_family in supportive and reading_family in adverse:
        return {
            "relation": "unresolved",
            "stale": False,
            "reason": f"Reading family {reading_family} одновременно отмечена как supportive и adverse.",
        }
    if reading_family in supportive:
        return {
            "relation": "supports",
            "stale": False,
            "reason": f"Сопоставимое дело принимает поддерживающее заявителя чтение {reading_family}.",
        }
    if reading_family in adverse:
        return {
            "relation": "adverse",
            "stale": False,
            "reason": f"Сопоставимое дело принимает неблагоприятное заявителю чтение {reading_family}.",
        }
    return {
        "relation": "neutral",
        "stale": False,
        "reason": f"Reading family {reading_family} не отнесена к supportive или adverse.",
    }


def build_explainable_queue(
    candidates: Iterable[Mapping[str, Any]],
    resolutions: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    quotas: Mapping[str, Mapping[str, int]] | None = None,
) -> dict[str, Any]:
    """Return one explained queue item for every screening candidate."""

    candidate_list = list(candidates)
    resolution_map = dict(resolutions or {})
    candidate_ids: list[str] = []
    seen: set[str] = set()
    for index, candidate in enumerate(candidate_list, start=1):
        candidate_id = candidate.get("candidate_id") if isinstance(candidate, Mapping) else None
        if not _nonempty(candidate_id) or candidate_id in seen:
            raise ValueError(f"У кандидата {index} отсутствует уникальный candidate_id.")
        candidate_id = candidate_id.strip()
        candidate_ids.append(candidate_id)
        seen.add(candidate_id)
    orphan_resolutions = sorted(set(resolution_map) - seen)
    if orphan_resolutions:
        raise ValueError("Решения ссылаются на неизвестных кандидатов: " + ", ".join(orphan_resolutions) + ".")

    quota_dimensions = ("court_id", "stratum_id", "lane")
    quota_config: dict[str, dict[str, int]] = {}
    for dimension, raw_limits in dict(quotas or {}).items():
        if dimension not in quota_dimensions or not isinstance(raw_limits, Mapping):
            raise ValueError(f"Неизвестная или неверная квота: {dimension}.")
        limits: dict[str, int] = {}
        for value, limit in raw_limits.items():
            if not _nonempty(value) or not isinstance(limit, int) or limit < 0:
                raise ValueError(f"Квота {dimension} должна содержать неотрицательные целые лимиты.")
            limits[str(value)] = limit
        quota_config[dimension] = limits
    quota_counts: dict[str, dict[str, int]] = {
        dimension: {value: 0 for value in limits}
        for dimension, limits in quota_config.items()
    }

    items: list[dict[str, Any]] = []
    unresolved: list[str] = []
    priority_candidate_ids: list[str] = []
    for candidate, candidate_id in zip(candidate_list, candidate_ids):
        resolution = resolution_map.get(candidate_id)
        base = {
            "candidate_id": candidate_id,
            "chain_id": candidate.get("chain_id"),
            "document_id": candidate.get("document_id"),
            "court_id": candidate.get("court_id"),
            "stratum_id": candidate.get("stratum_id"),
            "lane": candidate.get("lane"),
        }
        if not isinstance(resolution, Mapping):
            item = {
                **base,
                "status": "pending_review",
                "explanation": "Кандидат ожидает полнотекстовой проверки.",
                "reason_codes": ["pending_full_text_review"],
            }
            unresolved.append(candidate_id)
        elif resolution.get("decision") == "position_card" and _nonempty(
            resolution.get("position_card_id")
        ) and _nonempty(resolution.get("reason")):
            item = {
                **base,
                "status": "coded_position",
                "position_card_id": resolution["position_card_id"].strip(),
                "explanation": resolution["reason"].strip(),
                "reason_codes": ["full_text_position_coded"],
            }
        elif resolution.get("decision") == "exclude" and _nonempty(
            resolution.get("reason")
        ) and resolution.get("human_review") == "approved":
            item = {
                **base,
                "status": "reviewed_exclusion",
                "explanation": resolution["reason"].strip(),
                "reason_codes": ["human_reviewed_exclusion"],
            }
        else:
            item = {
                **base,
                "status": "pending_review",
                "explanation": "Предложенное решение не прошло проверку и требует ручного разрешения.",
                "reason_codes": ["invalid_resolution_pending_review"],
            }
            unresolved.append(candidate_id)
        if not quota_config:
            selected = True
        else:
            eligible_slots = []
            for dimension, limits in quota_config.items():
                value = candidate.get(dimension)
                if value in limits and quota_counts[dimension][value] < limits[value]:
                    eligible_slots.append((dimension, value))
            selected = bool(eligible_slots)
            if selected:
                for dimension, value in eligible_slots:
                    quota_counts[dimension][value] += 1
        item["priority_review"] = selected
        if selected:
            item["reason_codes"].append("quota_priority" if quota_config else "no_quota_filter")
            priority_candidate_ids.append(candidate_id)
        else:
            item["reason_codes"].append("quota_not_selected")
        items.append(item)
    return {
        "input_count": len(candidate_list),
        "output_count": len(items),
        "items": items,
        "unresolved_candidate_ids": unresolved,
        "priority_candidate_ids": priority_candidate_ids,
        "quota_counts": quota_counts,
        "all_candidates_preserved": len(candidate_list) == len(items),
    }


def analyze_case_relative_dynamics(
    position_cards: Iterable[Mapping[str, Any]],
    comparisons: Mapping[str, Mapping[str, Any]],
    applicant_relations: Mapping[str, Mapping[str, Any]],
    *,
    fingerprint_sha256: str,
    temporal_strata: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Describe reviewed change over time without inferring causation or completeness."""

    cards = list(position_cards)
    strata = [dict(item) for item in temporal_strata if isinstance(item, Mapping)]
    unresolved: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    for index, card in enumerate(cards, start=1):
        card_id = str(card.get("position_card_id", "")) if isinstance(card, Mapping) else ""
        errors = validate_position_card(card)
        comparison = comparisons.get(card_id)
        relation = applicant_relations.get(card_id)
        if errors:
            unresolved.append(
                {
                    "position_card_id": card_id or f"row-{index}",
                    "reason": "invalid_position_card",
                    "details": errors,
                }
            )
            continue
        if not isinstance(comparison, Mapping) or (
            comparison.get("fingerprint_sha256") != fingerprint_sha256
            or comparison.get("status") not in {"matched", "distinguishable"}
            or not isinstance(comparison.get("review_provenance"), Mapping)
            or comparison["review_provenance"].get("status") != "approved"
        ):
            unresolved.append(
                {
                    "position_card_id": card_id,
                    "reason": "comparison_not_current_and_reviewed",
                    "details": [],
                }
            )
            continue
        if not isinstance(relation, Mapping) or (
            relation.get("fingerprint_sha256") != fingerprint_sha256
            or relation.get("relation")
            not in {"supports", "adverse", "neutral", "distinguishes"}
            or relation.get("human_review") != "approved"
            or relation.get("stale") is True
        ):
            unresolved.append(
                {
                    "position_card_id": card_id,
                    "reason": "applicant_relation_not_current_and_reviewed",
                    "details": [],
                }
            )
            continue
        decision_day = date.fromisoformat(str(card["decision_date"]))
        stratum_id: str | None = None
        for stratum in strata:
            try:
                start = date.fromisoformat(str(stratum.get("date_from")))
                end = date.fromisoformat(str(stratum.get("date_to")))
            except ValueError:
                continue
            if start <= decision_day <= end:
                stratum_id = str(stratum.get("id"))
                break
        if not strata:
            stratum_id = f"year-{decision_day.year}"
        observations.append(
            {
                "position_card_id": card_id,
                "chain_id": str(card.get("chain_id")),
                "court_id": str(card.get("court_id")),
                "decision_date": decision_day.isoformat(),
                "year": str(decision_day.year),
                "stratum_id": stratum_id,
                "reading_family": str(card.get("reading_family")),
                "relation": str(relation.get("relation")),
                "materiality": str(card.get("outcome_materiality")),
                "comparability": str(comparison.get("status")),
            }
        )

    def aggregate(items: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        material = list(items)
        chains = {str(item["chain_id"]) for item in material}

        def counts(field: str) -> dict[str, int]:
            result: dict[str, set[str]] = {}
            for item in material:
                result.setdefault(str(item[field]), set()).add(str(item["chain_id"]))
            return {key: len(value) for key, value in sorted(result.items())}

        return {
            "position_card_count": len(material),
            "independent_chain_count": len(chains),
            "reading_family_chain_counts": counts("reading_family"),
            "relation_chain_counts": counts("relation"),
            "court_chain_counts": counts("court_id"),
            "materiality_chain_counts": counts("materiality"),
            "comparability_chain_counts": counts("comparability"),
        }

    by_year = {
        year: aggregate(item for item in observations if item["year"] == year)
        for year in sorted({str(item["year"]) for item in observations})
    }
    by_stratum = {
        stratum_id: aggregate(
            item for item in observations if item.get("stratum_id") == stratum_id
        )
        for stratum_id in sorted(
            {
                str(item["stratum_id"])
                for item in observations
                if item.get("stratum_id") is not None
            }
        )
    }
    ordered_strata = [
        str(item.get("id")) for item in strata if str(item.get("id")) in by_stratum
    ] or sorted(by_stratum)
    transitions: list[dict[str, Any]] = []
    for before, after in zip(ordered_strata, ordered_strata[1:]):
        left = by_stratum[before]
        right = by_stratum[after]
        sufficient = (
            left["independent_chain_count"] > 0
            and right["independent_chain_count"] > 0
        )
        changed = (
            left["reading_family_chain_counts"]
            != right["reading_family_chain_counts"]
        )
        transitions.append(
            {
                "from_stratum": before,
                "to_stratum": after,
                "status": (
                    "descriptive_distribution_changed"
                    if sufficient and changed
                    else "no_descriptive_change_observed"
                    if sufficient
                    else "insufficient_observation"
                ),
                "causal_claim_permitted": False,
            }
        )
    unassigned = sorted(
        item["position_card_id"]
        for item in observations
        if item.get("stratum_id") is None
    )
    return {
        "schema_version": "1.0",
        "fingerprint_sha256": fingerprint_sha256,
        "unit": "independent_case_chain",
        "position_card_count": len(observations),
        "independent_chain_count": len(
            {str(item["chain_id"]) for item in observations}
        ),
        "by_year": by_year,
        "by_stratum": by_stratum,
        "transitions": transitions,
        "unresolved_position_cards": unresolved,
        "unassigned_position_card_ids": unassigned,
        "temporal_analysis_complete": bool(observations)
        and not unresolved
        and not unassigned,
        "claim_limit": (
            "Изменение распределения в раскрытом корпусе является описанием наблюдений; "
            "оно не доказывает причинность, полноту практики или неконституционность."
        ),
    }


def build_adverse_review(
    position_cards: Iterable[Mapping[str, Any]],
    *,
    completed_buckets: Iterable[str],
    executed_query_ids_by_bucket: Mapping[str, Iterable[str]] | None = None,
    unresolved_segments_by_bucket: Mapping[str, Iterable[str]] | None = None,
    maximum_claim_effect_by_bucket: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Group adverse material into four mandatory, independently completed buckets."""

    completed = set(_unique_strings(completed_buckets))
    unknown_completed = sorted(completed - set(ADVERSE_BUCKETS))
    if unknown_completed:
        raise ValueError("Неизвестные adverse buckets: " + ", ".join(unknown_completed) + ".")
    grouped: dict[str, set[str]] = {bucket: set() for bucket in ADVERSE_BUCKETS}
    for index, card in enumerate(position_cards, start=1):
        if not isinstance(card, Mapping) or not _nonempty(card.get("position_card_id")):
            raise ValueError(f"У adverse-карточки {index} отсутствует position_card_id.")
        card_errors = validate_position_card(card)
        if card_errors:
            raise ValueError(
                f"Adverse-карточка {card.get('position_card_id')} не прошла "
                "полнотекстовую проверку: " + " ".join(card_errors)
            )
        buckets = card.get("adverse_buckets", [])
        if not isinstance(buckets, list):
            raise ValueError(f"adverse_buckets карточки {index} должен быть списком.")
        unknown = sorted(set(buckets) - set(ADVERSE_BUCKETS))
        if unknown:
            raise ValueError("Неизвестные adverse buckets: " + ", ".join(unknown) + ".")
        for bucket in buckets:
            grouped[bucket].add(card["position_card_id"].strip())
    bucket_payload = {
        bucket: sorted(grouped[bucket])
        for bucket in ADVERSE_BUCKETS
    }
    query_map = dict(executed_query_ids_by_bucket or {})
    unresolved_map = dict(unresolved_segments_by_bucket or {})
    effect_map = dict(maximum_claim_effect_by_bucket or {})
    bucket_reviews: dict[str, dict[str, Any]] = {}
    effective_completed: set[str] = set()
    for bucket in ADVERSE_BUCKETS:
        query_ids = _unique_strings(query_map.get(bucket, []))
        unresolved_segments = _unique_strings(unresolved_map.get(bucket, []))
        effect = effect_map.get(bucket)
        effect = " ".join(effect.split()) if _nonempty(effect) else None
        complete = (
            bucket in completed
            and bool(query_ids)
            and not unresolved_segments
            and effect is not None
        )
        if complete:
            effective_completed.add(bucket)
        bucket_reviews[bucket] = {
            "executed_query_ids": query_ids,
            "reviewed_position_card_ids": bucket_payload[bucket],
            "unresolved_source_segments": unresolved_segments,
            "maximum_claim_effect": effect,
            "completed": complete,
        }
    missing = [bucket for bucket in ADVERSE_BUCKETS if bucket not in effective_completed]
    no_hits = [
        bucket
        for bucket in ADVERSE_BUCKETS
        if bucket in effective_completed and not bucket_payload[bucket]
    ]
    return {
        "buckets": bucket_payload,
        "bucket_reviews": bucket_reviews,
        "completed_buckets": [
            bucket for bucket in ADVERSE_BUCKETS if bucket in effective_completed
        ],
        "missing_buckets": missing,
        "no_hit_buckets": no_hits,
        "completed": not missing,
        "no_hit_wording": (
            "В раскрытом наблюдаемом корпусе по завершённым дорожкам находки не обнаружены; "
            "отсутствие противоположной практики не доказано."
        ),
    }


def validate_normative_bridge(
    bridge: Mapping[str, Any],
    *,
    current_fingerprint_sha256: str | None = None,
    maximum_permitted_claim: str | None = None,
    position_cards: Mapping[str, Mapping[str, Any]] | None = None,
    comparisons: Mapping[str, Mapping[str, Any]] | None = None,
    applicant_relations: Mapping[str, Mapping[str, Any]] | None = None,
    adverse_review: Mapping[str, Any] | None = None,
) -> list[str]:
    """Validate the three-link bridge and the ordinary-remedy analysis."""

    if not isinstance(bridge, Mapping):
        return ["Нормативный мост должен быть объектом."]
    errors: list[str] = []
    required_strings = (
        ("norm_ref", "Не указана точная спорная норма."),
        ("applicant_case_meaning", "Не установлен исходозначимый смысл нормы в деле заявителя."),
        ("corpus_observation", "Не сформулирован ограниченный вывод из сопоставимого корпуса."),
        ("constitutional_consequence", "Не указано конкретное последствие для конституционного права."),
        ("ordinary_remedy_analysis", "Не объяснено, устраним ли предполагаемый дефект обычным средством защиты."),
        ("fingerprint_sha256", "Нормативный мост не связан с fingerprint дела заявителя."),
        ("maximum_permitted_claim", "Не указан максимальный допустимый вывод."),
        ("claim_wording", "Не указана проверяемая ограниченная формулировка вывода."),
        ("reviewer", "Не указан проверяющий нормативного моста."),
        ("reviewed_at", "Не указано время проверки нормативного моста."),
    )
    for field, message in required_strings:
        if not _nonempty(bridge.get(field)):
            errors.append(message)
    supporting = bridge.get("supporting_position_card_ids")
    adverse = bridge.get("adverse_position_card_ids")
    if not isinstance(supporting, list) or not supporting or not all(_nonempty(item) for item in supporting):
        errors.append("Нормативный мост не связан с поддерживающими position cards.")
    if not isinstance(adverse, list) or not all(_nonempty(item) for item in adverse):
        errors.append("adverse_position_card_ids должен быть явно заданным списком.")
    if bridge.get("human_review") != "approved":
        errors.append("Нормативный мост не одобрен человеком.")
    fingerprint = bridge.get("fingerprint_sha256")
    if not isinstance(fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
        errors.append("fingerprint_sha256 нормативного моста должен быть SHA-256.")
    if (
        _nonempty(current_fingerprint_sha256)
        and fingerprint != current_fingerprint_sha256
    ):
        errors.append("Нормативный мост устарел после изменения fingerprint дела.")
    if (
        _nonempty(maximum_permitted_claim)
        and bridge.get("maximum_permitted_claim") != maximum_permitted_claim
    ):
        errors.append(
            "maximum_permitted_claim нормативного моста не совпадает с текущим пределом вывода."
        )
    if isinstance(adverse_review, Mapping) and adverse_review.get("completed") is not True:
        errors.append("Нормативный мост нельзя одобрить до завершения adverse workbench.")

    card_map = dict(position_cards or {})
    comparison_map = dict(comparisons or {})
    relation_map = dict(applicant_relations or {})
    if position_cards is not None or comparisons is not None or applicant_relations is not None:
        for card_id in list(supporting or []):
            card = card_map.get(str(card_id))
            comparison = comparison_map.get(str(card_id))
            relation = relation_map.get(str(card_id))
            if not isinstance(card, Mapping) or (
                card.get("speaker") != "court"
                or card.get("quote_verified") is not True
                or card.get("full_text_reviewed") is not True
                or card.get("outcome_materiality") != "necessary_to_outcome"
                or card.get("human_review") != "approved"
            ):
                errors.append(
                    f"Поддерживающая карточка {card_id} не подтверждает необходимую для исхода позицию суда."
                )
            if not isinstance(comparison, Mapping) or (
                comparison.get("status") != "matched"
                or comparison.get("fingerprint_sha256") != current_fingerprint_sha256
                or not isinstance(comparison.get("review_provenance"), Mapping)
                or comparison["review_provenance"].get("status") != "approved"
            ):
                errors.append(f"Поддерживающая карточка {card_id} не имеет текущего одобренного matched-сравнения.")
            if not isinstance(relation, Mapping) or (
                relation.get("relation") != "supports"
                or relation.get("stale") is True
                or relation.get("human_review") != "approved"
            ):
                errors.append(f"Поддерживающая карточка {card_id} не имеет одобренного applicant-relative отношения supports.")
        for card_id in list(adverse or []):
            card = card_map.get(str(card_id))
            comparison = comparison_map.get(str(card_id))
            relation = relation_map.get(str(card_id))
            if not isinstance(card, Mapping) or card.get("human_review") != "approved":
                errors.append(f"Неблагоприятная карточка {card_id} не прошла ручную проверку.")
            if not isinstance(comparison, Mapping) or comparison.get("status") != "matched":
                errors.append(f"Неблагоприятная карточка {card_id} не имеет matched-сравнения.")
            if not isinstance(relation, Mapping) or relation.get("relation") != "adverse":
                errors.append(f"Неблагоприятная карточка {card_id} не подтверждена как adverse.")

    observation = bridge.get("corpus_observation")
    if isinstance(observation, str) and re.search(
        r"(?:частот\w*|числ\w*|расхожд\w*).*доказыва\w*.*неконституцион",
        observation,
        re.IGNORECASE,
    ):
        errors.append(
            "Корпусная частота не доказывает неконституционность нормы; число и расхождение решений также недостаточны сами по себе."
        )
    wording = bridge.get("claim_wording")
    if isinstance(wording, str) and re.search(
        r"(?:вся|полная|единообразн|закон\s+(?:в\s+целом\s+)?не\s+работает|доказыва\w*\s+неконституцион)",
        wording,
        re.IGNORECASE,
    ):
        errors.append(
            "Формулировка превышает раскрываемый корпус или превращает наблюдение в доказательство неконституционности."
        )
    return errors
