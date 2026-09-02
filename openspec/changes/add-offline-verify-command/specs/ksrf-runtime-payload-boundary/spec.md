## ADDED Requirements

### Requirement: Coordinated runtime verification binds one target observation

A trusted repo-side verification coordinator MUST open the runtime root as a
no-follow directory descriptor before structural preflight, retain that
descriptor through final postflight, and bind status, policy, and content reads
to the retained directory object. It MUST also capture and sample the lexical
root's device, inode, file type, and strict resolved path at phase boundaries.
Coordinated offline success MUST require two equal complete runtime content
identities with the autonomous policy observation between them. A changed,
rebound, symlinked, unavailable, or structurally non-clean target MUST NOT
transfer success to a replacement. The coordinator MUST load only its fixed
repo-side validator, MUST NOT execute target-side code, and MUST NOT claim an
atomic snapshot against arbitrary non-cooperating filesystem writers.

#### Scenario: Lexical root is replaced during validation

- **WHEN** the lexical target is replaced, rebound, converted to a symlink, or resolves elsewhere after its initial anchor
- **THEN** validation reads remain bound to the retained directory object, a replacement cannot inherit its success, and any mismatch present at a phase boundary prevents success

#### Scenario: A transient replacement is restored between samples

- **WHEN** a non-cooperating writer replaces and restores the same lexical path wholly between observable phase-boundary samples
- **THEN** any result describes only the retained directory object that is again bound at output and does not claim detection of that unobservable history or an atomic snapshot

#### Scenario: Runtime content changes during offline verification

- **WHEN** the complete local runtime identity differs between the coordinated initial and final content observations
- **THEN** offline verification records `RUNTIME_IDENTITY_CHANGED`, clears the passing local identity, and exits `1`

#### Scenario: Autonomous policy and content identity diverge

- **WHEN** target content changes after the autonomous policy observation but before the final complete identity
- **THEN** the final identity cannot inherit the earlier policy success and coordinated verification exits `1`

#### Scenario: Postflight becomes non-clean

- **WHEN** transaction evidence, a missing managed package, or unsafe metadata appears before final postflight
- **THEN** the coordinator exits `1` without printing the earlier validation as successful

#### Scenario: Target-side validator is modified

- **WHEN** TARGET contains its own validator with different behavior
- **THEN** coordinated verification ignores it and uses only the fixed regular non-symlink validator in the repository checkout

#### Scenario: Offline coordinator runs

- **WHEN** coordinated runtime verification is requested without current-release comparison
- **THEN** no network opener is called, freshness remains `not_checked`, and the result states that current `main` was not established
