## ADDED Requirements

### Requirement: Doctor help explains automation outcomes consistently

The public doctor help MUST present its process outcomes as one concise Russian
guide shared by `ksrf.py doctor` and `ksrf_setup_doctor.py`. Source-tree and
clean-installed help MUST be equivalent apart from executable paths, and the
guide MUST remain available under the supported Python runtimes.

#### Scenario: Shared source and installed help remain aligned

- **WHEN** both public launchers are invoked with `--help` from the source tree
  and a clean installation
- **THEN** each output contains the same `0`/`2`/`3` guide, exits `0`, and writes
  no stderr
- **AND** command names, options, defaults, JSON, non-help stdout/stderr, process
  behavior, probes, and filesystem or network effects remain unchanged
