## 1. Contract tests

- [x] 1.1 Add failing core tests for two distinct direct-sibling seven-file packages,
  one held safe parent, exact inventory, owner/mode/link/ACL/device rules, fourteen
  unique file inodes, and all established file/JSON/JSONL/ZIP resource limits.
- [x] 1.2 Add failing verifier tests for independent package contracts, secure
  installed-codebook binding, no invented uncertain expectations, both repeated
  stdout anchors, and raw seven-file equality.
- [x] 1.3 Add failing report/schema tests for the exact root, four statuses, tri-state
  checks, fixed reason/remediation order, value-free output, and fixed negative scope.
- [x] 1.4 Add failing CLI/help tests for the exact nested route, four required long
  options, Russian metavars, parser boundary, canonical stdout, empty handler stderr,
  and exact `0`/`3`/`2` precedence.
- [x] 1.5 Add hostile input, TOCTOU, descriptor-close, stdout interruption, resource,
  and no-side-effect tests across both packages, parent/leaf bindings, and codebooks.

## 2. Safe comparison runtime

- [x] 2.1 Reuse the profile-driven descriptor core for the fixed seven-file package
  profile and add cross-package inode/device/topology checks without regressing the
  installed import/finalization comparators.
- [x] 2.2 Factor or add structured package evaluation that preserves the established
  native package loader contract and classifies independent contract, installed
  codebook, manifest anchor, and packet anchor checks without localized-message
  matching.
- [x] 2.3 Implement sequential bounded validation, chunked seven-file comparison,
  complete final recapture, codebook recapture, leaf/path/parent rebinding, and
  fail-closed close handling.
- [x] 2.4 Build the closed value-free report and exact status/reason/remediation/scope
  projection, then register `compare-audit-bundles` with no extra option surface.

## 3. Installed schema and guidance

- [x] 3.1 Extend the installed practice-quality schema additively for the exact report
  while keeping validation compact and linear.
- [x] 3.2 Update installed `SKILL.md`, `references/practice-quality.md`, README, and
  Russian CLI help with a copyable four-input route, both-anchor origin, eligibility
  boundary, side-effect limits, outcome meanings, and downstream revalidation gates.

## 4. Verification and release

- [x] 4.1 Run focused comparator/core/schema/help tests and all existing prepare,
  import/finalization comparator, diagnostic, doctor, option, and parity regressions.
- [x] 4.2 Run full supported-Python suites, strict skill/schema/privacy validators,
  OpenSpec strict validation, clean external installation, source/install behavioral
  parity for all four states, and bytecode/exclusion checks.
- [x] 4.3 Obtain independent adversarial review and resolve every P1/P2.
- [x] 4.4 Refresh the release manifest only after runtime verification, synchronize
  delta specs, archive the change, commit atomically, push, verify live remote SHA,
  and install only from that verified checkout.

## Verification evidence

- Full skill suites: 606 tests passed on Python 3.13 and Python 3.10. After widening
  only the report-delivery exception boundary, all 38 comparator tests passed again
  on both runtimes, including custom-stream errors and empty-stderr assertions.
- Root suite: 352 tests, two platform skips, with one stale-manifest error after the
  final runtime edit. Regenerating the manifest resolved it; all 10 publication-guard
  tests passed on the final candidate. The other root tests had passed.
- Final source/install parity passed all five handler cases, UTF-8 help, exact
  options, hostile PYTHONPATH, no writes, and runtime-only install exclusions.
- Strict source validation passed for 15/15 skills without errors or warnings;
  clean external installation and offline runtime verification passed.
- Reproduced and corrected codebook parent/leaf rebinding, compound state handling,
  and output-delivery error disclosure. Legacy CLI symbols were not removed;
  existing filesystem helpers gained only opt-in device checks.
- Independent final read-only review found no unresolved P1/P2 or release blocker.
  This is not an independent full-suite rerun and makes no claim about compromise
  before invocation or mutations after the final observation.
