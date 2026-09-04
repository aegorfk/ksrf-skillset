## Context

Release14 produces a deterministic primary-answer-blinded ZIP plus a separate
custodian directory containing the full audit frame and primary coding. The second
coder returns a completed 20-field JSONL file, but the documented next step required
the custodian to calculate hashes and manually wrap every row in a four-field audit
decision. Downstream `coding-reliability` validates structure and binding digests
but has no packet-text or import-receipt input, so it cannot establish that quoted
passages were present in the reviewed packet.

This change adds the missing deterministic offline bridge. It is not a reviewer
portal, identity provider, content-review closure gate, adjudicator, or legal gate.

## Goals / Non-Goals

**Goals:**

- Verify one complete versioned `1.1` or `1.2` native custodian bundle and its exact
  blinded packet before consuming a returned coding file.
- Validate every returned main and alternative-ground quote against the exact packet
  text for that candidate.
- Emit the existing four-field audit-decision contract in frozen candidate order
  without manual hash or wrapper construction.
- Bind the returned secondary collection independently of input row order by sorting
  records on their canonical record digest before hashing the canonical array.
- Produce an exact receipt with input/output bindings, value-free field-difference
  maps, next-step flags, and conservative proof limits.
- Publish exactly the decisions and receipt atomically into a new private sibling
  directory without network, tests, evals, or runtime fixtures.

**Non-goals:**

- Authenticate a person, prove independent work, prove what packet a person viewed,
  or turn declared completion-state fields into evidence of a human act.
- Resolve coding disagreements, natively close manual content review, change the
  reliability algorithm, approve legal analysis, publish judicial text, refresh
  law/practice, or authorize filing.
- Import legacy five-file bundles, invent a missing external anchor, or silently
  migrate hand-built expert inputs.
- Extract ZIP members to disk or accept alternate archive layouts.

## Decisions

### The command is custodian-side and requires a separate manifest anchor

The route is:

```text
quality coding-audit-review-import \
  --bundle CUSTODIAN_BUNDLE \
  --expected-manifest-sha256 SHA256_FROM_PREPARE_STDOUT \
  --expected-secondary-coder REVIEWER_LABEL \
  --secondary-coding RETURNED_JSONL \
  --output-dir NEW_SIBLING_DIRECTORY
```

The reviewer receives only `independent-review-packet.zip`. The command runs after
the reviewer returns a separate file, so it may read the custodian's primary
decisions, but it never writes either input. The expected manifest digest must come
from successful `coding-audit-prepare` stdout or another separately retained
channel. Reading it from the bundle at import time is not an external binding.

The importer opens the bundle first, obtains and holds its actual parent directory
descriptor, and captures the bundle relative to that descriptor. `--output-dir`
must be an absent sibling name under this same actual parent. The parent must be a
directory owned by the current effective user and not writable by group or other
users. Output resolution and final publication recheck the user-facing parent path
against the held descriptor's device/inode identity.

### Prospective `1.2` and historical `1.1` have explicit fallback rules

New prepare runs emit contract `1.2` and an updated embedded guide. Its user-facing
wording is Russian: “пакет аудита”, `reading_family` (“семейство толкования”),
`supports` (“поддерживает”), and `adverse` (“противоречит”); the machine JSON names
remain unchanged. The exact updated guide bytes are bound through the inner member
digest, deterministic ZIP digest, and parent-manifest digest. A custodian must use
the two hashes emitted by the same preparation run rather than patching the ZIP or
reusing anchors from an earlier packet. Before sending a new `1.2` ZIP, the custodian
prospectively chooses a pseudonymous secondary-coder label, retains and communicates
it separately, and does not use a real name. Every returned row must normalize to
that one operator-supplied value and differ from its primary label. The receipt exposes only
`expected_secondary_coder_label_sha256` and always fixes
`secondary_coder_label_precommit_verified=false`; it names the successful narrow
comparison `secondary_coder_label_differs_from_each_sampled_primary_label=true`. Runtime
cannot prove when the label was chosen, authenticate its user, or prove independent
work.

