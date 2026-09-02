# Design

## Public shell route

`install.sh` принимает два взаимоисключающих read-only режима: `--status` и `--verify-current`. `--json` сохраняется только у `--status`: у current-verification до запуска валидатора возможен отдельный preflight failure, для которого нет validator JSON, поэтому публичный wrapper не создаёт смешанную машинную схему. Автоматизация использует стабильные коды результата. Режим проверки актуальности сначала выполняет офлайн-preflight существующим repo-side status-инспектором и допускает сеть только для структурно чистого, неширокого и не-symlink target. Затем он запускает repo-side `validate_ksrf_skillset.py` и не вызывает publication guard, установщик, восстановление или печать `export`.

## Validator contract

Новый additive-флаг `--require-current` допустим только вместе с `--check-updates`, полным canonical scope и runtime-профилем. После существующей проверки ошибок и strict-предупреждений он отображает freshness в код процесса: `current=0`, `different=10`, `unknown=20`. JSON-схема не меняется; human heading в current-required режиме прямо называет итог `current`, `different`, `unknown` либо validation failure и не печатает ложное «ПРОЙДЕНО». Без `--require-current` прежние коды и заголовки валидатора остаются неизменными.

Положительный `current` выдаётся только после повторного локального identity-прохода по завершении сетевого сравнения и повторного сравнения lexical runtime-root с исходными device/inode/type/resolved-path. Если target-файл или сам root изменился в сетевом окне, report получает `RUNTIME_IDENTITY_CHANGED`/`RUNTIME_ROOT_CHANGED`, freshness становится `unknown`, и validation failure имеет приоритет. Current-required режим запрещает `--report-out`, чтобы после финального identity-прохода не записать отчёт внутрь проверяемого target; JSON при необходимости остаётся только в stdout внутреннего validator CLI.

## Status guidance

Чистый статус остаётся полностью офлайн. Он проверяет наличие обычного исполняемого repo-side `install.sh` и рекомендует shell-quoted абсолютный путь `<repo>/install.sh --verify-current --target <exact absolute target>`. Если entry point отсутствует, неисполняем, является symlink, либо entry point/target содержит непечатаемые или surrogateescaped символы, выводится честный fallback без несуществующей или визуально подменяемой команды. Для non-clean статусов entry point не инспектируется.

## Safety boundaries

- Сеть открывается только из явно выбранного `--verify-current`/`--check-updates`.
- Удалённый SHA и manifest читаются по уже существующему ограниченному freshness-протоколу.
- `different` не означает повреждение, а `unknown` не превращается в `current`.
- Никакой режим не утверждает актуальность законодательства, судебной практики, provenance установки или filing readiness.

## Verification

Сначала RED-тесты фиксируют CLI argv, взаимную исключительность, отсутствие install/publication side effects, JSON и все три freshness exit-кода. После реализации запускаются focused tests, полный root suite, полный skill suite, strict source/runtime validators, shell/AST/public guards, clean-room установка и независимый security/user review.
