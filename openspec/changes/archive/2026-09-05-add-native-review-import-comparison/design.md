## Context

A successful `quality coding-audit-review-import` publishes exactly two private
files—`audit-decisions.jsonl` and
`coding-audit-review-import-receipt.json`—and returns the receipt self-digest and
next-step flags only through one complete stdout line followed by normal process
return. Some post-publication durability, descriptor-finalization, and
confirmation-delivery failures preserve a possibly complete directory while
invalidating that stdout. Their existing recovery is to preserve unchanged inputs,
repair the external fault, repeat into a new absent sibling, obtain a normal code-`0`
confirmation, byte-compare both directories, and use only the repeat's separately
retained receipt digest and flags.

Other failures are not eligible. Staging, cleanup, location, integrity, ACL,
hardlink, or unaccounted-inode uncertainty requires administrator-only accounting and
quarantine. The runtime does not persist a machine-readable recovery-class receipt,
so a later comparison cannot prove which earlier error occurred. Exit code `2` alone
therefore never authorizes self-service comparison.

Release19 added a hardened comparison for four-file finalization directories but
explicitly excluded review-import directories. Its safe-parent, bounded descriptor
capture, value-free report, final recapture, and authority boundaries are reusable;
its four-file inventory and finalization-specific relation are not.

The established `_load_native_coding_review_import` consumer verifies an import only
with the exact source bundle, a separately retained expected manifest SHA-256, and the
installed codebook. Comparing two import directories without those inputs could prove
raw equality but could not claim the existing bundle-bound receipt contract. This
change therefore requires five inputs and factors, rather than forks, the established
import verifier.

## Goals / Non-Goals

**Goals:**

- Provide `quality native-reliability compare-review-imports` as the installed,
  read-only implementation of the documented eligible review-import recovery
  comparison.
- Require one externally anchored source bundle plus two distinct safe import siblings
  and the successful repeat's external receipt digest.
- Validate both import outputs against the same exact bundle through one shared
  verifier, distinguish the uncertain internal/bundle relation from the repeated
  externally anchored relation, compare both fixed files as raw bytes, and fully
  recapture every input before success.
- Emit no input-derived path, digest, identifier, count, content, exception, inode, or
  timestamp while still providing stable machine-readable state and fixed Russian
  remediation.
- Remain bounded, linear, side-effect-free, and byte-identical between source and
  clean-installed launchers without installed tests or evals.

**Non-Goals:**

- Do not run or retry import, discover a default bundle or directory, or infer either
  external digest from a manifest or receipt.
- Do not authenticate how either supplied digest was obtained, observe the historical
  prepare/import normal returns, or verify that the uncertain directory came from an
  eligible uncertainty class.
- Do not repair, normalize, chmod, copy, merge, rename, delete, quarantine, persist,
  attach, finalize, promote, or select either directory for downstream use.
- Do not handle partial staging directories, escaped or unaccounted inodes/hardlinks,
  different parents, cross-filesystem inputs, finalization directories, or audit-bundle
  comparison.
- Do not re-read or authenticate the original returned `--secondary-coding` file or
  the cleartext expected coder label. Their receipt digests remain established import
  claims, not independently re-observed evidence in this comparison.
- Do not re-run the import producer, adjudicate values, resolve differences, reverify
  the workspace behind the source bundle, authenticate a reviewer, or establish legal
  correctness, current law, publication permission, claim readiness, or filing
  authority.

## Decisions

### 1. Require the source bundle, both external anchors, and two import siblings

The exact installed route is:

```text
judicial_meaning.py quality native-reliability compare-review-imports \
  --bundle DIR \
  --expected-manifest-sha256 SAVED_PREPARE_SHA256 \
  --uncertain-review-import-dir DIR \
  --repeated-review-import-dir DIR \
  --expected-import-receipt-sha256 SAVED_REPEAT_SHA256
```

All five options are required at argparse level. Missing values, omitted options,
unknown options, abbreviations, or other syntax faults use argparse exit `2` before
the handler and produce no comparison report. The handler accepts no positional path,
stdin input, default/discovery path, `--output`, cleartext coder label, returned
secondary file, or recovery-class flag.

