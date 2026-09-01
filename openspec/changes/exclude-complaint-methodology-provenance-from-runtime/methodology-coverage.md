# One-to-one audit переноса методологии

Источник аудита — tracked `skills/ksrf-argument-patterns/references/complaint-methodology-sources.md` на frozen base `f3647d0496c9ca524e68d041b3efa147e0372c64`. Инвентари URL, crawl-счётчики, локальные имена файлов, списки постов и high-signal anchors не включены: это provenance, а не пользовательское правило. Операционные source-boundary тезисы не скрыты этим исключением: они разобраны построчно ниже; два чисто distribution/provenance тезиса вынесены в отдельную таблицу.

Статусы:

- `retained` — правило имеет операционный runtime-owner;
- `superseded` — runtime применяет более строгий или более актуальный gate;
- `intentionally_rejected` — тезис не переносится как право, hard rule или пользовательский маршрут.

Сокращения:

- `OPC` — `skills/ksrf-complaint-cycle/references/offline-practice-core.md`
- `SCD` — `skills/ksrf-complaint-cycle/references/strategic-complaint-design.md`
- `SAR` — `skills/ksrf-complaint-cycle/references/source-authority-and-route.md`
- `SCI` — `skills/ksrf-complaint-cycle/references/science-support-pack.md`
- `CP` — `skills/ksrf-argument-patterns/references/counterargument-playbook.md`
- `EM` — `skills/ksrf-argument-patterns/references/evidence-maps.md`
- `EWM` — `skills/ksrf-argument-patterns/references/external-ks-complaint-webinar-methods.md`
- `SPI` — `skills/ksrf-argument-patterns/references/source-proof-impact-patterns.md`
- `EIM` — `skills/ksrf-rights-argument-builder/references/evidence-impact-method.md`
- `FFC` — `skills/ksrf-formal-filing-check/SKILL.md`
- `CRM` — `skills/ksrf-court-request-motion/SKILL.md`
- `AB` — `skills/ksrf-argument-patterns/references/automation-backlog.md`

## Distribution/provenance boundaries вне юридической методики

| Source line | Boundary | Статус | Owner |
|---|---|---|---|
| 3 | Provenance-журнал не нужен для подготовки жалобы; runtime автономен | retained | `tools/skillset_file_contract.py`, `install.sh`; `OPC` — автономное ядро |
| 315 | Telegram-выгрузки нужны только для provenance/discovery; runtime работает по встроенным справочникам | retained | exact source-only contract; `OPC`, `SCD` |

## Источники и маршруты

