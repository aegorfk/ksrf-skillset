# ksrf-native-coding-reliability-binding Specification

## Purpose
TBD - created by archiving change bind-native-coding-reliability-downstream. Update Purpose after archive.
## Requirements
### Requirement: Native coding reliability is an exact verified triple

The system MUST describe coding reliability as native for claim use only after it
verifies the unchanged closed `coding_reliability` v1.1 object, the closed
`coding_audit_finalization_receipt` object, and an independently supplied lowercase
SHA-256 retained from successful finalizer stdout. It MUST recompute both object
digests, require the expected digest to equal the receipt self-digest, and require
the receipt `coding_reliability_file_sha256` to equal SHA-256 of the canonical
compact sorted-key UTF-8 reliability JSON with `ensure_ascii=false`,
`allow_nan=false`, and exactly one trailing LF. It MUST also require exact
audit-plan, candidate-order, completion, and current-plan equalities where the
consumer has a current plan.

The implementation MUST NOT add or infer `native=true`, revise the
`coding_reliability` v1.1 fields, or treat a receipt member as the independently
supplied expectation.

#### Scenario: Confirmed Release16 pair becomes native input

- **WHEN** the exact finalizer reliability file and receipt are supplied with the
  separately retained successful stdout `receipt_sha256`
- **THEN** the verifier accepts native technical lineage only if every digest,
  plan, candidate, and completion equality holds
- **AND** acceptance does not assert authenticated review or legal authority

#### Scenario: Self-consistent artifacts lack an external expectation

- **WHEN** reliability and receipt are internally valid but the caller omits the
  expected digest or derives it only from the receipt being checked
- **THEN** native status is unavailable and every claim-use consumer fails closed

#### Scenario: Outer artifacts are rehashed after substitution

- **WHEN** any reliability, receipt, audit-plan, candidate population, or expected
  digest is replaced and surrounding hashes are recomputed
- **THEN** independent cross-artifact verification rejects the substituted triple

### Requirement: Finalization receipt is the sole four-field quality binding

Claim-bearing quality bindings MUST contain exactly six unique required types. The
`coding_audit_finalization_receipt` binding MUST contain exactly
`quality_type`, `artifact_sha256`, `artifact`, and
`expected_receipt_sha256`. Its `artifact_sha256` MUST bind the complete receipt
object, while `expected_receipt_sha256` MUST equal the independently supplied
external expectation and the recomputed receipt self-digest. Every other quality
binding MUST retain exactly `quality_type`, `artifact_sha256`, and `artifact` and
MUST reject `expected_receipt_sha256`.

#### Scenario: Six bindings preserve two different receipt digests

- **WHEN** a reviewed result carries all six required bindings
- **THEN** the receipt binding keeps the full-object artifact digest distinct from
  the out-of-band receipt self-digest and both are independently verified

#### Scenario: Generic binding smuggles an expectation

- **WHEN** a non-receipt binding includes `expected_receipt_sha256`, or the receipt
  binding omits it
- **THEN** the closed discriminated-union validator rejects the result

### Requirement: Native-binding diagnostics disclose no review content

Every new native-binding failure MUST emit only bounded reason codes, field names,
counts, permitted candidate identifiers, and SHA-256 values. It MUST NOT echo
coding values, quotations, substantive labels, pseudonyms, person-attributable
timestamps, complete input objects, or absolute paths. A valid triple MUST remain
only evidence of bounded technical lineage and MUST NOT establish reviewer
identity, authorship, independence, packet use, legal correctness, norm temporal
applicability, freshness, publication permission, approval, or filing readiness.

#### Scenario: Hostile private values fail verification

- **WHEN** an invalid reliability or receipt embeds distinctive private strings
- **THEN** the returned error or incomplete-status projection identifies only the
  bounded failure class and never repeats those strings or their path

### Requirement: Release16 migration never reconstructs a missing anchor

Existing Release16 finalization output SHALL satisfy the new verifier without
regenerating finalization only when the exact successful stdout digest was retained
outside the directory. Downstream uncertainty, handoff, import, state, and evidence
artifacts MUST be regenerated under the new contract. If the external digest is
missing or its confirmation was interrupted or uncertain, the system MUST direct
the user to the existing unchanged-input/new-sibling/byte-compare recovery and MUST
NOT read the expected value from the receipt.

#### Scenario: Existing confirmed finalization is migrated

- **WHEN** a user retains the exact two files and independently recorded successful
  stdout digest from Release16
- **THEN** only downstream artifacts need regeneration and the original
  finalization directory remains immutable

#### Scenario: Only the receipt survives

- **WHEN** the user has the receipt but no trustworthy external confirmation
- **THEN** the receipt self-digest remains audit-readable but cannot be promoted to
  the missing expectation

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

### Requirement: Native finalization comparison consumes two safe siblings and the repeat anchor

The system SHALL expose the installed native finalization comparison command.
The exact route `judicial_meaning.py quality native-reliability
compare-finalizations` MUST accept exactly
`--uncertain-finalization-dir`, `--repeated-finalization-dir`, and
`--expected-finalization-receipt-sha256` as required inputs. The expected value
MUST be lowercase 64-hex retained outside the repeated directory from that
finalizer invocation's complete successful stdout followed by normal return. The
command MUST NOT infer it from either receipt, accept stdin/default/discovery
input, or expose an output path.

Both directories MUST be different direct siblings under one actual parent held
by descriptor for the whole operation. The parent MUST be effective-user-owned,
not group/world writable, and free of every extended ACL on Darwin. Each directory
MUST be effective-user-owned mode `0700`, have a distinct device/inode identity,
be free of every extended ACL on Darwin, and contain exactly:

