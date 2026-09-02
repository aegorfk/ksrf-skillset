## Context

The validator intentionally has one detailed maintainer renderer for source and
runtime profiles. The public installer already uses a separate renderer for
offline verification, but `--verify-current` still forwards the maintainer
runtime text verbatim. As a result, an ordinary user sees source-only coverage
fields that are neither installed nor actionable.

## Goals / Non-Goals

**Goals:**

- Give every public current-release outcome a short, accurate Russian summary.
- Preserve package counts, error/warning counts, content identity, bounded
  readable findings, and legal/publication boundaries.
- Render from structured fields so wording is not coupled to maintainer prose.
- Preserve the exact validator report and all exit semantics.
- Give local prerequisite and trusted-policy failures fixed actionable Russian
  messages without leaking internal lifecycle names or exception text.

**Non-Goals:**

- Do not rename validator JSON keys or enum values.
- Do not change the direct validator CLI or source-profile QA output.
- Do not change freshness lookup, manifest comparison, status preflight, or
  installation behavior.
- Do not hide validation findings or claim that a matching skillset is legally
  current or filing-ready.

## Decisions

1. **Add a public current-verification renderer beside the offline renderer.**
   The installer owns its user-facing vocabulary while the validator remains a
   stable maintainer and machine interface.
2. **Map structured outcomes explicitly.** `current`, `different`, `unknown`,
   and validation failure each receive a distinct heading and explanation.
   Unknown or invalid data fails closed and never receives a positive heading.
3. **Keep evidence useful but readable.** The renderer keeps the exact digest,
   package/error/warning counts, remote version SHA when established, and up to
   50 finding locations/messages. Shared public finding rendering escapes
   display controls, bounds each value, omits maintainer-only codes, replaces
   exception-derived and internal-coordinate findings with fixed Russian text,
   and reports how many additional findings were not printed. The raw report
   remains complete.
4. **Preserve scope boundaries in every successful validation result.** The
   output states that source-release controls are separate and that equality is
   not proof of legal freshness, provenance, or filing readiness.
5. **Keep public errors fixed and actionable.** Code `1` explains that the
   target or required verification files are unavailable, unsafe, incomplete,
   or changing. Code `2` asks the user to update the repository and retry. Raw
   exception types/messages remain available only through maintainer tooling.
6. **Bind all checks to one copied snapshot.** The coordinator copies only the
   managed packages from the held installation root into a private temporary
   directory, runs content validation and offline policy against those same
   bytes, and compares their identity with a final held-root validation. A
   temporary live-tree A/B/A substitution therefore cannot make policy and
   identity observe different generations. Capture walks held directory
   descriptors, opens files with no-follow semantics, rejects symlinks,
   special files, hard links, device and mount boundaries, and reuses the
   status limits of 20,000 entries, 32 MiB per file, and 128 MiB total.

## Risks / Trade-offs

- **Two human renderers can drift** → tests bind each structured outcome and
  forbid the known internal labels in the public wrapper.
- **Simpler wording can hide useful diagnostics** → retain digest, counts,
  remote SHA, readable finding locations/messages, and an omitted-count notice;
  exact codes remain available in the unchanged maintainer/machine report.
- **Unexpected report shapes** → coordinator validation and existing code `2`
  path remain authoritative; the renderer never invents a positive state.
- **Copying can observe concurrent writes** → the final held-root identity must
  equal the snapshot identity; any mismatch invalidates the result.
- **Less detail in public stderr** → preserve exact exit classes and keep the
  unchanged direct validator CLI for maintainer diagnostics.

## Migration Plan

Publish as a human-output-only compatibility change, regenerate the release
manifest, install the exact release, and smoke-test `unknown` live plus
deterministic tests for all other outcomes. No installed-data migration is
required.

## Open Questions

None.
