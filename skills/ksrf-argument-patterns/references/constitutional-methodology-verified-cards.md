# Проверенные карточки конституционно-правовой методологии

Срез: **15 августа 2026 года**. Источник: wave `32-author-wave-2026-08-11` — 103 effective r3 method cards, 103 passed effective source reviews, 103 effective legal reviews и полный effective v2 conflict graph из 1 199 review-required связей. Этот файл — provenance-reference, а не самостоятельный источник действующего права и не разрешение автоматически менять поведение skills.

## Правило использования

1. Доктринальная карточка помогает выбрать вопрос, структуру проверки, форму вывода или hard negative.
2. Российское правовое утверждение и средство защиты подтверждай актуальной Конституцией РФ, ФКЗ о КС РФ и официальным актом КС РФ на дату задачи.
3. Не переносить имя автора как аргумент авторитета. В memo нужны точный тезис, locator, роль, предел и официальный российский якорь.
4. `behavior_candidate_pending_eval` не является действующей новой инструкцией: до завершения eval и явного human approval используй её только как исследовательскую гипотезу.
5. `reference_only_exact_overlap` означает, что полезная функция уже присутствует в skillset; не создавать второй тест или второй workflow.
6. `supporting_reference` сохраняет независимое происхождение и ограничения общей функции, но не создаёт отдельное поведенческое правило.
7. Model-semantic `passed` не является человеческим одобрением: human gate остаётся обязательным, а неполный legacy semantic-fingerprint gate запрещает promotion.

Legal reviews ниже имеют `law_as_of=2026-08-14`. Любое более позднее изменение официального права переводит зависимый вывод в `needs_revalidation`.

## Канонический реестр 19/19

