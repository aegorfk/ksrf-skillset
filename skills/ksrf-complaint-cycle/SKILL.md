---
name: ksrf-complaint-cycle
description: "Скилл организует полный цикл обращения в Конституционный Суд РФ, в том числе начиная с одного УИД дела или только с установленного набора skills. Он диагностирует сетап, собирает доступные акты, проверяет официальный источник и редакцию нормы, доказывает явное или имплицитное применение, предлагает конкурирующие конституционно-правовые варианты, готовит реальные DOCX/PDF и доводит комплект до человеческого подписания и подачи."
---

# Цикл жалобы в КС РФ

## Роль

Этот skill — тонкий маршрутизатор. Он хранит состояние дела и вызывает специализированные skills и deterministic scripts. Он не подменяет официальный источник, юридический hard gate или решение человека модельным score.

## Старт

1. Прочитай [машину состояний](references/router-and-state-machine.md).
2. Если пользователь установил только skills либо setup неизвестен, прочитай [профили](references/setup-profiles-and-capabilities.md), выполни `scripts/ksrf.py start --profile basic --json` и покажи пользователю все три профиля: `basic`, `research`, `expert`. Если профиль не выбран, используй `basic` только как явно названный рекомендуемый безопасный default, затем выполни `scripts/ksrf_setup_doctor.py --profile basic --json`. Ничего не устанавливай и не передавай вовне автоматически.
3. Создай или открой локальный matter по [контракту workspace](references/matter-workspace-and-artifacts.md). Пользовательские материалы по умолчанию `local_confidential`; при remote operation сначала примени [privacy gate](references/privacy-and-case-isolation.md).

## Обязательная последовательность

### 1. Собери record

Если дан УИД, сначала прочитай [UID-first workflow](references/uid-first-case-workflow.md) и используй УИД как первый вход, но не обещай полноту provider layer, которой нет. Инвентаризируй переданные файлы, raw hashes, роли и стадии; выполни OCR/visual check для сканов. Официальный endpoint, вернувший CAPTCHA/403/timeout, оставляет access gap, а не `not_found`.

Маршрутизируй первичную проверку в `ksrf-case-triage`, а процессуальную цепочку — в `ksrf-exhaustion-planner`. Для живого дела отдельно оцени `ksrf-court-request-motion`.

### 2. Проверь источник и редакцию

До допустимости прочитай [official source/version gate](references/official-source-and-version-gate.md). Для каждого filing-significant тезиса нужен официальный anchor. Casus Legal, Firecrawl, ГАРАНТ, mirrors, doctrine, embeddings и LLM — discovery/enrichment, не самостоятельная authority.

Создай `NormVersionPassport` по всем юридически значимым датам. Case-time и current filing-time редакции не схлопывай. Provider/official conflict, незакрытая amendment chain или stale anchor блокируют только зависимые claims.

Если применённая норма изменена, отменена, заменена, перенумерована либо изменился её судебный смысл, используй [сопоставление нормативного смысла](references/norm-meaning-continuity.md). Сравни прежнее и последующее регулирование по шести элементам: адресат, условие, исключения, последствие, переходное правило и подтверждённый судебный смысл. Раздельно установи прошлое применение, доказанное дальнейшее применение к старым отношениям, сохраняющийся вред и влияние новой редакции. Передай вывод в обычную проверку допустимости; эта методика не создаёт нового gate, права на повторную жалобу или нового срока.

### 3. Докажи применение

Прочитай [implicit-application gate](references/implicit-application-gate.md). На каждую пару `норма × акт/стадия` раздельно зафиксируй:

- `norm_use_status`;
- `outcome_causation`;
- `preservation_exhaustion`;
- full-act locators и human review, подтверждённый заранее созданным host-attested approval полного record/chain fingerprint.

Итоговые статусы: `explicitly_applied`, `implicitly_applied_proven`, `application_unclear`, `not_applied`; `directly_applied` — только legacy alias. Простое упоминание, довод стороны, тематическое сходство, исход дела или оставление акта без изменения не доказывают применения.

