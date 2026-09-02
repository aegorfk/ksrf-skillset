## Context

The runtime payload is location-independent as data, but several command examples still rely on prose placeholders or one fixed default installation. These examples are user-facing executable interfaces and must survive custom `--target`, `CODEX_HOME`, spaces in paths and an unrelated working directory. Separately, the HUDOC wrapper scripts launch code that is intentionally not bundled; implicit discovery of a nearby repository makes provenance and version selection depend on ambient machine state.

## Goals / Non-Goals

Goals:

- make every documented bundled command copyable after default or custom installation;
- give users one stable root variable and a shell-safe installer hint;
- reject unresolved placeholders before a release or installed payload is treated as clean;
- make external HUDOC code selection explicit, deterministic and actionable when unconfigured;
- retain all command tails, version pins, worktree behavior and legal stop rules.

Non-goals:

- bundle the HUDOC engine or the `ks_parser` repository;
- edit shell profiles, persist environment variables or select a repository for the user;
- change CLI semantics, arguments, outputs or legal methodology;
- treat successful path resolution as source, legal, publication or filing authority.

## Decisions

1. **One documented root expression.** Runtime examples use `KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"`, and every script path is double-quoted. An existing explicit `KSRF_SKILLS_ROOT` wins, then `CODEX_HOME`, then the normal home-directory default.
2. **Installer informs but does not persist.** After an exact install, `install.sh` prints one shell-escaped `export KSRF_SKILLS_ROOT=...` using the resolved target. It never changes `.zshrc`, `.bashrc` or another profile.
3. **Installed programs are probeable.** `ksrf.py` follows the existing bundled wrappers: prepend its sibling `lib` directory and import `ksrf.filing.cli`; repository-only `src` is not a runtime dependency. `validate_argument_research.py` recognizes `-h|--help` before reading an input path, so every unique documented CLI has a non-mutating zero-exit smoke probe.
4. **Preserve command meaning.** Tests inventory all 51 affected user-facing invocations, including the 49 installed-runtime commands and two public README commands, and compare the suffix beginning at the bundled script path, including subcommands and options, before and after the rewrite.
5. **Explicit HUDOC selection.** `HUDOC_KB_CLI` or `HUDOC_VECTOR_CLI` names the exact executable and has priority. Otherwise `HUDOC_KS_PARSER_REPO` is required and may resolve the configured root or one of its Git worktrees. Without either setting, launchers fail closed with an actionable message; they never inspect HOME or the current working directory.
6. **External boundary stays visible.** Runtime guidance says the HUDOC engine is not bundled and that an unconfigured resolver is a capability gap, not evidence that no relevant HUDOC material exists.
7. **Portable enforcement.** The shared validator and offline verifier reject unresolved `<skill-dir>`, `<skill-root>`, literal install-root placeholders, fixed `~/.codex/skills` command paths and implicit HOME/cwd repository discovery in runtime-eligible artifacts. Marker constants remain self-scannable through construction rather than file exemptions.
8. **No authority inference.** Passing the command-path gate proves only deterministic path resolution. Existing official-source, citation, privacy, human-review and filing gates remain unchanged.

## Risks / Trade-offs

- **Repeated root assignment adds visual weight** → use one identical two-line preamble per independently copyable code block and test exact consistency.
- **Custom targets contain spaces or quotes** → quote every expansion and have the installer render the resolved path with POSIX shell escaping.
- **Existing HUDOC users relied on ambient discovery** → provide an actionable error naming both supported variables and preserve configured root/worktree search.
- **Validator flags explanatory examples** → scope findings to executable command/root patterns and keep adversarial fixtures source-only.
- **Command rewrite changes an option accidentally** → compare normalized command tails and pin the seven CLI set.

## Migration Plan

1. Freeze live SHA, manifest and the exact 51-command inventory split into 49 installed-runtime and two public README invocations.
2. Record and strictly validate this OpenSpec change.
3. Add failing root, portable and HUDOC resolver regressions.
4. Rewrite runtime commands, installer output, authority link and HUDOC resolution.
5. Add shared command-path validation and offline parity, then regenerate the manifest.
6. Run focused/full suites, source strict, clean-room install into a path with spaces, runtime strict, OpenSpec strict and independent review.
7. Commit on the isolated branch, merge to `main`, confirm remote SHA, install and validate the exact payload.
8. Archive the change, regenerate the manifest from the merge SHA and publish the final evidence commit.

Rollback is a normal revert of the atomic release. No user data or external HUDOC repository is modified.
