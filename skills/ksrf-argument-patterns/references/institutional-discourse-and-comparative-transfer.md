# Институциональный дискурс и перенос сравнительного материала

Используй этот справочник для red-team конкурирующих толкований и проверки переносимости иностранного материала. Он не превращает deliberative theory, зарубежное решение или описание иностранного суда в российский источник права.

## 1. Objection-first discourse pass

Для существенного тезиса собери:

`claim -> speaker/source -> exact locator -> strongest competing reading -> affected group -> answer -> residual uncertainty`.

Проверь:

- представлено ли сильнейшее добросовестное альтернативное прочтение;
- может ли возражение быть проверено другим участником по тем же источникам;
- не смешана ли обязательность нормы с градуированным предпочтением ценности;
- не выдано ли согласие аудитории, популярность или риторическая сила за юридическую релевантность.

Отсутствие формальной противоположной стороны не снимает critic-pass. При недоступной позиции затронутой группы не реконструируй её уверенно: отметь `voice_missing`.

## 2. Contextualized functionalism

Иностранный материал получает `comparative_candidate` только после заполнения:

| Поле | Проверка |
| --- | --- |
| `domestic_question` | Какой точный российский вопрос исследуется |
| `foreign_source_status` | Суд, вид акта, обязательность, дата и официальный locator |
| `source_role/as_of` | Это statute, common law, convention, standing order, privilege, доктрина или историческое описание; на какую дату оно проверено |
| `claimed_function` | Какую функцию выполняет институт или аргумент |
| `tertium_comparationis` | По какому общему функциональному основанию объекты вообще сопоставляются |
| `selection_reason` | Почему выбраны эти объект, юрисдикция, дело и параметры, а не удобный пример с нужным результатом |
| `textual_context` | Совпадают ли тексты и место нормы в системе |
| `institutional_context` | Совпадают ли полномочия, процедура и адресаты |
| `social_historical_context` | Какие различия способны изменить смысл или эффект |
| `system_links` | С какими иными институтами связан сравниваемый элемент |
| `context_budget` | Какой контекст необходим для вывода и где дальнейшее расширение уже не меняет проверяемую функцию |
| `negative_example` | Что материал опровергает или заставляет проверить |
| `russian_anchor_gap` | Какого официального российского основания ещё нет |

Одинаковое название доктрины, похожая функция или совпавший результат не доказывают юридическую эквивалентность. По умолчанию вывод — discovery, counterexample или option generation.

### InstitutionalRuleCard

**Input → transform → output:** утверждение об иностранном институте или порядке → разложи его на `jurisdiction/as_of`, институт и реального актора, формальное полномочие, фактическую практику, `source_role`, enforcing/review actor, доступный remedy и currentness → `InstitutionalRuleCard` с отдельно отмеченными историческими и текущими слоями.

Не склеивай statute, common law, convention, standing order и privilege в единое «правило». Учебник или исторический трактат — только discovery source. Подтверждение требует текущего официального иностранного первичного источника; российская применимость — отдельной Конституции РФ, действующей нормы, официального акта КС РФ и материалов конкретного дела.

**Adverse/refute pass:** проверь позднейший statute/rule/case, изменившуюся convention, судебно отвергнутую privilege claim, несовпадение формального и фактического актора и иной review/remedy mechanism. Верни `historical_only` или `abstain_currentness`, если текущий первичный источник не найден, enforcing actor неизвестен либо source roles противоречат друг другу. Функциональную сопоставимость, currentness и любой российский мост утверждает юрист; карточка не создаёт полномочие, допустимость или средство защиты.

## 3. Ограниченный институциональный контекст

Описание иностранного суда может породить вопросы о доступности слушания, обмене аргументами, коллегиальности и публичном объяснении. Оно не доказывает материальную доктрину, полномочие либо процессуальное право в России. Архитектурно-визуальные источники маркируй `context_only` и не используй как самостоятельную runtime-норму.

## Выход

- `MaterialObjectionLedger`;
- `ComparativeTransferCard`;
- `InstitutionalRuleCard` либо `historical_only`/`abstain_currentness`;
- `voice_missing` и `russian_anchor_gap`;
- relation `supports`, `weakens`, `distinguishes` либо `blocks` только после проверки российского источника;
- `comparative_only` или `abstain`, если сопоставимость не доказана.

## Источники и locators

- Jürgen Habermas, *Between Facts and Norms*, MIT Press, 1996: конкурирующие прочтения и межсубъектная проверка, PDF 264–267 / печ. с. 222–225; различение норм и ценностей, PDF 295–299 / с. 253–257. SHA-256: `7eca34b93f1bb25bbe1d3278d4fe865e9d0b5fe6c7f667e91f62b37ea7a8c83f`.
- Vicki C. Jackson, “Comparative Constitutional Law: Methodologies”, in Michel Rosenfeld, András Sajó (eds.), *The Oxford Handbook of Comparative Constitutional Law*, Oxford University Press, 2012: contextualized functionalism, PDF 89–94 / печ. с. 67–72. SHA-256 полного тома: `75d1f10790720b25f69bcaa2285fff87936fd102159e9dc7e345f37caf3e22ca`.
- Jutta Limbach, “Working at the Federal Constitutional Court”, in *Das Bundesverfassungsgericht in Karlsruhe: Architektur und Rechtsprechung / Architecture and Jurisdiction*, Birkhäuser, 2004: слушание и обмен аргументами, PDF 49–61, особенно 50–52 / печ. с. 43–55, особенно 44–48. SHA-256: `2079a2ec72df2c7b907cf74e3b51af37350a61bccfcbd60e46d99b87ce79ea4c`. Источник имеет статус `context_only`.
- William Anson, *Английский парламент, его конституционные законы и обычаи*, пер. Н. А. Захарова, Юрайт, 2025, ISBN `978-5-534-15520-4`: репринт русского издания 1908 года и поздневикторианской доктрины; law/custom/convention — PDF 12–20; формальная и конвенциональная конституция — 37–43; созыв — 44–69; Commons/privileges — 70–163, судебные границы privileges — 157; Lords — 164–200; legislative process — 201–244; Crown in Parliament — 245–259; executive/legislative conflict — 260–295; историческая судебная функция — 296–317. Начиная с печатной с. 9, `PDF=print`; image-only scan, OCR-парафраз и буквальная цитата требуют визуальной проверки. SHA-256: `383fea6cdca3fdb3949042ea8d6bb6b9fe21a02de4c1fdcc0974141ece2bbb6d`. Статус — `historical_comparative_method_only`.
- М. А. Викулина, *Основы конституционного права Великобритании: исполнительная и законодательная ветви власти*, Проспект, 2021, ISBN `978-5-392-35203-6`: Crown, formal/actual power и source roles — PDF/печатные с. 4–19; executive/accountability — 20–31; Commons/scrutiny — 32–47; Lords/inquiry — 48–61; legislative preparation — 62–67; parliamentary stages — 68–75; post-legislative review — 71; TOC — PDF 78. Файл содержит 78 PDF-страниц при библиографическом объёме 80; полнота и currentness не презюмируются. SHA-256: `36973eba8462c77cffa7ddc96b4dab6307ec87247ec298c721d90b300c53ff37`.

Все источники — вторичная сравнительная методология. Их locators не подтверждают российское право, полномочия КС РФ или факт дела.