Russian metavars are `ПАПКА_ПАКЕТА_АУДИТА`,
`СОХРАНЁННЫЙ_SHA256_МАНИФЕСТА`, `СОМНИТЕЛЬНАЯ_ПАПКА_ИМПОРТА`,
`ПОВТОРНАЯ_ПАПКА_ИМПОРТА`, and `SHA256_УСПЕШНОГО_ПОВТОРА`.

`--expected-manifest-sha256` means only the lowercase 64-hex manifest self-digest
retained outside the bundle from the exact `coding-audit-prepare` invocation's
complete successful stdout followed by normal return. The command never reads that
expectation from `coding-audit-inputs-manifest.json`.

`--expected-import-receipt-sha256` means only the lowercase 64-hex receipt self-digest
retained outside the repeated directory from the repeated
`coding-audit-review-import` invocation's complete successful stdout followed by
normal return. The command never reads that expectation from either receipt. Requiring
both anchors prevents self-consistent arbitrary copies from satisfying the complete
comparison contract, although the command still cannot authenticate their provenance.

Alternatives rejected:

- A three-input, two-directory-only command would prove raw equality and receipt
  self-consistency without binding either receipt to the exact source bundle already
  required by every downstream native import consumer.
- Requiring the original returned secondary file and coder label would turn a recovery
  comparison into a producer replay and expand sensitive input handling without being
  necessary to prove equality of the two published outputs.
- Optional anchors or inferred paths would blur malformed invocation with a validly
  comparable mismatch and could select private material the user did not name.
- A new top-level namespace would separate the command from the existing native
  reliability doctor and Release19 recovery comparison.

### 2. Admit three distinct complete direct siblings under one held safe parent

The bundle path and two import-directory paths are normalized only to identify their
common parent and three leaf names. All leaf names must be nonempty, pairwise distinct
direct entries under one actual parent. The implementation opens that parent once with
no-follow directory semantics, retains its descriptor until all comparison work and
final recapture finish, and verifies that every supplied parent path and child name
continues to resolve to the retained identities.

The parent must be a directory owned by the effective user, not writable by group or
other users, and, on Darwin, have no extended ACL. The bundle and both import
directories must be pairwise distinct device/inode identities, effective-user-owned,
mode `0700`, and free of every extended ACL on Darwin.

The bundle inventory is exactly the established seven files:

```text
screening-candidates.audit.jsonl
primary-decisions.audit.jsonl
coding-audit-plan.json
secondary-review-queue.jsonl
secondary-coding-template.jsonl
independent-review-packet.zip
coding-audit-inputs-manifest.json
```

Each import inventory is exactly:

```text
audit-decisions.jsonl
coding-audit-review-import-receipt.json
```

Every regular file must be effective-user-owned, mode `0600`, single-link, distinct
from all other ten input file inodes, and free of every extended ACL on Darwin. A
partial, extra, linked, aliased, moved, or unsafe entry is not comparable and is never
repaired or removed. No Linux ACL inspection is claimed. Environments without the
required no-follow descriptor or ACL-inspection primitives fail closed.

The bundle uses the existing limits: 2 MiB for its manifest, 4 MiB for the audit plan,
256 MiB for the review ZIP, and 64 MiB for each remaining file. Each
`audit-decisions.jsonl` is limited to 64 MiB and each receipt to 8 MiB. Enumeration
stops after an eighth bundle entry or third import entry. JSON/JSONL/ZIP structural
limits remain the established bounded linear import-consumer limits rather than
unbounded parser work.

This topology and privacy result is not proof that the first import's historical
failure was eligible. Help and report scope keep
`original_recovery_eligibility_verified=false`.

### 3. Hold descriptors and recapture the bundle, both imports, and codebook

For each directory and file, the implementation uses no-follow path stat, open-at
through the retained parent/directory descriptor, descriptor stat, bounded read, and
post-read descriptor/path stat. Stable identity includes device, inode, type, mode,
owner, group, link count, size, and nanosecond modification/change times. Parent and
all three directory descriptors remain held throughout comparison.

