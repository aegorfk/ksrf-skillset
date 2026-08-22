---
name: ksrf-cassation-judicial-meaning
description: "Use when материалы дела заявителя нужно исследовать вместе с кассационной практикой до выбора тезиса для жалобы в КС РФ, особенно при спорном смысле нормы, конкурирующих толкованиях, предполагаемом расхождении, динамике или системной неопределённости."
---

# Исследование судебного смысла нормы

Этот скилл запускается **до** формулирования эмпирического тезиса о судебной практике. Он начинает с актов заявителя, строит нейтральный план проверки, собирает воспроизводимый корпус, ищет неблагоприятные материалы и только потом допускает кандидаты тезисов.

## Неподвижное правило

До завершения сбора, полнотекстового кодирования, adverse-pass и проверки охвата называй формулировки только `research_question` или `hypothesis_under_test`. Не ищи акты для подтверждения уже выбранной позиции и не пиши, что практика устойчива, хаотична, меняется или доказывает дефект нормы.

Практика может подтверждать придаваемый норме смысл и его последствия, но не становится самостоятельным предметом проверки КС РФ. Допустимость, применение нормы к заявителю, исчерпание, срок и средство защиты проверяются отдельно.

## Быстрый запуск

Требуется Python 3.10+; сторонние Python-пакеты, проект `ks_parser`, PostgreSQL, API-ключи и платные сервисы не нужны. Найди каталог этого скилла и используй его исполняемый файл из любого рабочего каталога:

```bash
python3 <skill-dir>/scripts/judicial_meaning.py intake \
  --workspace ./judicial-meaning-run \
  --inputs ./acts/

python3 <skill-dir>/scripts/judicial_meaning.py plan template \
  --workspace ./judicial-meaning-run
```

После проверки и заполнения `research-plan.json`:

```bash
python3 <skill-dir>/scripts/judicial_meaning.py plan freeze \
  --workspace ./judicial-meaning-run \
  --plan ./judicial-meaning-run/research-plan.json

python3 <skill-dir>/scripts/judicial_meaning.py collect \
  --workspace ./judicial-meaning-run --resume

python3 <skill-dir>/scripts/judicial_meaning.py screen \
  --workspace ./judicial-meaning-run

python3 <skill-dir>/scripts/judicial_meaning.py code \
  --workspace ./judicial-meaning-run
# Заполни coding-decisions.jsonl по полным текстам и проверь его:
python3 <skill-dir>/scripts/judicial_meaning.py code \
  --workspace ./judicial-meaning-run \
  --input ./judicial-meaning-run/coding-decisions.jsonl

# Первый analyze создаёт analysis.json и шаблон adverse-review.json,
# но не создаёт тезис до отдельной проверки adverse и coverage:
python3 <skill-dir>/scripts/judicial_meaning.py analyze \
  --workspace ./judicial-meaning-run

# Проверь exports/coverage.json, выполни все дорожки adverse-review.json,
# укажи completed=true, reviewer, результаты и ограничения:
python3 <skill-dir>/scripts/judicial_meaning.py review \
  --workspace ./judicial-meaning-run \
  --decision evidence_reviewed --reviewer "ФИО проверяющего" \
  --adverse-complete --coverage-complete \
  --adverse-file ./judicial-meaning-run/adverse-review.json

# Только теперь повторный analyze создаёт post-review thesis-candidates.jsonl:
python3 <skill-dir>/scripts/judicial_meaning.py analyze \
  --workspace ./judicial-meaning-run

# Проверь кандидата, заполни нормативный мост и human_review=approved:
python3 <skill-dir>/scripts/judicial_meaning.py review \
  --workspace ./judicial-meaning-run \
  --decision approved --reviewer "ФИО проверяющего" \
  --adverse-complete --coverage-complete \
  --adverse-file ./judicial-meaning-run/adverse-review.json \
  --thesis-file ./judicial-meaning-run/thesis-candidates.jsonl

python3 <skill-dir>/scripts/judicial_meaning.py validate \
  --workspace ./judicial-meaning-run --require-thesis-ready
```

Сбор может занять долгое время. Не держи весь корпус в контексте: работай через реестры, top-K очереди на ручное кодирование и checkpoint/resume.

Если акт заявителя — скан без текстового слоя, явно создай OCR-копию, затем визуально сверь каждую страницу и только после этого передай `.txt` в `intake`:

```bash
python3 <skill-dir>/scripts/judicial_meaning.py ocr \
  --input ./acts/scan.pdf \
  --output ./acts/scan.ocr.txt \
  --language rus
```

OCR требует локальные `pdftoppm` и `tesseract`; рядом создаётся provenance-файл `scan.ocr.txt.provenance.json` с хешами, версиями помощников и `human_verified=false`. Команда не подменяет ручную сверку.

## Рабочий цикл

