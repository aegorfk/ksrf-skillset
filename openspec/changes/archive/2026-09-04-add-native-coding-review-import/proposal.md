## Why

The blinded packet now gives a second coder enough material to work independently,
but the custodian must still hand-build the four-field `audit-decisions.jsonl` and
can accidentally accept a quote that was never checked against the exact packet
text. `quality coding-reliability` intentionally has no text input, so a structurally
self-consistent returned record can bypass the strongest native evidence binding.

## What Changes

- Add `quality coding-audit-review-import` for the custodian after the second coder
  returns a completed strict JSONL file.
- Require the parent manifest SHA-256 printed by `coding-audit-prepare` as an
  out-of-band expectation, so a self-consistently rewritten custodian bundle is
  not accepted merely because its unkeyed internal digests agree.
- Pin one expected normalized secondary-coder label for the complete returned batch,
  bind only its SHA-256 in the receipt, fix
  `secondary_coder_label_precommit_verified=false`, and disclose that string checks
  neither authenticate a person nor prove when the label was selected. Name the
  successful comparison narrowly as
  `secondary_coder_label_differs_from_each_sampled_primary_label=true`, because it
  covers every selected candidate rather than unrelated extra primary rows.
- Version new prepare packets as `1.2` with accurate embedded import guidance while
  retaining immutable `1.1` bytes for externally anchored Release14 imports. New
  `1.2` handoffs prospectively choose a pseudonymous label before ZIP transfer;
  historical `1.1` returns receive only a consistency check. If the Release14
  manifest SHA-256 was not retained separately, native import remains unavailable:
  regenerate `1.2` from the unchanged source workspace or use the expert/manual
  compatibility path instead of rediscovering the value inside the bundle.
- Accept only a complete versioned `1.1` or `1.2` native custodian bundle and verify its
  closed parent manifest, every parent content file, the deterministic six-member
  review ZIP, its inner manifest, built-in codebook, neutral brief, candidate
  bijection, exact packet text, and primary bindings before trusting any return.
- Validate exactly one completed 20-field secondary record for every required
  candidate, with no extras or duplicates, exact identity/codebook/edition parity,
  a coder label distinct from the primary coder, and every main or alternative
  quote checked both as a literal string and through the existing normalized
  quote-presence/record-structure validator against the candidate's exact packet
  text. These checks do not validate propositions, facts, reasoning, or legal
  correctness; expose only the narrow
  `returned_quote_literal_presence_verified=true` proof flag.
- Atomically publish a new two-file output directory containing canonical
  `audit-decisions.jsonl` and a self-digesting
  `coding-audit-review-import-receipt.json` bound to the exact bundle, ZIP, returned
  bytes, generated decisions, codebook, brief, and candidate population.
- Require that output to be an absent sibling of the input bundle under the same
  held, effective-user-owned, non-group/world-writable parent directory descriptor;
  use descriptor-relative no-follow operations, path rechecks, private output
  modes, durable fsync-backed no-replace publication, and bounded resource use.
  Bound the bundle inventory before reading all entries, recheck effective ownership
  and permissions before rename and during final verification, and build producer
  ZIPs only after size checks with ZIP64 disabled.
- Report both candidate partitions and value-free per-candidate field maps in
  `audited_field_differences` and `non_audited_content_differences`.
- Report agreement/disagreement counts, whether adjudication is required, and
  whether separate manual content review is required while stating that this
  advisory signal is not yet consumed by the reliability command. Release15
  introduces no native artifact or machine gate proving that manual content review
  was closed; a minimal separate external review record is required when that flag
  is true. Exit code `0` means only that import and publication succeeded, so
  automation must parse and stop on either next-step flag. Also state that
  string-level coder distinction is not identity authentication, independence
  proof, legal approval, publication permission, or filing readiness.
- Correct the downstream reliability contract: it validates closed records and
  hashes but does not read the packet or receipt and does not revalidate
  adjudicated `alternative_grounds` quotes/locators against packet text.
- Define the external recheck's `final_resolved_value_sha256` as SHA-256 over the
  exact UTF-8 bytes from compact sorted-key JSON with `ensure_ascii=false`,
  `allow_nan=false`, and no trailing newline; apply the same formula to the optional
  full-record `final_resolved_coding_sha256`.
- Keep `audit-decisions.jsonl` in frozen candidate order, while defining the
  receipt's canonical secondary-coding collection digest over records first sorted
  by each record's canonical digest.