The command first performs only a strict canonical closed-field manifest preview to
obtain a supported `codebook_version`. That preview is not a validated bundle and
grants no authority. It then captures exactly that installed codebook with the
established secure routine and performs full bundle validation against the capture.
The codebook is recaptured after evaluation. The command does not search arbitrary
codebook paths and never emits its path or content.

After all bundle, receipt, decision, digest, relation, and raw byte checks are
evaluated, the bundle and both imports are fully recaptured through the same held
parent, and the installed codebook is recaptured through its established secure path.
The recapture must have the same parent, directory, and file identities, exact
inventories, metadata, ACL results, and bytes as the initial captures; supplied parent
paths and leaf names must still bind those identities. Corresponding import bytes are
compared again after both final recaptures before success is delivered.

Drift, inability to repeat an inspection, unavailable required capability, or
descriptor-close uncertainty maps to `comparison_input_changed` and
`status=unreadable`; no successful report may be emitted from only the first snapshot.

### 4. Factor one bundle-bound import verifier instead of weakening the consumer

After the non-authoritative manifest preview and secure codebook capture, the source
bundle is loaded once through structured stages shared with the established native
audit-bundle loader. Those stages retain the existing exact manifest self-digest,
member byte digests, deterministic review ZIP, plan, codebook, candidate-population,
private-file, and contract validation. A syntactically valid external manifest
expectation that does not match the exact bundle is a mismatch rather than an inferred
replacement, and the comparator still evaluates every independently safe full-bundle
and codebook check after that mismatch. The legacy loader keeps its prior early-error
order; neither path classifies a stage by matching localized exception text.

The existing import loader is factored into shared pure verification stages used by
two explicit orchestration paths:

1. artifact stages validate strict canonical
   `coding-audit-review-import-receipt.json`, its closed object contract, recomputed
   unsigned-object self-digest, exact `audit-decisions.jsonl` canonical bytes and
   receipt file binding, and every existing receipt-to-bundle fixed field, digest,
   candidate population, audited-field order, difference-map/flag relation, and
   negative scope; and
2. an external receipt-expectation stage first validates lowercase
   64-hex syntax and then compares it to the recomputed receipt self-digest.

The legacy `_load_native_coding_review_import` orchestration preserves its exact
historical order and errors: receipt structural/canonical contract, receipt
self-digest, required external expectation, receipt-to-bundle fields and digest-field
syntax, decisions structural/canonical contract, file binding, then difference-map
relations. The comparator orchestration
evaluates every independently safe stage without short-circuiting a mismatch that
could otherwise hide a higher-priority invalid or administrator-only fault. It applies
the external stage only to the repeated directory with the separately supplied
successful-repeat digest. The uncertain directory remains bundle-bound but is never
called externally anchored and receives no expectation inferred from its receipt or
from raw equality. No path parses localized exception messages into stage results.

The receipt self-digest is over the canonical object without `receipt_sha256`; it is
not a digest of the receipt file with its trailing LF. Exact canonical file bytes bind
the parsed receipt object to the receipt file. The receipt's
`audit_decisions_file_sha256` must equal SHA-256 of the exact sibling bytes. Other
receipt digests for source bundle members and the returned secondary file remain
closed bundle/import claims. The command does not claim to re-observe the original
returned secondary file merely because those digest fields are valid.

A `match` requires every bundle and import check above and byte-for-byte equality of
both corresponding fixed files. Equality is over raw file bytes, not only hashes,
parsed objects, selected receipt fields, or directory archives. The command does not
parse or re-adjudicate private coding values beyond the established bundle-bound
consumer validation.

### 5. Emit a closed four-state value-free report

Every handler outcome has exactly these top-level members:

```text
schema_version, artifact_type, status, recovery_comparison_valid,
reason_codes, checks, remediation, scope
```

`schema_version` is `1.0`; `artifact_type` is
`native_review_import_comparison_report`; `recovery_comparison_valid` is true if and
only if `status=match`. State priority is:

