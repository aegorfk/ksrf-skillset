## 1. Контракт и RED

- [x] 1.1 Зафиксировать live base `5cb3390fe8bd2e5ee085b56d19f37c95da232377` и доказать, что OpenSpec уже отсутствует в install payload.
- [x] 1.2 Зафиксировать текущую утечку: 47 test-файлов / 843607 байт / 4 skills входят в global install.
- [x] 1.3 Оформить proposal, design и delta spec до изменения file contract.
- [x] 1.4 Добавить failing regression test, доказывающий, что `tests/` не должен копироваться.

## 2. Реализация

- [x] 2.1 Добавить минимальное development-only exclusion для path component `tests`.
- [x] 2.2 Сохранить `evals/` и остальные runtime/review assets в payload.
- [x] 2.3 Регенерировать manifest от exact live base после финальных правок.
- [x] 2.4 Добавить source-preserving reverse-sync mode и RED/GREEN на сохранение tests при удалении stale runtime files.
- [x] 2.5 Отразить `tests/` в machine-readable manifest exclusions.
- [x] 2.6 Синхронизировать portable validator manifest с runtime development-only boundary и добавить RED/GREEN.
- [x] 2.7 Перенести misplaced autocollect unittest из runtime `scripts/` в source `tests/` и выполнить его.
- [x] 2.8 Добавить fail-before-write guard и RED/GREEN для equality/ancestor/descendant overlap source и target.
- [x] 2.9 Сохранить repository-wide public-source guard для development-only paths и покрыть интеграционным regression.

## 3. Верификация и публикация

- [x] 3.1 Пройти focused RED/GREEN, root/full tests, strict skillset и strict OpenSpec validation.
- [x] 3.2 Подтвердить clean-room file/byte/package/tree hashes и отсутствие test paths.
- [x] 3.3 Получить независимый review без нерешённых P1/P2.
- [ ] 3.4 Опубликовать атомарно в `main`, подтвердить remote SHA и установить exact payload глобально.
- [ ] 3.5 Подтвердить, что source tests сохранены, global tests отсутствуют, а evals присутствуют.
