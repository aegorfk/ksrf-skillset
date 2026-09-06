# ksrf-writing-loop Specification

## Purpose
Preserve a source-bound complaint writing cycle: proposed concept, argument cards, versioned objections, separate revisions and working document export. Technical integrity remains separate from legal approval and filing authority.
## Requirements
### Requirement: Preserve a proposed constitutional concept
The writing plan SHALL preserve alternative issue formulations, a proposed principal choice and its reason. Missing substantive fields SHALL be shown as gaps and SHALL NOT prevent creating a labelled working concept.

#### Scenario: Incomplete concept
- **WHEN** the norm version or causal harm is unknown
- **THEN** the concept identifies the gap without inventing content or granting filing authority

### Requirement: Bind argument cards to source passages and exact wording
A composed draft SHALL bind argument cards to unique sentence identifiers and exact wording hashes. Each cited passage SHALL match its verified local object bytes at explicit character offsets. The output SHALL distinguish quote integrity from source authenticity and legal support.

#### Scenario: Wrong quote or record
- **WHEN** a quotation does not match its locator or its source object has changed
- **THEN** the operation fails with a diagnostic instead of reporting verified support

#### Scenario: Causal claim with incomplete grounds
- **WHEN** the proposed inference exceeds its recorded source roles and proof functions
- **THEN** the output retains a visible review gap and no legal authority is granted

### Requirement: Maintain versioned objections and rechecks
Reviews SHALL target the current draft hash and sentence hash. Revisions SHALL preserve objections, record exact changes and reasons, and reset affected objections to needs_recheck. An automated addressed status SHALL NOT represent independent legal approval.

#### Scenario: Previously addressed objection becomes stale
- **WHEN** the corresponding sentence changes again
- **THEN** the objection requires a fresh review against the new wording

#### Scenario: Stale revision
- **WHEN** a patch supplies a previous draft or sentence hash
- **THEN** it is rejected before a new proposed draft is emitted

### Requirement: Export separate proposed edits with intact boundaries
The workflow SHALL preserve the original, publish a separate proposed draft with a readable diff and explanation, and provide input compatible with render draft. It SHALL NOT carry approvals into the proposed revision or authorize signature, payment, filing or strict release.

#### Scenario: Approved source draft is revised
- **WHEN** the original contains approval declarations
- **THEN** those declarations remain only in the preserved original and do not approve the proposed revision

### Requirement: Revalidate stored writing artifacts
Status SHALL verify the saved packet, related artifacts and source objects. Altered artifacts, cross-matter parent references and missing source evidence SHALL result in an explicit integrity failure.

#### Scenario: Saved proposal was edited outside the workflow
- **WHEN** a stored artifact no longer matches its digest
- **THEN** status reports the mismatch and does not reuse the prior successful check

### Requirement: Preserve declared cross-sentence dependencies
The writing workflow SHALL accept optional reasoned dependencies between existing distinct sentence identifiers, including sentences without argument cards. It SHALL preserve omitted links and reject malformed, duplicate, unknown or redefined identifiers. Removing a link SHALL require an explicit reason retained in history. Retired identifiers SHALL NOT be reused. Graph completeness and legal validity SHALL remain unverified.

#### Scenario: Legacy payload or absent relation
- **WHEN** a payload provides no dependency declarations
- **THEN** the existing workflow remains usable and does not claim that unlinked arguments are independent

#### Scenario: Explicit retirement
- **WHEN** a revision retires an existing dependency with a reason
- **THEN** its history is preserved and that revision still checks consequences under the previous and next links

#### Scenario: Invalid declaration
- **WHEN** a dependency references an unknown sentence, itself, a duplicate identifier or an identifier with a different meaning
- **THEN** the operation fails before saving a new proposed packet

### Requirement: Propagate premise impact without changing dependent text
After applying all edits the workflow SHALL identify direct and transitive review targets under declared previous and next dependencies. It SHALL invalidate affected findings at most once per revision and seed a dedicated impact-review item for every dependency-affected sentence, even without an earlier finding. It SHALL preserve unaffected findings, original and dependent texts, and human authority boundaries. Review SHALL preserve stored impact context and require current draft and wording bindings.

