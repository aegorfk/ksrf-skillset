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

## Case isolation

Публичный акт или обезличенная методика могут переиспользоваться. Факты стороны, документы, персональные данные и внутренние notes остаются в `case_id`; для переноса требуется отдельная sanitization decision.