Exact old `1.1` guide bytes remain frozen so an externally anchored Release14
packet can be reproduced and imported under its declared version. Because the old
guide did not require a prospective pseudonym, `--expected-secondary-coder` checks
only batch consistency for an already-returned `1.1` file. If that file contains a
real name, the custodian asks its author for a pseudonymous returned copy and does
not silently edit it.

If the successful Release14 stdout or another genuinely separate record did not
retain `manifest_sha256`, the user must not rediscover the expected value inside the
bundle. Native import is unavailable. The safe fallback is to regenerate `1.2` from
the unchanged source workspace or use the existing expert/manual compatibility
route, which does not manufacture a native import receipt. The legacy unversioned
five-file bundle stays outside native import.

### Parent verification is closed, bounded, and version-specific

The loader bounds the top-level directory inventory before reading every child and
accepts exactly the seven regular top-level paths in a supported native bundle: the
six parent content files and
`coding-audit-inputs-manifest.json`. It rejects a symlink root or child, hardlink,
directory child, missing path, or extra path.

The canonical strict UTF-8 parent manifest must have the exact `1.1` or `1.2` field
set, producer, safety flags, ordered six-file inventory, self-digest, and lowercase
SHA-256 values. Each size and digest must match captured bytes. Screening, primary,
plan, queue, and template files are parsed with duplicate-key and non-finite-value
rejection. The importer reconstructs the audit plan from the complete closed
screening/primary populations and recorded sample limits and requires exact equality.
Content-bound candidate identities, manifest and plan populations, queue, templates,
selected primary hashes, codebook, brief, and source identity links must agree.

Before trusting internal consistency, the importer requires the parent
`manifest_sha256` to equal the separately supplied lowercase 64-hex expectation.
This rejects drift from that retained value; unkeyed internal hashes and exact ZIP
reproduction do not authenticate an author or provenance.

The capture inspects type before open and uses bounded descriptor-based
`O_NOFOLLOW` plus POSIX `O_NONBLOCK` reads for the bundle, children, returned file,
and built-in codebook. It requires stable regular single-link identities and
metadata before and after each read. FIFO, socket, device, and other special-file
inputs fail without waiting for a writer. Conservative limits apply to every parent
file both during import and producer prepublication validation, as well as to the
returned file, codebook, ZIP bytes, stored/uncompressed members and totals, physical
lines, records, JSON nesting/nodes, collections, and strings.

The producer checks the bounded size of every member and the total payload before
constructing the packet and opens its ZIP writer with `allowZip64=false`. Thus the
producer cannot create an archive form that the importer must reject as ZIP64.

Before `zipfile` parses entries, the importer parses the exact trailing 22-byte EOCD,
requires a comment-free, one-disk, six-entry non-ZIP64 archive, and bounds and locates
the central directory. ZIP metadata must then show `ZIP_STORED`, no encryption or
data descriptors, fixed flat names, no directories/traversal, extras, or comments,
canonical timestamps/modes, and bounded equal stored/uncompressed sizes. No member
is extracted to disk.

Diagnostics for untrusted duplicate keys, candidate IDs, and malformed archive
metadata are generic. They do not echo untrusted identifiers or values, packet text,
quotes, or absolute input paths.

### The deterministic builder is the ZIP equality oracle

The importer parses the brief, materials, and template from captured ZIP bytes and
calls the same deterministic version-aware packet builder with the verified parent
plan/frame/queue/template, captured materials, brief, and built-in codebook. The
regenerated archive must equal the input byte-for-byte.

That equality covers sorted member order, stored compression, fixed timestamp and
mode, names, extras/comments, exact version-specific Russian guide, exact built-in
codebook, closed neutral brief, material/template bijection, text digests, inner
inventory, and inner manifest self-digest. A syntactically valid but compressed,
reordered, renamed, duplicated, metadata-changed, or version-reinterpreted archive
fails.

### A pure builder validates returned coding against packet text

