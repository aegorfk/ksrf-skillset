# Контракты исследовательских артефактов

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

## KSRFRouteRecommendation

Формируется после `AdmissibilityMatrix` и, когда hard gates допускают содержательный проход, после исследования, но до drafting. При раннем `NO_GO_KSRF` или `ABSTAIN_PENDING_RECORD` портфель не требуется:

- `decision`: `GO_TO_KSRF`, `FIX_FIRST`, `COURT_REQUEST_ROUTE`, `NO_GO_KSRF` или `ABSTAIN_PENDING_RECORD`;
- `decisive_gate_evidence`, `preferred_option_id`, `reserve_option_ids`; для решения до содержательного портфеля `preferred_option_id=null`, а `reserve_option_ids=[]`;
- `expected_client_benefit`, `adverse_risks`, `alternatives_and_deadlines`;
- `next_actions_in_order`, `reconsideration_conditions`;
- `human_decision`: `pending`, `accepted`, `revise` или `declined`.

`GO_TO_KSRF` означает юридически обоснованную готовность к подаче, а не прогноз принятия с ложной числовой точностью. `Unknown` требует `FIX_FIRST` или `ABSTAIN_PENDING_RECORD`, но не автоматически `NO_GO_KSRF`. Неустранимый fail или чисто фактический спор позволяют `NO_GO_KSRF` сразу после admissibility без выдуманного issue option.

## Case isolation

Публичный акт или обезличенная методика могут переиспользоваться. Факты стороны, документы, персональные данные и внутренние notes остаются в `case_id`; для переноса требуется отдельная sanitization decision.
