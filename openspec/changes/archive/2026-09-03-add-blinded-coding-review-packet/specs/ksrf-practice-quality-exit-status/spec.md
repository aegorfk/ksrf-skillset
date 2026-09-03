## ADDED Requirements

### Requirement: Native audit preparation emits a primary-answer-blinded reviewer archive

New output from `quality coding-audit-prepare` MUST carry
`bundle_contract_version="1.1"` in the parent manifest and MUST add
`independent-review-packet.zip` as its sixth exact content file. The manifest
schema MUST retain a separate legacy branch under which a preceding five-file
manifest with no `bundle_contract_version` remains valid; the new producer MUST
emit only the exact six-file `1.1` variant and MUST NOT reinterpret a legacy
manifest as `1.1`.

The ZIP MUST contain exactly six members: the five payload members
`CODING-BRIEF.json`, `CODING-CODEBOOK.md`, `REVIEW-INSTRUCTIONS.md`,
`review-materials.jsonl`, and `secondary-coding-template.jsonl`, plus
`review-packet-manifest.json`, which inventories exactly those five payload members.
It MUST use a sorted flat path order, stored entries, fixed timestamps and
regular-file modes, and no archive comment so identical accepted inputs produce
identical bytes.

Each review-material row MUST have the exact closed field set `schema_version`,
`candidate_id`, `chain_id`, `document_id`, `source_text_sha256`,
`packet_text_sha256`, and `text`. It MUST carry the same candidate and
chain/document identities as the frozen audit inputs, the normalized store
`source_text_sha256`, a `packet_text_sha256` over the exact UTF-8 text string
supplied in that row, and the non-empty full text. It MUST NOT carry `source_id` or
`source_ids`. Exact full text MAY retain TAB, LF, VT, FF, and CR layout controls but
MUST contain a visible non-whitespace character and MUST reject every other Unicode
control (`Cc`) plus every format (`Cf`) and surrogate (`Cs`) code point before any
publication. The pending templates MUST equal the producer's selected secondary
templates byte for byte.

The sorted unique inner-manifest `candidate_ids`, the review-material candidate
IDs, and the pending-template candidate IDs MUST each equal the frozen audit
plan's exact `required_candidate_ids`, with every candidate present exactly once
in each JSONL file. For every candidate, `candidate_id`, `chain_id`, and
`document_id` MUST agree across material and template, and both text digests MUST
agree with the content-addressed document and exact supplied text. A missing,
extra, duplicate, or cross-bound row MUST prevent any parent bundle publication.

The self-digesting inner manifest MUST bind the exact candidate population and the
size and SHA-256 of all five payload members. It MUST declare primary-answer
blinding, full-text inclusion, pending independent review, no created human
approval, no default publication safety, and no legal readiness. Both the inner and
versioned parent manifests MUST repeat `codebook_sha256` for the exact built-in
codebook bytes and `coding_brief_file_sha256` for the exact serialized neutral-brief
bytes, and each value MUST equal the corresponding inner file-inventory digest.

The required `--codebook-version` input MUST accept exactly the release-supported
allowlist, which is only `1.0` in this release, and MUST resolve the tracked neutral
`CODING-CODEBOOK.md`. Primary records MUST carry that same version, but their value
is only an equality check: neither codebook selection nor any ZIP bytes may be
derived from a primary record. A missing or unsupported selection, primary mismatch,
or missing, unsafe, empty, non-UTF-8, or concurrently replaced codebook MUST prevent
publication.

`CODING-BRIEF.json` MUST be the exact closed self-digesting projection of the frozen
plan's neutral reviewer context: plan identity and title, selected codebook version,
exactly one directional hypothesis with only its ID, fixed
`hypothesis_under_test` status, text and norm references,
applicable norm editions, population, inclusion/exclusion rules, materiality rule,
and contradiction rule. It MUST NOT project query/search lanes or text, screening
matches, sampling metadata, primary coding, `approved_by`, `adverse_review`, or
other reviewer/search metadata. Because `supports`/`adverse` require a fixed
proposition and the 20-field coding record has one unqualified `relation`, an open
`research_question`, zero questions, or multiple frozen questions MUST prevent
publication and require separate per-hypothesis frozen plans and audit packets.

Apart from the independently captured unchanged judicial `text` and its content
identities/digests, the required candidate union, the closed neutral plan projection,
the opaque frozen-plan commitment, and the independently selected built-in codebook,
no inner field, metadata value, row order, path, or archive byte may derive from a
primary coding record or digest, first-coder identity, sample-lane label, or
adjudication. Raw query lanes, query text, and screening matches MUST NOT be
serialized. `plan_sha256` and each content-bound candidate ID MAY cryptographically
commit to the full frozen plan, including query lanes; documentation MUST NOT call
that commitment semantic secrecy from a party that knows or guesses the plan. The
content of the judicial act itself and membership in the union sample are not hidden
and MUST NOT be described as outcome-blind evaluation.

The parent manifest MUST bind the exact ZIP byte length and SHA-256, and successful
producer stdout MUST expose that same digest as
`independent_review_packet_sha256`. The embedded guide MUST instruct the custodian
to retain and communicate the expected digest separately from the ZIP and the
reviewer to compare the received ZIP against it before extraction or coding. The
inner self-digest MUST NOT be represented as authentication of its own enclosing
ZIP.

#### Scenario: User hands one archive to the independent coder

- **WHEN** a valid native audit bundle is prepared from a verified workspace
- **THEN** its parent manifest binds one deterministic
  `independent-review-packet.zip`
- **AND** that archive gives the reviewer all selected full texts, identities,
  pending templates, and Russian instructions without the primary answers
