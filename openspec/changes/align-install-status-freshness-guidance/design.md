## Context

`./install.sh --status` intentionally performs a bounded unlocked structural observation and never opens the network. The installed runtime validator now emits a deterministic local content identity by default and, only with `--check-updates`, compares it with the manifest at one immutable current-main SHA. Status guidance must connect these two layers without inflating the assurance of either.

## Decisions

### 1. Preserve the fast status boundary

Status will not import, execute, or duplicate the runtime validator and will not add network access. Its JSON shape, reason codes, exit codes, target reads, and no-write guarantee remain unchanged.

### 2. Change guidance, not classification

For `clean`, the message will say that only structure was observed and that content and freshness were not checked. `recommended_action` will render a shell-quoted command using the validator beside the current repository's `install.sh`, pass the exact observed target through `--skills-root`, and include the runtime freshness flags. This avoids depending on an older installed validator that may not implement `--check-updates`. If the repository-side validator is absent, or an exact command cannot be represented because a path contains surrogateescaped filesystem bytes, guidance says so instead of emitting a dead command. Non-clean states keep their existing install/recovery guidance and do not inspect the validator path because content freshness is not useful until structural blockers are resolved.

### 3. Keep assurance boundaries explicit

The guidance will not call `current` proof of installation provenance, legal-source freshness, or filing readiness. It will not imply that a network gap requires reinstalling. Reinstallation remains appropriate for `different`, missing, or incomplete payloads, while `unknown` remains a coverage gap.

## Verification

- Test-first assertions for clean JSON and Russian human guidance.
- Regression assertions that status performs no network, validation, install, or other mutation.
- Existing full root and skill suites, strict source/runtime validation, publication guard, and clean-room install before publication.
