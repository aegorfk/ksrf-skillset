## 1. Contract and Red Tests

- [x] 1.1 Validate the proposal, security design, and complete delta requirements for both affected capabilities.
- [x] 1.2 Add failing tests for REST `network_error` followed by exact Git ref success and immutable-SHA current/different comparison.
- [x] 1.3 Add failing tests for strict Git argv, executable search, environment, working directory, timeout, stdout cap, parser, cleanup, and bounded reason mapping.
- [x] 1.4 Add failing non-invocation tests for offline/default routes, hostile REST evidence, and immutable-manifest failures.

## 2. Runtime Validator

- [x] 2.1 Implement the isolated, fixed, non-interactive, time- and output-bounded Git ref resolver without target, source-tree, or temporary-file writes.
- [x] 2.2 Gate the fallback only on REST ref `network_error` and preserve the existing immutable manifest and post-network local identity checks.
- [x] 2.3 Preserve structured report shape, public wording, and all established exit-code meanings.

## 3. Verification and Review

- [x] 3.1 Run focused fallback tests and prove the intended red-to-green transition.
- [x] 3.2 Run full root and skill test suites, strict source/runtime validation, offline no-network/no-subprocess checks, shell syntax checks, and manifest self-containment checks.
- [x] 3.3 Run strict OpenSpec validation, `git diff --check`, skill quick validation, and independent security/spec review; resolve every material finding.

## 4. Atomic Publication and Installation

- [x] 4.1 Archive the validated OpenSpec change, synchronize both base specs, and re-run strict validation before release assembly.
- [x] 4.2 Rebase the complete release state directly onto the then-current canonical `main`, regenerate the manifest against that exact parent, and create one atomic release commit.
- [ ] 4.3 Push the feature ref, fast-forward canonical `main` once to the identical commit, and confirm the remote SHA plus publication guard.
- [ ] 4.4 Install the exact published runtime globally and verify offline and current-release behavior against the published SHA.