- Capture staging identity immediately after safe open and before `fchmod`; if
  that open fails, record the identity as unknown. Treat the atomic no-replace
  rename itself as the filesystem commit point, not a successful helper return.
  If the helper errors and the destination owns the captured staging inode,
  preserve it as state-uncertain. After any other failure following successful
  staging `mkdir`, preserve every possible temporary object and report cleanup
  uncertainty; never auto-unlink files or `rmdir` the staging entry because a
  concurrent name replacement prevents portable atomic ownership proof.
- Hold every created file descriptor and its device/inode through failure
  classification. Every post-`mkdir` uncertainty returns code `2` with empty
  stdout and reports the held parent identity, prior staging entry name, known
  staging-directory identity, and known created-file identities. Stop without
  retry or transfer; the user forwards the entire diagnostic to a system
  administrator because there is no self-service recovery command. The
  administrator must locate and account for every name/hardlink of each created
  inode, quarantine every located copy, and treat any inode or complete link set
  that cannot be accounted for as an unaccounted sensitive temporary copy.
- On macOS/Darwin, require the held parent on every recheck, the staging directory
  before file creation, each created file before its first byte, and the
  staging/final bundle directory and files before and after rename to have no
  extended ACL at all. Reject deny-only and non-inheriting ACEs too, and fail
  closed when the ACL API cannot prove absence. This guard is Darwin-specific:
  mode `0700`/`0600` alone does not establish privacy there and no Linux ACL
  inspection is claimed. User guidance directs operators to a private parent
  without extended ACL or to a system administrator, not to rely on `chmod` alone.
- Keep the `1.2` embedded user guide in plain Russian for the phrases “пакет аудита”,
  `reading_family` (“семейство толкования”), `supports` (“поддерживает”), and
  `adverse` (“противоречит”), while retaining exact JSON identifiers. Rebuilt guide
  bytes must flow into the immutable member, packet, and manifest digests; users must
  retain the hashes emitted by that same preparation run.
- Treat any parent-directory fsync failure after rename as durability-uncertain:
  preserve the visible result, recover the filesystem, rerun the same unchanged
  inputs into another absent sibling, and compare both two-file outputs bytewise
  before either is used downstream.
- Treat any post-rename parent-ownership/permission drift, destination-entry
  move/replacement, or output inventory, mode, link-count, size, identity, ACL, or
  byte drift as state-uncertain.
  Stop automation with inputs unchanged and forbid automatic retry or transfer.
  Report the held parent's device/inode, prior entry name, and published directory's
  device/inode plus every known created-file device/inode. This is emergency
  system-administrator recovery, not a self-service command: the user forwards the
  entire diagnostic, the administrator finds and accounts for every name/hardlink of
  each file and quarantines every located copy, and an unfound directory, inode, or
  incomplete link set remains an unaccounted sensitive copy.
- Add a distinct confirmation-delivery state after a fully published directory.
  From the start of the one-line success JSON delivery until normal command return,
  any error or asynchronous interruption—including short/failed write, explicit
  flush failure, or interruption after a complete successful flush—preserves the
  output, returns code `2`, and makes empty, partial, or apparently complete stdout
  invalid. Stop without using or retrying the same destination; rerun identical
  inputs into a new absent sibling and byte-compare both directories. A prepare
  anchor and an import receipt digest/next-step flags are authoritative only from
  the successful repeat stdout after that comparison.
- Add a separate finalization-uncertain state for any error or interruption after
  publication but before confirmation delivery begins, including a retained created
  file, published directory, or parent descriptor close failure and a wrapper
  interruption after the inner publisher returns. Expected stdout is empty and code
  `2` does not prove output absence; preserve but do not use the directory, do not
  overclaim its durability from this diagnostic, and recover through the same
  new-sibling repeat and byte comparison.
- Preserve the existing expert/manual `coding-audit-plan` and
  `coding-reliability` interfaces; this change adds a safer native route without
  silently treating legacy or hand-built artifacts as imported receipts.

## Impact

- Affected specs: `ksrf-practice-quality-exit-status`, `ksrf-user-facing-cli`.
- Affected runtime: `judicial_meaning.cli`, `judicial_meaning.practice_quality`,
  practice-quality JSON Schema, installed Russian references, and CLI inventory.
- No network, model, database, adjudication, legal approval, publication, or filing
  action is introduced.