| Source line/item | Метод | Статус | Runtime anchor |
|---|---|---|---|
| 29 | Учебная авторасшифровка — методический курс, а не официальный нормативный материал | retained | `SAR` — `Стенограммы заседаний`, уровень 4 |
| 31 | Машинная стенограмма остаётся вторичной; цитаты, нормы, реквизиты, статистику и текущие выводы нужно сверять по аудио/официальным источникам | retained | `SAR` — `Стенограммы заседаний`, официальная опора |
| 33 | Неофициальный Telegram-канал — discovery-слой, а не самостоятельная нормативная опора | retained | `SAR` — уровни 1 и 3; `AB` — publication radar |
| 35 | Zakon.ru — вторичный экспертный корпус для эвристик, framing и QA; действующее правило проверяется по официальным актам | retained | `SAR` — уровни 1 и 3 |
| 37 | Экспертный Telegram-корпус даёт discovery/методологию, но не нормативную опору без официальной проверки | retained | `SAR` — уровни 1 и 3 |
| 39 | Telegram-batch — training/source-discovery/legislative radar; финальные тезисы проверяются по официальным источникам | retained | `SAR` — уровни 1, 3 и 4; `AB` — publication radar |
| 41 | Practice-intelligence даёт failure modes для admissibility/drafting/filing/execution; процессуальные правила и реквизиты проверяются по первичным источникам | retained | `SAR` — уровни 1 и 3; `OPC` — source-role gate |
| 51 | Низкая перспектива не запрещает подачу, но отделяется от readiness | retained | `SCD` — `Решение о подаче при низкой ожидаемой перспективе` |
| 52 | Цели клиента, польза, риски, альтернативы и сроки | retained | `SCD` — поля `FilingDecisionRecord` |
| 53 | Информированное решение клиента и отдельное одобрение юриста | retained | `SCD` — `approvals` |
| 54 | Меморандум/обезличенная карточка как альтернатива подаче | retained | `SCD` — `alternatives_and_deadlines` |
| 58 | Моральное давление и обязанность подавать «ради общества» | intentionally_rejected | `SCD` — прямой запрет давления |
| 59 | Непроверенные проценты и статистика обращений | intentionally_rejected | `SCD` — запрет ложной точности; `SPI` — паспорт эмпирического тезиса |
| 60 | Общий тезис «исполнения нет» | superseded | `OPC` — `Проектирование последствий`, `Аудит фактического исполнения` |
| 61 | Политические/исторические формулы без нормы и state bridge | intentionally_rejected | `SAR` — source roles; `SCD` — `state-attribution bridge` |
| 74 | Telegram как publication radar | retained | `AB` — `ksrf-publication-radar` |
| 75 | Переход от secondary lead к официальному тексту | retained | `AB` — `ksrf-publication-radar`; `SAR` — official-source gate |
| 76 | Извлечение реквизитов и remedy вместо вторичной цитаты | retained | `AB` — поля `decision-update` |
| 77 | Commentary не равен binding position | retained | `SAR` — source roles; `SCD` — состязательная карта |
| 78 | Тематические сборники как discovery leads | retained | `AB` — `collection-signal` |
| 82 | `decision-update` | retained | `AB` — `ksrf-publication-radar` |
| 83 | `uncertainty-signal` | retained | `AB` — `ksrf-publication-radar` |
| 84 | `remedy-signal` | retained | `AB` — `ksrf-publication-radar` |
| 85 | `collection-signal` | retained | `AB` — `ksrf-publication-radar` |
| 86 | `commentary-signal` только для гипотез | retained | `AB` и `SCD` — lead boundary |
| 98 | Anti-appeal: дефект нормы вместо последней кассации | retained | `CP` — anti-appeal; `OPC` — `Anti-appeal filter` |
| 99 | Цитатное доказательство применения | retained | `CP` — quote window; `OPC` — `Матрица применения` |
| 100 | Факты только как юрисдикционный слой | retained | `CP`; `OPC` — `Паспорт конкретного дела` |
| 101 | Формализм как чрезмерный барьер | retained | `OPC` — `Формализм как барьер`; `CP` |
| 102 | Секретариат как самостоятельный pre-check | retained | `CP`; `FFC` — formal gate |
| 103 | Почти готовый судебный запрос | retained | `OPC` — `Ходатайство о запросе суда`; `CRM` |
| 104 | Сохранение конституционного аргумента снизу | retained | `EWM` — ранняя фиксация; `EM` — preservation evidence |
| 105 | Проектирование последствий в требовании | retained | `OPC` — `Проектирование последствий`; `SCD` — `Портфель средств защиты` |
| 106 | Карта сопоставимых групп и последствий | retained | `EM` — equality map; `SCD` — remedy portfolio |
| 107 | Основная и сохраняющая формулы | retained | `CP`; `SCD` — основной и более узкий результат |
| 132 | Telegram как lead/training/commentary | retained | `SAR`; `SCD` — состязательная карта |
| 133 | Модельные материалы не доказывают право | retained | `SAR` — training/sample boundary |
| 134 | При живом деле сначала проверить судебный запрос | retained | `CRM` — route trigger |
| 157 | Авторские и рекламные practitioner-каналы — practice lead, а не доказательство права или положительный класс допустимости | retained | `SAR` — уровни 1 и 3; duplicate boundary 132–133 |
| 321 | Refusal-risk lead из медийного изложения требует перехода к официальному акту | retained | `SAR` — official-source gate; duplicate boundary 33/75 |
| 322 | Медийная фактура полезна для состязательной карты, но не является источником права | retained | `SAR` — source-role labels; `SCD` — состязательная карта; duplicate boundary 77 |
| 135 | ГАС, «Мой арбитр», SudAct как фиксированный набор gates | superseded | `FFC` — source-agnostic acquisition/channel gates |
| 136 | Разные материалы получают разные доказательственные роли | retained | `OPC` — `Доказательственные роли` |
| 137 | Паспорт законопроекта | retained | `OPC`; `SPI` — legislative fact passport |
| 138 | Паспорт институционального факта | retained | `OPC` — institutional currentness |
| 139 | Международный материал и переходный режим | retained | `OPC` — international/domestic effect separation |
| 161 | Конкретное дело и причинная роль нормы | retained | `OPC` — case/application matrix |
| 162 | Сравнение прежнего решения по норме, вопросу, смыслу и последствию | retained | `OPC` — `Сравнение с прежней практикой КС РФ` |
| 163 | `continuing-effect pack` | retained | `OPC` — отменённая/утратившая силу норма |
| 164 | Отдельная причинная строка по каждой норме | retained | `OPC` — `Несколько норм` |
| 165 | Окружающее регулирование для legal certainty | retained | `OPC` — `Правовая определенность`; `EM` |
| 166 | Доверенность, суммы, реквизиты и сроки из каналов | superseded | `OPC` и `FFC` — current official check |
| 167 | Различение акта КС, материала Секретариата и особого мнения | retained | `OPC` — former-decision roles; `CP` — Secretariat/adverse roles |
| 168 | Execution gap audit | retained | `OPC` — `Аудит фактического исполнения` |
| 191 | Жалоба, запрос, разъяснение, применение позиции, экспертный материал | retained | `SAR` — route taxonomy; `OPC` — `Маршрут до текста` |
| 192 | Выбор инструмента до drafting | retained | `SAR`; `OPC` |
| 193a | Проверка типичных ошибок | retained | `CP`; `FFC` |
| 193b | Отдельный gate стадии слушания после принятия | retained | `OPC` — `После принятия обращения: отдельный gate слушания` |
| 212 | Прямое применение и цитатные окна | retained | `OPC` — `Матрица применения` |
| 213 | Неединичность и противоположные подходы | retained | `EM`; `SCI` — series/practice audit |
| 214 | Конкретное право и механизм нарушения | retained | `SCD` — constitutional argument; `OPC` — causal chain |
| 215 | КС, международный материал, comparative и эксперт | retained | `SAR`; `OPC` — ограниченные evidence roles |
| 216 | Факты/ошибка суда вместо нормативного дефекта | retained | `OPC` — `Anti-appeal filter` |
| 234 | Не просить отменить судебный акт | retained | `OPC` — `Drafting` |
| 235 | Предмет — норма/акт/правоприменительный смысл | retained | `OPC` — route и causal architecture |
| 236 | Право, применение, срок и исчерпание | superseded | `OPC` — зависимая цепочка hard gates; `FFC` |
| 237 | Содержание обращения | retained | `FFC` — filing content |
| 238 | Приложения и полномочия | retained | `FFC` — package gate |
| 252 | Запрос суда как отдельный маршрут | retained | `CRM` |
| 253 | Почему дело нельзя разрешить без проверки нормы | retained | `CRM` — impossibility bridge |
| 254 | Готовая формула вопроса и связь с исходом | retained | `CRM` — request formulation |
| 265 | Образец только для формы и red-team | retained | `SAR` — training/sample boundary |
| 266 | Нормативный дефект вместо недовольства исходом | retained | `OPC` — `Anti-appeal filter` |
| 267 | Хронология, механизм, норма, право и исчерпание | retained | `OPC` — case passport and causal chain |
| 268 | Фиксированный маршрут до ВС и годичный срок из старого гайда | superseded | `OPC` — dynamic route/current-law check; `SAR` |
| 279 | Полезность средства для доверителя независимо от отношения к институту | retained | `SCD` — externality and filing decision |
| 280 | КС не исправляет оценку доказательств и мотивировку | retained | `OPC` — `Anti-appeal filter` |
| 281 | Раннее сохранение позиции | retained | `EWM`; `EM` |
| 282 | Универсальная фиксированная лестница исчерпания | superseded | `OPC` — route tree/final relevant act |
| 283 | Имплицитное применение без прямой ссылки | retained | `SCD` — `implicit-application pack` |
| 284 | Одна главная проблема вместо россыпи нарушений | retained | `CP` — defect focus |
| 285 | Конституционная позиция видна в обычных жалобах | retained | `EWM`; `EM` |
| 286 | Аналогичные дела и последствия после постановления | retained | `OPC` — post-decision map; `EM` |

