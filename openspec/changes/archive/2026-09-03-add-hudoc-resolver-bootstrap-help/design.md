## Context

Each bundled resolver is a trust wrapper rather than the HUDOC search engine.
It either uses an exact direct CLI path or an explicitly named `ks_parser`
repository and compatible worktree. When configured, it validates version
constants and replaces itself with the external CLI while forwarding every
argument. When unconfigured, even `--help` reaches the terminal missing-engine
error.

## Goals / Non-Goals

- Goals:
  - make first-run configuration discoverable through exact local help;
  - keep the distinction between wrapper setup help and actual engine help
    explicit;
  - ensure local help performs no candidate, filesystem, Git, or exec work;
  - preserve every configured and non-help fail-closed branch.
- Non-Goals:
  - bundle or emulate the HUDOC engines or their search arguments;
  - auto-discover a repository from HOME, cwd, Git metadata, or another skill;
  - accept help when configuration is explicitly present but broken;
  - change expected indexer, evaluator, research, knowledge, or privacy versions;
  - change the candidate ordering, process environment, or legal promotion gates.

## Decisions

### Gate local help on absence, not value

At the first line of each `main()`, the wrapper recognizes local bootstrap help
only if its direct-CLI environment key and `HUDOC_KS_PARSER_REPO` are both absent
from `os.environ`, and argv is exactly `[-h]` or `[--help]`. Presence with an
empty or whitespace value is intentional configuration evidence and therefore
continues through `configured_path()` to the existing explicit error. This
prevents bootstrap help from masking a typo, stale path, or incompatible engine.

### Keep help exact and non-delegating

Each wrapper owns a stable Russian help string naming its exact direct variable,
CLI relative path, repository variable, and required versions. It states that
the local text covers setup only and that the configured engine provides its
actual command help. The local branch prints once to stdout and returns before
`candidates()`, path resolution, Git worktree enumeration, version reads, or
`execve()`.

An exact help flag with another token is not bootstrap help. With no
configuration it retains the ordinary missing-engine failure; with
configuration it is forwarded only after the existing compatibility gates.

### Leave configured delegation untouched

All non-bootstrap paths enter the existing body. A compatible direct or
repository candidate still receives the original `sys.argv[1:]` unchanged.
Blank, missing, incompatible, or old-version configured candidates retain their
current errors and no-fallback rules.

## Risks / Trade-offs

- Exit `0` for unconfigured exact help confirms only that setup guidance was
  displayed; it does not confirm engine availability, corpus coverage, or any
  legal authority. The help text states this explicitly.
- Bootstrap help does not enumerate engine subcommands because that would
  duplicate and drift from an external versioned interface. Users repeat
  `--help` after configuration to receive authoritative engine help.

## Verification

The regression suite binds literal help output for both wrappers and both help
flags, poisons candidate discovery/Git/exec in direct `main()` tests, and uses
real subprocesses from an unrelated cwd. Separate cases preserve unconfigured
no-argument failure, combined-help failure, blank/invalid configuration errors,
old-version rejection, and exact configured argv forwarding. Full source,
runtime, clean-install, manifest, and offline gates remain required.
