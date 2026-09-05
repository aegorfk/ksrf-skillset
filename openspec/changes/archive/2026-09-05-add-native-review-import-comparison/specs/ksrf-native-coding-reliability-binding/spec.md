## ADDED Requirements

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