## Локальная методологическая дельта

| Source line/item | Метод | Статус | Runtime anchor |
|---|---|---|---|
| 290 | Материал не становится правом без первичного источника | retained | `SAR` — source hierarchy |
| 294 | Нумерованные вопросы, comparative table и расчёт последствий | superseded | `SCD` — structured argument/externality; `EM` |
| 295 | Amicus как карта гипотез, не нейтральная позиция | retained | `SCD` — `Экспертный и amicus-пакет`; `SPI` |
| 296 | Эксперт: практика, comparative и системный эффект; риск перегруза | retained | `SCD`; `SPI` |
| 297 | Паспорт законодательного факта и зеркальность требования | retained | `OPC` — legislative passport and drafting |
| 298 | Межотраслевая причинная цепочка, `в той мере, в какой`, OCR-check | retained | `OPC` — causal chain/drafting; `SAR` — OCR boundary |
| 302 | Предмет, бремя, стандарт, критерии и конкретное доказательство | retained | `EIM` — evidence axes |
| 303 | Критический checklist судебного запроса и OCR boundary | retained | `CRM`; `SAR` |
| 307 | `норма -> применение -> дефект -> право -> вред -> гарантия` | retained | `OPC` — `Архитектура аргумента` |
| 308 | Бремя, стандарт, критерии и оценка доказательства раздельны | retained | `EIM` — evidence axes |
| 309 | Полный эмпирический паспорт | retained | `SPI` — empirical claim passport |
| 310 | Ограниченная роль amicus/эксперта | retained | `SCD`; `SPI` |
| 311 | Зеркальность доказанных элементов и отдельная опора последствий | retained | `OPC` — drafting; `SCD` — remedy portfolio |
| 328 | Паспорт нормативного носителя | retained | `SCD` — `Паспорт нормативного носителя` |
| 329 | `implicit-application pack` | retained | `SCD` — `Фактическое применение без прямой ссылки` |
| 330 | Статусы фактов | retained | `SCD` — `Факты как модель действия нормы` |
| 331 | `precedent-externality review` | retained | `SCD` — `Проверка внешнего эффекта решения` |
| 332 | Principal и более узкий результат | retained | `SCD` — `Конституционная аргументация и варианты результата` |
| 333 | `state-attribution bridge` и профессиональная легитимация | retained | `SCD` — `Частный спор и профессиональная гарантия` |
| 334 | Amicus и состязательная карта | retained | `SCD` — sections 7–8 |
| 335 | Исполнение, компенсация и расходы заранее | retained | `SCD` — section 12 |
| 353 | Профессиональные страницы не являются обязательной позицией | retained | `SAR`; `FFC` — current-law check |

