## ADDED Requirements

### Requirement: Native secondary coding import verifies the exact blinded handoff

The system SHALL expose `quality coding-audit-review-import --bundle DIR
--expected-manifest-sha256 SHA256 --secondary-coding FILE --output-dir DIR`. It MUST
also require `--expected-secondary-coder LABEL`. It MUST accept only a closed
versioned `bundle_contract_version` `1.1` or `1.2` native custodian bundle produced by
`quality coding-audit-prepare`; a legacy five-file manifest is not silently upgraded.

Before reading a secondary answer as evidence, the importer MUST bound the parent
directory inventory before reading every child and verify the exact inventory,
parent manifest field set and self-digest, sizes and
SHA-256 values of all six parent content files, frozen audit-plan contract and
digest, full screening and primary candidate populations, required queue/template
population, codebook/brief bindings, and source identity links available inside the
bundle. It MUST parse strict UTF-8 JSON/JSONL without duplicate keys or non-finite
values and reject symlinked inputs.

The importer MUST read the review ZIP without extracting it, require its exact six
unique flat members, and reproduce its complete bytes with the current deterministic
stored-ZIP builder. Equality MUST cover member order, names, timestamps, compression,
permissions, extras, comments, member contents, the inner closed self-digesting
manifest, the exact built-in codebook, neutral brief, instructions, material rows,
and pending templates. The reconstructed packet MUST equal the parent-bound ZIP
bytes; self-digests alone MUST NOT be described as authenticity.

The importer MUST require a canonical lowercase 64-hex expected parent-manifest
digest supplied separately from the bundle, and MUST require it to equal the
verified manifest's `manifest_sha256`. The interface MUST direct the custodian to
retain this value from successful `coding-audit-prepare` stdout rather than copy it
from the bundle during import. Internal self-digests alone MUST NOT be treated as a
defense against a self-consistently rewritten bundle.

New prepare runs MUST emit contract `1.2` with exact embedded native-import
guidance. The implementation MUST retain immutable old guide bytes and reproduce
externally anchored `1.1` Release14 packets by their declared version; it MUST NOT
reinterpret changed guide bytes under an existing version.

For a prospective `1.2` handoff the custodian MUST choose a pseudonymous expected
secondary-coder label before transferring the ZIP, retain and communicate that
value separately, and avoid real names. For a historical `1.1` return, whose frozen
guide did not require prospective label selection, the same argument is only a
batch-consistency expectation; a real name MUST be replaced by a newly returned
pseudonymous copy from its author rather than an unrecorded custodian edit. Runtime
MUST hash the normalized expectation into
`expected_secondary_coder_label_sha256` but MUST fix
`secondary_coder_label_precommit_verified=false` because it cannot prove when that
label was chosen.

If an otherwise exact `1.1` bundle lacks a parent-manifest SHA-256 retained outside
the bundle, native import MUST remain unavailable. Guidance MUST forbid recovering
the expectation from the bundle and instead direct the user to regenerate `1.2`
from the unchanged source workspace or use the expert/manual compatibility path;
that fallback MUST NOT manufacture a native import receipt.

Bundle files, the returned JSONL, and installed codebook MUST be captured through
bounded descriptor-based no-follow reads. The importer MUST inspect type before
open, use POSIX nonblocking opens, require a stable regular single-link file identity
and metadata before/after each read, reject symlinks, hardlinks, FIFO, socket, device,
and other special files without waiting for a writer, and recheck exact
descriptor/path identity, metadata, bytes, and bundle inventory immediately before
publication. Fixed conservative limits MUST apply to each parent file during both
producer in-memory prepublication validation and import capture, and to returned
bytes, codebook, ZIP stored/uncompressed totals and members, physical lines, record
counts, JSON nodes/nesting, strings, and lists. Before a general ZIP parser is
invoked, the exact trailing EOCD MUST declare one disk, no comment, exactly six
non-ZIP64 entries, and a bounded central directory ending immediately before EOCD.
ZIP metadata MUST then reject encryption, data descriptors, compression,
directories, non-flat names, extras, comments, or excess sizes; no member may be
extracted to disk. Diagnostics for untrusted duplicate keys, candidate IDs, or ZIP
metadata MUST be generic and MUST NOT echo untrusted identifiers/values, packet
text, quotes, or absolute input paths.

The producer MUST check every prospective ZIP member and aggregate payload against
the same conservative bounds before constructing the archive and MUST open the ZIP
writer with `allowZip64=false`. It MUST NOT create an archive shape that the import
contract rejects as ZIP64.

#### Scenario: Untampered versioned bundle is accepted as an input

- **WHEN** every closed parent and inner artifact, hash, candidate, and exact packet
  byte agrees with the current versioned native contract and the parent self-digest
  equals the separately retained expected digest
- **THEN** the importer proceeds to validate the returned secondary records
- **AND** it does not modify the bundle or expose primary answers to the second coder

#### Scenario: Legacy or altered bundle is rejected

- **WHEN** the bundle is legacy, its manifest differs from the separately retained
  expected digest, it has a missing or extra path, contains a symlink, or
  any parent/inner file, digest, ZIP property, codebook, brief, guide, identity, or
  exact text differs from the deterministic native contract
- **THEN** the importer fails with no output instead of trusting the self-digest or
  silently repairing the bundle

#### Scenario: A historical packet has no surviving external anchor

- **WHEN** the user has an exact `1.1` bundle but did not retain its parent-manifest
  digest outside that bundle
- **THEN** native import remains unavailable and the value is not rediscovered from
  the bundle
- **AND** guidance offers regeneration of `1.2` from the unchanged source workspace
  or the expert/manual path without a native receipt

#### Scenario: A special file or oversized archive is supplied

- **WHEN** an input is a FIFO or other non-regular file, any resource limit is
  exceeded, the bounded parent inventory has too many entries, or the ZIP
  EOCD/central directory declares ZIP64, extra entries, a comment, multiple disks,
  or excessive allocation
