"""Deterministic, dependency-free reporting for a judicial-meaning workspace."""

from __future__ import annotations

import hashlib
import html
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit


SCHEMA_VERSION = "1.0"

_DISPLAY_LABELS = {
    "court": "суд",
    "supports": "поддерживает позицию заявителя",
    "adverse": "неблагоприятна для позиции заявителя",
    "neutral": "нейтральна",
    "distinguishes": "различима с делом заявителя",
    "matched": "сопоставимо",
    "distinguishable": "различимо",
    "uncertain": "не определено",
    "necessary_to_outcome": "необходимо для результата",
    "independent_sufficient_ground": "самостоятельное достаточное основание",
    "contextual": "контекстная позиция",
    "unclear": "неясно",
    "reviewed_supporting": "проверена как поддерживающая",
    "reviewed_adverse_bucket": "проверена в неблагоприятной корзине",
    "not_in_adverse_bucket": "не отнесена к неблагоприятной корзине",
    "unproven_research_question": "только незавершённый исследовательский вопрос",
    "corroborated_observed_corpus": "ограниченный вывод о подтверждённом наблюдаемом корпусе",
    "bounded_observed_corpus": "ограниченный вывод о наблюдаемом корпусе",
    "insufficient_coverage": "только вывод о недостаточном охвате",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def derive_research_status(state: Mapping[str, Any]) -> dict[str, Any]:
    """Derive one fail-closed, user-facing Russian status from gate state."""

    approval_exists = bool(
        state.get("approval_exists")
        or state.get("human_approved")
        or state.get("candidate_approved")
    )
    if approval_exists and state.get("approval_hashes_match") is not True:
        code = "approval_stale"
        label = "Одобрение устарело"
        blocker = "План или доказательства изменились после решения проверяющего."
        next_action = "Повторить проверку доказательств и получить новое одобрение."
    elif state.get("plan_frozen") is not True:
        code = "plan_not_frozen"
        label = "Исследовательский план не зафиксирован"
        blocker = "До сбора нужно проверить и заморозить нейтральный план."
        next_action = "Заполнить и заморозить исследовательский план."
    elif "case_fingerprint_ready" in state and state.get("case_fingerprint_ready") is not True:
        code = "case_fingerprint_incomplete"
        label = "Отпечаток дела заявителя не готов"
        blocker = "Не подтверждены исходозначимые факты, спорная норма или их источники."
        next_action = "Уточнить отмеченные факты дела и повторить case prepare."
    elif state.get("collection_complete") is not True:
        code = "collection_incomplete"
        label = "Сбор корпуса не завершён"
        blocker = "Остаются необработанные или недоступные сегменты официального источника."
        next_action = "Продолжить сбор корпуса или явно проверить пробелы охвата."
    elif state.get("coding_complete") is not True:
        code = "coding_incomplete"
        label = "Полнотекстовая проверка не завершена"
        blocker = "Не все найденные документы получили проверенное решение кодировщика."
        next_action = "Разрешить оставшиеся карточки полнотекстового кодирования."
    elif "comparison_review_complete" in state and state.get("comparison_review_complete") is not True:
        code = "comparison_review_incomplete"
        label = "Сопоставимость дел не проверена"
        blocker = "Нет текущей ручной проверки материальных различий с делом заявителя."
        next_action = "Проверить матрицу сопоставимости по каждому исходозначимому признаку."
    elif "applicant_relation_complete" in state and state.get("applicant_relation_complete") is not True:
        code = "applicant_relation_incomplete"
        label = "Отношение позиций к делу заявителя не проверено"
        blocker = "Позиции не классифицированы как поддерживающие, неблагоприятные или различимые на текущем отпечатке дела."
        next_action = "Провести ручную классификацию applicant-relative позиций."
    elif state.get("adverse_review_complete") is not True:
        code = "adverse_review_incomplete"
        label = "Неблагоприятная практика не проверена"
        blocker = "Отдельный поиск противоположных и более узких прочтений не завершён."
        next_action = "Завершить adverse-проверку и раскрыть её запросы."
    elif state.get("coverage_review_complete") is not True:
        code = "coverage_review_incomplete"
        label = "Охват корпуса не проверен"
        blocker = "Не подтверждены границы наблюдаемой совокупности и недоступные сегменты."
        next_action = "Проверить охват, знаменатели и недоступные сегменты."
    elif "normative_bridge_complete" in state and state.get("normative_bridge_complete") is not True:
        code = "normative_bridge_incomplete"
        label = "Конституционный мост не проверен"
        blocker = "Не связаны смысл нормы в деле, сопоставимый корпус и конкретное конституционное последствие."
        next_action = "Проверить нормативный мост и предел допустимого вывода."
    elif "analysis_complete" in state and state.get("analysis_complete") is not True:
        code = "analysis_incomplete"
        label = "Корпусный анализ не завершён"
        blocker = "Нет текущего анализа независимых цепочек и временных страт."
        next_action = "Пересчитать анализ на текущем корпусе и отпечатке дела."
    elif (
        "temporal_analysis_complete" in state
        and state.get("temporal_analysis_complete") is not True
    ):
        code = "temporal_analysis_incomplete"
        label = "Динамика позиций не рассчитана"
        blocker = "Нет текущего applicant-relative расчёта по зафиксированным временным стратам."
        next_action = "Запустить case dynamics и проверить знаменатели независимых цепочек."
    elif state.get("human_approved") is not True:
        code = "human_review_pending"
        label = "Ожидается решение проверяющего"
        blocker = "Итог исследования ещё не одобрен человеком."
        next_action = "Передать доказательственный отчёт на ручную проверку."
    elif state.get("candidate_approved") is not True:
        code = "candidate_review_pending"
        label = "Кандидат тезиса не одобрен"
        blocker = "Не проверены допустимая формулировка и нормативный мост."
        next_action = "Проверить кандидата тезиса и нормативный мост."
    elif state.get("approval_hashes_match") is not True:
        code = "approval_stale"
        label = "Одобрение устарело"
        blocker = "Хеши одобрения не совпадают с текущими доказательствами."
        next_action = "Повторить проверку доказательств и получить новое одобрение."
    elif "validation_current" in state and state.get("validation_current") is not True:
        code = "validation_incomplete"
        label = "Итоговая проверка не пройдена"
        blocker = "Нет успешного validation-report для текущего плана, отпечатка и доказательств."
        next_action = "Запустить validate и устранить перечисленные ошибки."
    else:
        code = "drafting_ready"
        label = "Результат готов к ограниченной передаче"
        blocker = ""
        next_action = "Проверить формулировку и создать целевой handoff."

    drafting_ready = code == "drafting_ready"
    return {
        "schema_version": SCHEMA_VERSION,
        "code": code,
        "label": label,
        "blockers": [blocker] if blocker else [],
        "next_action": next_action,
        "drafting_ready": drafting_ready,
        "pending_task_counts": dict(state.get("pending_task_counts", {}))
        if isinstance(state.get("pending_task_counts"), Mapping)
        else {},
        "stale_artifacts": list(state.get("stale_artifacts", []))
        if isinstance(state.get("stale_artifacts"), list)
        else [],
        "maximum_permitted_claim": state.get(
            "maximum_permitted_claim", "unproven_research_question"
        ),
    }


def _text(value: Any) -> str:
    if value is None:
        return "—"
    return html.escape(str(value), quote=True)


def _display_text(value: Any) -> str:
    if isinstance(value, str):
        return _text(_DISPLAY_LABELS.get(value, value))
    return _text(value)


def _count_summary(value: Any) -> str:
    if not isinstance(value, Mapping) or not value:
        return "нет наблюдений"
    return "; ".join(
        f"{_DISPLAY_LABELS.get(str(key), str(key))}: {count}"
        for key, count in sorted(value.items(), key=lambda item: str(item[0]))
    )


def _official_link(value: Any) -> str:
    if not isinstance(value, str):
        return "—"
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return _text(value)
    escaped = html.escape(value, quote=True)
    return f'<a href="{escaped}" rel="noreferrer noopener">Открыть официальный источник</a>'


def _render_list(items: Any, *, empty: str) -> str:
    values = list(items) if isinstance(items, (list, tuple)) else []
    if not values:
        return f"<p>{_text(empty)}</p>"
    return "<ul>" + "".join(f"<li>{_text(item)}</li>" for item in values) + "</ul>"


def _render_report(model: Mapping[str, Any], status: Mapping[str, Any]) -> str:
    gaps = sorted(
        [item for item in model.get("coverage_gaps", []) if isinstance(item, Mapping)],
        key=lambda item: (str(item.get("id", "")), str(item.get("label", ""))),
    )
    findings = sorted(
        [item for item in model.get("findings", []) if isinstance(item, Mapping)],
        key=lambda item: (str(item.get("id", "")), str(item.get("title", ""))),
    )
    safe_wording = model.get("safe_wording", {})
    if not isinstance(safe_wording, Mapping):
        safe_wording = {}

    gap_html = []
    for gap in gaps:
        gap_html.append(
            '<details class="gap" id="gap-{anchor}"><summary>{identifier}: {label}</summary>'
            "<p><strong>Причина:</strong> {reason}</p></details>".format(
                anchor=_text(gap.get("id")),
                identifier=_text(gap.get("id")),
                label=_text(gap.get("label")),
                reason=_text(gap.get("reason")),
            )
        )
    if not gap_html:
        gap_html.append("<p>Заявленные пробелы охвата отсутствуют.</p>")

    finding_html = []
    for finding in findings:
        chains = sorted(
            [item for item in finding.get("chains", []) if isinstance(item, Mapping)],
            key=lambda item: str(item.get("chain_id", "")),
        )
        chain_html = []
        for chain in chains:
            chain_html.append(
                """<article class="chain" id="chain-{chain_id}">
<h4>{chain_id}: {court}, {date}</h4>
<dl>
<dt>Номер дела</dt><dd>{case_number}</dd>
<dt>Источник</dt><dd>{official_url}</dd>
<dt>Документ</dt><dd>{document_id}; SHA-256 {document_sha256}</dd>
<dt>Автор позиции</dt><dd>{speaker}</dd>
<dt>Точная цитата</dt><dd><blockquote>{quote}</blockquote></dd>
<dt>Локатор</dt><dd>{quote_locator}</dd>
<dt>Роль</dt><dd>{relation}</dd>
<dt>Карточка позиции</dt><dd>{position_card_id}</dd>
<dt>Исходозначимость</dt><dd>{materiality}</dd>
<dt>Сопоставимость</dt><dd>{comparability}</dd>
<dt>Неблагоприятный статус</dt><dd>{adverse_status}</dd>
<dt>Исход</dt><dd>{outcome}</dd>
<dt>Средство защиты</dt><dd>{remedy}</dd>
</dl>
</article>""".format(
                    chain_id=_text(chain.get("chain_id")),
                    court=_text(chain.get("court")),
                    date=_text(chain.get("decision_date")),
                    case_number=_text(chain.get("case_number")),
                    official_url=_official_link(chain.get("official_url")),
                    document_id=_text(chain.get("document_id")),
                    document_sha256=_text(chain.get("document_sha256")),
                    speaker=_display_text(chain.get("speaker")),
                    quote=_text(chain.get("quote")),
                    quote_locator=_text(chain.get("quote_locator")),
                    relation=_display_text(chain.get("relation")),
                    position_card_id=_text(chain.get("position_card_id")),
                    materiality=_display_text(chain.get("materiality")),
                    comparability=_display_text(chain.get("comparability")),
                    adverse_status=_display_text(chain.get("adverse_status")),
                    outcome=_text(chain.get("outcome")),
                    remedy=_text(chain.get("remedy")),
                )
            )
        finding_html.append(
            """<details class="finding" id="finding-{identifier}">
<summary>{title}: {count}; Знаменатель: {denominator}</summary>
<p><strong>Область знаменателя:</strong> {scope}</p>
{chains}
</details>""".format(
                identifier=_text(finding.get("id")),
                title=_text(finding.get("title")),
                count=_text(finding.get("count")),
                denominator=_text(finding.get("denominator")),
                scope=_text(finding.get("denominator_scope")),
                chains="".join(chain_html) or "<p>Цепочки для раскрытия отсутствуют.</p>",
            )
        )
    if not finding_html:
        finding_html.append("<p>Одобренные доказательственные выводы отсутствуют.</p>")

    temporal = model.get("temporal_analysis", {})
    if not isinstance(temporal, Mapping):
        temporal = {}
    temporal_blocks: list[str] = []
    strata = temporal.get("by_stratum") or temporal.get("by_year") or {}
    if isinstance(strata, Mapping):
        for stratum_id, summary in sorted(strata.items(), key=lambda item: str(item[0])):
            if not isinstance(summary, Mapping):
                continue
            temporal_blocks.append(
                "<details class=\"temporal\"><summary>{stratum}: цепочек {chains}, карточек {cards}</summary>"
                "<p><strong>Семьи прочтений:</strong> {families}</p>"
                "<p><strong>Отношение к делу:</strong> {relations}</p></details>".format(
                    stratum=_text(stratum_id),
                    chains=_text(summary.get("independent_chain_count")),
                    cards=_text(summary.get("position_card_count")),
                    families=_text(_count_summary(summary.get("reading_family_chain_counts"))),
                    relations=_text(_count_summary(summary.get("relation_chain_counts"))),
                )
            )
    transitions = temporal.get("transitions", [])
    transition_lines = []
    if isinstance(transitions, list):
        for transition in transitions:
            if not isinstance(transition, Mapping):
                continue
            transition_lines.append(
                f"{transition.get('from_stratum')} → {transition.get('to_stratum')}: "
                f"{transition.get('status')}; причинный вывод не допускается"
            )
    temporal_html = "".join(temporal_blocks) or "<p>Проверенная временная динамика ещё не рассчитана.</p>"
    temporal_limit = temporal.get(
        "claim_limit",
        "Динамика является описанием раскрытого корпуса и не доказывает причинность или полноту практики.",
    )

    return """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
*, *::before, *::after {{ box-sizing: border-box; }}
html {{ overflow-wrap: anywhere; }}
body {{ max-width: 72rem; margin: 0 auto; padding: 1.5rem; line-height: 1.5; min-width: 0; }}
main, section, details, dl, dd {{ min-width: 0; max-width: 100%; }}
section {{ margin-block: 2rem; }}
details {{ border: 1px solid currentColor; border-radius: .5rem; padding: .75rem; margin-block: .75rem; overflow-wrap: anywhere; }}
summary {{ cursor: pointer; font-weight: 650; }}
.gap {{ border-inline-start: .4rem solid #b45309; }}
.status {{ padding: 1rem; background: color-mix(in srgb, CanvasText 7%, Canvas); border-radius: .75rem; }}
dt {{ font-weight: 650; }} dd {{ margin-block-end: .5rem; margin-inline-start: 0; word-break: break-word; }}
blockquote {{ margin-inline: 0; padding-inline-start: 1rem; border-inline-start: .25rem solid currentColor; }}
@media (max-width: 36rem) {{
  body {{ padding: 1rem; }}
  h1 {{ font-size: 1.65rem; }}
  details {{ padding: .65rem; }}
}}
</style>
</head>
<body>
<header><h1>{title}</h1><p>Запуск: {run_id}</p></header>
<main>
<section aria-labelledby="status-heading"><h2 id="status-heading">Состояние исследования</h2>
<div class="status"><h3>{status_label}</h3>{blockers}<p><strong>Следующее действие:</strong> {next_action}</p></div></section>
<section aria-labelledby="boundary-heading"><h2 id="boundary-heading">Предел вывода и незавершённые задачи</h2>
<p><strong>Максимально допустимый вывод:</strong> {maximum_claim}</p>
<h3>Ожидающие задачи</h3>{pending_counts}
<h3>Устаревшие артефакты</h3>{stale_artifacts}</section>
<section aria-labelledby="gaps-heading"><h2 id="gaps-heading">Пробелы охвата</h2>{gaps}</section>
<section aria-labelledby="findings-heading"><h2 id="findings-heading">Позиции и доказательства</h2>{findings}</section>
<section aria-labelledby="temporal-heading"><h2 id="temporal-heading">Динамика проверенных позиций</h2>
{temporal}<h3>Изменения между стратами</h3>{transitions}<p><strong>Предел:</strong> {temporal_limit}</p></section>
<section aria-labelledby="wording-heading"><h2 id="wording-heading">Допустимая формулировка</h2>
<h3>Можно утверждать</h3><p>{allowed}</p>
<h3>Нельзя утверждать без дополнительных оснований</h3>{forbidden}
<h3>Что делать дальше</h3>{next_steps}
</section>
<section aria-labelledby="trace-heading"><h2 id="trace-heading">Контрольные хеши</h2>
<dl><dt>План</dt><dd>{plan_sha256}</dd><dt>Отпечаток дела</dt><dd>{fingerprint_sha256}</dd><dt>Доказательства</dt><dd>{evidence_sha256}</dd></dl></section>
</main>
</body>
</html>
""".format(
        title=_text(model.get("title", "Исследование кассационной практики")),
        run_id=_text(model.get("run_id")),
        status_label=_text(status.get("label")),
        blockers=_render_list(status.get("blockers"), empty="Блокирующих обстоятельств нет."),
        next_action=_text(status.get("next_action")),
        maximum_claim=_display_text(status.get("maximum_permitted_claim")),
        pending_counts=_render_list(
            [f"{key}: {value}" for key, value in sorted(status.get("pending_task_counts", {}).items())],
            empty="Ожидающие задачи не зарегистрированы.",
        ),
        stale_artifacts=_render_list(
            status.get("stale_artifacts"),
            empty="Устаревшие артефакты не зарегистрированы.",
        ),
        gaps="".join(gap_html),
        findings="".join(finding_html),
        temporal=temporal_html,
        transitions=_render_list(
            transition_lines,
            empty="Сопоставимые соседние страты не рассчитаны.",
        ),
        temporal_limit=_text(temporal_limit),
        allowed=_text(safe_wording.get("allowed")),
        forbidden=_render_list(
            safe_wording.get("forbidden"),
            empty="Запрещённые формулировки не перечислены.",
        ),
        next_steps=_render_list(
            safe_wording.get("next_steps"),
            empty="Следующие действия не указаны.",
        ),
        plan_sha256=_text(model.get("plan_sha256")),
        fingerprint_sha256=_text(model.get("fingerprint_sha256")),
        evidence_sha256=_text(model.get("evidence_sha256")),
    )


def write_offline_report(
    model: Mapping[str, Any],
    html_path: str | Path,
    manifest_path: str | Path,
) -> dict[str, Any]:
    """Write deterministic escaped HTML and its content-bound manifest atomically."""

    html_target = Path(html_path)
    manifest_target = Path(manifest_path)
    status = derive_research_status(
        model.get("state", {}) if isinstance(model.get("state", {}), Mapping) else {}
    )
    rendered = _render_report(model, status)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": model.get("run_id"),
        "plan_sha256": model.get("plan_sha256"),
        "evidence_sha256": model.get("evidence_sha256"),
        "fingerprint_sha256": model.get("fingerprint_sha256"),
        "model_sha256": hashlib.sha256(_canonical_bytes(model)).hexdigest(),
        "html_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "offline": True,
        "external_runtime_dependencies": [],
        "status": status,
    }
    _atomic_write_text(html_target, rendered)
    _atomic_write_text(
        manifest_target,
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )
    return manifest
