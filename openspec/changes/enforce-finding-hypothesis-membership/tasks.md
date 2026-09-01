## 1. Контракт и TDD

- [x] 1.1 Добавить RED-тест cross-hypothesis carryover
- [x] 1.2 Подтвердить `UNSAFE_PASS` на exact base
- [x] 1.3 Добавить positive и explicit multi-hypothesis controls
- [x] 1.4 Зафиксировать membership rule в contract и eval

## 2. Реализация и candidate verification

- [x] 2.1 Реализовать направленную membership-проверку без расширения scope
- [x] 2.2 Пройти focused/full tests, strict skill validation и OpenSpec validation
- [x] 2.3 Проверить exact candidate из чистой копии и получить независимый review
- [x] 2.4 Опубликовать только feature branch и подтвердить неизменность remote `main` и global skill

## 3. Promotion после отдельного human approval

- [ ] 3.1 Получить exact-byte human approval конкретного candidate commit
- [ ] 3.2 Опубликовать одобренный commit в `main` и подтвердить live SHA
- [ ] 3.3 Синхронизировать `~/.codex/skills/ksrf-explore-arguments` и подтвердить exact hashes
- [ ] 3.4 Повторить проверки на опубликованных байтах и только затем архивировать OpenSpec change
