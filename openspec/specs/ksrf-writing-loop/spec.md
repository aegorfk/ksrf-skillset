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
