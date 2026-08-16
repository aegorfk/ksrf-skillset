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
| `claimed_function` | Какую функцию выполняет институт или аргумент |
| `textual_context` | Совпадают ли тексты и место нормы в системе |
| `institutional_context` | Совпадают ли полномочия, процедура и адресаты |
| `social_historical_context` | Какие различия способны изменить смысл или эффект |
| `system_links` | С какими иными институтами связан сравниваемый элемент |
| `negative_example` | Что материал опровергает или заставляет проверить |
| `russian_anchor_gap` | Какого официального российского основания ещё нет |

Одинаковое название доктрины, похожая функция или совпавший результат не доказывают юридическую эквивалентность. По умолчанию вывод — discovery, counterexample или option generation.

## 3. Ограниченный институциональный контекст

Описание иностранного суда может породить вопросы о доступности слушания, обмене аргументами, коллегиальности и публичном объяснении. Оно не доказывает материальную доктрину, полномочие либо процессуальное право в России. Архитектурно-визуальные источники маркируй `context_only` и не используй как самостоятельную runtime-норму.

## Выход

- `MaterialObjectionLedger`;
- `ComparativeTransferCard`;
- `voice_missing` и `russian_anchor_gap`;
- relation `supports`, `weakens`, `distinguishes` либо `blocks` только после проверки российского источника;
- `comparative_only` или `abstain`, если сопоставимость не доказана.

## Источники и locators

- Jürgen Habermas, *Between Facts and Norms*, MIT Press, 1996: конкурирующие прочтения и межсубъектная проверка, PDF 264–267 / печ. с. 222–225; различение норм и ценностей, PDF 295–299 / с. 253–257. SHA-256: `7eca34b93f1bb25bbe1d3278d4fe865e9d0b5fe6c7f667e91f62b37ea7a8c83f`.
- Vicki C. Jackson, “Comparative Constitutional Law: Methodologies”, in Michel Rosenfeld, András Sajó (eds.), *The Oxford Handbook of Comparative Constitutional Law*, Oxford University Press, 2012: contextualized functionalism, PDF 89–94 / печ. с. 67–72. SHA-256 полного тома: `75d1f10790720b25f69bcaa2285fff87936fd102159e9dc7e345f37caf3e22ca`.
- Jutta Limbach, “Working at the Federal Constitutional Court”, in *Das Bundesverfassungsgericht in Karlsruhe: Architektur und Rechtsprechung / Architecture and Jurisdiction*, Birkhäuser, 2004: слушание и обмен аргументами, PDF 49–61, особенно 50–52 / печ. с. 43–55, особенно 44–48. SHA-256: `2079a2ec72df2c7b907cf74e3b51af37350a61bccfcbd60e46d99b87ce79ea4c`. Источник имеет статус `context_only`.

Все источники — вторичная сравнительная методология. Их locators не подтверждают российское право, полномочия КС РФ или факт дела.
