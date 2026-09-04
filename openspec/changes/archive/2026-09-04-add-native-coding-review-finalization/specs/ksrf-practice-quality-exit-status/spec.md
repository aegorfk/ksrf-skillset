## ADDED Requirements

### Requirement: Native coding review finalization consumes both exact ancestors

The system SHALL expose `quality coding-audit-finalize --bundle DIR
--expected-manifest-sha256 SHA256 --audit-import DIR
--expected-import-receipt-sha256 SHA256 [--resolutions FILE] --output-dir DIR`.
It MUST accept only an exact supported native `1.1` or `1.2` custodian bundle and
the exact two-file output of `quality coding-audit-review-import`. Both supplied
lowercase SHA-256 expectations MUST come from separately retained successful stdout
and MUST equal the revalidated parent manifest and import receipt respectively;
neither may be rediscovered from the object it is expected to anchor.

The finalizer MUST revalidate the closed bundle and import inventories, strict
JSON/JSONL, self-digests, every file byte and digest, deterministic review ZIP,
packet text, codebook, brief, frozen plan, candidate population, audit decisions,
receipt proof limits, and all cross-artifact bindings. It MUST use bounded
descriptor-based no-follow capture, require stable regular single-link inputs, and
reject symlinks, hardlinks, FIFO/socket/device inputs, excess resources, duplicate
JSON keys, non-finite values, self-consistent tampering, or input/parent drift.

The bundle, import directory, and absent output MUST be distinct siblings under one
held actual parent owned by the effective user and not writable by group or other
users. Internal hashes prove consistency only; they MUST NOT be described as
authentication or a substitute for the two external expectations.

#### Scenario: Both immutable native ancestors agree

- **WHEN** the complete bundle, complete Release15 import, and both separately
  retained expected digests agree byte-for-byte and by every closed binding
- **THEN** finalization derives the required difference-resolution population from
  the verified import receipt
- **AND** it never modifies either ancestor or trusts a caller-supplied whole final
  coding record

#### Scenario: An ancestor is replaced or self-consistently rewritten

- **WHEN** either external digest differs, an inventory or byte changes, a receipt
  is rebound to another bundle/decision population, an input is unsafe, or the
  common held-parent contract fails
- **THEN** the command returns code `2` with no successful closure receipt
- **AND** internal self-digests do not convert the changed artifacts into valid
  native provenance

### Requirement: Human resolutions form a complete pre-bound bijection

The required resolution set MUST be the exact union of every
`(candidate_id, field)` pair in `audited_field_differences` and
`non_audited_content_differences`, preserving the established eight-field then
four-field contract order. When this set is non-empty, the resolutions JSONL MUST
contain exactly one closed row per candidate in its union. Each row MUST bind the
exact import-receipt digest, candidate, complete ordered differing-field set, and
that candidate's exact primary and secondary coding digests.

Each differing field MUST appear exactly once in ordered `field_resolutions` and
select exactly one closed variant: `primary`, `secondary`, or `custom`. A primary or
secondary variant MUST contain only `field` and `choice`; a custom variant MUST also
contain exactly one field-typed `value`. The row MUST additionally contain a
canonical reviewer pseudonym distinct under the existing normalization/case-folding
rule from both bound coder labels, a non-future RFC 3339 `reviewed_at` with seconds
and timezone, `human_review="approved"`, and exact true declarations for
`full_text_reviewed`, `quote_locators_reviewed`, and `final_coding_approved`.

Rows MAY be supplied in any order. Missing candidates or required field choices are
validly incomplete and MUST return code `3` without a finalization directory.
Extra/duplicate candidates or fields, changed map membership/order, wrong hashes,
cross-candidate bindings, unknown choices, illegal custom values, malformed strict
JSON, or unexpected variant fields are invalid contract input and MUST return code
`2`. If both verified maps are empty, `--resolutions` MUST be omitted; if either is
non-empty and the option is omitted, the command MUST return code `3`.

