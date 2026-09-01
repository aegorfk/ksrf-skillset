## Context

Frozen live base: `f3647d0496c9ca524e68d041b3efa147e0372c64`. Текущий runtime manifest: 15 пакетов / 237 файлов / 8 153 384 байта.

Кандидат `skills/ksrf-argument-patterns/references/complaint-methodology-sources.md` занимает 69 194 байта и 415 строк. Он сам описывает себя как provenance/update journal, содержит историю crawl, локальные пути, source anchors и идеи сопровождения и прямо указывает, что runtime работает по автономным справочникам.

До изменения runtime-ссылки на basename существуют в `SKILL.md`, `automation-backlog.md`, root/mirrored corpus builder, generated JSON и offline verifier. Их нужно устранить или заменить до исключения.

После реализации manifest содержит 15 пакетов / 236 файлов / 8 088 532 байта, tree SHA-256 `c8bdce957da07ef45a415c9055185f3a701b2904469052b17dc78ef0be88b649` и release tree SHA-256 `cf66ca9043c7c7dd5e3585cda8d68d5d538c25c2c648d52d01e75d5f75adcc54`. Net-экономия относительно frozen base: 1 файл / 64 852 байта. Source journal сохранён с SHA-256 `6341e9870574e3473eb1831fc7eba0847f6956de06f2fd4fb200994f49b4ae26`.

## Decisions

1. **Exact source-only identity.** Исключается только package-qualified путь `ksrf-argument-patterns/references/complaint-methodology-sources.md`; basename, другие Markdown и lookalike paths не совпадают.
2. **Source retention.** Файл не удаляется, не переносится и не добавляется в `.gitignore`. Он остаётся versioned provenance и продолжает проходить source security/public-artifact checks.
3. **No dead runtime backlink.** Ни пользовательский `SKILL.md`, ни установленный reference Markdown/JSON, ни operational builder/verifier не может содержать excluded basename. Exact identity внутри portable validator остаётся необходимой policy declaration, а не пользовательским маршрутом.
4. **Successors are operational, not provenance mirrors.** Основные runtime owners: `ksrf-complaint-cycle/references/offline-practice-core.md`, `ksrf-complaint-cycle/references/strategic-complaint-design.md`, `ksrf-argument-patterns/references/evidence-maps.md`, `counterargument-playbook.md`, `science-support-pack.md`, `external-ks-complaint-webinar-methods.md` и `source-authority-and-route.md`.
5. **Builder metadata stays live.** Generated `skill_reference` больше не указывает на excluded journal и ведёт к `strategic-complaint-design.md; science-support-pack.md`; root/mirrored builder и JSON остаются согласованы.
6. **Fail-closed runtime/source split.** Runtime отвергает случайно установленный exact файл как `SOURCE_ONLY_ARTIFACT_PRESENT`; source profile допускает его identity только в source tree, но всё равно сканирует содержимое, symlink status и public-source violations.
7. **Methodology coverage is an independently reviewed artifact.** Полезная методология считается сохранённой только если каждый source-item в `methodology-coverage.md` имеет явный статус и существующий runtime anchor. Автоматические tests закрепляют exact distribution contract, два обнаруженных содержательных пробела и отсутствие dead runtime routes; полный смысловой перенос остаётся отдельным human review gate и не выдаётся за машинное доказательство.

## Methodology coverage matrix

Статусы: `retained` — правило живёт в указанном runtime owner; `superseded` — более строгий runtime gate покрывает исходное правило; `intentionally_rejected` — тезис не переносится как право, hard rule или пользовательский маршрут. Последний статус охватывает и предложенные maintainer-маршруты, которые сознательно оставлены за пределами user runtime.

