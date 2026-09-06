# Design

Новый optional объект `reasoning_checks` содержит `operator_checks` и
`residual_checks`, оба списки записей с уникальными id. Отсутствующий объект
оставляет старый пакет допустимым, но результат сообщает `provided=false`.

У claims допускается `finding_operator`: `proven`, `not_proven`, `proven_not`,
`act_exists`, `unknown`. Это декларация аналитика, не автоматическое извлечение.
Operator check связывает `premise_id`, `conclusion_id`, `same_proposition`
(boolean), `relation` (`equivalent` либо `requires_additional_premise`) и
непустое `explanation`. Equivalence требует same_proposition=true и одинаковых
известных операторов; разные операторы отвергаются, unknown/недостающий
оператор оставляет пробел, не доказывает эквивалентности. Одинаковые операторы
не удостоверяют тождество текста или юридическую истинность; это лишь контракт.
`requires_additional_premise` также всегда сохраняет needs_evidence: требуемое
дополнительное основание этот контракт не моделирует и не проверяет.

Residual check связывает `branch_id`, неповторяющиеся `remaining_ground_ids`
(подмножество оснований той же ветви) и две отдельные оценки `entitlement` и
`extent`. Каждая имеет `assessment` (`supported`, `not_supported`, `unknown`),
`reason` и `support_ids` из remaining_ground_ids. Оценка supported требует
непустой опоры. Unknown сохраняет needs_evidence. Нельзя оценкой существования
основания заполнить отсутствующую оценку объёма. Пустой остаток допустим для
неподтверждённости/неизвестности, но не для supported.

Все новые поля входят в существующий полный input_context_sha256. Выход
показывает количество проверок, provided и semantic_truth_verified=false.
Не добавлять поиск, зависимости или чтение внешнего корпуса. Новые справочные
операции evaluator-derived и не разрешаются для старого historical EVAL.
