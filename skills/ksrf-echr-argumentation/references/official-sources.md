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

## Материалы дела

До запроса проверить, опубликованы ли facts, questions to the parties, observations или related documents в HUDOC. Если нет, сформулировать узкий запрос с номером жалобы, датой и перечнем нужных документов по официальной процедуре. Не включать в корпус документы мирового соглашения и иные закрытые материалы.
