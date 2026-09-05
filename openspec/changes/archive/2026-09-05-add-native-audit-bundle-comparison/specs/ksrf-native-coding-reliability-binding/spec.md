## ADDED Requirements

### Requirement: Native audit-bundle comparison binds both repeat anchors

The system SHALL expose installed `judicial_meaning.py quality native-reliability
compare-audit-bundles` with exactly four required long options:
`--uncertain-audit-bundle-dir`, `--repeated-audit-bundle-dir`,
`--expected-manifest-sha256`, and
`--expected-independent-review-packet-sha256`. Both expected values MUST be lowercase
64-hex retained outside the repeated package from the same complete successful
`coding-audit-prepare` stdout followed by normal code-`0` return. The command MUST NOT
infer either value from either package, use either expected value for the uncertain
package, or accept stdin, positional, default, discovery, output, or abbreviated forms.

Both paths MUST name distinct direct-sibling directories under one actual parent held
throughout. The parent MUST be effective-user-owned, not group/world writable, and
free of every extended ACL on Darwin. Each package MUST be effective-user-owned mode
`0700`, on the parent's device, distinct by device/inode, ACL-free on Darwin, and
contain exactly the seven established preparation-package files. Every entry MUST be
a regular effective-user-owned mode-`0600` single-link file on its directory's device,
ACL-free on Darwin, and distinct from every other input file inode. Established
manifest, plan, JSONL, ZIP, structure, count, and size bounds MUST apply; missing
required descriptor/no-follow/ACL capability MUST fail closed.

Each package MUST independently satisfy the established canonical closed native
package contract and match its securely captured installed codebook. Only the repeated
package MUST match both external expectations: its recomputed manifest self-digest
against `--expected-manifest-sha256` and the raw ZIP SHA-256 against
`--expected-independent-review-packet-sha256`. Success MUST additionally require raw
byte equality of all seven corresponding files.

#### Scenario: Eligible uncertain package equals the two-anchor repeat

- **WHEN** the preserved original diagnostic expressly allowed repeat-and-compare,
  the same inputs produced a normally returned code-`0` sibling, and both values from
  that repeat stdout are supplied independently
- **THEN** `match` is available only after topology, privacy, both full contracts,
  both installed-codebook bindings, both repeated anchors, seven-file byte equality,
  and final recapture succeed
- **AND** no digest is reconstructed or emitted

#### Scenario: A bare exit code two is insufficient

- **WHEN** only the original preparation exit code is known
- **THEN** comparison eligibility remains unverified
- **AND** the command cannot convert a later safe-looking path into authorization

#### Scenario: One repeated stdout anchor is unavailable

- **WHEN** either expected digest was not separately retained from the complete
  successful repeat stdout
- **THEN** the handler cannot return `match`
- **AND** neither manifest nor ZIP supplies the missing expected value

#### Scenario: Stable valid package bytes differ

- **WHEN** both packages are independently valid but any corresponding raw file differs
- **THEN** the report is `mismatch` with exit `3`
- **AND** it exposes no filename, offset, digest, size, or value

### Requirement: Audit-bundle comparison is TOCTOU-resistant and read-only

The command MUST use one held parent plus no-follow open-at/stat operations and held
directory/file descriptors. Every bounded read MUST be surrounded by checks of device,
inode, type, mode, owner, group, link count, size, nanosecond modification/change
times, ACL, and parent/leaf path binding. Packages MUST be processed sequentially;
ZIP members MUST never be extracted to disk; raw comparison MUST use bounded chunks.

After all semantic and byte checks, the command MUST fully recapture both packages and
every used installed codebook, rebind supplied paths and fixed leaves, and repeat raw
seven-file equality. Drift, inability to repeat an inspection, resource exhaustion,
or descriptor-close uncertainty MUST fail as `unreadable`; initial observations MUST
NOT survive as `match`.

After parsing, the command MUST read only the two named packages and their exact
installed codebooks and write only one stdout report. It MUST NOT rerun preparation,
reread the source workspace, mutate permissions or contents, create files, extract an
archive, copy, move, delete, quarantine, transfer, import, finalize, promote, spawn a
subprocess, or access network, socket, HTTP, or database resources.

#### Scenario: Same-inode rewrite races comparison

- **WHEN** a captured object changes before final recapture completes
- **THEN** `comparison_input_changed` wins with `status=unreadable`
- **AND** no earlier equality is trusted

#### Scenario: Match leaves private inputs untouched