- **THEN** import fails promptly before blocking on the special file or asking the
  general ZIP parser to allocate from the rejected metadata
- **AND** the diagnostic does not repeat attacker-controlled record content

### Requirement: Every returned secondary record is closed and quote-presence checked

The returned file MUST contain exactly one strict closed 20-field completed coding
record for every sorted `required_candidate_id`, with no missing, extra, or duplicate
candidate. Input order MAY differ; canonical output order MUST follow the frozen
required candidate order.

For each candidate, the importer MUST require exact candidate, chain, document,
codebook, and norm-edition binding to the verified packet; the norm edition MUST be
one of the neutral brief's applicable edition IDs. Every secondary coder label MUST
normalize to one operator-pinned `--expected-secondary-coder` value and differ from
the corresponding selected primary record's coder under the same Unicode
normalization/case-folding rule used by reliability. Extra primary rows outside the
required sample MUST NOT broaden this check. The comparison is a string
distinction/consistency check, not identity authentication or proof that two humans
worked.

The record MUST satisfy the authoritative completed-coding structural contract,
including the declared completion values `human_review="approved"`,
`quote_verified=true`, and `full_text_reviewed=true`. The importer verifies those
declared values but MUST NOT describe them as proof that a real human performed the
stated acts, authorship, or attestation that the packet was actually used. The main
quote and every supplied alternative-ground quote MUST each
occur as a literal string in that candidate's exact packet text;
`validate_coding_against_text` MUST also pass only as an additional normalized
quote-presence check, not a semantic check. A digest supplied by the returned file
cannot replace these checks. The importer MUST NOT claim to validate the truth,
adequacy, or legal correctness of `proposition`, `material_facts`,
`reasoning_to_outcome`, or any other substantive coding judgment.

#### Scenario: Complete returned population becomes audit decisions

- **WHEN** every required returned record passes the closed contract, exact bindings,
  single pinned/distinct coder-label check, applicable-edition check, and exact
  packet-text checks
- **THEN** the importer emits one compatible four-field audit decision per candidate
- **AND** each decision carries the verified primary coding digest and canonical
  digest of the exact nested secondary record

#### Scenario: One malformed or cross-bound record blocks the batch

- **WHEN** any record or candidate population is incomplete, duplicated, extra,
  non-canonical, same-coder, wrong-edition, wrong-codebook, cross-bound, not completed,
  or has a main or alternative quote absent from its exact packet text
- **THEN** the entire import fails without decisions, receipt, or partial directory

### Requirement: Import output is atomic, content-bound, and conservatively scoped

The importer MUST accept only a new absent `--output-dir` that is a sibling of the
input bundle under the same actual parent directory. It MUST open the bundle first,
derive and hold that actual parent descriptor through final recheck and publication,
require the parent to be owned by the current effective user and not writable by
group or other users, and require the user-facing output-parent path to retain the
same device/inode identity. All temporary-directory, existence, file, no-replace
rename, and fsync operations MUST be relative to that held descriptor. It MUST
publish exactly `audit-decisions.jsonl` and
`coding-audit-review-import-receipt.json` by a no-replace atomic directory rename
and re-read every input plus the built-in codebook before publication. Temporary
and final directories MUST be mode `0700`, files MUST be mode `0600`, every file
and the temporary-directory inode MUST be fsynced before rename, and the parent
directory MUST be fsynced after rename. Effective-user ownership and absence of
group/other write permission on the held parent MUST be checked initially,
immediately before rename, and during final state verification.

On macOS/Darwin the publisher MUST additionally use fd-based checks to prove that
the held parent on every recheck, the temporary directory before any file creation,
each created file before its first byte, and the complete bundle directory plus
each file during pre- and post-rename verification have no extended ACL at all.
Every ACE MUST be rejected, including deny-only and non-inheriting entries. Failure
to load/call/free the ACL API or to prove stable fd identity across the probe MUST
fail closed. This requirement MUST NOT claim Linux ACL inspection, and the
`0700`/`0600` mode checks MUST NOT alone be described as proof of privacy on macOS.

Before the temporary-directory `mkdir`, a validation failure MAY return code `2`
with empty stdout and no output object. Once `mkdir` succeeds, every failure before
the commit point MUST preserve whatever temporary directory, created file, moved
entry, replacement, or external hardlink may exist and MUST return code `2` with
empty stdout. The publisher MUST NOT automatically unlink a file or remove the
temporary directory: portable APIs cannot atomically prove ownership when an
attacker can replace a name.

Temporary-directory identity MUST be captured immediately after safe open and
before `fchmod`; if the open fails, its identity MUST be explicitly recorded as
unknown. For every safely created file, the publisher MUST retain the original open
descriptor and captured `st_dev`/`st_ino` through failure classification.

The filesystem commit point MUST be the atomic no-replace rename itself, not the
rename helper's successful return. If the helper reports an error, the publisher
MUST check whether the destination name under the held parent owns the captured
temporary-directory inode. If it does, the publisher MUST preserve the directory
and report post-rename state uncertainty. Otherwise it MUST still delete nothing
and report cleanup uncertainty, even if the former temporary name appears to own
the inode.

Both post-`mkdir` uncertainty branches MUST report the held parent's
`st_dev`/`st_ino`, prior temporary entry name, the temporary directory's known
`st_dev`/`st_ino` or explicit unknown identity, and each known created file's
`st_dev`/`st_ino`. Automation MUST stop with inputs unchanged and prohibit retry or
transfer. The user MUST forward the entire diagnostic to a system administrator
because no self-service recovery command exists. The administrator MUST locate the
temporary/published directory and every created inode, account for all names and
hardlinks of every file, and quarantine every located copy. If a directory, inode,
or complete link set cannot be accounted for, a sensitive temporary or published
copy MUST be treated as unaccounted for.

