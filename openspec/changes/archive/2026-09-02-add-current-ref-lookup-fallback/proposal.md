## Why

`--verify-current` currently depends on one GitHub REST ref request, so a transient API-path failure can turn an otherwise verifiable installed skillset into `unknown` even when canonical Git transport remains available. A narrowly bounded second ref-resolution route can improve user-facing reliability without weakening exact-commit or fail-closed verification.

## What Changes

- Keep the canonical GitHub REST ref lookup as the first way to resolve `refs/heads/main`.
- Only when that request fails with the bounded `network_error` class, resolve the same exact canonical ref with a non-interactive, time-bounded `git ls-remote` subprocess using fixed arguments and a hardened environment.
- Strictly parse one exact lowercase commit SHA for `refs/heads/main`, then continue using the existing immutable-SHA manifest request and identity comparison.
- Never invoke the fallback for malformed, oversized, redirected, schema-invalid, or otherwise hostile REST evidence; those cases remain `unknown`.
- Keep offline validation, status, installation, report shape, exit codes, and public wording unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-runtime-payload-boundary`: refine the explicit runtime freshness contract with a fail-closed REST-first ref-resolution fallback and preserve the offline boundary.
- `ksrf-skillset-install-status`: define the bounded subprocess boundary used only by explicit current-release verification.

## Impact

The repository-side runtime validator and its regression tests change. The public installer delegates to that validator unchanged. No new package dependency, network host, report field, installation behavior, or user-visible command is introduced; the optional fallback uses the existing local Git executable when available.
