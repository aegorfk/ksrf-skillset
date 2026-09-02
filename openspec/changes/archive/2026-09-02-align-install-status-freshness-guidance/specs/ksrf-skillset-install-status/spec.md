## MODIFIED Requirements

### Requirement: Status output serves people and automation

Status SHALL provide concise Russian human output by default and deterministic JSON with bounded public fields when `--json` is selected. A clean result SHALL distinguish structural installation state from runtime content identity and online freshness. Without opening the network or executing validation, its recommended action SHALL emit a shell-quoted command that uses the current repository's validator, passes the observed target with `--skills-root`, and includes `--profile runtime --strict --check-updates`; it SHALL NOT depend on an older target-side validator or imply that reinstalling is the only way to observe freshness. If the repository validator is absent or the exact path cannot be represented as a safe shell command, status SHALL emit an honest fallback rather than a dead command. Non-clean states SHALL retain their existing action without inspecting the validator path. The guidance SHALL preserve that byte equality is not installation provenance, legal-source freshness, or filing readiness.

#### Scenario: Human clean result

- **WHEN** a user requests status without `--json`
- **THEN** the output explains the observed structural state, canonical skill count, executable repo-side runtime update-check command for the exact target, and read-only unlocked boundary in plain Russian

#### Scenario: JSON clean result

- **WHEN** automation requests clean status with `--json`
- **THEN** the stable report shape and exit code remain unchanged while `message` says content and freshness were not checked and `recommended_action` names an existing repo-side validator, the exact `--skills-root`, and `--profile runtime --strict --check-updates`

#### Scenario: Repo-side validator is absent

- **WHEN** status is invoked from a detached tool copy without the canonical validator beside it
- **THEN** recommended action says the validator is unavailable and directs the user to update the repository without emitting a nonexistent command

#### Scenario: Target path contains surrogateescaped bytes

- **WHEN** a clean POSIX target contains filesystem bytes that cannot be represented as ordinary Unicode command arguments
- **THEN** recommended action says a safe command cannot be formed and emits no misleading command for a different path

#### Scenario: Status remains offline

- **WHEN** clean status renders the runtime freshness recommendation
- **THEN** status itself invokes no network opener, validator, installer, subprocess, write, recovery, or lock operation

#### Scenario: JSON result

- **WHEN** automation requests status with `--json`
- **THEN** stdout contains one JSON object with schema version, status, severity, exit code, bounded stable reason code, target, target existence, managed-skill summary, optional transaction summary, message, recommended action, and an observation boundary declaring `explicit_mutations_performed=false`, `filesystem_access_time_updates_possible=true`, and `atomic_snapshot=false`

#### Scenario: Sensitive journal details

- **WHEN** a journal contains content identities and per-skill progress
- **THEN** status does not emit digests, journal bodies, old content, arbitrary unknown entry names, raw exceptions, or unrelated target entries

#### Scenario: Target contains surrogateescaped bytes

- **WHEN** a POSIX target argument contains bytes represented internally as unpaired surrogate code points
- **THEN** JSON and human stdout remain valid UTF-8 and render those bytes as bounded printable escapes

#### Scenario: Human recovery phase

- **WHEN** human output describes a pre-journal, building, prepared, rollback, committed, or cleanup phase
- **THEN** it uses a concise Russian phrase rather than the internal phase enum
