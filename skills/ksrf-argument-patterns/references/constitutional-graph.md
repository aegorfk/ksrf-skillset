# Constitutional Argument Graph

Portable JSON graph for navigating from facts and norm defects to constitutional articles, patterns, evidence and tools.

## Node Counts

- `automation_hook`: 58
- `constitutional_article`: 31
- `harm_type`: 59
- `ksrf_decision`: 83
- `norm_type`: 69
- `pattern`: 20

## Edge Counts

- `can_be_saved_by`: 20
- `has_anchor`: 160
- `may_trigger`: 153
- `reinforces_with`: 49
- `remedy_with`: 20
- `supported_by`: 60
- `uses_article`: 87

## How To Use

- Start from `norm:*` or `harm:*` nodes when facts are known.
- Move to `pattern:*` nodes to select argument families.
- Follow `uses_article`, `has_anchor`, `supported_by`, and package edges to build the complaint section.