| ID | Source method/check | Status | Runtime owner |
|---|---|---|---|
| M01 | Hard gates и QA отделены от стратегического решения о подаче | retained | `offline-practice-core.md` — hard gates; `strategic-complaint-design.md` — filing decision |
| M02 | Системная цель допустима лишь с индивидуальной пользой, рисками, альтернативами и сроками | retained | `strategic-complaint-design.md` — strategic filing decision |
| M03 | `FilingDecisionRecord`, информированное решение клиента и одобрение юриста | retained | `strategic-complaint-design.md` — decision record |
| M04 | Неподача: privacy-safe memorandum/card как альтернатива | retained | `strategic-complaint-design.md` — preserve-without-filing route |
| M05 | Моральное давление, непроверенная статистика и широкие политические тезисы | intentionally_rejected | `strategic-complaint-design.md` — запрет давления/ложной статистики; `source-authority-and-route.md` — source-role/state-attribution guards |
| M06 | Secondary/radar lead всегда ведёт к официальному тексту и source-role labels | superseded | `source-authority-and-route.md`; `offline-practice-core.md` — official-source gate |
| M07 | Жалоба не является ещё одной кассацией; нужен нормативный дефект | retained | `offline-practice-core.md` — anti-appeal gate |
| M08 | Quote window доказывает применение каждой нормы | retained | `evidence-maps.md` — quote-window/application evidence |
| M09 | Факты разделяются на admissibility и запрещённую переоценку | retained | `offline-practice-core.md`; `evidence-maps.md` |
| M10 | Формализм проверяется как чрезмерный барьер | retained | `counterargument-playbook.md` — formalism response |
| M11 | Секретариат — самостоятельный pre-check с ответом на возврат | retained | `counterargument-playbook.md`; `external-ks-complaint-webinar-methods.md` |
| M12 | Судебный запрос — отдельный маршрут с готовой формулой вопроса | retained | `offline-practice-core.md` — court-request route |
| M13 | Конституционный аргумент сохраняется в нижестоящих судах | retained | `external-ks-complaint-webinar-methods.md`; `evidence-maps.md` — preservation evidence |
| M14 | Просительная часть проектирует индивидуальные и системные последствия | retained | `offline-practice-core.md`; `strategic-complaint-design.md` — remedy design |
| M15 | Карта сопоставимых групп и альтернативная сохраняющая формула | retained | `strategic-complaint-design.md` — equality/cumulative burden and fallback remedy |
| M16 | Readiness подачи, документы и факты законодательства имеют отдельные паспорта | superseded | `offline-practice-core.md`; `source-authority-and-route.md` |
| M17 | Конкретное дело/прежний акт/утратившая силу норма/multi-norm анализируются причинно | retained | `offline-practice-core.md`; `evidence-maps.md` |
| M18 | Правовая определённость проверяется по окружающему регулированию | retained | `offline-practice-core.md` — `Правовая определенность` |
| M19 | Различаются акт судей, Секретариат и особое мнение | retained | `offline-practice-core.md` — former-decision comparison; `counterargument-playbook.md` — Secretariat/adverse roles |
| M20 | После решения проводится execution-gap audit | retained | `offline-practice-core.md` — execution planning |
| M21 | Инструмент выбирается до drafting: жалоба/запрос/разъяснение/application route | retained | `offline-practice-core.md` — route selection |
| M21b | После принятия отдельно проверяются форма рассмотрения, извещение, участие и материалы | retained | `offline-practice-core.md` — `После принятия обращения: отдельный gate слушания` |
| M22 | Применение, типичность практики, право, механизм и refusal risks | retained | `offline-practice-core.md`; `evidence-maps.md`; `counterargument-playbook.md` |
| M23 | Формальные требования, приложения, полномочия и пошлина — currentness-gated | retained | `offline-practice-core.md` — filing package |
| M24 | Образец служит формой/QA, но не заменяет диагностику | retained | `source-authority-and-route.md` — training/sample boundary |
| M25 | `норма -> применение -> дефект -> право -> последствие -> гарантия` | retained | `offline-practice-core.md` — `Архитектура аргумента` |
| M26 | Бремя, стандарт, критерии и оценка доказательства разделяются | retained | `ksrf-rights-argument-builder/references/evidence-impact-method.md` — evidence axes |
| M27 | Эмпирический тезис получает источник, период, знаменатель, метод и предел | retained | `source-proof-impact-patterns.md` — empirical claim passport |
| M28 | Amicus/expert — контекст и stress-test, не замена официального права | retained | `science-support-pack.md`; `strategic-complaint-design.md` |
| M29 | Просительная часть зеркалит только доказанные элементы | retained | `offline-practice-core.md`; `strategic-complaint-design.md` |
| M30 | Нормативный носитель, implicit application, fact status и externality review | retained | `strategic-complaint-design.md`; `evidence-maps.md` |
| M31 | Main/narrow remedy, state-attribution bridge, amicus map, execution and costs | retained | `strategic-complaint-design.md`; `offline-practice-core.md`; `science-support-pack.md` |
| M32 | Вебинар: barrier/two filters/four defects/non-singleton/fix norm/court request/Secretariat/remedy/red-team | retained | `external-ks-complaint-webinar-methods.md` |
| M33 | Calibration: cumulative burden/groups/conflicting practice/legislative purpose | retained | `strategic-complaint-design.md` — calibrated pattern set |
| M34 | Calibration: absolute ban/threat/less restrictive measures/competing remedy | retained | `strategic-complaint-design.md` — proportionality and competing remedy |
| M35 | Calibration: substitute guarantee; illegality/causation/fault/remedy; Secretariat response matrix | retained | `strategic-complaint-design.md` — `Четыре оси требования о восстановлении` и calibrated pattern set |
| M36 | Calibration: entrepreneurial-risk negative control and economic-effects stress test | retained | `strategic-complaint-design.md`; `science-support-pack.md` |
| C01 | Выбран правильный инструмент | retained | `offline-practice-core.md` — `Маршрут до текста` |
| C02 | Предмет — норма/смысл, не отмена судебного акта | retained | `offline-practice-core.md` — `Anti-appeal filter`, `Drafting` |
| C03 | Применение нормы доказано цитатой или причинной связкой | retained | `offline-practice-core.md` — `Матрица применения`, `Фактическое применение` |
| C04 | Право и механизм нарушения показаны | retained | `offline-practice-core.md` — `Архитектура аргумента` |
| C05 | Доводы не повторяют кассацию и не требуют переоценки | retained | `offline-practice-core.md` — `Anti-appeal filter` |
| C06 | Устойчивость проблемы исследована без превращения общественной значимости в hard gate | superseded | `evidence-maps.md` — practice map; `science-support-pack.md` — series audit |
| C07 | Исчерпание и срок проверены | retained | `offline-practice-core.md` — `Исчерпание и срок` |
| C08 | Приложения, полномочия и пошлина проверены по текущему правилу | retained | `offline-practice-core.md` — `Формальная подача и Секретариат` |
| C09 | Официальная практика найдена; международные/сравнительные материалы не обязательны | superseded | `offline-practice-core.md` — `Сравнение с прежней практикой`, `Доказательственные роли` |
| C10 | Есть ответ на типичные причины возврата/отказа | retained | `counterargument-playbook.md`; `offline-practice-core.md` — Secretariat red-team |
| C11 | Позиция сохранена в обычных судах | retained | `external-ks-complaint-webinar-methods.md` — ранняя фиксация нормы |
| C12 | Один главный дефект; multi-norm требует отдельной причинной строки | retained | `counterargument-playbook.md`; `offline-practice-core.md` — `Несколько норм` |
| C13 | Для каждой нормы есть quote window | retained | `evidence-maps.md`; `offline-practice-core.md` — `Матрица применения` |
| C14 | Факты допустимости отделены от запрещённой переоценки | retained | `strategic-complaint-design.md` — `Факты как модель действия нормы` |
| C15 | Судебный запрос содержит готовую формулу и невозможность обычного разрешения | retained | `offline-practice-core.md` — `Ходатайство о запросе суда` |
| C16 | Просительная часть проверена на индивидуальные и системные последствия | retained | `strategic-complaint-design.md` — `Портфель средств защиты`, `Исполнение и расходы` |
| C17 | Формалистский отказ проверен на разумность, достаточность сведений и чрезмерность | retained | `offline-practice-core.md` — `Формализм как барьер` |
| A01 | Maintainer methodology crawler и Zakon ingestor | intentionally_rejected | сохранены в source-only provenance/OpenSpec и удалены из runtime `automation-backlog.md` вместе с `ТЗ/...` route |
| A02 | Publication radar и claim validator | retained | `automation-backlog.md` — runtime research/verification opportunities без локальной source-зависимости |
| A03 | Admissibility, application, attachments и refusal-risk automation ideas | retained | пользовательский `automation-backlog.md` сохраняет эти bounded opportunities |
| A04 | Court-request automation как отдельный исполняемый маршрут | superseded | `ksrf-court-request-motion` заменяет идею конкретным runtime skill |

