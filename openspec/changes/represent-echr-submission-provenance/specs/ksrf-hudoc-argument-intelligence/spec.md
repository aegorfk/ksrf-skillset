## ADDED Requirements

### Requirement: Submission packets SHALL represent public-source provenance explicitly

Форма `ECHRArgumentPacket` SHALL содержать отдельные поля `reproduction_mode`, `original_application_in_source` и `complaint_completeness`. Для `source_actor=applicant|government|third_party` и `source_form=reproduced_in_public_act` пакет SHALL фиксировать доказуемый `reproduction_mode` либо `unclear`, если публичный акт не позволяет отличить цитирование от пересказа, а также `original_application_in_source=false` и `complaint_completeness=unknown_from_public_act`. Поясняющий текст вне формы SHALL NOT заменять эти поля.

#### Scenario: Applicant argument is reproduced in a public judgment

- **WHEN** публичный акт воспроизводит довод заявителя, но оригинальная application form не входит в источник
- **THEN** типизированный пакет содержит фактический `reproduction_mode`
- **AND** содержит `original_application_in_source=false`
- **AND** содержит `complaint_completeness=unknown_from_public_act`
- **AND** SHALL NOT представлять публичный пересказ как полный оригинальный текст жалобы

#### Scenario: Packet template omits one provenance field

- **WHEN** в форме отсутствует хотя бы одно из трёх обязательных полей
- **THEN** submission provenance gate SHALL fail closed
- **AND** пакет SHALL NOT считаться типизированным `ECHRArgumentPacket`