- `resolved-review-decisions.jsonl`
- `adjudications.jsonl`
- `coding-reliability.json`
- `coding-audit-finalization-receipt.json`

Every file MUST be regular, effective-user-owned mode `0600`, single-link,
distinct from all other input file inodes, and free of every extended ACL on
Darwin. The JSONL and reliability files MUST each be at most 64 MiB, the receipt
MUST be at most 8 MiB, and directory enumeration MUST stop after a fifth entry.
No Linux ACL inspection is claimed. Missing no-follow/descriptor/ACL inspection
capability MUST fail closed.

For each directory, the command MUST verify strict canonical receipt and
reliability JSON, the closed complete/non-stale contracts, both self-digests, and
the audit-plan and ordered-candidate relation. It MUST verify
`resolved_review_decisions_file_sha256`, `adjudications_file_sha256`, and
`coding_reliability_file_sha256` against the exact three sibling file byte
streams. Strict canonical bytes bind the parsed receipt object to the fourth file;
the recomputed `receipt_sha256` checks the unsigned object only and MUST NOT be
described as a full receipt-file SHA-256 because no such member exists. The
uncertain directory has only this internal relation and MUST NOT be called native
or be given an inferred expectation. The repeated directory's native relation MUST
include equality between its recomputed receipt self-digest and the separately
supplied expected digest. The shared evaluator MUST remain the only definition of
these reliability checks.

Success MUST additionally require raw byte-for-byte equality of all four
corresponding files, not only equal hashes, parsed objects, or selected receipt
fields. The command MUST NOT parse or re-adjudicate private resolved values beyond
bounded capture and the established receipt bindings.

#### Scenario: Eligible uncertain output equals an anchored successful repeat

- **WHEN** an earlier diagnostic expressly authorized unchanged-input
  repeat-and-compare recovery, the user supplies its preserved complete directory,
  a safe successful repeated sibling, and the digest retained from the repeat's
  complete successful stdout
- **THEN** `status=match` is available only after every topology, privacy,
  contract, four-file binding, uncertain internal relation, repeated native
  relation, external-anchor, byte-equality,
  and final-recapture check succeeds
- **AND** the command does not reconstruct or emit a digest

#### Scenario: Code two alone does not establish comparison eligibility

- **WHEN** the only known fact about the earlier finalizer is exit code `2`
- **THEN** the command cannot verify that repeat-and-compare recovery was allowed
- **AND** help requires the original diagnostic to have expressly directed that
  recovery before the user invokes comparison

#### Scenario: Staging or inode uncertainty remains administrator-only

- **WHEN** the earlier diagnostic required staging cleanup, inode/link accounting,
  location recovery, security investigation, or quarantine rather than explicitly
  authorizing a repeat
- **THEN** the comparison command is forbidden as a recovery route
- **AND** it does not turn a later safe-looking path into proof that every sensitive
  object was accounted for

#### Scenario: External repeat anchor is absent or copied implicitly

- **WHEN** no separately supplied valid expected digest is available
- **THEN** comparison cannot return `match`
- **AND** neither receipt member is promoted to the missing external input

#### Scenario: Corresponding bytes differ

- **WHEN** both directories are otherwise valid and stable but any corresponding
  fixed file differs by at least one byte
- **THEN** the report has `status=mismatch` and exit `3`
- **AND** it reveals no filename, offset, prefix, digest, size, or content

### Requirement: Finalization comparison capture is TOCTOU-resistant and finally recaptured

The command MUST use no-follow path stat and open-at operations through the one
held parent and held directory descriptors. Before and after every bounded read it
MUST verify device, inode, type, mode, owner, group, link count, size, and
nanosecond modification/change times. Parent and leaf paths MUST continue to bind
the opened identities. Corresponding bytes MUST be compared in bounded chunks and
all validation passes MUST be linear in input size.

After all contracts, digests, and byte equalities are evaluated, the command MUST
fully recapture both directories through the original held parent. Parent,
directory, and file identities, metadata, ACL results, exact inventories, and
bytes MUST equal their initial captures, and both supplied parent paths and leaf
names MUST still bind the retained identities. Drift, an unavailable repeated
inspection, or descriptor-close uncertainty MUST yield
`comparison_input_changed`, `status=unreadable`, and exit `2`; a report based only
on the initial capture MUST NOT claim `match`.

#### Scenario: Same-inode rewrite races comparison

- **WHEN** a file is rewritten in place, replaced, relinked, resized, remoded, or
  retimestamped between initial capture and final recapture
- **THEN** the command fails closed as `unreadable`
- **AND** no initially observed equality survives as a successful result

#### Scenario: Parent or child name is rebound

- **WHEN** a supplied parent path or either child entry no longer names the held
  identity at final recapture
- **THEN** the command reports only the closed input-changed reason
- **AND** it does not follow the replacement or disclose either path

### Requirement: Native finalization comparison report is closed deterministic and value-free

Every invocation that reaches the comparison handler MUST emit exactly one report
whose top-level members are exactly `schema_version`, `artifact_type`, `status`,
`recovery_comparison_valid`, `reason_codes`, `checks`, `remediation`, and `scope`.
`schema_version` MUST equal `1.0`; `artifact_type` MUST equal
`native_finalization_comparison_report`; `status` MUST be exactly one of `match`,
`mismatch`, `invalid`, or `unreadable`; and `recovery_comparison_valid` MUST be
true if and only if `status=match`.

`checks` MUST contain exactly these members:

