## 1. Контракт

- [x] 1.1 Зафиксировать точный stable base SHA, live `main` и deterministic RED между reference и schema/runtime.
- [x] 1.2 Оформить proposal, design, delta spec и пройти strict OpenSpec validation до реализации.

## 2. Реализация

- [x] 2.1 Исправить reference на canonical `raised_but_not_addressed`.
- [x] 2.2 Добавить scoped fail-closed cross-contract validator.
- [x] 2.3 Добавить focused pass/drift regression tests.
- [x] 2.4 Регенерировать manifest от exact base commit после финальных правок.

## 3. Верификация и кандидатная публикация

- [x] 3.1 Выполнить focused/root tests, strict package/full validators и strict OpenSpec validation.
- [x] 3.2 Выполнить clean-room install и подтвердить hashes без изменения global skills.
- [x] 3.3 Выполнить независимый review и подтвердить отсутствие schema/runtime/publication regression.
- [x] 3.4 Сделать атомарный commit, опубликовать только feature branch и подтвердить live branch SHA, неизменность `main` и глобального skill.

## 4. Перенос на актуальный application-binding base

- [x] 4.1 На `5a4b51be67428afefaeefd20dc7d2e0a3babf470` повторно получить RED: validator пропускает расходящийся reference/schema enum.
- [x] 4.2 Перенести только содержательный patch без старого manifest и регенерировать manifest от актуального base SHA.
- [x] 4.3 Повторить focused/full/root tests, strict skillset и OpenSpec validation, offline self-containment и clean-room hash check.
- [x] 4.4 Получить независимый review актуального diff без нерешённых P1/P2.
- [ ] 4.5 Опубликовать только refresh feature branch и подтвердить её SHA, неизменность `main` и глобальных skills.

## 5. Человеческий promotion gate

- [ ] 5.1 Получить отдельное одобрение точного refresh SHA до merge в `main`.
- [ ] 5.2 Получить отдельное одобрение точного refresh SHA до установки в глобальные skills.
