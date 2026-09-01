## ADDED Requirements

### Requirement: Court-request applicability SHALL bind to an exact passed passport revision

Для каждого оспариваемого структурного положения скилл SHALL возвращать верхнеуровневый `CourtRequestApplicabilityBinding` с `passport_id`, `passport_revision_id`, `timepoint_id`, `edition_id`, `applicability_status` и `blockers`. Статус `verified` SHALL быть допустим только при `NormVersionPassport.gate.status=passed` и ровно одном совпадении выбранной временной точки с выбранной редакцией в `timepoint_edition_map` текущей ревизии.

Скилл SHALL NOT доверять caller-supplied сохранённым `gate.status` или `filing_ready`: перед повышением статуса он SHALL требовать текущий результат существующего `assess_norm_version_passport(...)` с действующими official-evidence verifier, approval ledger и approval ID.

Уникальная пара SHALL считаться необходимым, но недостаточным условием: скилл SHALL отдельно доказать, что выбранная временная точка юридически управляет future applicability, либо что официальный transition rule однозначно выбирает редакцию для всего подтверждённого горизонта. Binding SHALL оставаться методологической статической проекцией, а не runtime или filing authority.

#### Scenario: Exact passed revision has one edition mapping

- **WHEN** четыре идентификатора совпадают с текущей ревизией паспорта
- **AND** `gate.status=passed`
- **AND** `timepoint_edition_map` содержит ровно одну пару выбранных `timepoint_id` и `edition_id`
- **AND** подтверждённый горизонт будущего решения целиком лежит в интервале редакции либо официальное переходное правило однозначно выбирает её для всего возможного горизонта
- **THEN** `applicability_status` MAY быть `verified`

#### Scenario: Passport or edition binding is not exact

- **WHEN** паспорт не прошёл gate, ревизия не совпадает либо временная точка имеет ноль или больше одного соответствия редакции
- **THEN** `applicability_status` SHALL быть `blocked`
- **AND** результат SHALL вернуть `FIX_FIRST` и не выдавать filing-ready формулу

#### Scenario: Official transition evidence is missing

- **WHEN** применимость зависит от изменяющего акта или переходного положения, официальный документ которого не сохранён и не верифицирован
- **THEN** результат SHALL вернуть `ABSTAIN_PENDING_OFFICIAL_SOURCE`
- **AND** SHALL перечислить недостающие акты
- **AND** SHALL NOT обозначать применимость или законодательную историю как проверенную

#### Scenario: Stored passed gate and unknown future horizon

- **WHEN** вход содержит сохранённые `gate.status=passed` и `filing_ready=true`, но текущая оценка с verifier и approval ledger не выполнена
- **AND** неизвестная дата будущего решения может пересечь границу редакций
- **THEN** binding SHALL остаться `blocked`
- **AND** результат SHALL вернуть `ABSTAIN_PENDING_RECORD`
- **AND** SHALL NOT выдумывать дату решения, подменять её filing-timepoint или выдавать filing-ready формулу

#### Scenario: Known future horizon conflicts with a unique event-time pair

- **WHEN** свежий passed паспорт однозначно связывает `T_event` с `E_old`
- **AND** подтверждённый горизонт будущего решения лежит в `E_new`
- **AND** официальное переходное правило не делает `E_old` управляющей редакцией
- **THEN** `T_event → E_old` SHALL NOT получить `applicability_status=verified`
- **AND** результат SHALL вернуть `FIX_FIRST` и не выдавать filing-ready формулу

### Requirement: The documented binding SHALL resist decoy and nesting ambiguity

Канонический `CourtRequestApplicabilityBinding` SHALL находиться корневым ключом JSON fence непосредственно под точным заголовком интерфейсного контракта. Ранний decoy fence, закрытый или незакрытый HTML-комментарий, заголовок внутри внешнего code fence либо вложенный ключ SHALL NOT считаться каноническим контрактом.

#### Scenario: Earlier decoy precedes a nested binding

- **WHEN** документ содержит корректно выглядящий decoy до контрактной секции, а в самой секции binding вложен в wrapper
- **THEN** offline contract test SHALL завершиться ошибкой

#### Scenario: Binding appears only inside an HTML comment

- **WHEN** корректно выглядящий заголовок и JSON fence находятся только после открытия закрытого либо незакрытого многострочного HTML-комментария
- **THEN** offline contract test SHALL завершиться ошибкой

#### Scenario: Binding heading appears inside an outer code fence

- **WHEN** корректно выглядящий заголовок и внутренний JSON fence находятся внутри внешнего fence длиной не менее четырёх backticks
- **THEN** offline contract test SHALL завершиться ошибкой

#### Scenario: Canonical safe-default binding

- **WHEN** точная секция содержит верхнеуровневый binding со всеми шестью полями
- **AND** шаблон использует `applicability_status=blocked` и `blockers=["FIX_FIRST"]`
- **THEN** offline contract test SHALL пройти