- `common_parent_valid`
- `directories_distinct`
- `uncertain_directory_readable`
- `repeated_directory_readable`
- `uncertain_directory_private`
- `repeated_directory_private`
- `uncertain_inventory_exact`
- `repeated_inventory_exact`
- `expected_receipt_sha256_valid`
- `uncertain_artifact_contracts_valid`
- `repeated_artifact_contracts_valid`
- `uncertain_receipt_self_digest_valid`
- `repeated_receipt_self_digest_valid`
- `repeated_external_receipt_digest_valid`
- `uncertain_receipt_file_bindings_valid`
- `repeated_receipt_file_bindings_valid`
- `uncertain_internal_relation_valid`
- `repeated_native_relation_valid`
- `directory_file_bytes_equal`
- `final_recapture_valid`

Each check MUST be Boolean when evaluated and null when an unavailable or invalid
prerequisite prevents evaluation. `final_recapture_valid=true` MUST require every
normal recapture prerequisite, while directly observed drift or descriptor-close
uncertainty MUST set it to false even when the drift prevents an earlier prerequisite;
it is null only when recapture is unavailable and no drift was observed. If drift
interrupts raw comparison before equality is established,
`directory_file_bytes_equal` MUST be null rather than false. Every independent safe
check MUST still be attempted so one directory does not hide an independently
observable fault in the other.

`reason_codes` MUST be duplicate-free and follow this exact fixed order:

1. `uncertain_finalization_unreadable`
2. `repeated_finalization_unreadable`
3. `comparison_input_changed`
4. `comparison_topology_invalid`
5. `uncertain_finalization_privacy_invalid`
6. `repeated_finalization_privacy_invalid`
7. `uncertain_finalization_inventory_invalid`
8. `repeated_finalization_inventory_invalid`
9. `expected_finalization_receipt_sha256_invalid`
10. `uncertain_finalization_artifact_contract_invalid`
11. `repeated_finalization_artifact_contract_invalid`
12. `uncertain_finalization_receipt_self_digest_mismatch`
13. `repeated_finalization_receipt_self_digest_mismatch`
14. `external_finalization_receipt_digest_mismatch`
15. `uncertain_finalization_file_binding_mismatch`
16. `repeated_finalization_file_binding_mismatch`
17. `uncertain_finalization_internal_relation_mismatch`
18. `repeated_finalization_native_relation_mismatch`
19. `finalization_directory_bytes_mismatch`

Each `remediation` entry MUST contain exactly `code` and `message_ru`, MUST be
selected from the fixed reason mapping, deduplicated, and ordered as follows:

1. `check_local_read_access`: `Проверьте доступность двух указанных локальных папок, не изменяя их; команда не выполняет восстановление.`
2. `preserve_and_stop`: `Остановите использование обеих папок и сохраните их неизменными; команда ничего не исправляет и не удаляет.`
3. `use_safe_complete_siblings`: `Сравнивайте только две разные полные четырёхфайловые папки финализации у одного приватного родителя; небезопасное или неполное состояние передайте системному администратору.`
4. `retain_successful_repeat_digest`: `Передайте строчный SHA-256 только из полного стандартного вывода успешно и нормально завершившегося повтора; не восстанавливайте его из квитанции.`
5. `administrator_quarantine`: `При изменении inode, жёсткой ссылке, ACL, неучтённом или перемещённом объекте остановите автоматику и передайте состояние системному администратору для учёта всех ссылок и карантина.`
6. `repeat_after_mismatch`: `Не используйте несовпавшие результаты; после проверки причины снова выполните финализацию из тех же неизменённых входов в новую отсутствующую соседнюю папку.`

Unreadable-directory reasons MUST select `check_local_read_access`; input drift
MUST select `preserve_and_stop` and `administrator_quarantine`; topology,
privacy, inventory, or artifact invalidity MUST select `preserve_and_stop`,
`use_safe_complete_siblings`, and `administrator_quarantine`; invalid or
mismatched external expectation MUST select `preserve_and_stop` and
`retain_successful_repeat_digest`; self/file/internal-or-native relation mismatch
MUST select `preserve_and_stop` and `repeat_after_mismatch`; and raw byte mismatch
MUST select `preserve_and_stop` and `repeat_after_mismatch`. When directly observed
input drift or topology/privacy/inventory/artifact invalidity is present, that
administrator-only state MUST suppress `repeat_after_mismatch` even if an independent
mismatch was also observed; remediation MUST NOT advise repeat and quarantine
together.

`scope` MUST contain exactly:

- `technical_recovery_comparison_only=true`
- `original_recovery_eligibility_verified=false`
- `repeat_normal_return_verified=false`
- `external_digest_provenance_authenticated=false`
- `original_durability_verified=false`
- `consumer_revalidation_required=true`
- `reviewer_identity_authenticated=false`
- `publication_safe=false`
- `legal_readiness=false`
- `filing_authorized=false`

The report MUST contain no input path, digest value, file bytes, candidate
identifier, count, substantive value or label, quotation, pseudonym,
person-attributable timestamp, inode/device coordinate, exception, environment
value, or complete input object. Stdout MUST be compact sorted-key UTF-8 JSON with
`ensure_ascii=false`, `allow_nan=false`, and exactly one trailing LF. Equivalent
stable inputs MUST produce byte-identical output.

#### Scenario: Hostile input values remain private

- **WHEN** a path, JSON value, or error embeds distinctive private text
- **THEN** the report contains only fixed enums, Booleans/null, fixed Russian
  remediation, and fixed scope
- **AND** stdout and handler stderr repeat no private value, path, digest, or
  exception text

#### Scenario: A prerequisite prevents evaluation

- **WHEN** an earlier read, privacy, inventory, or artifact prerequisite fails
- **THEN** each dependent check is null rather than true or ambiguously omitted
- **AND** independently safe checks remain deterministic

### Requirement: Native finalization comparison is read-only and local

