## Why

The installed runtime validator can prove structural and self-containment checks without shipping `tests/` or `evals/`, but it does not expose a stable identity for the bytes it checked. A user also cannot ask whether those bytes equal the currently published skill payload without returning to a repository checkout. The current guidance therefore leaves a gap between “runtime passes” and “runtime content equals current public `main`”.

## What Changes

- Add a deterministic local runtime-tree identity to validation reports without exposing the source publish manifest.
- Add an explicit runtime-only `--check-updates` option which remains off by default and performs a bounded read-only comparison with the canonical GitHub `main` manifest pinned to one resolved commit.
- Report `current`, `different`, `unknown`, or `not_checked` without calling a different/custom payload “old” or treating a network failure as proof of freshness.
- Keep validation exit semantics, source/release QA, publication authority, legal review gates, and the installed payload exclusion of `tests/`, `evals/`, maintainer specifications, and source-only materials unchanged.

## Capabilities

### Modified Capabilities

- `ksrf-runtime-payload-boundary`: expose runtime content identity and an optional bounded freshness observation from the installed validator.

## Impact

- `skills/ksrf-complaint-cycle/scripts/validate_ksrf_skillset.py`: local identity, bounded canonical lookup, JSON and Russian human output.
- `skills/ksrf-complaint-cycle/tests/test_validate_ksrf_skillset.py`: offline-default, current/different/unknown, pinned-SHA and hostile-response coverage.
- `README.md` and owning skill guidance: one installed-runtime command and honest interpretation boundaries.
- No automatic update, installation, write, account creation, source-release approval, legal authority, or filing authority.
