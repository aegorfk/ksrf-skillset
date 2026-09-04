## ADDED Requirements

### Requirement: Native reliability doctor diagnoses the exact triple

The installed `judicial_meaning.py quality native-reliability doctor` command MUST
accept `--coding-reliability`,
`--coding-audit-finalization-receipt`, and
`--expected-finalization-receipt-sha256` as three distinct inputs. It MUST NOT
infer the expected digest from the receipt. When all inputs are present and
individually valid, it MUST apply the existing Release 17 native-reliability
rules without weakening or duplicating them: the complete non-stale closed
`coding_reliability` v1.1 contract and evidence self-digest, the closed
finalization-receipt contract and recomputed receipt self-digest, equality with
the separately supplied lowercase expected digest, the exact reliability-file
digest, audit-plan digest equality, and exact ordered candidate-population
equality.

Each supplied file MUST be a finite regular local file, not a symlink, directory,
device, or FIFO, and MUST be at most 64 MiB so a handler invocation cannot block
on a special file or consume unbounded memory. The reliability input bytes MUST
equal compact sorted-key UTF-8 JSON with `ensure_ascii=false`,
`allow_nan=false`, and exactly one trailing LF. The receipt
`coding_reliability_file_sha256` MUST equal SHA-256 of those exact bytes. The
receipt self-digest MUST be recomputed over canonical compact sorted-key UTF-8
bytes of the receipt without `receipt_sha256` and without adding a file LF.
Any rejection by this bounded regular-file preflight, including the type and
size rules above, MUST use the corresponding closed `*_unreadable` reason and
top-level `status=unreadable`; it MUST NOT add a path, size, or operating-system
error to the report.

Candidate membership and ordered difference-population validation MUST use
bounded indexes and remain linear in the number of candidates and difference
pairs, treating the closed difference-field set as constant. A valid-shaped
input near the byte limit MUST NOT trigger repeated full scans of a candidate or
pair list.

The doctor MUST NOT accept a current-plan argument. Its `valid` state establishes
only the portable technical relation; every downstream consumer MUST continue to
revalidate its current plan, trusted origin, exact six bindings, and independent
claim-readiness gates.

#### Scenario: Exact retained triple is valid

- **WHEN** the user supplies the unchanged canonical reliability file, its exact
  finalization receipt, and the lowercase receipt self-digest independently
  retained from successful finalizer stdout
- **THEN** the doctor reports `status=valid` only when every Release 17 contract
  and relation check succeeds
- **AND** it does not assert current-plan, reviewer, legal, or filing authority

#### Scenario: One triple member is absent

- **WHEN** one or more of the three doctor options is omitted
- **THEN** the doctor reports `status=incomplete`
- **AND** it does not obtain the missing expected digest from a receipt member or
  a default path

#### Scenario: Individually valid members do not bind

- **WHEN** all three members are individually valid but a receipt self-digest,
  external digest, exact reliability-file digest, audit-plan digest, or ordered
  candidate population does not match
- **THEN** the doctor reports `status=mismatch`
- **AND** native technical lineage remains unavailable

#### Scenario: Release16 external anchor was not retained

- **WHEN** exact Release 16 reliability and receipt files remain but no trustworthy
  successful-stdout digest was retained outside the directory
- **THEN** the doctor treats the triple as incomplete
- **AND** it never promotes the receipt member to the missing external expectation

#### Scenario: Large valid-shaped populations remain bounded

- **WHEN** a reliability report or finalization receipt contains a large valid
  candidate population and a bounded set of difference pairs
- **THEN** membership and ordered-population checks use indexed linear passes
- **AND** validation does not rescan the full candidate or pair list for each item

### Requirement: Native reliability doctor report is closed deterministic and value-free

Every doctor invocation that reaches the handler MUST emit exactly one report
whose top-level members are exactly `schema_version`, `artifact_type`, `status`,
`native_relation_valid`, `reason_codes`, `checks`, `remediation`, and `scope`.
`schema_version` MUST equal `1.0`; `artifact_type` MUST equal
`native_reliability_doctor_report`; `status` MUST be exactly one of `valid`,
`incomplete`, `mismatch`, `invalid`, or `unreadable`; and
`native_relation_valid` MUST be true if and only if `status=valid`.

`checks` MUST contain exactly the following members:

- `coding_reliability_present`
- `coding_reliability_readable`
- `coding_reliability_contract_valid`
- `coding_reliability_complete`
- `finalization_receipt_present`
- `finalization_receipt_readable`
- `finalization_receipt_contract_valid`
- `expected_receipt_sha256_present`
- `expected_receipt_sha256_valid`
- `receipt_self_digest_valid`
- `external_receipt_digest_valid`
- `coding_reliability_file_digest_valid`
- `audit_plan_digest_valid`
- `candidate_population_valid`

