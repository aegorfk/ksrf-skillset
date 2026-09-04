## 1. Import contract tests

- [x] 1.1 Add source/install parity for a valid versioned native bundle and
  completed secondary JSONL; require byte-identical canonical decisions and receipt.
- [x] 1.2 Test closed candidate bijection, identity, codebook, norm-edition,
  one pinned/distinct coder label across the batch, declared completion flags, main
  quote, and every alternative quote through both literal and normalized checks
  against the exact candidate text; assert that declared completion-state and coder
  label checks are not represented as authenticated human evidence.
- [x] 1.3 Reject strict-JSON failures, missing/extra/duplicate candidates, extra or
  missing fields, stale digests, cross-bound text/identity, and legacy parent bundles.
- [x] 1.4 Reject tampered parent files/manifests and altered, compressed,
  reordered, renamed, duplicated, or metadata-drifted ZIP members, including
  codebook, brief, guide, materials, template, and inner manifest.
- [x] 1.4a Require the separately retained expected parent-manifest SHA-256 and
  prove that a self-consistently rewritten parent bundle is rejected.
- [x] 1.4b Preserve byte reproduction for old `1.1` packets and emit/test the new
  `1.2` packet with accurate embedded native-import guidance; cover prospective
  `1.2` pseudonym selection, historical `1.1` consistency-only handling, and the
  no-native-import fallback when no separate Release14 manifest digest survives.
- [x] 1.5 Test non-existing output, input containment/alias checks, symlink refusal,
  hardlink refusal, bounded oversized/deep inputs, descriptor identity/rename/A-B
  replacement races, atomic no-partial-output behavior, `0700`/`0600` modes,
  fsync publication, and immutable input trees. On macOS also require no extended
  ACL at all on the parent, temporary/final directories, and created files. Require
  output to be an absent
  sibling under the held actual parent descriptor, require effective-user ownership
  and no group/world write on that parent, recheck effective ownership and mode
  immediately before rename and during final verification, and reject path/inode
  retargeting.
- [x] 1.5a Test per-file/ZIP/member/record/node/string/line limits, pre-`zipfile`
  EOCD/central-directory and ZIP64 rejection, nonblocking FIFO/special-file refusal,
  early bounded bundle-inventory refusal, producer member/total preflight with
  `allowZip64=false`, and generic diagnostics that do not echo untrusted IDs, keys,
  values, packet text, quotes, or absolute paths.
- [x] 1.5b Simulate pre- and post-rename fsync failures. For the post-rename case,
  require a previously confirmed parent path, code `2`, empty stdout, preserved
  complete output, and guidance to recover the filesystem, rerun identical inputs
  into a new sibling, and byte-compare both outputs before downstream use.
- [x] 1.5c Separately simulate post-rename parent permission drift, destination-entry
  move/replacement, and output inventory, directory/file mode, file link-count,
  size, identity, or byte drift. Require code `2`, empty stdout, held-parent and
  published-directory and created-file device/inode plus prior-entry recovery
  coordinates, unchanged inputs, no retry/transfer, the entire diagnostic forwarded
  for emergency system-administrator accounting and quarantine of every file
  name/hardlink with no self-service command, and an unaccounted-sensitive-copy
  result if the directory, an inode, or its complete link set cannot be located.
  Explicitly bind link-count drift to
  [`test_post_rename_hardlink_requires_every_link_to_be_quarantined`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py).