After parsing, the command MUST read only the two explicitly supplied directories
and MUST write only its stdout report. It MUST NOT mutate permissions or content,
create a temporary or output file, invoke finalization or repair, copy, move,
delete, quarantine, attach, import, persist, promote, spawn a subprocess, or access
a network, socket, HTTP service, or database. The portable launcher MUST suppress
bytecode writes.

#### Scenario: Match has no external side effect

- **WHEN** two valid stable directories match
- **THEN** their bytes, metadata, names, and surrounding parent inventory remain
  unchanged
- **AND** the only attempted write is the canonical stdout report

#### Scenario: Failure performs no recovery action

- **WHEN** either input is unsafe, invalid, changed, or mismatched
- **THEN** the command emits only its bounded report and process status
- **AND** it does not repair, remove, quarantine, retry, or invoke an external path

### Requirement: Native review-import comparison consumes one exact bundle, two safe siblings, and both external anchors

The system SHALL expose the installed native review-import comparison command. The
exact route `judicial_meaning.py quality native-reliability
compare-review-imports` MUST accept exactly `--bundle`,
`--expected-manifest-sha256`, `--uncertain-review-import-dir`,
`--repeated-review-import-dir`, and `--expected-import-receipt-sha256` as
required inputs. The manifest expectation MUST be lowercase 64-hex retained outside
the bundle from the exact preparation invocation's complete successful stdout
followed by normal return. The receipt expectation MUST be lowercase 64-hex retained
outside the repeated import from that import invocation's complete successful stdout
followed by normal return. The command MUST NOT infer either value from a manifest or
receipt, accept stdin/default/discovery input, or expose an output path.

The bundle and both import directories MUST be pairwise distinct direct siblings
under one actual parent held by descriptor for the whole operation. The parent MUST
be effective-user-owned, not group/world writable, and free of every extended ACL on
Darwin. Each directory MUST be effective-user-owned mode `0700`, have a distinct
device/inode identity, and be free of every extended ACL on Darwin.

The bundle MUST contain exactly:

- `screening-candidates.audit.jsonl`
- `primary-decisions.audit.jsonl`
- `coding-audit-plan.json`
- `secondary-review-queue.jsonl`
- `secondary-coding-template.jsonl`
- `independent-review-packet.zip`
- `coding-audit-inputs-manifest.json`

Each import directory MUST contain exactly:

- `audit-decisions.jsonl`
- `coding-audit-review-import-receipt.json`

Every file MUST be regular, effective-user-owned mode `0600`, single-link, distinct
from all other ten input file inodes, and free of every extended ACL on Darwin. The
bundle MUST retain its existing 2 MiB manifest, 4 MiB plan, 256 MiB ZIP, and 64 MiB
other-file bounds. Each decisions file MUST be at most 64 MiB and each receipt at most
8 MiB. Enumeration MUST stop after an eighth bundle entry or a third import entry.
No Linux ACL inspection is claimed. Missing no-follow, descriptor, codebook, or ACL
inspection capability MUST fail closed.

The command MUST first use a strict canonical closed-field manifest preview only to
select a supported codebook version, then securely capture that exact installed
codebook, and only then fully validate the bundle through structured stages shared
with the established native bundle loader. The preview MUST NOT count as a validated
bundle or grant authority. A valid external-manifest mismatch MUST NOT short-circuit
independently safe bundle/codebook checks, while the legacy loader MUST retain its
existing early-error order. Neither path may classify a stage by matching localized
exception text. The command MUST factor and reuse, rather than fork, the existing
native import consumer verifier. For each import that shared verifier MUST validate strict canonical
receipt and decisions bytes, closed contracts, the recomputed receipt self-digest,
the receipt-to-decisions file binding, and every existing receipt-to-bundle fixed
field, digest, candidate-population, audited-field, difference-map/flag, and negative-
scope relation. The legacy loader orchestration MUST retain its exact prior check and
error order: receipt structural/canonical contract, receipt self-digest, required
external expectation, receipt-to-bundle fields and digest-field syntax, decisions
structural/canonical contract, file binding, then difference-map relations. The comparator MUST use the same pure stages
but evaluate every independently safe result instead of allowing an anchor mismatch to
hide a higher-priority invalid or administrator-only fault. Neither orchestration may
classify a stage by matching localized exception text.

The uncertain directory MUST receive only the bundle-bound layer and MUST NOT be
called externally anchored or be given an expectation inferred from its receipt. The
repeated directory MUST receive the same bundle-bound layer plus equality between its
recomputed receipt self-digest and the separately supplied expected import-receipt
digest. The command MUST disclose that it does not re-read the original returned
secondary file or authenticate its cleartext coder label.

Success MUST additionally require raw byte-for-byte equality of both corresponding
files, not only equal hashes, parsed objects, selected receipt fields, or directory
archives. The command MUST NOT re-run import, re-adjudicate private values, or infer
either external anchor.

#### Scenario: Eligible uncertain import equals one anchored successful repeat

- **WHEN** an earlier diagnostic expressly authorized unchanged-input
  repeat-and-compare recovery, and the user supplies one exact externally anchored
  source bundle, its preserved complete uncertain import, a safe successful repeated
  sibling, and the receipt digest retained from the repeat's complete successful
  stdout
- **THEN** `status=match` is available only after every topology, privacy, bundle,
  codebook, contract, receipt, file-binding, bundle-relation, external-anchor,
  two-file byte-equality, and final-recapture check succeeds
- **AND** the command reconstructs or emits neither digest

#### Scenario: Two self-consistent import directories lack the source bundle relation

- **WHEN** the user has two byte-identical import directories but omits the bundle or
  its separately retained manifest digest
