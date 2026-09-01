# Change: Exclude maintainer automation backlog from user runtime

## Why

`skills/ksrf-argument-patterns/references/automation-backlog.md` — это 259-строчный план будущей разработки с формулами «сделать», а не исполняемый пользовательский маршрут. Он занимает 22 929 байт в каждой установке, описывает нереализованные ingestor/radar/eval и может создать ложное впечатление о доступной автоматике.

## What changes

- Классифицировать только exact identity `ksrf-argument-patterns/references/automation-backlog.md` как tracked source-only maintainer backlog.
- Исключить его из manifest, clean install и глобального runtime; удалять stale-копию при переустановке.
- Сохранить backlog tracked и byte-preserved в source/reverse-sync, под secret/local-path/symlink/public-artifact checks.
- Убрать два runtime-backlink и вести их к уже исполняемым QA, evidence, authority и filing routes.
- Зафиксировать карту владения всех 23 backlog-идей, чтобы не потерять полезные gates и не выдавать планы за готовый функционал.

## Impact

- Frozen base: `4a45540a6fdb21745f58220a197c02c790f8b35d`.
- Source file: 259 строк, 22 929 байт, SHA-256 `d25a9df36f6c1d7d995deae35f22a6b9875ac6597251342492ae69a111d75e94`.
- Итоговый runtime: 15 пакетов / 235 файлов / 8 065 560 байт, tree SHA-256 `4ff5b3bfdca737d2a56c7d47987b196dde4f9ab83186a2c088f0377452d7b5a8`; net-сокращение от frozen base — 1 файл / 22 972 байта после замены ложного автоматического маршрута на доказательственные карты ходатайства/запроса. Release tree: 9 файлов / 198 479 байт, SHA-256 `4600d103f1c98644fac8297e6a32ca43b32c5640bff43628c70ebd71ecdac35a`.
- Затронуты contract, portable validator, installer tests, source security, два runtime routes, manifest и публичная документация.

## Non-goals

- Не удалять backlog из Git и не добавлять его в `.gitignore`.
- Не реализовывать описанные в backlog сервисы в этом change.
- Не менять legal/human filing gates, official-source policy или содержательные выводы.
- Не исключать другие Markdown по basename, suffix или glob.