- [x] 1.5d Simulate failures at every post-`mkdir` pre-rename phase, including
  staging open/identity/`fchmod`, file creation/write/fsync, staging verification,
  and staging fsync. Capture directory identity immediately after open and before
  `fchmod`, retain every created file descriptor/device/inode through
  classification, and never automatically unlink a file or remove the temporary
  directory. Require code `2`, empty stdout, parent/known-temporary and created-file
  device/inode plus prior temporary entry name (or explicit unknown identity),
  unchanged inputs, no retry/transfer, the entire diagnostic forwarded for
  emergency system-administrator accounting/quarantine of every hardlink with no
  self-service command, and an unaccounted-sensitive-temporary-copy result if an
  inode or complete link set cannot be located. Bind this to
  [`test_pre_rename_directory_fsync_failure_preserves_staging_for_quarantine`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_staging_setup_open_and_fchmod_failures_preserve_quarantine_entry`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  and [`test_failed_staging_open_never_removes_replacement_directory`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py).
- [x] 1.5e Simulate a rename helper that first moves the temporary-directory inode
  and then reports an error. Treat rename itself, rather than helper return, as the
  commit point: a destination owning the captured inode is preserved and reported
  state-uncertain; every other post-`mkdir` outcome is preserved and reported
  cleanup-uncertain, even if the old temporary name appears to match. Bind this to
  [`test_rename_then_helper_error_preserves_complete_published_output`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py).
- [x] 1.5f Link the created-inode/hardlink preservation scenarios to
  [`test_native_coding_review_import_cli.py`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py):
  `test_cleanup_detects_sensitive_hardlink_outside_staging`,
  `test_precommit_failure_never_attempts_destructive_unlink`, and
  `test_cleanup_never_unlinks_replacement_for_escaped_created_inode`. Require no
  guessed or automatic deletion, file-inode diagnostics, and administrator
  accounting and quarantine of every name/hardlink.
- [x] 1.5g Cover post-publication confirmation delivery through
  [`test_post_publish_stdout_write_or_flush_failure_preserves_output`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_closed_stdout_pipe_keeps_classified_exit_code_two`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_confirmation_recovery_survives_neutralizer_interrupt`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_interrupt_after_full_confirmation_before_return_invalidates_stdout`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  and [`test_prepare_flush_failure_preserves_bundle_but_not_manifest_anchor`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_audit_producer.py).
  From delivery start until normal command return, write exception, short write,
  explicit flush failure, closed pipe, neutralizer interruption, and asynchronous
  interruption even after a complete successful flush return code `2` while
  preserving complete output; empty, partial, and apparently complete stdout are all
  invalid. Automation stops without same-destination retry or use; identical inputs
  are repeated into a new absent sibling and outputs are byte-compared. Require
  prepare anchors and import receipt digest/flags/maps only from the successful
  repeat stdout followed by normal command return.
- [x] 1.5h Cover pre-delivery finalization failure and interruption through
  [`test_parent_close_failure_after_publish_has_distinct_empty_stdout_route`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_published_file_or_directory_close_failure_blocks_confirmation`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_keyboard_interrupt_during_published_descriptor_close_is_classified`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_import_interrupt_after_inner_return_uses_publisher_state`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_prepare_interrupt_after_inner_return_uses_publisher_state`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_audit_producer.py), and
  [`test_prepare_interrupt_after_parent_close_before_delivery_is_finalization`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_audit_producer.py).
  For any error or interruption after publication but before confirmation delivery
  starts—including a created-file, published-directory, or parent close failure and
  a wrapper interruption after inner return—confirmation is not formed, stdout stays
  empty, code `2` does not prove absence, and the finalization-uncertain diagnostic
  does not overclaim durability. Preserve without use and recover through an
  identical-input new-sibling repeat and byte comparison. Apply the same wrapper-
  order contract to prepare and import.
- [x] 1.5i Add platform-neutral unit coverage and real Darwin integration coverage
  for the macOS fd-based extended-ACL guard. Require every ACE, including deny-only
  and non-inheriting entries, to fail closed on the held parent at each recheck, the
  temporary directory before files, each file before its first byte, and complete
  bundle directory/files before and after rename; fail closed on ACL API/identity
  faults, assert no-op outside Darwin without claiming Linux ACL inspection, and
  verify Russian help directs the user to a private parent without ACL or an
  administrator rather than promising `chmod` is sufficient. Bind unit/help coverage
  to [`test_extended_acl_probe_is_fail_closed_and_recaptures_fd_identity`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)
  and [`test_prepare_and_import_help_disclose_darwin_acl_boundary`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  non-Darwin behavior and probe TOCTOU defenses to
  [`test_extended_acl_guard_is_a_noop_outside_darwin`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_darwin_acl_probe_rejects_mode_change_inside_system_call`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py), and
  [`test_darwin_acl_removal_during_probe_is_detected_by_ctime`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  and real Darwin integration to
  [`test_darwin_inherited_parent_acl_is_rejected_before_output`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)
  and [`test_darwin_acl_added_after_parent_precheck_is_caught_on_staging_fd`](../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py).
- [x] 1.6 Validate receipt schema/self-digest, exact file hashes, deterministic
  output ordering, narrowly named audited-field partition, other substantive-content
  differences, exact value-free `audited_field_differences` and
  `non_audited_content_differences` maps,
  `expected_secondary_coder_label_sha256`, fixed
  `secondary_coder_label_precommit_verified=false`, narrow
  `secondary_coder_label_differs_from_each_sampled_primary_label=true` and
  `returned_quote_literal_presence_verified=true` fields, secondary collection
  digest ordering by canonical record digest while decisions stay in candidate
  order, separate
  adjudication/content-review signals, and conservative verification/safety flags.
- [x] 1.7 Test that exit code `0` only confirms import/publication and that documented
  automation parses both next-step flags and stops on either `true`; demonstrate that
  Release15 has no native manual-content-review closure artifact and that downstream
  reliability/adjudication do not revalidate changed `alternative_grounds` against
  packet text. Preserve the exact compact sorted-key UTF-8 JSON, no-trailing-newline
  formula for `final_resolved_value_sha256` and optional full-record digest.

## 2. Runtime

- [x] 2.1 Add a bounded read-only native bundle loader that compares the out-of-band
  expected manifest digest, verifies the exact versioned parent contract, and
  reuses the Release14 deterministic packet builder as an equality oracle for all
  six ZIP members; use descriptor-relative no-follow reads, explicit resource
  limits, an early bounded directory inventory, stable identity/metadata capture,
  pre-`zipfile` EOCD bounds, nonblocking special-file refusal, generic diagnostics,
  producer ZIP preflight with `allowZip64=false`, and exact final recheck.
- [x] 2.2 Add a pure secondary-return validator/builder that emits compatible
  four-field audit decisions only after exact text, identity, edition, and coder
  checks.
- [x] 2.3 Add the self-digesting import receipt and atomically publish exactly the
  decisions and receipt into a new private directory after a final input/codebook
  recheck, using one held safe-parent descriptor, sibling-only no-replace output,
  effective-owner/mode and path/inode rechecks, distinct cleanup-uncertain,
  fsync-only, and post-rename state-uncertain recovery; immediate pre-`fchmod`
  temporary-directory identity capture; rename-as-commit-point error reconciliation;
  retained created-file descriptors/identities and unconditional no-destructive-
  cleanup preservation after `mkdir`; Darwin-only fail-closed absence of every
  extended ACL on parent/temporary/final directories and files at all required
  checkpoints; descriptor close before one-line confirmation delivery; distinct
  pre-delivery error/interruption finalization uncertainty and delivery-start-to-
  normal-return error/interruption recovery; and no packet text,
  quotes, untrusted values, or absolute input paths in receipts or diagnostics.
- [x] 2.4 Add Russian CLI arguments/help and machine-readable success output with
  exact field-difference maps, label digest/precommit limitation, explicit code-0
  semantics/proof boundaries, invalid empty/partial/full-looking stdout for any
  failure or interruption after delivery starts and before normal return, empty
  pre-delivery finalization-interruption stdout, same-input/new-sibling byte-compare
  recovery, macOS guidance to choose a private parent without extended ACL or ask an
  administrator rather than rely on `chmod`, and next action for adjudication,
  separate manual content review, or reliability.
- [x] 2.5 Extend the JSON Schema with the closed receipt contract while preserving
  existing legacy/manual reliability inputs.

## 3. User guidance

- [x] 3.1 Replace manual native wrapping instructions with the import command while
  retaining a clearly labelled expert/manual compatibility path.
- [x] 3.2 Explain what exact text validation and the receipt prove, what coder-label
  comparison and declared completion-state do not prove, and how both difference
  maps and next-step flags affect the next step.
- [x] 3.3 Document refusal of legacy/tampered bundles, atomic output, private modes,
  the Darwin extended-ACL boundary without a Linux claim, and the continued human
  adjudication/legal/publication/filing gates.
- [x] 3.4 Document the `1.2` prospective and `1.1` historical branches, missing-anchor
  fallback, sibling/safe-parent constraint, post-rename byte-comparison recovery,
  rename/commit-point reconciliation, unconditional preservation and no automatic
  deletion after temporary-directory `mkdir`, separate cleanup-uncertain and
  post-rename state-uncertain administrator lookup/quarantine of every hardlink and
  unaccounted-copy states, the `1.2` Russian terms “пакет аудита”, `reading_family` (“семейство
  толкования”), `supports` (“поддерживает”), and `adverse` (“противоречит”), same-run
  immutable digest guidance, post-publication confirmation-delivery interruption
  through normal return and pre-delivery wrapper/retained-descriptor finalization-
  uncertain recovery with
  repeat-only anchors/receipt flags, macOS no-extended-ACL requirements and safe
  operator remediation, minimal external manual-content review record with exact digest
  canonicalization, and downstream packet-text gap for adjudicated
  `alternative_grounds`.

## 4. Verification and release

- [x] 4.1 Run focused importer, producer regression, schema, CLI, race/hardlink,
  confirmation-delivery/BaseException, pre-delivery wrapper and all retained-
  descriptor finalization, source/install,
  platform-neutral ACL-unit, real Darwin ACL-integration, and Python 3.10 tests.
- [x] 4.2 Run full skill/repository suites, strict validation, manifest parity,
  clean-install, and offline self-containment checks.
- [x] 4.3 Obtain independent review with no unresolved P1/P2, complete and archive
  OpenSpec, publish one atomic commit to feature and main, verify exact remote SHA,
  and install that published tree globally.
