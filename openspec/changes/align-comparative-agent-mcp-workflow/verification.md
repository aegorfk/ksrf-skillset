# Проверка маршрута агентного исследования

Дата: 2026-09-20. Проверенная база выпуска: `940c438816760417f2d97a1e0c1ee376e0cd5bb3`.

## Изменение

Три скилла направляют агента через доступный MCP к адаптивному поиску, чтению полных актов и официальному поиску для закрытия конкретных пробелов. Методика остаётся переносимой между транспортами, предметами спора и средами. Отсутствие MCP или готового смыслового индекса не блокирует доступное исследование. Российские основания, неблагоприятная практика, роли источников и приватность остаются самостоятельными проверками. Юридические доктрины, fixtures, серверы и облачные ресурсы не изменены.

## Проверки

- Quick validation трёх изменённых скиллов: passed.
- Строгий source profile: 16/16, 0 ошибок, 0 предупреждений; public-source и repository safety включены.
- Offline self-containment: 16 скиллов, passed.
- OpenSpec: 71 passed, 0 failed при `validate --all --strict`.
- Clean-room установка и проверка окончательного runtime: 16/16, 307 файлов, 11 115 678 байт; digest `e2548649b393b89f44bdfaab33ec1f82f9e8b03a06cedd9ca6b905d90b811219`.
- Первый полный `pytest -q tests`: 637 passed, 11 skipped, 4 failed, 3290 subtests passed. Три падения воспроизведены на неизменённом baseline: устаревшие ожидаемые диапазоны и SHA уже опубликованных синтетических примеров. Четвёртое связано с намеренным изменением текста `ksrf-explore-arguments/SKILL.md`.
- Проверены канонические изменения `7e8f7ca`, `fc54fe6`, `940c438`: execution 1–16 и QA 1–42 сохранены; дополнения execution 17–19 и QA 43–45 синтетические, без файлов. Обновлены только ожидаемые значения тестов; ограничения и проверки сохранены и распространены на новые примеры.
- Повторный прогон трёх затронутых test-модулей: 22 passed, 122 subtests passed. После обновления контрольных значений повторялся этот направленный набор, а не весь набор из 652 тестов.
- Повторные проверки окончательного дерева: строгий source profile — 16/16, 0 ошибок и предупреждений; OpenSpec — 71 passed, 0 failed; `git diff --check` — passed. Свежий live main совпал с указанной базой выпуска.
- Независимая побайтовая проверка глобальной установки до обновления: 16 скиллов и 306 файлов совпадают с baseline; посторонних изменений, отсутствующих или лишних runtime-файлов нет.

## Независимая проверка поведения

Отдельный агент получил методику и два самодостаточных синтетических сценария без эталонного ответа. Сценарий A: отзыв разрешения, недоступный смысловой поиск, разрыв покрытия по годам и довод заявителя на первой странице MCP. Агент прочитал продолжение, отличил позицию суда от довода стороны, учёл неблагоприятный исход и запланировал адресный официальный поиск за непокрытый период. Сценарий B: социальная выплата и доступ к доказательствам при отсутствии MCP. Агент продолжил по доступному первичному тексту, не смешал процессуальную гарантию с правом на выплату и оставил российское нормативное звено условным.

Оба сценария passed по проверяемому маршруту. Внешних вызовов и изменений данных не было; запланированный поиск не выдавался за выполненный. Проверка не устанавливает качество будущей жалобы или юридический результат реального дела. Синтетические входы и ответ остаются вне runtime; SHA входа `9e797cd5019f21f5d878b8a20ace2ec049881d659c1bd9eb143cf2b9913c9044`, ответа `778a7f1d8c8c03f7ffaeb7e80521d0e1cf9eec8dcd6e5f0ea70e3d7b804c6c49`.

## Точный состав атомарного выпуска

- `skills/constitutional-comparative-research/SKILL.md`
- `skills/constitutional-comparative-research/references/agent-research-workflow.md`
- `skills/constitutional-comparative-research/references/corpus-and-provenance.md`
- `skills/ksrf-explore-arguments/SKILL.md`
- `skills/ksrf-complaint-cycle/SKILL.md`
- `tests/test_nonparticipant_enforcement_method.py`
- `tests/test_reparative_guarantee_access.py`
- `tests/test_runtime_retrospective_examples.py`
- `skills-manifest.json`
- `openspec/changes/align-comparative-agent-mcp-workflow/proposal.md`
- `openspec/changes/align-comparative-agent-mcp-workflow/design.md`
- `openspec/changes/align-comparative-agent-mcp-workflow/specs/comparative-agent-research/spec.md`
- `openspec/changes/align-comparative-agent-mcp-workflow/tasks.md`
- `openspec/changes/align-comparative-agent-mcp-workflow/verification.md`

## Postflight доставки

После одного атомарного commit требуются push в канонический main, равенство HEAD свежему live SHA, успешный `verify_publication_state.py`, глобальная установка из опубликованного checkout, runtime verify и чистый git status. Подготовка этого файла не доказывает выполнение postflight; окончательное подтверждение с SHA даётся в отчёте задачи.
