---
name: ksrf-cassation-judicial-meaning
description: "Скилл исследует материалы дела заявителя вместе с кассационной практикой до выбора тезиса для жалобы в КС РФ. Он применяется при спорном смысле нормы, конкурирующих толкованиях, предполагаемом расхождении, динамике или системной неопределённости и не подменяет доказательство применения нормы в индивидуальном деле."
---

# Исследование судебного смысла нормы

## Граница с применением в индивидуальном деле

Этот skill доказывает наблюдаемый судебный смысл в корпусе, но не статус применения к заявителю. На входе и выходе сохраняй `NormVersionPassport`; в handoff передавай authority/practice evidence, а per-stage `NormApplicationEvidence` формирует complaint cycle по полным актам заявителя. Повторяемость толкования, similarity и оставление акта без изменения не заменяют conjunctive implicit-application test из `../ksrf-complaint-cycle/references/implicit-application-gate.md`.

Этот скилл запускается **до** формулирования тезиса о кассационной практике. Он автономно работает на Python 3.10+ без проектной БД, API-ключей и платных сервисов: инвентаризирует акты заявителя, строит fingerprint дела, замораживает нейтральный поиск, ведёт публичный корпус и сравнивает полнотекстовые позиции. Его локально одобренный bounded result остаётся исследовательским handoff; в жалобу он входит только после центрального host-attested approval полного issue/practice/adverse binding.

## Неподвижное правило

До закрытия сбора, полнотекстового кодирования, сопоставимости, четырёх adverse-корзин, охвата и нормативного моста называй формулировку только `research_question` или `hypothesis_under_test`. Не ищи акты для подтверждения заранее выбранной позиции и не утверждай, что практика устойчива, хаотична, изменилась или доказывает неконституционность.

Практика может показывать смысл, придаваемый норме, и его последствия. Она не становится самостоятельным предметом проверки КС РФ. Допустимость, применение нормы к заявителю, исчерпание, срок и средство защиты проверяются отдельными KSRF-контурами.

## Обязательная последовательность

1. **Сначала intake.** Инвентаризируй акты заявителя и их хеши. Fingerprint по произвольному JSON без инвентаризированного документа запрещён.
2. **Затем fingerprint.** Зафиксируй нейтральный `issue`, точные `norm_refs` и признаки, включая обязательные `norm_edition`, `applicant_case_meaning`, `procedural_posture`. Проверенный документальный признак требует `document_id` и точного `quote_locator`; неизвестный материальный признак создаёт блокирующую задачу.
3. **Подтверди запросы до freeze.** `case prepare` создаёт только `suggested_unconfirmed`. Человек принимает нужные `query_id` через `query accept`; они входят в хеш плана. После freeze разрешён только раскрытый `post_freeze_supplemental`, который не меняет исходный знаменатель.
4. **Собери и закодируй корпус.** Сохраняй raw bytes, official URL, хеши, ошибки и незакрытые сегменты. Считай независимые цепочки дел, а не URL или PDF.
5. **Проверь каждую позицию применительно к делу.** Полная карточка позиции → ручное сравнение признаков → applicant-relative relation. Все карточки и все review-состояния остаются в реестрах; ни очередь, ни `uncertain`/`unresolved` не удаляют кандидата.
6. **Закрой четыре adverse-корзины.** Для каждой нужны выполненные query IDs, отсутствие неразрешённых сегментов и влияние пробела на `maximum_permitted_claim`.
7. **Проверь качество наблюдения.** По `references/practice-quality.md` отдельно построй межинстанционную траекторию смысла, девятимерный профиль неопределённости и frozen coding-reliability audit. Не считай оставление результата без изменения принятием мотивировки и не сворачивай измерения в score.
8. **Проверь нормативный мост и актуальность.** Свяжи смысл в деле заявителя, ограниченное наблюдение корпуса и конкретное конституционное последствие; отдельно объясни обычное средство защиты и выполни pre-filing refresh по явно заявленному coverage и полному treatment-quality-set текущего public cache.
9. **Только после проверки сформируй handoff.** Локальный compatibility-статус `drafting_ready` требует текущие хеши fingerprint/плана/evidence/quality/refresh, человеческую проверку и формулировку не сильнее `maximum_permitted_claim`, но означает лишь готовность evidence bundle к центральному gate. Reviewed v2 result строится CLI из текущих одобренных артефактов по selectors; произвольный findings payload запрещён. Получатель сначала выполняет `handoff check` с этим source workspace и ожидаемым target, затем требует pre-existing host-attested approval полного issue/practice/adverse binding. Bundle без внешнего anchor остаётся audit-only; filesystem anchor и SHA-256 не являются подписью или filing authority.
10. **Перед release свяжи exact practice-строку.** Для каждой строки жалобы отдельно сохрани constitutional `claim_id`, native `practice_claim_id`, selected `issue_option_id`, exact finding IDs, reviewed wording и byte-equal `maximum_permitted_claim`. Host заново проверяет current practice workspace, result, trust anchors, target-claim state, refresh, approvals `practice:<id>` и `selection`, а также независимый полный draft index — включая пустой. Правила и стоп-матрица: [привязка тезиса к filing](references/filing-evidence-binding.md).

