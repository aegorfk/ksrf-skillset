## Context

A successful native finalization publishes exactly four private files and returns a
receipt self-digest only through complete stdout followed by normal process return.
Some post-publication durability, descriptor-finalization, and confirmation-delivery
failures preserve a possibly complete directory while invalidating its stdout. Their
existing recovery is: preserve unchanged inputs, repair the external fault, repeat
into a new absent sibling, obtain a normal code-`0` confirmation, byte-compare the two
directories, and use only the repeat's separately retained receipt digest.

Other failures are not eligible. A staging, cleanup, location, integrity, ACL,
hardlink, or unaccounted-inode uncertainty requires administrator-only accounting and
quarantine. The current runtime does not persist a machine-readable recovery-class
receipt, so a later comparison cannot prove which earlier error occurred. The new
command therefore verifies only the post-hoc technical comparison and states this
limit explicitly; it never converts an ineligible state into self-service recovery.

The existing `quality native-reliability doctor` already provides a closed report and
shared native-reliability evaluator. The comparison belongs beside it, but must add a
safe four-file directory loader rather than treating two loose doctor inputs as a
finalization directory.

## Goals / Non-Goals

**Goals:**

- Provide `quality native-reliability compare-finalizations` as the installed,
  read-only implementation of the documented eligible recovery comparison.
- Make success hard to obtain accidentally: require distinct safe siblings, both
  exact four-file inventories, the repeat's external successful-stdout digest, every
  receipt/file binding, the uncertain internal relation, the repeated native relation,
  exact byte equality, and a final stable recapture.
- Emit no input-derived path, digest, identifier, count, content, exception, inode, or
  timestamp while still giving stable machine-readable state and fixed Russian action.
- Remain bounded, linear, side-effect-free, and byte-identical between source and
  clean-installed launchers.

**Non-Goals:**

- Do not run or retry finalization, discover default directories, or infer the external
  digest from either receipt.
- Do not authenticate how the supplied digest was obtained, observe the historical
  repeat's normal return, or verify that the uncertain directory came from an eligible
  uncertainty class.
- Do not repair, normalize, chmod, copy, merge, rename, delete, quarantine, persist,
  attach, import, promote, or select either directory for downstream use.
- Do not handle partial staging directories, escaped or unaccounted inodes/hardlinks,
  different parents, cross-filesystem inputs, import directories, or audit bundles.
- Do not rebuild final coding, re-adjudicate values, revalidate source bundle/import/
  resolutions/current plan, authenticate a reviewer, or establish legal correctness,
  current law, publication permission, claim readiness, or filing authority.

## Decisions

### 1. Extend the existing native-reliability namespace with three required inputs

The exact installed route is:

```text
judicial_meaning.py quality native-reliability compare-finalizations \
  --uncertain-finalization-dir DIR \
  --repeated-finalization-dir DIR \
  --expected-finalization-receipt-sha256 SAVED_REPEAT_SHA256
```

All three options are required at argparse level. Missing values, omitted options,
unknown options, abbreviations, or other syntax faults use argparse exit `2` before
the handler and produce no comparison report. The handler accepts no positional
directory, stdin input, default/discovery path, `--output`, or recovery-class flag.
The Russian metavars are `СОМНИТЕЛЬНАЯ_ПАПКА_ФИНАЛИЗАЦИИ`,
`ПОВТОРНАЯ_ПАПКА_ФИНАЛИЗАЦИИ`, and `SHA256_УСПЕШНОГО_ПОВТОРА`.

The digest option deliberately reuses the existing downstream option name. In this
command it means only the lowercase receipt self-digest retained outside the repeated
directory from the repeated finalizer's one complete successful stdout line followed
by normal return. It is never inferred from either receipt. Requiring it prevents two
identical arbitrary copies from satisfying the complete recovery contract, although
the command still cannot authenticate where the caller obtained it.

Alternatives rejected:

- A two-directory-only command would prove raw equality without binding the alleged
  repeat to its independent successful confirmation.
- A new top-level `quality` command would duplicate the namespace reserved for native
  reliability diagnostics and make the recovery route harder to discover from doctor
  remediation.