The pure builder receives the verified audit plan, primary rows, selected queue,
review materials, neutral brief, and returned records. It preserves duplicate
detection, requires the returned candidate set to equal the non-empty sorted
`required_candidate_ids`, accepts arbitrary input row order, and canonicalizes output
to frozen candidate order.

For every candidate it checks:

- the exact closed 20-field completed-coding shape and supplemental normalized
  quote-presence/record-structure validator;
- candidate, chain, document, codebook, source-text, primary-digest, queue, material,
  and template identity bindings;
- `norm_edition_id` membership in the closed neutral brief allowlist;
- one normalized batch coder label matching the operator expectation and distinct
  from the primary label of every selected candidate;
- the main quote and each supplied alternative-ground quote as literal Python-string
  substrings of that candidate's exact packet text.

The required `human_review="approved"`, `quote_verified=true`, and
`full_text_reviewed=true` values are declarations inside the returned contract.
They and quote-presence checks do not authenticate a human act, establish authorship,
prove packet use, verify a locator, or validate proposition, facts, reasoning,
temporal applicability, meaning, or legal correctness.

Each output decision contains exactly `candidate_id`, `primary_coding_sha256`,
`secondary_coding`, and `secondary_coding_sha256`. Both coding digests are recomputed;
none is trusted from the returned file. Decisions remain in frozen
`required_candidate_ids` order. The separate collection-level
`secondary_coding_sha256` sorts returned records by each record's canonical digest
before hashing the canonical array, so returned input row order cannot change that
collection binding.

### The receipt maps audited and non-audited differences without values

The receipt partitions the full population into sorted audited-field agreement and
disagreement IDs using the eight `AUDITED_CODING_FIELDS`: `label`, `speaker`,
`norm_edition_id`, `reading_family`, `relation`, `reasoning_to_outcome`,
`alternative_grounds`, and `remedy`. `audited_field_differences` contains one entry
for every disagreeing candidate with all and only the differing field names in
contract order, never their values.

It separately lists candidates that differ in `proposition`, `quote`,
`quote_locator`, or `material_facts`. `non_audited_content_differences` contains the
same value-free candidate-to-field mapping for that class.
`adjudication_required` is true exactly when an audited-field disagreement exists;
`non_audited_content_review_required` is true exactly when the second class exists.
Both are next-step signals, not proof of adjudication, content review, or reliability.

Release15 has no native artifact or machine validator proving closure of the manual
content-review signal. When it is true, the custodian keeps a separate external
record with at least candidate ID, reviewed field names, reviewer pseudonym,
`reviewed_at`, conclusion, receipt digest, and both coding digests, without calling
that record a built-in receipt.

`alternative_grounds` belongs wholly to the audited set. If adjudication changes it,
a human must recheck final nested quotes and locators against packet text and retain
a separate record. Its `final_resolved_value_sha256` is SHA-256 over the UTF-8 bytes
of `json.dumps(final_alternative_grounds, sort_keys=True, separators=(",", ":"),
ensure_ascii=False, allow_nan=False)` with no trailing newline. The optional
`final_resolved_coding_sha256` uses the identical formula over the complete final
20-field coding record. Downstream `coding-reliability` validates the closed adjudication
shape and hashes, but it neither reads the packet/import receipt nor revalidates
those final quotes or locators. Its `complete=true` does not prove that this recheck
or the non-audited manual review was closed.

### The two-file output and receipt are content-bound

The new directory contains exactly:

- `audit-decisions.jsonl`, canonical UTF-8 JSONL in required-candidate order;
- `coding-audit-review-import-receipt.json`, canonical UTF-8 JSON.

The receipt has this closed field set:

- identity: `schema_version`, `artifact_type`, `producer`,
  `bundle_contract_version`, `plan_sha256`, `audit_plan_sha256`,
  `codebook_version`;
- exact input bindings: `source_bundle_manifest_sha256`,
  `expected_source_bundle_manifest_sha256`,
  `source_bundle_manifest_file_sha256`, `review_packet_sha256`,
  `secondary_coding_file_sha256`, `secondary_coding_sha256`, `codebook_sha256`,
  `coding_brief_file_sha256`;
