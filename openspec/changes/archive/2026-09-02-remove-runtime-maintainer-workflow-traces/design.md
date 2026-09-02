## Context

The runtime file contract correctly removes `openspec/`, `tests/`, and `evals`, yet the installed payload still contains two user-facing references to an `OpenSpec change` and one Python docstring tied to `OpenSpec tasks 5.1--5.6`. The underlying safeguards are useful; only the unavailable maintainer coordinates are noise.

## Goals / Non-Goals

**Goals:**

- Make every installed reference understandable without repository knowledge.
- Preserve artifact contracts, negative/conflict examples, held-out evaluation, leakage review, traceability, and human approval.
- Reject future maintainer workflow names or numbered task coordinates from every runtime-eligible logical path and text file.
- Keep the finding deterministic and free of matched source text.

**Non-Goals:**

- Do not remove source specs, tests, evals, or provenance.
- Do not weaken or rename the existing safety and human-review gates.
- Do not reject ordinary legal numbering, statutory provisions, headings, or user task descriptions without an explicit maintainer-task marker.

## Decisions

### Separate bounded classifier and finding

Add `runtime_maintainer_workflow_markers(path, text)` next to the existing local-coordinate classifier. It normalizes both the logical runtime path and runtime text with NFKC, uses strict normalized JSON text for JSON files when available, and returns only stable marker classes. Physical checkout paths are used only for I/O and never enter either runtime classifier. The logical path is checked before content decoding, including for binary and unreadable files. The validator emits `RUNTIME_MAINTAINER_WORKFLOW_REFERENCE` with marker classes and the logical file path, never matched file content or a source excerpt.

The change-workflow marker recognizes the product name across case, simple horizontal-space/hyphen variants, and the compact `OpenSpecChange` form. The numbered-task marker requires explicit `internal`, `maintainer`, or `repository` context, or a `tasks.md` coordinate, followed through a bounded sequence of whitespace, punctuation, Markdown wrappers, or path/slug separators by a dotted numeric coordinate and optional range. ASCII-token boundaries treat `_`, `-`, and `/` as separators, so logical filenames cannot bypass the check. A bare user instruction such as `Task 5.1: ...` is allowed. This avoids treating ordinary user tasks or legal section numbering as repository coordinates.

### Self-safe implementation

The validator is itself installed. Its product-name token is assembled from separate source literals, and the regex source does not contain a matchable product-name occurrence. Tests and OpenSpec files may contain exact fixtures because the runtime contract excludes them.

### Wording-only cleanup

The two Markdown references retain their complete pre-implementation gate lists but replace the unavailable workflow name with a plain requirement for a separately documented and approved implementation plan. The Python docstring describes the bounded evidence contract directly and removes the numbered task range.

## Risks / Trade-offs

- [Over-broad marker rejects useful prose] → Require an explicit maintainer product name, maintainer-context task, or `tasks.md` coordinate; test ordinary user tasks and legal numbering as allowed.
- [Validator detects its own implementation] → Assemble the product token from separate literals and run the classifier over the exact release payload.
- [Cleanup accidentally weakens safeguards] → Assert the retained artifact, held-out/leakage, traceability, and human-approval language in positive tests.
- [Installer and portable validator exclusions drift] → Keep the existing root parity test for development-only parts, exact source-only paths, canonical classifications, and runtime lookalikes.
- [Physical checkout name creates false findings] → Classify only logical payload paths and cover a clean package under a deliberately marker-like external root.
- [Binary path escapes the guard] → Scan the logical path before any read/decode branch and cover an invalid-UTF-8 binary fixture.

## Migration Plan

1. Add red exact-payload and injected-file tests.
2. Add the classifier/finding and replace only the three confirmed runtime traces.
3. Run full source/runtime, clean-room, OpenSpec, skill, and independent review checks.
4. Archive the change, regenerate the manifest on current `main`, publish one atomic commit, and install the exact release.

## Open Questions

None.