- Optional arguments or inferred paths would blur malformed invocation with a validly
  comparable mismatch and could select private material the user did not name.

### 2. Admit only two distinct complete direct siblings under one held safe parent

The two path values are normalized only to identify their parent and leaf names. The
leaf names must be different, nonempty direct entries under one actual parent. The
implementation opens that parent once through no-follow directory semantics, retains
its descriptor until all comparison work and final recapture finish, and verifies that
both supplied parent paths and both child names continue to resolve to the retained
identities. The parent must be a directory owned by the effective user, not writable
by group or other users, and, on Darwin, have no extended ACL. No Linux ACL inspection
is claimed. Environments without the required no-follow descriptor primitives fail
closed.

Both child entries must be different directory device/inode identities, owned by the
effective user, mode `0700`, and, on Darwin, free of every extended ACL. Each inventory
must contain exactly, with no subdirectory or extra entry:

```text
resolved-review-decisions.jsonl
adjudications.jsonl
coding-reliability.json
coding-audit-finalization-receipt.json
```

Every file must be regular, mode `0600`, effective-user-owned, single-link, distinct
from all other seven file inodes, and free of every extended ACL on Darwin. A partial,
extra, linked, aliased, moved, or unsafe entry is not a comparable finalization. It is
never repaired or removed.

This topology check is not proof that the first directory's historical failure was
eligible. Help and report scope keep `original_recovery_eligibility_verified=false`.

### 3. Use bounded descriptor-held capture and mandatory final recapture

The per-file limits are fixed at 64 MiB for each JSONL file, 64 MiB for
`coding-reliability.json`, and 8 MiB for the finalization receipt. Directory listing
stops after a fifth entry. JSON validation and receipt population checks reuse bounded
indexes and remain linear. Corresponding file bytes are compared in bounded chunks,
without exposing an offset, prefix, filename-specific mismatch, digest, size, or first
failure value in the report.

For each directory and file, the implementation performs no-follow path stat, open-at
through the retained parent/directory descriptor, descriptor stat, bounded read, and
post-read descriptor/path stat. Stable identity includes device, inode, type, mode,
owner, group, link count, size, and nanosecond modification/change times. Parent and
directory descriptors remain held throughout the comparison.

After every contract, digest, and byte comparison is evaluated, both directories are
fully recaptured through the same held parent. The recapture must have the same parent,
directory, and file identities, exact inventories, metadata, ACL results, and bytes as
the initial captures; both user-supplied parent paths and leaf names must still bind
those identities. Drift, inability to repeat an inspection, or descriptor-close
uncertainty maps to `comparison_input_changed` and `status=unreadable`; no successful
report may be emitted from only the first snapshot.

### 4. Bind the repeat externally and validate all four finalization files

Each receipt must be strict canonical compact sorted-key UTF-8 JSON with one trailing
LF, unique keys, no non-finite values, the existing closed
`coding_audit_finalization_receipt` contract, and a valid recomputed self-digest over
the canonical object without `receipt_sha256` and without file LF. Exact canonical
bytes bind the parsed receipt object to the receipt file; `receipt_sha256` checks only
the unsigned object and is not a SHA-256 of the full receipt file. No separate full-file
SHA-256 member exists for that fourth file. For each directory, these three closed
receipt members must equal SHA-256 of the exact other file bytes:

```text
resolved_review_decisions_file_sha256
adjudications_file_sha256
coding_reliability_file_sha256
```

`coding-reliability.json` in each directory must have the existing exact canonical
bytes, closed complete/non-stale v1.1 contract, evidence self-digest, receipt file
digest, audit-plan digest, and ordered candidate-population relation. For the uncertain
directory this is only an internal relation and MUST NOT be called native because no
external digest exists for it. The repeated directory's native relation includes the
separately supplied lowercase 64-hex digest and requires equality with the repeated
receipt's recomputed self-digest. The comparison must reuse the shared evaluator; it
must not fork a new definition, infer an expected digest for the uncertain directory,
or parse exception text. Exact equality of all four file bytes is evaluated separately.

