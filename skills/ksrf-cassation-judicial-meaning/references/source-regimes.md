# Официальные источники и институциональные режимы

## Содержание

- [1. КСОЮ после реформы: встроенная дневная выдача](#1-ксою-после-реформы-встроенная-дневная-выдача)
- [2. Второй официальный маршрут 2 КСОЮ](#2-второй-официальный-маршрут-2-ксою)
- [3. Период до 01.10.2019](#3-период-до-01102019)
- [4. Fail-closed manifest verification и promotion](#4-fail-closed-manifest-verification-и-promotion)
- [5. Сверка маршрутов](#5-сверка-маршрутов)
- [6. Статусы страницы](#6-статусы-страницы)


## 1. КСОЮ после реформы: встроенная дневная выдача

Встроенный режим `ksoyu_post_2019` использует адаптер `ksoyu_daily_v2` для девяти КСОЮ с 01.10.2019. Он строит официальную дневную выдачу:

```text
https://{1..9}kas.sudrf.ru/modules.php?name=sud_delo&srv_num=1&H_date=DD.MM.YYYY
```

Адаптер структурно обнаруживает только same-origin ссылки на карточки, акты и навигацию. Пустая дата получает `success_empty` только при канонической форме `calformH`, совпадении запрошенной даты и даты содержательной области, точной датированной формуле «дел не назначено», отсутствии ссылок на дела/акты и пагинации. Registry, adapter и parser versions вместе с признаками классификации сохраняются в provenance. Resume сверяет collector manifest, `run_id` и `plan_sha256` до сетевого запроса.

Параметр следующей страницы не выдумывается. Если страница намекает на продолжение, но проверяемый адрес не извлечён, фиксируется `pagination_unresolved`.

`H_date` перечисляет дела, назначенные на дату. Максимальный статус — `closed_declared_enumeration_observed`. Это не банк всех вынесенных решений, всех рассмотренных дел или всех опубликованных актов. Поля совместимости с названием `closed_official_population_observed` имеют тот же ограниченный `denominator_scope`.

## 2. Второй официальный маршрут 2 КСОЮ

Registry содержит контракт `2kas_civil_result_date_search_v1` для официального поиска гражданской кассации 2 КСОЮ по дате результата. Его текущий статус:

- `adapter=null`;
- `operational_status=contract_only_not_wired`;
- `closed_for_declared_enumeration=false`;
- scope только `civil_cassation` и только выдача официального result-date search;
- официальная страница предупреждает, что ограничения публикации могут исключать дела из результатов.

Поэтому этот маршрут пока нельзя считать независимым закрытым перечислителем и нельзя использовать его отсутствие как нулевой результат. Он должен появляться в отчёте как open route gap. Даже после реализации его пределом останется `2kas_civil_cassation_official_search_results_by_result_date_not_all_court_output`.

## 3. Период до 01.10.2019

`regional_presidia_pre_2019` имеет `adapter=null` и `enumeration=not_configured`. Это иной институциональный режим дореформенной кассации региональных президиумов, а не ранний период 2 КСОЮ. Исследование 2016–2026 годов обязано разделить как минимум:

- 2016–30.09.2019 — дореформенный режим, сейчас `not_configured`;
- с 01.10.2019 — КСОЮ, только в пределах проверенного post-2019 route scope.

Нельзя подменять десятилетие семью годами КСОЮ, объединять режимы без comparability review, считать отсутствие адаптера отсутствием практики или называть корпус полным за 2016–2026 годы. Допустимый выход — отдельные страты, явный historical gap и более узкий `maximum_permitted_claim`.

Верховный Суд РФ, арбитражная кассация и специальные источники также остаются отдельными режимами `not_configured`/`discovery_only`, пока нет проверенного официального перечислителя.

## 4. Fail-closed manifest verification и promotion

`source verify-manifest` проверяет структуру и внутреннюю непротиворечивость manifest. Эта команда сама по себе не делает route operational и не закрывает denominator:

```bash
python3 <skill-dir>/scripts/judicial_meaning.py source verify-manifest \
  --input ./enumerator-candidate.json \
  --output ./enumerator-candidate.validated.json
```

Новый route повышается только из manifest с `configured=false`. В `enumerator-verification.json` должны быть `true` все gates:

- `registry_verified`;
- `applicability_verified`;
- `identity_verified`;
- `terminal_states_verified`;
- `fixtures_passed`;
- `resume_passed`;
- `live_smoke_passed`;

Там же нужны проверенные `adapter_id` и точный `closure_rule`. Promotion требует identified reviewer и ISO timestamp:

```bash
python3 <skill-dir>/scripts/judicial_meaning.py source promote-enumerator \
  --manifest ./enumerator-candidate.validated.json \
  --verification ./enumerator-verification.json \
  --reviewer "И.И. Иванов" \
  --reviewed-at 2026-08-27T14:00:00Z \
  --output ./enumerator-promotion.json
```

Результат содержит content-bound promotion certificate и promoted `manifest`. Любой false/missing gate, несовпадение adapter/closure, неверный digest или попытка повысить уже configured manifest завершается ошибкой. Не переносите вручную только поле `configured=true`: route без проверенного promotion certificate остаётся `observed_only`.

## 5. Сверка маршрутов

Подготовьте JSON/JSONL с manifests, observations и route coverage, затем выполните:

```bash
python3 <skill-dir>/scripts/judicial_meaning.py source reconcile \
  --manifests ./enumerator-manifests.json \
  --observations ./source-observations.jsonl \
  --route-coverage ./route-coverage.jsonl \
  --requested-from 2016-01-01 \
  --requested-to 2026-08-27 \
  --workspace ./judicial-meaning-run
```

Для `closed_declared_enumeration` недостаточно `success_empty=1`. Нужны одновременно:

- применимый configured manifest с проверенным promotion certificate;
- `total_segments > 0` и все сегменты в `success_empty`/`success_nonempty`;
- валидный `terminal_snapshot_sha256`;
- `terminal_rule_verified=true`;
- `pagination_complete=true`;
- `resume_verified=true`;
- `live_smoke_verified=true`.

Иначе route получает `observed_only` с `closure_blockers`. `source-reconciliation.json` хранит `found_by`, intersection, directional gaps, unresolved identities, coverage каждого route и historical gaps. Общий `closed_declared_enumerations` возможен только для всех применимых настроенных маршрутов и без применимого `not_configured`; даже он не означает «все акты кассации».

Discovery-only находка повышается до official evidence только после content-addressed official snapshot, HTTPS official URL, confirmed identity и ручного review. Совпадение номера или сниппет недостаточны.

## 6. Статусы страницы

- `success_nonempty`: HTTP 200, структура подтверждена, есть строки.
- `success_empty`: HTTP 200, структура и дата подтверждены, явно нулевой результат.
- `blocked`: CAPTCHA, защитная страница, 403 или иной запрет.
- `retryable_error`: timeout, DNS/TLS, 429, временный 5xx.
- `terminal_error`: невосстановимая ошибка или исчерпанный bounded retry.
- `pagination_unresolved`: признаки продолжения без проверяемого адреса.
- `unavailable`: официальный источник недоступен в заявленном режиме.
- `not_applicable`: режим действительно не действовал, с записанной причиной.
- `not_configured`: для применимого режима нет проверенного адаптера.
- `contract_only_not_wired`: есть специфицированный route contract, но нет operational adapter.

Ни один ошибочный, защитный, не настроенный или только специфицированный ответ не равен `success_empty`.
