---
name: ksrf-complaint-cycle
description: "Организовать полный цикл обращения в Конституционный Суд РФ, в том числе начиная с одного UID дела: самостоятельно собрать доступные акты, определить надлежащий маршрут, проверить допустимость, предложить конкурирующие конституционно-правовые варианты, дать go/no-go рекомендацию, подготовить и проверить жалобу, пройти формальную подачу и спланировать исполнение решения."
---

# Цикл жалобы в КС РФ

## Принцип

Управляй циклом по модели `жёсткая процессуальная оболочка -> адаптивное исследование -> ручной выбор -> drafting -> независимая проверка`. Не фиксируй конституционно-правовое обоснование до исследования и не считай существующие паттерны закрытым перечнем допустимых линий.

## Порядок работы

### 1. Определи маршрут и собери дело

1. Сначала прочитай `references/offline-practice-core.md`: это автономное практическое ядро, достаточное без Telegram, внешних методических сайтов и проектных корпусов.
2. Затем прочитай `references/strategic-complaint-design.md`: он добавляет паспорт нормативного носителя, доказательство фактического применения, проверку внешнего эффекта решения и проектирование исполнения.
3. Прочитай `references/source-authority-and-route.md` и различи:
   - индивидуальную/коллективную жалобу;
   - ходатайство стороны перед обычным судом;
   - запрос суда по конкретному делу;
   - запрос управомоченного публичного субъекта;
   - действия по исполнению решения КС РФ.
4. Если дан UID, считай его предпочтительным и достаточным первым входом. Прочитай `references/uid-first-case-workflow.md`, самостоятельно разреши UID, скачай доступные полные акты по всем ожидаемым стадиям, построй матрицу покрытия и создай `UIDCaseDossier`. Нулевое число найденных стадий не является полнотой: цепочка остаётся `unknown`, пока существование и состав производства не подтверждены официально.
5. Если даны материалы, проект или папка либо уже собран каталог по UID, обязательно запусти автосбор по `references/ksrf-tool-layer.md` и используй `CaseFile`. До вопросов пользователю создай `AutonomousIntakeRecord`: ранжированные кандидаты спорной нормы, событийную хронологию, гипотезы затронутого права и непосредственного правового последствия. Не выдавай автоматически извлечённый кандидат за подтверждённую норму или факт.
6. До статуса `document missing` выполни source-completeness pass:
   - рекурсивный inventory файлов и соседних тематических каталогов;
   - поиск по имени/типу документа независимо от наличия текстового индекса;
   - детект PDF без текстового слоя;
   - OCR image-only PDF с маркировкой candidate text;
   - визуальную сверку страниц для юридически значимых locators;
   - фиксацию path, hash/версии, page count, provenance и redaction limits.
7. Не приравнивай отсутствие full-text hit к отсутствию документа. Используй OCR, визуальное чтение и альтернативное извлечение средствами среды выполнения; не проси пользователя вручную перепечатать или юридически классифицировать документ. Только после исчерпания пакета и официального поиска можно запросить конкретный отсутствующий акт или узкий факт.

### 2. Примени жёсткие пороги

Используй `ksrf-case-triage` и `ksrf-exhaustion-planner`. В `AdmissibilityMatrix` отдельно проверь:

- компетенцию, надлежащего заявителя и конкретное дело;
- точную оспариваемую норму, допустимый нормативный носитель и её редакцию;
- судебное применение с цитатным окном;
- признаки нарушения права именно в результате применения;
- исчерпание и годичный срок;
- продолжающийся эффект и прежние решения по тому же вопросу;
- anti-appeal filter и надлежащий маршрут.

Происхождение источников, полноту материалов и точность цитат вынеси в `EvidenceGate`, privacy scope и human approval — в `ReleaseGate`. Сначала выдай `AdmissibilityMatrix`; только после неё переходи к оценке содержательных линий. `Unknown` не является `pass`, а карточка дела или поисковый сниппет не заменяют полный акт применения.

