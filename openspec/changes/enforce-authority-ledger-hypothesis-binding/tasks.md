# Tasks

## 1. Evidence and specification

- [x] 1.1 Confirm live base SHA and reproduce the deterministic cross-hypothesis RED.
- [x] 1.2 Define the scoped fail-closed contract and stop rule.
- [x] 1.3 Pass strict OpenSpec validation before implementation.

## 2. Test-driven implementation

- [x] 2.1 Add a failing test for an H1 block referencing an H2-only authority.
- [x] 2.2 Add positive coverage for a multi-hypothesis authority containing H1.
- [x] 2.3 Preserve authority hypothesis mappings and validate every block reference.
- [x] 2.4 Clarify the normative authority-ledger invariant.
- [x] 2.5 Regenerate the release manifest from the exact live base.

## 3. Verification and candidate publication

- [x] 3.1 Run focused tests, existing skill tests, root tests, strict package/full validators, and strict OpenSpec validation.
- [x] 3.2 Run offline self-containment and a clean-room install with exact hash comparison.
- [x] 3.3 Complete independent P1/P2 review.
- [x] 3.4 Commit atomically, publish only the feature branch, and confirm live branch SHA, unchanged main, and unchanged global skill.