- **THEN** argparse rejects the incomplete invocation before handler entry
- **AND** equality alone is not described as the established native import contract

#### Scenario: Code two alone does not establish comparison eligibility

- **WHEN** the only known fact about the earlier importer is exit code `2`
- **THEN** the command cannot verify that repeat-and-compare recovery was allowed
- **AND** help requires the original diagnostic to have expressly directed that
  recovery before the user invokes comparison

#### Scenario: Staging or inode uncertainty remains administrator-only

- **WHEN** the earlier diagnostic required staging cleanup, inode/link accounting,
  location recovery, integrity or security investigation, ACL handling, or quarantine
  rather than expressly authorizing a repeat
- **THEN** the comparison command is forbidden as a recovery route
- **AND** a later safe-looking path cannot substitute for accounting for every
  sensitive object and hardlink

#### Scenario: Either external anchor is absent or copied implicitly

- **WHEN** no separately supplied valid expected manifest or repeated receipt digest
  is available
- **THEN** comparison cannot return `match`
- **AND** no manifest or receipt member is promoted to the missing external input

#### Scenario: Corresponding import bytes differ

- **WHEN** the bundle and both imports are otherwise valid and stable but either
  corresponding fixed file differs by at least one byte
- **THEN** the report has `status=mismatch` and exit `3`
- **AND** it reveals no filename, offset, prefix, digest, size, or content

### Requirement: Review-import comparison is TOCTOU-resistant and finally recaptures every dependency

The command MUST use no-follow path stat and open-at operations through the one held
parent and three held directory descriptors. Before and after every bounded read it
MUST verify device, inode, type, mode, owner, group, link count, size, and nanosecond
modification/change times. Every supplied parent/leaf path MUST continue to bind its
opened identity. Corresponding import bytes MUST be compared in bounded chunks and
all validation passes MUST be linear in input size.

The exact installed codebook selected by the non-authoritative strict manifest preview
MUST be captured through the established secure codebook routine before full bundle
validation. After all contracts, digests, relations, and
byte equalities are evaluated, the command MUST fully recapture the bundle and both
imports through the original held parent and MUST securely recapture the codebook.
Parent, directory, file, and codebook identities, metadata, ACL results, exact
inventories, and bytes MUST equal their initial captures. Both import byte streams
MUST be compared again after both final recaptures. Drift, an unavailable repeated
inspection, or descriptor-close uncertainty MUST yield `comparison_input_changed`,
`status=unreadable`, and exit `2`; a report based only on the initial capture MUST NOT
claim `match`.

#### Scenario: Same-inode rewrite races comparison

- **WHEN** any bundle, import, or codebook file is rewritten in place, replaced,
  relinked, resized, remoded, or retimestamped between initial capture and final
  recapture
- **THEN** the command fails closed as `unreadable`
- **AND** no initially observed equality survives as a successful result

#### Scenario: Parent or child name is rebound

- **WHEN** a supplied parent path or any of the three child entries no longer names
  its held identity at final recapture
- **THEN** the command reports only the closed input-changed reason
- **AND** it does not follow the replacement or disclose any path

#### Scenario: Bundle changes after both imports were evaluated

- **WHEN** the exact source bundle changes after both receipt relations were initially
  checked
- **THEN** final recapture prevents `match` and returns `unreadable`
- **AND** neither import is described as still bound to the changed bundle

### Requirement: Native review-import comparison report is closed deterministic and value-free

Every invocation that reaches the comparison handler MUST emit exactly one report
whose top-level members are exactly `schema_version`, `artifact_type`, `status`,
`recovery_comparison_valid`, `reason_codes`, `checks`, `remediation`, and `scope`.
`schema_version` MUST equal `1.0`; `artifact_type` MUST equal
`native_review_import_comparison_report`; `status` MUST be exactly one of `match`,
`mismatch`, `invalid`, or `unreadable`; and `recovery_comparison_valid` MUST be true if
and only if `status=match`.

The additive installed JSON Schema branch MUST be closed and compact with size linear
in the fixed check/reason/remediation vocabularies. It MUST NOT enumerate combinations
or permutations merely to restate the deterministic builder's ordering; ordering MUST
remain enforced by the builder and source-only tests without inflating the installed
runtime payload.

`checks` MUST contain exactly these members:

- `common_parent_valid`
- `directories_distinct`
- `source_bundle_readable`
- `source_bundle_private`
- `source_bundle_inventory_exact`
- `expected_manifest_sha256_valid`
- `source_bundle_contract_valid`
- `source_bundle_external_manifest_digest_valid`
- `installed_codebook_readable`
- `installed_codebook_binding_valid`
- `uncertain_directory_readable`
- `repeated_directory_readable`
- `uncertain_directory_private`
- `repeated_directory_private`
- `uncertain_inventory_exact`
- `repeated_inventory_exact`
- `expected_import_receipt_sha256_valid`
- `uncertain_artifact_contracts_valid`
- `repeated_artifact_contracts_valid`
- `uncertain_receipt_self_digest_valid`
- `repeated_receipt_self_digest_valid`
- `repeated_external_receipt_digest_valid`
- `uncertain_receipt_file_binding_valid`
- `repeated_receipt_file_binding_valid`
- `uncertain_bundle_relation_valid`
- `repeated_bundle_relation_valid`
- `import_directory_file_bytes_equal`
- `final_recapture_valid`

Each check MUST be Boolean when evaluated and null when an unavailable or invalid
prerequisite prevents evaluation. `final_recapture_valid=true` MUST require every
normal recapture prerequisite, while directly observed drift or descriptor-close
uncertainty MUST set it to false even when drift prevents an earlier prerequisite; it
is null only when recapture is unavailable and no drift was observed. If drift
interrupts raw comparison before equality is established,
`import_directory_file_bytes_equal` MUST be null rather than false. Every independent
safe check MUST still be attempted so one import does not hide an independently
observable fault in the other.

