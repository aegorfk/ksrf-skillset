## Context

The quality layer already exposed a top-level `complete` signal, but both filing-significant CLI routes always exited successfully after rendering JSON. Coding reliability trusted several open or weakly bound records. Prefiling accepted a caller-provided iterable of treatments and a refresh object that did not prove declared coverage or the complete treatment population. That split allowed shell automation and portable handoff to over-read a syntactically valid but incomplete result.

The public corpus is the only component that can observe its complete treatment rows, immutable review history, indexed source text, and coverage state. Therefore it must produce the bounded inputs; the quality gate and handoff validator must consume and independently recheck them.

## Goals / Non-Goals

**Goals:**

- Align process success with exact Boolean completion while preserving actionable blocked reports.
- Make coding-reliability inputs closed, candidate-bound, content-bound, and independently reviewable.
- Require explicit, non-lossy coverage requirements and a complete treatment population.
- Bind refresh plan, treatment export, prefiling result, schemas, and handoff to the same current corpus state.
- Reject ambiguous identity and time representations at filing-significant boundaries.
- Keep the user-visible workflow executable from a clean-installed skillset.

**Non-Goals:**

- Claiming corpus completeness, correctness of a legal conclusion, legal approval, or authority to file.
- Starting network collection, repairing gaps, reviewing treatments, or mutating inputs automatically.
- Turning a disclosed coverage gap into absence of practice.
- Migrating historical artifacts by guessing or inserting hashes without primary data.
- Applying exit code `3` to unrelated informational commands.

## Decisions

1. Add a dedicated quality-gate renderer. It writes the same JSON as the existing renderer and then returns `0` only when `result.get("complete") is True`; every other valid assessment returns `3`. Exceptions handled by the CLI remain code `2` with stderr and no partial success artifact.

2. Apply the mapping only to `quality coding-reliability` and `quality prefiling-refresh`. Other quality commands keep their informational exit semantics.

3. Treat a coding audit as a closed evidence object. The plan has an exact field set and self-digest; screening and primary records are validated before sampling; secondary coding must satisfy the authoritative coding-record contract and name the outer candidate; adjudication can resolve only audited fields and must bind both coding hashes, a distinct canonical adjudicator, and a non-future aware RFC 3339 timestamp. Invalid, invisible-Unicode, missing-primary, and unresolved IDs remain in `invalid_*` and `unresolved_candidate_ids`. This release documents `audit-decisions.jsonl` and `adjudications.jsonl` as manually prepared contract-specific inputs, because no first-party producer exists yet. Every digest uses SHA-256 over UTF-8 JSON serialized with sorted keys, compact separators, `ensure_ascii=false`, and `allow_nan=false`; collection digests first sort records by their canonical digest.

4. Make coverage an explicit producer input. `cache refresh-plan` requires at least one object composed only of `court_id`, `period_id`, `enumerator_id`, and/or a supported `source_role`. Values must already use canonical whitespace and contain no control/format characters. The producer deduplicates and sorts requirements; every emitted gap repeats one declared scope and carries the fixed missing-observation reason and an action. A scope is observed only when every matching funnel-state row has a matching official role/URL at `full_text_extracted` or later with an intact snapshot, plus intact indexed text for `indexed` and later stages. A successful sibling cannot hide a blocked, early, discovery-only, or corrupt sibling in the same declared scope.

5. Bind refresh plans to treatment completeness. A plan records the current corpus evidence digest, all sorted treatment IDs, a population SHA over all treatment rows plus all review history, requirements, stale seed entries, and gaps. `plan_id` is the canonical digest of the unsigned plan.

6. Add one authoritative treatment producer: `cache treatment quality-export`. Its exact envelope contains `schema_version`, `export_type`, current corpus digest, population SHA, `integrity_issue_ids`, sorted IDs, one item per ID, and `set_sha256`. It exports unresolved or provenance-defective rows as candidate records with blockers instead of omitting them, and reports snapshot/index/foreign-key corruption at the envelope level. Its complete population has four disjoint effective partitions: candidate/pending, `verified`, `rejected`, and `superseded`.

7. Separate review meanings. A verified treatment requires a matching quote in indexed official full text bound to the candidate snapshot and source chain, a court speaker and locator, exact target-authority confirmation, structured target identity, reviewer, and immutable review history. A rejected treatment requires the same official full-text/chain review base and a canonical decision reason; quote, locator, and speaker may all be absent, but if a quote is supplied it must be a matching court quote with locator. A verified review cannot carry a rejection reason. The immutable raw `review_decision` remains `verified` or `rejected`; creating the sole allowed replacement changes only the prior row's effective exported status to `superseded`. The replacement must preserve source/target identity and remains pending until its own review. Branches, cycles, unresolved links, identity drift, and `reviewed_at < created_at` fail closed.