#### Scenario: Unchanged requested remedy
- **WHEN** an edited sentence reaches an unchanged requested-remedy sentence through declared dependencies
- **THEN** the remedy receives an impact-review item without being rewritten or declared legally incorrect

#### Scenario: Independent or conditional alternative
- **WHEN** another argument has no declared dependency on the changed premise
- **THEN** its wording and previous findings are preserved, while the report does not treat missing links as verified independence

#### Scenario: Several roots and cycles
- **WHEN** several edits reach the same dependent sentence or the recorded graph contains a cycle
- **THEN** traversal terminates and affected findings are invalidated once, regardless of edit order

#### Scenario: Fresh review after repeated impact
- **WHEN** an addressed impact-review item is affected by a later revision
- **THEN** it returns to needs_recheck with history and current context preserved

#### Scenario: Several unresolved impacts across revisions
- **WHEN** different premises affecting one target change in consecutive revisions without an intervening review
- **THEN** the current impact context and report preserve all unresolved causes with current wording anchors and historical snapshots

#### Scenario: Unresolved impact after retirement
- **WHEN** a dependency is retired and a stored premise changes before its impact is reviewed
- **THEN** the unresolved target retains all causes with refreshed anchors; an already addressed retired influence does not reopen solely because its former premise later changes

### Requirement: Report the scope and limits of premise review
Each writing packet SHALL provide a readable dependency-impact report distinguishing declared links, explicit retirements and current review targets. Methodology SHALL distinguish the applicant's premise from an opponent's premise, an alternative hypothesis and an established fact, and SHALL require separate reconsideration of requested-remedy scope. Neither source review nor passing technical tests SHALL be described as measured legal improvement or filing readiness.

#### Scenario: Opponent premise is rejected
- **WHEN** the applicant refutes an opponent's proposition without abandoning their own ground
- **THEN** that refutation alone does not require narrowing the applicant's claims or deleting a reserve argument

### Requirement: Review conclusion coverage backward from exact targets
The methodology SHALL reconstruct support from material conclusions and each distinct requested result back to intermediate propositions, evidence and applicable legal anchors. It SHALL record the reviewed and pending scope, distinguish the speaker and role of each proposition, and keep unknown links explicit. Missing runtime dependencies SHALL NOT constitute verified independence or a complete review.

#### Scenario: Unlinked requested result
- **WHEN** a requested result has no declared dependency or argument card
- **THEN** the drafter checks its actual necessary support or records the unanswered question without inventing an edge or declaring the result defective solely for missing metadata

#### Scenario: Procedural request under a condition
- **WHEN** a document contains a procedural request conditional on a later stage
- **THEN** the review keeps its condition, recipient and procedural effect separate from the substantive requested result

### Requirement: Reconstruct surviving support without changing the record
After a material premise change, the methodology SHALL temporarily withhold that premise from the reasoning and examine remaining source-bound chains. It SHALL distinguish cumulative support, alternative sufficient grounds, conditional reasoning and rebuttal of an opponent. It SHALL check shared prerequisites and the exact scope of the conclusion and requested result. This review SHALL NOT establish the negation of a withheld proposition, silently change a selected demand or automatically close an objection.

#### Scenario: Remaining path depends on the same premise
- **WHEN** a proposed substitute ground depends on the withheld premise through another intermediate proposition
- **THEN** the review identifies the hidden shared prerequisite and does not declare independent support

#### Scenario: Separate conditional fallback
- **WHEN** the source supports a fallback only under an explicit assumption
- **THEN** the drafter preserves that conditional form and verifies its limited consequence without asserting contradictory facts simultaneously

#### Scenario: Opponent argument defeated
- **WHEN** the applicant refutes one opponent reason
- **THEN** the applicant's own positive support and requested result are reviewed separately rather than inferred from the refutation

### Requirement: Separate methodological review from runtime and legal authority
The instructions SHALL explain that an impact report lists affected paths rather than all surviving grounds, and that the methodological worksheet is not a new executable packet schema. They SHALL reuse current writing review bindings and preserve existing legal, privacy and human-approval boundaries. Publication evidence SHALL distinguish source review and technical checks from comparative legal-quality measurement.

#### Scenario: Impact context omits an unchanged supporting ground
- **WHEN** an impact report includes the changed path but omits a second supporting path
- **THEN** the reviewer returns to the full draft and source-bound cards before deciding what remains supported
