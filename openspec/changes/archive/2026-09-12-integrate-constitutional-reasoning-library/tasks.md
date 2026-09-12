## Source audit

- [x] Зафиксировать точный 37-PDF manifest (18 книг/работ, включая один поздний полнотекстовый сборник, + 19 журнальных выпусков): SHA-256, страницы, библиография, extraction quality и дубликаты.
- [x] Прочитать оглавления и релевантные разделы; связать каждую принятую операцию с точным locator и контртезисом.
- [x] Провести overlap-аудит против актуальных 16 пакетов и отклонить пересказы без новой проверочной ценности.

## Skill and documentation changes

- [x] Интегрировать принятые операции в существующие одноуровневые references и добавить только необходимые trigger-ссылки в `SKILL.md`.
- [x] Донасытить evidence-ledger картой `fact_assembly / fact_deployment / reviewer_own_assembly` и ограниченным `SystemicDataAcquisitionGap`, не создавая отдельного книжного runtime-слоя.
- [x] Добавить в тот же evidence-ledger role audit исторического тезиса и повторную проверку фактического нарратива прежнего судебного акта, не превращая его в holding.
- [x] Обновить публичные документы об авторах и источниках без публикации полных текстов, OCR или реконструирующих выдержек.
- [x] Добавить реалистичные evals/tests для norm/fact/procedure, causation/proportionality и comparative-transfer границ.
- [x] После завершённого извлечения переместить входные PDF из inbox в локальный научный архив и проверить отсутствие необработанных поддерживаемых файлов.

## Verification and release

- [x] Выполнить source/provenance checks, advisory skill scan, OpenSpec strict validation и затронутые тесты.
- [x] Выполнить полный source-suite, repo validator, clean-room install и проверить 16-package manifest/runtime fingerprint.
- [x] Провести независимый review конкретного diff и поведенческих примеров; записать точные границы доказанного.
- [x] Опубликовать scoped atomic commit в `aegorfk/ksrf-skillset:main`, подтвердить remote SHA и синхронизировать глобальную установку.