Для жалобы частного лица внутри матрицы отдельно докажи prima facie субъективную заинтересованность: регулируемое отношение, применение нормы, индивидуальный правовой эффект и признаки нарушения права именно нормой. Веди `private/admission` и `public/objective norm-control` как два связанных ledger; системная важность не лечит отсутствие допуска.

Если порог не пройден, не компенсируй его качеством правовой позиции. Для неустранимого fail сразу верни `NO_GO_KSRF`; при критическом unknown после полного поиска — `ABSTAIN_PENDING_RECORD`; при реально устранимом пробеле — `FIX_FIRST`. Не требуй и не фабрикуй `ConstitutionalIssueOptions`, когда содержательное исследование заблокировано. Если дело продолжается, отдельно оцени `ksrf-court-request-motion` и `COURT_REQUEST_ROUTE`.

### 3. Запусти адаптивное исследование

Используй `ksrf-explore-arguments` до сборки правовой позиции. Исследование должно:

- начинаться с нейтрального профиля нормы, применения и вреда;
- проверить несколько направлений, включая направление против исходной версии;
- сохранить evidence-backed findings и отрицательные результаты;
- создать минимум две существенно разные гипотезы, если hard gate не блокирует работу;
- провести отдельный critic pass;
- вернуть principal/reserve/experimental/rejected portfolio.

До `ConstitutionalIssueOptions` запусти исполняемый `PracticeAnalysisGate` из `scripts/ksrf_practice_analysis.py` и следуй `references/practice-analysis-integration.md`. Он сканирует каждый кандидат/абзац и создаёт append-only `PracticeClaimLedger`. Если линия зависит от повторяемого судебного смысла нормы, расхождения, временной или межокружной динамики, количества решений, системности либо «неработоспособности» закона, состояние конкретного claim становится `required`: передай установленному `ksrf-cassation-judicial-meaning` только portable v2 `unproven_research_questions` с нейтральными вопросами, disconfirmation prompts, claim hashes и ссылками/хешами актов заявителя. Предварительный тезис не маркируй как finding.

Обратно принимай только artifact-derived portable v2 `approved_bounded_findings`/`authority_cards`, связанные с исходным request, текущими claim/fingerprint/plan/evidence hashes и proof records: selected positions/relations/adverse, нормативный мост, `validation-report.json` и `human-decision.json`. До drafting обязательно сверь bundle с внешним trust anchor из предшествующего `run attach`: sibling CLI перечитывает исходный request и доказательства в прикреплённом кассационном workspace. Внутренние SHA-256 без этой сверки означают лишь `audit_only_unanchored`. После anchored import нужен отдельный reviewed `within-limit` для точной текущей формулировки и её source-file hash. Legacy v1, неизвестный ID, неполный proof, stale binding, неполный охват или непройденный gate оставляют claim как `blocked`/`stale` и текст как `hypothesis_under_test`/`insufficient_coverage`; независимые claims и обычные hard gates продолжают свой маршрут.

Используй `ksrf-argument-patterns`, стенограммы, матрицы обоснований, `../ksrf-argument-patterns/references/external-ks-complaint-webinar-methods.md` и graph/retrieval как генераторы кандидатов и stress-test. Вебинарный материал помогает проверить нормативный барьер, неединичность практики, раннюю фиксацию нормы, ходатайство о запросе суда и риск неблагоприятного системного эффекта; он не является официальной позицией КС РФ. Отсутствие известного паттерна — риск исследования, но не автоматический отказ.

При применимом Lawinfo-триггере используй `../ksrf-argument-patterns/references/lawinfo-constitutional-methods-2023-2026.md`: проведи четыре семейства атак на существенный довод, раздели формальную и материальную определённость, а пропорциональность не сворачивай в единый score. Эти карточки направляют исследование, но не являются правом.

Если вопрос касается исторической модели жалобы, формы оспариваемого акта, письма/возврата Секретариата, старого правила срока/исчерпания, доказательств, письменного производства, вида решения, обязательности позиции либо исполнения, дополнительно открой `references/lawinfo-historical-complaint-procedure-2009-2024.md`. Применяй только совпавшую JH-M карточку как critic/reference layer: она не меняет текущий hard gate, а любой процессуальный вывод требует актуального официального якоря.

