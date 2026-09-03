# Change: Reject unsupported offline-verifier arguments before validation

## Why

The installed fallback command `verify_offline_self_containment.py` currently
ignores every command-line argument. A typo such as `--strcit`, an unexplained
positional value, or an invented `--skills-root DOES-NOT-EXIST` therefore runs
the embedded-root scan and prints a green result with exit code `0`. That can
mislead a user into believing the requested option or target was honored.

## What Changes

- Define the complete public grammar as either no arguments or exactly one help
  flag (`-h` or `--help`).
- Print concise Russian help and exit `0` without running validation for an
  exact help request.
- Reject every unknown, positional, combined, or misspelled argument with exit
  code `2` on stderr before filesystem validation and without a green result.
- Prevent direct execution from creating Python bytecode artifacts inside the
  installed skill while importing its bundled validation policy.
- Preserve the existing no-argument validation target, findings, success text,
  and exit codes, and preserve the importable validation API used by the
  trusted repository-side installer.
- Do not add an arbitrary target option: `install.sh --verify --target PATH`
  remains the trusted command for an explicitly selected installation root.

## Impact

- Affected runtime: the bundled offline verifier entry point.
- Affected QA: direct parser tests and real subprocess checks in the existing
  offline-containment test module.
- User-visible benefit: misspelled or unsupported commands can no longer look
  like a successful verification, while the established no-argument fallback
  continues to work unchanged and no longer dirties its own installed tree.
