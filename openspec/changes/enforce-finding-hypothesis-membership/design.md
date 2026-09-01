# Проектирование

## Инвариант

Глобальное существование `finding_id` недостаточно. Если H2 ссылается на F1, то `H2` должно присутствовать в `F1.hypothesis_ids`; иначе связь не доказана и validator обязан вернуть ошибку.

## Алгоритм

Во время прохода findings валидатор строит отображение `finding_id -> set(hypothesis_ids)` только из строковых элементов массива. Во время прохода hypotheses он сохраняет прежнюю проверку неизвестных finding IDs и отдельно проверяет каждый известный referenced finding против текущего непустого строкового `hypothesis_id`. Нестроковый либо пустой id не может удовлетворить membership и оставляет известную ссылку заблокированной.

Проверка направленная: она запрещает необъявленную ссылку hypothesis → finding. Она не требует, чтобы каждая объявленная в finding гипотеза обязательно использовала finding, и не выводит supporting/adverse полярность из `relation`.

## TDD и stop rule

1. RED: F1 связан только с H1, но H2 ссылается на F1; exact base `7c934ebf0282221c0efe3321d6cec57e6c403841` возвращает пустой список ошибок.
2. GREEN: тот же payload блокируется, H1→F1 проходит, F1→[H1,H2] с обеими ссылками проходит.
3. REFACTOR: не добавлять type-schema overhaul, relation polarity или обратное exact-set правило.

Candidate-этап заканчивается после full tests, strict validation, clean-copy verification и независимого review. Разрешена только feature branch; `main` и `~/.codex/skills` остаются неизменными, OpenSpec change — открытым. Полное завершение требует отдельного exact-byte human approval, публикации одобренного commit в `main`, live-SHA проверки, global sync и повторной проверки опубликованных байтов.