The prerequisite relation MUST be exact: the three readable checks and both expected
digest syntax checks have no check prerequisite; `directories_distinct` requires the
common-parent check and all three readable checks; each privacy check requires the
common-parent check plus its own readable check; and each inventory check requires its
own privacy check. The source-bundle contract requires its inventory; its external
manifest relation requires that contract plus valid manifest-digest syntax; and the
installed-codebook readable check requires a supported codebook version from the
strict canonical preview and records whether secure capture succeeded; the binding
requires the bundle contract plus a true codebook-readable check. Each import artifact contract requires its inventory; its self-digest and
file binding each require that artifact contract; its bundle relation requires that
artifact contract plus the source-bundle contract. The repeated external receipt
relation requires the repeated artifact contract and valid receipt-digest syntax but
MUST remain independently evaluable when the receipt's stored self-digest differs from
the recomputed value. Raw import-directory equality requires distinct directories and
both import inventories. A normal true final recapture requires the common parent,
distinct directories, all three inventories, the source-bundle contract, and the
true installed-codebook-readable check. A false relation MUST NOT suppress another
independently safe relation.

If initial secure codebook capture is unavailable, the report MUST set
`installed_codebook_readable=false`, retain already established bundle observations,
and leave the prevented binding/final-recapture checks null. If codebook recapture is
unavailable, the report MUST set `final_recapture_valid=false` and record input change.
If the exact installed codebook bytes differ from the bundle-bound codebook,
`installed_codebook_binding_valid` MUST be false and MUST map to
`source_bundle_artifact_contract_invalid`; the implementation MUST NOT classify either
case by matching localized exception text.

`reason_codes` MUST be duplicate-free and follow this exact fixed order:

1. `source_bundle_unreadable`
2. `installed_codebook_unreadable`
3. `uncertain_review_import_unreadable`
4. `repeated_review_import_unreadable`
5. `comparison_input_changed`
6. `comparison_topology_invalid`
7. `source_bundle_privacy_invalid`
8. `uncertain_review_import_privacy_invalid`
9. `repeated_review_import_privacy_invalid`
10. `source_bundle_inventory_invalid`
11. `uncertain_review_import_inventory_invalid`
12. `repeated_review_import_inventory_invalid`
13. `expected_manifest_sha256_invalid`
14. `expected_import_receipt_sha256_invalid`
15. `source_bundle_artifact_contract_invalid`
16. `uncertain_review_import_artifact_contract_invalid`
17. `repeated_review_import_artifact_contract_invalid`
18. `external_manifest_digest_mismatch`
19. `uncertain_review_import_receipt_self_digest_mismatch`
20. `repeated_review_import_receipt_self_digest_mismatch`
21. `external_import_receipt_digest_mismatch`
22. `uncertain_review_import_file_binding_mismatch`
23. `repeated_review_import_file_binding_mismatch`
24. `uncertain_review_import_bundle_relation_mismatch`
25. `repeated_review_import_bundle_relation_mismatch`
26. `review_import_directory_bytes_mismatch`

Each `remediation` entry MUST contain exactly `code` and `message_ru`, MUST be
selected from the fixed reason mapping, deduplicated, and ordered as follows:

1. `check_local_read_access`: `Проверьте доступность указанных локальных папок и встроенного справочника, не изменяя их; команда не выполняет восстановление.`
2. `preserve_and_stop`: `Остановите использование обеих папок импорта и сохраните пакет и результаты неизменными; команда ничего не исправляет и не удаляет.`
3. `use_safe_complete_siblings`: `Передавайте один полный семифайловый пакет и две разные полные двухфайловые папки импорта у одного приватного родителя; небезопасное или неполное состояние передайте системному администратору.`
4. `retain_successful_prepare_digest`: `Передайте manifest_sha256 только из полного стандартного вывода успешно и нормально завершившейся подготовки пакета; не восстанавливайте его из манифеста.`
5. `retain_successful_repeat_digest`: `Передайте receipt_sha256 только из полного стандартного вывода успешно и нормально завершившегося повторного импорта; не восстанавливайте его из квитанции.`
6. `administrator_quarantine`: `При изменении inode, жёсткой ссылке, ACL, неучтённом или перемещённом объекте остановите автоматику и передайте состояние системному администратору для учёта всех ссылок и карантина.`
7. `repeat_import_after_mismatch`: `Не используйте несовпавшие результаты; проверьте пакет и внешние якоря, затем только для разрешённого маршрута снова выполните импорт тех же неизменённых входов в новую отсутствующую соседнюю папку.`

Unreadable reasons MUST select `check_local_read_access`; input drift MUST select
`preserve_and_stop` and `administrator_quarantine`; topology, privacy, inventory, or
artifact invalidity MUST select `preserve_and_stop`, `use_safe_complete_siblings`, and
`administrator_quarantine`; invalid or mismatched manifest expectation MUST select
`preserve_and_stop` and `retain_successful_prepare_digest`; invalid or mismatched
receipt expectation MUST select `preserve_and_stop` and
`retain_successful_repeat_digest`; receipt self/file/bundle relation or raw byte
mismatch MUST select `preserve_and_stop` and `repeat_import_after_mismatch`.

When directly observed input drift or topology/privacy/inventory/artifact invalidity
is present, that administrator-only state MUST suppress
`repeat_import_after_mismatch` even if an independent mismatch was also observed;
remediation MUST NOT advise repeat and quarantine together.

`scope` MUST contain exactly:

