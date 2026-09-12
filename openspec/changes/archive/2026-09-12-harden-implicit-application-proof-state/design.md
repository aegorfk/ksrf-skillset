## Context

`classify_application` separates norm use from outcome causation. Wave eight
added a branch that keeps verified court-authored implicit norm use visible
when an independent ground defeats causal harm. Adversarial review showed that
the helper checked referenced full-act spans but omitted the premise-level
`inference_status` and record-level named approval. It could therefore emit a
reason code saying use was preserved from a contradicted or pending record.
The downstream filing gate still required a positive application status and a
trusted approval, so this was an overstatement rather than a filing bypass.

## Goals / Non-Goals

**Goals:**

- Make `implicit_norm_use_preserved` mean exactly what the classifier can
  establish: complete non-contradicted issue/logic evidence plus a diagnostic
  named-review marker, without calling that marker trusted approval of
  fingerprinted content.
- Preserve uncertainty and the independent-ground causation blocker as
  separate facts.
- Cover the negative proof states directly in executable tests.

**Non-Goals:**

- Treat an independent ground as evidence that the norm was or was not used.
- Replace the trusted host-attested approval required by the admissibility and
  release layers.
- Broaden the correction to direct application, norm-version or chain logic.

## Decisions

1. Split a *verified preservation* from an *unverified implicit-use candidate*.
   The existing positive helper will reject contradicted premises and require
   `HumanReview.is_named_approval` as a diagnostic marker. When
   `norm_use_status` still asserts a
   reasoning-linked implicit candidate but this proof is incomplete, the
   independent-ground branch will return `application_unclear` with
   `implicit_norm_use_not_verified`; it will not return `not_applied`.
   This is preferred to silently discarding the asserted norm-use axis.
2. Treat a contradicted premise as a missing/invalid conjunct in the ordinary
   implicit-proof branch. Even usable underlying spans cannot revive a
   premise-level contradiction.
3. Keep the existing two review layers distinct. The raw named-review marker is
   diagnostic and intentionally excluded from the canonical content
   fingerprint; the immutable trusted approval ledger is the only approval of
   exact fingerprinted content and remains necessary for admissibility and
   release.
4. Test both affirmative-non-application and generic independent-ground paths,
   because they call the same helper from different branches.
5. Normalize the affected OpenSpec SHALL bodies to one physical line and test
   `openspec show --json --deltas-only`, because OpenSpec 1.2.0 accepts wrapped
   bodies but exposes only the first physical line to machine consumers.
6. Treat a usable court/disposition `independent_ground` span as structured
   evidence that must agree with `outcome_causation`. Reject the record before
   classification when it does not, so the ordinary implicit branch cannot
   silently call an internally inconsistent record proven.
7. Mirror the duplicate-premise and independent-ground causation invariants in
   the Draft 2020-12 schema. Schema-only consumers must fail closed before the
   Python deserializer sees the artifact.
8. Apply the same nonblank-quote predicate to cross-instance incorporation and
   superseding-ground evidence in both chain assessment and binding. A locator
   proves where to inspect; it does not replace the quoted evidentiary content.
9. Keep classifier review and trusted approval separate in prose and runtime.
   A complete diagnostic marker permits the intermediate
   `implicitly_applied_proven` label; only the trusted ledger can authorize
   reliance on the fingerprinted record at admissibility or release.
10. Define a complete diagnostic marker as approved state, nonblank reviewer
    and a parseable timezone-aware RFC 3339 `reviewed_at`. Runtime treats an
    invalid value as unapproved; the standalone schema rejects a syntactically
    malformed shape and declares the standard `date-time` format.

## Risks / Trade-offs

- [Risk] Existing callers may have relied on a pending implicit record being
  called proven. → Keep the result and evidence auditable as
  `application_unclear`, add explicit reasons, and require callers to complete
  the already documented review step.
- [Risk] A raw named-review marker could be mistaken for approval. → Call it a
  diagnostic only, preserve the independent trusted-approval and causal-harm
  blockers, and state this in the reference and tests.
- [Risk] A contradicted premise may later be repaired. → Do not convert it to
  `not_applied`; return an uncertainty state that can be recomputed from a new
  immutable record.
- [Risk] Schema and runtime could reject different records. → Exercise both
  validators against duplicate-premise and both causal-axis conflict forms.
- [Risk] A located but empty chain span could retain an earlier positive result.
  → Require nonblank quoted content in assessment, integrity and positive-proof
  extraction, and cover both incorporation and superseding-ground paths.
- [Risk] An arbitrary nonempty review-time string could masquerade as a complete
  marker. → Validate RFC 3339 syntax and calendar/timezone semantics before any
  positive intermediate classification.

## Migration Plan

Publish a forward correction on top of the already verified wave-eight
release, regenerate the manifest against that exact parent, rerun focused and
full tests, archive this change, publish the closeout, and synchronize global
skills only from the final verified remote tree. Rollback is a normal revert;
no stored schema is migrated.

## Open Questions

None.
