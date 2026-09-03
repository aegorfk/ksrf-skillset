## Context

The native producer emits a strong custodian record: a complete screening frame,
the exact primary decisions, a frozen plan, a queue, pending templates, and a
manifest. That directory cannot itself be handed to the second coder because the
primary decisions disclose the answer. Conversely, its queue and templates alone
do not contain the full text required for independent legal coding.

The next boundary is therefore a one-way handoff artifact produced from the same
already-verified in-memory snapshot before the parent directory is atomically
published. It must be useful without the parent bundle and must not imply that
the second review has occurred.

## Goals / Non-Goals

**Goals:**

- Give a selected independent coder one obvious file to receive.
- Bind every supplied text to the same frozen candidate identity used by the
  custodian bundle.
- Prevent primary substantive answers, digests, coder identity, and sampling-lane
  hints, as well as unnecessary internal source-row IDs, from entering that file.
- Preserve a strict one-to-one mapping among every required candidate, its review
  material, its pending template, and the inner manifest.
- Give the custodian an external SHA-256 anchor for the exact ZIP bytes handed to
  the reviewer.
- Make every inner payload and the ZIP itself byte-deterministic.
- Explain the exact 20-field completion contract and privacy/human gates in plain
  Russian.

**Non-Goals:**

- Importing completed secondary coding or constructing `audit-decisions.jsonl`.
- Automatically deciding, adjudicating, approving, publishing, or filing anything.
- Making the reviewer blind to facts, reasoning, or outcome written in the source
  judicial act.
- Claiming that public-source court text is automatically suitable for unrestricted
  republication or transfer.
- Changing sampling, coding-field, reliability, or primary-bundle semantics.

## Decisions

### The shareable unit is a deterministic stored ZIP

The existing producer adds `independent-review-packet.zip` as the sixth content
file listed by the newly produced parent manifest. A new parent manifest carries
`bundle_contract_version="1.1"` and exactly six content files. The JSON Schema
retains a separate legacy branch for the preceding manifest shape: an old manifest
without `bundle_contract_version` remains valid only with its exact five original
content files, while a `1.1` manifest is valid only with the six-file shape. The
producer emits only `1.1`; it does not rewrite an old artifact or silently relabel
five files as the new format.

The archive uses only stored entries, a fixed 1980 timestamp, fixed regular-file
mode, an empty archive comment, and sorted flat ASCII paths. This avoids
zlib-version drift and path traversal while preserving one atomic publication of
the parent directory.

The archive contains exactly six members: five payload members plus the manifest
that inventories them:

- `review-materials.jsonl`: one selected candidate per row, with exactly
  `schema_version`, `candidate_id`, `chain_id`, `document_id`,
  `source_text_sha256`, `packet_text_sha256`, and `text`; internal `source_id` and
  `source_ids` are omitted because they are neither content identity nor necessary
  reviewer input;
- `secondary-coding-template.jsonl`: the same visibly pending templates already
  produced for the selected candidates;
- `CODING-BRIEF.json`: a closed, self-digesting projection of only the neutral
  frozen-plan context needed to apply the codebook;
- `CODING-CODEBOOK.md`: the exact built-in neutral codebook selected by the
  custodian through the required `--codebook-version 1.0` option;
- `REVIEW-INSTRUCTIONS.md`: a Russian guide telling the second coder to work from
  the full text, preserve identity fields, complete a separate copy under the exact
  20-field contract described below, verify the externally supplied ZIP digest,
  and return strict UTF-8 JSONL for later custodian-side binding;
- `review-packet-manifest.json`: exact candidate population, declared blinding
  scope and safety flags, hashes and sizes of the five payload members, exact
  codebook and brief file hashes, and its own canonical digest.

The sorted unique `candidate_ids` in the inner manifest equal the frozen audit
plan's `required_candidate_ids`. The candidate IDs in `review-materials.jsonl` and
`secondary-coding-template.jsonl` each equal that same set, exactly once. For each
candidate, `candidate_id`, `chain_id`, and `document_id` agree between the review
material and pending template; the review material's content-addressed document
identity and both text digests agree with the exact supplied text and the verified
custodian snapshot. Missing, extra, duplicate, or cross-candidate rows are a
producer error and no parent bundle is published.

### The exact ZIP digest is an external handoff anchor

The parent manifest binds the byte length and SHA-256 of the complete ZIP. The
producer repeats that same digest as `independent_review_packet_sha256` in its
machine-readable stdout. The embedded guide tells the custodian to retain that
value and communicate it separately from the archive, and tells the reviewer to
compare the received ZIP's SHA-256 with the independently received expected value
before extracting or coding. The inner self-digest protects the inner contract and
file inventory, but is not represented as authentication of its own enclosing ZIP.
No signature, reviewer authentication, or completed-review verification is claimed.

