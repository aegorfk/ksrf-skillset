## Context

KSRF-навыки уже разделяют официальные акты, практику, факты дела и методологические материалы, но доктрина до этого попадала в работу несистемно. Новый контур должен быть отраслево нейтральным, работать как до получения дела, так и после установления применённого смысла, не передавать частные материалы внешним сервисам и не повышать discovery-метаданные до юридического тезиса.

Публичный skillset использует фиксированный allowlist из 14 пакетов и отказывается синхронизироваться, если в глобальном каталоге появился необъявленный `ksrf-*`. Добавление пятнадцатого пакета поэтому является одноразовой миграцией самого release contract: чистый live preflight выполняется до правок, затем тот же versioned copier вызывается с обновлённым allowlist, manifest связывается с прежним live base и весь переход публикуется одним commit.

## Goals / Non-Goals

**Goals:**

- воспроизводимо находить научную проблематику по любой применённой отраслевой норме;
- сохранять происхождение, coverage и точную степень проверки каждого источника и тезиса;
- строить позиции, контрпозиции, кандидаты дефекта и falsifiable конституционные гипотезы;
- блокировать утечку частных query anchors и смешение результатов разных запусков;
- использовать только разрешённые интерфейсы и оставить покупку/оплату человеку;
- опубликовать пакет как пятнадцатый canonical KSRF skill.

**Non-Goals:**

- автоматически доказывать неконституционность, действующее право, применение нормы или факты;
- считать число публикаций голосованием либо citation count авторитетностью;
- обходить paywall, CAPTCHA, robots/ToS или автоматизировать банковское подтверждение;
- обещать полноту всей российской юридической науки;
- предписывать единственный конституционный довод до анализа конкретного дела.

## Decisions

1. **От нормы к проблеме, а не от конституционной статьи к подтверждению.** Запросы строятся по норме, судебной формуле, спорному элементу, механизму, последствию, процедуре, remedy, истории и adverse. Это уменьшает confirmation bias; конституционный мост появляется только после локализации отраслевого сбоя.
2. **Три режима с разными gates.** `exploratory_norm` выдаёт только norm-scoped candidates. `case_scoped` требует редакцию, публичный судебный смысл, механизм, последствие и ссылки на evidence. `hypothesis_verification` требует полный текст, исходные гипотезы и adverse-pass.
3. **Двухслойный процесс.** CLI детерминированно делает discovery, provenance и coverage. Атрибуция тезиса выполняется только при full-text/page verification человеком или вызывающим агентом.
4. **Разрешённые адаптеры и capability routing.** V1 автоматизирует Crossref и OpenAlex по документированным API; отсутствие ключа или интерфейса создаёт gap. CyberLeninka, eLIBRARY, СПС, каталоги и AI-search остаются ручными либо будущими adapters до проверки условий.
5. **Fail-closed privacy.** Все query-bearing поля имеют строгие типы. Для двух case-aware режимов человек одобряет точный `query_plan_hash`; mismatch блокирует сеть до записи.
6. **Fail-closed run identity.** Request hash, query plan hash и `search-run-config` hash связывают providers, query IDs и bounds с coverage. Частичный ответ, schema error либо stale artifact не считается завершённым bounded run.
7. **Консервативная дедупликация.** Автоматическое слияние выполняется по DOI/EDN/ISBN. Без сильного идентификатора записи остаются раздельными до ручного family review, чтобы не слить разные издания.
8. **Оплата как human gate.** Система готовит acquisition queue, проверяет открытые/библиотечные альтернативы и может подготовить счёт, но `payment_authorized` по умолчанию false.
9. **Одноразовая миграция allowlist.** До правок проверены clean checkout, expected remote и live SHA. После обновления allowlist используется тот же `install_skillset.py` для exact manifest-covered copy; затем генерируется manifest, выполняются полные проверки и один atomic push. После публикации обычный sync должен пройти без diff.

## Risks / Trade-offs

- **[Шум библиографических индексов]** → lexical priority считается только очередью чтения; содержательная релевантность требует full-text pass.
- **[Неполный российский охват]** → `coverage_complete=false`, точные provider gaps и отсутствие отрицательных выводов.
- **[False positive/negative privacy regex]** → строгие схемы и human approval hash для case-aware режимов.
- **[Доктрина маскируется под право]** → `cannot_satisfy`, claim types, page locators и обязательный official-first handoff.
- **[Старая выдача выглядит новой]** → run-config/provider/hash cross-check и новый workspace для иного request.
- **[Цена гибкости работодателя недооценена]** → обязательный adverse-pass и отдельные falsifiers.

## Migration Plan

1. Проверить глобальный пакет и его unit/eval/skill validation.
2. На чистом publish-worktree проверить live `origin/main`; зафиксировать base SHA.
3. Обновить canonical validator и 15-package allowlist, выполнить exact copy всех KSRF packages.
4. Добавить OpenSpec, README и publication docs, сгенерировать manifest от live base.
5. Выполнить validator, unit tests, clean-room install, manifest/publication verification и secret/runtime audit.
6. Создать один scoped commit, push `HEAD:main`, проверить live SHA.
7. Выполнить штатный sync уже на опубликованном clean HEAD; он должен завершиться без diff.

Rollback выполняется только новым явным release, который удаляет пакет из allowlist и переносит его имя в документированную retired policy; автоматического destructive rollback нет.

## Open Questions

- Нужен ли отдельный разрешённый adapter для CyberLeninka или достаточен ручной browser route?
- Будет ли локальный Zotero обязательным источником первого приоритета или опциональным provider?
- Какие подписные соглашения позволяют API/экспорт из eLIBRARY, Гарант и КонсультантПлюс без нарушения лицензии?
- Следует ли в следующей версии добавить Crossref/OpenAlex forward-citation graph и отдельный quality-eval на российской юридической выборке?
