## 1. Контракт и TDD

- [x] 1.1 Добавить RED-тест section-anchored верхнеуровневого binding
- [x] 1.2 Подтвердить отсутствие контракта на exact base
- [x] 1.3 Добавить decoy/nested negative controls и safe-default positive control
- [x] 1.4 Зафиксировать fail-closed правило в reference и eval

## 2. Candidate verification

- [x] 2.1 Пройти focused/full tests, strict skill validation и OpenSpec validation
- [x] 2.2 Проверить exact candidate из чистой копии и получить независимый review
- [x] 2.3 Механически пересобрать manifest и проверить его соответствие байтам
- [x] 2.4 Опубликовать только feature branch и подтвердить неизменность remote `main` и global skill

## 3. Promotion после отдельного human approval

- [ ] 3.1 Получить exact-byte human approval конкретного candidate commit
- [ ] 3.2 Опубликовать одобренный commit в `main` и подтвердить live SHA
- [ ] 3.3 Синхронизировать `~/.codex/skills/ksrf-court-request-motion` и подтвердить exact hashes
- [ ] 3.4 Повторить проверки на опубликованных байтах и только затем архивировать OpenSpec change
