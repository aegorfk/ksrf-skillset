## 1. Contract tests

- [x] 1.1 Add RED tests for the `0`/`2`/`3` guide in both source and
  clean-installed doctor launchers.
- [x] 1.2 Cover `--help` and `-h`, supported legacy Python, stdout/stderr, and
  the legal-readiness/no-remediation boundaries.
- [x] 1.3 Extend the shared Russian-help inventory so both the nested and
  standalone doctor routes retain the guide.

## 2. Shared help implementation

- [x] 2.1 Add one Russian exit-status epilog to the shared doctor parser.
- [x] 2.2 Confirm commands, options, defaults, JSON, probes, process behavior,
  and other non-help routes remain unchanged.

## 3. Release verification

- [x] 3.1 Regenerate the manifest and run focused, full, strict source/runtime,
  offline-containment, and quick-validation gates.
- [x] 3.2 Obtain independent implementation and trust-boundary review.
- [x] 3.3 Archive and strictly validate the OpenSpec change, publish the exact
  commit to feature and live main, install it globally, and verify freshness.
