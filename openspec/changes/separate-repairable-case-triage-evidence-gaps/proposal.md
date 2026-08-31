## Why

Текущий `ksrf-case-triage` уже не повышает доказательство применения нормы по карточке, доводу стороны или обрезанному цитатному окну. Однако слепой baseline показал другой дефект: устранимый пробел в уже имеющемся акте маршрутизируется как `ABSTAIN_PENDING_RECORD`, хотя воздержание предназначено для записи, недоступность которой подтверждена документированным поиском. Кроме того, repair-задача не всегда требует проверить причинный фрагмент, самостоятельные основания и двунаправленную связь цитаты с источником.

## What Changes

- Разделяется управляемый ремонт evidence packet (`FIX_FIRST`) и недоступная после bounded search запись (`ABSTAIN_PENDING_RECORD`).
- Для каждой пары `норма × стадия` вводится компактный `ApplicationEvidenceRecord` с явными полями источника, цитаты, роли говорящего, причинной роли, самостоятельного основания и сохранения довода.
- Для неполного окна задаётся одна ограниченная repair-задача с проверками `claim→source`, `source→claim` и `quote→page` на той же версии акта.
- Добавляется adversarial eval и сохраняются прежние evals как controls.

## Capabilities

### New Capabilities

- `ksrf-case-triage-evidence-routing`: fail-closed маршрутизация неполного доказательства применения нормы без смешения исправимого пробела и недоступной записи.

### Modified Capabilities

Нет существующего основного spec-слоя для `ksrf-case-triage`; изменение ограничено новой capability и текущим skill contract.

## Impact

- `skills/ksrf-case-triage/SKILL.md`.
- `skills/ksrf-case-triage/evals/evals.json`.
- `skills-manifest.json` как механическая проекция candidate skill tree.
- OpenSpec-артефакты и синтетические baseline/candidate evidence без материалов реального дела.
- Без изменения глобально установленных skills, filing authority, официальных источников или иных пакетов.
