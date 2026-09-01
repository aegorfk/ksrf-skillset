# Привязка тезиса практики к выпускаемой жалобе

`drafting_ready` и portable result подтверждают готовность исследовательского набора к центральной проверке. Они не дают права вставить эмпирический тезис в DOCX/PDF только по `finding_id`, локальному SHA или статусу `verified`.

## Раздельные идентичности

Для каждой выпускаемой строки `role=practice_claim` сохраняй раздельно:

- `claim_id` — конституционное требование выбранного `IssueCandidate`;
- `practice_claim_id` — идентификатор `PracticeClaimGate` и exact claim текущего practice-analysis ledger;
- `issue_option_id` — выбранный issue;
- `evidence_ids` — канонический уникальный набор exact `finding_id` из текущего wording review;
- `maximum_supported_inference` — строка, byte-equal текущему `maximum_permitted_claim`;
- точный текст строки — byte-equal текущему `wording_review.wording_text`.

Не угадывай соответствие между конституционным и эмпирическим claim. Host обязан доказать обе идентичности и их связь с выбранным issue.

## Что должен заново проверить host

На каждой сборке, проверке manifest, экспертном одобрении и финальной проверке перед подписью host:

1. Из своего реестра разрешает `matter_id + draft_id` в exact `case_id`, practice workspace revision и input-manifest fingerprint. Caller path не принимается.
2. Запускает current filing-stage validation и выбирает exact `practice_claim_id`.
3. Требует для него `state=ready`, `draft_blocked=false`, присутствие в `allowed_claim_ids`, отсутствие claim blockers и global integrity errors. Изолированный blocker другого claim оставляет нативный отчёт `valid=false`, `stage_verdict=partial`, но не меняет состояние target claim только при точном совпадении report/state ID-списков и error-set со всеми иными blocked claims; `valid=true` при `partial` считается противоречием.
4. Открывает current content-bound research request и imported v2 result по их `handoff_id`, заново вычисляет `request_sha256` и claim-set, требует точного совпадения canonical request/result claim bindings, затем сверяет plan/evidence/fingerprint SHA, selected proofs, finding records, exact `claim_wording` самого finding и его candidate, supporting/adverse sets, quality bindings, attachment и trust anchor. В multi-claim result exact-set относится ко всем findings, содержащим target `practice_claim_id`; structurally valid finding только другого bound claim не считается доказательством target и не создаёт ложный blocker.
5. Сверяет current `within_limit` wording review, exact finding set, текст и `maximum_permitted_claim`.
6. Требует current pre-filing refresh с `valid=true`, полным `ready_claim_set_sha256`, corpus cutoff и отсутствием более позднего material event. Research request создан до attachment/result; `recorded_at` refresh идёт после всех native material events каждого claim полного ready-set, filing generation/validation — после refresh, authority `checked_at` — после validation; `as_of`, день записи и день проверки совпадают.
7. Заново строит `issue_approval_requests()` и проверяет два независимых trusted approvals: `practice:<practice_claim_id>` и `selection`; selection должен оставаться `principal` либо `reserve`, а trusted approval IDs должны различаться.

Authority response сначала один раз отделяется от внешнего mutable/stateful `Mapping`, а затем только этот snapshot используется и для проверки, и для receipt. Повторное чтение host-объекта после валидации запрещено.

Caller-поля `verified`, `human_approved`, `ready`, `passed`, чужой receipt или собственный fingerprint ничего из этого не заменяют.

## Полнота draft

Per-line receipt недостаточен: строку и receipt можно удалить вместе либо переименовать роль в `narrative`. Поэтому host draft registry независимо возвращает полный индекс всех `practice_claim` строк exact matter/draft:

- `sentence_id`, `section_code`, `role`;
- `claim_id`, `practice_claim_id`, `issue_option_id`;
- `practice_binding_sha256`.

Индекс обязателен и при `bindings=[]`. Он не строится из переданного caller manifest и не подменяется `practice-analysis/claim-index.json`: исследовательский индекс не знает состав конкретного draft.

Все per-line receipts и полный индекс должны нести один `authority_revision_id`; per-line receipts дополнительно должны совпадать по workspace revision и input-manifest fingerprint. Individually valid receipts из разных snapshot не складываются в готовый пакет.

## Стоп-правила

- Вымышленный, лишний, повторный, строково-коэрцированный или cross-claim finding → release blocked.
- Изменение текста, claim revision, result, selected proofs, source, attachment, trust anchor, wording review, ceiling, issue selection, approval или refresh → старый receipt не действует.
- Practice approval без отдельного trusted selection approval → release blocked.
- Один trusted approval ID, повторно использованный для practice и selection, → release blocked.
- Claim receipts и index из разных authority/workspace snapshot → release blocked.
- Текущий target claim `too_strong`, `unclear`, stale или иначе не `ready` → release blocked.
- Удаление, вставка, замена или downgrade роли относительно host draft index → release blocked.
- Технически зелёный binding остаётся candidate evidence gate: он не разрешает юридическое одобрение, merge, global install, подпись, оплату, отправку или подачу.
