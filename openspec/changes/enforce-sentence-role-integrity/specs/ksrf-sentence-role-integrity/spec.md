## ADDED Requirements

### Requirement: Release roles use a closed canonical registry

The system SHALL recognize exactly `narrative`, `fact`, `court_reasoning`, `norm_text`, `legal_holding`, `application_finding`, `practice_claim`, `adverse_authority`, and `requested_remedy` as canonical complaint sentence roles. Outside the requested-remedy section, only omitted roles and legacy raw strings SHALL retain the existing explicit `narrative` default. In the requested-remedy section, absent/raw and explicitly canonical roles SHALL normalize to `requested_remedy`, while an explicit unknown string SHALL remain visible and blocked. A present role SHALL be a non-blank string preserved byte-for-byte. An explicit unknown role SHALL remain readable without trimming or alias conversion but SHALL produce a separate exact sentence-specific machine blocker on every release-support path.

#### Scenario: Unknown or misspelled role reaches release support

- **WHEN** a sentence declares `practice_cliam`, `application_findng`, or another value outside the canonical registry
- **THEN** release support fails with the exact sentence identifier and original role instead of treating the sentence as narrative

#### Scenario: Legacy sentence has no role

- **WHEN** a legacy mapping omits `role` or a legacy sentence is a raw string
- **THEN** normalization assigns explicit `narrative` outside the requested-remedy section, assigns `requested_remedy` inside that section, and preserves draft readability

#### Scenario: Alias looks semantically familiar

- **WHEN** a caller supplies `factual_claim`, `holding_claim`, `legal_claim`, or another plausible alias
- **THEN** the runtime does not guess a canonical role and blocks release pending explicit correction and review

#### Scenario: Explicit role is padded, blank, or not a string

- **WHEN** a caller supplies `" fact "`, a blank string, null, boolean, number, array, or object as `role`
- **THEN** the padded string remains an unknown exact value and blocks without trimming, while blank and non-string values are rejected as invalid input rather than defaulted to narrative

### Requirement: Draft compatibility does not create release authority

The structured complaint SHALL remain able to serialize an explicit unknown legacy role for migration. A blocked diagnostic filing manifest MAY retain that role when it carries a release blocker. Every ready filing manifest SHALL contain canonical roles only.

#### Scenario: Unknown legacy role is opened for repair

- **WHEN** a working draft contains an explicit unknown role
- **THEN** the line remains visible with its text and original role and is not silently deleted or rewritten

#### Scenario: Unknown requested-remedy role carries repair provenance

- **WHEN** a requested-remedy sentence has an explicit unknown role and existing `application_record_ids`
- **THEN** draft round-trip preserves those identifiers for repair while the line remains unbound and release-blocked

#### Scenario: Unknown role appears in a ready manifest

- **WHEN** a manifest declares expert-review or human-signing readiness while any sentence has an unknown role
- **THEN** both runtime verification and filing-package schema validation reject the ready projection

#### Scenario: Unknown role appears in a blocked diagnostic

- **WHEN** a blocked manifest preserves an unknown role and the corresponding blocker
- **THEN** the schema permits the diagnostic artifact only with an anchored machine-blocker shape, runtime requires exact sentence-and-role marker equality, and the artifact cannot be approved or promoted to readiness

#### Scenario: Similar but mismatched blocker is supplied

- **WHEN** the blockers array contains only a prefixed, suffixed, wrong-sentence, or wrong-role variant of the required unknown-role marker
- **THEN** runtime verification reports the exact corresponding blocker missing; schema independently rejects a malformed machine-marker envelope, while syntactically valid wrong-sentence or wrong-role correlation remains an explicit runtime check because portable JSON Schema cannot compare dynamic values across arrays

### Requirement: The host attests the complete sentence-role inventory

Every ready release SHALL resolve a pre-existing host draft registry for the exact matter and draft and SHALL receive every current sentence exactly once with a continuous global 1-based draft ordinal, strict sentence ID, section, exact text SHA-256, and canonical role. The response SHALL bind exact matter/draft identity, a deterministic ordered complete-index SHA-256, one host authority revision, and an RFC3339 snapshot check time stable for that revision. The runtime SHALL independently derive and compare the complete local ordered projection and SHALL NOT accept a registry manufactured from caller-supplied current entries.

#### Scenario: Filing role is downgraded to narrative

- **WHEN** a current host registry records a sentence as `application_finding` but the release projection relabels it `narrative`
- **THEN** exact complete-index comparison fails even if the sentence text and identifier are unchanged

#### Scenario: Sentence is deleted, inserted, moved, or rewritten

- **WHEN** the release projection differs from the host registry by sentence set, section, or exact text hash
- **THEN** the complete role index fails closed with no release receipt

#### Scenario: Sentences or sentence-bearing sections are reordered

- **WHEN** the same sentence identifiers, sections, texts, and roles appear in a different sentence order, including because two non-empty sections moved
- **THEN** their global ordinals and ordered index hash differ and the complete role index fails closed

#### Scenario: Host index is malformed or unknown

- **WHEN** the authority returns a scalar container, duplicate or non-contiguous ordinal, duplicate sentence, invalid identifier, unknown role, dishonest index hash, wrong matter/draft, or missing revision/check time
- **THEN** release support fails without coercion

#### Scenario: Complete index is exact

- **WHEN** every local sentence exactly matches the current host registry and all response bindings are valid
- **THEN** the runtime emits one immutable complete role-index receipt

### Requirement: Persisted role receipts are revalidated

Filing-package schema `1.4` SHALL persist the complete sentence-role index receipt, include it in the release basis, and require current host re-resolution during manifest verification, expert approval, and human signing/filing readiness. A ready manifest SHALL always carry the receipt; a blocked diagnostic MAY carry null.

#### Scenario: Authority changes after pack build

- **WHEN** the host registry changes any sentence, section, text, role, revision, or index after the pack was built
- **THEN** manifest verification fails and any prior approval becomes stale

#### Scenario: Cached render status is queried after authority change

- **WHEN** a prior render operation was ready but current support authority or the stored/current sentence-role receipt no longer matches
- **THEN** `render/status` revalidates the stored complaint input, reports blocked, and does not reuse the cached ready state as current authority

#### Scenario: Authority is absent

- **WHEN** a ready release path cannot resolve the host sentence-role registry
- **THEN** readiness is blocked even when all specialized evidence receipts are otherwise valid

#### Scenario: Blocked diagnostic has no role authority

- **WHEN** artifact generation is diagnostic and no sentence-role authority is available
- **THEN** a null receipt remains schema-valid only with `status=blocked`

### Requirement: Role integrity does not replace evidence or human gates

A valid complete role index SHALL establish only sentence identity and role integrity. It SHALL NOT establish truth, evidence sufficiency, legal approval, merge authority, global installation authority, signature, payment, transmission, or filing.

#### Scenario: Role index passes

- **WHEN** the complete role inventory is exact
- **THEN** all role-specific evidence, QA, legal, publication, and human gates remain independently required
