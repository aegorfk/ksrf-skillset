## Context

The remaining documented commands are `judicial_meaning.py`, `ksrf.py`,
`ksrf_setup_doctor.py`, `ksrf_autocollect.py`, `ksrf_practice_analysis.py`, and
`validate_argument_research.py`. Their descriptions are mostly Russian, but the
default parser scaffolding and generated metavariables are English. Several
descriptions also expose implementation jargon such as `supplemental`,
`frozen plan`, `bounded status`, `matter workspace`, and `per-claim gate`.

## Goals / Non-Goals

**Goals:**

- Make every reachable `--help` route in these six commands consistently
  Russian.
- Translate only presentation-time scaffolding and metavariables so parser
  state and non-help diagnostics stay unchanged.
- Preserve all command names, aliases, option strings, choice values, defaults,
  hidden switches, JSON fields, stdout/stderr placement, and exit codes.
- Verify installed runtime output rather than source literals alone.

**Non-Goals:**

- Do not rename English machine tokens or JSON/schema identifiers.
- Do not expose suppressed fixtures or maintainer switches.
- Do not translate runtime validation payloads or legal artifact contents in
  this release.
- Do not claim that every currently undocumented option receives a tutorial;
  fuller task guidance can be added as a separate incremental release.

## Decisions

### Help-only parser state

Each owning CLI receives a local bounded parser subclass. During
`format_help()` it temporarily substitutes Russian metavariables, renders help,
and restores every action in `finally`. Stable `argparse` headings and the
built-in help sentence are translated in the rendered string. `format_usage`,
`error`, and parsing behavior remain untouched so non-help diagnostics retain
their exact prior contract.

The manual argument-research validator keeps its existing non-help usage line
and emits a separate Russian help string only for `-h` and `--help`.

### Recursive route inventory

Source QA walks every nested subparser tree, including public aliases, to form
an explicit route inventory. A clean installation is then invoked for every
route. This catches regressions in deeply nested judicial-meaning, practice,
cache, quality, and matter commands without hand-selecting only easy examples.

### Plain Russian descriptions

Existing user-visible descriptions that contain implementation jargon are
rewritten in plain Russian. Executable tokens remain visible where the user
must type them; machine identifiers and choice values are not translated.

## Risks / Trade-offs

- [Temporary metavar mutation leaks into parser behavior] → Restore all actions
  in `finally` and assert parser-state equality before/after help plus exact
  non-help diagnostics.
- [A nested route is missed] → Recursively enumerate parser choices and assert
  stable route counts and canonical command families.
- [String replacement differs across Python versions] → Test current Python and
  a clean installed payload under `/usr/bin/python3` when present, including
  all 42 routes supported by that interpreter and the legacy `optional
  arguments:` heading. The 63 judicial-meaning routes are tested under the
  current interpreter but explicitly excluded from Python 3.9: the unchanged
  baseline imports `typing.TypeGuard`, which is unavailable there. This change
  does not broaden the skill's Python-version support.
- [Machine tokens are translated accidentally] → Assert command, alias, option,
  choice, default, destination, program label, parser defaults, handler, and
  `format_usage()` projections against the base contract.

## Migration Plan

1. Record the complete route/parser-state baseline and add red clean-runtime
   help tests.
2. Add help-only Russian formatters and plain-language description fixes.
3. Run focused, full, strict source/runtime, clean-room, OpenSpec, shell, quick
   validation, and independent review checks.
4. Archive, regenerate the manifest from the exact live `main`, publish one
   atomic commit, and install that exact release globally.
