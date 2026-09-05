## 1. Contract tests

- [x] 1.1 Add failing core tests for one exact externally anchored source bundle, two
  pairwise-distinct direct-sibling import directories, one held safe parent, exact
  seven/two/two-file inventories, `0700`/`0600`, owner/link/ACL rules, all established
  per-file/ZIP/JSON bounds, and all eleven unique input file inodes.
- [x] 1.2 Add failing verifier tests that preserve existing import-loader behavior,
  prove both imports use one shared bundle-bound layer, keep the uncertain receipt
  expectation absent, require the repeated external receipt digest, and compare both
  fixed raw files.
- [x] 1.3 Add failing report-schema tests for the exact root, four statuses, twenty-eight
  tri-state checks, twenty-six ordered closed reasons, exact fixed remediation, fixed negative
  scope, and rejection of every extra or input-derived value.
- [x] 1.4 Add failing CLI tests for the nested route, five required exact long options,
  Russian metavars/help, canonical stdout, empty handler stderr, parser boundary, and
  exact `0`/`3`/`2` precedence.
- [x] 1.5 Add hostile-value and TOCTOU tests for bundle/import/codebook and parent/leaf
  replacement, same/cross-parent directories, symlink/FIFO/device/subdirectory/extra
  entries, hardlinks/cross-input aliases, mode/owner/ACL drift, same-inode rewrite,
  final recapture changes, close uncertainty, and stdout interruption.
- [x] 1.6 Add availability and side-effect tests for file/list/ZIP/JSON bounds, linear
  validation, chunked full comparison, unchanged bytes/inventories, bytecode
  suppression, and prohibitions on mutation, temporary files, subprocesses, network,
  database, import, finalization, repair, quarantine, attachment, and promotion.

## 2. Shared verifier and safe comparison

- [x] 2.1 Before adding the new handler, factor the Release19 filesystem machinery
  into one profile-driven descriptor core for fixed path sets, byte limits, labels,
  invalid observations, leaf seals, raw directory comparison, and two-or-three-input
  held-parent binding. Keep the existing finalization-named entry points as thin
  compatibility wrappers so all Release19 behavior and patch-based tests remain
  unchanged.
- [x] 2.2 Factor the established native import consumer into a structured bundle-bound verifier
  and optional external-receipt-expectation layer; retain byte-identical behavior and
  errors for every existing `_load_native_coding_review_import` caller. Factor bundle
  validation into structured contract, external-manifest, and installed-codebook
  stages; do not classify failures by matching Russian exception text.
- [x] 2.3 Implement one descriptor-held capture for the bundle and two import siblings
  that reuses the established safe-parent, no-follow, private-mode, effective-owner,
  Darwin ACL, stable-identity, bounded-read, exact-inventory, and secure-codebook
  primitives.
- [x] 2.4 Validate the exact bundle with its external manifest expectation, both import
  receipt/decision pairs against that bundle, and only the repeated receipt against
  the external repeat expectation; compare both corresponding raw byte streams without
  inventing an expectation for the uncertain import.
- [x] 2.5 Fully recapture the bundle, both imports, and installed codebook through the
  retained identities, repeat the paired raw-byte comparison after recapture, and fail
  closed on every metadata, ACL, inventory, byte, path-binding, close, or capability
  uncertainty.
- [x] 2.6 Build the closed report projection with exact state/reason/check/remediation
  order, tri-state prerequisites, negative scope, and no serialization of paths,
  digests, identifiers, counts, contents, coordinates, exceptions, or environment.

## 3. Installed CLI schema and guidance

- [x] 3.1 Register `quality native-reliability compare-review-imports`, all five
  required options and Russian metavars, canonical one-line report output, and the
  exact process mapping without changing doctor, Release19 comparison, importer,
  finalizer, or downstream commands.
- [x] 3.2 Add `native_review_import_comparison_report` to the installed
  practice-quality schema additively and validate exact enums, tri-state checks,
  remediation objects, fixed scope, and `recovery_comparison_valid` equivalence. Keep
  the schema addition linear-size and compact; do not enumerate reason/remediation
  combinations or permutations that the deterministic builder already controls.
- [x] 3.3 Update installed `SKILL.md`, `references/practice-quality.md`, README, and CLI
  help with the five-input copyable route, both external-anchor origins, reason the
  source bundle is mandatory, eligible-vs-administrator recovery boundary,
  `0`/`3`/`2` meanings, no-side-effect boundary, and downstream legal gates.

## 4. Verification

- [x] 4.1 Run focused judicial-meaning core/schema/CLI tests plus existing import,
  finalization comparison, doctor, finalizer, downstream binding, exit-status,
  Russian-help, option-exactness, and runtime-path regressions.
- [x] 4.2 Run full source and supported-Python suites, strict skill/schema/privacy
  validators, and a clean external installation; prove byte-identical source/installed
  reports for all four states with unchanged directory snapshots and conflicting
  ambient `PYTHONPATH`.
- [x] 4.3 Obtain independent adversarial review of bundle-binding reuse, TOCTOU and
  side-effect boundaries, error precedence, value-free output, and legal/authority
  scope; resolve every P1/P2 before release.
- [x] 4.4 Run `openspec status --change add-native-review-import-comparison` and
  `openspec validate add-native-review-import-comparison --strict --no-interactive`;
  retain the change unarchived until every implementation task and independent review
  is complete.

## 5. Release integration

- [x] 5.1 Refresh `skills-manifest.json` and release identity only after runtime
  verification; prove the installed payload carries modified runtime/schema/guidance
  and still excludes tests, evals, OpenSpec, and source-only maintainer files.
- [x] 5.2 Synchronize validated delta specs, archive the OpenSpec change, create one
  atomic release commit, publish it, verify remote SHA equality, and install only from
  that verified checkout after all prior tasks and independent review pass.
