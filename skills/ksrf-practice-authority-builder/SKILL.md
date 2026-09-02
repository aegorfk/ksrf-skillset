---
name: ksrf-practice-authority-builder
description: Скилл official-first находит, проверяет и органично встраивает практику КС РФ, ВС РФ и ВАС РФ в аргументацию жалобы в Конституционный Суд РФ; CasusLegal используется лишь как необязательный discovery-канал. Он применяется для проверки гипотезы, судебного смысла нормы, adverse/refusal-позиций, authority ledger, drafting blocks и аудита цитат.
---

# Проверяемая опора на практику для жалобы в КС РФ

## Official-first provider contract

Следуй `../ksrf-complaint-cycle/references/official-source-and-version-gate.md`: authority class не равна acquisition transport. Casus Legal, Firecrawl и иные providers генерируют кандидатов; ключевой тезис проходит только после official full-text resolution, raw/extracted hashes, locator, edition check и adverse pass. Недоступность подписки снижает coverage, но не basic capability и не доказывает отсутствие позиции.

Локальные `human-decision.json`, reviewer fields, SHA-256 и успешный validator подтверждают исследовательскую целостность, но не дают filing authority. Перед включением bounded authority/practice claim в жалобу центральный issue gate по `../ksrf-complaint-cycle/references/router-and-state-machine.md` должен повторно проверить заранее созданный host-attested approval полного candidate, practice и adverse bindings.

## Роль

Используй CasusLegal как канал discovery и inspection, а не как самостоятельный источник права. Правовую опору образуют сами акты и содержащиеся в них проверенные позиции. Для ключевой цитаты открой полный текст, зафиксируй locator и сверь официальный источник.

Работай между `ksrf-explore-arguments` и `ksrf-rights-argument-builder`: получай case-scoped гипотезу или утвержденный `ArgumentPortfolio`, возвращай authority ledger и проверяемые drafting blocks. Не выбирай principal hypothesis за юриста и не компенсируй практикой непройденные hard gates допустимости.

До case-scoped работы используй `../ksrf-complaint-cycle/references/offline-practice-core.md` как автономный baseline по маршруту, допустимости, архитектуре аргумента и drafting. CasusLegal расширяет discovery, но не заменяет это ядро и не становится обязательной runtime-зависимостью всего KSRF-набора.

## Выбери режим

- `research`: найти supporting, weakening, distinguishing и blocking authorities для одной или нескольких гипотез.
- `drafting`: превратить проверенные authority records в аргументативные блоки после содержательной проверки и центрального host-attested approval полного связанного candidate.
- `audit`: проверить акты, тезисы, цитаты, locators, актуальность и необработанную adverse-практику в существующем проекте.

## Порядок работы

### 1. Проверь вход и доступ

1. Если переданы материалы дела, сначала собери `CaseFile` и `AutonomousIntakeRecord` по `../ksrf-complaint-cycle/references/ksrf-tool-layer.md`. Сам установи `case_id`, кандидатов точной нормы и редакции, судебный смысл, механизм вреда, затронутые права, доказательство применения и варианты remedy; затем проверь норму и доступные акты по официальным источникам.
2. Если норма или её применение не подтверждены после анализа пакета и официального pass, верни blocking gap с точной задачей получения отсутствующего акта; не спрашивай пользователя, какую норму или право выбрать, и не заменяй пробел похожей практикой.
3. Проверь наличие CasusLegal tools. Если MCP или подписка недоступны, явно запиши coverage gap и не имитируй поиск. Продолжай только по переданным или автономным официальным источникам.
4. Не сохраняй connector token. Токенизированный CasusLegal URL держи только в приватном case ledger; не переноси его в публичный skillset или процессуальный документ.

### 2. Построй query profile

Сформируй минимум пять независимых поисковых дорожек:

1. `norm_and_meaning`: норма, редакция, спорная интерпретация и системная связка.
2. `mechanism_and_harm`: как правило создает непосредственный конституционный вред.
3. `right_or_guarantee`: право, принцип или институциональная гарантия.
4. `remedy`: сохраняющий смысл, обязательная гарантия или иной минимальный способ устранения дефекта.
5. `adverse`: лучший контраргумент, более узкая позиция, отказная логика или иная редакция нормы.

Добавляй отдельную дорожку для доказательственного носителя, если спор касается бремени, стандарта или доступа к доказательствам. Не считай один широкий запрос достаточным.

Если тезис выходит за пределы применения к заявителю и утверждает повторяемый судебный смысл, split, динамику, системную практику либо remedial effect, сначала потребуй current claim mapping из исполняемого `PracticeAnalysisGate` (`../ksrf-complaint-cycle/references/practice-analysis-integration.md`), затем открой `references/judicial-meaning-evidence-acquisition.md`. Зафиксируй норму/редакцию, population/query frame, уровни инстанций, inclusion/exclusion, adverse pass, coverage limits и stop condition; для массового кодирования добавь MeasurementAudit, InterpretiveArgumentPassport и при необходимости EmpiricalTriangulationGate. Импортируй в authority ledger только artifact-derived portable v2 records с request/claim/proof bindings, которые повторно сверены с прикреплённым кассационным source workspace; unanchored bundle остаётся audit-only. `Adverse`, `distinguishes` и `neutral/context-only` сохраняй как разные отношения. Несколько найденных актов возвращают максимум `corroborated_sample`, а не автоматически «устойчивую практику».

### 3. Маршрутизируй MCP-вызовы

Прочитай `references/tool-routing.md` перед первым поиском. По умолчанию:

- начни с `mcp__casuslegal__casuslegal_search_practice` для смысловой карты и иерархических блоков;
- используй `mcp__casuslegal__casuslegal_find_term` для дословной формулы, нормы или устойчивого термина;
- после выбора опорного акта используй `mcp__casuslegal__casuslegal_find_similar` для аналогий и контрпримеров;
- открывай `mcp__casuslegal__casuslegal_get_case_details` только для ключевых актов и точной цитаты;
- используй `mcp__casuslegal__casuslegal_browse_practice` с сортировкой по дате, если нужен действительно последний акт;
- следуй `_response_format_hint` и используй возвращенный `url` дословно в исследовательском ответе.

### 4. Назначь акту юридическую функцию

Прочитай `references/authority-and-transferability.md`. Для каждой записи назначь `role` и `relation`:

- КС РФ: `constitutional_doctrine`, `remedy_model`, `adverse_authority`;
- Пленум или обзор ВС РФ: `judicial_meaning`;
- определение коллегии ВС РФ: `application_evidence`;
- ВАС РФ: `historical_line`;
- отказная, противоположная или более узкая позиция: `adverse_authority`.

Используй relation из общего исследовательского контракта: `supports`, `weakens`, `distinguishes`, `blocks`. Не называй определение ВС РФ самостоятельным доказательством неконституционности: оно обычно подтверждает устойчивость судебного смысла или практический механизм вреда.

### 5. Проверь переносимость и источник

Для каждого существенного акта проверь:

- норму, редакцию и временной контекст;
- совпадение механизма, вреда, стадии и институциональной ситуации;
- роль фактов и доказательственного носителя;
- совпадение или различие remedy;
- последующее регулирование и более поздние позиции;
- что тезис принадлежит суду, а не стороне или автору обзора;
- полный текст и locator для цитаты;
- минимум одну adverse, limiting или refusal-позицию для сильной аналогии.

Когда спор зависит от holding/dicta, уровня обобщения или аналогии, используй поля и stop rules из `../ksrf-argument-patterns/references/legal-reasoning-model-branches.md`. Common-law термины служат QA-структурой: юридический статус российского акта и применимое положение устанавливай по российской системе источников.

Если нужно извлечь позицию, проверить её последующее использование самим КС РФ отдельно от нижестоящей рецепции, обосновать дельту к прежнему решению или проследить uptake довода и post-filing события, прочитай `references/position-lifecycle-and-argument-uptake.md` и не повышай candidate до drafting без official full-text, current-law, adverse и human gates.

