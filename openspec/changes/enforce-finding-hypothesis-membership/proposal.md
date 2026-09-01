# Запрет переноса finding между несвязанными гипотезами

## Почему

`ResearchFinding.hypothesis_ids` задаёт гипотезы, которых касается finding, а `ArgumentHypothesis` отдельно перечисляет supporting/adverse finding IDs. Текущий валидатор проверяет ссылку только против глобального множества `finding_id`, поэтому finding, связанный исключительно с H1, можно без ошибки включить в H2. Это создаёт исполняемый `UNSAFE_PASS` и позволяет чужому evidence попасть в downstream drafting.

## Что меняется

- Валидатор проверяет для каждой ссылки гипотезы, что её `hypothesis_id` явно присутствует в `finding.hypothesis_ids`.
- Контракт артефактов закрепляет локальную membership-связь, а не только глобальное существование ID.
- Новый offline test покрывает cross-hypothesis negative, обычный positive и явный multi-hypothesis positive.
- Существующий eval уточняется тем же fail-closed правилом.

## Не входит

- Проверка полярности `relation` против supporting/adverse списка.
- Обратное exact-set равенство между finding и hypotheses.
- Изменение lifecycle, approval gates, `ConstitutionalIssueOption` или downstream builder.
- Публикация в `main` либо синхронизация глобального скилла без отдельного exact-byte human approval.

## Затрагиваемые файлы

- `skills/ksrf-explore-arguments/scripts/validate_argument_research.py`
- `skills/ksrf-explore-arguments/tests/test_validate_argument_research.py`
- `skills/ksrf-explore-arguments/references/artifact-contracts.md`
- `skills/ksrf-explore-arguments/evals/evals.json`
- `skills-manifest.json` (механически пересобранный publish manifest)