Независимый аудит обнаружил два первоначальных пробела: отдельный gate стадии слушания после принятия и четырёхосевую проверку `незаконность / причинность / вина / способ восстановления`, включая counterfactual влияния principal/reserve формулы на доступ к специальной компенсации. Они перенесены в retained successors и закреплены regression assertions. Полный one-to-one audit находится в `methodology-coverage.md` и подтверждается независимым смысловым review, а не имитируется неполным автоматическим тестом.

## Risks / Trade-offs

- Journal удобен maintainer’у для provenance; он остаётся в source checkout и исчезает только из user payload.
- Простое исключение без cleanup создало бы мёртвые ссылки; clean-room backlink test делает это release blocker.
- Матрица может декларировать покрытие шире фактического; tests проверяют уникальные anchor phrases, а независимый reviewer сверяет смысл.
- Exact allowlists canonical/portable могут разойтись; parity test обязателен.
- Generated JSON может разойтись с builder; deterministic regeneration или exact output assertion обязательны.

## Migration Plan

1. Зафиксировать OpenSpec и RED на exact identity, source retention/security, backlink cleanup и methodology coverage.
2. Обновить canonical/portable contracts, runtime routes и builder metadata; пересобрать generated JSON и manifest.
3. Прогнать полные source/runtime suites, clean-room install, strict OpenSpec и независимое ревью.
4. Опубликовать atomically в `main`, подтвердить remote SHA, установить exact global payload и архивировать change.

## Non-Goals

- Не удалять provenance journal из Git и не добавлять его в `.gitignore`.
- Не исключать другие Markdown-файлы, `automation-backlog.md`, builder или corpus JSON.
- Не расширять юридическую методологию сверх точного переноса двух выявленных source gaps; не менять official-source, authority или human filing gates.
- Не превращать basename/extension/glob в distribution rule.
