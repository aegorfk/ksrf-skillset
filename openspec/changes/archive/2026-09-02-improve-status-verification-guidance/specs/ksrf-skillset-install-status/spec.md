## MODIFIED Requirements

### Requirement: Status output serves people and automation

Status SHALL provide concise Russian human output by default and deterministic
JSON with bounded public fields when `--json` is selected. A clean result SHALL
distinguish structural installation state from runtime content identity and
online freshness. Without opening the network or executing validation, its
recommended action SHALL emit two ordered shell-quoted absolute commands from
the current repository for the exact target: first
`<repo>/install.sh --verify --target <exact target>` for local offline
integrity, then `<repo>/install.sh --verify-current --target <exact target>` for
optional online freshness. It SHALL NOT depend on older target-side policy or
imply that reinstalling is the only way to inspect the installation. If the
repository entry point is absent, non-executable, symlinked, or any command
value contains non-printable/control/surrogateescaped characters, status SHALL
emit an honest fallback rather than a dead, partial, or visually spoofable
command. Non-clean states SHALL retain their existing action without inspecting
the entry point. The guidance SHALL preserve that byte equality is not
installation provenance, legal-source freshness, or filing readiness.

#### Scenario: Human clean result

- **WHEN** a user requests status without `--json`
- **THEN** the output explains the observed structural state, canonical skill count, ordered executable offline and optional online commands for the exact target, and read-only unlocked boundary in plain Russian

#### Scenario: JSON clean result

- **WHEN** automation requests clean status with `--json`
- **THEN** the stable report shape and exit code remain unchanged while `message` says content and freshness were not checked and `recommended_action` names one existing repo-side installer, `--verify`, `--verify-current`, and the exact `--target` in that order

#### Scenario: Repo-side entry point is absent

- **WHEN** status is invoked from a detached tool copy without the canonical installer beside it
- **THEN** recommended action says the verification entry point is unavailable and directs the user to update the repository without emitting a nonexistent command

#### Scenario: Repo-side entry point is not executable

- **WHEN** the canonical installer exists but cannot be executed by the current process
- **THEN** status emits the same honest fallback and no dead shell command

#### Scenario: Target path contains surrogateescaped bytes

- **WHEN** a clean POSIX target contains filesystem bytes that cannot be represented as ordinary Unicode command arguments
- **THEN** recommended action says safe commands cannot be formed and emits no misleading command for a different path

#### Scenario: Target path contains display control characters

- **WHEN** a clean target spelling contains newline, carriage return, tab, escape, or another non-printable character
- **THEN** recommended action emits one fixed fallback without interpolating the path or a spoofable command line

#### Scenario: Status remains offline

- **WHEN** clean status renders the ordered verification recommendation
- **THEN** status itself invokes no network opener, validator, installer, subprocess, write, recovery, or lock operation

#### Scenario: JSON result

- **WHEN** automation requests status with `--json`
- **THEN** stdout contains one JSON object with schema version, status, severity, exit code, bounded stable reason code, target, target existence, managed-skill summary, optional transaction summary, message, recommended action, and an observation boundary declaring `explicit_mutations_performed=false`, `filesystem_access_time_updates_possible=true`, and `atomic_snapshot=false`

#### Scenario: Sensitive journal details

- **WHEN** a journal contains content identities and per-skill progress
- **THEN** status does not emit digests, journal bodies, old content, arbitrary unknown entry names, raw exceptions, or unrelated target entries

#### Scenario: Human recovery phase

- **WHEN** human output describes a pre-journal, building, prepared, rollback, committed, or cleanup phase
- **THEN** it uses a concise Russian phrase rather than the internal phase enum
