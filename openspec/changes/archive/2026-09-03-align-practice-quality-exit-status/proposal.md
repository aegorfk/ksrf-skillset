## Why

Two filing-significant quality commands returned process code `0` even when their JSON said `complete=false`. The prefiling route also accepted caller-assembled treatment arrays and loosely shaped refresh plans, so omitted pending treatments, undeclared coverage gaps, weak identifiers, or ambiguous timestamps could escape an automated stop. Schema and portable-handoff validation did not independently enforce the complete producer-to-consumer evidence chain.

## What Changes

- Return `0` from `quality coding-reliability` and `quality prefiling-refresh` only for exact top-level Boolean `complete=true`; preserve code `2` for input/I/O errors and return `3` with the full report for a valid incomplete or stale assessment.
- Close the coding-audit plan, secondary-coding, and adjudication contracts; bind every record to the frozen candidate and content hashes, validate the authoritative coding record, and retain malformed, invisible-Unicode, missing-primary, or unresolved IDs in diagnostics. Document the exact manually prepared JSONL shapes and the canonical UTF-8 JSON SHA-256 recipe; this release does not claim a native audit-input producer.
- Require `cache refresh-plan` to consume a non-empty explicit `coverage-requirements` JSON/JSONL file. Keep only supported canonical dimensions, derive gaps only from declared scopes, and bind the closed plan by `plan_id`.
- Add `cache treatment quality-export`, which emits the complete treatment population with current corpus digest, sorted IDs, population SHA, cache-integrity diagnostics, content-bound items, and set SHA. Candidate and invalid resolved rows remain visible rather than being silently omitted.
- Distinguish immutable raw `review_decision` values `verified` and `rejected` from the effective export status `superseded`. A single replacement preserves the former review, introduces a pending candidate until its own review, and creates a fourth complete-population partition; branches, cycles, identity drift, and invalid chronology fail closed.
- Require canonical identifiers and strict RFC 3339 timestamps with seconds and a timezone where the quality contract depends on identity or chronology; a treatment `reviewed_at` before its immutable `created_at`, or any future review/check timestamp, cannot produce completion.
- Make prefiling accept only the full treatment-quality-set envelope from the public-cache producer, require the existing `--corpus-root` plus at least one unique canonical claim ID, regenerate both producer artifacts in one read-only SQLite snapshot, and verify corpus digest, treatment IDs, population SHA, set SHA, plan digest, coverage requirement digest, integrity state, four-part treatment classification, and gap subset before completion. Read-only verification fingerprints the SQLite file and checks its header and sidecars before and after the transaction.
- Bind corpus evidence to distinct `seed_id`/`snapshot_id` observation pairs: a new source binding is material, while metadata-only re-fetches of the same bytes by the same seed are not represented as new evidence.
- Bring `practice-quality.v1.json`, `case-relative-workbench.v1.json`, runtime checks, and portable handoff validation into parity with these closed contracts.
- Document the exact producer-to-consumer CLI workflow, exit semantics, legal boundary, and intentional in-place hardening of the v1 schema paths. Existing artifacts must be regenerated rather than patched by hand.

## Capabilities

### New Capabilities

- `ksrf-practice-quality-exit-status`: fail-closed process outcomes and complete content-bound evidence contracts for coding reliability and prefiling refresh.

### Modified Capabilities

- `ksrf-user-facing-cli`: make exit codes and the required public-cache producer workflow discoverable from the installed Russian CLI and skill references.

## Impact

- Quality assessment and validation in `analysis.py`, `practice_quality.py`, and `cli.py`.
- Public-cache refresh/treatment producers and evidence digest in `public_corpus.py`.
- Portable quality validation in `handoff_workbench.py`.
- Closed JSON contracts in `practice-quality.v1.json` and `case-relative-workbench.v1.json`.
- Installed launcher, references, source/install regressions, skill tests, and release manifest.
- Existing v1-path artifacts become historical/audit-only until regenerated with this runtime.
- No automatic network access, filing, publication, approval, deletion, or remediation is introduced.