- exact output binding: `audit_decisions_file_sha256`;
- population/result: `candidate_ids`, `audited_fields`,
  `non_audited_content_fields`, `audited_field_agreement_candidate_ids`,
  `audited_field_disagreement_candidate_ids`, `audited_field_differences`,
  `non_audited_content_difference_candidate_ids`,
  `non_audited_content_differences`, `non_audited_content_review_required`,
  `adjudication_required`;
- label binding: `expected_secondary_coder_label_sha256`,
  `secondary_coder_label_precommit_verified=false`;
- bounded checks: `returned_quote_literal_presence_verified=true`,
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
  `publication_safe=false`, `legal_readiness=false`;
- `receipt_sha256`, the canonical digest of every preceding field.

`secondary_coding_file_sha256` binds exact returned bytes,
`secondary_coding_sha256` binds canonical returned records sorted by canonical
record digest, and
`audit_decisions_file_sha256` binds exact output bytes. Successful stdout repeats
receipt/output digests, counts, both value-free maps, both next-step flags, the label
digest/precommit limitation, and proof flags. Code `0` means only successful import
and publication. Automation must parse both `adjudication_required` and
`non_audited_content_review_required` and stop when either is true.

### Publication uses one held parent descriptor and no-replace rename

The bundle, returned file, and codebook are captured before validation. Immediately
before publication the importer recaptures the bundle by its name relative to the
same held actual parent descriptor, rechecks returned/codebook bytes, and rechecks
the user-facing parent path against the held device/inode. Any change aborts.

Staging creation, flat file writes/readback, staging fsync, destination existence
checks, exclusive no-replace rename, and parent fsync are descriptor-relative.
Staging and final directories are mode `0700`; files are mode `0600`; every file
and the staging directory are fsynced before rename. Effective-user ownership and
the absence of group/other write bits on the held parent are checked initially,
again immediately before rename, and during final state verification. Existing or
race-created destinations are never overwritten.

On macOS/Darwin these mode checks are necessary but not sufficient. The publisher
uses an fd-based fail-closed guard to require no extended ACL at all on the held
parent at every recheck, the staging directory before any file is created, each
new file before its first byte is written, and the bundle directory and every file
during the complete pre- and post-rename verification. Deny-only and non-inheriting
ACEs are rejected as well as permissive or inherited entries. Failure to load or
use the ACL API, or inability to prove a stable fd identity across its call, fails
closed. This makes no Linux ACL-inspection claim. Help tells a macOS operator to
choose a private parent without extended ACL or contact a system administrator;
`chmod` alone is not represented as removing or proving absence of an ACL.

Staging identity is captured immediately after its safe descriptor open and before
`fchmod`; if that open fails, the diagnostic records identity as unknown. The
publisher retains every successfully created file descriptor and its device/inode
through failure classification and confirmation finalization.

The filesystem commit point is the atomic no-replace rename itself, not the helper's
successful return. If the helper reports an error, publication is therefore
ambiguous until the destination name is checked relative to the held parent. If
that name owns the captured staging inode, the directory is preserved and the
publisher raises post-rename state uncertainty. Otherwise it performs no
destructive cleanup and raises cleanup uncertainty. A staging name that still
appears to own the inode does not make deletion safe against a concurrent
replacement.

Before staging `mkdir`, a validation failure can return code `2` with empty stdout
without creating an output object. From successful `mkdir` onward, every pre-commit
failure instead preserves whatever may exist under or outside the prior staging
name: no file `unlink` and no staging `rmdir` is attempted. This unconditional
preservation avoids deleting a replacement object where portable APIs cannot prove
ownership atomically.

Both post-`mkdir` uncertainty branches return code `2` with empty stdout and report
the held parent's `st_dev`/`st_ino`, prior staging entry name, the staging
directory's known `st_dev`/`st_ino` (or an explicit statement that identity capture
failed), and known device/inode coordinates for every created file. Automation
must stop with unchanged inputs and neither retry nor transfer anything. The user
must forward the entire diagnostic to a system administrator; there is no
self-service recovery command. The administrator locates the staging directory and
each created inode, accounts for all names and hardlinks of every file, and
quarantines every located copy. If an inode or its complete link set cannot be
accounted for, the incident remains an unaccounted sensitive temporary copy.

