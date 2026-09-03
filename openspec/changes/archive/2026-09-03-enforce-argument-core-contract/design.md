## Context

The validator's field-name sets currently detect omissions only inside
non-empty finding and hypothesis objects. At the root and portfolio levels,
`dict.get(..., [])` and `dict.get(..., {})` turn an absent collection into a
valid empty one. Most required scalar fields are never type-checked, and
finding-to-hypothesis references are never resolved. As a result, structurally
unusable JSON can produce exit code `0`.

The prose reference describes a broader portfolio and an optional ECHR
extension, but the repository's executable fixtures establish only five
portable portfolio fields and do not establish a stable runtime shape for
those extensions. This change therefore closes demonstrable false-greens
without claiming to validate undocumented internals.

## Goals / Non-Goals

- Goals:
  - distinguish missing required containers from present empty containers;
  - validate the existing finding and hypothesis core fields without coercion;
  - resolve every declared core identifier reference after collecting IDs;
  - keep deterministic, addressed diagnostics and total JSON handling;
  - make the success message honest about the validator's limited authority;
  - preserve source/install parity and valid empty research.
- Non-Goals:
  - define or validate `hard_gates`, `dimension_comparison`,
    `critic_findings`, `approval_reason`, or the ECHR extension;
  - require non-empty finding/hypothesis collections;
  - require bidirectional reciprocity, role disjointness, status-to-role
    alignment, reference-array uniqueness, or a minimum number of hypotheses;
  - reject additional extension fields;
  - assess source truth, legal sufficiency, drafting readiness, or filing
    authority.

## Decisions

### Treat presence and type as separate checks

The root requires `case_id`, `findings`, `hypotheses`, and `portfolio`.
Missing collection/object keys receive `root missing <field>` diagnostics;
present values retain field-specific type diagnostics. Empty arrays remain
valid. A malformed container is replaced only in local control flow so other
independent root fields can still be checked; the payload is never mutated.

Each finding and hypothesis continues to report missing fields in sorted order.
Present required text fields must be non-empty strings. `locator` accepts
`null` or a non-empty string, while the existing verified-finding rule still
requires a locator. String-array fields require arrays of non-empty strings.
`contains_sensitive_data` accepts only JSON booleans. Existing enum sets are
unchanged, and `fact_dispute_risk` remains free text because no executable enum
is published.

### Resolve references in two phases

The validator first traverses findings and hypotheses, collecting only valid
non-empty string IDs and validated reference entries. It then checks
hypothesis-to-finding and finding-to-hypothesis existence using those original
strings. This supports forward references and prevents invalid values from
being coerced into identifiers. Unknown-ID lists remain sorted and
deterministic. Duplicate object IDs retain their existing escaped diagnostic;
duplicate entries inside a reference array are not assigned new semantics.

### Keep the executable portfolio core intentionally small

The required portable portfolio core is exactly `human_approval`,
`principal_hypothesis_id`, `reserve_hypothesis_ids`,
`experimental_hypothesis_ids`, and `rejected_hypothesis_ids`, matching the
repository's source and installed fixtures. Extra fields remain opaque and
allowed.

`principal_hypothesis_id` is `null` or a non-empty string referring to a known
hypothesis. It remains forbidden before `human_approval=approved`. Approval
requires a non-null known principal and `approved_by` as a non-empty string;
the reviewer field stays optional in all other states.

### Narrow the success claim

Exit code `0` states in Russian that the checked core structure and references
are valid and that legal readiness was not evaluated. The validator does not
name unchecked extension internals as valid. Semantic failures keep code `1`
and `ERROR:` stdout; read/UTF-8/JSON/decoder failures keep code `2` and stderr.
At CLI startup, standard streams are configured for UTF-8 with escaped fallback
so Russian text and Unicode identifiers cannot turn a result into an encoding
traceback under a restrictive inherited process encoding.

## Risks / Trade-offs

- Previously accepted incomplete artifacts will now fail. Those artifacts did
  not satisfy the documented finding/hypothesis contract or the executable
  five-field portfolio shape.
- The validator remains intentionally partial for richer portfolio and ECHR
  data. The new success line makes that boundary visible rather than implying
  full semantic validation.
- Multiple errors may be reported for one malformed object when independent
  checks fail; ordering remains deterministic and tests pin representative
  cases.

## Verification

Focused tests first reproduce missing-root, missing-portfolio, wrong scalar,
wrong array, wrong boolean, unknown forward-reference, and malformed approval
false-greens. Compatibility controls prove that complete empty research and
unknown extension fields still pass. Source and clean-install subprocess tests
require exact exit channels, deterministic output, no traceback, and unchanged
input bytes. The release then runs the full root and per-skill suites, strict
source/runtime validation, offline containment, quick validation, manifest,
clean-install identity, independent review, atomic publication, and installed
current checks.
