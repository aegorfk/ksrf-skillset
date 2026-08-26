# Устранение проблем

## `case prepare` требует intake

Это обязательная защита. Выполните `intake`, возьмите `document_id` из `intake/applicant-manifest.jsonl` и свяжите каждый document-based `verified` feature с этим ID и точным `quote_locator`. Произвольный JSON, внешний URL или документ без извлечённого текста не подтверждают fingerprint.

Если `casework-dependencies.json` содержит missing tasks, не удаляйте их. Добавьте отсутствующие `norm_edition`, `applicant_case_meaning`, `procedural_posture` или подтвердите неизвестный материальный признак по акту; затем снова выполните `case prepare`. Новая ревизия корректно пометит прежние связи stale.

## PDF не извлечён

Core требует Python 3.10+, но не требует сторонних Python-пакетов. Для PDF он пробует локальный `pdftotext`. Для скана при наличии `pdftoppm` и `tesseract` выполните:

```bash
python3 <skill-dir>/scripts/judicial_meaning.py ocr \
  --input /полный/путь/акт.pdf \
  --output /полный/путь/акт.ocr.txt \
  --language rus
```

Команда пишет `.provenance.json` с хешами и версиями помощников, но оставляет `human_verified=false`. Визуально сверьте текст со всеми страницами и затем передайте проверенный `.txt` в `intake`. Если помощников нет или текст пуст, PDF остаётся `unextractable`; содержание нельзя угадывать.

## Запрос предложен, но не попал в frozen plan

`query-suggestions.jsonl` содержит только `suggested_unconfirmed`. До `plan freeze` выполните `query accept` для нужного `query_id` с reviewer и ISO timestamp. Если план уже заморожен, не редактируйте его и не пытайтесь повторить accept: используйте `query supplement` с reason. Supplemental-запрос раскрывается отдельно и не меняет исходный denominator.

## Compare или relation стали stale/unresolved

Проверьте `status.state.binding_diagnostics` и следующие bindings:

- comparison: fingerprint, applicant features, candidate features, position card, human review;
- relation: fingerprint, position card, comparison и applicant position.

Не исправляйте SHA-256 вручную. Повторно запустите `position check` при изменённой карточке, затем `compare` с текущим fingerprint и reviewer, затем `relation classify`. `uncertain`, `pending_human_review`, contextual/unclear materiality и неодобренная applicant position законно дают `unresolved`.

## Adverse bucket не завершается

Для каждой из четырёх корзин нужны: bucket среди searched и completed; хотя бы один фактически выполненный query ID; пустой список unresolved source segments; непустое объяснение влияния на maximum claim. Ноль найденных карточек допустим, но только после выполнения этих условий и только с формулой «не обнаружено в раскрытом поиске».

## Нормативный мост отклонён

Сверьте текущий `fingerprint_sha256` и точный `maximum_permitted_claim` из `status`. Supporting cards должны иметь `necessary_to_outcome`, одобренный `matched` comparison и relation `supports`; adverse cards — `matched` и relation `adverse`. Мост требует завершённого `case-adverse-review.json`, reviewer/time и `human_review=approved`. Не повышайте максимум формулировкой в `claim_wording`.

## Официальный сайт защищён или не открывается

Не обходите защиту. Сохраните `blocked`/`retryable_error`, повторите через `collect --resume` после нормального интервала и раскройте пробел охвата. Ошибка доступа не доказывает отсутствие акта.

Если встроенный Python не видит системное хранилище TLS-сертификатов, runtime может использовать локальный `curl` как проверяющий TLS fallback. Команда не содержит `--insecure`; имя, версия и профиль помощника записываются в provenance. При отсутствии `curl` сегмент остаётся `retryable_error`, а проверка сертификата не отключается.

## Запуск прерван

Повторите `collect --resume`. Завершённые страницы не скачиваются снова, зависшие leases восстанавливаются отдельным событием, предыдущие попытки не стираются.

Если resume сообщает несовпадение `run_id`, `plan_sha256` или collector manifest, не редактируйте `run.json` вручную. Начните новый запуск либо выполните отдельно проверенную переклассификацию raw snapshots с новым provenance; разные registry/adapter/parser versions нельзя молча объединять.

## Public cache отклоняет URL или пакет

Удалите credentials и secret-bearing query parameters; используйте только действительно публичный HTTP(S) URL, не localhost/private IP и не `file://`. Не ослабляйте проверку, чтобы импортировать акт заявителя: он должен остаться в case workspace.

При ошибке `import-run` проверьте manifest/object hashes, public roles, канонические URL, run pins, text provenance, непрерывность funnel и treatment history. Пакет валидируется целиком до записи; исправьте источник и экспортируйте заново, не редактируйте manifest или objects вручную.

## Enumerator valid, но route остаётся open

`source verify-manifest` не является promotion. Для closure нужны promotion certificate со всеми семью gates и runtime terminal evidence: terminal snapshot, terminal rule, pagination, resume и live smoke. Пока у 2 КСОЮ result-date search `adapter=null` и `contract_only_not_wired`, он остаётся открытым независимо от того, что контракт описан.

## Нужен период до 01.10.2019

Версия 1.0 не притворяется универсальным дореформенным краулером. Добавьте проверенный официальный adapter/registry segment или сохраните материалы в отдельной discovery-only страте. `regional_presidia_pre_2019=not_configured`; до закрытия источника итог ограничивается наблюдаемым корпусом.

## Слишком много кандидатов

Не сокращайте corpus после просмотра результата. Сохраните frozen plan, примените детерминированные query lanes, сформируйте приоритетную очередь полного текста и зафиксируйте pending/unresolved. Любая смена inclusion rule создаёт новую версию плана.

## Временная динамика не допускается

Проверьте `analysis.json`: `temporal_unassigned_chain_ids`, обе стороны каждого `interpretive_event_findings`, `comparability_approved` и `temporal_analysis_complete`. Не удаляйте неудобные цепочки и не переносите границу события после просмотра результата; исправление дат или плана требует нового проверяемого запуска.

## HTML создан, но статус не drafting-ready

Это штатно: `report` визуализирует и незавершённое исследование. Откройте `status` и устраните первое fail-closed состояние. Default report обязан показывать pending task counts, stale artifacts, open route/historical gaps, denominator scope и следующий шаг; наличие файла `report/index.html` не заменяет `validate --require-thesis-ready`.