Presence members MUST be Boolean. Every other check MUST be Boolean when evaluated
and null when a missing, unreadable, or invalid prerequisite prevents evaluation.
`scope` MUST contain exactly `technical_lineage_only=true`,
`consumer_revalidation_required=true`,
`reviewer_identity_authenticated=false`, `legal_readiness=false`, and
`filing_authorized=false`.

`reason_codes` MUST be a duplicate-free list drawn only from this closed enum and
ordered in the following fixed sequence whenever more than one applies:

1. `coding_reliability_unreadable`
2. `finalization_receipt_unreadable`
3. `coding_reliability_json_invalid`
4. `coding_reliability_canonical_bytes_invalid`
5. `coding_reliability_contract_invalid`
6. `finalization_receipt_json_invalid`
7. `finalization_receipt_contract_invalid`
8. `expected_finalization_receipt_sha256_invalid`
9. `coding_reliability_missing`
10. `finalization_receipt_missing`
11. `expected_finalization_receipt_sha256_missing`
12. `coding_reliability_incomplete`
13. `finalization_receipt_self_digest_mismatch`
14. `external_finalization_receipt_digest_mismatch`
15. `coding_reliability_file_digest_mismatch`
16. `audit_plan_digest_mismatch`
17. `candidate_population_mismatch`

Each `remediation` item MUST contain exactly `code` and `message_ru`, MUST be
selected from a fixed reason-to-remediation mapping, deduplicated, and ordered as
`check_local_read_access`, `use_original_finalizer_files`,
`provide_exact_triple`, `retain_external_digest`, then
`recover_in_new_sibling`. The corresponding messages MUST be exactly:

- `Проверьте, что указанный локальный файл существует и доступен для чтения; команда не будет его изменять.`
- `Используйте исходные файлы успешной финализации и не исправляйте их JSON вручную.`
- `Передайте оба неизменённых файла финализации и отдельно сохранённый SHA-256 из её успешного стандартного вывода.`
- `Берите ожидаемый SHA-256 только из стандартного вывода успешно завершившейся финализации и не восстанавливайте его из квитанции.`
- `Повторите финализацию из тех же неизменённых входов в новой соседней папке и побайтово сравните результат.`

Unreadable reasons MUST select `check_local_read_access`; JSON, canonical-byte,
or artifact-contract invalidity MUST select `use_original_finalizer_files`;
missing members and `coding_reliability_incomplete` MUST select
`provide_exact_triple`; a missing or invalid external expectation MUST also
select `retain_external_digest` and `recover_in_new_sibling`; and any relation
mismatch MUST select `recover_in_new_sibling`. Multiple selected entries MUST
remain deduplicated in the fixed remediation order above.

The report MUST NOT include input paths, digest values, candidate identifiers,
coding values, quotations, substantive labels, pseudonyms, attributable
timestamps, exceptions, environment values, or complete input objects. Stdout
MUST be the report serialized as compact sorted-key UTF-8 JSON with
`ensure_ascii=false`, `allow_nan=false`, and exactly one trailing LF. Identical
input presence and bytes MUST therefore produce byte-identical stdout across
repeated, source-tree, and clean-installed runs.

#### Scenario: Hostile invalid values remain private

- **WHEN** a path, malformed JSON object, or closed field embeds distinctive
  private text and doctor validation fails
- **THEN** stdout contains only the closed checks, reason codes, fixed Russian
  remediation, and fixed scope values
- **AND** neither stdout nor stderr repeats the private value or absolute path

#### Scenario: Repeated diagnosis is byte deterministic

- **WHEN** the same three input options and file bytes are diagnosed repeatedly
- **THEN** each run produces byte-identical compact JSON followed by one LF
- **AND** no timestamp, host path, exception wording, or environment-dependent
  member appears

#### Scenario: A prerequisite cannot be evaluated

- **WHEN** a member is absent, unreadable, or invalid before a relation check
- **THEN** that dependent check is null rather than optimistically true or
  ambiguously omitted

### Requirement: Native reliability doctor is read-only and local

After parsing, the doctor MUST read only the explicitly supplied reliability and
receipt files and MUST write only its stdout report. It MUST NOT expose an
`--output` option or invoke a file mutation, temporary-file, subprocess, network,
socket, HTTP, database, import, attachment, repair, finalization, or promotion
path. The portable launcher MUST suppress bytecode writes for the command.

#### Scenario: Valid diagnosis has no external side effect

- **WHEN** the doctor evaluates a valid triple from a clean installed skill
- **THEN** all input bytes and the surrounding directory inventory remain
  unchanged
- **AND** no network, database, subprocess, temporary-file, or mutation entry
  point is called

#### Scenario: Failure remains side-effect free

- **WHEN** a supplied file is unreadable or contains invalid or mismatched data
- **THEN** the doctor emits only its bounded report and exit status
- **AND** it does not repair the file, create an output, or attempt external
  recovery