| Card ID | Автор и работа | Проверенная функция | Source locator | Legal fit | Integration role | Материальный предел |
| --- | --- | --- | --- | --- | --- | --- |
| `cmc-khabrieva-review-remedy-01` | Т. Я. Хабриева, *Избранные труды. Том 2: Конституционный контроль* | матрица `требование → компетенция → юридический эффект` | печ. 21; PDF 23; гл. I §1 | `direct` | `behavior_candidate_pending_eval` | историческая классификация не устанавливает современные полномочия; эффект нормы не равен автоматической отмене индивидуального акта |
| `cmc-khabrieva-applied-meaning-02` | Т. Я. Хабриева, та же работа | сопоставление текста нормы, официального толкования и доказанной практики | печ. 24–25; PDF 26–27; гл. I §1 | `direct` | `reference_only_exact_overlap` | одно дело не доказывает устойчивую практику; применение и исчерпание проверяются отдельно |
| `cmc-khabrieva-lawmaking-focus-03` | Т. Я. Хабриева, та же работа | локализация дефекта в нормотворчестве, иерархии либо индивидуальном применении | печ. 21–23; PDF 23–25; гл. I §1 | `direct` | `reference_only_exact_overlap` | проявление дефекта в деле не исключает нормативного вопроса; чистая ошибка идёт в обычное обжалование |
| `cmc-khabrieva-court-routing-04` | Т. Я. Хабриева, *Правовая охрана Конституции* | карта `обычный суд / запрос суда / индивидуальная жалоба` | печ. 121–123; PDF 123–125; гл. V | `direct` | `behavior_candidate_pending_eval` | запрос суда и жалоба гражданина не взаимозаменяемы; обычные средства защиты не пропускаются |
| `cmc-khabrieva-restriction-audit-05` | Т. Я. Хабриева, та же работа | раздельная проверка формы, цели, необходимости, масштаба и существа права | печ. 124–125; PDF 126–127; гл. V | `direct` | `reference_only_exact_overlap` | сначала доказать право и вмешательство; стадийность не объявлять универсальной для всех прав |
| `cmc-morshchakova-rights-perimeter-01` | Т. Г. Морщакова, *Конституционная защита прав и свобод граждан судами Российской Федерации* | поиск конституционно значимого содержания непоименованного притязания | печ. 124; PDF 125 | `direct` | `behavior_candidate_pending_eval` | открытый каталог не превращает любое моральное или сервисное притязание в право; нужна официальная опора |
| `cmc-morshchakova-unified-meaning-04` | Т. Г. Морщакова, та же работа | вертикальная карта обязательного нормативного смысла | печ. 128; PDF 129 | `direct` | `reference_only_exact_overlap` | точный holding и сопоставимость нормы, редакции и фактов обязательны; пересмотр не автоматичен |
| `cmc-kokotov-transition-guarantees-04` | А. Н. Кокотов, *Конституционный принцип доверия в практике Конституционного Суда Российской Федерации* | хронология изменения нормы, обратного эффекта, ожидания и переходных гарантий | печ. 105; PDF 107 | `direct` | `reference_only_exact_overlap` | нет общего права на неизменность закона; надежда не равна приобретённому праву |
| `cmc-bondar-normative-doctrinal-decisions-05` | Н. С. Бондарь, *Российский судебный конституционализм* | разделение резолютивного эффекта, необходимого обоснования, смысла и scope | печ./PDF 62–64; §2.3 | `qualified` | `reference_only_exact_overlap` | декомпозиция аналитическая; не считать все рассуждения одинаково обязательными и не расширять holding |
| `cmc-bondar-constitutional-interpretation-07` | Н. С. Бондарь, та же работа | различение дефекта текста и дефекта толкования | печ./PDF 84; §3.1 | `direct` | `reference_only_exact_overlap` | сохраняющий смысл не должен переписывать норму; применённый или устойчивый смысл доказывается |
| `cmc-brezhnev-systemic-norm-control-02` | О. Брежнев, *Конституционно-правовые споры как явления современной действительности* | системная нормативная цепочка к конкретному конституционному вопросу | печ./PDF 6 | `qualified` | `reference_only_exact_overlap` | системная функция — эвристика, не официальный тест и не замена доказательства нормативного смысла |
| `cmc-lapaeva-formal-equality-test-01` | В. В. Лапаева, *Правовая демократия как цивилизационный выбор России* | comparator-группы, общий правовой масштаб и двусторонний equality test | печ. 156; PDF 157 | `direct` | `behavior_candidate_pending_eval` | группы должны быть релевантно сопоставимы; объективное различие иногда требует дифференциации |
| `cmc-dzhagaryan-critique-effect-separation-02` | А. А. Джагарян, *Вмененная безупречность: решения Конституционного Суда РФ и правовое качество* | три слоя: юридический эффект, фактическое исполнение, внешняя критика | печ. 116–117; PDF 118–119; разд. 3 | `qualified` | `behavior_candidate_pending_eval` | критика не меняет обязательный эффект и не оправдывает неисполнение; изменение позиции подтверждает только официальный акт |
| `cmc-mityukov-execution-gap-map-01` | М. А. Митюков, *Конституционные суды постсоветских государств: проблемы исполнения решений* | многоканальный аудит сроков, мер, аналогичных норм, практики и обхода | печ. 70; PDF 72 | `qualified` | `reference_only_exact_overlap` | матрица не добавляет постановлению новых требований и не создаёт средство защиты |
| `cmc-postnikov-legislative-form-guarantee-01` | А. Е. Постников, *О пределах подзаконного регулирования избирательных прав граждан* | reserve-of-law и delegation audit для правил, влияющих на реализацию права | печ. 31–32; PDF 1–2 | `qualified` | `behavior_candidate_pending_eval` | подтверждено прежде всего для избирательных гарантий; form defect не определяет исход и remedy |
| `cmc-postnikov-bylaw-boundary-02` | А. Е. Постников, та же работа | классификация существенной гарантии и технической конкретизации цифровой процедуры | печ. 41; PDF 11 | `qualified` | `supporting_reference` для `cmc-postnikov-legislative-form-guarantee-01` | цифровой checklist относится к ДЭГ, а не к любой технологии; значительная детализация может быть законно делегирована |
| `cmc-alexy-court-dual-character-03` | Роберт Алекси, *Сбалансированность, конституционный контроль и представительство* | раздельная проверка убедительности довода и доступного властного последствия | печ. 116; PDF 117; §2 | `direct` | `supporting_reference` для `cmc-khabrieva-review-remedy-01` | не импортировать германскую модель последствий; вид российского производства и резолютивная часть определяют эффект |
| `cmc-garlicki-positive-interpretation-03` | Лешек Гарлицкий, *Конституционные суды против верховных судов* | карта `судьба текста → обязательный смысл → последующая практика` | печ. 155; PDF 156; §3.3 | `direct` | `reference_only_exact_overlap` | не превращать ярлык «позитивное нормотворчество» в формально-юридическое требование |
| `cmc-kelsen-constitutive-invalidation-02` | Ханс Кельзен, *El control de la constitucionalidad de las leyes* | различение довода о дефекте, компетентного установления и последствий решения | печ. 86; PDF 6; разд. III | `qualified` | `supporting_reference` для `cmc-khabrieva-review-remedy-01` | не переносить конститутивную модель как российское право; учитывать прямое действие Конституции и отдельные маршруты пересмотра |