If the post-rename parent fsync alone fails after every other final state check has
succeeded, the command MUST return code `2` with empty stdout and a
durability-uncertain diagnostic saying that the complete directory at the confirmed
path may already be visible. That directory MUST be preserved but MUST NOT be
automatically deleted or used downstream. Recovery MUST require filesystem repair,
a rerun with the same unchanged inputs into another absent sibling, and a
byte-for-byte comparison of both two-file outputs before either is trusted.

Every post-rename state check MUST revalidate the held parent's effective owner and
permissions, the user-facing parent identity, the prior destination entry and
published-directory identity, the exact output inventory and directory mode `0700`,
and each file's regular type, single link, mode `0600`, size, identity, and bytes.
Any parent permission drift, destination-entry move/replacement, or output
inventory, mode, link-count, size, identity, or byte drift MUST be reported as
state-uncertain: a user-facing path or entry may no longer represent the directory
published through the held descriptor. The command MUST return code `2` with empty
stdout and disclose the held parent's `st_dev`/`st_ino`, prior published entry name,
published directory's `st_dev`/`st_ino`, plus each known created file's
`st_dev`/`st_ino`. Automation MUST stop, preserve every input unchanged, and neither
retry nor transfer any result. The diagnostic MUST say this is emergency
system-administrator recovery rather than a self-service command, and the user MUST
forward the entire diagnostic. The administrator MUST locate the directory and every
created inode, account for all names and hardlinks of every file, and quarantine
each located copy. If the directory, any inode, or its complete link set cannot be
accounted for, a sensitive output copy MUST remain classified as unaccounted for
rather than assumed absent. A concurrent change MUST fail without partial output.
Receipt and diagnostics MUST NOT contain packet text, quotes, untrusted field
values, or absolute input paths.

After complete durable publication, the importer MUST close every retained created-
file and published-directory descriptor and then the held parent descriptor before
emitting its one-line JSON confirmation. From the instant confirmation delivery is
marked started until normal command return, any error or asynchronous interruption
MUST preserve the complete published directory and return code `2`. This includes a
short/failed write, explicit stdout flush failure, and interruption after the full
line was successfully flushed. Stdout MAY be empty, partial, or apparently complete,
but every form MUST be declared invalid and MUST NOT be parsed or used. Automation
MUST stop, MUST NOT use the first output, and MUST NOT retry the same destination.
After stdout recovery, the custodian MUST rerun the same unchanged inputs into another
absent sibling, obtain one completely written and flushed success line followed by
normal command return, and byte-compare both directories. Only after equality MAY
the receipt digest, both next-step flags, and difference maps from that successful
repeat stdout be used.

Any error or asynchronous interruption after publication but before confirmation
delivery is marked started MUST use a separate finalization-uncertain diagnostic,
return code `2`, and leave stdout empty because no confirmation was formed. This
includes closing any retained created-file, published-directory, or parent descriptor
and a wrapper interruption after the inner publisher returns or after parent close.
Code `2` MUST NOT be described as proof that the output directory is absent, and this
diagnostic MUST NOT itself overclaim that the directory's durability was confirmed.
The found directory and all inputs MUST remain unchanged and unused; recovery MUST
use the same new-sibling identical-input repeat, successful confirmation and normal
return, and byte-for-byte comparison before any repeat receipt digest or flags are
trusted.

The receipt MUST be a closed self-digesting object bound to the separately supplied
expected parent-manifest digest, exact parent-manifest bytes/self-digest, review ZIP
bytes, returned secondary file bytes, canonical audit
decision bytes, codebook, brief, plan, and candidate population. It MUST partition
all candidates exactly once into narrowly named audited-field agreement and
disagreement lists. It MUST separately list differences in `proposition`, `quote`,
`quote_locator`, or `material_facts`. It MUST set `adjudication_required=true`
exactly when an established audited field differs and
`non_audited_content_review_required=true` exactly when that other substantive
content differs. The latter MUST be disclosed as requiring manual content review,
not called full agreement and not routed into the existing adjudication record,
whose closed contract permits only the eight audited fields. This release MUST
describe that second signal as advisory rather than a technical gate because the
existing reliability command does not consume the import receipt.

`audit-decisions.jsonl` MUST remain in frozen `required_candidate_ids` order. The
receipt's collection-level `secondary_coding_sha256` MUST instead sort the complete
returned records by each record's canonical digest before hashing the canonical
array, so it is independent of returned JSONL row order. This collection binding
MUST remain distinct from each decision's digest of its exact nested secondary
record.

For each audited disagreement, `audited_field_differences` MUST map its
`candidate_id` to all and only differing names from the eight audited fields in
contract order, without field values. For each non-audited content difference,
`non_audited_content_differences` MUST provide the same value-free mapping over the
four disclosed fields. Each map's candidate set MUST equal its corresponding
difference-ID list exactly.

Release15 MUST NOT claim a native artifact or machine validator that proves closure
of manual review for non-audited content. When such review is required, guidance
MUST require a separate external record containing at least candidate ID, reviewed
field names, reviewer pseudonym, `reviewed_at`, conclusion, receipt digest, primary
coding digest, and secondary coding digest; it MUST NOT call that record a native
receipt.

The receipt and stdout MUST fix `returned_quote_literal_presence_verified=true`,
`quote_locator_verified=false`,
`secondary_coder_label_differs_from_each_sampled_primary_label=true`,
`single_secondary_coder_label=true`,
`bundle_internal_consistency_verified=true`,
`expected_manifest_digest_match_verified=true`,
`norm_edition_allowlist_membership_verified=true`,
`source_workspace_reverified=false`, `reviewer_packet_use_attested=false`,
`norm_edition_temporal_applicability_verified=false`,
`reviewer_identity_authenticated=false`, `human_review_authenticated=false`,
`independence_verified=false`, `receipt_authenticated=false`,
`publication_safe=false`, and `legal_readiness=false`.
They MUST also expose `expected_secondary_coder_label_sha256` and fix
`secondary_coder_label_precommit_verified=false`.
They MUST NOT claim authorship, reviewer identity, independent-human participation,
agreement resolution, legal approval, publication permission, or filing authority.

