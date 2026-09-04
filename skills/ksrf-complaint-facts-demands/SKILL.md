---
name: ksrf-complaint-facts-demands
description: Скилл готовит факты, конституционный вопрос и просительную часть жалобы в КС РФ из материалов дела и утверждённого портфеля гипотез. Он применяется, чтобы связать точную редакцию нормы с явным или доказанным имплицитным применением и вредом, создать SentenceEvidenceMap, предложить основную и более узкую формулы требования и не подгонять фактуру под заранее заданный паттерн.
---

# Факты и просительная часть жалобы в КС РФ

## Общий контракт filing-readiness

Используй только проверенные `NormVersionPassport`, per-stage application records и выбранные человеком issue options. Положительный application/selection gate должен иметь заранее созданный host-attested approval полного объекта по `../ksrf-complaint-cycle/references/router-and-state-machine.md`; raw reviewer/approved fields диагностические. Каждый filing-significant тезис оформляй как `SentenceEvidenceMap` по `../ksrf-complaint-cycle/references/filing-package-and-release.md`; отсутствие evidence/locator остаётся blocker или явным placeholder.

Для каждой строки в разделе `requested_remedy` сохрани собственные `claim_id`, `issue_option_id`, `norm_passport_id` и canonical unique `application_record_ids`; её роль нельзя понизить до `narrative`, а supplied sentence ID обязан быть strict и уникальным. В complaint держи plural `issue_option_ids`. Singular alias, непустой `evidence_ids` и caller-supplied `verified/passed/filing_ready` не создают membership и не являются authority. Перед render/release line resolver обязан заново вернуть exact issue/application/passport/source snapshots и полные content-bound gate requests/receipts, а отдельный host index resolver — полный current set всех remedy-линий из authoritative draft registry. Source receipt связывает ID, claim/norm/edition, SHA, revision, verifier, time и locator; host IDs/locators принимаются только как canonical raw strings без coercion. Cross-claim, cross-edition, stale, unknown, duplicate, удалённая из multi-line manifest или unbound строка остаётся `BLOCKED` с её stable sentence ID по контракту `../ksrf-complaint-cycle/references/filing-package-and-release.md`.

## Порядок работы

1. Если даны материалы, собери `CaseFile` и `AutonomousIntakeRecord` по `../ksrf-complaint-cycle/references/ksrf-tool-layer.md`. Сам восстанови событийную хронологию, ранжируй спорные нормы и выведи проверяемую цепочку права и последствия; не проси пользователя заранее подготовить эти сведения.
2. Точно зафиксируй оспариваемую норму: акт, статья, часть/пункт, редакция, дата, номер и официальный источник.
3. Строй факты хронологически, оставляя статус заявителя, попытки реализовать право, непосредственный вред, применение нормы, сохранённые доводы и исчерпание. Пометь каждый существенный факт: `установлено судом`, `следует из документа и не оспорено`, `утверждение стороны`, `оспаривается` или `не подтверждено`.
4. По каждой судебной стадии фиксируй довод, speaker role, вывод суда, смысл нормы и точное цитатное окно. Отличай применение от упоминания. При отсутствии прямой ссылки собирай conjunctive pack по `../ksrf-complaint-cycle/references/implicit-application-gate.md`; полный pack даёт `implicitly_applied_proven` только после проверки заранее созданного host-attested approval полного record и всех chain fingerprints, а любое отсутствующее звено — `application_unclear`.
5. До связного текста собери карту `норма -> судебный смысл -> правовое последствие -> заявленный конституционный вред` по `references/norm-application-defect-map.md`. Если approved hypothesis использует более точную причинную структуру, добавь её как отдельную карту.
   Для общих, повторяемых и индивидуальных фактических посылок отдельно заполни `references/constitutional-facts-evidence-ledger.md`; системная статистика не заменяет факт применения к заявителю, а единичный случай не доказывает общий механизм.
   Если спор касается социального права или фактической доступности гарантии, используй `../ksrf-rights-argument-builder/references/social-rights-institutional-evidence.md`: отдельно покажи российский правовой якорь, паспорт индикатора, стадии access funnel и individual bridge. Не смешивай формальный отказ, проигрыш по существу и отсутствие исполнения.
   Если общие условия перекрывают специальную восстановительную гарантию, заполни [матрицу реального доступа](references/reparative-guarantee-access.md): докажи статус и применение каждого положения, проверь замкнутое условие, альтернативы, пределы статистики и встречные интересы. Раздели входной учёт, предоставление, законодательное исправление и пересмотр.
