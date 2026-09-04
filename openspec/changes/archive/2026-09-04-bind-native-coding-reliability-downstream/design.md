## Context

Release16 publishes a private four-file finalization directory. Two files form the
downstream evidence pair:

- `coding-reliability.json`, whose established contract is
  `coding_reliability` v1.1; and
- `coding-audit-finalization-receipt.json`, whose closed receipt binds the exact
  reliability file bytes and the complete native finalization state.

The finalizer also prints `receipt_sha256` after atomic publication and normal
confirmation. That out-of-band value is intentionally not recoverable as a trusted
anchor merely by reading the receipt's own `receipt_sha256` member. Current
uncertainty-profile, handoff, practice-analysis import, and complaint-sentence
binding paths nevertheless accept a complete reliability object without the
receipt or external expectation. They can therefore over-read a standalone manual
compatibility report as native closure.

The four claim-use consumers are deliberately independent:

1. `build_uncertainty_profile` and its CLI;
2. the portable handoff create/check/import path;
3. the standalone complaint-cycle v2 result validator; and
4. the complaint-cycle filing `practice_binding` validator.

The two complaint-cycle copies cannot import a sibling skill at runtime, so both
must implement and test the same closed verification semantics locally.

## Goals / Non-Goals

**Goals:**

- Make native reliability a verified relationship among an unchanged v1.1
  reliability artifact, a closed finalization receipt, and a separately supplied
  expected receipt digest.
- Carry that relationship through uncertainty output, portable handoff, trusted
  source material, result import, and sentence evidence binding.
- Preserve exact fail-closed behavior when any element, digest, candidate set, or
  audit-plan binding is missing or inconsistent.
- Preserve standalone reliability as readable compatibility diagnostics without
  allowing it to open a claim-use gate.
- Give holders of confirmed Release16 output a regeneration-only migration for
  downstream artifacts.
- Keep every new diagnostic value-free and every legal/human authority boundary
  explicit.

**Non-goals:**

- Change the `coding_reliability` v1.1 schema, algorithm, fields, digest recipe, or
  standalone command.
- Add `native=true` or any scalar that can be copied without verifying lineage.
- Authenticate finalizer stdout, a reviewer, authorship, independence, packet use,
  or occurrence of a declared human act.
- Revalidate source-workspace law/practice freshness, proposition truth, fact
  selection, locator meaning, legal correctness, temporal applicability,
  publication permission, approval, or filing readiness.
- Read a missing external expectation back from the receipt, silently upgrade old
  handoffs, or mutate historical artifacts.
- Add network, model, database, deletion, publication, or filing side effects.

## Decisions

### Native status is a relation, not a flag or reliability schema revision

One shared verifier consumes:

```text
coding-reliability.json
coding-audit-finalization-receipt.json
expected receipt_sha256 retained from successful finalizer stdout
```

It validates the established complete reliability contract, the exact closed
receipt fields and self-digest, equality of the receipt self-digest and the
separately supplied expected digest, and the receipt's byte binding to the
canonical reliability file. It also requires at least these cross-artifact
equalities:

- receipt `coding_reliability_file_sha256` equals SHA-256 of the exact canonical
  UTF-8 reliability JSON bytes with compact sorted keys, `ensure_ascii=false`,
  `allow_nan=false`, and exactly one trailing LF;
- receipt `audit_plan_sha256` equals reliability `audit_plan_sha256`;
- receipt `candidate_ids` equals reliability `required_candidate_ids` in exact
  canonical order;
- receipt and reliability each declare their existing exact complete/non-stale
  state; and
- where the consumer has a current plan, receipt `plan_sha256` equals that plan.

The verifier returns a bounded status/reason-code projection. It does not copy
substantive reliability diagnostics, coding values, quotations, coder/reviewer
labels, person-attributable times, or paths.

Alternative considered: add `native=true` to reliability. Rejected because a
caller could copy the Boolean and because changing v1.1 would break the explicitly
preserved compatibility contract. Alternative considered: infer native status from
the receipt alone. Rejected because that discards the out-of-band confirmation
anchor.

### Uncertainty profile receives the three inputs explicitly

`quality uncertainty-profile` retains `--coding-reliability` for compatibility and
adds paired receipt inputs:

```text
--coding-audit-finalization-receipt FILE
--expected-finalization-receipt-sha256 SHA256_FROM_SUCCESSFUL_STDOUT
```

