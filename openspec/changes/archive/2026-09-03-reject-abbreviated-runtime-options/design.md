## Context

The installed skillset exposes several independent `argparse` command trees.
Their Russian help lists exact option tokens, but the parser default
`allow_abbrev=True` accepts unique prefixes that are absent from that help. The
problem is especially visible on `ksrf.py matter init`: abbreviated identifiers
and workspace options reach the real handler and create a complete workspace.

## Goals / Non-Goals

- Goals:
  - require exact spelling for every long option in public installed CLIs;
  - apply the rule recursively to nested subparsers;
  - reject an abbreviated option before any handler or side effect;
  - preserve all exact command, option, help, JSON, and execution contracts;
  - distinguish a proper `--help` prefix, with or without `=VALUE`, from
    unrelated dash-prefixed paths in the legacy single-path argument validator.
- Non-Goals:
  - rename commands or options;
  - translate or otherwise redesign parse-error text in this release;
  - change short-option behavior, aliases, defaults, or positional values other
    than bare proper prefixes of a declared long option;
  - infer a likely intended option or automatically retry a typo.
  - reinterpret opaque argv delegated by the HUDOC resolver wrappers to a
    separately configured, version-checked external engine.
  - change the source-only `add_reference_tocs.py` maintainer utility, which is
    explicitly excluded from the installed runtime manifest.

## Decisions

### Enforce the invariant in parser classes

Each public custom `ArgumentParser` class will force
`allow_abbrev=False` in its constructor. `add_subparsers()` uses the current
parser type as its default `parser_class`, so nested parsers constructed from
that class inherit the same invariant. Public one-level parsers without a
custom class will receive the same explicit setting or a minimal equivalent
class.

Setting the value only on a root parser is insufficient because child parsers
otherwise retain the library default. Source QA will recursively inspect the
actual parser objects and require `False` at every reachable route.

### Treat unknown prefixes as errors, not compatibility aliases

Only declared option strings are part of the public contract. A unique prefix
that happened to work was undocumented, could change meaning when another
option is added, and is unsafe on commands that write files. It will now take
the ordinary parse-error path with code `2`. No handler may run, even when all
required values could otherwise be inferred.

### Keep exact invocations byte-compatible

The implementation changes parser configuration wherever runtime parsing uses
`argparse`. The legacy argument-research validator manually handles its one
path token and builds an `argparse` parser only for help, so it additionally
rejects only proper prefixes of `--help`, either bare or before `=VALUE`, before
file access. It does not treat unrelated dash-prefixed names as options. Exact
long options, short options,
choices, defaults, aliases, destinations, help output, normal stdout/stderr,
JSON fields, and handler results remain unchanged. Tests compare the recursive
parser inventory and execute successful exact `matter init` and dash-prefixed
path controls alongside the rejected abbreviation cases.

## Risks / Trade-offs

- A user script relying on an undocumented unique prefix will stop with a
  parse error. This is intentional: the full option shown by `--help` is the
  stable interface.
- Error wording differs across supported Python versions. The safety contract
  therefore binds the exit code, empty success output, and lack of side effects
  without introducing a new translation layer in this release. A separate case
  with every required option present binds the remaining abbreviated token in
  stderr; the dual-abbreviation case may report the missing declared options
  first.

## Verification

Tests first reproduce a successful abbreviated `matter init` and its writes.
The green suite then proves that the same source and clean-installed invocation
returns `2`, emits no stdout, and leaves the target and its parent snapshot
unchanged. A second invocation supplies every required exact option plus one
abbreviated optional token and requires that token in stderr. Recursive parser
inspection covers all eight installed parser modules, while exact-option and
declared-alias controls preserve successful execution and the existing
help-contract digests. Source and clean-installed subprocess checks prove that
the manual argument validator rejects `--he` and `--he=case.json` before
reading them but continues to validate unrelated dash-prefixed paths, including
names containing `=`. Full root/skill, strict source/runtime, offline, manifest,
clean-install, and publication checks remain required.
