# Локальная knowledge base HUDOC: interface-only workflow

Этот файл описывает поиск по локальной source-backed проекции. Он не добавляет новые substantive rules ЕСПЧ или КС РФ.

## Когда использовать

Используй базу для discovery по фактически проиндексированной части корпуса: найти sentence-attributed candidates довода заявителя/возражения государства/ответа большинства и затем вручную проверить speaker; собрать candidates норм, тестов, safeguards, alternatives, burden/evidence, remedies, adverse citations, представителей и нижестоящие суды.

Runtime по умолчанию задаётся через `HUDOC_ARCHIVE_ROOT` либо локальный корень архива:

- DB: `$HUDOC_ARCHIVE_ROOT/knowledge/v3/hudoc_knowledge_v3.sqlite3`;
- progress: `$HUDOC_ARCHIVE_ROOT/knowledge/v3/knowledge_progress.json`;
- стабильный resolver CLI: `scripts/hudoc_kb_cli.py` внутри текущего skill; он принимает `HUDOC_KB_CLI`, затем `HUDOC_KS_PARSER_REPO`, локальный repository candidate и его Git worktrees и запускает только связку `hudoc-knowledge-indexer-v3.6` + `hudoc-research-extractive-v5`;
- hybrid resolver CLI: `scripts/hudoc_vector_cli.py` внутри текущего skill; он принимает `HUDOC_VECTOR_CLI`, использует тот же repository/worktree discovery, проверяет `hudoc-vector-indexer-v2` + `hudoc-vector-evaluator-v2` + KB v3.6 + research v5 и использует отдельный HUDOC Qdrant на `127.0.0.1:6335`. Чужие Qdrant collections не выбирать.

Сначала вызови `--help`, затем `status` и `coverage`, передав `--db` до подкоманды. До полного v3.6 cycle, нулевых stale/failure/coverage deltas и privacy gate считай runtime `branch-local pilot`, а не полной базой. В поиск входят только current-v3.6 `ready`, построенные из `hudoc-research-extractive-v5`; `qa_required`/`quarantine` и старые research versions нельзя использовать содержательно. Если индекс ещё строится, явно сообщи фактическое покрытие.

## Минимальный порядок

1. `search`/`find-term` с фильтрами `family`, `language`, `actor`, `function`, `source-role`, `article`, `atom-type`, `matter-key` или `itemid`. Actor/function/source-role filters ищут только explicit sentence candidates; assertion-derived `source_role` проверяется отдельно от `paragraph_source_role_v13`. Нефильтрованный результат является paragraph candidate. `speaker_verified=false` блокирует окончательную атрибуцию.
   Если exact/FTS формулировки недостаточно, после успешных readiness/privacy/retrieval gates используй hybrid `search`: FTS top-N сохраняет точные identifiers, dense top-N ищет многоязычные смысловые аналоги, а RRF объединяет их. Evidence всегда гидратируется из SQLite; Qdrant payload не является источником цитаты.
2. `matter` для проверки всех variants и application numbers.
3. `citations`, `representatives`, `courts` — только как source-backed реестры; последние два ограничены v13 Russia-title candidate, но respondent/роль всё равно проверяются человеком; контакты автоматически не собирать.
4. Вернуться по official anchor и локатору к PDF/TXT/page JSONL; проверить speaker, контекст и статус документа.
5. Перенести результат в `ResearchFinding`, а не непосредственно в текст жалобы или skill rule.
6. Для повторного использования пройти `verified_case_finding -> cross_case_reusable -> skill_update_approved` с российским официальным якорем, adverse search, temporal/currentness и transfer limits.

## Обязательные ограничения

- `promotion_eligible=false` и `permitted_use=discovery_only` — блокирующие поля, не комментарий.
- BM25, frequency, variant count и cluster size не доказывают позицию Суда.
- Dense similarity, vector rank и RRF score также не доказывают позицию Суда и не создают `ResearchFinding`.
- `applicant_submission` — воспроизведение в публичном акте, а не оригинальная application form.
- Для submissions обязательны `source_form=reproduced_in_public_act`, `original_application_in_source=false`, `complaint_completeness=unknown_from_public_act` и фактический `reproduction_mode`; база не восстанавливает оригинальные жалобы.
- summary/press/communicated/separate opinion не голосуют как majority holding.
- если точный ответ Суда на довод не найден, `court_treatment=unclear`.
- citation target без exact application number/matter остаётся `ambiguous|unresolved`.
- email/phone редактируются из KB/RAG; имя/организация представителя допустимы только с публичным профессиональным locator. Любое контактное обогащение — отдельный approval workflow.
- `distinct_court_matter_count` и `court_assertion_candidates` — нейтральная очередь проверки, а не число дел, «поддержавших» тезис.
- substantive KSRF transfer невозможен без действующего официального российского якоря и ручной проверки.