Для каждой строки с ролью `application_finding` сохрани exact текст, `claim_id`, `norm_passport_id`, `application_record_ids`, `evidence_ids` и `maximum_supported_inference`. Не считай строку подтверждённой по caller-supplied `verified|human_approved`, произвольному ID или общему индексу ролей. Перед ready release host authority обязан независимо от выбранных ID вернуть полный current chain: выбранные записи должны быть положительными, причинно значимыми и иметь current norm/preservation/application approvals; доказательства должны точно покрывать non-contradicted direct proof либо роль и speaker каждой конкретной implicit premise, а также необходимое включение более раннего акта; каждый incorporated record обязан однозначно существовать на более ранней стадии; wording и предел вывода — совпасть с заранее одобренной scope-записью, которая связывает отдельные revision/check time цепочки. Любая пропущенная поздняя стадия, unresolved incorporation, contradicted/foreign/background span, stale fingerprint/approval, перефразирование либо неполный индекс всех `application_finding` блокирует строку с её `sentence_id`, но оставляет её доступной для исправления.

### 4. Примени hard gates

Сначала выдай `AdmissibilityMatrix`: компетенция/субъект, конкретное дело, норма/версия, judicial use, causal harm, preservation/exhaustion, срок, continuing effect, prior-position delta, anti-fourth-instance и допустимый remedy. Исполняемый формат матрицы и итоговой рекомендации задан схемами `schemas/ksrf_filing/admissibility-matrix.v1.schema.json` и `schemas/ksrf_filing/ksrf-route-recommendation.v1.schema.json`; порядок локальных команд описан в [контракте исследовательских артефактов](../ksrf-explore-arguments/references/artifact-contracts.md#admissibilitymatrix-и-локальный-маршрут). `Unknown` не проходит.

Результат: `GO_TO_KSRF`, `FIX_FIRST`, `COURT_REQUEST_ROUTE`, `NO_GO_KSRF` либо `ABSTAIN_PENDING_RECORD`. Даже `GO_TO_KSRF` остаётся рекомендацией для юриста: `human_decision=pending`, `legal_assessment_automated=false`, `filing_authority=false` и `filing_performed=false`. Не генерируй filing-ready текст при critical unknown и не считай машинную валидацию разрешением подписать или подать жалобу.

### 5. Исследуй варианты и отказные аналоги

Используй `ksrf-explore-arguments` для одного–четырёх существенно разных `ConstitutionalIssueOptions`; не выбирай generic proportionality/certainty fallback молча. При empirical practice claim включи `ksrf-cassation-judicial-meaning` и claim-level gate. Самостоятельный обезличенный обзор нормы можно запустить в [ksrf-doctrine-research](../ksrf-doctrine-research/SKILL.md) как `exploratory_norm` без портфеля. Если же доктринальный вопрос выбран внутри портфеля, передай его через условный router: он требует внешний trust-root/verifier для подписанных receipts и в текущем skill boundary fail-closed блокирует `case_scoped` и `hypothesis_verification`. Не подменяй verifier самозаявленным JSON, не запускай маршрут ради украшения готового довода и не считай доктрину официальным правом или закрытием admissibility gates.

Используй `ksrf-practice-authority-builder` official-first. Для empirical practice result требуй нативную тройку: точные reliability и квитанцию финализации плюс отдельно сохранённый SHA успешного stdout. Передавай тот же внешний SHA через профиль, шестую handoff-привязку и `result import`; не восстанавливай его из самой квитанции. Одиночный reliability остаётся диагностикой `compatibility_only` и не разрешает drafting. Для отказной проверки прочитай [контракт корпуса](references/failed-complaint-corpus.md): официальный акт КС РФ, оригинальная жалоба и письмо Секретариата имеют разные evidence roles. Private cross-matter retrieval требует consent/redaction и заранее созданного host-attested approval точного производного файла. Неполное покрытие не даёт отрицательного вывода.

Если сторонняя жалоба или профессиональная публикация используется для обновления скиллов либо публичной документации, примени [контракт публичной атрибуции](references/source-authority-and-route.md#публичная-атрибуция-жалобы-и-донора). До публичного упоминания отдельно проверь активные ссылки на точный источник жалобы, профессиональный канал донора и полный итоговый акт КС РФ; неполная тройка остается внутренним provenance и не достраивается догадкой.

Если передана подборка жалоб, сначала выполни [разбор по составу и ролям](references/complaint-batch-review.md): сверь дубли и редакции, проверь полноту чтения, отдели учебные работы, фрагменты и другие процедуры; итог каждого дела проверяй отдельно. Оригиналы остаются вне публичного skillset.

Покажи варианты заявителю/юристу и зафиксируй human selection principal/reserve. Для filing-significant перехода свяжи полный выбранный candidate и все его gates с заранее созданным host-attested approval. Модельный ranking и raw selection fields остаются advisory.

### 6. Составь жалобу

Используй `ksrf-complaint-facts-demands`, затем `ksrf-rights-argument-builder`. Каждая строка получает stable sentence ID и одну явную роль из закрытого реестра `narrative|fact|court_reasoning|norm_text|legal_holding|application_finding|practice_claim|adverse_authority|requested_remedy`; значимый факт и правовой тезис дополнительно получают evidence refs, locator и предел формулировки. Не обрезай и не угадывай alias, не превращай явную неизвестную роль в `narrative`: сохрани исходное значение для исправления и поставь точный sentence-specific blocker. Missing role или legacy raw string вне просительной части можно нормализовать как явный `narrative`; в разделе `requested_remedy` отсутствующая/raw либо явно каноническая роль становится `requested_remedy`, но явная неизвестная роль сохраняется и блокирует. Ready release требует current host-attested полного ordered индекса всех строк со сквозным 1-based ordinal, exact текстом, разделом и ролью. Unsupported/overclaimed sentence остаётся blocker или явным placeholder.

Практика ЕСПЧ через `ksrf-echr-argumentation` — optional research capability. Маршрут: coverage-aware HUDOC connector/FTS -> hydrated actor-separated `ECHRArgumentPacket` -> `ResearchFinding` и влияние на `ConstitutionalIssueOptions` -> проверенный `KSRFTransferPacket` в builder -> отдельный ECHR pass в `ksrf-complaint-qa`. Нужны официальный HUDOC anchor, точный majority holding/transfer limit и отдельный российский конституционный якорь. Applicant/separate-opinion method signals и raw/vector candidates не лечат domestic admissibility gates и не становятся drafting rule автоматически. `court_reasoning_method` после independent-matter/held-out/adverse/currentness/approval gates может изменить только research checklist или архитектуру довода; substantive Russian rule и filing sentence проходят отдельный `court_authority`/Russian-anchor маршрут. Exact-byte `skill_update_approved` bundle разрешает только конкретный diff скилла; он не заменяет complaint `ReleaseGate` и не разрешает подписание или подачу жалобы.

### 7. Проверь и выпусти

`ksrf-complaint-qa` работает outcome-blind как независимый refusal-first reviewer. После его прохода `ksrf-formal-filing-check` проверяет актуальные официальные правила и реальный `FilingPackageManifest`.

Прочитай [release contract](references/filing-package-and-release.md) и выполни `scripts/ksrf_filing_pack.py`. Filing manifest `1.5` может сохранить неизвестную роль только в `blocked`-диагностике с отдельным точным blocker `sentence_role_unknown:<sentence_id>:<исходная_роль>`; похожая строка, префикс или суффикс не считаются соответствием. Явно переданная роль не обрезается и не исправляется: отсутствующая роль либо legacy raw string становятся `narrative`, blank/non-string отклоняются, остальные неизвестные значения сохраняются и блокируют выпуск. Оба ready-статуса требуют только канонические роли и ненулевой current `sentence_role_index_receipt` от host-owned реестра, который не строится из caller manifest и связывает непрерывный сквозной ordinal каждой строки, её ID, раздел, exact-text hash и роль. Дополнительно нужен host-owned полный `application_finding` index даже при `bindings=[]`; при наличии таких строк каждая обязана иметь exact current receipt, а все per-line receipts и index — один top-level `authority_revision_id`. Вложенные norm/preservation/application/scope approvals сохраняют собственные immutable IDs и не подменяют этот snapshot. Первая сборка может дать только `ready_for_expert_review`. В `ready_for_human_signing_filing` комплект переводит только заранее созданный host-attested approval, связанный с полным неизменившимся release basis; для этого должны существовать DOCX/PDF, совпасть hashes, пройти semantic/visual QA, опись, свежесть и все юридические approvals. Строка с именем reviewer, caller-supplied JSON, обычный TTY и самозаявленный `verifier_id` остаются диагностикой и не повышают статус.

Подписание, пошлина, УКЭП и отправка остаются человеческими действиями. После фактического акта КС РФ используй `ksrf-decision-execution`.

## Выход

Верни:

- capability/profile report;
- matter и record coverage;
- official source и norm-version passports;
- per-stage application evidence и AdmissibilityMatrix;
- ConstitutionalIssueOptions, adverse delta и human selection;
- SentenceEvidenceMap и working/final draft;
- независимый QA verdict;
- реальные DOCX/PDF, опись, hashes, visual QA и FilingPackageManifest;
- точные blockers, coverage limits и следующий человеческий шаг.

## Стоп-правила

- `unavailable` не равно отсутствию источника.
- `application_unclear` не равно применению и не равно доказанному неприменению.
- Human approval не лечит legal/evidence gate; без настроенного host verifier filing-significant approval остаётся недоверенным.
- Не смешивай данные разных дел и public/private corpus.
- Не называй similarity, corpus frequency, число ссылок или eval score юридическим выводом.
- Перед процессуальным действием освежай официальные нормы и ссылки.

## Дополнительные references

Для повторной жалобы или спора о доступности другого судебного порядка открой [проверку нового вопроса и способов защиты](../ksrf-complaint-qa/references/renewed-complaint-and-remedy-gap.md). Не связывай более поздний текст с прежним отказом как с его результатом.

Если материалы касаются вынужденного выбора между правовыми статусами, открой [проверку запретов совмещения](../ksrf-rights-argument-builder/references/status-incompatibility-and-qualified-silence.md). Если передано заключение amicus, сначала установи его собственный предмет по [карточке заключения и толкования](../ksrf-doctrine-research/references/amicus-interpretation-and-remedy.md); соседняя жалоба не определяет его дело.

Открывай только по совпавшему trigger:

- `references/offline-practice-core.md` — автономный правовой baseline;
- `references/strategic-complaint-design.md` — стратегия предмета/remedy/исполнения;
- `references/practice-analysis-integration.md` — empirical claim gate;
- `references/docx-first-page-layout.md` — макет первой страницы;
- `references/science-support-pack.md` — роль доктрины/эмпирики;
- `references/crystal-themis-mootcourt-patterns.md` — учебный парный стресс-тест жалобы и возможного отзыва, только после закрытия evidence gates;
- `references/crystal-themis-argument-examples.md` — учебные примеры конкретных конституционных тестов по совпавшей тематике, не authority и не готовый текст;
- профильные references специализированного skill, который выполняет текущую стадию.

Для офлайн-проверки установленного набора предпочитай `./install.sh --verify` из свежего доверенного checkout репозитория: единый repo-side координатор связывает корень target между структурным preflight и postflight, применяет строгий полный runtime-профиль и автономный контракт ядра/UID без сети и без исполнения target-side policy. Прямые `scripts/verify_offline_self_containment.py` и `scripts/validate_ksrf_skillset.py --profile runtime --strict` используй только как раздельный диагностический fallback, честно отмечая, откуда взята политика и что нет общей preflight/postflight-границы. Если пользователь явно просит сравнить установку с текущим опубликованным `main`, используй repo-side `./install.sh --verify-current`, а не валидатор внутри проверяемого target. Код `0` означает только совпадение устойчивого до и после сетевого окна локального runtime-отпечатка с манифестом зафиксированного commit `main`, `10` — известное отличие (старый, настроенный, более новый/неопубликованный либо локально изменённый набор), а `20` сохраняет пробел сети или проверки. При отсутствии доверенного repo-side entry point сообщи пробел, не выдавай target-side проверку за независимое подтверждение. Behavioral/trigger evals выполняются только из source checkout перед публикацией; runtime-проверка и сетевое сравнение не заменяют source/release QA, проверку актуального права или полномочие на подачу.
