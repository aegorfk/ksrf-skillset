## Context

The installed runtime already produces an ordinary frozen research workspace and
consumes a closed coding-reliability audit, but there is no first-party bridge
between those two contracts. Users currently invent audit candidate IDs, copy
approved coding fields, calculate hashes, and assemble the sampling plan by
hand. That work is deterministic and therefore belongs in the runtime; the
independent secondary legal judgment does not.

The producer crosses four trust boundaries: the frozen research plan, the full
screening frame, approved primary coding, and stored source text. A bundle is
useful only when all four agree exactly. The implementation must stay offline,
must not mutate the source workspace, and must never turn a generated template
into evidence of human review.

## Goals / Non-Goals

**Goals:**

- Provide one installed `quality coding-audit-prepare` command that converts a
  valid existing workspace into the exact first-party audit inputs.
- Give every screened chain/document pair a stable, content-described audit
  identity bound to the frozen plan.
- Revalidate projected primary coding against the uniquely identified stored
  full text before publishing anything.
- Publish a deterministic, manifest-bound bundle as one staged directory
  transition and refuse an existing destination.
- Make the independent-review queue usable without exposing primary substantive
  answers, while making every generated coding template visibly pending.
- Align schema annotations and guidance with the already implemented sampling
  rule: general and exclusion samples are independently ranked maxima and may
  overlap; required candidates are their set union.

**Non-Goals:**

- Performing secondary coding, adjudication, legal approval, complaint filing,
  or any network retrieval.
- Replacing the compatible expert path that supplies exact audit inputs
  manually.
- Changing the deterministic sampling algorithm or the reliability consumer's
  completion semantics.
- Repairing malformed workspaces, overwriting a prior bundle, or mutating
  ordinary screening/coding/source artifacts.

## Decisions

### One workspace-to-bundle command

The CLI will expose `quality coding-audit-prepare --workspace DIR
--sample-size N --exclusion-sample-size N --output-dir DIR`. It derives the
current plan hash from the latest frozen workspace plan rather than accepting a
caller-provided hash. This removes a common cross-workspace binding error while
leaving `quality coding-audit-plan` available for expert/manual inputs.

An alternative was a sequence of small projection/hash/template commands. It
was rejected because users could mix outputs from different workspace states
between steps.

### Candidate identity is derived from canonical legal identity

For each unique screening pair, the candidate ID is
`audit-candidate-sha256:<digest>`, where `digest` is the canonical SHA-256 of
the exact object `{schema_version, plan_sha256, chain_id, document_id}`.
`source_id` and row order are excluded: source storage can move and ordering is
not legal identity. The producer first verifies that the declared
`text_sha256` equals the SHA-256 of the store-normalized captured text and that
`document_id` is exactly `document-sha256:<text_sha256>`. The otherwise compact
candidate preimage is therefore content-bound. Including the frozen plan also
prevents accidental reuse across research frames.

The producer requires canonical non-empty `chain_id` and `document_id`, positive
integer `source_id` values, and exact current screening-record fields. Multiple
source rows for one chain/document pair collapse to one audit candidate only
when their captured full-text SHA-256 and recomputed matches are identical; the
audit row preserves their sorted source IDs. Conflicting duplicates,
omissions, extras, or a non-unique primary coding fail before output creation.
Identity and content hashes are checked for every captured document text before
screening relevance is considered, so a corrupt non-hit row cannot silently
change the denominator.

### Primary coding is projected, not copied wholesale

The producer copies only the authoritative 20-field audit coding contract and
injects the derived `candidate_id`. Ordinary operational fields are not carried
into the audit contract. A pre-existing candidate ID is accepted only when it
equals the derived value. The projected record must satisfy the exact audit
shape and `validate_coding_against_text` against the uniquely identified source
text. This prevents a structurally plausible quote or coding card from being
silently rebound to another document.

### Frozen plan is independently verified

The latest versioned plan must contain `frozen=true` and a lowercase SHA-256.
The producer removes only `frozen` and `plan_sha256`, runs the ordinary plan
validator on the remaining plan, and recomputes the digest with the same
canonical JSON algorithm used by `freeze_plan`. It does not trust a filename or
stored digest alone.

### Generated secondary material cannot satisfy the gate

The bundle contains a secondary-review queue with identity, source-text digest,
primary-record digest, codebook version, and state
`independent_secondary_required`; it contains no primary label, proposition,
quote, relation, remedy, or other substantive answer. The companion exact-field
coding templates populate only identity/codebook fields, use null or empty
substantive placeholders, set `human_review="pending"`, and set both review
Booleans false. They are intentionally invalid as completed audit coding and
must be independently completed and wrapped in the existing four-field audit
decision contract.