## Как превращать найденное в конституционно-правовой материал

Поиск должен вернуть три независимых слоя: `что утверждала сторона`, `как на это ответило большинство Суда`, `что из структуры рассуждения переносимо как исследовательский приём`. Не склеивай их в один тезис.

Для каждого проверенного candidate заполни структурированный `KSRFTransferPacket`; свободный пересказ и общая ссылка на сайт не проходят gate:

- `challenged_norm_or_judicial_meaning`: точные реквизиты и редакция нормы, отдельная ссылка на конкретную страницу официального российского источника и воспроизводимый судебный смысл; без этого anti-fourth-instance gate закрыт;
- `domestic_application`: exact locator/evidence ID российского акта, причинная роль нормы и контрфактическая проверка;
- `constitutional_rights_and_official_anchors`: список конкретных статей Конституции РФ с официальным актом, локатором и датой проверки либо `unknown`;
- `defect_mechanism` и `individual_harm`: анализ, evidence IDs и допустимый статус факта (`court_established|document_uncontested`); довод стороны сам по себе не становится установленным фактом;
- `test_family_and_steps`: применимость, вмешательство/обязанность, законная цель, пригодность, необходимость, баланс, burden/evidence и remedy — каждый фактически присутствующий шаг с `actor=court_majority`, itemid/locator и `court_treatment=accepted|qualified`;
- `less_restrictive_alternative`, `procedural_safeguards`, `positive_obligation_or_remedy`: самостоятельные поля, а не общий пересказ;
- для positive obligation отдельно укажи `trigger`, `scope`, `content`, `breach`; несовместимость модели дефекта обязательного нормативного смысла и модели ошибки только в применении означает `model_conflict` и abstention;
- `russian_normative_anchors`: непустой список действующих официальных актов КС РФ/нормы права с точными URL, локаторами и датами проверки;
- `fourth_instance_boundary`: структурно укажи `object_of_review=norm_or_binding_judicial_meaning`, исключённую переоценку и анализ границы;
- `adverse_and_distinguishing`: `analysis` и непустые `result_ids`, связывающие adverse/distinguishing выводы с transfer packet; отдельно обязательный `adverse_search` содержит воспроизводимые `query`, `scope`, `checked_on`, `results` либо `checked_none_found`.

Для доводов заявителя действует отдельный method-only контур. Повторяемый приём можно считать только по независимым делам, где он воспроизведён в публичном акте с exact locator и явно записанной реакцией Суда (`accepted|rejected|qualified|not_addressed|unclear`). Method transfer дополнительно требует adverse review, currentness review, temporal effect, transfer limit и human review. Исключение из Russian-anchor gate действует только при одновременных `authority_status=non_authority`, `reuse_target=research_checklist_only` и `substantive_rule_changed=false`; такой приём может добавить вопрос или проверку в исследовательский чек-лист, но не материально-правовое утверждение от имени ЕСПЧ. Во всех остальных случаях российский якорь обязателен: отсутствие любого флага, изменение route/verdict либо попытка сформулировать substantive Court-authority rule возвращают полный `russian_normative_anchors` gate.

До ручной сверки позиции большинства, adverse search и российского якоря пакет имеет `promotion_eligible=false`. Приём заявителя может улучшить формулировку исследовательского вопроса или структуру жалобы, но не получает статус authority от одной лишь публикации в акте.

`export-rag` сохраняет sanitized discovery records с provenance и годится для retrieval; target обязан быть `.jsonl` внутри `$HUDOC_ARCHIVE_ROOT/knowledge/v3/exports/`, а raw текст открывается только по exact locator в PDF/TXT. Deterministic dense retrieval допускается только после human-gold exact/semantic/role/adverse/no-answer evaluation и нулевых privacy/stale/provenance defects. Любой LLM reranking, semantic classification либо synthesis запускается отдельно с Langfuse/DeepEval, gold/held-out, abstention и quality/cost/latency/error отчётом; он не пишет результат прямо в скиллы.
