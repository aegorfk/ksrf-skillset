## Why

The installed payload is now free of maintainer-only coordinates, but 49 runtime command invocations still cannot be copied as written: 42 use `<skill-dir>`, one uses `<skill-root>`, five assign the literal placeholder `/path/to/installed/skills`, and one hard-codes `~/.codex/skills`. Two more public README invocations hard-code that default. The problem therefore spans 51 user-facing invocations in 12 Markdown files and eight bundled command-line programs. Two HUDOC launchers also silently search the current directory and `~/Documents/ks_parser`, so the same installed skill can execute different external code depending on the user's machine.

## What Changes

- Give every bundled-script example in installed guidance and the public README the same quoted, executable root resolution: `KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"`.
- Preserve every documented subcommand, option, continuation and example operand while replacing only the unresolved program path.
- Make `install.sh` print a shell-safe `export KSRF_SKILLS_ROOT=...` for the resolved target without editing the user's shell profile.
- Repair the public `ksrf.py` wrapper so an installed copy imports its bundled `lib/ksrf` package rather than the repository-only `src` package.
- Give the eighth documented CLI, `validate_argument_research.py`, a normal zero-exit `--help` path so all unique user-facing programs can be smoke-tested after installation.
- Fix the broken authority-corpus companion link in `ksrf-argument-patterns/SKILL.md`.
- Make the HUDOC launchers accept only an exact CLI override or an explicitly configured `HUDOC_KS_PARSER_REPO`; remove HOME- and current-directory discovery while preserving repository worktree support, version checks, `PYTHONPATH` and subprocess working directory.
- Add portable source/runtime validation and offline parity for unresolved command roots and implicit external-code discovery.
- Add RED/GREEN command-inventory, clean-room path-with-spaces, HUDOC resolver, link and preservation tests.

## Capabilities

### Modified Capabilities

- `ksrf-runtime-payload-boundary`: installed commands resolve from the actual installation and external integrations cannot silently bind to a maintainer or current-working-directory checkout.

## Impact

- Frozen live base: `be97aff33e0895976fe810b313453362301c0ec7`.
- Runtime baseline: 15 packages / 234 files / 8,022,354 bytes / tree SHA-256 `d3193937fd539c7d4142c05f3312620ddba4a1de6f8f43cce187c23e43ca2654`.
- Release baseline: nine files / 193,459 bytes / tree SHA-256 `afe11148478193f80ef30f8af08beac7ee82d0d2ff747c984dc62f550b613851`.
- Command baseline: 49 unresolved invocations in 11 installed Markdown files plus two fixed-root README invocations, for 51 user-facing invocations in 12 Markdown files covering eight bundled CLIs.
- External-runtime baseline: two HUDOC launchers have implicit HOME and current-directory repository discovery in addition to explicit environment configuration.
- Wrapper baseline: the public README command resolves `ksrf.py`, but the installed wrapper exits before argument parsing because it imports repository-only `src.ksrf` instead of the bundled runtime library.
- Help baseline: seven of eight documented bundled CLIs accept `--help`; `validate_argument_research.py` currently treats it as an input filename and exits with an invalid-input error.
- Final runtime: 15 packages / 234 files / 8,035,436 bytes / tree SHA-256 `5170d0355279f9e13ae3d04aa01dc40f2caf77c52777b0e94bf3ef537ec14856`.
- Final release surface: nine files / 193,585 bytes / tree SHA-256 `58063e5f8096842d433a895f874c6de6b124e52910609e0be34c1d5a4e0a35cd`.
- Final command surface: 51/51 commands use the canonical quoted root across 33 independently copyable blocks; all eight unique CLIs pass clean-room `--help`; unresolved command roots and implicit HUDOC discovery findings are zero.
- No legal holding, authority status, method promotion, admissibility gate, filing authority, user case data or HUDOC interface-version pin changes.