When present, the resolution file MUST be a direct sibling under the same held
private parent as the bundle/import/output entries, owned by the effective user,
mode `0600`, regular, single-link, stable, and free of every Darwin extended ACL.
It MUST be recaptured through the held parent before staging because its selected
values and human declarations are private input data.

The pseudonym, timestamp, and Boolean/status fields are declarations. Validation of
their shape, distinction, chronology, and exact values MUST NOT be described as
authentication of identity/authorship, proof of independence or packet use, or
proof that the declared human act occurred.

#### Scenario: Every imported difference is resolved exactly once

- **WHEN** the resolution rows cover all and only the exact pairs in both verified
  maps with valid prebindings and one permitted choice per field
- **THEN** the finalizer derives each selected value from the bound primary,
  secondary, or typed custom source
- **AND** no difference is silently ignored or resolved twice

#### Scenario: Empty maps need no invented human record

- **WHEN** both verified difference maps are empty and `--resolutions` is omitted
- **THEN** finalization proceeds from exact imported agreement without inventing a
  resolver, timestamp, or adjudication

#### Scenario: Review is incomplete but not malformed

- **WHEN** a required resolutions file is omitted or a readable otherwise valid file
  has not yet covered every required candidate/field pair
- **THEN** stdout contains a fixed value-free incomplete envelope plus only the
  missing candidate/field population as its variable payload, process code is `3`,
  and no finalization directory is published

### Requirement: Final coding, adjudications, and reliability share one exact state

For every required candidate, the finalizer MUST deterministically rebuild a closed
20-field final coding record from the exact imported pair. An equal comparison field
MUST retain its exact primary value. Every differing comparison field MUST use only
its pre-bound resolution choice. For candidates with differences, the final
composite record MUST use the resolver pseudonym as the declared coder and the
authoritative completed-review state; candidates without differences MUST retain
the exact completed primary record. Every final record MUST preserve exact
candidate, chain, document, and codebook bindings and satisfy the authoritative
coding contract.

The final main quote and every quote within final `alternative_grounds` MUST each
occur as an exact literal substring of that candidate's exact packet text, and the
full final record MUST also pass the existing normalized quote-presence/text
validator. These checks establish presence and structure only. Locators MUST be
schema-valid and may be declared reviewed, but MUST NOT be machine-described as
verified; every finalization receipt MUST fix `quote_locator_verified=false`.

For each candidate with audited differences, the command MUST generate exactly one
existing-contract adjudication containing all and only those differing audited
fields with values from the final coding and the exact primary/secondary hashes,
resolver pseudonym, timestamp, and declared review. It MUST NOT create an empty
adjudication for a candidate with only non-audited differences. It MUST then derive
`coding-reliability.json` through the authoritative reliability assessment over the
exact bundle plan/primary population, imported audit decisions, and generated
adjudications.

Native code `0` MUST require complete map bijection, valid final coding, successful
literal and normalized quote checks, and exact Boolean
`coding-reliability.complete=true`. A structurally valid result that remains
incomplete or unresolved MUST return code `3` without publishing a closure
directory. The standalone `quality coding-reliability` command MUST remain available
for expert/manual compatibility, but its report MUST NOT be called native closure
because it does not validate a finalization receipt.

#### Scenario: Adjudicated alternative quote is rebound to packet text

- **WHEN** a primary, secondary, or custom choice supplies final
  `alternative_grounds`
- **THEN** every nested final quote must pass literal and normalized presence against
  the exact packet text before native closure
- **AND** locator semantics remain declared human review with
  `quote_locator_verified=false`

#### Scenario: Non-audited content can no longer bypass native closure

- **WHEN** the Release15 receipt reports one or more differences in `proposition`,
  `quote`, `quote_locator`, or `material_facts`
- **THEN** every such field participates in the same required resolution bijection
- **AND** the generated native receipt is unavailable until all are resolved and
  final quote checks pass

#### Scenario: Reliability remains unresolved

