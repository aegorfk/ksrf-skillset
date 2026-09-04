## 1. Contract tests

- [x] 1.1 Add pure tests for exact union/bijection derivation across audited and
  non-audited difference maps, deterministic field order, absent resolution input
  for empty maps, and code `3` for readable incomplete coverage.
- [x] 1.2 Cover the closed resolution-row variants, receipt/candidate/field/hash
  prebindings, canonical pseudonym and timestamp, required declarations,
  primary/secondary/custom choices, and rejection of duplicate, extra, cross-bound,
  ambiguous, non-finite, or schema-invalid rows.
- [x] 1.3 Prove deterministic final-coding reconstruction, compatible adjudication
  generation for all and only audited differences, exact empty adjudication output,
  and rederived reliability `complete=true`/code `0` versus unresolved code `3`.
- [x] 1.4 Cover exact literal and normalized presence of the final main quote and
  every final `alternative_grounds` quote for primary, secondary, and custom
  choices; verify that locator review stays declared with
  `quote_locator_verified=false`.
- [x] 1.5 Cover complete native bundle/import revalidation, both out-of-band digest
  mismatches, self-consistent tampering, wrong sibling/parent identity, input drift,
  special files, hardlinks, symlinks, and bounded-resource failures as code `2`.
- [x] 1.6 Cover deterministic four-file output, exact modes and inventory,
  value-free self-digesting receipt/stdout, all input/output bindings, and source
  versus clean-installed equivalence.
- [x] 1.7 Reuse the hardened publisher fault matrix: pre/post-mkdir failures,
  escaped hardlinks, ambiguous rename, post-rename drift, parent fsync,
  Darwin extended ACL/API faults, descriptor close, wrapper interruption, stdout
  short write/flush/BrokenPipe, and interruption after a complete flush.
- [x] 1.8 Assert no network/model/database/legal/publication/filing side effect and
  that standalone `coding-reliability` remains available but cannot emit a native
  finalization receipt.

## 2. Runtime implementation

- [x] 2.1 Add closed resolution/finalization constants and pure strict builders for
  required-pair derivation, resolution validation, final coding, resolved decisions,
  generated adjudications, and the value-free receipt.
- [x] 2.2 Add exact revalidation of the native bundle plus Release15 import
  directory and both externally supplied digests using the existing bounded
  descriptor-held capture primitives.
- [x] 2.3 Run literal and normalized exact-text checks over every final main and
  alternative-ground quote, then invoke the authoritative reliability assessment
  over generated adjudications.
- [x] 2.4 Add the four-file no-replace private publisher by reusing the Release15
  transaction/recovery/confirmation states and Darwin ACL guard without destructive
  cleanup.
- [x] 2.5 Register `quality coding-audit-finalize`, its exact arguments, and the
  `0`/`2`/`3` mapping while keeping standalone reliability compatibility intact.

## 3. Schema and installed guidance

- [x] 3.1 Add closed schema definitions for resolution rows, resolved decisions,
  and the self-digesting value-free finalization receipt; document non-local
  bijection, digest, chronology, and exact-text runtime invariants.
- [x] 3.2 Add plain-Russian help and installed guidance with a copyable end-to-end
  prepare -> import -> resolve-if-needed -> finalize command sequence, exact output
  filenames, and external-anchor retention rules.
- [x] 3.3 Explain that pseudonyms/declarations are unauthenticated, locator review is
  declared only, code `0` is bounded technical closure, and standalone reliability
  is a non-native compatibility route.
- [x] 3.4 Mirror Release15 private-parent, Darwin ACL, no-destructive-cleanup,
  administrator quarantine, finalization uncertainty, and interrupted-confirmation
  recovery guidance for the four-file output.
- [x] 3.5 Update public CLI inventory and ensure installed references contain no
  links to excluded `tests/` or `evals/` trees.

## 4. Verification and release

- [x] 4.1 Run focused finalization, import, reliability, schema, source/install, and
  fault-injection tests on supported Python runtimes.
- [x] 4.2 Run strict skill validation, full skill tests, root release tests, privacy
  scans, and `openspec validate --all --strict --no-interactive`.
- [x] 4.3 Archive the OpenSpec change, commit atomically, push main plus the release
  branch, verify both remote SHAs, install from the published tree, and pass
  `--verify` plus `--verify-current`.