## Вебинарные методы

| Source line/item | Метод | Статус | Runtime anchor |
|---|---|---|---|
| 359a | Нормативный барьер | retained | `EWM` — нормативный барьер |
| 359b | Два фильтра | retained | `EWM` — два фильтра |
| 359c | Четыре дефекта | retained | `EWM` — четыре дефекта |
| 359d | Неединичность практики | retained | `EWM` — эвристика, не hard gate |
| 359e | Ранняя фиксация нормы | retained | `EWM` — preservation |
| 359f | Ходатайство о запросе | retained | `EWM` — court request |
| 359g | Просительная формула | retained | `EWM` — prayer |
| 359h | Ответ Секретариату | retained | `EWM` — Secretariat response |
| 359i | Неблагоприятный системный эффект | retained | `EWM` — red-team consequences |
| 361 | Пошлины, региональные нормы, редакции и исчерпание из Q&A | intentionally_rejected | `EWM` и `FFC` требуют актуальной официальной проверки |

## Калибровочный пакет

| Source line/item | Метод | Статус | Runtime anchor |
|---|---|---|---|
| 365 | `ComplaintSourceAttribution` | retained | `SAR` — attribution contract |
| 369a | `cumulative-burden map` | retained | `SCD` — `Кумулятивная нагрузка` |
| 369b | Сопоставимые группы | retained | `EM` — equality map |
| 369c | Карта противоречивой практики | retained | `EM`; `SCI` |
| 369d | Цель регулирования и конечное бремя | retained | `SCD` — proportionality/cumulative burden |
| 370a | Абсолютный запрет против конкретной угрозы | retained | `SCD` — `Абсолютный запрет` |
| 370b | Менее ограничительные меры | retained | `SCD` — proportionality alternatives |
| 370c | Competing preserving interpretation | retained | `SCD` — preserving model |
| 370d | Формальный отказ не равен удовлетворению | retained | `SCD` — refusal boundary |
| 374 | Подмена обязательной гарантии | retained | `SCD` — `Подмена обязательной гарантии` |
| 375a | Незаконность | retained | `SCD` — `Четыре оси требования о восстановлении` |
| 375b | Причинность | retained | `SCD` — `Четыре оси требования о восстановлении` |
| 375c | Вина | retained | `SCD` — `Четыре оси требования о восстановлении` |
| 375d | Способ восстановления | retained | `SCD` — `Четыре оси требования о восстановлении` |
| 375e | Влияние principal/reserve prayer на доступ к специальной компенсации | retained | `SCD` — `remedy-access counterfactual` |
| 376 | Матрица ответа на уведомление | retained | `SCD` — `Ответ на уведомление Секретариата` |
| 377 | Негативный контроль функциональной эквивалентности | retained | `SCD` — `Негативный контроль замещающего правомочия` |
| 381 | Ограниченный consequence/economic stress-test | retained | `SCD` — `Последствия как вторичный стресс-тест` |
| 382 | Обращение, preliminary check, допустимость, применение и merits | superseded | `EWM`, `FFC`, `SAR` — current workflow |
| 384 | Privacy-safe анализ и запрет публичной атрибуции без доказательств | retained | `SAR` — `ComplaintSourceAttribution` |

