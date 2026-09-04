## ADDED Requirements

### Requirement: Native coding finalization is actionable in plain Russian

The clean-installed Russian CLI help and practice-quality guidance MUST expose a
copyable `quality coding-audit-finalize` command with required `--bundle`,
`--expected-manifest-sha256`, `--audit-import`,
`--expected-import-receipt-sha256`, and `--output-dir`, plus conditional
`--resolutions`. They MUST explain that the two expected digests are retained from
the successful prepare/import stdout outside the directories being checked, not
copied back from those directories during finalization.

Help MUST state that bundle, import, and new absent output are distinct siblings
under one private actual parent. It MUST name the four exact output files and show
the complete sequence prepare -> independent return -> native import -> resolve
reported differences if any -> native finalization. It MUST tell the user to omit
`--resolutions` when both imported maps are empty and require it when either map is
non-empty.

Help and installed guidance MUST state that a required resolution input is itself
private: a direct sibling under the same parent, owned by the effective user, mode
`0600`, single-link, and without any Darwin extended ACL. They MUST tell the user
to retain the successful finalization `receipt_sha256` from complete stdout outside
the finalization directory, and never recover that external anchor from the
self-digesting receipt being checked.

Guidance MUST publish the closed resolution-row shape and explain in ordinary
Russian that each row is pre-bound to the import receipt, candidate, entire ordered
field set, and primary/secondary hashes. It MUST explain the `primary`, `secondary`,
and `custom` choices; full bijection over both maps; pseudonymous reviewer label;
RFC 3339 review time; and exact declarations. It MUST state that a pseudonym and
declarations are not authentication, proof of authorship/independence/packet use, or
proof that a person performed the review.

#### Scenario: Custodian can complete the native review chain

- **WHEN** the user opens finalization help or installed practice-quality guidance
- **THEN** every required/conditional argument, external-anchor source, input
  relationship, resolution shape, and exact output filename is visible in Russian
- **AND** the user can distinguish no-difference finalization from the path that
  requires completed human resolution rows

### Requirement: Finalization help exposes bounded checks and exit meanings

The interface MUST explain that final coding is derived from exact imported values
and explicit choices rather than accepted whole; every final main and
`alternative_grounds` quote receives literal plus normalized presence checks against
the exact packet text; and generated adjudications and reliability use the same
captured state. It MUST also say that these checks do not validate proposition
truth, material facts, reasoning adequacy, legal correctness, norm temporal
applicability, or locator semantics. Locator review is declared only and successful
output always reports `quote_locator_verified=false`.

Help MUST define process code `2` as invalid contract/digest, unsafe filesystem
state, or I/O; code `3` as valid but incomplete/unresolved review with no closure
directory; and code `0` as atomic native technical closure only. It MUST say that
code `0` requires the generated reliability report to have exact
`complete=true`, but remains neither authenticated human review nor legal approval,
publication permission, freshness proof, or filing readiness.

The standalone `quality coding-reliability` workflow MUST remain discoverable as
the expert/manual compatibility path. Help MUST say plainly that its report alone
is not a native finalization receipt and cannot establish closure of Release15
non-audited differences or final packet-text revalidation.

#### Scenario: Automation can stop on three distinct outcomes

- **WHEN** the user reads `coding-audit-finalize --help`
- **THEN** Russian text distinguishes `0`, `2`, and `3`, whether a closure directory
  can be trusted, and the bounded meaning of a green receipt
- **AND** it does not instruct automation to infer human or legal authority from
  either reliability completion or finalization success

### Requirement: Finalization privacy and uncertainty recovery are discoverable

The finalizer help and installed guidance MUST inherit the Release15 private-output
rules in plain Russian: same effective-user-owned non-group/world-writable parent,
private sibling resolution input when present, new absent output sibling, `0700`
directory, `0600` files, and on macOS/Darwin no extended
ACL at all on every required parent/staging/final/file descriptor. They MUST reject
deny-only and non-inheriting ACEs, fail closed on ACL API/identity uncertainty, make
no Linux ACL-inspection claim, and never suggest that `chmod` alone proves ACL
absence.

Guidance MUST distinguish pre-`mkdir` validation failure from every post-`mkdir`
uncertainty. After staging starts, no file or directory is automatically unlinked;
known parent, directory, and file inode coordinates remain in value-free diagnostics
for administrator-only all-link accounting and quarantine. It MUST explain the
separate cleanup-, state-, durability-, and finalization-uncertain branches and that
an unaccounted inode/link set remains a sensitive unaccounted copy.

From the start of one-line success delivery through normal return, any write, flush,
pipe, or asynchronous interruption invalidates empty, partial, or apparently
complete stdout and preserves the directory. The user MUST stop, never retry the
same destination, repair the underlying fault, rerun unchanged inputs into a new
absent sibling, obtain a normal successful confirmation, and byte-compare the two
four-file directories before trusting the repeat receipt digest. The receipt and
diagnostics MUST be described as value-free: no packet text, quotes, substantive
selected values, pseudonyms, or absolute input paths.

#### Scenario: Interrupted success is not mistaken for closure

- **WHEN** staging/publication/confirmation fails or is interrupted after an output
  object may exist
- **THEN** help forbids destructive cleanup, same-destination retry, transfer, or
  parsing an apparently complete interrupted line
- **AND** it directs the user to the correct administrator quarantine or
  unchanged-input new-sibling repeat-and-byte-compare recovery