- **WHEN** all artifacts are structurally valid but the rederived authoritative
  reliability report is not exactly complete
- **THEN** the command returns code `3`, preserves the value-free unresolved report,
  and does not publish or imply technical closure

### Requirement: Finalization output is atomic, private, and value-free at receipt

Successful finalization MUST atomically publish a new absent sibling directory with
exactly `resolved-review-decisions.jsonl`, `adjudications.jsonl`,
`coding-reliability.json`, and
`coding-audit-finalization-receipt.json`. Resolved decisions MUST be in frozen
required-candidate order and bind the exact imported coding hashes, value-free
choice provenance, derived final coding, and canonical final-coding digest.
Adjudications MUST use their established canonical order, and the reliability file
MUST equal the report assessed for code `0`.

The closed self-digesting receipt MUST bind both external expectations, exact
bundle/manifest/packet/plan/import-receipt/audit-decision state, optional resolution
bytes or canonical absence, all three sibling output bytes, required and resolved
candidate/field populations, and the canonical final-coding collection digest. All
hashes MUST use the established compact sorted-key UTF-8 JSON recipe with
`ensure_ascii=false`, `allow_nan=false`, and no trailing newline where a canonical
object rather than file bytes is hashed.

Receipt and successful stdout MUST contain no packet text, quote, proposition,
material fact, selected/custom value, coder or reviewer label, person-attributable
timestamp, or absolute input path. They MUST expose only bounded identifiers, field
names, counts, digests, and proof-limit flags, including
`difference_resolution_bijection_verified=true`,
`final_quote_literal_presence_verified=true`,
`final_quote_normalized_presence_verified=true`, `reliability_complete=true`, and
always `quote_locator_verified=false`,
`source_workspace_reverified=false`, `reviewer_identity_authenticated=false`,
`human_review_authenticated=false`, `independence_verified=false`,
`receipt_authenticated=false`,
`norm_edition_temporal_applicability_verified=false`, `publication_safe=false`, and
`legal_readiness=false`.

Publication MUST reuse the Release15 descriptor-held no-follow/no-replace
transaction and its conservative recovery states: private `0700` directory and
`0600` files; retained descriptors and inode identities; file/directory/parent
fsync; no automatic unlink or directory removal after staging `mkdir`; atomic
rename as commit point; complete pre/post-rename identity, inventory, mode,
link-count, byte, effective-owner, and permission checks at every pre/post-open and
pre/post-rename boundary; and fail-closed fd-based absence
of every extended ACL on Darwin. ACL API/identity uncertainty MUST fail closed, and
no Linux ACL inspection is claimed.

Every post-`mkdir` failure MUST preserve possible sensitive temporary/published
objects and report the same cleanup-, state-, durability-, finalization-, or
confirmation-uncertain administrator recovery as Release15. Interrupted stdout is
invalid even if it appears complete. Recovery MUST use unchanged inputs, a new
absent sibling, successful normal return, and byte comparison of both exact
four-file directories; same-destination retry and destructive guessing are
forbidden.

#### Scenario: Native technical closure is published once

- **WHEN** both ancestors, every required resolution, final coding, quote check, and
  rederived reliability assessment pass without input or filesystem drift
- **THEN** the exact four-file private directory is published atomically and code
  `0` reports its finalization receipt digest
- **AND** code `0` is described only as bounded technical closure, never
  authenticated human review, legal approval, publication permission, or filing
  readiness

#### Scenario: Publication or confirmation becomes uncertain

- **WHEN** a failure occurs after staging begins or after rename, including Darwin
  ACL uncertainty, hardlink/identity drift, parent fsync, descriptor close, wrapper
  interruption, or stdout write/flush/interruption through normal return
- **THEN** code `2` preserves every possible object without destructive cleanup and
  invalidates any partial or apparently complete confirmation
- **AND** the user follows the Release15 administrator quarantine or unchanged-input
  new-sibling repeat-and-byte-compare recovery appropriate to the classified state
