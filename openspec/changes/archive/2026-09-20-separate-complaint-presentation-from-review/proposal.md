# Separate complaint presentation from review

## Why
The draft exporter inserts an administrative notice and sentence review IDs into the complaint itself. It also exposes the internal twelve-section model as twelve headings and leaves unresolved data without visible color. Users need a court-facing document and a separate review record, while legal readiness remains independently controlled.

## What Changes
- Use the complaint's formal header, two-line title, facts, constitutional reasoning, request, enclosures and signature as the document presentation.
- Keep workflow statuses, risk analysis and review IDs in a companion Markdown report and internal manifests.
- Preserve unknown data as explicit yellow-highlighted placeholders; never promote their support status.
- Add representative information only on the user's explicit instruction.
- Keep legal/evidence/release gates and human signing boundaries unchanged.

## Impact
Affected capabilities: `ksrf-working-draft` and new `ksrf-complaint-presentation`. Affected implementation: complaint renderer, working-draft exporter, their synthetic regression tests and global skill instructions. No private case material or reconstructive source text is included.
