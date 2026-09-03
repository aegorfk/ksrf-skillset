## 1. Contract and RED regression

- [x] 1.1 Record exact long-option matching and recursive subparser coverage.
- [x] 1.2 Add a source and clean-installed RED reproduction for abbreviated
  `matter init` options that currently create files.
- [x] 1.3 Add recursive parser-inventory coverage and representative
  non-mutating abbreviation cases for every public parser family.
- [x] 1.4 Preserve exact-option execution, help, aliases, defaults, and output.
- [x] 1.5 Cover the legacy single-path validator's `--help` prefixes, including
  `--prefix=VALUE`, without changing unrelated dash-prefixed path behavior.

## 2. Minimal runtime fix

- [x] 2.1 Force `allow_abbrev=False` in each public runtime parser class.
- [x] 2.2 Ensure every nested subparser inherits the same invariant.
- [x] 2.3 Keep handler dispatch and all exact-token contracts unchanged.

## 3. Verification and review

- [x] 3.1 Prove the focused RED-to-GREEN transition and absence of side effects.
- [x] 3.2 Run full root and skill suites, OpenSpec, strict source/runtime,
  offline containment, quick skill checks, manifest, and clean-install checks.
- [x] 3.3 Obtain independent implementation, adversarial, and trust-boundary
  review; resolve every in-scope P1/P2.

## 4. Atomic publication and installation

- [x] 4.1 Archive the validated change and synchronize the base specifications.
- [x] 4.2 Regenerate the manifest and create one atomic release commit.
- [x] 4.3 Push the feature ref and `main` to the identical commit and confirm
  the live SHA.
- [x] 4.4 Install the exact published runtime globally and verify its identity.