- **AND** producing it leaves secondary review, adjudication, legal approval, and
  filing incomplete

#### Scenario: Legacy and new parent manifests stay distinguishable

- **WHEN** schema validation receives an intact preceding five-file manifest
  without `bundle_contract_version` or a new six-file manifest with
  `bundle_contract_version="1.1"`
- **THEN** each is accepted only by its own exact schema branch
- **AND** a five-file `1.1` manifest, a six-file unversioned manifest, or either
  manifest with a mixed file set is rejected

#### Scenario: Every required candidate has exactly one review pair

- **WHEN** the producer assembles review materials, pending templates, and the
  inner manifest for a multi-candidate union
- **THEN** all three sorted unique candidate populations equal the frozen required
  candidate set
- **AND** omission, duplication, an extra candidate, or swapped identity/text
  binding prevents publication

#### Scenario: Primary answers change without changing selected membership

- **WHEN** two otherwise identical valid workspaces differ only in primary
  substantive coding, first-coder identity, and per-lane selection while retaining
  the same candidate union, codebook version, and source inputs
- **THEN** their independent-review ZIP bytes are identical
- **AND** their parent custodian artifacts may still differ and remain separately
  bound to their exact primary inputs
- **AND** unchanged judicial text remains byte-exact even if it contains a string
  also used by one primary coding record

#### Scenario: Codebook authority is independent and allowlisted

- **WHEN** the custodian omits `--codebook-version`, selects anything other than
  `1.0`, a primary record names another version, or the installed `1.0` codebook is
  missing, unsafe, empty, non-UTF-8, or changes during preparation
- **THEN** preparation fails without publishing a parent bundle
- **AND** no primary field is treated as authority for codebook selection or bytes

#### Scenario: Directional reviewer context is sufficient without revealing search design

- **WHEN** a valid frozen plan contains exactly one `hypothesis_under_test`
- **THEN** `CODING-BRIEF.json` contains only the closed neutral projection needed to
  apply the codebook and its self-digest binds every projected field
- **AND** both manifests bind the exact brief and codebook file bytes
- **AND** no query lane/text, match, sampling lane, primary answer, `approved_by`, or
  `adverse_review` appears in the ZIP

#### Scenario: Open or multiple questions cannot supply a relation target

- **WHEN** the verified frozen plan contains an open `research_question`, zero
  questions, or more than one question
- **THEN** preparation fails without output instead of guessing which proposition
  `supports`, `adverse`, or the returned `relation` addresses
- **AND** the custodian must prepare separate single-hypothesis frozen plans and
  audit packets

#### Scenario: Captured and normalized text representations differ

- **WHEN** a selected captured text contains layout whitespace that normalizes for
  the content-addressed document identity
- **THEN** `source_text_sha256` remains the normalized store digest
- **AND** `packet_text_sha256` verifies the exact text string supplied to the reviewer
- **AND** TAB, LF, VT, FF, and CR remain byte-exact, while NUL, every other `Cc`, and
  every `Cf` or `Cs` character cause fail-closed refusal with no output

#### Scenario: Collapsed source copies differ only in exact layout

- **WHEN** two source rows share one chain/document identity and normalized store
  digest but have different exact UTF-8 text strings
- **THEN** preparation fails without output instead of selecting a variant by
  source ID or input order

#### Scenario: Packet is not automatically public-safe

- **WHEN** the archive contains selected full judicial texts
- **THEN** its manifest fixes `publication_safe=false`
- **AND** the instructions require deliberate secure transfer and separate
  publication/redaction judgment rather than treating public-source status as
  blanket permission to republish personal data

#### Scenario: Reviewer receives an externally pinned archive

- **WHEN** preparation succeeds and the custodian transfers the ZIP
- **THEN** stdout exposes the same SHA-256 that the parent manifest records for the
  ZIP
- **AND** the instructions require the reviewer to compare that separately supplied
  expected digest before using the archive
- **AND** neither the digest nor a successful comparison claims a signature,
  reviewer identity, completed review, legal approval, or filing authority

### Requirement: Embedded review guidance states the closed completion contract

`REVIEW-INSTRUCTIONS.md` MUST name all and only the 20 fields of the authoritative
completed secondary-coding record: `candidate_id`, `chain_id`, `document_id`,
`label`, `speaker`, `proposition`, `quote`, `quote_locator`, `norm_edition_id`,
`reasoning_to_outcome`, `reading_family`, `relation`, `remedy`, `coder`,
`codebook_version`, `material_facts`, `alternative_grounds`, `human_review`,
`quote_verified`, and `full_text_reviewed`. It MUST list the seven accepted `label`
values and five accepted `relation` values, require `speaker="court"` for
substantive labels, distinguish unchanged identity/procedure fields from
human-authored coding, and state the non-empty visible text and canonical
identifier requirements.

The guide MUST define `material_facts` as a non-empty list of visible strings and
`alternative_grounds` as a list that may be empty, whose objects contain required
`ground` and Boolean `independently_sufficient`, optional `quote` and
`quote_locator`, and no other fields. It MUST permit `human_review="approved"`,
`quote_verified=true`, and `full_text_reviewed=true` only after those human acts
occurred. It MUST require a separate strict UTF-8 JSONL return file with exactly one
closed record per required candidate, unique keys, finite JSON values, and no edits
to the original packet/template.

#### Scenario: Second coder can return a contract-complete file

- **WHEN** the reviewer follows the embedded guide without access to the parent
  custodian directory
- **THEN** the guide identifies every required field, enum, nested shape, identity
  preservation rule, and strict JSONL constraint needed for a completed secondary
  record
- **AND** it says that return of the file does not itself prove independence,
  text verification, agreement, legal approval, or filing authority