1. `unreadable`: a required path/descriptor/read/inspection/codebook/ACL capability is
   unavailable, a resource bound is exceeded, an input changes, or final recapture or
   close cannot be confirmed;
2. `invalid`: stable readable input violates SHA syntax, sibling topology, privacy,
   exact inventory, canonical bytes, ZIP/JSON structure, or a closed artifact contract;
3. `mismatch`: all prerequisites needed for a relation are valid but the bundle's
   external manifest anchor, a receipt self-digest, receipt-to-decision binding,
   receipt-to-bundle relation, repeated external receipt anchor, or corresponding raw
   file equality fails;
4. `match`: every prerequisite, relation, equality, and final recapture succeeds.

`match` returns `0`, `mismatch` returns `3`, and `invalid` or `unreadable` returns `2`.
Every handler outcome emits one canonical compact sorted-key UTF-8 JSON line with
`ensure_ascii=false`, `allow_nan=false`, and one trailing LF on stdout with empty
stderr. Parser faults and stdout write/flush/interruption retain exit `2` and cannot
promise a complete report.

`checks` has exactly these Boolean-or-null members in this semantic order:

```text
common_parent_valid
directories_distinct
source_bundle_readable
source_bundle_private
source_bundle_inventory_exact
expected_manifest_sha256_valid
source_bundle_contract_valid
source_bundle_external_manifest_digest_valid
installed_codebook_readable
installed_codebook_binding_valid
uncertain_directory_readable
repeated_directory_readable
uncertain_directory_private
repeated_directory_private
uncertain_inventory_exact
repeated_inventory_exact
expected_import_receipt_sha256_valid
uncertain_artifact_contracts_valid
repeated_artifact_contracts_valid
uncertain_receipt_self_digest_valid
repeated_receipt_self_digest_valid
repeated_external_receipt_digest_valid
uncertain_receipt_file_binding_valid
repeated_receipt_file_binding_valid
uncertain_bundle_relation_valid
repeated_bundle_relation_valid
import_directory_file_bytes_equal
final_recapture_valid
```

A check is Boolean when evaluated and `null` when an earlier unavailable or invalid
prerequisite prevents evaluation. `final_recapture_valid=true` requires every normal
recapture prerequisite, while directly observed drift or descriptor-close uncertainty
sets it to `false` even when that drift prevents an earlier prerequisite. It is `null`
only when recapture is unavailable and no drift was observed. If drift interrupts raw
comparison before equality is established, `import_directory_file_bytes_equal` is
`null`, not a fabricated mismatch. Implementations attempt every independent safe
check so one import does not conceal an independently detectable fault in the other.

The exact tri-state prerequisite matrix is:

| Check | Required true prerequisites |
|---|---|
| `common_parent_valid` | none; stable topology failure is `false`, unavailable or drifting resolution is `null` |
| each `*_directory_readable` | none; each supplied entry is probed independently when its spelling is addressable |
| `directories_distinct` | `common_parent_valid` and all three directory-readable checks |
| each `*_directory_private` | `common_parent_valid` and its own directory-readable check |
| each `*_inventory_exact` | its own directory-private check |
| both expected-digest syntax checks | none |
| `source_bundle_contract_valid` | `source_bundle_inventory_exact` |
| `source_bundle_external_manifest_digest_valid` | `source_bundle_contract_valid` and `expected_manifest_sha256_valid` |
| `installed_codebook_readable` | a supported codebook version from the strict canonical manifest preview; successful capture is `true`, unavailable capture is `false` |
| `installed_codebook_binding_valid` | `source_bundle_contract_valid` and `installed_codebook_readable` |
| each import `*_artifact_contracts_valid` | its own import-inventory check |
| each import `*_receipt_self_digest_valid` | its own artifact-contract check |
| `repeated_external_receipt_digest_valid` | `repeated_artifact_contracts_valid` and `expected_import_receipt_sha256_valid`; it is independent of the receipt's stored self-digest field |
| each import `*_receipt_file_binding_valid` | its own artifact-contract check |
| each import `*_bundle_relation_valid` | `source_bundle_contract_valid` and its own artifact-contract check |
| `import_directory_file_bytes_equal` | `directories_distinct` and both import-inventory checks |
| `final_recapture_valid` | `common_parent_valid`, `directories_distinct`, all three inventory checks, `source_bundle_contract_valid`, and `installed_codebook_readable` |