- `technical_recovery_comparison_only=true`
- `original_recovery_eligibility_verified=false`
- `prepare_normal_return_verified=false`
- `repeat_normal_return_verified=false`
- `external_manifest_digest_provenance_authenticated=false`
- `external_import_receipt_digest_provenance_authenticated=false`
- `original_durability_verified=false`
- `source_workspace_reverified=false`
- `returned_secondary_file_reverified=false`
- `consumer_revalidation_required=true`
- `reviewer_identity_authenticated=false`
- `publication_safe=false`
- `legal_readiness=false`
- `filing_authorized=false`

The report MUST contain no input path, digest value, file bytes, candidate identifier,
count, substantive value or label, quotation, pseudonym, person-attributable timestamp,
inode/device coordinate, exception, environment value, or complete input object.
Stdout MUST be compact sorted-key UTF-8 JSON with `ensure_ascii=false`,
`allow_nan=false`, and exactly one trailing LF. Equivalent stable inputs MUST produce
byte-identical output.

#### Scenario: Hostile input values remain private

- **WHEN** a path, bundle member, receipt, decision, or error embeds distinctive
  private text
- **THEN** the report contains only fixed enums, Booleans/null, fixed Russian
  remediation, and fixed scope
- **AND** stdout and handler stderr repeat no private value, path, digest, identifier,
  coordinate, or exception text

#### Scenario: A prerequisite prevents evaluation

- **WHEN** an earlier read, privacy, inventory, bundle, codebook, or artifact
  prerequisite fails
- **THEN** each dependent check is null rather than true or ambiguously omitted
- **AND** independently safe checks remain deterministic

### Requirement: Native review-import comparison is read-only and local

After parsing, the command MUST read only the three explicitly supplied directories
and the exact installed codebook selected by the validated bundle, and MUST write only
its stdout report. It MUST NOT mutate permissions or content, create a temporary or
output file, invoke import, finalization, repeat, or repair, copy, move, delete,
quarantine, attach, persist, promote, spawn a subprocess, or access a network, socket,
HTTP service, or database. The portable launcher MUST suppress bytecode writes.

#### Scenario: Match has no external side effect

- **WHEN** one valid bundle and two valid stable import siblings match
- **THEN** their bytes, metadata, names, and surrounding parent inventory remain
  unchanged
- **AND** the only attempted write is the canonical stdout report

#### Scenario: Failure performs no recovery action

- **WHEN** any input is unsafe, invalid, changed, or mismatched
- **THEN** the command emits only its bounded report and process status
- **AND** it does not repair, remove, quarantine, retry, import, finalize, or invoke an
  external path

### Requirement: Native audit-bundle comparison binds both repeat anchors

The system SHALL expose installed `judicial_meaning.py quality native-reliability
compare-audit-bundles` with exactly four required long options:
`--uncertain-audit-bundle-dir`, `--repeated-audit-bundle-dir`,
`--expected-manifest-sha256`, and
`--expected-independent-review-packet-sha256`. Both expected values MUST be lowercase
64-hex retained outside the repeated package from the same complete successful
`coding-audit-prepare` stdout followed by normal code-`0` return. The command MUST NOT
infer either value from either package, use either expected value for the uncertain
package, or accept stdin, positional, default, discovery, output, or abbreviated forms.

Both paths MUST name distinct direct-sibling directories under one actual parent held
throughout. The parent MUST be effective-user-owned, not group/world writable, and
free of every extended ACL on Darwin. Each package MUST be effective-user-owned mode
`0700`, on the parent's device, distinct by device/inode, ACL-free on Darwin, and
contain exactly the seven established preparation-package files. Every entry MUST be
a regular effective-user-owned mode-`0600` single-link file on its directory's device,
ACL-free on Darwin, and distinct from every other input file inode. Established
manifest, plan, JSONL, ZIP, structure, count, and size bounds MUST apply; missing
required descriptor/no-follow/ACL capability MUST fail closed.

Each package MUST independently satisfy the established canonical closed native
package contract and match its securely captured installed codebook. Only the repeated
package MUST match both external expectations: its recomputed manifest self-digest
against `--expected-manifest-sha256` and the raw ZIP SHA-256 against
`--expected-independent-review-packet-sha256`. Success MUST additionally require raw
byte equality of all seven corresponding files.

#### Scenario: Eligible uncertain package equals the two-anchor repeat

- **WHEN** the preserved original diagnostic expressly allowed repeat-and-compare,
  the same inputs produced a normally returned code-`0` sibling, and both values from
  that repeat stdout are supplied independently
- **THEN** `match` is available only after topology, privacy, both full contracts,
  both installed-codebook bindings, both repeated anchors, seven-file byte equality,
  and final recapture succeed
- **AND** no digest is reconstructed or emitted

#### Scenario: A bare exit code two is insufficient

- **WHEN** only the original preparation exit code is known
- **THEN** comparison eligibility remains unverified
- **AND** the command cannot convert a later safe-looking path into authorization

#### Scenario: One repeated stdout anchor is unavailable

- **WHEN** either expected digest was not separately retained from the complete
  successful repeat stdout
- **THEN** the handler cannot return `match`
- **AND** neither manifest nor ZIP supplies the missing expected value

#### Scenario: Stable valid package bytes differ

- **WHEN** both packages are independently valid but any corresponding raw file differs
- **THEN** the report is `mismatch` with exit `3`
- **AND** it exposes no filename, offset, digest, size, or value

### Requirement: Audit-bundle comparison is TOCTOU-resistant and read-only

