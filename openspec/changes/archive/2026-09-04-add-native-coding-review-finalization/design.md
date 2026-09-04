## Context

Release15 closes the transport and import boundary for independent secondary
coding. Its receipt contains two complete, value-free difference maps:

- eight audited reliability fields; and
- four substantive fields deliberately outside the reliability metric.

The release correctly stops there. Audited differences still need adjudications;
non-audited differences need a separate human content review; and a changed
`alternative_grounds` value needs a fresh packet-text check. The standalone
`coding-reliability` command accepts the resulting records but neither reads the
native receipt nor the exact packet. Consequently its `complete=true` cannot close
those three obligations.

This change adds the missing native closure step. It remains an offline artifact
validator and deterministic producer, not a reviewer portal, identity provider,
legal judge, or filing gate.

## Goals / Non-Goals

**Goals:**

- Bind finalization to two separately retained anchors: the prepare manifest digest
  and the Release15 import-receipt digest.
- Require exact coverage of every pair in both imported difference maps.
- Derive final values from explicit primary/secondary/custom choices instead of
  trusting a caller-supplied final coding record.
- Revalidate every final main and alternative-ground quote against the exact
  candidate packet text.
- Generate compatible adjudications and independently rederive coding reliability.
- Publish a deterministic, private four-file output and a value-free receipt whose
  successful digest is safe to retain out of band.
- Keep incomplete review actionable through code `3` without manufacturing a
  closure artifact.

**Non-goals:**

- Authenticate a reviewer, pseudonym, time of review, independent work, packet use,
  or the truth of a declaration.
- Machine-verify quote locators, legal propositions, material-fact selection,
  reasoning adequacy, norm temporal applicability, or legal correctness.
- Change the reliability metric, silently upgrade legacy/manual artifacts, or call
  a hand-built reliability report native.
- Expose packet text or substantive coding values in a receipt or diagnostic.
- Perform network access, model calls, database writes, publication, filing, or
  legal approval.

## Decisions

### One command closes both difference classes

The native route is deliberately one transaction:

```text
quality coding-audit-finalize \
  --bundle CUSTODIAN_BUNDLE \
  --expected-manifest-sha256 SHA256_FROM_PREPARE_STDOUT \
  --audit-import IMPORT_DIRECTORY \
  --expected-import-receipt-sha256 SHA256_FROM_IMPORT_STDOUT \
  [--resolutions COMPLETED_RESOLUTIONS_JSONL] \
  --output-dir NEW_SIBLING_DIRECTORY
```

`--bundle`, `--audit-import`, and `--output-dir` must resolve to three distinct
entries under the same actual parent directory held by descriptor. The first two
must be exact existing native artifacts; the output must be absent. The parent must
belong to the effective user, deny group/other writes, and satisfy the inherited
Darwin extended-ACL rule.

When required, `--resolutions` must be a regular sibling file under that same held
parent, owned by the effective user, mode `0600`, with exactly one hardlink and no
Darwin extended ACL. It is recaptured by name through the held parent immediately
before publication. This file can contain private quotes, facts, reviewer labels,
and person-attributable time, so accepting a normal `0644` editor output would
break the private workflow even though the final directory itself is protected.

A single finalizer avoids two independently mutable closure notes and one ambiguous
ordering question. It resolves both maps first, rebuilds the final coding once,
checks its quotes once, derives adjudications once, and runs reliability over that
same captured state.

### Both native ancestors are fully revalidated

The finalizer accepts only a supported native `1.1` or `1.2` custodian bundle and
the exact two-file Release15 import directory. It performs the same bounded,
descriptor-relative, no-follow verification used by the importer: closed
inventories, regular single-link files, exact modes where required, strict UTF-8
JSON/JSONL with duplicate-key and non-finite rejection, stable identities and bytes,
closed self-digests, deterministic packet rebuild, candidate/codebook/brief/plan
bindings, and exact import decision population.

The operator-supplied parent-manifest digest must equal the verified manifest's
self-digest, and the operator-supplied import-receipt digest must equal the verified
receipt's self-digest. The import receipt must in turn bind the same bundle,
manifest, packet, plan, candidate population, and exact `audit-decisions.jsonl`.
Neither expectation may be rediscovered from the artifact being checked. Internal
self-consistency is not authentication.

All input resources are bounded before parse. Any path, inventory, byte, metadata,
codebook, or parent identity change between initial capture and prepublication
recheck blocks output.

### Resolution rows are pre-bound and bijective

The required resolution population is the union of every `(candidate_id, field)`
pair in `audited_field_differences` and
`non_audited_content_differences`. The two field classes remain disjoint and retain
their published contract order. One strict resolution row covers one candidate and
has this closed logical shape:

