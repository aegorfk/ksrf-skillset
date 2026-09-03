## 1. Contract tests

- [x] 1.1 Add source/install CLI tests for `0` on exact `complete=true`, `3` on valid incomplete/stale results, and `2` on invalid input or output I/O.
- [x] 1.2 Prove that code `3` preserves identical full JSON on stdout and at `--output` without implicit network, filing, approval, or remediation side effects.
- [x] 1.3 Cover missing/non-file record paths, malformed digests, required unique canonical claim IDs, reduced timestamps, future timestamps, and exact-Boolean fail-closed behavior.
- [x] 1.4 Cover closed coding plan/record/adjudication contracts, candidate identity mismatch, stale primary hashes, same reviewer aliases, unresolved disagreement, and false-exclusion adjudication.
- [x] 1.5 Cover explicit coverage requirements, undeclared/malformed gaps, closed refresh-plan digests, and producer-to-consumer refresh behavior.
- [x] 1.6 Cover full treatment population export, candidate retention, verified/rejected provenance, corpus/population/set mismatches, and source/install end-to-end prefiling.
- [x] 1.7 Cover schema/runtime parity and portable-handoff revalidation of the complete prefiling contract.
- [x] 1.8 Cover a successful and blocked sibling in one coverage scope, corrupt live-cache content, invisible Unicode identifiers/content, and a screening candidate missing its primary coding.
- [x] 1.9 Cover the complete supersession lifecycle, rejected/duplicate replacement branches, cycles and source/target drift, plus treatment `reviewed_at >= created_at` in producer, consumer, and installed routes.
- [x] 1.10 Cover read-only SQLite header/sidecar/static-fingerprint TOCTOU and the evidence-digest distinction between a new seed/snapshot binding and metadata-only re-fetch of an existing pair.

## 2. Runtime implementation

- [x] 2.1 Add a dedicated quality-gate result mapper and route only coding-reliability and prefiling-refresh through it.
- [x] 2.2 Close and hash-bind coding audit plans, secondary coding, adjudications, and reliability output; preserve invalid/unresolved diagnostics.
- [x] 2.3 Require explicit canonical coverage requirements and emit a closed refresh plan whose gaps are a subset of declared scopes.
- [x] 2.4 Include all treatment rows and review history in corpus/population evidence and add the complete `cache treatment quality-export` envelope.
- [x] 2.5 Enforce distinct content-bound verified/rejected review contracts, canonical identifiers, strict aware RFC 3339 timestamps, and no-future review/refresh times.
- [x] 2.6 Require the complete treatment envelope, current corpus/population/set bindings, subject evidence digest, and explicit unique claim IDs at prefiling.
- [x] 2.7 Recheck exact fields, digests, coverage, treatment completeness, chronology, and claims in the portable handoff runtime.
- [x] 2.8 Preserve immutable verified/rejected `review_decision`, derive effective `superseded` status for the unique predecessor, expose four disjoint population partitions, and fail closed on replacement branch/cycle/identity/chronology defects.
- [x] 2.9 Bind evidence digest to distinct seed/snapshot pairs and guard read-only live regeneration with SQLite header, sidecar, and static-file fingerprint checks before and after the transaction.

## 3. Schemas and installed guidance

- [x] 3.1 Close the changed input/output definitions in `practice-quality.v1.json` and mirror the complete prefiling contract in `case-relative-workbench.v1.json`.
- [x] 3.2 Explain exit `0`/`2`/`3` in Russian help for both quality gates.
- [x] 3.3 Document the exact coverage → treatment export → refresh plan → prefiling workflow and verified/rejected treatment requirements.
- [x] 3.4 Document handoff parity and the intentional in-place v1 hardening with mandatory regeneration of prior artifacts.
- [x] 3.5 Document the exact manual audit JSONL shapes and canonical SHA-256 recipe, supersession semantics, treatment chronology, static SQLite checks, and material observation-binding boundary.

## 4. Release verification and publication

- [x] 4.1 Regenerate the manifest and run focused, full, strict source/runtime, schema, offline-containment, and quick-validation gates.
- [x] 4.2 Obtain independent implementation, specification-honesty, and trust-boundary review; resolve all material findings.
- [x] 4.3 Archive and strictly validate OpenSpec.
- [x] 4.4 Commit atomically, publish the exact commit to feature and live main, verify remote SHA equality, install globally, and verify installed freshness and source/install parity.
