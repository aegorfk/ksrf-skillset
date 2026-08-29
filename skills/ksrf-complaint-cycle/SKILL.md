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

### 3. Докажи применение

Прочитай [implicit-application gate](references/implicit-application-gate.md). На каждую пару `норма × акт/стадия` раздельно зафиксируй:

- `norm_use_status`;
- `outcome_causation`;
- `preservation_exhaustion`;
- full-act locators и human review, подтверждённый заранее созданным host-attested approval полного record/chain fingerprint.

Итоговые статусы: `explicitly_applied`, `implicitly_applied_proven`, `application_unclear`, `not_applied`; `directly_applied` — только legacy alias. Простое упоминание, довод стороны, тематическое сходство, исход дела или оставление акта без изменения не доказывают применения.

### 4. Примени hard gates

Сначала выдай `AdmissibilityMatrix`: компетенция/субъект, конкретное дело, норма/версия, judicial use, causal harm, preservation/exhaustion, срок, continuing effect, prior-position delta, anti-fourth-instance и допустимый remedy. `Unknown` не проходит.

Результат: `GO_TO_KSRF`, `FIX_FIRST`, `COURT_REQUEST_ROUTE`, `NO_GO_KSRF` либо `ABSTAIN_PENDING_RECORD`. Не генерируй filing-ready текст при critical unknown.

### 5. Исследуй варианты и отказные аналоги

Используй `ksrf-explore-arguments` для одного–четырёх существенно разных `ConstitutionalIssueOptions`; не выбирай generic proportionality/certainty fallback молча. При empirical practice claim включи `ksrf-cassation-judicial-meaning` и claim-level gate.

Используй `ksrf-practice-authority-builder` official-first. Для отказной проверки прочитай [контракт корпуса](references/failed-complaint-corpus.md): официальный акт КС РФ, оригинальная жалоба и письмо Секретариата имеют разные evidence roles. Private cross-matter retrieval требует consent/redaction и заранее созданного host-attested approval точного производного файла. Неполное покрытие не даёт отрицательного вывода.

Покажи варианты заявителю/юристу и зафиксируй human selection principal/reserve. Для filing-significant перехода свяжи полный выбранный candidate и все его gates с заранее созданным host-attested approval. Модельный ranking и raw selection fields остаются advisory.

### 6. Составь жалобу

Используй `ksrf-complaint-facts-demands`, затем `ksrf-rights-argument-builder`. Каждый значимый факт и правовой тезис получает stable sentence ID, evidence refs, locator и предел формулировки. Unsupported/overclaimed sentence остаётся blocker или явным placeholder.

Практика ЕСПЧ через `ksrf-echr-argumentation` — optional research capability: нужен официальный HUDOC anchor, точный holding/transfer limit и отдельный российский конституционный якорь.

### 7. Проверь и выпусти

`ksrf-complaint-qa` работает outcome-blind как независимый refusal-first reviewer. После его прохода `ksrf-formal-filing-check` проверяет актуальные официальные правила и реальный `FilingPackageManifest`.

Прочитай [release contract](references/filing-package-and-release.md) и выполни `scripts/ksrf_filing_pack.py`. Первая сборка может дать только `ready_for_expert_review`. В `ready_for_human_signing_filing` комплект переводит только заранее созданный host-attested approval, связанный с полным неизменившимся release basis; для этого должны существовать DOCX/PDF, совпасть hashes, пройти semantic/visual QA, опись, свежесть и все юридические approvals. Строка с именем reviewer, caller-supplied JSON, обычный TTY и самозаявленный `verifier_id` остаются диагностикой и не повышают статус.

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

Открывай только по совпавшему trigger:

- `references/offline-practice-core.md` — автономный правовой baseline;
- `references/strategic-complaint-design.md` — стратегия предмета/remedy/исполнения;
- `references/practice-analysis-integration.md` — empirical claim gate;
- `references/docx-first-page-layout.md` — макет первой страницы;
- `references/science-support-pack.md` — роль доктрины/эмпирики;
- `references/crystal-themis-mootcourt-patterns.md` — учебный парный стресс-тест жалобы и возможного отзыва, только после закрытия evidence gates;
- `references/crystal-themis-argument-examples.md` — учебные примеры конкретных конституционных тестов по совпавшей тематике, не authority и не готовый текст;
- профильные references специализированного skill, который выполняет текущую стадию.

После изменения набора выполни `scripts/verify_offline_self_containment.py`, behavioral/trigger evals и clean-room validation.
