## Context

The verifier exposes reusable validation functions and a small executable
`main()`. Its constants intentionally derive the skills root from the installed
script location. The current `main()` never observes `sys.argv`, so every token
is silently discarded and the ordinary success sentence can be mistaken for a
successful execution of an option that does not exist.

## Goals / Non-Goals

- Goals:
  - make the accepted command grammar explicit and fail closed on every other
    token before the policy scans the filesystem;
  - provide an exact Russian help path that performs no validation;
  - preserve byte-for-byte no-argument stdout and existing validation exit
    semantics;
  - leave the installed runtime tree unchanged on help, argument failure, and
    ordinary verification;
  - keep repository-side imports and explicit-root function calls compatible.
- Non-Goals:
  - add `--skills-root`, strictness, network, JSON, or package-selection flags;
  - replace the repository-side `install.sh --verify` trust boundary;
  - change any offline policy rule or legal/release-readiness claim.

## Decisions

### Parse a closed grammar before validation

`main(argv=None)` receives an optional argument sequence for deterministic
tests and otherwise reads the process arguments. The parser accepts only an
empty sequence or exactly one of `-h` and `--help`; option abbreviation is
disabled. Every other sequence is routed to a Russian usage error with exit
code `2`. This explicit precheck also prevents `--help` followed by an unknown
token from exiting successfully before the unknown token is noticed.

Argument handling completes before calling
`validate_offline_self_containment()` or enumerating skill directories. Help
therefore describes the command without turning a documentation request into a
potentially expensive or misleading verification run.

The bundled validator remains bound at module import time because the trusted
repository-side coordinator temporarily injects that exact module while it
loads this policy. Direct script execution temporarily suppresses bytecode
generation around the sibling import and then restores the interpreter flag;
this prevents `scripts/__pycache__` from appearing without weakening that
binding or imposing a process-global setting on importers.

### Keep the installed script self-relative

No target-selection argument is introduced. The direct installed fallback
continues to validate the runtime that owns the script. A caller that needs an
explicit target must use the trusted repository-side installer coordinator,
which owns the target preflight/postflight contract and imports the validation
function directly.

### Preserve the no-argument contract

Once an empty argument list is accepted, the existing validation body and
rendering run unchanged. Existing success/failure wording, stdout placement,
and return codes `0` and `1` remain stable. Parser failures use stderr and code
`2`; exact help uses stdout and code `0` without printing a verification result.

## Risks / Trade-offs

- Scripts that accidentally supplied ignored arguments will now fail. This is
  intentional because their previous green result did not establish the
  requested behavior.
- The direct fallback remains narrower than the repository-side verifier. The
  help text points users to `install.sh --verify --target PATH` instead of
  duplicating its stronger coordination contract.

## Verification

Tests invoke `main(argv)` with the validation function replaced by a sentinel
and path enumeration replaced by a second sentinel; either would fail if help
or an argument error reached the scan. Full literal oracles bind Russian help
and error bytes. Real subprocess checks additionally bind exit codes,
stdout/stderr, and an unchanged installed-tree snapshot without relying on
`PYTHONDONTWRITEBYTECODE`. The ordinary no-argument success and findings output
are compared to the pre-change contract. Full source, runtime, clean-install,
manifest, and offline suites remain required.
