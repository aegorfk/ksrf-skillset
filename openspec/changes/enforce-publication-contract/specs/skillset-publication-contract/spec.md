## ADDED Requirements

### Requirement: Publication is part of completion
The workflow MUST treat every change to any versioned KSRF skillset file as incomplete until the exact release is synchronized, validated, committed atomically, pushed to `aegorfk/ksrf-skillset:main`, and the live remote SHA is verified to equal the local release HEAD.

#### Scenario: Local change is not yet published
- **WHEN** a KSRF skillset file has changed locally but the matching commit is not the live `main` SHA
- **THEN** the workflow reports the task as not fully published and records the exact unpublished file manifest and blocker

#### Scenario: Published release is complete
- **WHEN** the exact validated skillset snapshot is committed, pushed to `main`, and a fresh live lookup returns the same SHA as local HEAD
- **THEN** the workflow may report the public release as complete and includes the verified SHA

### Requirement: Global installation is fail closed
The installer MUST refuse to create, overwrite, or delete files in the canonical global KSRF skills directory unless the checkout is clean, its expected public remote is valid, its HEAD equals a freshly fetched live `refs/heads/main` SHA, and the bundled skill tree and executable release tools match the versioned manifest. Canonical and clean-room copies MUST use the same allowlist and runtime/secret exclusions and MUST reject broad, symlinked, or non-directory targets before writing.

#### Scenario: Checkout is stale or unpublished
- **WHEN** local HEAD differs from live `main`, the checkout is dirty, the remote is unexpected, the live check fails, or the manifest does not match
- **THEN** installation into the canonical global skills directory exits non-zero before copying or deleting any skill files

#### Scenario: Clean-room verification remains available
- **WHEN** an operator explicitly supplies a non-canonical target directory
- **THEN** the installer copies the same manifest-covered payload there without overwriting canonical global skills and clearly identifies the operation as a custom-target installation

### Requirement: Synchronization starts from verified main
The global-to-public synchronization workflow MUST verify a clean checkout at the live `origin/main` SHA before copying files, MUST fail before writes if any explicitly active mirrored tool is absent, MUST remove only explicitly retired first-party mirror names, MUST regenerate the skill and release-tool manifest after synchronization, and MUST leave commit and push as explicit release steps.

#### Scenario: Stale publication checkout
- **WHEN** synchronization is invoked from a checkout whose HEAD does not equal live `origin/main`
- **THEN** synchronization exits non-zero before changing the repository skill tree

#### Scenario: Successful synchronization
- **WHEN** the checkout is clean and current and all fourteen canonical global skills exist
- **THEN** the workflow synchronizes the allowlisted skill trees, mirrors the allowlisted tools, regenerates the manifest, and prints the remaining validation, commit, push, and live-SHA steps

### Requirement: Manifest base commit binds one atomic release
The manifest `remote_base_commit` MUST be a full lowercase 40-hex commit SHA that exists locally and exactly equals the first parent of release HEAD. The manifest MUST cover both the exact skill payload and executable release tools.

#### Scenario: Invalid or non-parent manifest base
- **WHEN** `remote_base_commit` is malformed, missing, not a commit, or differs from release `HEAD^`
- **THEN** publication verification exits non-zero before global installation or synchronization

#### Scenario: Additional release or documentation commit
- **WHEN** another commit is added after the manifest-bound atomic release commit
- **THEN** verification blocks until the manifest is regenerated from the new live base and the complete change is republished as one atomic commit

### Requirement: Publication blockers are explicit
If publication cannot complete, the workflow MUST preserve local work and report the exact unpublished files, validation state, local HEAD, observed live SHA when available, and the failed step.

#### Scenario: Push or live verification fails
- **WHEN** a release cannot be pushed or its remote SHA cannot be verified
- **THEN** no destructive rollback is performed and the final report identifies the unpublished manifest and failure precisely
