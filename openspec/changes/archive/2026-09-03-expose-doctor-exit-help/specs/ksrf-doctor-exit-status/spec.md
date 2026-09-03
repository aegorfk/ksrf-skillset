## ADDED Requirements

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