Если доступен CasusLegal MCP или пользователь передал практику высших судов, используй `ksrf-practice-authority-builder`, чтобы превратить результаты поиска в case-scoped authority ledger: назначить актам функции, проверить переносимость, найти adverse/refusal-позиции и отделить doctrine КС РФ от доказательства судебного смысла в практике ВС РФ. Недоступность подписки фиксируй как coverage gap и не делай ее препятствием для автономного исследования.

### 4. Дай варианты и получи решение человека

Если hard gates допускают исследование, представь заявителю или юристу `ConstitutionalIssueOptions`: для каждого варианта объясни проблему простыми словами, покажи норму и вредный смысл, предполагаемое право, механизм нарушения, доказательства за и против, вероятный отказ и основной/узкий remedy. Проси выбрать principal/reserve среди готовых вариантов, а не самостоятельно назвать нарушенное право или спорную норму. До drafting юрист должен утвердить principal и, при наличии, reserve hypothesis либо вернуть портфель на исследование. Запиши причину выбора и не скрывай adverse findings. Валидный JSON или лучший score не заменяют human approval.

После admissibility и исследования в каждом деле дай предварительную `KSRFRouteRecommendation`: `GO_TO_KSRF / FIX_FIRST / COURT_REQUEST_ROUTE / NO_GO_KSRF / ABSTAIN_PENDING_RECORD`. Обоснуй её hard gates, пользой для заявителя, рисками, альтернативами и ближайшими сроками без ложной числовой точности.

Если ожидаемая перспектива низкая либо цели включают фиксацию позиции, официальный след или системный эффект, создай `FilingDecisionRecord` по `references/strategic-complaint-design.md`. Раздельно зафиксируй legal readiness, прогноз, пользу и риски для клиента, альтернативы со сроками и предварительное решение `file_now / strengthen_ordinary_case_first / defer_until / do_not_file`. Стратегическая цель не устраняет hard gate и не меняет содержательный QA verdict.

### 5. Собери текст вокруг утверждённого портфеля

1. Используй `ksrf-complaint-facts-demands`, чтобы подготовить факты, связку применения, вопрос и несколько допустимых формул требования. Факты не подгоняются под известный паттерн.
2. Для утвержденных principal/reserve hypotheses проверь authority ledger через `ksrf-practice-authority-builder`; в drafting передавай только записи с понятной ролью, locator, transfer limit и завершенным adverse pass.
3. Перед передачей любого эмпирического абзаца в authority ledger выполни claim-level lint и `validate --stage drafting`; допускается только `supported_bounded` при state `ready`. Заблокированный claim можно оставить placeholder-гипотезой, не останавливая независимые разделы.
4. Используй `ksrf-rights-argument-builder`, чтобы превратить principal/reserve hypotheses и проверенный authority ledger в самостоятельные разделы с источниками, пределами и counterarguments.
5. Для каждого требования веди трассировку `норма -> судебный смысл -> непосредственное последствие -> конституционный вред -> предлагаемая гарантия -> приложение`.
6. Если причинная цепочка иной структуры лучше объясняет дело, используй её, но сохрани проверяемые anchors для нормы, применения, вреда и remedy.
7. При подготовке DOCX применяй единый макет первой страницы из `references/docx-first-page-layout.md`: шапка отдельным блоком на правой половине страницы, а заголовок — только `ЖАЛОБА` и `на нарушение конституционных прав и свобод`. Перечень оспариваемых норм в подзаголовок не выноси.

### 6. Подготовь вспомогательные материалы

До включения тезиса внеси его в реестр источников: функция, точное место, авторитетность, verification status и риск. Международные, сравнительные, исторические, научные, статистические и экспертные материалы могут:

- породить новую гипотезу;
- поддержать или ослабить существующую;
- показать alternative remedy или counterexample.