## Итоговый чеклист 1–17

| Source line/item | Проверка | Статус | Runtime anchor |
|---|---|---|---|
| 388/C01 | Правильный инструмент | retained | `SAR`; `OPC` — route selection |
| 389/C02 | Норма/смысл, не отмена решения | retained | `EM`; `OPC` — drafting |
| 390/C03 | Применение нормы | retained | `OPC` — application matrix |
| 391/C04 | Право и механизм | retained | `OPC`; `SCD` |
| 392/C05 | Anti-appeal | retained | `OPC` — anti-appeal filter |
| 393/C06 | Типовая/общественно значимая проблема как обязательный пункт | superseded | `EM`/`SCI` проверяют устойчивость; значимость не hard gate |
| 394/C07 | Исчерпание и срок | retained | `OPC`; `FFC` |
| 395/C08 | Приложения, представитель и пошлина | retained | `FFC` |
| 396/C09 | Обязательные прежние позиции КС/международные материалы | superseded | `OPC`: adverse search нужен, близкая аналогия не обязательна |
| 397/C10 | Ответ на причины отказа | retained | `CP`; `FFC` |
| 398/C11 | Сохранение позиции снизу | retained | `EWM`; `EM` |
| 399/C12 | Один главный дефект с multi-norm exception | retained | `CP`; `OPC` — `Несколько норм` |
| 400/C13 | Quote window по каждой норме | retained | `CP`; `EM`; `OPC` |
| 401/C14 | Факты допустимости отдельно от переоценки | retained | `SCD`; `CP` |
| 402/C15 | Готовая формула судебного запроса | retained | `CRM` |
| 403/C16 | Последствия, иные лица, компенсация и временный порядок | retained | `SCD` — sections 6 and 12 |
| 404/C17 | Формалистский барьер | retained | `OPC` — `Формализм как барьер` |

## Идеи автоматизации

| Source item | Статус | Runtime/source owner |
|---|---|---|
| `methodology-source-crawler` | intentionally_rejected | сохранён только в tracked source-only provenance/OpenSpec; удалён из `AB` |
| `zakon-rubric-methodology-ingestor` | intentionally_rejected | сохранён только в tracked source-only provenance/OpenSpec; удалён из `AB` |
| `ksrf-publication-radar` | retained | `AB` — user-operational discovery backlog |
| `admissibility-gate` | retained | `AB`; существующие hard gates показывают частичную реализацию |
| `norm-application-finder` | retained | `AB`; `OPC`/`EM` задают контракт результата |
| `attachments-checker` | retained | `AB`; `FFC` задаёт checklist |
| `refusal-risk-checker` | retained | `AB`; `CP` задаёт refusal taxonomy |
| `court-request-builder` | superseded | исполняемый `CRM` заменяет backlog-идею конкретным runtime skill |

## Source-only maintainer notes, удалённые из user payload

### `methodology-source-crawler`

- кандидат реализации: crawler утверждённых источников; исполняемого скрипта в репозитории сейчас нет, поэтому до запуска нужен отдельный OpenSpec change и реализация в публикационном checkout;
- сохранять HTML, документы и `crawl_index.json` в maintainer inbox `ТЗ/Гайды/Новое/constitutional_methodology_sources`;
- отделять методологическое ядро от широкого сайта-шума;
- обновлять tracked provenance journal только после ручного review;
- новые продуктовые идеи сначала оформлять отдельным OpenSpec change.

### `zakon-rubric-methodology-ingestor`

- собирать индекс рубрики Zakon.ru `Конституционное право` через `Redesign/ListByRubric/List/36/...`;
- скачивать публичные тексты, извлекать `div.typical` и исключать комментарии/сервисные блоки;
- строить срез по жалобе, Секретариату, допустимости, судебному запросу, пересмотру, правоприменительному смыслу и компенсации;
- отделять новости и мнения от переносимых drafting/QA эвристик;
- обновлять provenance только после ручной проверки и не считать Zakon.ru нормативным source of truth.

## Review boundary

Этот файл — доказательство независимого смыслового аудита, а не машинное утверждение эквивалентности текстов. Автоматические тесты отдельно проверяют exact source-only identity, no-overmatch, source security, reverse-sync, clean runtime backlinks, builder/JSON invariant и два найденных substantive gap. Финальный release требует обе группы доказательств.
