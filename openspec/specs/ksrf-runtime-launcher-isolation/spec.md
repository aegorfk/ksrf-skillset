# ksrf-runtime-launcher-isolation Specification

## Purpose
TBD - created by archiving change pin-runtime-launcher-libraries. Update Purpose after archive.
## Requirements
### Requirement: Portable launchers deterministically own their bundled package

Every KSRF runtime file launcher MUST place the resolved bundled `lib/`
directory at the highest-precedence
`sys.path` position before importing that package. Every exact duplicate of the
owned path MUST be removed, and every non-owned path entry MUST retain its value
and relative order. This contract applies to `judicial_meaning.py`, `ksrf.py`,
`ksrf_filing_pack.py`, and `ksrf_setup_doctor.py`. It does not claim to sandbox
arbitrary Python startup behavior or unrelated ambient imports.

#### Scenario: Bundled library is already present

- **WHEN** a user invokes a same-named file launcher from another working
  directory and `PYTHONPATH` already contains that launcher's bundled `lib/`
- **THEN** the launcher imports the bundled package, completes the requested
  help route, and does not import its own script file as that package

#### Scenario: Ambient package precedes the bundled library

- **WHEN** an unrelated directory containing a colliding package appears in
  `PYTHONPATH` before the already-present bundled `lib/`
- **THEN** each affected launcher selects its own bundled package and never
  executes the ambient package sentinel

#### Scenario: Non-owned search entries are preserved

- **WHEN** launcher bootstrap reorders an already-present bundled path
- **THEN** the bundled path occurs once at index zero and all other `sys.path`
  entries retain their original values and relative order

### Requirement: Entrypoint isolation does not change CLI or legal behavior

The launcher isolation fix MUST NOT rename public scripts, commands, aliases,
options, JSON fields, or package modules; change help text, stdout/stderr, exit
codes, or non-help handler behavior; or bypass any provenance, evidence,
human-review, publication, or filing gate.

#### Scenario: Existing command contracts are compared with the release base

- **WHEN** focused and existing CLI contract suites exercise the four launchers
- **THEN** the only changed behavior is deterministic bundled-package selection
  under a colliding ambient import path

#### Scenario: Clean installed payload is exercised

- **WHEN** the manifest-covered runtime is installed into a clean target and
  the launchers run under the adversarial path environments
- **THEN** every launcher uses only files present in that installed payload and
  succeeds without source-only tests, evals, OpenSpec files, or repository code
