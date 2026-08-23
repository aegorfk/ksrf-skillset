# Официальные источники ЕСПЧ

## Точка входа

| Ресурс | Адрес | Использование |
|---|---|---|
| HUDOC | https://hudoc.echr.coe.int/ | Первичные решения, решения о приемлемости, communicated cases, summaries и метаданные |
| HUDOC database | https://www.echr.coe.int/en/hudoc-database | Состав коллекций, FAQ, tutorials и manual |
| ECHR-KS | https://ks.echr.coe.int/ | Актуальные guides, key cases, обновления по статьям и архив CLIN |
| All Case-Law Guides | https://ks.echr.coe.int/web/echr-ks/all-case-law-guides | Полный актуальный перечень guides; сверять при каждом массовом обновлении |
| Apply to the Court | https://www.echr.coe.int/en/apply-to-the-court | Форма, правила подачи, сведения о производстве и документы для заявителей |
| Admissibility Guide | https://www.echr.coe.int/documents/admissibility_guide_eng.pdf | Допустимость; использовать актуальную редакцию |
| Rules and Practice Directions | https://www.echr.coe.int/en/practice-directions | Процессуальные требования, pleadings, anonymity, third-party intervention и Rule 39 |
| Factsheets | https://www.echr.coe.int/en/factsheets | Тематический обзор и стартовые ссылки, но не замена первоисточника |
| Access to case files | https://www.echr.coe.int/documents/d/echr/Practical_arrangements_ENG | Точечный доступ к материалам конкретного дела |

## Как поддерживать полный набор guides

Не встраивать копии всех guide в навык: они обновляются и быстро устаревают. При инвентаризации открыть страницу **All Case-Law Guides**, записать заголовок, статью/тему, дату редакции, язык и официальный URL. Для каждого практического задания загрузить только относящиеся к теме guides плюс Guide on Admissibility.

Сформировать обновляемый реестр с полями: `guide_title`, `article_or_theme`, `edition_date`, `official_url`, `checked_on`, `scope`, `related_hudoc_queries`.

## Шаблон аргументной карты

```text
case_id_and_title:
source_url:
document_type_and_status:
facts_material_to_issue:
domestic_law_or_practice:
convention_articles:
admissibility:
applicant_arguments:
government_arguments:
court_test_and_paragraphs:
holding_and_remedy:
constitutional_translation:
limits_and_counterarguments:
evidence_or_procedural_next_step:
```

## HUDOC: минимальная дисциплина поиска

1. Отобрать document collection и Convention Article.
2. Добавить keywords HUDOC, тип документа, государство, дату и importance при необходимости.
3. Выполнить свободный поиск на английском и французском; сохранить сам запрос и фильтры.
4. Выгрузить список результатов в CSV/Excel, если это доступно через интерфейс.
5. Проверить Case Details каждого опорного дела и сохранить устойчивую ссылку HUDOC.

## EchrVsReceptionTrace: сборник только как seed

Тематический сборник, указатель или перевод может дать поисковый lead, но не подтверждает содержание решения ЕСПЧ, роль ссылки в акте ВС РФ/КС РФ, currentness или устойчивую российскую практику.

**Input → transform → output:** issue/Convention Article и вторичный seed → получить точный официальный акт HUDOC с application number, датой, document type и paragraph locators → получить полный официальный акт ВС РФ, а при конституционном тезисе также релевантный официальный акт КС РФ и действующую норму → классифицировать роль как `adopted`, `paraphrased`, `mentioned`, `distinguished`, `rejected` либо `background` → `EchrVsReceptionTrace` с currentness/adverse status.

Минимальные поля: `echr_case_title`, `application_no`, `decision_date`, `document_type/status`, `article`, `hudoc_url`, `paragraphs`, `translation_source`, `vs_act_type/id/date`, `vs_official_url`, `vs_locator`, `reception_role`, `ksrf_or_current_law_anchor`, `currentness_checked_on`, `later_authority`, `adverse_cases`, `transfer_limit`.

Dedup выполняй раздельно: ЕСПЧ — по `application_no + decision_date + document_type`; российский акт — по официальному `act_id + date + act_type`. Совпадение названий или переводов не является дубликатом первичного акта и не доказывает его использование.

**Adverse/refute pass:** ищи более позднее решение Большой палаты, изменившееся регулирование, более поздний акт ВС РФ/КС РФ, `mention_only`, иной перевод существенного места, distinguishing/rejection и дела с противоположным результатом. Для утверждения об устойчивой рецепции заранее определи полный официальный российский корпус, период, запрос и negative set; отдельный сборник 2010–2015 годов этого не заменяет.

Верни `abstain_reception_trace`, если не получен хотя бы один первичный полный текст, отсутствует точный locator, неизвестна роль ссылки или currentness. Перевод, статус документа и reception role подтверждает человек. Карточка не доказывает российское право, допустимость жалобы, полномочие суда, факты или remedy.

### Проверенный вторичный seed и locators

- *Постановления Европейского Суда по правам человека, использованные в постановлениях и обзорах Верховного Суда Российской Федерации (2010–2015 гг.)*, ред. В. С. Ламбина, Статут, 2016, ISBN `978-5-8354-1284-6`: provenance и обозначение источника перевода — PDF/печатные с. 5–7; уголовные дела — с. 8–92; гражданские — 93–155; административные — 156–182; выдержки из постановлений Пленума ВС РФ — 183–219; указатель — 220–223; структурированный пример case/application/facts/ECtHR paragraphs/VS review — 8–12, Korovina → Обзор № 1 (2015) на с. 11. `PDF=print`, SHA-256 `b68299206e1fe564540be0983539fdcc1f811fe5c197493a6070e7f712595c1f`. Статус — `secondary_discovery_seed_2010_2015`; каждое звено заново проверяется по официальным HUDOC и российским источникам.

## Материалы дела

До запроса проверить, опубликованы ли facts, questions to the parties, observations или related documents в HUDOC. Если нет, сформулировать узкий запрос с номером жалобы, датой и перечнем нужных документов по официальной процедуре. Не включать в корпус документы мирового соглашения и иные закрытые материалы.
