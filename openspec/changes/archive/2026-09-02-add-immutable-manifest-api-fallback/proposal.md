## Why

Explicit current-release verification can now survive a transient GitHub ref-API failure, but it still becomes `unknown` whenever the single `raw.githubusercontent.com` manifest route is temporarily unavailable. GitHub's official Contents API can provide the same manifest bytes at the already resolved immutable SHA, improving verification availability without broadening what evidence may count as current.

## What Changes

- Keep the immutable raw manifest URL as the primary content route.
- Only when that request fails with bounded `network_error`, request `skills-manifest.json` once through GitHub's official Contents API raw media type with the same exact commit SHA.
- Apply the existing host, path, query, redirect, timeout, byte-cap, JSON, schema, digest, and count checks to the fallback evidence.
- Never invoke the fallback for malformed, redirected, oversized, or otherwise hostile raw evidence; never resolve the branch again.
- Keep offline validation, subprocess behavior, report shape, exit codes, public wording, and installation behavior unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-runtime-payload-boundary`: refine immutable-manifest retrieval with one exact-SHA, fail-closed official API fallback.
- `ksrf-skillset-install-status`: define the additional bounded network route used only by explicit current-release verification.

## Impact

The repository-side runtime validator and its regression tests change. The public installer delegates unchanged. No new command, package dependency, host owner, mutable ref lookup, report field, installation content class, or authority claim is introduced.
