## Context

Each affected script is a portable file launcher rather than an installed
console-script entry point. Python therefore places the script directory first
in `sys.path`. The launchers currently conditionally insert their resolved
sibling `lib/` path. Presence is not precedence: an existing later entry causes
the insertion to be skipped. This is immediately observable for
`judicial_meaning.py` and `ksrf.py`, whose filenames collide with the packages
they import, and it also permits an earlier ambient `ksrf` package to own the
other two launchers' imports.

## Goals / Non-Goals

- Goals:
  - deterministically import the package shipped beside each launcher;
  - keep launch behavior independent of current working directory;
  - preserve all non-owned path entries and all CLI behavior;
  - prove the behavior in real subprocesses, including the installed payload.
- Non-Goals:
  - sanitizing or disregarding the user's entire `PYTHONPATH`;
  - defending against arbitrary code executed by Python before launcher
    bootstrap;
  - renaming packages, changing public command paths, or introducing packaging
    and third-party dependencies.

## Decisions

### Normalize only the launcher-owned path

Each launcher computes its existing resolved `lib/` path, removes every exact
string occurrence of that one path from `sys.path`, and inserts it once at index
zero before the owned package import. This fixes presence-versus-precedence,
avoids duplicate owned entries, and leaves every other entry byte-for-byte and
in the same relative order.

### Apply the invariant to all four sibling-lib launchers

The change covers the complete current runtime pattern, not only the two files
whose names collide with their packages. Otherwise the filing-pack and doctor
wrappers would still select an unrelated `ksrf` package placed earlier by an
ambient checkout.

### Exercise the actual file entry points

Regression tests invoke the scripts with `subprocess`, a temporary working
directory, and explicit `PYTHONPATH` values. The red cases include the real
bundled path already present and a poison package before that path. Assertions
require successful help from the bundled implementation and reject the poison
sentinel. Existing CLI-contract suites remain the authority for exact public
help and non-help behavior.

## Risks / Trade-offs

- A user who intentionally expected another checkout's `ksrf` or
  `judicial_meaning` package to override an installed file launcher will no
  longer get that override. A portable launcher should own the code shipped in
  its same skill, so deterministic ownership is the safer contract.
- Exact-string removal does not canonicalize every symlink-equivalent path.
  The resolved canonical bundled path is still inserted first, so equivalent
  later entries cannot win package resolution and need not be mutated.

## Migration Plan

No workspace or artifact migration is required. Publish one atomic skillset
release, install its manifest-covered runtime, and verify the clean installed
launchers under the same adversarial environments.
