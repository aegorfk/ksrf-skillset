## Context

The runtime validator already enumerates every runtime-eligible file and hashes each file while excluding the same development and source-only surfaces as installation. The root release manifest exposes `tree_sha256` using a deterministic path/length/content algorithm. Runtime validation currently discards its internal manifest and cannot compare the installed bytes with canonical public `main`.

The check must remain source-independent and must not make ordinary validation depend on network availability. It must also avoid a time-of-check/time-of-use race between resolving `main` and reading its manifest.

## Goals

- Give every runtime report a deterministic identity for the exact runtime-eligible bytes observed.
- Let an installed user explicitly compare that identity with one immutable canonical `main` snapshot.
- Bound requests, response sizes, parsing, output, and timeout behavior.
- Preserve existing validator exit semantics and every source/runtime assurance boundary.

## Non-goals

- Proving which Git commit originally installed the local files.
- Calling every differing tree “outdated”; it may be older, custom, or locally modified.
- Automatically updating or writing any local file.
- Replacing source evals, release QA, publication verification, legal review, or filing authority.
- Treating GitHub availability or a remote manifest as an official legal source.

## Decisions

### 1. Reuse the release tree identity algorithm

After the portable manifest rows are sorted, the validator computes SHA-256 over the same sequence used by the root manifest: four-byte path length, POSIX path bytes, eight-byte content length, and file content. A second read verifies that size and per-file digest still match the rows already validated; a changed or unreadable file becomes a validation finding and no passing identity is emitted. The report exposes only algorithm, file count, byte count, and aggregate hash; runtime mode still exposes no standalone publish manifest or file inventory.

### 2. Network is explicit and pinned

Default validation performs no network call. `--check-updates` is accepted only with `--profile runtime` over the complete canonical 15-package allowlist; a partial package selection has no comparable remote tree and is rejected before network access. The check first resolves `refs/heads/main` through the fixed GitHub API endpoint, validates one lowercase 40-hex commit SHA, then fetches `skills-manifest.json` from the fixed raw-content host at that immutable SHA. Both responses use fixed byte caps, a short timeout, strict JSON/schema checks, and bounded reason codes. Redirects or final hosts outside the fixed GitHub allowlist are rejected.

### 3. Freshness is an observation, not provenance

The result is:

- `current`: local runtime tree hash equals the manifest tree hash at the resolved current `main` SHA;
- `different`: both identities are valid but differ;
- `unknown`: network, size, parsing, schema, pinning, or local-identity validation prevented comparison;
- `not_checked`: the caller did not request network access.

`current` means byte-equivalent runtime content, not proof that the local files were installed by that commit. `different` explicitly combines old, custom, and locally modified possibilities. `unknown` is a coverage gap and never becomes `current`.

### 4. Validation remains the primary exit contract

Freshness fields and human guidance do not change the existing 0/1/2 validation exit meanings. Callers that need policy enforcement consume the JSON freshness status explicitly. No warning is injected merely because optional network observation is unavailable, and `--strict` retains its existing validation meaning.

## Risks and mitigations

- **Remote branch moves between requests** → fetch the manifest by the resolved immutable commit SHA, not by `main`.
- **Oversized or malicious JSON** → fixed byte caps, strict shape/hash/count validation, bounded reason codes, no raw exception text in reports.
- **Local tree changes during validation** → recompute and cross-check every file against the already collected row before emitting an identity.
- **False “outdated” claim** → use `different`, explain older/custom/modified possibilities, and never infer chronology from unequal hashes.
- **Offline regression** → default no-network tests make any unsolicited opener call fail.
- **Assurance inflation** → retain `publish_manifest=null`, `source_release_eligible=false`, and explicit source/release/legal boundaries.

## Verification

- TDD tests for local parity with `skills-manifest.json`, no default network, immutable-SHA fetch, and every result state.
- Adversarial tests for oversized bodies, malformed/ref-confused JSON, wrong final host, non-hex SHA, manifest mismatch, timeout, and local file changes.
- Full root suite, all skill tests, source/runtime strict validation, offline self-containment, clean-room installation, and independent security/UX review before publication.