1. **Зафиксируй вход.** Инвентаризируй акты заявителя, хеши, процессуальные стадии и отсутствующие материалы. Не приписывай суду довод стороны. Если PDF не извлечён, запиши `unextractable` и запроси текстовую копию или локальное OCR; не угадывай содержание.
2. **Поставь вопросы, а не тезисы.** Для каждой применённой или предположительно применённой нормы сформулируй: какой смысл придан в деле заявителя; какие иные смыслы возможны; при каких сопоставимых фактах каждый смысл влияет на исход.
3. **Заморозь Evidence Acquisition Plan.** Обязательно укажи точную норму и редакции, суды, институциональные режимы, период, единицу `independent_case_chain`, поисковые дорожки, inclusion/exclusion, materiality, adverse и contradiction rules, правило охвата и максимум допустимого вывода при пробелах.
4. **Собери официально наблюдаемый корпус.** Встроенный адаптер обходит официальные дневные выдачи девяти КСОЮ с 01.10.2019, сохраняет raw bytes, хеши, ссылки, ошибки, пустые страницы и признаки навигации в локальные SQLite/JSONL. Не обходи CAPTCHA и не превращай 403/429/5xx/защитную страницу в «ничего не найдено».
5. **Отбери кандидатов с высоким recall.** Используй все дорожки плана: точная норма, редакция, синоним, механизм без номера статьи, противоположное толкование, тот же исход по иному основанию, позднейший акт или изменение закона.
6. **Кодируй полный текст.** На каждую центральную позицию укажи speaker, точную цитату и локатор, редакцию нормы, материальные факты, связь мотива с исходом, альтернативные основания, результат, reading family, отношение к исходной гипотезе и цепочку дела. Сниппет или упоминание нормы недостаточны.
7. **Проведи adverse-pass.** Ищи противоположные и более узкие прочтения, фактические различия, процессуальные отказы, альтернативные основания, позднейший закон и более высокую инстанцию. Ноль найденных adverse-актов означает только ноль в раскрытом охвате.
8. **Оцени охват и сопоставимость.** Считай независимые цепочки дел, а не URL/PDF. Разделяй редакции нормы и дореформенный/послереформенный режимы. Показатель охвата относится к официально опубликованной наблюдаемой выдаче, не ко всем рассмотренным делам.
9. **Сформируй кандидаты тезисов только после evidence review.** Первый `analyze` фиксирует измерения и создаёт незаполненный adverse-шаблон. Лишь после `evidence_reviewed`, завершённых adverse/coverage review и повторного `analyze` появляются кандидаты со статусами `corroborated_observed_corpus`, `material_split_candidate`, `temporal_shift_candidate`, `circuit_divergence_candidate`, `fact_sensitive_divergence`, `implementation_gap`, `contradicted`, `insufficient_coverage`, `needs_human_resolution`.
10. **Передай в жалобу только после человека.** `drafting_ready` требует human approval, совпадения хеша плана и доказательств, завершённых adverse/coverage review и формулировки не сильнее `maximum_permitted_claim`.

Подробные поля и правила см. в [контракте артефактов](references/artifact-contracts.md), [источниках и режимах](references/source-regimes.md), [кодировании и стоп-правилах](references/coding-and-thesis-gates.md) и [устранении проблем](references/troubleshooting.md).

## Стоп-правила

- Нет полного текста центрального акта → не кодируй судебный смысл.
- Не установлена применимая редакция → не объединяй период и не допускай сильный тезис.
- Есть `blocked`, `terminal_error`, `pagination_unresolved`, `not_configured` или open denominator → ограничь вывод наблюдаемым корпусом.
- Не разрешён спор о merge/split цепочки → исключи её из сильных количественных выводов.
- Нет adverse-pass или ручного подтверждения → нет `drafting_ready`.
- Не выводи неконституционность из частоты, расхождения или числа актов без моста от неопределённого нормативного смысла к нарушенному конституционному праву и невозможности устранить дефект конституционно-сообразным толкованием.

## Необязательные стыковки

Скилл автономен. Если установлены другие KSRF skills, передавай только файловые envelopes версии `1.0`:

- `ksrf-complaint-cycle` → ссылки на акты заявителя и нейтральные вопросы; обратно — только post-corpus результат;
- `ksrf-explore-arguments` → гипотезы и disconfirmation prompts; обратно — supported/narrowed/contradicted/unresolved кандидаты;
- `ksrf-practice-authority-builder` → только отобранные официальные акты с хешем, цитатой, ролью, adverse-status и chain ID;
- `ksrf-complaint-qa` → approved run, максимальный допустимый вывод и ограничения.

Отсутствие или несовместимость соседнего скилла не ломает локальное исследование и не меняет его доказательства.

Если установлен полный KSRF bundle, применяй общие offline-роли источников и provenance из [offline-practice-core](../ksrf-complaint-cycle/references/offline-practice-core.md). Если соседний скилл отсутствует, эквивалентные обязательные правила уже полностью изложены в локальных references этого скилла; runtime к соседнему файлу не обращается.
