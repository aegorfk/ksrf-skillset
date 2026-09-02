## Context

The practice-analysis CLI already renders Russian scaffolding and command
descriptions, and its integration guide treats `--help` as the primary command
reference. Nevertheless, only 6 of 42 public argument actions have authored
help. The remaining 36 are concentrated in 11 operational routes and include 21
paths to files, folders, or workspaces.

## Goals / Non-Goals

**Goals:**

- Make every public argument self-explanatory in Russian at the route where it
  is used.
- Distinguish a matter workspace, the nested practice-analysis state folder,
  source workspaces, input artifacts, and optional export files.
- Explain omission behavior and defaults without changing them.
- State human-review and audit-only boundaries where an option crosses an
  evidence or trust gate.
- Prove the installed help and parser contract exhaustively.

**Non-Goals:**

- Do not rename machine tokens, options, choices, destinations, JSON keys, or
  artifact types.
- Do not redesign the workflow, change validation, relax trust checks, or grant
  filing authority.
- Do not document judicial-meaning or maintainer CLIs in this change.
- Do not turn help into a full tutorial; keep detailed methodology in the skill
  references.
- Do not repair the pre-existing public/private claim-ID binding defect in
  `wording review`; isolate that behavior change in the next OpenSpec change.

## Decisions

### Help lives on each argument declaration

Each public `add_argument()` receives authored Russian help. Shared wording may
be factored into local constants only when the runtime semantics are identical.
The existing help-only metavar formatter remains responsible solely for Russian
presentation and continues to restore parser state in `finally`.

### Describe the actual data boundary

Path options identify whether they accept a matter workspace, a judicial-
meaning workspace, a trusted source workspace, an input JSON/document, or an
optional export. Explanations do not imply that a path is trusted merely because
it was supplied.

### Explain omission and gate behavior

Help states when omitted `--claim-id` values select the eligible set, how
`--skills-root` is discovered, when `--output` adds a copy rather than replacing
workspace state, and when missing trusted provenance leaves imported material
audit-only. Human decisions remain explicit machine tokens with Russian
meanings.

### Exhaustive contract test

Source QA recursively inventories all 18 routes and all 42 public argument
actions. It fails if any public action has absent, blank, or non-Russian help.
The same routes are invoked from a clean installed payload. Existing snapshots
continue to pin parser defaults, handlers, choices, program labels, usage,
state restoration, and exact non-help diagnostics.

### Preserve atomic tokens in narrow terminals

`format_help()` temporarily selects a help-only formatter which supplies the
Russian usage prefix before wrapping and disables wrapping inside a path,
identifier, date format, or option value. At 60–80 columns it uses a bounded
continuation indent so atomic tokens still fit. The original formatter and every temporary
metavar are restored in `finally`, so `format_usage()`, parsing, diagnostics,
and non-help state remain byte-for-byte compatible.

## Risks / Trade-offs

- [Help drifts from runtime behavior] → Derive wording from the consuming
  handler and assert high-risk defaults/boundaries with route-specific phrases.
- [Repeated workspace wording becomes inconsistent] → Use one precise phrase
  for matter workspace and explain the nested practice-analysis folder once per
  consuming route.
- [A help edit changes parsing] → Keep edits to `help=` only and retain the exact
  machine-contract SHA and non-help digest.
- [Source help passes but installed payload differs] → Invoke every route after
  a clean manifest-driven installation.
- [A readable token is split at a hyphen] → Exercise all installed routes at
  every width from `COLUMNS=60` through `COLUMNS=80`, reject split tokens, and
  bound every rendered line.

## Migration Plan

1. Record the 18-route, 42-action baseline and add a failing completeness test.
2. Add argument-level explanations and targeted semantic assertions.
3. Run focused, full, strict source/runtime, clean-room, OpenSpec, quick skill,
   shell, and independent review checks.
4. Archive, regenerate the manifest against exact live `main`, publish one
   atomic commit, and install that exact release globally.
