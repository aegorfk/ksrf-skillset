# Quality-слой анализа судебного смысла

Эти артефакты отвечают на разные вопросы и не сворачиваются в один score. `complete` означает завершённость заявленного протокола, а не доказанность «хаоса», неработоспособности закона или неконституционности.

## Движение смысла внутри цепочки

`chain-stage-observations.jsonl` хранит отдельные reviewed-наблюдения по каждой инстанции. Не передавай их в агрегатор, который выбирает одну карточку на независимую цепочку: межинстанционная траектория и межделовое сравнение — разные единицы анализа.

Обязательные различия:

- `source_stage` — где находится текст-доказательство;
- `position_actor_stage` — какому суду принадлежит позиция;
- `evidence_role` — `actor_primary_text` либо `later_court_report`;
- `treatment_of_prior` — `originates`, `expressly_adopts`, `follows`, `limits`, `rejects`, `does_not_reach`, `leaves_result_without_endorsing`, `unclear`;
- `outcome_materiality` и самостоятельные альтернативные основания;
- document hash, точная цитата/locator и human-review provenance.

Оставление результата без изменения не означает принятия мотивировки нижестоящего суда. Пересказ более ранней позиции в кассационном акте остаётся `later_court_report`, если нет первичного текста соответствующего автора позиции.

## Профиль неопределённости

`practice-uncertainty-profile.json` содержит ровно девять независимых измерений:

1. `comparable_reading_plurality`;
2. `fact_sensitivity`;
3. `court_distribution`;
4. `temporal_distribution`;
5. `chain_endorsement`;
6. `outcome_materiality`;
7. `higher_authority_treatment`;
8. `coverage_limits`;
9. `coding_reliability`.

Каждое измерение хранит state, независимые chain IDs, evidence refs, unknowns, claim effect и limitations. Поля `score`, `overall_score`, `index` и их смысловые аналоги запрещены. Профиль описывает доказательственную картину; нормативный мост и human approval остаются отдельными воротами.

## Надёжность кодирования

`coding-audit-plan.json` до второй разметки замораживает план, screening-frame hash, детерминированную SHA-выборку включённых карточек и отдельную выборку исключений. Вторичные review не заменяют primary cards.

`coding-reliability.json` становится complete только когда:

- второй coder отличается от primary coder;
- вся frozen sample размечена;
- расхождения по существенным полям сохранены;
- возможные ложные исключения явно отмечены;
- adjudication связан с content hashes обеих разметок;
- изменение любой входной карточки делает результат stale.

Вывод содержит counts, missing reviews, field disagreements, potential false exclusions и adjudications, но не единый коэффициент юридической готовности.

## Предподачная актуальность

`public-corpus-binding.json` фиксирует корпус, на котором выполнены анализ, trajectory, profile и bridge. `pre-filing-refresh.json` проверяет четыре независимых дорожки:

- официальные source routes;
- изменения закона;
- новые акты высших судов;
- verified и relevant pending treatments.

Результаты: `current_no_material_change`, `bounded_current_with_disclosed_gaps`, `refresh_incomplete`, `material_change_requires_reanalysis`. Новый relevant pending treatment блокирует прежний вывод ещё до изменения verified-only digest. Неизменившийся уже раскрытый route gap допускает только bounded-current формулировку и не становится нулём практики.

## Связь с handoff

Если claim зависит от trajectory, uncertainty, reliability или refresh, portable v2 result обязан включить content hashes соответствующих артефактов. Изменение любого связанного артефакта делает только зависимые claims stale. Reviewed result строится кассационным CLI из текущего workspace; caller не может передать собственный findings JSON.