Они не заменяют российский нормативный якорь и судебное применение. Неофициальный материал используется как lead/checklist до проверки по официальному источнику.

Для широкого доктринального поиска маршрутизируй вопрос через `../ksrf-argument-patterns/references/constitutionalist-authority-corpus.md`. В case-scoped ledger переноси конкретную работу и тезис, а не весь профиль автора. Записи `academic_indexed`, `bibliographic_lead` и особенно `discovery_only` требуют проверки первичной публикации до использования.

### 7. Проверь, подай и исполни

1. Перед `ksrf-complaint-qa` выполни `validate --stage qa`; он блокирует только активные empirical claims без current `ready`/`within-limit`, а не всю жалобу. Перед формальной подачей выполни `validate --stage filing` с текущим pre-filing refresh.
2. Используй `ksrf-complaint-qa` для hard gates, portfolio coherence, source traceability, refusal model и remedy fit.
3. До формальной подачи финализируй `FilingDecisionRecord`, если сработал его триггер: требуется информированное решение клиента и отдельное одобрение юриста без давления символической или общественной целью.
4. Используй `ksrf-formal-filing-check` только после содержательного verdict и human approval.
5. После акта КС РФ используй `ksrf-decision-execution` для последствий, пересмотра, разъяснения, исправления или применения в аналогичных делах.

## Выходы

- `Карта маршрута и hard gates`;
- `UIDCaseDossier` и матрица покрытия, если входом был UID;
- `AdmissibilityMatrix` до содержательной оценки;
- `ConstitutionalIssueOptions` для выбора заявителем или юристом;
- `Case-scoped research ledger`;
- `Argument portfolio` с adverse findings и critic report;
- `PracticeAnalysisGate`, `PracticeClaimLedger`, claim-level lint и pre-filing refresh при empirical trigger;
- `Human selection record`;
- `FilingDecisionRecord` при низкой перспективе или символических/системных целях;
- `KSRFRouteRecommendation` для каждого разобранного дела;
- `План/проект жалобы` с evidence traceability;
- `Содержательный QA verdict`;
- `Формальный filing pack`;
- `Мемо по исполнению`.

## Общие правила

- Финальные процессуальные документы пиши по-русски; иностранные материалы используй через перевод или русское изложение с приложением.
- Перед процессуальным действием проверяй действующие официальные нормы и правила.
- Не делай доступ к Telegram, Zakon.ru, проектной папке или исходному research-корпусу условием выполнения: используй встроенное автономное ядро; внешние вторичные источники нужны только для обновления или provenance.
- Не запускай полный цикл, если достаточно точечного скилла.
- Не выдавай pattern match, retrieval similarity, количество ссылок или scalar score за юридический вывод.
- Не смешивай findings разных дел; публичные источники и обезличенная методика переиспользуются отдельно от фактов стороны.
- Веди видимый список проблем, отклонённых гипотез и причин остановки исследования.

## Справочники