## Шесть потенциальных behavioral delta

До eval и human approval не загружай их как обязательные команды. Для design/review проверяются только следующие минимальные функции:

1. `remedy / competence / legal effect` gate — Хабриева; Алекси и Кельзен остаются supporting provenance.
2. Явная route map обычного суда, запроса суда и индивидуальной жалобы — Хабриева.
3. Optional open-rights branch с обязательным official-anchor gate — Морщакова.
4. Двусторонняя comparator-карта равенства — Лапаева.
5. Optional external-critique layer, не меняющий юридический эффект, — Джагарян.
6. Единый reserve-of-law/delegation subtest — Постников; цифровая карточка только supporting example.

## Нерешённые противоречия, которые нельзя компилировать

Четыре source/legal-reviewed конфликта не затрагивают перечисленные candidate rules, но задают обязательный `abstain` для выбора архитектуры пропорциональности:

- Barak `scope-before-justification` против Vaipan `cyclic proportionality`;
- Jackson `sequenced proportionality` против Vaipan;
- Möller `four-stage test` против Vaipan;
- Troitskaya `four-stage test` против Vaipan;

Не выбирать модель голосованием авторов, известностью или числом ссылок. До отдельного разрешения можно использовать модели только как альтернативные stress-tests с явной маркировкой и без объявления одной из них обязательной российской последовательностью.

Effective conflict v2 содержит 347 новых model-semantic `passed` reviews: все 342 связи, затрагивающие 19 candidate cards, и пять специально перепроверенных некандидатных пар. Остальные 852 пары сохраняют консервативный `uncertain`. Все 59 candidate↔candidate edges прошли: 40 `no_change`, 19 `narrow`, конфликтов между candidate cards нет. При этом human gate остаётся pending для всех 1 199 reviews. Для 133 строк канонический frozen semantic projection проверен дословно; 214 legacy A/B revisions имеют immutable ledger, но ещё не имеют канонического semantic fingerprint. Поэтому `semantic_fingerprint_gate_complete=false`, а promotion запрещён.

## Завершённые bounded source-revisions

Обе найденные source-trace ошибки Хабриевой исправлены immutable successors и независимо перечитаны в чистом контексте:

- `cmc-khabrieva-lawmaking-focus-03`: faithful quote SHA-256 `0a6464eaf2f3510df23c2f23a767939b25fe9988720691712cef791979f2c679`, effective review `source-review-khabrieva-lawmaking-focus-r1-clean-20260815-b9e4f1` — `passed/keep`;
- `cmc-khabrieva-review-remedy-01`: восстановлен исходный порядок фрагментов, quote SHA-256 `b3633ce4d4dcc69f26c3d934af49dc13e148169aa023c718aceb5d50c8b4c821`, effective review `source-review-khabrieva-review-remedy-source-fix-r1-clean-2026-08-15` — `passed/keep`.

Обе карточки входят в effective r3 corpus с точными post-seal pointers. Это закрывает прежний запрет на дословное использование исправленных окон, но не снимает legal-currentness, eval и human gates.

## Контрольный срез

- effective cards r3 SHA-256: `b0c8bce6b4e53892461be3c658cae7ba25a86aecd02962e12bdcde8f2cda8d7a`;
- effective source reviews r3 SHA-256: `a3181205dfe3eee4851dfacbba062f480c19b418c2d4ea2084d3e0699d563011`;
- effective legal reviews SHA-256: `767f3961d742968a8af11d1835fd0e3611e349feccdcf8479098445185f80282`;
- effective conflict reviews v2 r2 SHA-256: `f5f4886404b9db2ed98dc23bec365adeaa94deb904c608360bf702de5e0ebfb8`;
- effective compilation receipt SHA-256: `691e35f1a9c83eff2edfa973af3eca85143eef17bc0c333ac19568d48210bbcb`.

Эти хэши доказывают использованный срез, но не заменяют source locator или актуальную официальную правовую проверку.