- **WHEN** all checks succeed
- **THEN** package bytes, metadata, names, parent inventory, and installed codebooks
  remain unchanged
- **AND** no downstream action is performed

### Requirement: Native audit-bundle comparison report is closed and value-free

Every handler outcome MUST emit exactly one report with top-level keys
`schema_version`, `artifact_type`, `status`, `recovery_comparison_valid`,
`reason_codes`, `checks`, `remediation`, and `scope`. `schema_version` MUST be `1.0`,
`artifact_type` MUST be `native_audit_bundle_comparison_report`, `status` MUST be one
of `match`, `mismatch`, `invalid`, or `unreadable`, and
`recovery_comparison_valid` MUST be true exactly for `match`.

`checks` MUST contain exactly these ordered tri-state members:

- `common_parent_valid`
- `directories_distinct`
- `uncertain_bundle_readable`
- `repeated_bundle_readable`
- `uncertain_bundle_private`
- `repeated_bundle_private`
- `uncertain_inventory_exact`
- `repeated_inventory_exact`
- `expected_manifest_sha256_valid`
- `expected_independent_review_packet_sha256_valid`
- `uncertain_bundle_contract_valid`
- `repeated_bundle_contract_valid`
- `uncertain_installed_codebook_readable`
- `repeated_installed_codebook_readable`
- `uncertain_installed_codebook_binding_valid`
- `repeated_installed_codebook_binding_valid`
- `repeated_external_manifest_digest_valid`
- `repeated_external_independent_review_packet_digest_valid`
- `audit_bundle_file_bytes_equal`
- `final_recapture_valid`

Dependent checks MUST be null when a prerequisite prevents safe evaluation, while
independent safe checks continue. Directly observed drift MUST set final recapture
false and leave interrupted byte equality null rather than manufacturing mismatch.

`reason_codes` MUST be duplicate-free and follow this exact order:

1. `uncertain_audit_bundle_unreadable`
2. `repeated_audit_bundle_unreadable`
3. `uncertain_installed_codebook_unreadable`
4. `repeated_installed_codebook_unreadable`
5. `comparison_input_changed`
6. `comparison_topology_invalid`
7. `uncertain_audit_bundle_privacy_invalid`
8. `repeated_audit_bundle_privacy_invalid`
9. `uncertain_audit_bundle_inventory_invalid`
10. `repeated_audit_bundle_inventory_invalid`
11. `expected_manifest_sha256_invalid`
12. `expected_independent_review_packet_sha256_invalid`
13. `uncertain_audit_bundle_artifact_contract_invalid`
14. `repeated_audit_bundle_artifact_contract_invalid`
15. `uncertain_installed_codebook_binding_mismatch`
16. `repeated_installed_codebook_binding_mismatch`
17. `external_manifest_digest_mismatch`
18. `external_independent_review_packet_digest_mismatch`
19. `audit_bundle_directory_bytes_mismatch`

Remediation MUST use the fixed ordered codes `check_local_read_access`,
`preserve_and_stop`, `use_safe_complete_siblings`,
`retain_successful_repeat_anchors`, `use_exact_installed_codebook`,
`administrator_quarantine`, and `investigate_without_selection`, each paired only
with its fixed Russian message. Input drift or topology/privacy/inventory/contract
faults MUST suppress mismatch investigation and select preservation plus
administrator accounting/quarantine. A pure external-anchor or raw-byte mismatch
MUST select preservation and separate investigation without selecting a package or
authorizing another repeat. The report MUST
contain no path or basename, digest, identifier, count, size, codebook version,
content, device/inode coordinate, timestamp, exception, errno, environment value, or
complete input object.

`scope` MUST contain exactly:

- `technical_recovery_comparison_only=true`
- `original_recovery_eligibility_verified=false`
- `recovery_action_authorized=false`
- `repeat_normal_return_verified=false`
- `input_provenance_authenticated=false`
- `external_manifest_digest_provenance_authenticated=false`
- `external_independent_review_packet_digest_provenance_authenticated=false`
- `original_durability_verified=false`
- `source_workspace_reverified=false`
- `result_selection_performed=false`
- `downstream_use_authorized=false`
- `consumer_revalidation_required=true`
- `reviewer_identity_authenticated=false`
- `publication_safe=false`
- `legal_readiness=false`
- `filing_authorized=false`

#### Scenario: Hostile private values reach an error

- **WHEN** an input value or exception contains distinctive sensitive text
- **THEN** stdout contains only closed enums, booleans/null, fixed Russian remediation,
  and fixed scope
- **AND** handler stderr is empty