Минимальный старт из любого каталога:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" intake \
  --workspace ./judicial-meaning-run \
  --inputs ./acts/

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" case prepare \
  --workspace ./judicial-meaning-run \
  --answers ./case-answers.json

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" plan template \
  --workspace ./judicial-meaning-run
```

Точные команды и форматы находятся в профильных разделах:

- [контур позиций применительно к делу](references/case-relative-workbench.md) — intake, fingerprint, query lifecycle, position card, compare, relation, adverse, bridge, status/report/handoff;
- [контракт артефактов](references/artifact-contracts.md) — файлы, идентификаторы, неизменяемые hash bindings и stale-инвалидация;
- [публичный корпусный кеш](references/public-corpus-cache.md) — privacy boundary, ingest/search, funnel, treatment, public-only export/import;
- [quality-слой практики](references/practice-quality.md) — coding audit, явный coverage, полный treatment-set, prefiling exit codes и регенерация старых v1-артефактов;
- [источники и институциональные режимы](references/source-regimes.md) — перечислители, source reconcile, verify/promote и честные пределы маршрутов;
- [кодирование и допуск тезиса](references/coding-and-thesis-gates.md) — роли текста и независимые gates;
- [привязка тезиса к filing](references/filing-evidence-binding.md) — exact line binding, current host authority, два issue approvals и complete draft index;
- [устранение проблем](references/troubleshooting.md) — OCR, blocked routes, resume, stale artifacts и незакрытые периоды.

## Стоп-правила

- Нет intake, полного текста центрального акта, точного speaker/цитаты/локатора или применимой редакции → нет доказанного судебного смысла.
- Есть `missing_task`, `pending_human_review`, `uncertain`, `unresolved`, stale hash binding или неразрешённая merge/split identity → нет сильного applicant-relative вывода.
- Есть `blocked`, `retryable_error`, `terminal_error`, `pagination_unresolved`, `contract_only_not_wired`, `not_configured` или open denominator → вывод ограничивается наблюдаемым корпусом.
- Ноль adverse-находок означает только ноль по раскрытым завершённым запросам.
- Частота, число решений, расхождение и временная последовательность сами по себе не доказывают неконституционность.
- Не передавай формулы «вся практика», «устойчиво», «судебный хаос», «закон не работает» или причинный «тренд», если именно такой уровень не разрешён текущим `maximum_permitted_claim` и нормативным мостом.

## Автономность и стыковки

Скилл не требует соседних skills. Общие офлайн-правила источников, доказательственных ролей и fail-closed вывода бери из `../ksrf-complaint-cycle/references/offline-practice-core.md`. При наличии соседних skills передавай только portable файловые envelopes версии `2.0`:

- `ksrf-complaint-cycle` → акты заявителя и нейтральные вопросы; обратно только post-corpus результат;
- `ksrf-explore-arguments` → гипотезы и disconfirmation prompts;
- `ksrf-practice-authority-builder` → проверенные `authority_cards` с official URL, хешем, цитатой, ролью, adverse-status и chain ID;
- `ksrf-complaint-qa` → approved run, `maximum_permitted_claim` и раскрытые ограничения.

Отсутствие или несовместимость соседнего скилла не меняет доказательства и не ослабляет локальные gates. Legacy v1 и `selected_authorities` допускаются только для аудита старого envelope и никогда не дают `drafting_ready`; новый handoff связывает исходный request и claim hashes, artifact-derived findings, `authority_cards`, selected proofs, normative bridge, human decision и validation report.
