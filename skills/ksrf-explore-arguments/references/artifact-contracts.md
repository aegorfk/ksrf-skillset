# Контракты исследовательских артефактов

## Содержание

- [ResearchFinding](#researchfinding)
- [ECHR extension](#echr-extension)
- [ArgumentHypothesis](#argumenthypothesis)
- [ArgumentPortfolio](#argumentportfolio)
- [ConstitutionalIssueOption](#constitutionalissueoption)
- [AdmissibilityMatrix и локальный маршрут](#admissibilitymatrix-и-локальный-маршрут)
- [KSRFRouteRecommendation](#ksrfrouterecommendation)
- [Проверка JSON-артефакта](#проверка-json-артефакта)
- [Case isolation](#case-isolation)

## ResearchFinding

Обязательные поля:

- `finding_id`: уникальный в пределах дела идентификатор;
- `case_id`: идентификатор дела, запрещающий неявный cross-case reuse;
- `direction`: направление исследования;
- `thesis`: одно проверяемое утверждение;
- `source_anchor`: официальный URL, реквизиты акта или evidence id;
- `locator`: пункт, страница, абзац или цитатное окно; допускается `null` только при `candidate`;
- `relation`: `supports`, `weakens`, `distinguishes` или `blocks`;
- `hypothesis_ids`: затронутые гипотезы;
- `verification_status`: `candidate`, `verified`, `rejected` или `superseded`;
- `confidence`: `low`, `medium` или `high`;
- `limitations`: пределы вывода и альтернативное объяснение;
- `contains_sensitive_data`: признак конфиденциального содержания.

Finding не равен цитате. `thesis` должен точно соответствовать объёму подтверждения, а `limitations` — показывать, чего источник не доказывает.

### ECHR extension

Если finding получен из HUDOC, сначала создай actor-separated
`ECHRArgumentPacket` по
`../../ksrf-echr-argumentation/references/mcp-argument-intelligence-contract.md`.
В `ResearchFinding` дополнительно обязательны:

- `echr_packet_id`, `itemid`, `matter_key`, application number/date и document
  family;
- официальный HUDOC URL, source/artifact SHA, page/paragraph и
  sentence-or-char locator;
- `source_actor`, `source_function`, `source_role`, `source_form`,
  `speaker_verified` и `court_treatment`;
- для `court_treatment=accepted|rejected|qualified` — отдельный hydrated
  majority-response packet id, locator, exact text и source SHA; для
  `not_addressed` — review ref с охватом акта;
- `argument_function`, temporal/currentness status, adverse/distinguishing
  review и transfer limit;
- российский official-anchor evidence ref, URL, реквизиты, locator, checked-at
  и связанный `ksrf_transfer_packet_id` либо явный blocking status;
- `lifecycle_stage`, `reuse_target`, `promotion_eligible`, blockers, а для
  `cross_case_reusable|skill_update_approved` — human approval record id,
  scope, timestamp и SHA-256 одобренного input bundle.

Точная цитата допустима только из hydrated case details. Search snippet,
semantic profile, raw assertion и cluster label остаются `candidate`. Applicant
submission, even reproduced in a judgment, не является original application
или holding Суда; отдельное мнение остаётся research signal/counterargument.
Если отсутствует российский официальный anchor, ECHR finding может изменить
исследовательскую гипотезу, но его drafting reuse блокируется.
Голые enum `court_treatment`, `russian_official_anchor_status` и
`lifecycle_stage` доказательствами не являются и не проходят promotion gate.

## ArgumentHypothesis

Обязательные поля:

- `hypothesis_id`, `title`, `status`;
- `normative_mechanism` и `constitutional_harm`;
- `review_line`: возможный принцип, тест или комбинация;
- `supporting_finding_ids`, `adverse_finding_ids`;
- `falsifier`: наблюдение или источник, опровергающие линию;
- `fact_dispute_risk`;
- `refusal_model`;
- `primary_relief`, `narrower_relief`;
- `missing_materials`.

Статусы: `active`, `promoted`, `reserve`, `experimental`, `rejected`.

## ArgumentPortfolio

Обязательные поля:

- `hard_gates`: отдельный pass/fail/unknown по каждому порогу с evidence ids;
- `principal_hypothesis_id`;
- `reserve_hypothesis_ids`;
- `experimental_hypothesis_ids`;
- `rejected_hypothesis_ids` и причины;
- `dimension_comparison` без обязательной свёртки в один score;
- `critic_findings`;
- `human_approval`: `pending`, `approved`, `revise` или `rejected`;
- `approval_reason` и `approved_by`.

`principal_hypothesis_id` может быть `null`, пока решение человека не принято. Schema validity не означает drafting readiness.

## ConstitutionalIssueOption

Это пользовательское представление одной проверенной гипотезы, а не просьба к заявителю самому провести квалификацию. Обязательные поля:

- `option_id`, `hypothesis_id`, понятное краткое название;
- `plain_language_problem`: какое правило сработало и к какому последствию привело;
- `challenged_norm_and_meaning`, `right_or_principle`, `defect_and_test`;
- `application_and_harm_evidence_ids`;
- `supporting_finding_ids`, `adverse_finding_ids`, `refusal_model`;
- `primary_relief`, `narrower_relief`;
- `readiness`: `viable`, `conditional` или `rejected`;
- `key_risk`, `falsifier`, `missing_materials`;
- `portfolio_role_reason`: почему вариант principal, reserve, experimental или rejected.

Показывай два–четыре существенно разных варианта, если они подтверждаются материалом. Не фабрикуй разнообразие: при одной жизнеспособной линии перечисли проверенные и отклонённые альтернативы. Выбор человека относится к стратегии principal/reserve, а не заменяет исследование нормы и нарушенного права.

## AdmissibilityMatrix и локальный маршрут

`AdmissibilityMatrix` версии `1.0.0` заполняется до итогового выбора маршрута. Его исполняемая схема — `admissibility-matrix.v1.schema.json`; схема результата — `ksrf-route-recommendation.v1.schema.json`. Возьми [безопасный стартовый файл](../../ksrf-complaint-cycle/references/admissibility-matrix-template.v1.json): все его пороги остаются `unknown`, поэтому он не может сам открыть маршрут `GO_TO_KSRF`. Матрица должна содержать каждый из двенадцати порогов ровно один раз, доказательства по каждой строке, дату проверки официального правила, устранимость, доступность материалов и следующий шаг. `unknown` не превращается в `pass`, а недоступный после полного поиска источник не доказывает отсутствие основания. Каждый `option_binding` использует штатный `issue-candidate-content:sha256:<64 lowercase hex>` и должен совпасть с последним сохранённым кандидатом того же дела и требования; простая подстановка похожего ID, выдуманного хеша, статуса `viable` или чужих доказательств блокирует маршрут.

Локальный CLI выполняет три операции без сетевых и модельных вызовов:

- `ksrf admissibility validate` проверяет матрицу и сохраняет точный вход и результат в журнале дела;
- `ksrf admissibility derive` заново сверяет локальные официальные опоры, применяет фиксированный порядок решений и сохраняет `KSRFRouteRecommendation`;
- `ksrf admissibility status` повторно проверяет последнюю матрицу и добавляет новое событие, не изменяя прежнее. Если официальная опора больше не подтверждается, прежний `GO_TO_KSRF` понижается до `ABSTAIN_PENDING_RECORD`.

Переносимый пример для установленного набора skills:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
KSRF_WORKSPACE="/абсолютный/путь/к/делу"
KSRF_MATRIX="/абсолютный/путь/к/admissibility-matrix.json"

python3 "$KSRF_SKILLS_ROOT/ksrf-complaint-cycle/scripts/ksrf.py" admissibility validate --workspace "$KSRF_WORKSPACE" --payload "$KSRF_MATRIX" --json
python3 "$KSRF_SKILLS_ROOT/ksrf-complaint-cycle/scripts/ksrf.py" admissibility derive --workspace "$KSRF_WORKSPACE" --payload "$KSRF_MATRIX" --json
python3 "$KSRF_SKILLS_ROOT/ksrf-complaint-cycle/scripts/ksrf.py" admissibility status --workspace "$KSRF_WORKSPACE" --json
```

Только `GO_TO_KSRF` завершает этот маршрут кодом `0`; `FIX_FIRST`, `COURT_REQUEST_ROUTE`, `NO_GO_KSRF` и `ABSTAIN_PENDING_RECORD` остаются заблокированными состояниями и возвращают код `3`. Ошибка входного контракта возвращает код `2`. Эти коды управляют локальным процессом, а не юридическим решением.

## KSRFRouteRecommendation

Формируется после `AdmissibilityMatrix` и, когда hard gates допускают содержательный проход, после исследования, но до drafting. При раннем `NO_GO_KSRF` или `ABSTAIN_PENDING_RECORD` портфель не требуется:

- `decision`: `GO_TO_KSRF`, `FIX_FIRST`, `COURT_REQUEST_ROUTE`, `NO_GO_KSRF` или `ABSTAIN_PENDING_RECORD`;
- `matrix_revision_id`, `decision_rule_version`, `decisive_gate_evidence` и `blocker_codes`;
- `option_bindings` с точными `content_fingerprint`, `preferred_option_id`, `reserve_option_ids`; для решения до содержательного портфеля `preferred_option_id=null`, а `reserve_option_ids=[]`;
- `official_authority_evidence_ids` — только локально перепроверенные официальные опоры;
- `expected_client_benefit`, `adverse_risks`, `alternatives_and_deadlines`;
- `next_actions_in_order`, `reconsideration_conditions`;
- `human_decision=pending`, `human_legal_review_required=true`, `legal_assessment_automated=false`, `filing_authority=false`, `filing_performed=false`.

`GO_TO_KSRF` означает только машинно согласованную рекомендацию перейти к юридической проверке, а не прогноз принятия и не разрешение подать жалобу. Юрист отдельно проверяет вывод, человек отдельно принимает решение, подписывает и подаёт документы. `Unknown` требует `FIX_FIRST` или `ABSTAIN_PENDING_RECORD`, но не автоматически `NO_GO_KSRF`. Неустранимый fail или чисто фактический спор позволяют `NO_GO_KSRF` сразу после admissibility без выдуманного issue option.

## Проверка JSON-артефакта

`validate_argument_research.py` не исправляет и не преобразует вход
автоматически. Ошибки структуры корректного JSON возвращаются кодом `1` как
строки `ERROR:` с точным полем или индексом; проверка продолжает собирать
независимые ошибки и не должна завершаться Python traceback. Ошибка чтения,
кодировки UTF-8, синтаксиса JSON или ограничений декодера возвращается кодом
`2` в stderr.

Код `0` и строка `OK:` означают только соответствие исследовательского
артефакта машинному контракту. Они не подтверждают готовность жалобы,
достоверность источников или одобрение выбранной стратегии.

## Case isolation

Публичный акт или обезличенная методика могут переиспользоваться. Факты стороны, документы, персональные данные и внутренние notes остаются в `case_id`; для переноса требуется отдельная sanitization decision.