The receipt option and expected digest are all-or-nothing and require a reliability
file. Supplying an incoherent pair, malformed artifact, or mismatched digest is an
input error. Supplying only reliability remains a valid compatibility-diagnostics
route, but the coding-reliability dimension is explicitly non-native,
`usable_for_claim=false`, and blocks `claim_use_ready`.

A verified triple makes only that dimension technically usable. The profile binds
the exact reliability artifact digest, full receipt-artifact digest, and the
origin expected receipt self-digest in its closed `input_sha256s`; it does not embed
input values. The receipt and expected-origin keys become required profile fields
for claim-use validation. Missing keys identify historical/compatibility output and
cannot be treated as an old accepted variant.

Alternative considered: make all three CLI options unconditionally required.
Rejected because the diagnostic profile remains useful before audit completion and
because standalone reliability is intentionally preserved as diagnostics. The
claim-use gate, not diagnostic construction, is the breaking boundary.

### The sixth quality binding carries an explicit external expectation

Reviewed handoff payloads require six quality types. The existing five keep their
closed three-field shape:

```json
{"quality_type":"...","artifact_sha256":"...","artifact":{}}
```

The new sixth type is the sole four-field variant:

```json
{
  "quality_type": "coding_audit_finalization_receipt",
  "artifact_sha256": "<canonical digest of the full receipt object>",
  "artifact": {},
  "expected_receipt_sha256": "<out-of-band finalizer stdout value>"
}
```

`expected_receipt_sha256` is deliberately distinct from `artifact_sha256`: the
former must equal the receipt's recomputed self-digest, while the latter binds the
full object including that member. All other binding types reject the fourth
field. A generic relaxed binding object is not introduced.

`handoff create` adds a separate
`--expected-finalization-receipt-sha256` argument. It may be used only with exactly
one detected finalization-receipt `--quality-binding`, and a reviewed result cannot
be created without both. The loader must not populate the expectation from the
receipt. It constructs the special four-field binding only from the explicit CLI
value.

Handoff validation then verifies the native triple and a three-way profile link:

- profile reliability input hash equals the reliability binding's artifact hash;
- profile receipt input hash equals the receipt binding's artifact hash; and
- profile origin expected digest equals the receipt binding's
  `expected_receipt_sha256`.

The receipt also binds the same current plan and candidate population used by the
reliability object. Rehashing an outer handoff after replacing any inner element is
therefore insufficient.

Alternative considered: use the ordinary three-field receipt binding and treat
`artifact.receipt_sha256` as the external value. Rejected because it turns the
external expectation into a self-declaration by the artifact being checked.

### Trusted-source material binds the complete special binding

The source workspace persists the exact reviewed payload and trusted result receipt
as before. Its payload digest already covers the special binding, including the
explicit expected digest. Trusted quality storage keeps the receipt artifact under
its content digest, while the trusted result receipt's closed reconstruction must
bind the complete quality-binding population rather than silently reducing the
special variant to its artifact hash.

`handoff check` and `handoff import` for reviewed results continue to require the
trusted source workspace. They independently validate the portable native triple,
then compare its content-bound special binding through the trusted result receipt
and trusted quality copy. A trusted-source match is evidence of source-workspace
continuity, not authentication of the external digest or human review.

### Both complaint-cycle consumers revalidate, not merely count, the sixth type

The practice-analysis importer and complaint-sentence evidence binder each require
the exact six-type population for claim-bearing v2 results. Each independently
checks:

- the special four-field receipt-binding shape and three-field exclusivity for all
  other types;
- reliability and receipt closed contracts and digests;
- the external expected receipt digest;
- receipt-to-reliability file, audit-plan, plan, and candidate bindings; and
- the uncertainty profile's three exact native-origin bindings.

The complaint-cycle `result import` command also requires its own
`--expected-finalization-receipt-sha256` input. This value is supplied at import
time, independently of the transported handoff, and must equal the special
binding's `expected_receipt_sha256` and the recomputed receipt self-digest. The
importer records it in the append-only `result_import` event and includes it in that
event's self-digest. `run attach` does not accept the value because attachment
precedes research and native finalization; moving the expectation there would
either require an unknowable future digest or encourage a mutable placeholder.

State derivation reopens the immutable result and selected import event and repeats
the equality among event expectation, special binding expectation, and receipt
self-digest before `eligible_for_drafting` or `ready` can survive. An idempotent
re-import must present the same external expectation as the existing event;
otherwise it fails rather than returning the previous event as a successful no-op.