A `match` requires every check above and byte-for-byte equality of each corresponding
fixed file. Equality is over raw file bytes, not only hashes, parsed objects, selected
receipt fields, or directory archives. The command does not parse or re-adjudicate the
private resolved/adjudication values beyond bounded byte capture and their receipt
bindings.

### 5. Emit a closed four-state value-free report

Every handler outcome has exactly these top-level members:

```text
schema_version, artifact_type, status, recovery_comparison_valid,
reason_codes, checks, remediation, scope
```

`schema_version` is `1.0`; `artifact_type` is
`native_finalization_comparison_report`; `recovery_comparison_valid` is true if and
only if `status=match`. State priority is:

1. `unreadable`: a required path/descriptor/read/inspection/ACL capability is
   unavailable, a resource bound is exceeded, an input changes, or final recapture/
   close cannot be confirmed;
2. `invalid`: readable stable inputs violate SHA syntax, sibling topology, privacy,
   exact inventory, canonical bytes, or a closed artifact contract;
3. `mismatch`: all prerequisites needed for a relation are valid but a self-digest,
   receipt-to-file binding, uncertain internal relation, repeated native relation,
   external repeat anchor, or corresponding raw file equality fails;
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
uncertain_directory_readable
repeated_directory_readable
uncertain_directory_private
repeated_directory_private
uncertain_inventory_exact
repeated_inventory_exact
expected_receipt_sha256_valid
uncertain_artifact_contracts_valid
repeated_artifact_contracts_valid
uncertain_receipt_self_digest_valid
repeated_receipt_self_digest_valid
repeated_external_receipt_digest_valid
uncertain_receipt_file_bindings_valid
repeated_receipt_file_bindings_valid
uncertain_internal_relation_valid
repeated_native_relation_valid
directory_file_bytes_equal
final_recapture_valid
```

A check is Boolean when evaluated and `null` when an earlier unavailable/invalid
prerequisite prevents evaluation. `final_recapture_valid=true` requires every normal
recapture prerequisite, but a directly observed input drift or descriptor-close
uncertainty sets it to `false` even when that drift prevented an earlier prerequisite;
it is `null` only when recapture was not available and no drift was observed. If drift
interrupts the raw comparison before equality is established,
`directory_file_bytes_equal` is `null`, not a fabricated mismatch. Implementations
attempt every independent safe check, so one bad directory does not conceal an
independently detectable fault in the other.

`reason_codes` is duplicate-free and follows this exact order:

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

Each remediation entry has exactly `code` and `message_ru`, is selected from the
fixed mapping, deduplicated, and ordered as follows:

| Code | Exact Russian message |
|---|---|
| `check_local_read_access` | `Проверьте доступность двух указанных локальных папок, не изменяя их; команда не выполняет восстановление.` |
| `preserve_and_stop` | `Остановите использование обеих папок и сохраните их неизменными; команда ничего не исправляет и не удаляет.` |
| `use_safe_complete_siblings` | `Сравнивайте только две разные полные четырёхфайловые папки финализации у одного приватного родителя; небезопасное или неполное состояние передайте системному администратору.` |
| `retain_successful_repeat_digest` | `Передайте строчный SHA-256 только из полного стандартного вывода успешно и нормально завершившегося повтора; не восстанавливайте его из квитанции.` |
| `administrator_quarantine` | `При изменении inode, жёсткой ссылке, ACL, неучтённом или перемещённом объекте остановите автоматику и передайте состояние системному администратору для учёта всех ссылок и карантина.` |
| `repeat_after_mismatch` | `Не используйте несовпавшие результаты; после проверки причины снова выполните финализацию из тех же неизменённых входов в новую отсутствующую соседнюю папку.` |

Unreadable-directory reasons select `check_local_read_access`; input drift selects
`preserve_and_stop` and `administrator_quarantine`; topology, privacy, inventory, or
artifact invalidity selects `preserve_and_stop`, `use_safe_complete_siblings`, and
`administrator_quarantine`; invalid or mismatched external expectation selects
`preserve_and_stop` and `retain_successful_repeat_digest`; self/file/internal-or-native
relation mismatches select `preserve_and_stop` and `repeat_after_mismatch`; and raw
directory byte mismatch selects `preserve_and_stop` and `repeat_after_mismatch`.
However, directly observed input drift or topology/privacy/inventory/artifact
invalidity is administrator-only and suppresses `repeat_after_mismatch` even if an
independent mismatch was also observed; the report MUST NOT advise self-service repeat
alongside quarantine.

`scope` has exactly these fixed members:

```text
technical_recovery_comparison_only=true
original_recovery_eligibility_verified=false
repeat_normal_return_verified=false
external_digest_provenance_authenticated=false
original_durability_verified=false
consumer_revalidation_required=true
reviewer_identity_authenticated=false
publication_safe=false
legal_readiness=false
filing_authorized=false
```

No report member may contain an input path, digest value, fixed-file bytes, candidate
identifier, count, substantive value/label, quotation, pseudonym, attributable
timestamp, inode/device coordinate, exception text, environment value, or complete
input object. Equivalent stable inputs therefore produce byte-identical reports.

### 6. Enforce application-level read-only and installed parity

After parsing, the command may read only the two explicitly supplied directories and
write only its stdout report. It exposes no output path and invokes no mutation,
temporary-file, subprocess, network/socket/HTTP, database, finalization, import,
attachment, repair, quarantine, or promotion path. The portable launcher suppresses
bytecode writes. Tests snapshot both parents/directories and spy on side-effect entry
points for every state, including read and stdout failures.

The source-tree and clean-installed launchers must return identical report bytes,
stderr, and process code from a working directory outside the repository, reject
abbreviated long options, ignore an ambient conflicting `PYTHONPATH`, and require no
test, eval, OpenSpec, repository helper, new dependency, or new launcher at runtime.

## Risks / Trade-offs

- **`match` may be mistaken for proof that the old failure was eligible.** The runtime
  has no persisted eligibility evidence, so fixed scope says it is unverified and help
  keeps location/inode/security uncertainties on administrator quarantine.
- **A caller can copy the digest from the receipt.** Separate required input and exact
  equality prevent inference by the command but cannot authenticate provenance; the
  report keeps both external provenance and repeat normal return false.
- **Equal bytes may be mistaken for legal or human approval.** Fixed negative scope
  and downstream current-plan/trusted-origin gates remain mandatory.
- **A nominally read-only comparison can race same-user mutation.** Held descriptors,
  full stable identity, two captures, no-follow opens, single-link enforcement, and
  fail-closed ACL checks reduce the race; filesystem snapshots or hostile privileged
  writers remain outside the command's claim.
- **A malformed or partial first directory may tempt destructive cleanup.** It returns
  `invalid`/`unreadable`, preserves all objects, and routes to administrator handling.
- **Private values are read into the process.** Bounded streaming and value-free output
  avoid logs/files, but OS memory, swap, crash-dump, backup, and administrator access
  are not encryption or confidentiality guarantees.
- **Large exact files double comparison I/O because of final recapture.** Fixed per-file
  limits and linear chunked passes trade speed for a stable end-of-command claim.
- **New observable enums become a compatibility surface.** Closed schemas, fixed order,
  canonical output, and additive evolution prevent accidental Hyrum-law drift.

## Migration Plan

1. Add failing capture/evaluator, closed-report schema, CLI, hostile-value, race,
   resource-bound, and side-effect tests.
2. Implement the shared four-file loader and comparison projection without changing
   the existing doctor, finalizer, receipt, or downstream verifier behavior.
3. Add the installed route/schema/Russian help and point eligible finalization recovery
   guidance to it while preserving administrator-only stop rules.
4. Run focused and full suites, source/clean-install parity, strict skill/schema/privacy
   validation, strict OpenSpec validation, and an independent review.
5. Refresh the release manifest, publish atomically, verify the remote SHA, and install
   only from the verified published checkout after all implementation tasks pass.

Rollback removes only the additive subcommand, report-schema branch, and guidance.
Existing artifacts, finalization recovery prose, doctor, and consumers remain valid.

## Open Questions

None. The route, required external anchor, eligible scope, topology, resource bounds,
TOCTOU rules, validations, states, report fields, remediation, side-effect boundary,
and install behavior are closed by this change.
