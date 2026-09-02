## ADDED Requirements

### Requirement: Explicit current-release verification has stable outcomes

The public installer SHALL provide `--verify-current` as an explicitly online, non-installing route that first applies the existing offline status preflight, then validates the complete runtime target and compares its exact runtime identity with the manifest at the immutable SHA resolved from canonical `main`. It SHALL use the repository-side validator with runtime, strict, update-check, and current-required modes. After existing validation failures take precedence, the process SHALL return `0` for `current`, `10` for `different`, and `20` for `unknown`. It SHALL preserve that equality is not installation provenance, legal-source freshness, or filing readiness.

#### Scenario: Human current verification

- **WHEN** a user runs `install.sh --verify-current [--target PATH]`
- **THEN** the command performs no installation or recovery and prints the existing Russian runtime/freshness report for the exact target

#### Scenario: Exit-code automation

- **WHEN** automation runs `--verify-current` for a structurally clean target
- **THEN** the exit code distinguishes current, different, unknown, validation failure, and usage failure without parsing prose

#### Scenario: Explicit network boundary

- **WHEN** neither `--verify-current` nor the internal `--check-updates` flag is selected
- **THEN** installation and status do not initiate the freshness network lookup

#### Scenario: Unsafe or incomplete target

- **WHEN** the selected target is missing, structurally incomplete, a symlink, `/`, HOME, a file, or otherwise non-clean under the read-only status contract
- **THEN** current verification returns local prerequisite failure `1` before invoking the validator network lookup

#### Scenario: Known content difference

- **WHEN** runtime validation passes and the local identity differs from the immutable remote manifest identity
- **THEN** the report remains `freshness.status=different` and current-required mode returns `10` without calling the installer

#### Scenario: Incomplete freshness evidence

- **WHEN** runtime validation passes but remote SHA or manifest evidence cannot be established
- **THEN** the report remains `freshness.status=unknown` and current-required mode returns `20`, never `0`

#### Scenario: Existing validation failure takes precedence

- **WHEN** runtime validation fails or strict warnings exist
- **THEN** the existing validation code is returned before freshness-specific codes

#### Scenario: Target changes during the network window

- **WHEN** a candidate-current local tree changes after its first identity pass and before the post-network identity pass
- **THEN** the report fails with `RUNTIME_IDENTITY_CHANGED`, freshness is `unknown`, and no `current` success is emitted

#### Scenario: Target root is replaced during verification

- **WHEN** the lexical runtime root is replaced, rebound, or converted to a symlink after preflight
- **THEN** current-required validation fails with `RUNTIME_ROOT_CHANGED` and cannot return `0`

#### Scenario: Invalid option combinations

- **WHEN** `--verify-current` is combined with `--status` or `--json`, `--json` is used without `--status`, or validator `--require-current` lacks its required runtime update-check scope
- **THEN** the relevant CLI exits with usage code `2` before installation or freshness success is reported

## MODIFIED Requirements

### Requirement: Status output serves people and automation

Status SHALL provide concise Russian human output by default and deterministic JSON with bounded public fields when `--json` is selected. A clean result SHALL distinguish structural installation state from runtime content identity and online freshness. Without opening the network or executing validation, its recommended action SHALL emit a shell-quoted absolute `<repo>/install.sh --verify-current --target <exact target>` command from the current repository; it SHALL NOT depend on an older target-side validator or imply that reinstalling is the only way to observe freshness. If the repository entry point is absent, non-executable, symlinked, or any command value contains non-printable/control/surrogateescaped characters, status SHALL emit an honest fallback rather than a dead or visually spoofable command. Non-clean states SHALL retain their existing action without inspecting the entry point. The guidance SHALL preserve that byte equality is not installation provenance, legal-source freshness, or filing readiness.

#### Scenario: Human clean result

- **WHEN** a user requests status without `--json`
- **THEN** the output explains the observed structural state, canonical skill count, executable short current-verification command for the exact target, and read-only unlocked boundary in plain Russian

#### Scenario: JSON clean result

- **WHEN** automation requests clean status with `--json`
- **THEN** the stable report shape and exit code remain unchanged while `message` says content and freshness were not checked and `recommended_action` names an existing repo-side installer, `--verify-current`, and the exact `--target`

#### Scenario: Repo-side entry point is absent

- **WHEN** status is invoked from a detached tool copy without the canonical installer beside it
- **THEN** recommended action says the verification entry point is unavailable and directs the user to update the repository without emitting a nonexistent command

#### Scenario: Repo-side entry point is not executable

- **WHEN** the canonical installer exists but cannot be executed by the current process
- **THEN** status emits the same honest fallback and no dead shell command

#### Scenario: Target path contains surrogateescaped bytes

- **WHEN** a clean POSIX target contains filesystem bytes that cannot be represented as ordinary Unicode command arguments
- **THEN** recommended action says a safe command cannot be formed and emits no misleading command for a different path

#### Scenario: Target path contains display control characters

- **WHEN** a clean target spelling contains newline, carriage return, tab, escape, or another non-printable character
- **THEN** recommended action emits one fixed fallback without interpolating the path or a spoofable command line

#### Scenario: Status remains offline

- **WHEN** clean status renders the short current-verification recommendation
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
