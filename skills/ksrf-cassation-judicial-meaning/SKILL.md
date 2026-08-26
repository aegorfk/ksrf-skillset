---
name: ksrf-cassation-judicial-meaning
description: "Use when материалы дела заявителя нужно исследовать вместе с кассационной практикой до выбора тезиса для жалобы в КС РФ, особенно при спорном смысле нормы, конкурирующих толкованиях, предполагаемом расхождении, динамике или системной неопределённости."
---

# Исследование судебного смысла нормы

Этот скилл запускается **до** формулирования тезиса о кассационной практике. Он автономно работает на Python 3.10+ без проектной БД, API-ключей и платных сервисов: инвентаризирует акты заявителя, строит fingerprint дела, замораживает нейтральный поиск, ведёт публичный корпус, сравнивает полнотекстовые позиции и допускает в жалобу только ограниченный вывод, одобренный человеком.

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
7. **Проверь нормативный мост.** Свяжи смысл в деле заявителя, ограниченное наблюдение корпуса и конкретное конституционное последствие; отдельно объясни обычное средство защиты.
8. **Только после проверки сформируй handoff.** `drafting_ready` требует текущие хеши fingerprint/плана/evidence, человеческое одобрение и формулировку не сильнее `maximum_permitted_claim`.

Минимальный старт из любого каталога:

```bash
python3 <skill-dir>/scripts/judicial_meaning.py intake \
  --workspace ./judicial-meaning-run \
  --inputs ./acts/

python3 <skill-dir>/scripts/judicial_meaning.py case prepare \
  --workspace ./judicial-meaning-run \
  --answers ./case-answers.json

python3 <skill-dir>/scripts/judicial_meaning.py plan template \
  --workspace ./judicial-meaning-run
```

Точные команды и форматы находятся в профильных разделах:

- [контур позиций применительно к делу](references/case-relative-workbench.md) — intake, fingerprint, query lifecycle, position card, compare, relation, adverse, bridge, status/report/handoff;
- [контракт артефактов](references/artifact-contracts.md) — файлы, идентификаторы, неизменяемые hash bindings и stale-инвалидация;
- [публичный корпусный кеш](references/public-corpus-cache.md) — privacy boundary, ingest/search, funnel, treatment, public-only export/import;
- [источники и институциональные режимы](references/source-regimes.md) — перечислители, source reconcile, verify/promote и честные пределы маршрутов;
- [кодирование и допуск тезиса](references/coding-and-thesis-gates.md) — роли текста и независимые gates;
- [устранение проблем](references/troubleshooting.md) — OCR, blocked routes, resume, stale artifacts и незакрытые периоды.

## Стоп-правила

- Нет intake, полного текста центрального акта, точного speaker/цитаты/локатора или применимой редакции → нет доказанного судебного смысла.
- Есть `missing_task`, `pending_human_review`, `uncertain`, `unresolved`, stale hash binding или неразрешённая merge/split identity → нет сильного applicant-relative вывода.
- Есть `blocked`, `retryable_error`, `terminal_error`, `pagination_unresolved`, `contract_only_not_wired`, `not_configured` или open denominator → вывод ограничивается наблюдаемым корпусом.
- Ноль adverse-находок означает только ноль по раскрытым завершённым запросам.
- Частота, число решений, расхождение и временная последовательность сами по себе не доказывают неконституционность.
- Не передавай формулы «вся практика», «устойчиво», «судебный хаос», «закон не работает» или причинный «тренд», если именно такой уровень не разрешён текущим `maximum_permitted_claim` и нормативным мостом.

## Автономность и стыковки

Скилл не требует соседних skills. При их наличии передавай только файловые envelopes версии `1.0`:

- `ksrf-complaint-cycle` → акты заявителя и нейтральные вопросы; обратно только post-corpus результат;
- `ksrf-explore-arguments` → гипотезы и disconfirmation prompts;
- `ksrf-practice-authority-builder` → проверенные `authority_cards` с official URL, хешем, цитатой, ролью, adverse-status и chain ID;
- `ksrf-complaint-qa` → approved run, `maximum_permitted_claim` и раскрытые ограничения.

Отсутствие или несовместимость соседнего скилла не меняет доказательства и не ослабляет локальные gates. Legacy `selected_authorities` допускается только для проверки старого envelope; новый handoff использует `authority_cards`.
