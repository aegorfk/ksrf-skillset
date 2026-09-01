## Context

Canonical repository одновременно является исходником и источником установки. `install_skillset.py` использует `payload_files()` из `tools/skillset_file_contract.py`, поэтому сейчас все файлы внутри 15 skill directories, кроме runtime/secrets exclusions, копируются в `~/.codex/skills`. В результате unit tests и их fixtures устанавливаются пользователю, хотя выполняются только из source checkout. OpenSpec находится вне `skills/` и уже не копируется.

## Goals / Non-Goals

**Goals:**

- Уменьшить global install без удаления source evidence.
- Сделать один file contract источником истины для manifest, installer и hash verification.
- Сохранить все runtime, UI, schema, reference, script и eval assets.
- Доказать точный состав через unit test и clean-room hash verification.

**Non-Goals:**

- Удалять или игнорировать `openspec/`.
- Удалять тесты из Git.
- Исключать `evals/` либо менять validator requirements.
- Создавать второй dist branch или дублировать skills.
- Менять юридическую методологию, human gates или filing authority.

## Decisions

1. **Исключение определяется path component.** Любой файл, у которого относительный путь содержит компонент `tests`, считается development-only и не входит в install payload.
2. **Source остаётся полным.** Tests продолжают выполняться до публикации; clean `HEAD == live main` связывает их с release commit. Обратный global→repo sync сохраняет exact development-only paths из target source tree, одновременно заменяя runtime payload и удаляя stale runtime files.
3. **Evals остаются установленными.** Строгий skillset validator требует behavioral и trigger evals для каждого пакета, поэтому они не смешиваются с этим cleanup.
4. **OpenSpec остаётся source evidence.** `.gitignore` не применяется к tracked files и не является distribution mechanism.
5. **Один contract для copy/hash.** Manifest generation, clean-room install и global verification используют тот же `payload_files()`. Portable skillset validator зеркалит development-only path rule, потому что он должен работать автономно из установленного skill и не может импортировать repository tools.
6. **Source и target не пересекаются.** Installer сравнивает канонические пути и до любых записей отклоняет equality, ancestor и descendant overlap, чтобы runtime-only замена не могла удалить source tests.

## Risks / Trade-offs

- **Пользователь не сможет запускать unit tests из глобальной установки.** Это намеренно: поддерживаемый test path — canonical source checkout.
- **Новый runtime-файл случайно положат в `tests/`.** Он будет исключён; структура package должна хранить runtime fixtures вне development test tree.
- **Reverse sync удалит source evidence.** Sync обязан включать отдельный preserve-target-development mode и проверять exact bytes сохранённых paths до атомарной замены.
- **Installer запустят поверх checkout.** Любое пересечение source/target блокируется до staging и replacement.
- **Manifest заметно изменится.** Exact clean-room и package-level hash checks обязательны до push/install.

## Migration Plan

1. Получить RED на synthetic `tests/` tree, которое сейчас копируется.
2. Добавить минимальное development-only exclusion в общий file contract.
3. Доказать RED/GREEN, что reverse sync сохраняет target tests и всё ещё удаляет stale runtime files.
4. Пройти focused/root/full skillset/OpenSpec validation.
5. Регенерировать manifest от exact live base SHA.
6. Проверить clean-room install, опубликовать атомарно в `main` и повторить global exact-hash verification.

## Open Questions

Нет блокирующих вопросов.
