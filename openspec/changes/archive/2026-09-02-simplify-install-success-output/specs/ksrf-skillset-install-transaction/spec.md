## ADDED Requirements

### Requirement: Public installation success output is concise

The public `install.sh` entry point SHALL keep publication verification mandatory
before a canonical-target installation while presenting successful installation
output in concise Russian. It SHALL NOT expose the nested publication verifier's
maintainer sentence, repository identifier, commit SHA, runtime tree digest,
release tree digest, manifest base commit, or internal field labels during an
ordinary successful installation. The direct publication verifier, its JSON
output, and maintainer synchronization route SHALL remain unchanged. Successful
output SHALL appear only after the transaction has committed, exit `0`, and
include the existing concise Russian committed-success result and shell-safe
`KSRF_SKILLS_ROOT` export. It SHALL NOT claim current legal-source freshness,
publication authority, or filing readiness.

#### Scenario: Canonical installation succeeds

- **WHEN** publication verification succeeds and the canonical-target transaction commits
- **THEN** the wrapper exits `0` and stdout contains the concise Russian committed-success result and shell-safe export without the nested verifier sentence, hashes, repository identifier, or internal field labels

#### Scenario: Publication verification refuses

- **WHEN** publication verification returns non-zero before canonical-target installation
- **THEN** the wrapper returns the publication verifier's exact non-zero code, preserves its stderr, does not invoke the installer writer, and prints neither installation success nor the export

#### Scenario: Maintainer invokes publication verifier directly

- **WHEN** a maintainer runs `tools/verify_publication_state.py` directly in human or JSON mode, or uses the maintainer synchronization route
- **THEN** the existing detailed publication evidence and exit semantics remain unchanged

#### Scenario: Separate target succeeds

- **WHEN** a user explicitly installs to a non-canonical `--target`
- **THEN** the existing Russian notice that global skills are unchanged, committed installation result, and shell-safe export remain available without publication hashes