```json
{
  "schema_version": "1.0",
  "import_receipt_sha256": "<lowercase sha256>",
  "candidate_id": "<exact candidate id>",
  "difference_fields": ["<exact complete ordered field set>"],
  "primary_coding_sha256": "<exact imported binding>",
  "secondary_coding_sha256": "<exact imported binding>",
  "field_resolutions": [
    {"field": "<field>", "choice": "primary"},
    {"field": "<field>", "choice": "secondary"},
    {"field": "<field>", "choice": "custom", "value": "<typed value>"}
  ],
  "reviewer_pseudonym": "<canonical pseudonym>",
  "reviewed_at": "<RFC 3339 seconds and timezone>",
  "human_review": "approved",
  "full_text_reviewed": true,
  "quote_locators_reviewed": true,
  "final_coding_approved": true
}
```

The three displayed `field_resolutions` are alternatives, not a requirement to use
each choice. A `primary` or `secondary` object has exactly `field` and `choice`; a
`custom` object additionally has exactly `value`. `value` must satisfy the same
field-specific type/domain contract as an authoritative completed coding record.

Rows may arrive in any order, but there must be exactly one per candidate in the
union. `difference_fields` must equal that candidate's complete ordered field set
from both receipt maps, and `field_resolutions` must be a one-to-one list in the
same order. Missing candidate/field pairs are incomplete; extras, duplicates,
changed field classes, wrong hashes, cross-candidate bindings, unknown choices, or
wrong variant shapes are invalid. The reviewer pseudonym must be canonical and
must differ under the existing normalization/case-folding rule from both coder
labels for that candidate. `reviewed_at` is a non-future aware RFC 3339 timestamp
with seconds.

If both difference maps are empty, `--resolutions` is unnecessary and must be
omitted; agreement is closed directly from the imported records. If either map is
non-empty and the option is omitted, or a structurally readable resolution file
does not yet cover every required pair, the result is valid but incomplete and
returns code `3` without publishing a finalization directory. An unparseable,
ambiguous, extra, duplicated, wrongly bound, or schema-invalid row is code `2`.

The pseudonym and completion fields are user declarations. The runtime checks their
shape, distinction, exact values, and chronology only. It does not authenticate a
person, authorship, independence, packet use, or occurrence of the declared act.

### Final coding is derived, never accepted whole

For every imported candidate the finalizer starts from the exact primary record.
For each of the twelve comparison fields it requires either imported equality or
the resolution choice mandated by the corresponding difference map. A `primary`
choice copies the exact primary value; a `secondary` choice copies the exact nested
secondary value; and a `custom` choice uses only the typed value carried by the
bound field-resolution variant. No caller-supplied whole final record is trusted.

For a candidate with differences, the final composite coding records the resolver
pseudonym as its declared `coder` and fixes the authoritative completion-state
fields to their required completed values; its remaining identity, codebook, and
document bindings come from the exact imported pair. For a candidate with no
differences, the primary completed record is the final coding. The resulting object
must satisfy the authoritative closed 20-field coding contract. This derivation
does not imply that inherited or selected values are legally correct.

Every final main `quote` and every quote inside final `alternative_grounds` must be
found as an exact literal substring of the exact packet text for that candidate.
The whole final coding must also pass the existing normalized quote-presence and
record/text validator. These are presence/structure checks only. A locator is
schema-checked and human-declared as reviewed but is not mechanically tied to text;
the receipt therefore fixes `quote_locator_verified=false` and may separately state
`quote_locator_review_declared=true` only when every required declaration exists.

`resolved-review-decisions.jsonl` contains one canonical row per required candidate
in frozen candidate order. Each row binds the import receipt and original coding
hashes, records the value-free field/choice provenance, embeds the derived final
coding, and carries its canonical SHA-256. The output is explicitly a composite
resolution record, not an authenticated new act of the named pseudonym.

### Adjudications and reliability are generated from the same state

For every candidate with audited-field differences, the finalizer emits exactly
one existing-contract adjudication whose `resolved_fields` contains all and only
that candidate's audited differing fields, using the values in the derived final
coding. It binds the exact primary and secondary hashes, resolver pseudonym,
`reviewed_at`, and declared approved review. Candidates with only non-audited
differences do not receive an empty or invented adjudication.

The finalizer then invokes the authoritative pure reliability assessment with the
exact bundle plan and primary coding, exact imported audit decisions, and generated
adjudications. `coding-reliability.json` is the exact report. Native code `0`
requires its exact Boolean `complete=true`, full resolution-map bijection, valid
final coding population, and all exact quote-presence checks. A structurally valid
assessment that remains incomplete or unresolved returns code `3` and does not
publish a closure directory.

The standalone `quality coding-reliability` interface remains available for exact
expert/manual inputs. Its report remains non-native compatibility evidence because
it does not consume or validate a finalization receipt. Downstream guidance may
claim native closure only from the finalizer's receipt plus its externally retained
receipt digest.

### The published receipt is closed, self-digesting, and value-free

Successful publication contains exactly four files:

1. `resolved-review-decisions.jsonl`;
2. `adjudications.jsonl` (canonically empty when no audited difference exists);
3. `coding-reliability.json`; and
4. `coding-audit-finalization-receipt.json`.

