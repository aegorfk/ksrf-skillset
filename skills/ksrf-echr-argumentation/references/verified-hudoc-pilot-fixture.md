# Verified HUDOC pilot: regression fixture

Этот файл проверяет поведение skill на трёх визуально сверенных source-backed findings и одном реалистичном contract-only negative control. Он не добавляет новый материально-правовой тест и не разрешает перенос конкретных фактов в жалобу.

## Fixture 1: positive obligation

- Finding: `hudoc-001-248197-art2-operational-risk-test-v1`.
- Источник: `001-248197`, judgment, PDF page 38, source paragraph 159, `court_reasoning`.
- Допустимый результат: вернуть проверенную формулу `trigger -> scope -> content` как сравнительный finding и отдельно указать фактический контекст риска для жизни от третьего лица.
- Обязательный stop: `russian_anchor_status=not_verified` и `drafting_reuse_status=blocked_missing_russian_anchor`; не превращать finding в российскую обязанность или требование конкретной меры.

## Fixture 2: proportionality and a narrower alternative

- Finding: `hudoc-001-251250-art8-individual-balance-alternatives-v1`.
- Источник: `001-251250`, Chamber judgment, PDF page 28, source paragraph 87, `court_reasoning`.
- Допустимый результат: сохранить case-specific связь индивидуального взвешивания и рассмотрения менее обременительной альтернативы.
- Обязательные ограничения: окончательность акта отдельно перепроверить; не формулировать универсальное least-restrictive-means правило; не переносить швейцарский тюремный контекст и конкретную меру.
- Adverse boundary: сопоставить с fixture 3, а не скрывать его.

## Fixture 3: adverse or distinguishing boundary

- Finding: `hudoc-001-251403-art8-relevant-sufficient-process-boundary-v1`.
- Источник: `001-251403`, inadmissibility decision, PDF page 7, source paragraph 33, `court_reasoning`.
- Допустимый результат: показать, что интенсивность вмешательства сама по себе не заменяет проверку релевантных и достаточных оснований и качества процесса.
- Обязательные ограничения: не называть decision постановлением по существу об отсутствии нарушения; не создавать презумпцию соразмерности помещения детей или прекращения контактов.

## Fixture 4: mixed applicant/Court negative control

- Статус: `contract_negative_control`, не самостоятельный источник права и не finding по реальному делу.
- Один смешанный paragraph: “The applicant argued that the rule was automatic. The Court considers that an individual assessment was required.”
- Для первого предложения обязательны `source_actor=applicant`, `source_function=submission`, `source_form=reproduced_in_public_act`, фактический reproduction mode и `court_treatment=unclear`; paragraph-level роль не может повысить его до majority reasoning.
- Для второго предложения обязательны `source_actor=court_majority`, `source_function=reasoning`, `source_form=public_act`, `court_treatment=not_applicable` и отдельный exact sentence locator.
- Обязательный stop для applicant lane: `authority_status=non_authority`, `promotion_eligible=false`; он не создаёт Court test/holding, `ResearchFinding` или substantive KSRF transfer без отдельного majority locator и полного lifecycle.

## Expected behavior

Skill проходит fixture, только если он:

1. сохраняет `judgment` и `decision` как разные source roles и не повышает communicated case, summary или довод стороны до позиции Суда;
2. возвращает точный `itemid + PDF page + source paragraph + source_role`;
3. удерживает все три findings на `verified_case_finding`, пока нет проверенного российского официального якоря, cross-case pattern, завершённого adverse review и human approval;
4. показывает fixture 3 как предел для fixture 2;
5. на fixture 4 возвращает две раздельные sentence-level attribution records и не наследует actor/source role от смешанного paragraph;
6. не превращает ни один case-specific факт в reusable skill instruction.
