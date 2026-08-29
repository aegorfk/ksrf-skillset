# Проектирование

## Маршрут поиска

1. Сначала получить `hudoc_stats` и сохранить generation, число searchable/current/stale variants, FTS/privacy status и semantic blockers.
2. При неполной проекции разрешить только честный bounded FTS-discovery. Пустая выдача означает лишь отсутствие совпадения в текущем покрытии.
3. Dense/hybrid использовать только при `semantic_discovery_status=ready_unpromoted` и полном generation-bound audit.
4. Искать раздельно по actor/function/source-role: заявитель, государство, третье лицо, большинство Суда, отдельное мнение, редакционный материал.
5. Для точной цитаты открыть `hudoc_get_case_details`, сверить официальный HUDOC URL, itemid, application number/date, family, page/paragraph/sentence-or-char locator и source/artifact SHA.

## ECHRArgumentPacket

Пакет содержит:

- identity: `itemid`, `matter_key`, application number, дата, document family, язык;
- provenance: официальный HUDOC URL, source/artifact SHA, page, paragraph, sentence/char locator, точный фрагмент;
- attribution: `source_actor`, `source_function`, `source_role`, `source_form`, `speaker_verified`, `court_treatment`; non-unclear treatment ссылается на отдельный hydrated majority-response packet либо bounded review record;
- argument: `argument_function`, relation, test family/step, adverse/distinguishing material;
- transfer: применимость по времени, currentness, различия контекста и remedy, доказуемый российский официальный конституционный якорь и связанный `KSRFTransferPacket`;
- lifecycle: candidate/verified/cross-case/approved, blockers и разрешённый reuse target. Immutable lifecycle approval record и SHA input bundle необходимы для cross-case, но недостаточны для изменения скилла. `skill_update_approved` требует отдельный exact-byte bundle: frozen base tree/files, diff, fixtures, passing report и held-out binding, immutable public trust-registry snapshot с key provenance, а также две attestations разных trusted reviewer/approver по одному approval subject.

Semantic profile, snippet и cluster label не являются точной цитатой. Applicant submission, even reproduced in a judgment, не является original application или holding Суда.

## Интеграция в KSRF

- `ksrf-echr-argumentation` владеет поиском, атрибуцией, packet и transfer boundary.
- `ksrf-explore-arguments` принимает пакет как `ResearchFinding`, ведёт supporting/adverse lanes и формирует влияние на `ConstitutionalIssueOption`.
- `ksrf-rights-argument-builder` использует только проверенную мотивировку большинства как comparative support; заявитель и отдельное мнение дают method/counterargument signal.
- `ksrf-complaint-qa` проверяет цитату, actor/function/form/treatment, temporal/currentness/adverse и российский anchor.
- `ksrf-complaint-cycle` только маршрутизирует; международный материал не лечит domestic admissibility gates.

## Method-only слой

Можно сразу переиспользовать как исследовательский checklist, без изменения материально-правового правила:

- actor-response triangle;
- search → hydration → official-anchor proof chain;
- norm/meaning → application/causation → right → defect/harm → test/alternative/safeguards/remedy;
- positive-obligation decomposition `trigger/scope/content/breach`;
- scope/interference/justification separation;
- less-restrictive alternative, safeguards и remedy как отдельные поля;
- adverse/currentness/temporal/distinguishing pass;
- особое мнение только как research signal;
- различение judgment/decision/communicated/summary.

## Проверка и публикация

Каждый изменённый скилл проходит quick validation и negative evals. Release выполняется одним commit из чистого publish-worktree, push в `aegorfk/ksrf-skillset:main`, live SHA verification и только затем синхронизация канонических глобальных скиллов.
