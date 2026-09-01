# Представление происхождения доводов сторон в ECHRArgumentPacket

## Почему

Контракт уже требует для `applicant|government|third_party` фиксировать способ воспроизведения довода, отсутствие оригинальной жалобы в источнике и неизвестную полноту жалобы. Однако эти значения нельзя записать в объявленную форму `ECHRArgumentPacket`: поля отсутствуют в типизированном блоке. Из-за этого исполнитель может выполнить текстовое правило, но вернуть пакет, который не доказывает границы публичного источника.

## Что меняется

- Добавить в форму `ECHRArgumentPacket` поля `reproduction_mode`, `original_application_in_source` и `complaint_completeness` рядом с `source_form`.
- Закрепить контрактным тестом, что все три поля присутствуют в форме и что submission-gate требует безопасных значений.
- Уточнить negative eval: публичное воспроизведение довода не является оригинальной жалобой и не доказывает её полноту.

## Не входит

- Новая классификация actor, court treatment или majority response.
- Изменение lifecycle, российского anchor gate или условий drafting reuse.
- Продвижение кандидата в `main` либо синхронизация глобального скилла без отдельного точного human approval.

## Затрагиваемые файлы

- `skills/ksrf-echr-argumentation/references/mcp-argument-intelligence-contract.md`
- `skills/ksrf-echr-argumentation/references/verified-hudoc-pilot-fixture.md`
- `skills/ksrf-echr-argumentation/tests/test_interface_contract.py`
- `skills/ksrf-echr-argumentation/evals/evals.json`
- `skills-manifest.json` (механически пересобранный publish manifest)
