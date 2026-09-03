# ksrf-doctor-exit-status Specification

## Purpose
TBD - created by archiving change align-doctor-exit-status. Update Purpose after archive.
## Requirements
### Requirement: Capability doctor exit status matches top-level usability

The installed `ksrf.py doctor` command and `ksrf_setup_doctor.py` launcher MUST
return a process code that reflects the existing top-level capability-report
state without requiring callers to parse prose or reimplement classification.
The mapping MUST use only the final top-level state and MUST NOT change probe
execution, capability requirements, report contents, or remediation authority.

#### Scenario: Ready and degraded profiles remain usable

- **WHEN** a valid doctor run produces top-level state `ready` or `degraded`
- **THEN** both public launchers return code `0`
- **AND** emit the complete selected human or JSON report on stdout with empty
  stderr
- **AND** optional unavailable, unknown, or interactive capabilities do not
  become hard failures unless the existing classifier makes the profile
  `blocked`

#### Scenario: Blocked profile is not a process success

- **WHEN** a valid doctor run produces top-level state `blocked`
- **THEN** both public launchers return code `3`
- **AND** emit the complete actionable human or JSON report on stdout with
  empty stderr
- **AND** do not install, configure, transmit, or otherwise remediate anything

#### Scenario: Unknown top-level usability fails closed

- **WHEN** a valid report unexpectedly has a top-level state other than
  `ready` or `degraded`
- **THEN** the doctor command returns code `3`
- **AND** does not reinterpret that state as readiness

#### Scenario: Input and contract errors stay distinct

- **WHEN** doctor arguments or a capability manifest violate the existing
  input contract
- **THEN** both launchers retain code `2` and the existing error channel
- **AND** no partial success report is emitted

#### Scenario: Source and installed launchers agree

- **WHEN** the same manifest and profile are checked through source-tree and
  clean-installed copies of `ksrf.py doctor` and `ksrf_setup_doctor.py`
- **THEN** state, process code, stdout/stderr placement, and no-side-effect
  boundaries are identical apart from expected timestamps and paths

### Requirement: Doctor exit status contract is discoverable in command help

The installed `ksrf.py doctor --help` command and `ksrf_setup_doctor.py --help` launcher MUST explain the stable process-code mapping in Russian without
requiring repository documentation. The explanation MUST associate `0` with
`ready` or `degraded`, `2` with invalid arguments or capability-manifest input,
and `3` with `blocked` or an unrecognized report state. It MUST also state that
a blocked report remains on stdout and that the command does not install or
repair capabilities automatically.

#### Scenario: User discovers all process outcomes from either launcher

- **WHEN** a user invokes either doctor help route from a clean installation
- **THEN** stdout explains codes `0`, `2`, and `3` and their corresponding
  outcomes in Russian
- **AND** the help exits `0` with empty stderr

#### Scenario: Help matches the runtime contract

- **WHEN** release QA compares the help guide with deterministic `ready`,
  `degraded`, `blocked`, invalid-input, and unknown-state checks
- **THEN** the documented mapping equals the process behavior
- **AND** the help does not claim filing readiness, installation, or automatic
  remediation