The receipt binds the supplied expected digests; exact verified manifest, packet,
plan, import receipt, and audit-decision bytes; optional resolution-file bytes or
the canonical no-resolution state; all three sibling output bytes; required
candidate and difference-pair populations; resolved candidate/field populations;
and canonical final-coding collection digest. Its own digest is SHA-256 over the
closed unsigned object using sorted keys, compact separators, UTF-8,
`ensure_ascii=false`, `allow_nan=false`, and no trailing newline.

The receipt and success stdout contain only schema/producer identifiers, counts,
candidate IDs, field names, hashes, Boolean proof limits, and next-step status. They
do not repeat packet text, quotes, propositions, facts, selected/custom values,
coder or reviewer labels, timestamps attributable to a person, or absolute input
paths. Among its fixed limits are:

- `difference_resolution_bijection_verified=true`;
- `final_quote_literal_presence_verified=true`;
- `final_quote_normalized_presence_verified=true`;
- `quote_locator_review_declared=true` when resolution rows were required, while
  `quote_locator_verified=false` always;
- `reliability_complete=true`;
- `source_workspace_reverified=false`;
- `reviewer_identity_authenticated=false`;
- `human_review_authenticated=false`;
- `independence_verified=false`;
- `receipt_authenticated=false`;
- `norm_edition_temporal_applicability_verified=false`;
- `publication_safe=false`; and
- `legal_readiness=false`.

Code `0` means that these bounded technical checks and the atomic publication
completed. It does not establish freshness of law/practice, legal approval,
publication permission, or filing authority.

### Publication inherits the hardened Release15 transaction

The finalizer reuses, rather than weakens or forks, the Release15 secure capture and
publication contract. It uses descriptor-relative `O_NOFOLLOW`/nonblocking bounded
reads, stable regular single-link identity checks, a held effective-user-owned
parent, absent sibling output, private staging, mode `0700` directories and `0600`
files, retained file descriptors/inode identities, complete effective-owner checks
for staging/published directories and every output file, fsync of
files/directory/parent, and an atomic no-replace directory rename. On Darwin, every
required parent, resolution input, staging, file, and final descriptor must prove
absence of every extended ACL; ACL API or identity instability fails closed, and no
Linux ACL inspection is claimed.

Before staging `mkdir`, code `2` validation/I/O failure produces no output object.
After `mkdir`, failures preserve every possible temporary or published inode and
perform no automatic unlink or directory removal. Ambiguous rename, pre- and
post-rename drift, hardlink escape, parent-fsync uncertainty, descriptor-close
failure, wrapper interruption, and stdout write/flush/interruption through normal
return use the same Release15 cleanup-, state-, durability-, finalization-, and
confirmation-uncertain classifications. Diagnostics remain value-free and include
the held parent/staging/published/file inode coordinates needed for
administrator-only all-link accounting and quarantine.

Recovery never retries the same destination. After the underlying channel or
filesystem is repaired, the operator uses unchanged inputs and a new absent sibling,
obtains one complete successful confirmation and normal return, and byte-compares
both four-file outputs before trusting the repeat receipt digest. Apparently
complete stdout from an interrupted confirmation is invalid.

## Risks / Trade-offs

- [One resolution file could be hand-edited after review] -> Bind every row to both
  external ancestors and re-read its exact bytes immediately before publication;
  disclose that hashes do not authenticate a person.
- [A partial file could be mistaken for "no differences"] -> Derive the required
  pair set only from the verified receipt and require full bijection; reserve omitted
  resolution input for genuinely empty maps.
- [A custom final value could evade packet binding] -> Apply the same field schema,
  rebuild the entire final record, and perform literal plus normalized checks on all
  main/alternative quotes.
- [Locator review could be overstated] -> Keep it declared and always emit
  `quote_locator_verified=false`.
- [Reliability could drift from resolved output] -> Generate adjudications and run
  reliability from the same in-memory captured state; bind every emitted byte in
  one receipt.
- [Native and manual paths could be conflated] -> Require a finalization receipt for
  the native claim and label standalone reliability as compatibility evidence.
- [More private files enlarge the publication failure surface] -> Reuse the proven
  four-state Release15 recovery protocol and never destructively guess ownership.

## Migration Plan

1. Publish and install the release containing the new command and guidance.
2. Keep existing Release15 import directories immutable.
3. Retain the successful prepare manifest digest and import receipt digest outside
   their respective directories.
4. If either difference map is non-empty, create a complete bound resolution JSONL;
   otherwise omit `--resolutions`.
5. Run `coding-audit-finalize` into a new sibling and retain the successful
   finalization-receipt digest separately.
6. Use the generated reliability report and finalization receipt together for the
   native technical-closure record. Do not relabel old/manual reliability reports.

Rollback is the previous manifest-bound skillset commit. Rollback removes the new
native finalizer but does not invalidate immutable Release15 import artifacts or
make manual reliability evidence native.

## Open Questions

None.