A missing, duplicate, extra, malformed, compatibility-only, or cross-bound triple
prevents `drafting_ready`, `ready`, evidence-receipt creation, and every downstream
claim-use transition even if all outer hashes are recomputed. Historical files stay
readable in audit storage; they are not modified or silently promoted.

Duplicated local verification code is accepted here because installed skills are
independently runnable and complaint-cycle must not import the sibling skill.
Parity tests use identical positive and adversarial fixtures to prevent semantic
drift.

### Diagnostics remain bounded and value-free

New failures use a closed set of Russian user messages and stable machine-oriented
reason tokens such as missing triple, external digest mismatch, receipt self-digest
mismatch, reliability-file mismatch, candidate mismatch, plan mismatch, and
profile-origin mismatch. Diagnostics may show field names, counts, candidate IDs
already permitted by the value-free receipt, and SHA-256 values. They must not echo
the reliability/receipt payload, coding labels or selected values, quotes,
pseudonyms, human timestamps, or absolute paths.

Compatibility-only uncertainty output records only bounded reason codes and input
digests. A red gate is not presented as proof that the underlying legal analysis is
wrong; it means the required technical lineage is unavailable.

### Schema paths stay stable and contracts harden in place

Existing installed schema paths and top-level versions remain stable. The
practice-quality and workbench definitions gain the finalization receipt and
expanded uncertainty input bindings. Handoff and complaint-cycle quality bindings
become a discriminated union: exactly the one receipt type has
`expected_receipt_sha256`; every other type keeps the existing exact three fields.

This is intentional in-place hardening, not backward acceptance. Prior downstream
artifacts remain historical/audit-readable but do not satisfy current claim-use
validation.

## Risks / Trade-offs

- **[The expected digest is copied from the receipt]** → require a distinct CLI
  argument, never synthesize it in loaders, persist it in the special binding, and
  recheck it through trusted-source material.
- **[Outer rehash hides an inner substitution]** → independently recompute receipt,
  reliability, profile, candidate, and plan links at every consumer.
- **[Formatting changes break the receipt file hash]** → define and reuse the
  finalizer's canonical UTF-8 bytes with exactly one trailing LF; reject reformatted substitutes
  instead of guessing equivalence.
- **[Independent complaint consumers drift]** → use shared fixture vectors and
  parity tests while keeping each installed runtime self-contained.
- **[Old valid results suddenly fail]** → preserve audit readability and document a
  deterministic regeneration path; make the break occur only at claim-use gates.
- **[A valid triple is mistaken for human or legal authority]** → preserve all
  receipt false-limit flags, use technical-lineage language, and keep legal,
  freshness, publication, and filing decisions outside the contract.
- **[Diagnostics leak private review content]** → emit only bounded reason codes,
  permitted identifiers, counts, and digests; add hostile-value leak tests.
- **[Trusted source is over-described as authentication]** → describe it only as
  content continuity and retain the receipt's authentication/independence false
  flags.

## Migration Plan

1. Add failing contract tests for the native triple and verify that
   `coding_reliability` v1.1 remains byte/schema compatible.
2. Add the shared judicial-meaning verifier and wire the uncertainty profile to the
   explicit three-input path.
3. Add the sixth discriminated quality binding, paired handoff-create argument,
   trusted-source binding, and independent check/import validation.
4. Add the same fail-closed semantics to both complaint-cycle consumers and their
   schema, including the independent result-import argument, immutable event
   binding, and state recheck.
5. Update installed Russian guidance and run source/install parity plus full
   validation.
6. For existing Release16 output with a separately retained digest from a normal
   successful finalizer return, reuse the exact reliability/receipt files and that
   digest, then regenerate the uncertainty profile, handoff, imported result, and
   complaint evidence receipt.
7. If the external digest is absent, copied from the receipt, or came from an
   interrupted/uncertain confirmation, do not reconstruct it. Follow Release16
   recovery: repair the fault, rerun unchanged inputs into a new absent sibling,
   obtain normal successful stdout, and compare the complete outputs before using
   the new anchor.

Rollback may restore diagnostic construction behavior but must not reinterpret a
new or old unbound result as claim-usable. Historical artifacts remain immutable;
no destructive migration is required.

## Open Questions

None. The release intentionally fixes the sixth-binding shape, explicit CLI anchor,
three-way profile link, and compatibility boundary before runtime work begins.
