## ADDED Requirements

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