Лексическое, векторное или графовое сходство используй только как candidate generation. Если близкой аналогии нет, запиши `no_close_analogy_found`, а не отрицательный юридический вывод.

### 6. Собери authority ledger

Используй контракт `references/authority-ledger-contract.md`. Не смешивай записи разных дел и не переноси персональные данные вместе с публичной практикой.

Если корпус исследован `ksrf-cassation-judicial-meaning`, принимай через файловый handoff-envelope версии `1.0` не весь корпус, а только отобранные официальные акты из `approved_bounded_findings`. Для каждой импортируемой записи сохрани `run_id`, `plan_sha256`, `evidence_sha256`, `chain_id`, официальный URL, хеш документа, точную цитату и locator, роль, relation, adverse-status и предел вывода. Несовпадение хешей, отсутствие `human-decision.json`/`validation-report.json` либо статус, не допускающий drafting, блокирует перенос в drafting ledger, но не изменяет исходный исследовательский corpus. Не импортируй Python-модули соседнего скилла и не делай его наличие условием обычного точечного поиска authority.

Проверь JSON:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-practice-authority-builder/scripts/validate_authority_ledger.py" path/to/authority-ledger.json
```

Перед передачей в drafting сначала зафиксируй локальное reviewed-решение и проверь структуру ledger:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-practice-authority-builder/scripts/validate_authority_ledger.py" --require-drafting path/to/authority-ledger.json
```

Этот результат означает лишь `research_bundle_ready_for_central_gate`. Он не разрешает filing-significant drafting сам по себе: получи и проверь отдельный pre-existing host-attested approval полного issue/practice/adverse binding; при отсутствии host verifier оставь claim в `ready_for_expert_review` или `audit_only`.

Перед публикацией обезличенного ledger проверь утечку токенизированных URL:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-practice-authority-builder/scripts/validate_authority_ledger.py" --public path/to/authority-ledger.json
```

### 7. Встрой или проверь аргумент

Прочитай `references/argument-insertion-and-audit.md`.

Для drafting строй блок как `тезис -> позиция -> мост применимости -> вывод`. Отдельно обозначай:

- конституционный критерий из практики КС РФ;
- судебный смысл и его воспроизводимость из практики ВС РФ;
- связь этого смысла с применением в конкретном деле;
- предел аналогии и ответ на adverse authority;
- remedy, устраняющий нормативный механизм, а не пересматривающий факты.

В режиме audit не исправляй слабую ссылку дополнительной риторикой. Пометь `blocking source defect`, если акт не существует, цитата не подтверждает proposition, locator отсутствует или временной контекст делает перенос недостоверным.

## Вывод

Возвращай:

- `Query profile` и журнал реально выполненных дорожек;
- `Authority ledger` с ролями, relations и verification status;
- `Supporting/adverse map` по каждой гипотезе;
- `Drafting blocks` либо причины, почему drafting преждевременен;
- `Source defects` и `no_close_analogy_found`;
- `Human decision`: что именно должен утвердить юрист;
- `Coverage limits`: недоступные инструменты, непроверенные источники и незакрытые запросы.

## Ограничения

- Не выдавай список ссылок за аргумент и число актов за силу позиции.
- Не цитируй сниппет как полный текст.
- Не скрывай adverse findings и не удаляй их из внутреннего ledger после drafting.
- Не вставляй токенизированный CasusLegal URL в жалобу; используй реквизиты, locator и официальный источник.
- Не объявляй поиск исчерпывающим, если не выполнены релевантные дорожки или недоступна часть корпуса.
- Не делай доступ к CasusLegal условием автономной работы остальных KSRF skills.

## Необязательная стыковка

- `../ksrf-cassation-judicial-meaning/SKILL.md` — источник только выбранных, официально проверенных и одобренных актов для authority ledger; файловый envelope версии `1.0` сохраняет provenance и не подменяет проверку переносимости.
