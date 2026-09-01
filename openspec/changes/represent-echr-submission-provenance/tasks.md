## 1. Контракт и тест

- [x] 1.1 Добавить RED-тест на представимость трёх submission provenance fields
- [x] 1.2 Подтвердить падение теста на exact base
- [x] 1.3 Добавить поля в типизированную форму `ECHRArgumentPacket`
- [x] 1.4 Уточнить negative eval без расширения policy scope
- [x] 1.5 Зафиксировать полный безопасный tuple в contract fixture

## 2. Проверка кандидата

- [x] 2.1 Пройти узкий и полный test suite скилла
- [x] 2.2 Пройти strict OpenSpec validation и skill validation
- [x] 2.3 Проверить candidate из чистой копии и получить независимый review
- [x] 2.4 Опубликовать только feature branch и подтвердить неизменность remote `main` и глобального скилла

## 3. Promotion после отдельного human approval

- [ ] 3.1 Получить exact-byte human approval конкретного candidate commit
- [ ] 3.2 Опубликовать одобренный commit в `main` и подтвердить live SHA
- [ ] 3.3 Синхронизировать `~/.codex/skills/ksrf-echr-argumentation` и подтвердить exact hashes
- [ ] 3.4 Повторить проверки на опубликованных байтах и только затем архивировать OpenSpec change
