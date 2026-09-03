## ADDED Requirements

### Requirement: Matter initialization preflights the complete artifact layout

Matter initialization MUST inspect, before its first filesystem mutation or
manifest read, the workspace root and every existing component of `matter.json`
and all declared artifact routes. It MUST reject a symlinked workspace root, a
symlink on any planned route, a route that resolves outside the workspace, a
non-directory route ancestor, or an incompatible directory endpoint. When no
valid manifest owns the workspace, it MUST also reject any non-empty reserved
directory endpoint or pre-existing ledger after inspecting the complete route
set and before creating anything. A preflight rejection MUST leave the
workspace and every reachable external path without explicit mutation: path
kinds, link targets, modes, directory entries, and regular-file bytes remain
unchanged, although reads may update access-time metadata. Existing path types
MUST be inspected without following the final component, and a manifest MUST be
a regular file before it is opened. Inspection failures MUST use the matter
workspace error contract. This path-based guarantee covers hazards present when
preflight observes them; it does not claim atomicity against concurrent
substitution after the inspection.

#### Scenario: Artifact ancestor is a symlink

- **WHEN** any planned artifact route traverses a symlink that exists before
  initialization
- **THEN** initialization rejects it before creating a directory, ledger,
  manifest, or audit event, even if the link target is inside the workspace

#### Scenario: Symlink exits the selected matter folder

- **WHEN** a planned route traverses a symlink to an external directory
- **THEN** initialization fails without writing to either the lexical workspace
  or the external target

#### Scenario: A late ledger already exists

- **WHEN** no matter manifest exists and any one of the six planned ledger paths
  already exists
- **THEN** initialization rejects the complete layout before creating earlier
  ledgers or directories and preserves the existing file exactly

#### Scenario: Reserved directory contains unowned data

- **WHEN** no matter manifest exists and an input registry, object store,
  release directory, or audit-event directory already contains any entry
- **THEN** initialization rejects it before mutation instead of adopting the
  pre-existing entry into the new matter

#### Scenario: Workspace root is unsafe

- **WHEN** the selected workspace itself is a symlink or an existing
  non-directory
- **THEN** initialization fails before reading or writing through that path

#### Scenario: Manifest is not a regular file

- **WHEN** `matter.json` is a symlink, dangling symlink, directory, FIFO,
  device, or socket before initialization
- **THEN** initialization rejects its no-follow type without opening it and
  reports the existing matter-workspace error contract

#### Scenario: Existing manifest has an unsafe later route

- **WHEN** a regular `matter.json` exists but any later declared artifact route
  contains a symlink or incompatible type
- **THEN** initialization completes the structural route preflight and rejects
  the workspace before reading the manifest

### Requirement: Safe matter initialization behavior remains compatible

Matter initialization MUST preserve the schema, artifact paths, default privacy
controls, unresolved gates, human-only signature/payment/filing controls, CLI
success rendering, and idempotent reopening behavior for a structurally safe
workspace. Unsafe-path errors MUST use the existing public error channel and
exit semantics without presenting partial initialization as success.

#### Scenario: New safe matter is initialized

- **WHEN** the destination is absent or a compatible empty regular directory
- **THEN** the same manifest, six ledgers, directory routes, and initialization
  audit event are created under the selected workspace

#### Scenario: Compatible paths are pre-created

- **WHEN** reserved directory endpoints are real and empty and the workspace
  contains an unrelated non-route regular file
- **THEN** initialization succeeds and preserves that unrelated file

#### Scenario: Existing valid matter is reopened

- **WHEN** initialization is repeated with the same identifier and profile on a
  valid existing matter
- **THEN** the existing matter is returned without rewriting any artifact

#### Scenario: Public CLI encounters an unsafe route

- **WHEN** `ksrf matter init` receives a workspace whose planned route contains
  a pre-existing symlink or conflict
- **THEN** it returns the existing usage-error exit code on stderr, writes no
  success payload to stdout, and leaves workspace and external state unchanged
