## MODIFIED Requirements

### Requirement: Status reports concurrency limits honestly
Status SHALL treat its result as an unlocked bounded observation and SHALL not claim whether an installer process is active or whether a later installation will succeed. Retained evidence SHALL be classified from two independent comparison samples; an optimization SHALL NOT reuse a payload or mount snapshot across those samples.

#### Scenario: Stable retained transaction
- **WHEN** a valid transaction is observed without a changed root fingerprint
- **THEN** guidance says to wait if an installation is still running and otherwise rerun normal installation for validated recovery
- **AND** each of the two comparison samples traverses every evidence and live-skill payload file at most once

#### Scenario: State changes during observation
- **WHEN** the target remains anchored but any lock, canonical-skill, installer-root, journal, container, live-skill, or sampled mount-table fact determining classification changes during inspection
- **THEN** status is `recovery_required`, advises retrying after the installer finishes, and does not label the evidence corrupt

#### Scenario: Stable invalid evidence after a complete semantic sample
- **WHEN** all evidence and live-skill bytes have been sampled but a transaction state invariant fails
- **THEN** status reuses that complete sample fingerprint and does not perform an additional raw payload traversal for the same comparison sample

#### Scenario: Invalid evidence before a complete semantic sample
- **WHEN** parsing, layout, type, or budget validation fails before a complete comparable identity exists
- **THEN** status performs at most one bounded raw completion traversal for that comparison sample before applying the existing stable-invalid versus changing-evidence rule

#### Scenario: Mount discovery during retained-evidence inspection
- **WHEN** a stable retained transaction contains any number of safe nested directories
- **THEN** Linux child descriptors are compared with the target descriptor's `mnt_id`; if the target descriptor's ID is unavailable, the current live per-directory fallback remains in force, while an unavailable child ID after a target ID was established is rejected fail-closed
- **AND** hosts without Linux mountinfo do not repeatedly load an empty Linux set, while the two boundary samples remain independent and their method and target identity contribute to the comparable fingerprint

#### Scenario: Same-device bind mount is substituted
- **WHEN** a child directory has the expected device but its descriptor-bound Linux mount ID differs from the target sample mount ID
- **THEN** status rejects the child as a mount boundary without traversing it

#### Scenario: Target replacement during observation
- **WHEN** the target device or inode differs between the start and end samples
- **THEN** status is `unsafe` and no clean or recovery-safe conclusion is reported
