## Why

Release 17 makes every claim-bearing downstream consumer fail closed on an exact,
externally anchored native coding-reliability triple, but a user currently learns
about a missing or mismatched member only while running a larger consumer. A
read-only doctor is needed to classify that triple before handoff, import, or
uncertainty-profile construction without creating a new source of authority.

## What Changes

- Add the installed nested command `judicial_meaning.py quality native-reliability
  doctor` for an explicit reliability file, finalization-receipt file, and
  independently retained finalizer stdout SHA-256.
- Emit one closed, deterministic, value-free JSON report with stable `valid`,
  `incomplete`, `mismatch`, `invalid`, and `unreadable` states and process codes
  `0`, `3`, and `2`.
- Keep the command read-only and local: it writes no file, makes no network or
  database call, and does not repair, regenerate, import, or promote an artifact.
- Add fixed Russian remediation and help that preserve the Release 16 recovery
  rule and distinguish technical lineage from authentication, legal review, and
  filing authority.
- Require source-tree and clean-installed launchers to expose byte-equivalent
  reports and equal process behavior for equivalent inputs.

This is an additive CLI change. It does not revise `coding_reliability` v1.1,
weaken any Release 17 downstream gate, or change an existing artifact.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-native-coding-reliability-binding`: add a side-effect-free diagnostic
  projection over the existing exact native triple and define its closed,
  value-free report.
- `ksrf-practice-quality-exit-status`: add stable `0`/`3`/`2` process outcomes
  for the doctor without changing existing quality-gate outcomes.
- `ksrf-user-facing-cli`: expose the nested command, exact inputs, limitations,
  and recovery actions in Russian with clean-install parity.

## Impact

Implementation will be confined to the existing judicial-meaning quality library,
CLI parser, installed practice-quality schema and guidance, plus focused and
runtime-parity tests. The portable launcher and installer need no new executable,
dependency, network permission, database access, or payload class; their existing
file contract will carry the modified runtime files. Complaint-cycle import,
filing validation, handoff, uncertainty-profile state, and their current-plan
checks remain unchanged and authoritative.
