## MODIFIED Requirements

### Requirement: Independent grounds do not erase proven implicit norm use
The application route SHALL preserve `norm_use_status=reasoning_linked_implicit` when a complete verified court-authored record proves use of the norm's precise logic, even if `outcome_causation=independent_sufficient_ground` blocks the causal-harm gate. In that combination the route SHALL NOT return `not_applied`. The classifier reason `implicit_norm_use_preserved` SHALL require non-contradicted issue and operative-logic premise records, quoted full-act spans, a court-authored operative-logic span and a diagnostic named-review marker; that raw marker SHALL NOT be represented as approval of fingerprinted content or as a substitute for the separate trusted approval ledger. An asserted but pending, incomplete, rejected or contradicted implicit-use record SHALL remain `application_unclear` and SHALL NOT be described as proven or converted to positive non-application.

#### Scenario: Implicit use and an independent sufficient ground coexist
- **WHEN** a record has a diagnostic named-review marker and non-contradicted premises supporting court-authored use of the norm's precise logic but another sufficient ground independently sustains the same result
- **THEN** implicit norm use and the independent-ground causation status are both preserved
- **AND** the admissibility-facing application status remains `application_unclear`
- **AND** trusted approval of the fingerprinted record remains independently required
- **AND** the route does not relabel the norm as not applied or produce a complaint-ready causal claim.

#### Scenario: Supporting premise is contradicted
- **WHEN** the record asserts reasoning-linked implicit norm use but either the issue premise or operative-logic premise has `inference_status=contradicted`
- **THEN** the route returns `application_unclear` with an implicit-use verification gap
- **AND** does not emit `implicit_norm_use_preserved`, `implicitly_applied_proven` or a complaint-ready causal claim.

#### Scenario: Premise name is duplicated
- **WHEN** an implicit-use record supplies the same required premise more than once, including conflicting versions in either order
- **THEN** the record is rejected as non-canonical
- **AND** ordering cannot hide a contradicted premise or produce a positive application classification.

#### Scenario: Named-review marker is absent
- **WHEN** court-authored issue and operative-logic spans are present but the record has no complete diagnostic named-review marker
- **THEN** the route returns `application_unclear` with an implicit-use verification gap
- **AND** keeps the independent sufficient ground on the causation axis without returning `not_applied`.

#### Scenario: Review timestamp is malformed
- **WHEN** an approved diagnostic marker has a nonblank reviewer but `reviewed_at` is not a parseable timezone-aware RFC 3339 timestamp
- **THEN** runtime treats the marker as incomplete and does not emit `implicit_norm_use_preserved` or `implicitly_applied_proven`
- **AND** the standalone schema rejects a syntactically malformed shape and declares the `date-time` format, while runtime additionally validates calendar/time semantics.

#### Scenario: No implicit-use candidate exists
- **WHEN** a complete independent ground is proved and the record neither asserts nor proves direct or implicit norm use
- **THEN** the existing positive non-application route may return `not_applied`
- **AND** the correction does not infer implicit use from the independent ground itself.

#### Scenario: Only a party asserts the independent ground
- **WHEN** an affirmative non-application record cites an independent-ground span attributed only to a party
- **THEN** the route does not treat that assertion as court-proven non-application
- **AND** the result remains `application_unclear` unless court or disposition evidence supplies the ground.

#### Scenario: Independent-ground assertion contradicts the causation axis
- **WHEN** an affirmative complete-independent-ground record retains any outcome-causation status other than `independent_sufficient_ground`
- **THEN** the record is rejected as internally inconsistent
- **AND** the assertion cannot overwrite the canonical causation axis.

#### Scenario: Court ground evidence contradicts the causation axis
- **WHEN** a usable court- or disposition-authored `independent_ground` span appears in a record whose outcome-causation status is not `independent_sufficient_ground`
- **THEN** both the standalone schema and runtime reject the record as internally inconsistent
- **AND** the ordinary implicit branch cannot ignore the ground and emit `implicitly_applied_proven`.

#### Scenario: Standalone schema receives duplicate premises
- **WHEN** a schema-only consumer validates two implicit premise records with the same premise name
- **THEN** Draft 2020-12 validation rejects the artifact before runtime deserialization
- **AND** schema order cannot produce a different result from runtime order.

#### Scenario: Valid ground is accompanied by an invalid extra span
- **WHEN** one court-authored independent-ground span is valid but an additional cited span is contradicted, unlocated, blank or party-authored
- **THEN** only the valid span appears in the classification evidence identifiers
- **AND** the invalid extra span cannot borrow the valid span's proof status.

#### Scenario: Cross-instance proof has no quoted content
- **WHEN** an incorporation or later independent-ground span has a locator but its quote is empty or whitespace-only
- **THEN** chain assessment and evidence binding do not treat it as positive proof of survival, incorporation or supersession
- **AND** no release receipt is emitted from that span.

#### Scenario: Intermediate review is not release approval
- **WHEN** all four implicit premises and a complete diagnostic named-review marker support the intermediate classifier
- **THEN** the classifier may return `implicitly_applied_proven`
- **AND** admissibility and release remain blocked until the separate trusted ledger approves the exact content fingerprint.

## ADDED Requirements

### Requirement: Machine-readable SHALL bodies remain complete
Every changed OpenSpec requirement body SHALL keep its complete normative sentence on one physical line so `openspec show --json --deltas-only` exposes every continuation clause to machine consumers.

#### Scenario: Strict validation accepts a wrapped requirement
- **WHEN** strict validation passes but JSON projection would stop at the first physical line
- **THEN** release verification fails until the body is unwrapped and sentinel continuation clauses are visible in the JSON requirement text.

#### Scenario: Active correction is projected before archive
- **WHEN** the corrective change still exists under `openspec/changes`
- **THEN** the regression invokes `openspec show harden-implicit-application-proof-state --json --deltas-only`
- **AND** verifies the continuation clauses of both corrective deltas before capability sync and archive.