8. Accept only the exact quality-export envelope at prefiling and require `--corpus-root`. The CLI rejects a bare list, partial object, directory, missing file, foreign envelope, absent/malformed cache, invalid SQLite 3 header, or active `-wal`/`-shm`/`-journal` sidecar as code `2`. It opens the existing cache read-only, without schema creation or migration, records a static database fingerprint (device/inode, size, `mtime_ns`, and byte SHA-256), and regenerates the exact plan and treatment set inside one SQLite read snapshot. It checks the header, sidecars, and fingerprint again after the transaction so a TOCTOU change fails closed. The domain assessment compares live/caller corpus digest, treatment IDs, population SHA, set SHA and integrity diagnostics. A semantically stale/mismatched but structurally readable assessment remains visible with `complete=false` and code `3`.

9. Require at least one explicit `--claim-id`; values must be unique canonical identifiers. `subject_evidence_sha256` is a lowercase SHA-256. Filing-significant timestamps use the full RFC 3339 calendar date/full time with seconds and timezone. Every treatment review is not earlier than its immutable candidate `created_at`; the plan `as_of` equals `checked_through`; prefiling review is not earlier than the check; the check is not earlier than filing cutoff; future `as_of`, check, or review values cannot complete.

10. Validate the same closed prefiling artifact again at portable handoff. Handoff verifies the artifact digest, exact fields, requirements digest, gap-subset relation, matching corpus/population/set bindings, four disjoint treatment partitions whose union equals plan IDs, complete status, empty blockers, chronology, and the exact claim set.

11. Harden the existing v1 schema files in place. Their paths and top-level `schema_version: "1.0"` remain stable for installed callers, while changed input definitions carry explicit contract metadata where available. This is intentionally not backward acceptance: older audit, refresh, treatment, prefiling, and handoff artifacts must be regenerated from their authoritative producers.

12. Keep producer operations bounded and local. Refresh planning and quality export read the local public cache only; prefiling live verification is side-effect-free and rejects symlinked database/object-store components, content corruption, foreign-key violations, and static-store TOCTOU; a code `3` result never triggers network access, review, filing, publication, or implicit remediation.

13. Define the material observation boundary in the corpus digest. It includes the sorted distinct `seed_id`/`snapshot_id` binding set in addition to seeds and snapshots. A new seed-to-snapshot binding, including a binding to a seed with another role, changes the digest. Re-fetch metadata for an already represented pair (`fetched_at`, `content_type`, parser metadata) remains auditable but does not by itself claim new corpus evidence or change this digest.

## Risks / Trade-offs

- [Automation previously treated any rendered JSON as success] → Exit `3` is the intentional stop signal; preserve identical JSON on stdout and at `--output` for diagnosis.
- [A caller could omit a pending treatment] → Compare the complete producer IDs and population SHA in both plan and set, then require the classification union to cover every ID.
- [A caller could invent a gap or weaken requested coverage] → Require explicit requirements and accept only gaps whose exact scope is a member of that set.
- [The cache changes between producer calls] → Corpus/population bindings differ and prefiling fails closed; regenerate both artifacts from one stable state.
- [The SQLite file changes during a nominally read-only check] → Compare header, sidecars, and the static file fingerprint before and after the read transaction and reject the TOCTOU result.
- [A resolved database row lacks trustworthy provenance] → Export it as candidate with blockers, retaining visibility without promoting it.
- [A replacement could silently erase a prior reviewed decision] → Preserve raw review history, expose the prior row as `superseded`, retain the replacement as pending until separately reviewed, and reject branches/cycles/identity drift.
- [Repeated retrieval metadata could look like new evidence] → Digest distinct seed/snapshot bindings rather than observation events; a genuinely new source binding remains material.
- [Strict time/identifier rules reject formerly tolerated values] → Report the precise invalid/incomplete condition and document canonical RFC 3339 inputs.
- [In-place v1 hardening surprises stored-artifact users] → Preserve stable installed paths, state the incompatibility explicitly, and provide a deterministic regeneration order.
- [Code zero is mistaken for legal authority] → Repeat in CLI help, references, schema semantics, and handoff documentation that completion is bounded and filing remains a separate human gate.

## Migration Plan

1. Publish and install the manifest-bound skillset release.
2. Regenerate coding audit and reliability artifacts when used.
3. From one unchanged current public-cache state, run `cache treatment quality-export` and `cache refresh-plan --coverage-requirements ...`.
4. Re-run `quality prefiling-refresh` with every affected claim ID and the current workspace evidence SHA.
5. Rebuild reviewed handoff and trust receipts so they bind the new quality artifact hash.
6. Treat prior v1-path artifacts as historical/audit-readable only; do not copy fields or hashes into them manually.

Rollback is the previous manifest-bound commit. Rollback restores the previous runtime but does not make newly generated artifacts authoritative under that older contract.

## Open Questions

None.
