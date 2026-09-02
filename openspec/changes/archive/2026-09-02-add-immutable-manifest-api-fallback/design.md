## Context

Current verification resolves one immutable canonical commit, then reads `skills-manifest.json` from `raw.githubusercontent.com/<sha>/...`. Both the REST-first/Git ref resolver and the manifest parser are strict and bounded. The remaining single-endpoint failure mode is transport availability of the raw host after a valid SHA is already known.

GitHub documents a Contents API route that can return raw file content at an explicit `ref`. The manifest is small JSON, so the existing parser and byte cap can validate raw-media bytes from that official route without trusting metadata, download URLs, or a mutable branch.

## Goals / Non-Goals

**Goals:**

- Preserve the raw immutable URL as the primary route.
- After only a bounded raw-route `network_error`, attempt exactly one official Contents API raw-media request at the same validated 40-hex SHA.
- Reuse strict URL finality, no-redirect, socket-operation timeout, byte-cap, duplicate-key JSON, schema, digest, and count validation.
- Preserve report fields, reason vocabulary, exit meanings, public wording, and the post-network local identity pass.
- Prove that hostile raw evidence, offline routes, and invalid CLI scopes cannot reach the fallback.

**Non-Goals:**

- Do not resolve `main` again, accept a branch name, follow a returned `download_url`, fetch repository archives, or use Git for file content.
- Do not retry `invalid_response` or `response_too_large` from the primary route.
- Do not add authentication, read tokens, inherit API credentials, cache evidence, or write files.
- Do not claim provenance, legal freshness, publication authority, or filing readiness.

## Decisions

### One reason-gated fallback inside immutable manifest retrieval

`_fetch_remote_runtime_identity(commit_sha)` will keep raw retrieval first. Its fallback boundary surrounds only that primary request and catches only `_FreshnessLookupError("network_error")`. It then calls the Contents API once. Validation of either returned payload remains shared and occurs after retrieval.

Placing the gate inside manifest retrieval prevents a content failure from re-running ref resolution. An unconditional dual request was rejected because it adds latency and rate-limit use. Retrying malformed or oversized evidence was rejected because it could turn an explicit security failure into an apparent success.

### Fixed official Contents URL and raw media negotiation

The fallback URL is exactly `https://api.github.com/repos/aegorfk/ksrf-skillset/contents/skills-manifest.json?ref=<validated-sha>`. The request sends `Accept: application/vnd.github.raw+json`, `X-GitHub-Api-Version: 2026-03-10`, and the existing fixed user agent, with no authorization, cookie, compression, or environment-derived header. Existing URL validation requires HTTPS, the exact host, default TLS port, no credentials or fragment, and byte-for-byte matching path and query after the response; redirects remain rejected.

The freshness opener installs an explicit empty proxy handler before HTTPS handling. This disables `urllib` ambient proxy discovery for the REST ref, raw manifest, and Contents routes, so `HTTPS_PROXY` or related environment variables cannot reroute freshness traffic or synthesize `Proxy-Authorization`. Direct HTTPS with the system trust store remains the only HTTP transport.

The SHA is already constrained to lowercase 40-hex before URL construction. A metadata response, HTML error, changed media behavior, wrong path/query, or non-200 status cannot satisfy the manifest schema. Returned `download_url` values are never read or followed.

For the two immutable-manifest requests only, transport/socket errors and HTTP `408`, `429`, or `5xx` are classified as retryable-availability `network_error`; other HTTP errors, redirects, missing/non-`200` status, and coordinate changes are terminal `invalid_response`. The older REST-ref HTTP classification remains unchanged so this content fallback does not silently alter ref-resolution eligibility. The HTTP timeout remains a per-socket-operation bound; a hard aggregate wall-clock deadline is intentionally deferred to a separate change.

### Shared bounded parser with explicit request headers

The internal JSON reader gains optional fixed `Accept` and API-version inputs while retaining existing defaults for REST ref and raw-host requests. It continues reading at most the configured manifest cap plus one byte and rejecting duplicate keys, invalid UTF-8, non-finite constants, invalid structure, or invalid identity counts/hashes.

A separate permissive HTTP client or Contents metadata/base64 decoder was rejected because it would duplicate security checks and add more accepted formats than the user-facing outcome needs.

### Stable external behavior

If the fallback succeeds, verification reports the same already-resolved remote SHA and content comparison as before. If it fails, the existing bounded reason code from that failure is reported. No route label is added to JSON or human output, and offline/default flows remain unable to call either manifest endpoint.

## Risks / Trade-offs

- [GitHub API rate limiting affects the fallback] → Invoke it only after a raw transport failure and keep failure as honest `unknown`.
- [The API ignores raw media negotiation] → Treat returned metadata as schema-invalid rather than decoding another format.
- [The branch advances between requests] → Both routes use the previously validated immutable SHA; no branch request is repeated.
- [A network middlebox redirects or rewrites the URL] → Reject final URL host/path/query differences and all redirects.
- [Two official endpoints fail together] → Return the existing bounded `unknown`; never infer absence or current content.

## Migration Plan

1. Add red tests for successful exact-SHA fallback and all non-fallback/error boundaries.
2. Add the fixed Contents URL/header route and reason gate with no external schema change.
3. Run focused, full, strict, self-containment, public-wrapper, manifest, OpenSpec, and independent security checks.
4. Archive/synchronize the change and publish one atomic release commit directly on the current canonical parent.
5. Install and verify the exact published runtime. Roll back by reverting the release commit and reinstalling its predecessor.

## Open Questions

None.
