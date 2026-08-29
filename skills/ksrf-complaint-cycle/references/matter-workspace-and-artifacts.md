# Matter workspace и артефакты

## Структура

```text
matter-root/
  matter.json
  inputs/
  sources/
  norm_versions/
  application/
  issues/
  adverse/
  draft/
  release/
  audit/
  private/
```

`matter.json` хранит `schema_version`, `matter_id`, профиль, privacy class, стадии, blockers и версии зависимых артефактов.

## Регистрация входа

Для каждого файла/URL сохрани:

- stable `document_id`;
- роль документа и стадию;
- origin/receipt time;
- raw SHA-256 и extracted SHA-256;
- acquisition transport и transform chain;
- authority class;
- privacy class и consent link;
- extraction/visual-validation status;
- supersedes/duplicates relations.

Новый hash создаёт новую версию. Не перезаписывай доказательственную историю.

## Основные артефакты

- `CapabilityReport` — операционная готовность.
- `SourceObservation` — результат попытки доступа, включая negative/access state.
- `SourceEvidence` — реально полученный документ с identity/hashes.
- `NormVersionPassport` — редакции по юридически значимым датам.
- `StageApplicationRecord` — три оси использования нормы по каждому акту.
- `AdmissibilityMatrix` — юридические hard gates.
- `FailedComplaintRecord` — публичный отказ или consent-controlled submission episode.
- `ConstitutionalIssueOption` — один доказуемый вариант проблемы.
- `SentenceEvidenceMap` — тезис → источник/locator/предел.
- `FilingPackageManifest` — реальные файлы, hashes, QA, approvals и blockers.

## Инвалидация

Изменение raw hash, редакции нормы, критического акта, application finding, выбранной issue option или существенного предложения делает зависимые артефакты `stale`. Human approval не переживает изменение объекта, который был одобрен.

## Unknown policy

Не заполняй неизвестные значения модельной догадкой. Используй `unknown`, `record_missing`, `source_unavailable`, `conflict` или `ABSTAIN_PENDING_RECORD` и точную задачу, способную изменить состояние.
