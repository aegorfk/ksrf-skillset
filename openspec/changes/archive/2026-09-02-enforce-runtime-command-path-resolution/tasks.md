## 1. Contract and RED baseline

- [x] 1.1 Freeze live SHA, manifest, exact 51-command/12-file inventory (49 runtime plus two README), eight CLI set and two HUDOC discovery surfaces.
- [x] 1.2 Record proposal, design, delta requirements, risks, preservation checks and publication plan before implementation.
- [x] 1.3 Strictly validate the OpenSpec change.
- [x] 1.4 Add failing command inventory, path-with-spaces installer, authority-link, portable validator and HUDOC resolver tests.

## 2. Deterministic runtime paths

- [x] 2.1 Replace all 51 user-facing bundled-script invocations with the canonical quoted root without changing command tails.
- [x] 2.2 Make installation print a shell-safe root export, make all eight documented CLIs clean-room probeable, and fix the authority-corpus companion route.
- [x] 2.3 Remove implicit HOME/cwd HUDOC discovery, preserve explicit overrides/worktrees/version gates, and document the external-engine boundary.
- [x] 2.4 Add shared command-path validation and offline parity, then regenerate the manifest.

## 3. Verification and publication

- [x] 3.1 Run focused RED/GREEN, full suites, source strict, clean-room installation with spaces, runtime strict, offline verification, OpenSpec strict, manifest and diff checks.
- [x] 3.2 Obtain independent documentation, resolver and release reviews with no unresolved P1/P2.
- [x] 3.3 Publish atomically to `main`, confirm live SHA, install and verify the exact global payload.
- [x] 3.4 Archive the completed OpenSpec change, regenerate the manifest from the merge SHA and publish the final evidence commit.