A parent-directory fsync failure after rename, when every other final state recheck
has succeeded, returns code `2` with empty stdout and a durability-uncertain
diagnostic. The complete output at the confirmed path is preserved but must not be
deleted or used downstream automatically. After filesystem recovery, the custodian
reruns the same unchanged inputs into another absent sibling and compares both
two-file outputs byte-for-byte before trusting either.

Every post-rename state check revalidates effective ownership and permissions of the
held parent, the user-facing parent identity, the prior destination entry and
published-directory identity, exact output inventory, final directory mode `0700`,
and each file's regular type, single link, mode `0600`, size, identity, and bytes.
A parent permission drift, destination entry move/replacement, or output inventory,
mode, link-count, size, or byte drift is state-uncertain: the user-facing path or
entry may no longer represent what was published through the held descriptor. The
command returns code `2` with empty stdout and identifies the held parent's
`st_dev`/`st_ino`, prior published entry name, and the published directory's
`st_dev`/`st_ino`, plus the known device/inode of every created output file.
Automation must stop, preserve all inputs unchanged, and neither retry nor transfer
any result. This is emergency system-administrator recovery, not a self-service
command: the user forwards the entire diagnostic, the administrator locates the
directory and every created inode, accounts for all names and hardlinks of every
file, and quarantines each located copy. A directory, inode, or complete link set
that cannot be accounted for remains an unaccounted sensitive output copy rather
than assumed absent.

### Publication confirmation is delivered only after descriptor finalization

Both prepare and import build their one-line JSON confirmation during publication
but do not write it yet. After publication returns, the command wrapper first closes
its held parent descriptor and only then writes the exact line and explicitly flushes
stdout. From the moment delivery is marked started until the command returns
normally, any error or asynchronous interruption is a confirmation-delivery failure.
This includes a short write, write exception, flush exception, and interruption after
the complete line was written and explicitly flushed but before normal return. The
directory has already passed complete durable publication, so it is preserved, but
code `2` is returned and stdout may be empty, partial, or apparently complete. Every
such stdout form is invalid and must not be parsed.

Recovery stops automation and prohibits use of the first directory or retry into the
same destination. After stdout is repaired, the custodian reruns identical unchanged
inputs into a new absent sibling, obtains one fully written and flushed JSON line
followed by normal command return, and compares both directories byte-for-byte. For
prepare, only the successful repeat stdout can supply the out-of-band
`manifest_sha256` and transferable packet digest; the first bundle must not be used
to recreate its own external anchor. For import, only the successful repeat stdout
after byte equality can supply the receipt digest, next-step flags, and difference
maps.

Any error or asynchronous interruption after publication but before confirmation
delivery is marked started is earlier and distinct. It includes a retained-created-
file, published-directory, or parent-descriptor close exception, interruption after
the inner publisher returns, and interruption after parent close but before entering
delivery. No confirmation has yet been formed, so stdout is expected to be empty;
nevertheless code `2` does not prove that the published directory is absent. This
branch is finalization-uncertain and must not itself be described as confirmation of
durability. It preserves but does not use the found directory and follows the same
identical-input/new-sibling repeat, successful-stdout, and byte-comparison recovery.
These confirmation/finalization states use the parent and published-directory
coordinates; the separate cleanup- and state-uncertain branches continue to disclose
every created-file inode and require administrator accounting/quarantine of all names
and hardlinks.

## Risks / Trade-offs

- [Self-digests are forgeable] -> Require a separately retained expected manifest
  digest and describe it as drift detection, not authentication.
- [A different coder string can be invented] -> Pin one normalized batch label and
  hash it, but keep precommit, identity, and independence proof flags false.
- [A later release changes versioned bytes] -> Freeze guide/codebook behavior and
  require exact version-specific ZIP reproduction.