- `references/offline-practice-core.md` — автономная методология полного цикла без runtime-зависимости от внешней фактуры.
- `references/strategic-complaint-design.md` — автономное стратегическое проектирование предмета, применения, аргумента, результата и исполнения.
- `references/source-authority-and-route.md` — маршрут, иерархия источников, реестр тезисов и причинная трассировка.
- `references/ksrf-tool-layer.md` — автосбор `CaseFile` и проверяемые evidence refs.
- `references/uid-first-case-workflow.md` — маршрут `один UID -> скачанное досье -> допустимость -> варианты проблемы -> go/no-go` с минимальным взаимодействием.
- `references/ksrf-defect-taxonomy.md` — язык возможных дефектов и анти-паттерны; используй как словарь гипотез, не обязательную классификацию.
- `references/docx-first-page-layout.md` — единый воспроизводимый макет шапки и заголовка первой страницы жалобы в DOCX.
- `references/ksrf-embedded-guides.md`, `references/ksrf-live-argument-patterns.md`, `references/crystal-themis-*` — эвристики drafting и состязательного stress-test.
- `../ksrf-argument-patterns/references/*` — corpus/retrieval/evidence/language/critic materials; их роль и ограничения определяет активная гипотеза.
- `../ksrf-argument-patterns/references/external-ks-complaint-webinar-methods.md` — профессиональная методика подготовки жалобы: два фильтра, четыре дефекта, формула просительной части, ходатайство о запросе суда, ответ на возврат Секретариата и red-team последствий; не заменяет ФКЗ, Регламент и официальные акты.
- `../ksrf-argument-patterns/references/constitutional-methodology-reference-only-corpus.md` — self-contained слой 84 revise/comparative карточек для option generation, red-team и transfer limits; behavior и hard gates не меняет.
- Сравнительные workbooks по стадиям: `../ksrf-argument-patterns/references/comparative-argument-coding.md`, `../ksrf-argument-patterns/references/legal-reasoning-model-branches.md`, `../ksrf-argument-patterns/references/precedent-analogy-and-justification.md`, `../ksrf-argument-patterns/references/institutional-discourse-and-comparative-transfer.md`, `../ksrf-argument-patterns/references/constitutional-institutions-access-and-remedy.md`, `../ksrf-rights-argument-builder/references/proportionality-and-lawmaking-workbook.md`, `../ksrf-complaint-facts-demands/references/constitutional-facts-evidence-ledger.md`, `../ksrf-complaint-facts-demands/references/remedy-design-matrix.md`, `../ksrf-decision-execution/references/german-remedy-and-institutional-patterns.md` и `../ksrf-decision-execution/references/compliance-forecast-matrix.md`. Если тезис выходит за пределы одного дела и описывает линию практики, системность или фактический effect, сначала заполни `../ksrf-practice-authority-builder/references/judicial-meaning-evidence-acquisition.md`. Все эти файлы дают optional method/critic cards и не заменяют российские первичные источники.
- Российская научная методика аргументации: `../ksrf-argument-patterns/references/constitutional-argument-architecture.md` для построения/атаки довода, `../ksrf-complaint-qa/references/argument-quality-revision.md` для quality/revision review и `../ksrf-complaint-qa/references/meta-argumentation-qa.md` для trigger-check баланса, идентичности и эволюции. Все справочники вторичны: текущие нормы, полномочия и позиции подтверждаются официально.
- `../ksrf-practice-authority-builder/SKILL.md` — CasusLegal-backed authority ledger, проверка переносимости, adverse-практики и drafting blocks.
- `../ksrf-cassation-judicial-meaning/SKILL.md` — опциональное автономное исследование кассационного судебного смысла до тезиса; обмен только через версионированные файлы, без импорта кода между скиллами.
- `references/science-support-pack.md` — проверка роли научных, эмпирических и экспертных материалов.
- `references/sko-complaint-methods-2017-2026.md` — полнотекстовые методические карточки СКО по аргументации, доступу, remedy, истолкованию и исполнению.
- `references/russian-secondary-constitutional-procedure-crosscheck.md` — учебный и историко-доктринальный навигатор, включая Зорькина (2021) и Витрука (1998), по доказательствам, пакету обращения, допустимости, решениям и исполнению; авторская/институциональная атрибуция не превращает тезис в holding, любое поле требует актуального официального российского anchor и later-law check.
- `references/lawinfo-historical-complaint-procedure-2009-2024.md` — автономный реестр 38 статей и 13 JH-M карточек по нормативному предмету, screening/refusal, versioned exhaustion, evidence roles, видам/силе/исполнению решений и model conflicts; только reference-only refinement.
- `../ksrf-argument-patterns/references/lawinfo-constitutional-methods-2023-2026.md` и JSON рядом — источник происхождения и маршрутизация 15 российских методических карточек 2023–2026, включая конфликтный ledger абсолютного права; PDF из inbox не является runtime-зависимостью.

## Проверка автономности

После обновления KSRF-набора запускай `scripts/verify_offline_self_containment.py`. Проверка требует, чтобы все `ksrf-*` skills ссылались на встроенное ядро, а ядро и точки входа не содержали внешних runtime-зависимостей.