6. Для доказательственного спора укажи предмет, бремя, стандарт, доступ к сведениям, последствие недоказанности и нормативный носитель. Затем пройди `references/evidence-inference-and-dependency-audit.md`: отследи смену burden/presumption по стадиям, проверь rival explanation и evidential anchors, построй dependency graph против двойного учёта. Без носителя не превращай переоценку доказательства в конституционный вопрос; научные и Legal-AI модели остаются critic/eval и не устанавливают факт.
7. Получи principal/reserve hypotheses из утверждённого `ArgumentPortfolio`. Не выбирай 1–3 корпусных паттерна и не переписывай факты ради совпадения с библиотекой.
8. Сформулируй вопрос КС РФ для каждой жизнеспособной линии, сохраняя один фактический baseline. Покажи, чем principal и reserve отличаются по механизму, тесту или remedy.
9. Подготовь не менее двух уровней remedy, если это юридически возможно:
   - основная формула, устраняющая выявленный механизм;
   - более узкий конституционно-правовой смысл или гарантия, не предрешающие факты.
   Для сложной позитивной обязанности отдельно проверь диалоговый вариант: участники, предмет, временная защита, срок, отчётность, контроль и эскалация. Если дефект одновременно требует практического результата для заявителя и общего исправления, заполни `references/remedy-design-matrix.md` и проведи single-track red team. Включай любой сравнительно найденный элемент только при наличии российского нормативного якоря, компетентного адресата и законного downstream-маршрута.
   Для выбора модели нормативной коррекции и проверки исключения из общего правила используй `../ksrf-argument-patterns/references/constitutional-argument-architecture.md`: обоснуй точный дефект, минимальную коррекцию, затронутых лиц, переходный риск и официальное полномочие.
10. Сверь каждую часть требования с фактическим крючком, verified finding и полномочиями КС РФ. Для principal и reserve создай независимые remedy bindings: доказательство, application record, selected issue и редакция нормы должны принадлежать той же claim-линии; общую фактическую основу допускай только через current claim-scoped source receipt. Не проси отменить судебный акт или установить обстоятельства.
11. Для каждой активной линии укажи, какой практический результат устраняет дефект и каким процессуальным маршрутом он может быть реализован после решения.
12. Направь почти готовый проект в `ksrf-complaint-qa`.

## Формулы как варианты, а не шаблон

Формула `в той мере, в какой` полезна, когда точно назван вредный смысл. Для неопределённости, пробела, конфликта, переходного режима, процессуальной гарантии или позитивной обязанности структура может отличаться. Выбирай формулу из механизма и remedy portfolio; объясняй, почему она уже или шире альтернативы.

## Вывод

- `Проверенная фактура`;
- `Цитатные окна применения`;
- `Причинная карта`;
- `Principal/reserve questions`;
- `Primary/narrower relief formulas`;
- `Post-decision route`;
- `Фактические крючки и evidence ids`;
- `Несогласованности с портфелем`;
- `Недостающие материалы`;
- `Следующий скилл`.

## Ограничения

- Не исправляй пробелы выдуманными фактами.
- Не маскируй обычную апелляцию конституционными формулами.
- Не считай красивую просительную формулу доказательством дефекта.
- Не включай внешние материалы без роли, источника и verification status.

## Справочники

- `../ksrf-complaint-cycle/references/offline-practice-core.md` — автономная причинная архитектура, multi-norm матрица и правила зеркальности требования.
- `../ksrf-complaint-cycle/references/strategic-complaint-design.md` — статусы фактов, фактическое применение и портфель допустимых результатов.
- `../ksrf-complaint-cycle/references/source-authority-and-route.md` — маршрут и source registry.
- `references/workflow-reference.md` и `references/norm-application-defect-map.md` — факты, применение и зеркальность требования.
- `references/norm-system-and-gap-qualification.md` — системная карта нормы, квалификация пробела/молчания/коллизии, законодательный ответ, remedy-vacuum guard и secondary evidence lanes с current-law, corpus и human gates.
- `references/remedy-design-matrix.md` — двухконтурный результат, single-track critic, необратимый вред и competence gate для отложенных/диалоговых вариантов.
- `references/constitutional-facts-evidence-ledger.md` — doctrinal/reviewable/case-specific fact levels, freshness, burden и individual bridge без импорта американского процессуального режима.
- `references/evidence-inference-and-dependency-audit.md` — lifecycle бремени/презумпции, rival-explanation graph, evidential anchors, dependency/double-count audit и red-team объяснения Legal AI с российским нормативным gate.
- `../ksrf-rights-argument-builder/references/social-rights-institutional-evidence.md` — социальные факты, качество индикаторов, access funnel и fail-closed проверка институционального довода.
- `../ksrf-argument-patterns/references/constitutional-argument-architecture.md` — типы нормативной коррекции, двухтезисная проверка исключения и consequence/competence gates.
- `references/complaint-patterns.md` — исполняемые маршруты поиска позиции, карты практики, вариантов требования, портфеля материалов и проверки сохранения довода.
- `../ksrf-argument-patterns/references/language-formulas.md` — проверяемые варианты формулировок после выбора линии человеком.
- `../ksrf-complaint-cycle/references/ksrf-defect-taxonomy.md` — словарь возможных дефектов.
- `../ksrf-complaint-cycle/references/science-support-pack.md` — роль доктрины/эмпирики в фактах и приложениях.
- `../ksrf-complaint-cycle/references/sko-complaint-methods-2017-2026.md` — конфигурация просимого результата, граница истолкования и проверка полного механизма remedy.