A `false` relation or digest check does not suppress a different independently safe
relation check. An unavailable secure codebook capture sets
`installed_codebook_readable=false`, leaves already established bundle observations
intact, and leaves dependent binding/final-recapture checks `null`. An unavailable
recapture sets `final_recapture_valid=false` and records input change. An exact
installed-codebook byte mismatch sets
`installed_codebook_binding_valid=false` and maps to
`source_bundle_artifact_contract_invalid`. Thus the implementation does not rewrite a
successfully read bundle as unreadable merely because its installed dependency is
unavailable or mismatched.

`reason_codes` is duplicate-free and follows this exact order:

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

Each remediation entry has exactly `code` and `message_ru`, is selected from a fixed
mapping, deduplicated, and ordered as follows:

| Code | Exact Russian message |
|---|---|
| `check_local_read_access` | `Проверьте доступность указанных локальных папок и встроенного справочника, не изменяя их; команда не выполняет восстановление.` |
| `preserve_and_stop` | `Остановите использование обеих папок импорта и сохраните пакет и результаты неизменными; команда ничего не исправляет и не удаляет.` |
| `use_safe_complete_siblings` | `Передавайте один полный семифайловый пакет и две разные полные двухфайловые папки импорта у одного приватного родителя; небезопасное или неполное состояние передайте системному администратору.` |
| `retain_successful_prepare_digest` | `Передайте manifest_sha256 только из полного стандартного вывода успешно и нормально завершившейся подготовки пакета; не восстанавливайте его из манифеста.` |
| `retain_successful_repeat_digest` | `Передайте receipt_sha256 только из полного стандартного вывода успешно и нормально завершившегося повторного импорта; не восстанавливайте его из квитанции.` |
| `administrator_quarantine` | `При изменении inode, жёсткой ссылке, ACL, неучтённом или перемещённом объекте остановите автоматику и передайте состояние системному администратору для учёта всех ссылок и карантина.` |
| `repeat_import_after_mismatch` | `Не используйте несовпавшие результаты; проверьте пакет и внешние якоря, затем только для разрешённого маршрута снова выполните импорт тех же неизменённых входов в новую отсутствующую соседнюю папку.` |

Unreadable reasons select `check_local_read_access`; input drift selects
`preserve_and_stop` and `administrator_quarantine`; topology, privacy, inventory, or
artifact invalidity selects `preserve_and_stop`, `use_safe_complete_siblings`, and
`administrator_quarantine`; invalid or mismatched manifest expectation selects
`preserve_and_stop` and `retain_successful_prepare_digest`; invalid or mismatched
receipt expectation selects `preserve_and_stop` and
`retain_successful_repeat_digest`; receipt self/file/bundle relation or raw byte
mismatches select `preserve_and_stop` and `repeat_import_after_mismatch`.

Directly observed input drift or topology/privacy/inventory/artifact invalidity is
administrator-only and suppresses `repeat_import_after_mismatch` even if an independent
mismatch was also observed. The report never advises self-service repeat alongside
quarantine.

`scope` has exactly these fixed members:

```text
technical_recovery_comparison_only=true
original_recovery_eligibility_verified=false
prepare_normal_return_verified=false
repeat_normal_return_verified=false
external_manifest_digest_provenance_authenticated=false
external_import_receipt_digest_provenance_authenticated=false
original_durability_verified=false
source_workspace_reverified=false
returned_secondary_file_reverified=false
consumer_revalidation_required=true
reviewer_identity_authenticated=false
publication_safe=false
legal_readiness=false
filing_authorized=false
```

