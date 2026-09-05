## ADDED Requirements

### Requirement: Native audit-bundle comparison is actionable in Russian and portable

Source-tree and clean-installed launchers MUST expose the exact nested route `quality
native-reliability compare-audit-bundles`. Russian help MUST show required
`--uncertain-audit-bundle-dir` with metavar `СОМНИТЕЛЬНАЯ_ПАПКА_ПАКЕТА`, required
`--repeated-audit-bundle-dir` with metavar `ПОВТОРНАЯ_ПАПКА_ПАКЕТА`, required
`--expected-manifest-sha256` with metavar `SHA256_МАНИФЕСТА_УСПЕШНОГО_ПОВТОРА`, and
required `--expected-independent-review-packet-sha256` with metavar
`SHA256_ZIP_УСПЕШНОГО_ПОВТОРА`.

Help MUST say that both SHA values come from the same complete stdout line of the
normally returned code-`0` repeat, explain their different downstream roles, and
forbid reconstructing either from a package. It MUST require two different complete
seven-file private siblings under one safe parent and prohibit loose, partial,
staging, different-parent, or administrator-only inputs.

Help MUST explain `0=match`, `3=mismatch`, `2=invalid/unreadable`, exact raw equality,
full recapture, deterministic value-free stdout, and no output file, mutation,
automatic repeat, repair, delete, quarantine, transfer, subprocess, network, or
database operation. It MUST say a bare original exit `2` is insufficient: the full
original diagnostic must expressly allow unchanged-input repeat-and-compare. Staging,
cleanup, inode/hardlink, location, integrity, ACL/security, or quarantine uncertainty
forbids this user route.

Help and installed guidance MUST state that `match` cannot verify historical
eligibility, repeat normal return, anchor provenance, first-package durability, or the
source workspace; authorizes no downstream use; and grants no reviewer authentication,
legal correctness, current-law assurance, publication permission, complaint readiness,
or filing authority. Only the repeated package may proceed to fresh consumer
revalidation; the whole private package is never reviewer-facing, while its ZIP still
requires the separately retained packet anchor and normal privacy checks.

Equivalent source and clean-installed runs outside the repository MUST produce
byte-identical stdout, equal empty handler stderr, and equal process codes for all four
states. Both MUST reject abbreviated options, ignore conflicting ambient
`PYTHONPATH`, preserve all inputs, suppress bytecode writes, and need no installed
tests, evals, OpenSpec files, repository helper, new launcher, or dependency.

#### Scenario: Installed help gives one copyable complete command

- **WHEN** the user opens installed comparator help
- **THEN** it shows the exact four required options, Russian metavars, both anchor
  origins, eligibility condition, and `0`/`3`/`2` meanings
- **AND** exposes no output, discovery, repair, or automatic-repeat option

#### Scenario: Administrator state remains forbidden

- **WHEN** the original diagnostic names staging, cleanup, escaped/unaccounted inode
  or link, location, integrity, ACL/security, or quarantine uncertainty
- **THEN** help directs preservation and administrator recovery
- **AND** does not suggest comparison of a safe-looking path

#### Scenario: Match remains bounded technical evidence

- **WHEN** a user receives `match`
- **THEN** help directs only the repeated package to new consumer revalidation
- **AND** repeats every negative authority boundary

#### Scenario: Clean installation behaves identically

- **WHEN** equivalent match, mismatch, invalid, and unreadable inputs run from source
  and a clean install outside the repository
- **THEN** stdout, stderr, and process codes are identical
- **AND** surrounding filesystem snapshots are unchanged
