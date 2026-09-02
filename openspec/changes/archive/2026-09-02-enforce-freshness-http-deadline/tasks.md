## 1. Contract and Red Tests

- [x] 1.1 Validate the subprocess boundary, fixed route protocol, deadline semantics, and full deltas for both affected requirements.
- [x] 1.2 Add failing tests using an injectable monotonic clock for deadline-before-spawn ordering, continuously ready/trickling output, exact-boundary wake and exit rejection, just-before-boundary success, process-group kill/reap after both timeout and completed leader, stdout cap, selector faults, and single closed handles.
- [x] 1.3 Add failing tests for exact isolated argv/environment/cwd/stdio, fixed route and SHA validation, child exit mapping, and absence of raw diagnostics.
- [x] 1.4 Add failing integration tests in which the parent process runner raises deadline `network_error` for REST to one Git fallback, raw to one same-SHA Contents fallback, terminal Contents, and no helper on offline/invalid scopes.

## 2. Runtime Validator

- [x] 2.1 Refactor the three existing HTTP requests into closed fixed-route specifications while preserving request and response validation.
- [x] 2.2 Add the isolated internal HTTP helper and parent-side hard execution/output boundary using the existing process runner.
- [x] 2.3 Preserve proxy isolation, system CA fallback, immutable coordinates, fallback eligibility, local identity recheck, report shape, public wording, and exit meanings.

## 3. Verification and Review

- [x] 3.1 Prove the focused red-to-green transition and real deadline cleanup without living descendants.
- [x] 3.2 Run full root and skill suites, strict source/runtime validation, clean-room install/offline/current checks, shell syntax, manifest, and self-containment checks.
- [x] 3.3 Run strict OpenSpec validation, `git diff --check`, quick skill validation, and independent security/spec review; resolve every material finding.

## 4. Atomic Publication and Installation

- [x] 4.1 Archive the validated OpenSpec change, synchronize both base specs, and re-run strict validation.
- [x] 4.2 Rebase the complete release state onto the then-current canonical `main`, regenerate the manifest against that exact parent, and create one atomic release commit.
- [x] 4.3 Push the feature ref, fast-forward canonical `main` once to the identical commit, and confirm remote SHA plus publication guard.
- [x] 4.4 Install the exact published runtime globally and verify offline and current-release behavior against the published SHA.