An alternative was to prefill the primary answer for reviewer convenience. It
was rejected because it weakens reviewer independence and makes accidental
self-agreement likely.

### Reliability inputs use strict JSON

The reliability consumer parses the audit plan and every primary, secondary,
and adjudication record as strict UTF-8 JSON. Duplicate object keys are rejected
recursively, and `NaN`/positive or negative infinity are rejected rather than
using Python's permissive JSON extensions. This prevents a human-visible first
value and machine-consumed last value from describing different audit evidence.
The existing accepted shapes remain unchanged: one object, an array of objects,
or JSONL where the corresponding option already allowed them.

JSON permits an escaped lone surrogate even though that value cannot be encoded
as canonical UTF-8. Such a record remains visible as invalid (`complete=false`)
instead of crashing the consumer. Valid evidence keeps the normal canonical
digest; only malformed diagnostic sorting/fingerprinting falls back to sorted,
compact `ensure_ascii=true` bytes, which can never satisfy a supplied evidence
hash or make the malformed record eligible.

### Bundle contents and hashes are deterministic

The output directory contains:

- `screening-candidates.audit.jsonl` — the closed audit screening frame;
- `primary-decisions.audit.jsonl` — exact projected primary records;
- `coding-audit-plan.json` — the existing frozen sampling-plan contract;
- `secondary-review-queue.jsonl` — non-substantive independent-review work;
- `secondary-coding-template.jsonl` — visibly pending exact-field templates;
- `coding-audit-inputs-manifest.json` — source and generated-file bindings.

Rows are sorted by candidate ID and JSON uses UTF-8, sorted keys, compact
separators, `ensure_ascii=false`, and `allow_nan=false`. The manifest binds the
raw source artifact hashes, a canonical candidate/source-text inventory, every
generated content file's path/byte-count/SHA-256, candidate IDs, and the plan
hash. Its own `manifest_sha256` is the canonical digest of the exact remaining
manifest fields; the manifest file is therefore not recursively listed in its
own files array.

### Publication uses a staged sibling directory

All reads, normalization, legal-text validation, and byte rendering happen
before publication. The command requires an existing real parent outside the
source workspace and an absent destination. It checks containment lexically and
by `samefile` identity across every existing destination-parent ancestor, so a
case alias on a case-insensitive filesystem cannot redirect output into the
workspace. It then creates a uniquely named sibling staging directory, writes
and re-reads every file there, and performs one
same-filesystem no-replace directory rename (`RENAME_EXCL` on Darwin,
`RENAME_NOREPLACE` on Linux, and the equivalent non-replacing rename on
Windows). It checks destination absence again immediately before the rename
and fails closed on a platform without an atomic no-replace primitive. On a
pre-publication failure it removes only the uniquely owned staging directory;
the workspace and requested destination stay unchanged.

This is preferred over creating the final directory first because consumers
must never observe a partly written bundle.

## Risks / Trade-offs

- [A source artifact changes while it is being read] -> Read each authoritative
  file as bytes once, parse only those bytes, bind the exact bytes/text
  inventory into the manifest, and compare a second capture before publication;
  mixed or changing inputs fail without a bundle.
- [A generated pending template is mistaken for completed review] -> Keep its
  exact-field shape intentionally invalid for completed coding, mark it pending
  in every row and in guidance, and regression-test that reliability rejects it.
- [General and exclusion samples overlap] -> Preserve the existing deterministic
  rule, state that configured counts are maxima, and define required candidates
  as the sorted set union rather than adding the lengths.
- [Directory rename portability] -> Stage in the destination parent so the final
  move remains on one filesystem; fail closed when the parent/destination shape
  is unsafe, aliases the workspace, or the destination appears before publication.
- [Strict projection rejects older ordinary cards] -> Report the offending
  chain/document identities and require users to complete ordinary coding; do
  not synthesize legal fields or loosen the audit contract.

## Migration Plan

1. Add failing unit and CLI tests for identity, exact projection, plan/source
   binding, pending-template rejection, sampling semantics, and atomic failure.
2. Add the pure producer builder and exact validators, then the staged CLI
   adapter and Russian help.
3. Add closed schema definitions and update installed reference guidance.
4. Run focused, full skill, root, schema, source/install parity, clean-install,
   and offline self-containment checks.
5. Archive the validated OpenSpec change, publish one atomic skillset commit,
   verify the remote SHA, and install that exact commit globally.

Rollback is the prior skillset commit. Existing manually prepared exact inputs
remain consumable throughout; bundles already produced remain audit artifacts
but must still pass the current consumer before use.

## Open Questions

None. Human completion and wrapping of secondary decisions, and human-authored
adjudication finalization, are intentionally candidates for later releases.
