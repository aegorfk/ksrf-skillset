## 1. Контракт и документация

- [x] 1.1 Добавить обязательное агентное правило завершённости публикации и отчёта о блокерах.
- [x] 1.2 Описать операторский release workflow, live SHA-проверку и clean-room исключение.
- [x] 1.3 Обновить README с кратким контрактом для разработчиков и безопасной установки.

## 2. Fail-closed enforcement

- [x] 2.1 Реализовать stdlib guard для expected remote, чистоты checkout, live `main` SHA и manifest tree.
- [x] 2.2 Подключить guard к глобальной установке до любых изменений целевого каталога.
- [x] 2.3 Подключить preflight и регенерацию манифеста к синхронизации глобальных скиллов.

## 3. Проверка

- [x] 3.1 Добавить автоматические тесты pass/fail сценариев publication guard.
- [x] 3.2 Выполнить shell syntax, Python tests, OpenSpec validation и dry-run проверки без изменения глобальных скиллов.
- [x] 3.3 Зафиксировать точный изменённый манифест; commit и push оставить родительской release-задаче.

## 4. Исправления по review

- [x] 4.1 Объединить allowlist/exclusions manifest, canonical и clean-room copy; блокировать broad/symlink/non-directory цели до записи.
- [x] 4.2 Покрыть digest-ами исполняемые release-tools и ввести active/retired контракт зеркальных tools.
- [x] 4.3 Проверять формат, существование и точное равенство `remote_base_commit == HEAD^` и добавить регрессионные тесты.
