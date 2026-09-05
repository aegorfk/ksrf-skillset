## ADDED Requirements

### Requirement: Structured publication recovery is explicit, private, and install-portable

Russian help for the three installed native publisher commands MUST expose the exact
`--recovery-diagnostic-json` option on `quality coding-audit-prepare`,
`quality coding-audit-review-import`, and `quality coding-audit-finalize`. It SHALL
explain that the option changes
only classified publication-recovery stderr into one canonical JSON line; ordinary
errors and successful results are unchanged; stdout from a confirmation-delivery
failure remains invalid even if it appears complete; and the JSON can contain private
entry names and device/inode coordinates required for administrator recovery.

Help SHALL distinguish only `administrator_only` and
`repeat_then_compare_candidate`. It SHALL state that the latter is a candidate route,
not automatic permission: the user must preserve inputs/results, repair the external
fault, use a new absent sibling, obtain a normal successful repeat, and use the
applicable comparison procedure. It SHALL state that the diagnostic authenticates no
provenance or person, verifies no legal conclusion or current law, makes no artifact
public-safe, and grants no publication or filing authority.

#### Scenario: Each publisher documents the exact opt-in boundary

- **WHEN** the user invokes help for any of the three publisher commands
- **THEN** the Russian help names `--recovery-diagnostic-json`, stderr-only output,
  both closed routes, invalid confirmation stdout, the private-coordinate warning,
  and the fixed no-action and no-authority scope
- **AND** the option has no alias, abbreviation, environment default, output-file
  target, or effect on ordinary errors and successful paths

#### Scenario: Source and installed behavior agree

- **WHEN** equivalent deterministic recovery, ordinary-error, success, and incomplete
  cases run from the source launcher and a clean installed launcher
- **THEN** process codes and stdout are equal and both launchers emit byte-identical
  structured stderr or default human stderr as applicable
- **AND** the installed schema validates the structured line without installed tests,
  evals, OpenSpec, or maintainer-only files

#### Scenario: Parser faults do not masquerade as recovery diagnostics

- **WHEN** the new option is abbreviated, given a value, or used outside its three
  exact publisher routes
- **THEN** argparse returns code `2` before handler entry with its ordinary parser
  diagnostic
- **AND** no structured recovery JSON is emitted and no input or output path is opened
