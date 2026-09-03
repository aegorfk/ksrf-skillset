# Маршрутизатор и машина состояний жалобы в КС РФ

## Назначение

Этот файл задаёт общий контракт. Специализированные skills выполняют узкие стадии; `ksrf-complaint-cycle` хранит состояние и не повторяет их методику.

## Начальное состояние

После установки только набора skills состояние равно `skills_only`. Сначала выполни:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-complaint-cycle/scripts/ksrf_setup_doctor.py" --profile basic --json
```

Doctor ничего не устанавливает, не показывает значения секретов, не передаёт документы внешним сервисам и не превращает отсутствие платного provider в юридический отказ.
Верхнее состояние `ready` или `degraded` возвращает код `0`, а `blocked` —
код `3` с полным отчётом в stdout. Ошибка параметров или манифеста возвращает
код `2`; ни один из этих результатов сам не запускает исправление.

## Стадии

1. `setup_checked` — выбран профиль, записан `CapabilityReport`.
2. `matter_initialized` — создан локальный matter workspace и privacy scope.
3. `record_incomplete` либо `record_ready_for_analysis` — документы зарегистрированы с origin/hash/role.
4. `official_sources_pending` либо `sources_verified` — filing-significant источники разрешены до официальных anchors.
5. `norm_versions_pending` либо `norm_versions_verified` — для каждой нормы собран `NormVersionPassport`.
6. `application_pending` либо `application_reviewed` — по каждой норме и стадии заполнены три оси применения.
7. `admissibility_blocked`, `fix_first`, `court_request_route` либо `issue_research` — юридический маршрут после hard gates.
8. `issue_options_ready` — создано от одного до четырёх доказуемых вариантов без автоматического выбора.
9. `human_issue_selected` — юрист выбрал principal/reserve и зафиксировал причину.
10. `draft_working` — создаётся текст с `SentenceEvidenceMap`.
11. `qa_blocked` либо `qa_passed` — независимая отказная проверка без скрытого outcome.
12. `release_blocked`, `ready_for_expert_review` либо `ready_for_human_signing_filing` — реальные DOCX/PDF и manifest.
13. `filed_by_human` — только пользователь или представитель вручную подтверждает внешнее событие.
14. `decision_execution` — отдельный post-decision контур.

## Fail-closed переходы

- `unknown`, `unavailable`, `record_missing`, `application_unclear` и stale evidence не переходят в `pass`.
- Недоступный официальный сайт означает access gap, не отсутствие акта.
- Норма, найденная regex, поиском, RAG или моделью, остаётся кандидатом до доказательства редакции и применения.
- Блокировка одного claim не стирает независимые факты, источники или гипотезы.
- Рабочий черновик допустим до закрытия gates, но не получает метку готовности к подаче.
- Положительный filing-significant переход требует ранее созданного host-attested approval точного полного объекта; raw reviewer/approved поля, обычный TTY и сохранённый JSONL без проверяемой attestation остаются диагностикой.

## Маршрутизация в узкие skills

- intake и hard gates → `ksrf-case-triage`;
- исчерпание и сохранение довода → `ksrf-exhaustion-planner`;
- живое дело и будущая применимость → `ksrf-court-request-motion`;
- варианты проблемы → `ksrf-explore-arguments`;
- кассационный судебный смысл → `ksrf-cassation-judicial-meaning`;
- официальные authority и adverse → `ksrf-practice-authority-builder`;
- факты, вопрос, просьба, evidence map → `ksrf-complaint-facts-demands`;
- правовые разделы → `ksrf-rights-argument-builder`;
- независимая проверка → `ksrf-complaint-qa`;
- реальный комплект → `ksrf-formal-filing-check`;
- последствия решения → `ksrf-decision-execution`.

## Обязательный пользовательский отчёт

На каждой стадии сообщи простыми словами:

- что найдено;
- чего не хватает;
- почему это влияет на жалобу;
- какой следующий ограниченный шаг возможен;
- где требуется решение юриста или самого заявителя.