#### Scenario: Valid import publishes a deterministic receipt and next step

- **WHEN** a stable verified bundle and complete returned file pass every check
- **THEN** the two-file output is published atomically with exact hashes and a
  self-digesting receipt
- **AND** stdout reports candidate, audited-field agreement/disagreement, and other
  substantive-content-difference counts and value-free maps, whether formal
  adjudication is required, and whether separate manual content review is required
- **AND** code `0` means only that import and publication completed; automation must
  parse both next-step flags and stop if either is `true`

#### Scenario: Inputs change during import

- **WHEN** any bundle path/byte, returned-file byte, or built-in codebook changes
  between capture and the pre-publication recheck
- **THEN** the importer fails without publishing or overwriting any output

#### Scenario: Validation fails before temporary-directory creation

- **WHEN** validation fails before the publisher creates its temporary directory
- **THEN** the importer returns code `2` with empty stdout and creates no output object

#### Scenario: Failure after temporary-directory creation preserves evidence

- **WHEN** opening or changing the mode of the temporary directory, creating, writing,
  or synchronizing a file, verifying the directory, or synchronizing it fails after
  `mkdir` and before the no-replace rename
- **THEN** the importer returns code `2` with empty stdout and performs no automatic
  file unlink or temporary-directory removal
- **AND** it reports parent, prior temporary name, known temporary-directory, and
  known created-file coordinates for administrator-only quarantine, as exercised by
  [`test_pre_rename_directory_fsync_failure_preserves_staging_for_quarantine`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_staging_setup_open_and_fchmod_failures_preserve_quarantine_entry`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py), and
  [`test_precommit_failure_never_attempts_destructive_unlink`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)

#### Scenario: Temporary-directory open failure does not delete a replacement

- **WHEN** `mkdir` succeeds but opening the temporary name fails after that name was
  replaced
- **THEN** the importer preserves both possible directories, reports temporary
  identity as unknown, and takes the cleanup-uncertain administrator route, as
  exercised by
  [`test_failed_staging_open_never_removes_replacement_directory`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)

#### Scenario: Escaped created inode requires all-link quarantine

- **WHEN** a created temporary file acquires an external hardlink or its directory
  entry is replaced before commit
- **THEN** the retained descriptor/device/inode remains available for diagnosis,
  neither the former name nor a replacement is automatically deleted, and code `2`
  with empty stdout requires administrator accounting and quarantine of every link
- **AND** an inode or complete link set that cannot be accounted for remains an
  unaccounted sensitive copy, as exercised by
  [`test_cleanup_detects_sensitive_hardlink_outside_staging`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py) and
  [`test_cleanup_never_unlinks_replacement_for_escaped_created_inode`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)

#### Scenario: Rename helper reports an ambiguous result

- **WHEN** the no-replace rename helper reports an error after the filesystem commit
  point may already have moved the captured temporary-directory inode
- **THEN** a destination owning that inode is preserved and reported state-uncertain
- **AND** every other post-`mkdir` outcome is preserved without destructive cleanup
  and reported cleanup-uncertain, even if the former temporary name appears to match,
  as exercised by
  [`test_rename_then_helper_error_preserves_complete_published_output`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)

#### Scenario: macOS extended ACL fails closed

- **WHEN** a parent, temporary/final directory, or created file on Darwin has any
  extended ACE, including deny-only or non-inheriting, or the ACL API/identity
  stability cannot prove absence at a required fd-based checkpoint
- **THEN** publication returns code `2` without claiming `0700`/`0600` alone proves
  privacy; a post-`mkdir` failure preserves all possible temporary copies for the
  same quarantine route
- **AND** non-Darwin execution makes no Linux ACL-inspection claim, as covered by
  [`test_extended_acl_probe_is_fail_closed_and_recaptures_fd_identity`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_extended_acl_guard_is_a_noop_outside_darwin`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_darwin_acl_probe_rejects_mode_change_inside_system_call`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_darwin_acl_removal_during_probe_is_detected_by_ctime`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_darwin_inherited_parent_acl_is_rejected_before_output`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py), and
  [`test_darwin_acl_added_after_parent_precheck_is_caught_on_staging_fd`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)

#### Scenario: Parent synchronization fails after the atomic rename

- **WHEN** the complete staged directory has been atomically renamed but synchronizing
  its parent directory fails after all other final state checks were confirmed
- **THEN** the importer returns code `2` with empty stdout and says that durability is
  uncertain and the complete final directory may already be visible at that path
- **AND** it preserves that complete directory rather than automatically deleting or
  using it
- **AND** after filesystem recovery the user reruns the same unchanged inputs into a
  new absent sibling and byte-compares both two-file outputs before trusting either

#### Scenario: Published state changes after the atomic rename

- **WHEN** the no-replace rename completed through the held parent descriptor but a
  final check finds parent effective-owner/permission drift, a moved or replaced
  destination entry, or unexpected output inventory, mode, link count, size,
  identity, or bytes
- **THEN** the importer returns code `2` with empty stdout and reports the held
  parent's `st_dev`/`st_ino`, prior published entry name, and published directory's
  `st_dev`/`st_ino` plus known created-file device/inode as state-uncertain
- **AND** automation stops, preserves inputs unchanged, and neither retries nor
  transfers any result while the user forwards the entire diagnostic for emergency
  system-administrator recovery; no self-service recovery command is offered
- **AND** the administrator accounts for every name/hardlink of each created inode
  and quarantines every located copy; a missing directory, inode, or incomplete link
  set remains an unaccounted sensitive output copy

#### Scenario: Post-rename hardlink drift requires all-link quarantine

- **WHEN** a created output file acquires another hardlink after atomic rename and
  final verification observes `st_nlink!=1`
- **THEN** publication is state-uncertain, the diagnostic reports the child
  device/inode, and neither output name is automatically deleted or transferred
- **AND** the administrator must find, account for, and quarantine every name and
  hardlink of that inode; failure to account for the inode or its complete link set
  remains an unaccounted sensitive copy, as exercised by
  [`test_post_rename_hardlink_requires_every_link_to_be_quarantined`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)

#### Scenario: Published confirmation is interrupted before normal return

- **WHEN** the complete durable import directory has been published and delivery
  errors or is interrupted before normal command return, including after full flush
- **THEN** the importer returns code `2`, preserves the directory, and declares
  empty, partial, or apparently complete stdout invalid rather than parsing it
- **AND** the first output is not used or retried in place; identical unchanged
  inputs are run into a new absent sibling, the normally returned successful repeat
  stdout supplies the receipt digest/flags/maps, and both directories are
  byte-compared, as exercised by
  [`test_post_publish_stdout_write_or_flush_failure_preserves_output`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_closed_stdout_pipe_keeps_classified_exit_code_two`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_confirmation_recovery_survives_neutralizer_interrupt`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py), and
  [`test_interrupt_after_full_confirmation_before_return_invalidates_stdout`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)

#### Scenario: Finalization is interrupted before confirmation delivery starts

- **WHEN** publication has completed but a descriptor close fails or the wrapper is
  interrupted after inner return and before one-line JSON delivery starts
- **THEN** the importer returns code `2` with empty stdout, preserves the found
  directory, and reports finalization uncertainty distinct from confirmation delivery
- **AND** code `2` does not prove absence, the diagnostic does not overclaim
  durability, and recovery uses the same unchanged-input new-sibling repeat plus
  byte comparison, as exercised by
  [`test_parent_close_failure_after_publish_has_distinct_empty_stdout_route`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_published_file_or_directory_close_failure_blocks_confirmation`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_keyboard_interrupt_during_published_descriptor_close_is_classified`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py), and
  [`test_import_interrupt_after_inner_return_uses_publisher_state`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)

#### Scenario: Manual content closure is not fabricated

- **WHEN** `non_audited_content_review_required=true`
- **THEN** the importer reports the exact value-free field map but emits no native
  Release15 artifact claiming that manual review is complete
- **AND** a later `coding-reliability complete=true` cannot be cited as proof of
  closure because that command does not consume the receipt

## MODIFIED Requirements

### Requirement: Coding reliability uses a closed content-bound audit

The system MUST validate the exact frozen audit-plan field set and self-digest,
authoritative primary and secondary coding-record contracts, stable canonical
candidate identities, content hashes, normalized coder-label distinctions, and
closed adjudication records. Label inequality MUST NOT be described as validation
of independent reviewer identities. Every coding-reliability JSON and JSONL input
MUST use strict UTF-8 JSON with unique keys at every nesting level and MUST reject
`NaN` and infinities before evaluating the gate. Invalid records MUST remain visible
in the corresponding `invalid_*` and `unresolved_candidate_ids` collections and MUST
prevent completion.

The installed guidance MUST publish the exact `audit-decisions.jsonl` and
`adjudications.jsonl` object shapes. It MUST identify `quality coding-audit-prepare`
outputs as the first-party screening, primary, plan, queue, and
pending-template inputs and the native review importer as an optional producer of
four-field audit decisions from externally returned coding. Compatible exact
expert/manual inputs MUST remain supported. Returned secondary coding and
adjudications remain externally supplied contract-specific inputs; their
`human_review`, `quote_verified`, and `full_text_reviewed` completion-state values
MUST be treated as declarations rather than authenticated evidence of human
authorship, review, independence, or packet use.

All valid record hashes MUST use SHA-256 over UTF-8 JSON serialized with sorted
keys, compact separators, `ensure_ascii=false`, and `allow_nan=false`; collection
digests MUST sort records by their canonical record digest before hashing the
canonical array. A syntactically escaped lone surrogate that cannot be canonically
encoded MUST remain an invalid visible record and MAY use a deterministic
escaped-ASCII fingerprint only for diagnostics; that fingerprint MUST NOT validate
a content hash or make the record eligible.

The audit plan MUST select the general and false-exclusion samples by independent
canonical SHA-256 ranks. `sample_size` and `exclusion_sample_size` MUST be upper
bounds when the corresponding frame is smaller, the two selected lists MAY overlap,
and `required_candidate_ids` MUST equal their sorted set union.

`quality coding-reliability` MUST remain explicit about its evidence boundary. It
does not accept the blinded packet or native import receipt, does not technically
enforce `non_audited_content_review_required`, and does not revalidate primary,
secondary, or adjudicated quotes and locators against packet text. In particular,
when adjudication replaces the audited `alternative_grounds` field, reliability
validates only the exact adjudication field set, coder bindings, digests, reviewer
distinction, and chronology; it does not check the final nested quotes or locators.
Guidance MUST require a separate human packet-text recheck and external record after
such a replacement. Therefore `complete=true` MUST NOT be described as proof that
either this recheck or Release15's non-audited manual content review was completed.
The external record's `final_resolved_value_sha256` MUST be defined exactly as
SHA-256 over the UTF-8 encoding, without a trailing newline, of
`json.dumps(final_alternative_grounds, sort_keys=True, separators=(",", ":"),
ensure_ascii=False, allow_nan=False)`. If the full final 20-field coding record is
bound instead, `final_resolved_coding_sha256` MUST use that identical formula over
the full record.

#### Scenario: Secondary coding is bound to the audited candidate

- **WHEN** an outer audit record selects one required candidate but the nested
  content-bound secondary coding names another candidate
- **THEN** reliability records the required candidate in
  `invalid_binding_candidate_ids`, `invalid_audit_record_ids`, and
  `unresolved_candidate_ids`
- **AND** returns `complete=false` and process code `3`

#### Scenario: Equally incomplete records cannot simulate agreement

- **WHEN** primary or secondary coding omits a field required by the authoritative
  coding-record contract
- **THEN** the corresponding candidate is recorded as invalid and unresolved
- **AND** matching absent values do not count as agreement

#### Scenario: Missing primary coding remains visible

- **WHEN** a canonical candidate appears in the frozen screening frame but has no
  primary coding record
- **THEN** the plan records that candidate in `invalid_primary_record_ids`
- **AND** reliability cannot become complete even if no secondary disagreement is
  visible

#### Scenario: Unicode identity must be canonical and visible

- **WHEN** an identifier, coder, adjudicator, or mandatory coding text contains a
  Unicode format/control/surrogate payload that is not permitted visible multiline
  text
- **THEN** the record is invalid and remains visible in the applicable diagnostic
  collection
- **AND** ordinary canonical visible Unicode text is preserved rather than
  ASCII-folded
- **AND** an escaped lone surrogate cannot turn the result into an input exception
  or completed audit

#### Scenario: Adjudication is exact and chronological

- **WHEN** an adjudication contains an extra or unaudited resolved field, mismatched
  coding hashes, an orphan candidate, a reviewer equivalent to a coder, a reduced
  timestamp, or a future timestamp
- **THEN** the candidate remains unresolved
- **AND** reliability cannot become complete

#### Scenario: Sample maxima can overlap

- **WHEN** a false-exclusion candidate is selected by both independent ranks or
  either eligible frame is smaller than its configured maximum
- **THEN** both sample lists preserve their independently selected IDs
- **AND** required candidates are their sorted set union without requiring
  disjointness or exact configured lengths

#### Scenario: Ambiguous JSON cannot pass the declared-review gate

- **WHEN** the audit plan, primary coding, audit decision, or adjudication contains a
  repeated key at any nesting level or a non-finite JSON constant
- **THEN** coding reliability returns input error code `2` before assessing agreement
- **AND** it emits no completed reliability result

#### Scenario: Declared completion state is not authenticated human proof

- **WHEN** a structurally valid secondary record declares approved review and
  verified/full-text completion
- **THEN** native import and reliability may validate those exact declared values
- **AND** neither command claims to authenticate a person, authorship, independent
  work, or actual packet use

#### Scenario: Adjudication replaces alternative grounds

- **WHEN** a valid adjudication resolves an `alternative_grounds` disagreement with
  a new value and all closed hashes and chronology agree
- **THEN** reliability may resolve that audited field without reading packet text
- **AND** `complete=true` does not prove the final nested quotes or locators were
  rechecked; guidance requires a separate human recheck record

#### Scenario: Non-audited content review is outside Release15 reliability

- **WHEN** a native receipt reports `non_audited_content_review_required=true` but
  the exact four-field decisions otherwise satisfy coding reliability
- **THEN** reliability does not consume that receipt and may not technically block
  solely on the advisory flag
- **AND** its completed result cannot be used as proof that the separately required
  manual content review was performed

### Requirement: Native audit preparation emits a primary-answer-blinded reviewer archive

New output from `quality coding-audit-prepare` MUST carry
`bundle_contract_version="1.2"` in the parent manifest and MUST include
`independent-review-packet.zip` as its sixth exact content file. The manifest
schema MUST retain distinct branches for the preceding five-file manifest without
`bundle_contract_version`, the exact six-file Release14 `1.1` manifest, and the
exact six-file current `1.2` manifest. The new producer MUST emit only the `1.2`
variant and MUST NOT reinterpret a legacy or `1.1` manifest as `1.2`. Native import
MUST retain externally anchored `1.1` packets under their declared contract and
immutable Release14 guide bytes, while the unversioned five-file form remains on
the manual compatibility path.

The ZIP MUST contain exactly six members: the five payload members
`CODING-BRIEF.json`, `CODING-CODEBOOK.md`, `REVIEW-INSTRUCTIONS.md`,
`review-materials.jsonl`, and `secondary-coding-template.jsonl`, plus
`review-packet-manifest.json`, which inventories exactly those five payload members.
It MUST use a sorted flat path order, stored entries, fixed timestamps and
regular-file modes, and no archive comment so identical accepted inputs under the
same declared bundle contract produce identical bytes. Before constructing the ZIP,
the producer MUST enforce the configured byte limit for every member and the total
payload, and the ZIP writer MUST use `allowZip64=false`.

Prepare publication MUST use the same held-parent, no-replace, no-destructive-
cleanup-after-`mkdir`, descriptor-finalization, and uncertainty contract as import.
On macOS/Darwin it MUST additionally prove by file descriptor that the parent at
every recheck, the temporary directory before file creation, every created file
before its first byte, and the complete bundle directory/files before and after
rename have no extended ACL. Any ACE, including deny-only or non-inheriting, and
any ACL API/identity uncertainty MUST fail closed; mode `0700`/`0600` alone MUST
NOT be called sufficient on macOS, and no Linux ACL inspection is claimed.

Each review-material row MUST have the exact closed field set `schema_version`,
`candidate_id`, `chain_id`, `document_id`, `source_text_sha256`,
`packet_text_sha256`, and `text`. It MUST carry the same candidate and
chain/document identities as the frozen audit inputs, the normalized store
`source_text_sha256`, a `packet_text_sha256` over the exact UTF-8 text string
supplied in that row, and the non-empty full text. It MUST NOT carry `source_id` or
`source_ids`. Exact full text MAY retain TAB, LF, VT, FF, and CR layout controls but
MUST contain a visible non-whitespace character and MUST reject every other Unicode
control (`Cc`) plus every format (`Cf`) and surrogate (`Cs`) code point before any
publication. The pending templates MUST equal the producer's selected secondary
templates byte for byte.

The sorted unique inner-manifest `candidate_ids`, the review-material candidate
IDs, and the pending-template candidate IDs MUST each equal the frozen audit
plan's exact `required_candidate_ids`, with every candidate present exactly once
in each JSONL file. For every candidate, `candidate_id`, `chain_id`, and
`document_id` MUST agree across material and template, and both text digests MUST
agree with the content-addressed document and exact supplied text. A missing,
extra, duplicate, or cross-bound row MUST prevent any parent bundle publication.

The self-digesting inner manifest MUST bind the exact candidate population and the
size and SHA-256 of all five payload members. It MUST declare primary-answer
blinding, full-text inclusion, pending independent review, no created human
approval, no default publication safety, and no legal readiness. Both the inner and
versioned parent manifests MUST repeat `codebook_sha256` for the exact built-in
codebook bytes and `coding_brief_file_sha256` for the exact serialized neutral-brief
bytes, and each value MUST equal the corresponding inner file-inventory digest.

The required `--codebook-version` input MUST accept exactly the release-supported
allowlist, which is only `1.0` in this release, and MUST resolve the tracked neutral
`CODING-CODEBOOK.md`. Primary records MUST carry that same version, but their value
is only an equality check: neither codebook selection nor any ZIP bytes may be
derived from a primary record. A missing or unsupported selection, primary mismatch,
or missing, unsafe, empty, non-UTF-8, or concurrently replaced codebook MUST prevent
publication.

`CODING-BRIEF.json` MUST be the exact closed self-digesting projection of the frozen
plan's neutral reviewer context: plan identity and title, selected codebook version,
exactly one directional hypothesis with only its ID, fixed
`hypothesis_under_test` status, text and norm references, applicable norm editions,
population, inclusion/exclusion rules, materiality rule, and contradiction rule. It
MUST NOT project query/search lanes or text, screening matches, sampling metadata,
primary coding, `approved_by`, `adverse_review`, or other reviewer/search metadata.
Because `supports`/`adverse` require a fixed proposition and the 20-field coding
record has one unqualified `relation`, an open `research_question`, zero questions,
or multiple frozen questions MUST prevent publication and require separate
per-hypothesis frozen plans and audit packets.

Apart from the independently captured unchanged judicial `text` and its content
identities/digests, the required candidate union, the closed neutral plan projection,
the opaque frozen-plan commitment, and the independently selected built-in codebook,
no inner field, metadata value, row order, path, or archive byte may derive from a
primary coding record or digest, first-coder identity, sample-lane label, or
adjudication. Raw query lanes, query text, and screening matches MUST NOT be
serialized. `plan_sha256` and each content-bound candidate ID MAY cryptographically
commit to the full frozen plan, including query lanes; documentation MUST NOT call
that commitment semantic secrecy from a party that knows or guesses the plan. The
content of the judicial act itself and membership in the union sample are not hidden
and MUST NOT be described as outcome-blind evaluation.

The parent manifest MUST bind the exact ZIP byte length and SHA-256. Successful
producer stdout MUST expose that ZIP digest as
`independent_review_packet_sha256` and MUST also expose the exact parent-manifest
self-digest as `manifest_sha256`. The custodian MUST retain both values separately
from the bundle: communicate only the expected ZIP digest to the reviewer for
comparison before extraction or coding, and preserve the expected parent-manifest
digest for the later native import. The `1.2` embedded guide MUST direct the
custodian from the returned secondary JSONL to
`quality coding-audit-review-import` using the separately retained manifest digest
and expected secondary-coder label. Its user-facing prose MUST use “пакет аудита”,
gloss `reading_family` as “семейство толкования”, `supports` as “поддерживает”, and
`adverse` as “противоречит”, while preserving the exact machine identifiers. The
updated guide bytes MUST change their inner member digest and flow into the exact
deterministic ZIP and parent-manifest digests. The custodian MUST use the two anchors
from that same preparation run, not patch the immutable ZIP or reuse hashes from an
earlier packet. The inner self-digest MUST NOT be represented as authentication of
its own enclosing ZIP, and neither digest MUST be represented as reviewer
authentication.

Prepare MUST close every retained created-file and published-directory descriptor
and then its held output-parent descriptor before delivering the one-line stdout
confirmation. From delivery start until normal command return, any error or
asynchronous interruption—including short/failed write, explicit flush failure, and
interruption after a complete successful flush—MUST preserve the bundle, return code
`2`, and invalidate empty, partial, or apparently complete stdout. The custodian MUST
NOT use or retry that bundle in place. After stdout repair, the same unchanged
workspace inputs MUST be prepared into a new absent sibling and both bundles
byte-compared; only the complete success line followed by normal return from that
repeat MAY supply the out-of-band `manifest_sha256` and
`independent_review_packet_sha256`, and the first bundle MUST NOT be used to recreate
its own external manifest anchor. Any error or interruption after publication but
before delivery starts—including a retained created-file, published-directory, or
parent-descriptor close failure and a wrapper interruption after inner return or
parent close—MUST instead leave stdout empty and report finalization uncertainty:
code `2` does not prove bundle absence, and the diagnostic MUST NOT itself claim
confirmed durability. It MUST preserve the found bundle without use and require the
same new-sibling repeat, successful stdout and normal return, and byte comparison.

#### Scenario: User hands one archive to the independent coder

- **WHEN** a valid native audit bundle is prepared from a verified workspace
- **THEN** its parent manifest binds one deterministic
  `independent-review-packet.zip`
- **AND** that archive gives the reviewer all selected full texts, identities,
  pending templates, neutral brief, built-in codebook, and Russian instructions
  without the primary answers
- **AND** the `1.2` instructions say “пакет аудита”, `reading_family` (“семейство
  толкования”), `supports` (“поддерживает”), and `adverse` (“противоречит”) while
  retaining exact JSON identifiers, with their updated bytes covered by the same-run
  member, ZIP, and manifest digests
- **AND** producing it leaves secondary review, import, adjudication, legal approval,
  and filing incomplete

#### Scenario: Prepare confirmation delivery is interrupted before normal return

- **WHEN** the `1.2` bundle is completely and durably published but delivery errors
  or is interrupted before normal command return, including after full flush
- **THEN** code `2` preserves the bundle and declares empty, partial, or apparently
  complete stdout invalid
- **AND** the same unchanged inputs are prepared into a new absent sibling, both
  bundles are byte-compared, and only normally returned successful repeat stdout
  supplies the manifest and review-packet anchors, as exercised by
  [`test_prepare_flush_failure_preserves_bundle_but_not_manifest_anchor`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_audit_producer.py)

#### Scenario: Prepare finalization is interrupted before confirmation delivery

- **WHEN** the bundle has been published but a descriptor close fails or the wrapper
  is interrupted after inner return or parent close before delivery starts
- **THEN** code `2` leaves stdout empty without proving bundle absence or overclaiming
  durability
- **AND** the bundle is preserved without use and recovery requires the same
  identical-input new-sibling repeat, successful stdout, and byte comparison, as
  exercised by
  [`test_prepare_interrupt_after_inner_return_uses_publisher_state`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_audit_producer.py) and
  [`test_prepare_interrupt_after_parent_close_before_delivery_is_finalization`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_audit_producer.py)

#### Scenario: Legacy and versioned parent manifests stay distinguishable

- **WHEN** schema validation receives an intact preceding five-file manifest without
  `bundle_contract_version`, an exact six-file Release14 manifest with
  `bundle_contract_version="1.1"`, or an exact six-file current manifest with
  `bundle_contract_version="1.2"`
- **THEN** each is accepted only by its own exact schema branch and the new producer
  emits only `1.2`
- **AND** native import may accept only an externally anchored `1.1` or `1.2` packet
  under its declared version and immutable version-specific guide bytes
- **AND** an unversioned six-file manifest, a versioned five-file manifest, or any
  mixed or reinterpreted file set is rejected rather than upgraded silently

#### Scenario: Every required candidate has exactly one review pair

- **WHEN** the producer assembles review materials, pending templates, and the
  inner manifest for a multi-candidate union
- **THEN** all three sorted unique candidate populations equal the frozen required
  candidate set
- **AND** omission, duplication, an extra candidate, or swapped identity/text
  binding prevents publication

#### Scenario: Primary answers change without changing selected membership

- **WHEN** two otherwise identical valid workspaces differ only in primary
  substantive coding, first-coder identity, and per-lane selection while retaining
  the same candidate union, codebook version, and source inputs
- **THEN** their independent-review ZIP bytes are identical
- **AND** their parent custodian artifacts may still differ and remain separately
  bound to their exact primary inputs
- **AND** unchanged judicial text remains byte-exact even if it contains a string
  also used by one primary coding record

#### Scenario: Codebook authority is independent and allowlisted

- **WHEN** the custodian omits `--codebook-version`, selects anything other than
  `1.0`, a primary record names another version, or the installed `1.0` codebook is
  missing, unsafe, empty, non-UTF-8, or changes during preparation
- **THEN** preparation fails without publishing a parent bundle
- **AND** no primary field is treated as authority for codebook selection or bytes

#### Scenario: Producer cannot cross the importer's ZIP bounds

- **WHEN** a prospective review member or aggregate payload exceeds the configured
  packet limit, or would require a ZIP64 representation
- **THEN** preparation fails before creating or publishing an archive
- **AND** the deterministic writer uses `allowZip64=false`, so a successful producer
  cannot emit a ZIP64 packet rejected by the native importer

#### Scenario: Directional reviewer context is sufficient without revealing search design

- **WHEN** a valid frozen plan contains exactly one `hypothesis_under_test`
- **THEN** `CODING-BRIEF.json` contains only the closed neutral projection needed to
  apply the codebook and its self-digest binds every projected field
- **AND** both manifests bind the exact brief and codebook file bytes
- **AND** no query lane/text, match, sampling lane, primary answer, `approved_by`, or
  `adverse_review` appears in the ZIP

#### Scenario: Open or multiple questions cannot supply a relation target

- **WHEN** the verified frozen plan contains an open `research_question`, zero
  questions, or more than one question
- **THEN** preparation fails without output instead of guessing which proposition
  `supports`, `adverse`, or the returned `relation` addresses
- **AND** the custodian must prepare separate single-hypothesis frozen plans and
  audit packets

#### Scenario: Captured and normalized text representations differ

- **WHEN** a selected captured text contains layout whitespace that normalizes for
  the content-addressed document identity
- **THEN** `source_text_sha256` remains the normalized store digest
- **AND** `packet_text_sha256` verifies the exact text string supplied to the reviewer
- **AND** TAB, LF, VT, FF, and CR remain byte-exact, while NUL, every other `Cc`, and
  every `Cf` or `Cs` character cause fail-closed refusal with no output

#### Scenario: Collapsed source copies differ only in exact layout

- **WHEN** two source rows share one chain/document identity and normalized store
  digest but have different exact UTF-8 text strings
- **THEN** preparation fails without output instead of selecting a variant by
  source ID or input order

#### Scenario: Packet is not automatically public-safe

- **WHEN** the archive contains selected full judicial texts
- **THEN** its manifest fixes `publication_safe=false`
- **AND** the instructions require deliberate secure transfer and separate
  publication/redaction judgment rather than treating public-source status as
  blanket permission to republish personal data

#### Scenario: Reviewer and later importer receive separate external anchors

- **WHEN** `coding-audit-prepare` succeeds and the custodian transfers the ZIP
- **THEN** stdout exposes `independent_review_packet_sha256` equal to the parent
  manifest's ZIP digest and `manifest_sha256` equal to the parent self-digest
- **AND** the reviewer receives and compares only the separately supplied expected
  ZIP digest before using the archive, while the custodian separately retains the
  expected parent-manifest digest for native import
- **AND** neither digest nor a successful comparison claims a signature, reviewer
  identity, completed review, legal approval, or filing authority
