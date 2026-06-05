# KSRF Codex Skills

Private repository with Codex skills for preparing, checking, and enriching Russian Constitutional Court complaint work.

## Contents

- `skills/ksrf-argument-patterns` - corpus-grounded constitutional-law argument patterns extracted from KSRF Постановления.
- `skills/ksrf-*` - global KSRF complaint workflow skills integrated with the argument-pattern layer.
- `tools/` - local scripts for extracting and enriching the KSRF argument-pattern corpus.
- `openspec/changes/extract-ksrf-argument-pattern-skills` - OpenSpec change documenting the requirements and design.

The repository intentionally does not include the downloaded PDF corpus or extracted text cache. The current local corpus path is:

`/Users/aegorfk/Documents/ks_parser_lower_court_marker/ТЗ/Постановления КС РФ`

## Install Locally

```bash
./install.sh
```

This copies `skills/ksrf-*` into `~/.codex/skills`.

## Regenerate Enrichment References

From the source project that contains `analysis_results/ksrf_argument_patterns`:

```bash
python3 tools/enrich_ksrf_argument_patterns.py \
  --analysis /Users/aegorfk/Documents/ks_parser_lower_court_marker/analysis_results/ksrf_argument_patterns \
  --skill ./skills/ksrf-argument-patterns
```

## Notes

The constitutional argument graph is stored as portable JSON/Markdown under:

- `skills/ksrf-argument-patterns/references/constitutional_graph.json`
- `skills/ksrf-argument-patterns/references/constitutional-graph.md`

No separate graph database is required for the current workflow.
