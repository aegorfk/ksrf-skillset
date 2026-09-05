## Why

Native coding review import already tells a custodian to preserve an eligible
uncertain two-file output, repeat the same unchanged inputs into a new absent
sibling, obtain a normal successful confirmation, and byte-compare the two import
directories. That comparison remains a manual prose step. Generic filesystem tools
can follow links, omit an extra entry, race mutable names, expose private paths or
digests, or mistake equality for proof that the original failure was recoverable.

The Release19 finalization comparison intentionally excludes review-import
directories. A two-directory-only import comparison would also be too weak: the
existing import consumer validates a receipt against the exact source audit bundle
and its separately retained manifest digest. The installed recovery comparison must
retain that bundle-bound contract rather than declaring two self-consistent copies
valid in isolation.

## What Changes

- Add the installed nested command `judicial_meaning.py quality native-reliability
  compare-review-imports` with exactly five required inputs: the source audit bundle,
  its manifest SHA-256 retained from successful preparation stdout, the uncertain
  review-import directory, the newly repeated sibling, and the import receipt SHA-256
  retained from the repeat's complete successful stdout.
- Capture the bundle and both distinct two-file import directories as direct siblings
  through one held safe parent; require exact inventories, bounded no-follow reads,
  stable identities, private ownership/modes, single-link files, Darwin ACL absence,
  and complete final recapture of the bundle, both imports, and installed codebook.
- Reuse one shared import verifier: validate the exact externally anchored source
  bundle, each receipt and `audit-decisions.jsonl` against that bundle, the uncertain
  directory without an invented receipt expectation, and the repeated directory with
  its separately supplied receipt digest before reporting raw two-file equality.
- Emit one closed deterministic value-free JSON report with stable `match`,
  `mismatch`, `invalid`, and `unreadable` states and process codes `0`, `3`, and `2`.
- Keep the command local and read-only. It performs no import, repeat, repair, copy,
  move, deletion, quarantine, attachment, promotion, network, or database action.
- Make the exact route, five options, eligibility boundary, administrator exclusions,
  negative authority scope, and source/clean-install parity discoverable in Russian
  help and installed guidance.

This is an additive diagnostic/recovery comparison. It does not change either native
import artifact, `coding-audit-review-import`, the Release19 finalization comparison,
or any downstream finalization, reliability, handoff, complaint, publication, or
filing gate.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-native-coding-reliability-binding`: define the exact bundle-bound,
  descriptor-held review-import comparison and its closed value-free report.
- `ksrf-practice-quality-exit-status`: define comparison state precedence and exact
  `0`/`3`/`2` process outcomes without changing existing commands.
- `ksrf-user-facing-cli`: expose the installed nested route, Russian help, eligible
  recovery boundary, limitations, and source/install parity.

## Impact

A later implementation is limited to the existing judicial-meaning quality library,
CLI parser, installed practice-quality schema and guidance, focused source-only tests,
runtime parity checks, and the ordinary release manifest refresh. It adds no
dependency, launcher, service, persisted recovery token, filesystem mutation
permission, network access, or database access. Runtime, skills, schemas, tests, and
manifests are not changed by this proposal-only change.