The command MUST use one held parent plus no-follow open-at/stat operations and held
directory/file descriptors. Every bounded read MUST be surrounded by checks of device,
inode, type, mode, owner, group, link count, size, nanosecond modification/change
times, ACL, and parent/leaf path binding. Packages MUST be processed sequentially;
ZIP members MUST never be extracted to disk; raw comparison MUST use bounded chunks.

After all semantic and byte checks, the command MUST fully recapture both packages and
every used installed codebook, rebind supplied paths and fixed leaves, and repeat raw
seven-file equality. Drift, inability to repeat an inspection, resource exhaustion,
or descriptor-close uncertainty MUST fail as `unreadable`; initial observations MUST
NOT survive as `match`.

After parsing, the command MUST read only the two named packages and their exact
installed codebooks and write only one stdout report. It MUST NOT rerun preparation,
reread the source workspace, mutate permissions or contents, create files, extract an
archive, copy, move, delete, quarantine, transfer, import, finalize, promote, spawn a
subprocess, or access network, socket, HTTP, or database resources.

#### Scenario: Same-inode rewrite races comparison

- **WHEN** a captured object changes before final recapture completes
- **THEN** `comparison_input_changed` wins with `status=unreadable`
- **AND** no earlier equality is trusted

#### Scenario: Match leaves private inputs untouched

- **WHEN** all checks succeed
- **THEN** package bytes, metadata, names, parent inventory, and installed codebooks
  remain unchanged
- **AND** no downstream action is performed

### Requirement: Native audit-bundle comparison report is closed and value-free

Every handler outcome MUST emit exactly one report with top-level keys
`schema_version`, `artifact_type`, `status`, `recovery_comparison_valid`,
`reason_codes`, `checks`, `remediation`, and `scope`. `schema_version` MUST be `1.0`,
`artifact_type` MUST be `native_audit_bundle_comparison_report`, `status` MUST be one
of `match`, `mismatch`, `invalid`, or `unreadable`, and
`recovery_comparison_valid` MUST be true exactly for `match`.

`checks` MUST contain exactly these ordered tri-state members:

- `common_parent_valid`
- `directories_distinct`
- `uncertain_bundle_readable`
- `repeated_bundle_readable`
- `uncertain_bundle_private`
- `repeated_bundle_private`
- `uncertain_inventory_exact`
- `repeated_inventory_exact`
- `expected_manifest_sha256_valid`
- `expected_independent_review_packet_sha256_valid`
- `uncertain_bundle_contract_valid`
- `repeated_bundle_contract_valid`
- `uncertain_installed_codebook_readable`
- `repeated_installed_codebook_readable`
- `uncertain_installed_codebook_binding_valid`
- `repeated_installed_codebook_binding_valid`
- `repeated_external_manifest_digest_valid`
- `repeated_external_independent_review_packet_digest_valid`
- `audit_bundle_file_bytes_equal`
- `final_recapture_valid`

Dependent checks MUST be null when a prerequisite prevents safe evaluation, while
independent safe checks continue. Directly observed drift MUST set final recapture
false and leave interrupted byte equality null rather than manufacturing mismatch.

`reason_codes` MUST be duplicate-free and follow this exact order:

1. `uncertain_audit_bundle_unreadable`
2. `repeated_audit_bundle_unreadable`
3. `uncertain_installed_codebook_unreadable`
4. `repeated_installed_codebook_unreadable`
5. `comparison_input_changed`
6. `comparison_topology_invalid`
7. `uncertain_audit_bundle_privacy_invalid`
8. `repeated_audit_bundle_privacy_invalid`
9. `uncertain_audit_bundle_inventory_invalid`
10. `repeated_audit_bundle_inventory_invalid`
11. `expected_manifest_sha256_invalid`
12. `expected_independent_review_packet_sha256_invalid`
13. `uncertain_audit_bundle_artifact_contract_invalid`
14. `repeated_audit_bundle_artifact_contract_invalid`
15. `uncertain_installed_codebook_binding_mismatch`
16. `repeated_installed_codebook_binding_mismatch`
17. `external_manifest_digest_mismatch`
18. `external_independent_review_packet_digest_mismatch`
19. `audit_bundle_directory_bytes_mismatch`

Remediation MUST use the fixed ordered codes `check_local_read_access`,
`preserve_and_stop`, `use_safe_complete_siblings`,
`retain_successful_repeat_anchors`, `use_exact_installed_codebook`,
`administrator_quarantine`, and `investigate_without_selection`, each paired only
with its fixed Russian message. Input drift or topology/privacy/inventory/contract
faults MUST suppress mismatch investigation and select preservation plus
administrator accounting/quarantine. A pure external-anchor or raw-byte mismatch
MUST select preservation and separate investigation without selecting a package or
authorizing another repeat. The report MUST
contain no path or basename, digest, identifier, count, size, codebook version,
content, device/inode coordinate, timestamp, exception, errno, environment value, or
complete input object.

`scope` MUST contain exactly:

- `technical_recovery_comparison_only=true`
- `original_recovery_eligibility_verified=false`
- `recovery_action_authorized=false`
- `repeat_normal_return_verified=false`
- `input_provenance_authenticated=false`
- `external_manifest_digest_provenance_authenticated=false`
- `external_independent_review_packet_digest_provenance_authenticated=false`
- `original_durability_verified=false`
- `source_workspace_reverified=false`
- `result_selection_performed=false`
- `downstream_use_authorized=false`
- `consumer_revalidation_required=true`
- `reviewer_identity_authenticated=false`
- `publication_safe=false`
- `legal_readiness=false`
- `filing_authorized=false`

#### Scenario: Hostile private values reach an error

- **WHEN** an input value or exception contains distinctive sensitive text
- **THEN** stdout contains only closed enums, booleans/null, fixed Russian remediation,
  and fixed scope
- **AND** handler stderr is empty
