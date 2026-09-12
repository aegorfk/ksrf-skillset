# Verification

## Corrective behavior

- Approved, pending, rejected, incomplete, contradicted and absent implicit-use candidates were exercised through both affirmative and generic independent-ground paths and through the ordinary conjunctive branch.
- A 96-state independent matrix over review state, premise inference and span inference produced `implicit_norm_use_preserved` only for the nine complete named-review/non-contradicted combinations; the other 87 stayed `implicit_norm_use_not_verified`, none became `not_applied`, and the two call paths had zero divergence.
- Seventeen adversarial schema/runtime cases covered duplicate premise order and both forms of independent-ground causal-axis conflict with zero classification mismatch.
- Blank or contradicted incorporation and later-ground spans no longer prove survival or supersession. Invalid RFC 3339 review timestamps do not unlock `implicitly_applied_proven` or `implicit_norm_use_preserved`.
- The raw named-review marker remains diagnostic and excluded from fingerprinted content approval. A separate trusted ledger is still required for admissibility and release.

## Automated checks

- Focused correction: `51 passed, 52 subtests passed`.
- Broader application/OpenSpec set: `89 passed, 85 subtests passed`.
- Full `ksrf-complaint-cycle` package: `466 passed, 590 subtests passed` in `90.38s`.
- Stable root unittest suite after manifest regeneration: `624 tests` passed in `474.824s`, with `11` expected skips and zero failures or errors.
- The first root run before regeneration had exactly four manifest-identity failures and no behavioral failure; all four passed in the final root run after binding the manifest to the published parent.
- All six wave-eight skill entry points passed the official `quick_validate.py` check.
- Strict source-profile validation passed `16/16`, with zero errors and zero warnings. Offline self-containment passed `16/16`.
- Strict OpenSpec validation passed `68/68`; active `--json --deltas-only` and post-archive base-spec projections expose the continuation-clause sentinels. `git diff --check` passed.
- A diagnostic repository-wide `pytest --collect-only` is not the repository's canonical gate and encountered ten import-path collisions in root tests. No `pytest-all` result is claimed; the documented root unittest suite and explicit package pytest suite are the release gates recorded above.

## Release identity and scope

- Live `main` was re-read before manifest generation and remained `004d446ffe7792815453ed6b9c0cc91d202cffae`; no force push is permitted.
- The generated manifest is bound to that exact parent and records `16` skills, `302` runtime files, `11,049,801` bytes and runtime tree SHA-256 `c200e0cd6b443212e578ae2244bc9a189287a30314b4014503648302a843c6d6`.
- Release tooling remains `13` files, `413,669` bytes, tree SHA-256 `4c0a0d80d56b4820eca5e3bc5ee7af6f9ad26be4ea0c4c5c4754a22ea3867c85`.
- The corrective runtime diff contains no book/author identity, PDF/local-source path, source URL or added network client. Private books, OCR and reconstructive extracts remain outside the public repository and are not needed at runtime.

These checks establish bounded classifier behavior, package integrity and self-containment only. They do not establish current Russian law, application or causation in a particular case, admissibility, complaint readiness, legal approval or authority to file.
