# Реальный filing package и release gate

## Structured complaint

Рабочая модель содержит обязательные разделы жалобы, `matter_id`, `draft_id`, source/version bindings, norm passport IDs, выбранную issue option, approvals, formal check и `SentenceEvidenceMap`.

Для каждого filing-significant предложения запиши:

- stable sentence ID;
- роль: факт, мотив суда, текст нормы, holding, application finding, practice claim, adverse authority, remedy;
- evidence IDs и locators;
- support status;
- предел формулировки.

Unsupported или overclaimed sentence не проходит в release draft.

## Артефакты

Release pack содержит реальные:

- `constitutional-complaint.docx`;
- `constitutional-complaint.pdf`;
- опись приложений и включённые файлы/инструкции;
- sentence evidence map;
- unresolved-risk register;
- `filing-package-manifest.json`;
- page previews/visual-review record;
- SHA-256 каждого файла.

План export job или строка `DOCX ready` без файла не является артефактом.

## Проверка DOCX/PDF

- обязательные разделы и headings;
- единая первая страница и стили;
- отсутствие placeholders;
- совпадение filing-significant текста после PDF conversion;
- page count и читаемость;
- clipping, overlap, blank unexpected pages, broken tables, orphan headings, margins и pagination;
- совпадение ссылок на приложения с описью;
- renderer и version в manifest.

Если LibreOffice, pypdf, pdftoppm или visual review недоступны, release остаётся blocked с точным remediation.

## Статусы

- `working_draft` — разрешены blockers/placeholders, не готово к выпуску.
- `blocked` — legal/evidence/operational/release gate не закрыт.
- `ready_for_expert_review` — файлы технически собраны, но human legal approval не завершён.
- `ready_for_human_signing_filing` — gates закрыты; остаются только внешние действия человека.

## Инвалидация

Изменение source hash, NormVersionPassport, application record, issue selection, sentence text, enclosure или formal-rule freshness отменяет прежний release approval и требует нового manifest.

## Человеческая граница

Skill не применяет УКЭП, не платит пошлину, не отправляет пакет, не утверждает факт подачи. Финал — проверенный комплект и checklist для заявителя/представителя. Внешнее событие фиксируется только после фактического подтверждения человеком.