- [Special files or ZIP64 metadata consume resources] -> Use nonblocking no-follow
  regular-file reads, bound inventory before full traversal, parse/bound EOCD before
  `zipfile`, cap every resource tier, preflight producer payload sizes, and disable
  ZIP64 in the producer.
- [Ancestor paths can retarget] -> Open the bundle first, hold its actual parent
  descriptor, require sibling output, and recheck path/device/inode before rename.
- [Audited fields omit evidence wording] -> Emit a separate value-free map and an
  advisory manual-review flag without pretending Release15 can prove closure.
- [Adjudication changes alternative grounds] -> Require a separate human packet-text
  recheck and disclose downstream reliability's lack of packet text.
- [Parent fsync fails after rename] -> Preserve the ambiguous output, rerun
  unchanged inputs to a new sibling after recovery, and require a bytewise
  comparison.
- [Rename reports failure after moving the inode] -> Check the destination against
  the captured staging inode because rename, not helper return, is the commit
  point; never delete either possible object, and treat a matching destination as
  post-rename state uncertainty.
- [A hardlink escapes or a staging filename is replaced after mkdir] -> Retain
  created file descriptors/identities through classification, attempt no automatic
  unlink or rmdir, and disclose file coordinates for administrator accounting and
  quarantine of every link.
- [Any setup or pre-rename step fails after staging mkdir] -> Capture identity
  immediately after open and before `fchmod`, preserve every possible temporary
  object, stop without retry or transfer, and require emergency administrator
  quarantine or an unaccounted-sensitive-temporary-copy classification.
- [macOS mode bits hide an extended ACL] -> Reject every extended ACE, including
  deny-only and non-inheriting entries, on the held parent, staging/final directory,
  and created files at the specified fd-based checkpoints; fail closed on ACL API
  faults and make no Linux ACL-inspection claim.
- [Parent permissions, entry identity, or output bytes drift after rename] -> Stop
  without retry, preserve inputs, forward the entire diagnostic for administrator
  lookup/quarantine using parent, published-directory, and created-file identities
  plus the prior entry name; account for every file name/hardlink and treat any
  missing inode or incomplete link set as an unaccounted sensitive copy.
- [Delivery starts but the command is interrupted before normal return, including
  after a complete successful flush] -> Preserve the fully published output,
  invalidate even apparently complete stdout, stop downstream use, and repeat
  identical inputs into a new sibling for a successful line, normal return, and byte
  comparison.
- [A close failure or wrapper interruption occurs after publication but before
  confirmation delivery starts] -> Keep stdout empty, report finalization uncertainty
  without inferring absence or overclaiming durability, and use the same new-sibling
  comparison recovery.
- [Inputs/outputs contain sensitive data] -> Use private modes and, on macOS, prove
  absence of extended ACL; keep texts, quotes, values, and absolute input paths out
  of receipt and diagnostics.

## Migration Plan

1. Add source/install, tamper, population, text, receipt, and atomicity tests.
2. Add pure returned-coding validation and canonical decision construction.
3. Add the closed parent/ZIP loader, receipt builder, held-parent final recheck, and
   CLI route.
4. Add schema, Russian help, installed guidance, historical fallback, and the
   expert/manual compatibility boundary.
5. Add resource-limit, early-inventory, producer-no-ZIP64, FIFO, EOCD/ZIP64,
   diagnostic-secrecy, sibling/path-race, field-map, digest-order, exit-code,
   post-`mkdir` preservation, created-inode/hardlink races, rename-error commit-point
   reconciliation, cleanup-uncertain, fsync-only, post-rename state-uncertain
   quarantine, Darwin extended-ACL unit/integration coverage, confirmation-delivery,
   and retained-file/directory/parent close-finalization regressions.
6. Run focused/full/Python 3.10/strict/clean-install checks and independent review.
7. Archive OpenSpec, publish one atomic commit to feature and main, verify both
   remote SHAs, and install the exact published tree globally.

## Open Questions

None. A receipt-aware native manual-content-review closure gate is a later
compatibility change; Release15 deliberately preserves the expert/manual reliability
route while exposing the missing work honestly.