### The codebook is selected independently of primary answers

`--codebook-version` is required and accepts only the release-supported allowlist,
which for this release is exactly `1.0`. That selection resolves the tracked neutral
`CODING-CODEBOOK.md`; neither the version nor its bytes are derived from primary
coding. Every primary record must already declare the same version, but this is only
an equality check that rejects stale or mixed procedure. Unsupported versions,
missing selection, a missing or unsafe installed codebook, and any primary-version
mismatch fail before publication.

The exact codebook bytes are SHA-256-bound by the inner manifest, listed in its file
inventory, and repeated as `codebook_sha256` in the versioned parent manifest. There
is no scenario in this release where two different codebook versions are both valid:
adding a future version requires a separate versioned release, codebook asset, tests,
and contract update.

### The neutral brief is a closed frozen-plan projection

The reviewer must know the directional hypothesis, applicable norm editions, population boundary,
and inclusion, exclusion, materiality, and contradiction rules to code `relation`
and the other substantive fields. `CODING-BRIEF.json` therefore projects exactly:
`schema_version`, `artifact_type`, `plan_sha256`, `codebook_version`, `title`, one
`research_questions` entry with only `id`, fixed status `hypothesis_under_test`,
`question`, and `norm_refs`,
`norm_editions` with only edition identity, norm, dates, official URL and status,
the closed population fields, `inclusion_rules`, `exclusion_rules`,
`materiality_rule`, `contradiction_rule`, and `brief_sha256`.

The current 20-field coding record contains one unqualified `relation` and no
`research_question_id`; `supports` and `adverse` also need a fixed directional
proposition. The producer therefore accepts exactly one frozen
`hypothesis_under_test` for this handoff and fails without output for an open
`research_question`, zero questions, or multiple questions. Separate frozen audit
plans and packets are required for separate hypotheses. The brief
never projects `query_lanes`, query text, screening matches, sample membership or
lane, primary coding, `approved_by`, `adverse_review`, or other search/reviewer
metadata. Its `brief_sha256` canonically binds all remaining brief fields, and the
exact serialized brief bytes are bound in the inner file inventory and by matching
`coding_brief_file_sha256` fields in the inner and parent manifests.

### Blinding is structural and tested by invariance

The inner material, neutral brief, and manifest contracts have closed field sets.
Codebook version comes from the required independent CLI selection; primary coding
is only checked for equality and supplies no ZIP field. No inner field, metadata
value, row order, path, or archive byte may derive from a primary record, primary
digest, first-coder identity, per-lane membership, or adjudication. Raw query lanes,
query text, and screening matches are never serialized into the ZIP. The opaque
`plan_sha256` and content-bound candidate IDs nevertheless commit to the full frozen
plan, including its query lanes; this is integrity binding, not semantic secrecy
against a party that already knows or can guess the plan. The declared non-primary
inputs are the independently captured judicial `text` with its content
identities/digests, the required candidate union, the closed neutral frozen-plan
projection, the frozen-plan commitment, and the selected built-in codebook. A string that
independently occurs in the supplied judicial text is not treated as leaked primary
metadata: the text must remain exact even when it also happens to be the first
coder's quote or resembles another coding value. `candidate_id` depends only on
schema version, frozen search plan, chain ID, and content-addressed document ID.

A regression test changes valid primary substantive answers, including the label,
coder, and whether the same candidate appears in the exclusion lane, while keeping
the selected union, externally selected codebook version, frozen-plan projection,
and source inputs fixed; the ZIP must remain byte-identical. This proves more than a
forbidden-key scan and detects an accidental answer- or lane-derived field in any
inner material, manifest, instruction, order, or archive metadata. Separate
fail-closed tests cover a missing/unsupported CLI version, mixed primary versions,
and a codebook asset that is missing, non-UTF-8, empty, or replaced during the
pre-publication input recheck. Structural assertions permit arbitrary unchanged
valid source text but reject `source_ids` and every prohibited metadata field.

### Exact captured text gets two explicit digests

The existing `source_text_sha256` is the workspace store digest after NFC and
whitespace normalization and remains the digest embedded in `document_id`. The
review-material row also carries `packet_text_sha256`, calculated from the exact
UTF-8 text string placed in the row. This avoids falsely claiming that layout-
preserving captured text bytes equal the normalized store representation.

Exact court text may retain layout TAB, LF, VT, FF, and CR. It must be non-empty and
contain a visible non-whitespace character; runtime rejects every other Unicode
control (`Cc`) plus every format (`Cf`) and surrogate (`Cs`) code point. Both the
schema annotation and adversarial tests state this wider runtime rule because JSON
Schema regular expressions cannot portably enumerate every Unicode category. A
text with NUL or zero-width/format characters fails before any bundle is published,
while permitted layout controls remain byte-exact and are covered by
`packet_text_sha256`.