No report member may contain an input path, digest value, file bytes, candidate
identifier, count, substantive value/label, quotation, pseudonym, attributable
timestamp, inode/device coordinate, exception text, environment value, or complete
input object. Equivalent stable inputs therefore produce byte-identical reports. The
installed JSON Schema MUST express this additive report in compact linear-size form;
it MUST NOT enumerate combinations or permutations of reason/remediation values.
Exact ordering remains enforced by the builder and tests, while the schema stays a
closed portable runtime contract rather than installation bloat.

### 6. Enforce application-level read-only behavior and installed parity

After parsing, the command may read only the three explicitly supplied directories
and the exact installed codebook selected by the validated bundle. It writes only its
stdout report. It exposes no output path and invokes no mutation, temporary-file,
subprocess, network/socket/HTTP, database, import, finalization, attachment, repair,
quarantine, or promotion path. The portable launcher suppresses bytecode writes.

Tests snapshot the common parent, all three directories, and the codebook; they spy on
side-effect entry points for every state, including read and stdout failures. The
source-tree and clean-installed launchers must return identical report bytes, stderr,
and process code from a working directory outside the repository, reject abbreviated
long options, ignore an ambient conflicting `PYTHONPATH`, and require no test, eval,
OpenSpec, repository helper, new dependency, or new launcher at runtime.

## Risks / Trade-offs

- **`match` may be mistaken for proof that the old failure was eligible.** No persisted
  recovery-class evidence exists, so fixed scope keeps eligibility false and guidance
  preserves administrator-only recovery for unsafe classes.
- **A caller can copy either digest from the artifact being checked.** Required
  external inputs prevent inference by the command but cannot authenticate caller
  provenance; both provenance and normal-return flags remain false.
- **Bundle-bound output equality may be mistaken for producer replay.** The command
  validates the established import-consumer contract but does not re-read the returned
  secondary file, authenticate its author, or rerun import.
- **Equal bytes may be mistaken for legal or human approval.** Fixed negative scope
  and downstream current-plan, trusted-origin, difference-resolution, and legal gates
  remain mandatory.
- **A nominally read-only comparison can race same-user mutation.** Held descriptors,
  full stable identity, final recapture, no-follow opens, single-link enforcement, and
  fail-closed ACL checks reduce the race; filesystem snapshots or hostile privileged
  writers remain outside the command's claim.
- **A malformed or partial directory may tempt destructive cleanup.** It returns
  `invalid`/`unreadable`, preserves every object, and routes unsafe state to
  administrator handling.
- **Private values are read into the process.** Bounded processing and value-free
  output avoid reports/log files, but OS memory, swap, crash dumps, backups, and
  administrator access are not encryption guarantees.
- **The source bundle can be substantially larger than the two imports.** Existing
  fixed per-file and ZIP limits plus linear validation and final recapture trade I/O
  time for the same bundle-bound claim used by downstream consumers.
- **New observable enums become a compatibility surface.** Closed schemas, fixed
  ordering, canonical output, and additive evolution prevent accidental drift.

## Migration Plan

1. Add failing bundle/import capture, shared-verifier, closed-report, CLI, hostile-value,
   race, resource-bound, and side-effect tests.
2. Factor the established import consumer into shared bundle-bound and optional
   external-receipt layers without changing existing loader behavior.
3. Implement one held-parent capture for the bundle and two import siblings, raw
   two-file comparison, complete final recapture, and the closed report projection.
4. Add the installed route/schema/Russian help and point eligible import recovery
   guidance to it while preserving administrator-only stop rules.
5. Run focused/full supported-Python suites, source/clean-install parity, strict
   skill/schema/privacy validation, strict OpenSpec validation, and independent review.
6. Refresh the release manifest only after runtime verification, synchronize delta
   specs, archive the change, publish atomically, verify remote SHA, and install only
   from the verified checkout.

Rollback removes only the additive subcommand, report-schema branch, shared wrapper,
and guidance. Existing artifacts, import/finalization behavior, Release19 comparison,
and downstream consumers remain valid.

## Open Questions

None. The five inputs, external-anchor sources, bundle-bound verifier boundary,
topology, resource limits, TOCTOU rules, validations, states, report fields,
remediation, negative authority scope, side effects, and install behavior are closed by
this change.
