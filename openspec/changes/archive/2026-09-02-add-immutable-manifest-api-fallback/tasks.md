## 1. Contract and Red Tests

- [x] 1.1 Validate the proposal, exact endpoint/header design, and complete delta requirements for both affected capabilities.
- [x] 1.2 Add failing tests for raw `network_error` followed by exact-SHA Contents raw-media success producing current and different outcomes.
- [x] 1.3 Add failing tests proving raw invalid, redirected, oversized, malformed, or schema-invalid evidence never invokes the fallback.
- [x] 1.4 Add failing tests for Contents URL/header/finality/cap/schema errors, one-attempt behavior, no ref retry, and unchanged offline/report/exit boundaries.

## 2. Runtime Validator

- [x] 2.1 Add request-specific fixed media/version headers without changing existing ref and primary raw request semantics.
- [x] 2.2 Implement the exact-SHA Contents fallback around only the primary raw read `network_error`, before shared manifest validation.
- [x] 2.3 Preserve immutable SHA pinning, strict identity validation, report shape, public wording, and exit-code meanings.

## 3. Verification and Review

- [x] 3.1 Run focused tests and prove the intended red-to-green transition.
- [x] 3.2 Run full root and skill suites, strict source/runtime validation, offline/self-containment/public-wrapper checks, shell syntax, and manifest checks.
- [x] 3.3 Run strict OpenSpec validation, `git diff --check`, skill quick validation, and independent security/spec review; resolve every material finding.

## 4. Atomic Publication and Installation

- [x] 4.1 Archive the validated OpenSpec change, synchronize both base specs, and re-run strict validation before release assembly.
- [x] 4.2 Rebase the complete release state directly onto the then-current canonical `main`, regenerate the manifest against that exact parent, and create one atomic release commit.
- [ ] 4.3 Push the feature ref, fast-forward canonical `main` once to the identical commit, and confirm the remote SHA plus publication guard.
- [ ] 4.4 Install the exact published runtime globally and verify offline and current-release behavior against the published SHA.