When multiple captured sources collapse to one chain/document identity, their
normalized store digest is not enough to choose reviewer text. Every copy must also
have the same exact `packet_text_sha256`; otherwise the producer fails before
publication instead of selecting a layout variant by source ID or input order.

### The packet remains pending and non-public by default

The inner manifest fixes `review_state=independent_secondary_required`,
`contains_primary_coding=false`, `contains_full_text=true`,
`human_approval_created=false`, `publication_safe=false`, and
`legal_readiness=false`. The guide says the archive may contain personal or other
sensitive information copied from a court act and should go only to the chosen
reviewer through an appropriate channel. Producing it creates neither a completed
review nor permission to publish the text.

### The guide is the exact secondary-coding handoff contract

The embedded guide names all and only the 20 fields in a returned completed coding
record: `candidate_id`, `chain_id`, `document_id`, `label`, `speaker`,
`proposition`, `quote`, `quote_locator`, `norm_edition_id`,
`reasoning_to_outcome`, `reading_family`, `relation`, `remedy`, `coder`,
`codebook_version`, `material_facts`, `alternative_grounds`, `human_review`,
`quote_verified`, and `full_text_reviewed`.

It preserves the four prefilled identity/procedure values, lists the seven allowed
`label` values and five allowed `relation` values, requires `speaker="court"` for
`core_merits` and `contextual`, and requires all mandatory text/identifier fields to
be non-empty and visible. It defines `material_facts` as a non-empty list of visible
strings and `alternative_grounds` as a list that may be empty, where each object has
required `ground` and Boolean `independently_sufficient`, optional `quote` and
`quote_locator`, and no other fields. It requires the reviewer's own `coder`, and
permits `human_review="approved"`, `quote_verified=true`, and
`full_text_reviewed=true` only after the stated human acts occurred.

The guide requires a separate strict UTF-8 JSONL return file with one closed object
per candidate, no duplicate JSON keys, no non-finite values, no missing, extra, or
duplicate candidates, and no edits to the packet or template original. It says that
the custodian must later construct and verify `audit-decisions.jsonl`; returning a
file does not itself prove independence, text verification, agreement, or approval.

## Risks / Trade-offs

- [A stored ZIP is larger than a compressed archive] -> Prefer cross-version byte
  determinism; only the bounded selected union, not the full screening frame, is
  copied into the reviewer packet.
- [Sample membership can reflect exclusion oversampling] -> Do not expose which
  lane selected any candidate or the configured lane sizes; describe the scope as
  primary-answer blinding, not statistical concealment of selection design.
- [An open or multiple question set makes `supports`/`adverse` and one unqualified
  `relation` ambiguous] -> Fail closed unless the frozen plan has exactly one
  directional `hypothesis_under_test`; create separate frozen plans and audit
  packets rather than guessing a relation target.
- [A stale primary card names another codebook version] -> Treat the required CLI
  selection and tracked codebook as authority and use the primary value only for an
  exact equality check; reject unsupported or mixed versions.
- [A source row ID permits avoidable lookup into the custodian workspace] -> Omit
  `source_id`/`source_ids`; retain source-row provenance only in the parent bundle.
- [An inner self-digest can be replaced together with a modified ZIP] -> Publish
  the parent-bound ZIP digest on stdout and require an independently communicated
  expected value; do not claim signatures or authenticated reviewer identity.
- [The source act itself reveals the case outcome] -> State that outcome visibility
  is necessary for full-text legal coding and is outside this blinding claim.
- [A user shares the parent directory instead of the ZIP] -> Give the archive an
  explicit name and make both CLI help and the embedded guide say to share only
  that file, never the parent custodian bundle.
- [Full court text contains personal data] -> Mark publication safety false and
  require deliberate secure transfer/redaction judgment outside the producer.

## Migration Plan

1. Add failing versioned-schema compatibility, exact candidate-bijection,
   deterministic ZIP, primary/lane-invariance, required-codebook, neutral-brief,
   one-hypothesis, external-digest, content/control-policy, source/install parity,
   and atomic-output tests.
2. Extend the pure native builder with selected review materials.
3. Add the required allowlisted codebook selection, exact neutral brief,
   deterministic archive, versioned parent/inner-manifest production, and the
   externally visible ZIP digest to the existing CLI.
4. Update installed Russian help, exact embedded completion guide, methodology
   references, artifact table, and README benefit text.
5. Run focused/full/repository/source/install verification, archive OpenSpec,
   publish one atomic commit to feature and main, verify live SHA, and install the
   exact published runtime globally.

Rollback is the preceding skillset commit. Existing audit bundles stay valid under
their original manifest contract; regeneration is required to obtain the new
reviewer archive.

## Open Questions

None.
