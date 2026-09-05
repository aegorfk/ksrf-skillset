## ADDED Requirements

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
