## Why

Installer `--status` correctly reports only structure and transaction evidence, but its clean-state guidance still says that freshness is confirmed only by reinstalling from published `main`. The newly published runtime validator can now compare installed bytes with current canonical `main` without writing or reinstalling. Leaving the old recommendation makes the feature unnecessarily hard to discover and suggests a heavier action than required.

## What Changes

- Keep `--status` strictly offline, source-independent, bounded, and read-only.
- Make the clean message explicitly say that structure alone does not check content or freshness.
- Point the clean-state recommended action to an executable repo-side validator command with the exact target and `--profile runtime --strict --check-updates`, so an older installed validator is never required to understand the new flag.
- Provide an honest repository-update fallback when a directly copied status tool has no adjacent validator.
- Explain that reinstall remains the repair/update action only when the runtime tree differs or is incomplete.
- Cover both stable JSON and Russian human output without changing status schema or exit codes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-skillset-install-status`: align clean-state user guidance with the separate explicit runtime freshness observation.

## Impact

- `tools/install_skillset.py` clean-state message and recommended action.
- Installer status tests and public README wording.
- `skills-manifest.json` release-tool hash.
